"""M1 事务层：Ledger 写路径（source_manifest + raw_text 冻结，规格 §17）。

实现 run_m1 纯事务函数，保证阶段原子性与零写入安全。
"""

import hashlib
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


def _artifact_ref(service: LedgerService, revision_id: str) -> dict:
    """按修订元数据构造 ArtifactRef（§3 形状）。"""
    info = service.describe_revision(revision_id)
    return {
        "schema_version": "1.0.0",
        "artifact_kind": "artifact",
        "artifact_id": info["artifact_id"],
        "artifact_revision_id": revision_id,
        "artifact_type": info["artifact_type"],
    }


def _register_stage_package(
    service: LedgerService,
    *,
    step_run_id: str,
    processing_run_id: str,
    manifest_revision_id: str,
    raw_text_revision_ids: list,
    manifest_bytes: bytes,
    validation_report_revision_id: str,
    log_revision_id: str,
    configuration_revision_id: str,
) -> str:
    """登记 M1 StagePackage（包内清单 = 本步实际写出的修订），返回包修订号。"""
    outputs = [manifest_revision_id] + list(raw_text_revision_ids)
    stage_package_id = ids.new_id("stage_package_id", stage="m1")
    package_revision_id = ids.new_id("artifact_revision_id")
    package = {
        "schema_version": "1.0.0",
        "stage_package_id": stage_package_id,
        "artifact_revision_id": package_revision_id,
        "stage": "m1",
        "status": "sealed",
        "payload": {
            "manifest_revision_id": manifest_revision_id,
            "raw_text_revision_ids": list(raw_text_revision_ids),
            "page_count": len(raw_text_revision_ids),
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "input_artifacts": [],
            "output_artifacts": [_artifact_ref(service, rev) for rev in outputs],
            "counts": {"manifest": 1, "raw_text": len(raw_text_revision_ids)},
            "content_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        },
        "validation": {
            "passed": True,
            "report_artifacts": [
                _artifact_ref(service, validation_report_revision_id)
            ],
        },
        "lineage": {
            "upstream_artifacts": [],
            "transformations": [
                {
                    "operation": MANIFEST_TASK_ID,
                    "step_run_id": step_run_id,
                    "configuration_artifact_revision_id": configuration_revision_id,
                    "input_artifact_revision_ids": [],
                    "output_artifact_revision_ids": outputs,
                }
            ],
        },
        "logs": [_artifact_ref(service, log_revision_id)],
        "failures": [],
    }
    service.register_stage_package(
        step_run_id,
        package,
        json.dumps(package, sort_keys=True, ensure_ascii=False).encode("utf-8"),
        stage_package_id=stage_package_id,
        artifact_revision_id=package_revision_id,
    )
    service.seal_revision(package_revision_id)
    return package_revision_id


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
    row = service.store.conn.execute(
        "SELECT processing_run_id FROM processing_runs WHERE edition_part_id=? AND kind='edition_run' ORDER BY created_at DESC LIMIT 1",
        (edition_part_id,),
    ).fetchone()
    if row is not None:
        processing_run_id = row[0]
    else:
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

        # 校验报告：只写 M1 实际做过的检查（来源申报校验、edition_part 一致性、逐文件哈希）。
        _, validation_report_revision_id = service.put_artifact(
            step_run_id,
            "validation_report",
            json.dumps(
                {
                    "stage": "m1",
                    "tool": M1_TOOL,
                    "tool_version": M1_TOOL_VERSION,
                    "passed": True,
                    "checks": {
                        "source_declaration": "申报件键集与字段格式经 load_source 校验通过",
                        "edition_part_identity": "source_info.edition_part.artifact_id 与入参一致",
                        "file_hashes": "%d 个文件的 sha256 随文件记录登记" % len(files),
                        "manifest_serialization": "source_manifest 已确定性序列化并由本 StepRun 封存",
                    },
                },
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8"),
            producer_module=M1_TOOL,
            producer_version=M1_TOOL_VERSION,
        )
        service.seal_revision(validation_report_revision_id)
        _, log_revision_id = service.put_artifact(
            step_run_id,
            "step_log",
            (
                "ingest_source pages=%d raw_text=%d\n"
                % (len(files), len(raw_text_revision_ids))
            ).encode("utf-8"),
            producer_module=M1_TOOL,
            producer_version=M1_TOOL_VERSION,
        )
        service.seal_revision(log_revision_id)

        all_outputs = [manifest_revision_id] + raw_text_revision_ids
        service.record_transformation(
            step_run_id,
            operation=MANIFEST_TASK_ID,
            tool=M1_TOOL,
            tool_version=M1_TOOL_VERSION,
            configuration_revision_id=config_revision_id,
            input_revision_ids=[],
            output_revision_ids=all_outputs,
            validation_report_revision_id=validation_report_revision_id,
        )

        # StagePackage（TODO T04A 裁决 1）：包内清单为本步实际写出的修订。
        package_revision_id = _register_stage_package(
            service,
            step_run_id=step_run_id,
            processing_run_id=processing_run_id,
            manifest_revision_id=manifest_revision_id,
            raw_text_revision_ids=raw_text_revision_ids,
            manifest_bytes=m_bytes,
            validation_report_revision_id=validation_report_revision_id,
            log_revision_id=log_revision_id,
            configuration_revision_id=config_revision_id,
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
                "output_artifact_ids": all_outputs + [package_revision_id],
                "validation_report_ids": [validation_report_revision_id],
                "log_artifact_ids": [log_revision_id],
                "failure_artifact_ids": [],
            },
        )

        return {
            "manifest_revision_id": manifest_revision_id,
            "raw_text_revision_ids": raw_text_revision_ids,
            "step_run_id": step_run_id,
            "stage_package_revision_id": package_revision_id,
        }
    except Exception as exc:
        failed_check = "input_contract" if isinstance(exc, (IntakeRefused, ValueError)) else "internal"
        return _fail(service, step_run_id, failed_check, str(exc))
