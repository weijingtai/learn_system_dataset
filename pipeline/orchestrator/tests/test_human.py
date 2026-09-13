"""ACT impl-08/05：人工暂停与恢复的单元测试（规格 §7.1/§17/§17.1）。

先写本文件，运行 `.venv/bin/python -m unittest discover -s pipeline/orchestrator/tests -t .`
取得 ImportError 全红（Red），再实现 `pipeline/orchestrator/human.py`。
"""

import json
import unittest

from pipeline.ledger import ids
from pipeline.ledger.errors import InvalidResumeToken
from pipeline.orchestrator import EDITION_STAGES
from pipeline.orchestrator.edition_run import advance, run_until
from pipeline.orchestrator.errors import OrchestratorRefused
from pipeline.orchestrator.gate import evaluate_stage_gate
from pipeline.orchestrator.human import (
    reconcile_after_outage,
    record_human_event,
    recover,
    rerun_from_checkpoint,
    resume,
    suspend,
)
from pipeline.orchestrator.stubs import StubModule
from pipeline.orchestrator.tests.scaffold import make_step_request
from pipeline.orchestrator.tests.test_edition_run import EditionTestCase


class HumanTestCase(EditionTestCase):
    """公共脚手架：默认 m2 需人工、m4 可用 Checkpoint 重跑。"""

    def human_stubs(self, overrides=None):
        overrides = dict(overrides or {})
        overrides.setdefault("m2", StubModule("m2", human_queue=True))
        overrides.setdefault("m4", StubModule("m4", fail_on_task="t2"))
        return self.all_stubs(overrides)

    def to_m2_awaiting(self, stubs):
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)
        results = run_until(
            self.adapter, registry, handle, "m2", modules=modules, stages=EDITION_STAGES
        )
        item = results[-1]
        return (
            registry,
            modules,
            handle,
            item["step_run_id"],
            item["step_result"]["resume_token"],
        )

    def seal_human_event(self, step_run_id, decision="accept"):
        _artifact_id, revision_id = self.adapter.put_artifact(
            step_run_id,
            "human_event",
            json.dumps({"decision": decision}, sort_keys=True).encode("utf-8"),
            producer_module="tests",
            producer_version="1.0",
        )
        self.adapter.seal_revision(revision_id)
        return revision_id

    def begin_only(self, stub, processing_run_id, edition_part_id):
        configuration_revision_id = self.seed_configuration(
            processing_run_id, stage=stub.stage, module_id=stub.module_id, tasks=stub.tasks
        )
        request = make_step_request(processing_run_id, configuration_revision_id)
        self.adapter.begin_step_run(request)
        return request


class TestHumanRecovery(HumanTestCase):
    """覆盖 BDD §6：人工事件、恢复、对账与 Checkpoint 重跑。"""

    def test_record_human_event_writes_checkpoint_immediately(self):
        stubs = self.human_stubs()
        registry, modules, handle, step_run_id, token = self.to_m2_awaiting(stubs)
        before = len(self.adapter.list_checkpoints(handle["edition_part_id"], "m2"))
        event = self.seal_human_event(step_run_id)

        record_human_event(
            self.adapter, registry, handle, step_run_id, token, event, modules=modules
        )

        after = len(self.adapter.list_checkpoints(handle["edition_part_id"], "m2"))
        self.assertEqual(after, before + 1)
        latest = self.adapter.latest_checkpoint(handle["edition_part_id"], "m2")
        self.assertIn(event, latest["content"]["human_decisions"])

    def test_record_does_not_consume_token(self):
        stubs = self.human_stubs()
        registry, modules, handle, step_run_id, token = self.to_m2_awaiting(stubs)
        first = self.seal_human_event(step_run_id, "first")
        second = self.seal_human_event(step_run_id, "second")
        record_human_event(
            self.adapter, registry, handle, step_run_id, token, first, modules=modules
        )
        record_human_event(
            self.adapter, registry, handle, step_run_id, token, second, modules=modules
        )

        result = resume(
            self.adapter, registry, handle, step_run_id, token, modules=modules
        )
        self.assertEqual(result["status"], "succeeded")

    def test_resume_reexecutes_with_human_events_and_succeeds(self):
        stubs = self.human_stubs()
        registry, modules, handle, step_run_id, token = self.to_m2_awaiting(stubs)
        event = self.seal_human_event(step_run_id)
        record_human_event(
            self.adapter, registry, handle, step_run_id, token, event, modules=modules
        )

        result = resume(
            self.adapter, registry, handle, step_run_id, token, modules=modules
        )
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(
            self.adapter.get_step_run(step_run_id)["status"], "succeeded"
        )

    def test_resume_token_replay_rejected_zero_write(self):
        stubs = self.human_stubs()
        registry, modules, handle, step_run_id, token = self.to_m2_awaiting(stubs)
        event = self.seal_human_event(step_run_id)
        record_human_event(
            self.adapter, registry, handle, step_run_id, token, event, modules=modules
        )
        resume(self.adapter, registry, handle, step_run_id, token, modules=modules)

        before = self.row_counts()
        with self.assertRaises(InvalidResumeToken):
            resume(self.adapter, registry, handle, step_run_id, token, modules=modules)
        self.assertEqual(before, self.row_counts())

    def test_resume_without_events_fails_via_stub(self):
        stubs = self.human_stubs()
        registry, modules, handle, step_run_id, token = self.to_m2_awaiting(stubs)
        result = resume(
            self.adapter, registry, handle, step_run_id, token, modules=modules
        )
        self.assertEqual(result["status"], "failed")

    def test_no_timeout_awaiting_human_stays(self):
        stubs = self.human_stubs()
        registry, modules, handle, step_run_id, _token = self.to_m2_awaiting(stubs)
        for _ in range(3):
            result = advance(
                self.adapter, registry, handle, modules=modules, stages=EDITION_STAGES
            )
            self.assertEqual(result["action"], "waiting")
        self.assertEqual(
            self.adapter.get_step_run(step_run_id)["status"], "awaiting_human"
        )

    def test_suspend_awaiting_then_recover_keeps_token(self):
        stubs = self.human_stubs()
        registry, modules, handle, step_run_id, token = self.to_m2_awaiting(stubs)
        event = self.seal_human_event(step_run_id)
        record_human_event(
            self.adapter, registry, handle, step_run_id, token, event, modules=modules
        )
        suspend(self.adapter, step_run_id, "operator pause")
        self.assertEqual(
            self.adapter.get_step_run(step_run_id)["status"], "suspended"
        )

        outcome = recover(
            self.adapter, registry, handle, step_run_id, "operator recover", modules=modules
        )
        self.assertEqual(outcome["status"], "awaiting_human")
        self.assertIsNone(outcome["step_result"])

        result = resume(
            self.adapter, registry, handle, step_run_id, token, modules=modules
        )
        self.assertEqual(result["status"], "succeeded")

    def test_suspend_running_then_recover_reexecutes_without_redo(self):
        stub = StubModule("m1")
        registry = self.registry_with([stub])
        modules = {stub.module_id: stub}
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)
        request = self.begin_only(stub, processing_run_id, edition_part_id)

        _artifact_id, revision_id = self.adapter.put_artifact(
            request["step_run_id"],
            "stub_output",
            b"m1:t1",
            producer_module="tests",
            producer_version="1.0",
        )
        self.adapter.seal_revision(revision_id)
        self.adapter.write_checkpoint(
            request["step_run_id"],
            edition_part_id=edition_part_id,
            stage="m1",
            completed_tasks=[
                {
                    "task_id": "t1",
                    "artifact_revision_id": revision_id,
                    "status": "succeeded",
                    "terminal_state": None,
                }
            ],
            human_decisions=[],
            pending_queue=[],
            next_pointer=None,
        )
        suspend(self.adapter, request["step_run_id"], "infrastructure outage")

        outcome = recover(
            self.adapter,
            registry,
            handle,
            request["step_run_id"],
            "recover after outage",
            modules=modules,
        )
        self.assertEqual(outcome["status"], "running")
        self.assertEqual(outcome["step_result"]["status"], "succeeded")
        self.assertEqual([task for _srun, task in stub.executed_tasks], ["t2"])

    def test_reconcile_after_outage_suspends_running_only(self):
        stubs = self.human_stubs()
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        m1_request, _o, _t = self.execute_stub(
            stubs[0], processing_run_id, edition_part_id
        )
        m2_request, _o2, _t2 = self.execute_stub(
            stubs[1], processing_run_id, edition_part_id
        )
        m3_request = self.begin_only(stubs[2], processing_run_id, edition_part_id)

        suspended = reconcile_after_outage(self.adapter, handle, "host outage")
        self.assertEqual(suspended, [m3_request["step_run_id"]])
        self.assertEqual(
            self.adapter.get_step_run(m1_request["step_run_id"])["status"], "succeeded"
        )
        self.assertEqual(
            self.adapter.get_step_run(m2_request["step_run_id"])["status"],
            "awaiting_human",
        )
        self.assertEqual(
            self.adapter.get_step_run(m3_request["step_run_id"])["status"], "suspended"
        )

    def test_reconcile_never_rewrites_terminal(self):
        stubs = self.human_stubs({"m4": StubModule("m4", fail_on_task="t1")})
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        m1_request, _o, _t = self.execute_stub(
            stubs[0], processing_run_id, edition_part_id
        )
        m4_request, m4_outcome, _t4 = self.execute_stub(
            stubs[3], processing_run_id, edition_part_id
        )
        self.assertEqual(m4_outcome["status"], "failed")

        suspended = reconcile_after_outage(self.adapter, handle, "host outage")
        self.assertEqual(suspended, [])
        self.assertEqual(
            self.adapter.get_step_run(m1_request["step_run_id"])["status"], "succeeded"
        )
        self.assertEqual(
            self.adapter.get_step_run(m4_request["step_run_id"])["status"], "failed"
        )

    def test_rerun_from_checkpoint_skips_completed_and_preserves_failed_history(self):
        stub = StubModule("m4", fail_on_task="t2", supports_recovery=True)
        stubs = self.all_stubs({"m4": stub})
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        run_until(
            self.adapter, registry, handle, "m4", modules=modules, stages=EDITION_STAGES
        )
        m4_runs = [
            step
            for step in self.adapter.run_status(processing_run_id)["step_runs"]
            if step["stage"] == "m4"
        ]
        old_step_run_id = m4_runs[-1]["step_run_id"]
        self.assertEqual(
            self.adapter.get_step_run(old_step_run_id)["status"], "failed"
        )
        failure_event = [
            event
            for event in self.adapter.list_step_run_events(old_step_run_id)
            if event["event_type"] == "failure"
        ][-1]
        failure_ids = json.loads(failure_event["payload_json"])["failure_revision_ids"]
        self.assertTrue(failure_ids)
        self.assertEqual(
            self.adapter.get_revision(failure_ids[0])["status"], "sealed"
        )

        stub.fail_on_task = None
        result = rerun_from_checkpoint(
            self.adapter, registry, handle, "m4", modules=modules
        )
        self.assertEqual(result["status"], "succeeded")

        new_step_run_id = [
            step["step_run_id"]
            for step in self.adapter.run_status(processing_run_id)["step_runs"]
            if step["stage"] == "m4" and step["step_run_id"] != old_step_run_id
        ][0]
        self.assertEqual(
            self.adapter.get_step_run(old_step_run_id)["status"], "failed"
        )
        self.assertEqual(
            self.adapter.get_step_run(new_step_run_id)["supersedes_step_run_id"],
            old_step_run_id,
        )
        self.assertEqual(
            [task for _srun, task in stub.executed_tasks].count("t1"), 1
        )
        gate = evaluate_stage_gate(self.adapter, registry, handle, "m4")
        self.assertEqual(gate["gate"], "passed")

    def test_rerun_refused_when_not_supports_recovery(self):
        stub = StubModule("m4", fail_on_task="t2", supports_recovery=False)
        stubs = self.all_stubs({"m4": stub})
        registry = self.registry_with(stubs)
        modules = self.stub_modules(stubs)
        processing_run_id, edition_part_id = self.start_run()
        handle = self.handle(processing_run_id, edition_part_id)

        run_until(
            self.adapter, registry, handle, "m4", modules=modules, stages=EDITION_STAGES
        )
        before = self.row_counts()
        with self.assertRaises(OrchestratorRefused):
            rerun_from_checkpoint(
                self.adapter, registry, handle, "m4", modules=modules
            )
        self.assertEqual(before, self.row_counts())


if __name__ == "__main__":
    unittest.main()
