# T-08 BDD 验收场景（R2 返工版）

## B1 Tag 三个耦合接口完整承接且供给包唯一

**Given** 权威源 `tag_system/README.md:30-32` 确立了 Tag 系统依赖知识系统的三个唯一接口，
**When** 执行者查看架构规格 §1 与 §16.3，
**Then** 规格完整承接，且**供给子包在 §1 与 §16.3.1 两处同时正确**：

1. `最小盘面概念字典`：约 100–200 个概念，由 `KnowledgeDataPack` 供给，仅含稳定 ID + 名称 + 基础类象，**严格声明不含规则 DSL**；
2. `MarkContentBinding` 内容供给：由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给；
3. `EvidenceBundle` 服务：由 `EvidenceMapPack` 供给。

任一处把接口供给包改成别的子包（如把 `EvidenceBundle` 改为 `SearchIndexPack`），门禁必须非零退出。

## B2 五个关键字段的生产 Module 与归属子包精确匹配

**Given** 权威源 `tag_system/TAG_SYSTEM_DESIGN.md` 规定了语义物种的元数据字段，
**When** 执行者查看 §16.3.2 字段表格，
**Then** 每一行的生产 Module 与归属子包必须与下表完全一致：

| 字段 | 生产 Module | 归属子包 |
|---|---|---|
| `omen_carrying`（吉凶承载性） | M4 | `KnowledgeDataPack` |
| `condition_affordance`（条件可供性） | M4 | `RuleIndexPack` 与 `KnowledgeDataPack` |
| `school_variance_display`（流派分歧展示） | M4 / M6 | `KnowledgeDataPack` |
| `concept_id`（概念标识） | M4 | `KnowledgeDataPack` |
| 是否改变当前判断 | M4 / M7 / M6 | `KnowledgeDataPack`（`MarkContentBinding`） |

**And** M5 **只做校验**：生产 Module 列绝对不得出现 M5，M5 不得被写成字段生产者。

## B3 边界清晰声明

**Given** Tag 系统为外部独立消费端，
**When** 执行者查看架构规格 §1 系统边界，
**Then** 规格清晰声明黑箱通过 `PublicationPackage` 承接上述三个接口，且 Tag 侧 G4 必须以 `TAG_SYSTEM_DESIGN.md §12.2` 命名空间形式出现，不得与规格正文 G4 内容分层门禁混同。

## B4 异常路径：错误生产者归属（异常路径）

**Given** 把 `concept_id` 改成 `M2 / SourceAssetPack`，或只改某字段的生产 Module（Package 保持正确），或只改某字段的归属子包（Module 保持正确）；
**When** 运行语义门禁；
**Then** 必须非零退出，并打印该字段的实际值与期望值。

## B5 异常路径：错误接口供给包（异常路径）

**Given** 把任一接口（如 `EvidenceBundle`）的供给子包改成错误子包；
**When** 运行语义门禁；
**Then** 必须非零退出。
