"""ACT impl-08/06：CLI 的单元测试（规格 §5）。

先写本文件，运行 `.venv/bin/python -m unittest discover -s pipeline/orchestrator/tests -t .`
取得 ImportError 全红（Red），再实现 `pipeline/orchestrator/__main__.py`。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline.ledger import ids
from pipeline.ledger.service import LedgerService

REPO_ROOT = Path(__file__).resolve().parents[3]


def _env():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["LC_ALL"] = "en_US.UTF-8"
    return env


class TestOrchestratorCli(unittest.TestCase):
    """覆盖 BDD §7.6：CLI 末行与退出码纪律。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "ledger"
        self.root.mkdir(parents=True, exist_ok=True)

    def run_cli(self, *args):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "pipeline.orchestrator",
                "--root",
                str(self.root),
                *args,
            ],
            cwd=str(REPO_ROOT),
            env=_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )

    @staticmethod
    def last_line(result):
        return result.stdout.decode("utf-8").strip().splitlines()[-1]

    def test_cli_start_then_advance_refused_imported_m1(self):
        edition_part_id = ids.new_id("artifact_id")
        started = self.run_cli(
            "start", "--edition-part", edition_part_id, "--technique", "qizheng"
        )
        self.assertEqual(started.returncode, 0, started.stderr.decode("utf-8"))
        self.assertTrue(self.last_line(started).startswith("ORCH STARTED prun_"))
        processing_run_id = self.last_line(started).split()[-1]

        advanced = self.run_cli(
            "advance",
            "--run",
            processing_run_id,
            "--edition-part",
            edition_part_id,
            "--technique",
            "qizheng",
        )
        self.assertEqual(advanced.returncode, 2, advanced.stderr.decode("utf-8"))
        self.assertTrue(self.last_line(advanced).startswith("ORCH REFUSED m1"))

    def test_cli_status_json_has_four_query_keys(self):
        edition_part_id = ids.new_id("artifact_id")
        started = self.run_cli(
            "start", "--edition-part", edition_part_id, "--technique", "qizheng"
        )
        processing_run_id = self.last_line(started).split()[-1]

        result = self.run_cli(
            "status",
            "--run",
            processing_run_id,
            "--edition-part",
            edition_part_id,
            "--technique",
            "qizheng",
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
        lines = result.stdout.decode("utf-8").strip().splitlines()
        payload = json.loads(lines[0])
        self.assertEqual(
            set(payload.keys()),
            {"RunStatus", "StageProgress", "PendingQueue", "BlockingReasons"},
        )
        self.assertEqual(lines[-1], "ORCH STATUS OK")

    def test_cli_suspend_unknown_step_run_error_exit_1(self):
        result = self.run_cli(
            "suspend", "--step-run", "srun_" + "a" * 32, "--reason", "manual"
        )
        self.assertEqual(result.returncode, 1, result.stderr.decode("utf-8"))
        self.assertTrue(self.last_line(result).startswith("ORCH ERROR "))

    def test_cli_writer_locked_exit_3(self):
        service = LedgerService(self.root)
        self.addCleanup(service.close)
        result = self.run_cli(
            "start",
            "--edition-part",
            ids.new_id("artifact_id"),
            "--technique",
            "qizheng",
        )
        self.assertEqual(result.returncode, 3, result.stderr.decode("utf-8"))
        self.assertEqual(self.last_line(result), "ORCH LOCKED")

    def test_cli_advance_prints_gate_lines(self):
        edition_part_id = ids.new_id("artifact_id")
        started = self.run_cli(
            "start", "--edition-part", edition_part_id, "--technique", "qizheng"
        )
        processing_run_id = self.last_line(started).split()[-1]

        result = self.run_cli(
            "advance",
            "--run",
            processing_run_id,
            "--edition-part",
            edition_part_id,
            "--technique",
            "qizheng",
        )
        stdout = result.stdout.decode("utf-8")
        self.assertIn("ORCH GATE m1 blocked", stdout)

        import sqlite3

        connection = sqlite3.connect(
            "file:%s?mode=ro" % (self.root / "ledger.sqlite"), uri=True
        )
        try:
            revisions = connection.execute(
                "SELECT COUNT(*) FROM artifact_revisions"
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(revisions, 0)


if __name__ == "__main__":
    unittest.main()
