"""M1 电子文本入库模块。

负责从来源站点读入电子文本原始文件，校验元数据，构造并冻结 source_manifest。
"""

M1_TOOL = "pipeline.intake"
M1_TOOL_VERSION = "0.1.0"
MANIFEST_TASK_ID = "ingest_source"

__all__ = [
    "M1_TOOL",
    "M1_TOOL_VERSION",
    "MANIFEST_TASK_ID",
]
