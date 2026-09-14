"""M6 返工链：CorrectionRequest 与精确失效传播（§14.1、§17.1）。

本模块**不改 M4 修订状态**（G7-RULINGS 第 62 条 / D-08 推荐 B）：失效以
``ReworkImpactReport.invalidated[]`` 逐对象登记；旧 ``candidate_set`` 的物理替换由
M4' 重跑经 ``supersede_revision`` 完成（ACT 09）。
"""

import copy
import json

from pipeline.knowledge_extraction.serialize import canonical_json
from pipeline.ledger import ids
from pipeline.ledger.errors import MissingReference, NotConsumable, SchemaViolation
from pipeline.review import M6_TOOL, M6_TOOL_VERSION, propagation, step
from pipeline.review.errors import ReviewRefused
from pipeline.review.inputs import (
    _artifact_types,
    _read_doc,
    latest_succeeded_step_run,
)


def _fail(service, step_run_id, check, detail):
    """begin 之后的异常统一失败封存（检查名 correction_scope / internal）。"""
    failure_data = json.dumps(
        {"check": check, "detail": detail}, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    _, failure_rev = service.put_artifact(
        step_run_id,
        "failure_report",
        failure_data,
        producer_module=M6_TOOL,
        producer_version=M6_TOOL_VERSION,
    )
    service.seal_revision(failure_rev)
    service.fail_step_run(step_run_id, [failure_rev], "M6 %s: %s" % (check, detail))
    return {
        "status": "failed",
        "step_run_id": step_run_id,
        "failed_check": check,
        "failure_revision_id": failure_rev,
        "reason": detail,
    }


def _spans_by_id(spans_doc):
    """把 ``corpus_spans`` 文档规范化为 ``{span_id: span}``（兼容 list/dict 两种形态）。"""
    raw = (spans_doc or {}).get("spans")
    if isinstance(raw, list):
        return {
            s["span_id"]: s
            for s in raw
            if isinstance(s, dict) and "span_id" in s
        }
    if isinstance(raw, dict):
        return raw
    return {}


def _spans_revision_of_frozen(service, step_row):
    """取某 StepRun 冻结输入中的 ``corpus_spans`` 修订号（不存在返回 ``None``）。"""
    request = json.loads(step_row["request_json"] or "{}")
    frozen = list(request.get("input_artifact_ids") or [])
    types = _artifact_types(service, frozen)
    return next((r for r in frozen if types.get(r) == "corpus_spans"), None)


def _require_frozen_spans(service, step_run_id, source_span_ids):
    """校验 CorrectionRequest 的 span：非空、格式合法、且存在于本运行冻结 corpus_spans。"""
    step_row = service.get_step_run(step_run_id)
    if step_row is None:
        raise MissingReference("StepRun 不存在: %s" % step_run_id, code="REF_001")
    if not source_span_ids:
        raise SchemaViolation("source_span_ids 不能为空", code="SCH_002")
    for sid in source_span_ids:
        ids.validate("source_span_id", sid)
    spans_rev = _spans_revision_of_frozen(service, step_row)
    spans = _spans_by_id(_read_doc(service, spans_rev)) if spans_rev else {}
    unknown = [sid for sid in source_span_ids if sid not in spans]
    if unknown:
        raise ReviewRefused(
            "source_span_ids 不在本运行冻结 corpus_spans: %s" % unknown, code="REF_001"
        )


def request_correction(
    service, step_run_id, resume_token, *, source_span_ids, description
):
    """记一条 CorrectionRequest（``human_event``）+ Checkpoint（D-10）。

    复用 K2 已验收的 ``step.request_correction``（ACT 06 落于 ``step.py``），
    并补上 ACT 08 契约要求的前置：span 必须存在于本运行冻结 ``corpus_spans``。
    本函数在拒绝路径上零写入。
    """
    source_span_ids = list(source_span_ids)
    _require_frozen_spans(service, step_run_id, source_span_ids)
    return step.request_correction(
        service,
        step_run_id,
        resume_token,
        source_span_ids=source_span_ids,
        description=description,
    )


def _normalized_object(source_object, spans_by_id):
    """按 ``spans`` 文本长度把证据的 ``start_offset/end_offset`` 规范化为 ``start/end``。

    与 ``step.close_review`` 落 Gate 时的口径一致（既有代码约定，不改）。
    """
    obj = copy.deepcopy(source_object)
    for ev in obj.get("evidence", []):
        if "start" in ev and "end" in ev:
            continue
        span = spans_by_id.get(ev.get("source_span_id"), {})
        text_len = len(span.get("text", ""))
        span_start = span.get("start_offset", 0)
        s_off = ev.get("start_offset", 0)
        e_off = ev.get("end_offset", s_off)
        if 0 <= s_off < e_off <= text_len:
            start, end = s_off, e_off
        elif (
            span_start > 0
            and 0 <= (s_off - span_start) < (e_off - span_start) <= text_len
        ):
            start, end = s_off - span_start, e_off - span_start
        else:
            start, end = 0, text_len
        ev["start"], ev["end"] = start, end
    return obj


def _candidate_objects(candidate_set_doc, candidate_set_revision_id, spans_by_id):
    """从 ``candidate_set`` 构造对象清单（逐对象修订号统一为 ``candidate_set`` 修订，D-05）。"""
    objects = []
    for a in candidate_set_doc.get("assertions", []) or []:
        objects.append(
            {
                "entity_id": a["assertion_id"],
                "kind": "assertion",
                "source_object": _normalized_object(a, spans_by_id),
                "candidate_revision_id": candidate_set_revision_id,
            }
        )
    for v in candidate_set_doc.get("school_views", []) or []:
        objects.append(
            {
                "entity_id": v["school_view_id"],
                "kind": "school_view",
                "source_object": _normalized_object(v, spans_by_id),
                "candidate_revision_id": candidate_set_revision_id,
            }
        )
    return objects


def run_rework_propagation(
    service,
    edition_part_id: str,
    *,
    correction_request_revision_id: str,
    new_corpus_package_revision_id: str,
) -> dict:
    """执行 §14.1 精确失效传播：封存 ``ReworkImpactReport``，不产 StagePackage（D-14）。

    失败对象清单不作为参数（§14.1:643）：可达集合完全由新旧 corpus 差异与引用闭包推出。
    """
    # ---- begin 前解析（零写入）----
    old_review_step_run_id = latest_succeeded_step_run(service, edition_part_id, "m6")
    if old_review_step_run_id is None:
        raise ReviewRefused("无 succeeded 的 M6 首审运行，无法失效传播", code="REF_001")
    old_step = service.get_step_run(old_review_step_run_id)
    old_result = json.loads(old_step["result_json"] or "{}")
    old_outputs = list(old_result.get("output_artifact_ids") or [])
    old_output_types = _artifact_types(service, old_outputs)
    reviewed_edition_revs = [
        r for r in old_outputs if old_output_types.get(r) == "reviewed_edition"
    ]
    if len(reviewed_edition_revs) != 1:
        raise ReviewRefused("首审运行的 reviewed_edition 输出数不为 1", code="REF_001")
    reviewed_edition_rev = reviewed_edition_revs[0]
    reviewed_edition = _read_doc(service, reviewed_edition_rev) or {}

    old_request = json.loads(old_step["request_json"] or "{}")
    old_frozen = list(old_request.get("input_artifact_ids") or [])
    old_frozen_types = _artifact_types(service, old_frozen)

    def _pick(artifact_type):
        revs = [r for r in old_frozen if old_frozen_types.get(r) == artifact_type]
        if len(revs) != 1:
            raise ReviewRefused(
                "首审冻结输入 %s 数量不为 1" % artifact_type, code="REF_001"
            )
        return revs[0]

    old_corpus_package_rev = _pick("corpus_package")
    old_spans_rev = _pick("corpus_spans")
    old_candidate_package_rev = _pick("candidate_package")
    old_candidate_set_rev = _pick("candidate_set")
    old_validation_package_rev = _pick("validation_package")
    old_gate_results_rev = _pick("gate_results")

    old_spans_by_id = _spans_by_id(_read_doc(service, old_spans_rev))
    old_candidate_set_doc = _read_doc(service, old_candidate_set_rev) or {}

    # CorrectionRequest 必须 sealed、human_event、event_kind 正确且属首审包
    cr_row = service.get_revision(correction_request_revision_id)
    if cr_row is None:
        raise MissingReference(
            "CorrectionRequest 修订不存在: %s" % correction_request_revision_id,
            code="REF_001",
        )
    if cr_row["status"] != "sealed":
        raise NotConsumable(
            "CorrectionRequest 修订未 sealed: %s（当前 %s）"
            % (correction_request_revision_id, cr_row["status"])
        )
    if (
        _artifact_types(service, [correction_request_revision_id]).get(
            correction_request_revision_id
        )
        != "human_event"
    ):
        raise ReviewRefused("CorrectionRequest 必须是 human_event", code="REF_001")
    cr_doc = _read_doc(service, correction_request_revision_id) or {}
    if cr_doc.get("event_kind") != "correction_request":
        raise ReviewRefused("修订 event_kind 不是 correction_request", code="REF_001")
    if correction_request_revision_id not in (
        reviewed_edition.get("correction_request_revision_ids") or []
    ):
        raise ReviewRefused("CorrectionRequest 不属于首审 reviewed_edition", code="REF_001")

    # 新 corpus_package：sealed、由 succeeded m3 运行产出、且不同于旧包
    new_row = service.get_revision(new_corpus_package_revision_id)
    if new_row is None:
        raise MissingReference(
            "new_corpus_package 修订不存在: %s" % new_corpus_package_revision_id,
            code="REF_001",
        )
    if new_row["status"] != "sealed":
        raise NotConsumable(
            "new_corpus_package 修订未 sealed: %s（当前 %s）"
            % (new_corpus_package_revision_id, new_row["status"])
        )
    if (
        _artifact_types(service, [new_corpus_package_revision_id]).get(
            new_corpus_package_revision_id
        )
        != "corpus_package"
    ):
        raise ReviewRefused("new_corpus_package 必须是 corpus_package", code="REF_001")
    new_step = (
        service.get_step_run(new_row["step_run_id"]) if new_row.get("step_run_id") else None
    )
    if (
        new_step is None
        or new_step["stage"] != "m3"
        or new_step["status"] != "succeeded"
    ):
        raise ReviewRefused(
            "new_corpus_package 非由 succeeded m3 StepRun 产出", code="REF_001"
        )
    if new_corpus_package_revision_id == old_corpus_package_rev:
        raise ReviewRefused("new_corpus_package 与旧 corpus_package 相同", code="REF_001")
    new_corpus_package_doc = _read_doc(service, new_corpus_package_revision_id) or {}
    new_spans_rev = new_corpus_package_doc.get("spans_revision_id")
    if not new_spans_rev:
        raise ReviewRefused("new_corpus_package 缺 spans_revision_id", code="REF_001")

    rework_round_before = sum(
        1
        for cp in service.list_checkpoints(edition_part_id, "m6")
        if (cp.get("content") or {}).get("rework_impact_report_revision_id")
    )

    processing_run_id = old_step["processing_run_id"]

    # ---- 1) 运行配置 ----
    config_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical_json(
            {
                "stage": "m6",
                "task": "rework_propagation",
                "tool": M6_TOOL,
                "tool_version": M6_TOOL_VERSION,
                "threshold_ratio": 0.30,
                "threshold_round": 3,
            }
        ),
        producer_module=M6_TOOL,
        producer_version=M6_TOOL_VERSION,
    )[1]

    # ---- 2) 冻结输入 + supersede 首审运行（D-14 单线链）----
    old_decision_revs = [
        d["decision_revision_id"] for d in reviewed_edition.get("decisions", []) or []
    ]
    frozen = []
    for rev in (
        [reviewed_edition_rev]
        + old_decision_revs
        + [
            old_corpus_package_rev,
            old_spans_rev,
            old_candidate_package_rev,
            old_candidate_set_rev,
        ]
        + [new_corpus_package_revision_id, new_spans_rev, correction_request_revision_id]
    ):
        if rev and rev not in frozen:
            frozen.append(rev)

    new_step_run_id = ids.new_id("step_run_id")
    step_run_id = service.supersede_step_run(
        old_review_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": new_step_run_id,
            "input_artifact_ids": frozen,
            "technique_profile_id": old_request.get("technique_profile_id"),
            "configuration_artifact_id": config_revision_id,
        },
    )

    # ---- begin 之后：异常一律失败封存 ----
    try:
        new_spans_by_id = _spans_by_id(_read_doc(service, new_spans_rev))
        diff = propagation.changed_span_ids(
            {"spans": old_spans_by_id}, {"spans": new_spans_by_id}
        )
        affected = set(diff["changed"]) | set(diff["removed"])
        unchanged = [sid for sid in cr_doc["source_span_ids"] if sid not in affected]
        if unchanged:
            return _fail(
                service,
                step_run_id,
                "correction_scope",
                "CorrectionRequest 列出的 span 在新旧语料中未变化: %s" % unchanged,
            )

        old_candidates = _candidate_objects(
            old_candidate_set_doc, old_candidate_set_rev, old_spans_by_id
        )

        # ---- 4) 精确失效传播（不传对象清单；复用已验收 propagation.py）----
        report = propagation.propagate(
            old_candidates=old_candidates,
            old_spans_doc={"spans": old_spans_by_id},
            new_spans_doc={"spans": new_spans_by_id},
            validation_entries=[],
            standing_decisions=list(reviewed_edition.get("decisions", []) or []),
            rework_round_before=rework_round_before,
            trigger_correction_request_revision_id=correction_request_revision_id,
        )

        # ---- 5) D-08 推荐 B：不改 M4 修订状态；失效只登记进报告 ----
        # ---- 6) 封存 ReworkImpactReport / 校验报告 / 日志 ----
        _, report_rev = service.put_artifact(
            step_run_id,
            "rework_impact_report",
            canonical_json(report),
            producer_module=M6_TOOL,
            producer_version=M6_TOOL_VERSION,
        )
        service.seal_revision(report_rev)

        _, validation_report_rev = service.put_artifact(
            step_run_id,
            "validation_report",
            canonical_json(
                {
                    "gate_profile": "m6_rework_v1",
                    "checks": {"correction_scope": {"passed": True}},
                    "warnings": report["warnings"],
                }
            ),
            producer_module=M6_TOOL,
            producer_version=M6_TOOL_VERSION,
        )
        service.seal_revision(validation_report_rev)

        log_lines = [
            "rework_propagation round=%d" % report["rework_round"],
            "changed_span_ids=%s" % ",".join(report["changed_span_ids"]),
            "invalidated=%d carried_forward=%d needs_review=%d"
            % (
                report["invalidated_count"],
                report["carried_forward_count"],
                report["needs_review_count"],
            ),
        ]
        _, log_rev = service.put_artifact(
            step_run_id,
            "step_log",
            "\n".join(log_lines).encode("utf-8"),
            producer_module=M6_TOOL,
            producer_version=M6_TOOL_VERSION,
        )
        service.seal_revision(log_rev)

        # ---- 7) Checkpoint：引用报告，待复核项进 pending ----
        carried_decision_revs = [
            c["revision_id"] for c in report["carried_forward"] if c["kind"] == "decision"
        ]
        human_decisions = carried_decision_revs + [correction_request_revision_id]
        pending_queue = [{"task_id": n["queue_item_id"]} for n in report["needs_review"]]
        next_pointer = pending_queue[0] if pending_queue else None
        checkpoint_revision_id = service.write_checkpoint(
            step_run_id,
            edition_part_id=edition_part_id,
            stage="m6",
            completed_tasks=[
                {
                    "task_id": "rework_propagation",
                    "artifact_revision_id": report_rev,
                    "status": "succeeded",
                    "terminal_state": None,
                }
            ],
            human_decisions=human_decisions,
            pending_queue=pending_queue,
            next_pointer=next_pointer,
            rework_impact_report_revision_id=report_rev,
        )

        # ---- 8) Transformation ----
        transformation_id = service.record_transformation(
            step_run_id,
            operation="propagate_invalidation",
            tool=M6_TOOL,
            tool_version=M6_TOOL_VERSION,
            configuration_revision_id=config_revision_id,
            input_revision_ids=frozen,
            output_revision_ids=[report_rev],
            validation_report_revision_id=validation_report_rev,
            human_event_revision_ids=[correction_request_revision_id],
        )

        # ---- 9) finish（不产 StagePackage，D-14）----
        version = service.get_step_run(step_run_id)["status_version"]
        service.finish_step_run(
            step_run_id,
            {
                "schema_version": "1.0.0",
                "processing_run_id": processing_run_id,
                "step_run_id": step_run_id,
                "status_version": version + 1,
                "status": "succeeded",
                "output_artifact_ids": [report_rev],
                "validation_report_ids": [validation_report_rev],
                "log_artifact_ids": [log_rev],
                "failure_artifact_ids": [],
            },
        )
    except Exception as exc:
        return _fail(service, step_run_id, "internal", "%s: %s" % (type(exc).__name__, exc))

    return {
        "status": "succeeded",
        "step_run_id": step_run_id,
        "supersedes_step_run_id": old_review_step_run_id,
        "rework_impact_report_revision_id": report_rev,
        "invalidated": report["invalidated"],
        "carried_forward": report["carried_forward"],
        "needs_review": report["needs_review"],
        "warnings": report["warnings"],
        "counts": {
            "invalidated": report["invalidated_count"],
            "carried_forward": report["carried_forward_count"],
            "needs_review": report["needs_review_count"],
        },
        "checkpoint_revision_id": checkpoint_revision_id,
        "transformation_id": transformation_id,
    }
