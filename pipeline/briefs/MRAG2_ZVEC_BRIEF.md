# M-RAG2 任务书：Zvec 语义层（L3）编译管线

> 先读 pipeline/AGENT_GUIDE.md（含第 0 步和第五 A 节——本任务的验收强制含负例）。
> 定位：units/ 是唯一真相，本任务写的是第二条"编译器"——`units → Zvec 向量库`，与已有的
> `units → SQLite`（build_index.py）并列。库可随时删除重建，任何人工修正只改 units。
> 启用门槛：真实投产等单元数 ≥100；**现在先把管线建好并用现有数据做冒烟测试**。
> 禁止修改 corpus/、units/、validators/validate*.py、rag/build_index.py。

## 步骤 1：依赖与配置

1. `pip install zvec`（进 pipeline/.venv；装不上 → blocked，不许换其他向量库）；
2. 嵌入模型装 sentence-transformers＋`BAAI/bge-m3`；机器吃不下就先用 `BAAI/bge-small-zh-v1.5` 并在 config 里注明"冒烟用小模型，投产换 bge-m3 需整库重嵌"；
3. 写 `rag/vector_config.yaml`：

```yaml
store: zvec
collection_path: rag/vectors.zvec        # 本地落盘，可删可重建
embed_backend: sentence_transformers
embed_model: BAAI/bge-m3                 # 或冒烟小模型，见上
similarity_threshold: 0.5                # 低于此值不返回，宁缺毋滥
top_k: 5
```

4. requirements.txt 追加 zvec 与 sentence-transformers（锁版本号）。

## 步骤 2：`rag/build_vectors.py`

行为规定：

1. 遍历 units/，每个单元先跑 validate.py，FAIL 的跳过并记录（与 build_index.py 同规矩）；
2. **嵌入粒度 = 一条 assertion 一个向量**。嵌入文本按固定顺序拼接：proposition ＋ conditions 全文 ＋ 该条证据 span 的原文 quote；**不嵌 status、不嵌编号**；
3. 每条向量携带标量字段：assertion_id、proposition_id、unit_id、source_id、status、school_ids、technique_id——供检索时过滤（EvidenceBundle 的 status/流派闸门就靠它）；
4. 整库重建模式：每次运行先删除 collection 再全量重嵌，禁止增量修补；
5. 构建完写 meta（与 SQLite 的 meta 同等要求）：build_time、embed_model、向量条数、被嵌 unit 清单及各自 sha256、脚本自身 sha256。

## 步骤 3：`rag/query.py` 新增 `semantic` 子命令

```
python3 rag/query.py semantic "冬至夏至怎么换阵法" [--status cross_model_reviewed] [--school xxx]
```

固定行为：

1. 查询文本用同一模型嵌入 → Zvec 检索（应用 threshold 与标量过滤）；
2. 每条命中**必须回连出处**：用 assertion_id 到 SQLite 里取 evidence 的 span quote＋location 一并输出；取不到出处的命中丢弃不返回；
3. 输出字段固定：assertion_id、proposition、similarity（0–1 小数原样给，**禁止转成"概率/把握/准确率"类措辞**）、match_type: semantic、quotes[]；
4. 无命中时输出 `hits: []`＋一句可能原因，不凑数。

## 步骤 4：验收（正例＋负例，缺负例视为未完成）

正例：

| # | 测试 | 通过标准 |
|---|---|---|
| P1 | 连跑两次 build_vectors.py | 两次向量条数一致，meta 完整 |
| P2 | 换个说法查：如"冬至夏至换阵的规矩""五天算一个元" | 各命中对应主张，且每条带原文 quote 和 location |
| P3 | `--status cross_model_reviewed` 过滤 | 只返回该状态的条目 |

负例（每条贴命令和输出原文）：

| # | 负例 | 合格标准 |
|---|---|---|
| N1 | 查完全无关问题："今天股市怎么样""红烧肉的做法" | `hits: []`，不返回最接近的凑数 |
| N2 | 把 threshold 临时改成 0.99 再查 P2 的问题 | 返回空——证明阈值真的在生效 |
| N3 | 手工在临时副本库里造一条无 assertion_id 对应的向量再查 | 该条因回连不到出处被丢弃，不出现在结果里 |
| N4 | `--status expert_verified`（库里不存在的状态） | 返回空，不忽略过滤条件 |

## 步骤 5：汇报

新增文件清单、P1–P3 与 N1–N4 的命令＋输出原文、嵌入模型与耗时、lesson_candidates，停止。
不要做的事：不要改 SQLite 侧任何行为；不要给 semantic 结果加任何解读性文字；不要因为现有数据少而降低 threshold。
