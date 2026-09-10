# T-07 BDD 验收场景

## B1 KnowledgePack 14/15 目录全覆盖

Given 权威源 `LEARN_SYSTEM_TARGET.md §9` 提出了 KnowledgePack 的建议目录结构，
When 执行者查看架构规格 §16 M8 Dataset Compilation，
Then 能找到一张完整的双向映射表，包含全部目录项：
- `release-manifest`
- `schema`
- `concepts`
- `entries`
- `assertions`
- `applicability-rules`
- `school-views`
- `evidence-links`
- `source-spans`
- `source-anchors`
- `scan-assets-or-references`
- `exact-search-index`
- `fulltext-index`
- `optional-vector-index`
- `query-contract`
And 没有任何目录被静默遗漏，表中无空行。

## B2 明确落点与非目标显式标注

Given 各项目录在现代架构中分别对应独立的发布子包，
When 执行者核对映射表右列归属时，
Then 各项正确归入 PublicationPackage 对应子包（如 `ReleaseManifest`、`KnowledgeDataPack`、`RuleIndexPack`、`EvidenceMapPack`、`SourceAssetPack`、`SearchIndexPack`），
And `optional-vector-index` 显式标注为「本期不产出（依据 §21）」，而非静默省略。

## B3 概念取代声明

Given 历史文档存在旧术语 `KnowledgePack`，
When 执行者阅读架构规格时，
Then 规格包含明确的声明：「架构以 `PublicationPackage`（及核心子包 `KnowledgeDataPack`）正式取代早期草案中扁平单一的 `KnowledgePack` 概念」，消除多方协作歧义。
