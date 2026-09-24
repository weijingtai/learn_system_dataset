"""M6 返工链：CorrectionRequest 与精确失效传播（§14.1、§17.1）。

本模块**不改 M4 修订状态**（G7-RULINGS 第 62 条 / D-08 推荐 B）：失效以
``ReworkImpactReport.invalidated[]`` 逐对象登记；旧 ``candidate_set`` 的物理替换由
M4' 重跑经 ``supersede_revision`` 完成（ACT 09）。
"""

import copy
import json

from pipeline.knowledge_extraction import review_events
from pipeline.knowledge_extraction.serialize import canonical_json
from pipeline.ledger import ids
from pipeline.ledger.errors import MissingReference, NotConsumable, SchemaViolation
from pipeline.ledger.states import REVIEW_DECISION_TYPES
from pipeline.review import M6_TOOL, M6_TOOL_VERSION, model, propagation, step
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
    """按 ``spans`` 把证据的 ``start_offset/end_offset`` 规范化为 ``start/end``（委托给 model.normalize_candidate_object，单一权威）。"""
    return model.normalize_candidate_object(source_object, spans_by_id)


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


def _resolve_rerun_inputs(service, edition_part_id: str) -> dict:
    """复审输入解析：与 ``resolve_m6_inputs`` 同一规则，但**跳过**「M6 已封存」拒绝。

    ``inputs.py`` 不在本 ACT 写范围内，故在此按其规则复刻只读解析（零写入）。
    唯一差别：m3 输出按「最近 succeeded 运行」解析（修正语料会取代旧 m3 运行，
    ``resolve_m3_outputs`` 要求 m3 StagePackage 恰 1 条，不适用于重跑链）。
    """
    m3_step_run_id = latest_succeeded_step_run(service, edition_part_id, "m3")
    if m3_step_run_id is None:
        raise ReviewRefused("M3 未就绪: 无 succeeded StepRun", code="REF_001")
    m3_step = service.get_step_run(m3_step_run_id)
    m3_outputs = list(
        json.loads(m3_step["result_json"] or "{}").get("output_artifact_ids") or []
    )
    m3_types = _artifact_types(service, m3_outputs)

    def _m3_pick(kind):
        revs = [r for r in m3_outputs if m3_types.get(r) == kind]
        if len(revs) != 1:
            raise ReviewRefused("M3 输出 %s 数量不为 1" % kind, code="REF_001")
        return revs[0]

    corpus_stage_package_revision_id = _m3_pick("stage_package")
    corpus_package_revision_id = _m3_pick("corpus_package")
    spans_revision_id = _m3_pick("corpus_spans")
    processing_run_id = m3_step["processing_run_id"]
    technique_id = json.loads(m3_step["request_json"] or "{}").get(
        "technique_profile_id"
    )

    m4_step_run_id = latest_succeeded_step_run(service, edition_part_id, "m4")
    if m4_step_run_id is None:
        raise ReviewRefused("M4 未就绪: 无 succeeded StepRun", code="REF_001")
    m4_step = service.get_step_run(m4_step_run_id)
    if m4_step is None or m4_step["status"] != "succeeded":
        raise ReviewRefused("M4 StepRun 非 succeeded: %s" % m4_step_run_id, code="REF_001")
    m4_outputs = list(
        json.loads(m4_step["result_json"] or "{}").get("output_artifact_ids") or []
    )
    m4_types = _artifact_types(service, m4_outputs)
    candidate_package_revs = [r for r in m4_outputs if m4_types.get(r) == "candidate_package"]
    candidate_set_revs = [r for r in m4_outputs if m4_types.get(r) == "candidate_set"]
    if len(candidate_package_revs) != 1 or len(candidate_set_revs) != 1:
        raise ReviewRefused(
            "M4 输出形状不符（candidate_package 与 candidate_set 必须各 1 个）",
            code="REF_001",
        )
    candidate_package_revision_id = candidate_package_revs[0]
    candidate_set_revision_id = candidate_set_revs[0]
    candidate_pkg_doc = _read_doc(service, candidate_package_revision_id)
    if candidate_pkg_doc is None:
        raise MissingReference(
            "candidate_package 修订不存在: %s" % candidate_package_revision_id,
            code="REF_001",
        )
    if (
        candidate_pkg_doc.get("corpus_stage_package_revision_id")
        != corpus_stage_package_revision_id
        or candidate_pkg_doc.get("spans_revision_id") != spans_revision_id
    ):
        raise ReviewRefused(
            "candidate_package 未正确绑定 M3 的 corpus_stage_package 或 spans",
            code="REF_001",
        )

    m5_step_run_id = latest_succeeded_step_run(service, edition_part_id, "m5")
    if m5_step_run_id is None:
        raise ReviewRefused("M5 未就绪: 无 succeeded StepRun", code="REF_001")
    m5_step = service.get_step_run(m5_step_run_id)
    if m5_step is None or m5_step["status"] != "succeeded":
        raise ReviewRefused("M5 StepRun 非 succeeded: %s" % m5_step_run_id, code="REF_001")
    m5_outputs = list(
        json.loads(m5_step["result_json"] or "{}").get("output_artifact_ids") or []
    )
    m5_types = _artifact_types(service, m5_outputs)
    val_package_revs = [r for r in m5_outputs if m5_types.get(r) == "validation_package"]
    gate_results_revs = [r for r in m5_outputs if m5_types.get(r) == "gate_results"]
    if len(val_package_revs) != 1 or len(gate_results_revs) != 1:
        raise ReviewRefused(
            "M5 输出形状不符（validation_package 与 gate_results 必须各 1 个）",
            code="REF_001",
        )
    validation_package_revision_id = val_package_revs[0]
    gate_results_revision_id = gate_results_revs[0]
    val_pkg_doc = _read_doc(service, validation_package_revision_id)
    if val_pkg_doc is None:
        raise MissingReference(
            "validation_package 修订不存在: %s" % validation_package_revision_id,
            code="REF_001",
        )
    if (
        val_pkg_doc.get("gate", {}).get("passed") is not True
        or val_pkg_doc.get("scope") != "corpus_only"
    ):
        raise ReviewRefused(
            "M5 validation_package gate.passed 非 True 或 scope 非 corpus_only",
            code="REF_001",
        )

    # 经端口列 m5 StagePackage：原查询按 stage='m5' + 该 StepRun + succeeded 取第一行修订
    m5_sp_rows = [
        row
        for row in service.list_stage_packages("m5")
        if row["step_run_id"] == m5_step_run_id and row["step_run_status"] == "succeeded"
    ]
    if not m5_sp_rows:
        raise ReviewRefused("未找到 M5 StagePackage 记录", code="REF_001")
    m5_stage_package_doc = _read_doc(service, m5_sp_rows[0]["artifact_revision_id"])
    if (
        not isinstance(m5_stage_package_doc, dict)
        or m5_stage_package_doc.get("validation", {}).get("passed") is not True
    ):
        raise ReviewRefused("M5 StagePackage validation.passed 非 true", code="REF_001")

    candidate_set_doc = _read_doc(service, candidate_set_revision_id)
    if candidate_set_doc is None:
        raise MissingReference(
            "candidate_set 修订不存在: %s" % candidate_set_revision_id, code="REF_001"
        )
    candidate_objects = [
        {"entity_id": a["assertion_id"], "kind": "assertion", "source_object": a}
        for a in candidate_set_doc.get("assertions") or []
    ] + [
        {"entity_id": v["school_view_id"], "kind": "school_view", "source_object": v}
        for v in candidate_set_doc.get("school_views") or []
    ]

    for rev_id in (
        corpus_package_revision_id,
        spans_revision_id,
        corpus_stage_package_revision_id,
        candidate_package_revision_id,
        candidate_set_revision_id,
        validation_package_revision_id,
        gate_results_revision_id,
    ):
        row = service.get_revision(rev_id)
        if row is None:
            raise MissingReference("引用修订不存在: %s" % rev_id, code="REF_001")
        if row["status"] != "sealed":
            raise NotConsumable(
                "引用修订未 sealed: %s（当前 %s）" % (rev_id, row["status"])
            )

    return {
        "processing_run_id": processing_run_id,
        "technique_id": technique_id,
        "edition_part_id": edition_part_id,
        "corpus_package_revision_id": corpus_package_revision_id,
        "spans_revision_id": spans_revision_id,
        "corpus_stage_package_revision_id": corpus_stage_package_revision_id,
        "candidate_package_revision_id": candidate_package_revision_id,
        "candidate_set_revision_id": candidate_set_revision_id,
        "candidate_objects": candidate_objects,
        "validation_package_revision_id": validation_package_revision_id,
        "gate_results_revision_id": gate_results_revision_id,
        "validation_package": val_pkg_doc,
        "m3_step_run_id": m3_step_run_id,
        "m4_step_run_id": m4_step_run_id,
        "m5_step_run_id": m5_step_run_id,
    }


def open_rework_review(
    service,
    edition_part_id: str,
    *,
    rework_impact_report_revision_id: str,
    acknowledge_rework_warning: bool = False,
) -> dict:
    """复审只重放待复核项：新队列、继承决定不重做、阈值告警需显式确认（§14.1:640-645）。"""
    # ---- 前置（零写入）----
    report_row = service.get_revision(rework_impact_report_revision_id)
    if report_row is None:
        raise MissingReference(
            "ReworkImpactReport 修订不存在: %s" % rework_impact_report_revision_id,
            code="REF_001",
        )
    if report_row["status"] != "sealed":
        raise NotConsumable(
            "ReworkImpactReport 未 sealed: %s" % rework_impact_report_revision_id
        )
    latest = service.latest_checkpoint(edition_part_id, "m6")
    if (
        latest is None
        or latest["content"].get("rework_impact_report_revision_id")
        != rework_impact_report_revision_id
    ):
        raise ReviewRefused(
            "报告不是本分卷最新 m6 Checkpoint 所引用", code="REF_001"
        )
    propagation_step_run_id = latest["step_run_id"]
    propagation_step = service.get_step_run(propagation_step_run_id)
    if propagation_step is None or propagation_step["status"] != "succeeded":
        raise ReviewRefused(
            "最新 m6 Checkpoint 所属运行非 succeeded: %s" % propagation_step_run_id,
            code="REF_001",
        )
    propagation_request = json.loads(propagation_step["request_json"] or "{}")
    propagation_config = (
        _read_doc(service, propagation_request.get("configuration_artifact_id")) or {}
    )
    if propagation_config.get("task") != "rework_propagation":
        raise ReviewRefused(
            "最新 m6 Checkpoint 所属运行 task 非 rework_propagation", code="REF_001"
        )

    report = _read_doc(service, rework_impact_report_revision_id) or {}
    warnings = list(report.get("warnings") or [])
    if warnings and acknowledge_rework_warning is not True:
        raise ReviewRefused(
            "rework_threshold_exceeded 需操作者确认: 请显式 acknowledge_rework_warning",
            code="REF_001",
        )

    inputs = _resolve_rerun_inputs(service, edition_part_id)
    processing_run_id = inputs["processing_run_id"]

    first_review_step = service.get_step_run(
        propagation_step.get("supersedes_step_run_id")
    )
    first_config = {}
    if first_review_step is not None:
        first_request = json.loads(first_review_step["request_json"] or "{}")
        first_config = (
            _read_doc(service, first_request.get("configuration_artifact_id")) or {}
        )
    required_decision_types = first_config.get("required_decision_types") or {
        obj["entity_id"]: list(
            review_events.required_decision_types(
                obj["source_object"], entity_kind=obj["kind"]
            )
        )
        for obj in inputs["candidate_objects"]
    }

    carried_revs = [
        c["revision_id"]
        for c in report.get("carried_forward", []) or []
        if c.get("kind") == "decision"
    ]
    needs_review_revs = [
        n["decision_revision_id"] for n in report.get("needs_review", []) or []
    ]

    config_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical_json(
            {
                "stage": "m6",
                "task": "review",
                "mode": "rework",
                "tool": M6_TOOL,
                "tool_version": M6_TOOL_VERSION,
                "required_decision_types": required_decision_types,
                "verdicts": list(review_events.VERDICTS),
                "console": "cli",
            }
        ),
        producer_module=M6_TOOL,
        producer_version=M6_TOOL_VERSION,
    )[1]

    frozen = [
        inputs["corpus_stage_package_revision_id"],
        inputs["corpus_package_revision_id"],
        inputs["spans_revision_id"],
        inputs["candidate_package_revision_id"],
        inputs["candidate_set_revision_id"],
        inputs["validation_package_revision_id"],
        inputs["gate_results_revision_id"],
    ]
    for rev in [rework_impact_report_revision_id] + carried_revs + needs_review_revs:
        if rev and rev not in frozen:
            frozen.append(rev)

    step_run_id = service.supersede_step_run(
        propagation_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": ids.new_id("step_run_id"),
            "input_artifact_ids": frozen,
            "technique_profile_id": inputs["technique_id"],
            "configuration_artifact_id": config_revision_id,
        },
    )

    try:
        kind_by_entity = {
            obj["entity_id"]: obj["kind"] for obj in inputs["candidate_objects"]
        }
        entity_order = {
            obj["entity_id"]: idx
            for idx, obj in enumerate(inputs["candidate_objects"])
        }
        type_order = {
            name: idx for idx, name in enumerate(REVIEW_DECISION_TYPES)
        }
        queue = []
        for item in report.get("needs_review", []) or []:
            qid = item["queue_item_id"]
            entity_id, _, decision_type = qid.partition("#")
            queue.append(
                {
                    "queue_item_id": qid,
                    "target_entity_id": entity_id,
                    "kind": kind_by_entity.get(entity_id),
                    "decision_type": decision_type,
                    "seen_artifact_revision_id": inputs["candidate_set_revision_id"],
                }
            )
        # 按候选对象顺序 × §8.2 决定类型顺序（与首审队列同构）
        queue.sort(
            key=lambda it: (
                entity_order.get(it["target_entity_id"], len(entity_order)),
                type_order.get(it["decision_type"], len(type_order)),
            )
        )
        queue_bytes = json.dumps(queue, sort_keys=True, ensure_ascii=False).encode(
            "utf-8"
        )
        _, queue_revision_id = service.put_artifact(
            step_run_id,
            "review_queue",
            queue_bytes,
            producer_module=M6_TOOL,
            producer_version=M6_TOOL_VERSION,
        )
        service.seal_revision(queue_revision_id)

        completed_tasks = [
            {
                "task_id": "build_review_queue",
                "artifact_revision_id": queue_revision_id,
                "status": "succeeded",
                "terminal_state": None,
            }
        ]
        pending_queue = [{"task_id": item["queue_item_id"]} for item in queue]
        next_pointer = pending_queue[0] if pending_queue else None
        checkpoint_revision_id = service.write_checkpoint(
            step_run_id,
            edition_part_id=edition_part_id,
            stage="m6",
            completed_tasks=completed_tasks,
            human_decisions=list(carried_revs),
            pending_queue=pending_queue,
            next_pointer=next_pointer,
            rework_impact_report_revision_id=rework_impact_report_revision_id,
        )

        resume_token = service.await_human(step_run_id, [queue_revision_id])

        acknowledgement_revision_id = None
        if warnings:
            ack_doc = {
                "schema_version": "0.1.0-draft",
                "event_kind": "rework_threshold_ack",
                "stage": "m6",
                "step_run_id": step_run_id,
                "rework_impact_report_revision_id": rework_impact_report_revision_id,
                "warnings": warnings,
                "actor_ref": service.actor(),
            }
            _, ack_rev = service.put_artifact(
                step_run_id,
                "human_event",
                canonical_json(ack_doc),
                producer_module=M6_TOOL,
                producer_version=M6_TOOL_VERSION,
            )
            service.seal_revision(ack_rev)
            service.record_human_event(
                step_run_id, resume_token, ack_rev, decision_type=None
            )
            acknowledgement_revision_id = ack_rev
            checkpoint_revision_id = service.write_checkpoint(
                step_run_id,
                edition_part_id=edition_part_id,
                stage="m6",
                completed_tasks=completed_tasks,
                human_decisions=list(carried_revs) + [ack_rev],
                pending_queue=pending_queue,
                next_pointer=next_pointer,
                rework_impact_report_revision_id=rework_impact_report_revision_id,
            )
    except Exception as exc:
        return _fail(service, step_run_id, "internal", "%s: %s" % (type(exc).__name__, exc))

    return {
        "status": "awaiting_human",
        "processing_run_id": processing_run_id,
        "step_run_id": step_run_id,
        "resume_token": resume_token,
        "configuration_revision_id": config_revision_id,
        "frozen_input_revision_ids": frozen,
        "queue_revision_id": queue_revision_id,
        "queue": queue,
        "checkpoint_revision_id": checkpoint_revision_id,
        "rework_impact_report_revision_id": rework_impact_report_revision_id,
        "carried_decision_revision_ids": carried_revs,
        "acknowledgement_revision_id": acknowledgement_revision_id,
    }
