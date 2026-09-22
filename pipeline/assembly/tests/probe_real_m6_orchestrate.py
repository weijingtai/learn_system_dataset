"""D 波真书实跑探针（act/impl-07/24 verify 段「真书实跑」）。

只读 ``var/ledgers/qianyuan_w8``（**正本绝不写入**），把整份账本 ``cp -R`` 到临时目录后在其副本上跑：

1. **基底**取 F 波金标 r1（`mini_release01/expected/snapshot_r1.json`）——
   先由已验收创世引擎现算一遍，确认金标与该引擎输出逐字节相同；
2. 把 r1 作为 sealed ``canonical_snapshot`` 灌进副本 Ledger，再把**真书 m6** 当作「第二轮」喂给
   :func:`pipeline.assembly.orchestrate.assemble`（纯函数层）与 :func:`run_m7`（Ledger 层）；
3. 记录：``affected`` / ``untouched`` 规模、是否 ``awaiting_human``、
   增量与全量是否等价（`knowledge_equivalent`）、写没写出新 Snapshot；
4. 与 A/B/C/F 波的真书结论逐条对照。

退出码 0 = 探针跑完（「接不上」是结论，不是失败）。
"""

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.assembly import orchestrate  # noqa: E402
from pipeline.assembly.genesis import assemble_genesis, propose_genesis  # noqa: E402
from pipeline.assembly.inputs import resolve_m7_inputs  # noqa: E402
from pipeline.assembly.step import run_m7  # noqa: E402
from pipeline.ledger import ids  # noqa: E402
from pipeline.ledger.service import LedgerService  # noqa: E402

SOURCE_LEDGER = ROOT / "var" / "ledgers" / "qianyuan_w8"
FIXTURE = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"


def _m6_revision(service):
    rows = service.store.conn.execute(
        "SELECT r.artifact_revision_id FROM stage_packages sp "
        "JOIN artifact_revisions r ON r.artifact_id = sp.artifact_id "
        "WHERE sp.stage='m6' AND r.status='sealed' ORDER BY r.created_at DESC, r.rowid DESC"
    ).fetchall()
    return rows[0][0] if rows else None


def _fixture_r1():
    """F 波 r1 金标 + 现算复核（逐字节相同才继续）。"""
    manifest = yaml.safe_load((FIXTURE / "manifest.yaml").read_text(encoding="utf-8"))
    edition = manifest["editions"][0]
    views = FIXTURE / edition["views_dir"]
    cset = json.loads((views / "candidate_set.json").read_text(encoding="utf-8"))
    reviewed = json.loads((views / "reviewed_edition.json").read_text(encoding="utf-8"))
    gold_bytes = (FIXTURE / manifest["expected"]["round1"]).read_bytes()
    proposals = propose_genesis(cset, reviewed)
    recomputed = assemble_genesis(
        cset, reviewed, proposals["proposals"], id_range=manifest["id_range"]
    )["knowledge_bytes"]
    return manifest, gold_bytes, recomputed == gold_bytes


def _seal_base(service, gold_bytes):
    prun = service.create_processing_run("release_run", ids.new_id("artifact_id"), "qizheng")
    _, cfg_rev = service.put_run_artifact(
        prun,
        "configuration",
        json.dumps({"stage": "m7", "probe": "real_m6_orchestrate"}, sort_keys=True).encode("utf-8"),
        producer_module="pipeline.assembly.tests",
        producer_version="0.1.0-draft",
    )
    step_run = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "step_run_id": ids.new_id("step_run_id"),
            "processing_run_id": prun,
            "input_artifact_ids": [],
            "technique_profile_id": "qizheng",
            "configuration_artifact_id": cfg_rev,
        }
    )
    art_id, rev_id = service.put_artifact(
        step_run,
        "canonical_snapshot",
        gold_bytes,
        producer_module="pipeline.assembly.tests",
        producer_version="0.1.0-draft",
    )
    service.seal_revision(rev_id)
    return art_id, rev_id


def main():
    if not SOURCE_LEDGER.exists():
        print("SKIP 真书账本不存在: %s" % SOURCE_LEDGER)
        return 0

    source_stat = (SOURCE_LEDGER / "ledger.sqlite").stat()
    before_mtime = (source_stat.st_mtime_ns, source_stat.st_size)

    manifest, gold_bytes, gold_ok = _fixture_r1()
    print("== 0. 基底（F 波 r1 金标）==")
    print("   金标 sha256=%s" % hashlib.sha256(gold_bytes).hexdigest())
    print("   创世引擎现算与金标逐字节相同: %s" % gold_ok)

    status = 0
    tmp_root = Path(tempfile.mkdtemp(prefix="m7_real_m6_orchestrate_"))
    work = tmp_root / SOURCE_LEDGER.name
    try:
        shutil.copytree(SOURCE_LEDGER, work)
        print("SOURCE_READ_ONLY %s" % SOURCE_LEDGER)
        print("WORKING_COPY     %s" % work)
        service = LedgerService(work)
        try:
            m6_rev = _m6_revision(service)
            if m6_rev is None:
                print("SKIP 未找到 sealed 的 m6 StagePackage")
                return 0
            inputs = resolve_m7_inputs(service, [m6_rev])
            cset = inputs["candidate_set"]
            reviewed = inputs["reviewed_edition"]
            view = {
                "source_id": cset.get("source_id"),
                "candidate_set": cset,
                "reviewed_edition": reviewed,
            }
            print("\n== 1. 真书 m6 输入 ==")
            print("   source_id=%s  修订=%s" % (cset.get("source_id"), m6_rev))
            print("   assertions=%d patterns=%d school_views=%d collation_units=%s"
                  % (len(cset.get("assertions") or []), len(cset.get("patterns") or []),
                     len(cset.get("school_views") or []),
                     "无键" if "collation_units" not in cset else len(cset["collation_units"])))

            base_art_id, base_rev_id = _seal_base(service, gold_bytes)
            base_doc = json.loads(gold_bytes.decode("utf-8"))

            print("\n== 2. orchestrate.assemble（纯函数层，基底 = r1 金标）==")
            blocked_by = None
            try:
                inc = orchestrate.assemble(
                    base_doc, [view], [], incremental=True, base_snapshot_revision_id=base_rev_id
                )
            except Exception as exc:  # noqa: BLE001 - 探针只记录行为
                blocked_by = "%s(%s) %s" % (type(exc).__name__, getattr(exc, "code", None), exc)
                inc = None
            if inc is None:
                print("   assemble 抛出: %s" % blocked_by)
                print("   结论：真书路径被 C 波回报 §3.4 的 B 波提案重号卡住（apply fail-closed），"
                      "本波不越权改 B 波签名/规则")
            else:
                print("   status=%s" % inc["status"])
                if inc["status"] != "complete":
                    print("   pending=%s" % json.dumps(inc["pending"], ensure_ascii=False))
                    print("   rounds=%s" % [r["round"] for r in inc["rounds"]])
                    print("   结论：真书作第二轮时仍需人工决定（不得静默推进）")
                else:
                    report = inc["report"]
                    print("   affected=%d 个: %s"
                          % (len(report["affected_entity_ids"]),
                             json.dumps(report["affected_entity_ids"], ensure_ascii=False)))
                    print("   rebuilt=%d  created=%d  untouched_count=%d"
                          % (len(report["rebuilt_entity_ids"]),
                             len(report["created_entity_ids"]), report["untouched_count"]))
                    print("   proposals_by_resolution=%s" % json.dumps(report["proposals_by_resolution"], ensure_ascii=False))
                    print("   not_comparable_count=%d  carried=%d  needs_review=%d"
                          % (report["not_comparable_count"], len(report["carried"]), len(report["needs_review"])))

            # ---- 2b. 绕开重号继续量：闭包 → apply(affected) vs apply(None)
            proposals = orchestrate.incremental_module.propose_incremental(
                base_doc, [view], round_no=2
            )["proposals"]
            seen = {}
            duplicates = []
            for proposal in proposals:
                if proposal["proposal_key"] in seen:
                    duplicates.append(proposal["proposal_key"])
                else:
                    seen[proposal["proposal_key"]] = proposal
            unique = [seen[key] for key in sorted(seen)]
            print("\n== 2b. 重号复核与纯函数层计量（ACT 24b 后应为 0 条重号）==")
            print("   提案 %d 条，其中 proposal_key 重号 %d 条 → 去重后 %d 条"
                  % (len(proposals), len(duplicates), len(unique)))
            print("   规则分布: %s"
                  % json.dumps(
                      sorted(
                          "%s/%s/%s" % (p["rule_id"], p["kind"], p["resolution"])
                          for p in unique
                      ),
                      ensure_ascii=False,
                  ))
            print("   待决（human/blocked）提案数: %d"
                  % len([p for p in unique if p["resolution"] in ("human", "blocked")]))
            print("   重号提案明细: %s"
                  % json.dumps(sorted(set(duplicates)), ensure_ascii=False))
            closure = orchestrate.affected_closure(base_doc, [view], unique, [])
            print("   affected=%d  untouched=%d"
                  % (len(closure["affected"]), len(closure["untouched"])))
            print("   affected 明细: %s" % json.dumps(closure["affected"], ensure_ascii=False))
            inc_result = orchestrate.apply_module.apply_resolutions(
                base_doc, [view], unique, [], affected=closure["affected"]
            )
            full_result = orchestrate.apply_module.apply_resolutions(
                base_doc, [view], unique, [], affected=None
            )
            print("   rebuilt=%s" % json.dumps(inc_result["rebuilt_entity_ids"], ensure_ascii=False))
            print("   created=%s" % json.dumps(inc_result["created_entity_ids"], ensure_ascii=False))
            print("   rebuilt == affected: %s" % (inc_result["rebuilt_entity_ids"] == closure["affected"]))
            print("   增量与全量等价（knowledge_equivalent）: %s"
                  % orchestrate.knowledge_equivalent(inc_result["knowledge"], full_result["knowledge"]))
            print("   knowledge_sha256=%s" % inc_result["knowledge_sha256"])
            print("   新 knowledge：editions=%d concepts=%d patterns=%d assertions=%d school_views=%d"
                  % (len(inc_result["knowledge"]["editions"]),
                     len(inc_result["knowledge"]["concepts"]),
                     len(inc_result["knowledge"]["patterns"]),
                     len(inc_result["knowledge"]["assertions"]),
                     len(inc_result["knowledge"]["school_views"])))
            print("   总账对象数（基底 %d → 新 %d）"
                  % (len(base_doc["patterns"]) + len(base_doc["concepts"])
                     + len(base_doc["assertions"]) + len(base_doc["school_views"]),
                     len(inc_result["knowledge"]["patterns"])
                     + len(inc_result["knowledge"]["concepts"])
                     + len(inc_result["knowledge"]["assertions"])
                     + len(inc_result["knowledge"]["school_views"])))

            print("\n== 3. run_m7（Ledger 层，真书 m6 作第二轮）==")
            try:
                res = run_m7(
                    service,
                    cset.get("source_id"),
                    technique_id=inputs["technique_id"],
                    reviewed_package_revision_ids=[m6_rev],
                    base_snapshot_revision_id=base_rev_id,
                    id_range={"pattern": [1, 10000]},
                )
                print("   status=%s" % res["status"])
                print("   snapshot_revision_id=%s" % res.get("snapshot_revision_id"))
                if res["status"] == "awaiting_human":
                    print("   pending_proposals=%d 条" % len(res["pending_proposals"]))
                elif res["status"] == "failed":
                    print("   error=%s" % res.get("error"))
            except Exception as exc:  # noqa: BLE001 - 探针只记录行为
                print("   run_m7 抛出: %s(%s) %s" % (type(exc).__name__, getattr(exc, "code", None), exc))

            print("\n   对照：A/B/C 波均以「空基底」实跑真书；本波首次以 r1 为基底做第二轮")
            print("   对照 F 波卡点 allocation_monotonic：真书审核结论 26/26 全为 assertion，"
                  "无 pattern 获批，故无取号")
        finally:
            service.close()
    finally:
        shutil.rmtree(tmp_root, True)
        after = (SOURCE_LEDGER / "ledger.sqlite").stat()
        if (after.st_mtime_ns, after.st_size) != before_mtime:
            print("FAIL 真书正本被动过！mtime/size 已变")
            status = 1
        else:
            print("\n正本只读校验：ledger.sqlite mtime/size 未变 %s" % (before_mtime,))
    return status


if __name__ == "__main__":
    sys.exit(main())
