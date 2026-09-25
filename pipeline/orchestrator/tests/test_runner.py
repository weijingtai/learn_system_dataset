"""ACT impl-08/04：StepRun 执行器与 legacy 绑定的单元测试（规格 §7）。

先写本文件，全红后再实现 `pipeline/orchestrator/runner.py`。
本模块同时提供 test_edition_run 复用的假 legacy 入口。
"""

import json
import sqlite3
import unittest
from pathlib import Path

from pipeline.ledger.errors import SchemaViolation
from pipeline.orchestrator.errors import OrchestratorRefused
from pipeline.orchestrator.module import StepContext, bind_module
from pipeline.orchestrator.runner import execute_step, run_legacy
from pipeline.orchestrator.stubs import StubModule
from pipeline.orchestrator.tests.scaffold import (
    REPO_ROOT,
    LedgerTestCase,
    load_validator,
    make_step_request,
)


class ServicePort:
    """测试用：把直连 ``LedgerService`` 包成端口（仅测试允许触达 ``.objects``）。"""

    def __init__(self, service):
        self._service = service

    def read_object(self, sha256):
        return self._service.objects.get(sha256)

    def __getattr__(self, name):
        return getattr(self._service, name)


def finalize_step_run(port, request, outcome):
    """把 ``StepOutcome`` 推到终态（与 runner.finalize_outcome 同构，测试用）。"""
    step_run_id = request["step_run_id"]
    base = {
        "schema_version": "1.0.0",
        "processing_run_id": request["processing_run_id"],
        "step_run_id": step_run_id,
    }
    current = port.get_step_run(step_run_id)["status_version"]
    if outcome["status"] == "succeeded":
        port.finish_step_run(
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
        port.fail_step_run(step_run_id, outcome["failure_artifact_ids"], "stub failed")
        return None
    return port.await_human(step_run_id, outcome["pending_queue_artifact_ids"])


def make_legacy_entry(
    stage,
    *,
    tasks=("t1", "t2"),
    produces=("stub_output",),
    processing_run_id=None,
    raise_immediately=False,
):
    """构造一个假 ``legacy_self_driving`` 入口：自建配置/StepRun/StagePackage 并 finish。

    ``entry.received`` 记录实际收到的 ``entry_kwargs``。
    """

    def entry(service, edition_part_id, **kwargs):
        entry.received = kwargs
        if raise_immediately:
            raise RuntimeError("入口在建 StepRun 之前抛异常")
        processing_run = processing_run_id or service.create_processing_run(
            "release_run", edition_part_id, "qizheng"
        )
        port = ServicePort(service)
        stub = StubModule(
            stage,
            module_id="legacy.%s" % stage,
            tasks=tasks,
            produces=produces,
            consumes_from=None,
        )
        configuration = {
            "stage": stage,
            "module_id": stub.module_id,
            "tasks": list(tasks),
        }
        _artifact_id, config_revision_id = service.put_run_artifact(
            processing_run,
            "configuration",
            json.dumps(configuration, sort_keys=True, ensure_ascii=False).encode("utf-8"),
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
                stage=stage,
                module_id=stub.module_id,
            ),
        )
        finalize_step_run(port, request, outcome)
        return {"step_run_id": request["step_run_id"], "processing_run_id": processing_run}

    entry.received = None
    return entry


def _binding(stub):
    return bind_module(
        {"module_id": stub.module_id, "binding": "step_request", "entry": None},
        modules={stub.module_id: stub},
    )


def _start_foreign_revision(test_case, processing_run_id):
    """在同一 ProcessingRun 内另起一个 StepRun 并封存一个修订，返回该修订号。"""
    configuration_revision_id = test_case.seed_configuration(
        processing_run_id, stage="m2", module_id="other.m2"
    )
    request = make_step_request(processing_run_id, configuration_revision_id)
    test_case.adapter.begin_step_run(request)
    _artifact_id, revision_id = test_case.adapter.put_artifact(
        request["step_run_id"],
        "step_log",
        b"foreign",
        producer_module="tests",
        producer_version="1.0",
    )
    test_case.adapter.seal_revision(revision_id)
    return revision_id


class TestExecuteStep(LedgerTestCase):
    """覆盖 BDD §5.1/5.3/5.5/5.6：StepResult 迁移与失败封存。"""

    def _begin(self, stub, *, stage="m1"):
        processing_run_id, edition_part_id = self.start_run()
        configuration_revision_id = self.seed_configuration(
            processing_run_id, stage=stage, module_id=stub.module_id, tasks=stub.tasks
        )
        request = make_step_request(processing_run_id, configuration_revision_id)
        self.adapter.begin_step_run(request)
        context = StepContext(
            mode="fresh",
            edition_part_id=edition_part_id,
            stage=stage,
            module_id=stub.module_id,
        )
        return request, context

    def test_execute_step_succeeded_result_validates_schema_and_finishes(self):
        stub = StubModule("m1")
        request, context = self._begin(stub)
        result = execute_step(self.adapter, _binding(stub), request, context)
        self.assertEqual(result["status"], "succeeded")
        load_validator("step_result.schema.json").validate(result)
        self.assertEqual(
            self.adapter.get_step_run(request["step_run_id"])["status"], "succeeded"
        )

    def test_execute_step_failed_result_validates_schema(self):
        stub = StubModule("m1", fail_on_task="t2")
        request, context = self._begin(stub)
        result = execute_step(self.adapter, _binding(stub), request, context)
        self.assertEqual(result["status"], "failed")
        load_validator("step_result.schema.json").validate(result)
        self.assertEqual(
            self.adapter.get_step_run(request["step_run_id"])["status"], "failed"
        )

    def test_execute_step_awaiting_human_has_token_and_pending(self):
        stub = StubModule("m2", human_queue=True)
        request, context = self._begin(stub, stage="m2")
        result = execute_step(self.adapter, _binding(stub), request, context)
        self.assertEqual(result["status"], "awaiting_human")
        self.assertTrue(result["resume_token"])
        self.assertEqual(len(result["pending_queue_artifact_ids"]), 1)
        load_validator("step_result.schema.json").validate(result)

    def test_module_exception_sealed_as_failure_report(self):
        stub = StubModule("m1", raise_on_task="t1")
        request, context = self._begin(stub)
        result = execute_step(self.adapter, _binding(stub), request, context)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(result["failure_artifact_ids"]), 1)
        row = self.adapter.get_revision(result["failure_artifact_ids"][0])
        payload = json.loads(self.adapter.read_object(row["sha256"]).decode("utf-8"))
        self.assertEqual(payload["check"], "module_exception")

    def test_outcome_contract_violation_sealed_as_failure_report(self):
        class BadOutcome:
            module_id = "bad.m1"

            def plan(self, *args, **kwargs):
                return {"input_artifact_ids": [], "configuration": {}}

            def execute(self, port, request, context):
                return {"status": "succeeded"}

        processing_run_id, edition_part_id = self.start_run()
        configuration_revision_id = self.seed_configuration(
            processing_run_id, stage="m1", module_id="bad.m1"
        )
        request = make_step_request(processing_run_id, configuration_revision_id)
        self.adapter.begin_step_run(request)
        binding = bind_module(
            {"module_id": "bad.m1", "binding": "step_request", "entry": None},
            modules={"bad.m1": BadOutcome()},
        )
        result = execute_step(
            self.adapter,
            binding,
            request,
            StepContext(
                mode="fresh", edition_part_id=edition_part_id, stage="m1", module_id="bad.m1"
            ),
        )
        self.assertEqual(result["status"], "failed")
        row = self.adapter.get_revision(result["failure_artifact_ids"][0])
        payload = json.loads(self.adapter.read_object(row["sha256"]).decode("utf-8"))
        self.assertEqual(payload["check"], "outcome_contract")

    def test_finish_rejection_converted_to_failed(self):
        processing_run_id, edition_part_id = self.start_run()
        foreign = _start_foreign_revision(self, processing_run_id)

        class ForeignOutput:
            module_id = "foreign.m1"

            def plan(self, *args, **kwargs):
                return {"input_artifact_ids": [], "configuration": {}}

            def execute(self, port, request, context):
                return {
                    "status": "succeeded",
                    "output_artifact_ids": [foreign],
                    "validation_report_ids": [],
                    "log_artifact_ids": [],
                    "failure_artifact_ids": [],
                }

        configuration_revision_id = self.seed_configuration(
            processing_run_id, stage="m1", module_id="foreign.m1"
        )
        request = make_step_request(processing_run_id, configuration_revision_id)
        self.adapter.begin_step_run(request)
        binding = bind_module(
            {"module_id": "foreign.m1", "binding": "step_request", "entry": None},
            modules={"foreign.m1": ForeignOutput()},
        )
        result = execute_step(
            self.adapter,
            binding,
            request,
            StepContext(
                mode="fresh",
                edition_part_id=edition_part_id,
                stage="m1",
                module_id="foreign.m1",
            ),
        )
        self.assertEqual(result["status"], "failed")
        row = self.adapter.get_revision(result["failure_artifact_ids"][0])
        payload = json.loads(self.adapter.read_object(row["sha256"]).decode("utf-8"))
        self.assertEqual(payload["check"], "outcome_contract")

    def test_module_receives_port_guard(self):
        class PeekModule:
            module_id = "peek.m1"

            def plan(self, *args, **kwargs):
                return {"input_artifact_ids": [], "configuration": {}}

            def execute(self, port, request, context):
                port.store  # PortGuard 必须拦截

        processing_run_id, edition_part_id = self.start_run()
        configuration_revision_id = self.seed_configuration(
            processing_run_id, stage="m1", module_id="peek.m1"
        )
        request = make_step_request(processing_run_id, configuration_revision_id)
        self.adapter.begin_step_run(request)
        binding = bind_module(
            {"module_id": "peek.m1", "binding": "step_request", "entry": None},
            modules={"peek.m1": PeekModule()},
        )
        result = execute_step(
            self.adapter,
            binding,
            request,
            StepContext(
                mode="fresh", edition_part_id=edition_part_id, stage="m1", module_id="peek.m1"
            ),
        )
        self.assertEqual(result["status"], "failed")
        row = self.adapter.get_revision(result["failure_artifact_ids"][0])
        payload = json.loads(self.adapter.read_object(row["sha256"]).decode("utf-8"))
        self.assertEqual(payload["check"], "module_exception")


class TestRunLegacy(LedgerTestCase):
    """覆盖 BDD §5.7：legacy 绑定的重建、entry_kwargs 与 prun 边界。"""

    def _legacy_binding(self, descriptor, entry):
        return bind_module(descriptor, modules={descriptor["module_id"]: entry})

    def test_run_legacy_rebuilds_result_from_ledger(self):
        processing_run_id, edition_part_id = self.start_run()
        entry = make_legacy_entry("m3", processing_run_id=processing_run_id)
        descriptor = {
            "module_id": "m3.corpus_structural",
            "stage": "m3",
            "binding": "legacy_self_driving",
            "entry": "tests:fake",
            "entry_kwargs": {},
            "owns_processing_run": False,
        }
        out = run_legacy(
            self.adapter,
            self._legacy_binding(descriptor, entry),
            {
                "processing_run_id": processing_run_id,
                "edition_part_id": edition_part_id,
                "technique_id": "qizheng",
            },
        )
        self.assertEqual(out["processing_run_id"], processing_run_id)
        self.assertEqual(out["step_result"]["status"], "succeeded")
        load_validator("step_result.schema.json").validate(out["step_result"])

    def test_run_legacy_passes_entry_kwargs(self):
        processing_run_id, edition_part_id = self.start_run()
        entry = make_legacy_entry("m5", processing_run_id=processing_run_id)
        descriptor = {
            "module_id": "m5.automatic_validation",
            "stage": "m5",
            "binding": "legacy_self_driving",
            "entry": "tests:fake",
            "entry_kwargs": {"target_consumption_level": "INTERNAL_DEMO"},
            "owns_processing_run": False,
        }
        run_legacy(
            self.adapter,
            self._legacy_binding(descriptor, entry),
            {
                "processing_run_id": processing_run_id,
                "edition_part_id": edition_part_id,
                "technique_id": "qizheng",
            },
        )
        self.assertEqual(
            entry.received, {"target_consumption_level": "INTERNAL_DEMO"}
        )

    def test_run_legacy_owns_processing_run_skips_prun_check(self):
        processing_run_id, edition_part_id = self.start_run()
        entry = make_legacy_entry("m8", produces=("publication_package",))
        descriptor = {
            "module_id": "m8.dataset_compilation",
            "stage": "m8",
            "binding": "legacy_self_driving",
            "entry": "tests:fake",
            "entry_kwargs": {"consumption_level": "INTERNAL_DEMO"},
            "owns_processing_run": True,
        }
        out = run_legacy(
            self.adapter,
            self._legacy_binding(descriptor, entry),
            {
                "processing_run_id": processing_run_id,
                "edition_part_id": edition_part_id,
                "technique_id": "qizheng",
            },
        )
        self.assertNotEqual(out["processing_run_id"], processing_run_id)
        self.assertEqual(out["step_result"]["status"], "succeeded")

    def test_run_legacy_refused_before_begin_zero_writes(self):
        processing_run_id, edition_part_id = self.start_run()
        entry = make_legacy_entry("m3", raise_immediately=True)
        descriptor = {
            "module_id": "m3.corpus_structural",
            "stage": "m3",
            "binding": "legacy_self_driving",
            "entry": "tests:fake",
            "entry_kwargs": {},
            "owns_processing_run": False,
        }

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
        with self.assertRaises(OrchestratorRefused):
            run_legacy(
                self.adapter,
                self._legacy_binding(descriptor, entry),
                {
                    "processing_run_id": processing_run_id,
                    "edition_part_id": edition_part_id,
                    "technique_id": "qizheng",
                },
            )
        self.assertEqual(before, counts())

    def test_run_legacy_passes_through_zero_write_refusal(self):
        """裁决 Q1：入口返回零写入拒收（非异常）时原样透传，不抛异常、不写账本。"""
        processing_run_id, edition_part_id = self.start_run()

        def refusing_entry(service, edition_part_id, **kwargs):
            return {
                "refused": True,
                "reason": "M4 拒收（REF_001）：没有已登记的提交件；"
                "请先经 run_m4_submit 提交候选件",
            }

        descriptor = {
            "module_id": "m4.knowledge_extraction",
            "stage": "m4",
            "binding": "legacy_self_driving",
            "entry": "tests:fake",
            "entry_kwargs": {},
            "owns_processing_run": False,
        }

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
        out = run_legacy(
            self.adapter,
            self._legacy_binding(descriptor, refusing_entry),
            {
                "processing_run_id": processing_run_id,
                "edition_part_id": edition_part_id,
                "technique_id": "qizheng",
            },
        )
        self.assertEqual(
            out,
            {
                "refused": True,
                "reason": "M4 拒收（REF_001）：没有已登记的提交件；"
                "请先经 run_m4_submit 提交候选件",
            },
        )
        self.assertEqual(before, counts())

    def test_run_legacy_rejects_refusal_without_reason(self):
        """零写入拒收必须带理由：缺 reason 按契约违约拒收（零写入）。"""
        processing_run_id, edition_part_id = self.start_run()
        descriptor = {
            "module_id": "m4.knowledge_extraction",
            "stage": "m4",
            "binding": "legacy_self_driving",
            "entry": "tests:fake",
            "entry_kwargs": {},
            "owns_processing_run": False,
        }
        with self.assertRaises(OrchestratorRefused) as caught:
            run_legacy(
                self.adapter,
                self._legacy_binding(descriptor, lambda *a, **k: {"refused": True}),
                {
                    "processing_run_id": processing_run_id,
                    "edition_part_id": edition_part_id,
                    "technique_id": "qizheng",
                },
            )
        self.assertIn("reason", str(caught.exception))

    def test_run_legacy_refused_on_ledgerd_adapter(self):
        class NoDirectPort:
            def unwrap(self):
                raise NotImplementedError("ledgerd Adapter 不提供直连服务")

        descriptor = {
            "module_id": "m3.corpus_structural",
            "stage": "m3",
            "binding": "legacy_self_driving",
            "entry": "tests:fake",
            "entry_kwargs": {},
            "owns_processing_run": False,
        }
        with self.assertRaises(OrchestratorRefused):
            run_legacy(
                NoDirectPort(),
                self._legacy_binding(descriptor, lambda *a, **k: {}),
                {
                    "processing_run_id": "prun_" + "a" * 32,
                    "edition_part_id": "art_" + "a" * 32,
                    "technique_id": "qizheng",
                },
            )


if __name__ == "__main__":
    unittest.main()
