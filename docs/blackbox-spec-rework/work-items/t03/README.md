# T-03 状态枚举全集转录：执行工作包

状态：`READY`（已按标准六件套建立，等待串行派发执行 Agent）

## Goal

在架构规格中建立完备、清晰正交的状态枚举全集：
1. 原样照抄转录 7 个内容成熟度状态（Content Maturity Statuses）；
2. 原样照抄转录 9 个基础校验错误码（Failure Error Codes）；
3. 照抄并将专家审核 8 大维度明确落为 ReviewDecision 类型枚举（包含中文释义），替代单一粗粒度的 `expert_verified`；
4. 严格保留并衔接 D-03 已冻结的 5 个 Artifact status 与 6 个 StepRun status 及其合法迁移矩阵，**严禁退化为空表或标注 TODO(D-03)**；
5. 明确多轴正交性声明（物理制品生命周期、执行任务生命周期、领域内容成熟度彼此正交，不可混淆与相互推导）。

## Authority

- `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-03
- `pipeline/schemas/core/SCHEMA.md` v0.2 §5 与 §6
- `knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md` §3.2
- `openspec/learn-system-blackbox-architecture.md` §8.2（D-03 产物）
- `docs/blackbox-spec-rework/verify-T.sh`（T-03, T-03b, T-03c 判据）

## Dependencies

- D-03：已完成并处于 `ACCEPTED`，其定义的 Artifact status 与 StepRun status 必须作为既有事实完全保留。
- T-02：已完成并处于 `ACCEPTED`，§8.1 标识规范已就绪。
- 本任务是 T-04（三级消费级别与 G1–G7 门禁）的前置依赖。

## Scope

- WRITE：仅 `openspec/learn-system-blackbox-architecture.md`
- 规格落点：将现有 `§8.2 Artifact 与 StepRun 状态全集` 扩充重构为完整的 `§8.2 状态枚举全集`（包含四个独立维度子节或明确分节表）：
  1. **内容成熟度状态**（7 值）：`source_verified`, `machine_extracted`, `cross_model_reviewed`, `disputed`, `needs_expert`, `expert_verified`, `deprecated`；
  2. **专家审核决定类型**（8 类）：`review_source_fidelity`, `review_edition_collation`, `review_school_attribution`, `review_explanation_quality`, `review_case_authenticity`, `review_practical_validity`, `review_safety`, `review_rights`；
  3. **失败分类与错误码**（9 个）：`SRC_001`, `SRC_003`, `TXT_001`, `ID_001`, `ID_002`, `REF_001`, `SCH_001`, `SCH_002`, `SEM_001`；
  4. **制品物理状态与迁移**（5 值）：保留既有 `draft`, `sealed`, `quarantined`, `invalidated`, `superseded` 及迁移表；
  5. **单步运行状态与迁移**（6 值）：保留既有 `running`, `awaiting_human`, `suspended`, `succeeded`, `failed`, `superseded` 及迁移表。

## Forbidden

- 严禁删除、清空或将 D-03 的 Artifact / StepRun 状态回退为空表或标注 `TODO(D-03)`。
- 严禁擅自增删 7 个内容成熟度状态或修改其拼写。
- 严禁擅自修改 9 个错误码的编号或含义。
- 严禁把 8 类专家审核合并或遗漏任何一类；必须保留中文释义列以满足机器判据。
- 严禁修改任何代码、JSON Schema、测试、数据库文件、PLAN、TODO 或 `verify-T.sh`。
- 严禁引入外部依赖或新模块。

## Stop conditions

遇到以下情况必须立即停止并向上汇报，严禁自行决定：
1. 照抄源定义产生冲突或无法对应；
2. 修改后发现 D-03 机器判据或全局回归出现未预期的失败；
3. 发现需要修改 `openspec/learn-system-blackbox-architecture.md` 以外的文件。

## ACT review（wjt-react 四查）

- **忠实性**：通过；7 值、9 错误码、8 审核类别完全依照权威照抄源（SCHEMA.md v0.2 与 WORKFLOW v1.2 §3.2），D-03 既有成果 100% 保持。
- **可执行性**：通过；单文件写作用域，严格只改 §8.2，命令与判据确定。
- **可验收性**：通过；对应 `verify-T.sh` 中 T-03, T-03b, T-03c 三项机器判据，验收后 FAIL 计数应从 17 下降至 14。
- **防越界性**：通过；无代码修改、无 Schema 修改，禁止回退 D-03 状态机。

结论：工作包六件套完备，符合 G0 交付门禁，状态置为 `READY`。
