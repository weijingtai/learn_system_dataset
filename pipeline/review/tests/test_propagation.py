import unittest
import inspect
import ast
from pathlib import Path
from pipeline.review import propagation

class TestPropagation(unittest.TestCase):
    def setUp(self):
        self.old_spans_doc = {
            "spans": {
                "p0003_s08": {"text": "朱熹在《大学章句》中明确指出…", "geometry": {}, "start_offset": 10},
                "p0003_s05": {"text": "其实不然…", "source_anchor": {"bbox": {"x": 10.0}}},
                "p0003_s06": {"text": "测试文本", "start_offset": 20, "end_offset": 24},
                "p0001_s02": {"text": "孔门弟子多如此认为。", "geometry": {}}
            }
        }
        
        self.old_candidates = [
            {
                "entity_id": "as_qizheng_000001",
                "kind": "assertion",
                "source_object": {
                    "assertion_id": "as_qizheng_000001",
                    "text": "…",
                    "evidence": [{"source_span_id": "p0003_s08", "start": 0, "end": 8}]
                },
                "candidate_revision_id": "rev_c1111111111111111111111111111111"
            },
            {
                "entity_id": "as_qizheng_000002",
                "kind": "assertion",
                "source_object": {
                    "assertion_id": "as_qizheng_000002",
                    "text": "…",
                    "evidence": [{"source_span_id": "p0003_s05", "start": 0, "end": 4}]
                },
                "candidate_revision_id": "rev_c2222222222222222222222222222222"
            },
            {
                "entity_id": "as_qizheng_000003",
                "kind": "assertion",
                "source_object": {
                    "assertion_id": "as_qizheng_000003",
                    "text": "…",
                    "evidence": [{"source_span_id": "p0001_s02", "start": 0, "end": 4}]
                },
                "candidate_revision_id": "rev_c3333333333333333333333333333333"
            },
            {
                "entity_id": "sv_00000000000000000000000000000001",
                "kind": "school_view",
                "source_object": {
                    "school_view_id": "sv_00000000000000000000000000000001",
                    "subject_entity_id": "as_qizheng_000001", "source_refs": [{"source_span_id": "p0003_s08"}]
                },
                "candidate_revision_id": "rev_c4444444444444444444444444444444"
            }
        ]
        
        self.validation_entries = []
        
        self.standing_decisions = [
            {"queue_item_id": "as_qizheng_000001#review_source_fidelity", "target_entity_id": "as_qizheng_000001", "decision_revision_id": "rev_d1111111111111111111111111111111", "seen_artifact_revision_id": "rev_seen_1"},
            {"queue_item_id": "as_qizheng_000002#review_source_fidelity", "target_entity_id": "as_qizheng_000002", "decision_revision_id": "rev_d2222222222222222222222222222222", "seen_artifact_revision_id": "rev_seen_2"},
            {"queue_item_id": "as_qizheng_000003#review_source_fidelity", "target_entity_id": "as_qizheng_000003", "decision_revision_id": "rev_d3333333333333333333333333333333", "seen_artifact_revision_id": "rev_seen_3"},
            {"queue_item_id": "sv_00000000000000000000000000000001#review_source_fidelity", "target_entity_id": "sv_00000000000000000000000000000001", "decision_revision_id": "rev_d4444444444444444444444444444444", "seen_artifact_revision_id": "rev_seen_4"},
            {"queue_item_id": "sv_00000000000000000000000000000001#review_school_attribution", "target_entity_id": "sv_00000000000000000000000000000001", "decision_revision_id": "rev_d5555555555555555555555555555555", "seen_artifact_revision_id": "rev_seen_4"}
        ]
        
        self.trigger_cr_rev = "rev_cr111111111111111111111111111111"
        self.rework_round_before = 0

    def test_changed_spans_excludes_offset_shift(self):
        new_doc = {"spans": dict(self.old_spans_doc["spans"])}
        new_doc["spans"]["p0003_s06"] = {"text": "测试文本新", "start_offset": 20, "end_offset": 25}
        new_doc["spans"]["p0003_s08"] = {"text": "朱熹在《大学章句》中明确指出…", "geometry": {}, "start_offset": 11} # only offset changed
        
        diff = propagation.changed_span_ids(self.old_spans_doc, new_doc)
        self.assertEqual(diff["changed"], ["p0003_s06"])
        self.assertEqual(diff["added"], [])
        self.assertEqual(diff["removed"], [])

    def test_changed_removed_added_sets(self):
        new_doc = {"spans": dict(self.old_spans_doc["spans"])}
        del new_doc["spans"]["p0001_s02"]
        new_doc["spans"]["p0003_s05"] = {"text": "其实不然…", "source_anchor": {"bbox": {"x": 11.0}}}
        new_doc["spans"]["new_span"] = {"text": "new"}
        diff = propagation.changed_span_ids(self.old_spans_doc, new_doc)
        self.assertEqual(diff["removed"], ["p0001_s02"])
        self.assertEqual(diff["changed"], ["p0003_s05"])
        self.assertEqual(diff["added"], ["new_span"])

    def test_reachable_direct_and_transitive(self):
        # S1: change p0003_s08 text, change p0003_s05 anchor
        new_doc = {"spans": dict(self.old_spans_doc["spans"])}
        new_doc["spans"]["p0003_s08"] = {"text": "朱熹在《大学官句》中明确指出…", "geometry": {}}
        new_doc["spans"]["p0003_s05"] = {"text": "其实不然…", "source_anchor": {"bbox": {"x": 11.0}}}
        
        diff = propagation.changed_span_ids(self.old_spans_doc, new_doc)
        affected = set(diff["changed"]) | set(diff["removed"])
        
        reachable = propagation.reachable_entities(self.old_candidates, affected)
        # as_1 is directly reachable (p0003_s08)
        # as_2 is directly reachable (p0003_s05)
        # sv_1 is transitively reachable (subject_entity_id = as_1)
        self.assertEqual(sorted(reachable), ["as_qizheng_000001", "as_qizheng_000002", "sv_00000000000000000000000000000001"])

    def test_s1_counts_exact(self):
        new_doc = {"spans": dict(self.old_spans_doc["spans"])}
        new_doc["spans"]["p0003_s08"] = {"text": "朱熹在《大学官句》中明确指出…", "geometry": {}}
        new_doc["spans"]["p0003_s05"] = {"text": "其实不然…", "source_anchor": {"bbox": {"x": 11.0}}}
        
        res = propagation.propagate(old_candidates=self.old_candidates, old_spans_doc=self.old_spans_doc, new_spans_doc=new_doc, validation_entries=self.validation_entries, standing_decisions=self.standing_decisions, rework_round_before=self.rework_round_before, trigger_correction_request_revision_id=self.trigger_cr_rev)
        
        self.assertEqual(res["invalidated_count"], 3)
        self.assertEqual(res["carried_forward_count"], 3) # 1 candidate + 2 decisions? 
        # Wait, the contract says:
        # 4 对不可达候选: carried_forward += {"kind": "candidate"...}
        # 5 对立场决定: ... carried_forward += {"kind": "decision"...}
        # Unreachable candidate: as_qizheng_000003 (1)
        # Unreachable decision: as_qizheng_000003#review_source_fidelity (1)
        # Reachable decision but hash identical: as_qizheng_000002#review_source_fidelity (because only anchor changed) (1)
        # Total carried_forward = 1 + 1 + 1 = 3
        # needs_review: as_qizheng_000001 (1) + sv_1 (2) = 3
        self.assertEqual(len(res["invalidated"]), 3)
        self.assertEqual(len(res["carried_forward"]), 3)
        self.assertEqual(len(res["needs_review"]), 3)
        self.assertEqual(res["valid_object_count"], 4)
        self.assertEqual(res["invalidated_ratio"], 0.75)

    def test_s1_equal_content_reachable_decision_carried(self):
        new_doc = {"spans": dict(self.old_spans_doc["spans"])}
        new_doc["spans"]["p0003_s08"] = {"text": "朱熹在《大学官句》中明确指出…", "geometry": {}}
        new_doc["spans"]["p0003_s05"] = {"text": "其实不然…", "source_anchor": {"bbox": {"x": 11.0}}}
        
        res = propagation.propagate(old_candidates=self.old_candidates, old_spans_doc=self.old_spans_doc, new_spans_doc=new_doc, validation_entries=self.validation_entries, standing_decisions=self.standing_decisions, rework_round_before=self.rework_round_before, trigger_correction_request_revision_id=self.trigger_cr_rev)
        
        car = [c for c in res["carried_forward"] if c["kind"] == "decision" and c["entity_id"] == "as_qizheng_000002"]
        self.assertEqual(len(car), 1)

    def test_s1_changed_content_decisions_need_review(self):
        new_doc = {"spans": dict(self.old_spans_doc["spans"])}
        new_doc["spans"]["p0003_s08"] = {"text": "朱熹在《大学官句》中明确指出…", "geometry": {}}
        new_doc["spans"]["p0003_s05"] = {"text": "其实不然…", "source_anchor": {"bbox": {"x": 11.0}}}
        
        res = propagation.propagate(old_candidates=self.old_candidates, old_spans_doc=self.old_spans_doc, new_spans_doc=new_doc, validation_entries=self.validation_entries, standing_decisions=self.standing_decisions, rework_round_before=self.rework_round_before, trigger_correction_request_revision_id=self.trigger_cr_rev)
        
        nr = [n for n in res["needs_review"] if n["target_entity_id"] == "as_qizheng_000001"]
        self.assertEqual(len(nr), 1)
        self.assertEqual(nr[0]["reason"], "content_changed")

    def test_s1_school_view_two_decisions_need_review(self):
        new_doc = {"spans": dict(self.old_spans_doc["spans"])}
        new_doc["spans"]["p0003_s08"] = {"text": "朱熹在《大学官句》中明确指出…", "geometry": {}}
        new_doc["spans"]["p0003_s05"] = {"text": "其实不然…", "source_anchor": {"bbox": {"x": 11.0}}}
        
        res = propagation.propagate(old_candidates=self.old_candidates, old_spans_doc=self.old_spans_doc, new_spans_doc=new_doc, validation_entries=self.validation_entries, standing_decisions=self.standing_decisions, rework_round_before=self.rework_round_before, trigger_correction_request_revision_id=self.trigger_cr_rev)
        
        nr = [n for n in res["needs_review"] if n["target_entity_id"] == "sv_00000000000000000000000000000001"]
        self.assertEqual(len(nr), 2)

    def test_unreachable_object_and_decision_carried_with_from_revision(self):
        new_doc = {"spans": dict(self.old_spans_doc["spans"])}
        new_doc["spans"]["p0003_s08"] = {"text": "朱熹在《大学官句》中明确指出…", "geometry": {}}
        
        res = propagation.propagate(old_candidates=self.old_candidates, old_spans_doc=self.old_spans_doc, new_spans_doc=new_doc, validation_entries=self.validation_entries, standing_decisions=self.standing_decisions, rework_round_before=self.rework_round_before, trigger_correction_request_revision_id=self.trigger_cr_rev)
        
        # as_3 is unreachable
        car_c = [c for c in res["carried_forward"] if c["kind"] == "candidate" and c["entity_id"] == "as_qizheng_000003"]
        self.assertEqual(len(car_c), 1)
        self.assertEqual(car_c[0]["carried_from_revision_id"], "rev_c3333333333333333333333333333333")
        
        car_d = [c for c in res["carried_forward"] if c["kind"] == "decision" and c["entity_id"] == "as_qizheng_000003"]
        self.assertEqual(len(car_d), 1)
        self.assertEqual(car_d[0]["carried_from_revision_id"], "rev_seen_3")

    def test_removed_span_gives_target_removed(self):
        new_doc = {"spans": dict(self.old_spans_doc["spans"])}
        del new_doc["spans"]["p0003_s08"]
        
        res = propagation.propagate(old_candidates=self.old_candidates, old_spans_doc=self.old_spans_doc, new_spans_doc=new_doc, validation_entries=self.validation_entries, standing_decisions=self.standing_decisions, rework_round_before=self.rework_round_before, trigger_correction_request_revision_id=self.trigger_cr_rev)
        
        nr = [n for n in res["needs_review"] if n["target_entity_id"] == "as_qizheng_000001"]
        self.assertEqual(len(nr), 1)
        self.assertEqual(nr[0]["reason"], "target_removed")

    def test_threshold_by_round(self):
        new_doc = {"spans": dict(self.old_spans_doc["spans"])}
        new_doc["spans"]["p0001_s02"] = {"text": "孔门弟子多如此认为", "geometry": {}}
        
        res = propagation.propagate(old_candidates=self.old_candidates, old_spans_doc=self.old_spans_doc, new_spans_doc=new_doc, validation_entries=self.validation_entries, standing_decisions=self.standing_decisions, rework_round_before=2, trigger_correction_request_revision_id=self.trigger_cr_rev)
        
        self.assertEqual(res["rework_round"], 3)
        self.assertIn("rework_threshold_exceeded", res["warnings"])

    def test_threshold_below_ratio_no_warning(self):
        new_doc = {"spans": dict(self.old_spans_doc["spans"])}
        new_doc["spans"]["p0001_s02"] = {"text": "孔门弟子多如此认为", "geometry": {}}
        
        res = propagation.propagate(old_candidates=self.old_candidates, old_spans_doc=self.old_spans_doc, new_spans_doc=new_doc, validation_entries=self.validation_entries, standing_decisions=self.standing_decisions, rework_round_before=0, trigger_correction_request_revision_id=self.trigger_cr_rev)
        
        self.assertEqual(res["rework_round"], 1)
        # invalidated count = 1, valid_object_count = 4, ratio = 0.25 < 0.30
        self.assertEqual(res["warnings"], [])

    def test_report_key_order_exact(self):
        new_doc = {"spans": dict(self.old_spans_doc["spans"])}
        res = propagation.propagate(old_candidates=self.old_candidates, old_spans_doc=self.old_spans_doc, new_spans_doc=new_doc, validation_entries=self.validation_entries, standing_decisions=self.standing_decisions, rework_round_before=0, trigger_correction_request_revision_id=self.trigger_cr_rev)
        
        expected_keys = ["schema_version", "trigger_correction_request_revision_id", "rework_round", "changed_span_ids", "removed_span_ids", "reachable_entity_ids", "invalidated", "carried_forward", "needs_review", "invalidated_count", "carried_forward_count", "needs_review_count", "valid_object_count", "invalidated_ratio", "warnings", "affected_queues"]
        self.assertEqual(list(res.keys()), expected_keys)

    def test_propagate_signature_has_no_operator_selection(self):
        sig = inspect.signature(propagation.propagate)
        expected = {"old_candidates", "old_spans_doc", "new_spans_doc", "validation_entries", "standing_decisions", "rework_round_before", "trigger_correction_request_revision_id"}
        self.assertEqual(set(sig.parameters.keys()), expected)

    def test_module_does_not_reference_invalidate_revision(self):
        p = Path(__file__).parent.parent / "propagation.py"
        if p.exists():
            content = p.read_text()
            self.assertNotIn("invalidate_revision", content)

    def test_deterministic_twice(self):
        new_doc = {"spans": dict(self.old_spans_doc["spans"])}
        new_doc["spans"]["p0001_s02"] = {"text": "孔门弟子多如此认为", "geometry": {}}
        
        res1 = propagation.propagate(old_candidates=self.old_candidates, old_spans_doc=self.old_spans_doc, new_spans_doc=new_doc, validation_entries=self.validation_entries, standing_decisions=self.standing_decisions, rework_round_before=0, trigger_correction_request_revision_id=self.trigger_cr_rev)
        res2 = propagation.propagate(old_candidates=self.old_candidates, old_spans_doc=self.old_spans_doc, new_spans_doc=new_doc, validation_entries=self.validation_entries, standing_decisions=self.standing_decisions, rework_round_before=0, trigger_correction_request_revision_id=self.trigger_cr_rev)
        self.assertEqual(res1, res2)

if __name__ == '__main__':
    unittest.main()
