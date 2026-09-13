"""人工暂停与恢复（规格 §7.1、§17 :828、§17.1）。

覆盖：人工事件即时落盘（``record_human_event``）、token 消费与重跑（``resume``）、
操作者暂停（``suspend``）、对账恢复（``recover`` / ``reconcile_after_outage``）与从
Checkpoint 重跑（``rerun_from_checkpoint``）。只经 LedgerPort 读写，不 import 加工 Module；
不实现任何等待机制，也不读取 ``step_runs`` 上的时间字段。
"""

import json

from pipeline.contract_registry.ports import PortGuard
from pipeline.ledger import ids

from . import EDITION_STAGES
from .errors import OrchestratorRefused
from .gate import effective_step_runs
from .module import StepContext, bind_module
from .runner import execute_step


def _original_request(port, step_run_id):
    """取 StepRun 的原始 StepRequest（解析 ``request_json``）。"""
    step = port.get_step_run(step_run_id)
    return json.loads(step["request_json"])


def _human_events(port, step_run_id):
    """按事件顺序返回该 StepRun 上已登记的人工事件修订号。"""
    events = []
    for event in port.list_step_run_events(step_run_id):
        if event.get("event_type") == "human_event":
            payload = json.loads(event.get("payload_json") or "{}")
            events.append(payload.get("event_revision_id"))
    return events


def _descriptor_for_step(registry, step):
    descriptor = registry.module_for(step["stage"])
    if descriptor is None:
        raise OrchestratorRefused("阶段 %s 未登记 Module" % step["stage"])
    return descriptor


def _require_step_request(binding, stage):
    if binding.binding != "step_request":
        raise OrchestratorRefused(
            "阶段 %s 的绑定为 %s，不支持该人工恢复操作" % (stage, binding.binding)
        )
    return binding


def record_human_event(
    port,
    registry,
    handle,
    step_run_id,
    resume_token,
    event_revision_id,
    *,
    decision_type=None,
    modules=None,
):
    """登记一条人工事件并**立即**落盘一个 Checkpoint（token 不消费）。"""
    port.record_human_event(
        step_run_id, resume_token, event_revision_id, decision_type=decision_type
    )
    step = port.get_step_run(step_run_id)
    stage = step["stage"]
    descriptor = _descriptor_for_step(registry, step)
    binding = bind_module(descriptor, modules=modules)

    latest = port.latest_checkpoint(handle["edition_part_id"], stage)
    if latest is not None and latest.get("step_run_id") == step_run_id:
        base = latest.get("content") or {}
        completed_tasks = list(base.get("completed_tasks") or [])
        pending = list(base.get("pending_queue") or [])
    else:
        completed_tasks = []
        pending = []

    resolve_pending = getattr(binding.target, "resolve_pending", None)
    if callable(resolve_pending):
        pending = list(resolve_pending(pending, event_revision_id))

    return port.write_checkpoint(
        step_run_id,
        edition_part_id=handle["edition_part_id"],
        stage=stage,
        completed_tasks=completed_tasks,
        human_decisions=_human_events(port, step_run_id),
        pending_queue=pending,
        next_pointer=pending[0] if pending else None,
    )


def resume(port, registry, handle, step_run_id, resume_token, *, modules=None):
    """消费 token 并以 ``mode="resumed"`` 再次执行该 StepRun。"""
    port.resume(step_run_id, resume_token)
    step = port.get_step_run(step_run_id)
    descriptor = _descriptor_for_step(registry, step)
    binding = _require_step_request(
        bind_module(descriptor, modules=modules), step["stage"]
    )
    context = StepContext(
        mode="resumed",
        edition_part_id=handle["edition_part_id"],
        stage=step["stage"],
        module_id=descriptor.get("module_id"),
        human_event_revision_ids=tuple(_human_events(port, step_run_id)),
    )
    return execute_step(port, binding, _original_request(port, step_run_id), context)


def suspend(port, step_run_id, reason):
    """操作者暂停该 StepRun（来源 ``operator``）。"""
    port.suspend(step_run_id, reason, "operator")
    return None


def recover(port, registry, handle, step_run_id, reason, *, modules=None):
    """对账后恢复：回 ``awaiting_human`` 则不执行，回 ``running`` 则按 Checkpoint 续跑。"""
    target = port.recover(step_run_id, reason)
    if target == "awaiting_human":
        return {"status": target, "step_result": None}

    step = port.get_step_run(step_run_id)
    descriptor = _descriptor_for_step(registry, step)
    binding = _require_step_request(
        bind_module(descriptor, modules=modules), step["stage"]
    )
    latest = port.latest_checkpoint(handle["edition_part_id"], step["stage"])
    recovery_plan = None
    if latest is not None and latest.get("step_run_id") == step_run_id:
        content = latest.get("content") or {}
        recovery_plan = {
            "completed_task_ids": [
                item["task_id"]
                for item in content.get("completed_tasks") or []
                if item.get("status") == "succeeded"
            ]
        }
    context = StepContext(
        mode="recovered",
        edition_part_id=handle["edition_part_id"],
        stage=step["stage"],
        module_id=descriptor.get("module_id"),
        human_event_revision_ids=tuple(_human_events(port, step_run_id)),
        recovery_plan=recovery_plan,
    )
    step_result = execute_step(port, binding, _original_request(port, step_run_id), context)
    return {"status": target, "step_result": step_result}


def reconcile_after_outage(port, handle, reason):
    """把本运行内所有非终态 ``running`` 的 StepRun 转为 ``suspended(infrastructure)``。"""
    suspended = []
    for step in port.run_status(handle["processing_run_id"])["step_runs"]:
        if step.get("status") == "running":
            port.suspend(step["step_run_id"], reason, "infrastructure")
            suspended.append(step["step_run_id"])
    return suspended


def rerun_from_checkpoint(port, registry, handle, stage, *, modules=None):
    """从最近 Checkpoint 建新 StepRun（supersedes 旧运行）并续跑未完成任务。"""
    descriptor = registry.module_for(stage)
    if descriptor is None or descriptor.get("supports_recovery") is not True:
        raise OrchestratorRefused(
            "阶段 %s 未声明 supports_recovery，禁止从 Checkpoint 重跑" % stage
        )
    effective = effective_step_runs(port, handle, stage)
    if len(effective) != 1 or effective[0].get("status") not in ("failed", "suspended"):
        raise OrchestratorRefused(
            "阶段 %s 的有效运行不是唯一的 failed/suspended 运行" % stage
        )
    binding = _require_step_request(
        bind_module(descriptor, modules=modules), stage
    )

    upstream = {}
    for prior in EDITION_STAGES:
        if prior == stage:
            break
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
    input_ids = (
        list(planned.get("input_artifact_ids") or []) if isinstance(planned, dict) else []
    )
    if (
        not isinstance(configuration, dict)
        or configuration.get("stage") != descriptor.get("stage")
        or configuration.get("module_id") != descriptor.get("module_id")
    ):
        raise OrchestratorRefused("plan 的 configuration 与登记不符")
    for revision_id in input_ids:
        row = port.get_revision(revision_id)
        if row is None or row.get("status") != "sealed":
            raise OrchestratorRefused("plan 的输入修订未封存: %s" % revision_id)

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
    _new_step_run_id, recovery_plan = port.recover_from_checkpoint(
        handle["edition_part_id"], stage, request
    )
    context = StepContext(
        mode="rerun",
        edition_part_id=handle["edition_part_id"],
        stage=stage,
        module_id=descriptor.get("module_id"),
        human_event_revision_ids=tuple(recovery_plan.get("human_decisions") or []),
        recovery_plan=recovery_plan,
    )
    return execute_step(port, binding, request, context)
