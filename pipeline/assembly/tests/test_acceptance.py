"""M7 创世验收测试（act/g0-05、g0-06，spec §19.0）。"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]

#: m7-assembler 全部判据数（ACT 27 起 17 条）。
TOTAL_VERDICTS = 17
#: 引擎缺口导致、如实 BLOCKED 的判据；I 波（ACT 29/30）合并后清空。
KNOWN_GAP_BLOCKED = ("edition_collation",)
_REAL_LEDGER_DIR = ROOT / "var" / "ledgers" / "qianyuan_w8"


def expected_blocked():
    """按宿主实情算出应 BLOCKED 的判据：已知引擎缺口 + 无真书账本时的真书判据。

    CHARTER §27：不许写死计数——没有真书账本的机器上 upstream_m6_real_book 如实 BLOCKED，
    计数随之变化；写死 16/1 会让这类机器上的用例误红。
    """
    names = set(KNOWN_GAP_BLOCKED)
    if not _REAL_LEDGER_DIR.is_dir():
        names.add("upstream_m6_real_book")
    return names


def expected_summary():
    blocked = len(expected_blocked())
    return "SUMMARY pass=%d fail=0 blocked=%d" % (TOTAL_VERDICTS - blocked, blocked)


def expected_exit_code():
    return 2 if expected_blocked() else 0


class TestAcceptance(unittest.TestCase):
    def test_genesis_acceptance_summary_and_exit_2(self):
        from pipeline.assembly import acceptance

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = acceptance.main([])
        out = buf.getvalue()
        blocked = len(expected_blocked())
        self.assertEqual(code, expected_exit_code())
        self.assertIn(expected_summary(), out)
        self.assertEqual(out.count("PASS "), TOTAL_VERDICTS - blocked)
        self.assertEqual(out.count("BLOCKED "), blocked)
        self.assertEqual(out.count("FAIL "), 0)

    def test_blocked_lines_exact_text(self):
        """五条原 BLOCKED 已成真实判定；唯一仍 BLOCKED 的是引擎缺口那条，理由不得笼统。"""
        from pipeline.assembly import acceptance

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = acceptance.main([])
        out = buf.getvalue()
        if "edition_collation" in KNOWN_GAP_BLOCKED:
            self.assertIn(
                "BLOCKED edition_collation 多版次对勘（缺文/增文/异文）引擎缺口，见 CHARTER §19",
                out,
            )
        names = ["incremental_multi_edition", "identity_delta", "rework_replacement", "run_all_20_5"]
        if _REAL_LEDGER_DIR.is_dir():
            names.append("upstream_m6_real_book")
        else:
            # 无真书账本时必须如实 BLOCKED（宿主缺失），不许 PASS
            self.assertIn("BLOCKED upstream_m6_real_book 宿主缺失", out)
        for name in names:
            self.assertNotIn("BLOCKED %s " % name, out, "%s 不得再由写死的理由决定" % name)
        self.assertNotIn("未实现", out)

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
            proc.returncode, expected_exit_code(), f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
        last_line = proc.stdout.strip().splitlines()[-1]
        self.assertEqual(last_line, expected_summary())

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
            # 精确匹配判据名：startswith 会误命中 "BLOCKED upstream_m6_real_book"（CHARTER §27）
            if line.split()[:2] == ["BLOCKED", "upstream_m6_real"]:
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

    def test_shell_summary_pass_16_fail_0_blocked_1(self):
        shell_script = ROOT / "openspec" / "acceptance" / "m7-assembler.sh"
        proc = subprocess.run(
            ["bash", str(shell_script)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode, expected_exit_code(), f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
        last_line = proc.stdout.strip().splitlines()[-1]
        self.assertEqual(last_line, expected_summary())

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


#: G2 波（ACT 27）五条原写死 BLOCKED 的判据名
G2_FIVE = (
    "incremental_multi_edition",
    "edition_collation",
    "identity_delta",
    "rework_replacement",
    "run_all_20_5",
)

RELEASE_FIXTURE = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"
REAL_LEDGER = ROOT / "var" / "ledgers" / "qianyuan_w8"


def run_acceptance_main():
    from pipeline.assembly import acceptance

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = acceptance.main([])
    return code, buf.getvalue()


def verdict_line(out, name):
    for line in out.splitlines():
        parts = line.split()
        if parts[:2] and parts[0] in ("PASS", "FAIL", "BLOCKED") and len(parts) > 1:
            if parts[1] == name:
                return line
    return None


def tampered_release_fixture(tmp_dir, rel_path, mutate):
    """把 mini_release01 整份拷到临时目录并改坏其中一个金标（负向对照用）。"""
    target = Path(tmp_dir) / "mini_release01"
    shutil.copytree(RELEASE_FIXTURE, target)
    path = target / rel_path
    doc = json.loads(path.read_text(encoding="utf-8"))
    mutate(doc)
    path.write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return target


def clone_run_all_with_stub(tmp_dir, m7_exit_code):
    """在假仓库里放**真实**的 run_all.sh 与一个按给定退出码退出的 m7-assembler.sh 桩。"""
    acc_dir = Path(tmp_dir) / "openspec" / "acceptance"
    acc_dir.mkdir(parents=True)
    real = (ROOT / "openspec" / "acceptance" / "run_all.sh").read_text(encoding="utf-8")
    (acc_dir / "run_all.sh").write_text(real, encoding="utf-8")
    stub = acc_dir / "m7-assembler.sh"
    stub.write_text(
        "#!/usr/bin/env bash\necho 'BLOCKED stub_check 桩判定'\necho 'SUMMARY pass=0 fail=0 blocked=1'\nexit %d\n"
        % m7_exit_code,
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return acc_dir / "run_all.sh"


class TestAcceptanceIncremental(unittest.TestCase):
    """ACT 27（G2）：五条写死的 BLOCKED 改为真实判定 + 真书判据 + run_all 20.5 接线。"""

    # ------------------------------------------------------------ 具名用例 1
    def test_no_verdict_detail_says_not_implemented_when_implemented(self):
        """五条判据都已实现，输出里不得再出现「未实现」这种笼统理由。"""
        code, out = run_acceptance_main()
        for name in G2_FIVE:
            line = verdict_line(out, name)
            self.assertIsNotNone(line, "%s 必须有一条判定行" % name)
            self.assertNotIn("未实现", line, "%s 的理由不得是笼统的「未实现」" % name)
        self.assertNotIn("未实现", out)
        self.assertEqual(verdict_line(out, "upstream_m6_real").split()[0], "PASS")

    # ------------------------------------------------------------ 具名用例 2
    def test_incremental_multi_edition_judged_from_real_run(self):
        """r1 → ed99 增量实跑：succeeded + 增量 Gate 全过 + 产出与 r2 金标（逐字节/除 meta）相同。"""
        code, out = run_acceptance_main()
        self.assertEqual(verdict_line(out, "incremental_multi_edition").split()[0], "PASS")

        # 负向对照：金标被改坏，本判据必须转红（写死 PASS 会被这一条抓住）
        tmp = tempfile.mkdtemp(prefix="test_acc_inc_")
        self.addCleanup(shutil.rmtree, tmp, True)
        fake = tampered_release_fixture(
            tmp, "expected/snapshot_r2.json", lambda doc: doc.__setitem__("tampered", True)
        )
        from pipeline.assembly import acceptance

        with mock.patch.object(acceptance, "RELEASE_FIXTURE", fake):
            code2, out2 = run_acceptance_main()
        line = verdict_line(out2, "incremental_multi_edition")
        self.assertEqual(line.split()[0], "FAIL", line)
        self.assertEqual(code2, 1)

    # ------------------------------------------------------------ 具名用例 3
    def test_edition_collation_judged_from_real_run(self):
        """对齐关系正确 + 不可比单元无对勘关系 → 通过；缺文/增文/异文无生产者 → BLOCKED（非 PASS）。"""
        code, out = run_acceptance_main()
        line = verdict_line(out, "edition_collation")
        self.assertEqual(line.split()[0], "BLOCKED", line)
        self.assertIn("缺文/增文/异文", line)
        self.assertIn("CHARTER §19", line)

        # 负向对照：把对齐关系从金标里删掉，已实现的那半部分必须转红
        tmp = tempfile.mkdtemp(prefix="test_acc_coll_")
        self.addCleanup(shutil.rmtree, tmp, True)

        def drop_alignment(doc):
            doc["relations"] = [
                rel for rel in doc["relations"] if rel["relation_kind"] != "alignment"
            ]

        fake = tampered_release_fixture(tmp, "expected/snapshot_r2.json", drop_alignment)
        from pipeline.assembly import acceptance

        with mock.patch.object(acceptance, "RELEASE_FIXTURE", fake):
            code2, out2 = run_acceptance_main()
        line2 = verdict_line(out2, "edition_collation")
        self.assertEqual(line2.split()[0], "FAIL", line2)

    # ------------------------------------------------------------ 具名用例 4
    def test_identity_delta_judged_from_real_run(self):
        """r2 → ed01r2 实跑的 identity_delta 与金标一致，且每条理由引用都在本轮提案键里。"""
        code, out = run_acceptance_main()
        self.assertEqual(verdict_line(out, "identity_delta").split()[0], "PASS")

        tmp = tempfile.mkdtemp(prefix="test_acc_delta_")
        self.addCleanup(shutil.rmtree, tmp, True)
        fake = tampered_release_fixture(
            tmp,
            "expected/identity_delta_r3.json",
            lambda doc: doc["entries"][0].__setitem__("change_type", "split"),
        )
        from pipeline.assembly import acceptance

        with mock.patch.object(acceptance, "RELEASE_FIXTURE", fake):
            code2, out2 = run_acceptance_main()
        line = verdict_line(out2, "identity_delta")
        self.assertEqual(line.split()[0], "FAIL", line)

    # ------------------------------------------------------------ 具名用例 5
    def test_rework_replacement_judged_from_real_run(self):
        """ed01r2 按 (source_id, edition_part_ids) 识别为替换；退役/沿用/产出都与金标一致。"""
        code, out = run_acceptance_main()
        self.assertEqual(verdict_line(out, "rework_replacement").split()[0], "PASS")

        tmp = tempfile.mkdtemp(prefix="test_acc_rework_")
        self.addCleanup(shutil.rmtree, tmp, True)
        fake = tampered_release_fixture(
            tmp, "expected/snapshot_r3.json", lambda doc: doc.__setitem__("tampered", True)
        )
        from pipeline.assembly import acceptance

        with mock.patch.object(acceptance, "RELEASE_FIXTURE", fake):
            code2, out2 = run_acceptance_main()
        line = verdict_line(out2, "rework_replacement")
        self.assertEqual(line.split()[0], "FAIL", line)

    # ------------------------------------------------------------ 具名用例 6
    def test_upstream_m6_real_detail_says_synthetic_stub(self):
        """upstream_m6_real 的名字不改，但 detail 必须写明输入是合成桩、非真书。"""
        code, out = run_acceptance_main()
        note = [
            line for line in out.splitlines() if line.startswith("NOTE upstream_m6_real ")
        ]
        self.assertEqual(len(note), 1, "必须恰有一条 upstream_m6_real 的 NOTE 行")
        for token in ("合成桩", "upstream_stub", "非真书"):
            self.assertIn(token, note[0])

    # ------------------------------------------------------------ 具名用例 7
    def test_upstream_m6_real_book_blocked_without_ledger(self):
        """无真书账本时必须是 BLOCKED（不许判 PASS），且理由写明宿主缺失。"""
        from pipeline.assembly import acceptance

        missing = Path(tempfile.mkdtemp(prefix="test_acc_noledger_")) / "absent"
        self.addCleanup(shutil.rmtree, missing.parent, True)
        with mock.patch.object(acceptance, "REAL_LEDGER_DIR", missing):
            code, out = run_acceptance_main()
        line = verdict_line(out, "upstream_m6_real_book")
        self.assertIsNotNone(line)
        self.assertTrue(line.startswith("BLOCKED "), line)
        self.assertIn("宿主缺失", line)
        self.assertIn("无真书账本", line)
        self.assertNotEqual(verdict_line(out, "upstream_m6_real_book").split()[0], "PASS")

    # ------------------------------------------------------------ 具名用例 8
    def test_run_all_20_5_maps_exit_code_not_hardcoded(self):
        """run_all.sh 的 20.5 必须按 m7-assembler.sh 的真实退出码映射，不许写死。"""
        expectations = {0: "PASS", 1: "FAIL", 2: "BLOCKED", 3: "BLOCKED"}
        for rc, expected in expectations.items():
            tmp = tempfile.mkdtemp(prefix="test_acc_runall_")
            self.addCleanup(shutil.rmtree, tmp, True)
            script = clone_run_all_with_stub(tmp, rc)
            proc = subprocess.run(
                ["bash", str(script), "20.5"],
                cwd=tmp,
                capture_output=True,
                text=True,
            )
            line = [
                l for l in proc.stdout.splitlines()
                if l.startswith(("PASS  ", "FAIL  ", "BLOCKED  ")) and "20.5" in l
            ]
            self.assertEqual(len(line), 1, proc.stdout)
            self.assertTrue(
                line[0].startswith(expected),
                "m7-assembler 退出码 %d 必须映射为 %s，实际: %s" % (rc, expected, line[0]),
            )

    # ------------------------------------------------------------ 真书账本存在时的完整判定
    def test_upstream_m6_real_book_passes_on_this_host(self):
        """本机有 var/ledgers/qianyuan_w8 时，真书第二轮必须 succeeded 且增量 Gate 全过。"""
        if not (REAL_LEDGER / "ledger.sqlite").exists():
            self.skipTest("本机无真书账本")
        code, out = run_acceptance_main()
        line = verdict_line(out, "upstream_m6_real_book")
        self.assertTrue(line.startswith("PASS "), line)
        # 正本只读：判据自己会核对 mtime/size，这里再独立核一遍
        stat = (REAL_LEDGER / "ledger.sqlite").stat()
        self.assertGreater(stat.st_size, 0)


if __name__ == "__main__":
    unittest.main()
