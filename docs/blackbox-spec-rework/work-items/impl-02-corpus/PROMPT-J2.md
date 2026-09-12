# impl-02 · J2 组 Executor Prompt（ACT 03 → 04：Ledger 集成、m3-coverage 验收）

前置：J1 三个提交已在 HEAD 祖先中，且 `docs/blackbox-spec-rework/work-items/impl-02-corpus/ACCEPTANCE.md` 已记 ACT 00–02 `ACCEPTED`。不满足则停手，不要自己做 J1 的事。

你是执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复、代码注释、docstring 使用中文。

先完整阅读（只读）：`AGENTS.md`、`work-items/impl-02-corpus/README.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/03.yaml`、`act/04.yaml`、`ACCEPTANCE.md`、已落地的 `pipeline/corpus_compiler/*.py`、`pipeline/ledger/service.py`、`fixture_ingest.py`、`acceptance.py`（参照其退出码与 `prepare` 布局）、规格 §7、§10.1、§11、§17、§17.1、§19.0、`openspec/schemas/stage_package.schema.json` 与 `artifact_ref.schema.json`、`pipeline/corpus/_fixture/mini_ed01/`（expected/m3.stage_package.yaml、anomalies.yaml、verify.sh）、`openspec/acceptance/run_all.sh`（参照 `fx()` 与 `ledger_check`）。

只允许写：`pipeline/ledger/fixture_ingest.py` 与 `pipeline/ledger/tests/test_ingest.py`（仅 ACT 03 的 `stages` 扩展与一个测试）、`pipeline/corpus_compiler/**`、新建 `openspec/acceptance/m3-coverage.sh`。禁止改 `run_all.sh`、`pipeline/ledger` 其他文件、fixture、Schema、规格、`PLAN.md`。测试只用 `tempfile` 目录。

硬约束：标准库 + PyYAML/jsonschema；`unittest`；无新 ID 前缀；无模型 API；生产代码只读 Ledger 冻结修订（`acceptance.py` 读金标只经 `--fixture` 参数）；签名、返回键、检查名与 ACT contract 逐字一致；`acceptance.py` 退出码 3 只用于缺 fixture 或缺依赖，准备/运行/判定异常一律 FAIL 退出 1；`m3-coverage.sh` 永远调用仓库内规范 fixture `verify.sh`；`semantic_layer` 必须 BLOCKED；本批 `m3-coverage.sh` 必须返回 2，不得返回 0。

严格执行：

0. 开工前提：TDD §0 基线（`pipeline/corpus_compiler` 非缓存条目 6 个；门禁绿；`run_all.sh` 末行 `SUMMARY pass=2 fail=1 blocked=8`；`openspec/acceptance` 只有 `run_all.sh`）。`git status --short pipeline openspec/acceptance` 无输出。
1. `export LC_ALL=en_US.UTF-8`。
2. ACT 03：先写 `test_ingest.py` 追加用例与 `tests/test_step.py`（用例名逐字），记录 Red；实现 `fixture_ingest.stages`、`inputs.py`、`step.py`、`__main__.py`；ACT `verify`；TDD §3 回归；提交。
3. ACT 04：先写 `tests/test_acceptance.py`，记录 Red；实现 `acceptance.py`；新建 `m3-coverage.sh` 并 `chmod 755`；ACT `verify` 全部；回归；提交。
4. 两个提交；`git add` 只加 `commit.add` 列出的路径。
5. 停手规则：J1 未 ACCEPTED；任一基线不符；某条测试无法按定义写出；需要改 scope 外文件；contract 两种理解；任一门禁变红；`m3-coverage.sh` 结果不是 `SUMMARY pass=8 fail=0 blocked=1` 且 exit 2；`run_all.sh` 结果变化。一律停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定。

最终报告必须包含：两个提交 hash 与 `git show --stat --oneline`；基线原文；每个 ACT 的 Red 原文与 Green 末三行；`python -m pipeline.corpus_compiler` 在临时 Ledger 上的末行输出；`m3-coverage.sh` 全量输出与退出码；副本假 `verify.sh` 用例的输出与退出码；`run_all.sh` 末行；TDD §3 回归；`git status --short`；以及一句「等待主 Agent 独立验收」。
