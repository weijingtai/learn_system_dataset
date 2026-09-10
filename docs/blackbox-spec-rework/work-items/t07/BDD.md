# T-07 BDD 验收场景（R2 返工版）

## B1 15 项目录全覆盖且唯一

**Given** 权威源 `LEARN_SYSTEM_TARGET.md §9` 提出了 KnowledgePack 的建议目录结构，
**When** 执行者查看架构规格 §16.2 映射表，
**Then** 数据行总数严格等于 15，且以下每一项在第一列各出现且仅出现一次：
`release-manifest`、`schema`、`concepts`、`entries`、`assertions`、`applicability-rules`、`school-views`、`evidence-links`、`source-spans`、`source-anchors`、`scan-assets-or-references`、`exact-search-index`、`fulltext-index`、`optional-vector-index`、`query-contract`；
且表中无空行、无静默遗漏。

## B2 右列唯一落点

**Given** 各项目录分别对应唯一的发布子包，
**When** 执行者核对右列归属时，
**Then**：

- `query-contract` 规范化后**精确等于** `QueryContractPack（查询契约与接口定义）`，附加任何第二个子包（如 `EvidenceMapPack`、`RuleIndexPack`、`SearchIndexPack`）都必须判失败；
- `optional-vector-index` 规范化后**精确等于** `本期不产出（依据§21非目标）`，追加任何归属（如 `SearchIndexPack`）都必须判失败；
- 其余各项正确归入 `ReleaseManifest`、`KnowledgeDataPack`、`RuleIndexPack`、`EvidenceMapPack`、`SourceAssetPack`、`SearchIndexPack`，且不得出现无归宿项。

## B3 概念取代声明必须是肯定语义

**Given** 历史文档存在旧术语 `KnowledgePack`，
**When** 执行者阅读 §16.2 正文时，
**Then** 同一句肯定语义必须同时包含 `PublicationPackage`、`KnowledgeDataPack`、`正式取代`、`KnowledgePack`；
把「正式取代」改成「不得取代」等否定式时，门禁必须非零退出。

## B4 异常路径：追加第二归属（异常路径）

**Given** 给 `query-contract` 追加 `EvidenceMapPack`，或给 `optional-vector-index` 追加「同时归入 `SearchIndexPack`」；
**When** 运行语义门禁；
**Then** 必须非零退出，并打印实际归属与期望归属的差异。

## B5 异常路径：否定语义取代声明（异常路径）

**Given** 把取代声明中的「正式取代」改为「不得取代」；
**When** 运行语义门禁；
**Then** 必须非零退出。
