"""独立候选 Gate：对 ``candidate_set`` 做十二项输出契约检查（纯函数）。

本模块**不** import ``assemble`` / ``submission``：页块由本模块自行从 ``spans_doc``
重算。每项检查收集全部错误，不在首错处停止。
"""

import re

from pipeline.ledger import ids
from pipeline.ledger.errors import InvalidIdentifier

from . import (
    LAYERS,
    M4_ERROR_CODES,
    M4_STATUS_CEILING,
    REJECT_DISPOSITIONS,
    RELATIONS,
    SUPPORT_TYPES,
)
from .serialize import canonical_json, sha256_hex

_TOP_KEYS = (
    "schema_version",
    "technique_id",
    "source_id",
    "edition_part_artifact_id",
    "evidence_level",
    "span_layer",
    "source_channels",
    "assertions",
    "patterns",
    "school_views",
    "concept_mentions",
    "new_concept_candidates",
    "rejected",
    "disputes",
    "counts",
)

_OBJECT_TYPES = (
    "assertions",
    "patterns",
    "school_views",
    "concept_mentions",
    "new_concept_candidates",
)

_OBJECT_KEYS = {
    "assertions": (
        "assertion_id",
        "proposition_id",
        "proposition",
        "relation",
        "evidence",
        "conditions",
        "exceptions",
        "concept_refs",
        "school_ids",
        "layer",
        "content_status",
        "origin",
    ),
    "patterns": (
        "pattern_id",
        "name",
        "assertion_ids",
        "evidence",
        "interpretation",
        "interpretation_status",
        "recognition_rule_status",
        "content_status",
        "origin",
    ),
    "school_views": (
        "school_view_id",
        "school_id",
        "subject_entity_id",
        "claim_refs",
        "conflict_group_id",
        "changes_current_judgment",
        "source_refs",
        "evidence",
        "content_status",
        "origin",
    ),
    "concept_mentions": (
        "surface",
        "concept_ref",
        "evidence",
        "content_status",
        "origin",
    ),
    "new_concept_candidates": (
        "surface",
        "technique_id",
        "evidence",
        "content_status",
        "origin",
    ),
    "rejected": (
        "category",
        "lane",
        "item_index",
        "disposition",
        "reason_code",
        "detail",
    ),
    "disputes": ("dispute_id", "category", "key", "choice"),
}

_EVIDENCE_KEYS = (
    "source_span_id",
    "support_type",
    "start_offset",
    "end_offset",
    "quote",
    "quote_sha256",
)
_ORIGIN_KEYS = ("lane", "item_index")
_COUNT_KEYS = (
    "assertions",
    "patterns",
    "school_views",
    "concept_mentions",
    "new_concept_candidates",
    "rejected",
    "disputes",
    "human_decisions",
)
_CHOICES = ("a", "b", "both", "neither")
_DISPUTE_ID_RE = re.compile(r"^m4_d[0-9]{3}$")


def _page_blocks(spans_doc):
    """本模块自算页块（同页 Span text 以 ``"\\n"`` 连接），不复用装配器。"""
    order = []
    grouped = {}
    for span in spans_doc["spans"]:
        page = span["page"]
        if page not in grouped:
            grouped[page] = []
            order.append(page)
        grouped[page].append(span["text"])
    return {page: "\n".join(grouped[page]) for page in order}


def _iter_evidence(candidate_set):
    """遍历五类对象的全部证据，产出 ``(label, evidence)``。"""
    for key in _OBJECT_TYPES:
        for index, row in enumerate(candidate_set.get(key) or []):
            if not isinstance(row, dict):
                continue
            for ev_index, evidence in enumerate(row.get("evidence") or []):
                yield "%s[%d].evidence[%d]" % (key, index, ev_index), evidence


# ------------------------------------------------------------------ 十二项
def _check_schema_shape(candidate_set):
    errors = []
    if not isinstance(candidate_set, dict):
        return ["candidate_set 不是对象"]
    missing = set(_TOP_KEYS) - set(candidate_set)
    extra = set(candidate_set) - set(_TOP_KEYS)
    if missing or extra:
        errors.append("顶层键不符: 缺 %s 多 %s" % (sorted(missing), sorted(extra)))
    for key, allowed in _OBJECT_KEYS.items():
        rows = candidate_set.get(key)
        if not isinstance(rows, list):
            errors.append("%s 不是 list" % key)
            continue
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append("%s[%d] 不是对象" % (key, index))
                continue
            diff = set(row) ^ set(allowed)
            if diff:
                errors.append("%s[%d] 键集合不符: %s" % (key, index, sorted(diff)))
    for label, evidence in _iter_evidence(candidate_set):
        if not isinstance(evidence, dict):
            errors.append("%s 不是对象" % label)
            continue
        diff = set(evidence) ^ set(_EVIDENCE_KEYS)
        if diff:
            errors.append("%s 键集合不符: %s" % (label, sorted(diff)))
    for key in _OBJECT_TYPES:
        for index, row in enumerate(candidate_set.get(key) or []):
            if not isinstance(row, dict):
                continue
            origin = row.get("origin")
            if not isinstance(origin, dict) or set(origin) != set(_ORIGIN_KEYS):
                errors.append("%s[%d].origin 键集合不符" % (key, index))
    for index, row in enumerate(candidate_set.get("assertions") or []):
        if isinstance(row, dict):
            if row.get("relation") not in RELATIONS:
                errors.append("assertions[%d].relation 非闭集: %r" % (index, row.get("relation")))
            if row.get("layer") not in LAYERS:
                errors.append("assertions[%d].layer 非闭集: %r" % (index, row.get("layer")))
    for label, evidence in _iter_evidence(candidate_set):
        if isinstance(evidence, dict) and evidence.get("support_type") not in SUPPORT_TYPES:
            errors.append("%s.support_type 非闭集: %r" % (label, evidence.get("support_type")))
    allowed_reasons = set(M4_ERROR_CODES) | {None}
    for index, row in enumerate(candidate_set.get("rejected") or []):
        if not isinstance(row, dict):
            continue
        if row.get("disposition") not in REJECT_DISPOSITIONS:
            errors.append("rejected[%d].disposition 非闭集: %r" % (index, row.get("disposition")))
        if row.get("reason_code") not in allowed_reasons:
            errors.append("rejected[%d].reason_code 非闭集: %r" % (index, row.get("reason_code")))
    counts = candidate_set.get("counts")
    if not isinstance(counts, dict) or set(counts) != set(_COUNT_KEYS):
        errors.append("counts 键集合不符")
    return errors


def _id_errors(kind, value):
    try:
        ids.validate(kind, value)
    except InvalidIdentifier:
        return "%s 标识非法: %r" % (kind, value)
    return None


def _check_identity(candidate_set, config):
    errors = []
    id_range = (config or {}).get("id_range") or {}
    technique_id = candidate_set.get("technique_id")

    seen = set()
    for index, row in enumerate(candidate_set.get("assertions") or []):
        if not isinstance(row, dict):
            continue
        assertion_id = row.get("assertion_id")
        proposition_id = row.get("proposition_id")
        for kind, value in (("assertion_id", assertion_id), ("proposition_id", proposition_id)):
            problem = _id_errors(kind, value)
            if problem:
                errors.append("assertions[%d] %s" % (index, problem))
        if isinstance(assertion_id, str) and isinstance(proposition_id, str):
            if assertion_id.rsplit("_", 1)[-1] != proposition_id.rsplit("_", 1)[-1]:
                errors.append("assertions[%d] as/pr 号不一致" % index)
        if isinstance(assertion_id, str):
            parts = assertion_id.split("_")
            if len(parts) >= 3 and parts[1] != technique_id:
                errors.append("assertions[%d] 技法段不符: %s" % (index, assertion_id))
            if assertion_id in seen:
                errors.append("assertions[%d] assertion_id 重复: %s" % (index, assertion_id))
            seen.add(assertion_id)
            errors.extend(_range_errors("assertion", index, assertion_id, id_range.get("assertion")))

    pat_seen = set()
    for index, row in enumerate(candidate_set.get("patterns") or []):
        if not isinstance(row, dict):
            continue
        pattern_id = row.get("pattern_id")
        problem = _id_errors("pattern_id", pattern_id)
        if problem:
            errors.append("patterns[%d] %s" % (index, problem))
        if isinstance(pattern_id, str):
            parts = pattern_id.split("_")
            if len(parts) >= 3 and parts[1] != technique_id:
                errors.append("patterns[%d] 技法段不符: %s" % (index, pattern_id))
            if pattern_id in pat_seen:
                errors.append("patterns[%d] pattern_id 重复: %s" % (index, pattern_id))
            pat_seen.add(pattern_id)
            errors.extend(_range_errors("pattern", index, pattern_id, id_range.get("pattern")))

    sv_seen = set()
    for index, row in enumerate(candidate_set.get("school_views") or []):
        if not isinstance(row, dict):
            continue
        school_view_id = row.get("school_view_id")
        problem = _id_errors("school_view_id", school_view_id)
        if problem:
            errors.append("school_views[%d] %s" % (index, problem))
        if isinstance(school_view_id, str):
            if school_view_id in sv_seen:
                errors.append("school_views[%d] school_view_id 重复" % index)
            sv_seen.add(school_view_id)
        conflict_group_id = row.get("conflict_group_id")
        if conflict_group_id is not None:
            problem = _id_errors("conflict_group_id", conflict_group_id)
            if problem:
                errors.append("school_views[%d] %s" % (index, problem))
    return errors


def _range_errors(kind, index, value, bounds):
    if not bounds:
        return []
    parts = value.split("_")
    if len(parts) < 3 or not parts[-1].isdigit():
        return []
    number = int(parts[-1])
    if not (bounds[0] <= number <= bounds[1]):
        return ["%s[%d] %s 号 %d 越出 id_range %r" % (kind, index, kind, number, bounds)]
    return []


def _check_evidence_required(candidate_set):
    errors = []
    for key in _OBJECT_TYPES:
        for index, row in enumerate(candidate_set.get(key) or []):
            if isinstance(row, dict) and not row.get("evidence"):
                errors.append("%s[%d] evidence 为空" % (key, index))
    return errors


def _check_evidence_resolvable(candidate_set, spans_doc):
    errors = []
    span_map = {span["span_id"]: span for span in spans_doc["spans"]}
    for label, evidence in _iter_evidence(candidate_set):
        if not isinstance(evidence, dict):
            continue
        span = span_map.get(evidence.get("source_span_id"))
        if span is None:
            errors.append("%s.source_span_id 未知: %r" % (label, evidence.get("source_span_id")))
            continue
        start = evidence.get("start_offset")
        end = evidence.get("end_offset")
        if not isinstance(start, int) or not isinstance(end, int):
            errors.append("%s offset 非整数" % label)
            continue
        if not (span["start_offset"] <= start < end <= span["end_offset"]):
            errors.append(
                "%s offset [%d,%d) 越出 Span [%d,%d)"
                % (label, start, end, span["start_offset"], span["end_offset"])
            )
    return errors


def _check_quote_fidelity(candidate_set, spans_doc):
    errors = []
    span_map = {span["span_id"]: span for span in spans_doc["spans"]}
    blocks = _page_blocks(spans_doc)
    for label, evidence in _iter_evidence(candidate_set):
        if not isinstance(evidence, dict):
            continue
        quote = evidence.get("quote")
        if not isinstance(quote, str):
            errors.append("%s.quote 非字符串" % label)
            continue
        if sha256_hex(quote.encode("utf-8")) != evidence.get("quote_sha256"):
            errors.append("%s.quote_sha256 不一致" % label)
        span = span_map.get(evidence.get("source_span_id"))
        if span is None:
            continue
        start = evidence.get("start_offset")
        end = evidence.get("end_offset")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        block = blocks.get(span["page"], "")
        if block[start:end] != quote:
            errors.append("%s 页块切片 != quote" % label)
    return errors


def _check_status_ceiling(candidate_set):
    errors = []
    for key in _OBJECT_TYPES:
        for index, row in enumerate(candidate_set.get(key) or []):
            if isinstance(row, dict) and row.get("content_status") not in M4_STATUS_CEILING:
                errors.append(
                    "%s[%d].content_status 越权: %r" % (key, index, row.get("content_status"))
                )
    blob = canonical_json(candidate_set)
    if b"expert_verified" in blob:
        errors.append("candidate_set 全文出现 expert_verified")
    if b"cross_model_reviewed" in blob:
        errors.append("candidate_set 全文出现 cross_model_reviewed")
    return errors


def _check_layer_rules(candidate_set):
    errors = []
    for index, row in enumerate(candidate_set.get("assertions") or []):
        if isinstance(row, dict) and row.get("layer") == "case":
            errors.append("assertions[%d] layer=case（G4 命例不得作为通则主张）" % index)
    return errors


def _check_references(candidate_set, profile):
    errors = []
    assertions = [row for row in candidate_set.get("assertions") or [] if isinstance(row, dict)]
    patterns = [row for row in candidate_set.get("patterns") or [] if isinstance(row, dict)]
    assertion_ids = {row.get("assertion_id") for row in assertions}
    pattern_ids = {row.get("pattern_id") for row in patterns}
    canon = {row["concept_id"] for row in (profile.get("canon") or {}).get("concepts") or []}
    glossary = {row["concept_id"] for row in profile.get("glossary") or []}
    known_concepts = canon | glossary
    schools = {row["school_id"] for row in profile.get("schools") or []}
    technique_id = candidate_set.get("technique_id")

    for index, row in enumerate(patterns):
        for ref in row.get("assertion_ids") or []:
            if ref not in assertion_ids:
                errors.append("patterns[%d].assertion_ids 悬空: %s" % (index, ref))
    for index, row in enumerate(candidate_set.get("school_views") or []):
        if not isinstance(row, dict):
            continue
        if row.get("subject_entity_id") not in assertion_ids | pattern_ids:
            errors.append(
                "school_views[%d].subject_entity_id 悬空: %r" % (index, row.get("subject_entity_id"))
            )
        for ref in row.get("claim_refs") or []:
            if ref not in assertion_ids:
                errors.append("school_views[%d].claim_refs 悬空: %s" % (index, ref))
        if row.get("school_id") not in schools:
            errors.append("school_views[%d].school_id 未登记: %r" % (index, row.get("school_id")))
    for index, row in enumerate(assertions):
        for ref in row.get("concept_refs") or []:
            if ref not in known_concepts:
                errors.append("assertions[%d].concept_refs 未登记: %s" % (index, ref))
        for ref in row.get("school_ids") or []:
            if ref not in schools:
                errors.append("assertions[%d].school_ids 未登记: %s" % (index, ref))
    for index, row in enumerate(candidate_set.get("concept_mentions") or []):
        if not isinstance(row, dict):
            continue
        ref = row.get("concept_ref")
        if ref is not None and ref not in known_concepts:
            errors.append("concept_mentions[%d].concept_ref 未登记: %s" % (index, ref))
    for index, row in enumerate(candidate_set.get("new_concept_candidates") or []):
        if isinstance(row, dict) and row.get("technique_id") != technique_id:
            errors.append("new_concept_candidates[%d].technique_id 不符" % index)
    return errors


def _check_evidence_level_inherited(candidate_set, spans_doc):
    errors = []
    if candidate_set.get("evidence_level") != spans_doc.get("evidence_level"):
        errors.append("evidence_level 未继承 spans_doc")
    if candidate_set.get("span_layer") != "structural":
        errors.append("span_layer 非 structural: %r" % (candidate_set.get("span_layer"),))
    return errors


def _check_disputes_resolved(candidate_set):
    errors = []
    seen = set()
    for index, row in enumerate(candidate_set.get("disputes") or []):
        if not isinstance(row, dict):
            continue
        if row.get("choice") not in _CHOICES:
            errors.append("disputes[%d].choice 非闭集: %r" % (index, row.get("choice")))
        dispute_id = row.get("dispute_id")
        if not isinstance(dispute_id, str) or not _DISPUTE_ID_RE.match(dispute_id):
            errors.append("disputes[%d].dispute_id 格式非法: %r" % (index, dispute_id))
        elif dispute_id in seen:
            errors.append("disputes[%d].dispute_id 重复: %s" % (index, dispute_id))
        else:
            seen.add(dispute_id)
    return errors


def _check_counts_match(candidate_set):
    errors = []
    counts = candidate_set.get("counts")
    if not isinstance(counts, dict):
        return ["counts 不是对象"]
    for key in _COUNT_KEYS[:-1]:
        if counts.get(key) != len(candidate_set.get(key) or []):
            errors.append("counts.%s != 实际长度" % key)
    if counts.get("human_decisions") != len(candidate_set.get("disputes") or []):
        errors.append("counts.human_decisions != disputes 长度")
    return errors


def _check_source_consistency(candidate_set, profile, spans_doc):
    errors = []
    if candidate_set.get("technique_id") != profile.get("technique_id"):
        errors.append("technique_id != profile.technique_id")
    if candidate_set.get("source_id") != spans_doc.get("source_id"):
        errors.append("source_id != spans_doc.source_id")
    if candidate_set.get("edition_part_artifact_id") != spans_doc.get("edition_part_artifact_id"):
        errors.append("edition_part_artifact_id != spans_doc.edition_part_artifact_id")
    return errors


def evaluate_candidates(*, spans_doc, profile, candidate_set, config):
    """对 ``candidate_set`` 做十二项检查，返回 Gate 报告。"""
    plan = (
        ("schema_shape", lambda: _check_schema_shape(candidate_set)),
        ("identity", lambda: _check_identity(candidate_set, config)),
        ("evidence_required", lambda: _check_evidence_required(candidate_set)),
        ("evidence_resolvable", lambda: _check_evidence_resolvable(candidate_set, spans_doc)),
        ("quote_fidelity", lambda: _check_quote_fidelity(candidate_set, spans_doc)),
        ("status_ceiling", lambda: _check_status_ceiling(candidate_set)),
        ("layer_rules", lambda: _check_layer_rules(candidate_set)),
        ("references", lambda: _check_references(candidate_set, profile)),
        (
            "evidence_level_inherited",
            lambda: _check_evidence_level_inherited(candidate_set, spans_doc),
        ),
        ("disputes_resolved", lambda: _check_disputes_resolved(candidate_set)),
        ("counts_match", lambda: _check_counts_match(candidate_set)),
        (
            "source_consistency",
            lambda: _check_source_consistency(candidate_set, profile, spans_doc),
        ),
    )
    checks = []
    for name, func in plan:
        try:
            errors = func()
        except Exception as exc:  # noqa: BLE001 —— 检查自身异常转为该项错误，不中断其余检查
            errors = ["%s: %s" % (type(exc).__name__, exc)]
        checks.append({"name": name, "passed": not errors, "errors": errors})
    failed_checks = [row["name"] for row in checks if not row["passed"]]
    return {
        "gate_profile": config["gate_profile"],
        "structural": "failed" if failed_checks else "passed",
        "checks": checks,
        "failed_checks": failed_checks,
        "cross_model": "not_evaluated",
        "term_layering": "verify_only",
        "semantic_span_input": "not_evaluated",
    }
