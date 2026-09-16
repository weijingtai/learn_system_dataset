"""M2 决定表：人工终态决定表加载与 §7.1 人工事件登记。

实现 load_decisions 与 check_decisions_coverage 纯函数。
"""

from __future__ import annotations

from typing import Any

from .cleaner import Finding
from .errors import DigitizationRefused

ALLOWED_TERMINAL_STATES = frozenset({"processed", "known_unresolvable", "deferred"})
EXPECTED_SCHEMA_VERSION = "1.0.0"


def load_decisions(data: dict[str, Any]) -> dict[str, Any]:
    """校验并加载人工终态决定表。

    参数：
        data：人工决定表字典。

    返回：
        规范化字典，固定键序：schema_version, edition_part_artifact_id, entries。

    异常：
        DigitizationRefused：校验失败，错误码 SCH_001 或 SCH_002。
    """
    if not isinstance(data, dict):
        raise DigitizationRefused("decisions 数据必须为字典", code="SCH_001")

    # 顶层必填键
    for key in ("schema_version", "edition_part_artifact_id", "entries"):
        if key not in data:
            raise DigitizationRefused(f"decisions 缺少顶层必填键: {key}", code="SCH_001")

    if data["schema_version"] != EXPECTED_SCHEMA_VERSION:
        raise DigitizationRefused(
            f"schema_version 必须为 {EXPECTED_SCHEMA_VERSION}，实际为 {data['schema_version']}",
            code="SCH_002",
        )

    edition_part_artifact_id = data["edition_part_artifact_id"]
    if not isinstance(edition_part_artifact_id, str) or not edition_part_artifact_id.strip():
        raise DigitizationRefused("edition_part_artifact_id 必须为非空字符串", code="SCH_001")

    entries_raw = data["entries"]
    if not isinstance(entries_raw, list):
        raise DigitizationRefused("entries 必须为列表", code="SCH_001")

    cleaned_entries = []
    for idx, entry in enumerate(entries_raw):
        if not isinstance(entry, dict):
            raise DigitizationRefused(f"entries[{idx}] 必须为字典", code="SCH_001")

        for req_key in ("page", "terminal_state", "reason", "decided_by"):
            if req_key not in entry:
                raise DigitizationRefused(f"entries[{idx}] 缺少必填键: {req_key}", code="SCH_001")

        terminal_state = entry["terminal_state"]
        if terminal_state not in ALLOWED_TERMINAL_STATES:
            raise DigitizationRefused(
                f"entries[{idx}] terminal_state 非法: {terminal_state}",
                code="SCH_002",
            )

        reason = entry["reason"]
        if not isinstance(reason, str) or not reason.strip():
            raise DigitizationRefused(f"entries[{idx}] reason 必须为非空字符串", code="SCH_001")

        decided_by = entry["decided_by"]
        if not isinstance(decided_by, str) or not decided_by.strip():
            raise DigitizationRefused(f"entries[{idx}] decided_by 必须为非空字符串", code="SCH_001")

        cleaned_entry = {
            "page": entry["page"],
            "terminal_state": terminal_state,
            "reason": reason,
            "decided_by": decided_by,
        }
        if "finding_id" in entry:
            cleaned_entry["finding_id"] = entry["finding_id"]
        if "note" in entry:
            cleaned_entry["note"] = entry["note"]

        cleaned_entries.append(cleaned_entry)

    return {
        "schema_version": EXPECTED_SCHEMA_VERSION,
        "edition_part_artifact_id": edition_part_artifact_id,
        "entries": cleaned_entries,
    }


def check_decisions_coverage(
    decisions: dict[str, Any],
    findings: list[Finding],
) -> list[str]:
    """检查人工决定表是否覆盖全部 deferred 发现。

    返回需要决定但缺决定的 finding_id 列表。
    """
    entries = decisions.get("entries", [])
    decided_ids = {
        e.get("finding_id")
        for e in entries
        if isinstance(e, dict) and e.get("finding_id")
    }

    missing: list[str] = []
    for f in findings:
        if f.terminal_state == "deferred":
            if f.finding_id not in decided_ids:
                missing.append(f.finding_id)

    return missing
