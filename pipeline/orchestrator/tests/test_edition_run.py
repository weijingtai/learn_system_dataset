"""ACT impl-08/04：EditionRun 串联与 release 段的单元测试（规格 §6.1/§7/§17）。

先写本文件，全红后再实现 `pipeline/orchestrator/edition_run.py`。
"""

import json
import sqlite3
import unittest

import yaml

from pipeline.contract_registry.catalog import Registry, load_registry
from pipeline.ledger import ids
from pipeline.orchestrator import EDITION_STAGES, FIRST_SLICE_EDITION_STAGES
from pipeline.orchestrator.edition_run import (
    advance,
    edition_status,
    run_release,
    run_until,
    start_edition_run,
)
from pipeline.orchestrator.errors import OrchestratorRefused
from pipeline.orchestrator.gate import effective_step_runs
from pipeline.orchestrator.stubs import StubModule
from pipeline.orchestrator.tests.scaffold import REPO_ROOT
from pipeline.orchestrator.tests.test_gate import GateTestCase
from pipeline.orchestrator.tests.test_runner import make_legacy_entry

REGISTRY_PATH = REPO_ROOT / "pipeline" / "contract_registry" / "registry.yaml"


class EditionTestCase(GateTestCase):
    """公共脚手架：桩登记表、模块注入表与只读行数统计。"""

    def registry_from_descriptors(self, descriptors):
        doc = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
        doc["modules"] = list(descriptors)
        return Registry.from_dict(doc, repo_root=REPO_ROOT, allow_stub=True)

    def stub_modules(self, stubs):
        return {stub.module_id: stub for stub in stubs}

    def all_stubs(self, overrides=None):
        overrides = overrides or {}
        return [
            overrides.get(stage, StubModule(stage)) for stage in EDITION_STAGES
        ]

    def row_counts(self):
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


class TestEditionRun(EditionTestCase):
    """覆盖 BDD §5：串联、零写入、零写入阻断与首纵切计划。"""

    def test_run_until_m6_all_executed_then_complete(self):
        stubs = self.all_stubs()
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        results = run_until(
            self.adapter, registry, handle, "m6", modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual(results[-1]["action"], "complete")
        self.assertEqual(
            [item["stage"] for item in results if item["action"] == "executed"],
            list(EDITION_STAGES),
        )

    def test_advance_gate_reports_carry_upstream_gate(self):
        stubs = self.all_stubs()
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        advance(self.adapter, registry, handle, modules=modules, stages=EDITION_STAGES)
        result = advance(
            self.adapter, registry, handle, modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual(result["action"], "executed")
        self.assertEqual(result["stage"], "m2")
        self.assertEqual(result["gate_reports"]["m1"]["gate"], "passed")
        self.assertEqual(result["gate_reports"]["m1"]["stage"], "m1")

        step_result = result["step_result"]
        self.assertEqual(len(step_result["validation_report_ids"]), 1)
        row = self.adapter.get_revision(step_result["validation_report_ids"][0])
        content = json.loads(self.adapter.read_object(row["sha256"]).decode("utf-8"))
        self.assertEqual(content, {"passed": True})

    def test_downstream_frozen_inputs_include_upstream_stage_package(self):
        stubs = self.all_stubs()
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        run_until(
            self.adapter, registry, handle, "m3", modules=modules, stages=EDITION_STAGES
        )
        m2_run = effective_step_runs(self.adapter, handle, "m2")[-1]
        m2_result = json.loads(m2_run["result_json"])
        packages = [
            revision_id
            for revision_id in m2_result["output_artifact_ids"]
            if self.adapter.get_revision(revision_id)["schema_id"] == "stage_package"
        ]
        m3_run = effective_step_runs(self.adapter, handle, "m3")[-1]
        m3_request = json.loads(m3_run["request_json"])
        self.assertTrue(set(packages) & set(m3_request["input_artifact_ids"]))

    def test_failed_m3_blocks_and_no_m4_step_run(self):
        stubs = self.all_stubs({"m3": StubModule("m3", fail_on_task="t2")})
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        results = run_until(
            self.adapter, registry, handle, "m6", modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual(results[-1]["action"], "executed")
        self.assertEqual(results[-1]["stage"], "m3")
        self.assertEqual(results[-1]["step_result"]["status"], "failed")
        step_runs = self.adapter.run_status(processing_run_id)["step_runs"]
        self.assertFalse(any(step["stage"] == "m4" for step in step_runs))

    def test_blocked_advance_is_zero_write(self):
        stubs = self.all_stubs({"m3": StubModule("m3", fail_on_task="t2")})
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)
        run_until(
            self.adapter, registry, handle, "m6", modules=modules, stages=EDITION_STAGES
        )

        before = self.row_counts()
        result = advance(
            self.adapter, registry, handle, modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual(result["action"], "blocked")
        self.assertEqual(before, self.row_counts())

    def test_awaiting_human_m2_then_waiting_zero_write(self):
        stubs = self.all_stubs({"m2": StubModule("m2", human_queue=True)})
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        results = run_until(
            self.adapter, registry, handle, "m2", modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual(results[-1]["step_result"]["status"], "awaiting_human")

        before = self.row_counts()
        result = advance(
            self.adapter, registry, handle, modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual(result["action"], "waiting")
        self.assertEqual(before, self.row_counts())

    def test_unregistered_stage_refused_with_section_19_row_name(self):
        stubs = [StubModule(stage) for stage in ("m1", "m2", "m3", "m5")]
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        results = run_until(
            self.adapter, registry, handle, "m3", modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual(results[-1]["action"], "refused")
        self.assertEqual(results[-1]["stage"], "m4")
        self.assertIn("M4 Knowledge Extraction", results[-1]["reason"])

    def test_imported_stage_without_tasks_refused(self):
        registry = load_registry()
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)
        result = advance(
            self.adapter, registry, handle, stages=FIRST_SLICE_EDITION_STAGES
        )
        self.assertEqual(result["action"], "refused")
        self.assertIn("imported", result["reason"])

    def test_plan_config_stage_mismatch_refused_before_write(self):
        class WrongStage(StubModule):
            def plan(
                self, port, *, edition_part_id, processing_run_id, technique_id, upstream
            ):
                planned = super().plan(
                    port,
                    edition_part_id=edition_part_id,
                    processing_run_id=processing_run_id,
                    technique_id=technique_id,
                    upstream=upstream,
                )
                planned["configuration"]["stage"] = "m5"
                return planned

        stub = WrongStage("m1")
        registry = self.registry_with([stub])
        modules = {stub.module_id: stub}
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        before = self.row_counts()
        result = advance(
            self.adapter, registry, handle, modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual(result["action"], "refused")
        self.assertEqual(before, self.row_counts())

    def test_plan_unsealed_input_refused_before_write(self):
        class UnsealedInput(StubModule):
            def plan(
                self, port, *, edition_part_id, processing_run_id, technique_id, upstream
            ):
                planned = super().plan(
                    port,
                    edition_part_id=edition_part_id,
                    processing_run_id=processing_run_id,
                    technique_id=technique_id,
                    upstream=upstream,
                )
                planned["input_artifact_ids"] = ["rev_" + "a" * 32]
                return planned

        stub = UnsealedInput("m1")
        registry = self.registry_with([stub])
        modules = {stub.module_id: stub}
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        before = self.row_counts()
        result = advance(
            self.adapter, registry, handle, modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual(result["action"], "refused")
        self.assertEqual(before, self.row_counts())

    def test_adopt_rejects_foreign_technique(self):
        stubs = self.all_stubs()
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        edition_part_id = ids.new_id("artifact_id")
        handle = start_edition_run(
            self.adapter, edition_part_id=edition_part_id, technique_id="qizheng"
        )
        advance(self.adapter, registry, handle, modules=modules, stages=EDITION_STAGES)

        from pipeline.orchestrator.edition_run import adopt_edition_run

        with self.assertRaises(OrchestratorRefused):
            adopt_edition_run(
                self.adapter,
                processing_run_id=handle["processing_run_id"],
                edition_part_id=edition_part_id,
                technique_id="other",
            )

    def test_edition_status_conjunction_two_parts(self):
        stubs = self.all_stubs()
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)

        handle_a = start_edition_run(
            self.adapter, edition_part_id=ids.new_id("artifact_id"), technique_id="qizheng"
        )
        run_until(
            self.adapter, registry, handle_a, "m6", modules=modules, stages=EDITION_STAGES
        )
        handle_b = start_edition_run(
            self.adapter, edition_part_id=ids.new_id("artifact_id"), technique_id="qizheng"
        )
        advance(self.adapter, registry, handle_b, modules=modules, stages=EDITION_STAGES)
        advance(self.adapter, registry, handle_b, modules=modules, stages=EDITION_STAGES)

        status = edition_status(self.adapter, registry, [handle_a, handle_b])
        self.assertFalse(status["complete"])
        self.assertEqual(status["parts"][handle_a["edition_part_id"]], "complete")
        self.assertEqual(status["parts"][handle_b["edition_part_id"]], "incomplete")

        run_until(
            self.adapter, registry, handle_b, "m6", modules=modules, stages=EDITION_STAGES
        )
        status_after = edition_status(self.adapter, registry, [handle_a, handle_b])
        self.assertTrue(status_after["complete"])

    def test_first_slice_plan_runs_m1_m2_m3_m5_and_reports_gap(self):
        doc = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
        descriptors = [
            module for module in doc["modules"] if module["stage"] in ("m1", "m2")
        ]
        m3 = StubModule("m3")
        m5 = StubModule("m5", consumes_from="m3")
        descriptors.extend([m3.descriptor(), m5.descriptor()])
        registry = self.registry_from_descriptors(descriptors)
        modules = {m3.module_id: m3, m5.module_id: m5}

        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        # 先手工登记 m1/m2（imported 阶段只判 Gate）
        m1_stub = StubModule("m1", produces=("source_manifest",))
        self.execute_stub(m1_stub, processing_run_id, edition_part_id)
        ancestor = self.parsed_run(self.adapter, self._last_step_run(processing_run_id, "m1"))
        m2_stub = StubModule("m2", produces=("ocr_page_set",), consumes_from="m1")
        self.execute_stub(
            m2_stub, processing_run_id, edition_part_id, upstream={"m1": [ancestor]}
        )

        results = run_until(
            self.adapter,
            registry,
            handle,
            "m5",
            modules=modules,
            stages=FIRST_SLICE_EDITION_STAGES,
        )
        self.assertEqual(
            [item["stage"] for item in results if item["action"] == "executed"],
            ["m3", "m5"],
        )
        status = edition_status(self.adapter, registry, [handle])
        self.assertEqual(status["deferred_stages"], ["m4", "m6"])
        self.assertFalse(
            any(
                step["stage"] == "m4"
                for step in self.adapter.run_status(processing_run_id)["step_runs"]
            )
        )

    def _last_step_run(self, processing_run_id, stage):
        rows = [
            step
            for step in self.adapter.run_status(processing_run_id)["step_runs"]
            if step["stage"] == stage
        ]
        return rows[-1]["step_run_id"]

    @staticmethod
    def _release_descriptor(stage, module_id, entry_kwargs=None):
        return {
            "module_id": module_id,
            "stage": stage,
            "kind": "production",
            "binding": "legacy_self_driving",
            "entry": "tests:fake",
            "version": "0.1.0",
            "consumes": [],
            "produces": [{"artifact_type": "stub_output"}],
            "human_queue": stage == "m7",
            "supports_recovery": False,
            "entry_kwargs": dict(entry_kwargs or {}),
            "owns_processing_run": True,
        }

    def test_release_stages_are_m7_then_m8(self):
        # TODO T04B：release 段由 M7 推到 M8；M7 已接上，不再是缺口
        from pipeline.orchestrator import DEFERRED_STAGES, RELEASE_STAGES

        self.assertEqual(RELEASE_STAGES, ("m7", "m8"))
        self.assertNotIn("m7", DEFERRED_STAGES)

    def test_run_release_invokes_m7_then_m8_and_gates(self):
        edition_part_id = ids.new_id("artifact_id")
        calls = []
        m7_entry = make_legacy_entry("m7", produces=("stub_output",))
        m8_entry = make_legacy_entry("m8", produces=("stub_output",))

        def recording(stage, entry):
            def wrapped(service, edition_part_id, **kwargs):
                calls.append(stage)
                return entry(service, edition_part_id, **kwargs)

            return wrapped

        registry = self.registry_from_descriptors(
            [
                self._release_descriptor("m7", "m7.incremental_assembly"),
                self._release_descriptor(
                    "m8",
                    "m8.dataset_compilation",
                    {"consumption_level": "INTERNAL_DEMO"},
                ),
            ]
        )
        out = run_release(
            self.adapter,
            registry,
            edition_part_id=edition_part_id,
            technique_id="qizheng",
            modules={
                "m7.incremental_assembly": recording("m7", m7_entry),
                "m8.dataset_compilation": recording("m8", m8_entry),
            },
        )
        self.assertEqual(calls, ["m7", "m8"])
        self.assertEqual(out["action"], "executed")
        self.assertEqual(out["stage"], "m8")
        self.assertEqual(out["step_result"]["status"], "succeeded")
        self.assertTrue(out["processing_run_id"].startswith("prun_"))
        self.assertEqual(out["gate"]["gate"], "passed")
        self.assertEqual(sorted(out["gate_reports"]), ["m7", "m8"])
        self.assertEqual(out["gate_reports"]["m7"]["gate"], "passed")
        self.assertEqual(m7_entry.received, {})
        self.assertEqual(m8_entry.received, {"consumption_level": "INTERNAL_DEMO"})

        refused = run_release(
            self.adapter,
            self.registry_from_descriptors([]),
            edition_part_id=edition_part_id,
            technique_id="qizheng",
        )
        self.assertEqual(refused["action"], "refused")
        self.assertEqual(refused["stage"], "m7")
        self.assertIn("M7 Incremental Assembly", refused["reason"])

        only_m7 = make_legacy_entry("m7", produces=("stub_output",))
        refused_m8 = run_release(
            self.adapter,
            self.registry_from_descriptors(
                [self._release_descriptor("m7", "m7.incremental_assembly")]
            ),
            edition_part_id=ids.new_id("artifact_id"),
            technique_id="qizheng",
            modules={"m7.incremental_assembly": only_m7},
        )
        self.assertEqual(refused_m8["action"], "refused")
        self.assertEqual(refused_m8["stage"], "m8")
        self.assertIn("M8 Dataset Compilation", refused_m8["reason"])
        self.assertEqual(refused_m8["gate_reports"]["m7"]["gate"], "passed")

    def test_run_release_stops_at_m7_when_m7_not_succeeded(self):
        """M7 未 succeeded（失败或停在人工裁决）→ 停在 m7，不推进 m8。"""
        from pipeline.orchestrator.module import StepContext
        from pipeline.orchestrator.tests.scaffold import make_step_request
        from pipeline.orchestrator.tests.test_runner import ServicePort, finalize_step_run

        m8_entry = make_legacy_entry("m8", produces=("stub_output",))

        def failing_m7(service, edition_part_id, **kwargs):
            processing_run = service.create_processing_run(
                "release_run", edition_part_id, "qizheng"
            )
            port = ServicePort(service)
            stub = StubModule(
                "m7",
                module_id="legacy.m7",
                fail_on_task="t1",
                consumes_from=None,
            )
            _artifact_id, config_revision_id = service.put_run_artifact(
                processing_run,
                "configuration",
                json.dumps(
                    {"stage": "m7", "module_id": stub.module_id, "tasks": ["t1", "t2"]},
                    sort_keys=True,
                ).encode("utf-8"),
                producer_module="tests",
                producer_version="1.0",
            )
            request = make_step_request(processing_run, config_revision_id)
            service.begin_step_run(request)
            outcome = stub.execute(
                port,
                request,
                StepContext(
                    mode="fresh",
                    edition_part_id=edition_part_id,
                    stage="m7",
                    module_id=stub.module_id,
                ),
            )
            finalize_step_run(port, request, outcome)
            return {"step_run_id": request["step_run_id"], "processing_run_id": processing_run}

        registry = self.registry_from_descriptors(
            [
                self._release_descriptor("m7", "m7.incremental_assembly"),
                self._release_descriptor("m8", "m8.dataset_compilation"),
            ]
        )
        out = run_release(
            self.adapter,
            registry,
            edition_part_id=ids.new_id("artifact_id"),
            technique_id="qizheng",
            modules={
                "m7.incremental_assembly": failing_m7,
                "m8.dataset_compilation": m8_entry,
            },
        )
        self.assertEqual(out["action"], "executed")
        self.assertEqual(out["stage"], "m7")
        self.assertEqual(out["step_result"]["status"], "failed")
        self.assertIsNone(m8_entry.received, "m7 未 succeeded 时不得推进 m8")
        self.assertNotIn("m8", out["gate_reports"])


if __name__ == "__main__":
    unittest.main()
