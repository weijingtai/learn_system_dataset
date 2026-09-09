# Learn System 黑箱内部架构规格

状态：`REVIEW_FAILED_R1`

> R1 交叉审查（2026-09-08，架构 / 验收 / 用户体验 / 规划四角色独立进行）结论为**不通过**，
> 原 38 条返工项与追加的 2 条版权/存储返工项见 `PLAN.md` 的「黑箱架构规格 R1 审查返工项」一节。
> 在该节全部结清前，本规格不得作为 tasks 拆解依据，亦不得启动 M1-M8 任何 Module 的实现任务。

日期：2026-09-08

## 1. 系统边界

Learn System 是单机运行、全过程留痕的知识编译工具。它接收原始资料，完成识别、校验、整理和人工审核，最终输出供 APP 后端接收的数据集与原始资料包。

```text
原始资料
→ Learn System 黑箱［识别 + 校验 + 整理］
→ PublicationPackage［结构化数据 + 原始数据 + 二者关系］
```

APP 后端、客户端、Mark 渲染、学习笔记、经典讨论和端侧模型均在黑箱之外。黑箱只负责在输出中提供它们需要的稳定数据、查询契约和注解锚点。

## 2. 已确认原则

1. 所有处理均在单机完成，不建设微服务或消息队列。
2. 同一仓库内保持独立 Module；Module 不直接读取或修改其他 Module 的数据库。
3. Module 只通过 Artifact ID 和版本化 Package 交换数据。
4. `EditionRun` 归属于一个完整 Edition；阶段推进和 Gate 的最小单位是 `EditionPart`。Edition 只有在其全部 EditionPart 通过时才标记完整。
5. 多个 Edition 可以并行；同一 Edition 内按 EditionPart 推进，不按单页或 SourceSpan 推进下游阶段。
6. 每一步产生的业务数据、原始输出、人工决定、失败记录和执行证据必须永久留存。
7. 任何修改产生新 Revision；不覆盖旧 Artifact，不复用旧 ID。
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

所有加工 Module 使用同一外部 Interface：

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

Module 只能读取请求中明确冻结的 Artifact，不得读取上游工作目录中的“最新文件”。

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

Ledger 以单机本地进程提供统一 Interface。Pipeline、OCR FastAPI 和 Flutter Review Console 都通过本地客户端调用该进程，不直接打开 Metadata Ledger。进程默认绑定 loopback 或 Unix domain socket，只允许一个写入者实例；写事务由进程串行化，SQLite 使用 WAL 允许只读查询并发。进程级锁阻止第二个 Ledger 写入者启动。进程不可用时 Module 挂起 StepRun，不回退到直接写库。

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
8. PublicationPackage 同时包含结构化知识、原始资料及其关系。
9. 移动端数据与 GraphProjectionPack 来自同一 Canonical Snapshot，Graph 往返无损。
10. 更换 OCR、模型、索引或存储 Adapter 不改变相邻 Module 的 Interface。

## 21. 非目标

- 微服务、消息队列和分布式调度；
- APP 后端、客户端、Mark UI 或社交功能实现；
- 用户 Pattern 编辑器和发布流程；
- Embedding、向量检索和端侧语言模型；
- 要求三百页 Edition 在全部加工完成前不能产生任何可审核中间成果；系统按卷或连续页区间逐 Part 推进，但仍保留整本完成状态。
