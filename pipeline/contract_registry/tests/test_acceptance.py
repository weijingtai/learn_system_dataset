"""ACT impl-08/08：§20.10 验收判定的单元测试（规格 §19.0/§20 第 10 条）。

先写本文件，运行 `.venv/bin/python -m unittest discover -s pipeline/contract_registry/tests -t .`
取得 ImportError 全红（Red），再实现 `pipeline/orchestrator/suites.py` 与
`pipeline/contract_registry/acceptance.py`，最后新建 `openspec/acceptance/contract-registry.sh`。
"""

import contextlib
import copy
import hashlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "pipeline" / "contract_registry" / "registry.yaml"
SCRIPT = REPO_ROOT / "openspec" / "acceptance" / "contract-registry.sh"


def run_acceptance(args):
    from pipeline.contract_registry import acceptance

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = acceptance.main(args)
    return code, buffer.getvalue()


def _lines(output):
    return output.strip().splitlines()


class TestContractRegistryAcceptance(unittest.TestCase):
    """覆盖 BDD §9：五项判定、缺陷注入与退出码。"""

    def test_repository_yields_four_pass_one_blocked_exit_2(self):
        # T03 后 modules_port_clean 转 PASS；other_ports_adapters 仍 BLOCKED（TODO.md T03b）
        code, output = run_acceptance([])
        self.assertEqual(code, 2, output)
        lines = _lines(output)
        self.assertEqual(lines[-1], "SUMMARY pass=4 fail=0 blocked=1")
        for name in (
            "l0_schemas_verified",
            "registry_consistent",
            "storage_port_substitutable",
            "modules_port_clean",
        ):
            self.assertIn("PASS %s" % name, lines)

    def test_modules_port_clean_passes_after_t03(self):
        # TODO.md T03（2026-09-23）：M3 30 处、M5 15 处、M8 18 处走后门全部改为经 LedgerPort
        _code, output = run_acceptance([])
        self.assertIn("PASS modules_port_clean", _lines(output))

    def test_scanner_still_catches_backdoor_code_and_comments(self):
        # 上一条改成断言 PASS 后，须另证检测器本身仍灵敏：代码与注释里的 .store / .objects 都要报出
        from pipeline.contract_registry.acceptance import scan_ledger_internals

        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "fake_module"
            (pkg / "tests").mkdir(parents=True)
            (pkg / "step.py").write_text(
                "def f(service):\n"
                "    return service.store.conn.execute('SELECT 1')\n"
                "def g(reader, sha):\n"
                "    # 退回 reader.objects.get\n"
                "    return reader.read_object(sha)\n",
                encoding="utf-8",
            )
            (pkg / "tests" / "test_x.py").write_text("x.store.conn\n", encoding="utf-8")
            hits = scan_ledger_internals([pkg])
        self.assertEqual([line for _path, line in hits], [2, 4], "代码与注释都要命中；tests/ 下不扫")

    def test_t03c_packages_have_no_ledger_internals(self):
        # TODO.md T03c（2026-09-24）：M1/M2/M4/M6/M7 五个包 111 处走后门全部改为经 LedgerPort；
        # 这五个包尚未全部登记为生产模块，modules_port_clean 扫不到它们，由本用例单独守住
        from pipeline.contract_registry.acceptance import scan_ledger_internals

        for pkg in ("intake", "digitization", "knowledge_extraction", "assembly", "review"):
            with self.subTest(pkg=pkg):
                self.assertEqual(scan_ledger_internals([REPO_ROOT / "pipeline" / pkg]), [], pkg)

    def test_other_ports_blocked_counts_text(self):
        _code, output = run_acceptance([])
        line = [
            item for item in _lines(output) if item.startswith("BLOCKED other_ports_adapters")
        ][0]
        self.assertIn("ocr=0, model=0, index=0", line)

    def test_tampered_registry_hash_fails_exit_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
            doc["schemas"][0]["sha256"] = "0" * 64
            path = Path(tmp) / "registry.yaml"
            path.write_text(
                yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            code, output = run_acceptance(["--registry", str(path)])
        self.assertEqual(code, 1, output)
        self.assertIn("FAIL registry_consistent", output)

    def test_storage_outcome_divergence_fails(self):
        from pipeline.contract_registry import conformance

        real = conformance.normalize_outcome
        state = {"calls": 0}

        def divergent(port, processing_run_id):
            outcome = real(port, processing_run_id)
            state["calls"] += 1
            if state["calls"] >= 2 and outcome["steps"]:
                outcome["steps"][0]["event_types"] = list(
                    outcome["steps"][0]["event_types"]
                ) + ["extra"]
            return outcome

        with mock.patch(
            "pipeline.contract_registry.conformance.normalize_outcome", divergent
        ):
            code, output = run_acceptance([])
        self.assertEqual(code, 1, output)
        self.assertIn("FAIL storage_port_substitutable", output)

    def test_suite_covers_human_resume_path(self):
        from pipeline.contract_registry.ports import DirectLedgerAdapter
        from pipeline.contract_registry.conformance import normalize_outcome
        from pipeline.orchestrator.suites import stub_edition_suite

        with tempfile.TemporaryDirectory() as tmp:
            adapter = DirectLedgerAdapter(Path(tmp) / "ledger")
            self.addCleanup(adapter.close)
            processing_run_id = stub_edition_suite(adapter)
            outcome = normalize_outcome(adapter, processing_run_id)
        m2 = [step for step in outcome["steps"] if step["stage"] == "m2"][0]
        events = m2["event_types"]
        positions = [
            events.index(name)
            for name in ("await_human", "human_event", "resume")
        ]
        self.assertEqual(positions, sorted(positions))

    def test_orchestrator_leak_is_fail_not_blocked(self):
        from pipeline.contract_registry import acceptance

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "orchestrator"
            root.mkdir()
            (root / "leaky.py").write_text("svc.store.conn\n", encoding="utf-8")
            with mock.patch.object(acceptance, "ORCHESTRATOR_SCAN_ROOTS", [root]):
                code, output = run_acceptance([])
        self.assertEqual(code, 1, output)
        self.assertIn("FAIL modules_port_clean", output)
        self.assertNotIn("BLOCKED modules_port_clean", output)

    def test_scan_excludes_tests_directories(self):
        from pipeline.contract_registry.acceptance import scan_ledger_internals

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            (root / "tests" / "helper.py").write_text("x.store\n", encoding="utf-8")
            (root / "clean.py").write_text("x = 1\n", encoding="utf-8")
            self.assertEqual(scan_ledger_internals([root]), [])

    def test_missing_dependency_exit_3(self):
        from pipeline.contract_registry import acceptance

        with mock.patch.object(acceptance, "_dependencies_available", lambda: False):
            code, _output = run_acceptance([])
        self.assertEqual(code, 3)

    def test_shell_exit_2(self):
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=str(REPO_ROOT),
            env={**os.environ, "LC_ALL": "en_US.UTF-8"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,
        )
        self.assertEqual(result.returncode, 2, result.stderr.decode("utf-8"))
        lines = result.stdout.decode("utf-8").strip().splitlines()
        self.assertEqual(lines[-1], "SUMMARY pass=4 fail=0 blocked=1")


if __name__ == "__main__":
    unittest.main()
