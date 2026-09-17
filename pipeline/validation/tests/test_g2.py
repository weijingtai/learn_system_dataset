"""ACT 02 单元测试：G2 全书覆盖四项 Validator。

用例名与 act/02.yaml 的 tests 清单逐字一致；全部基于 ``fixture_context()``。
"""

import copy
import unittest

from pipeline.validation.g2_coverage import (
    validate_batch_partition,
    validate_contiguous_coverage,
    validate_count_reconciliation,
    validate_page_accounting,
)
from pipeline.validation.tests.helpers import (
    OFFSET_PAGE,
    fixture_context,
    offset_fixture_context,
)


def _by_check(result, check):
    return [f for f in result["findings"] if f["check"] == check]


class G2FixtureCleanTest(unittest.TestCase):
    def test_fixture_context_passes_all_g2_validators(self):
        ctx = fixture_context()
        for validator in (
            validate_page_accounting,
            validate_contiguous_coverage,
            validate_batch_partition,
            validate_count_reconciliation,
        ):
            self.assertEqual(
                validator(ctx)["findings"], [],
                "%s 在 fixture 上应无发现" % validator.__name__,
            )


class G2PageAccountingTest(unittest.TestCase):
    def test_missing_page_or_unregistered_page_fails_accounting(self):
        missing = fixture_context()
        del missing["page_docs"]["page_003"]
        self.assertTrue(_by_check(validate_page_accounting(missing), "page_missing"))

        unregistered = fixture_context()
        stray = copy.deepcopy(unregistered["spans_doc"]["spans"][0])
        stray["span_id"] = "ss_sanche_ed01_p0999_s01"
        stray["page"] = "page_999"
        unregistered["spans_doc"]["spans"].append(stray)
        self.assertTrue(
            _by_check(validate_page_accounting(unregistered), "page_unregistered")
        )

    def test_deferred_page_fails_accounting(self):
        ctx = fixture_context()
        ctx["terminal_states"] = dict(ctx["terminal_states"])
        ctx["terminal_states"]["page_003"] = "deferred"
        self.assertTrue(_by_check(validate_page_accounting(ctx), "page_deferred"))


class G2ContiguousCoverageTest(unittest.TestCase):
    def test_dropped_span_creates_gap_and_fails_contiguous_coverage(self):
        ctx = fixture_context()
        ctx["spans_doc"]["spans"] = [
            s for s in ctx["spans_doc"]["spans"]
            if s["span_id"] != "ss_sanche_ed01_p0001_s01"
        ]
        self.assertTrue(_by_check(validate_contiguous_coverage(ctx), "coverage_gap"))

    def test_overlapped_span_fails_contiguous_coverage(self):
        ctx = fixture_context()
        ctx["spans_doc"]["spans"][1]["start_offset"] = 4
        self.assertTrue(
            _by_check(validate_contiguous_coverage(ctx), "coverage_overlap")
        )

    def test_modified_span_text_fails_contiguous_coverage(self):
        ctx = fixture_context()
        ctx["spans_doc"]["spans"][0]["text"] = "篡改文本"
        self.assertTrue(
            _by_check(validate_contiguous_coverage(ctx), "span_text_mismatch")
        )


class G2BatchPartitionTest(unittest.TestCase):
    def test_batch_span_leak_or_duplicate_fails_batch_partition(self):
        duplicate = fixture_context()
        clone = copy.deepcopy(duplicate["spans_doc"]["spans"][0])
        clone["batch_id"] = "sanche_b002"
        duplicate["spans_doc"]["spans"].append(clone)
        self.assertTrue(
            _by_check(validate_batch_partition(duplicate), "batch_span_duplicate")
        )

        leak = fixture_context()
        clone2 = copy.deepcopy(leak["spans_doc"]["spans"][0])
        clone2["span_id"] = "ss_sanche_ed01_p0001_s99"
        clone2["batch_id"] = ""
        leak["spans_doc"]["spans"].append(clone2)
        self.assertTrue(_by_check(validate_batch_partition(leak), "batch_span_leak"))


class G2CountReconciliationTest(unittest.TestCase):
    def test_count_mismatch_fails_reconciliation(self):
        ctx = fixture_context()
        ctx["spans_doc"]["span_count"] = 42
        self.assertTrue(
            _by_check(validate_count_reconciliation(ctx), "count_mismatch")
        )


class G2OffsetLevelTest(unittest.TestCase):
    """R83（第 100 条 D5）：offset 档 G2 以 m3 coverage_report 实算值判定。"""

    def test_g2_offset_level_uses_coverage_report_values(self):
        clean = offset_fixture_context()
        for validator in (
            validate_page_accounting,
            validate_contiguous_coverage,
            validate_batch_partition,
            validate_count_reconciliation,
        ):
            self.assertEqual(
                validator(clean)["findings"], [],
                "%s 在 offset 合成上下文上应无发现" % validator.__name__,
            )

        ctx = offset_fixture_context()
        page = list(ctx["coverage_report"]["pages"])[0]
        ctx["coverage_report"]["pages"][page]["coverage"] = 0.5
        findings = _by_check(validate_contiguous_coverage(ctx), "count_mismatch")
        self.assertEqual(len(findings), 1)
        self.assertIn("coverage", findings[0]["detail"])

    def test_g2_offset_level_rejects_unregistered_report_page(self):
        ctx = offset_fixture_context()
        ctx["coverage_report"]["pages"]["page_999"] = dict(
            ctx["coverage_report"]["pages"][OFFSET_PAGE]
        )
        findings = _by_check(validate_page_accounting(ctx), "page_unregistered")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "REF_001")

    def test_g2_offset_level_batch_partition_is_bijective(self):
        ctx = offset_fixture_context()
        ctx["batch_assignments"]["batch_001"] = (
            ctx["batch_assignments"]["batch_001"][:-1]
        )
        self.assertTrue(_by_check(validate_batch_partition(ctx), "batch_span_leak"))


if __name__ == "__main__":
    unittest.main()
