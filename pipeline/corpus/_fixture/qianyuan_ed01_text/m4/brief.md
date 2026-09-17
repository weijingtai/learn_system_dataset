# 《乾元秘旨》「天官」「七煞」两节 · 知识候选独立抽取任务 v2（W8 8.2，第 100 条 D4、第 104 条 D2）

你是古籍术数（七政四余）知识抽取员。**只做一件事**：读下面给定的片段清单，按格式产出结构化知识候选。全程中文。

## 铁律

1. **只读** `spans_tianguan_qisha.yaml`（同目录）。不要读任何其他文件、不要看代码仓库、不要上网、不要看另一路抽取员的结果（你不知道也不应知道它在哪）。
2. **只抽原文明说的内容**，不补充原文没有的术数常识，不做推演。拿不准的宁可不抽。
3. 每条候选必须有证据：**以整个片段为单位**引用——证据只写 `source_span_id` 与 `support_type` 两个键，**不要**写 `quote`、`span_char_start`、`span_char_end`。一条候选需要多个片段时，按片段在清单中的先后顺序排列，只列必要的片段。
4. 候选总数（三类合计）**不超过 20 条**。
5. 不写任何「审核结论」「可信度」「建议接受」之类的字段——审核由用户本人做。

## 三类候选（只抽这三类；不抽 school_view）

### assertion（论断）
一条可独立成立的规则或判断，如「甲年生人以辛为官」。
```yaml
- proposition: <用原文用字概括的一句论断，尽量贴近原文>
  relation: supports        # 闭集 supports / qualifies / opposes / corresponds / equivalent；一般用 supports；是限定条件用 qualifies；是对应关系（甲↔辛）用 corresponds
  evidence:
  - {source_span_id: ss_qianyuan_ed01_o00xxxxx, support_type: direct}
  conditions: []            # 可选：原文明说的成立条件，每条一句
  exceptions: []            # 可选：原文明说的例外
  layer: general            # 闭集 general（通则）/ case（命例）/ editorial（注文、校勘、作者按语）
```
`support_type`：原文字面直接说了 → `direct`；需要把两三句合起来才成立 → `interpreted`。

### pattern（格局）
原文把若干论断组合成一个有名目的格局/取用法（如某种「制化」格）时才抽；没有明确名目不要硬造。
```yaml
- name: <原文里的格局名>
  assertion_propositions: [<引用你上面 assertion 的 proposition 原句，逐字一致>]
  evidence:
  - {source_span_id: ..., support_type: direct}
```

### concept_mention（术语提及）
原文中作为专门术语使用的词（如 天官、七煞、化禄）。同一术语只登记一条，证据取首次作为术语出现的片段。
```yaml
- surface: <术语原文用字>
  evidence:
  - {source_span_id: ..., support_type: direct}
```

## 产出

写一个 YAML 文件（路径见你的派发说明），顶层结构：
```yaml
lane: <a 或 b，见派发说明>
model: <你的模型名，见派发说明>
assertion: [ ... ]
pattern: [ ... ]
concept_mention: [ ... ]
notes: [ <可选：你跳过了哪些片段、为什么，每条一句> ]
```
写完后自查（用脚本核对，贴出结果）：每个 `source_span_id` 都在清单里；证据键只有 `source_span_id`/`support_type`；多证据按清单顺序；`pattern.assertion_propositions` 逐字等于本文件某条 assertion 的 proposition；某类没有候选时写空列表 `[]`；总数 ≤ 20。然后停止。
