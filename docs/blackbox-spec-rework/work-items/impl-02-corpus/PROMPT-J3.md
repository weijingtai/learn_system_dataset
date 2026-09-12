# impl-02 · J3 返工 Prompt（ACT 05：冻结输入完整性、终态严格比对、begin 后异常封存、缺 fixture 退出码）

你是执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`（HEAD 祖先必须含 `ea9126d`）。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复、注释、docstring 使用中文。

背景：主 Agent 独立验收 J2（`f4f4682`、`ea9126d`）时发现五处缺陷，全部写在 `docs/blackbox-spec-rework/work-items/impl-02-corpus/act/05.yaml` 的 `background`。本次只修这五处。

先完整阅读（只读）：`AGENTS.md`、`work-items/impl-02-corpus/act/05.yaml`、`act/03.yaml`、`act/04.yaml`、`pipeline/corpus_compiler/step.py`、`inputs.py`、`acceptance.py`、`tests/test_step.py`、`tests/test_acceptance.py`、`pipeline/ledger/objects.py`。

只允许写：`pipeline/corpus_compiler/step.py`、`pipeline/corpus_compiler/tests/test_step.py`、`pipeline/corpus_compiler/acceptance.py`、`pipeline/corpus_compiler/tests/test_acceptance.py`。其余一切禁止写入。

**台账纪律（硬性）**：你是执行者，不是验收者。不得修改 `HANDOFF.md`、`PLAN.md`、`docs/blackbox-spec-rework/SUBAGENT_TODO.md`、任何 `ACCEPTANCE.md`，不得在任何文件或提交信息里写「ACCEPTED」「验收通过」「主 Agent 审查」之类的结论。上一轮 `ad20ed6` 由执行方自行把 J2 记为 ACCEPTED，已被主 Agent 判为越权并更正。

**测试纪律（硬性）**：不得修改测试断言去迁就实现。`test_missing_fixture_exit_3` 必须断言 3。

严格执行：

0. 开工前提：`git status --short pipeline/corpus_compiler` 无输出；`.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -t .` 为 `Ran 59 tests … OK`；`bash openspec/acceptance/m3-coverage.sh` 末行 `SUMMARY pass=8 fail=0 blocked=1`。任一不符停手。
1. `export LC_ALL=en_US.UTF-8`。
2. 先按 `act/05.yaml` 的 `tests` 追加 7 个用例、修改 1 个断言、追加 1 个用例，运行测试记录 Red 原文（应有新用例失败，`test_missing_fixture_exit_3` 失败）。
3. 按 `contract` C1–C6 改 `step.py` 与 `acceptance.py`。
4. 运行 ACT `verify` 全部与 `docs/blackbox-spec-rework/work-items/impl-02-corpus/TDD.md` §3 回归。
5. `git add` 只加 `commit.add` 列出的四个文件，按 `commit.message` 提交。一个提交。
6. 停手规则：基线不符；某个新用例无法按定义写出；需要改 scope 外文件；contract 两种理解；任一门禁变红；`m3-coverage.sh` 不再是 `pass=8 fail=0 blocked=1` 且 exit 2。一律停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定。

最终报告：提交 hash 与 `git show --stat --oneline`；基线原文；Red 原文；Green 的 `Ran/OK` 行；verify 各项输出；`git status --short`；以及一句「等待主 Agent 独立验收」。
