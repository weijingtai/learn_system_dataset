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

    def test_repository_yields_three_pass_two_blocked_exit_2(self):
        code, output = run_acceptance([])
        self.assertEqual(code, 2, output)
        lines = _lines(output)
        self.assertEqual(lines[-1], "SUMMARY pass=3 fail=0 blocked=2")
        for name in (
            "l0_schemas_verified",
            "registry_consistent",
            "storage_port_substitutable",
        ):
            self.assertIn("PASS %s" % name, lines)

    def test_modules_port_clean_blocked_lists_three_dirty_modules(self):
        _code, output = run_acceptance([])
        line = [
            item for item in _lines(output) if item.startswith("BLOCKED modules_port_clean")
        ][0]
        for module_id in (
            "m3.corpus_structural",
            "m5.automatic_validation",
            "m8.dataset_compilation",
        ):
            self.assertIn(module_id, line)
        for path in (
            "pipeline/corpus_compiler/",
            "pipeline/validation/",
            "pipeline/dataset_compiler/",
        ):
            self.assertIn(path, line)

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
        self.assertEqual(lines[-1], "SUMMARY pass=3 fail=0 blocked=2")


if __name__ == "__main__":
    unittest.main()
