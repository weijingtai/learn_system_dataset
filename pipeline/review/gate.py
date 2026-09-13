import hashlib
import re

DECISION_TYPES = {
    "review_source_fidelity",
    "review_school_attribution",
    "review_logical_consistency",
    "review_technique_usage",
    "review_conflict_resolution",
    "review_knowledge_boundary",
    "review_homograph_disambiguation",
    "review_formatting"
}

VERDICTS = {"accept", "modify", "reject", "request_evidence", "school_dispute"}
STANDINGS = {"active", "carried_forward", "needs_review"}
HEX32_REGEX = re.compile(r"^rev_[0-9a-f]{32}$")

def evaluate_review(*, candidate_objects: list[dict], seen_revision_id: str, validation_package: dict, corpus_spans_doc: dict, decision_entries: list[dict], prior_decision_events: list[dict] = (), reviewed_edition: dict) -> dict:
    checks = {
        "validation_intake": {"passed": False, "detail": ""},
        "queue_coverage": {"passed": False, "detail": ""},
        "decision_anchoring": {"passed": False, "detail": ""},
        "decision_closed_sets": {"passed": False, "detail": ""},
        "zero_unresolved": {"passed": False, "detail": ""},
        "outcome_consistency": {"passed": False, "detail": ""},
        "evidence_closure": {"passed": False, "detail": ""},
        "school_divergence": {"passed": False, "detail": ""},
        "package_counts": {"passed": False, "detail": ""}
    }
    
    # validation_intake
    if validation_package.get("gate", {}).get("passed") is True and validation_package.get("scope") == "corpus_only":
        checks["validation_intake"]["passed"] = True
    else:
        checks["validation_intake"]["detail"] = "M5 package gate not passed or scope not corpus_only"

    # queue_coverage
    expected_queue = set()
    candidate_by_id = {}
    for c in candidate_objects:
        eid = c["entity_id"]
        candidate_by_id[eid] = c
        for dt in c.get("required_decision_types", []):
            expected_queue.add(f"{eid}#{dt}")
            
    actual_queue = {e["queue_item_id"] for e in decision_entries}
    if expected_queue == actual_queue:
        checks["queue_coverage"]["passed"] = True
    else:
        checks["queue_coverage"]["detail"] = "Queue items mismatch"

    # decision_anchoring
    anchoring_ok = True
    prior_by_decision_rev = {pe["decision_revision_id"]: pe for pe in prior_decision_events}
    
    for e in decision_entries:
        if e["target_entity_id"] not in candidate_by_id:
            anchoring_ok = False
            break
            
        if not (e.get("decision_revision_id") and HEX32_REGEX.match(e["decision_revision_id"])):
            anchoring_ok = False
            break
            
        is_modify = (e.get("verdict") == "modify")
        mod_rev = e.get("modified_revision_id")
        if is_modify:
            if not (mod_rev and HEX32_REGEX.match(mod_rev)):
                anchoring_ok = False
                break
        else:
            if mod_rev is not None:
                anchoring_ok = False
                break
                
        standing = e.get("standing")
        if standing == "active":
            if e.get("seen_revision_id") != seen_revision_id:
                anchoring_ok = False
                break
            if e.get("carried_from_revision_id") is not None or e.get("carried_to_revision_id") is not None or e.get("carried_content_hash") is not None:
                anchoring_ok = False
                break
        elif standing == "carried_forward":
            if e.get("carried_to_revision_id") != seen_revision_id:
                anchoring_ok = False
                break
            cf_rev = e.get("carried_from_revision_id")
            if not cf_rev or cf_rev not in prior_by_decision_rev:
                anchoring_ok = False
                break
            if prior_by_decision_rev[cf_rev].get("seen_revision_id") != e.get("seen_revision_id"):
                anchoring_ok = False
                break
            if e.get("carried_content_hash") != candidate_by_id[e["target_entity_id"]].get("content_hash"):
                anchoring_ok = False
                break
            if mod_rev is not None:
                anchoring_ok = False
                break
                
    if anchoring_ok:
        checks["decision_anchoring"]["passed"] = True

    # decision_closed_sets
    closed_sets_ok = True
    for e in decision_entries:
        if e.get("decision_type") not in DECISION_TYPES:
            closed_sets_ok = False
            break
        if e.get("verdict") not in VERDICTS:
            closed_sets_ok = False
            break
        if e.get("standing") not in STANDINGS:
            closed_sets_ok = False
            break
        if not e.get("rationale"):
            closed_sets_ok = False
            break
            
    if closed_sets_ok:
        checks["decision_closed_sets"]["passed"] = True

    # zero_unresolved
    zero_ok = True
    if reviewed_edition.get("unresolved_count") != 0:
        zero_ok = False
        
    counts_per_queue_item = {}
    for e in decision_entries:
        counts_per_queue_item[e["queue_item_id"]] = counts_per_queue_item.get(e["queue_item_id"], 0) + 1
        if e.get("verdict") == "request_evidence" or e.get("standing") == "needs_review":
            zero_ok = False
            
    if any(c != 1 for c in counts_per_queue_item.values()):
        zero_ok = False
        
    if zero_ok:
        checks["zero_unresolved"]["passed"] = True

    # outcome_consistency
    decisions_by_entity = {}
    for e in decision_entries:
        eid = e["target_entity_id"]
        decisions_by_entity.setdefault(eid, []).append(e)
        
    derived_approved = []
    derived_rejected = []
    
    for eid, group in decisions_by_entity.items():
        if any(e.get("verdict") == "reject" for e in group):
            derived_rejected.append(eid)
        elif all(e.get("verdict") in ("accept", "modify") for e in group):
            derived_approved.append(eid)
            
    derived_approved.sort()
    derived_rejected.sort()
    
    rev_approved_eids = sorted([x["entity_id"] for x in reviewed_edition.get("approved", [])])
    rev_rejected_eids = sorted(reviewed_edition.get("rejected", []))
    
    status_ok = all(x.get("content_status") == "expert_verified" for x in reviewed_edition.get("approved", []))
    union_set = set(derived_approved) | set(derived_rejected)
    all_c_set = set(candidate_by_id.keys())
    
    if derived_approved == rev_approved_eids and derived_rejected == rev_rejected_eids and status_ok and union_set == all_c_set:
        checks["outcome_consistency"]["passed"] = True

    # evidence_closure
    closure_ok = True
    spans_dict = corpus_spans_doc.get("spans", {})
    ev_links = reviewed_edition.get("evidence_links", [])
    ev_by_eid = {}
    for link in ev_links:
        ev_by_eid.setdefault(link["entity_id"], []).append(link)
        
    for x in reviewed_edition.get("approved", []):
        eid = x["entity_id"]
        c = candidate_by_id.get(eid)
        if c and c.get("kind") == "assertion":
            links = ev_by_eid.get(eid, [])
            if len(links) < 1:
                closure_ok = False
                break
            for link in links:
                span_id = link.get("source_span_id")
                if span_id not in spans_dict:
                    closure_ok = False
                    break
                text = spans_dict[span_id].get("text", "")
                start = link.get("start", 0)
                end = link.get("end", len(text))
                quote = text[start:end]
                if hashlib.sha256(quote.encode("utf-8")).hexdigest() != link.get("quote_sha256"):
                    closure_ok = False
                    break
                    
    if closure_ok:
        checks["evidence_closure"]["passed"] = True

    # school_divergence
    div_ok = True
    sv_ed = {x["entity_id"]: x for x in reviewed_edition.get("school_views", [])}
    for x in reviewed_edition.get("approved", []):
        eid = x["entity_id"]
        c = candidate_by_id.get(eid)
        if c and c.get("kind") == "school_view":
            if eid not in sv_ed:
                div_ok = False
                break
            if sv_ed[eid].get("conflict_group_id") != c.get("conflict_group_id"):
                div_ok = False
                break
                
    if div_ok:
        checks["school_divergence"]["passed"] = True

    # package_counts
    if len(reviewed_edition.get("approved", [])) + len(reviewed_edition.get("rejected", [])) == len(candidate_objects) and len(decision_entries) == len(expected_queue):
        checks["package_counts"]["passed"] = True

    review_passed = all(v["passed"] for v in checks.values())
    
    return {
        "review": "passed" if review_passed else "failed",
        "checks": checks
    }
