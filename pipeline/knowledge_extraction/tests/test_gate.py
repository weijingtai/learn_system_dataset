"""ACT 02 独立候选 Gate ``gate`` 的单测（先红后绿）。

基底用 ``assemble.assemble_candidates`` 在测试内生成；``gate.py`` 本身不得 import
``assemble`` / ``submission``（见 ``test_gate_does_not_import_assemble_or_submission``）。
"""

import copy
import re
import unittest
from pathlib import Path

import yaml

from pipeline.knowledge_extraction import assemble, gate
from pipeline.knowledge_extraction.submission import validate_submission

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_SPANS = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01" / "spans.yaml"
CANON_DIR = ROOT / "pipeline" / "schemas" / "shared" / "canon"
DATA = Path(__file__).resolve().parent / "data" / "appendix_a"

ID_RANGE = {"assertion": [1, 99], "proposition": [1, 99], "pattern": [1, 99]}
CONFIG = {"gate_profile": "thin_no_model", "id_range": ID_RANGE}


def build_profile():
    concepts = []
    for path in sorted(CANON_DIR.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for concept in doc["concepts"]:
            concepts.append(
                {
                    "concept_id": concept["concept_id"],
                    "surface": concept["surface"],
                    "aliases": list(concept.get("aliases", [])),
                    "domain": concept["domain"],
                    "rev": concept["rev"],
                }
            )
    return {
        "schema_version": "0.1.0-draft",
        "technique_id": "qizheng",
        "canon": {"files": [], "concepts": sorted(concepts, key=lambda row: row["concept_id"])},
        "homographs": [],
        "glossary": [],
        "schools": [],
    }


class GateTests(unittest.TestCase):
    def setUp(self):
        self.spans_doc = yaml.safe_load(FIXTURE_SPANS.read_text(encoding="utf-8"))
        self.profile = build_profile()
        submissions = {
            "assertion": {
                "a": validate_submission(
                    yaml.safe_load((DATA / "submission_assertion_a.yaml").read_text(encoding="utf-8")),
                    technique_id="qizheng",
                ),
                "b": validate_submission(
                    yaml.safe_load((DATA / "submission_assertion_b.yaml").read_text(encoding="utf-8")),
                    technique_id="qizheng",
                ),
            },
            "concept_mention": {
                "a": validate_submission(
                    yaml.safe_load(
                        (DATA / "submission_concept_mention_a.yaml").read_text(encoding="utf-8")
                    ),
                    technique_id="qizheng",
                ),
            },
        }
        lanes = {
            category: {
                lane: assemble.normalize_lane(
                    submission, spans_doc=self.spans_doc, profile=self.profile
                )
                for lane, submission in by_lane.items()
            }
            for category, by_lane in submissions.items()
        }
        result = assemble.assemble_candidates(
            spans_doc=self.spans_doc,
            profile=self.profile,
            lane_results=lanes,
            required_lanes={"assertion": ["a", "b"], "concept_mention": ["a"]},
            rulings={"m4_d001": "a"},
            id_range=ID_RANGE,
        )
        self.base = result["candidate_set"]

    def _evaluate(self, candidate_set):
        return gate.evaluate_candidates(
            spans_doc=self.spans_doc,
            profile=self.profile,
            candidate_set=candidate_set,
            config=CONFIG,
        )

    def _assert_fails(self, candidate_set, check_name):
        result = self._evaluate(candidate_set)
        self.assertEqual(result["structural"], "failed")
        checks = {row["name"]: row for row in result["checks"]}
        self.assertFalse(checks[check_name]["passed"], "期望检查失败: %s" % check_name)

    def _school_view(self, **overrides):
        row = {
            "school_view_id": "sv_" + "0" * 32,
            "school_id": "sch_qizheng_001",
            "subject_entity_id": "as_qizheng_000001",
            "claim_refs": ["as_qizheng_000001"],
            "conflict_group_id": None,
            "changes_current_judgment": True,
            "source_refs": [
                {"source_id": "src_sanche_ed01", "source_span_id": "ss_sanche_ed01_p0001_s02"}
            ],
            "evidence": [copy.deepcopy(self.base["assertions"][0]["evidence"][0])],
            "content_status": "machine_extracted",
            "origin": {"lane": "a", "item_index": 0},
        }
        row.update(overrides)
        return row

    # ------------------------------------------------------------- 基线与轴
    def test_gold_candidate_set_all_twelve_checks_pass(self):
        result = self._evaluate(copy.deepcopy(self.base))
        self.assertEqual(result["structural"], "passed")
        self.assertEqual(result["failed_checks"], [])
        self.assertEqual(len(result["checks"]), 12)
        self.assertTrue(all(row["passed"] for row in result["checks"]))

    def test_gate_reports_not_evaluated_axes(self):
        result = self._evaluate(copy.deepcopy(self.base))
        self.assertEqual(result["gate_profile"], "thin_no_model")
        self.assertEqual(result["cross_model"], "not_evaluated")
        self.assertEqual(result["term_layering"], "verify_only")
        self.assertEqual(result["semantic_span_input"], "not_evaluated")

    def test_gate_does_not_import_assemble_or_submission(self):
        source = (ROOT / "pipeline" / "knowledge_extraction" / "gate.py").read_text(
            encoding="utf-8"
        )
        for line in source.splitlines():
            if re.match(r"^\s*(from|import)\s", line) and (
                "assemble" in line or "submission" in line
            ):
                self.fail("gate.py 不得 import assemble/submission: %s" % line)

    # ------------------------------------------------------------- 篡改矩阵
    def test_delete_evidence_fails_evidence_required(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["assertions"][0]["evidence"] = []
        self._assert_fails(candidate_set, "evidence_required")

    def test_change_quote_char_fails_quote_fidelity(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["assertions"][0]["evidence"][0]["quote"] += "X"
        self._assert_fails(candidate_set, "quote_fidelity")

    def test_shift_offset_fails_quote_fidelity(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["assertions"][0]["evidence"][0]["start_offset"] += 1
        self._assert_fails(candidate_set, "quote_fidelity")

    def test_bad_quote_sha_fails_quote_fidelity(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["assertions"][0]["evidence"][0]["quote_sha256"] = "0" * 64
        self._assert_fails(candidate_set, "quote_fidelity")

    def test_unknown_span_fails_evidence_resolvable(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["assertions"][0]["evidence"][0][
            "source_span_id"
        ] = "ss_sanche_ed01_p0001_s99"
        self._assert_fails(candidate_set, "evidence_resolvable")

    def test_offset_outside_span_fails_evidence_resolvable(self):
        candidate_set = copy.deepcopy(self.base)
        evidence = candidate_set["assertions"][0]["evidence"][0]
        evidence["start_offset"] = 5000
        evidence["end_offset"] = 5001
        self._assert_fails(candidate_set, "evidence_resolvable")

    def test_duplicate_assertion_id_fails_identity(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["assertions"].append(copy.deepcopy(candidate_set["assertions"][0]))
        self._assert_fails(candidate_set, "identity")

    def test_pr_number_mismatch_fails_identity(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["assertions"][0]["proposition_id"] = "pr_qizheng_000099"
        self._assert_fails(candidate_set, "identity")

    def test_id_outside_range_fails_identity(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["assertions"][0]["assertion_id"] = "as_qizheng_000200"
        candidate_set["assertions"][0]["proposition_id"] = "pr_qizheng_000200"
        self._assert_fails(candidate_set, "identity")

    def test_expert_verified_fails_status_ceiling(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["assertions"][0]["content_status"] = "expert_verified"
        self._assert_fails(candidate_set, "status_ceiling")

    def test_cross_model_reviewed_fails_status_ceiling(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["assertions"][0]["content_status"] = "cross_model_reviewed"
        self._assert_fails(candidate_set, "status_ceiling")

    def test_case_layer_fails_layer_rules(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["assertions"][0]["layer"] = "case"
        self._assert_fails(candidate_set, "layer_rules")

    def test_dangling_claim_ref_fails_references(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["school_views"].append(
            self._school_view(claim_refs=["as_qizheng_000099"])
        )
        self._assert_fails(candidate_set, "references")

    def test_unregistered_school_fails_references(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["school_views"].append(self._school_view(school_id="sch_qizheng_999"))
        self._assert_fails(candidate_set, "references")

    def test_unknown_concept_ref_fails_references(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["assertions"][0]["concept_refs"] = ["co_shared_branch_99"]
        self._assert_fails(candidate_set, "references")

    def test_offset_level_fails_evidence_level_inherited(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["evidence_level"] = "offset_level"
        self._assert_fails(candidate_set, "evidence_level_inherited")

    def test_semantic_span_layer_fails_evidence_level_inherited(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["span_layer"] = "semantic"
        self._assert_fails(candidate_set, "evidence_level_inherited")

    def test_null_choice_fails_disputes_resolved(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["disputes"][0]["choice"] = None
        self._assert_fails(candidate_set, "disputes_resolved")

    def test_wrong_counts_fails_counts_match(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["counts"]["assertions"] += 1
        self._assert_fails(candidate_set, "counts_match")

    def test_technique_mismatch_fails_source_consistency(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["technique_id"] = "ziwei"
        self._assert_fails(candidate_set, "source_consistency")

    def test_extra_top_key_fails_schema_shape(self):
        candidate_set = copy.deepcopy(self.base)
        candidate_set["extra_key"] = 1
        self._assert_fails(candidate_set, "schema_shape")


if __name__ == "__main__":
    unittest.main()
