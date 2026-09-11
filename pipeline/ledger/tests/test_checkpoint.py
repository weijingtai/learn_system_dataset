"""ACT impl-01/03：StageCheckpoint（规格 §17.1）的单元测试。

先写本文件，与 ``test_service.py`` 一起运行并全红（``pipeline.ledger.service`` 尚不存在）。
所有用例只使用 ``tempfile`` 目录，绝不写 ``var/`` 或 fixture。
"""

import json
import unittest

from pipeline.ledger import ids
from pipeline.ledger.errors import LedgerError
from pipeline.ledger.tests.test_service import ServiceTestBase


class TestStageCheckpoint(ServiceTestBase):
    """覆盖 §17.1：每 task 落盘、单链、必含 11 项内容、恢复语义与阶段封存后禁写。"""

    # ------------------------------------------------------------ 脚手架
    def write(self, step_run_id, edition_part_id, stage, completed_tasks=(),
              human_decisions=(), pending_queue=(), next_pointer=None,
              rework_impact_report_revision_id=None):
        return self.service.write_checkpoint(
            step_run_id,
            edition_part_id=edition_part_id,
            stage=stage,
            completed_tasks=list(completed_tasks),
            human_decisions=list(human_decisions),
            pending_queue=list(pending_queue),
            next_pointer=next_pointer,
            rework_impact_report_revision_id=rework_impact_report_revision_id,
        )

    def task(self, step_run_id, task_id, status="succeeded",
             artifact_type="source_manifest", data=None, terminal_state=None):
        """构造一个 completed_tasks 项（输出修订为已 sealed 修订）。"""
        payload = data if data is not None else ("out:" + task_id).encode("utf-8")
        _, revision_id = self.put_sealed(step_run_id, artifact_type, payload)
        return {
            "task_id": task_id,
            "artifact_revision_id": revision_id,
            "status": status,
            "terminal_state": terminal_state,
        }

    def checkpoint_content(self, revision_id):
        row = self.service.store.get_revision(revision_id)
        return json.loads(self.service.objects.get(row["sha256"]).decode("utf-8"))

    def start(self, stage="m1", processing_run_id=None):
        processing_run_id = processing_run_id or self.new_processing_run()
        edition_part_id = ids.new_id("artifact_id")
        step_run_id, _ = self.begin(processing_run_id, stage)
        return processing_run_id, edition_part_id, step_run_id

    # --------------------------------------------------------------- 用例
    def test_checkpoint_chain_prev_pointer_and_single_chain(self):
        processing_run_id, part, step_run_id = self.start("m1")
        written = []
        for index in range(3):
            task = self.task(step_run_id, "task_%d" % index)
            written.append(
                self.write(
                    step_run_id,
                    part,
                    "m1",
                    completed_tasks=[task],
                    pending_queue=[{"task_id": "task_%d" % (index + 1)}],
                    next_pointer={"task_id": "task_%d" % (index + 1)},
                )
            )
        self.assertEqual(len(set(written)), 3)

        # 跨 StepRun 接链：新运行（supersedes 旧运行）继续同一条链
        config = self.seed_configuration(processing_run_id, "m1")
        rerun_id = ids.new_id("step_run_id")
        self.service.supersede_step_run(
            step_run_id,
            self.request(processing_run_id, rerun_id, config),
        )
        written.append(
            self.write(
                rerun_id,
                part,
                "m1",
                completed_tasks=[self.task(rerun_id, "task_3")],
            )
        )

        chain = self.service.list_checkpoints(part, "m1")
        self.assertEqual(
            [row["artifact_revision_id"] for row in chain], written
        )
        self.assertIsNone(chain[0]["prev_checkpoint_revision_id"])
        for previous, current in zip(chain, chain[1:]):
            self.assertEqual(
                current["prev_checkpoint_revision_id"],
                previous["artifact_revision_id"],
            )
        self.assertEqual(
            self.service.latest_checkpoint(part, "m1")["artifact_revision_id"],
            written[-1],
        )
        # 只有一条链：别的 EditionPart 看不到任何 Checkpoint
        self.assertEqual(
            self.service.list_checkpoints(ids.new_id("artifact_id"), "m1"), []
        )

    def test_checkpoint_content_has_all_required_fields(self):
        _, part, step_run_id = self.start("m1")
        task = self.task(step_run_id, "ingest_source")
        _, decision = self.put_sealed(step_run_id, "human_event", b"{}")
        first = self.write(
            step_run_id,
            part,
            "m1",
            completed_tasks=[task],
            human_decisions=[decision],
            pending_queue=[{"task_id": "next"}],
            next_pointer={"task_id": "next"},
            rework_impact_report_revision_id=None,
        )
        row = self.service.store.get_revision(first)
        self.assertEqual(row["status"], "sealed")
        self.assertEqual(self.artifact_type_of(first), "stage_checkpoint")

        content = self.checkpoint_content(first)
        self.assertEqual(
            set(content.keys()),
            {
                "edition_part_id",
                "stage",
                "step_run_id",
                "completed_tasks",
                "human_decisions",
                "pending_queue",
                "next_pointer",
                "actor_ref",
                "created_at",
                "prev_checkpoint_revision_id",
                "rework_impact_report_revision_id",
            },
        )
        self.assertEqual(content["edition_part_id"], part)
        self.assertEqual(content["stage"], "m1")
        self.assertEqual(content["step_run_id"], step_run_id)
        self.assertEqual(content["human_decisions"], [decision])
        self.assertEqual(content["pending_queue"], [{"task_id": "next"}])
        self.assertEqual(content["next_pointer"], {"task_id": "next"})
        self.assertEqual(content["actor_ref"], self.actor())
        self.assertIsNone(content["prev_checkpoint_revision_id"])
        self.assertIsNone(content["rework_impact_report_revision_id"])
        self.assertTrue(content["created_at"])
        self.assertEqual(
            [item["task_id"] for item in content["completed_tasks"]],
            ["ingest_source"],
        )

        second = self.write(
            step_run_id, part, "m1", completed_tasks=[self.task(step_run_id, "t2")]
        )
        self.assertEqual(
            self.checkpoint_content(second)["prev_checkpoint_revision_id"], first
        )
        # 元数据行与内容 JSON 都返回
        latest = self.service.latest_checkpoint(part, "m1")
        self.assertEqual(latest["artifact_revision_id"], second)
        self.assertEqual(latest["content"]["prev_checkpoint_revision_id"], first)

    def test_checkpoint_per_task_not_per_stage(self):
        processing_run_id, part, step_run_id = self.start("m2")
        tasks = ["page_001", "page_002", "page_003"]
        for index, name in enumerate(tasks):
            task = self.task(
                step_run_id,
                name,
                terminal_state="known_unrecognizable" if name == "page_002" else None,
            )
            remaining = [{"task_id": other} for other in tasks[index + 1:]]
            self.write(
                step_run_id,
                part,
                "m2",
                completed_tasks=[task],
                pending_queue=remaining,
                next_pointer=remaining[0] if remaining else None,
            )
        chain = self.service.list_checkpoints(part, "m2")
        # 3 个 task → 3 次落盘（不允许以阶段结束为唯一落盘点）
        self.assertEqual(len(chain), 3)
        contents = [
            self.checkpoint_content(item["artifact_revision_id"])
            for item in chain
        ]
        self.assertEqual(
            [len(content["completed_tasks"]) for content in contents], [1, 1, 1]
        )
        self.assertEqual(
            [
                content["completed_tasks"][0]["terminal_state"]
                for content in contents
            ],
            [None, "known_unrecognizable", None],
        )
        self.assertTrue(processing_run_id)

    def test_recover_from_checkpoint_skips_completed_and_replays_pending(self):
        processing_run_id, part, step_run_id = self.start("m3")
        done = self.task(step_run_id, "sanche_b001")
        done_two = self.task(step_run_id, "sanche_b002")
        still_pending = [{"task_id": name} for name in
                         ("sanche_b003", "sanche_b004", "sanche_b005")]
        checkpoint = self.write(
            step_run_id,
            part,
            "m3",
            completed_tasks=[done, done_two],
            human_decisions=[],
            pending_queue=still_pending,
            next_pointer=still_pending[0],
        )
        config = self.seed_configuration(processing_run_id, "m3")
        new_step_run_id = ids.new_id("step_run_id")
        returned, plan = self.service.recover_from_checkpoint(
            part,
            "m3",
            self.request(processing_run_id, new_step_run_id, config),
        )
        self.assertEqual(returned, new_step_run_id)
        self.assertEqual(plan["checkpoint_revision_id"], checkpoint)
        self.assertEqual(
            plan["completed_task_ids"], ["sanche_b001", "sanche_b002"]
        )
        self.assertEqual(
            [item["task_id"] for item in plan["pending_queue"]],
            ["sanche_b003", "sanche_b004", "sanche_b005"],
        )
        self.assertEqual(plan["next_pointer"], still_pending[0])
        self.assertEqual(plan["human_decisions"], [])

    def test_recover_creates_new_step_run_with_supersedes_and_recovery_event(self):
        processing_run_id, part, step_run_id = self.start("m3")
        self.write(
            step_run_id,
            part,
            "m3",
            completed_tasks=[self.task(step_run_id, "sanche_b001")],
            pending_queue=[{"task_id": "sanche_b002"}],
            next_pointer={"task_id": "sanche_b002"},
        )
        config = self.seed_configuration(processing_run_id, "m3")
        new_step_run_id = ids.new_id("step_run_id")
        returned, _ = self.service.recover_from_checkpoint(
            part,
            "m3",
            self.request(processing_run_id, new_step_run_id, config),
        )
        row = self.service.store.get_step_run(returned)
        self.assertEqual(row["supersedes_step_run_id"], step_run_id)
        self.assertEqual(row["status"], "running")
        recovery = self.events(returned, "recovery")
        self.assertEqual(len(recovery), 1)
        self.assertEqual(
            json.loads(recovery[0]["payload_json"])["checkpoint_revision_id"],
            self.service.latest_checkpoint(part, "m3")["artifact_revision_id"],
        )

    def test_failed_task_recorded_in_completed_list_with_failed_flag_and_must_be_redone(self):
        processing_run_id, part, step_run_id = self.start("m3")
        succeeded = self.task(step_run_id, "sanche_b001")
        failed = self.task(
            step_run_id,
            "sanche_b002",
            status="failed",
            artifact_type="failure_report",
            data=b"boom",
            terminal_state="failed",
        )
        pending = [{"task_id": "sanche_b002"}, {"task_id": "sanche_b003"}]
        self.write(
            step_run_id,
            part,
            "m3",
            completed_tasks=[succeeded, failed],
            pending_queue=pending,
            next_pointer=pending[0],
        )
        config = self.seed_configuration(processing_run_id, "m3")
        new_step_run_id = ids.new_id("step_run_id")
        _, plan = self.service.recover_from_checkpoint(
            part,
            "m3",
            self.request(processing_run_id, new_step_run_id, config),
        )
        # 失败 task 仍记入已完成清单并标记，但恢复时须重做（不在 completed_task_ids）
        self.assertEqual(plan["completed_task_ids"], ["sanche_b001"])
        self.assertNotIn("sanche_b002", plan["completed_task_ids"])
        self.assertIn("sanche_b002", [item["task_id"] for item in plan["pending_queue"]])
        content = self.checkpoint_content(
            self.service.latest_checkpoint(part, "m3")["artifact_revision_id"]
        )
        failed_items = [
            item for item in content["completed_tasks"] if item["status"] == "failed"
        ]
        self.assertEqual(len(failed_items), 1)
        self.assertEqual(failed_items[0]["task_id"], "sanche_b002")
        self.assertEqual(failed_items[0]["terminal_state"], "failed")
        self.assertTrue(
            self.service.store.get_revision(failed_items[0]["artifact_revision_id"])
        )

    def test_backfill_checkpoint_when_human_event_newer_than_checkpoint(self):
        processing_run_id, part, step_run_id = self.start("m2")
        self.write(
            step_run_id,
            part,
            "m2",
            completed_tasks=[self.task(step_run_id, "page_001")],
            human_decisions=[],
            pending_queue=[{"task_id": "page_002"}],
            next_pointer={"task_id": "page_002"},
        )
        queued = self.task(step_run_id, "page_002")
        token = self.service.await_human(
            step_run_id, [queued["artifact_revision_id"]]
        )
        _, decision = self.put_sealed(step_run_id, "human_event", b"{}")
        self.service.record_human_event(step_run_id, token, decision)

        before = len(self.service.list_checkpoints(part, "m2"))
        config = self.seed_configuration(processing_run_id, "m2")
        new_step_run_id = ids.new_id("step_run_id")
        self.service.recover_from_checkpoint(
            part,
            "m2",
            self.request(processing_run_id, new_step_run_id, config),
        )
        after = self.service.list_checkpoints(part, "m2")
        # 最后一个 Checkpoint 早于最后一次已接受人工决定 → 先补写再恢复
        self.assertEqual(len(after), before + 1)
        self.assertIn(decision, after[-1]["content"]["human_decisions"])
        self.assertEqual(len(after[-1]["content"]["human_decisions"]), 1)

    def test_sealed_stage_rejects_new_checkpoint_from_unrelated_step_run(self):
        processing_run_id, part, step_run_id = self.start("m1")
        first = self.write(
            step_run_id,
            part,
            "m1",
            completed_tasks=[self.task(step_run_id, "ingest_source")],
        )
        _, out = self.put_sealed(step_run_id, "source_manifest", b"m1-out")
        self.service.finish_step_run(
            step_run_id, self.result(processing_run_id, step_run_id, outputs=[out])
        )

        # 与已 succeeded 的 StepRun 无关的新运行不得再写该 (EditionPart, Stage)
        unrelated, _ = self.begin(processing_run_id, "m1")
        with self.assertRaises(LedgerError):
            self.write(
                unrelated,
                part,
                "m1",
                completed_tasks=[self.task(unrelated, "again")],
            )
        self.assertEqual(
            self.service.latest_checkpoint(part, "m1")["artifact_revision_id"], first
        )

        # 显式 supersedes 该 StepRun 的新运行可以续写
        config = self.seed_configuration(processing_run_id, "m1")
        rerun_id = ids.new_id("step_run_id")
        self.service.supersede_step_run(
            step_run_id, self.request(processing_run_id, rerun_id, config)
        )
        allowed = self.write(
            rerun_id,
            part,
            "m1",
            completed_tasks=[self.task(rerun_id, "again")],
        )
        self.assertEqual(
            self.service.latest_checkpoint(part, "m1")["artifact_revision_id"],
            allowed,
        )


if __name__ == "__main__":
    unittest.main()
