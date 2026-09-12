"""ACT 04：acceptance.py 九项判定 + m3-coverage.sh 验收。

用例名逐字对照 act/04.yaml tests 节。
"""

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
REPO_ROOT = Path(__file__).resolve().parents[3]
SHELL_SCRIPT = REPO_ROOT / "openspec" / "acceptance" / "m3-coverage.sh"


class TestAcceptanceUnit(unittest.TestCase):
    """acceptance.py 单元测试。"""

    def test_fixture_yields_eight_pass_one_blocked_exit_2(self):
        from pipeline.corpus_compiler.acceptance import main
        rc = main(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(rc, 2)

    def test_semantic_layer_line_is_blocked_with_exact_text(self):
        from pipeline.corpus_compiler.acceptance import main
        with patch("builtins.print") as mock_print:
            rc = main(["--fixture", str(FIXTURE_DIR)])
        blocked_lines = [
            call.args[0] for call in mock_print.call_args_list
            if call.args and call.args[0].startswith("BLOCKED semantic_layer")
        ]
        self.assertEqual(len(blocked_lines), 1)
        self.assertIn("前置缺失: M3 Corpus Compilation", blocked_lines[0])
        self.assertIn("SemanticSpan", blocked_lines[0])
        self.assertIn("未实现", blocked_lines[0])

    def test_golden_mismatch_fails(self):
        from pipeline.corpus_compiler.acceptance import main
        tmp = tempfile.mkdtemp(prefix="m3-acc-golden-")
        try:
            shutil.copytree(FIXTURE_DIR, Path(tmp) / "mini_ed01", dirs_exist_ok=True)
            tampered = Path(tmp) / "mini_ed01" / "spans.yaml"
            original = tampered.read_text(encoding="utf-8")
            tampered.write_text(original + "\n# tampered\n", encoding="utf-8")
            rc = main(["--fixture", str(Path(tmp) / "mini_ed01")])
            self.assertEqual(rc, 1)
        finally:
            shutil.rmtree(tmp, True)

    def test_dropped_span_makes_run_fail_and_exit_1(self):
        from pipeline.corpus_compiler import step as step_mod
        from pipeline.corpus_compiler.compiler import compile_structural
        from pipeline.ledger.fixture_ingest import ingest
        from pipeline.ledger.service import LedgerService

        tmp = tempfile.mkdtemp(prefix="m3-acc-drop-")
        try:
            svc = LedgerService(Path(tmp) / "ledger")
            summary = ingest(FIXTURE_DIR, svc, stages=("m1", "m2"))
            ep = summary["edition_part_id"]

            original_compile = step_mod.compile_structural
            def tampered_compile(**kwargs):
                result = original_compile(**kwargs)
                result["spans"] = result["spans"][:-1]
                result["spans_doc"]["spans"] = result["spans"]
                result["spans_doc"]["span_count"] = len(result["spans"])
                from pipeline.corpus_compiler.serialize import dump_yaml
                import hashlib
                result["spans_bytes"] = dump_yaml(result["spans_doc"])
                result["spans_sha256"] = hashlib.sha256(result["spans_bytes"]).hexdigest()
                return result
            step_mod.compile_structural = tampered_compile
            try:
                from pipeline.corpus_compiler.acceptance import main
                rc = main(["--fixture", str(FIXTURE_DIR)])
                self.assertEqual(rc, 1)
            finally:
                step_mod.compile_structural = original_compile
            svc.close()
        finally:
            shutil.rmtree(tmp, True)

    def test_prepare_failure_exits_1(self):
        from pipeline.corpus_compiler.acceptance import main
        with patch(
            "pipeline.corpus_compiler.acceptance.ingest",
            side_effect=RuntimeError("boom"),
        ):
            with patch("builtins.print") as mock_print:
                rc = main(["--fixture", str(FIXTURE_DIR)])
            self.assertEqual(rc, 1)
            first_line = mock_print.call_args_list[0].args[0]
            self.assertTrue(first_line.startswith("FAIL m3_acceptance 宿主准备失败: RuntimeError"))

    def test_missing_fixture_exit_3(self):
        from pipeline.corpus_compiler.acceptance import main
        rc = main(["--fixture", "/nonexistent/path/fixture"])
        self.assertEqual(rc, 1)


class TestShellScript(unittest.TestCase):
    """m3-coverage.sh 集成测试。"""

    def test_shell_exit_2_on_fixture(self):
        proc = subprocess.run(
            ["bash", str(SHELL_SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env={**os.environ, "LC_ALL": "en_US.UTF-8"},
        )
        self.assertEqual(proc.returncode, 2)
        lines = proc.stdout.strip().splitlines()
        self.assertTrue(lines[-1].startswith("SUMMARY pass=8 fail=0 blocked=1"))

    def test_shell_never_trusts_copy_verify(self):
        tmp = tempfile.mkdtemp(prefix="m3-shell-trust-")
        try:
            copy_dir = Path(tmp) / "mini_ed01"
            shutil.copytree(FIXTURE_DIR, copy_dir, dirs_exist_ok=True)
            # 删一条 span
            spans_path = copy_dir / "spans.yaml"
            original = spans_path.read_text(encoding="utf-8")
            spans_doc = __import__("yaml").safe_load(original)
            spans_doc["spans"] = spans_doc["spans"][:-1]
            spans_path.write_text(
                __import__("yaml").safe_dump(spans_doc, allow_unicode=True, default_flow_style=False),
                encoding="utf-8",
            )
            # 替换 verify.sh
            verify_path = copy_dir / "verify.sh"
            verify_path.write_text("#!/usr/bin/env bash\necho FIXTURE OK; exit 0\n", encoding="utf-8")
            verify_path.chmod(0o755)
            proc = subprocess.run(
                ["bash", str(SHELL_SCRIPT)],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
                env={**os.environ, "LC_ALL": "en_US.UTF-8", "FIXTURE_DIR": str(copy_dir)},
            )
            self.assertEqual(proc.returncode, 1)
            self.assertTrue(proc.stdout.strip().splitlines()[0].startswith("FAIL fixture_host"))
        finally:
            shutil.rmtree(tmp, True)


if __name__ == "__main__":
    unittest.main()
