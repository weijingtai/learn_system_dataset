# G5 · G 组 Executor Prompt（文档级状态翻转；仅在用户确认进入实现阶段后派发）

你是执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复使用中文。

先完整阅读（只读）：`AGENTS.md`、`docs/blackbox-spec-rework/work-items/g5/README.md`、`act/g5-01.yaml`、`docs/blackbox-spec-rework/reviews/G5-EXIT-REVIEW.md`。

只允许写：`openspec/learn-system-blackbox-architecture.md` 第 3 行与第 5–7 行、`docs/blackbox-spec-rework/README.md` 第 5 行。其余一切禁止；工作树里其他人的未提交改动原样保留。

严格执行：

0. 前提：`README.md` §2 的「用户确认」已填日期（主 Agent 填）；`git status --short openspec/learn-system-blackbox-architecture.md docs/blackbox-spec-rework/README.md` 无输出。任一不满足停手。
1. `export LC_ALL=en_US.UTF-8`；跑三门禁记录基线（应全绿）。
2. 按 `act/g5-01.yaml`：断言五个锚点与行号；替换第 3 行；用 `new_quote` 四行替换第 5–7 行（`<日期>` 换成 README §2 填的日期）；替换 README 第 5 行。`git diff --numstat` 必须恰为规格 +5/−4、README +1/−1。
3. 运行 ACT `verify` 全部；`grep -c '^状态：'` 必须与改前相同（节标签一行未动）。
4. `git add` 两个文件后按 `commit.message` 提交。一个提交。
5. 停手规则：锚点或行号不符；numstat 不符；任一门禁变红。停止、不自行决定，把原始输出交主 Agent。

最终报告：提交 hash 与 `git show --stat --oneline`；改前/改后第 1–9 行原文；verify 全部输出；`git status --short`；一句「等待主 Agent 独立验收」。
