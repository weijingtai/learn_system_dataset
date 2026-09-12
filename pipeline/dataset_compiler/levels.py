"""消费级别准入纯函数（规格 §16:666-678、§8.2:341-347，裁决 D9/D12）。

纯函数：不读文件、不访问 Ledger。合法但不满足准入的级别不抛异常，而是把
未满足项写入返回的 ``unmet`` 集合，由调用方在 begin 之后以 ``admission``
失败封存（§17:836）。
"""

import re

from pipeline.dataset_compiler import CONSUMPTION_LEVELS
from pipeline.dataset_compiler.errors import DatasetRefused
from pipeline.ledger.errors import SchemaViolation

# §8.2:341-347 内容成熟度闭集（逐字）
CONTENT_STATUSES = (
    "source_verified",
    "machine_extracted",
    "cross_model_reviewed",
    "disputed",
    "needs_expert",
    "expert_verified",
    "deprecated",
)

# §16:719-721 发布策略闭集
RELEASE_POLICIES = (
    "full_scan",
    "derived_page_images_only",
    "reference_and_hash_only",
)

# §11.1:527-528 证据级别闭集
EVIDENCE_LEVELS = ("offset_level", "glyphbox_level")

_MIN_APP_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def derive_source_release(content_statuses):
    """按 D9 推导来源发布级别：全部 ``expert_verified`` 才为 ``release``。

    空集合 → ``SCH_001``；未知状态 → ``SCH_002``；含 ``deprecated`` → 拒绝
    （``DatasetRefused(SCH_002)``）；其余为 ``dev``。
    """
    statuses = list(content_statuses)
    if not statuses:
        raise SchemaViolation("content_statuses 不能为空", code="SCH_001")
    for status in statuses:
        if status not in CONTENT_STATUSES:
            raise SchemaViolation(
                "未知内容状态: %r（§8.2 闭集）" % (status,), code="SCH_002"
            )
    if "deprecated" in statuses:
        raise DatasetRefused(
            "内容状态含 deprecated，拒绝编译（§8.2）", code="SCH_002"
        )
    if all(status == "expert_verified" for status in statuses):
        return "release"
    return "dev"


def evaluate_admission(
    *,
    consumption_level,
    content_statuses,
    evidence_level,
    release_policy,
    rights_status,
    schema_versions,
    min_app_version,
):
    """判定消费级别准入，返回准入结果 dict（D9/D10/D12）。

    返回键：``consumption_level``、``source_release``、``admitted``、
    ``unmet``（按字典序）、``watermark_required``、``isolation``。
    """
    # R0：枚举与格式校验（非法在 begin 之前以 SCH_002 拒绝）
    if consumption_level not in CONSUMPTION_LEVELS:
        raise SchemaViolation(
            "消费级别非法: %r（§16:666 闭集）" % (consumption_level,), code="SCH_002"
        )
    if evidence_level not in EVIDENCE_LEVELS:
        raise SchemaViolation(
            "证据级别非法: %r（§11.1 闭集）" % (evidence_level,), code="SCH_002"
        )
    if release_policy not in RELEASE_POLICIES:
        raise SchemaViolation(
            "发布策略非法: %r（§16 闭集）" % (release_policy,), code="SCH_002"
        )
    if min_app_version is not None and _MIN_APP_VERSION_RE.match(min_app_version) is None:
        raise SchemaViolation(
            "min_app_version 必须匹配 ^[0-9]+\\.[0-9]+\\.[0-9]+$: %r" % (min_app_version,),
            code="SCH_002",
        )

    # R1：来源发布级别（含 deprecated 拒绝）
    source_release = derive_source_release(content_statuses)

    # R2：未满足项集合
    unmet = set()
    if release_policy != "derived_page_images_only":
        unmet.add("release_policy_not_implemented")
    if consumption_level == "DEV_SEARCH":
        unmet.add("dev_search_gates_not_implemented")
    if consumption_level == "PUBLIC_RELEASE":
        # 恒加：PUBLIC_RELEASE 门禁未实现，fail-closed
        unmet.add("public_release_gates_not_implemented")
        if source_release == "dev":
            unmet.add("source_release_dev")
        if any(status != "expert_verified" for status in content_statuses):
            unmet.add("content_not_expert_verified")
        if evidence_level != "glyphbox_level":
            unmet.add("evidence_level_not_glyphbox")
        if isinstance(rights_status, str) and "unconfirmed" in rights_status:
            unmet.add("rights_unconfirmed")
        if any(str(value).endswith("-draft") for value in schema_versions.values()):
            unmet.add("draft_schema")
        if min_app_version is None:
            unmet.add("min_app_version_unset")

    unmet_list = sorted(unmet)

    # R3：返回结果
    return {
        "consumption_level": consumption_level,
        "source_release": source_release,
        "admitted": len(unmet_list) == 0,
        "unmet": unmet_list,
        "watermark_required": any(
            status.startswith("machine_") for status in content_statuses
        ),
        "isolation": "internal_only" if consumption_level == "INTERNAL_DEMO" else "none",
    }
