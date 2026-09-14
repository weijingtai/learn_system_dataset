"""M7 创世验收测试（act/g0-05，spec §19.0）。"""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]


class TestAcceptance(unittest.TestCase):
    def test_genesis_acceptance_summary_and_exit_2(self):
        from pipeline.assembly import acceptance

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = acceptance.main([])
        out = buf.getvalue()
        self.assertEqual(code, 2)
        self.assertIn("SUMMARY pass=10 fail=0 blocked=6", out)
        self.assertEqual(out.count("PASS "), 10)
        self.assertEqual(out.count("BLOCKED "), 6)
        self.assertEqual(out.count("FAIL "), 0)

    def test_blocked_lines_exact_text(self):
        from pipeline.assembly import acceptance

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = acceptance.main([])
        out = buf.getvalue()
        expected_blocked = [
            ("incremental_multi_edition", "多 Edition 增量对勘未实现（§15:655）"),
            ("edition_collation", "Alignment/VariantReading/Addition/Omission 未实现"),
            ("identity_delta", "跨版本身份迁移未实现（§6.3、§16:732）"),
            ("rework_replacement", "M6 返工替换未实现（D-14）"),
            (
                "upstream_m6_real",
                "「消费真实 M6 产出」的判定在 impl-06 实现并验收前恒 BLOCKED（第 66 条）；本切片输入为合成 ReviewedEditionPackage，不伪造",
            ),
            ("run_all_20_5", "§20.5 未接线（Q29 采纳 C）"),
        ]
        for name, desc in expected_blocked:
            self.assertIn(f"BLOCKED {name} {desc}", out)

    def test_acceptance_does_not_import_genesis_for_judgement(self):
        import ast

        acc_path = ROOT / "pipeline" / "assembly" / "acceptance.py"
        tree = ast.parse(acc_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotEqual(alias.name.split(".")[-1], "genesis")
            elif isinstance(node, ast.ImportFrom):
                mod = (node.module or "").split(".")[-1]
                self.assertNotEqual(mod, "genesis")

    def test_golden_mismatch_fails(self):
        from pipeline.assembly import acceptance

        tmp_dir = tempfile.mkdtemp(prefix="test_golden_")
        self.addCleanup(shutil.rmtree, tmp_dir, True)
        fake_gold = Path(tmp_dir) / "genesis_expected_knowledge.json"
        fake_gold.write_text('{"mismatched": true}', encoding="utf-8")
        buf = io.StringIO()
        with mock.patch.object(acceptance, "GOLDEN_KNOWLEDGE_PATH", fake_gold):
            with contextlib.redirect_stdout(buf):
                code = acceptance.main([])
        out = buf.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("FAIL genesis_snapshot", out)

    def test_prepare_failure_exits_1(self):
        from pipeline.assembly import acceptance

        buf = io.StringIO()
        with mock.patch(
            "pipeline.assembly.fixture_seed.seed_genesis_package",
            side_effect=RuntimeError("simulated prep error"),
        ):
            with contextlib.redirect_stdout(buf):
                code = acceptance.main([])
        out = buf.getvalue()
        self.assertEqual(code, 1)
        self.assertTrue(
            out.splitlines()[0].startswith(
                "FAIL m7_acceptance 宿主准备失败: RuntimeError"
            )
        )

    def test_shell_returns_2(self):
        shell_script = ROOT / "openspec" / "acceptance" / "m7-assembler.sh"
        proc = subprocess.run(
            ["bash", str(shell_script)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode, 2, f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
        last_line = proc.stdout.strip().splitlines()[-1]
        self.assertEqual(last_line, "SUMMARY pass=10 fail=0 blocked=6")

    def test_shell_missing_env_exit_3(self):
        tmp_dir = tempfile.mkdtemp(prefix="test_missing_env_")
        self.addCleanup(shutil.rmtree, tmp_dir, True)
        fake_repo = Path(tmp_dir) / "repo"
        fake_acc_dir = fake_repo / "openspec" / "acceptance"
        fake_acc_dir.mkdir(parents=True)
        shell_source = (
            ROOT / "openspec" / "acceptance" / "m7-assembler.sh"
        ).read_text(encoding="utf-8")
        fake_script = fake_acc_dir / "m7-assembler.sh"
        fake_script.write_text(shell_source, encoding="utf-8")
        fake_script.chmod(0o755)
        proc = subprocess.run(
            ["bash", str(fake_script)],
            cwd=str(fake_repo),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 3)
        self.assertIn("SUMMARY pass=0 fail=0 blocked=1", proc.stdout)

    def test_shell_never_trusts_copy_verify(self):
        tmp_dir = tempfile.mkdtemp(prefix="test_copy_verify_")
        self.addCleanup(shutil.rmtree, tmp_dir, True)
        fake_copy = Path(tmp_dir) / "fake_fixture"
        fake_copy.mkdir()
        fake_verify = fake_copy / "verify.sh"
        fake_verify.write_text("echo FAKE_VERIFY_RAN\nexit 1\n", encoding="utf-8")
        fake_verify.chmod(0o755)
        shell_script = ROOT / "openspec" / "acceptance" / "m7-assembler.sh"
        proc = subprocess.run(
            ["bash", str(shell_script)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=dict(os.environ, FIXTURE_DIR=str(fake_copy)),
        )
        self.assertNotIn("FAKE_VERIFY_RAN", proc.stdout)
        self.assertEqual(proc.returncode, 2)

    def test_upstream_m6_real_blocked_until_impl06_accepted(self):
        from pipeline.assembly import acceptance

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = acceptance.main([])
        out = buf.getvalue()
        for line in out.splitlines():
            if line.startswith("BLOCKED upstream_m6_real"):
                self.assertIn("impl-06 实现并验收前", line)
                break
        else:
            self.fail("BLOCKED upstream_m6_real line not found")

    def test_synthetic_decisions_not_counted_expert_verified(self):
        from pipeline.assembly.tests.test_genesis_ledger import (
            load_fixture_data,
        )

        doc = load_fixture_data()
        decisions = doc["reviewed_edition"]["decisions"]
        self.assertGreater(len(decisions), 0)
        for d in decisions:
            self.assertTrue(
                d.get("synthetic_fixture"), "synthetic_fixture must be true"
            )
        from pipeline.assembly import acceptance

        tmp, service, world = acceptance._prepare(Path(tempfile.mkdtemp()))
        try:
            snap_doc = world["snapshot_doc"]
            for p in snap_doc.get("patterns", []):
                self.assertNotIn("content_status", p)
        finally:
            service.close()
            shutil.rmtree(tmp, True)


if __name__ == "__main__":
    unittest.main()
