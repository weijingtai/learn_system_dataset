# BDD：G4 第三批

## 1. r3-01 D-16 映射表

- **1.1 零删行**：Given HEAD 的 `PLAN.md`，When 执行 r3-01，Then `git diff <base> -- PLAN.md` 中没有任何以 `-` 开头的内容行（不只是未勾选项，任何行都不删不改）。
- **1.2 §19 全覆盖**：Given §19 主表 19 个首列名，Then 映射表 A 第一列逐字出现这 19 个名字各一次，且每行都有非空 owner 文件路径，该路径在仓库内存在。
- **1.3 未勾选项全标注**：Given `PLAN.md` 63 条未勾选项，Then 表 B 的 43 个「开头文字」各恰匹配 1 条 `- [ ]` 行，标注 ∈ {mapped, superseded-by, out-of-scope}；其余 20 条全部位于 G6/注解社区各节，由一句归 `out-of-scope`。
- **1.4 新增登记**：Then 新节内恰 3 条新的 `- [ ]`（Artifact Ledger、Local Orchestrator、M7），各引用 `run_all.sh 20.N` 判据；`PLAN.md` 未勾选项 63 → 66。
- **1.5 唯一 owner**：Then `pipeline/TODO.md` P2 第 1 条标「唯一登记处」，`pattern_knowledge_workbench/TODO.md`、`LEARN_SYSTEM_TARGET.md` 对应行改为引用；三文件未勾选项计数不变（15 / 23 / 0）。
- **1.6 篡改可检出**：若把表 B 任一开头文字改错一字、或删掉表 A 一行、或删掉 PLAN 任一 `- [ ]` 行，TDD §1 至少一条变红。

## 2. r3-02 前缀登记

- **2.1**：Given §8.1 第 3b 节表 3 行，When 插入两行，Then 表 5 行，`pat_<technique>_<6位数字>` 与 `ent_<32hex>` 各出现 1 次，sch_/sv_/cg_ 三行逐字不变。
- **2.2**：Then 三个门禁不变红。

## 3. 停手

锚点命中不为 1；PLAN 未勾选项基线不是 63；任一开头文字匹配数不是 1；门禁变红；对 ACT 有两种理解 → 停手上报。
