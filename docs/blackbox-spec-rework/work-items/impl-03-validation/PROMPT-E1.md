# impl-03 · W3-E 实现 Prompt（M5 Automatic Validation 首切片——G1–G3 与 glyphbox_level 证据门禁）

你是执行 Agent（tmux 会话中的 `cmd`）。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复、注释、docstring 使用中文。回报写 `~/tmux-agents/runs/<会话>.report.md`（开工先写「## 状态：进行中」，每完成一个 ACT 追加一行；遇停手情形写「## 待裁决」+ 原始证据，停止等待）。

## 开工前提（任一不符停手上报，不得开工）

1. `impl-03-validation/ACT.yaml` 状态为 `READY_FOR_REVIEW` 且主 Agent 已放行（P2：`gate_results`、`validation_package` 与 `impl-00-interfaces/INTERFACES.md` §4 临时闭集**逐字一致**；开工前实跑 `python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py`，末行 `I00-IF SUMMARY pass=18 fail=0` 且 exit 0 才可开工）。
2. `git status --short pipeline/validation openspec/acceptance pipeline/corpus_compiler pipeline/ledger` 无输出。
3. 退出码/基线套件全绿：`verify-T.sh` 0 FAIL、`g3-r3/mutations.sh all` 109/109、`openspec/schemas/verify.sh` 返回 0、`check_d16.py` D16 OK。
4. `$TC`（corpus_compiler）与 `$TL`（ledger）`unittest` OK；`grep -cE '^\s+pass\s*$' pipeline/corpus_compiler/step.py` 为 0。
5. `bash openspec/acceptance/m3-coverage.sh` 末行 `SUMMARY pass=8 fail=0 blocked=1` 且 exit 2；`run_all.sh` 末行 `SUMMARY pass=2 fail=1 blocked=8`。
6. 完整基线以 `TDD.md` §0 为准。

## 先完整阅读（只读）

`AGENTS.md`；`docs/blackbox-spec-rework/G7-RULINGS.md` §1、§9；`G7-PLAN.md`；本包 `README.md`（尤其 §4 主 Agent 决定、§5 接口契约、§5.4 只读 SELECT 清单、§5.5 错误码缺口清单）、`ACT.yaml`、`act/00.yaml`–`act/06.yaml`、`BDD.md`、`TDD.md`；`work-items/impl-02-corpus/`（README、act/03、act/04、act/05、PROMPT-J3.md）；规格 `openspec/learn-system-blackbox-architecture.md` §7、§13、§13.1、§17、§17.1、§19.0、§20、§22；`pipeline/ledger/service.py`、`store.py`、`errors.py`、`ids.py`；`pipeline/corpus_compiler/step.py`、`inputs.py`、`gate.py`、`compiler.py`、`serialize.py`；`pipeline/corpus/_fixture/mini_ed01/`。

## 只允许写

`pipeline/validation/**`、`openspec/acceptance/m5-evidence-gate.sh`（均为新建）。其余一切禁止写入：规格正文、`openspec/schemas/**`、fixture 目录、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`openspec/acceptance/run_all.sh` 与 `m3-coverage.sh`、任何台账（HANDOFF/PLAN/SUBAGENT_TODO）、任何 `ACCEPTANCE.md`。

## 台账纪律（硬性）

你是执行者，不是验收者。不得修改 `HANDOFF.md`、`PLAN.md`、`SUBAGENT_TODO.md`、`G7-RULINGS.md`、`G7-PLAN.md`、任何 `ACCEPTANCE.md`，不得在任何文件或提交信息里写「ACCEPTED」「验收通过」「主 Agent 审查」之类的结论。只写上述「只允许写」范围。

## 测试纪律（硬性）

- 每个 ACT 先按 `tests_first` 写测试、运行取 Red 原文入回报，再实现；不得修改测试断言去迁就实现。
- 只用标准库 + PyYAML + jsonschema；不新增依赖、不新增 ID 前缀（`validator_id`、`task_id` 是任务标签）、不调用模型 API（P6 零模型调用）。
- 只用 `tempfile` 目录做测试，不写 `var/` 与 fixture。
- 公开函数名、参数名、返回键、检查名、artifact_type 与 `act/*.yaml` contract 逐字一致；中文注释与 docstring。

## 执行顺序（两轮，K1 全部 ACCEPTED 后才开 K2）

### 第一轮：K1（ACT 00–03，纯函数模块与 14 个已注册 Validator）

逐 ACT 串行，每个 ACT 一个提交（只 `git add` 其 `scope.write`，不得 `git add -A` / `git add .`）：

1. `act/00.yaml`（impl-03/00，≤75 分钟）：骨架、错误类型、规范 JSON、Finding、14 项 Validator 注册表与 `CHECK_CODES`。
2. `act/01.yaml`（impl-03/01，≤85 分钟）：G1 五项（`g1_source.py` + `replay.py`，`replay.py` 是唯一允许 import `pipeline.corpus_compiler.compiler` 的模块）。
3. `act/02.yaml`（impl-03/02，≤80 分钟）：G2 四项；`g2_coverage.py` 不得 import `pipeline.corpus_compiler`。
4. `act/03.yaml`（impl-03/03，≤80 分钟）：G3 五项；`g3_evidence.py` 不得 import `pipeline.corpus_compiler`。

每个 ACT：跑 `verify` 全部命令 + `TDD.md` §3 回归，把 Red 原文、Green 的 `Ran/OK` 行、`verify` 输出写入回报。K1 四个 ACT 全过后**停手**，写回报并等主 Agent 验收。

### 第二轮：K2（ACT 04–06，Ledger 读接口、run_m5 事务序列、验收脚本），K1 ACCEPTED 后

5. `act/04.yaml`（impl-03/04，≤75 分钟）：`resolve_m5_inputs`（17 个冻结修订，只接受 succeeded 上游，D-15）+ `build_context`；只读 SELECT 集中在三个私有函数（README §5.4）。
6. `act/05.yaml`（impl-03/05，≤90 分钟）：`run_m5` 事务序列、`gate_results` / `validation_package` / m5 StagePackage、CLI。要点：新类型仅 `gate_results`、`validation_package`，每 Validator 报告复用 `validation_report`；新内容 `schema_version: "0.1.0-draft"`；`validation.passed` 如实等于 `gate.passed`（§9 第 21 条）；gate 未过亦 `succeeded` 并封存（D-08 A）；退出码 0/1/2/3 纪律。
7. `act/06.yaml`（impl-03/06，≤80 分钟）：`acceptance.py` 十四项判定 + `openspec/acceptance/m5-evidence-gate.sh`（权限 755）；对抗输入用 mock compiler 构造 sealed 错误 m3 包（D-13 A）。

每个 ACT 一个提交、跑 `verify` 与回归。K2 全过后**停手**，写回报并等主 Agent 验收。

## 停手规则

基线不符；`docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py` 末行不是 `I00-IF SUMMARY pass=18 fail=0` 或 exit 非 0（即 `gate_results`/`validation_package` 未与 INTERFACES §4 逐字一致）；某个新用例无法按定义写出；contract 有两种理解；需要改「只允许写」之外的任何文件；任一门禁变红；`m3-coverage.sh` 不再是 `pass=8 fail=0 blocked=1` 且 exit 2，或 `run_all.sh` 末行改变。一律停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定。

## 最终报告（每次停手均写）

提交 hash 与 `git show --stat --oneline HEAD`（或分轮多个）；基线原文；每个 ACT 的 Red 原文；Green 的 `Ran/OK` 行；`verify` 各项输出；`git status --short`；新发现待裁决（没有写「无」）；末行「等待主 Agent 审阅」。
