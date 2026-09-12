# impl-02 · J1 组 Executor Prompt（ACT 00 → 01 → 02：检查脚本、结构编译器、独立 Gate）

你是执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`（HEAD 祖先必须含 `c939575`）。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复、代码注释、docstring 使用中文。

先完整阅读（只读）：`AGENTS.md`、`docs/blackbox-spec-rework/work-items/impl-02-corpus/README.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/00.yaml`、`act/01.yaml`、`act/02.yaml`、规格 `openspec/learn-system-blackbox-architecture.md` §8.1、§10.1、§11、§11.1、`pipeline/ledger/ids.py` 与 `errors.py`、`pipeline/corpus/_fixture/mini_ed01/`（manifest.yaml、pages/*.json、anomalies.yaml、spans.yaml、source/transcript_v1.md、tools/build_fixture.py 的 `build_spans` 与 `dump_yaml`）、`docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py`。

只允许写：`docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py`（ACT 00，仅 R5）、`pipeline/corpus_compiler/**`（新建）。其余一切禁止，包括 fixture、`pipeline/ledger/**`、`PLAN.md`；工作树里其他人的未提交改动原样保留。

硬约束：只用 Python 标准库 + 已装 PyYAML/jsonschema；`unittest`；不新增 ID 前缀；不调用模型 API；生产代码不读文件、不 import fixture 工具（测试可读 fixture 作输入与金标）；公开函数名、参数名、返回键、检查名与 ACT `contract` 逐字一致；`gate.py` 不得 import `compiler.py`/`serialize.py`；不得向全局 `yaml.SafeDumper` 注册 representer。

严格执行：

0. 开工前提：TDD §0 基线全部符合（`pipeline/corpus_compiler` 不存在、`openspec/acceptance` 只有 `run_all.sh`、门禁绿、`run_all.sh` 末行 `SUMMARY pass=2 fail=1 blocked=8`、`spans.yaml` 哈希 `ec6d77b9…`）。任一不符停手。
1. `export LC_ALL=en_US.UTF-8`。
2. ACT 00：先做 Red 副本并记录输出；按 `rule_change` 改 R5；ACT `verify` 四条；提交。
3. ACT 01：先写 `tests/test_compiler.py`（用例名逐字），运行 `.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -t .` 记录 Red；再实现 `__init__.py`/`errors.py`/`serialize.py`/`compiler.py`；ACT `verify`；TDD §3 回归；提交。
4. ACT 02：先写 `tests/test_gate.py`（用例名逐字），记录 Red；再实现 `gate.py`；ACT `verify`；回归；提交。
5. 三个 ACT 三个提交；`git add` 只加 ACT `commit.add` 列出的路径；不得 `git add -A` / `git add .`。
6. 停手规则：任一基线不符；金标字节无法对齐（报告首个差异字节位置与上下文，不得改 fixture）；某条测试无法按定义写出；需要改 scope 外文件或新增依赖；contract 有两种理解；任一门禁变红。一律停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定。

最终报告必须包含：三个提交 hash 与各自 `git show --stat --oneline`；基线原文；每个 ACT 的 Red 原文与 Green 末三行（用例数）；ACT 01 金标 sha256 实测值；ACT 02 每个篡改用例对应的失败检查名清单；TDD §3 回归输出；`git status --short`；以及一句「等待主 Agent 独立验收」。
