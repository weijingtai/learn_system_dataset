"""TODO.md T03c：LedgerPort 为 M1/M2/M4/M6/M7 新增的只读查询。

这 5 个包原先在模块里自己写 SQL（``.store.conn.execute``）、直接读对象存储（``.objects.get``），
共 111 处绕过端口。这里验证替代它们的端口方法：结果与原 SQL 一致、服务端与只读端同名同义、
进了端口闭集且 socket 客户端也有。
"""

import unittest

from pipeline.ledger import ids
from pipeline.ledger.service import LedgerReader
from pipeline.ledger.tests.test_service import ServiceTestBase

# 本任务新增的端口方法（随各包清零逐步追加）
T03C_METHODS = (
    "latest_processing_run",
    "latest_checkpoint_step_run",
    "list_human_events",
    "list_transformation_inputs",
    "list_transformation_outputs",
    "list_transformation_human_events",
    "list_revisions",
)


class LatestProcessingRunTest(ServiceTestBase):
    def test_returns_newest_run_of_kind_for_edition_part(self):
        edition_part_id = ids.new_id("artifact_id")
        self.assertIsNone(self.service.latest_processing_run(edition_part_id, "edition_run"))
        first = self.service.create_processing_run("edition_run", edition_part_id, "qizheng")
        second = self.service.create_processing_run("edition_run", edition_part_id, "qizheng")
        self.service.create_processing_run("release_run", edition_part_id, "qizheng")
        self.service.create_processing_run("edition_run", ids.new_id("artifact_id"), "qizheng")
        self.assertNotEqual(first, second)
        self.assertEqual(self.service.latest_processing_run(edition_part_id, "edition_run"), second)
        reader = LedgerReader(self.root)
        self.addCleanup(reader.close)
        self.assertEqual(reader.latest_processing_run(edition_part_id, "edition_run"), second)


class CheckpointStepRunTest(ServiceTestBase):
    def _checkpoint(self, step_run_id, edition_part_id, stage):
        return self.service.write_checkpoint(
            step_run_id,
            edition_part_id=edition_part_id,
            stage=stage,
            completed_tasks=[],
            human_decisions=[],
            pending_queue=[],
            next_pointer=None,
        )

    def test_latest_checkpoint_step_run_only_counts_steps_in_status(self):
        pr = self.new_processing_run()
        part = ids.new_id("artifact_id")
        self.assertIsNone(self.service.latest_checkpoint_step_run(part, "m4", "succeeded"))
        done, _ = self.begin(pr, stage="m4")
        running, _ = self.begin(pr, stage="m4")
        self._checkpoint(done, part, "m4")
        self._checkpoint(running, part, "m4")
        self.service.finish_step_run(done, self.result(pr, done))
        other_stage, _ = self.begin(pr, stage="m5")
        self._checkpoint(other_stage, part, "m5")
        self.service.finish_step_run(other_stage, self.result(pr, other_stage))
        # running 的检查点更新，但只认 succeeded
        self.assertEqual(self.service.latest_checkpoint_step_run(part, "m4", "succeeded"), done)
        self.assertEqual(self.service.latest_checkpoint_step_run(part, "m4", "running"), running)
        self.assertIsNone(self.service.latest_checkpoint_step_run(ids.new_id("artifact_id"), "m4", "succeeded"))


class HumanEventAndTransformationTest(ServiceTestBase):
    def test_human_events_in_write_order_and_transformation_links(self):
        pr = self.new_processing_run()
        step, config = self.begin(pr, stage="m1")
        _, queued = self.put_sealed(step, "ocr_page", b"pending")
        token = self.service.await_human(step, [queued])
        events = []
        for index, decision_type in enumerate((None, "review_source_fidelity", None)):
            _, event = self.put_sealed(step, "human_event", b"{\"n\": %d}" % index)
            self.service.record_human_event(step, token, event, decision_type=decision_type)
            events.append(event)
        self.service.resume(step, token)
        rows = self.service.list_human_events(step)
        self.assertEqual([row["event_revision_id"] for row in rows], events)
        self.assertEqual([row["decision_type"] for row in rows], [None, "review_source_fidelity", None])
        self.assertEqual({row["step_run_id"] for row in rows}, {step})
        self.assertTrue(all(row["created_at"] for row in rows))
        self.assertEqual(self.service.list_human_events(ids.new_id("step_run_id")), [])
        self.assertEqual(
            [row["event_revision_id"] for row in self.service.list_human_events()], events
        )

        _, out_a = self.put_sealed(step, "source_manifest", b"a")
        _, out_b = self.put_sealed(step, "source_manifest", b"b")
        transformation_id = self.service.record_transformation(
            step,
            operation="t03c",
            tool="tests",
            tool_version="1.0",
            configuration_revision_id=config,
            input_revision_ids=[],
            output_revision_ids=[out_b, out_a],
            human_event_revision_ids=list(reversed(events)),
        )
        # 与原 SQL 实际返回顺序一致：主键覆盖索引序（修订号升序）
        self.assertEqual(self.service.list_transformation_outputs(transformation_id), sorted([out_a, out_b]))
        self.assertEqual(self.service.list_transformation_inputs(transformation_id), [])
        self.assertEqual(self.service.list_transformation_human_events(transformation_id), sorted(events))
        reader = LedgerReader(self.root)
        self.addCleanup(reader.close)
        self.assertEqual(reader.list_human_events(step), rows)
        self.assertEqual(reader.list_transformation_human_events(transformation_id), sorted(events))


class ListRevisionsTest(ServiceTestBase):
    def test_filters_and_write_order(self):
        pr = self.new_processing_run()
        step_a, _ = self.begin(pr, stage="m1")
        _, a1 = self.put_sealed(step_a, "ocr_page", b"a1")
        step_b, _ = self.begin(pr, stage="m2")
        _, b1 = self.put_sealed(step_b, "ocr_page", b"b1")
        _, a2 = self.service.put_artifact(step_a, "ocr_page", b"a2", producer_module="tests", producer_version="1.0")
        # 写入顺序（rowid），跨 StepRun
        pages = self.service.list_revisions(artifact_type="ocr_page")
        self.assertEqual([row["artifact_revision_id"] for row in pages], [a1, b1, a2])
        self.assertEqual(
            [row["artifact_revision_id"] for row in self.service.list_revisions(artifact_type="ocr_page", status="sealed")],
            [a1, b1],
        )
        self.assertEqual(
            [row["artifact_revision_id"] for row in self.service.list_revisions(artifact_type="ocr_page", step_run_ids=[step_a])],
            [a1, a2],
        )
        self.assertEqual(
            [row["artifact_revision_id"] for row in self.service.list_revisions(step_run_ids=[step_b, step_a], artifact_type="ocr_page")],
            [a1, b1, a2],
        )
        self.assertEqual(self.service.list_revisions(step_run_ids=[]), [])
        by_run = self.service.list_revisions(processing_run_id=pr, artifact_type="ocr_page")
        self.assertEqual(len(by_run), 3)
        self.assertEqual(self.service.list_revisions(processing_run_id=self.new_processing_run()), [])
        # 形状：describe_revision 的字段 + prev_revision_id
        row = pages[0]
        info = self.service.describe_revision(a1)
        for key, value in info.items():
            self.assertEqual(row[key], value, key)
        self.assertIn("prev_revision_id", row)
        self.assertIsNone(row["prev_revision_id"])
        reader = LedgerReader(self.root)
        self.addCleanup(reader.close)
        self.assertEqual(reader.list_revisions(artifact_type="ocr_page"), pages)


class PortMethodSetTest(unittest.TestCase):
    def test_new_queries_are_in_the_port_closed_set_and_on_all_backends(self):
        from pipeline.contract_registry.ports import LEDGER_PORT_METHODS
        from pipeline.ledger.client import LedgerClient
        from pipeline.ledger.service import LedgerService

        for name in T03C_METHODS:
            with self.subTest(name=name):
                self.assertIn(name, LEDGER_PORT_METHODS)
                self.assertTrue(callable(getattr(LedgerService, name, None)))
                self.assertTrue(callable(getattr(LedgerReader, name, None)))
                self.assertTrue(callable(getattr(LedgerClient, name, None)))


if __name__ == "__main__":
    unittest.main()
