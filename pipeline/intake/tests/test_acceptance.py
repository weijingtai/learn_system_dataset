"""M1 电子文本入库验收测试。

涵盖三态（第 96 条 D2 / 第 101 条）：
- 宿主缺失 → BLOCKED (exit 2)
- 期望缺失 / SHA256SUMS 不符 → BLOCKED (exit 2)
- 齐备比对一致 → PASS (exit 0)
- 产出与期望不符 → FAIL (exit 1)

依据 G7-RULINGS 第 105 条：
退役原 J4 旧用例（断言「把 FIXTURE_DIR 当作已含流水线产物的 Ledger 目录读取」）：
- test_m1_check_passes_on_valid_ledger
- test_m1_check_fails_on_missing_manifest
保留用例：
- test_m1_check_blocked_on_no_ledger
"""

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

from pipeline.intake.acceptance import check_m1_intake

REPO_ROOT = Path(__file__).resolve().parents[3]
M1_SCRIPT = REPO_ROOT / "openspec" / "acceptance" / "m1-intake.sh"

# 合成原文及手算值（不依赖被测模块生成）
SYNTHETIC_TEXT = "---\ntitle: 测试\n---\n正文内容测试。\n"
SYNTHETIC_BYTES = SYNTHETIC_TEXT.encode("utf-8")
SYNTHETIC_SHA256 = hashlib.sha256(SYNTHETIC_BYTES).hexdigest()
SYNTHETIC_SIZE = len(SYNTHETIC_BYTES)
SYNTHETIC_CHARS = len(SYNTHETIC_TEXT)


def _create_synthetic_host(base_dir: Path, corrupt_expected: bool = False, corrupt_sums: bool = False) -> Path:
    """创建合成宿主目录（含原文、source_info.yaml、expected/）。"""
    host = base_dir / "synthetic_host"
    host.mkdir(parents=True, exist_ok=True)
    expected_dir = host / "expected"
    expected_dir.mkdir(parents=True, exist_ok=True)

    # 1. 原文
    text_path = host / "sample.md"
    text_path.write_bytes(SYNTHETIC_BYTES)

    # 2. 来源申报
    source_info = {
        "source_id": "src_synth_ed01",
        "work_title": "合成测试文本",
        "edition_note": "测试版本说明",
        "technique_id": "qizheng",
        "rights_status": "站方声明免费下载、未附许可证",
        "release_policy": "reference_and_hash_only",
        "edition_part": {
            "artifact_id": "art_00000000000000000000000000000001",
            "label": "合成部分",
            "pages": ["sample"],
        },
        "source_site": "example.org/synthetic",
        "source_url": "https://example.org/synthetic/sample.md",
        "file_sha256": SYNTHETIC_SHA256,
        "pages": ["sample"],
        "repo_commit": "1234567890abcdef1234567890abcdef12345678",
        "yaml_metadata": "---\ntitle: 测试\n---\n",
    }
    (host / "source_info.yaml").write_text(
        yaml.dump(source_info, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    # 3. 独立期望文件
    expected_data = {
        "schema": "qianyuan_m1_expected/1",
        "page": "sample",
        "sha256": SYNTHETIC_SHA256,
        "normalized_sha256": SYNTHETIC_SHA256,
        "size_bytes": SYNTHETIC_SIZE if not corrupt_expected else SYNTHETIC_SIZE + 999,
        "text_length_chars": SYNTHETIC_CHARS,
        "original_encoding": "utf-8",
        "repo_commit": "1234567890abcdef1234567890abcdef12345678",
        "source_site": "example.org/synthetic",
        "rights_status": "站方声明免费下载、未附许可证",
        "release_policy": "reference_and_hash_only",
    }
    exp_text = yaml.dump(expected_data, allow_unicode=True, sort_keys=False)
    exp_file = expected_dir / "m1_source_expected.yaml"
    exp_file.write_text(exp_text, encoding="utf-8")

    # 4. SHA256SUMS
    if corrupt_sums:
        bad_digest = "0" * 64
        (expected_dir / "SHA256SUMS").write_text(f"{bad_digest}  m1_source_expected.yaml\n", encoding="utf-8")
    else:
        digest = hashlib.sha256(exp_file.read_bytes()).hexdigest()
        (expected_dir / "SHA256SUMS").write_text(f"{digest}  m1_source_expected.yaml\n", encoding="utf-8")

    return host


class TestM1IntakeAcceptance(unittest.TestCase):
    """M1 intake acceptance 检查测试（第 96 条 D2 / 第 101 条 / 第 105 条）。"""

    def test_m1_check_blocked_on_no_ledger(self):
        """无宿主目录时 check_m1_intake 应返回 BLOCKED（保留已验收护栏）。"""
        results = check_m1_intake(Path("/nonexistent/path"))
        blocked_checks = [r for r in results if r["status"] == "BLOCKED"]
        self.assertGreater(len(blocked_checks), 0, "无宿主目录时应返回 BLOCKED")

    def test_shell_blocked_when_host_missing(self):
        """宿主缺失时，m1-intake.sh 报 BLOCKED 且 exit 2。"""
        env = os.environ.copy()
        env["FIXTURE_DIR"] = "/nonexistent/test/host/dir"
        proc = subprocess.run(
            ["bash", str(M1_SCRIPT)],
            env=env,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(proc.returncode, 2, f"宿主缺失应 exit 2，实际 stdout:\n{proc.stdout}")
        self.assertIn("BLOCKED", proc.stdout)
        self.assertIn("blocked=1", proc.stdout)

    def test_shell_blocked_when_expected_missing(self):
        """原文在但期望文件缺失时，m1-intake.sh 报 BLOCKED 且 exit 2。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            host = _create_synthetic_host(Path(tmpdir))
            # 删除期望文件
            (host / "expected" / "m1_source_expected.yaml").unlink()
            env = os.environ.copy()
            env["FIXTURE_DIR"] = str(host)
            proc = subprocess.run(
                ["bash", str(M1_SCRIPT)],
                env=env,
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            self.assertEqual(proc.returncode, 2, f"期望文件缺失应 exit 2，实际 stdout:\n{proc.stdout}")
            self.assertIn("BLOCKED", proc.stdout)
            self.assertIn("expected_present", proc.stdout)

    def test_shell_blocked_when_expected_checksum_mismatch(self):
        """期望文件存在但 SHA256SUMS 校验不符时，报 BLOCKED 且文案写明「期望文件被改动」，exit 2，不是 FAIL。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            host = _create_synthetic_host(Path(tmpdir), corrupt_sums=True)
            env = os.environ.copy()
            env["FIXTURE_DIR"] = str(host)
            proc = subprocess.run(
                ["bash", str(M1_SCRIPT)],
                env=env,
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            self.assertEqual(proc.returncode, 2, f"校验不符应 exit 2，实际 stdout:\n{proc.stdout}")
            self.assertIn("BLOCKED", proc.stdout)
            self.assertIn("期望文件被改动", proc.stdout)
            # 纪律：期望不可信即不可判定，不得判 FAIL
            self.assertNotIn("FAIL", proc.stdout)

    def test_shell_pass_on_matching_synthetic_host(self):
        """合成宿主原文与手写期望相符时，实跑比对全部 PASS 且 exit 0。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            host = _create_synthetic_host(Path(tmpdir))
            env = os.environ.copy()
            env["FIXTURE_DIR"] = str(host)
            proc = subprocess.run(
                ["bash", str(M1_SCRIPT)],
                env=env,
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            self.assertEqual(proc.returncode, 0, f"比对一致应 exit 0，实际 stdout:\n{proc.stdout}")
            self.assertIn("SUMMARY pass=11 fail=0 blocked=0", proc.stdout)

    def test_shell_fail_when_output_diverges_from_expected(self):
        """期望里故意改一个值（但校验和同步更新），实跑比对出 FAIL 且 exit 1。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            host = _create_synthetic_host(Path(tmpdir), corrupt_expected=True, corrupt_sums=False)
            env = os.environ.copy()
            env["FIXTURE_DIR"] = str(host)
            proc = subprocess.run(
                ["bash", str(M1_SCRIPT)],
                env=env,
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            self.assertEqual(proc.returncode, 1, f"比对不一致应 exit 1，实际 rc={proc.returncode} stdout:\n{proc.stdout}")
            self.assertIn("FAIL", proc.stdout)
            self.assertIn("source_size", proc.stdout)


if __name__ == "__main__":
    unittest.main()