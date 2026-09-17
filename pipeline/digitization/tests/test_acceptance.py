"""M2 电子文本清洗验收测试。

涵盖三态（第 96 条 D2 / 第 101 条）：
- 宿主缺失 → BLOCKED (exit 2)
- 期望缺失 / SHA256SUMS 不符 → BLOCKED (exit 2)
- 齐备比对一致 → PASS (exit 0)
- 产出与期望不符 → FAIL (exit 1)
- 12 类逐类比对、第 98 条① YAML 头范围规则
- 独立性护栏：不从 pipeline.digitization 导入头区间识别逻辑

依据 G7-RULINGS 第 105 条：
退役原 J4 旧用例（断言「把 FIXTURE_DIR 当作已含流水线产物的 Ledger 目录读取」）：
- test_m2_check_passes_on_valid_ledger
- test_m2_check_fails_on_deferred
- test_m2_check_fails_on_missing_report
保留用例：
- test_m2_check_blocked_on_no_ledger
"""

import ast
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

from pipeline.digitization import FINDING_KINDS
from pipeline.digitization.acceptance import (
    _compare_m2,
    check_m2_sanitization,
    detect_yaml_front_matter_end,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
M2_SCRIPT = REPO_ROOT / "openspec" / "acceptance" / "m2-sanitization.sh"

# 合成原文及手算值（不依赖被测模块生成）
# 包含 20 字符的 YAML front matter 与正文
SYNTHETIC_TEXT = "---\ntitle: test\n---\nhello world\n"
SYNTHETIC_BYTES = SYNTHETIC_TEXT.encode("utf-8")
SYNTHETIC_SHA256 = hashlib.sha256(SYNTHETIC_BYTES).hexdigest()
SYNTHETIC_SIZE = len(SYNTHETIC_BYTES)


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
        "source_id": "src_synth_m2_ed01",
        "work_title": "合成 M2 测试文本",
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
        "repo_commit": "abcdef1234567890abcdef1234567890abcdef12",
        "yaml_metadata": "---\ntitle: test\n---\n",
    }
    (host / "source_info.yaml").write_text(
        yaml.dump(source_info, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    # 3. 独立金标（YAML 头分离 1 条 escape_residue 0..20，其余 11 类无发现）
    golden_findings = {
        "schema": "golden_findings/1",
        "findings": [
            {
                "kind": "escape_residue",
                "raw_start": 0 if not corrupt_expected else 1,
                "raw_end": 20,
                "raw_excerpt": "---\ntitle: test\n---\n" if not corrupt_expected else "--\ntitle: test\n---\n",
                "basis": "YAML 头与正文分离",
            }
        ],
    }
    gold_text = yaml.dump(golden_findings, allow_unicode=True, sort_keys=False)
    gold_file = expected_dir / "golden_findings.yaml"
    gold_file.write_text(gold_text, encoding="utf-8")

    # 4. SHA256SUMS
    if corrupt_sums:
        bad_digest = "1" * 64
        (expected_dir / "SHA256SUMS").write_text(f"{bad_digest}  golden_findings.yaml\n", encoding="utf-8")
    else:
        digest = hashlib.sha256(gold_file.read_bytes()).hexdigest()
        (expected_dir / "SHA256SUMS").write_text(f"{digest}  golden_findings.yaml\n", encoding="utf-8")

    return host


class TestM2SanitizationAcceptance(unittest.TestCase):
    """M2 sanitization acceptance 检查测试（第 96 条 D2 / 第 98 条 / 第 101 条 / 第 105 条）。"""

    def test_m2_check_blocked_on_no_ledger(self):
        """无宿主目录时 check_m2_sanitization 应返回 BLOCKED（保留已验收护栏）。"""
        results = check_m2_sanitization(Path("/nonexistent/path"))
        blocked_checks = [r for r in results if r["status"] == "BLOCKED"]
        self.assertGreater(len(blocked_checks), 0, "无宿主目录时应返回 BLOCKED")

    def test_shell_blocked_when_host_missing(self):
        """宿主缺失时，m2-sanitization.sh 报 BLOCKED 且 exit 2。"""
        env = os.environ.copy()
        env["FIXTURE_DIR"] = "/nonexistent/test/host/dir"
        proc = subprocess.run(
            ["bash", str(M2_SCRIPT)],
            env=env,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(proc.returncode, 2, f"宿主缺失应 exit 2，实际 stdout:\n{proc.stdout}")
        self.assertIn("BLOCKED", proc.stdout)
        self.assertIn("blocked=1", proc.stdout)

    def test_shell_blocked_when_expected_missing(self):
        """原文在但金标文件缺失时，m2-sanitization.sh 报 BLOCKED 且 exit 2。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            host = _create_synthetic_host(Path(tmpdir))
            (host / "expected" / "golden_findings.yaml").unlink()
            env = os.environ.copy()
            env["FIXTURE_DIR"] = str(host)
            proc = subprocess.run(
                ["bash", str(M2_SCRIPT)],
                env=env,
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            self.assertEqual(proc.returncode, 2, f"金标缺失应 exit 2，实际 stdout:\n{proc.stdout}")
            self.assertIn("BLOCKED", proc.stdout)
            self.assertIn("golden_present", proc.stdout)

    def test_shell_blocked_when_expected_checksum_mismatch(self):
        """金标文件存在但 SHA256SUMS 校验不符时，报 BLOCKED 且文案写明「期望文件被改动」，exit 2，不是 FAIL。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            host = _create_synthetic_host(Path(tmpdir), corrupt_sums=True)
            env = os.environ.copy()
            env["FIXTURE_DIR"] = str(host)
            proc = subprocess.run(
                ["bash", str(M2_SCRIPT)],
                env=env,
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            self.assertEqual(proc.returncode, 2, f"校验不符应 exit 2，实际 stdout:\n{proc.stdout}")
            self.assertIn("BLOCKED", proc.stdout)
            self.assertIn("期望文件被改动", proc.stdout)
            self.assertNotIn("FAIL", proc.stdout)

    def test_shell_pass_on_matching_synthetic_host(self):
        """合成宿主原文与手写金标相符时，实跑 12 类逐类比对全部 PASS 且 exit 0。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            host = _create_synthetic_host(Path(tmpdir))
            env = os.environ.copy()
            env["FIXTURE_DIR"] = str(host)
            proc = subprocess.run(
                ["bash", str(M2_SCRIPT)],
                env=env,
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            self.assertEqual(proc.returncode, 0, f"比对一致应 exit 0，实际 stdout:\n{proc.stdout}")
            # 12 类逐类各有一行 PASS
            for kind in FINDING_KINDS:
                self.assertIn(f"PASS finding_kind_{kind}", proc.stdout, f"缺少 {kind} 的比对行")
            self.assertIn("fail=0 blocked=0", proc.stdout)

    def test_shell_fail_when_output_diverges_from_expected(self):
        """金标中故意改一个偏移（但校验和同步更新），实跑比对出 FAIL 且 exit 1。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            host = _create_synthetic_host(Path(tmpdir), corrupt_expected=True, corrupt_sums=False)
            env = os.environ.copy()
            env["FIXTURE_DIR"] = str(host)
            proc = subprocess.run(
                ["bash", str(M2_SCRIPT)],
                env=env,
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            self.assertEqual(proc.returncode, 1, f"比对不一致应 exit 1，实际 rc={proc.returncode} stdout:\n{proc.stdout}")
            self.assertIn("FAIL", proc.stdout)
            self.assertIn("finding_kind_escape_residue", proc.stdout)

    def test_compare_excludes_yaml_header_findings_except_separation(self):
        """第 98 条①：落在 YAML 头区间内的条目，除「YAML 头与正文分离」那条 escape_residue 外，不计入比对。"""
        raw_text = "---\ntitle: test\nurl: https://example.org\n---\n正文段落。"
        head_end = detect_yaml_front_matter_end(raw_text)
        self.assertGreater(head_end, 0, "应正确识别 YAML front matter 结束位置")

        # 构造三条金标：
        # 1. 头内 watermark（必须被排除）
        # 2. 头内 escape_residue（分离项，必须保留）
        # 3. 正文内 variant_mixed（必须保留）
        golden = {
            "findings": [
                {
                    "kind": "watermark",
                    "raw_start": 10,
                    "raw_end": 35,
                    "raw_excerpt": "url: https://example.org",
                    "basis": "溯源 URL",
                },
                {
                    "kind": "escape_residue",
                    "raw_start": 0,
                    "raw_end": head_end,
                    "raw_excerpt": raw_text[:head_end],
                    "basis": "YAML 头与正文分离",
                },
                {
                    "kind": "variant_mixed",
                    "raw_start": head_end + 1,
                    "raw_end": head_end + 2,
                    "raw_excerpt": "正",
                    "basis": "异体字",
                },
            ]
        }
        # 构造 M2 实跑结果：恰好产生头分离与正文 variant_mixed，不产生 watermark
        facts = {
            "raw_text": raw_text,
            "report_findings": [
                {
                    "kind": "escape_residue",
                    "raw_start": 0,
                    "raw_end": head_end,
                    "raw_excerpt": raw_text[:head_end],
                    "basis": "YAML 头与正文分离",
                },
                {
                    "kind": "variant_mixed",
                    "raw_start": head_end + 1,
                    "raw_end": head_end + 2,
                    "raw_excerpt": "正",
                    "basis": "异体字",
                },
            ],
            "deferred_count": 0,
            "gate_passed": True,
            "step_status": "succeeded",
        }
        results = _compare_m2(facts, golden)
        # watermark 因在头内被排除，故 finding_kind_watermark 比较的是空集 vs 空集 → PASS
        watermark_res = next(r for r in results if r["check"] == "finding_kind_watermark")
        self.assertEqual(watermark_res["status"], "PASS")

        # scope_rule 应记录排除了 1 条
        scope_res = next(r for r in results if r["check"] == "yaml_header_scope_rule")
        self.assertIn("排除 1 条", scope_res["detail"])

    def test_compare_does_not_import_digitization_for_header_range(self):
        """断言比对器模块源码不从 pipeline.digitization 导入头区间函数（反自证，第 95/101 条）。"""
        acc_file = REPO_ROOT / "pipeline" / "digitization" / "acceptance.py"
        source = acc_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(acc_file))

        forbidden_names = {
            "detect_yaml_front_matter",
            "detect_front_matter",
            "front_matter",
            "clean_text",
            "cleaner",
        }

        # 检查所有 import 与 import from（含相对导入，第 93 条纪律）
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    for fn in forbidden_names:
                        self.assertNotIn(
                            fn,
                            parts,
                            f"acceptance.py 不得导入清洗器模块: {alias.name}",
                        )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                # 检查模块名
                for fn in forbidden_names:
                    self.assertNotIn(
                        fn,
                        mod.split("."),
                        f"acceptance.py 不得从清洗器导入: module={mod}",
                    )
                # 检查导入的符号
                for alias in node.names:
                    self.assertNotIn(
                        alias.name,
                        forbidden_names,
                        f"acceptance.py 不得导入头区间相关符号: {alias.name} from {mod}",
                    )


if __name__ == "__main__":
    unittest.main()