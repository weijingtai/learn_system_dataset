# G4 第二批 · E 组 Executor Prompt（r2-03 §20 判据化 + run_all.sh）

前置：D 组两个提交必须已在 HEAD 祖先中（`ls pipeline/corpus/_fixture/mini_ed01/verify.sh` 存在，且 `bash pipeline/corpus/_fixture/mini_ed01/verify.sh` 末行 `FIXTURE OK`）。不满足则停手报告，不要自己去做 D 组的事。

你是执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复、注释与文档使用中文。

先完整阅读（只读）：`AGENTS.md`、`docs/blackbox-spec-rework/work-items/g4-r2/README.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/r2-03.yaml`、`pipeline/corpus/_fixture/mini_ed01/README.md` 与 `verify.sh`、规格 §19 主表第一列（BLOCKED 行名只能逐字取自那里）与 §20。

只允许写：`openspec/acceptance/run_all.sh`（新建）与 `openspec/learn-system-blackbox-architecture.md` 的 §20。其余一切路径禁止写入；工作树里其他人的未提交改动原样保留。

严格执行：

0. 开工前提：`git status --short openspec/learn-system-blackbox-architecture.md openspec/acceptance` 必须无输出（若已有他人未提交改动，你的 `git add` 会把它们一并带进提交）。有输出即停手报告。
1. `export LC_ALL=en_US.UTF-8`。运行 TDD §0 基线（祖先检查改为 D 组第二个提交的 hash）与 TDD §3 Red（`run_all.sh` 不存在 exit 127；§20 无「判据：」）。
2. 按 `act/r2-03.yaml`：断言三处锚点与 §20 恰 11 条；插入 `intro_paragraph`；第 7 条整行替换为 `item7_replacement`；11 条各在行末追加判据（编号必须与条目一致，条目原文一个字不改）；新建 `run_all.sh`，`script_spec` 的每条规则原样实现——能在 fixture 上判定的先判定，其余按规定输出 `BLOCKED  20.N  前置缺失: <§19 行名>；<说明>`，绝不把不可判定项写成 PASS。
3. 验证：TDD §3 全部 Green 值。当前 HEAD 的预期结果是 `20.7` 为 `FAIL`（0/496）、其余 10 条 `BLOCKED`、`SUMMARY pass=0 fail=1 blocked=10`、退出码 1；临时副本 fixture 删除一个 span 后 `FIXTURE_DIR=<副本> bash openspec/acceptance/run_all.sh 20.1` 必须变为 `FAIL  20.1`。然后 TDD §4 回归。
4. `chmod 755 openspec/acceptance/run_all.sh`；`git add openspec/acceptance/run_all.sh openspec/learn-system-blackbox-architecture.md` 后按 `commit.message` 提交。一个提交。不得使用 `git add -A` 或 `git add .`。
5. 停手规则：锚点命中不为 1；§20 不是 11 条；fixture verify 不是 `FIXTURE OK`；任一门禁变红；某条规则无法按 `script_spec` 实现；对 ACT 有两种理解。一律停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定。

最终报告必须包含：提交 hash 与 `git show --stat --oneline`；基线与 Red 输出；`run_all.sh` 全量输出原文（11 行 + SUMMARY）与退出码；`run_all.sh 20.7` 输出；篡改 fixture 后 `20.1` 的输出；TDD §3 各计数；TDD §4 回归；`git status --short`；以及一句「等待主 Agent 独立验收」。
