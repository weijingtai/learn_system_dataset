"""Artifact / StepRun 状态机与枚举闭集（规格 §8.2）。

四轴正交：Artifact status、StepRun status、Content Maturity、ReviewDecision Type。
迁移表逐字按 §8.2 第 4/5 节；表外取值抛 ``SchemaViolation(SCH_002)``，
表内但不合法的迁移抛 ``IllegalTransition``。
"""

from .errors import IllegalTransition, SchemaViolation

# §8.2 第 4 节：Artifact Revision 物理状态闭集
ARTIFACT_STATUS = ("draft", "sealed", "quarantined", "invalidated", "superseded")

# §8.2 第 4 节：Artifact status 合法迁移全集（未列出的迁移一律非法）
ARTIFACT_TRANSITIONS = {
    "draft": {"sealed", "quarantined"},
    "sealed": {"invalidated", "superseded"},
    "quarantined": {"superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
}

# §8.2 第 5 节：StepRun status 闭集
STEP_RUN_STATUS = (
    "running",
    "awaiting_human",
    "suspended",
    "succeeded",
    "failed",
    "superseded",
)

# §8.2 第 5 节：StepRun status 合法迁移全集（未列出的迁移一律非法）
STEP_RUN_TRANSITIONS = {
    "running": {"awaiting_human", "suspended", "succeeded", "failed", "superseded"},
    "awaiting_human": {"running", "suspended", "failed", "superseded"},
    "suspended": {"running", "failed", "superseded"},
    "succeeded": set(),
    "failed": set(),
    "superseded": set(),
}

# StepRun 终态闭集（无出边）
TERMINAL_STEP_RUN = frozenset({"succeeded", "failed", "superseded"})

# §8.2 第 1 节：内容成熟度状态闭集
CONTENT_MATURITY = (
    "source_verified",
    "machine_extracted",
    "cross_model_reviewed",
    "disputed",
    "needs_expert",
    "expert_verified",
    "deprecated",
)

# §8.2 第 2 节：专家审核决定类型闭集（8 类）
REVIEW_DECISION_TYPES = (
    "review_source_fidelity",
    "review_edition_collation",
    "review_school_attribution",
    "review_explanation_quality",
    "review_case_authenticity",
    "review_practical_validity",
    "review_safety",
    "review_rights",
)


def check_artifact_transition(cur, nxt):
    """校验 Artifact status 迁移；合法则返回目标状态。

    表外取值抛 ``SchemaViolation(code='SCH_002')``；表内不合法迁移抛 ``IllegalTransition``。
    """
    if cur not in ARTIFACT_TRANSITIONS or nxt not in ARTIFACT_TRANSITIONS:
        raise SchemaViolation(
            "非法 Artifact status 取值: %r→%r" % (cur, nxt), code="SCH_002"
        )
    if nxt not in ARTIFACT_TRANSITIONS[cur]:
        raise IllegalTransition("非法 Artifact status 迁移: %s→%s" % (cur, nxt))
    return nxt


def check_step_run_transition(cur, nxt):
    """校验 StepRun status 迁移；合法则返回目标状态。

    表外取值抛 ``SchemaViolation(code='SCH_002')``；表内不合法迁移抛 ``IllegalTransition``。
    """
    if cur not in STEP_RUN_TRANSITIONS or nxt not in STEP_RUN_TRANSITIONS:
        raise SchemaViolation(
            "非法 StepRun status 取值: %r→%r" % (cur, nxt), code="SCH_002"
        )
    if nxt not in STEP_RUN_TRANSITIONS[cur]:
        raise IllegalTransition("非法 StepRun status 迁移: %s→%s" % (cur, nxt))
    return nxt
