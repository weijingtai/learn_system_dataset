# T-03 BDD 验收场景

## B1 内容成熟度 7 值齐备且原样转录

Given 权威源 `pipeline/schemas/core/SCHEMA.md §5` 规定了 7 个内容成熟度状态，
When 执行者查看架构规格 §8.2，
Then 能完整找到 `source_verified`、`machine_extracted`、`cross_model_reviewed`、`disputed`、`needs_expert`、`expert_verified`、`deprecated` 全部 7 个枚举值及其确切含义，无拼写错误、无增删。

## B2 校验错误码 9 个原样照抄

Given 权威源 `pipeline/schemas/core/SCHEMA.md §6` 规定了 9 个错误码及其含义，
When 执行者查看架构规格 §8.2，
Then 能完整找到 `SRC_001`、`SRC_003`、`TXT_001`、`ID_001`、`ID_002`、`REF_001`、`SCH_001`、`SCH_002`、`SEM_001` 全部 9 个错误码，且中英文对应完全忠实于原文本。

## B3 专家审核 8 类细化枚举

Given 权威源 `knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md §3.2` 严禁使用单一 `expert_verified` 覆盖所有审核含义，
When 执行者查看架构规格 §8.2，
Then 专家审核被细化为 8 个独立的 ReviewDecision 类型枚举（`review_source_fidelity`、`review_edition_collation`、`review_school_attribution`、`review_explanation_quality`、`review_case_authenticity`、`review_practical_validity`、`review_safety`、`review_rights`），
And 表头或说明明确标注「取代 §14 原有的单一『专家签发』动作；依据 v1.2 §3.2 禁止用一个 expert_verified 覆盖所有含义」，
And 中文释义列明确包含「来源忠实度」、「版本和校勘」、「流派归属」、「解释质量」、「案例真实性」、「现实效度」、「安全」、「权利」。

## B4 D-03 既有状态完整保留（禁止建空表）

Given D-03 已在 §8.2 定义了 Artifact 5 值状态机与 StepRun 6 值状态机及其迁移矩阵，
When T-03 扩充 §8.2 为状态枚举全集时，
Then D-03 的 Artifact 状态（`draft`, `sealed`, `quarantined`, `invalidated`, `superseded`）及其迁移矩阵被完整保留，
And D-03 的 StepRun 状态（`running`, `awaiting_human`, `suspended`, `succeeded`, `failed`, `superseded`）及其迁移矩阵被完整保留，
And 严禁回退为空表，严禁标注 `TODO(D-03)`。

## B5 多轴正交声明

Given 架构存在物理制品、执行运行与领域内容等不同层面的状态，
When 消费者阅读规格时，
Then 规格明确声明：Artifact status（物理修订可消费性）、StepRun status（单步执行生命周期）、内容成熟度状态（领域内容审核/发布成熟程度）以及 ReviewDecision 类型彼此正交，不可混淆、互相取代或非法隐式推导。
