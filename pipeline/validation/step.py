"""M5 事务序列 ``run_m5``（规格 §13、§17、§17.1）。

顺序：resolve_m5_inputs → 配置 → begin_step_run → build_context → 14 个
Validator（fail-closed）→ gate_results → validation_package → 变换 → m5
StagePackage → finish_step_run。``begin_step_run`` 之后的任何异常一律转为
失败封存（检查名 ``internal``）；gate 未通过仍 ``succeeded`` 并照常封存
（D-08 A、§9 第 21 条）。
"""

import hashlib
import importlib
import json

from pipeline.ledger import ids

from . import CONSUMPTION_LEVELS, M5_TOOL, M5_TOOL_VERSION
from . import adapter_notes
from .context import build_context
from .findings import gate_summary, level_verdicts, make_report
from .inputs import resolve_m5_inputs
from .package import assemble_gate_results, assemble_validation_package
from .registry import VALIDATORS, _VALIDATOR_MODULES as _MODULE_OF
from .serialize import canonical_json

_VALIDATOR_IDS = [validator_id for validator_id, _gate, _func in VALIDATORS]


def _artifact_ref(service, revision_id):
    """构造过 ``artifact_ref.schema.json`` 的引用（stage_package 用包号身份）。"""
    info = service.describe_revision(revision_id)
    artifact_id, artifact_type = info["artifact_id"], info["artifact_type"]
    if artifact_type == "stage_package":
        return {
            "schema_version": "1.0.0",
            "artifact_kind": "stage_package",
            "stage_package_id": info["stage_package_id"],
            "artifact_revision_id": revision_id,
            "artifact_type": artifact_type,
        }
    return {
        "schema_version": "1.0.0",
        "artifact_kind": "artifact",
        "artifact_id": artifact_id,
        "artifact_revision_id": revision_id,
        "artifact_type": artifact_type,
    }


def run_m5(service, edition_part_id, *, target_consumption_level="INTERNAL_DEMO"):
    """在真实 Ledger 上执行 M5 校验的完整事务序列，返回 summary dict。"""
    inputs = resolve_m5_inputs(service, edition_part_id)
    processing_run_id = inputs["processing_run_id"]
    frozen_revision_ids = inputs["frozen_revision_ids"]

    config_data = canonical_json(
        {
            "stage": "m5",
            "tool": M5_TOOL,
            "tool_version": M5_TOOL_VERSION,
            "target_consumption_level": target_consumption_level,
        }
    )
    _, configuration_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        config_data,
        producer_module=M5_TOOL,
        producer_version=M5_TOOL_VERSION,
    )

    step_run_id = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": ids.new_id("step_run_id"),
            "input_artifact_ids": frozen_revision_ids,
            "technique_profile_id": inputs["technique_id"],
            "configuration_artifact_id": configuration_revision_id,
        }
    )

    try:
        return _run_after_begin(
            service,
            edition_part_id,
            inputs,
            step_run_id,
            processing_run_id,
            configuration_revision_id,
            frozen_revision_ids,
            target_consumption_level,
        )
    except Exception as exc:  # noqa: BLE001 —— begin 之后一律失败封存
        return _fail(service, step_run_id, "internal", "%s: %s" % (type(exc).__name__, exc))


def _run_after_begin(
    service,
    edition_part_id,
    inputs,
    step_run_id,
    processing_run_id,
    configuration_revision_id,
    frozen_revision_ids,
    target_consumption_level,
):
    ctx = build_context(
        service, inputs, target_consumption_level=target_consumption_level
    )

    findings = []
    reports = []
    report_revision_ids = []
    task_statuses = []
    checkpoint_revision_ids = []
    fail_closed = False

    for index, (validator_id, gate, func_name) in enumerate(VALIDATORS):
        if index > 0 and fail_closed:
            report = make_report(
                validator_id, gate, M5_TOOL_VERSION, "skipped_fail_closed", {}, []
            )
        else:
            try:
                module = importlib.import_module(_MODULE_OF[validator_id])
                result = getattr(module, func_name)(ctx)
                report = make_report(
                    validator_id, gate, M5_TOOL_VERSION, "succeeded",
                    result.get("checked", {}), result.get("findings", []),
                )
            except Exception as exc:  # noqa: BLE001 —— 单 task errored，不冒泡
                report = make_report(
                    validator_id, gate, M5_TOOL_VERSION, "errored", {}, []
                )
                report["detail"] = "%s: %s" % (type(exc).__name__, exc)

        _, report_revision_id = service.put_artifact(
            step_run_id, "validation_report", canonical_json(report),
            producer_module=M5_TOOL, producer_version=M5_TOOL_VERSION,
        )
        service.seal_revision(report_revision_id)
        report["report_revision_id"] = report_revision_id
        reports.append(report)
        report_revision_ids.append(report_revision_id)
        task_statuses.append(report["task_status"])
        findings.extend(report["findings"])

        if index == 0:
            fail_closed = report["task_status"] != "succeeded" or any(
                finding["severity"][level] == "error"
                for finding in report["findings"]
                for level in CONSUMPTION_LEVELS
            )

        status = "succeeded" if report["task_status"] == "succeeded" else "failed"
        pending_queue = [{"task_id": later} for later in _VALIDATOR_IDS[index + 1:]]
        checkpoint_revision_id = service.write_checkpoint(
            step_run_id,
            edition_part_id=edition_part_id,
            stage="m5",
            completed_tasks=[
                {
                    "task_id": validator_id,
                    "artifact_revision_id": report_revision_id,
                    "status": status,
                    "terminal_state": None,
                }
            ],
            human_decisions=[],
            pending_queue=pending_queue,
            next_pointer=pending_queue[0] if pending_queue else None,
        )
        checkpoint_revision_ids.append(checkpoint_revision_id)

    # 门禁级检查（W8 ACT 19 Q3，**不在** 14 项 Validator 套件内）：扫描 M4 提交件的
    # adapter_notes 截断自述。账本里没有 M4 提交件时（夹具与 OCR 档）产出恒为空，
    # 因而 validators/Checkpoint/冻结输入数不变、既有用例逐字节不受影响；确有提交件
    # 且命中时产出一条 error 发现，经 gate_summary 变成返工任务、gate.passed 转假。
    findings.extend(adapter_notes.scan(service, edition_part_id))

    verdicts = level_verdicts(findings, task_statuses)
    gate = gate_summary(target_consumption_level, findings, reports)

    gate_results_doc = assemble_gate_results(
        verdicts,
        findings,
        reports,
        target_consumption_level=target_consumption_level,
    )
    gate_results_bytes = canonical_json(gate_results_doc)
    _, gate_results_revision_id = service.put_artifact(
        step_run_id, "gate_results", gate_results_bytes,
        producer_module=M5_TOOL, producer_version=M5_TOOL_VERSION,
    )
    service.seal_revision(gate_results_revision_id)

    validation_package_doc = assemble_validation_package(
        gate_results_doc,
        inputs,
        gate,
        verdicts,
        target_consumption_level=target_consumption_level,
        gate_results_revision_id=gate_results_revision_id,
        edition_part_id=edition_part_id,
    )
    _, validation_package_revision_id = service.put_artifact(
        step_run_id, "validation_package", canonical_json(validation_package_doc),
        producer_module=M5_TOOL, producer_version=M5_TOOL_VERSION,
    )
    service.seal_revision(validation_package_revision_id)

    log_lines = [
        "resolve_m5_inputs frozen=%d" % len(frozen_revision_ids),
        "validators=%d findings=%d" % (len(reports), len(findings)),
        "gate.passed=%s" % gate["passed"],
    ]
    _, log_revision_id = service.put_artifact(
        step_run_id, "step_log", "\n".join(log_lines).encode("utf-8"),
        producer_module=M5_TOOL, producer_version=M5_TOOL_VERSION,
    )
    service.seal_revision(log_revision_id)

    transformation_id = service.record_transformation(
        step_run_id,
        operation="validate_corpus",
        tool=M5_TOOL,
        tool_version=M5_TOOL_VERSION,
        configuration_revision_id=configuration_revision_id,
        input_revision_ids=frozen_revision_ids,
        output_revision_ids=[gate_results_revision_id, validation_package_revision_id],
        validation_report_revision_id=report_revision_ids[0],
        human_event_revision_ids=[],
    )

    stage_package_id = ids.new_id("stage_package_id", stage="m5")
    package_revision_id = ids.new_id("artifact_revision_id")
    counts = gate_results_doc["counts"]
    package = {
        "schema_version": "1.0.0",
        "stage_package_id": stage_package_id,
        "artifact_revision_id": package_revision_id,
        "stage": "m5",
        "status": "sealed",
        "payload": {
            "validation_package_revision_id": validation_package_revision_id,
            "gate_results_revision_id": gate_results_revision_id,
            "scope": "corpus_only",
            "target_consumption_level": target_consumption_level,
            "gate": gate,
            "level_verdicts": verdicts,
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "input_artifacts": [
                _artifact_ref(service, revision_id)
                for revision_id in frozen_revision_ids
            ],
            "output_artifacts": [_artifact_ref(service, validation_package_revision_id)],
            "counts": {
                "validators": counts["validators"],
                "findings": counts["findings"],
                "failures": counts["failures"],
                "warnings": counts["warnings"],
                "rework_tasks": counts["rework_tasks"],
            },
            "content_sha256": hashlib.sha256(gate_results_bytes).hexdigest(),
        },
        "validation": {
            "passed": gate["passed"],
            "report_artifacts": [
                _artifact_ref(service, revision_id)
                for revision_id in report_revision_ids
            ],
        },
        "lineage": {
            "upstream_artifacts": [
                _artifact_ref(service, inputs["m3_package_revision_id"]),
                _artifact_ref(service, inputs["corpus_package_revision_id"]),
                _artifact_ref(service, inputs["corpus_spans_revision_id"]),
            ],
            "transformations": [
                {
                    "operation": "validate_corpus",
                    "step_run_id": step_run_id,
                    "configuration_artifact_revision_id": configuration_revision_id,
                    "input_artifact_revision_ids": frozen_revision_ids,
                    "output_artifact_revision_ids": [
                        gate_results_revision_id,
                        validation_package_revision_id,
                    ],
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

    current_version = service.get_step_run(step_run_id)["status_version"]
    step_manifest_revision_id = service.finish_step_run(
        step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "status_version": current_version + 1,
            "status": "succeeded",
            "output_artifact_ids": [
                gate_results_revision_id,
                validation_package_revision_id,
                package_revision_id,
            ],
            "validation_report_ids": report_revision_ids,
            "log_artifact_ids": [log_revision_id],
            "failure_artifact_ids": [],
        },
    )

    return {
        "status": "succeeded",
        "processing_run_id": processing_run_id,
        "step_run_id": step_run_id,
        "configuration_revision_id": configuration_revision_id,
        "frozen_input_revision_ids": frozen_revision_ids,
        "stage_package_id": stage_package_id,
        "package_revision_id": package_revision_id,
        "gate_results_revision_id": gate_results_revision_id,
        "validation_package_revision_id": validation_package_revision_id,
        "validator_report_revision_ids": report_revision_ids,
        "log_revision_id": log_revision_id,
        "step_manifest_revision_id": step_manifest_revision_id,
        "transformation_id": transformation_id,
        "checkpoint_revision_ids": checkpoint_revision_ids,
        "validator_reports": reports,
        "level_verdicts": verdicts,
        "gate": gate,
        "counts": {
            "validators": len(reports),
            "findings": len(findings),
            "failures": counts["failures"],
            "warnings": counts["warnings"],
            "rework_tasks": counts["rework_tasks"],
        },
    }


def _fail(service, step_run_id, check, detail):
    """失败封存：put failure_report → seal → fail_step_run。"""
    failure_data = json.dumps(
        {"check": check, "detail": detail}, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    _, failure_revision_id = service.put_artifact(
        step_run_id, "failure_report", failure_data,
        producer_module=M5_TOOL, producer_version=M5_TOOL_VERSION,
    )
    service.seal_revision(failure_revision_id)
    service.fail_step_run(step_run_id, [failure_revision_id], "M5 %s: %s" % (check, detail))
    return {
        "status": "failed",
        "step_run_id": step_run_id,
        "failed_check": check,
        "failure_revision_id": failure_revision_id,
        "reason": detail,
    }
