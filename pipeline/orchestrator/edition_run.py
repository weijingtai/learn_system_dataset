"""EditionRun：阶段推进、首切片 release 段与合取状态（规格 §6.1/§7/§17）。

``advance`` 从 Ledger 事实推导下一步，除 ``executed`` 外一律零写入；首纵切 Stage
Gate 报告**不落盘**（G7-RULINGS 第 46 条），由返回值 ``gate_reports`` 携带。
"""

import json
from pathlib import Path

import jsonschema
from referencing import Registry as _SchemaRegistry, Resource
from referencing.jsonschema import DRAFT202012

from pipeline.contract_registry.ports import PortGuard
from pipeline.ledger import ids
from pipeline.ledger.errors import SchemaViolation

from . import EDITION_STAGES
from .errors import OrchestratorRefused
from .gate import effective_step_runs, evaluate_stage_gate
from .module import StepContext, bind_module, descriptor_needs_run_inputs
from .run_inputs import persist_run_inputs, validate_run_inputs
from .runner import execute_step, run_legacy

# advance 的动作闭集
ADVANCE_ACTIONS = ("executed", "waiting", "blocked", "refused", "complete")

# 需要等待（不推进）的 StepRun 状态
WAITING_STATUSES = ("running", "awaiting_human", "suspended")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMAS_DIR = _REPO_ROOT / "openspec" / "schemas"
_STEP_REQUEST_VALIDATOR = None


def _step_request_validator():
    global _STEP_REQUEST_VALIDATOR
    if _STEP_REQUEST_VALIDATOR is None:
        schema = json.loads(
            (_SCHEMAS_DIR / "step_request.schema.json").read_text(encoding="utf-8")
        )
        artifact_ref = json.loads(
            (_SCHEMAS_DIR / "artifact_ref.schema.json").read_text(encoding="utf-8")
        )
        referring = _SchemaRegistry().with_resource(
            "artifact_ref.schema.json",
            Resource.from_contents(artifact_ref, default_specification=DRAFT202012),
        )
        _STEP_REQUEST_VALIDATOR = jsonschema.Draft202012Validator(
            schema, registry=referring
        )
    return _STEP_REQUEST_VALIDATOR


def _validate_step_request(request):
    errors = sorted(
        _step_request_validator().iter_errors(request), key=lambda item: list(item.path)
    )
    if errors:
        raise SchemaViolation(
            "StepRequest 校验失败: %s" % errors[0].message, code="SCH_001"
        )
    return request


def _result_dict(
    action,
    *,
    stage=None,
    step_run_id=None,
    step_result=None,
    gate=None,
    gate_reports=None,
    reason=None,
):
    return {
        "action": action,
        "stage": stage,
        "step_run_id": step_run_id,
        "step_result": step_result,
        "gate": gate,
        "gate_reports": gate_reports or {},
        "reason": reason,
    }


def _handle(processing_run_id, edition_part_id, technique_id, run_inputs=None):
    return {
        "processing_run_id": processing_run_id,
        "edition_part_id": edition_part_id,
        "technique_id": technique_id,
        "run_inputs": run_inputs,
    }


def start_edition_run(port, *, edition_part_id, technique_id, run_inputs=None):
    """新建一个 ``edition_run`` 并返回句柄。

    ``run_inputs`` 给出时按运行输入校验（必须显式 ``route: text``，裁决 2）并落成运行级
    ``configuration`` 修订；不给时不在启动阶段追问（桩/测试宿主不需要路线），由需要运行
    输入的 stage 在执行前拒收。
    """
    if run_inputs is not None:
        validate_run_inputs(run_inputs)
    processing_run_id = port.create_processing_run(
        "edition_run", edition_part_id, technique_id
    )
    if run_inputs is not None:
        persist_run_inputs(port, processing_run_id, run_inputs)
    return _handle(processing_run_id, edition_part_id, technique_id, run_inputs)


def adopt_edition_run(
    port, *, processing_run_id, edition_part_id, technique_id, run_inputs=None
):
    """接管既有 ``edition_run``：交叉校验技法与 Checkpoint 归属，不符即拒绝（零写入）。"""
    if run_inputs is not None:
        validate_run_inputs(run_inputs)
    status = port.run_status(processing_run_id)
    step_runs = status["step_runs"]
    own_ids = {step["step_run_id"] for step in step_runs}
    for step in step_runs:
        request = json.loads(step["request_json"]) if step.get("request_json") else {}
        if request.get("technique_profile_id") != technique_id:
            raise OrchestratorRefused(
                "StepRun %s 的 technique_profile_id 与 handle 不一致"
                % step["step_run_id"]
            )
    for stage in EDITION_STAGES:
        checkpoint = port.latest_checkpoint(edition_part_id, stage)
        if checkpoint is None:
            continue
        if checkpoint["step_run_id"] not in own_ids:
            raise OrchestratorRefused(
                "阶段 %s 的最新 Checkpoint 不属于本运行" % stage
            )
    return _handle(processing_run_id, edition_part_id, technique_id, run_inputs)


def _prior_stages(stages, stage):
    index = stages.index(stage)
    return list(stages[:index])


def _execute_step_request(port, binding, descriptor, handle, stages, stage, gate, gate_reports):
    upstream = {}
    for prior in _prior_stages(stages, stage):
        upstream[prior] = [
            row
            for row in effective_step_runs(port, handle, prior)
            if row.get("status") == "succeeded"
        ]
    planned = binding.target.plan(
        PortGuard(port),
        edition_part_id=handle["edition_part_id"],
        processing_run_id=handle["processing_run_id"],
        technique_id=handle["technique_id"],
        upstream=upstream,
    )
    configuration = planned.get("configuration") if isinstance(planned, dict) else None
    input_ids = list(planned.get("input_artifact_ids") or []) if isinstance(planned, dict) else []

    if (
        not isinstance(configuration, dict)
        or configuration.get("stage") != descriptor.get("stage")
        or configuration.get("module_id") != descriptor.get("module_id")
    ):
        return _result_dict(
            "refused",
            stage=stage,
            gate=gate,
            gate_reports=gate_reports,
            reason="plan 的 configuration 与登记不符",
        )
    for revision_id in input_ids:
        row = port.get_revision(revision_id)
        if row is None or row.get("status") != "sealed":
            return _result_dict(
                "refused",
                stage=stage,
                gate=gate,
                gate_reports=gate_reports,
                reason="plan 的输入修订未封存: %s" % revision_id,
            )

    data = json.dumps(configuration, sort_keys=True, ensure_ascii=False).encode("utf-8")
    config_revision_id = port.put_run_artifact(
        handle["processing_run_id"],
        "configuration",
        data,
        producer_module=descriptor.get("module_id"),
        producer_version=descriptor.get("version"),
    )[1]
    request = {
        "schema_version": "1.0.0",
        "processing_run_id": handle["processing_run_id"],
        "step_run_id": ids.new_id("step_run_id"),
        "input_artifact_ids": input_ids,
        "technique_profile_id": handle["technique_id"],
        "configuration_artifact_id": config_revision_id,
    }
    _validate_step_request(request)
    port.begin_step_run(request)
    context = StepContext(
        mode="fresh",
        edition_part_id=handle["edition_part_id"],
        stage=stage,
        module_id=descriptor.get("module_id"),
    )
    step_result = execute_step(port, binding, request, context)
    return _result_dict(
        "executed",
        stage=stage,
        step_run_id=request["step_run_id"],
        step_result=step_result,
        gate=gate,
        gate_reports=gate_reports,
    )


def advance(port, registry, handle, *, modules=None, stages=EDITION_STAGES):
    """推进一个 EditionRun 一步；除 ``executed`` 外一律零写入。"""
    gate_reports = {}
    for stage in stages:
        gate = evaluate_stage_gate(port, registry, handle, stage)
        gate_reports[stage] = gate
        if gate["gate"] == "passed":
            continue
        effective = effective_step_runs(port, handle, stage)
        waiting = [
            row for row in effective if row.get("status") in WAITING_STATUSES
        ]
        if waiting:
            return _result_dict(
                "waiting",
                stage=stage,
                step_run_id=waiting[0]["step_run_id"],
                gate=gate,
                gate_reports=gate_reports,
            )
        if any(row.get("status") == "failed" for row in effective):
            return _result_dict(
                "blocked",
                stage=stage,
                gate=gate,
                gate_reports=gate_reports,
                reason="存在失败未重跑的 StepRun",
            )
        if effective:
            failed_check = next(
                (
                    name
                    for name in gate["checks"]
                    if not gate["checks"][name]["ok"]
                ),
                None,
            )
            return _result_dict(
                "blocked",
                stage=stage,
                gate=gate,
                gate_reports=gate_reports,
                reason=failed_check,
            )
        descriptor = registry.module_for(stage)
        if descriptor is None:
            return _result_dict(
                "refused",
                stage=stage,
                gate=gate,
                gate_reports=gate_reports,
                reason="阶段 %s 未登记 Module（%s）"
                % (stage, registry.stage_rows.get(stage, stage)),
            )
        if descriptor_needs_run_inputs(descriptor):
            try:
                validate_run_inputs(handle.get("run_inputs"))
            except OrchestratorRefused as exc:
                return _result_dict(
                    "refused",
                    stage=stage,
                    gate=gate,
                    gate_reports=gate_reports,
                    reason=str(exc),
                )
        binding = bind_module(descriptor, modules=modules)
        if not binding.executable:
            return _result_dict(
                "refused",
                stage=stage,
                gate=gate,
                gate_reports=gate_reports,
                reason="阶段 %s 的绑定为 imported，无任务可执行" % stage,
            )
        if binding.binding == "legacy_self_driving":
            out = run_legacy(port, binding, handle)
            return _result_dict(
                "executed",
                stage=stage,
                step_run_id=out["step_run_id"],
                step_result=out["step_result"],
                gate=gate,
                gate_reports=gate_reports,
            )
        return _execute_step_request(
            port, binding, descriptor, handle, stages, stage, gate, gate_reports
        )
    return _result_dict("complete", gate_reports=gate_reports)


def run_release(port, registry, *, edition_part_id, technique_id, modules=None):
    """release 段：按 ``RELEASE_STAGES``（m7→m8）逐段执行 legacy 步（§6.2 ReleaseRun 状态机 DEFERRED）。

    每段入口自建 ProcessingRun（``owns_processing_run``），Gate 按该段自己的运行判定；
    某段未 ``succeeded``（失败，或 M7 停在人工裁决 ``awaiting_human``）即停在该段返回，
    不推进下一段。返回最后执行的那一段；``gate_reports`` 带已执行各段的 Gate。
    """
    # 局部导入：本次改动只落在 release 段（并行改动 advance/run_until 的执行者不受影响）
    from . import RELEASE_STAGES

    gate_reports = {}
    item = None
    for stage in RELEASE_STAGES:
        descriptor = registry.module_for(stage)
        if descriptor is None:
            return _result_dict(
                "refused",
                stage=stage,
                gate_reports=gate_reports,
                reason="阶段 %s 未登记 Module（%s）"
                % (stage, registry.stage_rows.get(stage, stage)),
            )
        binding = bind_module(descriptor, modules=modules)
        if binding.binding != "legacy_self_driving":
            return _result_dict(
                "refused",
                stage=stage,
                gate_reports=gate_reports,
                reason="release 段只支持 legacy_self_driving 绑定",
            )
        out = run_legacy(
            port,
            binding,
            {"edition_part_id": edition_part_id, "processing_run_id": None, "technique_id": technique_id},
        )
        handle = _handle(out["processing_run_id"], edition_part_id, technique_id)
        gate = evaluate_stage_gate(port, registry, handle, stage)
        gate_reports[stage] = gate
        item = {
            "action": "executed",
            "stage": stage,
            "step_run_id": out["step_run_id"],
            "processing_run_id": out["processing_run_id"],
            "step_result": out["step_result"],
            "gate": gate,
            "gate_reports": dict(gate_reports),
            "reason": None,
        }
        if out["step_result"].get("status") != "succeeded":
            break
    return item


def run_until(
    port,
    registry,
    handle,
    stage,
    *,
    modules=None,
    stages=EDITION_STAGES,
    max_steps=16,
):
    """反复 ``advance`` 直到目标 stage 的 Gate 通过或无法继续。"""
    results = []
    for _ in range(max_steps):
        item = advance(port, registry, handle, modules=modules, stages=stages)
        results.append(item)
        if item["action"] != "executed":
            break
        if (item.get("step_result") or {}).get("status") != "succeeded":
            break
        target_gate = item.get("gate_reports", {}).get(stage)
        if target_gate is not None and target_gate.get("gate") == "passed":
            break
    else:
        raise OrchestratorRefused("run_until 超过 max_steps=%d" % max_steps)
    return results


def edition_status(port, registry, handles):
    """Edition 合取状态：每个 Part 的 EDITION_STAGES 六个 Gate 全过才算 complete。"""
    handles = list(handles)
    deferred = [
        stage for stage in EDITION_STAGES if registry.module_for(stage) is None
    ]
    parts = {}
    for handle in handles:
        complete = all(
            evaluate_stage_gate(port, registry, handle, stage)["gate"] == "passed"
            for stage in EDITION_STAGES
        )
        parts[handle["edition_part_id"]] = "complete" if complete else "incomplete"
    return {
        "complete": bool(handles) and all(value == "complete" for value in parts.values()),
        "parts": parts,
        "deferred_stages": deferred,
    }
