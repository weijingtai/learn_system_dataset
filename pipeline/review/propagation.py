import json
from pipeline.review.model import content_hash

SPAN_COMPARE_KEYS = ("text", "source_anchor")
THRESHOLD_RATIO = 0.30
THRESHOLD_ROUND = 3

def changed_span_ids(old_spans_doc: dict, new_spans_doc: dict) -> dict:
    old_spans = old_spans_doc.get("spans", {})
    new_spans = new_spans_doc.get("spans", {})
    
    changed = []
    removed = []
    added = []
    
    for sid, old_s in old_spans.items():
        if sid not in new_spans:
            removed.append(sid)
        else:
            new_s = new_spans[sid]
            old_subset = {k: old_s[k] for k in SPAN_COMPARE_KEYS if k in old_s}
            new_subset = {k: new_s[k] for k in SPAN_COMPARE_KEYS if k in new_s}
            if json.dumps(old_subset, sort_keys=True, ensure_ascii=False) != json.dumps(new_subset, sort_keys=True, ensure_ascii=False):
                changed.append(sid)
                
    for sid in new_spans:
        if sid not in old_spans:
            added.append(sid)
            
    return {
        "changed": sorted(changed),
        "removed": sorted(removed),
        "added": sorted(added)
    }

def reachable_entities(candidates: list[dict], affected_span_ids: list[str]) -> list[str]:
    affected = set(affected_span_ids)
    reachable = set()
    
    # Direct
    for c in candidates:
        obj = c["source_object"]
        for ev in obj.get("evidence", []):
            if ev.get("source_span_id") in affected:
                reachable.add(c["entity_id"])
        for ref in obj.get("source_refs", []):
            if ref.get("source_span_id") in affected:
                reachable.add(c["entity_id"])
                
    # Transitive
    changed = True
    while changed:
        changed = False
        for c in candidates:
            eid = c["entity_id"]
            if eid in reachable:
                continue
            obj = c["source_object"]
            if obj.get("subject_entity_id") in reachable:
                reachable.add(eid)
                changed = True
            for cr in obj.get("claim_refs", []):
                if cr.get("entity_id") in reachable:
                    reachable.add(eid)
                    changed = True
                    
    return sorted(list(reachable))

def propagate(*, old_candidates: list[dict], old_spans_doc: dict, new_spans_doc: dict, validation_entries: list[dict], standing_decisions: list[dict], rework_round_before: int, trigger_correction_request_revision_id: str) -> dict:
    diff = changed_span_ids(old_spans_doc, new_spans_doc)
    affected = set(diff["changed"]) | set(diff["removed"])
    
    reachable_eids = reachable_entities(old_candidates, list(affected))
    reachable_set = set(reachable_eids)
    
    invalidated = []
    
    candidate_by_id = {}
    for c in old_candidates:
        candidate_by_id[c["entity_id"]] = c
        if c["entity_id"] in reachable_set:
            invalidated.append({
                "kind": "candidate",
                "entity_id": c["entity_id"],
                "revision_id": c["candidate_revision_id"]
            })
            
    invalidated.sort(key=lambda x: x["entity_id"])
    
    val_invalidated = []
    for ve in validation_entries:
        if ve["entity_id"] in reachable_set:
            val_invalidated.append({
                "kind": "validation_entry",
                "entity_id": ve["entity_id"],
                "revision_id": None,
                "check": ve.get("check")
            })
    val_invalidated.sort(key=lambda x: (x["entity_id"], x.get("check", "")))
    invalidated.extend(val_invalidated)
    
    carried_forward = []
    for c in old_candidates:
        if c["entity_id"] not in reachable_set:
            carried_forward.append({
                "kind": "candidate",
                "entity_id": c["entity_id"],
                "revision_id": c["candidate_revision_id"],
                "carried_from_revision_id": c["candidate_revision_id"]
            })
            
    needs_review = []
    removed_set = set(diff["removed"])
    
    standing_decisions = sorted(standing_decisions, key=lambda x: x["queue_item_id"])
    
    for d in standing_decisions:
        target = d["target_entity_id"]
        if target not in reachable_set:
            carried_forward.append({
                "kind": "decision",
                "entity_id": target,
                "revision_id": d["decision_revision_id"],
                "carried_from_revision_id": d["seen_artifact_revision_id"]
            })
        else:
            c = candidate_by_id.get(target)
            if c is None:
                continue
                
            has_removed = False
            obj = c["source_object"]
            for ev in obj.get("evidence", []):
                if ev.get("source_span_id") in removed_set:
                    has_removed = True
            for ref in obj.get("source_refs", []):
                if ref.get("source_span_id") in removed_set:
                    has_removed = True
                    
            if has_removed:
                needs_review.append({
                    "decision_revision_id": d["decision_revision_id"],
                    "target_entity_id": target,
                    "queue_item_id": d["queue_item_id"],
                    "reason": "target_removed"
                })
            else:
                old_hash = content_hash(c, old_spans_doc.get("spans", {}))
                new_hash = content_hash(c, new_spans_doc.get("spans", {}))
                if old_hash == new_hash:
                    carried_forward.append({
                        "kind": "decision",
                        "entity_id": target,
                        "revision_id": d["decision_revision_id"],
                        "carried_from_revision_id": d["seen_artifact_revision_id"]
                    })
                else:
                    needs_review.append({
                        "decision_revision_id": d["decision_revision_id"],
                        "target_entity_id": target,
                        "queue_item_id": d["queue_item_id"],
                        "reason": "content_changed"
                    })
                    
    valid_object_count = len(old_candidates) + len(validation_entries)
    ratio = round(len(invalidated) / valid_object_count, 4) if valid_object_count > 0 else 0.0
    
    rework_round = rework_round_before + 1
    warnings = []
    if rework_round >= THRESHOLD_ROUND or ratio >= THRESHOLD_RATIO:
        warnings.append("rework_threshold_exceeded")
        
    affected_queues = ["m6"] if len(needs_review) > 0 else []
    
    return {
        "schema_version": "1.0.0",
        "trigger_correction_request_revision_id": trigger_correction_request_revision_id,
        "rework_round": rework_round,
        "changed_span_ids": diff["changed"],
        "removed_span_ids": diff["removed"],
        "reachable_entity_ids": reachable_eids,
        "invalidated": invalidated,
        "carried_forward": carried_forward,
        "needs_review": needs_review,
        "invalidated_count": len(invalidated),
        "carried_forward_count": len(carried_forward),
        "needs_review_count": len(needs_review),
        "valid_object_count": valid_object_count,
        "invalidated_ratio": ratio,
        "warnings": warnings,
        "affected_queues": affected_queues
    }
