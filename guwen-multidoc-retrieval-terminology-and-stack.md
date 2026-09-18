# 多文档语义检索 + 相似/相反查找 + 溯源：术语地图与开源选型

> 场景：多篇文章 → 语义 span 抽取 → 图谱数据库 + embedding → RAG 检索 → 点开一条后要能回到原句、看含义、找相近/相反句、看前后句、看出处。
> 结论一句话：**这不是一个新问题，而是一条成熟链路的组合**——总称 **GraphRAG（图谱增强检索）+ 跨文档证据检索（Cross-document Evidence Retrieval）+ 来源溯源（Provenance / Attribution）**。

---

## 1. 术语地图：你的每个诉求都有一个专业名字

| 你想做的事 | 专业名称（英文） | 所属领域 |
|---|---|---|
| 按主题搜出相关内容并按相关度排序 | **Dense Retrieval + Reranking**（Learning-to-Rank）、**Hybrid Search**、**RRF**（Reciprocal Rank Fusion） | 信息检索（IR） |
| 图数据库 + 向量 + RAG | **GraphRAG / Knowledge-Graph RAG** | RAG |
| 点第一条 → 回到原句 | **Source Grounding / Span Attribution / Provenance** | 可解释性 / 溯源 |
| 这句话的"含义" | **Proposition / Normalized Claim**（命题） | 知识抽取 |
| 找意思**相近**的其他句 | **Semantic Textual Similarity (STS)**、**Paraphrase Retrieval**、**Dense Retrieval** | 语义检索 |
| 找意思**相反**的其他句 | **Natural Language Inference (NLI) → Contradiction Detection**；**Stance Detection**；**Claim Matching**；**Fact Verification (FEVER)** | NLI / 事实核查 / 论辩挖掘 |
| 这句话的前一句 / 后一句 | **Sentence-Window Retrieval**、**Parent-Document Retriever**、**Small-to-Big**、**Context Expansion** | RAG 上下文工程 |
| 这句话出自哪一篇 | **Provenance / Attribution / Citation Grounding** | 可信 AI |

> 学术上对"跨文档找相似/相反断言"最贴近的范式叫 **CDCL-NLI（Cross-Document Cross-Lingual NLI，2025）**，以及事实核查领域的 **claim matching**（Full Fact 等）。

---

## 2. 你的诉求 → 术语 → 用什么（落地映射）

| # | 诉求 | 术语 | 现成方案 |
|---|---|---|---|
| 1 | 搜出相关内容并排序 | Hybrid Retrieval + Rerank + RRF | RAGFlow / Onyx / LlamaIndex / Azure & Vertex AI Search；重排用 BGE-reranker-v2-m3、GTE-rerank |
| 2 | 回到原句 | Span Attribution / offset | LangExtract 式 quote→offset 锚定（你已有 span_id/offset） |
| 3 | 这句的含义 | Proposition | 你已抽取的 normalized claim |
| 4 | 相近的其他句（跨文档） | STS / ANN | span embedding（BGE-M3 / GTE）+ HNSW 近邻检索 |
| 5 | 相反的其他句（跨文档） | Contradiction Detection | NLI 模型（mDeBERTa-v3 multilingual NLI，100 语种含中文）；或 LLM verifier |
| 6 | 前一句 / 后一句 | Sentence-Window | span 节点存 `prev_id` / `next_id`；也可用 LlamaIndex SentenceWindowNodeParser |
| 7 | 出自哪一篇 | Provenance | `doc_id` + 章节 + `span_id`；W3C PROV 元数据 |

---

## 3. 参考架构（离线 + 在线）

```
【离线 · 数据层】
多篇文章
   │  语义切分（quote + offset + type + doc_id）
   ▼
┌─────────────────────────────┐      ┌──────────────────────────┐
│ 图数据库 · span 节点         │      │ 向量库 · span embedding   │
│ quote / offset / doc_id      │◄────►│ BGE-M3 / GTE（多语言）     │
│ prev_id / next_id / props    │      │ HNSW 近邻索引             │
└─────────────────────────────┘      └──────────────────────────┘
   ▲                                    ▲
   │ 图遍历（同文档/跨文档/命题关系）      │ 语义近邻（相似/相反候选）

【在线 · 检索链路】
用户查询 → 混合检索(向量 ANN + 全文) → RRF 融合 → Cross-encoder 重排 → Top-K 排序
   │
   ▼ 点开一条
   ① 回原句（offset） ② 含义（命题） ③ 相近句（ANN 近邻，跨文档）
   ④ 相反句（NLI 矛盾检测） ⑤ 前后句（prev/next 指针） ⑥ 出处（doc_id）
```

---

## 4. 开箱即用 / 大厂背书 / 开源方案清单（含 star 实况 2026-09）

### 4.1 全栈 RAG / 企业搜索（开箱即用）
| 方案 | ★ | 许可 | 备注 |
|---|---|---|---|
| **RAGFlow**（infiniflow，国内团队） | ★90.9k | Apache-2.0 | 全栈开源 RAG，内置混合检索/重排/知识库，落地最快 |
| **Onyx**（原 Danswer） | ★32.1k | 开源 | 企业级开源 AI 搜索 + RAG |
| **LlamaIndex** | ★52.2k | MIT | 组件最全：`SentenceWindowNodeParser`（前后句）、`AutoMergingRetriever`、`ParentDocumentRetriever`、`PropertyGraphIndex`（图 RAG） |
| Azure AI Search / Vertex AI Search | — | 商业托管 | 大厂托管，混合检索 + semantic ranker，免运维 |

### 4.2 图 + GraphRAG（把语义 span 存成图）
| 方案 | ★ | 许可 | 备注 |
|---|---|---|---|
| **Microsoft GraphRAG** | ★36.0k | MIT | 微软官方，社区/摘要/实体图，最主流 |
| **LightRAG**（港大） | ★39.7k | MIT | EMNLP2025，轻量快，star 最高 |
| **HippoRAG**（OSU） | ★4.0k | MIT | NeurIPS'24，海马体启发，多跳检索强 |
| **Neo4j GraphRAG**（neo4j-graphrag-python） | ★1.3k | Neo4j 官方 | 向量 + 全文 + 图遍历混合检索，官方维护 |
| **Graphiti**（Zep） | ★30.9k | Apache-2.0 | 实时**时序**知识图谱（可做"版本/时间"溯源） |
| **Cognee** | ★30.8k | Apache-2.0 | agent memory 图谱平台 |
| ArcadeDB / Neo4j | — | 开源/商业 | 作为图库底座 |

### 4.3 相似 / 相反 / 溯源
| 用途 | 方案 |
|---|---|
| 相似（embedding） | **BGE-M3**（智源，多语言+长文本）、**GTE**（阿里，多语言）、BCE/Conan |
| 排序（rerank） | **BGE-reranker-v2-m3**（智源）、**GTE-rerank**（阿里）、Cohere Rerank |
| **相反/矛盾** | **mDeBERTa-v3 multilingual NLI**（100 语种，含中文，entail/neutral/contradict 三分类）；FEVER / SciFact 范式 |
| 溯源锚定 | **LangExtract**（quote→offset）、**W3C PROV** |
| 归因评测 | **ALCE**（Attributed QA）、promptfoo RAG Source Attribution 插件 |

---

## 5. 关键提醒（这两点最容易翻车）

1. **"相反"不能用向量相似度做。** 向量近邻找的是"像"，不是"反"；"身强喜财官"和"身弱忌财官"向量上可能很近，语义却对立。正确做法：**ANN 先召回一堆"主题相近"的候选，再用 NLI/LLM verifier 判 entail / contradict / neutral**。这是两段式，不是一步到位。
2. **引用/出处会"说谎"。** 研究显示约 **50–90% 的 LLM 引用并不真正支撑其结论**（post-hoc 归因问题）。所以必须做**span 级溯源**（精确 offset），而不是让模型事后附一个看似合理的来源。

---

## 6. 针对你现有资产的选型建议

- **图库**：Neo4j + `neo4j-graphrag-python`（或 ArcadeDB）。span 节点带 `offset / doc_id / prev_id / next_id / type / props`——因为你有确定性偏移，"前后句"和"回到原句"几乎是零成本。
- **向量**：BGE-M3 或 GTE-multilingual，存 span embedding（多语言、支持长文本、中文强）。
- **重排**：BGE-reranker-v2-m3 或 GTE-rerank；多路召回的合并用 **RRF**。
- **相近句**：向量 ANN 近邻（跨文档，天然支持）。
- **相反句**：mDeBERTa 多语言 NLI 做矛盾检测；关键场景再上 LLM verifier。
- **溯源**：LangExtract 式锚定 + W3C PROV 元数据；每条结果都能回到精确字符区间。
- **想省事**：直接用 **RAGFlow** 或 **Onyx** 打底，再把 Neo4j/GraphRAG 作为图检索层接进去。
