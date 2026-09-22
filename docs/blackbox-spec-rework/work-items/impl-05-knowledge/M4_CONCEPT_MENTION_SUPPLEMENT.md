# 被批次上限截掉的 5 个 concept_mention 词条补登记记录（W8 ACT 19 Q2）

## 1. 缺口与点名来源

M4 brief 的固定「每批 20 条」上限让两路都**顶格截断**：真书「天官」「七煞」两节
734 字 / 41 片段，a 路正好 20 条、b 路正好 20 条。b 路抽取员在 `adapter_notes` 里
**逐个点名**了因上限未登记的术语（`submission_assertion_b.yaml` /
`submission_concept_mention_b.yaml` / `submission_pattern_b.yaml` 的 `adapter_notes`
逐字相同）：

> 抽取员 notes：十神名（伤官、食神、正财、偏财、偏印、正印、劫财）亦属专门术语，
> 但受 20 条上限所限未逐一登记，仅登记天官、七煞、化禄。

**来源：b 路 adapter_notes 点名 + 主 Agent 2026-09-20 查实。**

点名 7 个术语中，**伤官、食神已由 a 路登记**
（`submission_concept_mention_a.yaml`：伤官 → `ss_qianyuan_ed01_o0008736`、
食神 → `ss_qianyuan_ed01_o0008754`），故待补登记为其余 **5 条**：
正财、偏财、偏印、正印、劫财。

## 2. 五条词条与原文出处偏移

偏移两套并列（第 104 条 D5：**M4 证据偏移沿用清洗文本坐标，片段 ID 锚原始偏移**）。
`cleaned` 出自 M3 `corpus_spans` 修订 `rev_a163a3e4162c41b48e6829e676b11b01` 的
`start_offset`/`end_offset` 与 `source_anchor`。

| 词条 | 证据片段 `source_span_id` | 术语 cleaned 偏移 | 术语 raw 偏移 | 所在片段 cleaned 偏移 | 原文 |
|---|---|---|---|---|---|
| 正财 | `ss_qianyuan_ed01_o0008772` | `[8221, 8223)` | `[8775, 8777)` | `[8218, 8236)` | 以己为正财，己之化禄为月，月即正财； |
| 偏财 | `ss_qianyuan_ed01_o0008790` | `[8239, 8241)` | `[8793, 8795)` | `[8236, 8254)` | 以戊为偏财，戊之化禄为土，土即偏财； |
| 偏印 | `ss_qianyuan_ed01_o0008808` | `[8257, 8259)` | `[8811, 8813)` | `[8254, 8272)` | 以壬为偏印，壬之化禄为计，计即偏印； |
| 正印 | `ss_qianyuan_ed01_o0008826` | `[8275, 8277)` | `[8829, 8831)` | `[8272, 8290)` | 以癸为正印，癸之化禄为罗，罗即正印； |
| 劫财 | `ss_qianyuan_ed01_o0008844` | `[8293, 8295)` | `[8847, 8849)` | `[8290, 8308)` | 以乙为劫财，乙之化禄为孛，孛即劫财； |

五条落在 **5 个相连片段**上，形态与 a 路已登记的 伤官/食神 **完全一致**
（「以X为〈十神〉，X 之化禄为 Z，Z 即〈十神〉」）——即同一段十神铺陈被上限截掉了后 5 个，
不是新抽出来的东西。

取证据的口径是裁定 100 D2 的 concept_mention 口径：**同一术语只登记一条，证据取首次
作为专门术语出现的片段**。

## 3. 查证命令与实跑输出

### 3.1 账本只读查证（逐条取偏移，不凭空写）

```bash
cd /Users/jingtaiwei/Git/Public/learn_system && export LC_ALL=en_US.UTF-8
.venv/bin/python - <<'PY'
import os, sqlite3, yaml
conn = sqlite3.connect("file:var/ledgers/qianyuan_w8/ledger.sqlite?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT r.artifact_revision_id, r.object_key FROM artifact_revisions r "
                   "JOIN artifacts a ON a.artifact_id=r.artifact_id "
                   "WHERE a.artifact_type='corpus_spans'").fetchone()
conn.close()
doc = yaml.safe_load(open(os.path.join("var/ledgers/qianyuan_w8", row["object_key"]), "rb").read().decode("utf-8"))
print("corpus_spans 修订:", row["artifact_revision_id"])
for sid in ["ss_qianyuan_ed01_o0008772", "ss_qianyuan_ed01_o0008790", "ss_qianyuan_ed01_o0008808",
            "ss_qianyuan_ed01_o0008826", "ss_qianyuan_ed01_o0008844"]:
    s = [x for x in doc["spans"] if x["span_id"] == sid][0]
    a = s["source_anchor"]
    print("%s cleaned[%d,%d) raw[%d,%d) %s" % (sid, s["start_offset"], s["end_offset"], a["raw_start"], a["raw_end"], s["text"]))
PY
```

实跑输出（逐字）：

```
corpus_spans 修订: rev_a163a3e4162c41b48e6829e676b11b01
ss_qianyuan_ed01_o0008772 cleaned[8218,8236) raw[8772,8790) 以己为正财，己之化禄为月，月即正财；
ss_qianyuan_ed01_o0008790 cleaned[8236,8254) raw[8790,8808) 以戊为偏财，戊之化禄为土，土即偏财；
ss_qianyuan_ed01_o0008808 cleaned[8254,8272) raw[8808,8826) 以壬为偏印，壬之化禄为计，计即偏印；
ss_qianyuan_ed01_o0008826 cleaned[8272,8290) raw[8826,8844) 以癸为正印，癸之化禄为罗，罗即正印；
ss_qianyuan_ed01_o0008844 cleaned[8290,8308) raw[8844,8862) 以乙为劫财，乙之化禄为孛，孛即劫财；
```

### 3.2 生成（机械走完「点名 → 出处」全链）

```bash
python3 pipeline/tools/supplement_m4_concept_mentions.py              # 落盘
python3 pipeline/tools/supplement_m4_concept_mentions.py --check-only # 只核对

# 等价写法（两种调用方式输出一致，均已实跑核对）：
python3 -m pipeline.tools.supplement_m4_concept_mentions --check-only
```

实跑输出（逐字）：

```
点名条来自: submission_assertion_b.yaml
点名术语: 伤官、食神、正财、偏财、偏印、正印、劫财
已在提交件登记: 伤官、食神
待补登记: 5 条 -> 正财、偏财、偏印、正印、劫财
  正财  ss_qianyuan_ed01_o0008772  cleaned[8221,8223)  raw[8775,8777)  以己为正财，己之化禄为月，月即正财；
  偏财  ss_qianyuan_ed01_o0008790  cleaned[8239,8241)  raw[8793,8795)  以戊为偏财，戊之化禄为土，土即偏财；
  偏印  ss_qianyuan_ed01_o0008808  cleaned[8257,8259)  raw[8811,8813)  以壬为偏印，壬之化禄为计，计即偏印；
  正印  ss_qianyuan_ed01_o0008826  cleaned[8275,8277)  raw[8829,8831)  以癸为正印，癸之化禄为罗，罗即正印；
  劫财  ss_qianyuan_ed01_o0008844  cleaned[8293,8295)  raw[8847,8849)  以乙为劫财，乙之化禄为孛，孛即劫财；
写出: var/ledgers/qianyuan_w8_review/m4_concept_mention_supplement.yaml（4515 字节）
sha256: 87702ee3d66f5f5f4d6fff17f13ce0b9b90b94c7c8a2ed09973127085ba9f457
```

脚本不写死这 5 个词条：术语表从点名条括号内解析，再减去六份提交件
`items[].surface` 的去重并集，差集即待补条目。**点名条若不存在、或某词条在 41 段内
取不到确切出处，脚本打印 `REFUSED …`、退出码 1 且不落盘**（ACT 19 on_fail ①）。

## 4. 硬性口径核对

| 硬性要求 | 本件做法 |
|---|---|
| 每条必须带原文出处偏移；不许凭空写 | 每条都有 cleaned + raw 两套偏移 + 所在片段偏移 + `quote`；全部来自账本只读查证（§3.1） |
| **不许推断 `concept_refs`**（裁定 107 Q-M8-01） | 产出件**不含**任何 `concept_refs` 键（已核：`'concept_refs' in dump == False`）。要出 Concept 词条与引用，须由用户在 M6 审核表里显式 `modify` 补写 |
| 标注来源 | 产出件头部与 §3.2 输出均标「来源：b 路 adapter_notes 点名 + 主 Agent 2026-09-20 查实」 |
| **不许改真书正本账本** `var/ledgers/qianyuan_w8/` | 账本以 sqlite `mode=ro` 打开，只读查询；`git status --short var/ledgers/qianyuan_w8/` 无输出。六份已封存提交件的 `items` 与 sha256 一律未动 |
| 补登记落在 review 目录 | 产出落在 `var/ledgers/qianyuan_w8_review/` |

## 5. 产物位置与版本库边界

| 路径 | 是否入版本库 | 说明 |
|---|---|---|
| `pipeline/tools/supplement_m4_concept_mentions.py` | **是**（本件） | 可复算生成脚本；只读账本与提交件 |
| `docs/blackbox-spec-rework/work-items/impl-05-knowledge/M4_CONCEPT_MENTION_SUPPLEMENT.md` | **是**（本件） | 本记录 |
| `var/ledgers/qianyuan_w8_review/m4_concept_mention_supplement.yaml` | **否** | 生成物（sha256 `87702ee3…`），落在运行时账本区；`.gitignore:16` 已排除整个 `var/` |

按主 Agent 2026-09-21 裁决：**`var/` 下一律不入库**，本项交付物 = 可复算脚本 + 本记录。

## 6. 本件**不是**什么

- 不是对 M4 提交件的修改：六份提交件一字未动（它们的 sha256 记在 `m4/SHA256SUMS`，
  且是既成事实——抽取员当时确实漏登记了，如实留档即可）。
- 不是人工审核结论：本件登记的是 `machine_extracted` 工作数据；是否采纳、是否补
  Concept 引用，由用户本人决定（P7，第 104 条 D1）。
- 不解决上限本身：上限的修复在 ACT 19 Q1（brief 模板 v2.1 改自适应上限），本件只是
  把**已经发生**的截断如实补登记出来。
