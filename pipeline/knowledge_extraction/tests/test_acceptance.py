"""ACT 07 m4-stage-gate 验收（acceptance）与 shell 包装的单测（先红后绿）。"""

import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from pipeline.knowledge_extraction import acceptance

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
GOLD_DIR = FIXTURE_DIR / "m4"
DATA = Path(__file__).resolve().parent / "data" / "appendix_a"
SHELL = ROOT / "openspec" / "acceptance" / "m4-stage-gate.sh"

BLOCKED_EXPECTED = {
    "cross_model_extraction": "前置缺失: M4 Knowledge Extraction；生产模型 A/B 独立抽取与复核模型 C（§12.2）未接入 Model Adapter，本批为无模型薄接入",
    "semantic_span_input": "前置缺失: M3 Corpus Compilation；SemanticSpan 未实现，M4 以 StructuralSpan 薄接入（span_layer=structural）",
    "term_layering_scan": "前置缺失: Contract Registry；schemas/shared/homographs 与 qizheng 术语表不存在，L1/L2/L3 自动判层未实现（本批只校验提交件自带 concept_ref）",
}


def run_cli(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = acceptance.main(argv)
    return code, buf.getvalue()


class AcceptanceTests(unittest.TestCase):
    def test_fixture_yields_13_pass_3_blocked_exit_2(self):
        code, output = run_cli(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(code, 2)
        self.assertIn("SUMMARY pass=13 fail=0 blocked=3", output)
        self.assertEqual(output.count("PASS "), 13)

    def test_blocked_lines_exact_text(self):
        _code, output = run_cli(["--fixture", str(FIXTURE_DIR)])
        for name, text in BLOCKED_EXPECTED.items():
            self.assertIn("BLOCKED %s %s" % (name, text), output)

    def test_expected_counts_mismatch_fails_golden(self):
        tmp = tempfile.mkdtemp(prefix="m4-acc-expected-")
        self.addCleanup(shutil.rmtree, tmp, True)
        copy = Path(tmp) / "mini_ed01"
        shutil.copytree(FIXTURE_DIR, copy)
        expected_path = copy / "expected" / "m4.stage_package.yaml"
        expected = yaml.safe_load(expected_path.read_text(encoding="utf-8"))
        expected["manifest"]["counts"]["assertions"] = 3
        expected_path.write_text(
            yaml.safe_dump(expected, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        code, output = run_cli(["--fixture", str(copy)])
        self.assertEqual(code, 1)
        self.assertIn("FAIL golden_match", output)

    def test_ruling_choice_b_fails_golden(self):
        tmp = tempfile.mkdtemp(prefix="m4-acc-ruling-")
        self.addCleanup(shutil.rmtree, tmp, True)
        copy = Path(tmp) / "mini_ed01"
        shutil.copytree(FIXTURE_DIR, copy)
        ruling_path = copy / "m4" / "ruling_m4_d001.yaml"
        text = ruling_path.read_text(encoding="utf-8")
        ruling_path.write_text(text.replace("choice: a", "choice: b", 1), encoding="utf-8")
        code, output = run_cli(["--fixture", str(copy)])
        self.assertEqual(code, 1)
        self.assertIn("FAIL golden_match", output)

    def test_prepare_failure_exits_1(self):
        buf = io.StringIO()
        with mock.patch.object(
            acceptance, "ingest", side_effect=RuntimeError("boom")
        ):
            with contextlib.redirect_stdout(buf):
                code = acceptance.main(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(code, 1)
        self.assertTrue(
            buf.getvalue().splitlines()[0].startswith(
                "FAIL m4_acceptance 宿主准备失败: RuntimeError"
            )
        )

    def test_missing_fixture_exit_3(self):
        code, _output = run_cli(["--fixture", "/nonexistent/mini_ed01"])
        self.assertEqual(code, 3)

    def test_missing_gold_dir_exit_3(self):
        code, _output = run_cli(
            ["--fixture", str(FIXTURE_DIR), "--gold-dir", "/nonexistent/m4"]
        )
        self.assertEqual(code, 3)

    def test_acceptance_does_not_import_assemble_gate_submission(self):
        source = (ROOT / "pipeline" / "knowledge_extraction" / "acceptance.py").read_text(
            encoding="utf-8"
        )
        import re

        for line in source.splitlines():
            if re.match(r"^\s*(from|import)\s", line) and (
                "assemble" in line or ".gate" in line or "submission" in line
            ):
                self.fail("acceptance.py 不得 import assemble/gate/submission: %s" % line)

    def test_tests_data_equals_fixture_gold(self):
        for name in (
            "submission_assertion_a.yaml",
            "submission_assertion_b.yaml",
            "submission_concept_mention_a.yaml",
            "ruling_m4_d001.yaml",
        ):
            self.assertEqual(
                (DATA / name).read_bytes(),
                (GOLD_DIR / name).read_bytes(),
                "tests/data/appendix_a/%s 必须与 fixture m4 金标逐字相同" % name,
            )

    def test_shell_exit_2_on_fixture(self):
        proc = subprocess.run(
            ["bash", str(SHELL)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(
            proc.stdout.strip().splitlines()[-1], "SUMMARY pass=13 fail=0 blocked=3"
        )

    def test_shell_never_trusts_copy_verify(self):
        tmp = tempfile.mkdtemp(prefix="m4-acc-copy-")
        self.addCleanup(shutil.rmtree, tmp, True)
        copy = Path(tmp) / "mini_ed01"
        shutil.copytree(FIXTURE_DIR, copy)
        spans_path = copy / "spans.yaml"
        lines = spans_path.read_text(encoding="utf-8").splitlines()
        trimmed = []
        dropped = 0
        for line in lines:
            if line.startswith("- span_id:") and dropped < 1:
                dropped += 1
                continue
            trimmed.append(line)
        spans_path.write_text("\n".join(trimmed) + "\n", encoding="utf-8")
        (copy / "verify.sh").write_text("echo FIXTURE OK\nexit 0\n", encoding="utf-8")
        proc = subprocess.run(
            ["bash", str(SHELL)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={"FIXTURE_DIR": str(copy), "PATH": "/usr/bin:/bin"},
        )
        self.assertEqual(proc.returncode, 1)
        self.assertTrue(proc.stdout.splitlines()[0].startswith("FAIL fixture_host"))


if __name__ == "__main__":
    unittest.main()
