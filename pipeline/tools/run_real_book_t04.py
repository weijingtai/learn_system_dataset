"""真书《乾元秘旨》调度器 M1→M8 全线执行脚本（阶段 4）。

在空账本 var/ledgers/qianyuan_t04 上新建 EditionRun：
1. 预检：源文件与 6 份 M4 提交件哈希核对（与副本完全一致）；
2. 调度推进：M1→M3；
3. M4 提交件登记入库并 advance 至 awaiting_human 暂停；
4. 回放只读参考账本副本 var/ledgers/qianyuan_w8 上的 24 条 M4 裁决；
5. resume 恢复并自动推进通过 M5；
6. advance 至 M6 awaiting_human 暂停；
7. 回放 26 条 M6 审核决定；
8. resume 恢复，收口 EditionRun；
9. run_release 运行 M7 创世与 M8 编译；
10. 输出全阶段汇总报告数据与对位表。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml

from pipeline.contract_registry.catalog import load_registry
from pipeline.contract_registry.ports import DirectLedgerAdapter
from pipeline.knowledge_extraction.serialize import canonical_json
from pipeline.knowledge_extraction.submission import validate_submission
from pipeline.knowledge_extraction.submit import _parse_submission, run_m4_submit
from pipeline.ledger.service import LedgerReader
from pipeline.orchestrator import EDITION_STAGES
from pipeline.orchestrator.edition_run import (
    advance,
    run_release,
    run_until,
    start_edition_run,
)
from pipeline.orchestrator.human import resume
from pipeline.tools.replay_human_decisions import (
    ReplayMismatchError,
    load_m4_rulings_from_ledger,
    load_m6_decisions_from_ledger,
    load_m6_supplement_decisions,
    replay_m4_rulings,
    replay_m6_decisions,
)

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "pipeline" / "corpus" / "_fixture" / "qianyuan_ed01_text"
M4_DIR = HOST / "m4"
CANON_DIR = ROOT / "pipeline" / "schemas" / "shared" / "canon"
REF_LEDGER = ROOT / "var" / "ledgers" / "qianyuan_w8"
TARGET_LEDGER = ROOT / "var" / "ledgers" / "qianyuan_t04"

SUBMISSION_FILES = (
    "submission_assertion_a.yaml",
    "submission_assertion_b.yaml",
    "submission_pattern_a.yaml",
    "submission_pattern_b.yaml",
    "submission_concept_mention_a.yaml",
    "submission_concept_mention_b.yaml",
)

EXPECTED_RAW_SHA256 = "3f7170cd504e496096bc933ab5ed8805d68fa98625c91c5c09a9e3a61fcecdbb"


def verify_inputs_and_hashes() -> dict[str, str]:
    """开跑前核对原始文本与 6 份提交件 sha256，不符即停手报错。"""
    raw_path = HOST / "qianyuan_ed01_text.md"
    if not raw_path.is_file():
        raise FileNotFoundError(f"缺少原始文本: {raw_path}")

    raw_bytes = raw_path.read_bytes()
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    if raw_sha != EXPECTED_RAW_SHA256:
        raise ReplayMismatchError(
            f"原始文本 sha256 不符: 实际 {raw_sha} != 预期 {EXPECTED_RAW_SHA256}"
        )

    source_info_path = HOST / "source_info.yaml"
    source_info = yaml.safe_load(source_info_path.read_text(encoding="utf-8"))
    if source_info.get("file_sha256") != EXPECTED_RAW_SHA256:
        raise ReplayMismatchError(
            f"source_info.yaml file_sha256 不符: {source_info.get('file_sha256')}"
        )

    # 查验只读参考副本中的 6 个 candidate_submission
    submission_shas = {}
    with LedgerReader(REF_LEDGER) as reader:
        # 获取候选提交修订
        revs = reader.list_revisions(artifact_type="candidate_submission")
        ref_shas = {r["sha256"] for r in revs}

        for name in SUBMISSION_FILES:
            file_path = M4_DIR / name
            if not file_path.is_file():
                raise FileNotFoundError(f"缺少 M4 提交件: {file_path}")
            raw_content = file_path.read_bytes()
            doc = validate_submission(
                _parse_submission(raw_content), technique_id="qizheng"
            )
            canonical_bytes = canonical_json(doc)
            c_sha = hashlib.sha256(canonical_bytes).hexdigest()
            if c_sha not in ref_shas:
                raise ReplayMismatchError(
                    f"M4 提交件 {name} 的 canonical json sha256 ({c_sha}) 未在参考账本中找到！"
                )
            submission_shas[name] = c_sha

    return submission_shas


def run_full_pipeline(
    clean_target: bool = False,
    supplement_file: Path | str | None = None,
) -> dict[str, Any]:
    """在空账本上真跑 M1→M8 全流程，回放人工决定，返回统计与对位表。"""
    # 1. 预检
    print("[1/10] 核对源文件与 M4 提交件哈希...")
    sub_shas = verify_inputs_and_hashes()
    print(f"      源文件 SHA256 与 6 份 M4 提交件哈希比对通过 ({len(sub_shas)} 份)")

    # 2. 准备目标新账本目录
    if TARGET_LEDGER.exists() and clean_target:
        print(f"      清理目标账本目录: {TARGET_LEDGER}")
        shutil.rmtree(TARGET_LEDGER)
    TARGET_LEDGER.mkdir(parents=True, exist_ok=True)

    adapter = DirectLedgerAdapter(TARGET_LEDGER)
    service = adapter.unwrap()
    registry = load_registry()

    source_info = yaml.safe_load((HOST / "source_info.yaml").read_text(encoding="utf-8"))
    edition_part_id = source_info["edition_part"]["artifact_id"]

    try:
        # 3. 启动 EditionRun
        print("[2/10] 新建 EditionRun...")
        handle = start_edition_run(
            adapter,
            edition_part_id=edition_part_id,
            technique_id="qizheng",
            run_inputs={
                "route": "text",
                "source_dir": str(HOST),
                "source_info": source_info,
                "technique_profile": {
                    "technique_id": "qizheng",
                    "canon_dir": str(CANON_DIR),
                },
            },
        )
        edition_run_id = handle["processing_run_id"]
        print(f"      EditionRun ID: {edition_run_id}")

        # 4. 推进至 M3
        print("[3/10] 推进至 M3 (run_until m3)...")
        m1_m3_results = run_until(adapter, registry, handle, "m3")
        for res in m1_m3_results:
            if res.get("action") == "executed":
                print(f"      阶段 {res['stage']}: {res['step_result']['status']}")
                if res["step_result"]["status"] != "succeeded":
                    raise RuntimeError(f"阶段 {res['stage']} 失败: {res}")

        # 5. 登记 6 份 M4 提交件
        print("[4/10] 经公开入口登记 6 份 M4 提交件 (run_m4_submit)...")
        for name in SUBMISSION_FILES:
            summary = run_m4_submit(
                service,
                edition_part_id,
                (M4_DIR / name).read_bytes(),
                producer_module=f"t04_host:{name}",
                producer_version="0.1.0",
            )
            if summary.get("status") != "succeeded":
                raise RuntimeError(f"提交件 {name} 登记失败: {summary}")
        print("      6 份 M4 提交件登记成功")

        # 6. advance 停在 M4 awaiting_human
        print("[5/10] advance 推进 M4...")
        item_m4 = advance(adapter, registry, handle)
        if (
            item_m4.get("action") != "executed"
            or item_m4.get("stage") != "m4"
            or item_m4.get("step_result", {}).get("status") != "awaiting_human"
        ):
            raise RuntimeError(f"M4 未停在 awaiting_human: {item_m4}")

        m4_srun_id = item_m4["step_run_id"]
        m4_token = item_m4["step_result"]["resume_token"]
        print(f"      M4 暂停在 awaiting_human, StepRun: {m4_srun_id}")

        # 7. 回放 24 条 M4 类别裁决
        print("[6/10] 从参考副本回放 24 条 M4 类别裁决...")
        with LedgerReader(REF_LEDGER) as reader:
            old_disputes, old_rulings = load_m4_rulings_from_ledger(reader)
            m4_applied = replay_m4_rulings(
                service,
                m4_srun_id,
                m4_token,
                old_disputes=old_disputes,
                old_rulings=old_rulings,
            )
        print(f"      M4 回放完成: 成功登记 {len(m4_applied)} 条裁决")

        # 记录 M4 对位表 (old_event_rev -> new_event_rev)
        new_m4_events = service.list_human_events(m4_srun_id)
        new_m4_by_did = {}
        for ev in new_m4_events:
            ev_doc = json.loads(
                adapter.read_object(
                    service.get_revision(ev["event_revision_id"])["sha256"]
                ).decode("utf-8")
            )
            new_m4_by_did[ev_doc["dispute_id"]] = ev["event_revision_id"]

        m4_alignment_table = []
        for did, old_r in sorted(old_rulings.items()):
            m4_alignment_table.append(
                {
                    "dispute_id": did,
                    "old_event_revision_id": old_r["_event_revision_id"],
                    "new_event_revision_id": new_m4_by_did.get(did),
                    "choice": old_r["choice"],
                    "actor_ref": old_r.get("actor_ref"),
                }
            )

        # 恢复 M4 并推进通过 M5
        print("      恢复 M4 (resume)...")
        resumed_m4 = resume(adapter, registry, handle, m4_srun_id, m4_token)
        if resumed_m4.get("status") != "succeeded":
            raise RuntimeError(f"M4 恢复失败: {resumed_m4}")

        print("[7/10] advance 推进 M5 (自动)...")
        item_m5 = advance(adapter, registry, handle)
        if (
            item_m5.get("action") != "executed"
            or item_m5.get("stage") != "m5"
            or item_m5.get("step_result", {}).get("status") != "succeeded"
        ):
            raise RuntimeError(f"M5 执行失败: {item_m5}")

        # 检查 M5 gate_results 披露项
        m5_srun_id = item_m5["step_run_id"]
        m5_gate_revs = service.list_step_run_revisions(
            m5_srun_id, artifact_type="gate_results"
        )
        m5_gate_doc = json.loads(
            adapter.read_object(
                service.get_revision(m5_gate_revs[0]["artifact_revision_id"])["sha256"]
            ).decode("utf-8")
        )
        m5_failures_count = len(m5_gate_doc.get("failures", []))
        # 披露项是 adapter_notes 扫描发现的逐条点名截断（warning）
        m5_disclosure_warnings = [
            w for w in m5_gate_doc.get("warnings", []) if w.get("check") == "adapter_notes_truncation"
        ]
        m5_disclosure_count = len(m5_disclosure_warnings)
        print(
            f"      M5 succeeded, 披露项统计: warnings={m5_disclosure_count}条, errors={m5_failures_count}条"
        )

        # 8. advance 至 M6 awaiting_human
        print("[8/10] advance 推进 M6...")
        item_m6 = advance(adapter, registry, handle)
        if (
            item_m6.get("action") != "executed"
            or item_m6.get("stage") != "m6"
            or item_m6.get("step_result", {}).get("status") != "awaiting_human"
        ):
            raise RuntimeError(f"M6 未停在 awaiting_human: {item_m6}")

        m6_srun_id = item_m6["step_run_id"]
        m6_token = item_m6["step_result"]["resume_token"]
        print(f"      M6 暂停在 awaiting_human, StepRun: {m6_srun_id}")

        # 9. 回放 M6 审核决定
        print("[9/10] 从参考副本回放 M6 审核决定...")
        supplement_decisions = None
        if supplement_file:
            print(f"      加载 M6 补充决定: {supplement_file}")
            supplement_decisions = load_m6_supplement_decisions(supplement_file)

        with LedgerReader(REF_LEDGER) as reader:
            old_m6_decisions = load_m6_decisions_from_ledger(reader)
            try:
                m6_applied = replay_m6_decisions(
                    service,
                    m6_srun_id,
                    m6_token,
                    old_decisions=old_m6_decisions,
                    supplement_decisions=supplement_decisions,
                )
            except ReplayMismatchError as err:
                print(f"\n[PAUSE] M6 审核队列发现未记录的项: {err}")
                print(f"       调度器已停在 M6 awaiting_human (StepRun: {m6_srun_id})，未代用户做决定。")
                print("       等待用户提供 U07 decisions_supplement.yaml 后再继续。")
                return {
                    "edition_run_id": edition_run_id,
                    "edition_part_id": edition_part_id,
                    "status": "awaiting_human",
                    "paused_stage": "m6",
                    "m6_step_run_id": m6_srun_id,
                    "reason": str(err),
                }

        print(f"      M6 回放完成: 成功登记 {len(m6_applied)} 条决定")

        # 记录 M6 对位表 (old_event_rev -> new_event_rev)
        new_m6_events = service.list_human_events(m6_srun_id)
        new_m6_by_key = {}
        for ev in new_m6_events:
            ev_doc = json.loads(
                adapter.read_object(
                    service.get_revision(ev["event_revision_id"])["sha256"]
                ).decode("utf-8")
            )
            tgt = ev_doc.get("target") or {}
            key = (tgt.get("entity_id"), tgt.get("entity_kind"), ev_doc.get("decision_type"))
            new_m6_by_key[key] = ev["event_revision_id"]

        m6_alignment_table = []
        all_m6_for_table = list(old_m6_decisions)
        if supplement_decisions:
            all_m6_for_table.extend(supplement_decisions)

        for old_d in all_m6_for_table:
            key = (old_d["target_entity_id"], old_d["entity_kind"], old_d["decision_type"])
            m6_alignment_table.append(
                {
                    "entity_id": old_d["target_entity_id"],
                    "entity_kind": old_d["entity_kind"],
                    "decision_type": old_d["decision_type"],
                    "old_event_revision_id": old_d.get("_event_revision_id"),
                    "new_event_revision_id": new_m6_by_key.get(key),
                    "verdict": old_d["verdict"],
                    "actor_ref": old_d.get("actor_ref"),
                }
            )

        # 恢复 M6 并收口
        print("      恢复 M6 (resume)...")
        resumed_m6 = resume(adapter, registry, handle, m6_srun_id, m6_token)
        if resumed_m6.get("status") != "succeeded":
            raise RuntimeError(f"M6 恢复失败: {resumed_m6}")

        print("      收口 EditionRun (advance)...")
        item_close = advance(adapter, registry, handle)
        if item_close.get("action") != "complete":
            raise RuntimeError(f"EditionRun 未完成收口: {item_close}")
        print("      EditionRun 收口完成 (complete)")

        # 10. 执行 run_release (M7 创世 + M8 编译)
        print("[10/10] 执行 run_release (M7 创世 + M8 编译)...")
        release_res = run_release(
            adapter,
            registry,
            handle,
        )
        if (
            release_res.get("action") != "executed"
            or release_res.get("stage") != "m8"
            or release_res.get("step_result", {}).get("status") != "succeeded"
        ):
            raise RuntimeError(f"run_release 失败: {release_res}")

        m8_srun_id = release_res["step_run_id"]
        # 获取 M8 StagePackage 与 PublicationPackage
        m8_pkg_revs = service.list_step_run_revisions(
            m8_srun_id, artifact_type="stage_package", status="sealed"
        )
        m8_pkg = json.loads(
            adapter.read_object(
                service.get_revision(m8_pkg_revs[0]["artifact_revision_id"])["sha256"]
            ).decode("utf-8")
        )
        payload = m8_pkg.get("payload", {})
        knowledge_chain = payload.get("knowledge_chain")
        pub_rev_id = payload.get("publication_package_revision_id")

        print(f"       run_release 成功! M8 StepRun: {m8_srun_id}")
        print(f"       PublicationPackage 修订号: {pub_rev_id}")
        print(f"       knowledge_chain: {knowledge_chain}")

        # 统计所有阶段 StepRun
        step_runs_report = {}
        for stage in ("m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8"):
            s_runs = []
            # 查本库全部 step_runs
            all_sruns = service.list_step_runs(edition_part_id, stage=stage)
            for sr in all_sruns:
                s_runs.append(
                    {
                        "step_run_id": sr["step_run_id"],
                        "stage": sr["stage"],
                        "status": sr["status"],
                    }
                )
            step_runs_report[stage] = s_runs

        return {
            "edition_run_id": edition_run_id,
            "edition_part_id": edition_part_id,
            "step_runs": step_runs_report,
            "m4_alignment": m4_alignment_table,
            "m6_alignment": m6_alignment_table,
            "m5_disclosure": {
                "warnings": m5_disclosure_count,
                "errors": m5_failures_count,
            },
            "publication_package_revision_id": pub_rev_id,
            "knowledge_chain": knowledge_chain,
            "m8_step_run_id": m8_srun_id,
        }

    finally:
        adapter.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="真书全线运行驱动")
    parser.add_argument(
        "--supplement",
        type=str,
        default=None,
        help="U07 M6 补充决定 YAML 文件路径",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="不清理目标账本目录",
    )
    args = parser.parse_args()

    try:
        report = run_full_pipeline(
            clean_target=not args.no_clean,
            supplement_file=args.supplement,
        )
        print("\n=== 执行报告 ===")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if report.get("status") == "awaiting_human":
            return 2  # 正常暂停在 awaiting_human
        return 0
    except Exception as exc:
        print(f"\n[ERROR] 执行失败: {type(exc).__name__}: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
