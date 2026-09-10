# T-07 §16.2 映射表唯一性与肯定语义门禁：执行工作包

状态：`IMPLEMENTED_AWAITING_REVIEW`（R2 返工：门禁已改为精确相等校验；等待主 Agent 独立验收）

## Goal

使 `verify-T.sh` 对 §16.2 双向映射表做**唯一落点**校验：15 行目录项各出现且仅出现一次，右列必须规范化后精确相等，禁止在正确归属后追加第二个子包；取代声明必须在同一句肯定语义中包含 `PublicationPackage`、`KnowledgeDataPack`、`正式取代`、`KnowledgePack`，「不得取代」等否定句一律失败。

本轮返工不修改规格正文：§16.2 经 G3 R2 复核确认「正文基本正确，默认只读」，门禁必须向正文对齐。

## Authority

- `docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md`（T-07 四条返工项）
- `docs/blackbox-spec-rework/work-items/g3-r2/COLD_START_PROMPT.md`（本轮执行契约）
- `openspec/learn-system-blackbox-architecture.md` §16.2（只读基线）
- `LEARN_SYSTEM_TARGET.md §9`（15 个早期目录项来源）

## Dependencies

- D-07：本轮已返工并提交；
- T-06 / T-05 / T-04：均已 `ACCEPTED`；
- 与 D-07、T-08 共用同一门禁脚本，必须严格串行。

## Scope

- WRITE：
  - `docs/blackbox-spec-rework/verify-T.sh`（T-07 段精确映射门禁）
  - `docs/blackbox-spec-rework/work-items/t07/`（六件套）
- READ：
  - `docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md`
  - `openspec/learn-system-blackbox-architecture.md` §16.2
  - `LEARN_SYSTEM_TARGET.md §9`

## 已作废的旧口径（不得再出现于六件套）

- 旧指令「唯一允许修改规格正文、严禁修改 `verify-T.sh`」——本轮返工恰恰只改门禁，不改正文；
- 旧映射 `query-contract` → `RuleIndexPack` 与 `SearchIndexPack`——现行规格已唯一归属 `QueryContractPack`；
- 旧基线口径「8 FAIL → 7 FAIL」——当前基线为 0 FAIL，判据以变异测试为准。

## Forbidden

- 禁止修改规格正文、业务代码、JSON Schema、测试、数据库、依赖、Tag 权威文档；
- 禁止修改 `PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md` 或 G3 总 `ACCEPTANCE.md`；
- 禁止在映射表中留空行或删减 15 项中的任何一项；
- 禁止以子串匹配、关键词计数或放宽断言的方式取得绿色结果；
- 禁止把临时变异文件写入仓库（只在 `/tmp` 生成副本）；
- 禁止把状态写成 `ACCEPTED`。

## 门禁设计要点

| 断言 | 判据 |
|---|---|
| 表格结构 | 数据行总数严格等于 15，15 个 key 各出现且仅出现一次 |
| `query-contract` | 规范化（去反引号与空白）后精确等于 `QueryContractPack（查询契约与接口定义）` |
| `optional-vector-index` | 规范化后精确等于 `本期不产出（依据§21非目标）` |
| 取代声明 | 同一行同时含 `PublicationPackage`、`KnowledgeDataPack`、`正式取代`、`KnowledgePack`；出现 `不得取代` 等否定式即失败 |

## Stop Conditions

- 正常规格门禁非零，且失败不由本工作包造成；
- 任一强制变异仍返回 0；
- 为实现门禁必须修改规格正文、业务代码或 Scope 外文件；
- 允许文件存在他人的未提交修改。

## ACT Review（wjt-react 四查）

- **忠实性**：校验值直接取自 §16.2 现行正文，不新增、不改写语义。
- **可执行性**：规范化规则、期望字符串与变异命令均确定，可机械重现。
- **可验收性**：正常规格 0 FAIL 与三个变异非零必须同时成立才有效。
- **防越界性**：写范围限于门禁脚本与六件套，规格正文只读；旧冲突指令已删除。
