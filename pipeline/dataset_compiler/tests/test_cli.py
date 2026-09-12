"""ACT impl-04/06：CLI（python -m pipeline.dataset_compiler）退出码测试。"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline.dataset_compiler.tests._ledger_helpers import (
    REPO_ROOT,
    assets_available,
    prepare_m3,
    prepare_m8_ready,
)
from pipeline.dataset_compiler.tests._ledger_helpers import FIXTURE  # noqa: F401
from pipeline.ledger.service import LedgerService

_FIXTURE_EDITION_PART = "art_000000000000000000000000000000e1"


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m8-cli-")
        self.addCleanup(shutil.rmtree, self._tmp, True)

    def _seed(self, mode):
        """在临时 Ledger 上按 mode 准备并返回 (root, edition_part_id)。"""
        root = Path(self._tmp) / "ledger"
        service = LedgerService(root)
        try:
            if mode == "m8":
                prepared = prepare_m8_ready(service)
            elif mode == "m3":
                prepared = prepare_m3(service)
            else:
                prepared = {"edition_part_id": _FIXTURE_EDITION_PART}
            return root, prepared["edition_part_id"]
        finally:
            service.close()

    def _run(self, root, edition_part_id, level, min_app_version=None):
        command = [
            sys.executable,
            "-m",
            "pipeline.dataset_compiler",
            "--root",
            str(root),
            "--edition-part",
            edition_part_id,
            "--level",
            level,
        ]
        if min_app_version is not None:
            command += ["--min-app-version", min_app_version]
        return subprocess.run(
            command, capture_output=True, text=True, cwd=str(REPO_ROOT)
        )

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_cli_success_exit_0(self):
        root, edition_part_id = self._seed("m8")
        proc = self._run(root, edition_part_id, "INTERNAL_DEMO")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        last = proc.stdout.strip().splitlines()[-1]
        self.assertTrue(last.startswith("M8 OK"))
        self.assertIn("packs=2", last)

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_cli_public_release_exit_1(self):
        root, edition_part_id = self._seed("m8")
        proc = self._run(root, edition_part_id, "PUBLIC_RELEASE")
        self.assertEqual(proc.returncode, 1, msg=proc.stderr)
        last = proc.stdout.strip().splitlines()[-1]
        self.assertTrue(last.startswith("M8 FAILED"))
        self.assertTrue(last.endswith(" admission"))

    def test_cli_assets_unregistered_exit_2(self):
        root, edition_part_id = self._seed("m3")
        proc = self._run(root, edition_part_id, "INTERNAL_DEMO")
        self.assertEqual(proc.returncode, 2, msg=proc.stderr)
        self.assertTrue(
            proc.stdout.strip().splitlines()[-1].startswith("M8 REFUSED")
        )

    def test_cli_illegal_level_exit_2(self):
        root, edition_part_id = self._seed("none")
        proc = self._run(root, edition_part_id, "internal_demo")
        self.assertEqual(proc.returncode, 2, msg=proc.stderr)
        self.assertTrue(
            proc.stdout.strip().splitlines()[-1].startswith("M8 REFUSED")
        )
        service = LedgerService(root)
        try:
            runs = service.store.conn.execute(
                "SELECT COUNT(*) FROM processing_runs"
            ).fetchone()[0]
            steps = service.store.conn.execute(
                "SELECT COUNT(*) FROM step_runs"
            ).fetchone()[0]
        finally:
            service.close()
        self.assertEqual(runs, 0)
        self.assertEqual(steps, 0)


if __name__ == "__main__":
    unittest.main()
