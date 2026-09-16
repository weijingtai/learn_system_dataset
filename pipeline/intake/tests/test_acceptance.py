"""M1 电子文本入库验收测试。

synthetic_fixture: true，合成 Ledger 样例。
"""

import unittest
from pathlib import Path

from pipeline.intake.acceptance import check_m1_intake


class TestM1IntakeAcceptance(unittest.TestCase):
    """M1 intake acceptance 检查测试。"""

    def test_m1_check_passes_on_valid_ledger(self):
        """在有效 Ledger 目录上 check_m1_intake 应返回 PASS 项目。"""
        import tempfile
        import yaml
        from pipeline.ledger.service import LedgerService
        import tempfile

        # 创建一个临时 ledger 目录并写入最小 source_manifest
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_dir = Path(tmpdir)
            manifest = {
                "source_id": "test-work",
                "work_title": "Test Work",
                "edition_note": "test edition",
                "technique_id": "tech-001",
                "rights_status": "test rights",
                "release_policy": "full_scan",
                "edition_part": {"artifact_id": "ed01", "label": "test", "pages": ["page_001"]},
                "source_assets": [
                    {
                        "page": "page_001",
                        "path_ref": "page_001.txt",
                        "sha256": "a" * 64,
                        "size": 100,
                        "width": None,
                        "height": None,
                        "object_store": "local",
                        "in_git": False,
                        "yaml_metadata": None,
                        "source_site": "test.org",
                        "source_url": "https://test.org/file",
                        "repo_commit": None,
                    }
                ],
                "files": [],
                "conversion": {"tool": "pipeline.intake", "tool_version": "0.1.0", "inputs": [], "note": "M1 电子文本入库；不做清洗（§9）"},
                "content_status": "machine_extracted",
            }
            with open(ledger_dir / "source_manifest.yaml", "w", encoding="utf-8") as f:
                yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

            results = check_m1_intake(ledger_dir)
            # 检查是否有 PASS 状态的检查项
            passed_checks = [r for r in results if r["status"] == "PASS"]
            self.assertGreater(len(passed_checks), 0,
                               "应至少有 PASS 的检查项")

    def test_m1_check_fails_on_missing_manifest(self):
        """缺少 source_manifest.yaml 时 check_m1_intake 应返回 FAIL。"""
        import tempfile
        from pipeline.intake.acceptance import check_m1_intake

        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_dir = Path(tmpdir)
            # 故意不创建 source_manifest.yaml

            results = check_m1_intake(ledger_dir)
            failed_checks = [r for r in results if r["check"] == "manifest_exists" and r["status"] == "FAIL"]
            self.assertGreater(len(failed_checks), 0,
                               "应检出 manifest_exists FAIL")

    def test_m1_check_blocked_on_no_ledger(self):
        """无 Ledger 目录时 check_m1_intake 应返回 BLOCKED。"""
        from pipeline.intake.acceptance import check_m1_intake

        results = check_m1_intake(Path("/nonexistent/path"))
        blocked_checks = [r for r in results if r["status"] == "BLOCKED"]
        self.assertGreater(len(blocked_checks), 0,
                           "无 Ledger 目录时应返回 BLOCKED")