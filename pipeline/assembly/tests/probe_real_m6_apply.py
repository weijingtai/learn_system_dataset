"""C 波真书实跑探针（act/impl-07/23 verify 段「真书实跑」）。

只读 ``var/ledgers/qianyuan_w8``（**正本绝不写入**），把整份账本 ``cp -R`` 到临时目录后在其副本上跑：

1. 真 m6 → :func:`resolve_m7_inputs` → 视图
2. :func:`propose_incremental`（B 波）产出提案
3. :func:`apply_resolutions`（本波）把提案落到 knowledge：记录
   **发号结果**、**unapproved_with_self_issued_id 内容**、**identity_delta 条目数**、
   created/rebuilt 号、collation 计数、knowledge_sha256 与确定性（两次调用逐字节相同）
4. 把产出的 knowledge 喂给创世独立 Gate：验证 §8.1 的发号口径是否消掉了
   F 波实测的 ``allocation_monotonic`` 卡点（这是本波对真书路径的直接后果）
5. 结论与 B/A/F 波回报逐条对照

退出码 0 = 探针跑完（「接不上」是结论，不是失败）。
"""

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.assembly.apply import apply_resolutions  # noqa: E402
from pipeline.assembly.gate import evaluate_genesis  # noqa: E402
from pipeline.assembly.incremental import propose_incremental  # noqa: E402
from pipeline.assembly.inputs import resolve_m7_inputs  # noqa: E402
from pipeline.assembly.model import empty_snapshot_knowledge  # noqa: E402
from pipeline.ledger.service import LedgerService  # noqa: E402

SOURCE_LEDGER = ROOT / "var" / "ledgers" / "qianyuan_w8"


def _m6_revision(service):
    rows = service.store.conn.execute(
        "SELECT r.artifact_revision_id FROM stage_packages sp "
        "JOIN artifact_revisions r ON r.artifact_id = sp.artifact_id "
        "WHERE sp.stage='m6' AND r.status='sealed' ORDER BY r.created_at DESC, r.rowid DESC"
    ).fetchall()
    return rows[0][0] if rows else None


def main():
    if not SOURCE_LEDGER.exists():
        print("SKIP 真书账本不存在: %s" % SOURCE_LEDGER)
        return 0

    source_stat = (SOURCE_LEDGER / "ledger.sqlite").stat()
    before_mtime = (source_stat.st_mtime_ns, source_stat.st_size)

    status = 0
    tmp_root = Path(tempfile.mkdtemp(prefix="m7_real_m6_apply_"))
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
            technique_id = inputs["technique_id"]
            view = {
                "source_id": cset.get("source_id"),
                "candidate_set": cset,
                "reviewed_edition": reviewed,
            }
            base = empty_snapshot_knowledge(
                technique_id, {"pat_%s" % technique_id: [1, 10000]}
            )
            proposals = propose_incremental(base, [view], round_no=2)["proposals"]

            # B 波在真书上产出的 proposal_key 可能重号（同 surface ⇒ 同 subject ⇒ 同键）。
            # apply **必须** fail-closed（本探针先原样调一次证明这一点），
            # 然后为了让 C 波实跑能继续，用去重后的子集继续，并把重号如实写进回报。
            seen = {}
            duplicates = []
            for proposal in proposals:
                key = proposal["proposal_key"]
                if key in seen:
                    duplicates.append(proposal)
                else:
                    seen[key] = proposal
            applied_proposals = list(seen.values())
            collision = None
            try:
                apply_resolutions(base, [view], proposals, [])
            except Exception as exc:  # noqa: BLE001 - 探针只记录行为
                collision = "%s(%s) %s" % (type(exc).__name__, getattr(exc, "code", None), exc)

            print("\n== 1. 输入 ==")
            print("   source_id=%s  assertions=%d  patterns=%d  approved=%d"
                  % (cset.get("source_id"), len(cset.get("assertions") or []),
                     len(cset.get("patterns") or []), len(reviewed.get("approved") or [])))
            print("   proposals=%d（全部来自 B 波规则表）" % len(proposals))
            print("   其中 proposal_key 重号 %d 条（去重后 %d 条）" % (len(duplicates), len(applied_proposals)))
            for duplicate in duplicates[:5]:
                print("     dup key=%s subject=%s"
                      % (duplicate["proposal_key"], json.dumps(duplicate["subject"], ensure_ascii=False)))
            print("   原样入 apply（未去重）的行为: %s" % (collision or "未报错"))
            print("   ⚠ 真书无基底 Snapshot（创世 Gate 卡点见 F 波回报），本探针以**空基底**实跑")

            result = apply_resolutions(base, [view], applied_proposals, [])
            knowledge = result["knowledge"]
            identity_entries = result["identity_delta"]["entries"]
            collisions_note = "无"

            print("\n== 2. apply_resolutions（发号 / 身份增量）==")
            print("   knowledge_sha256=%s" % result["knowledge_sha256"])
            print("   editions=%d concepts=%d patterns=%d assertions=%d school_views=%d"
                  % (len(knowledge["editions"]), len(knowledge["concepts"]),
                     len(knowledge["patterns"]), len(knowledge["assertions"]),
                     len(knowledge["school_views"])))
            print("   id_allocation=%s" % json.dumps(knowledge["id_allocation"], ensure_ascii=False))
            print("   allocated_pattern_ids=%s" % json.dumps(knowledge["allocated_pattern_ids"], ensure_ascii=False))
            print("   retired_entity_ids=%s" % json.dumps(knowledge["retired_entity_ids"], ensure_ascii=False))
            print("   created_entity_ids (%d): %s"
                  % (len(result["created_entity_ids"]),
                     json.dumps(result["created_entity_ids"][:3], ensure_ascii=False) + ("…" if len(result["created_entity_ids"]) > 3 else "")))
            print("   rebuilt_entity_ids=%s" % json.dumps(result["rebuilt_entity_ids"], ensure_ascii=False))
            print("   identity_delta.entries=%d" % len(identity_entries))
            print("   collation.relations=%d  collation.not_comparable=%d"
                  % (len(result["collation"]["relations"]), len(result["collation"]["not_comparable"])))
            print("   resolution_log=%d 条（按 proposal_key 升序）" % len(result["resolution_log"]))
            print("   碰撞 fail-closed: %s" % collisions_note)
            print("   unapproved_with_self_issued_id (%d 条):"
                  % len(result["report"]["unapproved_with_self_issued_id"]))
            for item in result["report"]["unapproved_with_self_issued_id"]:
                print("     %s" % json.dumps(item, ensure_ascii=False))
            without_object = result["report"]["admit_new_without_object"]
            print("   admit_new 却没产出对象 (%d 条，真书均为无正式 co_ 号的 concept 候选):"
                  % len(without_object))
            for item in without_object[:5]:
                print("     %s" % json.dumps(item, ensure_ascii=False))

            again = apply_resolutions(base, [view], applied_proposals, [])
            print("\n== 3. 确定性 ==")
            print("   两次调用 knowledge_bytes 逐字节相同: %s"
                  % (again["knowledge_bytes"] == result["knowledge_bytes"]))
            print("   两次调用 identity_delta 逐字节相同: %s"
                  % (json.dumps(again["identity_delta"], sort_keys=True)
                     == json.dumps(result["identity_delta"], sort_keys=True)))

            gate = evaluate_genesis(candidate_set=cset, reviewed_edition=reviewed, knowledge=knowledge)
            failed = {key: value["detail"] for key, value in gate["checks"].items() if not value["passed"]}
            print("\n== 4. 创世独立 Gate（对 apply 的产出）==")
            print("   passed=%s" % gate["passed"])
            for key, detail in failed.items():
                print("   FAIL %s: %s" % (key, detail))
            print("   对照 F 波实测：当时 run_m7 在真书上卡 allocation_monotonic "
                  "(id_allocation[pat_qizheng]=2 != expected max 0)")

            print("\nSUMMARY real_m6_apply: assertions=%d id_allocation=%s unapproved=%d "
                  "identity_entries=%d not_comparable=%d duplicate_proposal_keys=%d "
                  "admit_new_without_object=%d gate_passed=%s"
                  % (len(knowledge["assertions"]),
                     json.dumps(knowledge["id_allocation"], ensure_ascii=False),
                     len(result["report"]["unapproved_with_self_issued_id"]),
                     len(identity_entries),
                     len(result["collation"]["not_comparable"]),
                     len(duplicates),
                     len(without_object),
                     gate["passed"]))
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
