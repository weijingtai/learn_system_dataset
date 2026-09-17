"""ACT 02 独立候选 Gate ``gate`` 的单测（先红后绿）。

基底用 ``assemble.assemble_candidates`` 在测试内生成；``gate.py`` 本身不得 import
``assemble`` / ``submission``（见 ``test_gate_does_not_import_assemble_or_submission``）。
"""

import copy
import hashlib
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


# ------------------------------------------------------------------ offset_level
OFFSET_EVIDENCE_TEXT = "余俱从天干取用"
OFFSET_SPAN_TEXT = "余俱从天干取用。"


def _offset_spans_doc():
    """合成 ``offset_level`` 片段：**无 page 键**，偏移为原文绝对偏移（第 100 条 D2/D4）。"""
    rows = [
        ("ss_qianyuan_ed01_o0008663", 8663, "天官者，天干之官也"),
        ("ss_qianyuan_ed01_o0008672", 8672, OFFSET_SPAN_TEXT),
    ]
    spans = []
    for index, (span_id, start, text) in enumerate(rows):
        spans.append(
            {
                "span_id": span_id,
                "sequence": index + 1,
                "start_offset": start,
                "end_offset": start + len(text),
                "text": text,
                "quote_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "evidence_level": "offset_level",
                "source_anchor": {},
            }
        )
    return {
        "work": "乾元秘旨",
        "source_id": "src_qianyuan_ed01",
        "edition_part_artifact_id": "art_00000000000000000000000000000001",
        "evidence_level": "offset_level",
        "content_status": "machine_extracted",
        "span_count": len(spans),
        "spans": spans,
    }


def _offset_submission(lane):
    """合成提交件：引文为片段 ``text`` 的逐字子串（无 span_char_*，只用 quote）。"""
    return validate_submission(
        {
            "schema_version": "0.1.0-draft",
            "category": "assertion",
            "lane": lane,
            "channel": "task_pipeline_manual",
            "technique_id": "qizheng",
            "producer": {"kind": "external_agent", "name": "synthetic_offset"},
            "items": [
                {
                    "proposition": "天官即天干之官",
                    "relation": "supports",
                    "evidence": [
                        {
                            "source_span_id": "ss_qianyuan_ed01_o0008672",
                            "support_type": "direct",
                            "quote": OFFSET_EVIDENCE_TEXT,
                        }
                    ],
                    "conditions": [],
                    "exceptions": [],
                    "layer": "general",
                }
            ],
        },
        technique_id="qizheng",
    )


class OffsetLevelGateTests(unittest.TestCase):
    """R82a：Gate 按 ``evidence_level`` 分派，offset 级片段不依赖 ``page``。"""

    def setUp(self):
        self.spans_doc = _offset_spans_doc()
        self.profile = build_profile()
        lanes = {
            "assertion": {
                lane: assemble.normalize_lane(
                    _offset_submission(lane),
                    spans_doc=self.spans_doc,
                    profile=self.profile,
                )
                for lane in ("a", "b")
            }
        }
        result = assemble.assemble_candidates(
            spans_doc=self.spans_doc,
            profile=self.profile,
            lane_results=lanes,
            required_lanes={"assertion": ["a", "b"]},
            rulings={},
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

    def test_offset_level_candidate_set_all_twelve_checks_pass(self):
        """正例：offset 级合成片段 + 合成提交件必须过全部十二项。"""
        result = self._evaluate(copy.deepcopy(self.base))
        self.assertEqual(result["failed_checks"], [])
        self.assertEqual(result["structural"], "passed")
        self.assertEqual(len(result["checks"]), 12)
        self.assertTrue(all(row["passed"] for row in result["checks"]))

    def test_offset_level_evidence_offsets_are_raw_text_absolute(self):
        """坐标语义：证据偏移 = 片段 ``start_offset`` + 片段内局部起点（原文绝对偏移）。"""
        evidence = self.base["assertions"][0]["evidence"][0]
        self.assertEqual(evidence["start_offset"], 8672)
        self.assertEqual(evidence["end_offset"], 8672 + len(OFFSET_EVIDENCE_TEXT))
        self.assertEqual(evidence["quote"], OFFSET_EVIDENCE_TEXT)
        self.assertEqual(self.base["evidence_level"], "offset_level")

    def test_offset_level_quote_not_verbatim_substring_fails_quote_fidelity(self):
        """反例：引文不是片段逐字子串即拒（sha 同步重算，只留切片一致性这一道关）。

        此用例是 offset 级引文校验的独立护栏：把该校验改成恒通过，它必须转红。
        """
        candidate_set = copy.deepcopy(self.base)
        evidence = candidate_set["assertions"][0]["evidence"][0]
        evidence["quote"] = "余俱从天干取乎"  # 既非片段子串，也不等于记录区间
        evidence["quote_sha256"] = hashlib.sha256(
            evidence["quote"].encode("utf-8")
        ).hexdigest()
        result = self._evaluate(candidate_set)
        self.assertEqual(result["structural"], "failed")
        checks = {row["name"]: row for row in result["checks"]}
        self.assertFalse(checks["quote_fidelity"]["passed"])
        self.assertIn("片段切片 != quote", "; ".join(checks["quote_fidelity"]["errors"]))

    def test_offset_level_wrong_quote_sha_fails_quote_fidelity(self):
        """反例：``quote_sha256`` 与 ``quote`` 不符即拒。"""
        candidate_set = copy.deepcopy(self.base)
        candidate_set["assertions"][0]["evidence"][0]["quote_sha256"] = "0" * 64
        result = self._evaluate(candidate_set)
        checks = {row["name"]: row for row in result["checks"]}
        self.assertFalse(checks["quote_fidelity"]["passed"])
        self.assertIn("quote_sha256 不一致", "; ".join(checks["quote_fidelity"]["errors"]))

    def test_offset_level_offset_outside_span_fails_evidence_resolvable(self):
        """反例：offset 越出片段区间即拒。"""
        candidate_set = copy.deepcopy(self.base)
        evidence = candidate_set["assertions"][0]["evidence"][0]
        evidence["start_offset"] = 1
        evidence["end_offset"] = 5
        result = self._evaluate(candidate_set)
        checks = {row["name"]: row for row in result["checks"]}
        self.assertFalse(checks["evidence_resolvable"]["passed"])


if __name__ == "__main__":
    unittest.main()
