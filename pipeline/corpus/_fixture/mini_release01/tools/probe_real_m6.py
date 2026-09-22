#!/usr/bin/env python
"""真书 m6 实跑探针（act/impl-07/20 契约二）。

回答一个问题：**真实 m6 产物能不能接上 M7，形状与 `mini_release01` fixture 假定的差在哪里。**

纪律
----
1. **真书正本只读**：脚本只 `cp -R` 到临时目录，之后全部读写都发生在副本上；
   正本路径从不交给 `LedgerService`，也不会被写。
2. 本波**不要求汇编跑通**：探针把「接不上」当作结论记录，不当作失败。
3. 退出码：0 = 探针跑完（结论可以是「接不上」）；1 = 探针自身异常；3 = 前置缺失。

用法
----
    .venv/bin/python pipeline/corpus/_fixture/mini_release01/tools/probe_real_m6.py
    .venv/bin/python .../probe_real_m6.py --source-ledger var/ledgers/qianyuan_w8 --json
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from pipeline.assembly import model as m7_model  # noqa: E402
from pipeline.assembly.gate import evaluate_genesis  # noqa: E402
from pipeline.assembly.genesis import assemble_genesis, propose_genesis  # noqa: E402
from pipeline.assembly.inputs import resolve_m7_inputs  # noqa: E402
from pipeline.assembly.step import run_m7  # noqa: E402
from pipeline.ledger import ids  # noqa: E402
from pipeline.ledger.service import LedgerService  # noqa: E402

DEFAULT_SOURCE = "var/ledgers/qianyuan_w8"
FIXTURE_DIR = Path(__file__).resolve().parents[1]


def _short(value, limit=180):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= limit else text[:limit] + "…"


def _fixture_assumptions():
    """读取 fixture 声明的上游假定，供逐条对照。"""
    import yaml

    manifest = yaml.safe_load((FIXTURE_DIR / "manifest.yaml").read_text(encoding="utf-8"))
    return manifest.get("upstream_assumptions", [])


def probe(source_ledger: Path, technique_id: str, report: dict) -> int:
    if not source_ledger.is_dir():
        print("BLOCKED 前置缺失：真书账本目录不存在 %s" % source_ledger)
        return 3

    tmp = Path(tempfile.mkdtemp(prefix="m7_real_m6_probe_"))
    ledger_copy = tmp / source_ledger.name
    shutil.copytree(source_ledger, ledger_copy)
    print("SOURCE_READ_ONLY %s" % source_ledger)
    print("WORKING_COPY     %s" % ledger_copy)

    service = LedgerService(ledger_copy)
    try:
        # ---------------------------------------------------------- 1) 账本清单
        inventory = []
        for row in service.store.conn.execute(
            "SELECT sp.stage, sp.stage_package_id, ar.artifact_revision_id, ar.status "
            "FROM stage_packages sp JOIN artifact_revisions ar ON ar.artifact_id = sp.artifact_id "
            "ORDER BY sp.stage"
        ):
            inventory.append(
                {"stage": row[0], "stage_package_id": row[1], "revision_id": row[2], "status": row[3]}
            )
        report["stage_packages"] = inventory
        print("\n== 1. StagePackage 清单 ==")
        for item in inventory:
            print("   %-4s %-38s %s %s" % (item["stage"], item["stage_package_id"], item["status"], item["revision_id"]))

        m6 = [item for item in inventory if item["stage"] == "m6"]
        if not m6:
            print("BLOCKED 前置缺失：账本内无 m6 StagePackage")
            return 3
        m6_rev = m6[0]["revision_id"]

        # ------------------------------------------------- 2) 输入解析能不能接上
        print("\n== 2. resolve_m7_inputs（M7 上游解析）==")
        try:
            inputs = resolve_m7_inputs(service, [m6_rev])
            report["resolve_ok"] = True
            print("   OK  technique_id=%s edition_part=%s" % (inputs["technique_id"], inputs["edition_part_artifact_id"]))
        except Exception as exc:  # noqa: BLE001
            report["resolve_ok"] = False
            report["resolve_error"] = "%s: %s" % (type(exc).__name__, exc)
            print("   接不上  %s: %s" % (type(exc).__name__, exc))
            print("\nSUMMARY real_m6_resolvable=False")
            return 0

        cset = inputs["candidate_set"]
        reviewed = inputs["reviewed_edition"]
        package = inputs["reviewed_package"]

        # ------------------------------------------------------ 3) M7 model 校验
        print("\n== 3. M7 model 校验（真实文档）==")
        report["model_validation"] = {}
        for name, fn, doc in (
            ("validate_candidate_set", m7_model.validate_candidate_set, cset),
            ("validate_reviewed_edition", m7_model.validate_reviewed_edition, reviewed),
            ("validate_reviewed_package", m7_model.validate_reviewed_package, package),
        ):
            try:
                fn(doc)
                report["model_validation"][name] = "ok"
                print("   OK   %s" % name)
            except Exception as exc:  # noqa: BLE001
                report["model_validation"][name] = "%s: %s" % (type(exc).__name__, exc)
                print("   红   %s -> %s: %s" % (name, type(exc).__name__, exc))

        # --------------------------------------------- 4) 字段形状逐条对照 fixture
        print("\n== 4. 真实 m6 字段形状 vs fixture 假定 ==")
        approved_kinds = sorted({item["kind"] for item in reviewed.get("approved", [])})
        collation_keys = sorted({repr(a.get("collation_key")) for a in cset.get("assertions", [])})
        link_keys = sorted(reviewed.get("evidence_links", [{}])[0].keys())
        decision_keys = sorted(reviewed.get("decisions", [{}])[0].keys()) if reviewed.get("decisions") else []
        observed = {
            "evidence_level": cset.get("evidence_level"),
            "span_layer": cset.get("span_layer"),
            "collation_units_present": "collation_units" in cset or "collation_units" in reviewed,
            "assertion_collation_key_values": collation_keys,
            "approved_kinds": approved_kinds,
            "approved_count": len(reviewed.get("approved", [])),
            "rejected_count": len(reviewed.get("rejected", [])),
            "candidate_patterns": len(cset.get("patterns", [])),
            "candidate_school_views": len(cset.get("school_views", [])),
            "candidate_concept_mentions": len(cset.get("concept_mentions", [])),
            "candidate_new_concept_candidates": len(cset.get("new_concept_candidates", [])),
            "candidate_disputes": len(cset.get("disputes", [])),
            "candidate_counts_keys": sorted(cset.get("counts", {}).keys()),
            "reviewed_edition_school_views": len(reviewed.get("school_views", [])),
            "decision_keys": decision_keys,
            "evidence_link_keys": link_keys,
            "evidence_links": len(reviewed.get("evidence_links", [])),
            "reviewed_edition_unresolved_count": reviewed.get("unresolved_count"),
            "package_keys": sorted(package.keys()),
        }
        report["observed"] = observed
        for key, value in observed.items():
            print("   %-34s %s" % (key, _short(value)))

        print("\n   fixture 声明的上游假定（逐条见 manifest.upstream_assumptions）：")
        report["fixture_assumptions"] = _fixture_assumptions()
        for item in report["fixture_assumptions"]:
            print("   [%s] %s" % (item["id"], item["statement"]))
            print("        真书实测：%s" % item["real_m6_observed"])

        # ---------------------------------------------------- 5) 纯函数干跑 + Gate
        print("\n== 5. propose/assemble/gate（副本上干跑，不落库）==")
        proposals = propose_genesis(cset, reviewed)
        asm = assemble_genesis(cset, reviewed, proposals["proposals"], id_range={"pattern": [1, 10000]})
        gate = evaluate_genesis(candidate_set=cset, reviewed_edition=reviewed, knowledge=asm["knowledge"])
        report["dry_run"] = {
            "proposals": len(proposals["proposals"]),
            "report": asm["report"],
            "gate_passed": gate["passed"],
            "gate_failed_checks": {k: v["detail"] for k, v in gate["checks"].items() if not v["passed"]},
        }
        print("   proposals=%d  report=%s" % (len(proposals["proposals"]), _short(asm["report"])))
        print("   gate_passed=%s" % gate["passed"])
        for name, detail in report["dry_run"]["gate_failed_checks"].items():
            print("   Gate FAIL %s | %s" % (name, detail))

        # ------------------------------------------------------- 6) 真实 run_m7
        print("\n== 6. run_m7（副本上实跑）==")
        before = service.get_revision(m6_rev)
        try:
            res = run_m7(
                service,
                inputs["edition_part_artifact_id"],
                technique_id=technique_id,
                reviewed_package_revision_ids=[m6_rev],
            )
            after = service.get_revision(m6_rev)
            report["run_m7"] = {
                "status": res["status"],
                "gate_passed": res["gate"]["passed"],
                "failed_checks": {k: v["detail"] for k, v in res["gate"]["checks"].items() if not v["passed"]},
                "upstream_unchanged": before["status"] == after["status"] and before["sha256"] == after["sha256"],
            }
            print("   status=%s gate_passed=%s" % (res["status"], res["gate"]["passed"]))
            for name, detail in report["run_m7"]["failed_checks"].items():
                print("   Gate FAIL %s | %s" % (name, detail))
            print("   上游 m6 未被改动：%s" % report["run_m7"]["upstream_unchanged"])
        except Exception as exc:  # noqa: BLE001
            report["run_m7"] = {"raised": "%s: %s" % (type(exc).__name__, exc)}
            print("   RAISED %s: %s" % (type(exc).__name__, exc))

        # ------------------------------------------- 7) D-02 scope 键在真账本可行
        print("\n== 7. D-02（ReleaseRun scope 键）在真账本副本上验证 ==")
        scope_key = ids.new_id("artifact_id")
        proc_id = service.create_processing_run("release_run", scope_key, technique_id)
        cfg_artifact_id, cfg_rev_id = service.put_run_artifact(
            proc_id,
            "configuration",
            json.dumps({"stage": "m7", "task": "assemble", "probe": True}, sort_keys=True).encode("utf-8"),
            artifact_id=scope_key,
            producer_module="probe_real_m6",
            producer_version="0.1.0-draft",
        )
        probe_step = service.begin_step_run(
            {
                "schema_version": "1.0.0",
                "step_run_id": ids.new_id("step_run_id"),
                "processing_run_id": proc_id,
                "input_artifact_ids": [m6_rev],
                "technique_profile_id": technique_id,
                "configuration_artifact_id": cfg_rev_id,
            }
        )
        for task in ("probe_r1", "probe_r2"):
            service.write_checkpoint(
                probe_step,
                edition_part_id=scope_key,
                stage="m7",
                completed_tasks=[{"task_id": task, "artifact_revision_id": cfg_rev_id, "status": "succeeded"}],
                human_decisions=[],
                pending_queue=[],
                next_pointer=None,
            )
        chain = service.list_checkpoints(scope_key, "m7")
        second_key = ids.new_id("artifact_id")
        second_proc = service.create_processing_run("release_run", second_key, technique_id)
        _, second_cfg = service.put_run_artifact(
            second_proc,
            "configuration",
            json.dumps({"stage": "m7", "task": "assemble"}, sort_keys=True).encode("utf-8"),
            artifact_id=second_key,
            producer_module="probe_real_m6",
            producer_version="0.1.0-draft",
        )
        second_step = service.begin_step_run(
            {
                "schema_version": "1.0.0",
                "step_run_id": ids.new_id("step_run_id"),
                "processing_run_id": second_proc,
                "input_artifact_ids": [m6_rev],
                "technique_profile_id": technique_id,
                "configuration_artifact_id": second_cfg,
            }
        )
        service.write_checkpoint(
            second_step,
            edition_part_id=second_key,
            stage="m7",
            completed_tasks=[{"task_id": "probe_r1", "artifact_revision_id": second_cfg, "status": "succeeded"}],
            human_decisions=[],
            pending_queue=[],
            next_pointer=None,
        )
        report["d02"] = {
            "scope_key": scope_key,
            "configuration_artifact_is_scope_key": cfg_artifact_id == scope_key,
            "chain_len": len(chain),
            "chain_chained": bool(chain)
            and chain[0]["prev_checkpoint_revision_id"] is None
            and len(chain) > 1
            and chain[1]["prev_checkpoint_revision_id"] == chain[0]["artifact_revision_id"],
            "second_run_chain_len": len(service.list_checkpoints(second_key, "m7")),
            "first_chain_untouched": len(service.list_checkpoints(scope_key, "m7")) == len(chain),
        }
        for key, value in report["d02"].items():
            print("   %-34s %s" % (key, value))

        print("\nSUMMARY real_m6_resolvable=True run_m7_status=%s gate_passed=%s" % (
            report.get("run_m7", {}).get("status", "raised"),
            report.get("dry_run", {}).get("gate_passed"),
        ))
        return 0
    finally:
        service.close()
        shutil.rmtree(tmp, True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="probe_real_m6")
    parser.add_argument("--source-ledger", default=DEFAULT_SOURCE)
    parser.add_argument("--technique-id", default="qizheng")
    parser.add_argument("--json", action="store_true", help="额外输出 JSON 报告")
    args = parser.parse_args(argv)

    source = Path(args.source_ledger)
    if not source.is_absolute():
        source = REPO_ROOT / source
    report = {"source_ledger": str(source), "technique_id": args.technique_id}
    code = probe(source, args.technique_id, report)
    if args.json:
        print("\n" + json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
