"""M2 事务层单元测试（synthetic_fixture: true）。"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.digitization.cleaner import Finding
from pipeline.digitization.errors import DigitizationRefused
from pipeline.digitization.step import run_m2
from pipeline.ledger import ids
from pipeline.ledger.service import LedgerService


def _fixture_source():
    return {
        "source_id": "src_qianyuan_ed01",
        "technique_id": "qizheng",
        "edition_part": {
            "artifact_id": "art_000000000000000000000000000000e1",
            "label": "周易卷一",
        },
    }


class TestStep(unittest.TestCase):
    """M2 Ledger 写路径事务测试集。"""

    def setUp(self):
        self.tmp_ledger_dir = tempfile.TemporaryDirectory()
        self.service = LedgerService(self.tmp_ledger_dir.name)
        self.source_info = _fixture_source()
        self.edition_part_id = self.source_info["edition_part"]["artifact_id"]

        # 先在 Ledger 中注入一个 raw_text revision 作为 M2 输入
        self.proc_run_id = self.service.create_processing_run(
            "edition_run", self.edition_part_id, self.source_info["technique_id"]
        )
        cfg_bytes = json.dumps({"stage": "m1"}).encode("utf-8")
        _, cfg_rev = self.service.put_run_artifact(
            self.proc_run_id,
            "configuration",
            cfg_bytes,
            producer_module="test_setup",
            producer_version="0.1.0",
        )
        srun_init_id = ids.new_id("step_run_id")
        self.service.begin_step_run(
            {
                "schema_version": "1.0.0",
                "processing_run_id": self.proc_run_id,
                "step_run_id": srun_init_id,
                "input_artifact_ids": [],
                "technique_profile_id": self.source_info["technique_id"],
                "configuration_artifact_id": cfg_rev,
            }
        )
        self.raw_content = "太极图说\n天地之初，太极肇判。\u200b".encode("utf-8")
        _, self.raw_text_rev_id = self.service.put_artifact(
            srun_init_id,
            "raw_text",
            self.raw_content,
            producer_module="test_setup",
            producer_version="0.1.0",
        )
        self.service.seal_revision(self.raw_text_rev_id)
        self.service.finish_step_run(
            srun_init_id,
            {
                "schema_version": "1.0.0",
                "processing_run_id": self.proc_run_id,
                "step_run_id": srun_init_id,
                "status_version": 1,
                "status": "succeeded",
                "output_artifact_ids": [self.raw_text_rev_id],
                "validation_report_ids": [],
                "log_artifact_ids": [],
                "failure_artifact_ids": [],
            },
        )

    def tearDown(self):
        self.service.close()
        self.tmp_ledger_dir.cleanup()

    def test_run_m2_success(self):
        """synthetic_fixture: true，合法输入 → 三个 revision_id + gate_result.passed=True。"""
        res = run_m2(
            self.service,
            self.raw_text_rev_id,
            self.source_info,
            self.edition_part_id,
        )
        self.assertIn("cleaned_revision_id", res)
        self.assertIn("patch_revision_id", res)
        self.assertIn("report_revision_id", res)
        self.assertIn("gate_result", res)
        self.assertIn("step_run_id", res)

        self.assertTrue(res["cleaned_revision_id"].startswith("rev_"))
        self.assertTrue(res["patch_revision_id"].startswith("rev_"))
        self.assertTrue(res["report_revision_id"].startswith("rev_"))
        self.assertTrue(res["gate_result"].passed)

        # 检查 StepRun 终态
        step = self.service.get_step_run(res["step_run_id"])
        self.assertIsNotNone(step)
        self.assertEqual(step["status"], "succeeded")

    def test_run_m2_gate_failure(self):
        """synthetic_fixture: true，deferred findings → gate_result.passed=False, failed_check="m2_gate"。"""
        # 模拟 cleaner 产生 deferred finding
        deferred_finding = Finding(
            finding_id="missing@0-1",
            kind="missing",
            raw_start=0,
            raw_end=1,
            raw_excerpt="太",
            context="太极",
            action="flagged",
            patch_id=None,
            basis="缺字标记",
            terminal_state="deferred",
        )

        with patch("pipeline.digitization.step.clean_text") as mock_clean:
            from pipeline.digitization.cleaner import CleanResult

            mock_clean.return_value = CleanResult(
                cleaned_text=self.raw_content.decode("utf-8"),
                findings=[deferred_finding],
            )
            res = run_m2(
                self.service,
                self.raw_text_rev_id,
                self.source_info,
                self.edition_part_id,
            )
            self.assertFalse(res["gate_result"].passed)
            self.assertEqual(res["failed_check"], "m2_gate")
            step = self.service.get_step_run(res["step_run_id"])
            self.assertEqual(step["status"], "failed")

    def test_run_m2_duplicate_refused(self):
        """synthetic_fixture: true，同 edition_part_id 二次运行 → DigitizationRefused。"""
        res = run_m2(
            self.service,
            self.raw_text_rev_id,
            self.source_info,
            self.edition_part_id,
        )
        self.assertTrue(res["gate_result"].passed)

        # 二次运行相同 edition_part_id 应当抛出 DigitizationRefused
        with self.assertRaises(DigitizationRefused) as ctx:
            run_m2(
                self.service,
                self.raw_text_rev_id,
                self.source_info,
                self.edition_part_id,
            )
        self.assertIn("M2 已封存", str(ctx.exception))

    def test_run_m2_zero_writes_on_failure(self):
        """synthetic_fixture: true，失败时 Ledger 行数不变。"""
        def count_core_tables():
            tables = [
                "artifacts",
                "artifact_revisions",
                "step_runs",
                "processing_runs",
                "stage_checkpoints",
            ]
            counts = {}
            for t in tables:
                row = self.service.store.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
                counts[t] = row[0]
            return counts

        before = count_core_tables()

        bad_source = _fixture_source()
        bad_source["edition_part"]["artifact_id"] = "art_000000000000000000000000000000e2"

        with self.assertRaises(DigitizationRefused):
            run_m2(
                self.service,
                self.raw_text_rev_id,
                bad_source,
                self.edition_part_id,
            )

        after = count_core_tables()
        self.assertEqual(before, after, "预检被拒时核心表行数必须完全不变")

    def test_run_m2_raw_text_unchanged(self):
        """synthetic_fixture: true，raw_text 修订不可变。"""
        content_before = self.service.objects.get(
            self.service.store.get_revision(self.raw_text_rev_id)["sha256"]
        )
        sha_before = hashlib.sha256(content_before).hexdigest()

        run_m2(
            self.service,
            self.raw_text_rev_id,
            self.source_info,
            self.edition_part_id,
        )

        content_after = self.service.objects.get(
            self.service.store.get_revision(self.raw_text_rev_id)["sha256"]
        )
        sha_after = hashlib.sha256(content_after).hexdigest()

        self.assertEqual(content_before, content_after)
        self.assertEqual(sha_before, sha_after)

    def test_run_m2_manifest_sha256(self):
        """synthetic_fixture: true，sanitization_report 内容 sha256 可取回。"""
        res = run_m2(
            self.service,
            self.raw_text_rev_id,
            self.source_info,
            self.edition_part_id,
        )
        report_rev_id = res["report_revision_id"]
        rev = self.service.get_revision(report_rev_id)
        self.assertIsNotNone(rev)

        content_bytes = self.service.objects.get(rev["sha256"])
        self.assertIsNotNone(content_bytes)
        computed_sha = hashlib.sha256(content_bytes).hexdigest()
        self.assertEqual(computed_sha, rev["sha256"])

    def test_run_m2_cli_success(self):
        """synthetic_fixture: true，exit 0，"M2 OK"。"""
        with tempfile.TemporaryDirectory() as tmp_cli_ledger:
            cli_service = LedgerService(tmp_cli_ledger)
            p_run_id = cli_service.create_processing_run(
                "edition_run", self.edition_part_id, self.source_info["technique_id"]
            )
            cfg_bytes = json.dumps({"stage": "m1"}).encode("utf-8")
            _, cfg_rev = cli_service.put_run_artifact(
                p_run_id,
                "configuration",
                cfg_bytes,
                producer_module="test_cli",
                producer_version="0.1.0",
            )
            s_init = ids.new_id("step_run_id")
            cli_service.begin_step_run(
                {
                    "schema_version": "1.0.0",
                    "processing_run_id": p_run_id,
                    "step_run_id": s_init,
                    "input_artifact_ids": [],
                    "technique_profile_id": self.source_info["technique_id"],
                    "configuration_artifact_id": cfg_rev,
                }
            )
            _, raw_rev = cli_service.put_artifact(
                s_init,
                "raw_text",
                "测试文本内容".encode("utf-8"),
                producer_module="test_cli",
                producer_version="0.1.0",
            )
            cli_service.seal_revision(raw_rev)
            cli_service.finish_step_run(
                s_init,
                {
                    "schema_version": "1.0.0",
                    "processing_run_id": p_run_id,
                    "step_run_id": s_init,
                    "status_version": 1,
                    "status": "succeeded",
                    "output_artifact_ids": [raw_rev],
                    "validation_report_ids": [],
                    "log_artifact_ids": [],
                    "failure_artifact_ids": [],
                },
            )
            cli_service.close()

            with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
                json.dump(self.source_info, f, ensure_ascii=False)
                src_json_path = f.name

            try:
                cmd = [
                    sys.executable,
                    "-m",
                    "pipeline.digitization",
                    "--raw-text-revision-id",
                    raw_rev,
                    "--source-json",
                    src_json_path,
                    "--edition-part-id",
                    self.edition_part_id,
                    "--ledger-dir",
                    tmp_cli_ledger,
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
                lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
                self.assertTrue(lines[-1].startswith("M2 OK"), f"Output末行非 M2 OK: {proc.stdout}")
            finally:
                Path(src_json_path).unlink(missing_ok=True)

    def test_run_m2_cli_gate_failure(self):
        """synthetic_fixture: true，exit 1。"""
        with tempfile.TemporaryDirectory() as tmp_cli_ledger:
            cli_service = LedgerService(tmp_cli_ledger)
            p_run_id = cli_service.create_processing_run(
                "edition_run", self.edition_part_id, self.source_info["technique_id"]
            )
            cfg_bytes = json.dumps({"stage": "m1"}).encode("utf-8")
            _, cfg_rev = cli_service.put_run_artifact(
                p_run_id,
                "configuration",
                cfg_bytes,
                producer_module="test_cli",
                producer_version="0.1.0",
            )
            s_init = ids.new_id("step_run_id")
            cli_service.begin_step_run(
                {
                    "schema_version": "1.0.0",
                    "processing_run_id": p_run_id,
                    "step_run_id": s_init,
                    "input_artifact_ids": [],
                    "technique_profile_id": self.source_info["technique_id"],
                    "configuration_artifact_id": cfg_rev,
                }
            )
            _, raw_rev = cli_service.put_artifact(
                s_init,
                "raw_text",
                "文本【缺字】测试".encode("utf-8"),
                producer_module="test_cli",
                producer_version="0.1.0",
            )
            cli_service.seal_revision(raw_rev)
            cli_service.finish_step_run(
                s_init,
                {
                    "schema_version": "1.0.0",
                    "processing_run_id": p_run_id,
                    "step_run_id": s_init,
                    "status_version": 1,
                    "status": "succeeded",
                    "output_artifact_ids": [raw_rev],
                    "validation_report_ids": [],
                    "log_artifact_ids": [],
                    "failure_artifact_ids": [],
                },
            )
            cli_service.close()

            with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
                json.dump(self.source_info, f, ensure_ascii=False)
                src_json_path = f.name

            try:
                cmd = [
                    sys.executable,
                    "-c",
                    (
                        "from unittest.mock import patch\n"
                        "from pipeline.digitization.cleaner import Finding, CleanResult\n"
                        "import pipeline.digitization.__main__ as main\n"
                        "import sys\n"
                        "f = Finding('m1', 'missing', 0, 1, '缺', '', 'flagged', None, '缺字', 'deferred')\n"
                        "with patch('pipeline.digitization.step.clean_text', return_value=CleanResult('缺', [f])):\n"
                        "    sys.argv = ['pipeline.digitization', '--raw-text-revision-id', "
                        f"'{raw_rev}', '--source-json', '{src_json_path}', '--edition-part-id', "
                        f"'{self.edition_part_id}', '--ledger-dir', '{tmp_cli_ledger}']\n"
                        "    main.main()\n"
                    ),
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True)
                self.assertEqual(proc.returncode, 1, f"stdout: {proc.stdout}, stderr: {proc.stderr}")
            finally:
                Path(src_json_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
