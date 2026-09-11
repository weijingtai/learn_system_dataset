# G3 R3 Executor Prompt

> 状态：`SUPERSEDED`，不得派发。本 Prompt 对应的 89 例草稿已被 `ffe19df`（98 例）与 `241c38c`（109 例）取代；G3 R5 已 `ACCEPTED`，见 `../g3-r5/`。以下为历史内容。

你是 G3 R3 防假绿返工执行 Agent。进入 `/Users/jingtaiwei/Git/Public/learn_system` 当前工作树，不切换分支。

先完整阅读：`AGENTS.md`、`HANDOFF.md`、`PLAN.md`、`docs/blackbox-spec-rework/reviews/G3-REVIEW-R3.md`，然后完整阅读本目录 `README.md`、`BDD.md`、`CANONICAL.md`、`CASES.md`、`TDD.md`、`ACT.yaml`、`act/01.yaml`～`act/07.yaml`。这些文件包含全部背景、权威常量、89 个稳定 case、范围和停手条件，不依赖任何聊天上下文。

严格执行：

1. 确认分支为 `codex/docs/knowledge-compilation`，确认 `e0e62a8` 是 HEAD 祖先，记录 HEAD 和工作区状态；允许文件若有重叠脏改动立即停手。
2. 严格按 `act/01.yaml`～`act/07.yaml` 串行执行。先新增 `mutations.sh` 骨架，再按 `CASES.md` 逐组录入 d07-01..25、t07-01..25、t08-01..39。每例先断言 Anchor 精确命中，再用独立临时副本和 `SPEC=` 运行门禁。expected 常量只来自 `CANONICAL.md`。
3. 修 D-07：精确匹配三个 Package 起始行与唯一向后兼容规范句；禁止否定词枚举。运行正常门禁和 `d07`，通过后独立提交。
4. 修 T-07：对 TDD 中全部 15 项映射做完整字典精确比较；取代声明必须唯一且整句精确相等。运行正常门禁和 `t07`，通过后独立提交。
5. 修 T-08：精确验证 §1 三行、§16.3.1 三个标题块及唯一供给声明、§16.3.2 五字段表和上方五条说明；拒绝接口子串、额外包、重复供给和 M5 生产者。运行正常门禁、`t08` 和 `all`，通过后独立提交。
6. 最终运行 ACT 的全部验证。必须恰有 89 例，正常规格必须 0 FAIL，`MUTATIONS: 89/89 rejected`，格式检查必须通过。
7. 不修改任何工作包或验收文档；把实际证据放在最终报告交给主 Agent。不要宣布 G3 通过，不要启动 G4。

实现原则：比较“完整结构和值”，不是猜测自然语言含义。任何为了让测试通过而放宽断言、跳过变异、忽略替换失败、固定返回码或缩减矩阵，均视为任务失败。

最终报告必须包含七个提交、真实文件清单、Red/Green 输出、每组与总变异计数、格式检查、工作区状态以及“等待主 Agent 独立验收；未启动 G4”。
