"""TODO.md T03c（M6 ``review/acceptance.py``）：清零时新增的只读查询。

``review/acceptance.py`` 原先自己写 SQL 查三类账本元数据：某 stage 的全部 Checkpoint
所属 StepRun 号（去重）、某修订最早的 ``sealed`` 状态事件时间、引用某 ReworkImpactReport
的 Checkpoint 条数。这里验证替代它们的端口方法：结果与原 SQL 一致、服务端与只读端同名同义、
进了端口闭集且 socket 客户端也有。
"""

import unittest

from pipeline.ledger import ids
from pipeline.ledger.service import LedgerReader
from pipeline.ledger.tests.test_service import ServiceTestBase

# 本次（M6 acceptance）新增的端口方法
METHODS = (
    "list_stage_checkpoint_step_runs",
    "first_sealed_event_created_at",
    "count_checkpoints_by_rework_report",
)


class _CheckpointMixin(ServiceTestBase):
    def _checkpoint(self, step_run_id, edition_part_id, stage, report=None):
        return self.service.write_checkpoint(
            step_run_id,
            edition_part_id=edition_part_id,
            stage=stage,
            completed_tasks=[],
            human_decisions=[],
            pending_queue=[],
            next_pointer=None,
            rework_impact_report_revision_id=report,
        )


class ListStageCheckpointStepRunsTest(_CheckpointMixin):
    def test_returns_distinct_step_runs_of_that_stage_in_write_order(self):
        pr = self.new_processing_run()
        part = ids.new_id("artifact_id")
        step_a, _ = self.begin(pr, stage="m6")
        step_b, _ = self.begin(pr, stage="m6")
        step_m5, _ = self.begin(pr, stage="m5")
        self.assertEqual(self.service.list_stage_checkpoint_step_runs("m7"), [])

        self._checkpoint(step_a, part, "m6")
        self._checkpoint(step_m5, part, "m5")
        self._checkpoint(step_b, part, "m6")
        self._checkpoint(step_a, part, "m6")  # 同一运行第二个 Checkpoint 不重复

        # 去重、只含该 stage、按首次写入顺序
        self.assertEqual(
            self.service.list_stage_checkpoint_step_runs("m6"), [step_a, step_b]
        )
        self.assertEqual(
            self.service.list_stage_checkpoint_step_runs("m5"), [step_m5]
        )

        reader = LedgerReader(self.root)
        self.addCleanup(reader.close)
        self.assertEqual(reader.list_stage_checkpoint_step_runs("m6"), [step_a, step_b])


class FirstSealedEventCreatedAtTest(ServiceTestBase):
    def test_returns_earliest_sealed_event_time_and_none_otherwise(self):
        pr = self.new_processing_run()
        step, _ = self.begin(pr, stage="m1")
        _, sealed = self.put_sealed(step, "source_manifest", b"x")
        _, unsealed = self.service.put_artifact(
            step, "source_manifest", b"y", producer_module="tests", producer_version="1.0"
        )
        expected = self.service.store.conn.execute(
            "SELECT created_at FROM revision_status_events "
            "WHERE artifact_revision_id=? AND to_status='sealed' "
            "ORDER BY created_at LIMIT 1",
            (sealed,),
        ).fetchone()[0]
        self.assertEqual(self.service.first_sealed_event_created_at(sealed), expected)
        self.assertIsNone(self.service.first_sealed_event_created_at(unsealed))
        self.assertIsNone(
            self.service.first_sealed_event_created_at(ids.new_id("artifact_revision_id"))
        )

        reader = LedgerReader(self.root)
        self.addCleanup(reader.close)
        self.assertEqual(reader.first_sealed_event_created_at(sealed), expected)


class CountCheckpointsByReworkReportTest(_CheckpointMixin):
    def test_counts_only_checkpoints_referencing_that_report(self):
        pr = self.new_processing_run()
        part = ids.new_id("artifact_id")
        step, _ = self.begin(pr, stage="m6")
        _, report = self.put_sealed(step, "rework_impact_report", b"{}")
        _, other = self.put_sealed(step, "rework_impact_report", b"{}")
        self.assertEqual(self.service.count_checkpoints_by_rework_report(report), 0)

        self._checkpoint(step, part, "m6", report=report)
        self._checkpoint(step, part, "m6")
        self._checkpoint(step, part, "m6", report=other)
        self._checkpoint(step, part, "m6", report=report)

        self.assertEqual(self.service.count_checkpoints_by_rework_report(report), 2)
        self.assertEqual(self.service.count_checkpoints_by_rework_report(other), 1)
        self.assertEqual(
            self.service.count_checkpoints_by_rework_report(
                ids.new_id("artifact_revision_id")
            ),
            0,
        )

        reader = LedgerReader(self.root)
        self.addCleanup(reader.close)
        self.assertEqual(reader.count_checkpoints_by_rework_report(report), 2)


class PortMethodSetTest(unittest.TestCase):
    def test_new_queries_are_in_the_port_closed_set_and_on_all_backends(self):
        from pipeline.contract_registry.ports import LEDGER_PORT_METHODS
        from pipeline.ledger.client import LedgerClient
        from pipeline.ledger.service import LedgerService

        for name in METHODS:
            with self.subTest(name=name):
                self.assertIn(name, LEDGER_PORT_METHODS)
                self.assertTrue(callable(getattr(LedgerService, name, None)))
                self.assertTrue(callable(getattr(LedgerReader, name, None)))
                self.assertTrue(callable(getattr(LedgerClient, name, None)))


if __name__ == "__main__":
    unittest.main()
