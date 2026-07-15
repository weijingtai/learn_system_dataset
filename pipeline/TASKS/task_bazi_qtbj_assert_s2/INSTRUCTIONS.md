# 主张提取任务说明（工位 5·八字专版，全流程风险最高、规则最严）

你的唯一任务：对 input/segments.yaml 里的每个段落，提取"原文主张了什么"，一条命题一条记录，每条绑定证据。

开工前必读：`pipeline/lessons/LESSONS.md` 的"通用"＋"工位 5"小节；本任务包 input/ 里的 `glossary_v0.yaml`（术语参照，命中就用其 concept_id）。

## 铁律（违反即整条作废）

1. **只提取原文说了的**。你自己的八字知识一个字都不许进 proposition——原文没说"甲木见庚为杀主刚断"，就不存在这条主张。
2. **⚠ 命例必须排除（本工位头号风险）**：`input/segments.yaml` 里 `case_candidate: true` 的段是**命造举例**（某人某盘的断验、"如某命…主大贵"之类），**不提取为主张**，一律放进 `skipped_segments` 并注明 `reason: case_example`。把命例当通则会污染整个知识库——这是章程第 2 条的核心，宁可漏提不可错提。
3. **证据绑定**：每条主张的 evidence 必须引用段落对应的 span（映射：seg_id sNN → source_span_id 用 input/spans.yaml 里该段的 span_id，形如 ss_qtbj_ed01_p0001_s01）。
4. **限定词全部进 conditions**：月令（"正月""三冬"）、旺衰、"若/凡/惟/独/偏宜/最忌"一个都不许丢。八字的断语高度依赖月令与配置，丢了就错。
5. **否定方向不许反**："莫/勿/非/不可/最忌/怕"提出来的主张必须保留否定。
6. **一条一个命题**：一句里有两个主张就拆两条（如"用丙，佐以壬"是两条：取丙为用、以壬为佐）。
7. 纯叙事/铺陈句没有可提取的主张 → 放 skipped_segments，reason: narrative，不是错误。
8. 两种读法都通 → 该段 needs_escalation，出 ESC 草稿放 result.yaml，继续做其他段。

## 编号
只用 task.yaml 里 id_range 分配的号段，assertion 与 proposition 同号段各自编号。

## 输出格式（YAML）

```yaml
assertions:
  - assertion_id: as_bazi_000001
    proposition: 正月甲木取丙火为用神，以解余寒
    proposition_id: pr_bazi_000001
    relation: supports          # supports / qualifies / opposes
    evidence:
      - source_span_id: ss_qtbj_ed01_p0001_s02
        support_type: direct    # direct=原文明说 / interpreted=通行解读
    conditions:
      - 正月（寅月）
      - 用于余寒未除之时
    exceptions: []
    concept_ids: [co_bazi_000xxx]   # 命中 glossary 的术语填其 id，没有留空
    status: machine_extracted   # 固定填这个，禁止填更高状态
skipped_segments:
  - seg_id: s03
    reason: case_example        # case_example / narrative
```

## 自查清单（交付前逐条过）
1. **case_candidate 的段我全放进 skipped 了吗？**（头号检查）
2. 遮住 proposition 只看证据原文——原文真的这么说了吗？
3. 月令/旺衰等限定词都进 conditions 了吗？
4. 否定方向对吗？
5. 一条里藏着两条吗？
6. 每段都有交代吗（要么出主张、要么进 skipped）？
