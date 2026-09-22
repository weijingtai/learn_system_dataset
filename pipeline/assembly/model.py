"""M7 视图与快照模型校验纯函数（spec §15, §6.2, §8.1）。"""

import copy
import re
from dataclasses import dataclass, field

from pipeline.ledger import ids
from pipeline.ledger.errors import (
    DuplicateIdentifier,
    InvalidIdentifier,
    MissingReference,
    SchemaViolation,
)
from pipeline.ledger.states import CONTENT_MATURITY
from .canonical import canonical_json, content_sha256, nfc_key, work_key
from .errors import AssemblyRefused

RELATIONS = ("supports", "qualifies", "opposes", "corresponds", "equivalent")

_REVIEWED_PACKAGE_REQUIRED = frozenset({
    "schema_version",
    "reviewed_edition_revision_id",
    "decision_revision_ids",
    "decision_count",
    "approved_count",
    "rejected_count",
    "unresolved_count",
    "correction_request_revision_ids",
    "rework_impact_report_revision_id",
})

_REVIEWED_EDITION_REQUIRED = frozenset({
    "schema_version",
    "edition_part_artifact_id",
    "candidate_set_revision_id",
    "candidate_package_revision_id",
    "validation_package_revision_id",
    "approved",
    "rejected",
    "decisions",
    "evidence_links",
    "school_views",
    "correction_request_revision_ids",
    "rework_impact_report_revision_id",
    "unresolved_count",
})

_CANDIDATE_SET_REQUIRED = frozenset({
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
})

_APPROVED_REJECTED_KINDS = frozenset({"assertion", "pattern", "school_view", "concept"})


def validate_reviewed_package(doc: dict) -> dict:
    """校验 ReviewedEditionPackage 结构与标识格式。

    必填：schema_version, reviewed_edition_revision_id, decision_revision_ids,
          decision_count, approved_count, rejected_count, unresolved_count,
          correction_request_revision_ids, rework_impact_report_revision_id。
    unresolved_count != 0 抛 AssemblyRefused(SCH_001)。
    """
    if not isinstance(doc, dict):
        raise SchemaViolation("ReviewedEditionPackage 必须为字典", code="SCH_001")

    missing = _REVIEWED_PACKAGE_REQUIRED - set(doc.keys())
    if missing:
        raise SchemaViolation(
            "ReviewedEditionPackage 缺必填键: %s" % sorted(missing),
            code="SCH_001",
        )

    if doc.get("unresolved_count") != 0:
        raise AssemblyRefused(
            "ReviewedEditionPackage 存在未解决项 (unresolved_count=%r)"
            % (doc.get("unresolved_count"),),
            code="SCH_001",
        )

    ids.validate("artifact_revision_id", doc["reviewed_edition_revision_id"])

    if not isinstance(doc["decision_revision_ids"], list):
        raise SchemaViolation("decision_revision_ids 必须为列表", code="SCH_002")
    for did in doc["decision_revision_ids"]:
        ids.validate("artifact_revision_id", did)

    if not isinstance(doc["correction_request_revision_ids"], list):
        raise SchemaViolation("correction_request_revision_ids 必须为列表", code="SCH_002")
    for cid in doc["correction_request_revision_ids"]:
        ids.validate("artifact_revision_id", cid)

    if doc["rework_impact_report_revision_id"] is not None:
        ids.validate("artifact_revision_id", doc["rework_impact_report_revision_id"])

    return {
        "doc": copy.deepcopy(doc),
        "reviewed_edition_revision_id": doc["reviewed_edition_revision_id"],
    }


def validate_reviewed_edition(doc: dict) -> dict:
    """校验 ReviewedEdition 结构、实体标识、证据链引用及冲突组。

    必填键逐字取 impl-06-review/README.md §5.3。
    unresolved_count != 0 抛 AssemblyRefused(SCH_001)。
    """
    if not isinstance(doc, dict):
        raise SchemaViolation("ReviewedEdition 必须为字典", code="SCH_001")

    missing = _REVIEWED_EDITION_REQUIRED - set(doc.keys())
    if missing:
        raise SchemaViolation(
            "ReviewedEdition 缺必填键: %s" % sorted(missing),
            code="SCH_001",
        )

    if doc.get("unresolved_count") != 0:
        raise AssemblyRefused(
            "ReviewedEdition 存在未解决项 (unresolved_count=%r)"
            % (doc.get("unresolved_count"),),
            code="SCH_001",
        )

    ids.validate("artifact_id", doc["edition_part_artifact_id"])
    ids.validate("artifact_revision_id", doc["candidate_set_revision_id"])
    ids.validate("artifact_revision_id", doc["candidate_package_revision_id"])
    ids.validate("artifact_revision_id", doc["validation_package_revision_id"])

    for cid in doc["correction_request_revision_ids"]:
        ids.validate("artifact_revision_id", cid)
    if doc["rework_impact_report_revision_id"] is not None:
        ids.validate("artifact_revision_id", doc["rework_impact_report_revision_id"])

    seen_entities = set()
    approved_index = {}
    approved_hashes = {}

    for item in doc["approved"]:
        for key in ("entity_id", "kind", "artifact_revision_id", "content_status"):
            if key not in item:
                raise SchemaViolation("approved 元素缺字段: %s" % key, code="SCH_001")
        kind = item["kind"]
        if kind not in _APPROVED_REJECTED_KINDS:
            raise SchemaViolation("approved 元素非法 kind: %r" % (kind,), code="SCH_002")

        eid = item["entity_id"]
        _validate_typed_entity_id(kind, eid)
        ids.validate("artifact_revision_id", item["artifact_revision_id"])
        for did in item.get("decision_revision_ids", []):
            ids.validate("artifact_revision_id", did)

        if eid in seen_entities:
            raise DuplicateIdentifier(
                "approved ∪ rejected 中 entity_id 重复: %s" % eid,
                code="ID_002",
            )
        seen_entities.add(eid)
        approved_index[eid] = item
        approved_hashes[eid] = content_sha256(item)

    rejected_ids = []
    for item in doc["rejected"]:
        for key in ("entity_id", "kind", "artifact_revision_id", "content_status"):
            if key not in item:
                raise SchemaViolation("rejected 元素缺字段: %s" % key, code="SCH_001")
        kind = item["kind"]
        if kind not in _APPROVED_REJECTED_KINDS:
            raise SchemaViolation("rejected 元素非法 kind: %r" % (kind,), code="SCH_002")

        eid = item["entity_id"]
        _validate_typed_entity_id(kind, eid)
        ids.validate("artifact_revision_id", item["artifact_revision_id"])
        for did in item.get("decision_revision_ids", []):
            ids.validate("artifact_revision_id", did)

        if eid in seen_entities:
            raise DuplicateIdentifier(
                "approved ∪ rejected 中 entity_id 重复: %s" % eid,
                code="ID_002",
            )
        seen_entities.add(eid)
        rejected_ids.append(eid)
    rejected_ids.sort()

    for link in doc["evidence_links"]:
        for key in ("entity_id", "source_span_id", "start_offset", "end_offset", "quote_sha256"):
            if key not in link:
                raise SchemaViolation("evidence_links 缺字段: %s" % key, code="SCH_001")
        ids.validate("source_span_id", link["source_span_id"])
        if link.get("corpus_spans_revision_id") is not None:
            ids.validate("artifact_revision_id", link["corpus_spans_revision_id"])
        if link["entity_id"] not in seen_entities:
            raise MissingReference(
                "evidence_links entity_id 不在 approved ∪ rejected 中: %s" % link["entity_id"],
                code="REF_001",
            )

    for sv in doc["school_views"]:
        for key in ("school_view_id", "school_id", "subject_entity_id", "changes_current_judgment"):
            if key not in sv:
                raise SchemaViolation("school_views 缺字段: %s" % key, code="SCH_001")
        ids.validate("school_view_id", sv["school_view_id"])
        ids.validate("school_id", sv["school_id"])
        if sv.get("conflict_group_id") is not None:
            ids.validate("conflict_group_id", sv["conflict_group_id"])
        if sv["subject_entity_id"] not in seen_entities:
            raise MissingReference(
                "school_views subject_entity_id 不在 approved ∪ rejected 中: %s"
                % sv["subject_entity_id"],
                code="REF_001",
            )

    wk = None
    if "work_key" in doc and doc["work_key"]:
        wk = doc["work_key"]
    elif "source_id" in doc and doc["source_id"]:
        wk = work_key(doc["source_id"])
    elif doc.get("evidence_links"):
        m = re.match(r"^ss_([a-z][a-z0-9]*)_ed[0-9]{2}_.*", doc["evidence_links"][0]["source_span_id"])
        if m:
            wk = m.group(1)
    if wk is None:
        wk = "unknown"

    return {
        "work_key": wk,
        "edition_part_artifact_id": doc["edition_part_artifact_id"],
        "candidate_package_revision_id": doc["candidate_package_revision_id"],
        "doc": copy.deepcopy(doc),
        "approved_index": approved_index,
        "rejected_ids": rejected_ids,
        "hashes": approved_hashes,
    }


def validate_candidate_set(doc: dict) -> dict:
    """校验 M4 candidate_set（取已验收 assemble.py:637-651 真实形状）。"""
    if not isinstance(doc, dict):
        raise SchemaViolation("candidate_set 必须为字典", code="SCH_001")

    missing = _CANDIDATE_SET_REQUIRED - set(doc.keys())
    if missing:
        raise SchemaViolation(
            "candidate_set 缺必填键: %s" % sorted(missing),
            code="SCH_001",
        )

    tech = doc["technique_id"]
    if not isinstance(tech, str) or not re.match(r"^[a-z][a-z0-9]*$", tech):
        raise SchemaViolation("technique_id 非法: %r" % (tech,), code="SCH_002")

    ids.validate("source_id", doc["source_id"])
    ids.validate("artifact_id", doc["edition_part_artifact_id"])

    if doc["span_layer"] != "structural":
        raise SchemaViolation("span_layer 必须为 'structural': %r" % (doc["span_layer"],), code="SCH_002")
    if doc["evidence_level"] not in ("offset_level", "glyphbox_level"):
        raise SchemaViolation("evidence_level 非法: %r" % (doc["evidence_level"],), code="SCH_002")

    counts = doc["counts"]
    if not isinstance(counts, dict):
        raise SchemaViolation("counts 必须为字典", code="SCH_002")
    for list_key in (
        "assertions",
        "patterns",
        "school_views",
        "concept_mentions",
        "new_concept_candidates",
        "rejected",
        "disputes",
    ):
        if counts.get(list_key) != len(doc[list_key]):
            raise SchemaViolation(
                "counts[%s]=%r 与列表长度 %d 不一致"
                % (list_key, counts.get(list_key), len(doc[list_key])),
                code="SCH_002",
            )

    assertion_ids_set = set()
    for a in doc["assertions"]:
        aid = a["assertion_id"]
        ids.validate("assertion_id", aid)
        ids.validate("proposition_id", a["proposition_id"])
        if not isinstance(a.get("proposition"), str) or not a["proposition"]:
            raise SchemaViolation("assertion.proposition 必须为非空字符串", code="SCH_002")
        if a.get("relation") not in RELATIONS:
            raise SchemaViolation("assertion.relation 非法: %r" % (a.get("relation"),), code="SCH_002")
        if not isinstance(a.get("evidence"), list) or not a["evidence"]:
            raise SchemaViolation("assertion.evidence 必须为非空列表", code="SCH_002")
        for ev in a["evidence"]:
            ids.validate("source_span_id", ev["source_span_id"])
        for k in ("conditions", "exceptions", "concept_refs", "school_ids"):
            if not isinstance(a.get(k), list):
                raise SchemaViolation("assertion.%s 必须为列表" % k, code="SCH_002")
        for sch in a["school_ids"]:
            ids.validate("school_id", sch)
        if a.get("layer") not in ("general", "case", "editorial"):
            raise SchemaViolation("assertion.layer 非法: %r" % (a.get("layer"),), code="SCH_002")
        if a.get("content_status") not in CONTENT_MATURITY:
            raise SchemaViolation("assertion.content_status 非法: %r" % (a.get("content_status"),), code="SCH_002")
        if not isinstance(a.get("origin"), dict):
            raise SchemaViolation("assertion.origin 必须为字典", code="SCH_002")
        assertion_ids_set.add(aid)

    assertion_to_patterns = {aid: [] for aid in assertion_ids_set}
    pattern_ids_set = set()
    for p in doc["patterns"]:
        pat_id = p.get("pattern_id")
        if pat_id is None:
            if not p.get("candidate_key"):
                raise SchemaViolation("pattern_id 为 null 且无 candidate_key", code="SCH_002")
        else:
            ids.validate("pattern_id", pat_id)
            pattern_ids_set.add(pat_id)

        if not isinstance(p.get("name"), str) or not p["name"]:
            raise SchemaViolation("pattern.name 必须为非空字符串", code="SCH_002")
        if not isinstance(p.get("assertion_ids"), list):
            raise SchemaViolation("pattern.assertion_ids 必须为列表", code="SCH_002")
        for aid in p["assertion_ids"]:
            if aid not in assertion_ids_set:
                raise MissingReference("pattern.assertion_ids 悬空: %s" % aid, code="REF_001")
            if pat_id is not None:
                assertion_to_patterns[aid].append(pat_id)

        if p.get("interpretation_status") not in ("not_captured", "captured"):
            raise SchemaViolation("pattern.interpretation_status 非法", code="SCH_002")
        if p.get("recognition_rule_status") not in ("not_captured", "captured"):
            raise SchemaViolation("pattern.recognition_rule_status 非法", code="SCH_002")
        if p.get("content_status") not in CONTENT_MATURITY:
            raise SchemaViolation("pattern.content_status 非法: %r" % (p.get("content_status"),), code="SCH_002")

    for aid in assertion_to_patterns:
        assertion_to_patterns[aid].sort()

    school_view_ids_set = set()
    for sv in doc["school_views"]:
        svid = sv["school_view_id"]
        ids.validate("school_view_id", svid)
        ids.validate("school_id", sv["school_id"])
        sub = sv["subject_entity_id"]
        if sub not in assertion_ids_set and sub not in pattern_ids_set:
            raise MissingReference("school_view.subject_entity_id 悬空: %s" % sub, code="REF_001")
        if not isinstance(sv.get("claim_refs"), list):
            raise SchemaViolation("school_view.claim_refs 必须为列表", code="SCH_002")
        for aid in sv["claim_refs"]:
            if aid not in assertion_ids_set:
                raise MissingReference("school_view.claim_refs 悬空: %s" % aid, code="REF_001")
        if sv.get("conflict_group_id") is not None:
            ids.validate("conflict_group_id", sv["conflict_group_id"])
        if not isinstance(sv.get("changes_current_judgment"), bool):
            raise SchemaViolation("school_view.changes_current_judgment 必须为布尔值", code="SCH_002")
        if not isinstance(sv.get("source_refs"), list):
            raise SchemaViolation("school_view.source_refs 必须为列表", code="SCH_002")
        if sv.get("content_status") not in CONTENT_MATURITY:
            raise SchemaViolation("school_view.content_status 非法: %r" % (sv.get("content_status"),), code="SCH_002")
        school_view_ids_set.add(svid)

    for cm in doc["concept_mentions"]:
        if not isinstance(cm.get("surface"), str) or not cm["surface"]:
            raise SchemaViolation("concept_mention.surface 必须为非空字符串", code="SCH_002")
        ref = cm.get("concept_ref")
        if not (re.match(ids.PATTERNS["technique_concept_id"], str(ref)) or re.match(ids.PATTERNS["shared_concept_id"], str(ref))):
            raise InvalidIdentifier("concept_ref 格式非法: %r" % (ref,), code="ID_001")
        if cm.get("content_status") not in CONTENT_MATURITY:
            raise SchemaViolation("concept_mention.content_status 非法: %r" % (cm.get("content_status"),), code="SCH_002")

    for ncc in doc["new_concept_candidates"]:
        if not isinstance(ncc.get("surface"), str) or not ncc["surface"]:
            raise SchemaViolation("new_concept_candidate.surface 必须为非空字符串", code="SCH_002")
        if not isinstance(ncc.get("technique_id"), str) or not re.match(r"^[a-z][a-z0-9]*$", ncc["technique_id"]):
            raise SchemaViolation("new_concept_candidate.technique_id 非法", code="SCH_002")
        if ncc.get("content_status") not in CONTENT_MATURITY:
            raise SchemaViolation("new_concept_candidate.content_status 非法", code="SCH_002")

    hashes = {}
    for a in doc["assertions"]:
        hashes["assertion:%s" % a["assertion_id"]] = content_sha256(a)
    for p in doc["patterns"]:
        if p.get("pattern_id"):
            hashes["pattern:%s" % p["pattern_id"]] = content_sha256(p)
    for sv in doc["school_views"]:
        hashes["school_view:%s" % sv["school_view_id"]] = content_sha256(sv)

    return {
        "work_key": work_key(doc["source_id"]),
        "technique_id": doc["technique_id"],
        "source_id": doc["source_id"],
        "edition_part_artifact_id": doc["edition_part_artifact_id"],
        "doc": copy.deepcopy(doc),
        "pattern_ids": sorted(pattern_ids_set),
        "assertion_ids": sorted(assertion_ids_set),
        "assertion_to_patterns": assertion_to_patterns,
        "school_view_ids": sorted(school_view_ids_set),
        "hashes": hashes,
    }


def empty_snapshot_knowledge(technique_id: str, id_range: dict) -> dict:
    """初始化空的 CanonicalKnowledgeSnapshot knowledge 字典。"""
    return {
        "technique_id": technique_id,
        "id_allocation": {},
        "id_range": copy.deepcopy(id_range),
        "allocated_pattern_ids": [],
        "retired_entity_ids": [],
        "editions": [],
        "concepts": [],
        "patterns": [],
        "assertions": [],
        "school_views": [],
        "conflict_groups": [],
        "relations": [],
    }


def validate_snapshot_knowledge(knowledge: dict) -> None:
    """自检 CanonicalKnowledgeSnapshot knowledge 结构、排序及发号一致性。"""
    if not isinstance(knowledge, dict):
        raise SchemaViolation("knowledge 必须为字典", code="SCH_002")

    tech = knowledge.get("technique_id")
    if not tech:
        raise SchemaViolation("knowledge.technique_id 必填", code="SCH_002")

    # 校验 id_range
    id_range = knowledge.get("id_range")
    if not isinstance(id_range, dict):
        raise SchemaViolation("knowledge.id_range 必须为字典", code="SCH_002")
    expected_range_key = "pat_%s" % tech
    if expected_range_key not in id_range:
        raise SchemaViolation(
            "id_range 必须包含键 %r，收到: %r" % (expected_range_key, list(id_range.keys())),
            code="SCH_002",
        )
    rng_val = id_range[expected_range_key]
    if (
        not isinstance(rng_val, (list, tuple))
        or len(rng_val) != 2
        or not isinstance(rng_val[0], int)
        or not isinstance(rng_val[1], int)
        or rng_val[0] < 0
        or rng_val[1] < 0
        or rng_val[0] > rng_val[1]
    ):
        raise SchemaViolation("id_range 值必须为 [start, end] 且 start <= end: %r" % (rng_val,), code="SCH_002")
    start, end = rng_val[0], rng_val[1]

    _check_sorted(knowledge.get("editions", []), key_fn=lambda x: x["source_id"], name="editions")
    # D1（ACT impl-07/11）：editions[] 每项必须含 evidence_level（闭集）和 corpus_spans_revision_id（可为 None）
    _EVIDENCE_LEVELS = frozenset({"offset_level", "glyphbox_level"})
    for ed in knowledge.get("editions", []):
        if "evidence_level" not in ed:
            raise SchemaViolation(
                "editions 条目缺必填字段 evidence_level（source_id=%r）" % ed.get("source_id"),
                code="SCH_001",
            )
        if ed["evidence_level"] not in _EVIDENCE_LEVELS:
            raise SchemaViolation(
                "editions 条目 evidence_level 非法（须在 %s 内）: %r" % (sorted(_EVIDENCE_LEVELS), ed["evidence_level"]),
                code="SCH_002",
            )
        if "corpus_spans_revision_id" not in ed:
            raise SchemaViolation(
                "editions 条目缺必填字段 corpus_spans_revision_id（source_id=%r）" % ed.get("source_id"),
                code="SCH_001",
            )
    _check_sorted(knowledge.get("concepts", []), key_fn=lambda x: x["concept_id"], name="concepts")
    _check_sorted(knowledge.get("patterns", []), key_fn=lambda x: x["pattern_id"], name="patterns")
    patterns_ids = [p["pattern_id"] for p in knowledge.get("patterns", [])]
    if len(patterns_ids) != len(set(patterns_ids)):
        raise DuplicateIdentifier("patterns 中存在重复 pattern_id", code="ID_002")
    _check_sorted(knowledge.get("assertions", []), key_fn=lambda x: x["assertion_id"], name="assertions")
    _check_sorted(knowledge.get("school_views", []), key_fn=lambda x: x["school_view_id"], name="school_views")
    _check_sorted(knowledge.get("conflict_groups", []), key_fn=lambda x: x["conflict_group_id"], name="conflict_groups")
    _check_sorted(knowledge.get("relations", []), key_fn=lambda x: x["relation_key"], name="relations")

    retired = knowledge.get("retired_entity_ids", [])
    if not isinstance(retired, list):
        raise SchemaViolation("retired_entity_ids 必须为列表", code="SCH_002")
    if retired != sorted(retired):
        raise SchemaViolation("retired_entity_ids 必须升序排序", code="SCH_002")
    retired_set = set(retired)

    # 活对象收集
    alive_concepts = set(c["concept_id"] for c in knowledge.get("concepts", []))
    alive_patterns = set(patterns_ids)
    alive_assertions = set(a["assertion_id"] for a in knowledge.get("assertions", []))
    alive_svs = set(sv["school_view_id"] for sv in knowledge.get("school_views", []))
    all_alive = alive_concepts | alive_patterns | alive_assertions | alive_svs

    overlap = all_alive & retired_set
    if overlap:
        raise DuplicateIdentifier("活对象号与 retired 重叠: %s" % sorted(overlap), code="ID_002")

    # 校验 pattern 顶层无 content_status
    for p in knowledge.get("patterns", []):
        if "content_status" in p:
            raise SchemaViolation(
                "pattern 顶层不得出现 content_status 键: %s" % p["pattern_id"],
                code="SCH_002",
            )

    # 校验 assertion evidence
    for a in knowledge.get("assertions", []):
        for ev in a.get("evidence", []):
            st = ev.get("start_offset")
            en = ev.get("end_offset")
            if st is not None and en is not None and st > en:
                raise SchemaViolation(
                    "assertion.evidence start_offset > end_offset: %d > %d" % (st, en),
                    code="SCH_002",
                )

    # 校验 allocated_pattern_ids
    allocated = knowledge.get("allocated_pattern_ids", [])
    if not isinstance(allocated, list):
        raise SchemaViolation("allocated_pattern_ids 必须为列表", code="SCH_002")
    if allocated != sorted(allocated) or len(allocated) != len(set(allocated)):
        raise SchemaViolation("allocated_pattern_ids 必须升序且互异", code="SCH_002")

    pat_prefix = "pat_%s_" % tech
    allocated_numbers = []
    for pid in allocated:
        if not pid.startswith(pat_prefix):
            raise SchemaViolation("allocated_pattern_id 前缀不符合 %s: %s" % (pat_prefix, pid), code="SCH_002")
        num_part = pid[len(pat_prefix):]
        if not re.match(r"^[0-9]{6}$", num_part):
            raise SchemaViolation("allocated_pattern_id 必须为 6 位数字: %s" % pid, code="SCH_002")
        val = int(num_part)
        if val < start or val > end:
            raise SchemaViolation(
                "allocated_pattern_id %s 超出 id_range [%d, %d]" % (pid, start, end),
                code="SCH_002",
            )
        if pid in retired_set:
            raise DuplicateIdentifier(
                "allocated_pattern_id %s 与 retired 重叠" % pid,
                code="ID_002",
            )
        allocated_numbers.append(val)

    # 校验 id_allocation
    id_alloc = knowledge.get("id_allocation", {})
    if not isinstance(id_alloc, dict):
        raise SchemaViolation("id_allocation 必须为字典", code="SCH_002")

    # 提取命名空间内所有 pattern 号
    alive_pat_numbers = []
    for pid in alive_patterns:
        if pid.startswith(pat_prefix):
            num_part = pid[len(pat_prefix):]
            if re.match(r"^[0-9]{6}$", num_part):
                alive_pat_numbers.append(int(num_part))

    retired_pat_numbers = []
    for pid in retired_set:
        if pid.startswith(pat_prefix):
            num_part = pid[len(pat_prefix):]
            if re.match(r"^[0-9]{6}$", num_part):
                retired_pat_numbers.append(int(num_part))

    all_numbers = alive_pat_numbers + retired_pat_numbers + allocated_numbers
    max_pat_number = max(all_numbers) if all_numbers else 0

    if allocated and expected_range_key not in id_alloc:
        raise SchemaViolation(
            "allocated_pattern_ids 非空时 id_allocation 必须存在键 %r" % expected_range_key,
            code="SCH_002",
        )

    if expected_range_key in id_alloc:
        alloc_val = id_alloc[expected_range_key]
        if alloc_val < max_pat_number:
            raise SchemaViolation(
                "id_allocation[%r]=%d 小于命名空间最大号 %d"
                % (expected_range_key, alloc_val, max_pat_number),
                code="SCH_002",
            )
        target_max = max(alive_pat_numbers + allocated_numbers) if (alive_pat_numbers or allocated_numbers) else 0
        if target_max > 0 and alloc_val != target_max:
            raise SchemaViolation(
                "id_allocation[%r]=%d 必须等于活对象与补发最大号 %d"
                % (expected_range_key, alloc_val, target_max),
                code="SCH_002",
            )

    # 校验 relations 活对象端点
    for rel in knowledge.get("relations", []):
        for ep in ("from_entity_id", "to_entity_id"):
            val = rel.get(ep)
            if val is not None and val not in all_alive:
                raise MissingReference("relations 端点 %s 悬空" % val, code="REF_001")

    # 校验 conflict_groups 成员在 school_views 中
    for cg in knowledge.get("conflict_groups", []):
        for mid in cg.get("member_school_view_ids", []):
            if mid not in alive_svs:
                raise MissingReference("conflict_groups 成员 %s 悬空" % mid, code="REF_001")


def _validate_typed_entity_id(kind: str, eid: str) -> None:
    if kind == "assertion":
        ids.validate("assertion_id", eid)
    elif kind == "pattern":
        ids.validate("pattern_id", eid)
    elif kind == "school_view":
        ids.validate("school_view_id", eid)
    elif kind == "concept":
        if not (re.match(ids.PATTERNS["technique_concept_id"], eid) or re.match(ids.PATTERNS["shared_concept_id"], eid)):
            raise InvalidIdentifier("concept entity_id 非法: %s" % eid, code="ID_001")


def _check_sorted(items: list, key_fn, name: str) -> None:
    if not isinstance(items, list):
        raise SchemaViolation("%s 必须为列表" % name, code="SCH_002")
    keys = [key_fn(item) for item in items]
    if keys != sorted(keys):
        raise SchemaViolation("%s 列表未按主键升序排序: %r" % (name, keys), code="SCH_002")


# ---------------------------------------------------------------------------
# 增量汇编新增的闭集与类型（act/impl-07/22 contract 一/二；§8.1）。
# 本节**只新增**，上方既有定义一字未改。
# ---------------------------------------------------------------------------

#: D-12：提案键的命名空间（`kind` 只允许这四个）
PROPOSAL_KINDS = ("merge", "alias", "conflict", "evidence")

#: D-05 采纳 A：并入语义闭集，**禁止静默并入**
MERGE_RELATIONS = ("attach", "admit_new", "merge_entities")

#: 提案三态 + `decided`（已有合法人工决定）
PROPOSAL_RESOLUTIONS = ("auto", "human", "blocked", "decided")

#: CHARTER §3.1：配对的全部可用依据（本波只允许这三条确定性依据）
PAIR_STRATEGIES = ("exact_collation_key", "shared_evidence_span", "same_formal_object")


@dataclass(frozen=True)
class PairCandidate:
    """配对候选（`:mod:`pipeline.assembly.matcher` 的唯一产出类型）。

    ``suggestion`` 是旁路字段：将来接入模型建议时只填这里，且**不得**进入 Gate 判定、
    不得影响 ID 发号、不得改变自动裁定结果。本波恒为 ``None``。
    """

    left_key: str
    right_key: str
    strategy: str
    shared: tuple = field(default_factory=tuple)
    suggestion: object = None

    def as_dict(self) -> dict:
        return {
            "left_key": self.left_key,
            "right_key": self.right_key,
            "strategy": self.strategy,
            "shared": list(self.shared),
            "suggestion": self.suggestion,
        }
