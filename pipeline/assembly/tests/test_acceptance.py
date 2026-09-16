"""M7 创世验收测试（act/g0-05、g0-06，spec §19.0）。"""

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
        self.assertIn("SUMMARY pass=11 fail=0 blocked=5", out)
        self.assertEqual(out.count("PASS "), 11)
        self.assertEqual(out.count("BLOCKED "), 5)
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
        self.assertEqual(last_line, "SUMMARY pass=11 fail=0 blocked=5")

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
        """upstream_m6_real 已转为 PASS，验证其不在 BLOCKED 列表中。"""
        from pipeline.assembly import acceptance

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = acceptance.main([])
        out = buf.getvalue()
        for line in out.splitlines():
            if line.startswith("BLOCKED upstream_m6_real"):
                self.fail("upstream_m6_real should not be BLOCKED")

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

    def test_upstream_m6_real_passes_and_snapshot_has_patterns(self):
        from pipeline.assembly import acceptance

        tmp, service, world = acceptance._prepare_with_real_m6()
        try:
            snap_doc = world["snapshot_doc"]
            self.assertIn("patterns", snap_doc)
            self.assertIn("assertions", snap_doc)
            self.assertIn("technique_id", snap_doc)
        finally:
            service.close()
            shutil.rmtree(tmp, True)

    def test_upstream_m6_real_independent_of_run_m7_gate(self):
        import ast as _ast

        acc_path = ROOT / "pipeline" / "assembly" / "acceptance.py"
        tree = _ast.parse(acc_path.read_text(encoding="utf-8"))
        func = None
        for node in _ast.walk(tree):
            if isinstance(node, _ast.FunctionDef) and node.name == "check_upstream_m6_real":
                func = node
                break
        self.assertIsNotNone(func, "check_upstream_m6_real not found")
        source = _ast.get_source_segment(
            acc_path.read_text(encoding="utf-8"), func
        )
        self.assertNotIn("run_m7", source.split("独立核对")[1] if "独立核对" in source else source)

    def test_upstream_m6_real_m6_package_immutable(self):
        from pipeline.assembly import acceptance

        tmp, service, world = acceptance._prepare_with_real_m6()
        try:
            before = world["real_m6_before"]
            after = world["real_m6_after"]
            self.assertEqual(before["status"], after["status"])
            self.assertEqual(before["sha256"], after["sha256"])
        finally:
            service.close()
            shutil.rmtree(tmp, True)

    def test_no_model_calls_counts_parse_failures(self):
        from pipeline.assembly import acceptance

        tmp_dir = Path(tempfile.mkdtemp(prefix="test_parse_fail_"))
        self.addCleanup(shutil.rmtree, tmp_dir, True)
        bad_file = tmp_dir / "bad_syntax.py"
        bad_file.write_text("def x(\n", encoding="utf-8")
        assembly_dir = acceptance.REPO_ROOT / "pipeline" / "assembly"
        errors = acceptance.check_no_model_calls(
            {"_scan_dir": assembly_dir, "_extra_files": [bad_file]}
        )
        parse_errors = [e for e in errors if "bad_syntax.py" in e]
        self.assertGreater(len(parse_errors), 0, "parse failure should be counted")

    def test_upstream_m6_real_synthetic_fixture_true(self):
        from pipeline.review.testing.upstream_stub import load_data as m6_load_data

        decisions_doc = m6_load_data("m6_decisions")
        self.assertTrue(
            decisions_doc.get("synthetic_fixture"),
            "m6_decisions must be marked synthetic_fixture: true",
        )

    def test_shell_summary_pass_11_fail_0_blocked_5(self):
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
        self.assertEqual(last_line, "SUMMARY pass=11 fail=0 blocked=5")

    def test_stub_candidate_set_conforms_to_m7_validate(self):
        """桩 seed 后 candidate_set 过 M7 validate_candidate_set，防漂移。"""
        import json
        import tempfile
        import shutil

        from pipeline.ledger.service import LedgerService
        from pipeline.review.testing.upstream_stub import seed_upstream
        from pipeline.assembly.model import validate_candidate_set

        fixture_dir = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
        tmp = Path(tempfile.mkdtemp(prefix="test_stub_conform_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        service = LedgerService(tmp / "ledger")
        self.addCleanup(service.close)
        seed = seed_upstream(service, fixture_dir)
        cset_rev = service.get_revision(seed["candidate_set_revision_id"])
        cset_doc = json.loads(service.objects.get(cset_rev["sha256"]).decode())
        validate_candidate_set(cset_doc)


if __name__ == "__main__":
    unittest.main()
