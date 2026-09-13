# ACCEPTANCE：impl-08 Local Orchestrator + Contract Registry 首切片

状态：`READY_FOR_REVIEW`（W4-I 定稿 2026-09-12；本文件 §0–§4 由执行者起草，§5 由主 Agent 填写）

## 0. 转译审查（主 Agent 四查）

- 忠实性：§1 目标逐条对应规格 §5:116–128（Orchestrator 职责与六项查询闭集）、§6.1:149（阶段推进条件）、§7/§7.1:181–226（统一 Interface、StepRun 生命周期、人工恢复）、§17/§17.1:836–846（事务序列、Checkpoint 粒度与恢复语义）；`run_m3`/`run_m5`/`run_m8`/`ingest`/`register_source_assets` 的签名与返回键逐条核对（README §2）；M4/M6/M7 与 ReleaseRun 显式标 DEFERRED（README §9），§20.1 的 BLOCKED 不被宣称关闭。
- 覆盖性：BDD 1–9 每条对应 ACT `tests` 用例名与 TDD §1 Green 值；Gate 八项独立实现；验收不信任返回值（real_chain 独立重算）；退出码纪律沿用 impl-02/impl-03 先例；矩阵外篡改、桩隔离、legacy 在 ledgerd 下、`run_all.sh` 其余九条逐字不变。
- 可执行性：每个 ACT 有函数签名、规则、检查名、用例名、CLI 与退出码、`commit`；时长 60/80/75/75/90/90/75/90/85/45 分钟（act/10 DEFERRED 不计）。
- 独立性：K1–K3 只用桩与假入口，不依赖 impl-02/03/04；K4 依赖 impl-02/03/04 均 ACCEPTED 与本机派生页图；写范围与 impl-03（`pipeline/validation/**`）、impl-04（`pipeline/dataset_compiler/**`、`m8-span-identity.sh`）不重叠；`run_all.sh` 仅 ACT 09 写，且须在 impl-04 ACT 08 验收后（P4）。

## 1. 范围核对

- 每个提交只含 ACT `commit.add` 路径；`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`pipeline/validation/**`、`pipeline/dataset_compiler/**`、`openspec/schemas/**`、规格、fixture、其他 work-items 未动；无 `var/`、`__pycache__`；`git diff --check`。
- ACT 09 的 diff 只触及 20.1/20.10 两个 case 体与一个新增 `accept_check` 函数；其余九条 §20 输出与基线逐字相同。

## 2. 门禁与判据（`git archive` 干净树，软链 `.venv` 与工作台 assets，`FIXTURE_ASSET_ROOT` 指本机页图）

- 门禁绿；两套 `unittest`（contract_registry、orchestrator）全过且用例数达 TDD §1 阈值；`run_all.sh` 在 ACT 09 前仍 `pass=2 fail=1 blocked=8`，ACT 09 后条数不变。
- ACT 07 后 `orchestrator-gate.sh` → `SUMMARY pass=5 fail=0 blocked=1`、exit 2；ACT 08 后 `contract-registry.sh` → `SUMMARY pass=3 fail=0 blocked=2`、exit 2。
- TDD §2 附加判据逐条实跑。

## 3. 语义与质量审查（主 Agent）

- Gate 与验收判定的独立重算；`advance`/`run_release` 的零写入纪律（waiting/blocked/refused/complete 前后三表行数不变）。
- 首纵切链真实跑通 m1/m2（imported）→ m3 → m5（legacy）→ m8（legacy release），m3/m5/m8 StagePackage 全过；m1_shim supersede 后 m1 Gate 与 lineage 行为符合 §4.1 N-2 A。
- `run_m8` 的 release_run 边界与 `entry_kwargs` 透传符合 §4.1 N-3 A；`owns_processing_run` 不被误用于非 release 入口。
- 端口闭集、Adapter 替换判定、桩隔离、生产表无 `kind: stub`；`modules_port_clean` 如实列 BLOCKED 与 文件:行号（D-9）。
- 退出码纪律；中文注释；无 `except: pass`；未写台账或结论性措辞。

## 4. 结论（待主 Agent 填写）

- 各 ACT `ACCEPTED`/返工结论、§4.1 各待裁决项的裁定、impl-00 §5.2 缺口的处置，由主 Agent 在本节与 `SUBAGENT_TODO`/`HANDOFF` 同步。

## 5. 验收记录

§5 验收记录由主 Agent 填写。
