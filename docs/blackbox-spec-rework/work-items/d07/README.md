# D-07 TechniqueProfilePack 与 QueryContractPack 工作包

状态：`IMPLEMENTED_AWAITING_REVIEW`（R2 返工：门禁已改为专属块解析；等待主 Agent 独立验收）

## Goal

使 `verify-T.sh` 对 `TechniqueProfilePack`、`QueryContractPack`、`RuleIndexPack` 三份契约**各自在专属段内**闭合校验，禁止 §16 其他文字跨块代偿；并同步本工作包六件套，消除与现行规格冲突的旧口径。

本轮返工不修改规格正文：`openspec/learn-system-blackbox-architecture.md` §13、§16.1–§16.3 经 G3 R2 复核确认「正文基本正确，默认只读」，门禁必须向正文对齐。

## Authority

- `docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md`（D-07 四条返工项）
- `docs/blackbox-spec-rework/work-items/g3-r2/COLD_START_PROMPT.md`（本轮执行契约）
- `openspec/learn-system-blackbox-architecture.md` §13、§16（只读基线）
- `docs/blackbox-spec-rework/verify-T.sh`

## Dependencies

- D-01 / D-05 / T-04 / T-06 / T-11 / T-13：均已 `ACCEPTED`
- 与 T-07、T-08 共用同一门禁脚本，必须严格串行

## Scope

- WRITE：
  - `docs/blackbox-spec-rework/verify-T.sh`（D-07 段专属块门禁）
  - `docs/blackbox-spec-rework/work-items/d07/`（六件套）
- READ：
  - `docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md`
  - `openspec/learn-system-blackbox-architecture.md` §13、§16

## Forbidden

- 禁止修改规格正文、业务代码、Schema、数据库、fixture、依赖、Tag 权威文档；
- 禁止修改 `PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md` 或 G3 总 `ACCEPTANCE.md`；
- 禁止把临时变异文件写入仓库（只在 `/tmp` 生成副本）；
- 禁止以放宽断言、固定返回码、只数关键词的方式取得绿色结果；
- 禁止把状态写成 `ACCEPTED`。

## 门禁设计要点

三份契约的导语行是唯一锚点，切片规则为「从导语行到下一个专属段导语或下一个标题」，锚点缺失或重复出现即 FAIL：

| 专属块 | 锚点导语 | 块内强制断言 |
|---|---|---|
| `TP` | 承载各术数领域确定性事实结构与规则语法标准 | `FactSet Profile`、`事实字段与枚举` + `闭集枚举`（且不得被 `客户端自由猜测` 等否定语义取代）、`operator 集合`、`AST schema 版本`、`禁止…可执行或模型生成…Python` |
| `QC` | 规范发布包对外暴露的确定性只读查询契约 | `getEntry`、`getSourceSpan`、`searchKnowledge`、`matchFacts`、向后兼容声明 |
| `RI` | 承载确定性适用规则索引 | `每条规则` + `显式声明` + `profile_version` + `AST schema 版本`、`结构化 AST/YAML/JSON` |

§13 另断言 M5 在 G6 下校验 FactSet 可执行性，且写明不负责生产（仅 Validator）。

## Stop Conditions

- 正常规格门禁非零，且失败不由本工作包造成；
- 任一强制变异仍返回 0；
- 为实现门禁必须修改规格正文、业务代码或 Scope 外文件；
- 允许文件存在他人的未提交修改。

## ACT Review（wjt-react 四查）

- **忠实性**：断言逐条对应 §16 正文事实，不改写、不压缩既有正确语义。
- **可执行性**：锚点、切片规则、变异命令均确定，可机械重现。
- **可验收性**：正常规格 0 FAIL 与三个变异非零必须同时成立才有效。
- **防越界性**：写范围限于门禁脚本与六件套，规格正文只读。
