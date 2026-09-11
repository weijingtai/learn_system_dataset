# G4 第一批：D-13 / D-10 / D-11 / D-06 / D-08 / D-14 规格落实

状态：`READY`（主 Agent 2026-09-10 编写并自审）
task_id：`blackbox-g4-r1-spec-batch`
权威需求来源：`docs/blackbox-spec-rework/D-design.md` 对应六条；`PLAN.md`「黑箱架构规格 R1 审查返工项」RB/RC/RF 组；`SUBAGENT_TODO.md` G4 节
基线提交：`e64f2a4`（G3 已 `ACCEPTED`，`verify-T.sh` 0 FAIL，`mutations.sh all` 109/109，`openspec/schemas/verify.sh` 通过）
分支：`codex/docs/knowledge-compilation`

## Goal

把六条已裁定的设计项写入权威规格 `openspec/learn-system-blackbox-architecture.md`（D-14 另同步根 `LEARN_SYSTEM_TARGET.md`），每条按本目录 `act/<id>.yaml` 给定的**确定文本**落实；全部既有机器门禁保持绿色。

## 分组与并行

三组由用户交给外部执行 Agent，在主工作树 `codex/docs/knowledge-compilation` 上**串行**执行（同一文件，不得同时开工；A/B/C 之间顺序任意，组内顺序固定），写入章节互不重叠：

| 组 | ACT 顺序 | 写入章节 | Prompt |
|---|---|---|---|
| A | `act/d13.yaml` → `act/d10.yaml` → `act/d11.yaml` | §6.2、§14（新增 14.1）、§17（新增 17.1） | `PROMPT-A.md` |
| B | `act/d06.yaml` → `act/d08.yaml` | §12.2、§16（树 + 两个新块，位于 `TechniqueProfilePack` 起始行之前）、§18、§20 | `PROMPT-B.md` |
| C | `act/d14.yaml` | §19 主表新增「分期」列、新增 §22、根 `LEARN_SYSTEM_TARGET.md` §13 追加说明 | `PROMPT-C.md` |

每组交付后由主 Agent 独立验收（`ACCEPTANCE.md`），全部通过后统一更新协调文档。

## Scope

- 允许写：`openspec/learn-system-blackbox-architecture.md`；C 组另可写根 `LEARN_SYSTEM_TARGET.md`
- 允许读：`AGENTS.md`、本目录全部文件、`docs/blackbox-spec-rework/D-design.md`、`docs/blackbox-spec-rework/verify-T.sh`（只读，理解门禁）、`openspec/legacy-storage-transition.md`
- 其余一切路径禁止写入（含 `verify-T.sh`、`mutations.sh`、Schema、`PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`、本工作包）

## Forbidden

1. 修改 G3 冻结区域：§16 中 `TechniqueProfilePack`/`QueryContractPack`/`RuleIndexPack` 三个 START 行及其到 `### 16.2` 之前的全部内容、§16.2 全部、§16.3 全部；§1 三接口行；§8.2 状态表；§13 G1–G7 表；§16 证据链七项。判定标准：`verify-T.sh` 0 FAIL 且 `mutations.sh all` 109/109。
2. 改动 §3–§18 任一章节标题后的 `状态：` 行（T-13 结构门禁）。
3. 新造门禁代号（只允许 G1–G7）、新造 ID 前缀（§8.1 未登记的前缀只能写「待用户确认」占位）。
4. 改写 ACT 未要求的既有句子；删除任何既有内容（除 ACT 明确指定的替换）。
5. 放宽、跳过或改动任何验证命令；`git add -A`/`git add .`；stash/reset/clean/rebase/push；切换到主工作树分支。
6. 遇到 ACT 未写明的决定自行拍板。

## Inputs（HEAD `e64f2a4` 的定位锚点，均为整行精确匹配）

- §6.2 流程块首行：`既有 CanonicalKnowledgeSnapshot`；末行：`→ PublicationPackage`；块后说明句：`任何 Edition 都可以单独加入和单独发布；后续加入新版本时才执行可比部分的对勘。`
- §14 待替换句所在行：`M6 只读显示 M2 的扫描、OCR 和字框。发现 OCR 错误时创建 `CorrectionRequest` 并退回 M2，由 FastAPI + Vue 校对工具修正；之后只让血缘可达的派生物失效，未受影响的人工决定可继承到新 Revision。`
- §14 末句：`输出 `ReviewedEditionPackage`，包括获批和驳回知识、所有 ReviewDecision、Revision、证据关系及零个未解决项。`
- §17 末句：`所有步骤按以下事务执行：创建 StepRun、冻结输入、验证输入 Contract、执行、保存原始输出和日志、计算哈希、验证输出、记录 Transformation、封存 StepManifest、写入最终状态。失败和部分输出也必须封存；重跑创建新 StepRun。`
- §12.2 列表行：`- Interpretation、School、Alias；`；其后段落首句以 `不同类别不得由一个模型一次混合完成。` 开头
- §16 树：`├── QueryContractPack` 行；`GraphProjectionPack 与移动端数据必须来自同一 CanonicalKnowledgeSnapshot，并共享 `release_id`、`canonical_hash`、实体 ID 和关系 ID。` 行（其后一空行，再是 TP START 行）
- §18 行：`- `KnowledgeGraph`：Work、Edition、Pattern、Assertion、Rule、School 和 Evidence 关系；`
- §20 末条：`10. 更换 OCR、模型、索引或存储 Adapter 不改变相邻 Module 的 Interface。`
- §19 主表表头：`| 目标 Module | 层级 | 当前实现 | 当前差距 |`，分隔行 `|---|---|---|---|`，19 个数据行，表后注：`注：本表行序为盘点顺序，非施工顺序；施工顺序见上方拓扑，三个基础设施是前置层。`
- §21 末行：`- 要求三百页 Edition 在全部加工完成前不能产生任何可审核中间成果；系统按卷或连续页区间逐 Part 推进，但仍保留整本完成状态。`
- `LEARN_SYSTEM_TARGET.md` §13 块后句：`这条纵切通过后，再扩展十干十二月、十神和格局，随后复用相同 Interface 接入其他术数。`

## Dependencies

- D-01/D-02/D-03/D-05/D-09/D-12/D-17/D-19 已 `ACCEPTED`；本批不依赖 D-15/D-16/D-18。
- 机器门禁：`docs/blackbox-spec-rework/verify-T.sh`（须 `export LC_ALL=en_US.UTF-8`）、`docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all`、`openspec/schemas/verify.sh`。

## Stop Conditions

- 任一锚点整行命中次数不为 1；
- 任一门禁在自己改动后变红且无法在本 ACT 允许范围内恢复；
- 需要新造 ID 前缀、门禁代号或改动冻结区域才能完成；
- 对 ACT 文本有两种理解。

遇到以上任一情况：停止，报告锚点、命令、退出码、原始输出与 `git status --short`，不扩大范围。

## 决定记录

**2026-09-10 主 Agent 设计裁定（执行者不得改动）**
- D-13：Review Console M7 模式的 ReviewDecision 归属本 ReleaseRun 的 M7 StepRun；不改变任何已封存 ReviewedEditionPackage；Edition 级事实需改动时走新 EditionRun。
- D-10：影响面单位 = 被修正 SourceSpan/StructuralSpan；血缘可达者 `invalidated`，不可达者 `carried_forward`；等价则继承、变化则 `needs_review`；`ReworkImpactReport` 四字段；告警阈值 累计轮次 ≥ 3 或单轮失效占比 ≥ 30%，告警不自动阻断。
- D-11：StageCheckpoint 是独立 Ledger 对象（非 StagePackage 前身/子集），按 Artifact 语义使用 `art_`/`rev_`；人工阶段每次人工决定后即时落盘。
- D-06：白名单四类；稳定性等级 `permanent`/`migratable`/`best_effort`；IdentityMigrationMap 四类 `migrated`/`merged`/`split`/`retired`；§20 新增第 11 条。
- D-08：SchoolViewPack 是 `KnowledgeDataPack` 内 `school-views` 的逻辑分包，不新增顶层子包（避免与 §16.2 冻结映射冲突）；`school_id`/`school_view_id` 前缀待用户确认，规格只写占位说明。
- D-14：首纵切内 = Artifact Ledger、M3、M5、M8 四行；其余按 `act/d14.yaml` 表；§22 状态 `讨论候选`，待用户过目。

**2026-09-10 转译审查（原规划者，四查）**：见 `ACCEPTANCE.md` §0。
