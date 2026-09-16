"""M2 Gate 单元测试（synthetic_fixture: true）。"""

import ast
import inspect
import unittest
from pathlib import Path

import pipeline.digitization
from pipeline.digitization.gate import GateResult, evaluate_m2_gate


class TestGate(unittest.TestCase):
    """M2 Gate 放行判定测试集。"""

    def _make_valid_report(self):
        return {
            "schema_version": "0.1.0-draft",
            "findings": [
                {
                    "finding_id": "control_char@10-11",
                    "kind": "control_char",
                    "raw_start": 10,
                    "raw_end": 11,
                    "raw_excerpt": "\u200b",
                    "context": "ctx",
                    "action": "patched",
                    "patch_id": "patch_001",
                    "basis": "basis",
                    "terminal_state": "processed",
                }
            ],
            "patches": [
                {
                    "patch_id": "patch_001",
                    "raw_start": 10,
                    "raw_end": 11,
                    "cleaned_start": 10,
                    "cleaned_end": 10,
                    "action": "patched",
                    "basis": "basis",
                }
            ],
            "summary": {
                "replacement_char": 0,
                "private_use_area": 0,
                "escape_residue": 0,
                "watermark": 0,
                "header_footer": 0,
                "duplicate": 0,
                "missing": 0,
                "textualized_diagram": 0,
                "variant_mixed": 0,
                "suspected_error": 0,
                "control_char": 1,
                "encoding_issue": 0,
                "deferred_count": 0,
            },
        }

    def test_gate_passes_clean_input(self):
        """synthetic_fixture: true，无 findings → passed=True。"""
        report = {
            "schema_version": "0.1.0-draft",
            "findings": [],
            "patches": [],
            "summary": {
                "replacement_char": 0,
                "private_use_area": 0,
                "escape_residue": 0,
                "watermark": 0,
                "header_footer": 0,
                "duplicate": 0,
                "missing": 0,
                "textualized_diagram": 0,
                "variant_mixed": 0,
                "suspected_error": 0,
                "control_char": 0,
                "encoding_issue": 0,
                "deferred_count": 0,
            },
        }
        res = evaluate_m2_gate(report)
        self.assertTrue(res.passed)
        self.assertEqual(res.failed_checks, [])

    def test_gate_passes_with_processed_findings(self):
        """synthetic_fixture: true，有 processed findings → passed=True。"""
        report = self._make_valid_report()
        res = evaluate_m2_gate(report)
        self.assertTrue(res.passed)
        self.assertEqual(res.failed_checks, [])

    def test_gate_fails_deferred(self):
        """synthetic_fixture: true，deferred_count > 0 → passed=False, 'no_deferred'。"""
        report = self._make_valid_report()
        report["summary"]["deferred_count"] = 1
        res = evaluate_m2_gate(report)
        self.assertFalse(res.passed)
        self.assertIn("no_deferred", res.failed_checks)

    def test_gate_fails_invalid_kind(self):
        """synthetic_fixture: true，非法 kind → passed=False, 'findings_valid'。"""
        report = self._make_valid_report()
        report["findings"][0]["kind"] = "illegal_kind_name"
        res = evaluate_m2_gate(report)
        self.assertFalse(res.passed)
        self.assertIn("findings_valid", res.failed_checks)

    def test_gate_fails_invalid_terminal_state(self):
        """synthetic_fixture: true，非法 terminal_state → passed=False, 'findings_valid'。"""
        report = self._make_valid_report()
        report["findings"][0]["terminal_state"] = "illegal_state"
        res = evaluate_m2_gate(report)
        self.assertFalse(res.passed)
        self.assertIn("findings_valid", res.failed_checks)

    def test_gate_fails_patch_missing(self):
        """synthetic_fixture: true，patch_id 不在 patches 中 → passed=False, 'patches_consistent'。"""
        report = self._make_valid_report()
        report["findings"][0]["patch_id"] = "non_existent_patch"
        res = evaluate_m2_gate(report)
        self.assertFalse(res.passed)
        self.assertIn("patches_consistent", res.failed_checks)

    def test_gate_fails_summary_mismatch(self):
        """synthetic_fixture: true，计数不符 → passed=False, 'summary_consistent'。"""
        report = self._make_valid_report()
        report["summary"]["control_char"] = 99  # 实际只有 1 个
        res = evaluate_m2_gate(report)
        self.assertFalse(res.passed)
        self.assertIn("summary_consistent", res.failed_checks)

    def test_gate_fails_invalid_report(self):
        """synthetic_fixture: true，缺 findings 键 → passed=False, 'report_valid'。"""
        report = self._make_valid_report()
        del report["findings"]
        res = evaluate_m2_gate(report)
        self.assertFalse(res.passed)
        self.assertIn("report_valid", res.failed_checks)

    def test_gate_accepts_every_terminal_state(self):
        """synthetic_fixture: true，权威闭集里每一个终态都须通过 findings_valid（第 96 条 D1）。"""
        for state in pipeline.digitization.TERMINAL_STATES:
            with self.subTest(terminal_state=state):
                report = self._make_valid_report()
                report["findings"][0]["terminal_state"] = state
                res = evaluate_m2_gate(report)
                self.assertNotIn(
                    "findings_valid",
                    res.failed_checks,
                    f"权威终态 {state} 被 findings_valid 拒绝",
                )

    def test_gate_rejects_stale_ocr_terminal_states(self):
        """synthetic_fixture: true，OCR 路线遗留的 retained/rejected 不在权威闭集，须被拒。"""
        for state in ("retained", "rejected"):
            with self.subTest(terminal_state=state):
                self.assertNotIn(state, pipeline.digitization.TERMINAL_STATES)
                report = self._make_valid_report()
                report["findings"][0]["terminal_state"] = state
                res = evaluate_m2_gate(report)
                self.assertIn(
                    "findings_valid",
                    res.failed_checks,
                    f"遗留终态 {state} 未被 findings_valid 拒绝",
                )

    def test_gate_terminal_states_is_package_constant(self):
        """gate.TERMINAL_STATES 必须与包常量是同一个对象（is，非 ==），防止再次分叉。"""
        from pipeline.digitization import gate

        self.assertIs(gate.TERMINAL_STATES, pipeline.digitization.TERMINAL_STATES)

    def test_gate_independence(self):
        """不 import cleaner/patcher/reporter/raw_text。"""
        from pipeline.digitization import gate

        source = inspect.getsource(gate)
        tree = ast.parse(source)
        forbidden = {"cleaner", "patcher", "reporter", "raw_text"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    for f in forbidden:
                        self.assertNotIn(f, parts, f"gate.py 非法 import 了 {f}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    parts = node.module.split(".")
                    for f in forbidden:
                        self.assertNotIn(f, parts, f"gate.py 非法 from ... import 了 {f}")
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden, f"gate.py 非法引入了 {alias.name}")


if __name__ == "__main__":
    unittest.main()
