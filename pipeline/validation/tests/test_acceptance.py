"""ACT 06 单元测试：m5-evidence-gate 十四项判定与脚本。

用例名与 act/06.yaml 的 tests 清单逐字一致。
"""

import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from pipeline.validation import acceptance

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
SCRIPT = REPO / "openspec" / "acceptance" / "m5-evidence-gate.sh"


class AcceptanceMainTest(unittest.TestCase):
    def _run(self, argv):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = acceptance.main(argv)
        return code, buffer.getvalue()

    def test_fixture_yields_nine_pass_five_blocked_exit_2(self):
        code, output = self._run(["--fixture", str(FIXTURE)])
        lines = [line for line in output.splitlines() if line.strip()]
        passes = [line for line in lines if line.startswith("PASS ")]
        blocked = [line for line in lines if line.startswith("BLOCKED ")]
        self.assertEqual(code, 2)
        self.assertEqual(len(passes), 9)
        self.assertEqual(len(blocked), 5)
        self.assertEqual(lines[-1], "SUMMARY pass=9 fail=0 blocked=5")

    def test_blocked_lines_use_section19_names(self):
        _code, output = self._run(["--fixture", str(FIXTURE)])
        blocked = [line for line in output.splitlines() if line.startswith("BLOCKED ")]
        joined = "\n".join(blocked)
        self.assertIn("M4 Knowledge Extraction", joined)
        self.assertIn("M3 Corpus Compilation", joined)

    def test_prepare_failure_exits_1(self):
        with mock.patch(
            "pipeline.validation.acceptance.fixture_ingest.ingest",
            side_effect=RuntimeError("boom"),
        ):
            code, output = self._run(["--fixture", str(FIXTURE)])
        self.assertEqual(code, 1)
        self.assertTrue(
            output.splitlines()[0].startswith(
                "FAIL m5_acceptance 宿主准备失败: RuntimeError"
            ),
            output.splitlines()[0],
        )

    def test_missing_fixture_exit_3(self):
        code, _output = self._run(["--fixture", "/nonexistent/m5-fixture"])
        self.assertEqual(code, 3)


class AcceptanceChecksTest(unittest.TestCase):
    def test_gate_and_levels_passed_failed_failed(self):
        with acceptance.harness(FIXTURE) as state:
            gate_results = state["gate_results"]
        self.assertEqual(
            gate_results["level_verdicts"],
            {"INTERNAL_DEMO": "passed", "DEV_SEARCH": "failed", "PUBLIC_RELEASE": "failed"},
        )
        self.assertTrue(gate_results["gate"]["passed"])

    def test_adversarial_offset_mismatch_hits_g3(self):
        checks = acceptance.adversarial_checks(FIXTURE, "offset_mismatch")
        self.assertIn("offset_mismatch", checks)

    def test_adversarial_page_hash_mismatch_hits_g1(self):
        checks = acceptance.adversarial_checks(FIXTURE, "page_hash_mismatch")
        self.assertIn("page_image_hash_mismatch", checks)

    def test_adversarial_dropped_last_span_hits_g2(self):
        checks = acceptance.adversarial_checks(FIXTURE, "dropped_last_span")
        self.assertTrue(
            {"coverage_gap", "span_boundary_mismatch", "count_mismatch"} & checks,
            checks,
        )

    def test_adversarial_offset_level_for_public_hits_g3(self):
        checks = acceptance.adversarial_checks(FIXTURE, "offset_level")
        self.assertIn("evidence_level_insufficient", checks)

    def test_adversarial_bypass_requires_all_four(self):
        hits = {
            name: acceptance.adversarial_checks(FIXTURE, name)
            for name in acceptance.ADVERSARIAL
        }
        expected = {
            "offset_mismatch": "offset_mismatch",
            "page_hash_mismatch": "page_image_hash_mismatch",
            "dropped_last_span": "count_mismatch",
            "offset_level": "evidence_level_insufficient",
        }
        for name, check in expected.items():
            self.assertIn(check, hits[name], name)

    def test_fail_closed_tamper_marks_thirteen_skipped(self):
        result = acceptance.fail_closed_probe(FIXTURE)
        self.assertEqual(result["skipped"], 13)
        self.assertEqual(
            result["level_verdicts"],
            {"INTERNAL_DEMO": "failed", "DEV_SEARCH": "failed", "PUBLIC_RELEASE": "failed"},
        )
        self.assertTrue(result["step_run_succeeded"])
        self.assertTrue(result["package_sealed"])
        self.assertFalse(result["validation_passed"])
        self.assertFalse(result["downstream_consumable"])


class ShellScriptTest(unittest.TestCase):
    def test_shell_exit_2_on_fixture(self):
        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=str(REPO), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        output = proc.stdout.decode("utf-8", "replace")
        self.assertEqual(proc.returncode, 2, output)
        self.assertEqual(output.splitlines()[-1], "SUMMARY pass=9 fail=0 blocked=5")

    def test_shell_never_trusts_copy_verify(self):
        copy_dir = Path(tempfile.mkdtemp(prefix="m5-copy-")) / "mini_ed01"
        self.addCleanup(shutil.rmtree, str(copy_dir.parent), True)
        shutil.copytree(FIXTURE, copy_dir)
        # 删一条 span，并把副本自带 verify.sh 换成永远成功的假脚本
        import yaml

        spans = yaml.safe_load((copy_dir / "spans.yaml").read_text(encoding="utf-8"))
        spans["spans"] = spans["spans"][:-1]
        (copy_dir / "spans.yaml").write_text(
            yaml.dump(spans, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        (copy_dir / "verify.sh").write_text("#!/usr/bin/env bash\necho FIXTURE OK\nexit 0\n")
        import os

        os.chmod(copy_dir / "verify.sh", 0o755)

        env = dict(os.environ)
        env["FIXTURE_DIR"] = str(copy_dir)
        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=str(REPO), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        output = proc.stdout.decode("utf-8", "replace")
        self.assertEqual(proc.returncode, 1, output)
        self.assertTrue(output.splitlines()[0].startswith("FAIL fixture_host"), output)


if __name__ == "__main__":
    unittest.main()
