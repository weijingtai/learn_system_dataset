"""ACT impl-08/02：统一 Module Interface 适配层与桩的单元测试（规格 §7）。

先写本文件，运行 `.venv/bin/python -m unittest discover -s pipeline/orchestrator/tests -t .`
因 `pipeline.orchestrator` 尚不存在而全红。
"""

import json
import unittest
from pathlib import Path

from pipeline.ledger.errors import SchemaViolation
from pipeline.orchestrator.errors import OrchestratorRefused
from pipeline.orchestrator.module import (
    StepContext,
    bind_module,
    validate_outcome,
)
from pipeline.orchestrator.stubs import StubModule
from pipeline.orchestrator.tests.scaffold import REPO_ROOT, LedgerTestCase, load_validator

REV = "rev_" + "a" * 32


def succeeded_outcome():
    return {
        "status": "succeeded",
        "output_artifact_ids": [REV],
        "validation_report_ids": [],
        "log_artifact_ids": [],
        "failure_artifact_ids": [],
    }


class TestValidateOutcome(unittest.TestCase):
    """覆盖 BDD §3.1：StepOutcome 形态校验。"""

    def test_validate_outcome_accepts_three_valid_shapes(self):
        failed = {
            "status": "failed",
            "output_artifact_ids": [],
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [REV],
        }
        awaiting = {
            "status": "awaiting_human",
            "output_artifact_ids": [],
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
            "pending_queue_artifact_ids": [REV],
        }
        for outcome in (succeeded_outcome(), failed, awaiting):
            self.assertEqual(validate_outcome(outcome), [])

    def test_validate_outcome_rejects_bad_status_and_missing_keys(self):
        bad = succeeded_outcome()
        bad["status"] = "bogus"
        self.assertTrue(any("status" in p for p in validate_outcome(bad)))
        missing = {"status": "succeeded"}
        problems = validate_outcome(missing)
        self.assertTrue(any("output_artifact_ids" in p for p in problems))

    def test_validate_outcome_rejects_reserved_keys(self):
        for key, value in (
            ("resume_token", "tok"),
            ("step_run_id", "srun_" + "a" * 32),
            ("status_version", 1),
        ):
            outcome = succeeded_outcome()
            outcome[key] = value
            self.assertTrue(
                any(key in p for p in validate_outcome(outcome)),
                "保留键 %s 未被拒" % key,
            )

    def test_validate_outcome_awaiting_requires_pending_and_others_forbid_it(self):
        awaiting = succeeded_outcome()
        awaiting["status"] = "awaiting_human"
        self.assertTrue(
            any("pending_queue_artifact_ids" in p for p in validate_outcome(awaiting))
        )
        forbidden = succeeded_outcome()
        forbidden["pending_queue_artifact_ids"] = [REV]
        self.assertTrue(
            any("pending_queue_artifact_ids" in p for p in validate_outcome(forbidden))
        )

    def test_validate_outcome_failed_requires_failure_evidence(self):
        failed = succeeded_outcome()
        failed["status"] = "failed"
        self.assertTrue(
            any("failure_artifact_ids" in p for p in validate_outcome(failed))
        )

    def test_validate_outcome_rejects_duplicate_and_malformed_revisions(self):
        duplicate = succeeded_outcome()
        duplicate["output_artifact_ids"] = [REV, REV]
        self.assertTrue(any("重复" in p for p in validate_outcome(duplicate)))
        malformed = succeeded_outcome()
        malformed["output_artifact_ids"] = ["rev_ZZZ"]
        self.assertTrue(any("非法" in p for p in validate_outcome(malformed)))


class TestBindModule(unittest.TestCase):
    """覆盖 BDD §3.2：三种绑定的解析与拒绝。"""

    def test_step_context_rejects_unknown_mode(self):
        with self.assertRaises(SchemaViolation) as ctx:
            StepContext(
                mode="bogus",
                edition_part_id="art_" + "a" * 32,
                stage="m1",
                module_id="stub.m1",
            )
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_bind_module_imported_not_executable(self):
        binding = bind_module(
            {"module_id": "m1.fixture_import", "binding": "imported", "entry": None}
        )
        self.assertFalse(binding.executable)
        self.assertIsNone(binding.target)

    def test_bind_module_injected_step_request_object(self):
        stub = StubModule("m1")
        binding = bind_module(
            {"module_id": "stub.m1", "binding": "step_request", "entry": None},
            modules={"stub.m1": stub},
        )
        self.assertTrue(binding.executable)
        self.assertIs(binding.target, stub)

    def test_bind_module_step_request_missing_execute_refused(self):
        class NoExecute:
            def plan(self, *args, **kwargs):
                return {}

        with self.assertRaises(OrchestratorRefused):
            bind_module(
                {"module_id": "stub.m1", "binding": "step_request", "entry": None},
                modules={"stub.m1": NoExecute()},
            )

    def test_bind_module_entry_unresolvable_refused(self):
        with self.assertRaises(OrchestratorRefused):
            bind_module(
                {
                    "module_id": "m3.corpus_structural",
                    "binding": "legacy_self_driving",
                    "entry": "pipeline.orchestrator.stubs:definitely_missing_symbol",
                }
            )

    def test_bind_module_carries_entry_kwargs_and_owns_processing_run(self):
        def fake_entry(service, edition_part_id, **kwargs):
            return {}

        m5 = {
            "module_id": "m5.automatic_validation",
            "binding": "legacy_self_driving",
            "entry": "pipeline.validation.step:run_m5",
            "entry_kwargs": {"target_consumption_level": "INTERNAL_DEMO"},
            "owns_processing_run": False,
        }
        binding = bind_module(m5, modules={"m5.automatic_validation": fake_entry})
        self.assertEqual(
            binding.entry_kwargs, {"target_consumption_level": "INTERNAL_DEMO"}
        )
        self.assertIs(binding.owns_processing_run, False)

        m8 = {
            "module_id": "m8.dataset_compilation",
            "binding": "legacy_self_driving",
            "entry": "pipeline.dataset_compiler.step:run_m8",
            "entry_kwargs": {"consumption_level": "INTERNAL_DEMO"},
            "owns_processing_run": True,
        }
        binding8 = bind_module(m8, modules={"m8.dataset_compilation": fake_entry})
        self.assertIs(binding8.owns_processing_run, True)

        with self.assertRaises(OrchestratorRefused):
            bind_module(
                dict(m5, entry_kwargs="INTERNAL_DEMO"),
                modules={"m5.automatic_validation": fake_entry},
            )
        with self.assertRaises(OrchestratorRefused):
            bind_module(
                dict(m8, owns_processing_run="yes"),
                modules={"m8.dataset_compilation": fake_entry},
            )


class TestStubModule(LedgerTestCase):
    """覆盖 BDD §3.3：桩的 Checkpoint 粒度与 StagePackage。"""

    def _run_stub(self, stub, *, stage="m1", tasks=("t1", "t2"), mode="fresh",
                  recovery_plan=None, human_event_revision_ids=()):
        processing_run_id, edition_part_id = self.start_run()
        configuration_revision_id = self.seed_configuration(
            processing_run_id, stage=stage, module_id=stub.module_id, tasks=tasks
        )
        request = self.begin(processing_run_id, configuration_revision_id)
        context = StepContext(
            mode=mode,
            edition_part_id=edition_part_id,
            stage=stage,
            module_id=stub.module_id,
            human_event_revision_ids=tuple(human_event_revision_ids),
            recovery_plan=recovery_plan,
        )
        outcome = stub.execute(self.adapter, request, context)
        return edition_part_id, request, outcome

    def test_stub_execute_writes_checkpoint_per_task_and_valid_stage_package(self):
        stub = StubModule("m1")
        edition_part_id, _request, outcome = self._run_stub(stub)
        self.assertEqual(validate_outcome(outcome), [])
        self.assertEqual(outcome["status"], "succeeded")
        checkpoints = self.adapter.list_checkpoints(edition_part_id, "m1")
        self.assertEqual(len(checkpoints), 2)

        package_revision = None
        for revision_id in outcome["output_artifact_ids"]:
            row = self.adapter.get_revision(revision_id)
            if row["schema_id"] == "stage_package":
                package_revision = revision_id
        self.assertIsNotNone(package_revision, "未产出 StagePackage")
        row = self.adapter.get_revision(package_revision)
        package = json.loads(self.adapter.read_object(row["sha256"]).decode("utf-8"))
        load_validator("stage_package.schema.json").validate(package)
        self.assertEqual(package["stage"], "m1")

    def test_stub_awaiting_human_outcome_on_fresh(self):
        stub = StubModule("m2", human_queue=True)
        _edition_part_id, _request, outcome = self._run_stub(stub, stage="m2")
        self.assertEqual(validate_outcome(outcome), [])
        self.assertEqual(outcome["status"], "awaiting_human")
        self.assertEqual(len(outcome["pending_queue_artifact_ids"]), 1)

    def test_stub_skips_recovery_completed_tasks(self):
        stub = StubModule("m1")
        _edition_part_id, _request, outcome = self._run_stub(
            stub, mode="rerun", recovery_plan={"completed_task_ids": ["t1"]}
        )
        self.assertEqual(outcome["status"], "succeeded")
        self.assertEqual([task for _srun, task in stub.executed_tasks], ["t2"])


class TestSourceHygiene(unittest.TestCase):
    """覆盖 BDD §3.4：非测试源码不出现加工 Module 包名。"""

    def test_orchestrator_sources_do_not_name_processing_modules(self):
        source_dir = REPO_ROOT / "pipeline" / "orchestrator"
        for path in source_dir.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("corpus_compiler", text, path.name)
            self.assertNotIn("dataset_compiler", text, path.name)
            self.assertNotIn("pipeline.validation", text, path.name)


if __name__ == "__main__":
    unittest.main()
