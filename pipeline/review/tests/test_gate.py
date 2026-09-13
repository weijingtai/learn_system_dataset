import unittest
import ast
from pathlib import Path
from pipeline.review import gate
import hashlib

class TestReviewGate(unittest.TestCase):
    def setUp(self):
        self.seen_rev = "rev_11111111111111111111111111111111"
        self.spans = {
            "spans": {
                "p0003_s04": {"text": "四书章句集注", "geometry": {}},
                "p0003_s08": {"text": "大学章句", "geometry": {}},
                "p0003_s03": {"text": "这并非简单的字面对应", "geometry": {}},
                "p0003_s05": {"text": "其实不然", "geometry": {}},
                "p0001_s02": {"text": "孔门弟子多如此认为", "geometry": {}}
            }
        }
        self.co1 = {"entity_id": "as_qizheng_000001", "kind": "assertion", "required_decision_types": ["review_source_fidelity"], "content_hash": "hash1"}
        self.co2 = {"entity_id": "as_qizheng_000002", "kind": "assertion", "required_decision_types": ["review_source_fidelity"], "content_hash": "hash2"}
        self.co3 = {"entity_id": "as_qizheng_000003", "kind": "assertion", "required_decision_types": ["review_source_fidelity"], "content_hash": "hash3"}
        self.sv1 = {"entity_id": "sv_00000000000000000000000000000001", "kind": "school_view", "required_decision_types": ["review_source_fidelity", "review_school_attribution"], "content_hash": "hash4"}
        
        self.candidates = [self.co1, self.co2, self.co3, self.sv1]
        self.validation_package = {"gate": {"passed": True}, "scope": "corpus_only"}
        
        self.de1 = {"decision_revision_id": "rev_22222222222222222222222222222222", "queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "kind": "assertion", "decision_type": "review_source_fidelity", "verdict": "accept", "standing": "active", "seen_revision_id": self.seen_rev, "modified_revision_id": None, "carried_from_revision_id": None, "carried_to_revision_id": None, "carried_content_hash": None, "rationale": "ok"}
        self.de2 = {"decision_revision_id": "rev_22222222222222222222222222222222", "queue_item_id": "as_qizheng_000002#review_source_fidelity", "target_entity_id": "as_qizheng_000002", "kind": "assertion", "decision_type": "review_source_fidelity", "verdict": "reject", "standing": "active", "seen_revision_id": self.seen_rev, "modified_revision_id": None, "carried_from_revision_id": None, "carried_to_revision_id": None, "carried_content_hash": None, "rationale": "no"}
        self.de3 = {"decision_revision_id": "rev_22222222222222222222222222222222", "queue_item_id": "as_qizheng_000003#review_source_fidelity", "target_entity_id": "as_qizheng_000003", "kind": "assertion", "decision_type": "review_source_fidelity", "verdict": "accept", "standing": "active", "seen_revision_id": self.seen_rev, "modified_revision_id": None, "carried_from_revision_id": None, "carried_to_revision_id": None, "carried_content_hash": None, "rationale": "ok"}
        self.de4 = {"decision_revision_id": "rev_22222222222222222222222222222222", "queue_item_id": "sv_00000000000000000000000000000001#review_source_fidelity", "target_entity_id": "sv_00000000000000000000000000000001", "kind": "school_view", "decision_type": "review_source_fidelity", "verdict": "accept", "standing": "active", "seen_revision_id": self.seen_rev, "modified_revision_id": None, "carried_from_revision_id": None, "carried_to_revision_id": None, "carried_content_hash": None, "rationale": "ok"}
        self.de5 = {"decision_revision_id": "rev_22222222222222222222222222222222", "queue_item_id": "sv_00000000000000000000000000000001#review_school_attribution", "target_entity_id": "sv_00000000000000000000000000000001", "kind": "school_view", "decision_type": "review_school_attribution", "verdict": "accept", "standing": "active", "seen_revision_id": self.seen_rev, "modified_revision_id": None, "carried_from_revision_id": None, "carried_to_revision_id": None, "carried_content_hash": None, "rationale": "ok"}
        
        self.entries = [self.de1, self.de2, self.de3, self.de4, self.de5]
        
        self.prior_events = []
        
        q1_hash = hashlib.sha256("四书".encode("utf-8")).hexdigest()
        q3_hash = hashlib.sha256("孔门".encode("utf-8")).hexdigest()
        
        self.reviewed_ed = {
            "unresolved_count": 0,
            "approved": [
                {"entity_id": "as_qizheng_000001", "content_status": "expert_verified"},
                {"entity_id": "as_qizheng_000003", "content_status": "expert_verified"},
                {"entity_id": "sv_00000000000000000000000000000001", "content_status": "expert_verified"}
            ],
            "rejected": ["as_qizheng_000002"],
            "evidence_links": [
                {"entity_id": "as_qizheng_000001", "source_span_id": "p0003_s04", "start": 0, "end": 2, "quote_sha256": q1_hash},
                {"entity_id": "as_qizheng_000003", "source_span_id": "p0001_s02", "start": 0, "end": 2, "quote_sha256": q3_hash}
            ],
            "school_views": [
                {"entity_id": "sv_00000000000000000000000000000001", "conflict_group_id": "cg_11111111111111111111111111111111"}
            ]
        }
        # Assuming sv_00000000000000000000000000000001 has conflict_group_id in candidates? 
        self.sv1["conflict_group_id"] = "cg_11111111111111111111111111111111"

    def test_golden_all_nine_pass(self):
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=self.entries, prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        self.assertEqual(res["review"], "passed")
        for k, v in res["checks"].items():
            self.assertTrue(v["passed"])

    def test_check_names_and_order_exact(self):
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=self.entries, prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        expected = ["validation_intake", "queue_coverage", "decision_anchoring", "decision_closed_sets", "zero_unresolved", "outcome_consistency", "evidence_closure", "school_divergence", "package_counts"]
        self.assertEqual(list(res["checks"].keys()), expected)

    def test_validation_gate_not_passed_fails_validation_intake(self):
        pkg = {"gate": {"passed": False}, "scope": "corpus_only"}
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=pkg, corpus_spans_doc=self.spans, decision_entries=self.entries, prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["validation_intake"]["passed"])

    def test_validation_scope_not_corpus_only_fails_validation_intake(self):
        pkg = {"gate": {"passed": True}, "scope": "something"}
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=pkg, corpus_spans_doc=self.spans, decision_entries=self.entries, prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["validation_intake"]["passed"])

    def test_missing_queue_item_fails_queue_coverage(self):
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=self.entries[:-1], prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["queue_coverage"]["passed"])

    def test_wrong_seen_anchor_fails_decision_anchoring(self):
        entries = list(self.entries)
        entries[0] = dict(entries[0])
        entries[0]["seen_revision_id"] = "rev_99999999999999999999999999999999"
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=entries, prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["decision_anchoring"]["passed"])

    def test_modify_without_modified_revision_fails_decision_anchoring(self):
        entries = list(self.entries)
        entries[0] = dict(entries[0])
        entries[0]["verdict"] = "modify"
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=entries, prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["decision_anchoring"]["passed"])

    def test_accept_with_modified_revision_fails_decision_anchoring(self):
        entries = list(self.entries)
        entries[0] = dict(entries[0])
        entries[0]["modified_revision_id"] = "rev_33333333333333333333333333333333"
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=entries, prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["decision_anchoring"]["passed"])

    def test_carried_without_carried_from_fails_decision_anchoring(self):
        entries = list(self.entries)
        entries[0] = dict(entries[0])
        entries[0]["standing"] = "carried_forward"
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=entries, prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["decision_anchoring"]["passed"])

    def test_carried_entry_passes_when_carried_to_matches_and_hash_equal(self):
        entries = list(self.entries)
        entries[0] = dict(entries[0])
        entries[0]["standing"] = "carried_forward"
        entries[0]["seen_revision_id"] = "rev_old1111111111111111111111111111"
        entries[0]["carried_to_revision_id"] = self.seen_rev
        entries[0]["carried_from_revision_id"] = "rev_old_decision111111111111111111"
        entries[0]["carried_content_hash"] = "hash1"
        
        pe = [{"decision_revision_id": "rev_old_decision111111111111111111", "seen_revision_id": "rev_old1111111111111111111111111111"}]
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=entries, prior_decision_events=pe, reviewed_edition=self.reviewed_ed)
        self.assertTrue(res["checks"]["decision_anchoring"]["passed"])

    def test_carried_with_wrong_carried_to_fails_decision_anchoring(self):
        entries = list(self.entries)
        entries[0] = dict(entries[0])
        entries[0]["standing"] = "carried_forward"
        entries[0]["seen_revision_id"] = "rev_old1111111111111111111111111111"
        entries[0]["carried_to_revision_id"] = "rev_bad1111111111111111111111111111"
        entries[0]["carried_from_revision_id"] = "rev_old_decision111111111111111111"
        entries[0]["carried_content_hash"] = "hash1"
        pe = [{"decision_revision_id": "rev_old_decision111111111111111111", "seen_revision_id": "rev_old1111111111111111111111111111"}]
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=entries, prior_decision_events=pe, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["decision_anchoring"]["passed"])

    def test_carried_from_unknown_event_fails_decision_anchoring(self):
        entries = list(self.entries)
        entries[0] = dict(entries[0])
        entries[0]["standing"] = "carried_forward"
        entries[0]["seen_revision_id"] = "rev_old1111111111111111111111111111"
        entries[0]["carried_to_revision_id"] = self.seen_rev
        entries[0]["carried_from_revision_id"] = "rev_old_decision111111111111111111"
        entries[0]["carried_content_hash"] = "hash1"
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=entries, prior_decision_events=[], reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["decision_anchoring"]["passed"])

    def test_carried_content_hash_changed_fails_decision_anchoring(self):
        entries = list(self.entries)
        entries[0] = dict(entries[0])
        entries[0]["standing"] = "carried_forward"
        entries[0]["seen_revision_id"] = "rev_old1111111111111111111111111111"
        entries[0]["carried_to_revision_id"] = self.seen_rev
        entries[0]["carried_from_revision_id"] = "rev_old_decision111111111111111111"
        entries[0]["carried_content_hash"] = "hash_different"
        pe = [{"decision_revision_id": "rev_old_decision111111111111111111", "seen_revision_id": "rev_old1111111111111111111111111111"}]
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=entries, prior_decision_events=pe, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["decision_anchoring"]["passed"])

    def test_unknown_decision_type_fails_closed_sets(self):
        entries = list(self.entries)
        entries[0] = dict(entries[0])
        entries[0]["decision_type"] = "unknown_type"
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=entries, prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["decision_closed_sets"]["passed"])

    def test_empty_rationale_fails_closed_sets(self):
        entries = list(self.entries)
        entries[0] = dict(entries[0])
        entries[0]["rationale"] = ""
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=entries, prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["decision_closed_sets"]["passed"])

    def test_request_evidence_standing_fails_zero_unresolved(self):
        entries = list(self.entries)
        entries[0] = dict(entries[0])
        entries[0]["verdict"] = "request_evidence"
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=entries, prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["zero_unresolved"]["passed"])

    def test_needs_review_standing_fails_zero_unresolved(self):
        entries = list(self.entries)
        entries[0] = dict(entries[0])
        entries[0]["standing"] = "needs_review"
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=entries, prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["zero_unresolved"]["passed"])

    def test_duplicate_standing_for_item_fails_zero_unresolved(self):
        entries = list(self.entries)
        entries.append(dict(entries[0]))
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=entries, prior_decision_events=self.prior_events, reviewed_edition=self.reviewed_ed)
        self.assertFalse(res["checks"]["zero_unresolved"]["passed"])

    def test_approved_with_reject_dimension_fails_outcome(self):
        ed = dict(self.reviewed_ed)
        ed["approved"] = list(ed["approved"])
        ed["approved"].append({"entity_id": "as_qizheng_000002", "content_status": "expert_verified"})
        ed["rejected"] = []
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=self.entries, prior_decision_events=self.prior_events, reviewed_edition=ed)
        self.assertFalse(res["checks"]["outcome_consistency"]["passed"])

    def test_rejected_entity_dropped_fails_outcome(self):
        ed = dict(self.reviewed_ed)
        ed["rejected"] = []
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=self.entries, prior_decision_events=self.prior_events, reviewed_edition=ed)
        self.assertFalse(res["checks"]["outcome_consistency"]["passed"])

    def test_quote_hash_mismatch_fails_evidence_closure(self):
        ed = dict(self.reviewed_ed)
        ed["evidence_links"] = list(ed["evidence_links"])
        ed["evidence_links"][0] = dict(ed["evidence_links"][0])
        ed["evidence_links"][0]["quote_sha256"] = "wrong_hash"
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=self.entries, prior_decision_events=self.prior_events, reviewed_edition=ed)
        self.assertFalse(res["checks"]["evidence_closure"]["passed"])

    def test_unknown_span_fails_evidence_closure(self):
        ed = dict(self.reviewed_ed)
        ed["evidence_links"] = list(ed["evidence_links"])
        ed["evidence_links"][0] = dict(ed["evidence_links"][0])
        ed["evidence_links"][0]["source_span_id"] = "missing_span"
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=self.entries, prior_decision_events=self.prior_events, reviewed_edition=ed)
        self.assertFalse(res["checks"]["evidence_closure"]["passed"])

    def test_school_view_group_mismatch_fails_school_divergence(self):
        ed = dict(self.reviewed_ed)
        ed["school_views"] = [{"entity_id": "sv_00000000000000000000000000000001", "conflict_group_id": "cg_wrong"}]
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=self.entries, prior_decision_events=self.prior_events, reviewed_edition=ed)
        self.assertFalse(res["checks"]["school_divergence"]["passed"])

    def test_count_mismatch_fails_package_counts(self):
        ed = dict(self.reviewed_ed)
        ed["approved"] = ed["approved"][:-1]
        res = gate.evaluate_review(candidate_objects=self.candidates, seen_revision_id=self.seen_rev, validation_package=self.validation_package, corpus_spans_doc=self.spans, decision_entries=self.entries, prior_decision_events=self.prior_events, reviewed_edition=ed)
        self.assertFalse(res["checks"]["package_counts"]["passed"])

    def test_gate_does_not_import_model_or_propagation(self):
        p = Path(__file__).parent.parent / "gate.py"
        if not p.exists():
            return
        tree = ast.parse(p.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name in ("pipeline.review.model", "pipeline.review.propagation", "pipeline.review.step", "pipeline.review.rework"):
                        self.fail(f"gate.py imports {name.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if "pipeline.review.model" in mod or "pipeline.review.propagation" in mod or "pipeline.review.step" in mod or "pipeline.review.rework" in mod:
                    self.fail(f"gate.py from-imports {mod}")

if __name__ == '__main__':
    unittest.main()
