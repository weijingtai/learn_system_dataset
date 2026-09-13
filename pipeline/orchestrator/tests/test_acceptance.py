"""ACT impl-08/07：§20.1 验收判定的单元测试（规格 §19.0/§20.1/§22.3）。

先写本文件，运行 `.venv/bin/python -m unittest discover -s pipeline/orchestrator/tests -t .`
取得 ImportError 全红（Red），再实现 `pipeline/orchestrator/acceptance.py`，
最后新建 `openspec/acceptance/orchestrator-gate.sh`。
"""

import contextlib
import functools
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.ledger import ids
from pipeline.orchestrator.module import StepContext
from pipeline.orchestrator.stubs import StubModule

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
ASSET_ROOT = REPO_ROOT / "ocr" / "data_work" / "sanche_pages"
REGISTRY_PATH = REPO_ROOT / "pipeline" / "contract_registry" / "registry.yaml"
GATE_SCRIPT = REPO_ROOT / "openspec" / "acceptance" / "orchestrator-gate.sh"

BLOCKED_M1_M6 = (
    "BLOCKED registered_modules_m1_m6 前置缺失: M4 Knowledge Extraction；"
    "Local Orchestrator 首切片已串联 m1–m3、m5 Gate，m4/m6 未登记生产 Module"
)


class _ServicePort:
    """测试用：把直连 LedgerService 包成端口。"""

    def __init__(self, service):
        self._service = service

    def read_object(self, sha256):
        return self._service.objects.get(sha256)

    def __getattr__(self, name):
        return getattr(self._service, name)


def _finalize(port, request, outcome):
    step = request["step_run_id"]
    current = port.get_step_run(step)["status_version"]
    if outcome["status"] == "succeeded":
        port.finish_step_run(
            step,
            {
                "schema_version": "1.0.0",
                "processing_run_id": request["processing_run_id"],
                "step_run_id": step,
                "status_version": current + 1,
                "status": "succeeded",
                "output_artifact_ids": list(outcome["output_artifact_ids"]),
                "validation_report_ids": list(outcome["validation_report_ids"]),
                "log_artifact_ids": list(outcome["log_artifact_ids"]),
                "failure_artifact_ids": [],
            },
        )
    else:
        port.fail_step_run(step, outcome["failure_artifact_ids"], "test finalize")


def fake_run_m3_without_m2_inputs(service, edition_part_id, **kwargs):
    """假 m3 legacy 入口：冻结输入只含 m1 manifest，其余照常封存合法 StagePackage。"""
    from pipeline.corpus_compiler.inputs import resolve_m3_inputs

    inputs = resolve_m3_inputs(service, edition_part_id)
    processing_run_id = inputs["processing_run_id"]
    technique_id = inputs["technique_id"]
    manifest_revision_id = inputs["manifest_revision_id"]
    port = _ServicePort(service)
    stub = StubModule("m3", module_id="fake.m3", consumes_from=None)
    configuration = {"stage": "m3", "module_id": "fake.m3", "tasks": ["t1", "t2"]}
    _artifact_id, config_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        json.dumps(configuration, sort_keys=True).encode("utf-8"),
        producer_module="tests",
        producer_version="1.0",
    )
    request = {
        "schema_version": "1.0.0",
        "processing_run_id": processing_run_id,
        "step_run_id": ids.new_id("step_run_id"),
        "input_artifact_ids": [manifest_revision_id],
        "technique_profile_id": technique_id,
        "configuration_artifact_id": config_revision_id,
    }
    service.begin_step_run(request)
    outcome = stub.execute(
        port,
        request,
        StepContext(
            mode="fresh",
            edition_part_id=edition_part_id,
            stage="m3",
            module_id="fake.m3",
        ),
    )
    _finalize(port, request, outcome)
    return {"step_run_id": request["step_run_id"], "processing_run_id": processing_run_id}


def run_acceptance(args):
    from pipeline.orchestrator import acceptance

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = acceptance.main(args)
    return code, buffer.getvalue()


@functools.lru_cache(maxsize=1)
def default_run():
    return run_acceptance(
        ["--fixture", str(FIXTURE_DIR), "--asset-root", str(ASSET_ROOT)]
    )


def _lines(output):
    return output.strip().splitlines()


def _write_registry(mutator, directory):
    doc = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    mutator(doc)
    path = Path(directory) / "registry.yaml"
    path.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


class TestAcceptanceVerdicts(unittest.TestCase):
    """覆盖 BDD §8：六项判定、缺陷注入与退出码。"""

    def test_fixture_yields_five_pass_one_blocked_exit_2(self):
        code, output = default_run()
        self.assertEqual(code, 2, output)
        lines = _lines(output)
        self.assertEqual(lines[-1], "SUMMARY pass=5 fail=0 blocked=1")
        for name in (
            "gate_blocks_incomplete",
            "gate_chain_stub_m1_m6",
            "edition_conjunction",
            "recovery_via_orchestrator",
            "real_chain_mini_ed01",
        ):
            self.assertIn("PASS %s" % name, lines)
        self.assertIn(BLOCKED_M1_M6, lines)

    def test_blocked_line_exact_text_m4(self):
        _code, output = default_run()
        blocked = [line for line in _lines(output) if line.startswith("BLOCKED ")]
        self.assertEqual(blocked, [BLOCKED_M1_M6])

    def test_gate_bypass_defect_detected(self):
        from unittest import mock

        def always_passed(*args, **kwargs):
            return {"gate": "passed", "checks": {}, "stage": "x"}

        with mock.patch(
            "pipeline.orchestrator.gate.evaluate_stage_gate", always_passed
        ):
            code, output = run_acceptance(
                ["--fixture", str(FIXTURE_DIR), "--asset-root", str(ASSET_ROOT)]
            )
        self.assertEqual(code, 1, output)
        self.assertIn("FAIL gate_blocks_incomplete", output)

    def test_real_chain_detects_missing_upstream_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            def mutate(doc):
                for module in doc["modules"]:
                    if module["module_id"] == "m3.corpus_structural":
                        module["entry"] = (
                            "pipeline.orchestrator.tests.test_acceptance:"
                            "fake_run_m3_without_m2_inputs"
                        )

            registry = _write_registry(mutate, tmp)
            code, output = run_acceptance(
                [
                    "--fixture",
                    str(FIXTURE_DIR),
                    "--asset-root",
                    str(ASSET_ROOT),
                    "--registry",
                    str(registry),
                ]
            )
        self.assertEqual(code, 1, output)
        self.assertIn("FAIL real_chain_mini_ed01", output)

    def test_real_chain_reaches_m5_and_m8(self):
        code, output = default_run()
        self.assertEqual(code, 2, output)
        self.assertIn("PASS real_chain_mini_ed01", output)

        with tempfile.TemporaryDirectory() as empty_assets:
            code2, output2 = run_acceptance(
                [
                    "--fixture",
                    str(FIXTURE_DIR),
                    "--asset-root",
                    empty_assets,
                ]
            )
        self.assertEqual(code2, 2, output2)
        self.assertIn(
            "BLOCKED real_chain_mini_ed01 前置缺失: M1 Source Intake；派生页图缺失",
            output2,
        )
        self.assertNotIn("FAIL real_chain_mini_ed01", output2)

    def test_stub_registry_never_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            def mutate(doc):
                for module in doc["modules"]:
                    if module["module_id"] == "m3.corpus_structural":
                        module["kind"] = "stub"
                        module["binding"] = "step_request"
                        module["entry"] = None

            registry = _write_registry(mutate, tmp)
            code, output = run_acceptance(
                [
                    "--fixture",
                    str(FIXTURE_DIR),
                    "--asset-root",
                    str(ASSET_ROOT),
                    "--registry",
                    str(registry),
                ]
            )
        self.assertEqual(code, 1, output)
        self.assertIn("FAIL registered_modules_m1_m6", output)
        self.assertNotIn("PASS registered_modules_m1_m6", output)

    def test_prepare_failure_exits_1(self):
        from unittest import mock

        with mock.patch(
            "pipeline.ledger.fixture_ingest.ingest",
            side_effect=RuntimeError("boom"),
        ):
            code, output = run_acceptance(
                ["--fixture", str(FIXTURE_DIR), "--asset-root", str(ASSET_ROOT)]
            )
        self.assertEqual(code, 1, output)
        self.assertTrue(
            any(
                line.startswith("FAIL real_chain_mini_ed01 宿主准备失败: RuntimeError")
                for line in _lines(output)
            ),
            output,
        )

    def test_missing_fixture_exit_3(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, output = run_acceptance(["--fixture", str(Path(tmp) / "nope")])
        self.assertEqual(code, 3, output)


class TestGateShell(unittest.TestCase):
    """覆盖 BDD §8.4：orchestrator-gate.sh 的宿主校验与退出码。"""

    def _run(self, *, fixture=None, asset_root=None):
        env = dict(os.environ)
        env["LC_ALL"] = "en_US.UTF-8"
        if fixture is not None:
            env["FIXTURE_DIR"] = str(fixture)
        if asset_root is not None:
            env["FIXTURE_ASSET_ROOT"] = str(asset_root)
        return subprocess.run(
            ["bash", str(GATE_SCRIPT)],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,
        )

    def test_shell_exit_2_on_fixture(self):
        result = self._run(asset_root=ASSET_ROOT)
        self.assertEqual(result.returncode, 2, result.stderr.decode("utf-8"))
        lines = result.stdout.decode("utf-8").strip().splitlines()
        self.assertEqual(lines[-1], "SUMMARY pass=5 fail=0 blocked=1")

    def test_shell_never_trusts_copy_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy_dir = Path(tmp) / "mini_ed01"
            shutil.copytree(FIXTURE_DIR, copy_dir)
            spans = copy_dir / "spans.yaml"
            lines = spans.read_text(encoding="utf-8").rstrip().splitlines()
            spans.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
            (copy_dir / "verify.sh").write_text(
                "#!/usr/bin/env bash\necho FIXTURE OK; exit 0\n", encoding="utf-8"
            )
            result = self._run(fixture=copy_dir, asset_root=ASSET_ROOT)
        self.assertEqual(result.returncode, 1, result.stdout.decode("utf-8"))
        first = result.stdout.decode("utf-8").strip().splitlines()[0]
        self.assertTrue(first.startswith("FAIL fixture_host"), first)


if __name__ == "__main__":
    unittest.main()
