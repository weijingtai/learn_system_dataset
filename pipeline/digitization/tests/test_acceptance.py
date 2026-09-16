"""M2 电子文本清洗验收测试。

synthetic_fixture: true，合成 Ledger 样例。
"""

import unittest
from pathlib import Path

from pipeline.digitization.acceptance import check_m2_sanitization


class TestM2SanitizationAcceptance(unittest.TestCase):
    """M2 sanitization acceptance 检查测试。"""

    def test_m2_check_passes_on_valid_ledger(self):
        """在有效 Ledger 目录上 check_m2_sanitization 应返回 PASS 项目。"""
        import tempfile
        import yaml

        # 创建一个临时 ledger 目录并写入最小所需 artifact
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_dir = Path(tmpdir)

            # 写入 sanitization_report.yaml
            report = {
                "schema_version": "0.1.0-draft",
                "findings": [],
                "patches": [],
                "summary": {"deferred_count": 0},
            }
            with open(ledger_dir / "sanitization_report.yaml", "w", encoding="utf-8") as f:
                yaml.dump(report, f, default_flow_style=False, sort_keys=False)

            # 写入 deterministic_patch_set.yaml
            with open(ledger_dir / "deterministic_patch_set.yaml", "w", encoding="utf-8") as f:
                yaml.dump([], f, default_flow_style=False, sort_keys=False)

            # 写入 cleaned_text_revision
            with open(ledger_dir / "cleaned_text_revision", "w", encoding="utf-8") as f:
                f.write("清洗后的文本内容")

            results = check_m2_sanitization(ledger_dir)
            passed_checks = [r for r in results if r["status"] == "PASS"]
            self.assertGreater(len(passed_checks), 0,
                               "应至少有 PASS 的检查项")

    def test_m2_check_fails_on_deferred(self):
        """有 deferred findings 时 check_m2_sanitization 应返回 FAIL（no_deferred）。"""
        import tempfile
        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_dir = Path(tmpdir)

            report = {
                "schema_version": "0.1.0-draft",
                "findings": [],
                "patches": [],
                "summary": {"deferred_count": 1},
            }
            with open(ledger_dir / "sanitization_report.yaml", "w", encoding="utf-8") as f:
                yaml.dump(report, f, default_flow_style=False, sort_keys=False)

            results = check_m2_sanitization(ledger_dir)
            failed_checks = [r for r in results if r["check"] == "no_deferred" and r["status"] == "FAIL"]
            self.assertGreater(len(failed_checks), 0,
                               "应检出 no_deferred FAIL 时 deferred_count > 0")

    def test_m2_check_fails_on_missing_report(self):
        """缺少 sanitization_report.yaml 时 check_m2_sanitization 应返回 FAIL。"""
        import tempfile
        import yaml
        from pipeline.digitization.acceptance import check_m2_sanitization

        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_dir = Path(tmpdir)
            # 故意不创建 sanitization_report.yaml

            results = check_m2_sanitization(ledger_dir)
            failed_checks = [r for r in results if r["check"] == "report_exists" and r["status"] == "FAIL"]
            self.assertGreater(len(failed_checks), 0,
                               "应检出 report_exists FAIL")

    def test_m2_check_blocked_on_no_ledger(self):
        """无 Ledger 目录时 check_m2_sanitization 应返回 BLOCKED。"""
        from pipeline.digitization.acceptance import check_m2_sanitization

        results = check_m2_sanitization(Path("/nonexistent/path"))
        blocked_checks = [r for r in results if r["status"] == "BLOCKED"]
        self.assertGreater(len(blocked_checks), 0,
                           "无 Ledger 目录时应返回 BLOCKED")