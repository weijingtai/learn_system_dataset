import json
import hashlib
from pipeline.review.errors import ReviewRefused
from pipeline.ledger.errors import InvalidIdentifier, DuplicateIdentifier, SchemaViolation, MissingReference
from pipeline.ledger.ids import validate
from pipeline.knowledge_extraction.review_events import required_decision_types, build_review_decision
from pipeline.review import CANDIDATE_KINDS, STANDINGS

NON_CONTENT_KEYS = ("candidate_revision_id", "content_status", "origin")
APPROVED_CONTENT_STATUS = "expert_verified"
ENTITY_ID_KINDS = {"assertion": "assertion_id", "school_view": "school_view_id"}

def queue_item_id(entity_id: str, decision_type: str) -> str:
    return f"{entity_id}#{decision_type}"

def required_types(candidate: dict) -> list[str]:
    return list(required_decision_types(candidate["source_object"], entity_kind=candidate["kind"]))

def build_review_queue(*, candidates: list[dict], seen_revision_id: str) -> list[dict]:
    validate("artifact_revision_id", seen_revision_id)
    seen_ids = set()
    queue = []
    
    for candidate in candidates:
        entity_id = candidate["entity_id"]
        kind = candidate["kind"]
        
        if kind not in CANDIDATE_KINDS:
            raise ReviewRefused(f"Unknown kind {kind}", code="SCH_002")
            
        try:
            validate(ENTITY_ID_KINDS[kind], entity_id)
        except InvalidIdentifier as e:
            raise InvalidIdentifier(f"Invalid id {entity_id}", code="ID_001")
            
        if entity_id in seen_ids:
            raise DuplicateIdentifier(f"Duplicate entity_id {entity_id}", code="ID_002")
        seen_ids.add(entity_id)
        
        req_types = required_types(candidate)
        if not req_types:
            raise SchemaViolation("Empty required_types", code="SCH_002")
            
        for dt in req_types:
            queue.append({
                "queue_item_id": queue_item_id(entity_id, dt),
                "target_entity_id": entity_id,
                "kind": kind,
                "decision_type": dt,
                "seen_artifact_revision_id": seen_revision_id
            })
            
    return queue

def decision_event(*, queue_item: dict, seen_artifact_revision_id: str, processing_run_id: str, step_run_id: str, verdict: str, rationale: str, actor_ref: str, evidence_refs: tuple = (), consumption_level: str = "INTERNAL_DEMO") -> dict:
    if not rationale:
        raise SchemaViolation("Rationale cannot be empty", code="SCH_002")
    return build_review_decision(
        decision_type=queue_item["decision_type"],
        verdict=verdict,
        entity_kind=queue_item["kind"],
        entity_id=queue_item["target_entity_id"],
        seen_artifact_revision_id=seen_artifact_revision_id,
        processing_run_id=processing_run_id,
        step_run_id=step_run_id,
        actor_ref=actor_ref,
        rationale=rationale,
        evidence_refs=evidence_refs,
        consumption_level=consumption_level
    )

def event_bytes(event: dict) -> bytes:
    return json.dumps(event, sort_keys=True, ensure_ascii=False).encode("utf-8")

def decision_entry(*, decision_revision_id: str, queue_item: dict, event: dict = None, standing: str = "active", carried_from_revision_id: str = None, carried_to_revision_id: str = None, carried_content_hash: str = None, modified_revision_id: str = None) -> dict:
    if standing == "active":
        if event is None:
            raise ValueError("event required for active standing")
        if event["event_kind"] != "review_decision":
            raise ValueError("event_kind must be review_decision")
        if event["target"]["entity_id"] != queue_item["target_entity_id"]:
            raise ValueError("entity_id mismatch")
        if event["target"]["artifact_revision_id"] != queue_item["seen_artifact_revision_id"]:
            raise ValueError("seen_artifact_revision_id mismatch")
            
        verdict = event["verdict"]
        if verdict == "modify":
            if modified_revision_id is None:
                raise ReviewRefused("modify requires modified_revision_id", code="SCH_001")
            validate("artifact_revision_id", modified_revision_id)
        else:
            if modified_revision_id is not None:
                raise ReviewRefused("only modify allows modified_revision_id", code="SCH_001")
                
        if carried_from_revision_id is not None or carried_to_revision_id is not None or carried_content_hash is not None:
            raise ValueError("carried fields must be None for active standing")
            
        seen_rev = event["target"]["artifact_revision_id"]
        rationale = event["rationale"]
        
    elif standing == "carried_forward":
        if event is None:
            raise ValueError("event required for carried_forward standing")
        seen_rev = event["target"]["artifact_revision_id"]
        
        if carried_to_revision_id != queue_item["seen_artifact_revision_id"]:
            raise ValueError("carried_to_revision_id mismatch")
        validate("artifact_revision_id", carried_to_revision_id)
        
        if carried_from_revision_id != decision_revision_id:
            raise ValueError("carried_from_revision_id mismatch")
        validate("artifact_revision_id", carried_from_revision_id)
        
        if carried_content_hash is None:
            raise ValueError("carried_content_hash is required")
            
        verdict = event["verdict"]
        # 第 74 条：carried modify 必须保留首审封存的 reviewed_candidate 修订
        if verdict == "modify":
            if modified_revision_id is None:
                raise ReviewRefused("carried modify requires modified_revision_id", code="SCH_001")
            validate("artifact_revision_id", modified_revision_id)
        elif modified_revision_id is not None:
            raise ReviewRefused("only modify allows modified_revision_id", code="SCH_001")
        
        rationale = event["rationale"]
        
    elif standing == "needs_review":
        seen_rev = queue_item["seen_artifact_revision_id"]
        if carried_from_revision_id is not None or carried_to_revision_id is not None or carried_content_hash is not None:
            raise ValueError("carried fields must be None for needs_review")
        verdict = None
        rationale = None
    else:
        raise ValueError("Invalid standing")

    return {
        "decision_revision_id": decision_revision_id,
        "queue_item_id": queue_item["queue_item_id"],
        "target_entity_id": queue_item["target_entity_id"],
        "kind": queue_item["kind"],
        "decision_type": queue_item["decision_type"],
        "verdict": verdict,
        "standing": standing,
        "seen_revision_id": seen_rev,
        "modified_revision_id": modified_revision_id,
        "carried_from_revision_id": carried_from_revision_id,
        "carried_to_revision_id": carried_to_revision_id,
        "carried_content_hash": carried_content_hash,
        "rationale": rationale
    }

def normalize_content(candidate: dict, spans_by_id: dict) -> bytes:
    obj = dict(candidate["source_object"])
    for k in NON_CONTENT_KEYS:
        obj.pop(k, None)
        
    if "evidence" in obj:
        evidence_quotes = []
        for l in obj["evidence"]:
            span_id = l["source_span_id"]
            if span_id not in spans_by_id:
                raise MissingReference("Missing span", code="REF_001")
            text = spans_by_id[span_id]["text"]
            start = l["start"]
            end = l["end"]
            if not (0 <= start < end <= len(text)):
                raise SchemaViolation("Invalid offsets", code="SCH_002")
            evidence_quotes.append({
                "source_span_id": span_id,
                "quote": text[start:end]
            })
        obj["evidence_quotes"] = evidence_quotes
        
    if "source_refs" in obj:
        source_quotes = []
        for s in obj["source_refs"]:
            span_id = s["source_span_id"]
            if span_id not in spans_by_id:
                raise MissingReference("Missing span", code="REF_001")
            source_quotes.append({
                "source_span_id": span_id,
                "quote": spans_by_id[span_id]["text"]
            })
        obj["source_quotes"] = source_quotes
        
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

def content_hash(candidate: dict, spans_by_id: dict) -> str:
    return hashlib.sha256(normalize_content(candidate, spans_by_id)).hexdigest()

def fold_decisions(queue: list[dict], decision_entries: list[dict]) -> dict:
    folded = {item["queue_item_id"]: None for item in queue}
    valid_entity_ids = {item["queue_item_id"]: item["target_entity_id"] for item in queue}
    queue_seen_revs = {item["queue_item_id"]: item["seen_artifact_revision_id"] for item in queue}
    
    for entry in decision_entries:
        qid = entry["queue_item_id"]
        if qid not in folded:
            raise ReviewRefused("Item not in queue", code="REF_001")
        if entry["target_entity_id"] != valid_entity_ids[qid]:
            raise ReviewRefused("entity_id mismatch", code="REF_001")
            
        standing = entry["standing"]
        if standing in ("active", "needs_review"):
            if entry["seen_revision_id"] != queue_seen_revs[qid]:
                raise ReviewRefused("seen_revision mismatch", code="REF_001")
        elif standing == "carried_forward":
            if entry.get("carried_to_revision_id") != queue_seen_revs[qid]:
                raise ReviewRefused("carried_to_revision mismatch", code="REF_001")
                
        folded[qid] = entry
        
    return folded

def outcome(queue: list[dict], folded: dict) -> dict:
    groups = {}
    for item in queue:
        eid = item["target_entity_id"]
        if eid not in groups:
            groups[eid] = []
        groups[eid].append(item["queue_item_id"])
        
    out = {"approved": [], "rejected": [], "unresolved": []}
    
    for eid, qids in groups.items():
        is_unresolved = False
        is_rejected = False
        
        for qid in qids:
            entry = folded[qid]
            if entry is None or entry.get("verdict") == "request_evidence" or entry.get("standing") == "needs_review":
                out["unresolved"].append(qid)
                is_unresolved = True
            elif not is_unresolved:
                if entry.get("verdict") == "reject":
                    is_rejected = True
                    
        if is_unresolved:
            continue
        if is_rejected:
            out["rejected"].append(eid)
        else:
            out["approved"].append(eid)
            
    return out
