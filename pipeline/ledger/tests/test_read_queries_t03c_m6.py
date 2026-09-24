"""TODO.md T03c：M6（``pipeline/review``）清零时新增的只读查询。

``review/step.py`` 原先自己写 SQL 查「某 StepRun 的 stage_checkpoints 元数据行」
（最新一行的 ``edition_part_id``、带 ReworkImpactReport 的那一行）。这里验证替代它的
端口方法：结果与原 SQL 一致（按 rowid 写入顺序）、服务端与只读端同名同义、进了端口闭集
且 socket 客户端也有。
"""

import unittest

from pipeline.ledger import ids
from pipeline.ledger.service import LedgerReader
from pipeline.ledger.tests.test_service import ServiceTestBase

# 本次（M6）新增的端口方法
METHODS = (
    "list_step_run_checkpoints",
)


class ListStepRunCheckpointsTest(ServiceTestBase):
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

    def test_returns_only_this_step_runs_checkpoints_in_write_order(self):
        pr = self.new_processing_run()
        part = ids.new_id("artifact_id")
        other_part = ids.new_id("artifact_id")
        step, _ = self.begin(pr, stage="m6")
        other, _ = self.begin(pr, stage="m6")
        self.assertEqual(self.service.list_step_run_checkpoints(step), [])
        self.assertEqual(
            self.service.list_step_run_checkpoints(ids.new_id("step_run_id")), []
        )

        _, report = self.put_sealed(step, "rework_impact_report", b"{}")
        first = self._checkpoint(step, part, "m6")
        second = self._checkpoint(step, part, "m6", report=report)
        self._checkpoint(other, other_part, "m6")

        rows = self.service.list_step_run_checkpoints(step)
        # 写入顺序（rowid），不是 created_at 序；只含本 StepRun
        self.assertEqual(
            [row["artifact_revision_id"] for row in rows], [first, second]
        )
        self.assertEqual(
            [row["step_run_id"] for row in rows], [step, step]
        )
        self.assertEqual(rows[0]["edition_part_id"], part)
        self.assertIsNone(rows[0]["rework_impact_report_revision_id"])
        self.assertEqual(rows[-1]["rework_impact_report_revision_id"], report)
        for row in rows:
            self.assertEqual(row["stage"], "m6")
            self.assertTrue(row["artifact_id"])
            self.assertTrue(row["actor_ref"])
            self.assertTrue(row["created_at"])
            self.assertIn("prev_checkpoint_revision_id", row)

        reader = LedgerReader(self.root)
        self.addCleanup(reader.close)
        self.assertEqual(reader.list_step_run_checkpoints(step), rows)


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
