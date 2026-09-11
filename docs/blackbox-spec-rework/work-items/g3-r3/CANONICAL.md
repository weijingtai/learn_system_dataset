# G3 R3 权威常量

本文件是门禁 expected 值的唯一照抄源。执行脚本必须硬编码这些常量，不得从待测 `$SPEC` 动态生成 expected。

规范化规则固定为：仅删除反引号 `` ` ``、星号 `*`、空格、Tab 和 CR；保留其他全部字符，包括中英文标点、数字、斜杠、否定词和标识符。比较前后均使用同一规则。

## D-07

以下各行在 §16 中必须规范化后精确出现一次：

```text
[D07-TP-START] `TechniqueProfilePack` 承载各术数领域确定性事实结构与规则语法标准，消除跨技法匹配歧义：
[D07-TP-PROFILE] - **FactSet Profile**：针对不同术数体系定义专用事实切片 Profile，包括八字 `BaziFactSet`、七政 `QizhengFactSet`、紫微 `ZiweiFactSet`、奇门 `QimenFactSet`、六壬 `LiuRenFactSet`；依 2026-09-08 用户裁定，首纵切内部验收包采用 `QizhengFactSet`；
[D07-TP-FIELDS] - **事实字段与枚举**：严格列出各 Profile 允许的事实键名、数据类型及闭集枚举值，禁止非受控字段参与确定性匹配；
[D07-TP-OPERATORS] - **operator 集合**：规范规则条件所允许的确定性比较与集合操作符全集（如 `eq`、`neq`、`in`、`not_in`、`gt`、`gte`、`lt`、`lte`、`all`、`any`、`none`）；
[D07-TP-AST] - **AST schema 版本**：定义规则 AST 的结构化模式版本（如 `ast_schema_version: "1.0"`），规则纯声明式表达，**禁止使用任何可执行或模型生成的 Python 规则**。
[D07-QC-START] `QueryContractPack` 规范发布包对外暴露的确定性只读查询契约与客户端调用接口，定义四个核心接口及兼容声明：
[D07-QC-ENTRY] - **`getEntry(entry_id)`**：按稳定实体标识获取对应 `KnowledgeEntry` 条目及其主张和上下文；
[D07-QC-SPAN] - **`getSourceSpan(span_id)`**：按片段标识获取底层 `SourceSpan` 原文、校勘与定位引用；
[D07-QC-SEARCH] - **`searchKnowledge(query, filters)`**：执行跨条目/术语的精确与全文知识检索；
[D07-QC-MATCH] - **`matchFacts(fact_set)`**：输入版本化 FactSet，执行确定性规则匹配并返回全部且仅返回适用规则，明确报告已满足条件、缺失条件与触发例外；任一条件不全或例外成立时不得输出肯定判断；
[D07-QC-COMPAT] - **向后兼容声明**：明确规定查询契约接口必须保持向后兼容演进，客户端只依赖稳定接口契约，不直接绑定底层文件存储形式。
[D07-RI-START] `RuleIndexPack` 承载确定性适用规则索引：
[D07-RI-VERSION] - **Profile 版本声明**：`RuleIndexPack` 中每条规则必须显式声明其所依据的 `Profile 版本`（如 `profile_version: "qizheng_v1.0"`）及 `AST schema 版本`；
[D07-RI-DECLARATIVE] - **规则纯声明式结构**：所有适用规则必须使用纯声明式的 `结构化 AST/YAML/JSON` 表达，禁止包含任何动态 Python 逻辑或自由文本代码块。
```

D-07 块边界：START 行之后连续的 `- ` 项属于该块；遇到空行或下一个非列表段落即结束。不得用描述子串代替 START 全行。

## T-07

取代规范句：

```text
[T07-REPLACEMENT] 黑箱架构规格以多子包组合的 `PublicationPackage`（特别是其中的结构化知识主体 `KnowledgeDataPack`）正式取代早期草案中单一扁平的 `KnowledgePack` 概念。
```

§16.2 的 15 个规范化 key/value：

| Anchor | key | value |
|---|---|---|
| T07-M01 | release-manifest | ReleaseManifest（发布清单与元数据摘要） |
| T07-M02 | schema | KnowledgeDataPack（及ContractRegistry对应模式定义） |
| T07-M03 | concepts | KnowledgeDataPack（概念定义及术语体系） |
| T07-M04 | entries | KnowledgeDataPack（知识条目KnowledgeEntry集合） |
| T07-M05 | assertions | KnowledgeDataPack（结构化主张Assertion集合） |
| T07-M06 | applicability-rules | RuleIndexPack（与KnowledgeDataPack中的适用规则） |
| T07-M07 | school-views | KnowledgeDataPack（各流派分歧与立场视图） |
| T07-M08 | evidence-links | EvidenceMapPack（证据链接与跨层关联） |
| T07-M09 | source-spans | EvidenceMapPack（与KnowledgeDataPack中的原文片段引用） |
| T07-M10 | source-anchors | EvidenceMapPack（底本物理位置证据锚点，必须随包发布） |
| T07-M11 | scan-assets-or-references | SourceAssetPack（扫描图或受控引用） |
| T07-M12 | exact-search-index | SearchIndexPack（精确检索索引） |
| T07-M13 | fulltext-index | SearchIndexPack（全文检索索引） |
| T07-M14 | optional-vector-index | 本期不产出（依据§21非目标） |
| T07-M15 | query-contract | QueryContractPack（查询契约与接口定义） |

## T-08

§1 三行：

```text
[T08-S1-01] 1. `最小盘面概念字典`：规模约 100–200 个概念，由 `KnowledgeDataPack` 供给，仅包含稳定 `concept_id` + 名称 + 基础类象，**严格声明不含规则 DSL**，用以解除 `TAG_SYSTEM_DESIGN.md §12.2` 的 G4 依赖倒挂问题；
[T08-S1-02] 2. `MarkContentBinding` 内容供给：由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给，为 UI 标记提供内容与分歧数据；
[T08-S1-03] 3. `EvidenceBundle` 服务：由 `EvidenceMapPack` 供给，为解盘与证据高亮提供底层的无损证据链切片。
```

§16.3.1 块标题与唯一供给行：

```text
[T08-B1-HEAD] 1. **`最小盘面概念字典`**：
[T08-B1-SUPPLY]    - **供给子包**：由 `KnowledgeDataPack` 供给；
[T08-B1-LIMIT]    - **硬限制约束**：**严格声明不含规则 DSL**，用以解除 `TAG_SYSTEM_DESIGN.md §12.2` 的 G4 依赖倒挂问题。规则 DSL 属于后续阶段的 RuntimeFeature 范围，不在最小概念字典中承载。
[T08-B2-HEAD] 2. **`MarkContentBinding` 内容供给**：
[T08-B2-SUPPLY]    - **供给子包**：由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给；
[T08-B3-HEAD] 3. **`EvidenceBundle` 服务**：
[T08-B3-SUPPLY]    - **供给子包**：由 `EvidenceMapPack` 供给；
```

编号块起于精确 HEAD 行，止于下一个匹配 `^[1-3]\. \*\*` 的行或 `#### 16.3.2`。每块匹配 `^[[:space:]]+- \*\*供给子包\*\*：` 的行数必须为 1。

§16.3.2 五条说明：

```text
[T08-P01] - `omen_carrying`（吉凶承载性）：指示该标记是否承载吉凶定性，由 M4 生产，归入 `KnowledgeDataPack`（由 M5 负责校验其合规性，M5 不得作为字段生产者）；
[T08-P02] - `condition_affordance`（条件可供性）：指示该标记可承载的条件槽位，由 M4 结构化生产，归入 `RuleIndexPack` 与 `KnowledgeDataPack`（由 M5 负责校验其可执行性，M5 不得作为字段生产者）；
[T08-P03] - `school_variance_display`（流派分歧展示）：指示各流派对此标记的不同定性或观点分歧，由 M4/M6 审核产出，归入 `KnowledgeDataPack`；
[T08-P04] - `concept_id`（概念标识）：全局稳定的概念 ID，由 M4 术语判层确定，归入 `KnowledgeDataPack`；
[T08-P05] - 「是否改变当前判断」：明确规定属于 `MarkContentBinding` 的核心内容状态字段，必须由知识层（M4/M7/M6）通过判定状态供给，**UI 不得猜测**。
```

§16.3.2 五条表格数据行：

```text
[T08-R01] | `omen_carrying` | 吉凶承载性：指示该标记是否承载吉凶定性 | M4 | `KnowledgeDataPack` | 满足吉凶标定标准（`canonical` / `none`），严禁 UI 自行推导吉凶；M5 仅作为 Validator 负责检验标定合规性，不得作为生产者 |
[T08-R02] | `condition_affordance` | 条件可供性：指示该标记可承载的条件槽位 | M4 | `RuleIndexPack` 与 `KnowledgeDataPack` | 结构化输出条件依赖；当 `omen_carrying=canonical` 时必填；M5 仅作为 Validator 负责校验规则可执行性，不得作为生产者 |
[T08-R03] | `school_variance_display` | 流派分歧展示：指示各流派对此标记的不同定性或观点分歧 | M4 / M6 | `KnowledgeDataPack` | 存在流派分歧的知识点强制展示多流派对照，严禁单一流派静默覆盖 |
[T08-R04] | `concept_id` | 概念标识：全局稳定的概念 ID | M4 | `KnowledgeDataPack` | 术语判层产出的稳定概念 ID，盘面语义物种必须绑定 |
[T08-R05] | 是否改变当前判断 | 指示分歧是否导致格局或断语定性翻转 | M4 / M7 / M6 | `KnowledgeDataPack`（`MarkContentBinding`） | 核心内容状态字段，必须由知识层通过判定状态与 ReviewDecision 供给，**UI 不得猜测** |
```

Package 标识提取正则固定为 `[A-Za-z][A-Za-z0-9]*Pack`。集合比较必须同时比较成员和值的出现次数，不能只取第一个匹配。

G4 命名空间和“不含规则 DSL”必须在 §1 的 T08-S1-01 与 §16.3.1 的 T08-B1-LIMIT 两处分别校验；任一处缺失都失败。
