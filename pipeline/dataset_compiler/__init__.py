"""M8 Dataset Compilation 工具包（规格 §16）。

首切片（纵切 §22.1）只签发 ``INTERNAL_DEMO`` 消费级别，子包内容以代码草案
契约表达（``schema_version: "0.1.0-draft"``，D5/P3）。
"""

# 工具标识与版本（供 Ledger 记录 configuration_artifact 时引用）
M8_TOOL = "pipeline.dataset_compiler"
M8_TOOL_VERSION = "0.1.0"

# 消费级别闭集（规格 §16:666 逐字）
CONSUMPTION_LEVELS = ("INTERNAL_DEMO", "DEV_SEARCH", "PUBLIC_RELEASE")

# 首切片实际签发的消费级别（§22.1:968）
SUPPORTED_LEVELS = ("INTERNAL_DEMO",)

# 子包内容草案 Schema 版本（D5/P3）
SUB_PACK_SCHEMA_VERSION = "0.1.0-draft"
