"""M2 事务层：Ledger 写路径（cleaned_text_revision + deterministic_patch_set + sanitization_report）。

根据规格 §17 实现 run_m2 纯事务函数，保证阶段原子性、不可变性与零写入安全。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pipeline.ledger import ids
from pipeline.ledger.service import LedgerService

from . import M2_TOOL, M2_TOOL_VERSION
from .cleaner import clean_text
from .errors import DigitizationRefused
from .gate import GateResult, evaluate_m2_gate
from .patcher import build_patches
from .reporter import build_sanitization_report

# failed_check 闭集
FAILED_CHECKS = ("input_contract", "m2_gate", "internal")


def _fail(
    service: LedgerService,
    step_run_id: str,
    failed_check: str,
    detail: str,
    gate_result: GateResult | None = None,
) -> dict[str, Any]:
    """begin 之后的失败封存。"""
    if failed_check not in FAILED_CHECKS:
        failed_check = "internal"
    reason = f"{failed_check}: {detail}"
    service.fail_step_run(step_run_id, [], reason)
    res: dict[str, Any] = {
        "error": reason,
        "step_run_id": step_run_id,
        "failed_check": failed_check,
    }
    if gate_result is not None:
        res["gate_result"] = gate_result
    return res


def _read_revision_bytes(service: LedgerService, revision_id: str) -> bytes:
    """从 Ledger 读取修订的对象字节。"""
    rev = service.store.get_revision(revision_id)
    if rev is None:
        raise DigitizationRefused(f"raw_text 修订不存在: {revision_id}", code="SCH_003")
    sha256 = rev.get("sha256")
    if not sha256:
        raise DigitizationRefused(f"raw_text 修订缺失 sha256: {revision_id}", code="SCH_003")
    data = service.objects.get(sha256)
    if data is None:
        raise DigitizationRefused(f"raw_text 对象数据缺失: {sha256}", code="SCH_003")
    return data


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
    raw_text_revision_id: str,
    outputs: list,
    report_bytes: bytes,
    validation_report_revision_id: str,
    log_revision_id: str,
    configuration_revision_id: str,
) -> str:
    """登记 M2 StagePackage（包内清单 = 本步实际写出的修订），返回包修订号。"""
    stage_package_id = ids.new_id("stage_package_id", stage="m2")
    package_revision_id = ids.new_id("artifact_revision_id")
    package = {
        "schema_version": "1.0.0",
        "stage_package_id": stage_package_id,
        "artifact_revision_id": package_revision_id,
        "stage": "m2",
        "status": "sealed",
        "payload": {
            "cleaned_text_revision_id": outputs[0],
            "deterministic_patch_set_revision_id": outputs[1],
            "sanitization_report_revision_id": outputs[2],
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "input_artifacts": [_artifact_ref(service, raw_text_revision_id)],
            "output_artifacts": [_artifact_ref(service, rev) for rev in outputs],
            "counts": {"cleaned_text": 1, "patch_set": 1, "sanitization_report": 1},
            "content_sha256": hashlib.sha256(report_bytes).hexdigest(),
        },
        "validation": {
            "passed": True,
            "report_artifacts": [
                _artifact_ref(service, validation_report_revision_id)
            ],
        },
        "lineage": {
            "upstream_artifacts": [_artifact_ref(service, raw_text_revision_id)],
            "transformations": [
                {
                    "operation": "sanitize_text",
                    "step_run_id": step_run_id,
                    "configuration_artifact_revision_id": configuration_revision_id,
                    "input_artifact_revision_ids": [raw_text_revision_id],
                    "output_artifact_revision_ids": list(outputs),
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


def run_m2(
    service: LedgerService,
    raw_text_revision_id: str,
    source_info: dict[str, Any],
    edition_part_id: str,
) -> dict[str, Any]:
    """在真实 Ledger 上执行 M2 电子文本清洗的完整事务序列（规格 §17）。

    事务序列：
    1. 检查同一 edition_part_id 不得已有 m2 Checkpoint，有则 DigitizationRefused
    2. 读取 raw_text 修订内容
    3. begin_step_run(service, stage="m2", task_id="sanitize_text")
    4. 执行 clean_text(raw_content) → CleanResult
    5. 执行 build_patches(raw_text, cleaned_text, findings) → patches
    6. 执行 build_sanitization_report(findings, patches) → report
    7. 执行 evaluate_m2_gate(report) → gate_result
    8. 如果 gate_result.passed == false：fail_step_run(service, failed_check="m2_gate")
    9. 如果有 deferred findings：await_human(service, ...) → 返回 awaiting_human
    10. put_artifact(service, artifact_type="cleaned_text_revision", ...)
    11. put_artifact(service, artifact_type="deterministic_patch_set", ...)
    12. put_artifact(service, artifact_type="sanitization_report", ...)
    13. record_transformation(service, task_id="sanitize_text", ...)
    14. seal_revision(service, cleaned_rev)
    15. finish_step_run(service)

    返回：
        成功：{"cleaned_revision_id": str, "patch_revision_id": str, "report_revision_id": str, "gate_result": GateResult, "step_run_id": str}
        失败封存：{"gate_result": GateResult, "step_run_id": str, "failed_check": str, "error": str}
    """
    # ---- 1. begin 前校验（零写入保证）----
    if not isinstance(source_info, dict):
        raise DigitizationRefused("source_info 必须是字典", code="SCH_001")

    ep = source_info.get("edition_part", {})
    if not isinstance(ep, dict) or ep.get("artifact_id") != edition_part_id:
        raise DigitizationRefused("edition_part_id 与 source_info 不匹配", code="SCH_002")

    # 检查同一 edition_part_id 不得已有 m2 Checkpoint
    checkpoints = service.list_checkpoints(edition_part_id, "m2")
    if checkpoints:
        raise DigitizationRefused("M2 已封存")

    # 读取 raw_text 修订内容
    try:
        raw_bytes = _read_revision_bytes(service, raw_text_revision_id)
    except DigitizationRefused:
        raise
    except Exception as exc:
        raise DigitizationRefused(f"无法读取 raw_text 修订: {exc}", code="SCH_003")

    raw_text_str = raw_bytes.decode("utf-8")

    # ---- 2. 创建或复用 ProcessingRun 并写入配置 ----
    technique_id = source_info.get("technique_id", "default_tech")
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
            "stage": "m2",
            "tool": M2_TOOL,
            "tool_version": M2_TOOL_VERSION,
            "task_id": "sanitize_text",
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    _, config_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        config_data,
        producer_module=M2_TOOL,
        producer_version=M2_TOOL_VERSION,
    )

    # ---- 3. begin_step_run ----
    step_run_id = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": ids.new_id("step_run_id"),
            "input_artifact_ids": [raw_text_revision_id],
            "technique_profile_id": technique_id,
            "configuration_artifact_id": config_revision_id,
        }
    )

    # ---- 4. begin 之后：任何异常转为失败封存 ----
    try:
        clean_result = clean_text(raw_text_str)
        patches = build_patches(
            raw_text_str, clean_result.cleaned_text, clean_result.findings
        )
        report = build_sanitization_report(clean_result.findings, patches)
        gate_result = evaluate_m2_gate(report)

        if not gate_result.passed:
            return _fail(
                service,
                step_run_id,
                failed_check="m2_gate",
                detail=str(gate_result.failed_checks),
                gate_result=gate_result,
            )

        # 保存清洗文本产物
        cleaned_bytes = clean_result.cleaned_text.encode("utf-8")
        _, cleaned_rev = service.put_artifact(
            step_run_id,
            "cleaned_text_revision",
            cleaned_bytes,
            producer_module=M2_TOOL,
            producer_version=M2_TOOL_VERSION,
        )
        service.seal_revision(cleaned_rev)

        # 保存 patch 集合产物（可序列化 dict 列表）
        patches_data = [
            {
                "patch_id": p.patch_id,
                "raw_start": p.raw_start,
                "raw_end": p.raw_end,
                "cleaned_start": p.cleaned_start,
                "cleaned_end": p.cleaned_end,
                "action": p.action,
                "basis": p.basis,
                "replacement": p.replacement,
            }
            for p in patches
        ]
        patches_bytes = json.dumps(
            patches_data, ensure_ascii=False, indent=2, sort_keys=True
        ).encode("utf-8")
        _, patch_rev = service.put_artifact(
            step_run_id,
            "deterministic_patch_set",
            patches_bytes,
            producer_module=M2_TOOL,
            producer_version=M2_TOOL_VERSION,
        )
        service.seal_revision(patch_rev)

        # 保存 sanitization 报告产物
        report_bytes = json.dumps(
            report, ensure_ascii=False, indent=2, sort_keys=True
        ).encode("utf-8")
        _, report_rev = service.put_artifact(
            step_run_id,
            "sanitization_report",
            report_bytes,
            producer_module=M2_TOOL,
            producer_version=M2_TOOL_VERSION,
        )
        service.seal_revision(report_rev)

        all_outputs = [cleaned_rev, patch_rev, report_rev]

        # 校验报告：只写 M2 实际做过的检查（清洗报告的结论 + m2 Gate 判定）。
        _, validation_report_revision_id = service.put_artifact(
            step_run_id,
            "validation_report",
            json.dumps(
                {
                    "stage": "m2",
                    "tool": M2_TOOL,
                    "tool_version": M2_TOOL_VERSION,
                    "passed": True,
                    "checks": {
                        "m2_gate": "sanitization_report 经 evaluate_m2_gate 判定通过（failed_checks=%s）"
                        % list(gate_result.failed_checks),
                        "deferred_count": "report.deferred_count=%s"
                        % report.get("deferred_count"),
                        "patch_count": "deterministic_patch_set 条数=%d" % len(patches),
                    },
                },
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8"),
            producer_module=M2_TOOL,
            producer_version=M2_TOOL_VERSION,
        )
        service.seal_revision(validation_report_revision_id)
        _, log_revision_id = service.put_artifact(
            step_run_id,
            "step_log",
            (
                "sanitize_text findings=%d patches=%d\n"
                % (len(clean_result.findings), len(patches))
            ).encode("utf-8"),
            producer_module=M2_TOOL,
            producer_version=M2_TOOL_VERSION,
        )
        service.seal_revision(log_revision_id)

        # 记录变换
        service.record_transformation(
            step_run_id,
            operation="sanitize_text",
            tool=M2_TOOL,
            tool_version=M2_TOOL_VERSION,
            configuration_revision_id=config_revision_id,
            input_revision_ids=[raw_text_revision_id],
            output_revision_ids=all_outputs,
            validation_report_revision_id=validation_report_revision_id,
        )

        # StagePackage（TODO T04A 裁决 1）：包内清单为本步实际写出的修订。
        package_revision_id = _register_stage_package(
            service,
            step_run_id=step_run_id,
            processing_run_id=processing_run_id,
            raw_text_revision_id=raw_text_revision_id,
            outputs=all_outputs,
            report_bytes=report_bytes,
            validation_report_revision_id=validation_report_revision_id,
            log_revision_id=log_revision_id,
            configuration_revision_id=config_revision_id,
        )

        # 写入 checkpoint
        service.write_checkpoint(
            step_run_id,
            edition_part_id=edition_part_id,
            stage="m2",
            completed_tasks=[
                {
                    "task_id": "sanitize_text",
                    "artifact_revision_id": cleaned_rev,
                    "status": "succeeded",
                    "terminal_state": None,
                }
            ],
            human_decisions=[],
            pending_queue=[],
            next_pointer=None,
        )

        # 完成 step_run
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
            "cleaned_revision_id": cleaned_rev,
            "patch_revision_id": patch_rev,
            "report_revision_id": report_rev,
            "gate_result": gate_result,
            "step_run_id": step_run_id,
            "stage_package_revision_id": package_revision_id,
        }
    except Exception as exc:
        failed_check = (
            "input_contract"
            if isinstance(exc, (DigitizationRefused, ValueError))
            else "internal"
        )
        return _fail(service, step_run_id, failed_check, str(exc))
