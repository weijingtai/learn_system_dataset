# Learn System 黑箱内部架构规格

状态：`REVIEW_FAILED_R1`

> R1 交叉审查（2026-09-08，架构 / 验收 / 用户体验 / 规划四角色独立进行）结论为**不通过**，
> 原 38 条返工项与追加的 2 条版权/存储返工项见 `PLAN.md` 的「黑箱架构规格 R1 审查返工项」一节。
> 在该节全部结清前，本规格不得作为 tasks 拆解依据，亦不得启动 M1-M8 任何 Module 的实现任务。

日期：2026-09-08

## 1. 系统边界

Learn System 是单机运行、全过程留痕的知识编译工具。它接收原始资料，完成识别、校验、整理和人工审核，最终输出供 APP 后端接收的数据集与符合 ReleasePolicy 的 SourceAssetPack。

```text
原始资料
→ Learn System 黑箱［识别 + 校验 + 整理］
→ PublicationPackage［结构化数据 + SourceAssetPack + 二者关系］
```

APP 后端、客户端、Mark 渲染、学习笔记、经典讨论和端侧模型均在黑箱之外。黑箱只负责在输出中提供它们需要的稳定数据、查询契约和注解锚点。

## 2. 已确认原则

1. 所有处理均在单机完成，不建设微服务或消息队列。
2. 同一仓库内保持独立 Module；Module 不直接读取或修改其他 Module 的数据库。
3. Module 只通过 Artifact ID 和版本化 Package 交换数据。
4. `EditionRun` 归属于一个完整 Edition；阶段推进和 Gate 的最小单位是 `EditionPart`。Edition 只有在其全部 EditionPart 通过时才标记完整。
5. 多个 Edition 可以并行；同一 Edition 内按 EditionPart 推进，不按单页或 SourceSpan 推进下游阶段。
6. 每一步产生的业务数据、原始输出、人工决定、失败记录和执行证据必须永久留存。
7. 任何修改都产生新的不可变物理修订，旧 Artifact 不得覆盖，每次修订的 `artifact_revision_id` 禁止复用；业务对象的 `entity_id` 跨 Revision 稳定且必须复用。不得以 `stable_key` 等旁路字段代替这两类标识的正式语义。
8. SQLite、文件目录、Graph 和未来其他存储均为 Adapter，不定义领域模型。
9. Knowledge Graph 与 Lineage Graph 必须同时存在，并可无损投影到 Graph 存储。
10. 模型输出只能成为候选，不能绕过校验和人工审核进入正式数据集。

## 3. 书籍、版本与载体

`Work` 表示抽象著作；`Edition` 表示一个具体刻本、抄本、整理本或电子来源版本；`SourceAsset` 表示该 Edition 的 PDF、PNG、EPUB、TXT 等文件。

```text
Work：《三辰通载》
├── Edition：宋刻本
├── Edition：明刻本
├── Edition：韩国流传本
└── Edition：电子转录本
```

不同 Edition 独立加工、独立保存、互不覆盖。新版本以后按月增量加入，不要求预先收齐。版本间使用 `Alignment`、`VariantReading`、`Addition` 和 `Omission` 表达对勘关系。

同一 Edition 的扫描 PDF、分页 PNG、OCR JSON、校订文本是 SourceAsset 或派生产物，不另建 Edition。

`EditionPart` 是 Edition 内可独立通过阶段 Gate 的自然分部。优先采用原书的“卷”；没有稳定卷界时采用连续页区间。不得把单页或 SourceSpan 直接作为 EditionPart。《三辰通载三十卷》以卷为 EditionPart，目录页和附录另设明确的连续页区间 Part。

## 4. Pattern（格局）

`Concept` 是可跨来源或术数对齐的规范术语身份，不要求具有机器识别规则。当前将各术数中“有关键名称、识别规则、解释、衍生含义和来源”的对象统一称为“格局”，内部稳定类型 `Pattern` 是 Technique 范围内可规则识别的 Concept 子类型。七政四余是当前唯一已有原型的 Technique，紫微斗数、太乙神数、八字、大六壬、奇门遁甲等以后通过 `TechniqueProfile` 扩展。

```text
Pattern
├── PatternShape
├── PatternAlias
├── PatternRecognitionRule
├── PatternInterpretation
├── PatternEvidence
└── PatternRevision
```

旧七政原型当前主要拥有名称和部分识别规则。解释、出处没有录入时必须标为 `not_captured`，不得解释为客观不存在。

Pattern 有两个来源空间：

- `official_release`：古籍、其他信源或 APP 开发者编写的官方内容，经黑箱审核后输出；这是当前范围。
- `user_authored`：用户未来可创建并设为 `private` 或 `public`；当前只预留来源类型和 Provider seam，不设计或实现编辑流程。

用户 Pattern 与官方 Pattern 使用独立命名空间，不得直接修改官方数据。

一个 Pattern 聚合一条或多条 Assertion，并可关联多条规则、解释、流派视图和证据。M7 汇编 Concept、Pattern、Assertion 及其关系；M8 把一个 Concept 或 Pattern 编译为面向 APP 的 `KnowledgeEntry`。KnowledgeEntry 是发布视图，不是来源事实，也不能取代 Assertion 或 SourceSpan。内部规范身份分别使用 `concept_id`、`pattern_id`；发布词条使用 `entry_id`。

三者的最小字段如下：

- `Concept`：`concept_id`、规范名、别名、术数范围、本体层级、Revision 和状态；
- `Pattern`：`pattern_id`、`concept_id`、`technique_id`、识别规则引用、Assertion 引用、解释引用、证据引用、Revision 和状态；
- `KnowledgeEntry`：`entry_id`、`subject_entity_id`、`release_id`、标题、Assertion/Rule/SchoolView/Evidence 引用和身份迁移状态。

KnowledgeEntry 的内容只能由 M8 从已审核对象编译，不接受工作台或模型直接写入。

## 5. 总体组织

黑箱包含八个加工 Module 和三个基础设施 Module。

```text
M1 Source Intake
→ M2 Digitization & Correction
→ M3 Corpus Compilation
→ M4 Knowledge Extraction
→ M5 Automatic Validation
→ M6 Review & Curation
→ M7 Incremental Knowledge Assembly
→ M8 Dataset Compilation
```

基础设施：

- `Artifact Ledger`：保存内容、Revision、血缘和运行记录；
- `Local Orchestrator`：执行阶段状态机、Gate、暂停、恢复和重跑；
- `Contract Registry`：管理所有 Package Schema、TechniqueProfile 和兼容规则。

`Review Console` 是跨人工阶段共用的交互 Interface，不是第九个加工 Module。现有 `pattern_knowledge_workbench` 向该 Interface 演进，分别呈现 M3 边界分歧、M4 提取分歧、M6 正式审核和 M7 汇编提案；人工决定始终归属发起该队列的 ProcessingRun、StepRun 和 Stage。

## 6. 两种运行

### 6.1 EditionRun

每个具体 Edition 拥有一个 EditionRun；其 EditionPart 独立执行 M1 至 M6：

```text
SourcePackage
→ DigitizationPackage
→ CorpusPackage
→ CandidatePackage
→ ValidationPackage
→ ReviewedEditionPackage
```

一个 EditionPart 的阶段内可以有多项任务，但只有全部任务完成、失败为零、输出 Contract 通过且 `StageManifest` 封存后，该 Part 才能进入下一阶段。Edition 级完成状态是其已声明全部 Part Gate 的合取。资料客观缺少影印本或出处不算未完成，但必须使用明确状态记录。

EditionPart 也是技术上的最小编译/发布范围。Part 级结果可以进入内部验收或开发检索包；标记为完整 Edition 的公开发布必须覆盖已声明的全部 Part。G2 的 100% 覆盖分别在 Part 内计算，并在 Edition 层对全部 Part 作合取。

### 6.2 ReleaseRun

ReleaseRun 读取既有 `CanonicalKnowledgeSnapshot` 与本次新增的一个或多个 `ReviewedEditionPackage`：

```text
既有 CanonicalKnowledgeSnapshot
+ 新 ReviewedEditionPackage
→ M7 增量汇编
→ Review Console（仅处理不能自动裁定的 M7 提案）
→ M7 封存汇编结果
→ 新 CanonicalKnowledgeSnapshot Revision
→ M8 数据集编译
→ PublicationPackage
```

任何 Edition 都可以单独加入和单独发布；后续加入新版本时才执行可比部分的对勘。

## 7. 统一 Module Interface

所有加工 Module 使用同一外部 Interface；调用可以在一个 StepRun 内跨越执行、等待人工与恢复，不承诺单次同步返回最终结果：

```text
execute(StepRequest) → StepResult
```

`StepRequest` 至少包含：

- `processing_run_id`
- `step_run_id`
- `input_artifact_ids`
- `technique_profile_id`
- `configuration_artifact_id`

`StepResult` 至少包含：

- `status`
- `output_artifact_ids`
- `validation_report_ids`
- `log_artifact_ids`
- `failure_artifact_ids`

`StepRequest` 与 `StepResult` 的机器契约由以下 JSON Schema（Draft 2020-12，`schema_version: "1.0.0"`）冻结：
- `openspec/schemas/step_request.schema.json`
- `openspec/schemas/step_result.schema.json`

Module 只能读取请求中明确冻结的 Artifact，不得读取上游工作目录中的“最新文件”。

### 7.1 StepRun 生命周期与人工恢复

一次 `StepRun` / `execute` 只覆盖一个 EditionPart 的一个阶段任务，以及该任务衍生的整个人工队列；不得为队列中的每条人工决定另建 StepRun。每条人工决定作为不可变事件写入 Artifact Ledger，并归属原 `processing_run_id`、`step_run_id` 和 Stage。一个阶段可以包含多个此类任务，只有该 EditionPart 在该阶段的全部任务都达到 `succeeded`，Stage Gate 才能通过。

StepRun 创建后从 `running` 开始。当任务需要人工处理时，进入 `awaiting_human` 并持久化以下恢复上下文：

- 不透明、单次使用的 `resume_token`，同时绑定该 `step_run_id` 与当前 `status_version`；成功恢复后立即作废；
- 本次 StepRequest 最初冻结的全部输入 `artifact_revision_id`；
- 待处理队列的 Artifact Revision 引用；
- 已明确写回且归属该 StepRun 的不可变人工事件 Artifact Revision 引用。

`resume_token` 只是本地状态机的防重放恢复凭据，不是登录、会话或鉴权 token。`record_human_event(step_run_id, resume_token, event_artifact_revision_id)` 先校验绑定关系并把不可变人工事件写入 Ledger；事件登记本身不消费 token。队列处理完成后，调用 `resume(step_run_id, resume_token)` 原子消费 token，并按 §8.2 的合法迁移把 StepRun 恢复为 `running`。恢复执行只读取最初冻结的输入 Revision 和通过该接口明确写回的事件 Artifact，不读取工作目录中的“最新文件”，也不通过外部轮询发现人工结果。

单人单机模式默认没有自动超时。实现可以登记 `deadline` 用于提醒，但超过 deadline 不得自动把 StepRun 标为 `failed`，也不得清空或丢弃待处理队列；操作者可以显式把 `awaiting_human` 转为 `suspended`。

`suspended` 表示操作者主动暂停，或基础设施暂不可用；它不是等待业务人工决定的 `awaiting_human`。恢复前必须保留冻结输入、队列引用和已写入事件，并按 §8.2 的迁移重新进入 `running`。

## 8. Package 公共结构

每个 StagePackage 都包含：

```text
payload       本阶段实际数据
manifest      输入、输出、数量、Schema和哈希
validation    本阶段校验结果
lineage       上游Artifact与转换关系
logs          完整执行日志
failures      本次及此前失败记录引用
```

Package 封存后不可修改。修正产生新的 Package Revision。
StagePackage 与制品引用的机器契约由以下 JSON Schema（Draft 2020-12，`schema_version: "1.0.0"`）冻结：
- `openspec/schemas/stage_package.schema.json`
- `openspec/schemas/artifact_ref.schema.json`

四份 L0 机器契约的唯一验证命令为：
```bash
bash openspec/schemas/verify.sh
```

### 8.1 标识与版本规范

#### 1. 标识语义（业务身份与物理修订分离）

`entity_id` 表示跨 Revision 稳定、必须复用的业务身份。Pattern、Assertion、SourceSpan、Concept、SchoolView、KnowledgeEntry 等领域对象均使用稳定 `entity_id`；具体 Contract 可以使用 `pattern_id`、`concept_id`、`entry_id`、`ocr_profile_id` 等领域化字段名，但它们必须遵守同一 `entity_id` 语义，不得因内容修订而换号。

`artifact_revision_id` 表示一次不可变物理修订。Artifact、StagePackage 等对象在每次封存或修正其实际内容时都必须创建新的 `artifact_revision_id`，旧修订永久保留，且任何新修订不得复用既有 `artifact_revision_id`；领域化字段 `ocr_profile_revision_id` 遵守同一 `artifact_revision_id` 语义。

§7 的 `input_artifact_ids`、`configuration_artifact_id` 与 `output_artifact_ids` 都必须引用已冻结的 `artifact_revision_id`；执行方只能按这些精确修订读取或返回 Artifact，绝不能把它们解析为对象的“最新版本”。

StepRun 自身使用 `step_run_id`，不使用 `artifact_revision_id` 充当运行身份。每次重跑都创建新的 StepRun 和新的 `step_run_id`；该次运行产生的 Artifact 仍按上一段取得各自的 `artifact_revision_id`。

ReviewDecision 与 EvidenceLink 必须同时记录目标对象的 `entity_id`，以及作出决定或建立证据关系时所见的 `artifact_revision_id`。下游 Annotation 以目标对象的 `entity_id` 为主锚，并必须记录创建时所见的 `artifact_revision_id`。两部分缺一即不能重现当时内容；不得只锚定物理修订，也不得以 `stable_key` 绕过 `entity_id`。

对象删除后，其 `entity_id` 永久退役；对象合并或拆分时，新对象必须取得新的 `entity_id`，不得把任一旧 `entity_id` 复用于语义已经改变的新对象。旧身份到新身份的迁移关系由后续 `IdentityMigrationMap` 表达。

#### 2. 已冻结标识格式（原样沿用）

既有系统已冻结八类标识格式，本规范原样沿用，不修改前缀、分隔符或数字位数：

| 对象 | 标识格式 | 权威出处 | 说明 |
|---|---|---|---|
| 来源（Source） | `src_<work>_ed<NN>` | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §1 | 作品底本来源标识，`<work>` 为作品简称，`<NN>` 为两位底本版次编号 |
| 原文片段（SourceSpan） | `ss_<work>_ed<NN>_p<NNNN>_s<NN>` | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §2 | 原文证据切片，含作品、版次、4位页码及2位句子序号 |
| 知识单元（KnowledgeUnit） | `ku_<technique>_<6位数字>` | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §3 | 技法知识单元，`<technique>` 为技法代号，后接6位定长数字编号 |
| 主张（Assertion） | `as_<technique>_<6位数字>` | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §4 | 知识主张，`<technique>` 为技法代号，后接6位定长数字编号 |
| 命题（Proposition） | `pr_<technique>_<6位数字>` | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §4 | 原子命题，`<technique>` 为技法代号，后接6位定长数字编号 |
| 共享概念（Shared Canon Concept） | `co_shared_<domain>_NN` | 沿用 `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md` §二 L1 | 跨技法共享源数据概念（如天干、地支、五行等闭集），不隶属单一技法 |
| 技法概念（Technique-Private Concept） | `co_<technique>_<6位数字>` | 沿用 `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md` §二 L3 | 技法独有概念（如八字十神、奇门门宫），后接6位定长数字编号 |
| 同形字面锚（Homograph Surface Anchor） | `hg_<4位数字>` | 沿用 `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md` §二 L2 | 跨技法同形异义词字面共享锚，后接4位定长数字编号 |

注：上述八行格式分别来自 `pipeline/schemas/core/SCHEMA.md` v0.2 与 `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md`，执行方必须严格维持原样，不得擅自合并、重命名或变动位数。

#### 3. 新对象标识格式（已确认）

为黑箱架构新引入的核心对象定义标识格式。为遵循单人单机最小依赖原则，统一使用 Python 标准库 `uuid.uuid4().hex`（UUIDv4，32位全小写十六进制字符串）作为无状态稳定段，无需引入中心化发号器、数据库自增序列或外部第三方包。

以下六类新对象标识格式已由用户于 2026-09-09 确认并冻结，D-02 机器 Schema 必须按此实现：

| 对象 | 冻结格式 | 语义归属 | 说明与防冲突理由 |
|---|---|---|---|
| Artifact | `art_<32hex>` | 逻辑身份（`artifact_id`） | 知识制品逻辑对象身份，多次修订保持稳定 |
| Artifact Revision | `rev_<32hex>` | 物理修订（`artifact_revision_id`） | 不可变物理修订标识，每次封存或修正生成全新修订号 |
| ProcessingRun | `prun_<32hex>` | 运行身份 | 批处理运行标识；**必须使用 `prun_` 前缀**，严禁使用 `pr_`，避免与既有已冻结命题 ID（`pr_<technique>_<6位数字>`）冲突 |
| StepRun | `srun_<32hex>` | 运行身份（`step_run_id`） | 管道单步执行标识，每次重跑均分配全新 ID |
| StagePackage | `pkg_<stage>_<32hex>` | 逻辑身份（`stage_package_id`） | 阶段包逻辑身份标识。`<stage>` 明确冻结为 `m1`、`m2`、`m3`、`m4`、`m5`、`m6`、`m7`、`m8` 闭集（其他值非法，不得自行加入基础设施阶段）；修正同一个 StagePackage 时保留 `stage_package_id`，每个不可变版本另取新的 `artifact_revision_id=rev_<32hex>`。StagePackage 的 ArtifactRef 同时携带 `stage_package_id` 与 `artifact_revision_id` |
| Release | `rel_<32hex>` | 发布版本 | 正式发布版本标识 |

规范约束与非法格式判定：
1. **身份与 Revision 分离**：`Artifact`（`art_<32hex>`）与 `Artifact Revision`（`rev_<32hex>`）是两种不同性质的标识，严禁合并为一个字段。同一 Artifact 产生新版内容时，`artifact_id` 保持不变，每版获得唯一的 `artifact_revision_id`。
2. **StagePackage 逻辑身份与修订分离**：`pkg_<stage>_<32hex>` 明确定义为 StagePackage 的逻辑身份（`stage_package_id`），非不可变物理版本载体。修正同一个 StagePackage 时保留 `stage_package_id`，每个不可变版本另取新的 `artifact_revision_id=rev_<32hex>`。明确 StagePackage 的 ArtifactRef 同时携带 `stage_package_id` 与 `artifact_revision_id`。
3. **Stage 阶段闭集**：`<stage>` 明确冻结为 `m1`、`m2`、`m3`、`m4`、`m5`、`m6`、`m7`、`m8` 闭集；其他值非法，不得自行加入基础设施阶段。
4. **前缀命名与冲突规避**：ProcessingRun 必须使用 `prun_`。严禁将 `pr_` 复用于 ProcessingRun，否则判为非法。
5. **非法格式可判定**：缺前缀、十六进制非32位、包含大写字母（必须全小写十六进制 `[0-9a-f]{32}`）、`<stage>` 取值超出 `m1` 至 `m8` 闭集范围、或数字位数不符者，校验器与消费者一律判定为非法标识。

#### 4. 版本轴分离规则（Schema Version 与 Content Revision）

架构确立 **Schema 版本与 content Revision 分离**（Schema Version 与 Content Revision 分离）原则：
1. **Schema Version（契约版本）**：描述数据结构、校验字段与类型定义的演进（如 v0.1、v0.2、v1.0），由数据规范文档与机器 Schema 定义。
2. **Content Revision（内容修订）**：描述在特定契约下生成的物理知识实例数据的不可变修订（如 `rev_<32hex>`）。
3. **独立演进**：两者沿独立维度递增，不强制同号。重新编译、修复知识内容或重跑流水线只需生成新的 Content Revision，无需升级 Schema Version；Schema Version 升级时，历史 Content Revision 仍保留并指向当时的 Schema Version，实现契约升级与内容修订的彻底解耦。

### 8.2 状态枚举全集

本架构确立多轴正交的状态机与枚举体系：物理制品生命周期（Artifact status）、单步任务执行生命周期（StepRun status）、领域内容成熟度状态（Content Maturity Status）以及专家审核决定类型（ReviewDecision Type）彼此正交，分别管控不同层面的语义，不可混用、互相取代或非法隐式推导。

#### 1. 内容成熟度状态（Content Maturity Status）

以下 7 个内容成熟度状态描述领域知识内容在流水线处理与审核过程中的成熟程度，逐字转录并沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §5（对应 v1.1.1 §9.4）；表外取值无效：

| 内容成熟度状态（Status） | 中文释义与含义 | 权威出处 |
|---|---|---|
| `source_verified` | 原文与出处已核对 | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §5 |
| `machine_extracted` | 单模型抽取候选 | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §5 |
| `cross_model_reviewed` | 异构模型交叉复核 | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §5 |
| `disputed` | 存在冲突 | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §5 |
| `needs_expert` | 需要专家判断 | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §5 |
| `expert_verified` | 专家确认（未来） | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §5 |
| `deprecated` | 已撤回 | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §5 |

#### 2. 专家审核决定类型（ReviewDecision Type）

依据 `knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md` §3.2 规定，禁止使用一个 `expert_verified` 覆盖所有审核含义。在 Review Console（M6 及相关人工工位）中，专家审核被细化为 8 个独立的 ReviewDecision 类型枚举；中文仅作释义列，取值一律为小写下划线：

> 表头声明：本表取代 §14 原有的单一『专家签发』动作；依据 v1.2 §3.2 禁止用一个 expert_verified 覆盖所有含义。

| 审核决定类型（ReviewDecision Type，取代 §14 原有的单一『专家签发』动作；依据 v1.2 §3.2 禁止用一个 expert_verified 覆盖所有含义） | 中文释义 | 说明与审核维度 |
|---|---|---|
| `review_source_fidelity` | 来源忠实度 | 审核文本与原书/底本切片的一致性，核验是否有误读、漏字或伪造 |
| `review_edition_collation` | 版本和校勘 | 审核多版本文字异同、异体字、脱文、衍文及底本校订结论 |
| `review_school_attribution` | 流派归属 | 审核主张、概念与规则所属的术数流派分类，防止静默混派 |
| `review_explanation_quality` | 解释质量 | 审核白话解释、术理阐述与逻辑推导的准确性与通顺度 |
| `review_case_authenticity` | 案例真实性 | 审核所引历史案例或验证用例的真实来源、授权记录与推演完整性 |
| `review_practical_validity` | 现实效度 | 审核现实效度状态与适用边界，严格区分原书记载与现实预测有效性 |
| `review_safety` | 安全 | 安全审核，阻断欺骗、诱导依赖、高风险断言或违反监管红线的内容 |
| `review_rights` | 权利 | 权利审核，确认原书、扫描图像、派生产物的版权及分发许可状态 |

#### 3. 校验错误码与失败分类（Failure Error Codes）

以下 9 个错误码为确定性校验程序（M5 Validator 等）的标准输出集合，逐字转录并沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §6（对应 v1.1.1 §9.7 子集）；表外代码无效：

| 错误码（Code） | 中文释义 | 分类与说明 | 权威出处 |
|---|---|---|---|
| `SRC_001` | 来源文件缺失 | 来源校验（Source） | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §6 |
| `SRC_003` | 哈希不匹配 | 来源校验（Source） | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §6 |
| `TXT_001` | 引用与原文不一致 | 文本校验（Text） | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §6 |
| `ID_001` | 编号格式错误 | 标识校验（Identity） | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §6 |
| `ID_002` | 编号重复 | 标识校验（Identity） | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §6 |
| `REF_001` | 引用的对象不存在 | 引用校验（Reference） | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §6 |
| `SCH_001` | 缺少必填字段 | 模式校验（Schema） | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §6 |
| `SCH_002` | 非法枚举值 | 模式校验（Schema） | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §6 |
| `SEM_001` | 主张没有任何证据 | 语义校验（Semantic） | 沿用 `pipeline/schemas/core/SCHEMA.md` v0.2 §6 |

#### 4. 制品物理状态与合法迁移（Artifact Status）

以下是 Artifact Revision 自身的完整状态集合（已于 D-03 冻结保留），描述该物理修订是否可被运行消费；表外取值无效。

| Artifact status | 含义 |
|---|---|
| `draft` | 正在写入，内容尚未封存，任何 StepRun 都不得消费或引用为冻结输入。 |
| `sealed` | 内容已封存为不可变 Revision，可以被精确引用并作为运行输入。 |
| `quarantined` | 封存前验证失败；保留内容与证据供诊断，但不得被运行消费。 |
| `invalidated` | 原先已封存的 Revision 因上游变化而失效；历史仍保留，但新运行不得消费。 |
| `superseded` | 已被更新的 Artifact Revision 取代；历史重放仍可精确读取，新运行不得把它当作当前输入。 |

Artifact status 的合法迁移全集如下；未列出的迁移一律非法：

| 当前状态 | 可迁移至 |
|---|---|
| `draft` | `sealed`、`quarantined` |
| `sealed` | `invalidated`、`superseded` |
| `quarantined` | `superseded` |
| `invalidated` | `superseded` |
| `superseded` | 无，终态 |

修正 Artifact 必须新建 Artifact Revision 和新的 `artifact_revision_id`，不得把旧 Revision 改回 `draft` 或 `sealed`。

#### 5. 单步运行状态与合法迁移（StepRun Status）

以下是 StepRun 自身的完整状态集合（已于 D-03 冻结保留），描述一次阶段任务的执行生命周期；表外取值无效。

| StepRun status | 含义 |
|---|---|
| `running` | 正在执行、校验或持久化该阶段任务。 |
| `awaiting_human` | 计算暂停，正在等待该 StepRun 的人工队列事件通过 §7.1 接口写回。 |
| `suspended` | 操作者主动暂停，或基础设施暂不可用；不表示正在等待业务人工决定。 |
| `succeeded` | 该阶段任务及其整个人工队列已完成并通过输出 Contract；终态。 |
| `failed` | 该阶段任务已明确失败，失败记录已封存；终态。 |
| `superseded` | 未完成的旧运行已被新 StepRun 取代，不再接收输出；终态。 |

StepRun status 的合法迁移全集如下；未列出的迁移一律非法：

| 当前状态 | 可迁移至 |
|---|---|
| `running` | `awaiting_human`、`suspended`、`succeeded`、`failed`、`superseded` |
| `awaiting_human` | `running`、`suspended`、`failed`、`superseded` |
| `suspended` | `running`、`failed`、`superseded` |
| `succeeded` | 无，终态 |
| `failed` | 无，终态 |
| `superseded` | 无，终态 |

重跑永远创建新的 StepRun 和新的 `step_run_id`，新运行以 `supersedes_step_run_id` 指向被取代的运行，不得清空、复用或篡改旧运行。旧运行尚未终结时可以按上表进入 `superseded`；旧运行已经处于 `succeeded`、`failed` 或 `superseded` 时保持原终态，仅由新运行的关联字段表达重跑关系。

#### 6. 多轴状态正交性声明

架构明确声明多轴状态正交原则：
1. **制品物理状态（Artifact status）**：管物理修订的可消费性与存活状态（`draft`、`sealed`、`quarantined`、`invalidated`、`superseded`）；
2. **单步运行状态（StepRun status）**：管单步流水线任务的执行生命周期（`running`、`awaiting_human`、`suspended`、`succeeded`、`failed`、`superseded`）；
3. **内容成熟度状态（Content Maturity Status）**：管领域知识内容本身的核对、复核、专家审核与废弃进度（`source_verified`、`machine_extracted`、`cross_model_reviewed`、`disputed`、`needs_expert`、`expert_verified`、`deprecated`）；
4. **审核决定类型（ReviewDecision Type）**：管人工在具体审核维度上作出的裁决类型（`review_source_fidelity` 等 8 类）。

物理制品生命周期、单步任务执行生命周期与领域内容成熟度三者正交，不可混用、互相取代或非法隐式推导。例如：物理状态为 `sealed` 的不可变 Artifact Revision 中，其承载的主张或单元内容成熟度状态完全可以是 `machine_extracted` 或 `disputed`；执行状态为 `succeeded` 的 StepRun 亦可产出包含 `needs_expert` 内容状态的制品。

## 9. M1 Source Intake

输入：PDF、PNG、EPUB、TXT、Markdown、旧数据库或其他 SourceSubmission。

输出 `SourcePackage`：

- Work、Edition、SourceAsset；
- 原始文件或受控外部引用、SHA-256、页数和派生物清单；
- 来源说明、权利和准入决定；
- 原始目录、文件清单和媒体属性。

M1 不做 OCR、文本清洗或知识判断。

版权受限原件进入本地 content-addressed Object Store，不进入 Git。Git 只保存允许提交的转录、派生产物、manifest 和哈希；PublicationPackage 是否携带图像由 ReleasePolicy 决定。具体旧路径与迁移状态以 `openspec/legacy-storage-transition.md` 为唯一说明。

## 10. M2 Digitization & Correction

M2 同时覆盖扫描识别与电子文本清洗，不能遗漏人工校订。

```text
原文件预检
→ OCR或EPUB/TXT解析
→ 自动异常检查
→ 人工校对/清洗
→ EditionPart验收
→ DigitizationPackage
```

扫描来源必须保留：原始扫描、拆页、OCR 原始 JSON、字框、置信度、校订 Revision、异常页、质量报告和完整审计日志。现有 FastAPI + Vue OCR 校对工具属于本 Module。

扫描识别必须使用版本化 `OCRProfile`，按 Edition 绑定并允许 EditionPart 在版式显著不同时覆盖。每个 Profile 先以代表页校准、人工验收并冻结 Revision，批量 StepRun 只读取该冻结 Revision；引擎置信度不得冒充人工抽样得到的实际正确率。当前继续使用现有 `ocr/` 引擎和 FastAPI + Vue，不引入第二 OCR 引擎或新调参 UI。字段、校准、追溯和最少代码边界见 `openspec/ocr-profile-parameterization.md`。

EPUB/TXT 必须检查编码、乱码、替换字符、PUA、控制字符、水印、广告、页眉页脚、重复章节、缺失章节和异常字段。任何清理必须生成 `RawText`、`CleanedTextRevision`、`DeterministicPatchSet` 和 `SanitizationReport`，不得静默删除。

M2 Gate 通过前，该 EditionPart 的校对和清洗任务必须全部完成。异常页必须进入显式终态，不能因暂未处理而被计为完成。

## 11. M3 Corpus Compilation

M3 把校订结果组织成可引用语料，不再静默纠正文义：

```text
校订数据
→ StructuralSpan
→ SemanticSpan
→ SourceAnchor
→ CoverageReport
→ CorpusPackage
```

扫描来源的 Span 必须可回到页码、字框和原始图；电子来源必须可回到 EPUB 章节或原始字符 offset。

语义切分采用“规则优先、模型辅助、人工处理分歧”：

1. 标题、条目、表格等清晰结构使用确定性规则；
2. 论说散文和注疏混排可由两个独立模型提出边界；
3. 模型只输出 `start_offset/end_offset` 和理由，原文由程序截取；
4. 两个结果不一致时由独立复核或人工决定；
5. M3 内完成条件/结论、正文/注文、通则/命例完整性检查，不把明显切分问题推迟到 M4；边界分歧进入 Review Console 的 M3 模式。

M3 Gate 要求该 EditionPart 内同层 Span 全文覆盖 100%、无缺口、无重叠，拼接结果与该 Part 校订原文一致，未解决语义分歧为零。Edition 级覆盖率是全部 EditionPart 覆盖率的加权合取。

## 12. M4 Knowledge Extraction

M4 将 SemanticSpan 分别提取为候选：

- Concept / Pattern；
- 原子 Assertion；
- PatternRecognitionRule / ApplicabilityRule；
- 必要、加强、破坏和例外条件；
- Interpretation、School、Alias；
- Case、注文和 EvidenceLink。

不同类别不得由一个模型一次混合完成。生产模型 A、B 独立工作且初次不可见彼此结果；复核模型 C 必须重读原文，不得只看两份答案。系统按证据比较，不采用多数票。未解决语义分歧进入人工队列，不能通过 M4 Gate。

模型 Prompt、输入、完整 Response、参数、版本、解析结果、错误、差异报告和人工决定全部作为 Artifact 保存。未解决类别分歧进入 Review Console 的 M4 模式。

## 13. M5 Automatic Validation

M5 是确定性校验，不使用模型替代规则判断，也不修改 Candidate。

通用 Validator 检查 Schema、ID、哈希、引用、原文逐字一致性、证据范围、内容分层、血缘和状态。TechniqueProfile Validator 检查事实字段、枚举、规则 AST、必要/加强/破坏/例外条件和规则可执行性。

输出 `ValidationPackage`，包含通过项、失败项、警告、断裂关系、返工任务和 Validator 版本。严重错误、失败任务和待修任务均为零后，M5 Gate 才能通过。

Python 标准库 `tokenize` 不用于古文语义提取。规则使用结构化 AST/YAML/JSON 表达，不执行用户或模型生成的 Python 代码。

## 14. M6 Review & Curation 与 Review Console

M6 读取 CandidatePackage、ValidationPackage 和 CorpusPackage，提供原文/扫描对照、模型差异、返工项、接受、修改、驳回、补证、流派分歧和专家签发。

当前 `pattern_knowledge_workbench` 是七政格局编辑原型，不是完整 Review Console。目标工作台通过 TechniqueProfile 支持多术数，并以同一界面的不同模式承接 M3、M4、M6 和 M7 人工队列。其 SQLite 只能作为 UI 查询投影，审核命令、Revision 和 ReviewDecision 必须写入 Artifact Ledger 本地进程。

- M3 模式读取 DigitizationPackage、边界候选和分歧报告；输出归属于 M3 StepRun 的边界 ReviewDecision；
- M4 模式读取 CorpusPackage、A/B/C Candidate 和差异报告；输出归属于 M4 StepRun 的类别 ReviewDecision；
- M6 模式读取 CandidatePackage、ValidationPackage 和 CorpusPackage，完成正式审核；
- M7 模式读取汇编 Proposal 和证据关系，输出归属于 ReleaseRun 的合并 ReviewDecision。

现有依赖私有 `ai_core` 的聊天与直接生成规则能力从 Review Console 剥离。模型调用统一属于 M4 的 Model Adapter；以后如需在审核界面提供模型建议，只显示已经进入 CandidatePackage 且完整留痕的候选，不恢复旁路聊天写入。

M6 只读显示 M2 的扫描、OCR 和字框。发现 OCR 错误时创建 `CorrectionRequest` 并退回 M2，由 FastAPI + Vue 校对工具修正；之后只让血缘可达的派生物失效，未受影响的人工决定可继承到新 Revision。

输出 `ReviewedEditionPackage`，包括获批和驳回知识、所有 ReviewDecision、Revision、证据关系及零个未解决项。

## 15. M7 Incremental Knowledge Assembly

M7 不等待同一 Work 的全部版本。它把本次新增的 ReviewedEditionPackage 增量汇入既有 CanonicalKnowledgeSnapshot，生成新的 Snapshot Revision。

M7 保留同名异义、异名同义、多套规则、不同流派和相反结论。它先产生 `MergeProposal`、`AliasProposal`、`ConflictProposal` 和 `EvidenceRelationProposal`；不能确定的关系使用 Review Console 的 M7 模式人工裁决。该 ReviewDecision 归属 ReleaseRun，不修改已封存的 ReviewedEditionPackage。提案、差异和决定全部保留。

加入同一 Work 的新 Edition 时，M7 仅对可比内容建立 Alignment、VariantReading、Addition 和 Omission，不覆盖旧版本。

## 16. M8 Dataset Compilation

M8 冻结 CanonicalKnowledgeSnapshot Revision、发布范围、TechniqueProfile 和 ReleasePolicy，编译：

```text
PublicationPackage
├── KnowledgeDataPack
├── RuleIndexPack
├── SearchIndexPack
├── EvidenceMapPack
├── SourceAssetPack
├── GraphProjectionPack
├── ReleaseManifest
└── ValidationReport
```

建议一个 Technique 一个 Release，一个 Edition 一个 SourceAssetPack。每个子包、索引和编译报告都是独立 Artifact，不得只保留最终压缩包。

`SourceAssetPack` 按权利状态选择内容级别：

- `full_scan`：携带完整原始扫描，仅用于权利已确认允许分发的来源；
- `derived_page_images_only`：携带允许分发的派生页图，可直接完成扫描定位和高亮；
- `reference_and_hash_only`：只携带 SourceAsset 引用、SHA-256、页标识和权利说明；客户端只有在本地或受权后端可解析该引用时才能打开原书。

客户端必须具备按 SourceAsset 引用打开原书的能力，但每个 Release 是否携带原图由 ReleasePolicy 决定。首纵切为内部验收包，采用 `derived_page_images_only`；它不自动取得公开分发权。

GraphProjectionPack 与移动端数据必须来自同一 CanonicalKnowledgeSnapshot，并共享 `release_id`、`canonical_hash`、实体 ID 和关系 ID。

## 17. Artifact Ledger

Artifact Ledger 使用本地混合存储：

- 大文件和中间产物按 SHA-256 存入 content-addressed Object Store；
- 身份、Revision、运行、关系和状态存入 SQLite Metadata Ledger。

Ledger 以单机本地进程提供统一 Interface。Pipeline、OCR FastAPI 和 Flutter Review Console 都通过本地客户端调用该进程，不直接打开 Metadata Ledger。进程默认绑定 loopback 或 Unix domain socket，只允许一个写入者实例；写事务由进程串行化，SQLite 使用 WAL 允许只读查询并发。进程级锁阻止第二个 Ledger 写入者启动。

Ledger 暂不可用时适用 §8.2 的 `suspended` 语义：Module 立即停止接收或宣称已接收输出，也不回退到直接写库。若 Ledger 当下不可写，就不得声称 `suspended` 已经落盘；服务恢复后，Orchestrator 先读取最后持久状态并对账，再按合法迁移顺序写入 `suspended` 事件及状态、`recovery` 事件，并在允许继续时从 `suspended` 转回 `running`。若最后持久状态已经是终态，则不得改写。每次进入和离开 `suspended` 都必须持久化原因、时间、操作者或基础设施来源，以及冻结输入和待处理队列引用。

当前是单人单机工具，不实现登录、密码、会话、RBAC 或用户身份验证。边界只保留极薄的 `ActorProvider.current_actor()` 接口，本地实现固定返回 `local_owner`，审计事件继续保存 `actor_ref`。未来上线时可替换为 OIDC 等在线身份适配器，不修改领域对象或历史审计记录。这里的操作者身份与 `entity_id`、`artifact_revision_id` 等业务对象标识完全独立；后者不能因当前没有登录系统而省略。

本地 Object Store 保存受版权限制的原件和大体积中间产物，不进入 Git。Git、Object Store 与 PublicationPackage 的职责，以及旧存储的迁移/重跑/冻结决议，以 `openspec/legacy-storage-transition.md` 为准。

每个 Artifact 至少记录类型、Schema、哈希、大小、ProcessingRun、StepRun、生产 Module/版本、输入 Artifact、配置、校验报告、时间、状态和权利范围。相同内容物理去重，但逻辑引用和生产关系分别保留。

所有步骤按以下事务执行：创建 StepRun、冻结输入、验证输入 Contract、执行、保存原始输出和日志、计算哈希、验证输出、记录 Transformation、封存 StepManifest、写入最终状态。失败和部分输出也必须封存；重跑创建新 StepRun。

## 18. 双图与 Graph 无损要求

系统同时维护：

- `KnowledgeGraph`：Work、Edition、Pattern、Assertion、Rule、School 和 Evidence 关系；
- `LineageGraph`：Artifact、Revision、运行、工具、模型、校验和审核决定的生产关系。

重要关系必须有稳定 ID、Revision、状态和来源，不得只埋入自由文本。Graph 投影必须支持完整快照和增量输出，并通过实体/关系计数、哈希、悬空引用和往返重建校验。

任一 PublicationPackage 内容必须能回溯到 Canonical Revision、Reviewed Candidate、ReviewDecision、ValidationReport、模型运行、SourceSpan、校订 Revision、OCR 原始结果和原始 SourceAsset；反向也能查询某个原始页影响了哪些 Release。

## 19. 当前实现映射与差距

| 目标 Module | 当前实现 | 当前差距 |
|---|---|---|
| M1 Source Intake | `pipeline/runner/ingest_raw.py`、corpus manifest | Work/Edition/SourceAsset/Rights 契约不统一；未进入统一 Ledger |
| M2 Digitization & Correction | `ocr/`、FastAPI + Vue 校对工具 | 电子文本清洗不足；导出未完整携带扫描、页面 JSON、全部字框、审计和质量包 |
| M3 Corpus Compilation | `pipeline/corpus`、outline、batches、segmentation | 当前 LM 复制文本切分；缺双层 Span、严格 offset、完整 SourceAnchor；已有整书漏编假绿 |
| M4 Knowledge Extraction | concept/assertion/paraphrase 任务 | 多数为机器态；类别仍混杂；跨模型与人工裁决未形成统一 Stage Gate |
| M5 Automatic Validation | `pipeline/validators` | 主要是局部加工校验；无法阻断全书漏编、错误证据范围和零命中假绿 |
| M6 Review Workbench | `pattern_knowledge_workbench` | 七政硬编码；缺来源对照、模型比较、状态机、版本审计和通用 TechniqueProfile |
| M7 Incremental Assembly | `knowledge_system/` 设计文档 | 缺可执行 Assembler、跨 Edition 对勘、稳定 Pattern 聚合和提案裁决流程 |
| M8 Dataset Compilation | `pipeline/rag` 开发索引 | 缺正式 Dataset Compiler、PublicationPackage、Graph 投影、ReleaseManifest 和发布校验 |
| Artifact Ledger | 无 | 缺 Object Store、Metadata Ledger、Revision 和 Lineage Graph |
| Local Orchestrator | 零散脚本和任务目录 | 缺 EditionRun/ReleaseRun 状态机、阶段 Gate、Checkpoint 和失效传播 |
| Contract Registry | `pipeline/schemas` 零散规范 | 缺完整 Package Schema、Schema 版本、迁移器和 consumes/produces 声明 |

### 19.1 旧存储处置

旧存储不是 Module Interface。已确认处置如下，详细状态、哈希、源码调用点和迁移完成标准见 `openspec/legacy-storage-transition.md`：

| 旧存储 | 处置 |
|---|---|
| OCR 页面 JSON、校订历史和审计日志 | 迁移 |
| `ocr/data_work/index.db` | 重跑；它是可重建全文索引，不迁移旧索引行 |
| `pipeline/corpus/` | 迁移 |
| `pipeline/units/` | 冻结为历史快照，修复后从 CorpusPackage 重跑 |
| `pipeline/rag/index.sqlite` | 重跑，不得进入正式 Release |
| `pattern_knowledge_workbench/assets/ge_ju_database.sqlite` | 冻结为历史快照，只作 UI seed 或未来 legacy candidate 来源 |

## 20. 黑箱完成标准

1. 一个 EditionPart 严格按 M1-M6 阶段 Gate 完成，任何未完成任务不能流入下一阶段；Edition 完成是全部 Part Gate 的合取。
2. 任一阶段失败后可从该 EditionPart 最近 StageCheckpoint 恢复；历史失败不被覆盖。
3. 每个语义转换都有输入、输出、工具/模型、配置、校验和人工决定记录。
4. 原始数据、校订数据、候选、驳回项、正式知识和发布物均可双向追溯。
5. 新 Edition 可单独增量加入同一 Work，不要求收齐其他版本，也不改旧身份。
6. Pattern 名称、规则、解释和出处可逐项补全；`not_captured` 不被误判为不存在。
7. 当前七政格局数据可作为官方 Candidate 输入；用户 Pattern 仅保留未来 Adapter seam。
8. PublicationPackage 同时包含结构化知识、符合 ReleasePolicy 的 SourceAssetPack 及其关系。`reference_and_hash_only` 必须包含可由本地 Object Store 或受权后端解析的受控引用、SHA-256、页标识、权利说明和完整 Evidence 映射才满足本条；不要求携带原始文件字节。引用不可解析时验收失败。
9. 移动端数据与 GraphProjectionPack 来自同一 Canonical Snapshot，Graph 往返无损。
10. 更换 OCR、模型、索引或存储 Adapter 不改变相邻 Module 的 Interface。

## 21. 非目标

- 微服务、消息队列和分布式调度；
- 当前版本的注册、登录、密码、会话、RBAC 和多用户身份验证；仅保留 `ActorProvider` 接口；
- APP 后端、客户端、Mark UI 或社交功能实现；
- 用户 Pattern 编辑器和发布流程；
- Embedding、向量检索和端侧语言模型；
- 要求三百页 Edition 在全部加工完成前不能产生任何可审核中间成果；系统按卷或连续页区间逐 Part 推进，但仍保留整本完成状态。
