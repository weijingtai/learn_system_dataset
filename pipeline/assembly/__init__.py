"""M7 增量知识汇编子系统（spec §15, §6.2）。"""

M7_TOOL = "pipeline.assembly"
M7_TOOL_VERSION = "0.1.0"
SNAPSHOT_SCHEMA_VERSION = "0.1.0-draft"
M6_STAGE_PACKAGE_STAGE = "m6"
SNAPSHOT_ARTIFACT_TYPE = "canonical_snapshot"
PACKAGE_ARTIFACT_TYPE = "assembly_package"

__all__ = [
    "M7_TOOL",
    "M7_TOOL_VERSION",
    "SNAPSHOT_SCHEMA_VERSION",
    "M6_STAGE_PACKAGE_STAGE",
    "SNAPSHOT_ARTIFACT_TYPE",
    "PACKAGE_ARTIFACT_TYPE",
]
