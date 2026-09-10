# T-07 Executor Prompt

你是 T-07 文档执行 Agent。请在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支工作，禁止切换分支或进入其他 worktree。

先完整阅读并严格遵循：

- `docs/blackbox-spec-rework/work-items/t07/README.md`
- `docs/blackbox-spec-rework/work-items/t07/BDD.md`
- `docs/blackbox-spec-rework/work-items/t07/TDD.md`
- `docs/blackbox-spec-rework/work-items/t07/ACT.yaml`

【关键执行铁律与特别指示】：
1. 遇到任何照抄源冲突、规格歧义或意外失败，严禁自己做决定，必须立即停止并向上汇报！
2. 唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`；严禁修改任何代码、JSON Schema、测试、工作包文档、TODO、PLAN 或 `verify-T.sh`。
3. 先保存 Red baseline（运行 `bash docs/blackbox-spec-rework/verify-T.sh` 并确认 8 FAIL，T-07 为 FAIL）。
4. 在 `openspec/learn-system-blackbox-architecture.md` §16 M8 Dataset Compilation 末尾（在 `## 17. Artifact Ledger` 之前），新增小节「16.2 KnowledgePack 与 PublicationPackage 双向映射表」：
   - 写入概念取代声明：**黑箱架构规格以多子包组合的 `PublicationPackage`（特别是其中的结构化知识主体 `KnowledgeDataPack`）正式取代早期草案中单一扁平的 `KnowledgePack` 概念。**
   - 写入两列完整映射表，逐项对应 `LEARN_SYSTEM_TARGET.md §9` 中的全部条目，严禁遗漏任何一项，严禁留空行：
     - `release-manifest` → `ReleaseManifest`（发布清单与元数据摘要）
     - `schema` → `KnowledgeDataPack`（及 Contract Registry 对应模式定义）
     - `concepts` → `KnowledgeDataPack`（概念定义及术语体系）
     - `entries` → `KnowledgeDataPack`（知识条目 KnowledgeEntry 集合）
     - `assertions` → `KnowledgeDataPack`（结构化主张 Assertion 集合）
     - `applicability-rules` → `RuleIndexPack`（与 `KnowledgeDataPack` 中的适用规则）
     - `school-views` → `KnowledgeDataPack`（各流派分歧与立场视图）
     - `evidence-links` → `EvidenceMapPack`（证据链接与跨层关联）
     - `source-spans` → `EvidenceMapPack`（与 `KnowledgeDataPack` 中的原文片段引用）
     - `source-anchors` → `EvidenceMapPack`（底本物理位置证据锚点，必须进发布包）
     - `scan-assets-or-references` → `SourceAssetPack`（扫描图或受控引用）
     - `exact-search-index` → `SearchIndexPack`（精确检索索引）
     - `fulltext-index` → `SearchIndexPack`（全文检索索引）
     - `optional-vector-index` → **本期不产出（依据 §21 非目标）**
     - `query-contract` → `RuleIndexPack` 与 `SearchIndexPack`（查询契约与接口定义）
5. 完成后运行 `docs/blackbox-spec-rework/work-items/t07/TDD.md` 中的全部 Green checks、`bash docs/blackbox-spec-rework/verify-T.sh`（FAIL 数必须从 8 严格减少至 7，且 T-07 为 PASS）以及 `git diff --check`。
6. 确认无误后提交修改，提交消息必须严格为：`docs: map KnowledgePack directories to PublicationPackage artifacts`。
7. 最终报告必须包含：commit hash、真实修改文件、Red baseline、Green 原始摘要、双向映射表核验对照及全局 T 结果。
