"""ACT impl-04/00：消费级别准入纯函数的测试。

统一「fixture 同型输入」见 ``_fixture_like``；所有期望值逐字取自 ACT 契约。
"""

import unittest

from pipeline.dataset_compiler.levels import (
    derive_source_release,
    evaluate_admission,
)
from pipeline.dataset_compiler.errors import DatasetRefused
from pipeline.ledger.errors import SchemaViolation


def _fixture_like():
    """fixture（mini_ed01）同型的准入输入。"""
    return {
        "content_statuses": {"machine_extracted"},
        "evidence_level": "glyphbox_level",
        "release_policy": "derived_page_images_only",
        "rights_status": "public_domain_text（文字公版；扫描件分发权 unconfirmed）",
        "schema_versions": {
            "evidence_map_pack": "0.1.0-draft",
            "release_manifest": "0.1.0-draft",
            "source_asset_pack": "0.1.0-draft",
        },
        "min_app_version": None,
    }


def _admit(consumption_level, **overrides):
    kwargs = _fixture_like()
    kwargs.update(overrides)
    return evaluate_admission(consumption_level=consumption_level, **kwargs)


class InternalDemoAdmissionTests(unittest.TestCase):
    """INTERNAL_DEMO 是首纵切唯一签发的消费级别。"""

    def test_internal_demo_machine_extracted_admitted_with_watermark(self):
        result = _admit("INTERNAL_DEMO")
        self.assertTrue(result["admitted"])
        self.assertEqual(result["unmet"], [])
        self.assertTrue(result["watermark_required"])
        self.assertEqual(result["source_release"], "dev")
        self.assertEqual(result["isolation"], "internal_only")

    def test_internal_demo_offset_level_admitted(self):
        result = _admit("INTERNAL_DEMO", evidence_level="offset_level")
        self.assertTrue(result["admitted"])
        self.assertEqual(result["unmet"], [])


class AdmissionRejectionTests(unittest.TestCase):
    """非法枚举在准入前以 SCH_002/SCH_001 拒绝。"""

    def test_unknown_level_SCH_002(self):
        with self.assertRaises(SchemaViolation) as ctx:
            _admit("internal_demo")
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_unknown_evidence_level_SCH_002(self):
        with self.assertRaises(SchemaViolation) as ctx:
            _admit("INTERNAL_DEMO", evidence_level="unknown_level")
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_unknown_content_status_SCH_002(self):
        with self.assertRaises(SchemaViolation) as ctx:
            _admit("INTERNAL_DEMO", content_statuses={"not_a_status"})
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_deprecated_content_refused(self):
        with self.assertRaises(DatasetRefused) as ctx:
            _admit("INTERNAL_DEMO", content_statuses={"deprecated"})
        self.assertEqual(ctx.exception.code, "SCH_002")
        self.assertIn("deprecated", str(ctx.exception))

    def test_empty_statuses_SCH_001(self):
        with self.assertRaises(SchemaViolation) as ctx:
            _admit("INTERNAL_DEMO", content_statuses=set())
        self.assertEqual(ctx.exception.code, "SCH_001")

    def test_min_app_version_bad_format_SCH_002(self):
        with self.assertRaises(SchemaViolation) as ctx:
            _admit("INTERNAL_DEMO", min_app_version="v1")
        self.assertEqual(ctx.exception.code, "SCH_002")


class FailClosedLevelTests(unittest.TestCase):
    """DEV_SEARCH / PUBLIC_RELEASE 一律 fail-closed。"""

    def test_dev_search_not_admitted(self):
        result = _admit("DEV_SEARCH")
        self.assertFalse(result["admitted"])
        self.assertEqual(result["unmet"], ["dev_search_gates_not_implemented"])

    def test_public_release_fixture_like_inputs_unmet_exact(self):
        result = _admit("PUBLIC_RELEASE")
        self.assertFalse(result["admitted"])
        self.assertEqual(
            result["unmet"],
            [
                "content_not_expert_verified",
                "draft_schema",
                "min_app_version_unset",
                "public_release_gates_not_implemented",
                "rights_unconfirmed",
                "source_release_dev",
            ],
        )

    def test_public_release_all_expert_still_not_admitted(self):
        result = _admit(
            "PUBLIC_RELEASE",
            content_statuses={"expert_verified"},
            schema_versions={
                "evidence_map_pack": "1.0.0",
                "release_manifest": "1.0.0",
                "source_asset_pack": "1.0.0",
            },
            rights_status="public_domain",
            min_app_version="1.2.3",
        )
        self.assertFalse(result["admitted"])
        self.assertEqual(result["unmet"], ["public_release_gates_not_implemented"])
        self.assertEqual(result["source_release"], "release")

    def test_reference_and_hash_only_not_implemented(self):
        result = _admit(
            "INTERNAL_DEMO", release_policy="reference_and_hash_only"
        )
        self.assertFalse(result["admitted"])
        self.assertEqual(result["unmet"], ["release_policy_not_implemented"])


class SourceReleaseDerivationTests(unittest.TestCase):
    """D9：只有全部 expert_verified 才是 release 级（source_verified 不算）。"""

    def test_source_release_derivation_table(self):
        cases = [
            ({"expert_verified"}, "release"),
            ({"source_verified"}, "dev"),
            ({"expert_verified", "source_verified"}, "dev"),
            ({"cross_model_reviewed"}, "dev"),
            ({"expert_verified", "disputed"}, "dev"),
        ]
        for statuses, expected in cases:
            with self.subTest(statuses=statuses):
                self.assertEqual(derive_source_release(statuses), expected)


if __name__ == "__main__":
    unittest.main()
