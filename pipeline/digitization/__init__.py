"""M2 电子文本清洗模块。

实现十三项清洗检查、确定性 patch 映射与 SanitizationReport 生成。
"""

M2_TOOL = "pipeline.digitization"
M2_TOOL_VERSION = "0.1.0"

FINDING_KINDS = (
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
)

TERMINAL_STATES = (
    "processed",
    "known_unresolvable",
    "deferred",
)

ACTIONS = (
    "kept",
    "patched",
    "flagged",
)

__all__ = [
    "M2_TOOL",
    "M2_TOOL_VERSION",
    "FINDING_KINDS",
    "TERMINAL_STATES",
    "ACTIONS",
]
