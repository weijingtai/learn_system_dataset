"""ACT 01 纯函数候选装配 ``assemble`` 的单测（先红后绿）。

读 fixture ``spans.yaml`` 仅作只读输入；profile 在测试内由 canon 目录构造。
"""

import copy
import unittest
from pathlib import Path

import yaml

from pipeline.knowledge_extraction import assemble
from pipeline.knowledge_extraction.errors import ExtractionRefused
from pipeline.knowledge_extraction.submission import validate_submission

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_SPANS = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01" / "spans.yaml"
CANON_DIR = ROOT / "pipeline" / "schemas" / "shared" / "canon"
DATA = Path(__file__).resolve().parent / "data" / "appendix_a"

ID_RANGE = {"assertion": [1, 99], "proposition": [1, 99], "pattern": [1, 99]}


def build_profile():
    """由 canon 目录构造运行级 technique_profile（homographs/glossary/schools 空）。"""
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


def load_raw(name):
    with open(DATA / name, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_submission(name):
    return validate_submission(load_raw(name), technique_id="qizheng")


def make_submission(category, lane, items, channel="fixture_gold"):
    return validate_submission(
        {
            "schema_version": "0.1.0-draft",
            "category": category,
            "lane": lane,
            "channel": channel,
            "technique_id": "qizheng",
            "producer": {"kind": "human", "name": "local_owner"},
            "items": items,
        },
        technique_id="qizheng",
    )


class AssembleTests(unittest.TestCase):
    def setUp(self):
        self.spans_doc = yaml.safe_load(FIXTURE_SPANS.read_text(encoding="utf-8"))
        self.index = assemble.span_index(self.spans_doc)
        self.profile = build_profile()

    def _norm(self, submission, profile=None):
        return assemble.normalize_lane(
            submission, spans_doc=self.spans_doc, profile=profile or self.profile
        )

    def _gold_lanes(self, profile=None, rulings_key="m4_d001"):
        profile = profile or self.profile
        lanes = {
            "assertion": {
                "a": self._norm(load_submission("submission_assertion_a.yaml"), profile),
                "b": self._norm(load_submission("submission_assertion_b.yaml"), profile),
            },
            "concept_mention": {
                "a": self._norm(load_submission("submission_concept_mention_a.yaml"), profile),
            },
        }
        return lanes, {"assertion": ["a", "b"], "concept_mention": ["a"]}

    # ------------------------------------------------------------- 页块 / 定位
    def test_page_blocks_equal_transcript_sections(self):
        blocks = assemble.page_blocks(self.spans_doc)
        expected_1 = "\n".join(
            span["text"] for span in self.spans_doc["spans"] if span["page"] == "page_001"
        )
        expected_3 = "\n".join(
            span["text"] for span in self.spans_doc["spans"] if span["page"] == "page_003"
        )
        self.assertEqual(blocks["page_001"], expected_1)
        self.assertEqual(blocks["page_003"], expected_3)

    def test_locate_by_span_char_range(self):
        result = assemble.locate_evidence(
            {
                "source_span_id": "ss_sanche_ed01_p0001_s04",
                "support_type": "direct",
                "span_char_start": 0,
                "span_char_end": 7,
            },
            self.index,
        )
        self.assertEqual(result["start_offset"], 20)
        self.assertEqual(result["end_offset"], 27)
        self.assertEqual(result["quote"], "三辰通載三十卷")

    def test_locate_by_unique_quote(self):
        result = assemble.locate_evidence(
            {
                "source_span_id": "ss_sanche_ed01_p0001_s02",
                "support_type": "direct",
                "quote": "錢如璧撰",
            },
            self.index,
        )
        self.assertEqual((result["start_offset"], result["end_offset"]), (8, 12))

    def test_locate_whole_span_when_no_range_no_quote(self):
        result = assemble.locate_evidence(
            {"source_span_id": "ss_sanche_ed01_p0001_s04", "support_type": "direct"},
            self.index,
        )
        self.assertEqual((result["start_offset"], result["end_offset"]), (20, 37))
        self.assertEqual(result["quote"], "三辰通載三十卷宋錢如璧撰據静嘉堂藏")

    def test_quote_not_found_TXT_001(self):
        with self.assertRaises(assemble._ItemRejected) as ctx:
            assemble.locate_evidence(
                {
                    "source_span_id": "ss_sanche_ed01_p0001_s02",
                    "support_type": "direct",
                    "quote": "不存在",
                },
                self.index,
            )
        self.assertEqual(ctx.exception.reason_code, "TXT_001")
        self.assertIn("不在 Span 内", ctx.exception.detail)

    def test_quote_ambiguous_TXT_001(self):
        with self.assertRaises(assemble._ItemRejected) as ctx:
            assemble.locate_evidence(
                {
                    "source_span_id": "ss_sanche_ed01_p0003_s13",
                    "support_type": "direct",
                    "quote": "宮",
                },
                self.index,
            )
        self.assertEqual(ctx.exception.reason_code, "TXT_001")
        self.assertIn("不唯一", ctx.exception.detail)

    def test_range_quote_mismatch_TXT_001(self):
        with self.assertRaises(assemble._ItemRejected) as ctx:
            assemble.locate_evidence(
                {
                    "source_span_id": "ss_sanche_ed01_p0001_s04",
                    "support_type": "direct",
                    "span_char_start": 0,
                    "span_char_end": 7,
                    "quote": "三辰",
                },
                self.index,
            )
        self.assertEqual(ctx.exception.reason_code, "TXT_001")

    def test_unknown_span_REF_001(self):
        with self.assertRaises(assemble._ItemRejected) as ctx:
            assemble.locate_evidence(
                {"source_span_id": "ss_sanche_ed01_p0001_s99", "support_type": "direct"},
                self.index,
            )
        self.assertEqual(ctx.exception.reason_code, "REF_001")

    # ------------------------------------------------------------- 逐条准入
    def test_empty_evidence_SEM_001(self):
        submission = make_submission(
            "assertion",
            "a",
            [{"proposition": "宋錢如璧撰", "relation": "supports", "evidence": []}],
        )
        result = self._norm(submission)
        self.assertEqual(result["accepted"], [])
        self.assertEqual(result["rejected"][0]["reason_code"], "SEM_001")

    def test_case_layer_refused_SCH_002(self):
        submission = make_submission(
            "assertion",
            "a",
            [
                {
                    "proposition": "宋錢如璧撰",
                    "relation": "supports",
                    "layer": "case",
                    "evidence": [
                        {
                            "source_span_id": "ss_sanche_ed01_p0001_s02",
                            "support_type": "direct",
                            "quote": "錢如璧撰",
                        }
                    ],
                }
            ],
        )
        result = self._norm(submission)
        self.assertEqual(result["accepted"], [])
        self.assertEqual(result["rejected"][0]["reason_code"], "SCH_002")
        self.assertIn("G4", result["rejected"][0]["detail"])

    def test_shared_concept_ref_verified_against_canon(self):
        def item(concept_ref):
            return {
                "proposition": "宋錢如璧撰",
                "relation": "supports",
                "concept_refs": [concept_ref],
                "evidence": [
                    {
                        "source_span_id": "ss_sanche_ed01_p0003_s01",
                        "support_type": "direct",
                        "quote": "辰",
                    }
                ],
            }

        good = self._norm(make_submission("assertion", "a", [item("co_shared_branch_05")]))
        self.assertEqual(len(good["accepted"]), 1)
        bad = self._norm(make_submission("assertion", "a", [item("co_shared_branch_99")]))
        self.assertEqual(bad["accepted"], [])
        self.assertEqual(bad["rejected"][0]["reason_code"], "REF_001")

    def test_concept_mention_surface_mismatch_TXT_001(self):
        submission = make_submission(
            "concept_mention",
            "a",
            [
                {
                    "surface": "甲",
                    "concept_ref": "co_shared_branch_05",
                    "evidence": [
                        {
                            "source_span_id": "ss_sanche_ed01_p0003_s01",
                            "support_type": "direct",
                            "quote": "辰",
                        }
                    ],
                }
            ],
        )
        result = self._norm(submission)
        self.assertEqual(result["accepted"], [])
        self.assertEqual(result["rejected"][0]["reason_code"], "TXT_001")

    def test_technique_concept_ref_without_glossary_REF_001(self):
        submission = make_submission(
            "concept_mention",
            "a",
            [
                {
                    "surface": "辰",
                    "concept_ref": "co_qizheng_000001",
                    "evidence": [
                        {
                            "source_span_id": "ss_sanche_ed01_p0003_s01",
                            "support_type": "direct",
                            "quote": "辰",
                        }
                    ],
                }
            ],
        )
        result = self._norm(submission)
        self.assertEqual(result["rejected"][0]["reason_code"], "REF_001")

    def test_unregistered_school_id_REF_001(self):
        submission = make_submission(
            "school_view",
            "a",
            [
                {
                    "school_id": "sch_qizheng_001",
                    "subject": {"kind": "assertion", "key": "宋錢如璧撰"},
                    "claim_propositions": ["宋錢如璧撰"],
                    "changes_current_judgment": True,
                    "evidence": [
                        {
                            "source_span_id": "ss_sanche_ed01_p0001_s02",
                            "support_type": "direct",
                            "quote": "錢如璧撰",
                        }
                    ],
                }
            ],
        )
        result = self._norm(submission)
        self.assertEqual(result["rejected"][0]["reason_code"], "REF_001")

    def test_homograph_surface_without_sense_REF_001(self):
        profile = build_profile()
        profile["homographs"] = [{"surface": "驛馬", "sense": None}]
        submission = make_submission(
            "concept_mention",
            "a",
            [
                {
                    "surface": "驛馬",
                    "evidence": [
                        {
                            "source_span_id": "ss_sanche_ed01_p0001_s01",
                            "support_type": "direct",
                            "quote": "三辰",
                        }
                    ],
                }
            ],
        )
        result = self._norm(submission, profile)
        self.assertEqual(result["rejected"][0]["reason_code"], "REF_001")
        self.assertIn("同形字面", result["rejected"][0]["detail"])

    # ------------------------------------------------------------- 双路差异
    def test_reconcile_identical_lanes_no_dispute(self):
        raw = load_raw("submission_assertion_a.yaml")
        raw["lane"] = "b"
        b_sub = validate_submission(copy.deepcopy(raw), technique_id="qizheng")
        lanes = {
            "assertion": {
                "a": self._norm(load_submission("submission_assertion_a.yaml")),
                "b": self._norm(b_sub),
            }
        }
        result = assemble.reconcile_lanes(
            lanes, required_lanes={"assertion": ["a", "b"]}
        )
        self.assertEqual(result["disputes"], [])
        self.assertEqual(len(result["agreed"]["assertion"]), 2)

    def test_reconcile_gold_one_dispute_m4_d001(self):
        lanes, required = self._gold_lanes()
        result = assemble.reconcile_lanes(lanes, required_lanes=required)
        self.assertEqual(len(result["disputes"]), 1)
        dispute = result["disputes"][0]
        self.assertEqual(dispute["dispute_id"], "m4_d001")
        self.assertEqual(dispute["category"], "assertion")
        self.assertEqual(
            dispute["key"],
            [
                ["ss_sanche_ed01_p0001_s02", 8, 12],
                ["ss_sanche_ed01_p0001_s04", 27, 32],
            ],
        )
        self.assertEqual(len(result["agreed"]["assertion"]), 1)
        self.assertEqual(len(result["agreed"]["concept_mention"]), 2)
        b_rejected = [row for row in result["rejected"] if row["lane"] == "b"]
        self.assertEqual(len(b_rejected), 1)
        self.assertEqual(b_rejected[0]["reason_code"], "TXT_001")
        self.assertEqual(b_rejected[0]["item_index"], 2)

    def test_missing_required_lane_refused(self):
        lanes = {
            "assertion": {
                "a": self._norm(load_submission("submission_assertion_a.yaml"))
            }
        }
        with self.assertRaises(ExtractionRefused) as ctx:
            assemble.reconcile_lanes(lanes, required_lanes={"assertion": ["a", "b"]})
        self.assertIn("缺必需路", ctx.exception.message)

    def test_unruled_dispute_refused(self):
        lanes, required = self._gold_lanes()
        with self.assertRaises(ExtractionRefused) as ctx:
            assemble.assemble_candidates(
                spans_doc=self.spans_doc,
                profile=self.profile,
                lane_results=lanes,
                required_lanes=required,
                rulings={},
                id_range=ID_RANGE,
            )
        self.assertIn("未裁决", ctx.exception.message)

    def test_ruling_both_marks_disputed(self):
        lanes, required = self._gold_lanes()
        result = assemble.assemble_candidates(
            spans_doc=self.spans_doc,
            profile=self.profile,
            lane_results=lanes,
            required_lanes=required,
            rulings={"m4_d001": "both"},
            id_range=ID_RANGE,
        )
        assertions = result["candidate_set"]["assertions"]
        self.assertEqual(len(assertions), 3)
        self.assertEqual(
            sum(1 for row in assertions if row["content_status"] == "disputed"), 2
        )

    def test_ruling_neither_moves_to_rejected_ruled_out(self):
        lanes, required = self._gold_lanes()
        result = assemble.assemble_candidates(
            spans_doc=self.spans_doc,
            profile=self.profile,
            lane_results=lanes,
            required_lanes=required,
            rulings={"m4_d001": "neither"},
            id_range=ID_RANGE,
        )
        candidate_set = result["candidate_set"]
        self.assertEqual(len(candidate_set["assertions"]), 1)
        ruled_out = [
            row for row in candidate_set["rejected"] if row["disposition"] == "ruled_out"
        ]
        self.assertEqual(len(ruled_out), 2)
        self.assertTrue(all(row["reason_code"] is None for row in ruled_out))

    def test_id_range_exhausted_ID_001(self):
        lanes, required = self._gold_lanes()
        with self.assertRaises(ExtractionRefused) as ctx:
            assemble.assemble_candidates(
                spans_doc=self.spans_doc,
                profile=self.profile,
                lane_results=lanes,
                required_lanes=required,
                rulings={"m4_d001": "a"},
                id_range={"assertion": [1, 1], "proposition": [1, 1], "pattern": [1, 1]},
            )
        self.assertEqual(ctx.exception.code, "ID_001")
        self.assertIn("号段耗尽", ctx.exception.message)

    def test_gold_counts_and_ids(self):
        lanes, required = self._gold_lanes()
        result = assemble.assemble_candidates(
            spans_doc=self.spans_doc,
            profile=self.profile,
            lane_results=lanes,
            required_lanes=required,
            rulings={"m4_d001": "a"},
            id_range=ID_RANGE,
        )
        candidate_set = result["candidate_set"]
        assertions = candidate_set["assertions"]
        self.assertEqual(
            [(row["assertion_id"], row["proposition"]) for row in assertions],
            [
                ("as_qizheng_000001", "宋錢如璧撰"),
                ("as_qizheng_000002", "三辰通載三十卷"),
            ],
        )
        self.assertEqual(assertions[0]["proposition_id"], "pr_qizheng_000001")
        self.assertEqual(
            [
                (
                    row["source_span_id"],
                    row["start_offset"],
                    row["end_offset"],
                    row["quote"],
                )
                for row in assertions[0]["evidence"]
            ],
            [
                ("ss_sanche_ed01_p0001_s02", 8, 12, "錢如璧撰"),
                ("ss_sanche_ed01_p0001_s04", 27, 32, "宋錢如璧撰"),
            ],
        )
        self.assertEqual(
            [
                (
                    row["surface"],
                    row["evidence"][0]["start_offset"],
                    row["evidence"][0]["end_offset"],
                )
                for row in candidate_set["new_concept_candidates"]
            ],
            [("身宮", 68, 70), ("官祿宮", 119, 122)],
        )
        self.assertEqual(
            candidate_set["counts"],
            {
                "assertions": 2,
                "patterns": 0,
                "school_views": 0,
                "concept_mentions": 0,
                "new_concept_candidates": 2,
                "rejected": 1,
                "disputes": 1,
                "human_decisions": 1,
            },
        )

    def test_school_view_with_synthetic_profile(self):
        profile = build_profile()
        profile["schools"] = [{"school_id": "sch_qizheng_001"}]
        sv_items = [
            {
                "school_id": "sch_qizheng_001",
                "subject": {"kind": "assertion", "key": "宋錢如璧撰"},
                "claim_propositions": ["宋錢如璧撰"],
                "conflict_key": "conflict_a",
                "changes_current_judgment": True,
                "evidence": [
                    {
                        "source_span_id": "ss_sanche_ed01_p0001_s02",
                        "support_type": "direct",
                        "quote": "錢如璧撰",
                    }
                ],
            },
            {
                "school_id": "sch_qizheng_001",
                "subject": {"kind": "assertion", "key": "三辰通載三十卷"},
                "claim_propositions": ["三辰通載三十卷"],
                "conflict_key": "conflict_a",
                "changes_current_judgment": False,
                "evidence": [
                    {
                        "source_span_id": "ss_sanche_ed01_p0001_s04",
                        "support_type": "direct",
                        "quote": "三辰通載三十卷",
                    }
                ],
            },
        ]
        lanes = {
            "assertion": {
                "a": self._norm(load_submission("submission_assertion_a.yaml"), profile),
                "b": self._norm(load_submission("submission_assertion_b.yaml"), profile),
            },
            "school_view": {
                "a": self._norm(make_submission("school_view", "a", copy.deepcopy(sv_items)), profile),
                "b": self._norm(make_submission("school_view", "b", copy.deepcopy(sv_items)), profile),
            },
        }
        calls = {"school_view_id": 0, "conflict_group_id": 0}

        def factory(kind):
            calls[kind] += 1
            prefix = "sv_" if kind == "school_view_id" else "cg_"
            return prefix + ("%032d" % calls[kind])

        result = assemble.assemble_candidates(
            spans_doc=self.spans_doc,
            profile=profile,
            lane_results=lanes,
            required_lanes={"assertion": ["a", "b"], "school_view": ["a", "b"]},
            rulings={"m4_d001": "a"},
            id_range=ID_RANGE,
            id_factory=factory,
        )
        school_views = result["candidate_set"]["school_views"]
        self.assertEqual(len(school_views), 2)
        self.assertEqual(
            school_views[0]["conflict_group_id"], school_views[1]["conflict_group_id"]
        )
        self.assertNotEqual(
            school_views[0]["school_view_id"], school_views[1]["school_view_id"]
        )
        self.assertEqual(calls["conflict_group_id"], 1)

    def test_deterministic_bytes_twice(self):
        lanes, required = self._gold_lanes()
        kwargs = dict(
            spans_doc=self.spans_doc,
            profile=self.profile,
            lane_results=lanes,
            required_lanes=required,
            rulings={"m4_d001": "a"},
            id_range=ID_RANGE,
        )
        first = assemble.assemble_candidates(**kwargs)
        second = assemble.assemble_candidates(**kwargs)
        self.assertEqual(first["candidate_bytes"], second["candidate_bytes"])


if __name__ == "__main__":
    unittest.main()
