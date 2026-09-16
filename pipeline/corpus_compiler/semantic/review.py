"""M3 语义层事务：边界分歧队列、人工裁决即时落盘与恢复封存（act/05，规格 §17.1）。

流程（README §4.3、BDD 场景 6）：

    1. ``open_semantic_review``：解析 M2 冻结输入 → 结构切分 → 窗口选择 → 双路独立提议 →
       比较与分歧判定 → 封存 ``boundary_review_queue`` → StepRun 进入 ``awaiting_human``
       并返回单次有效的 ``resume_token``；
    2. ``submit_boundary_decision``：审核员逐条提交裁决，写不可变 ``human_event``
       （``schema: m3_boundary_decision/1``、``decision_type: review_source_fidelity``），
       **每条裁决被接受后立即落盘一个独立 Checkpoint**（§17.1），绝不延后合并；
    3. ``resume_m3_text_full``：全部分歧窗口解决后方可恢复；未决分歧存在时严禁放行
       （抛 ``DisputesUnresolved``，StepRun 维持 ``awaiting_human``）。恢复后合成
       ``sem_`` 语义片段、运行独立语义 Gate，组装并登记 m3 StagePackage
       （``gate_profile: structural_and_semantic``）、StepRun 终态 ``succeeded``。

P7：本模块只定义决定表格式与导入路径，**不代填任何人工结论**；测试用裁决一律标
``synthetic_fixture: true``。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from pipeline.ledger import ids
from pipeline.ledger.service import LedgerService

from ..errors import CompileRefused
from ..step_offset import resolve_m3_text_inputs
from ..text_compiler import compile_offset_spans, dump_yaml_bytes
from .offset_assemble import (
    BOUNDARY_CROSS_MODEL_AGREED,
    BOUNDARY_HUMAN_DECIDED,
    GATE_PROFILE,
    compile_semantic_offset,
)
from .offset_rules import DEFAULT_MODEL_MIN_CHARS, select_text_windows
from .proposals import compare_proposals, parse_proposal
from .proposer import ReplayProposer, load_recordings

M3_SEMANTIC_TOOL = "pipeline.corpus_compiler.semantic.review"
M3_SEMANTIC_TOOL_VERSION = "0.1.0"

QUEUE_SCHEMA = "m3_boundary_review_queue/1"
DECISION_SCHEMA = "m3_boundary_decision/1"
DECISION_TYPE = "review_source_fidelity"

QUEUE_ARTIFACT_TYPE = "boundary_review_queue"
EVENT_ARTIFACT_TYPE = "human_event"

DECISION_CHOICES = ("a", "b", "custom")


class SemanticRefused(CompileRefused):
    """语义层事务被拒绝（非法裁决、非分歧窗口、Gate 未通过等）。"""


class DisputesUnresolved(CompileRefused):
    """存在未决分歧窗口：严禁恢复（规格 §11:521）。"""


def open_semantic_review(
    service: LedgerService,
    edition_part_id: str,
    *,
    recordings: bytes,
    model_min_chars: int = DEFAULT_MODEL_MIN_CHARS,
) -> dict[str, Any]:
    """开语义层运行：双路提议 → 分歧入队 → ``awaiting_human``（返回 ``resume_token``）。

    零模型调用（P6）：双路提议一律来自手写合成录制（``ReplayProposer``）。
    """
    # ---- 1. M2 冻结输入（P5 + §10.1 门禁；失败在 begin 之前抛出，零写入）----
    inputs = resolve_m3_text_inputs(service, edition_part_id)

    # ---- 2. 结构切分（确定性，与结构层同一算法）----
    structural = compile_offset_spans(
        work=inputs.work,
        edition=inputs.edition,
        edition_part_artifact_id=edition_part_id,
        raw_text_revision_id=inputs.raw_text_revision_id,
        raw_text=inputs.raw_text,
        cleaned_text_revision_id=inputs.cleaned_text_revision_id,
        cleaned_text=inputs.cleaned_text,
        patches=inputs.patches,
    )

    # ---- 3. 窗口选择与双路独立提议 ----
    windows = select_text_windows(structural["spans"], model_min_chars=model_min_chars)
    recorded = load_recordings(recordings)
    proposer_a = ReplayProposer(recorded)
    proposer_b = ReplayProposer(recorded)

    resolutions: dict[str, dict] = {}
    window_items: list[dict] = []

    for window in windows:
        parsed_a = parse_proposal(
            proposer_a.propose(slot="a", window=window), window["text"]
        )
        parsed_b = parse_proposal(
            proposer_b.propose(slot="b", window=window), window["text"]
        )
        compared = compare_proposals(parsed_a, parsed_b)

        item = dict(window)
        item["proposal_a"] = parsed_a
        item["proposal_b"] = parsed_b
        item["status"] = compared["status"]
        item["reason"] = compared["reason"]
        item["segments"] = compared["segments"]
        window_items.append(item)

        if compared["status"] == "agreed":
            resolutions[window["window_id"]] = {
                "boundary_origin": BOUNDARY_CROSS_MODEL_AGREED,
                "segments": compared["segments"],
            }

    disputed = [item for item in window_items if item["status"] == "disputed"]

    # ---- 4. 配置与 StepRun（同阶段已封存则经 supersede 续写，rulings 32/58）----
    processing_run_id = inputs.processing_run_id
    if not processing_run_id:
        processing_run_id = service.create_processing_run(
            "edition_run", edition_part_id, inputs.technique_id
        )

    config_bytes = json.dumps(
        {
            "stage": "m3",
            "tool": M3_SEMANTIC_TOOL,
            "tool_version": M3_SEMANTIC_TOOL_VERSION,
            "evidence_level": "offset_level",
            "gate_profile": GATE_PROFILE,
            "model_min_chars": model_min_chars,
            "proposer": "replay",
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    _, config_rev = service.put_run_artifact(
        processing_run_id,
        "configuration",
        config_bytes,
        producer_module=M3_SEMANTIC_TOOL,
        producer_version=M3_SEMANTIC_TOOL_VERSION,
    )

    frozen = [
        inputs.raw_text_revision_id,
        inputs.cleaned_text_revision_id,
        inputs.patch_set_revision_id,
        inputs.report_revision_id,
    ]
    request = {
        "schema_version": "1.0.0",
        "processing_run_id": processing_run_id,
        "step_run_id": ids.new_id("step_run_id"),
        "input_artifact_ids": frozen,
        "technique_profile_id": inputs.technique_id,
        "configuration_artifact_id": config_rev,
    }

    previous = _previous_succeeded_m3_run(service, edition_part_id)
    if previous is None:
        step_run_id = service.begin_step_run(request)
    else:
        step_run_id = service.supersede_step_run(previous, request)

    # ---- 5. 封存分歧队列 + Checkpoint + awaiting_human ----
    queue_doc = {
        "schema": QUEUE_SCHEMA,
        "edition_part_id": edition_part_id,
        "work": inputs.work,
        "edition": inputs.edition,
        "model_min_chars": model_min_chars,
        "raw_text_revision_id": inputs.raw_text_revision_id,
        "cleaned_text_revision_id": inputs.cleaned_text_revision_id,
        "patch_set_revision_id": inputs.patch_set_revision_id,
        "report_revision_id": inputs.report_revision_id,
        "structural_spans_sha256": hashlib.sha256(
            structural["spans_bytes"]
        ).hexdigest(),
        "resolutions": resolutions,
        "dispute_count": len(disputed),
        "windows": window_items,
    }
    queue_bytes = json.dumps(queue_doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
    _, queue_rev = service.put_artifact(
        step_run_id,
        QUEUE_ARTIFACT_TYPE,
        queue_bytes,
        producer_module=M3_SEMANTIC_TOOL,
        producer_version=M3_SEMANTIC_TOOL_VERSION,
        configuration_revision_id=config_rev,
    )
    service.seal_revision(queue_rev)

    pending = [
        {"task_id": _review_task_id(item["window_id"]), "window_id": item["window_id"]}
        for item in disputed
    ]
    service.write_checkpoint(
        step_run_id,
        edition_part_id=edition_part_id,
        stage="m3",
        completed_tasks=[
            {
                "task_id": QUEUE_ARTIFACT_TYPE,
                "artifact_revision_id": queue_rev,
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=[],
        pending_queue=pending,
        next_pointer=pending[0] if pending else None,
    )

    resume_token = service.await_human(step_run_id, [queue_rev])

    return {
        "status": "awaiting_human",
        "step_run_id": step_run_id,
        "resume_token": resume_token,
        "queue_revision_id": queue_rev,
        "queue": queue_doc,
        "window_count": len(window_items),
        "dispute_count": len(disputed),
        "disputed_windows": [item["window_id"] for item in disputed],
        "structural_spans": structural["spans"],
    }


def submit_boundary_decision(
    service: LedgerService,
    step_run_id: str,
    resume_token: str,
    decision: dict,
) -> dict[str, Any]:
    """提交一条边界分歧人工裁决，并**立即**落盘独立 Checkpoint（§17.1）。

    异常：
        InvalidResumeToken: StepRun 非 ``awaiting_human`` 或 token 不匹配（Ledger 层抛出）；
        SemanticRefused: 决定表格式非法、指向窗口非分歧窗口或切分不合法。
    """
    step = service.get_step_run(step_run_id)
    if step is None:
        raise SemanticRefused("StepRun 不存在: %s" % step_run_id)
    if step["status"] != "awaiting_human":
        raise SemanticRefused(
            "StepRun %s 状态为 %s，非 awaiting_human，拒绝裁决" % (step_run_id, step["status"])
        )
    # token 校验（与 Ledger 公开写路径同一校验；非法即 InvalidResumeToken，不消费 token）
    service._check_token(step, resume_token)

    queue_doc = _read_queue(service, step_run_id)
    edition_part_id = queue_doc["edition_part_id"]

    document = _validate_decision_document(decision)
    window_id = document["window_id"]
    item = next(
        (w for w in queue_doc.get("windows", []) if w.get("window_id") == window_id), None
    )
    if item is None:
        raise SemanticRefused("窗口 %r 不在本次边界分歧队列中" % (window_id,))
    if item.get("status") != "disputed":
        raise SemanticRefused(
            "窗口 %r 双路边界一致（%s），无需人工裁决" % (window_id, item.get("status"))
        )

    segments = _validate_segments(document.get("segments"), item.get("text"), window_id)
    _check_choice_consistency(document, item, segments)

    event_doc = dict(document)
    event_doc["segments"] = segments
    event_bytes = json.dumps(event_doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
    _, event_rev = service.put_artifact(
        step_run_id,
        EVENT_ARTIFACT_TYPE,
        event_bytes,
        producer_module=M3_SEMANTIC_TOOL,
        producer_version=M3_SEMANTIC_TOOL_VERSION,
    )
    service.seal_revision(event_rev)
    service.record_human_event(
        step_run_id, resume_token, event_rev, decision_type=DECISION_TYPE
    )

    # ---- 核心纪律：每条裁决被接受后立即落盘一个独立 Checkpoint ----
    mine = _my_checkpoints(service, step_run_id, edition_part_id)
    human_decisions: list[str] = []
    for checkpoint in mine:
        for revision_id in checkpoint["content"].get("human_decisions", []) or []:
            if revision_id not in human_decisions:
                human_decisions.append(revision_id)
    if event_rev not in human_decisions:
        human_decisions.append(event_rev)

    decided = _decided_windows(service, step_run_id, edition_part_id)
    decided.add(window_id)
    remaining = [
        {"task_id": _review_task_id(w["window_id"]), "window_id": w["window_id"]}
        for w in queue_doc.get("windows", [])
        if w.get("status") == "disputed" and w.get("window_id") not in decided
    ]

    checkpoint_revision_id = service.write_checkpoint(
        step_run_id,
        edition_part_id=edition_part_id,
        stage="m3",
        completed_tasks=[
            {
                "task_id": _review_task_id(window_id),
                "artifact_revision_id": event_rev,
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=human_decisions,
        pending_queue=remaining,
        next_pointer=remaining[0] if remaining else None,
    )

    return {
        "status": "recorded",
        "step_run_id": step_run_id,
        "window_id": window_id,
        "event_revision_id": event_rev,
        "checkpoint_revision_id": checkpoint_revision_id,
        "remaining_disputes": len(remaining),
    }


def resume_m3_text_full(
    service: LedgerService,
    step_run_id: str,
    resume_token: str,
    *,
    gate: Callable | None = None,
) -> dict[str, Any]:
    """全部分歧解决后恢复：合成语义片段 → 语义 Gate → 登记 m3 StagePackage → succeeded。

    参数：
        gate: 独立语义 Gate 可调用（act/06 的 ``evaluate_semantic_offset``）。缺省 None 时
            延迟导入该模块；Gate 返回 ``semantic != "passed"`` 时拒绝恢复（StepRun 保持
            ``awaiting_human``，token 不被消费）。

    异常：
        DisputesUnresolved: 仍有分歧窗口未裁决（StepRun 维持 ``awaiting_human``）；
        SemanticRefused: Gate 未通过；
        InvalidResumeToken: StepRun 非 ``awaiting_human`` 或 token 不匹配。
    """
    step = service.get_step_run(step_run_id)
    if step is None:
        raise SemanticRefused("StepRun 不存在: %s" % step_run_id)
    if step["status"] != "awaiting_human":
        raise SemanticRefused(
            "StepRun %s 状态为 %s，非 awaiting_human，拒绝恢复" % (step_run_id, step["status"])
        )
    service._check_token(step, resume_token)

    queue_doc = _read_queue(service, step_run_id)
    edition_part_id = queue_doc["edition_part_id"]
    model_min_chars = queue_doc.get("model_min_chars", DEFAULT_MODEL_MIN_CHARS)

    disputed = [
        item for item in queue_doc.get("windows", []) if item.get("status") == "disputed"
    ]
    decisions = _load_decisions(service, step_run_id, edition_part_id)
    unresolved = [item["window_id"] for item in disputed if item["window_id"] not in decisions]
    if unresolved:
        raise DisputesUnresolved(
            "存在未决分歧窗口 %d 个: %s" % (len(unresolved), ", ".join(unresolved))
        )

    # ---- 合成语义片段：一致窗口取比较结果，分歧窗口取人工裁决 ----
    inputs = resolve_m3_text_inputs(service, edition_part_id)
    structural = compile_offset_spans(
        work=inputs.work,
        edition=inputs.edition,
        edition_part_artifact_id=edition_part_id,
        raw_text_revision_id=inputs.raw_text_revision_id,
        raw_text=inputs.raw_text,
        cleaned_text_revision_id=inputs.cleaned_text_revision_id,
        cleaned_text=inputs.cleaned_text,
        patches=inputs.patches,
    )

    resolutions = {
        window_id: dict(resolution)
        for window_id, resolution in (queue_doc.get("resolutions") or {}).items()
    }
    decision_documents = []
    for item in disputed:
        document = decisions[item["window_id"]]
        segments = _validate_segments(
            document.get("segments"), item.get("text"), item["window_id"]
        )
        resolutions[item["window_id"]] = {
            "boundary_origin": BOUNDARY_HUMAN_DECIDED,
            "segments": segments,
        }
        decision_documents.append(document)

    windows = select_text_windows(structural["spans"], model_min_chars=model_min_chars)
    semantic_doc = compile_semantic_offset(
        structural_spans=structural["spans"],
        windows=windows,
        resolutions=resolutions,
        raw_text_revision_id=inputs.raw_text_revision_id,
        raw_text=inputs.raw_text,
        cleaned_text_revision_id=inputs.cleaned_text_revision_id,
        cleaned_text=inputs.cleaned_text,
        patches=inputs.patches,
        work=inputs.work,
        edition=inputs.edition,
        edition_part_artifact_id=edition_part_id,
    )
    semantic_bytes = dump_yaml_bytes(semantic_doc)

    # ---- 语义 Gate（独立实现；结果 load-bearing）----
    gate_fn = gate if gate is not None else _default_semantic_gate()
    gate_result = gate_fn(
        cleaned_text=inputs.cleaned_text,
        patches=inputs.patches,
        structural_spans_doc=structural["spans_doc"],
        semantic_spans_doc=semantic_doc,
        window_responses=queue_doc.get("windows", []),
        decisions=decision_documents,
        model_min_chars=model_min_chars,
    )
    if gate_result.get("semantic") != "passed":
        failed = [
            name
            for name, check in (gate_result.get("checks") or {}).items()
            if not check.get("ok")
        ]
        raise SemanticRefused("语义 Gate 未通过: %s" % (", ".join(failed) or "semantic != passed"))

    # ---- 消费 token：awaiting_human → running ----
    service.resume(step_run_id, resume_token)

    _, spans_rev = service.put_artifact(
        step_run_id,
        "semantic_spans",
        semantic_bytes,
        producer_module=M3_SEMANTIC_TOOL,
        producer_version=M3_SEMANTIC_TOOL_VERSION,
    )
    service.seal_revision(spans_rev)

    report_doc = {
        "schema_version": "0.1.0-draft",
        "kind": "stage_gate",
        "stage": "m3",
        "gate_profile": GATE_PROFILE,
        "semantic": gate_result.get("semantic"),
        "checks": gate_result.get("checks"),
        "span_count": semantic_doc["span_count"],
        "window_count": semantic_doc["window_count"],
        "dispute_count": semantic_doc["dispute_count"],
    }
    _, report_rev = service.put_artifact(
        step_run_id,
        "validation_report",
        json.dumps(report_doc, sort_keys=True, ensure_ascii=False).encode("utf-8"),
        producer_module=M3_SEMANTIC_TOOL,
        producer_version=M3_SEMANTIC_TOOL_VERSION,
    )
    service.seal_revision(report_rev)

    frozen = service._frozen_input_ids(step_run_id)
    queue_revision_id = _queue_revision(service, step_run_id)
    input_revision_ids = [
        revision_id
        for revision_id in dict.fromkeys(list(frozen) + [queue_revision_id])
        if revision_id
    ]
    human_event_revision_ids = [d["_revision_id"] for d in decisions.values() if d.get("_revision_id")]

    service.record_transformation(
        step_run_id,
        operation="compile_semantic",
        tool=M3_SEMANTIC_TOOL,
        tool_version=M3_SEMANTIC_TOOL_VERSION,
        configuration_revision_id=json.loads(step["request_json"])["configuration_artifact_id"],
        input_revision_ids=input_revision_ids,
        output_revision_ids=[spans_rev],
        human_event_revision_ids=human_event_revision_ids,
    )

    package = _build_stage_package(
        service,
        step_run_id=step_run_id,
        spans_revision_id=spans_rev,
        validation_report_revision_id=report_rev,
        semantic_doc=semantic_doc,
        semantic_bytes=semantic_bytes,
        input_revision_ids=input_revision_ids,
        configuration_revision_id=json.loads(step["request_json"])["configuration_artifact_id"],
    )
    package_id = package["stage_package_id"]
    package_revision_id = package["artifact_revision_id"]
    service.register_stage_package(
        step_run_id,
        package,
        json.dumps(package, sort_keys=True, ensure_ascii=False).encode("utf-8"),
        stage_package_id=package_id,
        artifact_revision_id=package_revision_id,
    )
    service.seal_revision(package_revision_id)

    current = service.get_step_run(step_run_id)
    service.finish_step_run(
        step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": current["processing_run_id"],
            "step_run_id": step_run_id,
            "status_version": current["status_version"] + 1,
            "status": "succeeded",
            "output_artifact_ids": [spans_rev, report_rev],
            "validation_report_ids": [report_rev],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
        },
    )

    return {
        "status": "succeeded",
        "step_run_id": step_run_id,
        "semantic": gate_result.get("semantic"),
        "spans_revision_id": spans_rev,
        "validation_report_revision_id": report_rev,
        "stage_package_id": package_id,
        "stage_package_revision_id": package_revision_id,
        "span_count": semantic_doc["span_count"],
        "window_count": semantic_doc["window_count"],
        "dispute_count": semantic_doc["dispute_count"],
        "resume_token": resume_token,
    }


# --------------------------------------------------------------------------
# 内部辅助
# --------------------------------------------------------------------------


def _review_task_id(window_id: str) -> str:
    """人工裁决任务的 Checkpoint task_id（``review:<window_id>``）。"""
    return "review:%s" % window_id


def _previous_succeeded_m3_run(service: LedgerService, edition_part_id: str):
    """本 EditionPart 上最近一个 succeeded 的 m3 StepRun（经读接口查出，不写死号）。"""
    for checkpoint in service.list_checkpoints(edition_part_id, "m3"):
        step_run_id = checkpoint["content"].get("step_run_id")
        if not step_run_id:
            continue
        step = service.get_step_run(step_run_id)
        if step is not None and step.get("status") == "succeeded":
            return step_run_id
    return None


def _my_checkpoints(service: LedgerService, step_run_id: str, edition_part_id: str):
    """本 StepRun 写下的 Checkpoint（按链序）。"""
    return [
        checkpoint
        for checkpoint in service.list_checkpoints(edition_part_id, "m3")
        if checkpoint["content"].get("step_run_id") == step_run_id
    ]


def _queue_revision(service: LedgerService, step_run_id: str):
    """从 ``await_human`` 事件取回 ``boundary_review_queue`` 修订号。"""
    for event in service.list_step_run_events(step_run_id):
        if event.get("event_type") != "await_human":
            continue
        payload = json.loads(event.get("payload_json") or "{}")
        pending = payload.get("pending_queue") or []
        if pending:
            return pending[0]
    return None


def _read_queue(service: LedgerService, step_run_id: str) -> dict:
    """读回并解析本次运行的边界分歧队列。"""
    queue_rev = _queue_revision(service, step_run_id)
    if not queue_rev:
        raise SemanticRefused("StepRun %s 无 boundary_review_queue 记录" % step_run_id)
    revision = service.get_revision(queue_rev)
    if revision is None:
        raise SemanticRefused("队列修订不存在: %s" % queue_rev)
    document = json.loads(service.objects.get(revision["sha256"]).decode("utf-8"))
    if document.get("schema") != QUEUE_SCHEMA:
        raise SemanticRefused("队列 schema 非 %r" % QUEUE_SCHEMA)
    return document


def _decided_windows(service: LedgerService, step_run_id: str, edition_part_id: str) -> set:
    """已完成裁决的窗口集合（按 Checkpoint 的 review:<window_id> 任务）。"""
    decided = set()
    for checkpoint in _my_checkpoints(service, step_run_id, edition_part_id):
        for task in checkpoint["content"].get("completed_tasks", []) or []:
            task_id = task.get("task_id") or ""
            if task_id.startswith("review:") and task.get("artifact_revision_id"):
                decided.add(task_id.split(":", 1)[1])
    return decided


def _load_decisions(service: LedgerService, step_run_id: str, edition_part_id: str) -> dict:
    """读回本运行的全部人工裁决文档（``{window_id: 裁决字典}``）。"""
    decisions: dict[str, dict] = {}
    for checkpoint in _my_checkpoints(service, step_run_id, edition_part_id):
        for task in checkpoint["content"].get("completed_tasks", []) or []:
            task_id = task.get("task_id") or ""
            revision_id = task.get("artifact_revision_id")
            if not task_id.startswith("review:") or not revision_id:
                continue
            revision = service.get_revision(revision_id)
            if revision is None:
                raise SemanticRefused("裁决事件修订不存在: %s" % revision_id)
            document = json.loads(service.objects.get(revision["sha256"]).decode("utf-8"))
            document["_revision_id"] = revision_id
            decisions[task_id.split(":", 1)[1]] = document
    return decisions


def _validate_decision_document(decision) -> dict:
    """校验决定表顶层形态（schema / decision_type 恒为 review_source_fidelity）。"""
    if not isinstance(decision, dict):
        raise SemanticRefused("裁决必须是映射")

    document = dict(decision)
    if document.get("schema") != DECISION_SCHEMA:
        raise SemanticRefused("裁决 schema 必须为 %r" % DECISION_SCHEMA)
    if document.get("decision_type") != DECISION_TYPE:
        raise SemanticRefused("裁决 decision_type 恒为 %r" % DECISION_TYPE)

    window_id = document.get("window_id")
    if not isinstance(window_id, str) or not window_id:
        raise SemanticRefused("裁决缺 window_id")

    choice = document.get("choice")
    if choice not in DECISION_CHOICES:
        raise SemanticRefused("裁决 choice 必须为 %r 之一，实际 %r" % (DECISION_CHOICES, choice))

    if document.get("synthetic_fixture") not in (True, False, None):
        raise SemanticRefused("裁决 synthetic_fixture 必须为布尔值")

    return document


def _validate_segments(segments, window_text, window_id) -> list[list[int]]:
    """校验裁决切分：整数区间、首尾相连、完整覆盖窗口（与提议同一套纪律）。"""
    if not isinstance(window_text, str):
        raise SemanticRefused("窗口 %r 原文缺失，无法校验裁决" % (window_id,))
    if not isinstance(segments, list) or not segments:
        raise SemanticRefused("窗口 %r 的裁决切分为空" % (window_id,))

    normalized: list[list[int]] = []
    for pair in segments:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise SemanticRefused("窗口 %r 的裁决区间形非法: %r" % (window_id, pair))
        start, end = pair[0], pair[1]
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
            or start < 0
            or end > len(window_text)
            or start >= end
        ):
            raise SemanticRefused(
                "窗口 %r 的裁决区间越界或非法: [%r, %r)" % (window_id, start, end)
            )
        normalized.append([start, end])

    if normalized[0][0] != 0 or normalized[-1][1] != len(window_text):
        raise SemanticRefused("窗口 %r 的裁决未完整覆盖窗口" % (window_id,))
    previous_end = normalized[0][0]
    for start, end in normalized:
        if start > previous_end:
            raise SemanticRefused("窗口 %r 的裁决存在缺口: [%d, %d)" % (window_id, previous_end, start))
        if start < previous_end:
            raise SemanticRefused("窗口 %r 的裁决存在重叠: [%d, %d)" % (window_id, start, previous_end))
        previous_end = end
    return normalized


def _check_choice_consistency(document: dict, item: dict, segments: list) -> None:
    """选择 A / B 时，裁决切分必须与该侧提议逐字一致（防止错标来源）。"""
    choice = document.get("choice")
    if choice == "a":
        expected = (item.get("proposal_a") or {}).get("segments")
    elif choice == "b":
        expected = (item.get("proposal_b") or {}).get("segments")
    else:
        return
    if expected is not None and [list(pair) for pair in expected] != segments:
        raise SemanticRefused(
            "窗口 %r 选择 %s，但裁决切分与该侧提议不一致"
            % (document.get("window_id"), choice)
        )


def _default_semantic_gate() -> Callable:
    """延迟载入独立语义 Gate（act/06 落地；本模块不重复实现 Gate，防同错同过）。"""
    try:
        from .semantic_gate import evaluate_semantic_offset
    except ImportError as exc:  # pragma: no cover - act/05 阶段该模块尚未落地
        raise SemanticRefused("独立语义 Gate 不可用: %s" % exc)
    return evaluate_semantic_offset


def _revision_ref(service: LedgerService, revision_id: str, artifact_type: str) -> dict:
    """构造符合 artifact_ref.schema.json 的制品引用。"""
    revision = service.get_revision(revision_id)
    if revision is None:
        raise SemanticRefused("制品修订不存在: %s" % revision_id)
    return {
        "schema_version": "1.0.0",
        "artifact_kind": "artifact",
        "artifact_id": revision["artifact_id"],
        "artifact_revision_id": revision_id,
        "artifact_type": artifact_type,
    }


def _build_stage_package(
    service: LedgerService,
    *,
    step_run_id: str,
    spans_revision_id: str,
    validation_report_revision_id: str,
    semantic_doc: dict,
    semantic_bytes: bytes,
    input_revision_ids: list,
    configuration_revision_id: str,
) -> dict:
    """组装符合 stage_package.schema.json 的 m3 StagePackage（语义层全量档）。"""
    step = service.get_step_run(step_run_id)
    package_id = ids.new_id("stage_package_id", stage="m3")
    package_revision_id = ids.new_id("artifact_revision_id")

    transformation = {
        "operation": "compile_semantic",
        "step_run_id": step_run_id,
        "configuration_artifact_revision_id": configuration_revision_id,
        "input_artifact_revision_ids": list(dict.fromkeys(input_revision_ids)),
        "output_artifact_revision_ids": [spans_revision_id],
    }

    package = {
        "schema_version": "1.0.0",
        "stage_package_id": package_id,
        "artifact_revision_id": package_revision_id,
        "stage": "m3",
        "status": "sealed",
        "payload": {
            "spans_revision_id": spans_revision_id,
            "coverage_report_revision_id": validation_report_revision_id,
            "coverage": semantic_doc["span_count"],
            "gate_profile": GATE_PROFILE,
            "semantic": "passed",
            "evidence_level": "offset_level",
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": step["processing_run_id"],
            "step_run_id": step_run_id,
            "input_artifacts": [
                _revision_ref(service, revision_id, "artifact")
                for revision_id in dict.fromkeys(input_revision_ids)
            ],
            "output_artifacts": [
                _revision_ref(service, spans_revision_id, "semantic_spans"),
                _revision_ref(service, validation_report_revision_id, "validation_report"),
            ],
            "counts": {
                "spans": semantic_doc["span_count"],
                "windows": semantic_doc["window_count"],
                "disputes": semantic_doc["dispute_count"],
            },
            "content_sha256": hashlib.sha256(semantic_bytes).hexdigest(),
        },
        "validation": {
            "passed": True,
            "report_artifacts": [
                _revision_ref(service, validation_report_revision_id, "validation_report")
            ],
        },
        "lineage": {
            "upstream_artifacts": [
                _revision_ref(service, revision_id, "artifact")
                for revision_id in dict.fromkeys(input_revision_ids)
            ],
            "transformations": [transformation],
        },
        "logs": [],
        "failures": [],
    }
    return package
