# impl-01 · H3 返工 Prompt（ACT 06：宿主准备失败必须是 FAIL）

你是执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`（HEAD 祖先必须含 `45d99a1`）。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复、注释、docstring 使用中文。

背景：你交付的 ACT 03/04/05 已验收通过，主 Agent 只发现一处：`pipeline/ledger/acceptance.py` 在灌入或判定抛异常时返回退出码 3，`run_all.sh` 会把它显示成 BLOCKED，从而把 Ledger 的真实回归藏成「前置缺失」。细节与规则见 `docs/blackbox-spec-rework/work-items/impl-01-ledger/act/06.yaml`。

只允许写：`pipeline/ledger/acceptance.py`、`pipeline/ledger/tests/test_acceptance.py`。禁止改 `run_all.sh` 与其他任何文件；工作树里其他人的未提交改动原样保留。

严格执行：

0. 开工前提：`git status --short pipeline/ledger openspec/acceptance` 无输出。
1. `export LC_ALL=en_US.UTF-8`。
2. 先在 `tests/test_acceptance.py` 追加 `tests` 列出的两个用例（名称逐字），运行 `.venv/bin/python -m unittest discover -s pipeline/ledger/tests -t .` 记录 Red 原文。
3. 按 `contract.exit_codes` 改 `acceptance.main`：退出码 3 只留两处，其余异常一律打印原有 FAIL 行后返回 1；同步模块头部退出码说明。
4. 运行 ACT `verify` 全部与 TDD §3 回归。
5. `git add pipeline/ledger/acceptance.py pipeline/ledger/tests/test_acceptance.py` 后按 `commit.message` 提交。一个提交。
6. 停手规则：Red 不是「返回 3 ≠ 1」；需要改 scope 外文件；`run_all.sh` 结果不再是 `pass=2 fail=1 blocked=8`；任一门禁变红。停止、不自行决定，把原始输出交主 Agent。

最终报告：提交 hash 与 `git show --stat --oneline`；Red 原文；Green 末三行；verify 各项输出；`git status --short`；一句「等待主 Agent 独立验收」。
