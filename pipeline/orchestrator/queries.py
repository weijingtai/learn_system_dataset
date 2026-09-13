"""六项只读查询（规格 §5 :117–127 闭集）。

只调用 LedgerPort 读方法与 ``gate.evaluate_stage_gate`` / ``gate.effective_step_runs``，
不写入任何数据。
"""

import json
from datetime import datetime

from pipeline.ledger.errors import MissingReference

from . import EDITION_STAGES
from .gate import effective_step_runs, evaluate_stage_gate

# 六项查询（名称闭集）
QUERY_NAMES = (
    "RunStatus",
    "StageProgress",
    "PendingQueue",
    "BlockingReasons",
    "ReworkImpact",
    "ThroughputEstimate",
)

_TERMINAL_STEP_RUN = frozenset({"succeeded", "failed", "superseded"})


def _parse_json(value):
    if value is None or isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return None
    return None


def _failed_checks(gate):
    return [
        name for name in gate["checks"] if not gate["checks"][name]["ok"]
    ]


def run_status(port, registry, handle):
    """RunStatus：Ledger 聚合状态 + 该 Part 是否全 Gate 通过。"""
    raw = port.run_status(handle["processing_run_id"])
    complete = all(
        evaluate_stage_gate(port, registry, handle, stage)["gate"] == "passed"
        for stage in EDITION_STAGES
    )
    return {
        "processing_run_id": handle["processing_run_id"],
        "edition_part_id": handle["edition_part_id"],
        "status": raw["status"],
        "started_at": raw["started_at"],
        "finished_at": raw["finished_at"],
        "edition_part_complete": complete,
    }


def stage_progress(port, registry, handle):
    """StageProgress：各 stage 的计数、Gate 与未通过检查名。"""
    raw = port.stage_progress(handle["processing_run_id"]) or {}
    defaults = {
        "step_runs": 0,
        "succeeded": 0,
        "failed": 0,
        "running": 0,
        "awaiting_human": 0,
        "suspended": 0,
        "superseded": 0,
        "last_checkpoint_revision_id": None,
    }
    progress = {}
    previous_passed = False
    for stage in EDITION_STAGES:
        entry = dict(defaults)
        entry.update(raw.get(stage) or {})
        effective = effective_step_runs(port, handle, stage)
        gate = evaluate_stage_gate(port, registry, handle, stage)
        if not effective and not previous_passed:
            entry["gate"] = "not_started"
            entry["failed_checks"] = []
        elif not effective:
            entry["gate"] = "blocked"
            entry["failed_checks"] = _failed_checks(gate)
        else:
            entry["gate"] = gate["gate"]
            entry["failed_checks"] = _failed_checks(gate)
        previous_passed = entry["gate"] == "passed"
        progress[stage] = entry
    return progress


def pending_queue(port, registry, handle):
    """PendingQueue：五个专用队列恒存在，非专用阶段的待办进 ``non_human_pending``。"""
    queues = {name: [] for name in registry.human_queues.values()}
    non_human_pending = []
    run = port.run_status(handle["processing_run_id"])
    for step in run["step_runs"]:
        if step.get("status") != "awaiting_human":
            continue
        await_events = [
            event
            for event in port.list_step_run_events(step["step_run_id"])
            if event.get("event_type") == "await_human"
        ]
        if not await_events:
            continue
        last = await_events[-1]
        payload = json.loads(last.get("payload_json") or "{}")
        item = {
            "step_run_id": step["step_run_id"],
            "stage": step["stage"],
            "pending_queue_artifact_ids": list(payload.get("pending_queue") or []),
            "since": last.get("created_at"),
        }
        stage = step["stage"]
        if stage in registry.human_queues:
            queues[registry.human_queues[stage]].append(item)
        else:
            non_human_pending.append(dict(item, reason="阶段无专用人工队列"))

    for stage in EDITION_STAGES:
        checkpoint = port.latest_checkpoint(handle["edition_part_id"], stage)
        if checkpoint is None:
            continue
        content = checkpoint.get("content") or {}
        pending = list(content.get("pending_queue") or [])
        if not pending:
            continue
        step = port.get_step_run(checkpoint["step_run_id"])
        if step is not None and step.get("status") not in _TERMINAL_STEP_RUN:
            non_human_pending.append(
                {
                    "stage": stage,
                    "step_run_id": checkpoint["step_run_id"],
                    "pending_tasks": pending,
                }
            )
    return {"queues": queues, "non_human_pending": non_human_pending}


def blocking_reasons(port, registry, handle):
    """BlockingReasons：首个未通过 Gate 的 stage 的全部未通过检查 + rework 告警。"""
    blocking = []
    run = port.run_status(handle["processing_run_id"])
    for stage in EDITION_STAGES:
        gate = evaluate_stage_gate(port, registry, handle, stage)
        if gate["gate"] == "passed":
            continue
        for name in gate["checks"]:
            if not gate["checks"][name]["ok"]:
                blocking.append(
                    {
                        "stage": stage,
                        "check": name,
                        "detail": gate["checks"][name]["detail"],
                    }
                )
        break

    rework_round = sum(
        1 for step in run["step_runs"] if step.get("supersedes_step_run_id")
    )
    warnings = []
    if rework_round >= 3:
        warnings.append(
            {
                "code": "rework_threshold_exceeded",
                "rework_round": rework_round,
                "ratio_check": "not_evaluated",
            }
        )
    return {"blocking": blocking, "warnings": warnings}


def rework_impact(port, registry, handle, artifact_revision_id):
    """ReworkImpact：按 StepRun 粒度血缘可达性估算返工影响面。"""
    trigger = port.get_revision(artifact_revision_id)
    if trigger is None:
        raise MissingReference(
            "触发修订不存在: %s" % artifact_revision_id, code="REF_001"
        )
    run = port.run_status(handle["processing_run_id"])
    steps = run["step_runs"]

    reached = {artifact_revision_id}
    affected_steps = set()
    changed = True
    while changed:
        changed = False
        for step in steps:
            if step["step_run_id"] in affected_steps:
                continue
            request = _parse_json(step.get("request_json")) or {}
            inputs = set(request.get("input_artifact_ids") or [])
            if inputs & reached:
                affected_steps.add(step["step_run_id"])
                result = _parse_json(step.get("result_json")) or {}
                for revision_id in result.get("output_artifact_ids") or []:
                    if revision_id not in reached:
                        reached.add(revision_id)
                        changed = True

    affected_stages = []
    for stage in EDITION_STAGES:
        if any(
            step["stage"] == stage and step["step_run_id"] in affected_steps
            for step in steps
        ):
            affected_stages.append(stage)

    invalidated_count = len(reached) - 1
    all_outputs = set()
    for step in steps:
        if step.get("status") == "succeeded":
            result = _parse_json(step.get("result_json")) or {}
            all_outputs.update(result.get("output_artifact_ids") or [])
    carried_forward_count = len(all_outputs) - invalidated_count

    needs_review_count = 0
    for step in steps:
        if step["step_run_id"] in affected_steps:
            needs_review_count += sum(
                1
                for event in port.list_step_run_events(step["step_run_id"])
                if event.get("event_type") == "human_event"
            )

    affected_queues = []
    for stage in affected_stages:
        name = registry.human_queues.get(stage)
        if name is not None and name not in affected_queues:
            affected_queues.append(name)

    rework_round = sum(
        1 for step in steps if step.get("supersedes_step_run_id")
    )
    return {
        "estimate": True,
        "trigger_revision_id": artifact_revision_id,
        "affected_stages": affected_stages,
        "invalidated_count": invalidated_count,
        "carried_forward_count": carried_forward_count,
        "needs_review_count": needs_review_count,
        "rework_round": rework_round,
        "trigger_correction_request_id": None,
        "affected_queues": affected_queues,
    }


def _parse_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def throughput_estimate(port, registry, handle):
    """ThroughputEstimate：按已 succeeded StepRun 的历时均值估算剩余阶段耗时。"""
    run = port.run_status(handle["processing_run_id"])
    samples_by_stage = {stage: [] for stage in EDITION_STAGES}
    all_samples = []
    for step in run["step_runs"]:
        if step.get("status") != "succeeded":
            continue
        start = _parse_timestamp(step.get("created_at"))
        end = _parse_timestamp(step.get("updated_at"))
        if start is None or end is None:
            continue
        seconds = (end - start).total_seconds()
        if step["stage"] in samples_by_stage:
            samples_by_stage[step["stage"]].append(seconds)
        all_samples.append(seconds)

    per_stage_seconds = {
        stage: (sum(values) / len(values) if values else None)
        for stage, values in samples_by_stage.items()
    }
    remaining_stages = [
        stage
        for stage in EDITION_STAGES
        if evaluate_stage_gate(port, registry, handle, stage)["gate"] != "passed"
    ]
    if all_samples:
        estimated = (sum(all_samples) / len(all_samples)) * len(remaining_stages)
    else:
        estimated = None
    return {
        "per_stage_seconds": per_stage_seconds,
        "remaining_stages": remaining_stages,
        "estimated_remaining_seconds": estimated,
        "basis": "succeeded_step_runs",
    }
