# G3 R2 冷启动返工执行契约

状态：`SUPERSEDED_BY_R3_REVIEW`。本文件规定的 10 个变异已经修复，但 R3 发现 7 个新假绿；不得再次把本文件作为放行依据。后续返工以 `../../reviews/G3-REVIEW-R3.md` 为准，待新的冷启动执行契约生成后再派发。

## Goal

修复 D-07、T-07、T-08 的验收假绿与六件套冲突，使 10 个强制错误变异全部被机器门禁拒绝；完成后只提交返工证据，等待主 Agent 独立验收，不自行启动 G4。

## One-Line Launch Prompt

你是 G3 R2 文档返工执行 Agent。进入 `/Users/jingtaiwei/Git/Public/learn_system`，从头完整阅读 `AGENTS.md`、`HANDOFF.md`、`PLAN.md` 和 `docs/blackbox-spec-rework/work-items/g3-r2/COLD_START_PROMPT.md`，严格按 D-07 → T-07 → T-08 串行执行，每项独立提交；不得修改业务代码、不得自行宣布 G3 通过或启动 G4，遇到本契约的停手条件立即报告。

## Baseline

- 仓库：`/Users/jingtaiwei/Git/Public/learn_system`
- 分支：`codex/docs/knowledge-compilation`；保持当前分支，禁止切换分支或进入其他 worktree。
- 起点应包含验收回退提交 `cc03b79`。运行 `git merge-base --is-ancestor cc03b79 HEAD` 验证它是当前 `HEAD` 的祖先；否则停止报告。
- 正常规格当前运行 `bash docs/blackbox-spec-rework/verify-T.sh` 为 `FAIL 合计: 0`。这不是完成证据，因为错误变异仍能返回 0。
- 权威缺陷台账：`docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md`。
- 权威规格正文：`openspec/learn-system-blackbox-architecture.md` §16.1–§16.3。正文当前基本正确，默认只读；门禁和六件套必须与它对齐。

## Read Set

开始执行前完整阅读：

1. `AGENTS.md`、`HANDOFF.md`、`PLAN.md`
2. `docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md`
3. `docs/blackbox-spec-rework/verify-T.sh`
4. `openspec/learn-system-blackbox-architecture.md` §16.1–§16.3
5. `docs/blackbox-spec-rework/work-items/d07/` 全部文件
6. `docs/blackbox-spec-rework/work-items/t07/` 全部文件
7. `docs/blackbox-spec-rework/work-items/t08/` 全部文件

## Scope

允许修改：

- `docs/blackbox-spec-rework/verify-T.sh`
- `docs/blackbox-spec-rework/work-items/d07/{README.md,BDD.md,TDD.md,ACT.yaml,PROMPT.md,ACCEPTANCE.md}`
- `docs/blackbox-spec-rework/work-items/t07/{README.md,BDD.md,TDD.md,ACT.yaml,PROMPT.md,ACCEPTANCE.md}`
- `docs/blackbox-spec-rework/work-items/t08/{README.md,BDD.md,TDD.md,ACT.yaml,PROMPT.md,ACCEPTANCE.md}`

`openspec/learn-system-blackbox-architecture.md` 仅用于读取和临时变异测试。若发现必须修改正文，立即停止并报告精确冲突，不得自行改写。

## Forbidden

- 不修改任何业务代码、Schema、数据库、依赖、Tag 权威文档或其他工作包。
- 不修改 `PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md` 或 G3 总 `ACCEPTANCE.md`；这些由主 Agent 验收后更新。
- 不通过放宽断言、忽略错误、固定返回码或只数关键词来获得绿色结果。
- 不把临时变异文件放入仓库；使用 `/tmp`，每次变异从未修改的权威规格重新复制。
- 不改写、压缩或删除既有正确语义来迁就门禁。
- 不合并、不推送、不启动 G4。

## Task Contract

### 0. 起点检查

1. 记录当前分支、`HEAD`、`git status --short`。
2. 验证 `cc03b79` 是当前 `HEAD` 的祖先。
3. 运行正常规格门禁和 `git diff --check`，保存原始结果。
4. 如存在不属于允许范围的未提交改动，保留不碰；若与允许文件重叠，立即停止。

完成标准：起点证据齐全，无重叠脏文件；正常规格门禁为 0。

### 1. D-07：专属块门禁

先用 `/tmp` 副本建立 Red baseline：以下每种错误规格在修复前仍返回 0，证明门禁不能识别缺陷。随后修改门禁与 D-07 六件套。

每个变异都按同一方式独立运行：从权威规格重新复制到 `/tmp/g3-r2-<case>.md`，只修改该临时副本，然后运行 `SPEC=/tmp/g3-r2-<case>.md bash docs/blackbox-spec-rework/verify-T.sh` 并记录退出码；禁止连续叠加变异。

门禁必须分别解析并只在对应专属块内验证：

- `TechniqueProfilePack`：FactSet Profile、事实字段与闭集枚举、operator 集合、AST schema 版本、禁止可执行或模型生成的 Python 规则。
- `QueryContractPack`：`getEntry`、`getSourceSpan`、`searchKnowledge`、`matchFacts` 四接口和向后兼容声明。
- `RuleIndexPack`：每条规则显式声明 `profile_version` 与 AST schema 版本，规则为声明式 AST/YAML/JSON。
- M5 仅验证 FactSet 规则在 G6 下的可执行性，不生产上述契约。

强制变异：

1. 删除“事实字段与枚举”整条。
2. 将该条改成“包中不列任何事实字段与枚举；字段由客户端自由猜测”。
3. 删除 RuleIndexPack 的“每条规则必须显式声明 Profile 版本及 AST schema 版本”整条。

完成标准：正常规格返回 0；三个变异分别返回非零；ReleaseManifest 或其他 §16 文本不能代偿缺失内容。更新 D-07 的 README/BDD/TDD/ACT/PROMPT/ACCEPTANCE，状态写 `IMPLEMENTED_AWAITING_REVIEW`，不得写 `ACCEPTED`。独立提交，建议消息：`fix: harden D-07 package-specific gates`。

### 2. T-07：映射唯一性与肯定语义

在 D-07 提交完成后执行。门禁必须解析 §16.2 的 15 行映射，并验证每个 key 恰好出现一次。除既有 15 项映射外，以下两格必须规范化后精确相等：

- `query-contract` → `QueryContractPack（查询契约与接口定义）`
- `optional-vector-index` → `本期不产出（依据 §21 非目标）`

取代声明必须在同一句肯定语义中包含 `PublicationPackage`、`KnowledgeDataPack`、`正式取代`、`KnowledgePack`；“不得取代”等否定句必须失败。

强制变异：

1. 给 query-contract 追加 `EvidenceMapPack`。
2. 给 optional-vector-index 追加“同时归入 SearchIndexPack”。
3. 把“正式取代”改成“不得取代”。

同步 T-07 六件套：删除旧的双 IndexPack 映射、旧 FAIL 数、禁止修改门禁等冲突指令；以当前 0 FAIL 基线和变异测试为准。

完成标准：正常规格返回 0；三个变异分别返回非零；六件套之间无相互冲突。状态写 `IMPLEMENTED_AWAITING_REVIEW`。独立提交，建议消息：`fix: enforce T-07 exact package mappings`。

### 3. T-08：精确生产者与供给包

在 T-07 提交完成后执行。门禁必须精确验证三接口：

- `最小盘面概念字典` → `KnowledgeDataPack`
- `MarkContentBinding` → `KnowledgeDataPack` 与 `RuleIndexPack`
- `EvidenceBundle` → `EvidenceMapPack`

门禁必须精确验证五字段：

| 字段 | 生产 Module | 归属子包 |
|---|---|---|
| `omen_carrying` | M4 | `KnowledgeDataPack` |
| `condition_affordance` | M4 | `RuleIndexPack` 与 `KnowledgeDataPack` |
| `school_variance_display` | M4 / M6 | `KnowledgeDataPack` |
| `concept_id` | M4 | `KnowledgeDataPack` |
| 是否改变当前判断 | M4 / M7 / M6 | `KnowledgeDataPack`（`MarkContentBinding`） |

同时保留：M5 仅为 Validator；最小概念字典不含规则 DSL；Tag 的 G4 必须写成 `TAG_SYSTEM_DESIGN.md §12.2` 的命名空间形式。

强制变异：

1. 把 `concept_id` 改为 `M2 / SourceAssetPack`。
2. 任选五字段，只改成错误 Module，Package 保持正确。
3. 任选五字段，只改成错误 Package，Module 保持正确。
4. 将任一接口改为错误供给包。

同步 T-08 六件套：删除 M4/M5 共同生产、旧 FAIL 数和旧提交指令；BDD、TDD、ACT、Prompt 必须一致说明 M5 只校验。

完成标准：正常规格返回 0；四个变异分别返回非零；六件套无旧口径。状态写 `IMPLEMENTED_AWAITING_REVIEW`。独立提交，建议消息：`fix: enforce T-08 ownership mappings`。

## Final Validation Gates

三项提交完成后执行：

1. `bash docs/blackbox-spec-rework/verify-T.sh`：退出 0，`FAIL 合计: 0`。
2. 逐一重跑上述 10 个强制变异：每个均必须非零退出；恢复正常规格后再次为 0。
3. `git diff --check`：退出 0。
4. 核对三个提交的文件清单：只能包含 Scope 中对应文件。
5. `git status --short`：不得出现本任务产生的未提交文件。

## Stop Conditions

出现任一情况立即停止，不扩大范围：

- 起点提交不在当前历史中，或当前分支不符。
- 允许文件存在他人的未提交修改。
- 权威规格正文与本契约中的精确映射冲突。
- 为实现门禁必须修改规格正文、业务代码或 Scope 外文件。
- 正常规格失败，且失败不由本任务修改造成。
- 任一错误变异仍返回 0。
- 后续任务需要在前一任务未提交、未验证时启动。

## Required Final Evidence

最终只报告事实，不自行宣布验收通过。报告必须包含：

- 三个提交 hash 与各自修改文件清单。
- 正常规格最终门禁的退出码和 `FAIL 合计`。
- 10 个强制变异的名称、修复前退出码、修复后退出码。
- `git diff --check` 与 `git status --short` 原始摘要。
- 发现的冲突、跳过项、残余风险。
- 明确写明：`等待主 Agent 独立验收；未启动 G4。`

## Residual Risks

- 本工作包只修复已知门禁和六件套冲突，不证明整个架构规格不存在其他语义缺口。
- 正常门禁 0 FAIL 只有与全部错误变异非零同时成立才有意义。
- G4 的任务选择、六件套和派发 Prompt 均不在本工作包范围内。
