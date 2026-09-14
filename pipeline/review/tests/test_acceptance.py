import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from pipeline.ledger.service import LedgerService
from pipeline.review import acceptance

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
DATA_DIR = ROOT / "pipeline" / "review" / "testing" / "data"
SHELL = ROOT / "openspec" / "acceptance" / "m6-data-fields.sh"


def _run_main(argv):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = acceptance.main(argv)
    return code, stream.getvalue()


class TestAcceptance(unittest.TestCase):
    def test_fixture_yields_eleven_pass_three_blocked_exit_2(self):
        code, out = _run_main(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(code, 2)
        lines = out.splitlines()
        self.assertEqual(len([l for l in lines if l.startswith("PASS ")]), 11)
        self.assertEqual(len([l for l in lines if l.startswith("BLOCKED ")]), 3)
        self.assertEqual(lines[-1], "SUMMARY pass=11 fail=0 blocked=3")

    def test_blocked_lines_exact_text(self):
        _code, out = _run_main(["--fixture", str(FIXTURE_DIR)])
        self.assertIn("BLOCKED snapshot_projection 前置缺失: M7 创世汇编", out)
        self.assertIn(
            "BLOCKED legacy_workbench_seed 前置缺失: M6 Review Workbench；"
            "pattern_knowledge_workbench 旧数据体未迁入（准入判定见 run_all 20.7）",
            out,
        )
        self.assertIn(
            "BLOCKED upstream_real 前置缺失: M4 Knowledge Extraction；"
            "M5 仍 scope=corpus_only，candidate 级校验未实现；本次为非生产合成 M4 输入与合成决定",
            out,
        )

    def test_expected_review_tampered_fails(self):
        tmp = tempfile.mkdtemp(prefix="m6-acceptance-expected-")
        self.addCleanup(shutil.rmtree, tmp, True)
        expected = yaml.safe_load((DATA_DIR / "expected_review.yaml").read_text(encoding="utf-8"))
        expected["rework"]["invalidated_count"] = expected["rework"]["invalidated_count"] + 1
        tampered = Path(tmp) / "expected_review.yaml"
        tampered.write_text(yaml.safe_dump(expected, allow_unicode=True), encoding="utf-8")

        code, out = _run_main(
            ["--fixture", str(FIXTURE_DIR), "--expected", str(tampered)]
        )
        self.assertEqual(code, 1)
        self.assertIn("FAIL precise_invalidation", out)

    def test_deleted_decision_event_fails(self):
        original = acceptance._step.record_decision
        counter = {"calls": 0}

        def wrapper(service, step_run_id, token, **kwargs):
            counter["calls"] += 1
            if counter["calls"] != 1:
                return original(service, step_run_id, token, **kwargs)
            original_write_checkpoint = service.write_checkpoint
            service.write_checkpoint = lambda *a, **k: None
            try:
                return original(service, step_run_id, token, **kwargs)
            finally:
                service.write_checkpoint = original_write_checkpoint

        with mock.patch.object(acceptance._step, "record_decision", side_effect=wrapper):
            code, out = _run_main(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(code, 1)
        self.assertIn("FAIL checkpoint_per_decision", out)

    def test_cross_module_status_change_detected(self):
        original = acceptance._prepare

        def wrapper(fixture_dir, expected_path):
            tmp, service, world = original(fixture_dir, expected_path)
            row = service.store.conn.execute(
                "SELECT r.artifact_revision_id FROM artifact_revisions r "
                "JOIN step_runs s ON s.step_run_id = r.step_run_id "
                "WHERE s.stage='m4' AND r.status='sealed' LIMIT 1"
            ).fetchone()
            service.invalidate_revision(row[0], "acceptance-test")
            return tmp, service, world

        with mock.patch.object(acceptance, "_prepare", side_effect=wrapper):
            code, out = _run_main(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(code, 1)
        self.assertIn("FAIL no_cross_module_status_change", out)

    def test_prepare_failure_exits_1(self):
        with mock.patch.object(
            acceptance, "seed_upstream", side_effect=RuntimeError("boom")
        ):
            code, out = _run_main(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(code, 1)
        self.assertTrue(
            out.splitlines()[0].startswith(
                "FAIL m6_acceptance 宿主准备失败: RuntimeError"
            ),
            out.splitlines()[0],
        )

    def test_missing_fixture_exit_3(self):
        code, out = _run_main(["--fixture", "/nonexistent-fixture-dir-xyz"])
        self.assertEqual(code, 3)
        self.assertIn("BLOCKED m6_acceptance 前置缺失", out)

    def _run_shell(self, fixture_dir=None):
        env = os.environ.copy()
        env["LC_ALL"] = "en_US.UTF-8"
        env["PYTHONPATH"] = str(ROOT)
        if fixture_dir is not None:
            env["FIXTURE_DIR"] = str(fixture_dir)
        return subprocess.run(
            ["bash", str(SHELL)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
        )

    def test_shell_exit_2_on_fixture(self):
        res = self._run_shell()
        self.assertEqual(res.returncode, 2, res.stderr + res.stdout)
        lines = [l for l in res.stdout.splitlines() if l.strip()]
        self.assertEqual(lines[-1], "SUMMARY pass=11 fail=0 blocked=3")

    def test_shell_never_trusts_copy_verify(self):
        tmp = tempfile.mkdtemp(prefix="m6-acceptance-copy-")
        self.addCleanup(shutil.rmtree, tmp, True)
        copy_dir = Path(tmp) / "mini_ed01"
        shutil.copytree(FIXTURE_DIR, copy_dir)
        spans_path = copy_dir / "spans.yaml"
        spans_doc = yaml.safe_load(spans_path.read_text(encoding="utf-8"))
        spans_doc["spans"] = spans_doc["spans"][:-1]
        spans_doc["span_count"] = len(spans_doc["spans"])
        spans_path.write_text(
            yaml.safe_dump(spans_doc, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        fake_verify = copy_dir / "verify.sh"
        fake_verify.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        fake_verify.chmod(0o755)

        res = self._run_shell(fixture_dir=copy_dir)
        self.assertEqual(res.returncode, 1, res.stderr + res.stdout)
        first = res.stdout.splitlines()[0]
        self.assertTrue(first.startswith("FAIL fixture_host"), first)


if __name__ == "__main__":
    unittest.main()
