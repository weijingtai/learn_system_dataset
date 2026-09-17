# 乾元秘旨（电子文本）M4 提交件宿主（W8 8.2，第 100 条 D4、第 104 条 D1–D3）

本目录是《乾元秘旨》**电子文本**路线（`offset_level`）的 M4 候选提交件宿主：
六份提交件由**两个不同厂商的 AI 独立盲抽**、经主 Agent **机械转换**而成，
供 M4（`pipeline.knowledge_extraction`）在 Ledger 上实跑消费。

## 来源与抽取范围

- 原文：本 fixture 根目录 `qianyuan_ed01_text.md`（逐字节原样，sha256
  `3f7170cd504e496096bc933ab5ed8805d68fa98625c91c5c09a9e3a61fcecdbb`），
  见 `../source_info.yaml` 与 `../expected/m1_source_expected.yaml`（第 95、101 条）。
- 抽取范围：**连续两节正文**「天官」「七煞」，**RawText（原始文本）字符偏移
  [8663, 9397)**；对应 M3 导出的 **41 个片段**（片段清单
  `spans_tianguan_qisha.yaml` sha256
  `b4240c748ca0cc0883980328d01e4c06effeef7f99bd6924724fea747f9e4cd7`）。
- 抽取任务书 `brief.md`（协议 v2）sha256
  `c3e72bd4a9482258a6868322f371ec1b8993ca24099bb88f5143e7d538bf295e`
  （即六份提交件 `producer.prompt_sha256` 的取值）。

## 抽取协议 v2（第 104 条 D2）

**证据以整个片段为单位**：每条证据只写 `source_span_id` 与 `support_type` 两个键，
**不写** `quote` / `span_char_start` / `span_char_end`——M4 `locate_evidence`
（`pipeline/knowledge_extraction/assemble.py:54-91`）对无区间无引文的证据即取整个片段。
一条候选需要多个片段时按片段在清单中的先后顺序排列，只列必要的片段。

v2 取代 v1：v1 允许自由截取引文，导致两路证据键（片段 + 区间）无法对齐、35 条分歧里
几乎全是「引文起止差一个标点」；v1 产出已作废存档，不入库。

## 两路模型（互不可见）

| 路 | 模型 | `producer.name` | 抽取件 sha256（`response_sha256`） | 提交件（条数） |
|---|---|---|---|---|
| a | `claude-sonnet-5` | `w8_lane_a` | `d9b7d66060930d0ea45c896c06ae6d342aba3f871961638e6b1f7d128796ecd9` | `submission_assertion_a.yaml`（13）、`submission_pattern_a.yaml`（0）、`submission_concept_mention_a.yaml`（7） |
| b | `deepseek/deepseek-v4.1-flash` | `w8_lane_b` | `8c14e641ffd41bfe888d29e980c17f207f0751d98a4e5257a3f43cd055d5401d` | `submission_assertion_b.yaml`（15）、`submission_pattern_b.yaml`（2）、`submission_concept_mention_b.yaml`（3） |

两路抽取员**互不可见、不读 `pipeline/**` 任何代码**，只读片段清单；每类候选合计
不超过 20 条（brief 铁律）。

**空类别如实提交**（第 104 条 D3）：a 路两节内未见原文明说的、带专门名目的格局，
`submission_pattern_a.yaml` 以 `items: []` 如实提交（「看过、没有」≠「没提交」）。

## 提交件性质

- `channel: task_pipeline_manual`、`producer.kind: external_agent`、`status` 缺省
  （即 `null`，M4 据此以 `machine_extracted` 入库）。
- 六份提交件的 `items` **一字未改**（机械转换只把抽取件顶层结构映射到提交件契约）。
- **内容为 AI 抽取的 `machine_extracted` 候选，未经人工审核**；不得进入任何
  `expert_verified` 判定（P7/§5）。**分歧裁决由用户本人填写**（第 104 条 D1）。

## 本目录**不含**的两类文件（有意为之）

- **无 `ruling_*.yaml`**：规格 §12:572「未解决语义分歧进入人工队列，**不能通过 M4
  Gate**」——M4 分歧必须由**用户本人**裁决后方能 `resume_m4` 封存（第 104 条 D1）。
  主 Agent 只生成空白裁决表，本宿主不带任何裁决件。
- **无 `candidate_set.yaml` 金标**：没有人工金标，不得以被测实现自身输出充当金标
  （第 95 条反自证）。

## SHA256SUMS

`SHA256SUMS` 覆盖 `brief.md` 与六份提交件（不含 `README.md` 自身——无法自哈希），
条目路径**相对本 fixture 目录**（即 `m4/...`，与 OCR 路线 `mini_ed01/m4/SHA256SUMS`
同口径），按路径排序；校验在 fixture 根目录执行：

```bash
cd pipeline/corpus/_fixture/qianyuan_ed01_text && shasum -a 256 -c m4/SHA256SUMS
```
