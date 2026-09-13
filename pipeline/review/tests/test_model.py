import unittest
import json
import hashlib
from pipeline.review import model
from pipeline.review.errors import ReviewRefused
from pipeline.ledger.errors import InvalidIdentifier, DuplicateIdentifier, SchemaViolation, MissingReference

class TestReviewModel(unittest.TestCase):
    def setUp(self):
        self.spans_by_id = {
            "p0003_s04": {"text": "《四书章句集注》所言…", "geometry": {}},
            "p0003_s08": {"text": "朱熹在《大学章句》中明确指出…", "geometry": {}},
            "p0003_s03": {"text": "这并非简单的字面对应…", "geometry": {}},
            "p0003_s05": {"text": "其实不然…", "geometry": {}},
            "p0001_s02": {"text": "孔门弟子多如此认为。", "geometry": {}},
        }
        
        self.c1 = {
            "entity_id": "as_qizheng_000001",
            "kind": "assertion",
            "source_object": {
                "assertion_id": "as_qizheng_000001",
                "text": "…",
                "evidence": [
                    {"source_span_id": "p0003_s04", "start": 0, "end": 4},
                    {"source_span_id": "p0003_s08", "start": 0, "end": 2}
                ]
            }
        }
        self.c2 = {
            "entity_id": "as_qizheng_000002",
            "kind": "assertion",
            "source_object": {
                "assertion_id": "as_qizheng_000002",
                "text": "…",
                "evidence": [
                    {"source_span_id": "p0003_s03", "start": 0, "end": 3},
                    {"source_span_id": "p0003_s05", "start": 0, "end": 4}
                ]
            }
        }
        self.c3 = {
            "entity_id": "as_qizheng_000003",
            "kind": "assertion",
            "source_object": {
                "assertion_id": "as_qizheng_000003",
                "text": "…",
                "evidence": [
                    {"source_span_id": "p0001_s02", "start": 0, "end": 4}
                ]
            }
        }
        self.c4 = {
            "entity_id": "sv_00000000000000000000000000000001",
            "kind": "school_view",
            "source_object": {
                "school_view_id": "sv_00000000000000000000000000000001",
                "school": "zhuxi",
                "text": "…",
                "source_refs": [
                    {"source_id": "sc_001", "source_span_id": "p0003_s08"}
                ]
            }
        }
        self.candidates = [self.c1, self.c2, self.c3, self.c4]
        self.seen_revision = "rev_11111111111111111111111111111111"

    def test_queue_five_items_ids_and_order(self):
        queue = model.build_review_queue(candidates=self.candidates, seen_revision_id=self.seen_revision)
        self.assertEqual(len(queue), 5)
        # c1
        self.assertEqual(queue[0]["queue_item_id"], "as_qizheng_000001#review_source_fidelity")
        self.assertEqual(queue[0]["target_entity_id"], "as_qizheng_000001")
        self.assertEqual(queue[0]["kind"], "assertion")
        self.assertEqual(queue[0]["decision_type"], "review_source_fidelity")
        self.assertEqual(queue[0]["seen_artifact_revision_id"], self.seen_revision)
        # c4 has two
        self.assertEqual(queue[3]["queue_item_id"], "sv_00000000000000000000000000000001#review_source_fidelity")
        self.assertEqual(queue[4]["queue_item_id"], "sv_00000000000000000000000000000001#review_school_attribution")
        
        # Check key order
        expected_keys = ["queue_item_id", "target_entity_id", "kind", "decision_type", "seen_artifact_revision_id"]
        self.assertEqual(list(queue[0].keys()), expected_keys)

    def test_queue_deterministic_twice(self):
        q1 = model.build_review_queue(candidates=self.candidates, seen_revision_id=self.seen_revision)
        q2 = model.build_review_queue(candidates=self.candidates, seen_revision_id=self.seen_revision)
        self.assertEqual(q1, q2)

    def test_queue_uses_review_events_required_decision_types(self):
        reqs1 = model.required_types(self.c1)
        self.assertEqual(reqs1, ["review_source_fidelity"])
        reqs4 = model.required_types(self.c4)
        self.assertEqual(reqs4, ["review_source_fidelity", "review_school_attribution"])

    def test_queue_invalid_entity_id_ID_001(self):
        bad_c = {"entity_id": "bad", "kind": "assertion", "source_object": {"assertion_id": "bad", "evidence": []}}
        with self.assertRaises(InvalidIdentifier) as ctx:
            model.build_review_queue(candidates=[bad_c], seen_revision_id=self.seen_revision)
        self.assertEqual(ctx.exception.code, "ID_001")

    def test_queue_duplicate_entity_ID_002(self):
        with self.assertRaises(DuplicateIdentifier) as ctx:
            model.build_review_queue(candidates=[self.c1, self.c1], seen_revision_id=self.seen_revision)
        self.assertEqual(ctx.exception.code, "ID_002")

    def test_queue_unknown_kind_SCH_002(self):
        bad_c = {"entity_id": "as_qizheng_000001", "kind": "unknown", "source_object": {}}
        with self.assertRaises(ReviewRefused) as ctx:
            model.build_review_queue(candidates=[bad_c], seen_revision_id=self.seen_revision)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_decision_event_matches_review_events_key_order(self):
        q_item = {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        ev = model.decision_event(queue_item=q_item, seen_artifact_revision_id=self.seen_revision, processing_run_id="prun_11111111111111111111111111111111", step_run_id="srun_11111111111111111111111111111111", verdict="accept", rationale="ok", actor_ref="user_1")
        self.assertEqual(ev["event_kind"], "review_decision")
        self.assertEqual(ev["decision_type"], "review_source_fidelity")
        self.assertEqual(ev["target"]["entity_id"], "as_qizheng_000001")

    def test_decision_event_has_no_standing_key(self):
        q_item = {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        ev = model.decision_event(queue_item=q_item, seen_artifact_revision_id=self.seen_revision, processing_run_id="prun_11111111111111111111111111111111", step_run_id="srun_11111111111111111111111111111111", verdict="accept", rationale="ok", actor_ref="user_1")
        self.assertNotIn("standing", ev)

    def test_decision_entry_seen_anchor_and_modify_modified_revision(self):
        q_item = {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        ev = model.decision_event(queue_item=q_item, seen_artifact_revision_id=self.seen_revision, processing_run_id="prun_11111111111111111111111111111111", step_run_id="srun_11111111111111111111111111111111", verdict="modify", rationale="ok", actor_ref="user_1")
        entry = model.decision_entry(decision_revision_id="rev_22222222222222222222222222222222", queue_item=q_item, event=ev, standing="active", modified_revision_id="rev_33333333333333333333333333333333")
        self.assertEqual(entry["seen_revision_id"], self.seen_revision)
        self.assertEqual(entry["modified_revision_id"], "rev_33333333333333333333333333333333")
        self.assertEqual(entry["verdict"], "modify")

    def test_decision_entry_accept_forbids_modified_revision(self):
        q_item = {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        ev = model.decision_event(queue_item=q_item, seen_artifact_revision_id=self.seen_revision, processing_run_id="prun_11111111111111111111111111111111", step_run_id="srun_11111111111111111111111111111111", verdict="accept", rationale="ok", actor_ref="user_1")
        with self.assertRaises(ReviewRefused):
            model.decision_entry(decision_revision_id="rev_22222222222222222222222222222222", queue_item=q_item, event=ev, standing="active", modified_revision_id="rev_33333333333333333333333333333333")

    def test_decision_entry_modify_requires_modified_revision(self):
        q_item = {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        ev = model.decision_event(queue_item=q_item, seen_artifact_revision_id=self.seen_revision, processing_run_id="prun_11111111111111111111111111111111", step_run_id="srun_11111111111111111111111111111111", verdict="modify", rationale="ok", actor_ref="user_1")
        with self.assertRaises(ReviewRefused):
            model.decision_entry(decision_revision_id="rev_22222222222222222222222222222222", queue_item=q_item, event=ev, standing="active")

    def test_decision_entry_active_forbids_carried_fields(self):
        q_item = {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        ev = model.decision_event(queue_item=q_item, seen_artifact_revision_id=self.seen_revision, processing_run_id="prun_11111111111111111111111111111111", step_run_id="srun_11111111111111111111111111111111", verdict="accept", rationale="ok", actor_ref="user_1")
        with self.assertRaises(Exception):
            model.decision_entry(decision_revision_id="rev_22222222222222222222222222222222", queue_item=q_item, event=ev, standing="active", carried_to_revision_id=self.seen_revision)

    def test_decision_entry_carried_keeps_old_seen_and_carried_to(self):
        old_seen = "rev_00000000000000000000000000000000"
        q_item = {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        ev = model.decision_event(queue_item=q_item, seen_artifact_revision_id=old_seen, processing_run_id="prun_11111111111111111111111111111111", step_run_id="srun_11111111111111111111111111111111", verdict="accept", rationale="ok", actor_ref="user_1")
        
        entry = model.decision_entry(decision_revision_id="rev_12345678901234561234567890123456", queue_item=q_item, event=ev, standing="carried_forward", carried_from_revision_id="rev_12345678901234561234567890123456", carried_to_revision_id=self.seen_revision, carried_content_hash="hash_1")
        self.assertEqual(entry["seen_revision_id"], old_seen)
        self.assertEqual(entry["carried_to_revision_id"], self.seen_revision)
        self.assertEqual(entry["carried_from_revision_id"], "rev_12345678901234561234567890123456")

    def test_decision_entry_carried_requires_carried_from_and_content_hash(self):
        old_seen = "rev_00000000000000000000000000000000"
        q_item = {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        ev = model.decision_event(queue_item=q_item, seen_artifact_revision_id=old_seen, processing_run_id="prun_11111111111111111111111111111111", step_run_id="srun_11111111111111111111111111111111", verdict="accept", rationale="ok", actor_ref="user_1")
        with self.assertRaises(Exception):
            model.decision_entry(decision_revision_id="rev_22222222222222222222222222222222", queue_item=q_item, event=ev, standing="carried_forward", carried_to_revision_id=self.seen_revision)

    def test_decision_empty_rationale_rejected(self):
        q_item = {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        with self.assertRaises(SchemaViolation):
            model.decision_event(queue_item=q_item, seen_artifact_revision_id=self.seen_revision, processing_run_id="prun_11111111111111111111111111111111", step_run_id="srun_11111111111111111111111111111111", verdict="accept", rationale="", actor_ref="user_1")

    def test_decision_school_dispute_requires_school_attribution(self):
        # We assume pipeline.knowledge_extraction.review_events checks this. Let's just pass invalid combo.
        q_item = {"queue_item_id": "sv_00000000000000000000000000000001#review_source_fidelity", "target_entity_id": "sv_00000000000000000000000000000001", "kind": "school_view", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        with self.assertRaises(SchemaViolation):
            model.decision_event(queue_item=q_item, seen_artifact_revision_id=self.seen_revision, processing_run_id="prun_11111111111111111111111111111111", step_run_id="srun_11111111111111111111111111111111", verdict="school_dispute", rationale="dispute", actor_ref="user_1")

    def test_decision_invalid_verdict_rejected(self):
        q_item = {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        with self.assertRaises(SchemaViolation):
            model.decision_event(queue_item=q_item, seen_artifact_revision_id=self.seen_revision, processing_run_id="prun_11111111111111111111111111111111", step_run_id="srun_11111111111111111111111111111111", verdict="unknown", rationale="ok", actor_ref="user_1")

    def test_fold_carried_entry_seen_mismatch_allowed(self):
        q_item = {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        queue = [q_item]
        entry = {
            "queue_item_id": "as_qizheng_000001#review_source_fidelity",
            "target_entity_id": "as_qizheng_000001",
            "standing": "carried_forward",
            "seen_revision_id": "rev_00000000000000000000000000000000",
            "carried_to_revision_id": self.seen_revision
        }
        folded = model.fold_decisions(queue, [entry])
        self.assertEqual(folded["as_qizheng_000001#review_source_fidelity"], entry)

    def test_fold_active_entry_seen_mismatch_REF_001(self):
        q_item = {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        queue = [q_item]
        entry = {
            "queue_item_id": "as_qizheng_000001#review_source_fidelity",
            "target_entity_id": "as_qizheng_000001",
            "standing": "active",
            "seen_revision_id": "rev_00000000000000000000000000000000"
        }
        with self.assertRaises(ReviewRefused) as ctx:
            model.fold_decisions(queue, [entry])
        self.assertEqual(ctx.exception.code, "REF_001")

    def test_fold_unknown_item_REF_001(self):
        q_item = {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "seen_artifact_revision_id": self.seen_revision}
        queue = [q_item]
        entry = {
            "queue_item_id": "as_qizheng_000002#review_source_fidelity",
            "target_entity_id": "as_qizheng_000002"
        }
        with self.assertRaises(ReviewRefused) as ctx:
            model.fold_decisions(queue, [entry])
        self.assertEqual(ctx.exception.code, "REF_001")

    def test_outcome_approved_rejected_unresolved(self):
        q_items = [
            {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001"},
            {"queue_item_id": "as_qizheng_000002#review_source_fidelity", "target_entity_id": "as_qizheng_000002"},
            {"queue_item_id": "as_qizheng_000003#review_source_fidelity", "target_entity_id": "as_qizheng_000003"},
            {"queue_item_id": "sv_00000000000000000000000000000001#review_source_fidelity", "target_entity_id": "sv_00000000000000000000000000000001"},
            {"queue_item_id": "sv_00000000000000000000000000000001#review_school_attribution", "target_entity_id": "sv_00000000000000000000000000000001"}
        ]
        folded = {
            "as_qizheng_000001#review_source_fidelity": {"verdict": "accept", "standing": "active"},
            "as_qizheng_000002#review_source_fidelity": {"verdict": "reject", "standing": "active"},
            "as_qizheng_000003#review_source_fidelity": {"verdict": "request_evidence", "standing": "active"},
            "sv_00000000000000000000000000000001#review_source_fidelity": {"verdict": "accept", "standing": "active"},
            "sv_00000000000000000000000000000001#review_school_attribution": None
        }
        out = model.outcome(q_items, folded)
        self.assertEqual(out["approved"], ["as_qizheng_000001"])
        self.assertEqual(out["rejected"], ["as_qizheng_000002"])
        self.assertEqual(out["unresolved"], ["as_qizheng_000003#review_source_fidelity", "sv_00000000000000000000000000000001#review_school_attribution"])

    def test_content_hash_ignores_geometry_but_not_text(self):
        norm1 = model.normalize_content(self.c1, self.spans_by_id)
        hash1 = model.content_hash(self.c1, self.spans_by_id)
        
        c1_alt = dict(self.c1)
        c1_alt["source_object"] = dict(self.c1["source_object"])
        c1_alt["source_object"]["content_status"] = "draft"
        
        hash2 = model.content_hash(c1_alt, self.spans_by_id)
        self.assertEqual(hash1, hash2)
        
        c1_diff_text = dict(self.c1)
        c1_diff_text["source_object"] = dict(self.c1["source_object"])
        c1_diff_text["source_object"]["text"] = "other"
        hash3 = model.content_hash(c1_diff_text, self.spans_by_id)
        self.assertNotEqual(hash1, hash3)

    def test_normalize_missing_span_and_bad_offsets(self):
        c_bad_span = dict(self.c1)
        c_bad_span["source_object"] = dict(self.c1["source_object"])
        c_bad_span["source_object"]["evidence"] = [{"source_span_id": "missing", "start": 0, "end": 2}]
        with self.assertRaises(MissingReference) as ctx:
            model.normalize_content(c_bad_span, self.spans_by_id)
        self.assertEqual(ctx.exception.code, "REF_001")
        
        c_bad_offset = dict(self.c1)
        c_bad_offset["source_object"] = dict(self.c1["source_object"])
        c_bad_offset["source_object"]["evidence"] = [{"source_span_id": "p0003_s04", "start": 4, "end": 2}]
        with self.assertRaises(SchemaViolation) as ctx2:
            model.normalize_content(c_bad_offset, self.spans_by_id)
        self.assertEqual(ctx2.exception.code, "SCH_002")

if __name__ == '__main__':
    unittest.main()
