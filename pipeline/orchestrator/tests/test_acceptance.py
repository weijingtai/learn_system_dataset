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
# OCR 宿主：仍是桩判定（gate_blocks_incomplete 等）与 TestGateShell 的宿主。
FIXTURE_DIR = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
# §20.1 的判据宿主（裁决 4）：电子文本路线，调度器在其上跑 M1→M6 全线。
TEXT_FIXTURE_DIR = (
    REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "qianyuan_ed01_text"
)
ASSET_ROOT = REPO_ROOT / "ocr" / "data_work" / "sanche_pages"
REGISTRY_PATH = REPO_ROOT / "pipeline" / "contract_registry" / "registry.yaml"
GATE_SCRIPT = REPO_ROOT / "openspec" / "acceptance" / "orchestrator-gate.sh"

# 裁决 4 后，宿主不是电子文本路线时 20.1 判据行的前缀（BLOCKED，绝不回落 mini_ed01）。
BLOCKED_NON_TEXT_HOST = (
    "BLOCKED real_chain_mini_ed01 前置缺失: M1 Source Intake；"
    "裁决 4 指定的电子文本宿主缺 source_info.yaml："
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
    """假 m3 legacy 入口：正常走 run_m3_text 编译封存，但故意只冻结 m1 产出，漏冻结 m2 产出。"""
    from pipeline.corpus_compiler import step_offset

    original_begin = service.begin_step_run
    original_record = service.record_transformation
    original_package = service.register_stage_package

    def begin_without_m2(req):
        # 故意只保留 raw_text（M1 产物），剥离 M2 产物，制造血缘缺失
        req["input_artifact_ids"] = req["input_artifact_ids"][:1]
        return original_begin(req)

    def record_without_m2(step_run_id, *args, **kw):
        if "input_revision_ids" in kw:
            kw["input_revision_ids"] = kw["input_revision_ids"][:1]
        elif len(args) >= 5:
            args = list(args)
            args[4] = args[4][:1]
        return original_record(step_run_id, *args, **kw)

    def register_without_m2(srun_id, pkg, content, **kw):
        pkg["manifest"]["input_artifacts"] = pkg["manifest"]["input_artifacts"][:1]
        pkg["lineage"]["upstream_artifacts"] = pkg["lineage"]["upstream_artifacts"][:1]
        pkg["lineage"]["transformations"][0]["input_artifact_revision_ids"] = (
            pkg["lineage"]["transformations"][0]["input_artifact_revision_ids"][:1]
        )
        content = json.dumps(pkg, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return original_package(srun_id, pkg, content, **kw)

    service.begin_step_run = begin_without_m2
    service.record_transformation = record_without_m2
    service.register_stage_package = register_without_m2
    try:
        return step_offset.run_m3_text(service, edition_part_id, **kwargs)
    finally:
        service.begin_step_run = original_begin
        service.record_transformation = original_record
        service.register_stage_package = original_package


def run_acceptance(args):
    from pipeline.orchestrator import acceptance

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = acceptance.main(args)
    return code, buffer.getvalue()


@functools.lru_cache(maxsize=1)
def default_run():
    """§20.1 的默认运行：裁决 4 的电子文本宿主（电子文本路线不读任何页图）。"""
    return run_acceptance(["--fixture", str(TEXT_FIXTURE_DIR)])


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

    def test_text_host_yields_six_pass_exit_0(self):
        """改前：宿主 mini_ed01 → 5 PASS + BLOCKED registered_modules，exit 2。
        改后（裁决 4）：电子文本宿主 → 六项全 PASS（含 M1→M6 全线），exit 0。"""
        code, output = default_run()
        self.assertEqual(code, 0, output)
        lines = _lines(output)
        self.assertEqual(lines[-1], "SUMMARY pass=6 fail=0 blocked=0")
        for name in (
            "gate_blocks_incomplete",
            "gate_chain_stub_m1_m6",
            "edition_conjunction",
            "recovery_via_orchestrator",
            "real_chain_mini_ed01",
            "registered_modules_m1_m6",
        ):
            self.assertTrue(
                any(line == "PASS %s" % name or line.startswith("PASS %s " % name) for line in lines),
                "PASS %s not found in lines: %r" % (name, lines),
            )
        self.assertNotIn("BLOCKED ", output)
        self.assertNotIn("FAIL ", output)

    def test_blocked_line_is_exactly_the_text_chain_on_a_non_text_host(self):
        """改前：断言 mini_ed01 上唯一的 BLOCKED 行是 registered_modules（首切片未登记 m4/m6）。
        改后（裁决 4）：m4/m6 已登记，而 OCR 宿主不是 20.1 宿主 → 唯一 BLOCKED 行是
        real_chain 的「宿主不是电子文本路线」，其余全 PASS、无 FAIL。"""
        code, output = run_acceptance(["--fixture", str(FIXTURE_DIR)])
        self.assertEqual(code, 2, output)
        blocked = [line for line in _lines(output) if line.startswith("BLOCKED ")]
        self.assertEqual(len(blocked), 1, output)
        self.assertTrue(blocked[0].startswith(BLOCKED_NON_TEXT_HOST), blocked[0])
        self.assertNotIn("FAIL ", output)

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
        """改前：在旧 OCR 宿主 mini_ed01 上注入假 M3（漏 M2 输入），断言 real_chain 报 FAIL。
        改后（裁决 4）：在裁决 4 电子文本宿主上注入假 M3（仅冻结 M1 raw_text，漏冻结 M2 产出），
        上游血缘缺失导致链路阻断并判定为 FAIL，exit 1。"""
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
                    str(TEXT_FIXTURE_DIR),
                    "--registry",
                    str(registry),
                ]
            )
        self.assertEqual(code, 1, output)
        self.assertIn("FAIL real_chain_mini_ed01", output)

    def test_real_chain_reaches_m6(self):
        """改前（test_real_chain_reaches_m5_and_m8）：default_run exit 2，断言旧链达到 m5/m8 且空页图报 BLOCKED。
        改后（裁决 4）：default_run exit 0 且 real_chain PASS（M1→M6 全线）；
        当电子文本宿主缺失前置素材（如 M4 提交件）时，正当判定为 BLOCKED，exit 2 且无 FAIL。"""
        code, output = default_run()
        self.assertEqual(code, 0, output)
        self.assertTrue(
            any(
                line.startswith("PASS real_chain_mini_ed01")
                for line in _lines(output)
            ),
            output,
        )

        with tempfile.TemporaryDirectory() as tmp:
            broken_host = Path(tmp) / "broken_text_host"
            shutil.copytree(TEXT_FIXTURE_DIR, broken_host)
            (broken_host / "m4" / "submission_assertion_a.yaml").unlink()
            code2, output2 = run_acceptance(["--fixture", str(broken_host)])
        self.assertEqual(code2, 2, output2)
        self.assertIn(
            "BLOCKED real_chain_mini_ed01 前置缺失: M4 Knowledge Extraction；宿主 M4 提交件缺失：submission_assertion_a.yaml",
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
            "pipeline.orchestrator.acceptance._drive_text_chain",
            side_effect=RuntimeError("boom"),
        ):
            code, output = run_acceptance(["--fixture", str(TEXT_FIXTURE_DIR)])
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
