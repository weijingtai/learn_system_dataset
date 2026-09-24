"""StepRun 执行器：``execute(StepRequest) → StepResult``（规格 §7）与 legacy 绑定适配。

StepRun 的终态迁移集中在本模块：Module 只返回 ``StepOutcome``，由
``finalize_outcome`` 转 L0 StepResult 并调用 Ledger 的 ``finish_step_run`` /
``fail_step_run`` / ``await_human``；异常或违约 outcome 封存 ``failure_report``。
"""

import json
from pathlib import Path

import jsonschema
from referencing import Registry as _SchemaRegistry, Resource
from referencing.jsonschema import DRAFT202012

from pipeline.contract_registry.ports import PortGuard
from pipeline.ledger.errors import LedgerError, SchemaViolation

from . import ORCH_TOOL, ORCH_TOOL_VERSION
from .errors import OrchestratorRefused
from .module import OUTCOME_LIST_KEYS, validate_outcome

# 编排层就地失败的检查名
FAILURE_CHECKS = ("module_exception", "outcome_contract")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMAS_DIR = _REPO_ROOT / "openspec" / "schemas"
_STEP_RESULT_VALIDATOR = None


def _step_result_validator():
    global _STEP_RESULT_VALIDATOR
    if _STEP_RESULT_VALIDATOR is None:
        schema = json.loads(
            (_SCHEMAS_DIR / "step_result.schema.json").read_text(encoding="utf-8")
        )
        artifact_ref = json.loads(
            (_SCHEMAS_DIR / "artifact_ref.schema.json").read_text(encoding="utf-8")
        )
        referring = _SchemaRegistry().with_resource(
            "artifact_ref.schema.json",
            Resource.from_contents(artifact_ref, default_specification=DRAFT202012),
        )
        _STEP_RESULT_VALIDATOR = jsonschema.Draft202012Validator(
            schema, registry=referring
        )
    return _STEP_RESULT_VALIDATOR


def _validate_step_result(result):
    errors = sorted(
        _step_result_validator().iter_errors(result), key=lambda item: list(item.path)
    )
    if errors:
        raise SchemaViolation(
            "StepResult 校验失败: %s" % errors[0].message, code="SCH_001"
        )
    return result


def _base_result(request, outcome):
    result = {
        "schema_version": "1.0.0",
        "processing_run_id": request["processing_run_id"],
        "step_run_id": request["step_run_id"],
    }
    for key in OUTCOME_LIST_KEYS:
        result[key] = list(outcome.get(key) or [])
    return result


def _seal_failure(port, request, check, detail):
    """封存 ``failure_report`` 并把 StepRun 置为 failed，返回失败 StepResult。"""
    step_run_id = request["step_run_id"]
    payload = json.dumps(
        {"check": check, "detail": detail}, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    _artifact_id, revision_id = port.put_artifact(
        step_run_id,
        "failure_report",
        payload,
        producer_module=ORCH_TOOL,
        producer_version=ORCH_TOOL_VERSION,
    )
    port.seal_revision(revision_id)
    port.fail_step_run(step_run_id, [revision_id], "orchestrator %s: %s" % (check, detail))
    result = {
        "schema_version": "1.0.0",
        "processing_run_id": request["processing_run_id"],
        "step_run_id": step_run_id,
        "status": "failed",
        "status_version": port.get_step_run(step_run_id)["status_version"],
        "output_artifact_ids": [],
        "validation_report_ids": [],
        "log_artifact_ids": [],
        "failure_artifact_ids": [revision_id],
    }
    return _validate_step_result(result)


def finalize_outcome(port, request, outcome):
    """把合法 ``StepOutcome`` 转成过 Schema 的 StepResult 并迁移 StepRun 终态。"""
    step_run_id = request["step_run_id"]
    status = outcome["status"]

    if status == "succeeded":
        result = _base_result(request, outcome)
        result["status"] = "succeeded"
        result["status_version"] = (
            port.get_step_run(step_run_id)["status_version"] + 1
        )
        _validate_step_result(result)
        try:
            port.finish_step_run(step_run_id, result)
        except LedgerError as exc:
            return _seal_failure(
                port,
                request,
                "outcome_contract",
                "%s: %s" % (type(exc).__name__, exc),
            )
        return result

    if status == "failed":
        port.fail_step_run(
            step_run_id, list(outcome.get("failure_artifact_ids") or []), "module failed"
        )
        result = _base_result(request, outcome)
        result["status"] = "failed"
        result["status_version"] = port.get_step_run(step_run_id)["status_version"]
        return _validate_step_result(result)

    token = port.await_human(step_run_id, list(outcome["pending_queue_artifact_ids"]))
    result = _base_result(request, outcome)
    result["status"] = "awaiting_human"
    result["status_version"] = port.get_step_run(step_run_id)["status_version"]
    result["resume_token"] = token
    result["pending_queue_artifact_ids"] = list(outcome["pending_queue_artifact_ids"])
    return _validate_step_result(result)


def execute_step(port, binding, request, context):
    """执行一步：调 Module，捕获异常与违约 outcome，最终返回 StepResult。"""
    try:
        outcome = binding.target.execute(PortGuard(port), request, context)
    except Exception as exc:  # noqa: BLE001 - 统一转为失败封存
        return _seal_failure(
            port, request, "module_exception", "%s: %s" % (type(exc).__name__, exc)
        )
    problems = validate_outcome(outcome)
    if problems:
        return _seal_failure(port, request, "outcome_contract", "; ".join(problems))
    return finalize_outcome(port, request, outcome)


# 入口需要运行输入时由描述符声明（TODO T04A 裁决 2/3）
RUN_INPUTS_KEY = "receives_run_inputs"


def _awaiting_pending_queue(port, step_run_id):
    """最近一次 ``await_human`` 事件里的待处理队列修订号。"""
    for event in reversed(port.list_step_run_events(step_run_id)):
        if event.get("event_type") == "await_human":
            payload = json.loads(event.get("payload_json") or "{}")
            return list(payload.get("pending_queue") or [])
    return []


def legacy_step_result(port, step, *, resume_token=None):
    """从 Ledger 事实重建 legacy StepRun 的 StepResult（succeeded/failed/awaiting_human）。

    ``resume_token`` 只可能是入口当次返回的明文；本函数不写任何地方（裁决 3 硬约束）。
    """
    step_run_id = step["step_run_id"]
    status = step["status"]
    if status == "succeeded":
        result = json.loads(step["result_json"])
    elif status == "failed":
        failure_ids = []
        for event in port.list_step_run_events(step_run_id):
            if event.get("event_type") == "failure":
                payload = json.loads(event.get("payload_json") or "{}")
                failure_ids = list(payload.get("failure_revision_ids") or [])
        result = {
            "schema_version": "1.0.0",
            "processing_run_id": step["processing_run_id"],
            "step_run_id": step_run_id,
            "status": "failed",
            "status_version": step["status_version"],
            "output_artifact_ids": [],
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": failure_ids,
        }
    elif status == "awaiting_human":
        pending_queue = _awaiting_pending_queue(port, step_run_id)
        if not isinstance(resume_token, str) or len(resume_token) < 32:
            raise OrchestratorRefused(
                "legacy 入口停在 awaiting_human 但未返回 resume_token: %s" % step_run_id
            )
        if not pending_queue:
            raise OrchestratorRefused(
                "legacy 入口停在 awaiting_human 但待处理队列为空: %s" % step_run_id
            )
        result = {
            "schema_version": "1.0.0",
            "processing_run_id": step["processing_run_id"],
            "step_run_id": step_run_id,
            "status": "awaiting_human",
            "status_version": step["status_version"],
            "output_artifact_ids": [],
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
            "resume_token": resume_token,
            "pending_queue_artifact_ids": pending_queue,
        }
    else:
        raise OrchestratorRefused(
            "legacy 入口 StepRun 状态不可接受: %s" % status
        )
    _validate_step_result(result)
    return result


def run_legacy(port, binding, handle):
    """调用 ``legacy_self_driving`` 入口，并从 Ledger 重建 StepResult。

    入口可在同一 StepRun 上停成 ``awaiting_human``（M4 分歧、M6 审核）；此时重建的
    StepResult 带入口当次返回的 ``resume_token``（只经内存交给调用方，不落盘）。
    """
    try:
        service = port.unwrap()
    except NotImplementedError:
        raise OrchestratorRefused("legacy_self_driving 需要直连 Ledger Adapter")

    entry_kwargs = dict(binding.entry_kwargs)
    if binding.descriptor.get(RUN_INPUTS_KEY) is True:
        entry_kwargs["run_inputs"] = handle.get("run_inputs")
    try:
        summary = binding.target(
            service, handle["edition_part_id"], **entry_kwargs
        )
    except Exception as exc:  # noqa: BLE001 - 入口承诺 begin 之前零写入
        raise OrchestratorRefused(
            "legacy 入口异常（%s: %s）" % (type(exc).__name__, exc)
        )

    step_run_id = summary["step_run_id"]
    step = port.get_step_run(step_run_id)
    if step is None:
        raise OrchestratorRefused("legacy 入口返回的 step_run_id 不存在: %s" % step_run_id)

    if binding.owns_processing_run:
        processing_run_id = summary["processing_run_id"]
    else:
        if step["processing_run_id"] != handle["processing_run_id"]:
            raise OrchestratorRefused(
                "legacy 入口的 processing_run_id 与 handle 不一致: %s != %s"
                % (step["processing_run_id"], handle["processing_run_id"])
            )
        processing_run_id = handle["processing_run_id"]

    result = legacy_step_result(
        port, step, resume_token=summary.get("resume_token")
    )
    return {
        "step_run_id": step_run_id,
        "processing_run_id": processing_run_id,
        "step_result": result,
    }
