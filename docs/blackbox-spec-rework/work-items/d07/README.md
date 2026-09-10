# D-07 TechniqueProfilePack 与 QueryContractPack 工作包

状态：`READY`

## Goal

在黑箱架构规格中完整定义 `TechniqueProfilePack` 与 `QueryContractPack` 两个子包，规范 `FactSet`、事实字段与枚举、operator 集合、规则 AST schema 版本、只读查询接口（`getEntry`、`getSourceSpan`、`searchKnowledge`、`matchFacts`）及语义兼容性声明；明确 `RuleIndexPack` 中每条规则声明所依据的 Profile 版本，规则纯声明式 AST 表达（禁止可执行 Python），并在 M5 中建立规则对 FactSet 可执行性的 G6 验证，明确 M5 仅做验证而不负责生产 Tag 字段。

## Authority

- `docs/blackbox-spec-rework/D-design.md` §D-07
- `pipeline/DATASET_ACCEPTANCE_STANDARD.md` §4-G6
- `LEARN_SYSTEM_TARGET.md` §7
- `openspec/subagent-delivery-gate.md`
- 2026-09-08 用户裁定：首纵切采用 `QizhengFactSet`

## Dependencies

- D-01（`entity_id` 拆分）：`ACCEPTED`
- D-05（Pattern / Concept / KnowledgeEntry 三层结构）：`ACCEPTED`
- T-04（G1–G7 门禁）：`ACCEPTED`
- T-06（证据链）：`ACCEPTED`
- T-11（差距表）：`ACCEPTED`
- T-13（状态标签）：`ACCEPTED`

## Scope

- WRITE：
  - `openspec/learn-system-blackbox-architecture.md`（§13, §16）
  - `docs/blackbox-spec-rework/work-items/d07/`（六件套）
  - `docs/blackbox-spec-rework/verify-T.sh`（增加 D-07 语义门禁）
- READ：
  - `docs/blackbox-spec-rework/D-design.md`
  - `pipeline/DATASET_ACCEPTANCE_STANDARD.md`
  - `LEARN_SYSTEM_TARGET.md`
  - `openspec/learn-system-blackbox-architecture.md`

## Forbidden

- 严禁修改业务代码、Schema、数据库或 fixture；
- 严禁修改 `PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`；
- 严禁触碰或还原并发中的注解系统文档（`docs/annotation-community/`、`openspec/annotation-community/`）；
- 规则不得允许可执行 Python 代码，必须强制结构化 AST / YAML / JSON；
- M5 仅负责 FactSet 可执行性校验，严禁将 M5 列为 Tag 字段生产工位；
- 严禁仅靠简单关键词计数作为验收依据。

## Stop Conditions

- 若旧规格无法证明为红（Red），立即停止；
- 若变异测试删除四接口之一、Profile version、AST version 或 FactSet 时门禁未报失败，立即停止；
- 若出现非授权文件修改，立即停止。

## ACT Review（wjt-react 四查）

- **忠实性**：涵盖 TechniqueProfilePack、QueryContractPack、四查询接口、AST schema 版本、FactSet profile、Profile 声明、禁止 Python 规则及 M5 G6 校验。
- **可执行性**：写路径明确，命令确定，Red/Green 步骤与负向变异可机械重现。
- **可验收性**：正反判据均采用非零退出码与二元断言，杜绝假绿。
- **防越界性**：严格圈定三个写文件，显式禁止触碰工作区并发文件。
