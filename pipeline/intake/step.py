"""M1 事务层：Ledger 写路径（source_manifest + raw_text 冻结，规格 §17）。

实现 run_m1 纯事务函数，保证阶段原子性与零写入安全。
"""

import json

from pipeline.ledger import ids
from pipeline.ledger.service import LedgerService

from . import M1_TOOL, M1_TOOL_VERSION, MANIFEST_TASK_ID
from .errors import IntakeRefused, SourceAssetMissing
from .manifest import manifest_bytes
from .source import load_source

# failed_check 闭集
FAILED_CHECKS = ("input_contract", "internal")


def _fail(service: LedgerService, step_run_id: str, failed_check: str, detail: str) -> dict:
    """begin 之后的失败封存。"""
    if failed_check not in FAILED_CHECKS:
        failed_check = "internal"
    reason = f"{failed_check}: {detail}"
    service.fail_step_run(step_run_id, [], reason)
    return {
        "error": reason,
        "step_run_id": step_run_id,
        "failed_check": failed_check,
    }


def run_m1(service: LedgerService, source_info: dict, files: list[dict], edition_part_id: str) -> dict:
    """在真实 Ledger 上执行 M1 入库的完整事务序列（规格 §17）。

    参数：
        service：LedgerService 直连服务实例。
        source_info：来源元数据申报字典。
        files：读取到的文件对象列表 [{"page", "path_ref", "data", "sha256", "size"}]。
        edition_part_id：版本部件 artifact_id。

    返回：
        成功时返回 {"manifest_revision_id": str, "raw_text_revision_ids": list[str], "step_run_id": str}。
        失败时封存并返回 {"error": str}。
    """
    # ---- 1. begin 前校验（零写入保证）----
    # 校验来源申报信息
    valid_source = load_source(source_info)

    # 校验 edition_part_id 一致性
    if valid_source["edition_part"]["artifact_id"] != edition_part_id:
        raise IntakeRefused("edition_part_id 与 source_info 不匹配", code="SCH_002")

    # 检查同一 edition_part_id 不得已有 m1 Checkpoint
    checkpoints = service.list_checkpoints(edition_part_id, "m1")
    if checkpoints:
        raise IntakeRefused("M1 已封存")

    if not files:
        raise IntakeRefused("files 列表不能为空", code="SCH_001")

    # ---- 2. 创建或复用 ProcessingRun 并写入配置 ----
    technique_id = valid_source["technique_id"]
    processing_run_id = service.latest_processing_run(edition_part_id, "edition_run")
    if processing_run_id is None:
        processing_run_id = service.create_processing_run(
            "edition_run", edition_part_id, technique_id
        )

    config_data = json.dumps(
        {
            "stage": "m1",
            "tool": M1_TOOL,
            "tool_version": M1_TOOL_VERSION,
            "task_id": MANIFEST_TASK_ID,
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    _, config_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        config_data,
        producer_module=M1_TOOL,
        producer_version=M1_TOOL_VERSION,
    )

    # ---- 3. begin_step_run ----
    step_run_id = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": ids.new_id("step_run_id"),
            "input_artifact_ids": [],
            "technique_profile_id": technique_id,
            "configuration_artifact_id": config_revision_id,
        }
    )

    # ---- 4. begin 之后：任何异常转为失败封存 ----
    try:
        raw_text_revision_ids = []
        for f in files:
            _, raw_rev_id = service.put_artifact(
                step_run_id,
                "raw_text",
                f["data"],
                producer_module=M1_TOOL,
                producer_version=M1_TOOL_VERSION,
            )
            service.seal_revision(raw_rev_id)
            raw_text_revision_ids.append(raw_rev_id)

        m_bytes = manifest_bytes(valid_source, files)
        _, manifest_revision_id = service.put_artifact(
            step_run_id,
            "source_manifest",
            m_bytes,
            producer_module=M1_TOOL,
            producer_version=M1_TOOL_VERSION,
        )
        service.seal_revision(manifest_revision_id)

        all_outputs = [manifest_revision_id] + raw_text_revision_ids
        service.record_transformation(
            step_run_id,
            operation=MANIFEST_TASK_ID,
            tool=M1_TOOL,
            tool_version=M1_TOOL_VERSION,
            configuration_revision_id=config_revision_id,
            input_revision_ids=[],
            output_revision_ids=all_outputs,
        )

        service.write_checkpoint(
            step_run_id,
            edition_part_id=edition_part_id,
            stage="m1",
            completed_tasks=[
                {
                    "task_id": MANIFEST_TASK_ID,
                    "artifact_revision_id": manifest_revision_id,
                    "status": "succeeded",
                    "terminal_state": None,
                }
            ],
            human_decisions=[],
            pending_queue=[],
            next_pointer=None,
        )

        current_version = service.get_step_run(step_run_id)["status_version"]
        service.finish_step_run(
            step_run_id,
            {
                "schema_version": "1.0.0",
                "processing_run_id": processing_run_id,
                "step_run_id": step_run_id,
                "status_version": current_version + 1,
                "status": "succeeded",
                "output_artifact_ids": all_outputs,
                "validation_report_ids": [],
                "log_artifact_ids": [],
                "failure_artifact_ids": [],
            },
        )

        return {
            "manifest_revision_id": manifest_revision_id,
            "raw_text_revision_ids": raw_text_revision_ids,
            "step_run_id": step_run_id,
        }
    except Exception as exc:
        failed_check = "input_contract" if isinstance(exc, (IntakeRefused, ValueError)) else "internal"
        return _fail(service, step_run_id, failed_check, str(exc))
