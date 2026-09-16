"""M2 纯函数：SanitizationReport 生成（规格 §4.4、§81）。

提供 build_sanitization_report，构造固定键序的发现报告与统计摘要。
"""

from . import FINDING_KINDS
from .cleaner import Finding
from .patcher import Patch


def build_sanitization_report(findings: list[Finding], patches: list[Patch]) -> dict:
    """构建 SanitizationReport 报告字典。

    参数：
        findings：发现项对象列表。
        patches：修补项对象列表。

    返回：
        符合契约结构的字典对象。
    """
    # 统计各 kind 数量
    summary = {k: 0 for k in FINDING_KINDS}
    deferred_count = 0

    serialized_findings = []
    for f in findings:
        summary[f.kind] = summary.get(f.kind, 0) + 1
        if f.terminal_state == "deferred":
            deferred_count += 1

        finding_dict = {
            "finding_id": f.finding_id,
            "kind": f.kind,
            "raw_start": f.raw_start,
            "raw_end": f.raw_end,
            "raw_excerpt": f.raw_excerpt,
            "context": f.context,
            "action": f.action,
            "patch_id": f.patch_id,
            "basis": f.basis,
            "terminal_state": f.terminal_state,
        }
        serialized_findings.append(finding_dict)

    summary["deferred_count"] = deferred_count

    serialized_patches = []
    for p in patches:
        patch_dict = {
            "patch_id": p.patch_id,
            "raw_start": p.raw_start,
            "raw_end": p.raw_end,
            "cleaned_start": p.cleaned_start,
            "cleaned_end": p.cleaned_end,
            "action": p.action,
            "basis": p.basis,
        }
        serialized_patches.append(patch_dict)

    return {
        "schema_version": "0.1.0-draft",
        "findings": serialized_findings,
        "patches": serialized_patches,
        "summary": summary,
    }
