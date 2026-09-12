"""M3 Corpus Compilation 结构层工具包（规格 §11）。

本批只落地结构层：StructuralSpan + SourceAnchor（``glyphbox_level``）+
批次 + 独立结构 Gate。SemanticSpan（规格 §11 第 2–5 条：双模型边界提议、
分歧人工裁决）本批不做，见工作项 README「主 Agent 决定」。
"""

# 工具标识与版本（供 Ledger 记录 configuration_artifact 时引用）
M3_TOOL = "pipeline.corpus_compiler"
M3_TOOL_VERSION = "0.1.0"
