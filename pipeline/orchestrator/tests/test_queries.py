"""ACT impl-08/06：六项只读查询的单元测试（规格 §5 :117–127）。

先写本文件，运行 `.venv/bin/python -m unittest discover -s pipeline/orchestrator/tests -t .`
取得 ImportError 全红（Red），再实现 `pipeline/orchestrator/queries.py`。
"""

import json
import unittest

from pipeline.ledger.errors import MissingReference
from pipeline.orchestrator import EDITION_STAGES
from pipeline.orchestrator.edition_run import run_until
from pipeline.orchestrator.gate import effective_step_runs
from pipeline.orchestrator.queries import (
    QUERY_NAMES,
    blocking_reasons,
    pending_queue,
    rework_impact,
    run_status,
    stage_progress,
    throughput_estimate,
)
from pipeline.orchestrator.stubs import StubModule
from pipeline.orchestrator.tests.scaffold import make_step_request
from pipeline.orchestrator.tests.test_edition_run import EditionTestCase


class QueryTestCase(EditionTestCase):
    """公共脚手架：推进到指定 stage 与只读行数统计（继承 EditionTestCase）。"""

    def advance_all(self, stubs, handle, registry, modules, stage):
        run_until(
            self.adapter, registry, handle, stage, modules=modules, stages=EDITION_STAGES
        )

    def package_revision(self, handle, stage):
        run = effective_step_runs(self.adapter, handle, stage)[-1]
        result = json.loads(run["result_json"])
        return [
            revision_id
            for revision_id in result["output_artifact_ids"]
            if self.adapter.get_revision(revision_id)["schema_id"] == "stage_package"
        ][0]


class TestQueries(QueryTestCase):
    """覆盖 BDD §7：六项查询闭集、结构与零写入。"""

    def test_query_names_closed_set_six(self):
        self.assertEqual(
            QUERY_NAMES,
            (
                "RunStatus",
                "StageProgress",
                "PendingQueue",
                "BlockingReasons",
                "ReworkImpact",
                "ThroughputEstimate",
            ),
        )

    def test_pending_queue_five_keys_and_m2_item(self):
        stubs = self.all_stubs({"m2": StubModule("m2", human_queue=True)})
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)
        run_until(
            self.adapter, registry, handle, "m2", modules=modules, stages=EDITION_STAGES
        )

        result = pending_queue(self.adapter, registry, handle)
        self.assertEqual(len(result["queues"]), 5)
        self.assertEqual(len(result["queues"]["M2 异常页与低置信字"]), 1)
        for name in (
            "M3 边界分歧",
            "M4 类别分歧",
            "M6 待签发",
            "M7 待裁决",
        ):
            self.assertEqual(result["queues"][name], [])

    def test_pending_queue_non_human_stage_goes_to_non_human_pending(self):
        stubs = self.all_stubs({"m5": StubModule("m5", human_queue=True)})
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)
        run_until(
            self.adapter, registry, handle, "m5", modules=modules, stages=EDITION_STAGES
        )

        result = pending_queue(self.adapter, registry, handle)
        self.assertTrue(result["non_human_pending"])
        self.assertEqual(result["non_human_pending"][0]["stage"], "m5")
        self.assertIn("reason", result["non_human_pending"][0])

    def test_blocking_reasons_lists_first_blocked_stage_checks(self):
        stubs = self.all_stubs({"m2": StubModule("m2", human_queue=True)})
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)
        run_until(
            self.adapter, registry, handle, "m2", modules=modules, stages=EDITION_STAGES
        )

        result = blocking_reasons(self.adapter, registry, handle)
        self.assertTrue(result["blocking"])
        self.assertTrue(all(item["stage"] == "m2" for item in result["blocking"]))
        checks = {item["check"] for item in result["blocking"]}
        self.assertIn("all_tasks_succeeded", checks)
        self.assertIn("no_pending_work", checks)

    def test_rework_threshold_warning_after_three_supersedes(self):
        stub = StubModule("m1")
        registry = self.registry_with([stub])
        modules = {stub.module_id: stub}
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        previous = None
        for _ in range(4):
            configuration_revision_id = self.seed_configuration(
                processing_run_id, stage="m1", module_id=stub.module_id
            )
            request = make_step_request(processing_run_id, configuration_revision_id)
            if previous is None:
                self.adapter.begin_step_run(request)
            else:
                self.adapter.supersede_step_run(previous, request)
            previous = request["step_run_id"]

        result = blocking_reasons(self.adapter, registry, handle)
        self.assertTrue(
            any(
                warning["code"] == "rework_threshold_exceeded"
                for warning in result["warnings"]
            )
        )

    def test_stage_progress_passed_blocked_not_started(self):
        stubs = self.all_stubs({"m2": StubModule("m2", human_queue=True)})
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)
        run_until(
            self.adapter, registry, handle, "m2", modules=modules, stages=EDITION_STAGES
        )

        progress = stage_progress(self.adapter, registry, handle)
        self.assertEqual(list(progress), list(EDITION_STAGES))
        self.assertEqual(progress["m1"]["gate"], "passed")
        self.assertEqual(progress["m2"]["gate"], "blocked")
        self.assertEqual(progress["m3"]["gate"], "not_started")
        self.assertTrue(progress["m2"]["failed_checks"])

    def test_run_status_edition_part_complete_false_then_true(self):
        stubs = self.all_stubs()
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        self.assertFalse(run_status(self.adapter, registry, handle)["edition_part_complete"])
        run_until(
            self.adapter, registry, handle, "m6", modules=modules, stages=EDITION_STAGES
        )
        status = run_status(self.adapter, registry, handle)
        self.assertTrue(status["edition_part_complete"])
        self.assertEqual(status["processing_run_id"], processing_run_id)
        self.assertEqual(status["edition_part_id"], edition_part_id)

    def test_rework_impact_reaches_downstream_stages(self):
        stubs = self.all_stubs()
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)
        run_until(
            self.adapter, registry, handle, "m4", modules=modules, stages=EDITION_STAGES
        )

        trigger = self.package_revision(handle, "m1")
        impact = rework_impact(self.adapter, registry, handle, trigger)
        self.assertIs(impact["estimate"], True)
        self.assertEqual(impact["trigger_revision_id"], trigger)
        for stage in ("m2", "m3", "m4"):
            self.assertIn(stage, impact["affected_stages"])
        self.assertEqual(impact["trigger_correction_request_id"], None)
        self.assertIsInstance(impact["invalidated_count"], int)

    def test_rework_impact_unknown_revision_ref_001(self):
        stubs = self.all_stubs()
        registry = self.registry_with(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)
        with self.assertRaises(MissingReference) as ctx:
            rework_impact(self.adapter, registry, handle, "rev_" + "a" * 32)
        self.assertEqual(ctx.exception.code, "REF_001")

    def test_throughput_none_without_history_and_number_with_history(self):
        stubs = self.all_stubs()
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        empty = throughput_estimate(self.adapter, registry, handle)
        self.assertIsNone(empty["estimated_remaining_seconds"])
        self.assertEqual(empty["basis"], "succeeded_step_runs")

        run_until(
            self.adapter, registry, handle, "m2", modules=modules, stages=EDITION_STAGES
        )
        filled = throughput_estimate(self.adapter, registry, handle)
        self.assertIsNotNone(filled["estimated_remaining_seconds"])
        self.assertGreaterEqual(filled["estimated_remaining_seconds"], 0)
        self.assertIsInstance(filled["per_stage_seconds"]["m1"], float)

    def test_queries_are_zero_write(self):
        stubs = self.all_stubs({"m2": StubModule("m2", human_queue=True)})
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)
        run_until(
            self.adapter, registry, handle, "m2", modules=modules, stages=EDITION_STAGES
        )
        trigger = self.package_revision(handle, "m1")

        before = self.row_counts()
        run_status(self.adapter, registry, handle)
        stage_progress(self.adapter, registry, handle)
        pending_queue(self.adapter, registry, handle)
        blocking_reasons(self.adapter, registry, handle)
        rework_impact(self.adapter, registry, handle, trigger)
        throughput_estimate(self.adapter, registry, handle)
        self.assertEqual(before, self.row_counts())


if __name__ == "__main__":
    unittest.main()
