"""薄 M1 页图登记 shim（D2；impl-09 M1 落地后替换）。

文件与 CLI 名显式标 ``m1_shim``：本模块是本包唯一读文件的生产代码，职能属
M1 Source Intake（§22.3:991「手工登记 SourceAsset」）。
"""

SHIM_TOOL = "pipeline.dataset_compiler.shim.m1_shim"
SHIM_TOOL_VERSION = "0.1.0"
