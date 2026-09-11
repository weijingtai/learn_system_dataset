# impl-01 · H2 组 Executor Prompt（ACT 03 → 04 → 05：服务 API、本地进程、宿主判定）

前置：H1 三个提交已在 HEAD 祖先中，且主 Agent 已在 `ACCEPTANCE.md` 记 ACT 00–02 `ACCEPTED`（读 `docs/blackbox-spec-rework/work-items/impl-01-ledger/ACCEPTANCE.md` 确认）。不满足则停手，不要自己做 H1 的事。

你是执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复、代码注释、docstring 使用中文。

先完整阅读（只读）：`AGENTS.md`、`work-items/impl-01-ledger/README.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/03.yaml`、`act/04.yaml`、`act/05.yaml`、已落地的 `pipeline/ledger/*.py`、规格 §7、§7.1、§8.1、§8.2、§17、§17.1、`openspec/schemas/step_request.schema.json`、`step_result.schema.json`、`stage_package.schema.json`、`pipeline/corpus/_fixture/mini_ed01/`（manifest、expected 三包、anomalies、spans）、`openspec/acceptance/run_all.sh`。

只允许写：`pipeline/ledger/**`、`openspec/acceptance/run_all.sh`（仅 ACT 05 指定的三处：a3 后追加 `ledger_check` 定义、a1/a2 两行替换）。禁止改 fixture、Schema、规格、`.gitignore`。测试只用 `tempfile` 目录。

硬约束同 H1：标准库 + PyYAML/jsonschema；`unittest`；无新前缀；签名与 ACT contract 逐字一致；`resume_token` 只存哈希；不得把 20.2/20.3 写成无条件 PASS；BLOCKED 行名逐字属 §19 第一列。

严格执行：

0. 开工前提：TDD §0 基线（`ls pipeline/ledger | wc -l` = 13；三门禁绿；`run_all.sh` 末行 `SUMMARY pass=0 fail=1 blocked=10`）。`git status --short pipeline/ledger openspec/acceptance` 无输出。
1. `export LC_ALL=en_US.UTF-8`。
2. ACT 03：先写 `tests/test_service.py`、`tests/test_checkpoint.py`（用例名逐字），记录 Red；实现 `service.py`（`LedgerService`、`LedgerReader`，方法名与参数名逐字按 `contract.methods`）；ACT `verify`；TDD §3 回归；提交。
3. ACT 04：先写 `tests/test_daemon.py`，记录 Red；实现 `ledgerd.py`/`client.py`/`cli.py`；ACT `verify`；回归；提交。
4. ACT 05：先写 `tests/test_ingest.py`、`tests/test_acceptance.py`，记录 Red；实现 `fixture_ingest.py`、`acceptance.py`、`service.put_run_artifact`；断言 `run_all.sh` 三个锚点各恰 1 次后按 `run_all_sh` 精确改动；ACT `verify` 全部（含篡改副本 → `FAIL  20.2`、BLOCKED 行名核对）；回归；提交。
5. 三个提交；`git add` 只加 `commit.add` 列出的路径。
6. 停手规则：H1 未 ACCEPTED；任一基线不符；某条测试无法按定义写出；`run_all.sh` 锚点命中不为 1；需要改 scope 外文件、fixture 或 Schema；contract 两种理解；任一门禁变红；`run_all.sh` 结果不是 `pass=2 fail=1 blocked=8`。一律停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定。

最终报告必须包含：三个提交 hash 与 `git show --stat --oneline`；基线原文；每个 ACT 的 Red 原文与 Green 末三行；`fixture_ingest` 末行 `INGEST OK …`；`acceptance --check 20_2` 与 `20_3` 全量输出；`run_all.sh` 全量输出（11 行 + SUMMARY）与退出码；篡改副本的 `20.2` 输出；TDD §3 回归；`git status --short`；以及一句「等待主 Agent 独立验收」。
