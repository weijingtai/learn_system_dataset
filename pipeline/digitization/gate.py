"""M2 Gate 放行判定纯函数层。

根据 §10.1 要求，Gate 独立于清洗过程，只消费 SanitizationReport。
严禁从 cleaner、patcher、reporter 或 raw_text 导入任何符号。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

FINDING_KINDS = frozenset(
    {
        "replacement_char",
        "private_use_area",
        "escape_residue",
        "watermark",
        "header_footer",
        "duplicate",
        "missing",
        "textualized_diagram",
        "variant_mixed",
        "suspected_error",
        "control_char",
        "encoding_issue",
    }
)

TERMINAL_STATES = frozenset({"processed", "deferred", "retained", "rejected"})

VARIANT_MIXED_WARNING_THRESHOLD = 50


@dataclass
class GateResult:
    """M2 Gate 判定结果。"""

    passed: bool
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def evaluate_m2_gate(
    report: dict[str, Any],
    decisions: dict[str, Any] | None = None,
) -> GateResult:
    """评估 M2 SanitizationReport 放行准则。

    逐条独立检查：
    1. report_valid：report 结构合法（含 findings、summary 键，且类型正确）
    2. no_deferred：summary.deferred_count == 0
    3. findings_valid：每个 finding 的 kind in FINDING_KINDS，terminal_state in TERMINAL_STATES
    4. patches_consistent：每个 finding 的 patch_id 如存在则在 patches 列表中
    5. summary_consistent：summary 各 kind 计数 == 实际 findings 数
    """
    failed_checks: list[str] = []
    warnings: list[str] = []

    # 1. report_valid
    if (
        not isinstance(report, dict)
        or "findings" not in report
        or "summary" not in report
        or not isinstance(report["findings"], list)
        or not isinstance(report["summary"], dict)
    ):
        failed_checks.append("report_valid")
        return GateResult(passed=False, failed_checks=failed_checks, warnings=warnings)

    findings: list[dict[str, Any]] = report["findings"]
    summary: dict[str, Any] = report["summary"]
    patches: list[dict[str, Any]] = report.get("patches", [])

    # 2. no_deferred
    if summary.get("deferred_count", 0) != 0:
        failed_checks.append("no_deferred")

    # 3. findings_valid
    findings_valid = True
    for finding in findings:
        if not isinstance(finding, dict):
            findings_valid = False
            break
        kind = finding.get("kind")
        state = finding.get("terminal_state")
        if kind not in FINDING_KINDS or state not in TERMINAL_STATES:
            findings_valid = False
            break
    if not findings_valid:
        failed_checks.append("findings_valid")

    # 4. patches_consistent
    patch_ids = {
        p.get("patch_id")
        for p in patches
        if isinstance(p, dict) and "patch_id" in p
    }
    patches_consistent = True
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        pid = finding.get("patch_id")
        if pid is not None and pid not in patch_ids:
            patches_consistent = False
            break
    if not patches_consistent:
        failed_checks.append("patches_consistent")

    # 5. summary_consistent
    kind_counts = Counter(
        f.get("kind") for f in findings if isinstance(f, dict) and "kind" in f
    )
    summary_consistent = True
    for kind in FINDING_KINDS:
        if summary.get(kind, 0) != kind_counts.get(kind, 0):
            summary_consistent = False
            break
    if not summary_consistent:
        failed_checks.append("summary_consistent")

    # Warnings
    variant_mixed_count = kind_counts.get("variant_mixed", 0)
    if variant_mixed_count > VARIANT_MIXED_WARNING_THRESHOLD:
        warnings.append(
            f"variant_mixed count ({variant_mixed_count}) exceeds threshold ({VARIANT_MIXED_WARNING_THRESHOLD})"
        )

    passed = len(failed_checks) == 0
    return GateResult(passed=passed, failed_checks=failed_checks, warnings=warnings)
