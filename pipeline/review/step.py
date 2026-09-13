import copy
import hashlib
import json
import yaml

from pipeline.knowledge_extraction import review_events
from pipeline.knowledge_extraction.serialize import canonical_json
from pipeline.ledger import ids
from pipeline.ledger.errors import MissingReference, SchemaViolation
from pipeline.review import M6_TOOL, M6_TOOL_VERSION, gate, model
from pipeline.review.errors import ReviewRefused
from pipeline.review.inputs import _read_doc, latest_succeeded_step_run, resolve_m6_inputs


def _read_bytes(reader, sha256):
    read = getattr(reader, "read_object", None)
    if read is not None:
        return read(sha256)
    return reader.objects.get(sha256)


def _fail(service, step_run_id, check, detail):
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
    service.fail_step_run(step_run_id, [failure_rev], f"M6 {check}: {detail}")
    return {
        "status": "failed",
        "step_run_id": step_run_id,
        "failed_check": check,
        "failure_revision_id": failure_rev,
        "reason": detail,
    }


def open_review(service, edition_part_id: str, *, required_decision_types=None) -> dict:
    inputs = resolve_m6_inputs(service, edition_part_id)
    processing_run_id = inputs["processing_run_id"]
    technique_id = inputs["technique_id"]

    if required_decision_types is None:
        req_types_by_entity = {
            obj["entity_id"]: list(
                review_events.required_decision_types(
                    obj["source_object"], entity_kind=obj["kind"]
                )
            )
            for obj in inputs["candidate_objects"]
        }
    else:
        req_types_by_entity = dict(required_decision_types)

    config_dict = {
        "stage": "m6",
        "task": "review",
        "tool": M6_TOOL,
        "tool_version": M6_TOOL_VERSION,
        "required_decision_types": req_types_by_entity,
        "verdicts": list(review_events.VERDICTS),
        "console": "cli",
    }
    _, config_rev_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical_json(config_dict),
        producer_module=M6_TOOL,
        producer_version=M6_TOOL_VERSION,
    )

    frozen_input_revision_ids = [
        inputs["corpus_stage_package_revision_id"],
        inputs["corpus_package_revision_id"],
        inputs["spans_revision_id"],
        inputs["candidate_package_revision_id"],
        inputs["candidate_set_revision_id"],
        inputs["validation_package_revision_id"],
        inputs["gate_results_revision_id"],
    ]

    step_run_id = ids.new_id("step_run_id")
    service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "input_artifact_ids": frozen_input_revision_ids,
            "technique_profile_id": technique_id,
            "configuration_artifact_id": config_rev_id,
        }
    )

    # 校验输入契约（input_contract）
    try:
        spans_doc = _read_doc(service, inputs["spans_revision_id"]) or {}
        raw_spans = spans_doc.get("spans")
        if isinstance(raw_spans, list):
            spans_dict = {s["span_id"]: s for s in raw_spans if isinstance(s, dict) and "span_id" in s}
        elif isinstance(raw_spans, dict):
            spans_dict = raw_spans
        else:
            spans_dict = {}
        cand_set_doc = _read_doc(service, inputs["candidate_set_revision_id"]) or {}
        cand_pkg_doc = _read_doc(service, inputs["candidate_package_revision_id"]) or {}

        if cand_pkg_doc.get("candidate_set_revision_id") != inputs["candidate_set_revision_id"]:
            raise ValueError("candidate_package 与 candidate_set 修订号不一致")

        for c in inputs["candidate_objects"]:
            source_obj = c["source_object"]
            for ev in source_obj.get("evidence", []):
                span_id = ev.get("source_span_id")
                if span_id not in spans_dict:
                    raise ValueError(f"Span {span_id} 不在 corpus_spans 中")
                span = spans_dict[span_id]
                text = span.get("text", "")
                start = ev.get("start_offset") if "start_offset" in ev else ev.get("start", 0)
                end = ev.get("end_offset") if "end_offset" in ev else ev.get("end", len(text))
                quote = ev.get("quote", text[start:end])
                if hashlib.sha256(quote.encode("utf-8")).hexdigest() != ev.get("quote_sha256"):
                    raise ValueError(f"quote_sha256 与截取引文不一致: {quote}")

        queue = model.build_review_queue(
            candidates=inputs["candidate_objects"],
            seen_revision_id=inputs["candidate_set_revision_id"],
        )
        queue_bytes = json.dumps(queue, sort_keys=True, ensure_ascii=False).encode("utf-8")
        _, queue_revision_id = service.put_artifact(
            step_run_id,
            "review_queue",
            queue_bytes,
            producer_module=M6_TOOL,
            producer_version=M6_TOOL_VERSION,
        )
        service.seal_revision(queue_revision_id)

        pending_queue = [{"task_id": item["queue_item_id"]} for item in queue]
        next_pointer = pending_queue[0] if pending_queue else None
        checkpoint_revision_id = service.write_checkpoint(
            step_run_id,
            edition_part_id=edition_part_id,
            stage="m6",
            completed_tasks=[
                {
                    "task_id": "build_review_queue",
                    "artifact_revision_id": queue_revision_id,
                    "status": "succeeded",
                    "terminal_state": None,
                }
            ],
            human_decisions=[],
            pending_queue=pending_queue,
            next_pointer=next_pointer,
        )

        resume_token = service.await_human(step_run_id, [queue_revision_id])
    except Exception as exc:
        return _fail(service, step_run_id, "input_contract", str(exc))

    return {
        "status": "awaiting_human",
        "processing_run_id": processing_run_id,
        "step_run_id": step_run_id,
        "resume_token": resume_token,
        "configuration_revision_id": config_rev_id,
        "frozen_input_revision_ids": frozen_input_revision_ids,
        "queue_revision_id": queue_revision_id,
        "queue": queue,
        "checkpoint_revision_id": checkpoint_revision_id,
    }


def record_decision(
    service,
    step_run_id: str,
    resume_token: str,
    *,
    queue_item_id: str,
    verdict: str,
    rationale: str,
    modified_content=None,
    evidence_refs=(),
) -> dict:
    step = service.get_step_run(step_run_id)
    if step is None:
        raise MissingReference(f"StepRun 不存在: {step_run_id}", code="REF_001")
    if step["status"] != "awaiting_human":
        raise ReviewRefused(f"StepRun {step_run_id} 状态非 awaiting_human: {step['status']}", code="REF_001")

    # 预校验 resume_token（零写入）
    if hasattr(service, "_check_token"):
        service._check_token(step, resume_token)

    # 查 edition_part_id
    cp_row = service.store.conn.execute(
        "SELECT edition_part_id FROM stage_checkpoints WHERE step_run_id=? ORDER BY rowid DESC LIMIT 1",
        (step_run_id,),
    ).fetchone()
    edition_part_id = cp_row[0] if cp_row else None

    # 读取本运行的 review_queue
    queue_row = service.store.conn.execute(
        "SELECT r.artifact_revision_id FROM artifact_revisions r "
        "JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "WHERE a.artifact_type = 'review_queue' AND r.step_run_id = ?",
        (step_run_id,),
    ).fetchone()
    if not queue_row:
        # Check input artifacts if recovered
        queue_row = service.store.conn.execute(
            "SELECT r.artifact_revision_id FROM frozen_inputs f "
            "JOIN artifact_revisions r ON r.artifact_revision_id = f.artifact_revision_id "
            "JOIN artifacts a ON a.artifact_id = r.artifact_id "
            "WHERE a.artifact_type = 'review_queue' AND f.step_run_id = ?",
            (step_run_id,),
        ).fetchone()

    if not queue_row:
        raise ReviewRefused("找不到本运行的 review_queue 修订", code="REF_001")
    queue_revision_id = queue_row[0]
    queue = _read_doc(service, queue_revision_id) or []

    queue_item = None
    for item in queue:
        if item["queue_item_id"] == queue_item_id:
            queue_item = item
            break
    if queue_item is None:
        raise ReviewRefused(f"queue_item_id {queue_item_id} 不在队列中", code="REF_001")

    if not rationale:
        raise SchemaViolation("Rationale 必须非空", code="SCH_002")
    if verdict not in review_events.VERDICTS:
        raise SchemaViolation(f"非法 verdict: {verdict}", code="SCH_002")

    # 校验 resume_token（若错误抛出异常，零写入）
    # service.record_human_event 会在写入事务内校验 token，如果 token 错误会抛出异常

    modified_revision_id = None
    if verdict == "modify":
        if not isinstance(modified_content, dict):
            raise ReviewRefused("modify 必须提供 modified_content 字典", code="SCH_002")
        # 查找原候选对象
        cand_set_rev = queue_item["seen_artifact_revision_id"]
        cand_set = _read_doc(service, cand_set_rev) or {}
        orig_obj = None
        target_eid = queue_item["target_entity_id"]
        for a in cand_set.get("assertions", []):
            if a.get("assertion_id") == target_eid:
                orig_obj = a
                break
        if orig_obj is None:
            for v in cand_set.get("school_views", []):
                if v.get("school_view_id") == target_eid:
                    orig_obj = v
                    break
        if orig_obj is None:
            raise ReviewRefused(f"原候选对象未找到: {target_eid}", code="REF_001")

        new_obj = dict(orig_obj)
        new_obj.update(modified_content)
        reviewed_cand_bytes = json.dumps(new_obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
        _, modified_revision_id = service.put_artifact(
            step_run_id,
            "reviewed_candidate",
            reviewed_cand_bytes,
            producer_module=M6_TOOL,
            producer_version=M6_TOOL_VERSION,
        )
        service.seal_revision(modified_revision_id)

    event = model.decision_event(
        queue_item=queue_item,
        seen_artifact_revision_id=queue_item["seen_artifact_revision_id"],
        processing_run_id=step["processing_run_id"],
        step_run_id=step_run_id,
        verdict=verdict,
        rationale=rationale,
        actor_ref=service.actor(),
        evidence_refs=tuple(evidence_refs),
    )
    event_bytes = model.event_bytes(event)
    _, event_rev = service.put_artifact(
        step_run_id,
        "human_event",
        event_bytes,
        producer_module=M6_TOOL,
        producer_version=M6_TOOL_VERSION,
    )
    service.seal_revision(event_rev)

    # 写入人机交互事件，校验 token
    service.record_human_event(
        step_run_id,
        resume_token,
        event_rev,
        decision_type=queue_item["decision_type"],
    )

    # 汇总本运行及继承的所有 human_events
    prior_checkpoint = service.latest_checkpoint(edition_part_id, "m6") if edition_part_id else None
    inherited_decisions = []
    if prior_checkpoint and prior_checkpoint["step_run_id"] != step_run_id:
        inherited_decisions = list(prior_checkpoint["content"].get("human_decisions", []))

    cur_events = service.store.conn.execute(
        "SELECT event_revision_id FROM human_events WHERE step_run_id=? AND decision_type IS NOT NULL ORDER BY rowid ASC",
        (step_run_id,),
    ).fetchall()
    cur_decision_revs = [r[0] for r in cur_events]

    all_decision_revs = list(inherited_decisions)
    for rev in cur_decision_revs:
        if rev not in all_decision_revs:
            all_decision_revs.append(rev)

    # Map target_entity_id -> modified_candidate_revision_id
    mod_by_eid = {}
    mod_rows = service.store.conn.execute(
        "SELECT r.artifact_revision_id FROM artifacts a "
        "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
        "WHERE a.artifact_type = 'reviewed_candidate' AND r.step_run_id = ?",
        (step_run_id,),
    ).fetchall()
    for m_row in mod_rows:
        m_doc = _read_doc(service, m_row[0])
        if m_doc:
            m_eid = m_doc.get("assertion_id") or m_doc.get("school_view_id")
            if m_eid:
                mod_by_eid[m_eid] = m_row[0]

    # 重建 decision_entry
    entries = []
    for d_rev in all_decision_revs:
        ev_doc = _read_doc(service, d_rev)
        if not ev_doc or ev_doc.get("event_kind") != "review_decision":
            continue
        ev_qid = model.queue_item_id(ev_doc["target"]["entity_id"], ev_doc["decision_type"])
        ev_qitem = next((it for it in queue if it["queue_item_id"] == ev_qid), None)
        if not ev_qitem:
            continue
        # 查找是否有 modified_candidate
        mod_rev = None
        if ev_doc.get("verdict") == "modify":
            mod_rev = modified_revision_id if d_rev == event_rev else mod_by_eid.get(ev_qitem["target_entity_id"])
        entry = model.decision_entry(
            decision_revision_id=d_rev,
            queue_item=ev_qitem,
            event=ev_doc,
            standing="active",
            modified_revision_id=mod_rev,
        )
        entries.append(entry)

    folded = model.fold_decisions(queue, entries)

    completed_tasks = [
        {
            "task_id": "build_review_queue",
            "artifact_revision_id": queue_revision_id,
            "status": "succeeded",
            "terminal_state": None,
        }
    ]
    for it in queue:
        qid = it["queue_item_id"]
        if folded.get(qid) is not None:
            completed_tasks.append(
                {
                    "task_id": f"m6_review_{it['target_entity_id']}_{it['decision_type']}",
                    "artifact_revision_id": folded[qid]["decision_revision_id"],
                    "status": "succeeded",
                    "terminal_state": None,
                }
            )

    pending = [
        it["queue_item_id"]
        for it in queue
        if folded.get(it["queue_item_id"]) is None
        or folded[it["queue_item_id"]]["verdict"] == "request_evidence"
    ]
    next_pointer = {"task_id": pending[0]} if pending else None

    checkpoint_revision_id = service.write_checkpoint(
        step_run_id,
        edition_part_id=edition_part_id,
        stage="m6",
        completed_tasks=completed_tasks,
        human_decisions=all_decision_revs,
        pending_queue=[{"task_id": qid} for qid in pending],
        next_pointer=next_pointer,
    )

    return {
        "decision_revision_id": event_rev,
        "modified_revision_id": modified_revision_id,
        "checkpoint_revision_id": checkpoint_revision_id,
        "remaining": len(pending),
    }


def recover_review(service, edition_part_id: str, *, reason: str) -> dict:
    old_checkpoint = service.latest_checkpoint(edition_part_id, "m6")
    if old_checkpoint is None:
        raise MissingReference(f"没有可恢复的 M6 StageCheckpoint: {edition_part_id}", code="REF_001")

    old_step_run_id = old_checkpoint["step_run_id"]
    old_step = service.get_step_run(old_step_run_id)
    if old_step is None:
        raise MissingReference(f"StepRun 不存在: {old_step_run_id}", code="REF_001")
    if old_step["status"] in ("succeeded", "failed", "superseded"):
        raise ReviewRefused(f"StepRun {old_step_run_id} 已处于终态: {old_step['status']}", code="REF_001")

    old_req = json.loads(old_step["request_json"] or "{}")

    # 获取 old queue revision
    old_queue_rev = old_checkpoint["content"]["completed_tasks"][0]["artifact_revision_id"]

    # 获取旧运行全部 sealed human_event（包括 correction_request，用于冻结输入）
    old_events = service.store.conn.execute(
        "SELECT event_revision_id, decision_type FROM human_events WHERE step_run_id=? ORDER BY rowid ASC",
        (old_step_run_id,),
    ).fetchall()
    old_event_revs = [r[0] for r in old_events]
    old_decision_revs = [r[0] for r in old_events if r[1] is not None]

    old_frozen = list(old_req.get("input_artifact_ids") or [])
    new_frozen = []
    for r in old_frozen + [old_queue_rev] + old_event_revs:
        if r not in new_frozen:
            new_frozen.append(r)

    new_step_run_id = ids.new_id("step_run_id")
    new_request = {
        "schema_version": "1.0.0",
        "processing_run_id": old_step["processing_run_id"],
        "step_run_id": new_step_run_id,
        "input_artifact_ids": new_frozen,
        "technique_profile_id": old_req.get("technique_profile_id"),
        "configuration_artifact_id": old_req.get("configuration_artifact_id"),
    }

    new_step_id, plan = service.recover_from_checkpoint(
        edition_part_id, "m6", new_request, step_run_id=new_step_run_id
    )

    queue = _read_doc(service, old_queue_rev) or []
    entries = []
    mod_by_eid = {}
    mod_rows = service.store.conn.execute(
        "SELECT r.artifact_revision_id FROM artifacts a "
        "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
        "WHERE a.artifact_type = 'reviewed_candidate' AND r.step_run_id = ?",
        (old_step_run_id,),
    ).fetchall()
    for m_row in mod_rows:
        m_doc = _read_doc(service, m_row[0])
        if m_doc:
            m_eid = m_doc.get("assertion_id") or m_doc.get("school_view_id")
            if m_eid:
                mod_by_eid[m_eid] = m_row[0]

    for d_rev in old_decision_revs:
        ev_doc = _read_doc(service, d_rev)
        if not ev_doc or ev_doc.get("event_kind") != "review_decision":
            continue
        ev_qid = model.queue_item_id(ev_doc["target"]["entity_id"], ev_doc["decision_type"])
        ev_qitem = next((it for it in queue if it["queue_item_id"] == ev_qid), None)
        if not ev_qitem:
            continue
        mod_rev = None
        if ev_doc.get("verdict") == "modify":
            mod_rev = mod_by_eid.get(ev_qitem["target_entity_id"])
        entry = model.decision_entry(
            decision_revision_id=d_rev,
            queue_item=ev_qitem,
            event=ev_doc,
            standing="active",
            modified_revision_id=mod_rev,
        )
        entries.append(entry)

    folded = model.fold_decisions(queue, entries)

    completed_tasks = [
        {
            "task_id": "build_review_queue",
            "artifact_revision_id": old_queue_rev,
            "status": "succeeded",
            "terminal_state": None,
        }
    ]
    for it in queue:
        qid = it["queue_item_id"]
        if folded.get(qid) is not None:
            completed_tasks.append(
                {
                    "task_id": f"m6_review_{it['target_entity_id']}_{it['decision_type']}",
                    "artifact_revision_id": folded[qid]["decision_revision_id"],
                    "status": "succeeded",
                    "terminal_state": None,
                }
            )

    pending = [
        it["queue_item_id"]
        for it in queue
        if folded.get(it["queue_item_id"]) is None
        or folded[it["queue_item_id"]]["verdict"] == "request_evidence"
    ]
    next_pointer = {"task_id": pending[0]} if pending else None

    checkpoint_revision_id = service.write_checkpoint(
        new_step_id,
        edition_part_id=edition_part_id,
        stage="m6",
        completed_tasks=completed_tasks,
        human_decisions=old_event_revs,
        pending_queue=[{"task_id": qid} for qid in pending],
        next_pointer=next_pointer,
    )

    token = service.await_human(new_step_id, [old_queue_rev])

    return {
        "step_run_id": new_step_id,
        "supersedes_step_run_id": old_step_run_id,
        "resume_token": token,
        "carried_decision_revision_ids": old_event_revs,
        "replayed_pending": pending,
        "checkpoint_revision_id": checkpoint_revision_id,
    }


def _artifact_ref(service, revision_id):
    row = service.store.conn.execute(
        "SELECT a.artifact_id, a.artifact_type FROM artifacts a "
        "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
        "WHERE r.artifact_revision_id=?",
        (revision_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Revision {revision_id} not found")
    artifact_id, artifact_type = row[0], row[1]
    if artifact_type == "stage_package":
        package_row = service.store.conn.execute(
            "SELECT sp.stage_package_id FROM stage_packages sp "
            "JOIN artifact_revisions r ON r.artifact_id = sp.artifact_id "
            "WHERE r.artifact_revision_id=?",
            (revision_id,),
        ).fetchone()
        return {
            "schema_version": "1.0.0",
            "artifact_kind": "stage_package",
            "stage_package_id": package_row[0],
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


def request_correction(
    service,
    step_run_id: str,
    resume_token: str,
    *,
    source_span_ids: list[str],
    description: str,
) -> dict:
    step = service.get_step_run(step_run_id)
    if step is None:
        raise MissingReference(f"StepRun 不存在: {step_run_id}", code="REF_001")
    if step["status"] != "awaiting_human":
        raise ReviewRefused(f"StepRun {step_run_id} 状态非 awaiting_human: {step['status']}", code="REF_001")
    if hasattr(service, "_check_token"):
        service._check_token(step, resume_token)
    if not source_span_ids:
        raise SchemaViolation("source_span_ids 不能为空", code="SCH_002")
    if not description or not description.strip():
        raise SchemaViolation("description 不能为空", code="SCH_002")

    for sid in source_span_ids:
        ids.validate("source_span_id", sid)

    cp_row = service.store.conn.execute(
        "SELECT edition_part_id FROM stage_checkpoints WHERE step_run_id=? ORDER BY rowid DESC LIMIT 1",
        (step_run_id,),
    ).fetchone()
    edition_part_id = cp_row[0] if cp_row else None

    event_doc = {
        "schema_version": "0.1.0-draft",
        "event_kind": "correction_request",
        "stage": "m6",
        "step_run_id": step_run_id,
        "source_span_ids": list(source_span_ids),
        "description": description,
        "target_stage": "m2",
        "actor_ref": service.actor(),
    }
    event_bytes = canonical_json(event_doc)
    _, event_rev = service.put_artifact(
        step_run_id,
        "human_event",
        event_bytes,
        producer_module=M6_TOOL,
        producer_version=M6_TOOL_VERSION,
    )
    service.seal_revision(event_rev)

    service.record_human_event(
        step_run_id,
        resume_token,
        event_rev,
        decision_type=None,
    )

    last_cp = service.latest_checkpoint(edition_part_id, "m6") if edition_part_id else None
    if last_cp:
        completed_tasks = list(last_cp["content"].get("completed_tasks", []))
        human_decisions = list(last_cp["content"].get("human_decisions", []))
        pending_queue = list(last_cp["content"].get("pending_queue", []))
        next_pointer = last_cp["content"].get("next_pointer")
    else:
        completed_tasks = []
        human_decisions = []
        pending_queue = []
        next_pointer = None

    human_decisions.append(event_rev)
    checkpoint_revision_id = service.write_checkpoint(
        step_run_id,
        edition_part_id=edition_part_id,
        stage="m6",
        completed_tasks=completed_tasks,
        human_decisions=human_decisions,
        pending_queue=pending_queue,
        next_pointer=next_pointer,
    )
    return {
        "correction_request_revision_id": event_rev,
        "checkpoint_revision_id": checkpoint_revision_id,
    }


def close_review(service, step_run_id: str, resume_token: str) -> dict:
    step = service.get_step_run(step_run_id)
    if step is None:
        raise MissingReference(f"StepRun 不存在: {step_run_id}", code="REF_001")
    if step["status"] != "awaiting_human":
        raise ReviewRefused(f"StepRun {step_run_id} 状态非 awaiting_human: {step['status']}", code="REF_001")
    if hasattr(service, "_check_token"):
        service._check_token(step, resume_token)

    cp_row = service.store.conn.execute(
        "SELECT edition_part_id FROM stage_checkpoints WHERE step_run_id=? ORDER BY rowid DESC LIMIT 1",
        (step_run_id,),
    ).fetchone()
    edition_part_id = cp_row[0] if cp_row else None

    # 读取本运行的 review_queue
    queue_row = service.store.conn.execute(
        "SELECT r.artifact_revision_id FROM artifact_revisions r "
        "JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "WHERE a.artifact_type = 'review_queue' AND r.step_run_id = ?",
        (step_run_id,),
    ).fetchone()
    if not queue_row:
        queue_row = service.store.conn.execute(
            "SELECT r.artifact_revision_id FROM frozen_inputs f "
            "JOIN artifact_revisions r ON r.artifact_revision_id = f.artifact_revision_id "
            "JOIN artifacts a ON a.artifact_id = r.artifact_id "
            "WHERE a.artifact_type = 'review_queue' AND f.step_run_id = ?",
            (step_run_id,),
        ).fetchone()
    if not queue_row:
        raise ReviewRefused("找不到本运行的 review_queue 修订", code="REF_001")
    queue_rev = queue_row[0]
    queue = _read_doc(service, queue_rev) or []

    # 查 candidate_set 与 spans
    req = json.loads(step["request_json"] or "{}")
    frozen = list(req.get("input_artifact_ids") or [])
    config_rev = req.get("configuration_artifact_id")
    config_doc = _read_doc(service, config_rev) or {}
    required_decision_types = config_doc.get("required_decision_types") or {}

    types_map = {}
    if frozen:
        placeholders = ",".join("?" * len(frozen))
        t_rows = service.store.conn.execute(
            "SELECT r.artifact_revision_id, a.artifact_type FROM artifact_revisions r "
            "JOIN artifacts a ON a.artifact_id = r.artifact_id "
            "WHERE r.artifact_revision_id IN (%s)" % placeholders,
            tuple(frozen),
        ).fetchall()
        types_map = {r[0]: r[1] for r in t_rows}

    cand_set_rev = next((r for r in frozen if types_map.get(r) == "candidate_set"), None)
    spans_rev = next((r for r in frozen if types_map.get(r) == "corpus_spans"), None)
    corpus_package_rev = next((r for r in frozen if types_map.get(r) == "corpus_package"), None)
    candidate_package_rev = next((r for r in frozen if types_map.get(r) == "candidate_package"), None)
    validation_package_rev = next((r for r in frozen if types_map.get(r) == "validation_package"), None)

    cand_set_doc = _read_doc(service, cand_set_rev) or {}
    spans_doc = _read_doc(service, spans_rev) or {}
    raw_spans = spans_doc.get("spans")
    if isinstance(raw_spans, list):
        spans_dict = {s["span_id"]: s for s in raw_spans if isinstance(s, dict) and "span_id" in s}
    elif isinstance(raw_spans, dict):
        spans_dict = raw_spans
    else:
        spans_dict = {}

    cand_objects = [
        {"entity_id": a["assertion_id"], "kind": "assertion", "source_object": a}
        for a in cand_set_doc.get("assertions", [])
    ] + [
        {
            "entity_id": v["school_view_id"],
            "kind": "school_view",
            "source_object": v,
            "conflict_group_id": v.get("conflict_group_id"),
        }
        for v in cand_set_doc.get("school_views", [])
    ]
    cand_by_id = {c["entity_id"]: c for c in cand_objects}

    # 查本运行已封存 reviewed_candidate
    mod_by_eid = {}
    mod_rows = service.store.conn.execute(
        "SELECT r.artifact_revision_id FROM artifacts a "
        "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
        "WHERE a.artifact_type = 'reviewed_candidate' AND r.step_run_id = ?",
        (step_run_id,),
    ).fetchall()
    for m_row in mod_rows:
        m_doc = _read_doc(service, m_row[0])
        if m_doc:
            m_eid = m_doc.get("assertion_id") or m_doc.get("school_view_id")
            if m_eid:
                mod_by_eid[m_eid] = m_row[0]

    # 读取所有 human_events
    cur_events = service.store.conn.execute(
        "SELECT event_revision_id, decision_type FROM human_events WHERE step_run_id=? ORDER BY rowid ASC",
        (step_run_id,),
    ).fetchall()
    decision_revs = [r[0] for r in cur_events if r[1] is not None]

    # 收集全部 correction_requests（按记录顺序：冻结输入中及本运行中）
    correction_revs = []
    for r in frozen:
        if types_map.get(r) == "human_event":
            f_doc = _read_doc(service, r)
            if f_doc and f_doc.get("event_kind") == "correction_request" and r not in correction_revs:
                correction_revs.append(r)
    for r in cur_events:
        if r[1] is None:
            c_doc = _read_doc(service, r[0])
            if c_doc and c_doc.get("event_kind") == "correction_request" and r[0] not in correction_revs:
                correction_revs.append(r[0])

    entries = []
    for d_rev in decision_revs:
        ev_doc = _read_doc(service, d_rev)
        if not ev_doc or ev_doc.get("event_kind") != "review_decision":
            continue
        ev_qid = model.queue_item_id(ev_doc["target"]["entity_id"], ev_doc["decision_type"])
        ev_qitem = next((it for it in queue if it["queue_item_id"] == ev_qid), None)
        if not ev_qitem:
            continue
        mod_rev = mod_by_eid.get(ev_qitem["target_entity_id"]) if ev_doc.get("verdict") == "modify" else None
        entry = model.decision_entry(
            decision_revision_id=d_rev,
            queue_item=ev_qitem,
            event=ev_doc,
            standing="active",
            modified_revision_id=mod_rev,
        )
        entries.append(entry)

    folded = model.fold_decisions(queue, entries)
    outcome = model.outcome(queue, folded)
    if outcome["unresolved"]:
        raise ReviewRefused(f"未解决项 {len(outcome['unresolved'])}: {outcome['unresolved']}", code="REF_001")

    # 1. service.resume
    service.resume(step_run_id, resume_token)

    try:
        # 2. 构造 reviewed_edition
        approved = []
        for c in cand_objects:
            eid = c["entity_id"]
            if eid in outcome["approved"]:
                art_rev = mod_by_eid.get(eid, cand_set_rev)
                d_revs = [
                    folded[qid]["decision_revision_id"]
                    for qid, ent in folded.items()
                    if ent and ent["target_entity_id"] == eid
                ]
                approved.append({
                    "entity_id": eid,
                    "kind": c["kind"],
                    "artifact_revision_id": art_rev,
                    "content_status": "expert_verified",
                    "decision_revision_ids": d_revs,
                })

        rejected = []
        for c in cand_objects:
            eid = c["entity_id"]
            if eid in outcome["rejected"]:
                d_revs = [
                    folded[qid]["decision_revision_id"]
                    for qid, ent in folded.items()
                    if ent and ent["target_entity_id"] == eid
                ]
                rejected.append({
                    "entity_id": eid,
                    "kind": c["kind"],
                    "artifact_revision_id": cand_set_rev,
                    "content_status": c["source_object"].get("content_status", "machine_extracted"),
                    "decision_revision_ids": d_revs,
                })

        decisions = []
        for q_item in queue:
            qid = q_item["queue_item_id"]
            ent = folded[qid]
            decisions.append({
                "decision_revision_id": ent["decision_revision_id"],
                "queue_item_id": qid,
                "target_entity_id": ent["target_entity_id"],
                "seen_artifact_revision_id": ent["seen_revision_id"],
                "current_target_revision_id": ent.get("modified_revision_id") or ent.get("carried_to_revision_id") or ent["seen_revision_id"],
                "modified_revision_id": ent.get("modified_revision_id"),
                "decision_type": ent["decision_type"],
                "verdict": ent["verdict"],
                "standing": ent["standing"],
                "carried_from_revision_id": ent.get("carried_from_revision_id"),
                "carried_to_revision_id": ent.get("carried_to_revision_id"),
                "trigger_correction_request_id": None,
            })

        evidence_links = []
        for app in approved:
            eid = app["entity_id"]
            c = cand_by_id[eid]
            src_obj = c["source_object"]
            if eid in mod_by_eid:
                mod_doc = _read_doc(service, mod_by_eid[eid])
                if mod_doc:
                    src_obj = mod_doc
            for ev in src_obj.get("evidence", []):
                span_id = ev.get("source_span_id")
                if span_id in spans_dict:
                    span = spans_dict[span_id]
                    text = span.get("text", "")
                    text_len = len(text)
                    span_start = span.get("start_offset", 0)
                    if "start" in ev and "end" in ev:
                        start, end = ev["start"], ev["end"]
                    elif "start_offset" in ev and "end_offset" in ev:
                        s_off = ev["start_offset"]
                        e_off = ev["end_offset"]
                        if 0 <= s_off < e_off <= text_len:
                            start, end = s_off, e_off
                        elif span_start > 0 and 0 <= (s_off - span_start) < (e_off - span_start) <= text_len:
                            start, end = s_off - span_start, e_off - span_start
                        else:
                            start, end = 0, text_len
                    else:
                        start, end = 0, text_len
                    quote = text[start:end]
                    q_hash = hashlib.sha256(quote.encode("utf-8")).hexdigest()
                    evidence_links.append({
                        "entity_id": eid,
                        "source_span_id": span_id,
                        "start": start,
                        "end": end,
                        "quote_sha256": q_hash,
                        "corpus_spans_revision_id": spans_rev,
                    })

        school_views = []
        for app in approved:
            if app["kind"] == "school_view":
                c = cand_by_id[app["entity_id"]]
                src_obj = c["source_object"]
                school_views.append({
                    "school_view_id": app["entity_id"],
                    "entity_id": app["entity_id"],
                    "school_id": src_obj.get("school_id"),
                    "subject_entity_id": src_obj.get("subject_entity_id"),
                    "conflict_group_id": src_obj.get("conflict_group_id"),
                    "changes_current_judgment": src_obj.get("changes_current_judgment", False),
                })

        reviewed_edition = {
            "approved": approved,
            "rejected": rejected,
            "decisions": decisions,
            "evidence_links": evidence_links,
            "school_views": school_views,
            "correction_request_revision_ids": correction_revs,
            "rework_impact_report_revision_id": None,
            "unresolved_count": 0,
        }

        # 3. Gate
        cand_for_gate = []
        for obj in cand_objects:
            obj_copy = copy.deepcopy(obj)
            for ev in obj_copy["source_object"].get("evidence", []):
                span_id = ev.get("source_span_id")
                span = spans_dict.get(span_id, {})
                text_len = len(span.get("text", ""))
                span_start = span.get("start_offset", 0)
                if "start" not in ev and "start_offset" in ev:
                    s_off = ev["start_offset"]
                    e_off = ev.get("end_offset", s_off)
                    if 0 <= s_off < e_off <= text_len:
                        ev["start"], ev["end"] = s_off, e_off
                    elif span_start > 0 and 0 <= (s_off - span_start) < (e_off - span_start) <= text_len:
                        ev["start"], ev["end"] = s_off - span_start, e_off - span_start
                    else:
                        ev["start"], ev["end"] = 0, text_len
            cand_for_gate.append({
                **obj_copy,
                "required_decision_types": required_decision_types.get(obj["entity_id"], ["review_source_fidelity"]),
                "content_hash": model.content_hash(obj_copy, spans_dict),
            })

        val_pkg_doc = _read_doc(service, validation_package_rev) or {}
        reviewed_edition_for_gate = {
            **reviewed_edition,
            "rejected": [x["entity_id"] if isinstance(x, dict) else x for x in reviewed_edition.get("rejected", [])],
        }
        gate_report = gate.evaluate_review(
            candidate_objects=cand_for_gate,
            seen_revision_id=cand_set_rev,
            validation_package=val_pkg_doc,
            corpus_spans_doc={"spans": spans_dict},
            decision_entries=list(folded.values()),
            prior_decision_events=(),
            reviewed_edition=reviewed_edition_for_gate,
        )

        val_report_doc = {
            "gate_profile": "m6_review_v1",
            "review": gate_report["review"],
            "checks": gate_report["checks"],
            "failed_checks": [k for k, v in gate_report["checks"].items() if not v["passed"]],
        }
        _, val_report_rev = service.put_artifact(
            step_run_id,
            "validation_report",
            canonical_json(val_report_doc),
            producer_module=M6_TOOL,
            producer_version=M6_TOOL_VERSION,
        )
        service.seal_revision(val_report_rev)

        log_lines = ["evaluate_review review=%s" % gate_report["review"]] + [
            "check %s: passed=%s" % (k, v["passed"]) for k, v in gate_report["checks"].items()
        ]
        _, log_rev = service.put_artifact(
            step_run_id,
            "step_log",
            "\n".join(log_lines).encode("utf-8"),
            producer_module=M6_TOOL,
            producer_version=M6_TOOL_VERSION,
        )
        service.seal_revision(log_rev)

        if gate_report["review"] == "failed":
            failed_names = ",".join(val_report_doc["failed_checks"])
            return _fail(service, step_run_id, "review_gate", failed_names)

        # 4. put reviewed_edition and reviewed_edition_package
        reviewed_edition_bytes = canonical_json(reviewed_edition)
        _, edition_rev = service.put_artifact(
            step_run_id,
            "reviewed_edition",
            reviewed_edition_bytes,
            producer_module=M6_TOOL,
            producer_version=M6_TOOL_VERSION,
        )
        service.seal_revision(edition_rev)

        package_doc = {
            "schema_version": "1.0.0",
            "reviewed_edition_revision_id": edition_rev,
            "edition_part_id": edition_part_id,
            "counts": {
                "approved": len(reviewed_edition["approved"]),
                "rejected": len(reviewed_edition["rejected"]),
                "decisions": len(reviewed_edition["decisions"]),
            },
        }
        _, package_rev = service.put_artifact(
            step_run_id,
            "reviewed_edition_package",
            canonical_json(package_doc),
            producer_module=M6_TOOL,
            producer_version=M6_TOOL_VERSION,
        )
        service.seal_revision(package_rev)

        # 5. record_transformation
        all_human_event_revs = [r[0] for r in cur_events]
        trans_input_revs = frozen + [queue_rev] + list(mod_by_eid.values())
        transformation_id = service.record_transformation(
            step_run_id,
            operation="review_candidates",
            tool=M6_TOOL,
            tool_version=M6_TOOL_VERSION,
            configuration_revision_id=config_rev,
            input_revision_ids=trans_input_revs,
            output_revision_ids=[edition_rev, package_rev],
            validation_report_revision_id=val_report_rev,
            human_event_revision_ids=all_human_event_revs,
        )

        # 6. m6 StagePackage
        stage_package_id = ids.new_id("stage_package_id", stage="m6")
        package_revision_id = ids.new_id("artifact_revision_id")
        stage_package = {
            "schema_version": "1.0.0",
            "stage_package_id": stage_package_id,
            "artifact_revision_id": package_revision_id,
            "stage": "m6",
            "status": "sealed",
            "payload": {
                "reviewed_edition_revision_id": edition_rev,
                "decision_revision_ids": [d["decision_revision_id"] for d in reviewed_edition["decisions"]],
                "unresolved_count": 0,
            },
            "manifest": {
                "schema_version": "1.0.0",
                "processing_run_id": step["processing_run_id"],
                "step_run_id": step_run_id,
                "input_artifacts": [_artifact_ref(service, x) for x in frozen],
                "output_artifacts": [_artifact_ref(service, package_rev)],
                "counts": {
                    "approved": len(reviewed_edition["approved"]),
                    "rejected": len(reviewed_edition["rejected"]),
                    "decisions": len(reviewed_edition["decisions"]),
                    "correction_requests": len(reviewed_edition["correction_request_revision_ids"]),
                },
                "content_sha256": hashlib.sha256(reviewed_edition_bytes).hexdigest(),
            },
            "validation": {
                "passed": True,
                "report_artifacts": [_artifact_ref(service, val_report_rev)],
            },
            "lineage": {
                "upstream_artifacts": [
                    _artifact_ref(service, corpus_package_rev),
                    _artifact_ref(service, candidate_package_rev),
                    _artifact_ref(service, validation_package_rev),
                ],
                "transformations": [
                    {
                        "operation": "review_candidates",
                        "step_run_id": step_run_id,
                        "configuration_artifact_revision_id": config_rev,
                        "input_artifact_revision_ids": trans_input_revs,
                        "output_artifact_revision_ids": [edition_rev, package_rev],
                    }
                ],
            },
            "logs": [_artifact_ref(service, log_rev)],
            "failures": [],
        }
        service.register_stage_package(
            step_run_id,
            stage_package,
            canonical_json(stage_package),
            stage_package_id=stage_package_id,
            artifact_revision_id=package_revision_id,
        )
        service.seal_revision(package_revision_id)

        # 7. finish_step_run
        version = service.get_step_run(step_run_id)["status_version"]
        step_manifest_rev = service.finish_step_run(
            step_run_id,
            {
                "schema_version": "1.0.0",
                "processing_run_id": step["processing_run_id"],
                "step_run_id": step_run_id,
                "status_version": version + 1,
                "status": "succeeded",
                "output_artifact_ids": [
                    package_revision_id,
                    edition_rev,
                    package_rev,
                ],
                "validation_report_ids": [val_report_rev],
                "log_artifact_ids": [log_rev],
                "failure_artifact_ids": [],
            },
        )

        return {
            "status": "succeeded",
            "processing_run_id": step["processing_run_id"],
            "step_run_id": step_run_id,
            "reviewed_edition_revision_id": edition_rev,
            "reviewed_edition_package_revision_id": package_rev,
            "stage_package_id": stage_package_id,
            "package_revision_id": package_revision_id,
            "validation_report_revision_id": val_report_rev,
            "log_revision_id": log_rev,
            "transformation_id": transformation_id,
            "step_manifest_revision_id": step_manifest_rev,
            "approved": [x["entity_id"] for x in reviewed_edition["approved"]],
            "rejected": [x["entity_id"] for x in reviewed_edition["rejected"]],
            "gate": gate_report,
        }
    except Exception as exc:
        return _fail(service, step_run_id, "internal", str(exc))


def run_m6(service, edition_part_id: str, *, required_decision_types=None) -> dict:
    m6_step_id = latest_succeeded_step_run(service, edition_part_id, "m6")
    if m6_step_id is None:
        return open_review(service, edition_part_id, required_decision_types=required_decision_types)
    return {"status": "succeeded", "step_run_id": m6_step_id}

