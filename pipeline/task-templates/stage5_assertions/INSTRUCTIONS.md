# 主张提取任务说明（工位 5，全流程风险最高，规则最严）

你的唯一任务：对 input/segments.yaml 里的每个段落，提取"原文主张了什么"，一条命题一条记录，每条绑定证据。

开工前必读：pipeline/lessons/LESSONS.md 的"通用"＋"工位 5"小节；本任务包 input/ 里的 glossary.yaml（术语参照）和 editorial_notes.yaml（若有，括号内容的文层归属以它为准）。

## 铁律（违反即整条作废）

1. **只提取原文说了的**。你自己的奇门知识一个字都不许进 proposition——原文没说"天蓬凶"，就不存在这条主张。
2. **证据绑定**：每条主张的 evidence 必须引用段落编号对应的 span（映射规则：seg_id sNN → source_span_id ss_yanbo_ed02_p0001_sNN）。
3. **限定词全部进 conditions**：月令、旺衰、阴阳遁、"若/凡/惟/独/偏宜"一个都不许丢。
4. **否定方向不许反**："莫/勿/非/不可"提出来的主张必须保留否定。
5. **一条一个命题**：一句里有两个主张就拆两条。
6. 纯叙事句（如典故铺陈）没有可提取的主张 → 跳过即可，不是错误。
7. 两种读法都通 → 该段 needs_escalation，按 HANDBOOK 2.3 出 ESC 草稿放 result.yaml，继续做其他段。

## 编号

只许使用 task.yaml 里 id_range 分配的号段（assertion 与 proposition 同号段各自编号）。

## 输出格式（YAML）

```yaml
assertions:
  - assertion_id: as_qimen_000100
    proposition: 奇门以冬至、夏至为阴阳遁分界，起局宫数以一、九为始
    proposition_id: pr_qimen_000100
    relation: supports          # supports / qualifies / opposes
    evidence:
      - source_span_id: ss_yanbo_ed02_p0001_s01
        support_type: interpreted   # direct=原文明说 / interpreted=通行解读
    conditions:
      - 此为"二至还乡一九宫"的通行解读
    exceptions: []
    school_ids: []
    status: machine_extracted   # 固定填这个，禁止填更高状态
```

## 自查清单（交付前逐条过）

1. 遮住 proposition 只看证据原文——原文真的这么说了吗？
2. 限定词都进 conditions 了吗？
3. 否定方向对吗？
4. 一条里藏着两条吗？
5. support_type 里"原文明说"和"你的解读"分清了吗？
