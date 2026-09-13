"""测试与验收用桩 Module（``kind`` 恒为 ``stub``）。

桩只在测试与验收场景以 ``Registry.from_dict(..., allow_stub=True)`` 构造；桩产物的
``artifact_type``（如 ``stub_output``、``review_queue_item``）不入 INTERFACES §4 闭集，
不得出现在生产登记表的产物中。
"""

import hashlib
import json

from pipeline.ledger.ids import STAGES, new_id

# 桩产物的 artifact_type（仅测试/验收场景）
STUB_OUTPUT_TYPE = "stub_output"
REVIEW_QUEUE_TYPE = "review_queue_item"

_PACKAGE_MODES = ("valid", "missing", "wrong_stage", "with_failures")


def _previous_stage(stage):
    """返回闭集中位于 ``stage`` 之前的阶段（m1 无前驱 → ``None``）。"""
    index = STAGES.index(stage)
    return STAGES[index - 1] if index > 0 else None


def _other_stage(stage):
    """返回一个与 ``stage`` 不同的合法阶段（用于 ``wrong_stage`` 负例）。"""
    index = STAGES.index(stage)
    return STAGES[(index + 1) % len(STAGES)]


class StubModule:
    """一个可配置的 ``step_request`` 绑定桩 Module。"""

    def __init__(
        self,
        stage,
        *,
        module_id=None,
        tasks=("t1", "t2"),
        fail_on_task=None,
        raise_on_task=None,
        human_queue=False,
        validation_passed=True,
        stage_package_mode="valid",
        produces=(STUB_OUTPUT_TYPE,),
        consumes_from=None,
        supports_recovery=True,
    ):
        if stage not in STAGES:
            raise ValueError("非法 stage: %r" % (stage,))
        if stage_package_mode not in _PACKAGE_MODES:
            raise ValueError("非法 stage_package_mode: %r" % (stage_package_mode,))
        self.stage = stage
        self.module_id = module_id or ("stub.%s" % stage)
        self.tasks = tuple(tasks)
        self.fail_on_task = fail_on_task
        self.raise_on_task = raise_on_task
        self.human_queue = human_queue
        self.validation_passed = validation_passed
        self.stage_package_mode = stage_package_mode
        self.produces = tuple(produces)
        self.supports_recovery = supports_recovery
        self.consumes_from = (
            _previous_stage(stage) if consumes_from is None else consumes_from
        )
        # 执行计数：(step_run_id, task_id)
        self.executed_tasks = []

    def descriptor(self):
        """返回登记表描述符（``kind="stub"``，``binding="step_request"``）。"""
        consumes = []
        if self.consumes_from:
            consumes = [
                {"artifact_type": "stage_package", "from_stage": self.consumes_from}
            ]
        return {
            "module_id": self.module_id,
            "stage": self.stage,
            "kind": "stub",
            "binding": "step_request",
            "entry": None,
            "version": "0.0.0",
            "consumes": consumes,
            "produces": [{"artifact_type": item} for item in self.produces],
            "human_queue": self.human_queue,
            "supports_recovery": self.supports_recovery,
        }

    # ------------------------------------------------------------- plan
    def plan(
        self, port, *, edition_part_id, processing_run_id, technique_id, upstream
    ):
        """冻结上游 StagePackage 修订为输入，并给出配置内容。"""
        input_artifact_ids = []
        for step in (upstream or {}).get(self.consumes_from, []) or []:
            result = step.get("result") or {}
            for revision_id in result.get("output_artifact_ids", []) or []:
                row = port.get_revision(revision_id)
                if row is not None and row.get("schema_id") == "stage_package":
                    input_artifact_ids.append(revision_id)
        return {
            "input_artifact_ids": input_artifact_ids,
            "configuration": {
                "stage": self.stage,
                "module_id": self.module_id,
                "tasks": list(self.tasks),
            },
        }

    # ---------------------------------------------------------- execute
    def execute(self, port, request, context):
        """逐 task 执行，写 Checkpoint 与 StagePackage，返回 ``StepOutcome``。"""
        step_run_id = request["step_run_id"]
        skip = (
            set(context.recovery_plan["completed_task_ids"])
            if context.recovery_plan
            else set()
        )
        outputs = []
        payloads = []
        completed = []
        for index, task in enumerate(self.tasks):
            if task in skip:
                continue
            if self.raise_on_task == task:
                raise RuntimeError("桩在 task %s 上抛异常" % task)

            payload = ("%s:%s" % (self.stage, task)).encode("utf-8")
            _artifact_id, revision_id = port.put_artifact(
                step_run_id,
                self.produces[0],
                payload,
                producer_module=self.module_id,
                producer_version="0.0.0",
            )
            port.seal_revision(revision_id)
            outputs.append(revision_id)
            payloads.append(payload)
            self.executed_tasks.append((step_run_id, task))

            task_status = "failed" if task == self.fail_on_task else "succeeded"
            completed.append(
                {
                    "task_id": task,
                    "artifact_revision_id": revision_id,
                    "status": task_status,
                    "terminal_state": None,
                }
            )
            remaining = [{"task_id": item} for item in self.tasks[index + 1 :]]
            port.write_checkpoint(
                step_run_id,
                edition_part_id=context.edition_part_id,
                stage=self.stage,
                completed_tasks=list(completed),
                human_decisions=list(context.human_event_revision_ids),
                pending_queue=remaining,
                next_pointer=remaining[0]["task_id"] if remaining else None,
            )

            if task_status == "failed":
                failure_revision = self._put_failure(port, step_run_id, "stub_task", task)
                return {
                    "status": "failed",
                    "output_artifact_ids": list(outputs),
                    "validation_report_ids": [],
                    "log_artifact_ids": [],
                    "failure_artifact_ids": [failure_revision],
                }

        if self.human_queue and context.mode == "fresh":
            _artifact_id, revision_id = port.put_artifact(
                step_run_id,
                REVIEW_QUEUE_TYPE,
                json.dumps(
                    {"stage": self.stage, "queue": "stub"},
                    sort_keys=True,
                    ensure_ascii=False,
                ).encode("utf-8"),
                producer_module=self.module_id,
                producer_version="0.0.0",
            )
            port.seal_revision(revision_id)
            return {
                "status": "awaiting_human",
                "output_artifact_ids": list(outputs),
                "validation_report_ids": [],
                "log_artifact_ids": [],
                "failure_artifact_ids": [],
                "pending_queue_artifact_ids": [revision_id],
            }

        if (
            self.human_queue
            and context.mode == "resumed"
            and not context.human_event_revision_ids
        ):
            failure_revision = self._put_failure(
                port, step_run_id, "missing_human_event", "resumed 但无人工事件"
            )
            return {
                "status": "failed",
                "output_artifact_ids": list(outputs),
                "validation_report_ids": [],
                "log_artifact_ids": [],
                "failure_artifact_ids": [failure_revision],
            }

        report_revision = self._put(
            port,
            step_run_id,
            "validation_report",
            json.dumps(
                {"passed": bool(self.validation_passed)},
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8"),
        )
        log_revision = self._put(port, step_run_id, "step_log", b"stub")

        package_revision = None
        if self.stage_package_mode != "missing":
            package_revision = self._register_package(
                port, request, outputs, payloads, report_revision, log_revision
            )

        port.record_transformation(
            step_run_id,
            operation="stub_" + self.stage,
            tool=self.module_id,
            tool_version="0.0.0",
            configuration_revision_id=request["configuration_artifact_id"],
            input_revision_ids=request["input_artifact_ids"],
            output_revision_ids=list(outputs),
            validation_report_revision_id=report_revision,
            human_event_revision_ids=list(context.human_event_revision_ids),
        )

        result_outputs = list(outputs)
        if package_revision is not None:
            result_outputs.append(package_revision)
        return {
            "status": "succeeded",
            "output_artifact_ids": result_outputs,
            "validation_report_ids": [report_revision],
            "log_artifact_ids": [log_revision],
            "failure_artifact_ids": [],
        }

    # ----------------------------------------------------------- helper
    def _put(self, port, step_run_id, artifact_type, data):
        _artifact_id, revision_id = port.put_artifact(
            step_run_id,
            artifact_type,
            data,
            producer_module=self.module_id,
            producer_version="0.0.0",
        )
        port.seal_revision(revision_id)
        return revision_id

    def _put_failure(self, port, step_run_id, check, detail):
        return self._put(
            port,
            step_run_id,
            "failure_report",
            json.dumps(
                {"check": check, "detail": detail}, sort_keys=True, ensure_ascii=False
            ).encode("utf-8"),
        )

    @staticmethod
    def _artifact_ref(port, revision_id, artifact_type):
        row = port.get_revision(revision_id)
        return {
            "schema_version": "1.0.0",
            "artifact_kind": "artifact",
            "artifact_id": row["artifact_id"],
            "artifact_revision_id": revision_id,
            "artifact_type": artifact_type,
        }

    def _register_package(
        self, port, request, outputs, payloads, report_revision, log_revision
    ):
        """构造并登记一个过 L0 Schema 的 StagePackage，返回其修订号。"""
        package_stage = self.stage
        if self.stage_package_mode == "wrong_stage":
            package_stage = _other_stage(self.stage)
        package_id = new_id("stage_package_id", package_stage)
        revision_id = new_id("artifact_revision_id")
        content_sha256 = hashlib.sha256(b"".join(payloads)).hexdigest()
        failures = []
        if self.stage_package_mode == "with_failures":
            failures = [self._artifact_ref(port, report_revision, "validation_report")]
        package = {
            "schema_version": "1.0.0",
            "stage_package_id": package_id,
            "artifact_revision_id": revision_id,
            "stage": package_stage,
            "status": "sealed",
            "payload": {"stage": package_stage, "tasks": list(self.tasks)},
            "manifest": {
                "schema_version": "1.0.0",
                "processing_run_id": request["processing_run_id"],
                "step_run_id": request["step_run_id"],
                "input_artifacts": [
                    self._artifact_ref(port, revision, "stage_package")
                    for revision in request["input_artifact_ids"]
                ],
                "output_artifacts": [
                    self._artifact_ref(port, revision, self.produces[0])
                    for revision in outputs
                ],
                "counts": {"tasks": len(self.tasks), "outputs": len(outputs)},
                "content_sha256": content_sha256,
            },
            "validation": {
                "passed": bool(self.validation_passed),
                "report_artifacts": [
                    self._artifact_ref(port, report_revision, "validation_report")
                ],
            },
            "lineage": {"upstream_artifacts": [], "transformations": []},
            "logs": [self._artifact_ref(port, log_revision, "step_log")],
            "failures": failures,
        }
        data = json.dumps(package, sort_keys=True, ensure_ascii=False).encode("utf-8")
        port.register_stage_package(
            request["step_run_id"],
            package,
            data,
            stage_package_id=package_id,
            artifact_revision_id=revision_id,
        )
        port.seal_revision(revision_id)
        return revision_id
