"""ACT 07：acceptance.py 电子文本宿主支持 + m3-coverage.sh 电子文本路由。

用例名逐字对照 act/07.yaml tests 节（14 条具名用例），另有两条例外宿主/护栏用例。

synthetic_fixture: true —— 凡需「有效宿主」的用例一律以 tempfile 构造合成宿主，
**不依赖**正在另行落地的真实宿主 `pipeline/corpus/_fixture/qianyuan_ed01_text`（P4）。
"""

import ast
import hashlib
import io
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import yaml

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
REPO_ROOT = Path(__file__).resolve().parents[3]
SHELL_SCRIPT = REPO_ROOT / "openspec" / "acceptance" / "m3-coverage.sh"

# ---------------------------------------------------------------- 合成宿主常量
# 电子文本样例（synthetic_fixture: true）：无需清洗的干净文本，M2 清洗恒等、Gate 放行。
# 结构切分产出 2 片：`乾元秘旨\n`（5 字，非窗口）与 `太極而動…動靜相生。\n`（21 字，窗口）。
SYNTH_SOURCE_TEXT = "乾元秘旨\n太極而動，動而生陽，靜而生陰，動靜相生。\n"

# 含显式缺失标记 → M2 产出 terminal_state=deferred 的 missing 发现 → M3 必须阻断（第 95 条）。
SYNTH_DEFERRED_TEXT = "乾元秘旨\n太極而動，動而生陽，靜而生陰，此處【缺】一字。\n"

# 双模型回放录制：窗口 qianyuan_w001 两路边界故意不一致 → disputed → 人工裁决。
SYNTH_RECORDINGS = """schema: m3_boundary_recordings/1
synthetic: true
template_id: m3_boundary_v1
recordings:
  - window_id: qianyuan_w001
    slot: a
    response: '{"segments": [{"start_offset": 0, "end_offset": 10, "reason": "首句"}, {"start_offset": 10, "end_offset": 21, "reason": "次句"}]}'
  - window_id: qianyuan_w001
    slot: b
    response: '{"segments": [{"start_offset": 0, "end_offset": 14, "reason": "另切"}, {"start_offset": 14, "end_offset": 21, "reason": "余下"}]}'
"""

# 人工裁决（P7：由宿主提供，不由被测模块代填；标 synthetic_fixture）。
SYNTH_DECISIONS = """- schema: m3_boundary_decision/1
  decision_type: review_source_fidelity
  window_id: qianyuan_w001
  choice: custom
  segments: [[0, 10], [10, 21]]
  synthetic_fixture: true
"""

SYNTH_EDITION_PART_ID = "art_000000000000000000000000000000e1"

# 电子文本端到端子项名（逐字取自 act/07 contract；**不**从被测模块导入，否则护栏自证）
ELECTRONIC_SUBCHECKS = (
    "host_source",
    "m1_manifest",
    "m2_gate",
    "m3_semantic",
    "semantic_gate",
    "stage_package",
    "zero_network",
)

# 宿主缺失时的 exact BLOCKED 文本（逐字取自 act/07 contract）
ELECTRONIC_HOST_MISSING_LINE = (
    "BLOCKED semantic_layer 前置缺失: 电子文本验收宿主匮乏；未提供 --electronic-text-fixture"
)


def _source_info(data: bytes) -> dict:
    """合成 M1 来源申报（synthetic_fixture: true）。"""
    return {
        "source_id": "src_qianyuan_ed01",
        "work_title": "乾元秘旨",
        "edition_note": "殆知阁电子文本（合成样例）",
        "technique_id": "qizheng",
        "rights_status": "站方声明免费下载、未附许可证",
        "release_policy": "reference_and_hash_only",
        "edition_part": {
            "artifact_id": SYNTH_EDITION_PART_ID,
            "label": "卷一",
            "pages": ["page_001"],
        },
        "source_site": "github.com/daizhige-org/daizhigev20",
        "source_url": "https://example.invalid/qianyuan.md",
        "file_sha256": hashlib.sha256(data).hexdigest(),
        "pages": ["page_001"],
    }


def _build_synthetic_host(
    root: Path,
    *,
    source_text: str = SYNTH_SOURCE_TEXT,
    recordings: str = SYNTH_RECORDINGS,
    decisions: str = SYNTH_DECISIONS,
) -> Path:
    """以 tempfile 构造合成电子文本宿主（synthetic_fixture: true）。

    宿主布局：
        source_info.yaml      M1 来源申报
        page_001.txt          电子文本原文件（其字节被 file_sha256 钉住）
        recordings.yaml       双模型回放录制
        human_decisions.yaml  人工边界裁决列表
    """
    root.mkdir(parents=True, exist_ok=True)
    data = source_text.encode("utf-8")
    (root / "source_info.yaml").write_text(
        yaml.safe_dump(_source_info(data), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (root / "page_001.txt").write_bytes(data)
    (root / "recordings.yaml").write_text(recordings, encoding="utf-8")
    (root / "human_decisions.yaml").write_text(decisions, encoding="utf-8")
    return root


def _run_acceptance(argv):
    """调用 acceptance.main，返回 (rc, stdout)。"""
    from pipeline.corpus_compiler.acceptance import main

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(argv)
    return rc, buf.getvalue()


class TestAcceptanceUnit(unittest.TestCase):
    """acceptance.py 单元测试。"""

    def test_fixture_yields_eight_pass_one_blocked_exit_2(self):
        from pipeline.corpus_compiler.acceptance import main
        rc = main(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(rc, 2)

    def test_semantic_layer_line_is_blocked_with_exact_text(self):
        from pipeline.corpus_compiler.acceptance import main
        with mock.patch("builtins.print") as mock_print:
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
        with mock.patch(
            "pipeline.corpus_compiler.acceptance.ingest",
            side_effect=RuntimeError("boom"),
        ):
            with mock.patch("builtins.print") as mock_print:
                rc = main(["--fixture", str(FIXTURE_DIR)])
            self.assertEqual(rc, 1)
            first_line = mock_print.call_args_list[0].args[0]
            self.assertTrue(first_line.startswith("FAIL m3_acceptance 宿主准备失败: RuntimeError"))

    def test_missing_fixture_exit_3(self):
        from pipeline.corpus_compiler.acceptance import main
        rc = main(["--fixture", "/nonexistent/path/fixture"])
        self.assertEqual(rc, 3)

    def test_missing_manifest_exit_3(self):
        from pipeline.corpus_compiler.acceptance import main
        tmp = tempfile.mkdtemp(prefix="m3-acc-nomanifest-")
        try:
            rc = main(["--fixture", tmp])
            self.assertEqual(rc, 3)
        finally:
            shutil.rmtree(tmp, True)

    def test_missing_yaml_exit_3(self):
        from pipeline.corpus_compiler import acceptance as acceptance_module
        with mock.patch.object(acceptance_module, "yaml", None):
            with mock.patch("builtins.print") as mock_print:
                rc = acceptance_module.main(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(rc, 3)
        first_line = mock_print.call_args_list[0].args[0]
        self.assertTrue(first_line.startswith("FAIL m3_acceptance 宿主准备失败: ImportError"))


class TestElectronicAcceptance(unittest.TestCase):
    """acceptance.py 电子文本路由（synthetic_fixture: true，全部用 tempfile 合成宿主）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="m3-elec-")
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.host = _build_synthetic_host(self.base / "host")
        self.absent = self.base / "absent_host"

    def test_missing_fixture_exact_blocked_message(self):
        """synthetic_fixture: true，未提供宿主时 semantic_layer 判 BLOCKED，文本逐字。"""
        rc, out = _run_acceptance(["--electronic-text-fixture", str(self.absent)])
        self.assertEqual(rc, 2)
        self.assertIn(ELECTRONIC_HOST_MISSING_LINE, out)
        self.assertIn("SUMMARY pass=0 fail=0 blocked=1", out)

    def test_electronic_semantic_acceptance_subchecks_no_fail(self):
        """synthetic_fixture: true，各具名子项均出现且 fail=0，**不**钉死 pass 总数（第 54、87 条）。"""
        rc, out = _run_acceptance(["--electronic-text-fixture", str(self.host)])
        self.assertEqual(rc, 0, out)
        for name in ELECTRONIC_SUBCHECKS:
            self.assertRegex(
                out, r"(?m)^PASS %s " % re.escape(name), "缺子项 %s\n%s" % (name, out)
            )
        self.assertNotIn("FAIL ", out)
        self.assertNotIn("BLOCKED ", out)
        summary = re.search(r"(?m)^SUMMARY pass=\d+ fail=(\d+) blocked=(\d+)$", out)
        self.assertIsNotNone(summary, out)
        self.assertEqual(summary.group(1), "0", out)
        self.assertEqual(summary.group(2), "0", out)

    def test_tampered_electronic_fixture_fails_acceptance(self):
        """synthetic_fixture: true，宿主原文被篡改（追踪链断裂）时不得伪造绿灯。"""
        (self.host / "page_001.txt").write_text("篡改后的文本\n", encoding="utf-8")
        rc, out = _run_acceptance(["--electronic-text-fixture", str(self.host)])
        self.assertEqual(rc, 1, out)
        self.assertIn("FAIL host_source", out)

    def test_electronic_acceptance_blocked_on_deferred_findings(self):
        """synthetic_fixture: true，宿主含 deferred 发现（missing）→ M3 阻断判 BLOCKED exit 2。"""
        host = _build_synthetic_host(self.base / "deferred_host", source_text=SYNTH_DEFERRED_TEXT)
        rc, out = _run_acceptance(["--electronic-text-fixture", str(host)])
        self.assertEqual(rc, 2, out)
        self.assertIn("BLOCKED m2_gate", out)
        self.assertNotIn("PASS m2_gate", out)

    def test_zero_network_enforced_during_acceptance(self):
        """synthetic_fixture: true，零网络护栏 load-bearing：注入网络调用必报 zero_network FAIL。"""
        from pipeline.corpus_compiler import semantic

        # 1. 正常宿主：全程零网络
        rc, out = _run_acceptance(["--electronic-text-fixture", str(self.host)])
        self.assertEqual(rc, 0, out)
        self.assertIn("PASS zero_network", out)

        # 2. 注入网络调用：验收必须如实报 zero_network FAIL（护栏不得空转）
        real_open = semantic.review.open_semantic_review

        def network_hitting_open(*args, **kwargs):
            import socket as _socket

            try:
                _socket.create_connection(("127.0.0.1", 9), timeout=0.05)
            except Exception:
                pass
            return real_open(*args, **kwargs)

        with mock.patch.object(
            semantic.review, "open_semantic_review", network_hitting_open
        ):
            rc2, out2 = _run_acceptance(["--electronic-text-fixture", str(self.host)])
        self.assertEqual(rc2, 1, out2)
        self.assertIn("FAIL zero_network", out2)

    def test_acceptance_cli_exit_codes(self):
        """synthetic_fixture: true，CLI 退出码：有效宿主 0、篡改 1、宿主缺失 2。"""
        rc, out = _run_acceptance(["--electronic-text-fixture", str(self.host)])
        self.assertEqual(rc, 0, out)

        tampered = _build_synthetic_host(self.base / "tampered_host")
        (tampered / "page_001.txt").write_text("篡改\n", encoding="utf-8")
        rc, out = _run_acceptance(["--electronic-text-fixture", str(tampered)])
        self.assertEqual(rc, 1, out)

        rc, out = _run_acceptance(["--electronic-text-fixture", str(self.absent)])
        self.assertEqual(rc, 2, out)

        rc, _ = _run_acceptance(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(rc, 2)

    def test_acceptance_summary_line_format(self):
        """synthetic_fixture: true，SUMMARY 末行格式逐字 `SUMMARY pass=N fail=N blocked=N`。"""
        pattern = re.compile(r"^SUMMARY pass=\d+ fail=\d+ blocked=\d+$")
        for argv in (
            ["--electronic-text-fixture", str(self.host)],
            ["--electronic-text-fixture", str(self.absent)],
            ["--fixture", str(FIXTURE_DIR)],
        ):
            rc, out = _run_acceptance(argv)
            last = out.strip().splitlines()[-1]
            self.assertRegex(last, pattern, "argv=%s\n%s" % (argv, out))

    def test_acceptance_does_not_import_compiler_internals(self):
        """第 88 条护栏：acceptance.py 不得直接 import 编译器底层实现模块（防同错同过）。"""
        source = (REPO_ROOT / "pipeline" / "corpus_compiler" / "acceptance.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.append(node.module)
                imported.extend(alias.name for alias in node.names)

        forbidden = (
            "text_compiler",
            "offset_anchors",
            "gate_offset",
            "assemble_offset",
            "step_offset",
            "offset_assemble",
            "offset_rules",
            "proposals",
            "proposer",
            "corpus_compiler.compiler",
            "corpus_compiler.gate",
            "corpus_compiler.serialize",
            "corpus_compiler.inputs",
        )
        for module in imported:
            for name in forbidden:
                self.assertNotIn(
                    name, module, "acceptance.py 违规引入编译器实现模块: %s" % module
                )

    def test_run_all_sh_untouched_and_zero_network(self):
        """第 88 条护栏：run_all.sh 无任何未提交修改，且电子文本验收全程零网络。"""
        target = "openspec/acceptance/run_all.sh"
        diff = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--", target],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        self.assertEqual(diff.stdout.strip(), "", "run_all.sh 存在未提交修改: %s" % diff.stdout)
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--", target],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        self.assertEqual(untracked.stdout.strip(), "", "run_all.sh 被列为未跟踪: %s" % untracked.stdout)
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", target],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        self.assertEqual(status.stdout.strip(), "", "run_all.sh 状态不干净: %s" % status.stdout)

        rc, out = _run_acceptance(["--electronic-text-fixture", str(self.host)])
        self.assertEqual(rc, 0, out)
        self.assertIn("PASS zero_network", out)


class TestCoverageShell(unittest.TestCase):
    """m3-coverage.sh 电子文本路由（synthetic_fixture: true）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="m3-shell-")
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)

    def _run_shell(self, env_overrides=None, script=None):
        env = {k: v for k, v in os.environ.items() if not k.startswith("ELECTRONIC_TEXT_FIXTURE")}
        env["LC_ALL"] = "en_US.UTF-8"
        env.update(env_overrides or {})
        return subprocess.run(
            ["bash", str(script or SHELL_SCRIPT)],
            capture_output=True, text=True, cwd=str(REPO_ROOT), env=env,
        )

    def _sandbox(self, fake_python: str, *, electronic_host: bool) -> Path:
        """把脚本复制进伪仓库根，并放置行为可控的 `.venv/bin/python`。"""
        root = self.base / ("sandbox_%d" % len(list(self.base.iterdir())))
        dest = root / "openspec" / "acceptance" / "m3-coverage.sh"
        dest.parent.mkdir(parents=True)
        shutil.copy2(SHELL_SCRIPT, dest)
        py = root / ".venv" / "bin" / "python"
        py.parent.mkdir(parents=True)
        py.write_text(fake_python, encoding="utf-8")
        py.chmod(0o755)
        if electronic_host:
            (root / "pipeline" / "corpus" / "_fixture" / "qianyuan_ed01_text").mkdir(parents=True)
        # OCR 路线的旧宿主存在，用于证明默认宿主未回落到它（第 94 条 D2）
        (root / "pipeline" / "corpus" / "_fixture" / "mini_ed01").mkdir(parents=True)
        return dest

    def test_missing_fixture_exits_2_blocked(self):
        """第 88 条护栏：宿主缺失时脚本输出含 exact BLOCKED 文本且 exit=2，不伪造绿灯。"""
        proc = self._run_shell(
            {"ELECTRONIC_TEXT_FIXTURE_DIR": str(self.base / "no_such_host")}
        )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("BLOCKED m3_coverage 前置缺失: 电子文本验收宿主不存在", proc.stdout)
        self.assertIn("SUMMARY pass=0 fail=0 blocked=1", proc.stdout)

    def test_shell_script_exits_2_when_fixture_missing(self):
        """synthetic_fixture: true，显式指向不存在的宿主目录 → exit 2。"""
        proc = self._run_shell(
            {"ELECTRONIC_TEXT_FIXTURE_DIR": str(self.base / "absent_dir")}
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("SUMMARY pass=0 fail=0 blocked=1", proc.stdout)

    def test_shell_script_exits_0_when_fixture_valid(self):
        """synthetic_fixture: true，合成宿主有效 → exit 0 且 fail=0。"""
        host = _build_synthetic_host(self.base / "valid_host")
        proc = self._run_shell({"ELECTRONIC_TEXT_FIXTURE_DIR": str(host)})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("fail=0 blocked=0", proc.stdout.splitlines()[-1])

    def test_shell_script_handles_environment_variable_override(self):
        """synthetic_fixture: true，ELECTRONIC_TEXT_FIXTURE_DIR 覆盖生效（默认宿主不存在）。"""
        host = _build_synthetic_host(self.base / "override_host")
        proc = self._run_shell({"ELECTRONIC_TEXT_FIXTURE_DIR": str(host)})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PASS zero_network", proc.stdout)

        proc_missing = self._run_shell(
            {"ELECTRONIC_TEXT_FIXTURE_DIR": str(self.base / "override_absent")}
        )
        self.assertEqual(proc_missing.returncode, 2)

    def test_shell_default_host_is_not_ocr_mini_ed01(self):
        """第 94 条 D2：默认宿主不得回落到 OCR 路线的 mini_ed01（沙箱内 mini_ed01 存在）。"""
        dest = self._sandbox("#!/bin/sh\necho 'PASS fixture_host 伪造'\nexit 0\n", electronic_host=False)
        proc = self._run_shell(script=dest)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("BLOCKED m3_coverage 前置缺失: 电子文本验收宿主不存在", proc.stdout)
        self.assertNotIn("fixture_host", proc.stdout)
        self.assertNotIn("SUMMARY pass=8", proc.stdout)

    def test_shell_no_silent_pass_on_empty_output(self):
        """第 94 条 D3：入口退出 0 但零输出 → 脚本不得返回 0。"""
        dest = self._sandbox("#!/bin/sh\nexit 0\n", electronic_host=True)
        proc = self._run_shell(script=dest)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("SUMMARY", proc.stdout)

    def test_shell_no_silent_pass_on_nonzero_rc(self):
        """第 94 条 D3：入口非零退出（即便输出一行 PASS）→ 脚本不得返回 0。"""
        dest = self._sandbox(
            '#!/bin/sh\necho "PASS host_source 伪造的绿灯"\nexit 7\n', electronic_host=True
        )
        proc = self._run_shell(script=dest)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
