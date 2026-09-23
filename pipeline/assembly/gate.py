"""M7 独立创世 Gate evaluate_genesis（spec §15, §20.5, act/g0-03）。

纯函数；禁止 import genesis，自行从 candidate_set 与 reviewed_edition 独立重算身份与保真。
"""

import copy
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from pipeline.assembly import canonical, model
from pipeline.ledger import ids


def _check_schema_and_ids(knowledge: dict) -> Tuple[bool, str]:
    try:
        model.validate_snapshot_knowledge(knowledge)
        return True, "snapshot knowledge schema and ids valid"
    except Exception as e:
        return False, str(e)


def _check_identity_preserved(knowledge: dict) -> Tuple[bool, str]:
    retired = knowledge.get("retired_entity_ids", [])
    if retired != []:
        return False, "retired_entity_ids must be empty in genesis, found: %r" % (retired,)

    identity_delta = knowledge.get("identity_delta")
    if identity_delta is not None and identity_delta != {} and identity_delta != []:
        return False, "identity_delta must be empty or None in genesis, found: %r" % (identity_delta,)

    meta = knowledge.get("meta", {})
    if isinstance(meta, dict):
        base_snap = meta.get("base_snapshot_revision_id")
        if base_snap is not None:
            return False, "base_snapshot_revision_id must be None in genesis, found: %r" % (base_snap,)

    return True, "identity preserved, no retired entities or base"


def _check_allocation_monotonic(cset_doc: dict, knowledge: dict) -> Tuple[bool, str]:
    tech = knowledge.get("technique_id") or cset_doc.get("technique_id")
    expected_range_key = "pat_%s" % tech
    id_range = knowledge.get("id_range")
    if not isinstance(id_range, dict) or expected_range_key not in id_range:
        return False, "id_range missing key %s" % expected_range_key

    rng = id_range[expected_range_key]
    if (
        not isinstance(rng, (list, tuple))
        or len(rng) != 2
        or not isinstance(rng[0], int)
        or not isinstance(rng[1], int)
        or rng[0] < 0
        or rng[1] < 0
        or rng[0] > rng[1]
    ):
        return False, "id_range [%r] invalid" % (rng,)
    start, end = rng[0], rng[1]

    allocated = knowledge.get("allocated_pattern_ids", [])
    if not isinstance(allocated, list):
        return False, "allocated_pattern_ids must be list"
    if len(allocated) != len(set(allocated)):
        return False, "allocated_pattern_ids contains duplicates: %r" % (allocated,)

    pat_prefix = "pat_%s_" % tech
    allocated_numbers = []
    for pid in allocated:
        if not isinstance(pid, str) or not pid.startswith(pat_prefix):
            return False, "allocated_pattern_id prefix invalid: %r" % (pid,)
        num_str = pid[len(pat_prefix):]
        if not re.match(r"^[0-9]{6}$", num_str):
            return False, "allocated_pattern_id format invalid: %r" % (pid,)
        val = int(num_str)
        if val < start or val > end:
            return False, "allocated_pattern_id %r outside range [%d, %d]" % (pid, start, end)
        allocated_numbers.append(val)

    # 独立核对：补发号不与候选集中既有合法 pat_ 号重复（第 71 条裁决）
    cset_pats = set()
    for p in cset_doc.get("patterns", []):
        c_pid = p.get("pattern_id")
        if c_pid and isinstance(c_pid, str):
            cset_pats.add(c_pid)
    overlap = set(allocated) & cset_pats
    if overlap:
        return False, "allocated_pattern_ids overlap with candidate set patterns: %r" % sorted(overlap)

    # 活对象命名空间号
    live_numbers = []
    for p in knowledge.get("patterns", []):
        pid = p.get("pattern_id")
        if pid and isinstance(pid, str) and pid.startswith(pat_prefix):
            num_str = pid[len(pat_prefix):]
            if re.match(r"^[0-9]{6}$", num_str):
                live_numbers.append(int(num_str))

    all_numbers = set(live_numbers) | set(allocated_numbers)
    expected_alloc = max(all_numbers) if all_numbers else 0
    id_alloc = knowledge.get("id_allocation", {})
    if not isinstance(id_alloc, dict):
        return False, "id_allocation must be dict"

    actual_alloc = id_alloc.get(expected_range_key)
    if expected_alloc > 0 or actual_alloc is not None:
        if actual_alloc != expected_alloc:
            return False, "id_allocation[%s]=%r != expected max %r" % (expected_range_key, actual_alloc, expected_alloc)

    return True, "allocation monotonic and within range"


def _check_provenance_complete(cset_doc: dict, re_doc: dict, knowledge: dict) -> Tuple[bool, str]:
    k_assertions = {a.get("assertion_id") for a in knowledge.get("assertions", [])}
    k_patterns = {p.get("pattern_id") for p in knowledge.get("patterns", [])}
    k_svs = {sv.get("school_view_id") for sv in knowledge.get("school_views", [])}
    k_concepts = {c.get("concept_id") for c in knowledge.get("concepts", [])}

    bound_concept_refs = {
        cm.get("concept_ref")
        for cm in cset_doc.get("concept_mentions", [])
        if cm.get("concept_ref")
    }

    for item in re_doc.get("approved", []):
        kind = item.get("kind")
        eid = item.get("entity_id")
        if kind == "assertion":
            if eid not in k_assertions:
                return False, "approved assertion %s missing from knowledge" % eid
        elif kind == "pattern":
            if eid not in k_patterns:
                return False, "approved pattern %s missing from knowledge" % eid
        elif kind == "school_view":
            if eid not in k_svs:
                return False, "approved school_view %s missing from knowledge" % eid
        elif kind == "concept":
            if eid in bound_concept_refs and eid not in k_concepts:
                return False, "approved bound concept %s missing from knowledge" % eid

    return True, "all approved entities present in knowledge"


def _check_view_objects_unaltered(cset_doc: dict, knowledge: dict) -> Tuple[bool, str]:
    cset_a_map = {a["assertion_id"]: a for a in cset_doc.get("assertions", []) if "assertion_id" in a}
    for a in knowledge.get("assertions", []):
        aid = a.get("assertion_id")
        if aid in cset_a_map:
            c_a = cset_a_map[aid]
            if canonical.nfc_key(a.get("proposition", "")) != canonical.nfc_key(c_a.get("proposition", "")):
                return False, "assertion %s proposition altered: %r != %r" % (
                    aid,
                    a.get("proposition"),
                    c_a.get("proposition"),
                )

    cset_p_map = {p["pattern_id"]: p for p in cset_doc.get("patterns", []) if p.get("pattern_id")}
    for p in knowledge.get("patterns", []):
        pid = p.get("pattern_id")
        c_p = cset_p_map.get(pid)
        if c_p:
            if canonical.nfc_key(p.get("name", "")) != canonical.nfc_key(c_p.get("name", "")):
                return False, "pattern %s name altered: %r != %r" % (pid, p.get("name"), c_p.get("name"))
            if "interpretation" in p and c_p.get("interpretation") is not None:
                if canonical.nfc_key(p["interpretation"]) != canonical.nfc_key(c_p["interpretation"]):
                    return False, "pattern %s interpretation altered" % pid
            # provenance content_sha256 可复算
            expected_sha = model.content_sha256(c_p)
            for prov in p.get("provenance", []):
                if prov.get("content_sha256") != expected_sha:
                    return False, "pattern %s provenance content_sha256 mismatch" % pid

    return True, "view objects unaltered and sha256 verified"


def _check_no_silent_fold(cset_doc: dict, re_doc: dict, knowledge: dict) -> Tuple[bool, str]:
    k_sv_ids = {sv.get("school_view_id") for sv in knowledge.get("school_views", [])}
    approved_sv_ids = {
        item["entity_id"]
        for item in re_doc.get("approved", [])
        if item.get("kind") == "school_view"
    }

    missing_sv = approved_sv_ids - k_sv_ids
    if missing_sv:
        return False, "approved school_views missing from knowledge: %s" % sorted(missing_sv)

    declared_members_by_cg: Dict[str, set] = {}
    for sv in cset_doc.get("school_views", []):
        svid = sv.get("school_view_id")
        cgid = sv.get("conflict_group_id")
        if svid in approved_sv_ids and cgid:
            declared_members_by_cg.setdefault(cgid, set()).add(svid)

    k_cg_map = {
        cg.get("conflict_group_id"): set(cg.get("member_school_view_ids", []))
        for cg in knowledge.get("conflict_groups", [])
    }

    for cgid, declared_members in declared_members_by_cg.items():
        if cgid not in k_cg_map:
            return False, "declared conflict_group %s missing from knowledge" % cgid
        actual_members = k_cg_map[cgid]
        if not declared_members.issubset(actual_members):
            return False, "conflict_group %s members %s not subset of %s" % (
                cgid,
                sorted(declared_members),
                sorted(actual_members),
            )

    return True, "no silent fold, all school views and conflict groups preserved"


def _check_first_layer_display(knowledge: dict) -> Tuple[bool, str]:
    sv_map = {
        sv.get("school_view_id"): sv.get("changes_current_judgment", False)
        for sv in knowledge.get("school_views", [])
    }
    for cg in knowledge.get("conflict_groups", []):
        cgid = cg.get("conflict_group_id")
        fld = cg.get("first_layer_display")
        members = cg.get("member_school_view_ids", [])
        expected_fld = any(sv_map.get(m, False) for m in members)
        if fld != expected_fld:
            return False, "conflict_group %s first_layer_display %r != expected %r" % (
                cgid,
                fld,
                expected_fld,
            )
    return True, "first_layer_display matches member changes_current_judgment"


def _check_maturity_not_synthesized(re_doc: dict, knowledge: dict) -> Tuple[bool, str]:
    for p in knowledge.get("patterns", []):
        if "content_status" in p:
            return False, "pattern %s has top-level content_status" % p.get("pattern_id")
    for c in knowledge.get("concepts", []):
        if "content_status" in c:
            return False, "concept %s has top-level content_status" % c.get("concept_id")

    approved_status = {
        item.get("entity_id"): item.get("content_status")
        for item in re_doc.get("approved", [])
    }

    for a in knowledge.get("assertions", []):
        aid = a.get("assertion_id")
        if aid in approved_status:
            exp_status = approved_status[aid]
            if a.get("content_status") != exp_status:
                return False, "assertion %s content_status %r != approved %r" % (
                    aid,
                    a.get("content_status"),
                    exp_status,
                )

    for sv in knowledge.get("school_views", []):
        svid = sv.get("school_view_id")
        if svid in approved_status:
            exp_status = approved_status[svid]
            if sv.get("content_status") != exp_status:
                return False, "school_view %s content_status %r != approved %r" % (
                    svid,
                    sv.get("content_status"),
                    exp_status,
                )

    return True, "content_status matches approved values, no top-level on patterns/concepts"


def _check_decisions_consistent(re_doc: dict, knowledge: dict) -> Tuple[bool, str]:
    meta = knowledge.get("meta", {})
    if isinstance(meta, dict):
        drefs = meta.get("decision_refs")
        if drefs is not None and drefs != {}:
            return False, "meta.decision_refs must be empty in genesis, found: %r" % (drefs,)

    rejected_eids = {
        item.get("entity_id")
        for item in re_doc.get("rejected", [])
        if item.get("entity_id")
    }
    if rejected_eids:
        k_eids = set()
        for c in knowledge.get("concepts", []):
            k_eids.add(c.get("concept_id"))
        for p in knowledge.get("patterns", []):
            k_eids.add(p.get("pattern_id"))
        for a in knowledge.get("assertions", []):
            k_eids.add(a.get("assertion_id"))
        for sv in knowledge.get("school_views", []):
            k_eids.add(sv.get("school_view_id"))
        overlap = k_eids & rejected_eids
        if overlap:
            return False, "rejected entities present in knowledge: %s" % sorted(overlap)

    return True, "decisions consistent, no manual decision refs and rejected entities absent"


def _check_genesis_only(knowledge: dict) -> Tuple[bool, str]:
    rels = knowledge.get("relations")
    if rels != []:
        return False, "relations must be empty in genesis, found: %r" % (rels,)

    idd = knowledge.get("identity_delta")
    if idd is not None and idd != {} and idd != []:
        return False, "identity_delta must be empty or None in genesis, found: %r" % (idd,)

    meta = knowledge.get("meta", {})
    if isinstance(meta, dict):
        base_rev = meta.get("base_snapshot_revision_id")
        if base_rev is not None:
            return False, "meta.base_snapshot_revision_id must be None in genesis, found: %r" % (base_rev,)

    return True, "genesis only, no relations, identity_delta, or base snapshot"


def _run_check(fn, *args) -> Dict[str, Any]:
    try:
        ok, detail = fn(*args)
        return {"passed": bool(ok), "detail": str(detail)}
    except Exception as e:
        return {"passed": False, "detail": "Exception during check: %s" % e}


def evaluate_genesis(*, candidate_set: dict, reviewed_edition: dict, knowledge: dict) -> dict:
    """独立创世 Gate 校验函数（spec §15, §20.5）。

    重算并核对 10 项检查，固定顺序：
    1. schema_and_ids
    2. identity_preserved
    3. allocation_monotonic
    4. provenance_complete
    5. view_objects_unaltered
    6. no_silent_fold
    7. first_layer_display
    8. maturity_not_synthesized
    9. decisions_consistent
    10. genesis_only
    """
    if isinstance(candidate_set, dict) and "doc" in candidate_set:
        cset_doc = candidate_set["doc"]
    else:
        cset_doc = candidate_set

    if isinstance(reviewed_edition, dict) and "doc" in reviewed_edition:
        re_doc = reviewed_edition["doc"]
    else:
        re_doc = reviewed_edition

    checks: Dict[str, Dict[str, Any]] = {}

    checks["schema_and_ids"] = _run_check(_check_schema_and_ids, knowledge)
    checks["identity_preserved"] = _run_check(_check_identity_preserved, knowledge)
    checks["allocation_monotonic"] = _run_check(_check_allocation_monotonic, cset_doc, knowledge)
    checks["provenance_complete"] = _run_check(_check_provenance_complete, cset_doc, re_doc, knowledge)
    checks["view_objects_unaltered"] = _run_check(_check_view_objects_unaltered, cset_doc, knowledge)
    checks["no_silent_fold"] = _run_check(_check_no_silent_fold, cset_doc, re_doc, knowledge)
    checks["first_layer_display"] = _run_check(_check_first_layer_display, knowledge)
    checks["maturity_not_synthesized"] = _run_check(_check_maturity_not_synthesized, re_doc, knowledge)
    checks["decisions_consistent"] = _run_check(_check_decisions_consistent, re_doc, knowledge)
    checks["genesis_only"] = _run_check(_check_genesis_only, knowledge)

    overall_passed = all(c["passed"] for c in checks.values())

    return {
        "passed": overall_passed,
        "checks": checks,
    }


# =========================================================================== 增量独立 Gate
# `evaluate_assembly`（act/impl-07/25，E 波）。
#
# 边界纪律：本段**不 import** `matcher` / `apply` / `incremental` / `orchestrate` / `genesis`。
# 闭包、可比单元与「实际改动的对象集」全部在这里**独立重算**——
# 照搬被验对象的实现等于自己验自己（W8 ACT 18）。

#: 检查名与顺序逐字固定（act/06.yaml contract；校准见 act/25.yaml 第一节）
ASSEMBLY_CHECK_ORDER = (
    "schema_and_ids",
    "identity_preserved",
    "allocation_monotonic",
    "provenance_complete",
    "view_objects_unaltered",
    "untouched_byte_identical",
    "affected_scope_exact",
    "collation_comparable_only",
    "no_silent_fold",
    "first_layer_display",
    "identity_delta_contract",
    "maturity_not_synthesized",
    "decisions_consistent",
)

_ASM_COLLECTIONS = ("patterns", "concepts", "assertions", "school_views")
_ASM_ID_KEYS = {
    "patterns": "pattern_id",
    "concepts": "concept_id",
    "assertions": "assertion_id",
    "school_views": "school_view_id",
}
_ASM_CLOSURE_RELATION_KINDS = ("alias_of", "distinct_from", "merged_into")
_ASM_COLLATION_KINDS = ("alignment", "variant_reading", "addition", "omission")
_ASM_PAIRING_RELATION_KINDS = ("alias_of", "merged_into")
_ASM_CHANGE_TYPES = ("migrated", "merged", "split", "retired")
#: not_comparable 理由闭集；有键单元按此顺序取第一个命中的（CHARTER §28 Q7、§29 Q11）
_ASM_NOT_COMPARABLE_REASONS = (
    "view_undeclared",
    "same_source",
    "base_undeclared",
    "multiple_assertions_per_unit",
    "declared_without_assertion",
    "missing_collation_key",
)
_ASM_ENTITY_KINDS = ("pattern", "concept", "assertion")


def _asm_doc(doc: Any) -> Any:
    """接受原始文档与「已校验结果」两种形状（`{"doc": …}`）。"""
    if isinstance(doc, dict) and isinstance(doc.get("doc"), dict):
        return doc["doc"]
    return doc


def _asm_views(views: Sequence[dict]) -> List[dict]:
    out: List[dict] = []
    for view in views or []:
        cset = _asm_doc(view.get("candidate_set") or {}) or {}
        reviewed = _asm_doc(view.get("reviewed_edition") or {}) or {}
        out.append(
            {
                "source_id": view.get("source_id") or cset.get("source_id"),
                "candidate_set": cset,
                "reviewed_edition": reviewed,
            }
        )
    return out


def _asm_index(knowledge: dict) -> Dict[str, Any]:
    index: Dict[str, Any] = {
        collection: {
            item.get(_ASM_ID_KEYS[collection]): item
            for item in knowledge.get(collection) or []
            if item.get(_ASM_ID_KEYS[collection])
        }
        for collection in _ASM_COLLECTIONS
    }
    index["conflict_groups"] = {
        item.get("conflict_group_id"): item for item in knowledge.get("conflict_groups") or []
    }
    index["alive"] = set().union(*(set(index[c]) for c in _ASM_COLLECTIONS))
    index["kind_of"] = {
        entity_id: collection[:-1]
        for collection in _ASM_COLLECTIONS
        for entity_id in index[collection]
    }
    return index


def _asm_work_key(source_id: Optional[str]) -> Optional[str]:
    try:
        return canonical.work_key(source_id) if source_id else None
    except Exception:
        return None


def _asm_collation_contacts(index: Dict[str, Any], key: Any, source_id: Any) -> Set[str]:
    """基底中同 `collation_key` 的 Assertion（两侧 work_key 都可算时才要求相等）。"""
    if not key:
        return set()
    work = _asm_work_key(source_id)
    out: Set[str] = set()
    for assertion_id, assertion in index["assertions"].items():
        if assertion.get("collation_key") != key:
            continue
        other = _asm_work_key(assertion.get("source_id"))
        if work is not None and other is not None and other != work:
            continue
        out.add(assertion_id)
    return out


def _asm_concept_content(candidate: dict) -> dict:
    """Concept 的视图内容口径：名称（或 surface）+ 别名（与 apply 同口径，独立重写）。"""
    return {
        "name": candidate.get("name") or candidate.get("surface"),
        "aliases": list(candidate.get("aliases") or []),
    }


def _asm_view_candidates(view: dict) -> Dict[str, Dict[str, dict]]:
    """按**声明键**给视图对象建表（只查表，不做任何配对判断）。"""
    cset = view.get("candidate_set") or {}
    source_id = view.get("source_id")
    out: Dict[str, Dict[str, dict]] = {"pattern": {}, "assertion": {}, "school_view": {}, "concept": {}}
    for pattern in cset.get("patterns") or []:
        for key in (pattern.get("pattern_id"), pattern.get("candidate_key")):
            if key:
                out["pattern"].setdefault(key, pattern)
    for assertion in cset.get("assertions") or []:
        if assertion.get("assertion_id"):
            out["assertion"].setdefault(assertion["assertion_id"], assertion)
    for school_view in cset.get("school_views") or []:
        if school_view.get("school_view_id"):
            out["school_view"].setdefault(school_view["school_view_id"], school_view)
    for candidate in list(cset.get("concept_mentions") or []) + list(
        cset.get("new_concept_candidates") or []
    ):
        for key in (
            candidate.get("concept_ref"),
            candidate.get("concept_id"),
            candidate.get("surface"),
            candidate.get("candidate_key"),
        ):
            if key:
                out["concept"].setdefault(key, candidate)
    if source_id:
        out["source_id"] = source_id  # type: ignore[assignment]
    return out


def _asm_view_provenance_hash(kind: str, candidate: dict) -> Optional[str]:
    if kind == "concept":
        return canonical.content_sha256(_asm_concept_content(candidate))
    return canonical.content_sha256(candidate)


def _asm_text_sha(proposition: Any) -> Optional[str]:
    if proposition is None:
        return None
    return canonical.sha256_hex(canonical.nfc_key(proposition).encode("utf-8"))


def _asm_approved(view: dict) -> Set[Tuple[str, str]]:
    return {
        (item.get("kind"), item.get("entity_id"))
        for item in (view.get("reviewed_edition") or {}).get("approved") or []
        if item.get("entity_id")
    }


def _asm_declared_presence(view: dict) -> Dict[str, bool]:
    """视图**声明**的可比单元：只读视图 `collation_units`（CHARTER §28 Q5）。

    有 collation_key 却没声明单元的断言**不算声明**（它是 `view_undeclared`）；null 键声明不入表。
    """
    cset = view.get("candidate_set") or {}
    out: Dict[str, bool] = {}
    for entry in cset.get("collation_units") or []:
        key = entry.get("collation_key")
        if key:
            out[key] = bool(entry.get("present", True))
    return out


def _asm_edition_units(edition: dict) -> Dict[str, bool]:
    """Snapshot 里某版次**声明过**的可比单元：只读 `editions[].collation_units`（§25.5），不从断言推。"""
    return {
        entry.get("collation_key"): bool(entry.get("present"))
        for entry in edition.get("collation_units") or []
        if entry.get("collation_key")
    }


def _asm_closure(base_knowledge: dict, views: Sequence[dict], decisions: Sequence[dict]) -> Dict[str, List[str]]:
    """Gate **独立重算**的 affected 闭包（act/05.yaml:20-31 的第 1–3 条口径）。

    触点只取**视图与决定已声明**的字段，与 base 已有号相交：
    候选自带号 / 候选候选键 / 名称命中 / 概念号 / collation_key 同键 / present=false 单元 /
    替换时 provenance 哈希变化的对象；再沿 `alias_of`/`distinct_from`/`merged_into` 两端与
    冲突组同组迭代到不动点。**不读 proposals，不调用被验模块。**
    """
    base = base_knowledge or {}
    index = _asm_index(base)
    alive = index["alive"]
    contacts: Set[str] = set()

    for view in views:
        cset = view.get("candidate_set") or {}
        source_id = view.get("source_id")
        for pattern in cset.get("patterns") or []:
            for key in (pattern.get("pattern_id"), pattern.get("candidate_key")):
                if key in alive:
                    contacts.add(key)
            name = pattern.get("name")
            if name:
                for pattern_id, base_pattern in index["patterns"].items():
                    base_name = base_pattern.get("name")
                    if base_name and canonical.nfc_key(base_name) == canonical.nfc_key(name):
                        contacts.add(pattern_id)
        for candidate in list(cset.get("concept_mentions") or []) + list(
            cset.get("new_concept_candidates") or []
        ):
            for key in (
                candidate.get("concept_ref"),
                candidate.get("concept_id"),
                candidate.get("surface"),
                candidate.get("candidate_key"),
            ):
                if key in alive:
                    contacts.add(key)
        for assertion in cset.get("assertions") or []:
            if assertion.get("assertion_id") in alive:
                contacts.add(assertion["assertion_id"])
            contacts |= _asm_collation_contacts(index, assertion.get("collation_key"), source_id)
        for school_view in cset.get("school_views") or []:
            for key in (school_view.get("school_view_id"), school_view.get("subject_entity_id")):
                if key in alive:
                    contacts.add(key)
        # 对勘单元触点（README §6:533，CHARTER §28 Q6）：只有声明 present:false 的单元、
        # 与基底为本 source 声明过而视图不再声明的单元，才让基底该位置的断言入触点；
        # present:true 的单元本身不贡献（它的断言已在上面按「同 (work_key, collation_key)」入触点）。
        presence = _asm_declared_presence(view)
        for key, present in presence.items():
            if not present:
                contacts |= _asm_collation_contacts(index, key, source_id)
        for edition in base.get("editions") or []:
            if edition.get("source_id") != source_id:
                continue
            for key in _asm_edition_units(edition):
                if key not in presence:
                    contacts |= _asm_collation_contacts(index, key, source_id)

        # 替换：同一来源在基底的 provenance 哈希与视图声明不一致，**或被删除的对象本身**
        # （act/05.yaml:20-31 的替换条：被删除对象按其 base 记录计算触点）。
        declared = _asm_view_candidates(view)
        for kind, collection in (("pattern", "patterns"), ("concept", "concepts")):
            for entity_id, item in index[collection].items():
                if not any(
                    (row.get("source_id") == source_id) for row in item.get("provenance") or []
                ):
                    continue
                candidate = declared[kind].get(entity_id)
                if candidate is None:
                    # 本版次不再声明该对象 → 被删除，对象自身入触点
                    contacts.add(entity_id)
                    continue
                expected = _asm_view_provenance_hash(kind, candidate)
                rows = [
                    row
                    for row in item.get("provenance") or []
                    if row.get("source_id") == source_id
                ]
                if all(row.get("content_sha256") != expected for row in rows):
                    contacts.add(entity_id)
        # 断言：本 source 的基底断言，其 collation_key 本轮已不再被该视图声明 → 被删除
        # （与 `orchestrate` 的替换条同口径；act/05.yaml:23-24）。
        for assertion_id, assertion in index["assertions"].items():
            if assertion.get("source_id") != source_id:
                continue
            collation_key = assertion.get("collation_key")
            if collation_key and not presence.get(collation_key, False):
                contacts.add(assertion_id)

    for decision in decisions or []:
        for target in decision.get("target_entity_ids") or []:
            if target in alive:
                contacts.add(target)
            group = index["conflict_groups"].get(target)
            if group is not None:
                contacts |= {
                    member
                    for member in group.get("member_school_view_ids") or []
                    if member in alive
                }

    adjacency: Dict[str, Set[str]] = {}
    for relation in base.get("relations") or []:
        if relation.get("relation_kind") not in _ASM_CLOSURE_RELATION_KINDS:
            continue
        left, right = relation.get("from_entity_id"), relation.get("to_entity_id")
        if left and right:
            adjacency.setdefault(left, set()).add(right)
            adjacency.setdefault(right, set()).add(left)
    for group in base.get("conflict_groups") or []:
        members = list(group.get("member_school_view_ids") or [])
        for member in members:
            adjacency.setdefault(member, set()).update(other for other in members if other != member)

    affected = {entity_id for entity_id in contacts if entity_id in alive}
    frontier = list(affected)
    while frontier:
        current = frontier.pop()
        for neighbour in adjacency.get(current, ()):
            if neighbour in alive and neighbour not in affected:
                affected.add(neighbour)
                frontier.append(neighbour)

    return {"affected": sorted(affected), "untouched": sorted(alive - affected)}


def _asm_modified_ids(base_knowledge: dict, knowledge: dict) -> Set[str]:
    """**实际发生**的事实：基底活对象里、在总账中消失或规范字节已变的那些。

    这是 §14.1 的行为判据——比对「实际改动的对象集」与 `affected`，
    而不是只从裁定推导「将要改动的对象集」。
    """
    base_index = _asm_index(base_knowledge)
    now_index = _asm_index(knowledge)
    modified: Set[str] = set()
    for entity_id in base_index["alive"]:
        collection = base_index["kind_of"][entity_id] + "s"
        if entity_id not in now_index["alive"]:
            modified.add(entity_id)
            continue
        if canonical.canonical_json(base_index[collection][entity_id]) != canonical.canonical_json(
            now_index[collection][entity_id]
        ):
            modified.add(entity_id)
    return modified


def _asm_check_schema_and_ids(knowledge: dict, decisions: Sequence[dict], identity_delta: dict) -> Tuple[bool, str]:
    ok, detail = _check_schema_and_ids(knowledge)
    if not ok:
        return False, detail

    offenders: List[Tuple[str, str]] = []
    for relation in knowledge.get("relations") or []:
        key = relation.get("relation_key")
        if key and ids.kind_of(key) is not None:
            offenders.append(("relation_key", key))
    for decision in decisions or []:
        key = decision.get("proposal_key")
        if key and ids.kind_of(key) is not None:
            offenders.append(("proposal_key", key))
    for entry in ((identity_delta or {}).get("entries") or []):
        key = (entry.get("reason_ref") or {}).get("proposal_key")
        if key and ids.kind_of(key) is not None:
            offenders.append(("reason_ref.proposal_key", key))
    if offenders:
        return False, "局部键取了已登记号前缀形态（不得混入正式编号空间）: %r" % (offenders,)
    return True, "snapshot knowledge schema/ids valid; 关系键与提案键均非登记号"


def _asm_check_identity_preserved(base_knowledge: dict, knowledge: dict, identity_delta: dict) -> Tuple[bool, str]:
    base_index = _asm_index(base_knowledge or {})
    now_index = _asm_index(knowledge or {})
    delta_from = {
        entry.get("from_entity_id") for entry in (identity_delta or {}).get("entries") or []
    }
    missing = sorted(
        entity_id
        for entity_id in base_index["alive"]
        if entity_id not in now_index["alive"] and entity_id not in delta_from
    )
    if missing:
        return False, "基底活对象既不在总账、也不在 identity_delta 的 from：%s" % missing

    revived = sorted(set((base_knowledge or {}).get("retired_entity_ids") or []) & now_index["alive"])
    if revived:
        return False, "基底已退役的号在新总账里又活了：%s" % revived

    both = sorted(set((knowledge or {}).get("retired_entity_ids") or []) & now_index["alive"])
    if both:
        return False, "同一号同时出现在 retired_entity_ids 与活对象里：%s" % both
    return True, "基底 %d 个活对象全部有下落，且无退役号复活" % len(base_index["alive"])


def _asm_check_allocation_monotonic(base_knowledge: dict, views: Sequence[dict], knowledge: dict) -> Tuple[bool, str]:
    technique_id = (knowledge or {}).get("technique_id")
    if not technique_id:
        return False, "knowledge.technique_id 缺失"
    prefix = "pat_%s_" % technique_id
    range_key = "pat_%s" % technique_id

    def numbers(pattern_ids: Iterable[Any]) -> Set[int]:
        out: Set[int] = set()
        for pattern_id in pattern_ids:
            if not isinstance(pattern_id, str) or not pattern_id.startswith(prefix):
                continue
            tail = pattern_id[len(prefix):]
            if re.match(r"^[0-9]{6}$", tail):
                out.add(int(tail))
        return out

    base_live = numbers(
        item.get("pattern_id") for item in (base_knowledge or {}).get("patterns") or []
    )
    live = numbers(item.get("pattern_id") for item in (knowledge or {}).get("patterns") or [])
    view_declared: Set[int] = set()
    for view in views:
        view_declared |= numbers(
            pattern.get("pattern_id")
            for pattern in (view.get("candidate_set") or {}).get("patterns") or []
        )

    watermark = int(((base_knowledge or {}).get("id_allocation") or {}).get(range_key) or 0)
    newly_issued = sorted(live - base_live - view_declared)
    too_low = sorted(number for number in newly_issued if number <= watermark)
    if too_low:
        return False, "新发 pat_ 号未大于基底 id_allocation[%s]=%d: %r" % (range_key, watermark, too_low)

    allocation = ((knowledge or {}).get("id_allocation") or {}).get(range_key)
    highest = max(
        live
        | numbers((base_knowledge or {}).get("retired_entity_ids") or [])
        | numbers((knowledge or {}).get("retired_entity_ids") or []),
        default=0,
    )
    if allocation is None or int(allocation) < highest:
        return False, "id_allocation[%s]=%r 小于活对象与 retired 最大号 %d" % (
            range_key,
            allocation,
            highest,
        )
    return True, "新发号 %r 均大于基底水位 %d；id_allocation=%r ≥ 最大号 %d" % (
        newly_issued,
        watermark,
        allocation,
        highest,
    )


def _asm_check_provenance_complete(views: Sequence[dict], knowledge: dict, identity_delta: dict) -> Tuple[bool, str]:
    index = _asm_index(knowledge or {})
    delta_from = {
        entry.get("from_entity_id") for entry in (identity_delta or {}).get("entries") or []
    }
    provenance_rows = set()
    for collection in ("patterns", "concepts"):
        for item in (knowledge or {}).get(collection) or []:
            for row in item.get("provenance") or []:
                provenance_rows.add((row.get("source_id"), row.get("content_sha256")))
    text_hashes = {
        item.get("text_sha256") for item in (knowledge or {}).get("assertions") or []
    }

    missing: List[str] = []
    for view in views:
        declared = _asm_view_candidates(view)
        for kind, entity_id in sorted(_asm_approved(view)):
            if entity_id in delta_from:
                continue
            if kind == "assertion":
                if entity_id in index["assertions"]:
                    continue
                candidate = declared["assertion"].get(entity_id) or {}
                digest = _asm_text_sha(candidate.get("proposition"))
                if digest and digest in text_hashes:
                    continue  # 新号由发号器给出，按文本哈希定位落点
            elif kind == "pattern":
                if entity_id in index["patterns"]:
                    continue
                candidate = declared["pattern"].get(entity_id)
                if candidate is not None:
                    digest = _asm_view_provenance_hash("pattern", candidate)
                    if (view.get("source_id"), digest) in provenance_rows:
                        continue
            elif kind == "concept":
                if entity_id in index["concepts"]:
                    continue
                candidate = declared["concept"].get(entity_id)
                if candidate is not None:
                    digest = _asm_view_provenance_hash("concept", candidate)
                    if (view.get("source_id"), digest) in provenance_rows:
                        continue
            elif kind == "school_view":
                if entity_id in index["school_views"]:
                    continue
            else:
                continue
            missing.append("%s:%s" % (kind, entity_id))
    if missing:
        return False, "已获批的视图对象在总账里找不到落点：%s" % sorted(missing)
    return True, "本视图已获批对象全部落在总账（活对象或 provenance）"


def _asm_check_view_objects_unaltered(views: Sequence[dict], knowledge: dict) -> Tuple[bool, str]:
    index = _asm_index(knowledge or {})
    for view in views:
        source_id = view.get("source_id")
        approved = _asm_approved(view)
        declared = _asm_view_candidates(view)
        for kind, collection in (("pattern", "patterns"), ("concept", "concepts")):
            for entity_id, item in index[collection].items():
                if (kind, entity_id) not in approved:
                    continue
                candidate = declared[kind].get(entity_id)
                if candidate is None:
                    continue
                rows = [
                    row
                    for row in item.get("provenance") or []
                    if row.get("source_id") == source_id
                ]
                expected = _asm_view_provenance_hash(kind, candidate)
                if not rows:
                    return False, (
                        "%s %s 的视图来源行在总账里缺席（改动被基底旧版静默覆盖）: source_id=%s"
                        % (kind, entity_id, source_id)
                    )
                if all(row.get("content_sha256") != expected for row in rows):
                    return False, "%s %s 的 provenance 哈希与**视图**版本不符: 视图 %s / 总账 %r" % (
                        kind,
                        entity_id,
                        expected,
                        [row.get("content_sha256") for row in rows],
                    )
        for assertion in (view.get("candidate_set") or {}).get("assertions") or []:
            assertion_id = assertion.get("assertion_id")
            if not assertion_id or ("assertion", assertion_id) not in approved:
                continue
            if assertion_id not in index["assertions"]:
                continue
            expected = _asm_text_sha(assertion.get("proposition"))
            if expected is None:
                continue
            actual = index["assertions"][assertion_id].get("text_sha256")
            if actual != expected:
                return False, "assertion %s 的文本哈希与**视图**版本不符: 视图 %s / 总账 %r" % (
                    assertion_id,
                    expected,
                    actual,
                )
    return True, "视图对象在总账里逐字节等于视图版本（无静默回退）"


def _asm_check_untouched_byte_identical(
    base_knowledge: dict, views: Sequence[dict], decisions: Sequence[dict], knowledge: dict
) -> Tuple[bool, str]:
    closure = _asm_closure(base_knowledge, views, decisions)
    base_index = _asm_index(base_knowledge or {})
    now_index = _asm_index(knowledge or {})
    violations: List[str] = []
    for entity_id in closure["untouched"]:
        collection = base_index["kind_of"][entity_id] + "s"
        if entity_id not in now_index["alive"]:
            violations.append("%s 从总账消失" % entity_id)
            continue
        if canonical.canonical_json(base_index[collection][entity_id]) != canonical.canonical_json(
            now_index[collection][entity_id]
        ):
            violations.append("%s 规范字节已变" % entity_id)
    if violations:
        return False, "闭包外的 %d 个基底对象必须逐字节原样，实际: %s" % (
            len(closure["untouched"]),
            violations,
        )
    return True, "闭包外 %d 个基底对象逐字节原样" % len(closure["untouched"])


def _asm_check_affected_scope_exact(
    base_knowledge: dict,
    views: Sequence[dict],
    decisions: Sequence[dict],
    knowledge: dict,
    report: dict,
) -> Tuple[bool, str]:
    closure = _asm_closure(base_knowledge, views, decisions)
    affected = (report or {}).get("affected_entity_ids")
    if affected is None:
        return False, "report.affected_entity_ids 缺失（增量轮必填）"
    affected_set = {str(entity_id) for entity_id in affected}
    expected_set = set(closure["affected"])
    if affected_set != expected_set:
        return False, "report.affected 与 Gate 自算闭包不一致: 少 %r 多 %r" % (
            sorted(expected_set - affected_set),
            sorted(affected_set - expected_set),
        )

    rebuilt = (report or {}).get("rebuilt_entity_ids")
    if rebuilt is None:
        return False, "report.rebuilt_entity_ids 缺失"
    outside = sorted({str(entity_id) for entity_id in rebuilt} - expected_set)
    if outside:
        return False, "rebuilt ⊄ 自算闭包: %r" % outside

    # §14.1 行为判据：看**实际发生了什么**（基底对象在总账里消失/字节变），
    # 而不是只从裁定推导「将要改什么」。闭包漏掉被改动的对象时，
    # apply 会拿基底旧版把它静默拷回——这条就是那个洞的探测器。
    modified = _asm_modified_ids(base_knowledge or {}, knowledge or {})
    unaccounted = sorted(modified - expected_set)
    if unaccounted:
        return False, "实际被改动的基底对象不在 affected 内（闭包漏对象）：%r" % unaccounted
    return True, "affected 与自算闭包精确相等；rebuilt ⊆ 闭包；实际改动 %d 个全在闭包内" % len(
        modified
    )


def _asm_entity_span_ids(entity: Optional[dict]) -> Set[str]:
    if not entity:
        return set()
    spans = {
        evidence.get("source_span_id")
        for evidence in entity.get("evidence") or []
        if isinstance(evidence, dict)
    }
    for row in entity.get("provenance") or []:
        if not isinstance(row, dict):
            continue
        spans.update(row.get("source_span_ids") or [])
        if row.get("source_span_id"):
            spans.add(row["source_span_id"])
    spans.discard(None)
    return spans


def _asm_has_pairing_basis(index: Dict[str, Any], endpoints: Sequence[str]) -> bool:
    """端点之间能不能由**确定性依据**解释：同一正式号 / 相等 collation_key / 共享证据片段。"""
    if len(endpoints) < 2:
        return True  # 单端（addition/omission 的缺侧）本身不是配对声明
    if endpoints[0] == endpoints[1]:
        return True
    keys = [
        index["assertions"][entity_id].get("collation_key")
        if entity_id in index["assertions"]
        else None
        for entity_id in endpoints
    ]
    if keys[0] and keys[0] == keys[1]:
        return True

    def entity_of(entity_id: str) -> Optional[dict]:
        for collection in _ASM_COLLECTIONS:
            if entity_id in index[collection]:
                return index[collection][entity_id]
        return None

    if _asm_entity_span_ids(entity_of(endpoints[0])) & _asm_entity_span_ids(entity_of(endpoints[1])):
        return True
    return False


def _asm_not_comparable_row(source_id: Any, key: Any, assertion_id: Any, reason: str) -> dict:
    return {
        "assertion_id": assertion_id,
        "collation_key": key,
        "reason": reason,
        "source_id": source_id,
    }


def _asm_not_comparable_sort_key(row: dict) -> Tuple[str, str, str]:
    return (
        str(row.get("source_id") or ""),
        str(row.get("collation_key") or ""),
        str(row.get("assertion_id") or ""),
    )


def _asm_collation_plan(base_knowledge: dict, view: dict) -> Tuple[Dict[Tuple[str, str], dict], List[dict]]:
    """对本轮视图**独立重算**对勘单元（CHARTER §25.2–25.5、§28、§29）。

    视图 = 新版；与视图 source 不同、同 work_key 的每个基底版次 = 旧版，逐对算。
    声明只读视图 `collation_units` 与基底 `editions[].collation_units`；获批断言在视图一侧取
    `reviewed_edition.approved`，在基底一侧取基底 knowledge 的断言。

    返回 ``(expected, not_comparable)``：
    ``expected[(旧版 source, collation_key)] = {"kind": "pair"|"addition"|"omission", "new": 号|None, "old": 号|None}``；
    两侧都声明 present:false 的单元不出现。``not_comparable`` 按 §29 Q11 口径（已排序）。
    """
    source_id = view.get("source_id")
    work = _asm_work_key(source_id)
    declared = _asm_declared_presence(view)
    approved = _asm_approved(view)
    rows: List[dict] = []

    new_by_key: Dict[str, List[str]] = {}
    for assertion in (view.get("candidate_set") or {}).get("assertions") or []:
        assertion_id = assertion.get("assertion_id")
        if not assertion_id or ("assertion", assertion_id) not in approved:
            continue
        key = assertion.get("collation_key")
        if key:
            new_by_key.setdefault(key, []).append(assertion_id)
        else:
            rows.append(_asm_not_comparable_row(source_id, None, assertion_id, "missing_collation_key"))
    for entry in (view.get("candidate_set") or {}).get("collation_units") or []:
        if not entry.get("collation_key"):
            rows.append(_asm_not_comparable_row(source_id, None, None, "missing_collation_key"))

    old_by_source: Dict[Any, Dict[str, List[str]]] = {}
    for assertion in (base_knowledge or {}).get("assertions") or []:
        if assertion.get("collation_key"):
            old_by_source.setdefault(assertion.get("source_id"), {}).setdefault(
                assertion["collation_key"], []
            ).append(assertion.get("assertion_id"))
    editions = [
        edition
        for edition in (base_knowledge or {}).get("editions") or []
        if (edition.get("work_key") or _asm_work_key(edition.get("source_id"))) == work
    ]

    expected: Dict[Tuple[str, str], dict] = {}
    for key in sorted(set(declared) | set(new_by_key)):
        if key not in declared:
            rows.append(_asm_not_comparable_row(source_id, key, None, "view_undeclared"))
            continue
        new_present = declared[key]
        new_ids = new_by_key.get(key) or []
        reasons: List[str] = []
        comparable = False
        for edition in editions:
            base_source = edition.get("source_id")
            if base_source == source_id:
                reasons.append("same_source")
                continue
            old_units = _asm_edition_units(edition)
            if key not in old_units:
                reasons.append("base_undeclared")
                continue
            old_present = old_units[key]
            old_ids = old_by_source.get(base_source, {}).get(key) or []
            if len(new_ids) > 1 or len(old_ids) > 1:
                reasons.append("multiple_assertions_per_unit")
                continue
            if (new_present and not new_ids) or (old_present and not old_ids):
                reasons.append("declared_without_assertion")
                continue
            if new_present and old_present:
                expected[(base_source, key)] = {"kind": "pair", "new": new_ids[0], "old": old_ids[0]}
            elif new_present:
                expected[(base_source, key)] = {"kind": "addition", "new": new_ids[0], "old": None}
            elif old_present:
                expected[(base_source, key)] = {"kind": "omission", "new": None, "old": old_ids[0]}
            comparable = True
        # 对至少一个基底版次可比 → 不列；对所有都不可比 → 列一项，取优先级最高的理由（§29 Q11 第 5 条）
        if not comparable:
            reason = min(reasons or ["base_undeclared"], key=_ASM_NOT_COMPARABLE_REASONS.index)
            rows.append(_asm_not_comparable_row(source_id, key, None, reason))
    return expected, sorted(rows, key=_asm_not_comparable_sort_key)


def _asm_is_collation_relation(relation: dict, index: Dict[str, Any]) -> bool:
    """四类对勘关系，外加 R07b 拒绝落成的 distinct_from（两端都是断言且 detail 带 collation_key，§29 Q10）。"""
    kind = relation.get("relation_kind")
    if kind in _ASM_COLLATION_KINDS:
        return True
    if kind != "distinct_from":
        return False
    ends = (relation.get("from_entity_id"), relation.get("to_entity_id"))
    return all(end in index["assertions"] for end in ends) and bool(
        (relation.get("detail") or {}).get("collation_key")
    )


def _asm_relation_touches(relation: dict, index: Dict[str, Any], sources: Set[Any]) -> bool:
    """是否**涉及本轮视图 source**（§29 Q8，§31 更正）：任一端断言属于视图 source，
    或 addition / omission 的缺侧（absent_source_id）是视图 source。

    §29 Q8 原文只写了 omission，漏了 addition：同书返工时，旧轮「新版有、本书缺」的增文，
    其缺侧正是本轮视图，必须随本轮重算，不能要求原样保留。
    """
    for end in (relation.get("from_entity_id"), relation.get("to_entity_id")):
        if end in index["assertions"] and index["assertions"][end].get("source_id") in sources:
            return True
    detail = relation.get("detail") or {}
    return (
        relation.get("relation_kind") in ("addition", "omission")
        and detail.get("absent_source_id") in sources
    )


def _asm_collation_shape(relation: dict, index: Dict[str, Any]) -> str:
    """与本轮视图无关、任何对勘关系都须满足的形状（§25.1、§25.3、§25.6）；返回失败理由，空串表示通过。"""
    kind = relation.get("relation_kind")
    name = "%s %s" % (kind, relation.get("relation_key"))
    left, right = relation.get("from_entity_id"), relation.get("to_entity_id")
    if kind in ("addition", "omission"):
        if left is None or right is not None:
            return "%s 方向不符 §25.6：from 必须是断言、to 必须为 null（实为 %r → %r）" % (name, left, right)
    elif left is None or right is None:
        return "%s 出现 null 端点（null 端点只许出现在 addition / omission）" % name
    if left == right:
        return "%s 是自环（两端同为 %s）" % (name, left)
    for end in (left, right):
        if end is not None and end not in index["assertions"]:
            return "%s 的端点 %s 不是总账里的断言" % (name, end)
    left_source = index["assertions"][left].get("source_id")
    if right is not None and left_source == index["assertions"][right].get("source_id"):
        return "%s 两端同属一个版次 %s（同一版次不跟自己比，§25.3）" % (name, left_source)
    if kind in ("addition", "omission"):
        absent = (relation.get("detail") or {}).get("absent_source_id")
        if not absent or absent == left_source:
            return "%s 的 absent_source_id=%r 必须是另一个版次（from 属于 %s）" % (name, absent, left_source)
    return ""


def _asm_check_collation_relation(
    relation: dict,
    index: Dict[str, Any],
    view_source: Any,
    base_sources: Set[Any],
    expected: Dict[Tuple[str, str], dict],
) -> Tuple[Optional[Tuple[str, str]], str]:
    """逐条核一条涉及视图的对勘关系；返回 (所落单元, 失败理由)，理由为空串表示通过。"""
    kind = relation.get("relation_kind")
    name = "%s %s" % (kind, relation.get("relation_key"))
    left, right = relation.get("from_entity_id"), relation.get("to_entity_id")
    detail = relation.get("detail") or {}

    reason = _asm_collation_shape(relation, index)
    if reason:
        return None, reason
    source_of = {end: index["assertions"][end].get("source_id") for end in (left, right) if end}

    if kind == "addition":
        if source_of[left] != view_source:
            return None, "%s 方向不符 §25.6：from 必须是新版（%s）断言，实为 %s" % (
                name, view_source, source_of[left],
            )
    elif kind == "omission":
        if source_of[left] == view_source:
            return None, "%s 方向不符 §25.6：from 必须是旧版断言，实为新版 %s 的" % (name, view_source)
    elif source_of[left] != view_source or source_of[right] == view_source:
        return None, "%s 方向不符 §25.6：from 须为新版（%s）断言、to 须为旧版断言，实为 %s → %s" % (
            name, view_source, source_of[left], source_of[right],
        )

    key = detail.get("collation_key")
    keys = {index["assertions"][end].get("collation_key") for end in (left, right) if end}
    if not key or keys != {key}:
        return None, "%s 的 detail.collation_key=%r 与端点断言的 collation_key %r 不一致" % (
            name, key, sorted(k or "" for k in keys),
        )

    if kind == "addition":
        base_source = detail.get("absent_source_id")
        if base_source == view_source or base_source not in base_sources:
            return None, "%s 的 absent_source_id=%r 不是旧版版次" % (name, base_source)
    elif kind == "omission":
        base_source = source_of[left]
        if detail.get("absent_source_id") != view_source:
            return None, "%s 的 absent_source_id=%r 应为新版 %s" % (
                name, detail.get("absent_source_id"), view_source,
            )
    else:
        base_source = source_of[right]

    unit_id = (base_source, key)
    unit = expected.get(unit_id)
    if unit is None:
        return None, "%s 落在不可比单元上（%s@%s：任一侧未声明 / 同 source / 声明 present 无获批断言 / 同侧多条断言）" % (
            name, key, base_source,
        )
    wanted = {"pair": ("alignment", "variant_reading", "distinct_from")}.get(unit["kind"], (unit["kind"],))
    if kind not in wanted:
        return None, "%s 与推出的单元类型不符：%s@%s 应为 %s" % (name, key, base_source, "/".join(wanted))
    if unit["kind"] == "omission":
        if left != unit["old"]:
            return None, "%s 的 from=%s 不是旧版在该位置的断言 %s" % (name, left, unit["old"])
        return unit_id, ""
    if left != unit["new"] or (unit["kind"] == "pair" and right != unit["old"]):
        return None, "%s 的端点 %r → %r 与推出的断言 %r → %r 不符" % (
            name, left, right, unit["new"], unit["old"],
        )
    if unit["kind"] == "addition":
        return unit_id, ""

    mode = (relation.get("resolution") or {}).get("mode")
    if kind == "distinct_from":
        if mode != "human":
            return None, "%s 是 R07b 拒绝的落点，必须 resolution.mode=human（实为 %r）" % (name, mode)
        return unit_id, ""
    if mode != "human":
        subjects = [index["assertions"][end].get("subject_entity_id") for end in (left, right)]
        if subjects[0] is None or subjects[0] != subjects[1]:
            return None, "%s（auto）两端 subject_entity_id 须非空且相等，实为 %r（不同或为 null 应走 R07b）" % (
                name, subjects,
            )
    same_text = (
        index["assertions"][left].get("text_sha256") == index["assertions"][right].get("text_sha256")
    )
    if kind == "alignment" and not same_text:
        return None, "%s 两端 text_sha256 不同，应为 variant_reading" % name
    if kind == "variant_reading" and same_text:
        return None, "%s 两端 text_sha256 相同，应为 alignment" % name
    return unit_id, ""


def _asm_check_collation_comparable_only(
    base_knowledge: dict, views: Sequence[dict], knowledge: dict, collation: dict
) -> Tuple[bool, str]:
    """多版次对勘按 CHARTER §25 / §28 / §29 **独立重算**后逐条核对，另保留并入类关系的配对依据检查。"""
    base = base_knowledge or {}
    ledger = knowledge or {}
    index = _asm_index(ledger)
    base_index = _asm_index(base)

    # 1. 版次声明只从 editions[].collation_units 读：缺字段不许静默当空（§25.5，§29 Q9）
    for label, document in (("基底", base), ("新 knowledge", ledger)):
        for edition in document.get("editions") or []:
            if "collation_units" not in edition:
                return False, "%s editions[%s] 缺 collation_units 字段（不得当作空）" % (
                    label, edition.get("source_id"),
                )

    # 2. Snapshot 如实记下视图声明；其余版次条目与基底逐字节相同（§28 Q4）
    view_sources = {view.get("source_id") for view in views}
    base_editions = {edition.get("source_id"): edition for edition in base.get("editions") or []}
    now_editions = {edition.get("source_id"): edition for edition in ledger.get("editions") or []}
    for view in views:
        wanted = [
            {"collation_key": key, "present": present}
            for key, present in sorted(_asm_declared_presence(view).items())
        ]
        written = (now_editions.get(view.get("source_id")) or {}).get("collation_units")
        if written != wanted:
            return False, "新 knowledge 的 editions[%s].collation_units 与视图声明不一致: 写入 %r / 视图 %r" % (
                view.get("source_id"), written, wanted,
            )
    for source_id, edition in base_editions.items():
        if source_id in view_sources:
            continue
        if canonical.canonical_json(now_editions.get(source_id)) != canonical.canonical_json(edition):
            return False, "editions[%s] 不是本轮视图的版次，必须与基底逐字节相同" % source_id

    # 3. 独立重算可比单元与 not_comparable 清单（§28 Q7、§29 Q11），清单逐项比对（含理由与字段集）
    plans = {view.get("source_id"): _asm_collation_plan(base, view) for view in views}
    expected_rows = sorted(
        (row for _, rows in plans.values() for row in rows), key=_asm_not_comparable_sort_key
    )
    reported_rows = list((collation or {}).get("not_comparable") or [])
    if reported_rows != expected_rows:
        return False, "edition_collation_set.not_comparable 与 Gate 独立推出的清单不一致: 实报 %r / 推出 %r" % (
            reported_rows, expected_rows,
        )

    # 4. 任何对勘关系都须满足的形状；不涉及本轮视图的原样带过来，必须与基底逐字节相同（§29 Q8）
    for relation in ledger.get("relations") or []:
        if _asm_is_collation_relation(relation, index):
            reason = _asm_collation_shape(relation, index)
            if reason:
                return False, reason

    def carried(document: dict, document_index: Dict[str, Any]) -> List[str]:
        return sorted(
            canonical.canonical_json(relation)
            for relation in document.get("relations") or []
            if _asm_is_collation_relation(relation, document_index)
            and not _asm_relation_touches(relation, document_index, view_sources)
        )

    if carried(ledger, index) != carried(base, base_index):
        return False, "不涉及本轮视图的对勘关系必须与基底逐字节相同（不许改写也不许静默删掉）"

    # 5. 涉及视图的对勘关系逐条核（§25.6、§28、§29），并数每个单元的落点
    counts: Dict[Tuple[Any, Tuple[str, str]], int] = {}
    for relation in ledger.get("relations") or []:
        kind = relation.get("relation_kind")
        if _asm_is_collation_relation(relation, index):
            touched = [
                source_id
                for source_id in sorted(view_sources, key=str)
                if _asm_relation_touches(relation, index, {source_id})
            ]
            if not touched:
                continue  # 带过来的关系，第 4 步已验
            view_source = touched[0]
            expected, _ = plans[view_source]
            base_sources = {
                edition.get("source_id")
                for edition in base.get("editions") or []
                if edition.get("source_id") != view_source
            }
            unit_id, reason = _asm_check_collation_relation(
                relation, index, view_source, base_sources, expected
            )
            if reason:
                return False, reason
            counts[(view_source, unit_id)] = counts.get((view_source, unit_id), 0) + 1
            continue
        if kind not in _ASM_PAIRING_RELATION_KINDS:
            continue
        # alias_of / merged_into：并入类关系也要有确定性依据（校准 4，§10.1）
        endpoints = [
            entity_id
            for entity_id in (relation.get("from_entity_id"), relation.get("to_entity_id"))
            if entity_id
        ]
        if not _asm_has_pairing_basis(index, endpoints):
            return False, "%s 关系 %s 推不出确定性配对依据: %r" % (
                kind,
                relation.get("relation_key"),
                endpoints,
            )

    # 6. 完整性（反向）：每个可比单元恰一条关系，防止引擎静默漏掉对勘（§28 Q1/Q2）
    total = 0
    for view_source, (expected, _) in sorted(plans.items(), key=lambda item: str(item[0])):
        for unit_id, unit in sorted(expected.items()):
            total += 1
            got = counts.get((view_source, unit_id), 0)
            if got != 1:
                wanted = {"pair": "alignment/variant_reading/distinct_from(human)"}.get(
                    unit["kind"], unit["kind"]
                )
                return False, "完整性：单元 %s@%s（新版 %s）应恰有一条 %s 关系，实有 %d 条" % (
                    unit_id[1], unit_id[0], view_source, wanted, got,
                )
    return True, "对勘关系按 §25/§28/§29 独立重算全部吻合：%d 个可比单元各恰一条关系；not_comparable %d 项逐项一致" % (
        total,
        len(expected_rows),
    )


def _asm_check_no_silent_fold(
    base_knowledge: dict, views: Sequence[dict], knowledge: dict, identity_delta: dict
) -> Tuple[bool, str]:
    index = _asm_index(knowledge or {})
    delta_from = {
        entry.get("from_entity_id") for entry in (identity_delta or {}).get("entries") or []
    }
    missing: List[str] = []
    for school_view in (base_knowledge or {}).get("school_views") or []:
        sid = school_view.get("school_view_id")
        if sid and sid not in index["school_views"] and sid not in delta_from:
            missing.append("base:%s" % sid)
    for view in views:
        for school_view in (view.get("candidate_set") or {}).get("school_views") or []:
            sid = school_view.get("school_view_id")
            if sid and sid not in index["school_views"] and sid not in delta_from:
                missing.append("%s:%s" % (view.get("source_id"), sid))
    if missing:
        return False, "流派视图被静默折叠（既不在总账也不在 identity_delta）: %s" % sorted(missing)

    for group in (base_knowledge or {}).get("conflict_groups") or []:
        group_id = group.get("conflict_group_id")
        current = index["conflict_groups"].get(group_id)
        if current is None:
            return False, "基底冲突组 %s 在总账里消失" % group_id
        lost = sorted(
            set(group.get("member_school_view_ids") or [])
            - set(current.get("member_school_view_ids") or [])
        )
        if lost:
            return False, "基底冲突组 %s 成员减少: %r" % (group_id, lost)
    return True, "基底与视图的流派视图全部在座，基底冲突组成员未减少"


def _asm_check_identity_delta_contract(
    base_knowledge: dict,
    knowledge: dict,
    decisions: Sequence[dict],
    report: dict,
    identity_delta: dict,
) -> Tuple[bool, str]:
    entries = (identity_delta or {}).get("entries")
    if entries is None:
        return False, "identity_delta.entries 缺失"
    index = _asm_index(knowledge or {})

    # 草稿口径（CHARTER §16.1 第二条）：只认**本轮提案键**。
    # E 波退而求其次的放宽口径（总账里已落地的键 ∪ 决定 ∪ 沿用）已删掉；
    # `report` 缺 `round_proposal_keys` 时判 FAIL，不许静默退回旧口径。
    round_keys = (report or {}).get("round_proposal_keys")
    if round_keys is None:
        return False, "report 缺 round_proposal_keys：identity_delta 契约须以本轮提案集为准"
    allowed_keys = {key for key in round_keys if key}

    for entry in entries:
        change_type = entry.get("change_type")
        if change_type not in _ASM_CHANGE_TYPES:
            return False, "change_type 不在闭集 %r 内: %r" % (list(_ASM_CHANGE_TYPES), change_type)
        entity_kind = entry.get("entity_kind")
        if entity_kind not in _ASM_ENTITY_KINDS:
            return False, "entity_kind 不在闭集 %r 内: %r" % (list(_ASM_ENTITY_KINDS), entity_kind)
        reason_ref = entry.get("reason_ref") or {}
        if reason_ref.get("kind") != "proposal":
            return False, "reason_ref.kind 必须为 proposal: %r" % (reason_ref,)
        if reason_ref.get("proposal_key") not in allowed_keys:
            return False, "reason_ref.proposal_key 不在本轮提案集内: %r" % (
                reason_ref.get("proposal_key"),
            )

        to_ids = list(entry.get("to_entity_ids") or [])
        live_to = [entity_id for entity_id in to_ids if entity_id in index["alive"]]
        if change_type == "merged":
            if len(to_ids) != 1 or len(live_to) != 1:
                return False, "merged 的 to 必须恰为 1 个活对象: %r" % (to_ids,)
        elif change_type == "split":
            if len(to_ids) < 2 or len(live_to) != len(to_ids):
                return False, "split 的 to 必须 ≥ 2 且全为活对象: %r" % (to_ids,)
            allocation = entry.get("span_allocation")
            if not isinstance(allocation, dict) or not allocation:
                return False, "split 缺 span_allocation（必须覆盖旧对象且互不相交）"
            spans = [span for value in allocation.values() for span in (value or [])]
            if len(spans) != len(set(spans)):
                return False, "split 的 span_allocation 不互不相交: %r" % (allocation,)
            source = entry.get("from_entity_id")
            old = None
            for collection in _ASM_COLLECTIONS:
                if source in _asm_index(base_knowledge or {})["alive"]:
                    old = _asm_index(base_knowledge or {})[collection].get(source)
                    if old is not None:
                        break
            old_spans = _asm_entity_span_ids(old)
            if old_spans and set(spans) != old_spans:
                return False, "split 的 span_allocation 未覆盖旧对象全部 span: %r != %r" % (
                    sorted(set(spans)),
                    sorted(old_spans),
                )
        elif change_type == "retired":
            if to_ids:
                return False, "retired 的 to 必须为空: %r" % (to_ids,)
    return True, "identity_delta %d 条全符契约" % len(entries)


def _asm_check_maturity_not_synthesized(views: Sequence[dict], knowledge: dict) -> Tuple[bool, str]:
    for pattern in (knowledge or {}).get("patterns") or []:
        if "content_status" in pattern:
            return False, "pattern %s 顶层出现 content_status" % pattern.get("pattern_id")
    for concept in (knowledge or {}).get("concepts") or []:
        if "content_status" in concept:
            return False, "concept %s 顶层出现 content_status" % concept.get("concept_id")

    index = _asm_index(knowledge or {})
    for view in views:
        declared = _asm_view_candidates(view)
        approved_status = {
            item.get("entity_id"): item.get("content_status")
            for item in (view.get("reviewed_edition") or {}).get("approved") or []
        }
        for assertion in (view.get("candidate_set") or {}).get("assertions") or []:
            assertion_id = assertion.get("assertion_id")
            if assertion_id not in index["assertions"]:
                continue
            expected = approved_status.get(assertion_id, assertion.get("content_status"))
            if expected is None:
                continue
            actual = index["assertions"][assertion_id].get("content_status")
            if actual != expected:
                return False, "assertion %s 的 content_status %r ≠ 视图原值 %r" % (
                    assertion_id,
                    actual,
                    expected,
                )
        for school_view in (view.get("candidate_set") or {}).get("school_views") or []:
            sid = school_view.get("school_view_id")
            if sid not in index["school_views"]:
                continue
            expected = approved_status.get(sid, school_view.get("content_status"))
            if expected is None:
                continue
            actual = index["school_views"][sid].get("content_status")
            if actual != expected:
                return False, "school_view %s 的 content_status %r ≠ 视图原值 %r" % (
                    sid,
                    actual,
                    expected,
                )
        for kind, collection in (("pattern", "patterns"), ("concept", "concepts")):
            for entity_id, item in index[collection].items():
                candidate = declared[kind].get(entity_id)
                if candidate is None or "content_status" not in candidate:
                    continue
                expected = approved_status.get(entity_id, candidate.get("content_status"))
                for row in item.get("provenance") or []:
                    if row.get("source_id") != view.get("source_id"):
                        continue
                    if row.get("content_status") != expected:
                        return False, "%s %s 的 provenance content_status %r ≠ 视图原值 %r" % (
                            kind,
                            entity_id,
                            row.get("content_status"),
                            expected,
                        )
    return True, "Pattern/Concept 顶层无 content_status，provenance 与断言状态等于视图原值"


def _asm_check_decisions_consistent(
    base_knowledge: dict,
    knowledge: dict,
    decisions: Sequence[dict],
    identity_delta: dict,
) -> Tuple[bool, str]:
    """决定唯一，且每条决定都有落点（关系/冲突组的人工裁定 **或** 身份变更记录），
    反过来「凭空出现的 human 裁定」与「无决定的 merged/split」也一律拒收。

    CHARTER §22.1：§19.2 把合并的落点定在 IdentityDelta（不写 `merged_into` 关系），
    所以决定的落点必须把 IdentityDelta 算进来 —— 否则任何 merge/split 决定都恒不能通过。
    这不是放宽：两侧强度都保留，且新口径比旧口径多验「delta 与决定的类型必须对应」。
    `retired` 来自 R11 自动提案，**不要求**决定（它的 `reason_ref` 由 `identity_delta_contract` 验）。
    """
    keys = [decision.get("proposal_key") for decision in decisions or []]
    if len(keys) != len(set(keys)):
        return False, "决定的 proposal_key 必须唯一: %r" % (keys,)

    def human_keys(document: dict) -> Set[str]:
        out: Set[str] = set()
        for relation in (document or {}).get("relations") or []:
            resolution = relation.get("resolution") or {}
            if resolution.get("mode") == "human" and resolution.get("proposal_key"):
                out.add(resolution["proposal_key"])
        for group in (document or {}).get("conflict_groups") or []:
            for resolution in group.get("resolutions") or []:
                if (resolution or {}).get("mode") == "human" and resolution.get("proposal_key"):
                    out.add(resolution["proposal_key"])
        return out

    # 身份变更记录的落点：按理由引用的提案键归集（只数 merged / split）
    delta_by_key: Dict[str, List[dict]] = {}
    for entry in (identity_delta or {}).get("entries") or []:
        if entry.get("change_type") not in ("merged", "split"):
            continue
        reason_ref = entry.get("reason_ref") or {}
        key = reason_ref.get("proposal_key")
        if key:
            delta_by_key.setdefault(key, []).append(entry)

    identity_choices = {"merge_entities": "merged", "split": "split"}
    identity_keys: Set[str] = set()
    for decision in decisions or []:
        expected = identity_choices.get(decision.get("choice"))
        if expected is None:
            continue
        key = decision.get("proposal_key")
        identity_keys.add(key)
        matches = delta_by_key.get(key) or []
        if len(matches) != 1:
            return False, (
                "决定 %s（choice=%s）必须恰有一条与之对应的 change_type=%s 的 IdentityDelta，实为 %d 条"
                % (key, decision.get("choice"), expected, len(matches))
            )
        if matches[0].get("change_type") != expected:
            return False, (
                "决定 %s（choice=%s）对应的 IdentityDelta change_type=%r，与决定的选项不符（期望 %s）"
                % (key, decision.get("choice"), matches[0].get("change_type"), expected)
            )
    for key in sorted(delta_by_key):
        if key in identity_keys:
            continue
        return False, (
            "无决定却出现 change_type=%s 的 IdentityDelta（merged/split 只许由人工决定触发）: %s"
            % (delta_by_key[key][0].get("change_type"), key)
        )

    now_human = human_keys(knowledge)
    base_human = human_keys(base_knowledge)
    decided = {key for key in keys if key}

    not_landed = sorted(decided - now_human - identity_keys)
    if not_landed:
        return False, "有决定却没有以 mode=human 落地（也不是 merge/split 身份变更）: %r" % not_landed
    unexplained = sorted(now_human - decided - base_human)
    if unexplained:
        return False, "总账里的 human 裁定没有对应决定: %r" % unexplained
    return True, "%d 条决定与 %d 处 human 裁定 / %d 条身份变更一一对应" % (
        len(decided),
        len(now_human),
        len(identity_keys),
    )


def evaluate_assembly(
    *,
    base_knowledge: dict,
    views: Sequence[dict],
    decisions: Sequence[dict],
    knowledge: dict,
    identity_delta: dict,
    collation: dict,
    report: dict,
) -> dict:
    """M7 **独立**增量 Gate（act/impl-07/25；检查清单逐字沿用 act/06）。

    重算并核对 13 项检查，固定顺序见 :data:`ASSEMBLY_CHECK_ORDER`：

    1. `schema_and_ids` — `model.validate_snapshot_knowledge` 通过；关系键/提案键/理由键均非登记号
    2. `identity_preserved` — 基底活对象有下落（活对象或 `identity_delta.from`）；退役号不复活
    3. `allocation_monotonic` — 新发 `pat_` 号 > 基底 `id_allocation`；`id_allocation` ≥ 活对象/退役最大号
    4. `provenance_complete` — 已获批视图对象在总账里有落点（活对象或 provenance）
    5. `view_objects_unaltered` — 对照**视图**版本逐字节比对（§14.1 静默覆盖的探测器）
    6. `untouched_byte_identical` — Gate **自算闭包**之外的对象规范字节不变
    7. `affected_scope_exact` — `report.affected == 自算闭包`、`rebuilt ⊆ 闭包`、实际改动 ⊆ 闭包
    8. `collation_comparable_only` — 对勘按 CHARTER §25/§28/§29 从版次声明独立重算：关系两端、方向、
       四类内容条件、不可比单元零关系、可比单元恰一条（完整性）、not_comparable 清单逐项；并入关系有确定性依据（§10.1）
    9. `no_silent_fold` — 流派视图不被静默折叠，基底冲突组成员不减少
    10. `first_layer_display` — 每组等于任一成员的 `changes_current_judgment`
    11. `identity_delta_contract` — 变更类型/实体类型/理由引用/分裂配额均符契约
    12. `maturity_not_synthesized` — Pattern/Concept 顶层无 `content_status`，provenance 状态等于视图原值
    13. `decisions_consistent` — 决定唯一；落点（human 裁定 / merge·split 身份变更）与决定一一对应
        （CHARTER §22.1：§19.2 把合并落点改到 IdentityDelta 后，本项必须把 delta 算进来）

    `report` 只信 `affected_entity_ids` / `rebuilt_entity_ids` / `carried` / `needs_review`，
    `identity_delta` 与 `collation` 只信其契约字段；闭包与可比单元一律在 :func:`_asm_closure`
    与 `_asm_check_collation_comparable_only` 里独立重算。
    """
    base = _asm_doc(base_knowledge) or {}
    normalized_views = _asm_views(views or [])
    normalized_decisions = list(decisions or [])
    ledger = _asm_doc(knowledge) or {}
    delta = _asm_doc(identity_delta) or {}
    collation_doc = _asm_doc(collation) or {}
    report_doc = _asm_doc(report) or {}

    checks: Dict[str, Dict[str, Any]] = {}
    checks["schema_and_ids"] = _run_check(
        _asm_check_schema_and_ids, ledger, normalized_decisions, delta
    )
    checks["identity_preserved"] = _run_check(
        _asm_check_identity_preserved, base, ledger, delta
    )
    checks["allocation_monotonic"] = _run_check(
        _asm_check_allocation_monotonic, base, normalized_views, ledger
    )
    checks["provenance_complete"] = _run_check(
        _asm_check_provenance_complete, normalized_views, ledger, delta
    )
    checks["view_objects_unaltered"] = _run_check(
        _asm_check_view_objects_unaltered, normalized_views, ledger
    )
    checks["untouched_byte_identical"] = _run_check(
        _asm_check_untouched_byte_identical, base, normalized_views, normalized_decisions, ledger
    )
    checks["affected_scope_exact"] = _run_check(
        _asm_check_affected_scope_exact, base, normalized_views, normalized_decisions, ledger, report_doc
    )
    checks["collation_comparable_only"] = _run_check(
        _asm_check_collation_comparable_only, base, normalized_views, ledger, collation_doc
    )
    checks["no_silent_fold"] = _run_check(
        _asm_check_no_silent_fold, base, normalized_views, ledger, delta
    )
    checks["first_layer_display"] = _run_check(_check_first_layer_display, ledger)
    checks["identity_delta_contract"] = _run_check(
        _asm_check_identity_delta_contract, base, ledger, normalized_decisions, report_doc, delta
    )
    checks["maturity_not_synthesized"] = _run_check(
        _asm_check_maturity_not_synthesized, normalized_views, ledger
    )
    checks["decisions_consistent"] = _run_check(
        _asm_check_decisions_consistent, base, ledger, normalized_decisions, delta
    )

    return {
        "passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
    }
