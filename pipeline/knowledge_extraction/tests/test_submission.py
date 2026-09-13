"""ACT 00 提交件契约 ``validate_submission`` 的单测（先红后绿）。"""

import copy
import unittest
from pathlib import Path

import yaml

from pipeline.knowledge_extraction.submission import validate_submission
from pipeline.ledger.errors import SchemaViolation

DATA = Path(__file__).resolve().parent / "data" / "appendix_a"


def load(name):
    """读取附录 A 的测试数据副本。"""
    with open(DATA / name, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.base = load("submission_assertion_a.yaml")

    def test_valid_assertion_submission_passes(self):
        doc = validate_submission(copy.deepcopy(self.base), technique_id="qizheng")
        item = doc["items"][0]
        self.assertEqual(item["conditions"], [])
        self.assertEqual(item["exceptions"], [])
        self.assertEqual(item["concept_refs"], [])
        self.assertEqual(item["school_ids"], [])
        self.assertIsNone(item["status"])
        self.assertIsNone(doc["source_task"])
        self.assertEqual(doc["skipped"], [])
        self.assertEqual(doc["adapter_notes"], [])

    def test_mixed_category_item_key_SCH_002(self):
        doc = copy.deepcopy(self.base)
        doc["items"][0]["surface"] = "身宮"
        with self.assertRaises(SchemaViolation) as ctx:
            validate_submission(doc, technique_id="qizheng")
        self.assertEqual(ctx.exception.code, "SCH_002")
        self.assertIn("类别混合", ctx.exception.message)

    def test_missing_required_field_SCH_001(self):
        doc = copy.deepcopy(self.base)
        del doc["items"][0]["proposition"]
        with self.assertRaises(SchemaViolation) as ctx:
            validate_submission(doc, technique_id="qizheng")
        self.assertEqual(ctx.exception.code, "SCH_001")

    def test_unknown_enum_values_SCH_002(self):
        top_cases = (("category", "bogus"), ("lane", "z"), ("channel", "bogus"))
        for key, value in top_cases:
            with self.subTest(key=key):
                doc = copy.deepcopy(self.base)
                doc[key] = value
                with self.assertRaises(SchemaViolation) as ctx:
                    validate_submission(doc, technique_id="qizheng")
                self.assertEqual(ctx.exception.code, "SCH_002")
        for field in ("relation", "layer"):
            with self.subTest(key=field):
                doc = copy.deepcopy(self.base)
                doc["items"][0][field] = "bogus"
                with self.assertRaises(SchemaViolation) as ctx:
                    validate_submission(doc, technique_id="qizheng")
                self.assertEqual(ctx.exception.code, "SCH_002")
        with self.subTest(key="support_type"):
            doc = copy.deepcopy(self.base)
            doc["items"][0]["evidence"][0]["support_type"] = "bogus"
            with self.assertRaises(SchemaViolation) as ctx:
                validate_submission(doc, technique_id="qizheng")
            self.assertEqual(ctx.exception.code, "SCH_002")

    def test_status_above_machine_extracted_SCH_002(self):
        for status in ("cross_model_reviewed", "expert_verified"):
            with self.subTest(status=status):
                doc = copy.deepcopy(self.base)
                doc["items"][0]["status"] = status
                with self.assertRaises(SchemaViolation) as ctx:
                    validate_submission(doc, technique_id="qizheng")
                self.assertEqual(ctx.exception.code, "SCH_002")

    def test_technique_id_mismatch_SCH_002(self):
        doc = copy.deepcopy(self.base)
        doc["technique_id"] = "ziwei"
        with self.assertRaises(SchemaViolation) as ctx:
            validate_submission(doc, technique_id="qizheng")
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_unpaired_span_char_range_SCH_001(self):
        doc = copy.deepcopy(self.base)
        del doc["items"][0]["evidence"][0]["span_char_end"]
        with self.assertRaises(SchemaViolation) as ctx:
            validate_submission(doc, technique_id="qizheng")
        self.assertEqual(ctx.exception.code, "SCH_001")

    def test_school_view_subject_shape(self):
        doc = {
            "schema_version": "0.1.0-draft",
            "category": "school_view",
            "lane": "a",
            "channel": "fixture_gold",
            "technique_id": "qizheng",
            "producer": {"kind": "human", "name": "local_owner"},
            "items": [
                {
                    "school_id": "sch_qizheng_001",
                    "subject": {"kind": "assertion", "key": "宋錢如璧撰"},
                    "claim_propositions": ["宋錢如璧撰"],
                    "changes_current_judgment": True,
                    "evidence": [
                        {
                            "source_span_id": "ss_sanche_ed01_p0001_s02",
                            "support_type": "direct",
                        }
                    ],
                }
            ],
        }
        validated = validate_submission(copy.deepcopy(doc), technique_id="qizheng")
        self.assertTrue(validated["items"][0]["changes_current_judgment"])
        bad = copy.deepcopy(doc)
        bad["items"][0]["subject"] = {"kind": "bogus", "key": ""}
        with self.assertRaises(SchemaViolation):
            validate_submission(bad, technique_id="qizheng")

    def test_concept_mention_fixture_submission_passes(self):
        doc = validate_submission(
            load("submission_concept_mention_a.yaml"), technique_id="qizheng"
        )
        self.assertEqual(len(doc["items"]), 2)
        self.assertIsNone(doc["items"][0]["concept_ref"])
        self.assertEqual(doc["items"][0]["surface"], "身宮")


if __name__ == "__main__":
    unittest.main()
