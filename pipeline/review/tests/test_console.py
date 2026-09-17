import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.ledger.service import LedgerService
from pipeline.review.testing.upstream_stub import seed_upstream, seed_offset_upstream

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
DATA_DIR = ROOT / "pipeline" / "review" / "testing" / "data"


class TestConsole(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m6-console-test-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.ledger_dir = Path(self._tmp) / "ledger"
        service = LedgerService(self.ledger_dir)
        try:
            self.seed_result = seed_upstream(service, FIXTURE_DIR)
            self.edition_part_id = self.seed_result["edition_part_id"]
        finally:
            service.close()

    def _run_cli(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        cmd = [
            sys.executable,
            "-m",
            "pipeline.review",
            "--root",
            str(self.ledger_dir),
            *args,
        ]
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
        )

    def _open_review(self):
        res = self._run_cli("open", "--edition-part", self.edition_part_id)
        self.assertEqual(res.returncode, 0, f"open failed: {res.stderr}\n{res.stdout}")
        # Parse M6 AWAITING <step_run_id> token=<resume_token> pending=<n>
        lines = [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]
        last = lines[-1]
        parts = last.split()
        self.assertEqual(parts[0], "M6")
        self.assertEqual(parts[1], "AWAITING")
        step_run_id = parts[2]
        token = parts[3].split("=")[1]
        return step_run_id, token, res.stdout

    def test_help_exit_0(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        res = subprocess.run(
            [sys.executable, "-m", "pipeline.review", "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("open", res.stdout)
        self.assertIn("close", res.stdout)

    def test_open_prints_queue_and_awaiting_line(self):
        step_run_id, token, stdout = self._open_review()
        self.assertTrue(step_run_id.startswith("srun_"))
        self.assertTrue(token)
        lines = [l for l in stdout.strip().split("\n") if l.strip()]
        self.assertTrue(len(lines) >= 6)  # 5 queue items + 1 awaiting line
        for item_line in lines[:-1]:
            self.assertIn("pending", item_line)
            cols = item_line.split("\t")
            self.assertEqual(len(cols), 3)
            self.assertEqual(cols[2], "pending")
        self.assertIn("M6 AWAITING", lines[-1])

    def test_open_without_upstream_refused_exit_2(self):
        res = self._run_cli("open", "--edition-part", "art_nonexistent00000000000000000")
        self.assertEqual(res.returncode, 2)
        out = res.stdout + res.stderr
        self.assertIn("M6 REFUSED", out)

    def test_show_read_only_row_counts_unchanged(self):
        step_run_id, token, _ = self._open_review()
        service = LedgerService(self.ledger_dir)
        try:
            rev_count_before = service.store.conn.execute("SELECT count(*) FROM artifact_revisions").fetchone()[0]
            he_count_before = service.store.conn.execute("SELECT count(*) FROM human_events").fetchone()[0]
        finally:
            service.close()

        res = self._run_cli(
            "show",
            "--step-run",
            step_run_id,
            "--item",
            "as_qizheng_000001#review_source_fidelity",
        )
        self.assertEqual(res.returncode, 0, f"show failed: {res.stderr}\n{res.stdout}")

        service = LedgerService(self.ledger_dir)
        try:
            rev_count_after = service.store.conn.execute("SELECT count(*) FROM artifact_revisions").fetchone()[0]
            he_count_after = service.store.conn.execute("SELECT count(*) FROM human_events").fetchone()[0]
        finally:
            service.close()

        self.assertEqual(rev_count_before, rev_count_after)
        self.assertEqual(he_count_before, he_count_after)

    def test_show_prints_evidence_anchor_fields(self):
        step_run_id, token, _ = self._open_review()
        res = self._run_cli(
            "show",
            "--step-run",
            step_run_id,
            "--item",
            "as_qizheng_000001#review_source_fidelity",
        )
        self.assertEqual(res.returncode, 0)
        out = res.stdout
        self.assertIn("TARGET as_qizheng_000001", out)
        self.assertIn("EVIDENCE", out)
        self.assertIn("page=", out)
        self.assertIn("line=", out)
        self.assertIn("bbox=", out)
        self.assertIn("image_sha256=", out)
        self.assertIn("quote=", out)

    def test_decide_batch_full_then_close_ok(self):
        step_run_id, token, _ = self._open_review()
        decisions_file = DATA_DIR / "m6_decisions.yaml"
        res_batch = self._run_cli(
            "decide-batch",
            "--step-run",
            step_run_id,
            "--resume-token",
            token,
            "--from-file",
            str(decisions_file),
        )
        self.assertEqual(res_batch.returncode, 0, f"decide-batch failed: {res_batch.stderr}\n{res_batch.stdout}")
        lines = [l for l in res_batch.stdout.strip().split("\n") if l.strip()]
        self.assertEqual(len(lines), 5)
        for l in lines:
            self.assertIn("M6 DECIDED", l)

        res_close = self._run_cli(
            "close",
            "--step-run",
            step_run_id,
            "--resume-token",
            token,
        )
        self.assertEqual(res_close.returncode, 0, f"close failed: {res_close.stderr}\n{res_close.stdout}")
        self.assertIn("M6 OK", res_close.stdout)
        self.assertIn("approved=3 rejected=1 decisions=5", res_close.stdout)

    def test_decide_batch_stops_on_third_invalid_keeps_first_two(self):
        step_run_id, token, _ = self._open_review()
        raw_decisions = yaml.safe_load((DATA_DIR / "m6_decisions.yaml").read_text(encoding="utf-8"))
        items = list(raw_decisions["decisions"])
        items[2]["verdict"] = "invalid_verdict_xxx"

        bad_yaml_file = Path(self._tmp) / "bad_decisions.yaml"
        bad_yaml_file.write_text(yaml.safe_dump({"decisions": items}), encoding="utf-8")

        res_batch = self._run_cli(
            "decide-batch",
            "--step-run",
            step_run_id,
            "--resume-token",
            token,
            "--from-file",
            str(bad_yaml_file),
        )
        self.assertEqual(res_batch.returncode, 2)
        out = res_batch.stdout + res_batch.stderr
        self.assertIn("M6 REFUSED", out)

        service = LedgerService(self.ledger_dir)
        try:
            he_rows = service.store.conn.execute(
                "SELECT count(*) FROM human_events WHERE step_run_id=?",
                (step_run_id,),
            ).fetchone()[0]
        finally:
            service.close()

        self.assertEqual(he_rows, 2)

    def test_close_with_pending_exit_2(self):
        step_run_id, token, _ = self._open_review()
        res_close = self._run_cli(
            "close",
            "--step-run",
            step_run_id,
            "--resume-token",
            token,
        )
        self.assertEqual(res_close.returncode, 2)
        out = res_close.stdout + res_close.stderr
        self.assertIn("M6 REFUSED", out)

    def test_wrong_token_exit_2(self):
        step_run_id, token, _ = self._open_review()
        res_close = self._run_cli(
            "close",
            "--step-run",
            step_run_id,
            "--resume-token",
            "invalid_resume_token_value",
        )
        self.assertEqual(res_close.returncode, 2)
        out = res_close.stdout + res_close.stderr
        self.assertIn("M6 REFUSED", out)

    def test_show_prints_offset_level_evidence_anchor_fields(self):
        offset_tmp = tempfile.mkdtemp(prefix="m6-offset-console-test-")
        self.addCleanup(shutil.rmtree, offset_tmp, True)
        ledger_dir = Path(offset_tmp) / "ledger"
        service = LedgerService(ledger_dir)
        try:
            seed_res = seed_offset_upstream(service)
            ep_id = seed_res["edition_part_id"]
        finally:
            service.close()

        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        cmd_open = [
            sys.executable,
            "-m",
            "pipeline.review",
            "--root",
            str(ledger_dir),
            "open",
            "--edition-part",
            ep_id,
        ]
        res_open = subprocess.run(cmd_open, capture_output=True, text=True, env=env, cwd=str(ROOT))
        self.assertEqual(res_open.returncode, 0, res_open.stderr)
        lines = [line.strip() for line in res_open.stdout.strip().split("\n") if line.strip()]
        step_run_id = lines[-1].split()[2]

        cmd_show = [
            sys.executable,
            "-m",
            "pipeline.review",
            "--root",
            str(ledger_dir),
            "show",
            "--step-run",
            step_run_id,
            "--item",
            "as_qizheng_000001#review_source_fidelity",
        ]
        res_show = subprocess.run(cmd_show, capture_output=True, text=True, env=env, cwd=str(ROOT))
        self.assertEqual(res_show.returncode, 0, res_show.stderr)
        out = res_show.stdout
        self.assertIn("TARGET as_qizheng_000001", out)
        self.assertIn("EVIDENCE ss_qianyuan_ed01_o0008663", out)
        self.assertIn("raw_text_revision_id=", out)
        self.assertIn("raw_start=8663", out)
        self.assertIn("raw_end=8673", out)
        self.assertIn("start_offset=8663", out)
        self.assertIn("end_offset=8673", out)
        self.assertIn("quote=天官者，天干之官", out)

    def test_glyphbox_console_output_format_invariance(self):
        # 既有 glyphbox 路线控制台输出逐字段不破坏
        step_run_id, token, _ = self._open_review()
        res = self._run_cli(
            "show",
            "--step-run",
            step_run_id,
            "--item",
            "as_qizheng_000001#review_source_fidelity",
        )
        self.assertEqual(res.returncode, 0)
        lines = [l for l in res.stdout.splitlines() if l.startswith("EVIDENCE ")]
        self.assertTrue(len(lines) >= 1)
        ev_line = lines[0]
        self.assertIn("page=", ev_line)
        self.assertIn("line=", ev_line)
        self.assertIn("bbox=", ev_line)
        self.assertIn("image_sha256=", ev_line)
        self.assertIn("quote=", ev_line)
        self.assertNotIn("raw_text_revision_id=", ev_line)


if __name__ == "__main__":
    unittest.main()
