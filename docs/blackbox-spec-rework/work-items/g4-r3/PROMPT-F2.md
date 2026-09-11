# G4 第三批 · F 组返工 Prompt（r3-03：check_d16.py R3 兼容已勾选行）

你是执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`（HEAD 祖先必须含 `e306258`）。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复、注释与文档使用中文。

背景：你交付的 `76bc4b4` / `e306258` 已验收通过。主 Agent 随后按验收结论勾选了 PLAN.md 中 21 条 `superseded-by` 条目，导致 `check_d16.py` 的 R3（只数 `- [ ] <开头>`）在 HEAD 上误报。这是主 Agent 当初 checker 规则的缺陷，不是你的错。改动细节见 `docs/blackbox-spec-rework/work-items/g4-r3/act/r3-03.yaml`。

只允许写：`docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py`。禁止改 `PLAN.md` 与其他任何文件；工作树里其他人的未提交改动原样保留。

严格执行：

0. 开工前提：`git status --short docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py PLAN.md` 无输出。
1. `export LC_ALL=en_US.UTF-8`；先跑 `python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py; echo exit=$?` 记录 Red 原文（应为 `D16 FAIL R3 …`，exit 1）。
2. 按 `act/r3-03.yaml` 的 `rule_change` 修改 R3 与 R4 的匹配逻辑；不改其他规则、不改输出格式、不加 try/except。
3. 验证：`check_d16.py` → `D16 OK` exit 0；ACT `verify` 三例篡改自检各得预期结果（原文贴报告）；`git diff --check`。
4. `git add docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py` 后按 `commit.message` 提交。一个提交。
5. 停手规则：Red 不是 R3；改 R3/R4 以外才能过；对 rule_change 有两种理解。停止、不自行决定，把原始输出交主 Agent。

最终报告：提交 hash 与 `git show --stat --oneline`；Red/Green 原文；三例自检输出；`git status --short`；一句「等待主 Agent 独立验收」。
