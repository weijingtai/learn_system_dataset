"""ACT impl-08/03：独立 Stage Gate 的单元测试（规格 §6.1 :149、§20.1 :937）。

先写本文件，全红后再实现 `pipeline/orchestrator/gate.py`。
测试内自建 StepRun（begin → execute → finish/fail/await_human），不 import runner/edition_run。
"""

import ast
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.contract_registry.catalog import Registry, load_registry
from pipeline.contract_registry.ports import DirectLedgerAdapter
from pipeline.ledger.fixture_ingest import ingest
from pipeline.ledger.service import LedgerService
from pipeline.orchestrator.gate import (
    GATE_CHECKS,
    effective_step_runs,
    evaluate_stage_gate,
    succeeded_step_runs,
)
from pipeline.orchestrator.module import StepContext
from pipeline.orchestrator.stubs import StubModule
from pipeline.orchestrator.tests.scaffold import (
    REPO_ROOT,
    LedgerTestCase,
    make_step_request,
)

REGISTRY_PATH = REPO_ROOT / "pipeline" / "contract_registry" / "registry.yaml"


def _finalize(adapter, request, outcome):
    """按 StepOutcome 把 StepRun 推到终态（或 awaiting_human），返回 token 或 None。"""
    step_run_id = request["step_run_id"]
    base = {
        "schema_version": "1.0.0",
        "processing_run_id": request["processing_run_id"],
        "step_run_id": step_run_id,
    }
    current = adapter.get_step_run(step_run_id)["status_version"]
    if outcome["status"] == "succeeded":
        adapter.finish_step_run(
            step_run_id,
            dict(
                base,
                status_version=current + 1,
                status="succeeded",
                output_artifact_ids=list(outcome["output_artifact_ids"]),
                validation_report_ids=list(outcome["validation_report_ids"]),
                log_artifact_ids=list(outcome["log_artifact_ids"]),
                failure_artifact_ids=[],
            ),
        )
        return None
    if outcome["status"] == "failed":
        adapter.fail_step_run(step_run_id, outcome["failure_artifact_ids"], "stub failed")
        return None
    return adapter.await_human(step_run_id, outcome["pending_queue_artifact_ids"])


class NonMappingPackageModule(StubModule):
    """登记 schema 合法的 StagePackage，但把修订字节写成非映射内容（裁定 57 负例）。"""

    def _register_package(self, port, request, outputs, payloads, report_revision, log_revision):
        class _SwapPort:
            def __init__(self, inner):
                self._inner = inner

            def register_stage_package(self, step_run_id, package, data, **kwargs):
                return self._inner.register_stage_package(
                    step_run_id, package, b"- not a mapping\n", **kwargs
                )

            def __getattr__(self, name):
                return getattr(self._inner, name)

        return super()._register_package(
            _SwapPort(port), request, outputs, payloads, report_revision, log_revision
        )


class GateTestCase(LedgerTestCase):
    """公共脚手架：桩登记表与一次桩阶段执行。"""

    def registry_with(self, stubs):
        doc = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
        doc["modules"] = [stub.descriptor() for stub in stubs]
        return Registry.from_dict(doc, repo_root=REPO_ROOT, allow_stub=True)

    def handle(self, processing_run_id, edition_part_id):
        return {
            "processing_run_id": processing_run_id,
            "edition_part_id": edition_part_id,
            "technique_id": "qizheng",
        }

    def execute_stub(
        self,
        stub,
        processing_run_id,
        edition_part_id,
        *,
        upstream=None,
        input_override=None,
        finish=True,
        mode="fresh",
        recovery_plan=None,
        human_event_revision_ids=(),
    ):
        configuration_revision_id = self.seed_configuration(
            processing_run_id, stage=stub.stage, module_id=stub.module_id, tasks=stub.tasks
        )
        planned = stub.plan(
            self.adapter,
            edition_part_id=edition_part_id,
            processing_run_id=processing_run_id,
            technique_id="qizheng",
            upstream=upstream or {},
        )
        input_ids = (
            planned["input_artifact_ids"]
            if input_override is None
            else input_override
        )
        request = make_step_request(
            processing_run_id, configuration_revision_id, input_artifact_ids=input_ids
        )
        self.adapter.begin_step_run(request)
        context = StepContext(
            mode=mode,
            edition_part_id=edition_part_id,
            stage=stub.stage,
            module_id=stub.module_id,
            human_event_revision_ids=tuple(human_event_revision_ids),
            recovery_plan=recovery_plan,
        )
        outcome = stub.execute(self.adapter, request, context)
        token = _finalize(self.adapter, request, outcome) if finish else None
        return request, outcome, token

    @staticmethod
    def parsed_run(adapter, step_run_id):
        row = adapter.get_step_run(step_run_id)
        parsed = dict(row)
        parsed["result"] = json.loads(row["result_json"]) if row["result_json"] else None
        return parsed


class TestStageGate(GateTestCase):
    """覆盖 BDD §4：八项检查的通过/阻断与只读性。"""

    def test_passed_on_successful_stub_m1(self):
        registry = self.registry_with([StubModule("m1")])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(StubModule("m1"), processing_run_id, edition_part_id)
        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m1"
        )
        self.assertEqual(gate["gate"], "passed")
        self.assertEqual(list(gate["checks"]), list(GATE_CHECKS))
        self.assertTrue(all(check["ok"] for check in gate["checks"].values()))

    def test_blocked_when_no_step_run(self):
        registry = self.registry_with([StubModule("m1")])
        processing_run_id, edition_part_id = self.start_run()
        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m1"
        )
        self.assertEqual(gate["gate"], "blocked")
        self.assertFalse(gate["checks"]["tasks_present"]["ok"])

    def test_blocked_when_failed(self):
        registry = self.registry_with([StubModule("m1", fail_on_task="t2")])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(
            StubModule("m1", fail_on_task="t2"), processing_run_id, edition_part_id
        )
        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m1"
        )
        self.assertEqual(gate["gate"], "blocked")
        self.assertFalse(gate["checks"]["all_tasks_succeeded"]["ok"])

    def test_blocked_when_awaiting_human(self):
        stub = StubModule("m2", human_queue=True)
        registry = self.registry_with([stub])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(stub, processing_run_id, edition_part_id)
        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m2"
        )
        self.assertEqual(gate["gate"], "blocked")
        self.assertFalse(gate["checks"]["all_tasks_succeeded"]["ok"])
        self.assertFalse(gate["checks"]["no_pending_work"]["ok"])

    def test_blocked_when_stage_package_missing(self):
        stub = StubModule("m1", stage_package_mode="missing")
        registry = self.registry_with([stub])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(stub, processing_run_id, edition_part_id)
        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m1"
        )
        self.assertEqual(gate["gate"], "blocked")
        self.assertFalse(gate["checks"]["stage_package_valid"]["ok"])

    def test_blocked_when_stage_package_wrong_stage(self):
        stub = StubModule("m1", stage_package_mode="wrong_stage")
        registry = self.registry_with([stub])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(stub, processing_run_id, edition_part_id)
        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m1"
        )
        self.assertEqual(gate["gate"], "blocked")
        self.assertFalse(gate["checks"]["stage_package_valid"]["ok"])

    def test_stage_package_valid_rejects_non_mapping_content(self):
        stub = NonMappingPackageModule("m1")
        registry = self.registry_with([stub])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(stub, processing_run_id, edition_part_id)
        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m1"
        )
        check = gate["checks"]["stage_package_valid"]
        self.assertFalse(check["ok"])
        self.assertIn("内容不可读", check["detail"])

    def test_blocked_when_validation_not_passed(self):
        stub = StubModule("m1", validation_passed=False)
        registry = self.registry_with([stub])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(stub, processing_run_id, edition_part_id)
        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m1"
        )
        self.assertEqual(gate["gate"], "blocked")
        self.assertFalse(gate["checks"]["validation_passed"]["ok"])

    def test_blocked_when_stage_package_has_failures(self):
        stub = StubModule("m1", stage_package_mode="with_failures")
        registry = self.registry_with([stub])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(stub, processing_run_id, edition_part_id)
        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m1"
        )
        self.assertEqual(gate["gate"], "blocked")
        self.assertFalse(gate["checks"]["failures_zero"]["ok"])

    def test_blocked_when_produces_type_missing(self):
        stub = StubModule("m1")
        registry = self.registry_with([stub])
        registry.modules[0]["produces"].append({"artifact_type": "extra_type"})
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(stub, processing_run_id, edition_part_id)
        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m1"
        )
        self.assertEqual(gate["gate"], "blocked")
        self.assertFalse(gate["checks"]["output_contract"]["ok"])

    def test_blocked_when_checkpoint_has_pending(self):
        stub = StubModule("m1")
        registry = self.registry_with([stub])
        processing_run_id, edition_part_id = self.start_run()
        request, outcome, _ = self.execute_stub(
            stub, processing_run_id, edition_part_id, finish=False
        )
        self.adapter.write_checkpoint(
            request["step_run_id"],
            edition_part_id=edition_part_id,
            stage="m1",
            completed_tasks=[
                {
                    "task_id": "t2",
                    "artifact_revision_id": outcome["output_artifact_ids"][-1],
                    "status": "succeeded",
                    "terminal_state": None,
                }
            ],
            human_decisions=[],
            pending_queue=[{"task_id": "leftover"}],
            next_pointer="leftover",
        )
        _finalize(self.adapter, request, outcome)
        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m1"
        )
        self.assertEqual(gate["gate"], "blocked")
        self.assertFalse(gate["checks"]["no_pending_work"]["ok"])

    def test_blocked_when_upstream_output_not_frozen(self):
        stub = StubModule("m2")
        registry = self.registry_with([stub])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(stub, processing_run_id, edition_part_id, input_override=[])
        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m2"
        )
        self.assertEqual(gate["gate"], "blocked")
        self.assertFalse(gate["checks"]["upstream_lineage"]["ok"])

    def test_superseded_failed_run_ignored(self):
        registry = self.registry_with([StubModule("m1")])
        processing_run_id, edition_part_id = self.start_run()
        request, outcome, _ = self.execute_stub(
            StubModule("m1", fail_on_task="t2"), processing_run_id, edition_part_id
        )
        self.assertEqual(outcome["status"], "failed")

        stub_ok = StubModule("m1")
        configuration_revision_id = self.seed_configuration(
            processing_run_id, stage="m1", module_id=stub_ok.module_id, tasks=stub_ok.tasks
        )
        new_request = make_step_request(processing_run_id, configuration_revision_id)
        self.adapter.supersede_step_run(request["step_run_id"], new_request)
        context = StepContext(
            mode="rerun",
            edition_part_id=edition_part_id,
            stage="m1",
            module_id=stub_ok.module_id,
        )
        outcome2 = stub_ok.execute(self.adapter, new_request, context)
        _finalize(self.adapter, new_request, outcome2)

        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m1"
        )
        self.assertEqual(gate["gate"], "passed")
        self.assertEqual(
            gate["effective_step_run_ids"], [new_request["step_run_id"]]
        )

    def test_superseded_run_without_stage_package_stays_effective(self):
        registry = self.registry_with([StubModule("m1")])
        processing_run_id, edition_part_id = self.start_run()
        request, _outcome, _ = self.execute_stub(
            StubModule("m1"), processing_run_id, edition_part_id
        )

        stub_shim = StubModule("m1", stage_package_mode="missing")
        configuration_revision_id = self.seed_configuration(
            processing_run_id, stage="m1", module_id=stub_shim.module_id, tasks=stub_shim.tasks
        )
        new_request = make_step_request(processing_run_id, configuration_revision_id)
        self.adapter.supersede_step_run(request["step_run_id"], new_request)
        context = StepContext(
            mode="rerun",
            edition_part_id=edition_part_id,
            stage="m1",
            module_id=stub_shim.module_id,
        )
        outcome2 = stub_shim.execute(self.adapter, new_request, context)
        _finalize(self.adapter, new_request, outcome2)

        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m1"
        )
        self.assertEqual(gate["gate"], "passed")
        self.assertIn(request["step_run_id"], gate["effective_step_run_ids"])
        self.assertIn(new_request["step_run_id"], gate["effective_step_run_ids"])

    def test_upstream_lineage_accepts_superseded_succeeded_ancestor(self):
        registry = self.registry_with([StubModule("m2")])
        processing_run_id, edition_part_id = self.start_run()
        request, _outcome, _ = self.execute_stub(
            StubModule("m1"), processing_run_id, edition_part_id
        )

        # 用不承载包的新 m1 运行接替，旧运行仍是 succeeded 祖先
        shim = StubModule("m1", stage_package_mode="missing")
        configuration_revision_id = self.seed_configuration(
            processing_run_id, stage="m1", module_id=shim.module_id, tasks=shim.tasks
        )
        shim_request = make_step_request(processing_run_id, configuration_revision_id)
        self.adapter.supersede_step_run(request["step_run_id"], shim_request)
        shim_outcome = shim.execute(
            self.adapter,
            shim_request,
            StepContext(
                mode="rerun",
                edition_part_id=edition_part_id,
                stage="m1",
                module_id=shim.module_id,
            ),
        )
        _finalize(self.adapter, shim_request, shim_outcome)

        ancestor = self.parsed_run(self.adapter, request["step_run_id"])
        stub_m2 = StubModule("m2")
        first_m2_request, _first_m2_outcome, _ = self.execute_stub(
            stub_m2, processing_run_id, edition_part_id, upstream={"m1": [ancestor]}
        )
        gate = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m2"
        )
        self.assertTrue(gate["checks"]["upstream_lineage"]["ok"])

        # 引用 failed 运行的产出 → 不通过（failed 运行须 supersede 既有 succeeded 运行以绕开封存守卫）
        failed_stub = StubModule("m1", fail_on_task="t1")
        failed_configuration = self.seed_configuration(
            processing_run_id,
            stage="m1",
            module_id=failed_stub.module_id,
            tasks=failed_stub.tasks,
        )
        failed_request = make_step_request(processing_run_id, failed_configuration)
        self.adapter.supersede_step_run(
            shim_request["step_run_id"], failed_request
        )
        failed_outcome = failed_stub.execute(
            self.adapter,
            failed_request,
            StepContext(
                mode="rerun",
                edition_part_id=edition_part_id,
                stage="m1",
                module_id=failed_stub.module_id,
            ),
        )
        _finalize(self.adapter, failed_request, failed_outcome)
        self.assertEqual(failed_outcome["status"], "failed")
        stub_m2b = StubModule("m2")
        m2b_configuration = self.seed_configuration(
            processing_run_id, stage="m2", module_id=stub_m2b.module_id, tasks=stub_m2b.tasks
        )
        m2b_request = make_step_request(
            processing_run_id,
            m2b_configuration,
            input_artifact_ids=list(failed_outcome["output_artifact_ids"]),
        )
        self.adapter.supersede_step_run(
            first_m2_request["step_run_id"], m2b_request
        )
        m2b_outcome = stub_m2b.execute(
            self.adapter,
            m2b_request,
            StepContext(
                mode="rerun",
                edition_part_id=edition_part_id,
                stage="m2",
                module_id=stub_m2b.module_id,
            ),
        )
        _finalize(self.adapter, m2b_request, m2b_outcome)
        gate2 = evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m2"
        )
        self.assertFalse(gate2["checks"]["upstream_lineage"]["ok"])

    def test_gate_performs_no_writes(self):
        registry = self.registry_with([StubModule("m1")])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(StubModule("m1"), processing_run_id, edition_part_id)

        def counts():
            connection = sqlite3.connect(
                "file:%s?mode=ro" % (self.root / "ledger.sqlite"), uri=True
            )
            try:
                return tuple(
                    connection.execute(
                        "SELECT COUNT(*) FROM %s" % table
                    ).fetchone()[0]
                    for table in ("artifact_revisions", "step_runs", "audit_log")
                )
            finally:
                connection.close()

        before = counts()
        evaluate_stage_gate(
            self.adapter, registry, self.handle(processing_run_id, edition_part_id), "m1"
        )
        self.assertEqual(before, counts())

    def test_gate_module_imports_are_independent(self):
        tree = ast.parse(
            (REPO_ROOT / "pipeline" / "orchestrator" / "gate.py").read_text(
                encoding="utf-8"
            )
        )
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
        for name in names:
            for forbidden in ("runner", "module", "stubs", "edition_run", "corpus_compiler"):
                self.assertNotIn(forbidden, name)


class TestEffectiveRuns(GateTestCase):
    """辅助断言：effective/succeeded 集合的解析形态。"""

    def test_effective_and_succeeded_helpers(self):
        registry = self.registry_with([StubModule("m1")])
        processing_run_id, edition_part_id = self.start_run()
        request, _outcome, _ = self.execute_stub(
            StubModule("m1"), processing_run_id, edition_part_id
        )
        handle = self.handle(processing_run_id, edition_part_id)
        effective = effective_step_runs(self.adapter, handle, "m1")
        self.assertEqual([run["step_run_id"] for run in effective], [request["step_run_id"]])
        self.assertIsInstance(effective[0]["request"], dict)
        succeeded = succeeded_step_runs(self.adapter, handle, "m1")
        self.assertEqual([run["step_run_id"] for run in succeeded], [request["step_run_id"]])
        self.assertEqual(evaluate_stage_gate(self.adapter, registry, handle, "m1")["gate"], "passed")


class TestStagePackageYamlBytes(unittest.TestCase):
    """裁定 57：Gate 读取 ``fixture_ingest`` 写入的 YAML 字节包（非 JSON）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "ledger"
        self.fixture_dir = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"

    def test_stage_package_valid_accepts_yaml_bytes_package(self):
        service = LedgerService(self.root)
        try:
            summary = ingest(self.fixture_dir, service, stages=("m1", "m2"))
        finally:
            service.close()
        adapter = DirectLedgerAdapter(self.root)
        self.addCleanup(adapter.close)
        handle = {
            "processing_run_id": summary["processing_run_id"],
            "edition_part_id": summary["edition_part_id"],
            "technique_id": summary["technique_id"],
        }
        gate = evaluate_stage_gate(adapter, load_registry(), handle, "m1")
        check = gate["checks"]["stage_package_valid"]
        self.assertTrue(check["ok"], check["detail"])


if __name__ == "__main__":
    unittest.main()
