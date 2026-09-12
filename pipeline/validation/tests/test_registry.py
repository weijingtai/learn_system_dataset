"""ACT 00 单元测试：骨架、14 项 Validator 注册表、错误码闭集与分级判定。

本文件先于实现编写（tests_first）；用例名与 act/00.yaml 的 tests 清单逐字一致。
"""

import unittest

from pipeline.ledger.errors import ERROR_CODES, SchemaViolation

from pipeline.validation import CONSUMPTION_LEVELS
from pipeline.validation.findings import (
    gate_summary,
    level_verdicts,
    make_finding,
    make_report,
)
from pipeline.validation.registry import CHECK_CODES, VALIDATORS
from pipeline.validation.serialize import canonical_json
from pipeline.validation.tests.helpers import fixture_context

# act/00.yaml contract：14 项注册表，顺序固定
EXPECTED_VALIDATORS = (
    ("g1_frozen_bytes", "G1", "validate_frozen_bytes"),
    ("g1_page_registry", "G1", "validate_page_registry"),
    ("g1_content_hashes", "G1", "validate_content_hashes"),
    ("g1_unresolved_chars", "G1", "validate_unresolved_chars"),
    ("g1_replay", "G1", "validate_replay"),
    ("g2_page_accounting", "G2", "validate_page_accounting"),
    ("g2_contiguous_coverage", "G2", "validate_contiguous_coverage"),
    ("g2_batch_partition", "G2", "validate_batch_partition"),
    ("g2_count_reconciliation", "G2", "validate_count_reconciliation"),
    ("g3_span_identity", "G3", "validate_span_identity"),
    ("g3_references", "G3", "validate_references"),
    ("g3_strict_offset_quote", "G3", "validate_strict_offset_quote"),
    ("g3_glyphbox_anchor", "G3", "validate_glyphbox_anchor"),
    ("g3_evidence_level", "G3", "validate_evidence_level"),
)

_SEV = ("error", "warning", "info")


def _severity(a, b, c):
    """构造三级严重度字典。"""
    return {"INTERNAL_DEMO": a, "DEV_SEARCH": b, "PUBLIC_RELEASE": c}


def _subject():
    return {
        "entity_id": "ss_sanche_ed01_p0001_s01",
        "artifact_revision_id": None,
        "page": "page_001",
    }


class RegistryTest(unittest.TestCase):
    def test_validators_count_and_order_exact_14(self):
        self.assertEqual(len(VALIDATORS), 14)
        self.assertEqual(tuple(VALIDATORS), EXPECTED_VALIDATORS)

    def test_all_gates_in_g1_g2_g3(self):
        gates = {gate for _vid, gate, _func in VALIDATORS}
        self.assertEqual(gates, {"G1", "G2", "G3"})

    def test_error_code_mapping_strictly_in_spec_subset(self):
        legal = set(ERROR_CODES) | {None}
        self.assertTrue(CHECK_CODES, "CHECK_CODES 不得为空")
        for name, code in CHECK_CODES.items():
            self.assertIn(code, legal, "检查名 %s 的错误码越出闭集: %r" % (name, code))
        # §5.5 缺口清单：三项无歧义映射，取 None
        self.assertIsNone(CHECK_CODES["count_mismatch"])
        self.assertIsNone(CHECK_CODES["unproofread_glyphs"])
        self.assertIsNone(CHECK_CODES["replay_tool_mismatch"])


class FindingsTest(unittest.TestCase):
    def test_make_finding_validates_code_and_severity(self):
        finding = make_finding(
            "g1_frozen_bytes", "G1", "hash_mismatch", "SRC_003",
            _severity(*_SEV), _subject(),
        )
        self.assertEqual(finding["code"], "SRC_003")
        self.assertEqual(finding["check"], "hash_mismatch")
        self.assertEqual(
            set(finding["severity"]), {"INTERNAL_DEMO", "DEV_SEARCH", "PUBLIC_RELEASE"}
        )
        self.assertEqual(
            finding["subject"],
            {
                "entity_id": "ss_sanche_ed01_p0001_s01",
                "artifact_revision_id": None,
                "page": "page_001",
            },
        )
        # 表外错误码 → SchemaViolation(SCH_002)
        with self.assertRaises(SchemaViolation) as ctx:
            make_finding(
                "g1_frozen_bytes", "G1", "hash_mismatch", "XYZ_001",
                _severity(*_SEV), _subject(),
            )
        self.assertEqual(ctx.exception.code, "SCH_002")
        # 非法严重度值 → SchemaViolation
        with self.assertRaises(SchemaViolation):
            make_finding(
                "g1_frozen_bytes", "G1", "hash_mismatch", "SRC_003",
                _severity("fatal", "error", "error"), _subject(),
            )
        # 缺级键 → SchemaViolation
        with self.assertRaises(SchemaViolation):
            make_finding(
                "g1_frozen_bytes", "G1", "hash_mismatch", "SRC_003",
                {"INTERNAL_DEMO": "error"}, _subject(),
            )

    def test_level_verdicts_internal_demo_warn_passes_but_public_fails(self):
        finding = make_finding(
            "g1_unresolved_chars", "G1", "unresolved_glyph", "SRC_001",
            _severity("warning", "error", "error"), _subject(),
        )
        self.assertEqual(
            level_verdicts([finding], ["succeeded"]),
            {"INTERNAL_DEMO": "passed", "DEV_SEARCH": "failed", "PUBLIC_RELEASE": "failed"},
        )

    def test_level_verdicts_fail_closed_on_skipped_or_errored_task(self):
        finding = make_finding(
            "g1_unresolved_chars", "G1", "unproofread_glyphs", None,
            _severity("info", "info", "info"), _subject(),
        )
        for status in ("skipped_fail_closed", "errored"):
            self.assertEqual(
                level_verdicts([finding], [status]),
                {
                    "INTERNAL_DEMO": "failed",
                    "DEV_SEARCH": "failed",
                    "PUBLIC_RELEASE": "failed",
                },
                "task_status=%s 时三级必须 fail-closed" % status,
            )

    def test_make_report_and_gate_summary_shape(self):
        finding = make_finding(
            "g1_unresolved_chars", "G1", "unproofread_glyphs", None,
            _severity("info", "warning", "error"), _subject(),
        )
        report = make_report(
            "g1_unresolved_chars", "G1", "1.0.0", "succeeded",
            {"spans": 43}, [finding],
        )
        self.assertEqual(report["schema_version"], "0.1.0-draft")
        self.assertEqual(report["task_status"], "succeeded")
        self.assertEqual(report["findings"], [finding])
        summary = gate_summary("INTERNAL_DEMO", [finding], [report])
        self.assertEqual(
            set(summary),
            {"passed", "severe_error_count", "failed_task_count", "pending_rework_count"},
        )
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["severe_error_count"], 0)
        self.assertEqual(summary["failed_task_count"], 0)


class SerializeTest(unittest.TestCase):
    def test_canonical_json_determinism(self):
        doc = {"b": [2, 1], "a": {"d": 4, "c": 3}, "text": "三辰通載"}
        first = canonical_json(doc)
        second = canonical_json({"text": "三辰通載", "a": {"c": 3, "d": 4}, "b": [2, 1]})
        self.assertEqual(first, second)
        self.assertIsInstance(first, bytes)
        # 键排序 + 无多余空白 + 非 ASCII 不转义
        self.assertEqual(
            first.decode("utf-8"),
            '{"a":{"c":3,"d":4},"b":[2,1],"text":"三辰通載"}',
        )

    def test_consumption_levels_closed_set(self):
        self.assertEqual(
            tuple(CONSUMPTION_LEVELS),
            ("INTERNAL_DEMO", "DEV_SEARCH", "PUBLIC_RELEASE"),
        )


class FixtureContextTest(unittest.TestCase):
    def test_fixture_context_loads_all_spans_and_pages(self):
        ctx = fixture_context()
        self.assertEqual(len(ctx["spans_doc"]["spans"]), 43)
        self.assertEqual(len(ctx["raw"]["frozen"]), 17)
        self.assertEqual(
            set(ctx["page_docs"]), {"page_001", "page_002", "page_003"}
        )
        self.assertEqual(ctx["terminal_states"], {"page_002": "known_unrecognizable"})
        self.assertEqual(ctx["target_consumption_level"], "INTERNAL_DEMO")


if __name__ == "__main__":
    unittest.main()
