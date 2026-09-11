# BDD：G5 文档级状态翻转

- **1 前提**：Given `reviews/G5-EXIT-REVIEW.md` 14 条准出条件中前 13 条已有证据、第 14 条「用户确认进入实现阶段」已填日期，When 派发 g5-01，Then 才允许执行；否则执行者停手。
- **2 只改头部**：When 执行，Then 规格 `--numstat` 恰 +3/−2、README +1/−1；`grep -c '^状态：'` 改前改后相同；三门禁不变。
- **3 不越级**：Then 规格中不出现 `最终规范` 作为节状态（T-13b 仍 PASS）；新状态词是 `R1_REWORK_CLOSED` 而非 `ACCEPTED`。
- **4 可回溯**：Then 头部引用块仍保留 R1 审查日期与 PLAN 节指针，并新增准出日期与证据路径。
