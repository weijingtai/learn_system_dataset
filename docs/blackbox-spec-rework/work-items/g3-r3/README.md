# G3 R3 防假绿返工工作包

状态：`SUPERSEDED`（2026-09-10 主 Agent 标记）。本目录除 `mutations.sh` 外的文件是 89 例早期草稿，落后于已提交的 98 例（`ffe19df`）与 109 例（`241c38c`）实现，不得作为执行入口。现行验收证据见 `../g3-r5/ACCEPTANCE.md`。以下为历史内容。

原状态：`PREPARING_ACT_REVIEW`

## Goal

用结构化精确校验替换关键词与有限否定词判断，并建立 89 例永久变异回归套件，使 D-07、T-07、T-08 的已知错误、等价错误和同类错误一次性被拦截。

## Authority

按以下优先级执行：

1. `docs/blackbox-spec-rework/reviews/G3-REVIEW-R3.md`
2. `openspec/learn-system-blackbox-architecture.md` §1、§16.1–§16.3 当前正确正文
3. 本目录 `CANONICAL.md`、`CASES.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`PROMPT.md`
4. D-07、T-07、T-08 原六件套仅作历史证据；与本包冲突时以本包为准

## Design Decision

- 禁止继续扩充否定词黑名单。
- 文档门禁采用三种封闭结构：精确规范句、精确表格字典、精确命名块。
- 规范化只允许去除 Markdown 装饰和空白；不得删除汉字、英文标识、数字、否定词、标点或 Package 名。
- 每个断言同时检查“值正确”和“出现次数恰为 1”。
- 所有期望常量必须硬编码自本工作包，不得从待测 `$SPEC` 动态读取后再与自身比较。
- 每个变异先验证替换确实发生且只发生预期次数；变异未生效必须判测试失败，不能拿正常规格的绿色冒充。
- 所有变异只写 `/tmp`，权威规格正文保持只读。

## Scope

允许修改：

- `docs/blackbox-spec-rework/verify-T.sh`
- 新增 `docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh`

禁止修改：规格正文、业务代码、Schema、依赖、任何 BDD/TDD/ACT/Prompt/Acceptance、PLAN、HANDOFF、总 TODO、G3 总验收、其他工作包。执行证据由最终报告交给主 Agent 落盘。

## Execution Order

1. ACT 01：建立 harness 骨架和自检。
2. ACT 02：录入 D-07 的 25 个 case，保存 Red。
3. ACT 03：录入 T-07 的 25 个 case，保存 Red。
4. ACT 04：录入 T-08 的 39 个 case，冻结 89 例完整 Red。
5. ACT 05：修 D-07，25/25 转 Green。
6. ACT 06：修 T-07，25/25 转 Green。
7. ACT 07：修 T-08，39/39 及 89/89 转 Green。
8. 只报告证据，等待主 Agent 验收，不启动 G4。

## Stop Conditions

- 当前分支不是 `codex/docs/knowledge-compilation`，或 `e0e62a8` 不是 HEAD 祖先。
- 允许修改文件存在他人的未提交修改。
- 任何任务要求改动规格正文或 Scope 外文件。
- 变异替换次数不是预期值。
- 正常规格门禁变红，或非目标 T/D 项出现退化。
- 前一阶段未提交便开始后一阶段。

七个机械 ACT 位于 `act/01.yaml`～`act/07.yaml`，必须串行执行；每项标注 45–60 分钟预算。
