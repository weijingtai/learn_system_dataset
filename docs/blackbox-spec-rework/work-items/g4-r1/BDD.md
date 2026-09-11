# BDD：G4 第一批规格落实

所有场景的 Given：在各自 worktree 的 HEAD（祖先含 `e64f2a4`）上，`export LC_ALL=en_US.UTF-8`。

## 1. 回归（每个 ACT 完成后都必须成立）

- When 运行 `bash docs/blackbox-spec-rework/verify-T.sh`
- Then 尾行 `FAIL 合计: 0`
- When 运行 `bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all`
- Then 尾行 `MUTATIONS: 109/109 rejected`（说明 G3 冻结区域与锚点行未被触动）
- When 运行 `bash openspec/schemas/verify.sh`
- Then exit 0
- When 运行 `git diff --check`
- Then 无输出

## 2. D-13 ReleaseRun 人工回路

- Given §6.2 流程块
- When 读取该块
- Then 块内出现 `Review Console（M7 模式）`、`M7 回流` 两行，且顺序为 汇编 → 裁决 → 回流 → 封存 → Snapshot → M8 → PublicationPackage
- And 块后段落明确：该 ReviewDecision 归属本 ReleaseRun 的 M7 StepRun；不改变任何已封存 `ReviewedEditionPackage` 的 `artifact_revision_id`；Edition 级事实改动走新 EditionRun

## 3. D-10 精确失效传播

- Given §14
- Then 存在 `### 14.1 精确失效传播` 小节；`carried_forward`、`ReworkImpactReport`、`needs_review`、`invalidated` 均出现；写明告警阈值；`grep -c "M3 至 M6 全部失效"` 为 0
- And §14 原句「之后只让血缘可达的派生物失效，未受影响的人工决定可继承到新 Revision。」被替换为指向 14.1 的句子，不再有「整个 Edition 失效」语义

## 4. D-11 StageCheckpoint

- Given §17
- Then 存在 `### 17.1 StageCheckpoint` 小节；全文 `StageCheckpoint` 出现 ≥ 4 次；写明粒度、必含内容、恢复语义、与 StagePackage 的关系（独立对象）、M2/M3/M4/M6 每次人工决定后即时持久化

## 5. D-06 AnchorContractPack

- Given §16、§18、§20
- Then §16 树含 `├── AnchorContractPack`；`AnchorContractPack` 块位于 `GraphProjectionPack…` 段落之后、`TechniqueProfilePack` START 行之前；块内含白名单四类、三级稳定性承诺、`IdentityMigrationMap` 四类变化、可迁移率定义
- And §18 KnowledgeGraph 行含「锚点迁移关系」；§20 出现第 11 条

## 6. D-08 SchoolView

- Given §12.2、§16、§18
- Then §12.2 列表行为 `- Interpretation、SchoolView、Alias；`，其后有 SchoolView 定义段（含 `school_id`、`conflict_group_id`、`changes_current_judgment`、Work/Edition 不得折叠进 School、`review_school_attribution`）
- And §16 含 `SchoolViewPack` 块（逻辑分包，隶属 `KnowledgeDataPack` 的 `school-views`）；§18 KnowledgeGraph 行 `School` 改为 `SchoolView`
- And 规格未新造 `school_id` 前缀，只有「待用户确认」占位句

## 7. D-14 分期与首纵切

- Given §19 主表、§22、`LEARN_SYSTEM_TARGET.md` §13
- Then §19 主表为五列，19 个数据行每行末列取值 ∈ {首纵切内, 首纵切后, 本阶段暂缓}；取值为 `首纵切内` 的行恰 4 行（Artifact Ledger、M3、M5、M8）
- And 新增 `## 22. 实施分期与首个纵切`，首个非空行为 `状态：讨论候选`；含三元组、七政版纵切链、三阶段分期表、取舍理由、「待用户过目」声明
- And `LEARN_SYSTEM_TARGET.md` §13 块后新增一段指向 §22 的裁定说明；原块不删

## 8. 失败路径

- Given 任一锚点整行命中不为 1
- Then 执行者停手报告，不做近似匹配
- Given 某项门禁在改动后变红
- Then 执行者停手报告原始 FAIL 行，不改门禁脚本、不删既有内容迁就
