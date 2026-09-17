# ACCEPTANCE：impl-03 M5 首切片（G1–G3 与 glyphbox_level 证据门禁）

状态：`READY_FOR_REVIEW`——本文件是主 Agent 独立验收的清单模板；§0–§4 的结论在验收时由主 Agent 据实填写，本包执行者不得代填。

## 0. 转译审查（主 Agent 四查，验收时逐项核对）

- **忠实性**：G1–G3 逐项对应 §13.1（588–590）与 `DATASET_ACCEPTANCE_STANDARD.md` §4；`glyphbox_level` 证据门禁（§11.1:525–528）进入 `g3_glyphbox_anchor` 与 `g3_evidence_level`；`scope: corpus_only`、G4/G5/G6 `not_evaluated`、验收判 BLOCKED 与 §9 第 2、22 条一致，差距不被宣称关闭；fail-closed（§13:608）进入 `g1_frozen_bytes` 前置与 task_status；不变更 Candidate、不生产 Tag 字段（§13:580、610）；零模型调用（P6）。
- **覆盖性**：`BDD.md` §1–§7 每个场景在 `BDD.md` §8 有 ≥1 个 `act/*.yaml` `tests` 用例名与 `TDD.md` §1 Red/Green 行；对抗输入覆盖「M3 同错同过」（D-13）；矩阵外篡改防假绿；退出码纪律 0/1/2/3 沿用 impl-01 ACT 06/impl-02 教训。
- **可执行性**：每个 ACT 有 `scope.write`、`tests_first`、contract（函数签名、检查名、退出码纪律）、`verify`（精确命令与期望）、`commit`；时长均 ≤ 110 分钟；引用的 `LedgerService` 方法与参数经 `pipeline/ledger/service.py` 逐条核对存在；引用的 M3 artifact_type 与 `pipeline/corpus_compiler/step.py` 实际写入一致。
- **独立性**：K1 与 K2 串行；`g1_source`/`g2_coverage`/`g3_evidence` 不 import `pipeline.corpus_compiler`，仅 `replay.py` 可 import compiler；`acceptance.py` 不 import 内部验证器逻辑，一律独立重算。

## 1. 范围核对

每个提交只含对应 ACT `commit.add` 路径；未动规格、`openspec/schemas/**`、fixture、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`run_all.sh`、`m3-coverage.sh`、任何台账；无 `var/`、`__pycache__`；`m5-evidence-gate.sh` 权限 755；`git diff --check` 无输出。

## 2. 门禁与判据（`git archive` 干净树，软链 `.venv` 与工作台 assets，`FIXTURE_ASSET_ROOT` 指本机页图）

- `verify-T.sh` 0 FAIL；`g3-r3/mutations.sh all` 109/109；`openspec/schemas/verify.sh` 0；`check_d16.py` D16 OK。
- 账本与 `corpus_compiler` `unittest` 用例数不变；`pipeline/validation` `unittest` 用例数达 `TDD.md` §1 阈值（ACT 06 后累计 ≥ 83）且全 OK。
- ACT 06 后 `m5-evidence-gate.sh` → `SUMMARY pass=9 fail=0 blocked=5`、exit 2；`m3-coverage.sh` 仍 `pass=8 fail=0 blocked=1`、exit 2；`run_all.sh` 仍 `pass=2 fail=1 blocked=8`。
- `TDD.md` §2 附加判据逐条实跑。

## 3. 语义与质量审查（主 Agent）

- Validator 纯函数性；G2/G3 独立重算覆盖与文本块；`acceptance.py` 独立重算、不信任 `run_m5` 返回值。
- `run_m5` 事务序列与 §17 一致；begin 之前的拒绝无写入；begin 之后的失败封存完整、无 m5 StagePackage。
- 冻结输入恰 17 个且全部 sealed，等于 `resolve_m5_inputs` 角色集合；上游 StagePackage 只接受 `succeeded` StepRun（D-15）。
- 新 artifact_type 仅 `gate_results`、`validation_package`，与 `INTERFACES.md` §4 逐字一致（`check_interfaces.py` 末行 `I00-IF SUMMARY pass=18 fail=0`、exit 0），每 Validator 报告复用 `validation_report`；新内容 `schema_version: "0.1.0-draft"`；未新增 `openspec/schemas/` 文件。
- m5 StagePackage `validation.passed` 如实等于 `gate.passed`；gate 未过时 StepRun 仍 `succeeded` 且下游不得仅凭 `succeeded` 放行（§9 第 21 条）。
- 错误码取值 ⊆ `errors.ERROR_CODES ∪ {None}`，缺口清单与 README §5.5 一致；只读 SELECT 仅限 README §5.4 清单。
- 退出码纪律；BLOCKED 行名逐字属 §19 第一列；中文注释；无 `except: pass`；零模型调用。

## 4. 结论

K1、K2 各自通过后由主 Agent 记 `ACCEPTED` 并同步台账；全部通过后 §19.0「M5 全书与证据校验不足」仍不宣称关闭（返回 2，缺 M4 与 quote hash），`run_all.sh` 不变。结论行由主 Agent 填写。

## 5. 验收记录由主 Agent 填写

### 5.1 W3-E 实现（2026-09-12，主 Agent 独立验收，`git archive` 干净树）

执行者：tmux 中的 cmd（DeepSeek V4.1 Flash），会话 `w3e`，按 executor_groups 分组停下待验收。

- K1（ACT 00–03：`25b2fcc`、`48ebbfb`、`1fab5b1`、`0a77975`）：范围仅 `pipeline/validation`；`validation` 50 OK、ledger 74 OK、corpus_compiler 68 OK；除 `replay.py` 外无 `corpus_compiler` import；六个纯函数模块无文件/时间/随机/uuid/环境副作用；无 `validator_report`/`gate_report` 字面；全部门禁绿。执行方 amend 未推送的 ACT 00 提交（G7-RULINGS 第 28 条接受）。
- K2（ACT 04–06：`817cd64`、`9aaccf5`、`6e21038`；返工 `8367893`）：范围仅 `pipeline/validation` 与 `openspec/acceptance/m5-evidence-gate.sh`；`validation` 86 OK（返工后 87 OK）；`m5-evidence-gate.sh` `SUMMARY pass=9 fail=0 blocked=5`、exit 2；`run_all.sh` 仍 `pass=2 fail=1 blocked=8`；`m3-coverage.sh` exit 2；`verify-T.sh` 0 FAIL、`mutations.sh` 109/109、`schemas/verify.sh` 0、`check_d16.py` OK、`check_interfaces.py` 18 PASS。`acceptance.py` 三处 `corpus_compiler` import 仅用于构造真实上游与对抗性篡改（包装 `compile_structural`、替换 `step.evaluate_structural` 放行），判定逻辑不借用 M3 Gate，合规。
- 矩阵外端到端（主 Agent 脚本 13 项全过）：fixture 上 `run_m5` succeeded、恰 1 个 m5 包、冻结输入 17（corpus_only）、findings 7（warnings 5、failures 0）、INTERNAL_DEMO 下 `validation.passed=true`；两次独立运行 `gate_results`（去身份字段）一致；`corpus_spans`/`corpus_package` 冻结对象改一字节 → StepRun succeeded 但无可消费包（第 21 条）；无 m3 提交 → begin 前 `ValidationRefused` 无包；`PUBLIC_RELEASE` 目标 → 级别判定 `{INTERNAL_DEMO: passed, DEV_SEARCH: failed, PUBLIC_RELEASE: failed}`、无可消费包；begin 后注入异常 → failed/internal 封存、无 m5 包；验收脚本在 Ledger `gate_results` 被改时 exit 1（不信任返回值）。
- 返工（第 33 条⑤）：begin 之后失败的 CLI 退出码由 2 改 1；主 Agent 在 `8367893` 干净树注入 `write_checkpoint` 异常 → rc 1、末行 `M5 FAILED internal: …`。
- 登记（第 33 条②）：act/04–06 脚手架文字 `ingest(m1,m2,m3)` 与 BDD 真实链路不一致，实现与测试以 BDD 为准，文档待后续修订。字框比对缺陷修正落在 `9aaccf5`（第 33 条①）。

impl-03（M5 首切片）`ACCEPTED`。`m5-evidence-gate.sh` 返回 2（G4/G5/G6 `not_evaluated` 判 BLOCKED），§19 M5 差距不宣称关闭。

### 5.2 W8 8.3 返工 R83 + R83b + R83c（2026-09-16，主 Agent 独立验收，`git archive 2db0fcc` 干净树；执行器 cmd DeepSeek V4.1 Flash）

判定：**R83（`2537b75`）、R83b（`82f7148`）、R83c（`2db0fcc`，impl-00 登记表更正）ACCEPTED**。第 100 条 D5、第 103 条落地，**真书 M5 在 `INTERNAL_DEMO` 通过**。

- 过程：R83 真书 G1 failed（M2 有意保留的 39 个私用区码位被判 `forbidden_char_in_text`），执行方未放宽判据、停手上报 → 第 103 条（offset 档与清洗报告对账；登记表陈旧闭集更正）→ R83b/R83c。
- 套件（干净树）：validation `Ran 108 OK`、knowledge_extraction `Ran 145 OK`、corpus `Ran 163 OK`、impl-00 tests `Ran 31 OK`；`check_interfaces` `pass=39 fail=0`；`m5-evidence-gate.sh`（mini_ed01）`SUMMARY pass=9 fail=0 blocked=5`，与改前相同；`run_all.sh` 基线不变。
- **用例审计**（AST 逐函数）：`test_g1/g2/g3/test_step.py`、`test_check_interfaces.py` 删 0、改 0，仅新增；`tests/helpers.py` 改 `fixture_context`（仅追加键，原键值不变）与新增 offset 夹具，无既有夹具取值变化。
- **主 Agent 独立脚本**真书 M1→M2→`run_m3_text`→`run_m5`：`INTERNAL_DEMO` → `status: succeeded`、`gate.passed: true`、`level_verdicts {INTERNAL_DEMO: passed, DEV_SEARCH: passed, PUBLIC_RELEASE: failed}`、`findings 40 / failures 0 / warnings 39`；`PUBLIC_RELEASE` → `gate.passed: false`、`severe_error_count 40`（39 条披露项升 error + `evidence_level_insufficient`）。
- **主 Agent 篡改**（临时副本）：去掉对账中的 `kind` 比对 → `test_g1_offset_pua_with_mismatched_kind_is_error` 转红。执行方另两组（跳过终态判断、OCR 档也走对账）亦转红。
- 执行方报备：`deferred_count` 实际在 `summary.deferred_count`，M2 Gate/验收/M3 读取一致，impl-09 README 第 228–229 行键清单写法易误读为顶层键——列 W8 跟进，不阻断。
