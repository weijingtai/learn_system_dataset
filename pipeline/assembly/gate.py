"""M7 独立创世 Gate evaluate_genesis（spec §15, §20.5, act/g0-03）。

纯函数；禁止 import genesis，自行从 candidate_set 与 reviewed_edition 独立重算身份与保真。
"""

import copy
import re
from typing import Any, Dict, Tuple

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
