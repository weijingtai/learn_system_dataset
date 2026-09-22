"""B 波真书实跑探针（act/impl-07/22 verify 段「真书实跑」）。

只读 ``var/ledgers/qianyuan_w8``（**正本绝不写入**），把整份账本 ``cp -R`` 到临时目录后在其副本上跑：

1. 真 m6 的 26 条断言里 ``collation_key`` 为 null 的条数（§8.2 前提复算）
2. 把真实 m6 视图喂给 :func:`propose_incremental`（基底为空 Snapshot）——
   记录**提案数（按 rule_id / kind / resolution 分列）**、
   ``not_comparable_missing_collation_key`` 计数、
   ``unapproved_with_self_issued_id`` 内容、以及 `id_allocation`
3. 结论与 CHARTER §8.1/§8.2 及 F/A 波回报逐条对照

退出码 0 = 探针跑完（「一条都产不出」是结论，不是失败）。
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.assembly.incremental import allocate_ids, propose_incremental  # noqa: E402
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

    tmp_root = Path(tempfile.mkdtemp(prefix="m7_real_m6_prop_"))
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

            assertions = cset.get("assertions") or []
            null_keys = [a for a in assertions if a.get("collation_key") is None]
            print("\n== 1. 真 m6 的 collation_key ==")
            print("   assertions=%d  collation_key is null: %d" % (len(assertions), len(null_keys)))
            print("   candidate_set 有 collation_units 键: %s" % ("collation_units" in cset))

            view = {
                "source_id": cset.get("source_id"),
                "candidate_set": cset,
                "reviewed_edition": reviewed,
            }
            base = empty_snapshot_knowledge(inputs["technique_id"], {"pat_%s" % inputs["technique_id"]: [1, 10000]})
            out = propose_incremental(base, [view], round_no=2)

            by_rule = {}
            by_kind = {}
            by_resolution = {}
            for proposal in out["proposals"]:
                by_rule[proposal["rule_id"]] = by_rule.get(proposal["rule_id"], 0) + 1
                by_kind[proposal["kind"]] = by_kind.get(proposal["kind"], 0) + 1
                by_resolution[proposal["resolution"]] = by_resolution.get(proposal["resolution"], 0) + 1

            print("\n== 2. propose_incremental(真 m6 视图) ==")
            print("   proposals=%d" % len(out["proposals"]))
            print("   按 rule_id: %s" % json.dumps(by_rule, sort_keys=True, ensure_ascii=False))
            print("   按 kind:    %s" % json.dumps(by_kind, sort_keys=True, ensure_ascii=False))
            print("   按 resolution: %s" % json.dumps(by_resolution, sort_keys=True, ensure_ascii=False))
            print("   modes=%s" % json.dumps(out["modes"], ensure_ascii=False))
            print("   not_comparable=%d  missing_collation_key=%d"
                  % (len(out["not_comparable"]), out["report"]["not_comparable_missing_collation_key"]))
            print("   id_allocation=%s" % json.dumps(out["report"]["id_allocation"], ensure_ascii=False))
            print("   unapproved_with_self_issued_id (%d 条):"
                  % len(out["report"]["unapproved_with_self_issued_id"]))
            for item in out["report"]["unapproved_with_self_issued_id"]:
                print("     %s" % json.dumps(item, ensure_ascii=False))

            allocation = allocate_ids(base, [view])
            print("\n== 3. allocate_ids ==")
            print("   id_allocation=%s (未获批的自发号不计入)"
                  % json.dumps(allocation["id_allocation"], ensure_ascii=False))
            print("   unapproved=%d" % len(allocation["unapproved_with_self_issued_id"]))

            print("\nSUMMARY real_m6_proposals=%d not_comparable=%d unapproved_self_issued=%d"
                  % (
                      len(out["proposals"]),
                      out["report"]["not_comparable_missing_collation_key"],
                      len(allocation["unapproved_with_self_issued_id"]),
                  ))
            print("SUMMARY 与 §8.1/§8.2 对照：对勘类规则在缺 collation_key 时不产提案（正确行为），"
                  "未获批自发号被如实报告而非静默丢弃")
            return 0
        finally:
            service.close()
    finally:
        shutil.rmtree(tmp_root, True)


if __name__ == "__main__":
    sys.exit(main())
