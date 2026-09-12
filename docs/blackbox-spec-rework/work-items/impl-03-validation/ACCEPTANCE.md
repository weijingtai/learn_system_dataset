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
