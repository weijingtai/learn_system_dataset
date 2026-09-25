"""Local Orchestrator（规格 §5/§6.1/§7/§7.1/§17）。

首纵切最薄切片：阶段推进、独立 Stage Gate、EditionRun/release 段、人工暂停恢复与
六项只读查询。本包不 import 任何加工 Module 包，Module 只经登记表 ``entry``
（importlib）或 ``modules=`` 注入解析。
"""

# 工具标识与版本
ORCH_TOOL = "pipeline.orchestrator"
ORCH_TOOL_VERSION = "0.1.0"

# §6.1 :138：EditionRun 阶段基准（§20.1 的 M1–M6 判据）
EDITION_STAGES = ("m1", "m2", "m3", "m4", "m5", "m6")

# release 段：M7 → M8 两个 legacy 步，各自建 ProcessingRun（TODO T04B；§6.2 ReleaseRun 状态机 DEFERRED）
RELEASE_STAGES = ("m7", "m8")

# 首纵切计划（m4/m6 为已声明缺口）
FIRST_SLICE_EDITION_STAGES = ("m1", "m2", "m3", "m5")

# 首纵切未串联、缺生产 Module 的阶段
DEFERRED_STAGES = ("m4", "m6")
