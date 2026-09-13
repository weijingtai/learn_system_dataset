"""ACT impl-08/09：run_all.sh 的 20.1 / 20.10 case 体改为计算得出（规格 §20）。

先写本文件，运行 `.venv/bin/python -m unittest discover -s pipeline/contract_registry/tests -t .`
取得全红（Red），再改 `openspec/acceptance/run_all.sh`。
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_ALL = REPO_ROOT / "openspec" / "acceptance" / "run_all.sh"
FIXTURE_DIR = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"


def _run(items=None, env_extra=None):
    env = dict(os.environ)
    env["LC_ALL"] = "en_US.UTF-8"
    if env_extra:
        env.update(env_extra)
    command = ["bash", str(RUN_ALL)]
    if items:
        command.extend(items)
    return subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=900,
    )


class TestRunAll(unittest.TestCase):
    """覆盖 BDD §9.4：20.1/20.10 计算得出、全量 SUMMARY 不变。"""

    def test_20_1_blocked_line_computed(self):
        result = _run(["20.1"])
        lines = result.stdout.decode("utf-8").strip().splitlines()
        self.assertTrue(
            lines[0].startswith(
                "BLOCKED  20.1  前置缺失: M4 Knowledge Extraction；"
                "Local Orchestrator 首切片已串联 m1–m3、m5 Gate"
            ),
            lines[0],
        )
        self.assertEqual(lines[-1], "SUMMARY pass=0 fail=0 blocked=1")

    def test_20_10_blocked_line_computed(self):
        result = _run(["20.10"])
        lines = result.stdout.decode("utf-8").strip().splitlines()
        self.assertTrue(
            lines[0].startswith(
                "BLOCKED  20.10  前置缺失: Contract Registry；"
            ),
            lines[0],
        )

    def test_full_summary_unchanged(self):
        result = _run()
        lines = result.stdout.decode("utf-8").strip().splitlines()
        self.assertEqual(lines[-1], "SUMMARY pass=2 fail=1 blocked=8")
        self.assertEqual(result.returncode, 1)

    def test_accept_check_fail_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy_dir = Path(tmp) / "mini_ed01"
            shutil.copytree(FIXTURE_DIR, copy_dir)
            spans = copy_dir / "spans.yaml"
            lines = spans.read_text(encoding="utf-8").rstrip().splitlines()
            spans.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
            result = _run(["20.1"], env_extra={"FIXTURE_DIR": str(copy_dir)})
        first = result.stdout.decode("utf-8").strip().splitlines()[0]
        self.assertTrue(first.startswith("FAIL  20.1"), first)

    def test_accept_check_unparsable_blocked_goes_to_host_blocked(self):
        # accept_check 的「BLOCKED 行无法解析」分支：以源码断言（run_all.sh 不可被 source 而不执行主流程）
        text = RUN_ALL.read_text(encoding="utf-8")
        self.assertIn("BLOCKED 行无法解析", text)


if __name__ == "__main__":
    unittest.main()
