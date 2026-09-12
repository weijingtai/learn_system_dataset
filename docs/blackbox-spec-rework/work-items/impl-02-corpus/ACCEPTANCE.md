# ACCEPTANCE：impl-02 M3 结构层

状态：`READY`（J1 待用户交外部 Agent；J2 在 J1 `ACCEPTED` 后派发）

## 0. 转译审查（主 Agent 四查，2026-09-11）

- 忠实性：结构切段规则逐项对应 fixture `build_spans`（金标）与规格 §11 Gate「同层 Span 全文覆盖 100%、无缺口、无重叠、拼接一致」；§10.1 终态放行/阻断与「严禁裸标」进入编译器 R2 与 Gate `page_accounting`；§11.1 `glyphbox_level` 进入 `glyphbox_anchors`；§7「只读冻结输入」进入 `inputs.py` 与 `input_contract`；§17.1「每 task 一个 Checkpoint」进入每批 Checkpoint；§19.0 `m3-coverage.sh` 作为完成判据。语义层未做被显式标为 BLOCKED，`m3-coverage.sh` 返回 2 而非 0，差距不被宣称关闭。
- 覆盖性：BDD 1–5 每条对应 ACT `tests` 用例名与 TDD §1 Green 值；独立 Gate、独立验收重算、矩阵外篡改防假绿；退出码纪律与副本脚本不被信任沿用 impl-01 ACT 06 与 D-18 教训。
- 可执行性：见下方派发前核对；每个 ACT 有函数签名、规则、检查名、用例名、CLI 与退出码；时长 15/60/75/120/75 分钟。
- 独立性：J1、J2 串行；ACT 03 对 `pipeline/ledger` 只扩一个参数与一个测试。

派发前核对（主 Agent 脚本，2026-09-11）：7 份 YAML 可解析；fixture spans.yaml sha256 = ec6d77b9… 且等于 expected/m3 content_sha256；pipeline/corpus_compiler 不存在；openspec/acceptance 只有 run_all.sh；按 ACT 01 通用规则（私有 Dumper、每页每 10 行一批、全局批号）独立复算 spans 字节与金标逐字节相同；全局 SafeDumper 未被修改；ACT 00 Red 可复现：勾选节 C「Artifact Ledger」→ D16 FAIL R5 新节 C 未勾选项数=2（应 3）；§19 第一列含「M3 Corpus Compilation」；§19.0 登记 `m3-coverage.sh`；ACT 03 调用的 7 个 LedgerService 方法均存在。

## 1. 范围核对

每个提交只含 ACT `commit.add` 路径；fixture、Schema、规格、`run_all.sh`、`pipeline/ledger` 其他文件未动；无 `var/`、`__pycache__`；`git diff --check`。

## 2. 门禁与判据（`git archive` 干净树，软链 `.venv` 与工作台 assets，`FIXTURE_ASSET_ROOT` 指本机页图）

- 门禁绿；两套 `unittest` 全过且用例数达 TDD §1 阈值；`run_all.sh` 仍 `pass=2 fail=1 blocked=8`。
- ACT 04 后 `m3-coverage.sh` → `SUMMARY pass=8 fail=0 blocked=1`、exit 2。
- TDD §2 附加判据逐条实跑。

## 3. 语义与质量审查（主 Agent）

- 编译器纯函数性；Gate 与验收判定的独立重算；金标字节一致且两次运行相同。
- `run_m3` 事务序列与 §17 一致；begin 之前的拒绝无写入；begin 之后的失败封存完整、无 m3 StagePackage。
- 冻结输入恰为 6 个；StagePackage 血缘与 Transformation 一致；配置记录 `gate_profile` 与 `batch_size`。
- 退出码纪律；`semantic_layer` 恒 BLOCKED；中文注释；无 `except: pass`。

## 4. 结论

J1、J2 各自通过后记 `ACCEPTED`；全部通过后 SUBAGENT_TODO G7 impl-02 `ACCEPTED`、HANDOFF 同步；主 Agent 在 ACT 00 验收后勾选 PLAN D-16 节 C「Artifact Ledger」并附 `c939575`。
