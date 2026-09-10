# T-08 Tag 区三个耦合接口与字段承接：执行工作包

状态：`IMPLEMENTED_AWAITING_REVIEW`（R2 返工：owner/package 与供给包已改为精确校验；等待主 Agent 独立验收）

## Goal

使 `verify-T.sh` 精确校验 Tag 区契约，而不是只检查字段唯一与 M5 缺席：

1. **三个耦合接口的供给包**：`最小盘面概念字典` → `KnowledgeDataPack`；`MarkContentBinding` → `KnowledgeDataPack` 与 `RuleIndexPack`；`EvidenceBundle` → `EvidenceMapPack`。§16.3.1 与 §1 两处必须同时正确。
2. **五个关键字段的生产 Module 与归属子包逐字段精确相等**：
   - `omen_carrying`：`M4` / `KnowledgeDataPack`
   - `condition_affordance`：`M4` / `RuleIndexPack` 与 `KnowledgeDataPack`
   - `school_variance_display`：`M4 / M6` / `KnowledgeDataPack`
   - `concept_id`：`M4` / `KnowledgeDataPack`
   - 是否改变当前判断：`M4 / M7 / M6` / `KnowledgeDataPack`（`MarkContentBinding`）
3. 保留：M5 仅为 Validator（生产列不得出现 M5）；最小盘面概念字典不含规则 DSL；Tag 的 G4 必须写成 `TAG_SYSTEM_DESIGN.md §12.2` 的命名空间形式。

本轮返工不修改规格正文：§1 与 §16.3 经 G3 R2 复核确认「正文基本正确，默认只读」，门禁必须向正文对齐。

## Authority

- `docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md`（T-08 三条返工项）
- `docs/blackbox-spec-rework/work-items/g3-r2/COLD_START_PROMPT.md`（本轮执行契约）
- `tag_system/README.md:30-32`、`tag_system/TAG_SYSTEM_DESIGN.md`
- `openspec/learn-system-blackbox-architecture.md` §1、§16.3（只读基线）

## Dependencies

- T-07：本轮已返工并提交；
- T-06：已 `ACCEPTED`；
- 与 D-07、T-07 共用同一门禁脚本，必须严格串行。

## Scope

- WRITE：
  - `docs/blackbox-spec-rework/verify-T.sh`（T-08 段精确归属门禁）
  - `docs/blackbox-spec-rework/work-items/t08/`（六件套）
- READ：
  - `docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md`
  - `tag_system/README.md`、`tag_system/TAG_SYSTEM_DESIGN.md`
  - `openspec/learn-system-blackbox-architecture.md` §1、§16.3

## 已作废的旧口径（不得再出现于六件套）

- 旧口径「`omen_carrying` / `condition_affordance` 由 M4/M5 共同生产」——现行规格为 M4 生产、M5 仅校验；
- 旧基线口径「7 FAIL → 5 FAIL」——当前基线为 0 FAIL，判据以变异测试为准；
- 旧指令「唯一允许修改规格正文、严禁修改 `verify-T.sh`」——本轮返工恰恰只改门禁，不改正文；
- 旧提交指令——本轮统一使用 `fix: enforce T-08 ownership mappings`。

## Forbidden

- 禁止篡改字段名（`omen_carrying`、`condition_affordance`、`school_variance_display`、`concept_id`）；
- 禁止把 M5 列为字段生产 Module；
- 禁止把 Tag 侧 G4 裸写而不带 `TAG_SYSTEM_DESIGN.md §12.2` 命名空间；
- 禁止修改规格正文、业务代码、JSON Schema、测试、数据库、依赖或其他工作包；
- 禁止修改 `PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md` 或 G3 总 `ACCEPTANCE.md`；
- 禁止以放宽断言或只看字段名的方式取得绿色结果；
- 禁止把临时变异文件写入仓库（只在 `/tmp` 生成副本）；
- 禁止把状态写成 `ACCEPTED`。

## Stop Conditions

- 正常规格门禁非零，且失败不由本工作包造成；
- 任一强制变异仍返回 0；
- 为实现门禁必须修改规格正文、业务代码或 Scope 外文件；
- 允许文件存在他人的未提交修改。

## ACT Review（wjt-react 四查）

- **忠实性**：owner/package 期望值逐条取自现行 §16.3.2 表格与 §16.3.1/§1 供给声明。
- **可执行性**：规范化规则、期望值、变异命令均确定，可机械重现。
- **可验收性**：正常规格 0 FAIL 与四个变异非零必须同时成立才有效。
- **防越界性**：写范围限于门禁脚本与六件套，规格正文只读；旧冲突口径已删除。
