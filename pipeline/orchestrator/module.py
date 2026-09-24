"""统一 Module Interface 适配层（规格 §7）。

Module 只描述自己（``descriptor``），并把执行结果表达为 ``StepOutcome``；StepRun 的
建立与终态迁移由 Orchestrator 独占。三种绑定：

- ``step_request``：标准形态，Orchestrator 建 StepRun，Module 实现 ``plan``/``execute``；
- ``legacy_self_driving``：挂接自建 StepRun 的入口（先判上游 Gate 再调入口）；
- ``imported``：不执行，只判 Gate。

本模块不 import 任何加工 Module 包。
"""

import importlib
import re
from dataclasses import dataclass

from pipeline.ledger.errors import SchemaViolation

from .errors import OrchestratorRefused

# StepOutcome 合法状态
STEP_OUTCOME_STATUSES = ("succeeded", "failed", "awaiting_human")

# StepOutcome 必备列表键
OUTCOME_LIST_KEYS = (
    "output_artifact_ids",
    "validation_report_ids",
    "log_artifact_ids",
    "failure_artifact_ids",
)

# Module 不得回填的保留键（由 Orchestrator 单方面填充 StepResult 时写入）
OUTCOME_RESERVED_KEYS = (
    "schema_version",
    "processing_run_id",
    "step_run_id",
    "status_version",
    "resume_token",
)

# StepContext.mode 闭集
CONTEXT_MODES = ("fresh", "resumed", "recovered", "rerun")

_REVISION_RE = re.compile(r"^rev_[0-9a-f]{32}$")


@dataclass(frozen=True)
class StepContext:
    """一次 Module 执行的上下文（执行模式、人工事件与恢复计划）。"""

    mode: str
    edition_part_id: str
    stage: str
    module_id: str
    human_event_revision_ids: tuple = ()
    recovery_plan: dict = None

    def __post_init__(self):
        if self.mode not in CONTEXT_MODES:
            raise SchemaViolation(
                "StepContext.mode 非法: %r" % (self.mode,), code="SCH_002"
            )


def validate_outcome(outcome):
    """校验 StepOutcome；返回问题文本列表（空 = 合法）。"""
    problems = []
    if not isinstance(outcome, dict):
        return ["outcome 必须是 dict"]
    status = outcome.get("status")
    if status not in STEP_OUTCOME_STATUSES:
        problems.append("status 非法: %r" % (status,))
    for key in OUTCOME_LIST_KEYS:
        value = outcome.get(key)
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            problems.append("%s 必须是 list[str]" % key)
    for key in OUTCOME_RESERVED_KEYS:
        if key in outcome:
            problems.append("outcome 不得含保留键 %s" % key)

    pending_present = "pending_queue_artifact_ids" in outcome
    pending = outcome.get("pending_queue_artifact_ids")
    if status == "awaiting_human":
        if not isinstance(pending, list) or not pending:
            problems.append("awaiting_human 必须带非空 pending_queue_artifact_ids")
    elif pending_present:
        problems.append("非 awaiting_human 不得带 pending_queue_artifact_ids")

    if status == "failed" and not outcome.get("failure_artifact_ids"):
        problems.append("failed 必须带非空 failure_artifact_ids")

    for key in OUTCOME_LIST_KEYS:
        value = outcome.get(key)
        if not isinstance(value, list):
            continue
        seen = set()
        for revision_id in value:
            if revision_id in seen:
                problems.append("%s 含重复修订: %s" % (key, revision_id))
            seen.add(revision_id)
            if not isinstance(revision_id, str) or not _REVISION_RE.match(revision_id):
                problems.append("%s 修订号非法: %r" % (key, revision_id))
    return problems


class ModuleBinding:
    """解析后的 Module 绑定（描述符 + 目标 + 入口参数）。"""

    def __init__(
        self, descriptor, *, binding, target, entry_kwargs, owns_processing_run
    ):
        self.descriptor = descriptor
        self.binding = binding
        self.target = target
        self.entry_kwargs = entry_kwargs
        self.owns_processing_run = owns_processing_run

    @property
    def executable(self):
        """``imported`` 绑定不可执行。"""
        return self.binding != "imported"


def _resolve_entry(entry, module_id):
    """经 ``importlib`` 解析登记表 ``"模块:属性"`` 入口。"""
    if not isinstance(entry, str) or ":" not in entry:
        raise OrchestratorRefused("entry 非法（module %s）: %r" % (module_id, entry))
    module_path, _, attr = entry.partition(":")
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:  # noqa: BLE001 - 包装为拒绝
        raise OrchestratorRefused(
            "entry 无法导入 %s（%s: %s）" % (entry, type(exc).__name__, exc)
        )
    try:
        return getattr(module, attr)
    except AttributeError:
        raise OrchestratorRefused("entry 缺属性 %s" % entry)


def descriptor_needs_run_inputs(descriptor):
    """描述符是否声明入口需要 EditionRun 运行输入（``receives_run_inputs: true``）。"""
    return descriptor.get("receives_run_inputs") is True


def resolve_entry(entry, module_id):
    """经 ``importlib`` 解析登记表 ``"模块:属性"`` 入口（人工恢复入口共用）。"""
    return _resolve_entry(entry, module_id)


def bind_module(descriptor, *, modules=None):
    """按描述符与 ``modules=`` 注入表解析出 ``ModuleBinding``。"""
    modules = modules or {}
    module_id = descriptor.get("module_id")
    binding = descriptor.get("binding")

    entry_kwargs = descriptor.get("entry_kwargs", {})
    if not isinstance(entry_kwargs, dict):
        raise OrchestratorRefused("entry_kwargs 必须是 dict: %s" % module_id)
    owns_processing_run = descriptor.get("owns_processing_run", False)
    if not isinstance(owns_processing_run, bool):
        raise OrchestratorRefused("owns_processing_run 必须是 bool: %s" % module_id)

    if binding == "imported":
        target = None
    elif binding in ("step_request", "legacy_self_driving"):
        if module_id in modules:
            target = modules[module_id]
        else:
            target = _resolve_entry(descriptor.get("entry"), module_id)
        if binding == "step_request":
            if not (
                callable(getattr(target, "plan", None))
                and callable(getattr(target, "execute", None))
            ):
                raise OrchestratorRefused(
                    "step_request 绑定缺 plan/execute: %s" % module_id
                )
        elif not callable(target):
            raise OrchestratorRefused(
                "legacy_self_driving 绑定 target 必须可调用: %s" % module_id
            )
    else:
        raise OrchestratorRefused("未知 binding（module %s）: %r" % (module_id, binding))

    return ModuleBinding(
        descriptor,
        binding=binding,
        target=target,
        entry_kwargs=entry_kwargs,
        owns_processing_run=owns_processing_run,
    )
