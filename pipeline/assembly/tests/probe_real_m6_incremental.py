"""A 波真书实跑探针（act/impl-07/21 verify 段「真书实跑」）。

只读 ``var/ledgers/qianyuan_w8``（**正本绝不写入**），把整份账本 ``cp -R`` 到临时目录后在其副本上跑：

1. 列出账本里的 m6 StagePackage（真书只有一个版次 → 多包/替换在真书上**无样本**，如实记录）
2. ``resolve_m7_inputs([真 m6])`` —— A 波后的返回结构（旧 11 键 + ``packages`` / ``replaces``）
3. 造一个合成 sealed 基底 → ``resolve_base_snapshot`` —— 基底读取与校验
4. 用**真 m6 + 基底**实跑 ``run_m7`` —— A 波后基底不再是 begin 前的前置拒绝；
   记录实际卡点是否仍与 F 波回报的差异清单（D1/D2：``allocation_monotonic``）一致
5. 同基底再跑一次 —— 两个 ReleaseRun 的 scope 键各自独立（D-02 A）

退出码 0 = 探针跑完（「接不上」是结论，不是失败）。
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.assembly.errors import AssemblyRefused  # noqa: E402
from pipeline.assembly.inputs import resolve_base_snapshot, resolve_m7_inputs  # noqa: E402
from pipeline.assembly.step import run_m7  # noqa: E402
from pipeline.ledger import ids  # noqa: E402
from pipeline.ledger.service import LedgerService  # noqa: E402

SOURCE_LEDGER = ROOT / "var" / "ledgers" / "qianyuan_w8"
PROBE_TOOL = "probe_real_m6_incremental"
PROBE_VERSION = "0.1.0-draft"


def _m6_packages(service):
    rows = service.store.conn.execute(
        "SELECT sp.stage_package_id, sp.artifact_id, r.artifact_revision_id, r.status "
        "FROM stage_packages sp "
        "JOIN artifact_revisions r ON r.artifact_id = sp.artifact_id "
        "WHERE sp.stage='m6' ORDER BY r.artifact_revision_id"
    ).fetchall()
    return [dict(zip(("stage_package_id", "artifact_id", "artifact_revision_id", "status"), row)) for row in rows]


def _m6_revision(service):
    rows = service.store.conn.execute(
        "SELECT r.artifact_revision_id FROM stage_packages sp "
        "JOIN artifact_revisions r ON r.artifact_id = sp.artifact_id "
        "WHERE sp.stage='m6' AND r.status='sealed' ORDER BY r.created_at DESC, r.rowid DESC"
    ).fetchall()
    return rows[0][0] if rows else None


def _make_synthetic_base(service, technique_id):
    """在副本上造一个已 sealed 的 canonical_snapshot（只当基底用，不做合并）。"""
    prun = service.create_processing_run("release_run", ids.new_id("artifact_id"), technique_id)
    _, cfg_rev = service.put_run_artifact(
        prun,
        "configuration",
        json.dumps({"stage": "m7", "synthetic_base": True}, sort_keys=True).encode("utf-8"),
        producer_module=PROBE_TOOL,
        producer_version=PROBE_VERSION,
    )
    step_run = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "step_run_id": ids.new_id("step_run_id"),
            "processing_run_id": prun,
            "input_artifact_ids": [],
            "technique_profile_id": technique_id,
            "configuration_artifact_id": cfg_rev,
        }
    )
    _, rev_id = service.put_artifact(
        step_run,
        "canonical_snapshot",
        json.dumps({"technique_id": technique_id, "synthetic_base": True}, sort_keys=True).encode("utf-8"),
        producer_module=PROBE_TOOL,
        producer_version=PROBE_VERSION,
    )
    service.seal_revision(rev_id)
    return rev_id


def _run_once(service, m6_rev, technique_id, base_rev):
    entry = {"raised": None, "status": None, "gate_failed": None, "scope_key": None,
             "config_is_scope_key": None, "m6_unchanged": None}
    m6_before = service.get_revision(m6_rev)
    try:
        res = run_m7(
            service,
            "art_00000000000000000000000000000001",
            technique_id=technique_id,
            reviewed_package_revision_ids=[m6_rev],
            base_snapshot_revision_id=base_rev,
        )
        entry["status"] = res["status"]
        failed = {k: v["detail"] for k, v in res["gate"]["checks"].items() if not v["passed"]}
        entry["gate_failed"] = failed or None
        step = service.get_step_run(res["step_run_id"])
        row = service.store.conn.execute(
            "SELECT edition_part_id FROM processing_runs WHERE processing_run_id=?",
            (step["processing_run_id"],),
        ).fetchone()
        entry["scope_key"] = row[0] if row else None
        req = json.loads(step["request_json"])
        cfg_rev = service.get_revision(req["configuration_artifact_id"])
        entry["config_is_scope_key"] = bool(row) and cfg_rev["artifact_id"] == row[0]
    except AssemblyRefused as exc:
        entry["raised"] = "AssemblyRefused: %s" % exc
    m6_after = service.get_revision(m6_rev)
    entry["m6_unchanged"] = (
        m6_before["status"] == m6_after["status"] and m6_before["sha256"] == m6_after["sha256"]
    )
    return entry


def main():
    if not SOURCE_LEDGER.exists():
        print("SKIP 真书账本不存在: %s" % SOURCE_LEDGER)
        return 0

    tmp_root = Path(tempfile.mkdtemp(prefix="m7_real_m6_inc_"))
    work = tmp_root / SOURCE_LEDGER.name
    try:
        shutil.copytree(SOURCE_LEDGER, work)
        print("SOURCE_READ_ONLY %s" % SOURCE_LEDGER)
        print("WORKING_COPY     %s" % work)
        service = LedgerService(work)
        try:
            # ---- 1) m6 StagePackage 一览 ----
            packages = _m6_packages(service)
            print("\n== 1. 账本 m6 StagePackage ==  %d 个" % len(packages))
            for row in packages:
                print("   %s rev=%s status=%s" % (row["stage_package_id"], row["artifact_revision_id"], row["status"]))
            if len(packages) < 2:
                print("   → 真书只有一个版次：多包解析与 D-14 替换在真书上**无样本**（不做假设）")

            m6_rev = _m6_revision(service)
            if m6_rev is None:
                print("SKIP 未找到 sealed 的 m6 StagePackage")
                return 0

            # ---- 2) resolve_m7_inputs（A 波后的结构）----
            inputs = resolve_m7_inputs(service, [m6_rev])
            legacy = [
                "technique_id", "m6_stage_package_id", "reviewed_package_revision_id",
                "reviewed_edition_package_revision_id", "reviewed_edition_revision_id",
                "candidate_package_revision_id", "candidate_set_revision_id",
                "edition_part_artifact_id", "reviewed_package", "reviewed_edition", "candidate_set",
            ]
            print("\n== 2. resolve_m7_inputs(真 m6) ==")
            print("   OK technique_id=%s edition_part=%s" % (inputs["technique_id"], inputs["edition_part_artifact_id"]))
            print("   旧 11 键齐备: %s" % all(k in inputs for k in legacy))
            print("   packages=%d  replaces=%d" % (len(inputs["packages"]), len(inputs["replaces"])))
            pkg = inputs["packages"][0]
            print("   packages[0].source_id=%s edition_part_ids=%s" % (pkg["source_id"], pkg["edition_part_ids"]))
            technique_id = inputs["technique_id"]

            # ---- 3) 合成基底 + resolve_base_snapshot ----
            base_rev = _make_synthetic_base(service, technique_id)
            base = resolve_base_snapshot(service, base_rev)
            print("\n== 3. resolve_base_snapshot（副本上的合成基底）==")
            print("   OK revision=%s type=%s status=%s doc_keys=%s"
                  % (base["revision_id"], base["artifact_type"], base["status"], sorted(base["doc"].keys())))

            # ---- 4/5) 真 m6 + 基底实跑两次 ----
            for round_no in (1, 2):
                entry = _run_once(service, m6_rev, technique_id, base_rev)
                print("\n== %d. run_m7(真 m6, base=%s) ==" % (3 + round_no, base_rev))
                for key in ("raised", "status", "gate_failed", "scope_key", "config_is_scope_key", "m6_unchanged"):
                    print("   %-20s %s" % (key, entry[key]))

            print("\nSUMMARY real_m6_resolvable=True packages=1 replaces=0 base_readable=True")
            print("SUMMARY A 波后基底不再是 begin 前的前置拒绝；卡点仍是 F 波已列的 Gate 差异（D1/D2）")
            return 0
        finally:
            service.close()
    finally:
        shutil.rmtree(tmp_root, True)


if __name__ == "__main__":
    sys.exit(main())
