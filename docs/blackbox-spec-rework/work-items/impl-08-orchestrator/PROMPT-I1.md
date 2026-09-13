# impl-08 · I1 实现 Prompt（ACT 00–09：Local Orchestrator + Contract Registry 首切片）

你是执行 Agent，运行在 tmux，无人实时看屏幕。所有回复、注释、docstring、提交信息使用中文。

工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。

先完整阅读（只读）：本目录 `README.md`（§1 目标、§3 范围、§4 主 Agent 决定、§4.1 待主 Agent 裁决、§6/§7 契约、§8 分组、§9 DEFERRED）、`ACT.yaml`、`BDD.md`、`TDD.md`、`act/00.yaml`–`act/10.yaml`、`docs/blackbox-spec-rework/G7-RULINGS.md` §1（P1–P9）、§6、§9/§9.1/§9.2、`impl-00-interfaces/INTERFACES.md` §1/§2/§4/§6 与 `README.md` §5.2、`impl-02-corpus/act/03.yaml`（Ledger 事务模板）、`impl-04-dataset/README.md`（§6/§7 M8 契约与 m1_shim）、`pipeline/ledger/service.py`（公开方法）、`pipeline/ledger/client.py`、`pipeline/ledger/ids.py`、`pipeline/corpus_compiler/step.py`（`run_m3`）、`pipeline/validation/step.py`（`run_m5`）、`pipeline/dataset_compiler/step.py`（`run_m8`）与 `pipeline/dataset_compiler/shim/m1_shim_source_assets.py`。

## 只允许写

- `pipeline/contract_registry/**`（新建，含 `tests/`）
- `pipeline/orchestrator/**`（新建，含 `tests/`）
- `openspec/acceptance/orchestrator-gate.sh`（ACT 07 新建）、`openspec/acceptance/contract-registry.sh`（ACT 08 新建）
- `openspec/acceptance/run_all.sh`（**仅 ACT 09**，仅新增一个 `accept_check` 函数与改 20.1/20.10 两个 case 体）

其余一律禁止写入：`pipeline/ledger/**`（P9；`act/10.yaml` DEFERRED，未获主 Agent 裁决不得执行）、`pipeline/corpus_compiler/**`、`pipeline/validation/**`、`pipeline/dataset_compiler/**`、`openspec/schemas/**`、`pipeline/corpus/_fixture/**`、规格正文、`openspec/id-prefix-registry.md`、`HANDOFF.md`、`PLAN.md`、`SUBAGENT_TODO.md`、`G7-*.md`、任何 `ACCEPTANCE.md` §5、其他 work-items。不得改 ACT contract 里的函数名/参数名/返回键/检查名/artifact_type/CLI 末行去迁就实现。

## 台账纪律（硬性）

你是执行者，不是验收者。不得修改 `HANDOFF.md`、`PLAN.md`、`SUBAGENT_TODO.md`、任何 `ACCEPTANCE.md`、`G7-*.md`；不得在任何文件或提交信息里写「ACCEPTED」「验收通过」「主 Agent 审查」之类的结论。台账由主 Agent 写。

## 测试纪律（硬性）

- 每个 ACT 先写测试（用例名与 ACT `tests` 逐字）并运行取得 **Red 原文**，再实现；Red 原文与 Green 的 `Ran/OK` 行写进最终报告。
- 不得修改测试断言去迁就实现；不得删改已有断言。
- 只用标准库 + PyYAML + jsonschema；不新增依赖、不新增 ID 前缀（`module_id`/`port_id`/`adapter_id` 是登记表标签）、不调用模型 API（P6）。
- 测试只用 tempfile 目录；不写 `var/` 与 fixture；新增 artifact_type 一律先经 `INTERFACES.md` §4 登记（本包不新增，Gate 证据复用 `validation_report`）。

## 开工前提（任一不符，停手上报）

```bash
cd /Users/jingtaiwei/Git/Public/learn_system
export LC_ALL=en_US.UTF-8
git status --short pipeline/orchestrator pipeline/contract_registry openspec/acceptance   # 空
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                                   # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1             # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo $?                                    # 0
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py                        # D16 OK
.venv/bin/python -m unittest discover -s pipeline/ledger/tests -t . 2>&1 | tail -1     # OK
.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -t . 2>&1 | tail -1   # OK
.venv/bin/python -m unittest discover -s pipeline/validation/tests -t . 2>&1 | tail -1 # OK
.venv/bin/python -m unittest discover -s pipeline/dataset_compiler/tests -t . 2>&1 | tail -1  # OK
bash openspec/acceptance/run_all.sh | tail -1                                          # SUMMARY pass=2 fail=1 blocked=8
ls openspec/acceptance/                                                               # run_all.sh m3-coverage.sh m5-evidence-gate.sh m8-span-identity.sh
```

## 逐步

按 `ACT.yaml` 的 K1 → K2 → K3 → K4 顺序串行；每组 `ACCEPTED` 后再派下一组：

1. **K1（ACT 00 → 01）**：登记表目录与端口。ACT 00 建包骨架、`registry.yaml`（**五项 Module**：m1/m2 `imported`、m3/m5/m8 `legacy_self_driving`，m5/m8 带 `entry_kwargs`，m8 `owns_processing_run: true`）、`load_registry`/`check_registry`/`module_for`/`interface_fingerprint` 与 CLI；ACT 01 `ports.py`/`conformance.py`。每个 ACT 一个提交，`commit.add` / `commit.message` 逐字照 act 文件。
2. **K2（ACT 02 → 03 → 04）**：`module.py`（三绑定 + `entry_kwargs`/`owns_processing_run`）、`stubs.py`；`gate.py`（八项 + `effective_step_runs` 的 supersede 规则 + `succeeded_step_runs`）；`runner.py`/`edition_run.py`（`advance`/`run_until`/`run_release`/`edition_status`，`FIRST_SLICE_EDITION_STAGES`）。
3. **K3（ACT 05 → 06）**：`human.py`；`queries.py`/`__main__.py`（六项查询与 CLI）。
4. **K4（ACT 07 → 08 → 09）**：`acceptance.py`+`orchestrator-gate.sh`；`suites.py`+`contract_registry/acceptance.py`+`contract-registry.sh`；最后 `run_all.sh`。**ACT 09 前置**：impl-04 ACT 08 已验收，且无并发改 `run_all.sh`（P4）；否则停手。
5. 每个 ACT 后运行该 ACT `verify` 全部与 `TDD.md` §3 回归；`git add` 只加该 ACT `commit.add` 列出的路径，一个提交。
6. 每个 ACT 完成后在 `~/tmux-agents/runs/<会话>.report.md` 追加一行「- [x] ACT <id>」，并附该 ACT 的 Red/Green 原文。

## 分组停下规则

每组完成后停下，把该组 Red/Green、`verify` 输出与 `git show --stat --oneline` 交主 Agent；得到继续指令后再开下一组。K4 的 `real_chain_mini_ed01` 依赖 impl-02/impl-03/impl-04 均 ACCEPTED 与本机派生页图，缺一即停手上报（不得伪造页图）。

## 停手规则

遇下列任一，停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定：

- 基线任一门禁不符；`pipeline/orchestrator` 或 `pipeline/contract_registry` 已有内容；K4 前置（impl-02/03/04 ACCEPTED、页图、无并发 run_all 写者）不满足。
- `run_m3`/`run_m5`/`run_m8`/`ingest`/`register_source_assets` 的实际签名、返回键或 StepRun 语义与 README §6 表不符（如 `run_m8` 不再自建 release_run）。
- `LedgerClient` 缺 `LEDGER_PORT_METHODS` 中任一公开方法；ledgerd 无法在测试中启动。
- 某条测试无法按 ACT `tests` 定义写出；contract 有两种理解；需要改 scope 外文件；任一门禁变红。
- `run_all.sh` 存在并发写入者（P4）；其余九条 §20 输出出现任何差异或 SUMMARY 条数变化时不得提交。

## 最终报告（写 `~/tmux-agents/runs/<会话>.report.md`）

- 各 ACT 提交 hash 与 `git show --stat --oneline <hash>`；
- 基线原文；各 ACT 的 Red 原文与 Green 的 `Ran/OK` 行；
- 各 ACT `verify` 输出（命令 + 末行）；
- `git status --short`；末行「等待主 Agent 独立验收」。
