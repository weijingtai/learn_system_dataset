# Learn System 最终目标、运行方式与现状

> 状态：项目最终开发目标，2026-09-08 经用户确认。
> 本文是跨 `ocr/`、`pipeline/`、`knowledge_system/`、`tag_system/` 的总入口；各目录内的规范继续约束各自实现。
> `Embedding-AI/` 不属于当前主线，后期通过模型 Adapter 接入。

## 1. 一句话目标

Learn System 是一套离线知识编译系统：把公开授权的术数古籍扫描件、PDF、图片或电子文本，编译成可验证、可索引、可版本化、可下载到移动端的 `KnowledgePack`。排盘 APP 用确定性引擎生成盘面事实，再从本地 KnowledgePack 找出与当前盘面匹配的古籍词条、条件、例外与原文证据，交给 UI 展示。

用户还可以对词条、原句或扫描页位置写私人笔记；公开笔记可进入社区讨论，支持评论、回复、点赞、点彩、收藏和分享。

## 2. 系统边界

### Learn System 负责

- 登记书籍版本、来源、权利状态和文件哈希；
- OCR、人工校对、版面与字框审计；
- 生成可引用的转录文本和扫描位置映射；
- 抽取概念、知识主张、适用条件、例外、流派和证据；
- 运行确定性校验、跨模型复核和人工签发；
- 编译不可手工编辑的 KnowledgePack 与各种索引；
- 为客户端提供稳定的查询契约、版本和回滚信息。

### 排盘 APP 负责

- 确定性排盘和盘面事实计算；
- 产生相应术数的 `ChartFactSet`；
- 调用本地知识匹配接口，不直接读取加工区文件；
- 渲染词条、古籍原文、扫描定位、Tag/Mark 和社区注解；
- 保存私人笔记，并与服务端同步公开注解和互动。

### 端侧小语言模型负责（后期）

- 查询编排、结果排序、归纳和自然语言表达；
- 不负责确定性排盘；
- 不作为知识来源；
- 不取代确定性召回、发布门禁和原文证据。

## 3. 两个核心使用场景

### 3.1 排盘后自动匹配古籍知识

例如八字排出“丙日干、亥月”，APP 产生：

```yaml
technique_id: bazi
day_stem: bing
month_branch: hai
```

知识匹配模块应返回“十月丙火”及其相关主张。如果盘面还提供壬水、甲木、戊土、透干、十神、刑冲合害等事实，匹配器继续返回更具体的条件、加强条件、限制条件和破格条件。

例如七政四余排出“寅月、木星入寅宫”，确定性规则可匹配“青龙扶砚”；太阳与木星同宫可成为加强条件，禁忌星体或对宫状态可成为限制/破格条件。此过程不依赖 AI。

### 3.2 图书馆阅读与锚定注解

用户可以按术数、书籍、章节、词条或原文阅读 KnowledgePack，并对以下对象写注解：

- `KnowledgeEntry`：一个稳定词条；
- `Assertion`：一条可验证知识主张；
- `SourceSpan`：一句或一段原文；
- `SourceAnchor`：PDF/PNG 页面中的具体区域或字框范围。

注解分两层：

- 私人注解：默认仅作者可见，可跨设备同步；
- 公开注解：其他用户可见，可评论、回复、点赞、点彩、收藏和分享。

公开注解可以通过未来的 Social Adapter 接入 `xuan-social`，但必须保留知识锚点，不能退化成与原文无关的普通帖子。

## 4. 端到端运行流程

```text
原始 PDF / PNG / EPUB / 文本
  ↓ 1. Source Ingestion
SourceAsset + RightsGrant + file hash
  ↓ 2. Page Extraction / OCR
OcrDocument + OcrPage + OCR 字框
  ↓ 3. Proofreading
修订记录 + anomaly + audit log
  ↓ 4. Transcript Compilation
Transcript + PageMap + AnchorMap
  ↓ 5. Segmentation
SourceSpan
  ↓ 6. Knowledge Extraction
Concept + Assertion + ApplicabilityRule + SchoolView
  ↓ 7. Evidence Binding
Assertion → SourceSpan → OCR 字框 → 原始扫描页
  ↓ 8. Review / Validation
机器校验 + 跨模型复核 + 人工签发 + 权利门禁
  ↓ 9. Entry Aggregation
KnowledgeEntry
  ↓ 10. Release Compilation
不可变 KnowledgePack + ReleaseManifest
  ↓ 11. Index Compilation
SQLite / 全文 / Graph / 可选向量索引
  ↓ 12. Distribution
签名、分片、下载、升级、回滚
  ↓
排盘 APP：ChartFactSet → KnowledgeMatch → UI / Tag / Annotation
```

每一步都是独立 Module，通过版本化 Interface 连接。OCR 引擎、索引实现或模型可以替换，但不得迫使上下游理解其内部实现。

## 5. 存储无关的核心对象

SQLite、RAG、Graph 或其他数据库只是 Adapter。项目的逻辑模型不得由某一种存储格式定义。

核心对象至少包括：

- `SourceAsset`：原始 PDF、PNG、EPUB 或文本；
- `SourceEdition`：书籍、版本、来源和权利信息；
- `OcrPage` / `OcrGlyph`：页面、字框、置信度和修订历史；
- `SourceAnchor`：文本位置到扫描位置的稳定映射；
- `SourceSpan`：可引用的原文片段；
- `Concept`：稳定概念；
- `Assertion`：知识主张；
- `ApplicabilityRule`：该主张适用于什么盘面事实；
- `SchoolView`：流派归属与分歧；
- `KnowledgeEntry`：面向产品的词条聚合；
- `EvidenceLink`：主张到原文和扫描证据的连接；
- `Annotation`：私人或公开注解；
- `ReleaseManifest`：版本、依赖、哈希、权利、审批和兼容信息。

## 6. 无损证据链

任何展示给用户的知识都必须能够反向定位：

```text
KnowledgeEntry
  → Assertion
    → EvidenceLink
      → SourceSpan
        → SourceAnchor
          → OcrPage / OcrGlyph range
            → SourceAsset（PDF 页或 PNG）
```

客户端最终应能打开原始扫描件并高亮对应区域。纯文本引用只能算开发级证据，不能算最终无损证据链。

## 7. 盘面匹配接口

不同术数共享查询框架，但各自拥有独立 FactSet Profile：

- `BaziFactSet`
- `QizhengFactSet`
- `ZiweiFactSet`
- `QimenFactSet`
- `LiuRenFactSet`

以八字为例，基础条件应结构化为：

```yaml
applicability:
  all:
    - fact: day_stem
      operator: eq
      value: bing
    - fact: month_branch
      operator: eq
      value: hai
```

更细条件可以覆盖透干、藏干、十神、旺衰、刑冲合害、格局和神煞。APP 负责生成这些确定性事实，KnowledgePack 负责声明哪些知识与哪些事实匹配。

确定性匹配器负责完整召回；语言模型只能在召回结果上进行编排、排序和表达。

## 8. Tag/Mark 的位置

Tag 不是数据库标签，也不负责判断格局。它是 `KnowledgeMatch` 或盘面语义的 UI 投影：

```text
ChartFactSet
  → Deterministic Matcher
  → KnowledgeMatch / MarkInstance
  → TagRenderModel
  → 盘面角标、状态、详情卡和证据入口
```

知识侧通过 `MarkContentBinding` 提供概念、条件、流派分歧和证据；Tag/UI 不得自行猜测知识语义。

## 9. KnowledgePack 的建议结构

```text
knowledge-pack-<technique>-<version>/
├── release-manifest
├── schema
├── concepts
├── entries
├── assertions
├── applicability-rules
├── school-views
├── evidence-links
├── source-spans
├── source-anchors
├── scan-assets-or-references
├── exact-search-index
├── fulltext-index
├── optional-vector-index
└── query-contract
```

实际可以打包成一个或多个 SQLite、Protobuf、JSONL、Parquet 或索引二进制文件；客户端只依赖逻辑 Interface 和版本契约。

## 10. 现有工具与成熟度

成熟度定义：

- **可用**：真实数据已运行，适合作为后续实现基础；
- **开发可用**：能完成局部工作，但缺完整门禁、泛化或发布保证；
- **仅规格**：设计文档存在，没有可执行实现；
- **缺失**：尚无满足目标的实现或规格不足。

| 阶段 | 现有位置 | 当前水平 | 可用范围 | 主要缺口 |
|---|---|---|---|---|
| 原始资料 | `raw_books/` | 开发可用 | 保存八字、奇门试点原书 | 权利模型不统一；扫描资产覆盖不足 |
| 文本原料入库 | `pipeline/runner/ingest_raw.py` | 开发可用 | UTF-8 文本入 corpus、生成 manifest/hash | 不能直接处理扫描图；RightsGrant 不完整 |
| OCR 引擎 | `ocr/src/gujiorc/ocr/` | 开发可用 | PaddleOCR、预处理、切分、方向判断 | 横排 R7、曲线/星盘版面、生产环境复现 |
| OCR 校对 | `ocr/local/`、`ocr/src/gujiorc/core/` | 开发可用 | 改字、补框、生僻字、审计、异常登记 | Web UI 尚未完成浏览器验收；多用户协作未实现 |
| OCR 导出 | `ocr/src/gujiorc/core/export.py` | 开发可用 | 生成 transcript、manifest 和 transcript hash | 不导出扫描图、page JSON、字框 anchor、审计和质量包；未知字协议不统一 |
| Corpus Schema | `pipeline/schemas/core/SCHEMA.md` | 可用（M1） | source/unit/assertion/evidence 最小结构 | 缺 SourceAnchor、RightsGrant、ApplicabilityRule、Annotation、Release schema |
| 任务生成 | `pipeline/tools/gen_*.py`、`tools/lib/taskgen.py` | 开发可用 | 八字批量任务和部分通用下游任务 | 多处仍硬编码八字/《穷通宝鉴》；奇门和其他技法未完全泛化 |
| 模型运行归档 | `pipeline/runner/run_task.py` | 开发可用 | prompt/input/response 哈希和运行归档 | 未串联输出校验/审批 gate；可能过早写 completed；成本元数据不完整 |
| 确定性校验 | `pipeline/validators/` | 可用（加工级） | unit、引用、ID、assertion、glossary、coverage、RAG 检查 | 校验 PASS 不代表内容已批准；发布级 fail-closed 门禁缺失 |
| 知识单元 | `pipeline/units/` | 开发可用 | 现有八字/奇门单元及原文证据 | 多数 assertions 为 `machine_extracted`；一 span 一临时 unit，不是稳定产品词条 |
| L1/L2 检索 | `pipeline/rag/` | 开发可用 | assertion 和原文定位设计已存在 | 当前索引是 dev；concept→assertion 断链；完整 span ID 解析有缺陷；迁移后预置 SQLite 需重建验证 |
| L3 向量检索 | `pipeline/briefs/MRAG2_ZVEC_BRIEF.md` | 仅规格 | 后期语义召回设计 | 尚无实现；不是第一阶段依赖 |
| 知识总规范 | `knowledge_system/` | 规格较成熟 | 对象、流程、决策、质量与发布目标 | 文档状态与实际产物有陈旧项；没有编译为可执行政策 |
| ReleaseBundle | `knowledge_system/` 相关规范 | 仅规格 | 已定义“APP 只消费发布包”原则 | 无 compiler、release validator、正式产物、签名和回滚实现 |
| 结构化盘面匹配 | 尚无独立 Module | 缺失 | 现有自然语言 `conditions` 可供人工理解 | 缺 FactSet Profile、ApplicabilityRule、Matcher 和可查询索引 |
| Tag/Mark | `tag_system/` | 仅规格 | 对象分层、视觉语法、样式包与接口设计 | 无 Registry loader、MarkContentBinding 产出、MarkInstance Adapter 或 UI 实现 |
| APP 接入 | 规范中的查询接口 | 仅规格 | `getEntry/getSourceSpan/searchKnowledge` 等方向明确 | 无 AppKnowledgeAdapter、下载/升级/回滚实现 |
| 注解与社区 | 本文目标；外部 `xuan-social` 可参考 | 缺失 | 产品场景已明确 | 缺 Annotation schema、锚点、权限、同步、互动和 Social Adapter |
| 端侧 AI | `Embedding-AI/` 暂不处理 | 后置 | 不属于当前主线 | 后期通过独立 Model Adapter 接入 |

## 11. 当前已有的真实成果

- OCR 已具备扫描识别、字框编辑、生僻字处理、审计日志和 corpus 导出代码；
- `pipeline/corpus/` 已有八字和奇门试点语料；
- `pipeline/TASKS/` 已积累分段、概念、主张、释义和模型运行记录；
- `pipeline/units/` 已有 139 个知识单元文件夹；
- 《穷通宝鉴》“十月丙火”已形成 `ku_bazi_000046`，含 5 条证据绑定主张；
- validators 已覆盖多种加工级确定性检查；
- SQLite/FTS L1/L2 检索已有开发实现；
- Knowledge 与 Tag 的职责拆分和三个允许的跨区接口已经形成规范。

## 12. 阻断最终目标的缺口

### P0：先形成不含 AI 的最小闭环

1. 定义并实现 `SourceAnchor`，保留 transcript → OCR 字框 → PDF/PNG 的无损映射；
2. 统一 source ID、rights、未知字和异常页协议；
3. 泛化 taskgen，移除书名与技法硬编码；
4. 定义各术数 FactSet Profile 和结构化 `ApplicabilityRule`；
5. 将现有自然语言 conditions 编译/标注为可查询条件；
6. 修复 concept→assertion→evidence 检索链及完整 span ID 索引；
7. 实现 `KnowledgeReleaseCompiler`、ReleaseManifest 和发布级 validator；
8. 提供只读 `AppKnowledgeAdapter`；
9. 用一个真实八字垂直切片证明排盘事实可以匹配词条并打开原始扫描位置。

### P1：产品化与多术数扩展

1. 把一 span 一 unit 聚合为稳定 `KnowledgeEntry`；
2. 增加流派、冲突、条件、例外和审核状态过滤；
3. 为七政四余、紫微、奇门、六壬建立 FactSet Profile 与样例包；
4. 实现 KnowledgePack 分片、签名、下载、升级和回滚；
5. 实现 `MarkContentBinding`、`ChartSemanticAdapter` 和 Tag 的最小只读展示；
6. 实现私人/公开 Annotation 以及 `xuan-social` Social Adapter。

### P2：后期增强

1. L3 向量或 Graph Adapter；
2. EvidenceBundle 和 `check_answer`；
3. 端侧小语言模型查询编排与解释；
4. 更复杂的 Tag 样式、编辑器和 Marketplace。

## 13. 第一条验收纵切

第一阶段只证明一条完整链，不追求同时覆盖所有术数：

```text
一页八字古籍扫描
→ OCR 与人工校对
→ corpus + manifest + SourceAnchor
→ SourceSpan / Assertion / ApplicabilityRule
→ validator
→ KnowledgePack
→ BaziFactSet(day_stem=bing, month_branch=hai)
→ 匹配“十月丙火”全部主张
→ APP mock 展示原文
→ 打开原始扫描页并高亮对应区域
→ 对该原句保存私人注解和公开讨论锚点
```

这条纵切通过后，再扩展十干十二月、十神和格局，随后复用相同 Interface 接入其他术数。

## 14. 最终完成定义

Learn System 达到最终目标，至少需要满足：

- 任一发布词条可以回到原始扫描证据；
- 排盘 APP 不依赖 AI 即可确定性召回相关知识；
- SQLite、RAG、Graph 可以替换而不改变核心对象和客户端查询契约；
- 未通过权利、证据、状态和审批门禁的内容无法发布；
- 客户端只读取版本化 KnowledgePack，不读取加工区；
- 私人和公开注解都稳定锚定到可版本迁移的知识/原文对象；
- 多术数通过独立 FactSet Profile 扩展，不复制整条管线；
- AI 缺席或更换时，基础排盘、匹配、证据和阅读功能仍可运行。

