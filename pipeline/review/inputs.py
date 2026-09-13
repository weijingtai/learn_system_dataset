import json
import yaml

from pipeline.knowledge_extraction.inputs import resolve_m3_outputs
from pipeline.ledger.errors import MissingReference, NotConsumable
from pipeline.review.errors import ReviewRefused


def _read_bytes(reader, sha256):
    read = getattr(reader, "read_object", None)
    if read is not None:
        return read(sha256)
    return reader.objects.get(sha256)


def _read_doc(reader, revision_id):
    row = reader.get_revision(revision_id)
    if row is None:
        return None
    raw = _read_bytes(reader, row["sha256"])
    if raw is None:
        return None
    text = raw.decode("utf-8")
    try:
        return json.loads(text)
    except ValueError:
        return yaml.safe_load(text)


def _artifact_types(reader, revision_ids):
    revision_ids = [rev for rev in revision_ids if rev]
    if not revision_ids:
        return {}
    placeholders = ",".join("?" * len(revision_ids))
    rows = reader.store.conn.execute(
        "SELECT r.artifact_revision_id, a.artifact_type FROM artifact_revisions r "
        "JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "WHERE r.artifact_revision_id IN (%s)" % placeholders,
        tuple(revision_ids),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def latest_succeeded_step_run(reader, edition_part_id, stage):
    rows = reader.store.conn.execute(
        "SELECT DISTINCT c.step_run_id, c.created_at, c.rowid FROM stage_checkpoints c "
        "JOIN step_runs r ON r.step_run_id = c.step_run_id "
        "WHERE c.edition_part_id=? AND c.stage=? AND r.status='succeeded' "
        "ORDER BY c.created_at DESC, c.rowid DESC",
        (edition_part_id, stage),
    ).fetchall()
    return rows[0][0] if rows else None


def resolve_m6_inputs(reader, edition_part_id: str) -> dict:
    # 检查 M6 是否已封存
    m6_step_run_id = latest_succeeded_step_run(reader, edition_part_id, "m6")
    if m6_step_run_id is not None:
        raise ReviewRefused("M6 已封存: StepRun 已 succeeded", code="REF_001")

    # 复用 resolve_m3_outputs 取 m3
    m3 = resolve_m3_outputs(reader, edition_part_id)
    m3_step_run_id = m3["m3_step_run_id"]
    processing_run_id = m3["processing_run_id"]
    technique_id = m3["technique_id"]
    corpus_stage_package_revision_id = m3["corpus_stage_package_revision_id"]
    corpus_package_revision_id = m3["corpus_package_revision_id"]
    spans_revision_id = m3["spans_revision_id"]

    # M4
    m4_step_run_id = latest_succeeded_step_run(reader, edition_part_id, "m4")
    if m4_step_run_id is None:
        raise ReviewRefused("M4 未就绪: 无 succeeded StepRun", code="REF_001")

    m4_step = reader.get_step_run(m4_step_run_id)
    if m4_step is None or m4_step["status"] != "succeeded":
        raise ReviewRefused(f"M4 StepRun 非 succeeded: {m4_step_run_id}", code="REF_001")

    m4_result = json.loads(m4_step["result_json"] or "{}")
    m4_outputs = list(m4_result.get("output_artifact_ids") or [])
    m4_types = _artifact_types(reader, m4_outputs)

    candidate_package_revs = [r for r in m4_outputs if m4_types.get(r) == "candidate_package"]
    candidate_set_revs = [r for r in m4_outputs if m4_types.get(r) == "candidate_set"]
    if len(candidate_package_revs) != 1 or len(candidate_set_revs) != 1:
        raise ReviewRefused(
            "M4 输出形状不符（candidate_package 与 candidate_set 必须各 1 个）",
            code="REF_001",
        )

    candidate_package_revision_id = candidate_package_revs[0]
    candidate_set_revision_id = candidate_set_revs[0]

    candidate_pkg_doc = _read_doc(reader, candidate_package_revision_id)
    if candidate_pkg_doc is None:
        raise MissingReference(
            f"candidate_package 修订不存在: {candidate_package_revision_id}",
            code="REF_001",
        )

    if (
        candidate_pkg_doc.get("corpus_stage_package_revision_id") != corpus_stage_package_revision_id
        or candidate_pkg_doc.get("spans_revision_id") != spans_revision_id
    ):
        raise ReviewRefused(
            "candidate_package 未正确绑定 M3 的 corpus_stage_package 或 spans",
            code="REF_001",
        )

    # M5
    m5_step_run_id = latest_succeeded_step_run(reader, edition_part_id, "m5")
    if m5_step_run_id is None:
        raise ReviewRefused("M5 未就绪: 无 succeeded StepRun", code="REF_001")

    m5_step = reader.get_step_run(m5_step_run_id)
    if m5_step is None or m5_step["status"] != "succeeded":
        raise ReviewRefused(f"M5 StepRun 非 succeeded: {m5_step_run_id}", code="REF_001")

    m5_result = json.loads(m5_step["result_json"] or "{}")
    m5_outputs = list(m5_result.get("output_artifact_ids") or [])
    m5_types = _artifact_types(reader, m5_outputs)

    val_package_revs = [r for r in m5_outputs if m5_types.get(r) == "validation_package"]
    gate_results_revs = [r for r in m5_outputs if m5_types.get(r) == "gate_results"]
    if len(val_package_revs) != 1 or len(gate_results_revs) != 1:
        raise ReviewRefused(
            "M5 输出形状不符（validation_package 与 gate_results 必须各 1 个）",
            code="REF_001",
        )

    validation_package_revision_id = val_package_revs[0]
    gate_results_revision_id = gate_results_revs[0]

    val_pkg_doc = _read_doc(reader, validation_package_revision_id)
    if val_pkg_doc is None:
        raise MissingReference(
            f"validation_package 修订不存在: {validation_package_revision_id}",
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

    # 经 stage_packages 只读 SELECT 取 m5 StagePackage
    m5_sp_rows = reader.store.conn.execute(
        "SELECT sp.stage_package_id, r.artifact_revision_id FROM stage_packages sp "
        "JOIN artifact_revisions r ON r.artifact_id = sp.artifact_id "
        "JOIN step_runs sr ON sr.step_run_id = r.step_run_id "
        "WHERE sp.stage='m5' AND r.step_run_id=? AND sr.status='succeeded'",
        (m5_step_run_id,),
    ).fetchall()
    if not m5_sp_rows:
        raise ReviewRefused("未找到 M5 StagePackage 记录", code="REF_001")

    m5_stage_package_doc = _read_doc(reader, m5_sp_rows[0][1])
    if (
        not isinstance(m5_stage_package_doc, dict)
        or m5_stage_package_doc.get("validation", {}).get("passed") is not True
    ):
        raise ReviewRefused("M5 StagePackage validation.passed 非 true", code="REF_001")

    # candidate_objects
    candidate_set_doc = _read_doc(reader, candidate_set_revision_id)
    if candidate_set_doc is None:
        raise MissingReference(
            f"candidate_set 修订不存在: {candidate_set_revision_id}",
            code="REF_001",
        )

    assertions = candidate_set_doc.get("assertions") or []
    school_views = candidate_set_doc.get("school_views") or []
    candidate_objects = [
        {"entity_id": a["assertion_id"], "kind": "assertion", "source_object": a}
        for a in assertions
    ] + [
        {"entity_id": v["school_view_id"], "kind": "school_view", "source_object": v}
        for v in school_views
    ]

    # 所有引用修订状态必须为 "sealed"
    required_sealed = [
        corpus_package_revision_id,
        spans_revision_id,
        corpus_stage_package_revision_id,
        candidate_package_revision_id,
        candidate_set_revision_id,
        validation_package_revision_id,
        gate_results_revision_id,
    ]
    for rev_id in required_sealed:
        rev_row = reader.get_revision(rev_id)
        if rev_row is None:
            raise MissingReference(f"引用修订不存在: {rev_id}", code="REF_001")
        if rev_row["status"] != "sealed":
            raise NotConsumable(f"引用修订未 sealed: {rev_id}（当前 {rev_row['status']}）")

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
