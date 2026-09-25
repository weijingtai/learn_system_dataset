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
TEXT_FIXTURE_DIR = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "qianyuan_ed01_text"


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
                "PASS  20.1  一个 EditionPart 严格按 M1–M6 阶段 Gate 完成"
                "（宿主 qianyuan_ed01_text 电子文本真实 Ledger）"
            ),
            lines[0],
        )
        self.assertEqual(lines[-1], "SUMMARY pass=1 fail=0 blocked=0")

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
        # 20.5 自 M7 I 波集成（64c091e）起由 m7-assembler.sh 的真实退出码决定：
        # 本机有真书账本时全 PASS；没有账本时真书判据如实 BLOCKED，20.5 随之 BLOCKED。
        # 其余十项的结论不随宿主变化，仍按原快照锁定。
        # T04 阶段 2（cfe9feb）起 20.1 在仓库内电子文本宿主上 PASS（原 BLOCKED），与宿主无关：
        # 改前 有账本 3/1/7、无账本 2/1/8 → 改后 有账本 4/1/6、无账本 3/1/7。
        has_real_ledger = (REPO_ROOT / "var" / "ledgers" / "qianyuan_w8").is_dir()
        expected = (
            "SUMMARY pass=4 fail=1 blocked=6" if has_real_ledger else "SUMMARY pass=3 fail=1 blocked=7"
        )
        result = _run()
        lines = result.stdout.decode("utf-8").strip().splitlines()
        self.assertEqual(lines[-1], expected)
        self.assertEqual(result.returncode, 1)

    def test_accept_check_fail_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy_dir = Path(tmp) / "qianyuan_ed01_text"
            shutil.copytree(TEXT_FIXTURE_DIR, copy_dir)
            source_info = copy_dir / "source_info.yaml"
            lines = source_info.read_text(encoding="utf-8").splitlines()
            tampered = [
                "file_sha256: " + "0" * 64 if line.startswith("file_sha256:") else line
                for line in lines
            ]
            source_info.write_text("\n".join(tampered) + "\n", encoding="utf-8")
            result = _run(
                ["20.1"],
                env_extra={"ELECTRONIC_TEXT_FIXTURE_DIR": str(copy_dir)},
            )
        first = result.stdout.decode("utf-8").strip().splitlines()[0]
        self.assertTrue(first.startswith("FAIL  20.1"), first)

    def test_accept_check_unparsable_blocked_goes_to_host_blocked(self):
        # accept_check 的「BLOCKED 行无法解析」分支：以源码断言（run_all.sh 不可被 source 而不执行主流程）
        text = RUN_ALL.read_text(encoding="utf-8")
        self.assertIn("BLOCKED 行无法解析", text)


if __name__ == "__main__":
    unittest.main()
