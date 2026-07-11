# RAG_GUIDE：检索系统构建操作手册 v1.0

> 读者：负责构建/维护检索系统的 AI agent。铁律同 `AGENT_GUIDE.md`。
> 两个用途：① 给 AI 占测提供"只许引用、不许发挥"的证据；② 让任何人快速定位"典籍里的某一句话在哪本书哪一页"。
> 大原则：**检索库是派生品**——只从通过校验的 units 编译生成，可以随时删掉重建；原始真相永远在 `units/` 和 `corpus/`。

---

## 第 1 章 三层架构（先懂这张表再动手）

| 层 | 回答什么问题 | 技术 | 特点 |
|---|---|---|---|
| L1 结构层 | "天蓬星有哪些主张？""这条主张的原文出处？" | SQLite 普通表＋外键 | 精确、零幻觉、毫秒级。**占测主链路只走这层** |
| L2 全文层 | "'二至还乡'这句在哪本书哪页？" | SQLite FTS5 全文索引 | 精确到模糊之间；解决简繁体、标点差异 |
| L3 语义层 | "有没有讲'木在春天需要火'这类意思的句子？" | 向量检索（embedding） | 意思相近但用词不同时才需要；**最后才建** |

顺序铁律：**先建 L1＋L2，验证达标后才允许建 L3。** 大部分定位需求 L1/L2 就能解决；L3 成本高、结果软，只做兜底。

**双存储分工（2026-07-11 确认）**：SQLite（L1/L2）与 Zvec（L3）并存，分工按**查询类型**切、不按消费者切——精确事实（术语→主张→出处、定位原句）一律 SQLite，词条 UI 和 AI 都从这里取；相似类比（案例相似、语义近似）走 Zvec，主要供 AI。AI 证据组装顺序固定：先 SQLite 拿事实，不够再 Zvec 拿类比（§4.1）。案例库（Case）建成后其向量层落在 Zvec，检索用标量过滤（术数/盘面特征/结果/授权状态），命中案例只作类比且必须带出处。观察项：Turso（SQLite 的 Rust 重写）当前 beta 且 FTS 非 FTS5 兼容，不采用；若将来成熟，其原生向量＋FTS 或可合并双存储，届时再评估。

---

## 第 2 章 M-RAG1：构建 L1＋L2

### 步骤 1：写编译脚本 `rag/build_index.py`

行为规定：

1. 遍历 `units/` 下所有通过校验的单元（先对每个单元跑 `validators/validate.py`，FAIL 的**跳过并记录**，不许索引坏数据）；
2. 生成 `rag/index.sqlite`，表结构照抄：

```sql
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
-- 必须写入: build_time, unit_count, skipped_units, source_release(暂填 dev)

CREATE TABLE spans(
  span_id TEXT PRIMARY KEY, source_id TEXT, file TEXT,
  quote TEXT,        -- 原文原样（繁体、含标点）
  quote_norm TEXT,   -- 检索用规范形：繁转简＋去标点（转换用 opencc，禁止自写映射表）
  location TEXT);

CREATE TABLE assertions(
  assertion_id TEXT PRIMARY KEY, unit_id TEXT, proposition_id TEXT,
  proposition TEXT, relation TEXT, status TEXT,
  conditions TEXT, exceptions TEXT, school_ids TEXT);  -- 列表字段存 JSON 字符串

CREATE TABLE evidence(assertion_id TEXT, span_id TEXT, support_type TEXT);

CREATE TABLE mentions(concept_id TEXT, surface TEXT, span_id TEXT, unit_id TEXT);
-- 【数据来源规定（v1.0 勘误补充）】mentions 由 schemas/techniques/*/glossary*.yaml 的
-- seg_ids 填充：seg 序号映射到同 source_id 下的 span（_s<n> 后缀），只收已索引 span，
-- rejected 状态的术语不收。首版实现漏此表数据来源，教训：建表语句必须同时写明每张表的填充来源。

CREATE VIRTUAL TABLE spans_fts USING fts5(quote_norm, span_id UNINDEXED);
```

3. `opencc` 不可用时：blocked，不许用"自己写几个常用字映射"顶替（会漏字，实测简繁一字之差就查不到）；
4. 脚本可重复运行：每次先删旧库整体重建，**绝不增量修补**。

### 步骤 2：写查询脚本 `rag/query.py`

三个子命令，输出一律 YAML：

```
python3 rag/query.py locate "二至还乡"        # L2：定位原句 → span_id＋原文＋出处
python3 rag/query.py concept qimen.star.tianpeng   # L1：术语 → 相关主张＋各自证据
python3 rag/query.py assertion as_qimen_000001     # L1：主张 → 全部字段＋证据原文
```

`locate` 的内部顺序（固定，不许跳）：

1. 查询词做同样的规范化（繁转简＋去标点）；
2. 先精确子串匹配 `quote_norm LIKE '%...%'`；
3. 无结果 → FTS5 匹配；
4. 仍无结果 → 老实输出 `hits: []`＋一句"未找到，可能原因：不在已索引范围/用词不同（L3 未启用）"。**禁止返回"最接近的"凑数。**

### 步骤 3：验收（全部满足才算 M-RAG1 完成）

| # | 测试 | 通过标准 |
|---|---|---|
| 1 | `build_index.py` 跑两遍 | 两遍结果一致，meta 表有统计数字 |
| 2 | `locate "二至还乡"`（**简体**查询） | 命中 `ss_yanbo_ed01_p0001_s02`，返回**繁体原文**"二至還鄉一九宮"＋location |
| 3 | `locate "二至还鄉一九"`（混写＋无标点） | 同样命中 |
| 4 | `locate "天蓬落坎"`（库里没有的内容） | `hits: []`，不编造 |
| 5 | `assertion as_qimen_000001` | 返回主张全字段＋证据原文引文 |
| 6 | 故意让一个单元校验 FAIL 再重建 | 该单元被跳过且记录在 meta.skipped_units |
| 7 | `concept <已签发术语的 concept_id>` | 返回该术语的全部已索引 span（quote＋location），mentions 表非空【v1.0 勘误新增：首版验收漏测此链路】 |

---

## 第 3 章 M-RAG2：语义层 L3（L1/L2 验收后才做）

1. **嵌入什么**：每个知识单元一条向量，输入文本 = 白话释义＋术语表面形列表＋proposition 文本拼接。**不嵌原始文言**（文言语义密度太高，通用 embedding 模型效果差，这是行业实测结论）；
2. **模型**：本地用 `bge-m3`（sentence-transformers 加载）；不方便本地跑就用智谱 `embedding-3` 接口。选哪个写进 `rag/config.yaml`，换模型必须整库重嵌；
3. **存储【2026-07-11 决策修订】**：采用 **Zvec**（阿里开源的进程内嵌入式向量库，`pip install zvec`，本地落盘，无服务进程）替代原 numpy 方案。理由：标量过滤（检索时按 status/流派/来源过滤，直接服务 EvidenceBundle 组装）、dense＋sparse 混合、有 Flutter/JS SDK（将来 APP 端可内置同一索引做端上语义检索）。约束不变：Zvec 只接管 L3，L1/L2 仍是 SQLite；索引仍是可删可重建的派生品；requirements 锁定版本。**服务型向量数据库（faiss 服务、milvus、qdrant 等）仍然禁止**——不引入任何需要独立运维的进程；
4. **阈值**：相似度低于 0.5 的结果不返回（宁缺毋滥），阈值写在 config 里，调整须记录理由；
5. **输出规矩**：L3 结果必须标 `match_type: semantic`，且**永远附带 span 出处**——语义命中的也要能点回原书，做不到就不返回；
6. 验收：构造 5 条"换个说法"的查询（如用"冬至夏至换阵法"找"二至還鄉"），至少命中 3 条；5 条无关查询（如"今天天气"）全部空手而归。

---

## 第 4 章 占测链路：EvidenceBundle 的组装规程

这是 RAG 服务于"AI 占测准确率"的核心。回答模型**只能看到 bundle，不能自由检索，更不能用自带知识**。

### 4.1 组装步骤（固定顺序）

```
输入：盘面事实（结构化 concept_id 列表）＋用户问题
1. 盘面事实 → L1：每个 concept_id 查 mentions → assertions → evidence（精确，主证据）
2. 用户问题 → L2 locate（用户可能直接引了原文）
3. 仍不足 → L3 语义兜底（标记 match_type: semantic）
4. 过滤：status 为 deprecated 的丢弃；disputed 的保留但必须带争议标记
5. 分组：按 school_ids 分派系，冲突主张并列，禁止只留一派
6. 截断：每个概念最多 N 条（config 里定，默认 5），按 status 等级排序
   （cross_model_reviewed > machine_extracted > 其他）
输出：evidence_bundle.yaml
```

### 4.2 evidence_bundle.yaml 固定格式

```yaml
bundle_id: eb_<时间戳>
chart_facts: [qimen.star.tianpeng, qimen.palace.kan]
question: "（用户原话）"
evidence:
  - assertion_id: as_qimen_000001
    proposition: "……"
    conditions: ["……"]        # 条件必须原样带上，这是防"半吊子断语"的关键
    status: machine_extracted
    school_ids: []
    disputed: false
    quotes:
      - span_id: ss_yanbo_ed01_p0001_s02
        text: 二至還鄉一九宮
        location: 第1页 第2句
    match_type: exact          # exact / fulltext / semantic
conflicts:                     # 派系冲突单列，回答模型必须并列呈现
  - proposition_ids: [pr_x, pr_y]
    note: 两派对此相反
forbidden:                     # 回答模型的禁区，组装时固定写入
  - 不得输出 bundle 之外的任何术数论断
  - 不得给健康/灾祸/生死类结论
  - 每条论断后必须标注 span_id
```

### 4.3 回答后的机器复查（必须实现，不然前面白做）

写 `rag/check_answer.py`：输入 = 回答文本＋bundle。检查：

1. 回答里每个术数论断句是否带 `[ss_…]` 标注 → 没带的列出；
2. 标注的 span_id 是否真在 bundle 里 → 不在的 = 编造引用，**整个回答作废**；
3. 命中 forbidden 关键词（死、绝症、必死、破产等清单在 config）→ 作废。

输出 `pass / fail＋原因`。fail 的回答不许展示，只能重新生成或回复"依据不足"。

---

## 第 5 章 与流水线的联动规矩

- 索引重建时机：units 有新增/修订并通过校验后；**索引永远落后于 units，不许反过来**（禁止先索引再补单元）；
- 索引库带版本：meta 表记 build_time 和当时的 unit 清单哈希；占测记录里存这个哈希，出错可追溯"当时用的哪版知识"；
- `rag/` 整个目录可以随时删除重建，因此**任何人工修正都不许改索引库**，只许改 units 再重建（改库 = 下次重建就丢）。

## 第 6 章 容错

| 情况 | 动作 |
|---|---|
| 构建时某单元校验 FAIL | 跳过＋记录，继续；FAIL 比例超过 20% → blocked（上游可能坏了） |
| opencc / embedding 模型装不上 | blocked，说明缺什么。不许换"差不多的"替代品 |
| 查询无结果 | 如实返回空，附可能原因。永不凑数 |
| bundle 组不出任何证据 | 回答模型只能输出"当前知识库对此盘面无可引用依据"，这是正确行为不是失败 |
| check_answer 连续 fail 3 次 | 停止重试，记录该问题到 escalations/，人工看是不是知识缺口 |

## 第 7 章 建设顺序与当前状态

```
M-RAG1  L1+L2（SQLite＋FTS5）   ← 依赖：units 里有内容（M2 之后启动）
M-RAG2  L3 语义层（Zvec）        ← 管线可先建（任务书 briefs/MRAG2_ZVEC_BRIEF.md，验收含负例 N1–N4）；真实投产等单元数 ≥ 100
M-RAG3  EvidenceBundle＋复查器   ← 依赖：M-RAG1；与排盘引擎对接时补 chart_facts 输入
```

当前状态【2026-07-11 更新】：**M-RAG1 首版已实现并通过验收**（build_index.py / query.py / index.sqlite，locate·assertion·concept 三链路实测；mentions 空表事故已修，见第 2 章勘误）。未实现：L3 语义层、EvidenceBundle、check_answer。已知实现偏差：`concept` 子命令当前只返回术语的原文 span，尚未联结到主张（规格要求"术语→主张＋证据"）——升级 query.py 时补 `mentions→evidence→assertions` 的 JOIN。发布门槛：`source_release: dev` 的索引仅限开发使用，不得被 APP 消费；转正式需 unit 清单哈希、脚本哈希、依赖版本与 RightsGrant 完整（PIPELINE_REVIEW_v1 §P0-4）。
