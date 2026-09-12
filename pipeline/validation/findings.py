"""M5 Finding、Validator 报告与分级判定。

- ``make_finding`` 构造单条发现，严格校验错误码（§8.2 九码或 ``None``）与
  三级严重度；
- ``make_report`` 构造每 task 一个的 Validator 报告（内容结构复用通用
  ``validation_report``，``schema_version`` 恒 ``0.1.0-draft``）；
- ``level_verdicts`` 对三级消费级别分别给出 ``passed``/``failed``；
- ``gate_summary`` 汇总目标级别的 Gate 结论。
"""

from pipeline.ledger.errors import SchemaViolation

from . import CONSUMPTION_LEVELS
from .registry import CHECK_CODES

# 严重度取值闭集
_SEVERITY_VALUES = ("error", "warning", "info")
# 发现的 relation 闭集（§5.2）
_RELATIONS = (None, "artifact_ref", "content_hash", "anchor_image", "batch_membership")
# 返工阶段闭集（D-11：无新前缀，只区分 m2/m3）
_REWORK_STAGES = ("m2", "m3", None)
# Validator 报告的 task_status 闭集
_TASK_STATUSES = ("succeeded", "errored", "skipped_fail_closed")


def make_finding(
    validator_id,
    gate,
    check,
    code,
    severity,
    subject,
    relation=None,
    rework_stage=None,
    detail="",
):
    """构造一条 M5 发现。

    参数：
        validator_id：注册表中的 Validator 标识。
        gate：``G1``/``G2``/``G3``。
        check：检查名，必须是 ``registry.CHECK_CODES`` 的键。
        code：§8.2 九码之一或 ``None``；表外码抛 ``SchemaViolation(SCH_002)``。
        severity：``{INTERNAL_DEMO, DEV_SEARCH, PUBLIC_RELEASE}`` → 取值 ∈
            ``("error", "warning", "info")``；非法严重度抛 ``SchemaViolation``。
        subject：至少含 ``entity_id`` 与 ``artifact_revision_id``，涉及时含 ``page``。
        relation：``None``/``artifact_ref``/``content_hash``/``anchor_image``/
            ``batch_membership``。
        rework_stage：``m2``/``m3``/``None``。
        detail：人类可读补充说明。

    返回 Finding dict。
    """
    legal_codes = set(CHECK_CODES.values())
    if code is not None and code not in legal_codes:
        raise SchemaViolation(
            "M5 发现使用了表外错误码: %r" % (code,), code="SCH_002"
        )
    if not isinstance(check, str) or check not in CHECK_CODES:
        raise SchemaViolation("M5 发现使用了未登记检查名: %r" % (check,), code="SCH_002")
    if not isinstance(severity, dict) or set(severity) != set(CONSUMPTION_LEVELS):
        raise SchemaViolation(
            "severity 必须恰含三级键 %r: %r" % (tuple(CONSUMPTION_LEVELS), severity),
            code="SCH_002",
        )
    for level in CONSUMPTION_LEVELS:
        if severity[level] not in _SEVERITY_VALUES:
            raise SchemaViolation(
                "severity[%s] 非法: %r" % (level, severity[level]), code="SCH_002"
            )
    if relation not in _RELATIONS:
        raise SchemaViolation("relation 非法: %r" % (relation,), code="SCH_002")
    if rework_stage not in _REWORK_STAGES:
        raise SchemaViolation("rework_stage 非法: %r" % (rework_stage,), code="SCH_002")
    if not isinstance(subject, dict):
        raise SchemaViolation("subject 必须是 dict: %r" % (subject,), code="SCH_002")

    return {
        "validator_id": validator_id,
        "gate": gate,
        "check": check,
        "code": code,
        "severity": {level: severity[level] for level in CONSUMPTION_LEVELS},
        "subject": {
            "entity_id": subject.get("entity_id"),
            "artifact_revision_id": subject.get("artifact_revision_id"),
            "page": subject.get("page"),
        },
        "relation": relation,
        "rework_stage": rework_stage,
        "detail": detail,
    }


def make_report(validator_id, gate, version, task_status, checked, findings):
    """构造每 task 一个的 Validator 报告（``artifact_type=validation_report``）。

    ``task_status`` ∈ ``("succeeded", "errored", "skipped_fail_closed")``；
    ``checked`` 为计数 dict；``findings`` 为发现列表。
    """
    if task_status not in _TASK_STATUSES:
        raise SchemaViolation("task_status 非法: %r" % (task_status,), code="SCH_002")
    return {
        "schema_version": "0.1.0-draft",
        "validator_id": validator_id,
        "gate": gate,
        "version": version,
        "task_status": task_status,
        "checked": dict(checked or {}),
        "findings": list(findings or []),
    }


def level_verdicts(findings, task_statuses):
    """对每个消费级别给出 ``passed``/``failed``。

    规则：任一 ``task_status != "succeeded"``，或存在任一 finding 在该级别下
    严重度为 ``error``，则该级别 ``failed``，否则 ``passed``。
    """
    statuses = list(task_statuses or [])
    failed_task = any(status != "succeeded" for status in statuses)
    verdicts = {}
    for level in CONSUMPTION_LEVELS:
        has_error = any(
            finding["severity"][level] == "error" for finding in (findings or [])
        )
        verdicts[level] = "failed" if (failed_task or has_error) else "passed"
    return verdicts


def gate_summary(target_level, findings, reports):
    """汇总目标级别的 Gate 结论。

    返回 ``{passed, severe_error_count, failed_task_count, pending_rework_count}``：
    ``passed`` 在无目标级 ``error``、无失败 task、无待返工任务时为真；
    ``pending_rework_count`` 按 ``(rework_stage, validator_id, check)`` 聚合计数。
    """
    findings = list(findings or [])
    reports = list(reports or [])
    severe = [
        finding for finding in findings
        if finding["severity"][target_level] == "error"
    ]
    failed_tasks = [
        report for report in reports if report["task_status"] != "succeeded"
    ]
    rework_keys = set()
    for finding in severe:
        stage = finding.get("rework_stage")
        if stage is None:
            continue
        rework_keys.add((stage, finding["validator_id"], finding["check"]))
    passed = not severe and not failed_tasks and not rework_keys
    return {
        "passed": passed,
        "severe_error_count": len(severe),
        "failed_task_count": len(failed_tasks),
        "pending_rework_count": len(rework_keys),
    }
