"""M5 Automatic Validation（规格 §13）工具包。

本包落地 M5 首切片：从 Artifact Ledger 冻结读取已 ``succeeded`` 的 M3
结构层产出，以确定性、不改输入、fail-closed 的 14 个已注册 Validator
执行 G1（来源与可重放性）、G2（全书覆盖）、G3（身份、引用与证据锚点）。
"""

# 工具标识与版本（供 Ledger 记录 configuration 与 Validator 报告时引用）
M5_TOOL = "pipeline.validation"
M5_TOOL_VERSION = "1.0.0"

# 消费级别闭集（规格 §16）
CONSUMPTION_LEVELS = ("INTERNAL_DEMO", "DEV_SEARCH", "PUBLIC_RELEASE")
