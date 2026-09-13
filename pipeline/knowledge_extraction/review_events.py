"""审核决定事件契约 ``review_decision`` 与内容成熟度推导（纯函数）。

本模块不访问 Ledger、不读文件；**不建签发 StepRun**（签发归属 M6，D-07），也不产生任何
真实 ``expert_verified``。真实签发需由用户撰写决定表（P7 / README §9）。
"""

import copy

from pipeline.ledger import ids
from pipeline.ledger.errors import InvalidIdentifier, LedgerError, SchemaViolation
from pipeline.ledger.states import REVIEW_DECISION_TYPES

from . import CANDIDATE_SCHEMA_VERSION

# 审核决定 verdict 闭集（D-08）
VERDICTS = ("accept", "modify", "reject", "request_evidence", "school_dispute")
# entity_kind → pipeline.ledger.ids 家族名
ENTITY_KINDS = {
    "assertion": "assertion_id",
    "pattern": "pattern_id",
    "school_view": "school_view_id",
}
CONSUMPTION_LEVELS = ("INTERNAL_DEMO", "DEV_SEARCH", "PUBLIC_RELEASE")
REVIEW_STAGE = "m6"  # D-07：签发归属 M6

_TOP_KEYS = (
    "schema_version",
    "event_kind",
    "stage",
    "decision_type",
    "verdict",
    "target",
    "processing_run_id",
    "step_run_id",
    "actor_ref",
    "rationale",
    "evidence_refs",
    "consumption_level",
)
_TARGET_KEYS = ("entity_kind", "entity_id", "artifact_revision_id")


def build_review_decision(
    *,
    decision_type,
    verdict,
    entity_kind,
    entity_id,
    seen_artifact_revision_id,
    processing_run_id,
    step_run_id,
    actor_ref,
    rationale,
    evidence_refs=(),
    consumption_level="INTERNAL_DEMO",
):
    """构造一条 ``review_decision`` 事件；返回前先过 ``validate_review_decision``。"""
    doc = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "event_kind": "review_decision",
        "stage": REVIEW_STAGE,
        "decision_type": decision_type,
        "verdict": verdict,
        "target": {
            "entity_kind": entity_kind,
            "entity_id": entity_id,
            "artifact_revision_id": seen_artifact_revision_id,
        },
        "processing_run_id": processing_run_id,
        "step_run_id": step_run_id,
        "actor_ref": actor_ref,
        "rationale": rationale,
        "evidence_refs": list(evidence_refs),
        "consumption_level": consumption_level,
    }
    validate_review_decision(doc)
    return doc


def validate_review_decision(doc):
    """校验 ``review_decision`` 事件；返回深拷贝。"""
    if not isinstance(doc, dict):
        raise SchemaViolation("review_decision 必须是对象", code="SCH_001")
    keys = set(doc)
    extra = keys - set(_TOP_KEYS)
    if extra:
        raise SchemaViolation(
            "review_decision 含未知键: %s" % sorted(extra), code="SCH_002"
        )
    missing = [key for key in _TOP_KEYS if key not in keys]
    if missing:
        raise SchemaViolation(
            "review_decision 缺必填键: %s" % missing, code="SCH_001"
        )
    if doc["event_kind"] != "review_decision" or doc["stage"] != REVIEW_STAGE:
        raise SchemaViolation("event_kind/stage 不符", code="SCH_002")
    if doc["decision_type"] not in REVIEW_DECISION_TYPES:
        raise SchemaViolation(
            "decision_type 不在 §8.2 第 2 表: %r" % (doc["decision_type"],), code="SCH_002"
        )
    if doc["verdict"] not in VERDICTS:
        raise SchemaViolation("verdict 非闭集: %r" % (doc["verdict"],), code="SCH_002")

    target = doc["target"]
    if not isinstance(target, dict):
        raise SchemaViolation("target 必须是对象", code="SCH_001")
    target_extra = set(target) - set(_TARGET_KEYS)
    if target_extra:
        raise SchemaViolation(
            "target 含未知键: %s" % sorted(target_extra), code="SCH_002"
        )
    target_missing = [key for key in _TARGET_KEYS if key not in target]
    if target_missing:
        raise SchemaViolation("target 缺必填键: %s" % target_missing, code="SCH_001")
    entity_kind = target["entity_kind"]
    if entity_kind not in ENTITY_KINDS:
        raise SchemaViolation("entity_kind 非闭集: %r" % (entity_kind,), code="SCH_002")
    ids.validate(ENTITY_KINDS[entity_kind], target["entity_id"])  # ID_001
    ids.validate("artifact_revision_id", target["artifact_revision_id"])  # ID_001
    ids.validate("processing_run_id", doc["processing_run_id"])  # ID_001
    ids.validate("step_run_id", doc["step_run_id"])  # ID_001

    evidence_refs = doc["evidence_refs"]
    if not isinstance(evidence_refs, list):
        raise SchemaViolation("evidence_refs 必须是 list", code="SCH_001")
    for reference in evidence_refs:
        ids.validate("source_span_id", reference)  # ID_001

    for key in ("rationale", "actor_ref"):
        value = doc[key]
        if not isinstance(value, str) or not value.strip():
            raise SchemaViolation("%s 必须为非空字符串" % key, code="SCH_001")
    if doc["consumption_level"] not in CONSUMPTION_LEVELS:
        raise SchemaViolation(
            "consumption_level 非闭集: %r" % (doc["consumption_level"],), code="SCH_002"
        )
    if doc["verdict"] == "school_dispute" and doc["decision_type"] != "review_school_attribution":
        raise SchemaViolation(
            "verdict=school_dispute 只能配 review_school_attribution", code="SCH_002"
        )
    return copy.deepcopy(doc)


def required_decision_types(candidate, *, entity_kind):
    """按 D-08 返回该对象齐备 ``expert_verified`` 所必需的决定类型（按 §8.2 第 2 表顺序）。"""
    required = {"review_source_fidelity"}
    if entity_kind == "school_view" or (candidate.get("school_ids") or []):
        required.add("review_school_attribution")
    return tuple(kind for kind in REVIEW_DECISION_TYPES if kind in required)


def derive_content_status(
    candidate, decisions, *, entity_kind, entity_id, candidate_revision_id
):
    """按 D-08 由审核决定推导内容成熟度；未见修订/不合法决定不计入。"""
    required = required_decision_types(candidate, entity_kind=entity_kind)
    latest = {}
    for decision in decisions or []:
        try:
            valid = validate_review_decision(decision)
        except LedgerError:
            continue
        target = valid["target"]
        if (
            target["entity_id"] != entity_id
            or target["artifact_revision_id"] != candidate_revision_id
        ):
            continue
        latest[valid["decision_type"]] = valid["verdict"]
    verdicts = [latest[kind] for kind in required if kind in latest]
    if any(verdict == "reject" for verdict in verdicts):
        return "deprecated"
    if any(verdict == "school_dispute" for verdict in verdicts):
        return "disputed"
    if any(verdict in ("modify", "request_evidence") for verdict in verdicts):
        return "needs_expert"
    if all(kind in latest and latest[kind] == "accept" for kind in required):
        return "expert_verified"
    return candidate.get("content_status")
