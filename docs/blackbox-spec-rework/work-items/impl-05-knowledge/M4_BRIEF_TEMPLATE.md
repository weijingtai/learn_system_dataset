# M4 抽取任务书模板 · 协议 v2.1（W8 ACT 19 Q1；承接第 100 条 D4、第 104 条 D2）

本文件是 M4（`pipeline.knowledge_extraction`）跨模型独立抽取所用**任务书（brief）的
权威模板**。派发时按本模板逐批实例化，实例文件与片段清单一同交给抽取员。

- **协议 v2**（第 104 条 D2，本模板逐字沿用其铁律与三类候选格式）：证据以**整个片段**
  为单位，只写 `source_span_id` 与 `support_type`。
- **协议 v2.1**（本模板的唯一改动，ACT 19 Q1）：把每批候选总数的**固定上限 20 条**改为
  **自适应上限 = `ceil(1.2 × 该批片段数)`**，并在铁律中要求「因上限略去任何候选必须
  在 `adapter_notes` 中逐条点名」。
- 已发出的实例 `pipeline/corpus/_fixture/qianyuan_ed01_text/m4/brief.md`（v2）**不改**：
  它是入库夹具，sha256 `c3e72bd4a9482258a6868322f371ec1b8993ca24099bb88f5143e7d538bf295e`
  记在 `m4/README.md` 与 `m4/SHA256SUMS`，且是六份提交件 `producer.prompt_sha256` 的取值。
  v2.1 只约束**此后**新派发的批次，不追溯已封存的抽取件（不重跑 M4）。

改动理由：实测 `${work}「天官」「七煞」` 两节一片 734 字 / 41 片段，两路都**顶格截断**
在 20 条，b 路 `adapter_notes` 自述「为控总数略去」「受 20 条上限所限未逐一登记」，造成
真实漏抽（5 个 `concept_mention` 词条）。固定上限对论断密集的短批次必然截断；自适应上限
随片段数伸缩，并对不可避免的截断强制留痕，使截断可被下游检出（见本批 Q3）。

---

## 模板正文（占位符以 `⟨…⟩` 标注，派发时替换）

# ⟨书名⟩⟨节名⟩ · 知识候选独立抽取任务 v2.1（第 100 条 D4、第 104 条 D2）

你是古籍术数（⟨technique⟩）知识抽取员。**只做一件事**：读下面给定的片段清单，按格式产出结构化知识候选。全程中文。

## 铁律

1. **只读** ⟨片段清单文件名⟩（同目录）。不要读任何其他文件、不要看代码仓库、不要上网、不要看另一路抽取员的结果（你不知道也不应知道它在哪）。
2. **只抽原文明说的内容**，不补充原文没有的术数常识，不做推演。拿不准的宁可不抽。
3. 每条候选必须有证据：**以整个片段为单位**引用——证据只写 `source_span_id` 与 `support_type` 两个键，**不要**写 `quote`、`span_char_start`、`span_char_end`。一条候选需要多个片段时，按片段在清单中的先后顺序排列，只列必要的片段。
4. **候选总数（三类合计）上限 = `ceil(1.2 × 本批片段数)`**，即 ⟨按本批 N 个片段算出：`ceil(1.2 × N) = M` 条⟩。
   - 该上限是**预算**不是目标：够不着就如实少抽，**不要**为凑数拆分或重复登记。
   - **因上限略去任何候选，必须在 `adapter_notes` 中逐条点名**：略去的对象（片段 ID 或术语/论断原文用字）、所属类别、一句话理由（如「与已抽某条义近」「属命例性铺陈」「仅一句且属附带」）。**没有逐条点名的截断视为违规提交**。
5. 不写任何「审核结论」「可信度」「建议接受」之类的字段——审核由用户本人做。

## 三类候选（只抽这三类；不抽 school_view）

### assertion（论断）
一条可独立成立的规则或判断，如「甲年生人以辛为官」。
```yaml
- proposition: <用原文用字概括的一句论断，尽量贴近原文>
  relation: supports        # 闭集 supports / qualifies / opposes / corresponds / equivalent；一般用 supports；是限定条件用 qualifies；是对应关系（甲↔辛）用 corresponds
  evidence:
  - {source_span_id: ⟨前缀⟩_o0000000, support_type: direct}
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
写完后自查（用脚本核对，贴出结果）：每个 `source_span_id` 都在清单里；证据键只有 `source_span_id`/`support_type`；多证据按清单顺序；`pattern.assertion_propositions` 逐字等于本文件某条 assertion 的 proposition；某类没有候选时写空列表 `[]`；总数 ≤ 本批上限；**若因上限略去候选，`notes` 里已逐条点名**。然后停止。

---

## 实例化注意（给派发者，不进抽取员可见正文）

1. `⟨片段清单文件名⟩` 与派发路径必须与实际文件名一致；片段清单只含本批片段，
   `source_span_id` 前缀与清单内 ID 逐字一致。
2. 上限按**本批**片段数算，不按全书算：`ceil(1.2 × 41) = 50`（该批实测上限），
   `ceil(1.2 × 10) = 12`。上限值写进正文时把算式与结果一并写出，便于抽取员自查。
3. 抽取员**只读片段清单**，不得读 `pipeline/**`（第 104 条 D2 的盲抽前提）。
4. 抽取件与提交件的差别由 Adapter 机械转换（`adapters/task_pipeline.py`），
   任务书里不要替抽取员写提交件契约字段。
