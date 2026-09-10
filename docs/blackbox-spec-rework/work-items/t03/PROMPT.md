# T-03 Executor Prompt

你是 T-03 文档执行 Agent。请在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支工作，禁止切换分支或进入其他 worktree。

先完整阅读并严格遵循：

- `docs/blackbox-spec-rework/work-items/t03/README.md`
- `docs/blackbox-spec-rework/work-items/t03/BDD.md`
- `docs/blackbox-spec-rework/work-items/t03/TDD.md`
- `docs/blackbox-spec-rework/work-items/t03/ACT.yaml`

【关键执行铁律与用户特别指示】：
1. 遇到任何照抄源冲突、规格歧义或意外失败，严禁自己做决定，必须立即停止并向上汇报！
2. 唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`；严禁修改任何代码、JSON Schema、测试、工作包文档、TODO、PLAN 或 `verify-T.sh`。
3. 先保存 Red baseline（运行 `bash docs/blackbox-spec-rework/verify-T.sh` 并记录）。
4. **【铁律：保留 D-03 已有状态】**：D-03 已在 §8.2 冻结了 Artifact status（5 值）和 StepRun status（6 值）及其迁移矩阵。旧 T-03 转录说明中提到的“建空表并标注 TODO(D-03)”已经过时；本轮**严禁回退为空表，严禁标注 TODO(D-03)**，必须完整保留 D-03 既有定义与迁移矩阵。
5. 在 `openspec/learn-system-blackbox-architecture.md` §8.2 建立结构严整的「状态枚举全集」：
   - **内容成熟度状态 7 值**：逐字照抄 `pipeline/schemas/core/SCHEMA.md §5`（`source_verified`, `machine_extracted`, `cross_model_reviewed`, `disputed`, `needs_expert`, `expert_verified`, `deprecated`），标明「沿用 SCHEMA.md v0.2 §5」；
   - **专家审核决定类型 8 类**：依据 `knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md §3.2` 细化为 8 个 ReviewDecision 类型枚举（`review_source_fidelity`, `review_edition_collation`, `review_school_attribution`, `review_explanation_quality`, `review_case_authenticity`, `review_practical_validity`, `review_safety`, `review_rights`），中文释义列必须包含对应原词，且表头写明「取代 §14 原有的单一『专家签发』动作；依据 v1.2 §3.2 禁止用一个 expert_verified 覆盖所有含义」；
   - **失败分类与错误码 9 个**：逐字照抄 `pipeline/schemas/core/SCHEMA.md §6`（`SRC_001`, `SRC_003`, `TXT_001`, `ID_001`, `ID_002`, `REF_001`, `SCH_001`, `SCH_002`, `SEM_001`），含中文释义，标明「沿用 SCHEMA.md v0.2 §6」；
   - **制品物理状态与迁移**：保留 D-03 既有 5 值及迁移表；
   - **单步运行状态与迁移**：保留 D-03 既有 6 值及迁移表；
   - **多轴正交性声明**：明确声明物理制品生命周期、单步任务执行生命周期与领域内容成熟度三者正交，不可混用或隐式推导。
6. 完成后运行 `docs/blackbox-spec-rework/work-items/t03/TDD.md` 中的全部 Green checks、`bash docs/blackbox-spec-rework/verify-T.sh`（FAIL 数必须从 17 严格单调减少至 14，且 T-03、T-03b、T-03c 均 PASS）以及 `git diff --check`。
7. 确认无误后提交修改，提交消息必须严格为：`docs: transcribe status enums and review decision types`。
8. 最终报告必须包含：commit hash、真实修改文件、Red baseline、Green 原始摘要、各枚举表逐项对照、保留 D-03 状态检查证明及全局 T 结果。
