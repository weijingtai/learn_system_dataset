# impl-01 · H1 组 Executor Prompt（ACT 00 → 01 → 02：检查脚本、标识与状态机、存储层）

你是执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`（HEAD 祖先必须含 `70c05cd`）。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复、代码注释、docstring 使用中文。

先完整阅读（只读）：`AGENTS.md`、`docs/blackbox-spec-rework/work-items/impl-01-ledger/README.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/00.yaml`、`act/01.yaml`、`act/02.yaml`、规格 `openspec/learn-system-blackbox-architecture.md` §8.1、§8.2、§17、`openspec/id-prefix-registry.md` §4、`openspec/legacy-storage-transition.md` §2。

只允许写：`docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py`（ACT 00，仅 R3 行数条件）、`pipeline/ledger/**`（新建）、根 `.gitignore`（追加一行 `var/`）。其余一切禁止；工作树里其他人的未提交改动原样保留。Ledger 测试只用 `tempfile` 目录，绝不写 `var/` 或 fixture。

硬约束：只用 Python 标准库 + 已装 PyYAML/jsonschema，不装任何包；测试框架 `unittest`（本机无 pytest）；不新增任何 ID 前缀；公开函数/类/常量名与参数名与 ACT `contract` 逐字一致；DDL 表名列名逐字一致。

严格执行：

0. 开工前提：TDD §0 基线全部符合（`pipeline/ledger` 不存在、三门禁绿、`run_all.sh` 末行 `SUMMARY pass=0 fail=1 blocked=10`、`env ok`）。任一不符停手。
1. `export LC_ALL=en_US.UTF-8`。
2. ACT 00：按 `rule_change` 改 R3；ACT `verify` 三条；提交。
3. ACT 01：**先写** `tests/test_ids.py`、`tests/test_states.py`，用例名与 ACT `tests` 逐字相同，运行 `.venv/bin/python -m unittest discover -s pipeline/ledger/tests -t .` 记录 Red 原文；再实现 `ids.py`/`states.py`/`errors.py`/`actor.py`；ACT `verify`；TDD §3 回归；提交。
4. ACT 02：先写 `tests/test_objects.py`、`tests/test_store.py`（Red 原文）；再实现 `objects.py`/`store.py`/`lock.py`，根 `.gitignore` 追加 `var/`；ACT `verify`；TDD §3 回归；提交。
5. 三个 ACT 三个提交；`git add` 只加 ACT `commit.add` 列出的路径；不得 `git add -A` / `git add .`。
6. 停手规则：任一基线不符；某条测试无法按 ACT 定义写出；实现需要改 scope 外文件或新增依赖；对 contract 有两种理解；任一门禁变红。一律停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定。

最终报告必须包含：三个提交 hash 与各自 `git show --stat --oneline`；基线原文；每个 ACT 的 Red 原文与 Green 末三行（用例数）；ACT 02 的 `sqlite_master` 表名列表；`grep -Fxc 'var/' .gitignore`；TDD §3 回归输出；`git status --short`；以及一句「等待主 Agent 独立验收」。
