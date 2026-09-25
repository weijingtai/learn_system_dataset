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
from pipeline.orchestrator.gate import effective_step_runs, evaluate_stage_gate
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

    def edition_with_release(self, release_descriptors, target="m6"):
        """桩 m1–m6 + 给定发布段描述符的登记表；新建 EditionRun 并推到 ``target``。

        T04 Q7 起 ``run_release`` 以 EditionRun 句柄为准入（读其 m6 Gate），发布段用例
        必须先有真实推进到 m6 的 EditionRun，不能再凭空给一个 edition_part_id。
        """
        stubs = self.all_stubs()
        registry = self.registry_from_descriptors(
            [stub.descriptor() for stub in stubs] + list(release_descriptors)
        )
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)
        run_until(
            self.adapter, registry, handle, target,
            modules=self.stub_modules(stubs), stages=EDITION_STAGES,
        )
        return registry, handle

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

    def test_run_until_stops_after_target_stage_never_executes_next(self):
        """``run_until(..., "m3")`` 执行完 m3 就停，绝不执行 m4（目标 Gate 按执行之后的事实判）。"""
        stubs = self.all_stubs()
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        results = run_until(
            self.adapter, registry, handle, "m3", modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual(
            [item["stage"] for item in results if item["action"] == "executed"],
            ["m1", "m2", "m3"],
        )
        step_runs = self.adapter.run_status(processing_run_id)["step_runs"]
        self.assertEqual(
            sorted({step["stage"] for step in step_runs}), ["m1", "m2", "m3"]
        )
        self.assertEqual(modules["stub.m4"].executed_tasks, [])
        self.assertEqual(
            evaluate_stage_gate(self.adapter, registry, handle, "m3")["gate"], "passed"
        )

        # 目标 Gate 已过时再 run_until 同一目标：零写入，不执行任何 stage
        before = self.row_counts()
        again = run_until(
            self.adapter, registry, handle, "m3", modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual([item for item in again if item["action"] == "executed"], [])
        self.assertEqual(before, self.row_counts())

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

        # 目标取 m4：run_until 不再越过目标，推到未登记的 m4 才会被拒
        results = run_until(
            self.adapter, registry, handle, "m4", modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual(results[-1]["action"], "refused")
        self.assertEqual(results[-1]["stage"], "m4")
        self.assertIn("M4 Knowledge Extraction", results[-1]["reason"])

    def test_imported_stage_without_tasks_refused(self):
        """``imported`` 绑定无任务可执行 → 拒收，理由点名 ``imported``，且零写入。

        改前：直接拿生产登记表来推（当时的 m1/m2 就是 ``imported`` 夹具模块）。
        裁决 2 把夹具导入入口从生产表删掉后，生产表里再没有 ``imported`` 模块，
        该分支必须在本用例里**显式构造**（与 `test_catalog` 的同类改写同口径）；
        同时补上「拒收零写入」与阶段名两条断言，只收紧不放宽。
        """
        descriptor = dict(StubModule("m1").descriptor())
        descriptor["binding"] = "imported"
        registry = self.registry_from_descriptors([descriptor])
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        before = self.row_counts()
        result = advance(
            self.adapter, registry, handle, stages=FIRST_SLICE_EDITION_STAGES
        )
        self.assertEqual(result["action"], "refused")
        self.assertEqual(result["stage"], "m1")
        self.assertIn("imported", result["reason"])
        self.assertEqual(before, self.row_counts(), "拒收零写入")

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

    def test_legacy_entry_refusal_is_reported_and_zero_write(self):
        """裁决 Q1：legacy 入口在**任何写入之前**拒收时，advance 零写入返回 refused。

        入口不是抛异常、也不是留下一个 failed StepRun，而是返回零写入拒收；调度器
        如实报出理由（含出路），且反复 advance 不产生任何新修订。
        """

        def refusing_entry(service, edition_part_id, **kwargs):
            refusing_entry.received = kwargs
            return {
                "refused": True,
                "reason": "M4 拒收（REF_001）：没有已登记的提交件；"
                "请先经 run_m4_submit 提交候选件",
            }

        m1 = StubModule("m1")
        m2 = StubModule("m2", consumes_from="m1")
        m3 = StubModule("m3", consumes_from="m2")
        descriptor = {
            "module_id": "m4.knowledge_extraction",
            "stage": "m4",
            "kind": "production",
            "binding": "legacy_self_driving",
            "entry": "tests:refusing_entry",
            "version": "0.1.0",
            "consumes": [],
            "produces": [{"artifact_type": "candidate_package"}],
            "human_queue": True,
            "supports_recovery": False,
            "entry_kwargs": {},
            "owns_processing_run": False,
        }
        registry = self.registry_from_descriptors(
            [m1.descriptor(), m2.descriptor(), m3.descriptor(), descriptor]
        )
        modules = self.stub_modules([m1, m2, m3])
        modules["m4.knowledge_extraction"] = refusing_entry
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)
        run_until(
            self.adapter,
            registry,
            handle,
            "m3",
            modules=modules,
            stages=EDITION_STAGES,
        )

        before = self.row_counts()
        first = advance(
            self.adapter, registry, handle, modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual(first["action"], "refused")
        self.assertEqual(first["stage"], "m4")
        self.assertIsNone(first["step_run_id"])
        self.assertIn("run_m4_submit", first["reason"])
        self.assertIn("REF_001", first["reason"])
        self.assertEqual(before, self.row_counts(), "拒收必须零写入")

        second = advance(
            self.adapter, registry, handle, modules=modules, stages=EDITION_STAGES
        )
        self.assertEqual(second["action"], "refused", "不许反复调起后改口")
        self.assertEqual(second["reason"], first["reason"])
        self.assertEqual(before, self.row_counts(), "重复 advance 不得新增修订")
        self.assertFalse(
            any(
                step["stage"] == "m4"
                for step in self.adapter.run_status(processing_run_id)["step_runs"]
            ),
            "拒收不建 StepRun",
        )

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
        """首切片：m1/m2 已登记 → 调度器只跑 m3/m5，并如实报 m4/m6 缺口。

        改前：m1/m2 的描述符直接取自生产登记表（当时它们是 ``imported`` 夹具模块，
        `produces` 恰好与本用例手工执行的桩一致）。裁决 2 把生产表的 m1/m2 换成文本
        路线生产模块（`consumes`/`produces` 均不同），手工登记的桩包就不再满足
        描述符的 `output_contract`——守卫的意图（已满足的阶段不重跑、缺口如实报出）
        不变，故描述符改由本用例的两个桩自述。断言未改。
        """
        m1_stub = StubModule("m1", produces=("source_manifest",))
        m2_stub = StubModule("m2", produces=("ocr_page_set",), consumes_from="m1")
        m3 = StubModule("m3")
        m5 = StubModule("m5", consumes_from="m3")
        registry = self.registry_from_descriptors(
            [
                m1_stub.descriptor(),
                m2_stub.descriptor(),
                m3.descriptor(),
                m5.descriptor(),
            ]
        )
        modules = {m3.module_id: m3, m5.module_id: m5}

        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        # 先手工登记 m1/m2（已满足的阶段只判 Gate）
        self.execute_stub(m1_stub, processing_run_id, edition_part_id)
        ancestor = self.parsed_run(self.adapter, self._last_step_run(processing_run_id, "m1"))
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
        # T04 Q7 改写：改前凭空给 edition_part_id 调 run_release；改后先经桩把 EditionRun 推到
        # m6，再以其句柄调用（发布准入读 EditionRun 的 m6 Gate）。断言只增不减。
        calls = []
        m7_entry = make_legacy_entry("m7", produces=("stub_output",))
        m8_entry = make_legacy_entry("m8", produces=("stub_output",))

        def recording(stage, entry):
            def wrapped(service, edition_part_id, **kwargs):
                calls.append(stage)
                return entry(service, edition_part_id, **kwargs)

            return wrapped

        registry, handle = self.edition_with_release(
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
            handle,
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

        no_release_registry, _ = self.edition_with_release([])
        refused = run_release(self.adapter, no_release_registry, handle)
        self.assertEqual(refused["action"], "refused")
        self.assertEqual(refused["stage"], "m7")
        self.assertIn("M7 Incremental Assembly", refused["reason"])

        only_m7 = make_legacy_entry("m7", produces=("stub_output",))
        only_m7_registry, only_m7_handle = self.edition_with_release(
            [self._release_descriptor("m7", "m7.incremental_assembly")]
        )
        refused_m8 = run_release(
            self.adapter,
            only_m7_registry,
            only_m7_handle,
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

        # T04 Q7 改写：同上，先有推进到 m6 的 EditionRun 再调 run_release；断言不变。
        registry, handle = self.edition_with_release(
            [
                self._release_descriptor("m7", "m7.incremental_assembly"),
                self._release_descriptor("m8", "m8.dataset_compilation"),
            ]
        )
        out = run_release(
            self.adapter,
            registry,
            handle,
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


def freezing_release_entry(stage, upstream_stages, calls=None):
    """假 ``legacy_self_driving`` 发布段入口：像真 M7/M8 一样按 EditionPart 找上游并冻结。

    每个上游 stage 取该 EditionPart 名下最新 succeeded 运行的 sealed StagePackage，冻结为
    本运行输入；本段自建 ``release_run``（``owns_processing_run``）。``upstream_stages`` 为空
    时什么也不冻结（构造「血缘断开」的负例）。
    """
    from pipeline.orchestrator.module import StepContext
    from pipeline.orchestrator.tests.scaffold import make_step_request
    from pipeline.orchestrator.tests.test_runner import ServicePort, finalize_step_run

    def entry(service, edition_part_id, **kwargs):
        if calls is not None:
            calls.append(stage)
        inputs = []
        for upstream in upstream_stages:
            succeeded = [
                row["step_run_id"]
                for row in service.list_step_runs(edition_part_id, upstream)
                if row["status"] == "succeeded"
            ]
            rows = service.list_step_run_revisions(
                succeeded[-1], artifact_type="stage_package", status="sealed"
            )
            inputs.append(rows[0]["artifact_revision_id"])
        processing_run = service.create_processing_run("release_run", edition_part_id, "qizheng")
        port = ServicePort(service)
        stub = StubModule(stage, module_id="legacy.%s" % stage, tasks=("t1",), consumes_from=None)
        _artifact_id, config_revision_id = service.put_run_artifact(
            processing_run,
            "configuration",
            json.dumps({"stage": stage, "module_id": stub.module_id, "tasks": ["t1"]}, sort_keys=True).encode("utf-8"),
            producer_module="tests",
            producer_version="1.0",
        )
        request = make_step_request(processing_run, config_revision_id, input_artifact_ids=inputs)
        service.begin_step_run(request)
        outcome = stub.execute(
            port,
            request,
            StepContext(mode="fresh", edition_part_id=edition_part_id, stage=stage, module_id=stub.module_id),
        )
        finalize_step_run(port, request, outcome)
        return {"step_run_id": request["step_run_id"], "processing_run_id": processing_run}

    return entry


class TestReleaseAdmissionAndLineage(EditionTestCase):
    """T04 阶段 4 Q7：release 准入读 EditionRun 的 m6；各段 Gate 按显式上游句柄判血缘；Gate 不过即停。

    release run 只承载 m7/m8；m1–m6 只在 EditionRun 里。Gate 仍只按句柄的运行号取数，
    不按 EditionPart 回退——调度器把「上游在哪个运行」显式交给它。
    """

    @staticmethod
    def _release_descriptor(stage, module_id, consumes_from):
        descriptor = TestEditionRun._release_descriptor(stage, module_id)
        descriptor["consumes"] = [
            {"artifact_type": "stage_package", "from_stage": upstream} for upstream in consumes_from
        ]
        return descriptor

    def _edition(self, target="m6"):
        """发布段描述符（m7 吃 m6；m8 吃 m6 与 m7）；EditionRun 推到 ``target``。"""
        return self.edition_with_release(
            [
                self._release_descriptor("m7", "m7.incremental_assembly", ["m6"]),
                self._release_descriptor("m8", "m8.dataset_compilation", ["m6", "m7"]),
            ],
            target,
        )

    def test_release_reads_m6_from_edition_run_and_lineage_across_runs(self):
        registry, handle = self._edition("m6")
        calls = []
        out = run_release(
            self.adapter,
            registry,
            handle,
            modules={
                "m7.incremental_assembly": freezing_release_entry("m7", ["m6"], calls),
                "m8.dataset_compilation": freezing_release_entry("m8", ["m6", "m7"], calls),
            },
        )
        self.assertEqual(calls, ["m7", "m8"])
        self.assertEqual((out["action"], out["stage"]), ("executed", "m8"), out.get("reason"))
        self.assertEqual(out["gate_reports"]["m7"]["gate"], "passed", out["gate_reports"]["m7"]["checks"])
        self.assertEqual(out["gate_reports"]["m8"]["gate"], "passed", out["gate_reports"]["m8"]["checks"])
        # release run 只承载 m7/m8，EditionRun 不多出发布段运行
        for stage in ("m7", "m8"):
            release_run = out["gate_reports"][stage]["processing_run_id"]
            self.assertNotEqual(release_run, handle["processing_run_id"])
            stages = {row["stage"] for row in self.adapter.run_status(release_run)["step_runs"]}
            self.assertEqual(stages, {stage})
        edition_stages = {row["stage"] for row in self.adapter.run_status(handle["processing_run_id"])["step_runs"]}
        self.assertEqual(edition_stages, set(EDITION_STAGES))

    def test_release_refused_zero_write_when_edition_m6_gate_not_passed(self):
        registry, handle = self._edition("m5")
        calls = []
        before = self.row_counts()
        out = run_release(
            self.adapter,
            registry,
            handle,
            modules={
                "m7.incremental_assembly": freezing_release_entry("m7", ["m6"], calls),
                "m8.dataset_compilation": freezing_release_entry("m8", ["m6", "m7"], calls),
            },
        )
        self.assertEqual((out["action"], out["stage"]), ("refused", "m7"))
        self.assertIn("m6", out["reason"])
        self.assertIn(handle["processing_run_id"], out["reason"])
        self.assertEqual(calls, [])
        self.assertEqual(before, self.row_counts())

    def test_release_stops_when_m7_gate_blocked(self):
        """M7 跑成功但没冻结 m6（血缘断）→ m7 Gate 不过 → 停在 m7，不推进 m8。"""
        registry, handle = self._edition("m6")
        calls = []
        out = run_release(
            self.adapter,
            registry,
            handle,
            modules={
                "m7.incremental_assembly": freezing_release_entry("m7", [], calls),
                "m8.dataset_compilation": freezing_release_entry("m8", ["m6", "m7"], calls),
            },
        )
        self.assertEqual(calls, ["m7"])
        self.assertEqual((out["action"], out["stage"]), ("executed", "m7"))
        self.assertEqual(out["step_result"]["status"], "succeeded")
        self.assertEqual(out["gate"]["gate"], "blocked")
        self.assertFalse(out["gate"]["checks"]["upstream_lineage"]["ok"])
        self.assertNotIn("m8", out["gate_reports"])

    def test_gate_without_upstream_handles_still_reads_only_its_own_run(self):
        """不给显式上游句柄时 Gate 行为不变：只在本运行里找上游（不按 EditionPart 回退）。"""
        registry, handle = self._edition("m6")
        out = run_release(
            self.adapter,
            registry,
            handle,
            modules={
                "m7.incremental_assembly": freezing_release_entry("m7", ["m6"]),
                "m8.dataset_compilation": freezing_release_entry("m8", ["m6", "m7"]),
            },
        )
        m7_handle = self.handle(out["gate_reports"]["m7"]["processing_run_id"], handle["edition_part_id"])
        alone = evaluate_stage_gate(self.adapter, registry, m7_handle, "m7")
        self.assertEqual(alone["gate"], "blocked")
        self.assertFalse(alone["checks"]["upstream_lineage"]["ok"])


class HumanInputStub(StubModule):
    """模拟 m4：成功但无阶段包、只登记描述符声明的人工输入件的运行。

    - ``writes_human=False``：构造「声明了却没有任何该类型修订」的负例；
    - ``writes_produces=True``：构造「写过 produces 类型却仍无包」的负例。

    描述符显式带 ``human_input_artifact``（裁决 Q2），produces 默认为
    ``candidate_package``（与人工输入件不同）。
    """

    def __init__(
        self,
        stage,
        *,
        human_input_type="candidate_submission",
        writes_human=True,
        writes_produces=False,
        **kwargs
    ):
        kwargs.setdefault("produces", ("candidate_package",))
        super().__init__(stage, stage_package_mode="missing", **kwargs)
        self.human_input_type = human_input_type
        self.writes_human = writes_human
        self.writes_produces = writes_produces

    def descriptor(self):
        descriptor = dict(super().descriptor())
        descriptor["human_input_artifact"] = self.human_input_type
        return descriptor

    def execute(self, port, request, context):
        step_run_id = request["step_run_id"]
        outputs = []
        for flag, artifact_type in (
            (self.writes_human, self.human_input_type),
            (self.writes_produces, self.produces[0]),
        ):
            if not flag:
                continue
            _artifact_id, revision_id = port.put_artifact(
                step_run_id,
                artifact_type,
                b"stub-human-input",
                producer_module=self.module_id,
                producer_version="0.0.0",
            )
            port.seal_revision(revision_id)
            outputs.append(revision_id)
        port.write_checkpoint(
            step_run_id,
            edition_part_id=context.edition_part_id,
            stage=self.stage,
            completed_tasks=[
                {
                    "task_id": "submit",
                    "artifact_revision_id": revision_id,
                    "status": "succeeded",
                    "terminal_state": None,
                }
                for revision_id in outputs
            ],
            human_decisions=[],
            pending_queue=[],
            next_pointer=None,
        )
        return {
            "status": "succeeded",
            "output_artifact_ids": list(outputs),
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
        }


class TestAdvanceHumanInputReentry(EditionTestCase):
    """裁决 Q2：仅「只承载声明的人工输入件、尚未产出 produces 类型」的 stage 才重入登记入口。"""

    def test_declared_stage_with_human_input_run_reenters_entry(self):
        prior = HumanInputStub("m1")
        registry = self.registry_with([prior])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(prior, processing_run_id, edition_part_id)

        entry = StubModule("m1", module_id=prior.module_id)
        result = advance(
            self.adapter,
            registry,
            self.handle(processing_run_id, edition_part_id),
            modules={prior.module_id: entry},
            stages=("m1",),
        )
        self.assertEqual((result["action"], result["stage"]), ("executed", "m1"))
        self.assertTrue(entry.executed_tasks, "重入必须真的调起登记入口")

    def test_undeclared_stage_with_succeeded_no_package_still_blocked(self):
        stub = StubModule("m1", stage_package_mode="missing")
        registry = self.registry_with([stub])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(stub, processing_run_id, edition_part_id)

        before = self.row_counts()
        result = advance(
            self.adapter,
            registry,
            self.handle(processing_run_id, edition_part_id),
            modules={stub.module_id: stub},
            stages=("m1",),
        )
        self.assertEqual(result["action"], "blocked")
        self.assertEqual(before, self.row_counts())

    def test_declared_stage_without_human_input_revision_still_blocked(self):
        stub = HumanInputStub("m1", writes_human=False)
        registry = self.registry_with([stub])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(stub, processing_run_id, edition_part_id)

        before = self.row_counts()
        result = advance(
            self.adapter,
            registry,
            self.handle(processing_run_id, edition_part_id),
            modules={stub.module_id: stub},
            stages=("m1",),
        )
        self.assertEqual(result["action"], "blocked")
        self.assertEqual(before, self.row_counts())

    def test_declared_stage_with_produces_written_still_blocked(self):
        stub = HumanInputStub("m1", writes_produces=True)
        registry = self.registry_with([stub])
        processing_run_id, edition_part_id = self.start_run()
        self.execute_stub(stub, processing_run_id, edition_part_id)

        before = self.row_counts()
        result = advance(
            self.adapter,
            registry,
            self.handle(processing_run_id, edition_part_id),
            modules={stub.module_id: stub},
            stages=("m1",),
        )
        self.assertEqual(result["action"], "blocked")
        self.assertEqual(before, self.row_counts())


if __name__ == "__main__":
    unittest.main()
