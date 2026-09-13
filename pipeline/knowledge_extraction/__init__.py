"""M4 Knowledge Extraction 最薄接入（规格 §12、§12.1、§12.2、§22.3 阶段 1）。

本包首切片不调用任何模型（P6）：候选只来自提交件 Adapter 的登记（fixture 金标、
人工/外部 Agent 按工位 5 格式写出的草稿）。产出 ``content_status`` 上限为
``needs_expert``，不得出现 ``expert_verified`` / ``cross_model_reviewed``（P7）。
"""

from pipeline.ledger.errors import ERROR_CODES as M4_ERROR_CODES

M4_TOOL = "pipeline.knowledge_extraction"
M4_TOOL_VERSION = "0.1.0"
CANDIDATE_SCHEMA_VERSION = "0.1.0-draft"

# 候选类别、路别、渠道与生产者闭集（§5.2、§6.2）
CATEGORIES = ("assertion", "pattern", "school_view", "concept_mention")
LANES = ("a", "b", "c")
CHANNELS = ("fixture_gold", "task_pipeline_manual", "model_adapter", "legacy_workbench")
ACCEPTED_CHANNELS = ("fixture_gold", "task_pipeline_manual")  # D-01：首切片只收前两个
PRODUCER_KINDS = ("fixture", "human", "external_agent", "model")

# 主张闭集（SCHEMA.md §4）
RELATIONS = ("supports", "qualifies", "opposes", "corresponds", "equivalent")
# 主张层闭集（§13.1 G4：通则 / 命例 / 注文·异文·校勘；与 INTERFACES §3.2 一致）
LAYERS = ("general", "case", "editorial")
SUPPORT_TYPES = ("direct", "interpreted")

# M4 产出的内容成熟度上限（P7）
M4_STATUS_CEILING = ("machine_extracted", "disputed", "needs_expert")

# 被拒条目的处置闭集（§6.3）
REJECT_DISPOSITIONS = ("refused", "ruled_out")

# 各类别 item 的必填 / 可选键（§6.2 表）
ITEM_KEYS = {
    "assertion": {
        "required": ("proposition", "relation", "evidence"),
        "optional": ("conditions", "exceptions", "concept_refs", "school_ids", "layer", "status"),
    },
    "pattern": {
        "required": ("name", "assertion_propositions", "evidence"),
        "optional": ("interpretation", "status"),
    },
    "school_view": {
        "required": (
            "school_id",
            "subject",
            "claim_propositions",
            "changes_current_judgment",
            "evidence",
        ),
        "optional": ("conflict_key", "status"),
    },
    "concept_mention": {
        "required": ("surface", "evidence"),
        "optional": ("concept_ref", "status"),
    },
}
