# G4 第二批 · E 组返工 Prompt（r2-03 一处：run_all.sh 一律调用规范 verify.sh）

你是执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`（HEAD 祖先必须含 `4884b6a`）。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复、注释与文档使用中文。

背景：你在 `4884b6a` 交付的 `openspec/acceptance/run_all.sh` 判据全部通过，主 Agent 只对 `fx()` 一处裁定返工。裁定原文见 `docs/blackbox-spec-rework/work-items/g4-r2/ACCEPTANCE.md` §5.1 第 3 条与 `act/r2-03.yaml` 的 `script_spec` fixture 子检查行（已改）。

只允许写：`openspec/acceptance/run_all.sh`。其余一切路径禁止写入；工作树里其他人的未提交改动原样保留。

严格执行：

0. 开工前提：`git status --short openspec/acceptance openspec/learn-system-blackbox-architecture.md` 必须无输出，否则停手报告。
1. `export LC_ALL=en_US.UTF-8`；先跑 `bash openspec/acceptance/run_all.sh; echo exit=$?` 记录改前基线（应为 11 行 + SUMMARY、exit 1）。
2. 改 `fx()`：一律执行 `bash "$REPO_ROOT/pipeline/corpus/_fixture/mini_ed01/verify.sh"`，以环境变量 `FIXTURE_DIR`（已解析为绝对路径）透传被验目录；删除「先跑 `$FIXTURE_DIR/verify.sh`、`BLOCKED_ENV` 时回退」的整段分支及其注释；规范脚本不存在 → `BLOCKED  20.N  前置缺失: M3 Corpus Compilation；fixture 缺失`（行名逐字不变）。除 `fx()` 外的任何行不改。
3. 验证（全部原文贴入报告）：
   - TDD §3 全部判据（`docs/blackbox-spec-rework/work-items/g4-r2/TDD.md` §3），预期与改前一致：11 行、`SUMMARY pass=0 fail=1 blocked=10`、exit 1。
   - 副本删一个 span：`FIXTURE_DIR=<副本> bash openspec/acceptance/run_all.sh 20.1` → `FAIL  20.1`。
   - 未篡改副本：同命令 → `BLOCKED  20.1`。
   - 新增对照：把副本自带的 `verify.sh` 整个替换为只有一行 `echo FIXTURE OK` 的脚本，且副本删一个 span，再跑 `20.1` → 必须仍为 `FAIL  20.1`（证明副本脚本从未被信任）。
   - `grep -c 'FIXTURE_DIR/verify.sh' openspec/acceptance/run_all.sh` → 0。
   - TDD §4 回归：`verify-T.sh` 0 FAIL、`mutations.sh all` 109/109、`schemas/verify.sh` exit 0、`git diff --check`。
4. `git add openspec/acceptance/run_all.sh` 后提交，信息：`fix(D-18): run_all.sh always uses canonical fixture verify.sh (never trusts copy's script)`。一个提交。不得 `git add -A` / `git add .`。
5. 停手规则：任一验证值不符；任一门禁变红；需要改 `fx()` 以外的行才能通过。一律停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定。

最终报告必须包含：提交 hash 与 `git show --stat --oneline`；改前基线；第 3 步每项输出原文与退出码；`git status --short`；以及一句「等待主 Agent 独立验收」。
