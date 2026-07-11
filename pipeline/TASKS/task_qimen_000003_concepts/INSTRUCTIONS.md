# 术语候选提取任务说明（用于术语表尚不存在时的初版建立）

你的唯一任务：从输入的切分段落里，找出所有**术数专用词**，登记为候选清单。

## 什么算术语（只认这五类）

1. 星：如天蓬、天任一类星名；
2. 门：如开门、休门一类门名；
3. 神：如值符、太阴、六合一类神煞名；
4. 干支与遁：天干地支、阳遁阴遁、三奇六仪一类；
5. 格局/法诀名：如地遁、天三门一类有专名的格局或方法。

普通文言词（如"妙难穷""一掌中"）不是术语。拿不准的照样登记，但 `sure` 填 false。

## 硬性规矩

- surface 必须与段落原文**逐字一致**（复制粘贴）；
- 你只登记"哪个词在哪些段出现"，**禁止解释词义**（那需要证据，是后续工位的事）；
- 同一个词出现多段 → 一条记录，seg_ids 列全；
- 禁止用你自己的奇门知识补充段落里没出现的术语。

## 输出格式（YAML）

```yaml
candidates:
  - surface: 值符
    kind_guess: god        # star / door / god / stem_branch_dun / pattern / other
    seg_ids: [s56, s57]
    sure: true
  - surface: 天三门
    kind_guess: pattern
    seg_ids: [s25]
    sure: true
```

## 切分粒度与经验

开工前读 pipeline/lessons/LESSONS.md 的"通用"与"工位 4"小节。发现新经验写进 result.yaml 的 lesson_candidates。
