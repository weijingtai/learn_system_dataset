# ACCEPTANCE：impl-08 Local Orchestrator + Contract Registry 首切片

状态：`READY_FOR_REVIEW`（W4-I 定稿 2026-09-12；本文件 §0–§4 由执行者起草，§5 由主 Agent 填写）

## 0. 转译审查（主 Agent 四查）

- 忠实性：§1 目标逐条对应规格 §5:116–128（Orchestrator 职责与六项查询闭集）、§6.1:149（阶段推进条件）、§7/§7.1:181–226（统一 Interface、StepRun 生命周期、人工恢复）、§17/§17.1:836–846（事务序列、Checkpoint 粒度与恢复语义）；`run_m3`/`run_m5`/`run_m8`/`ingest`/`register_source_assets` 的签名与返回键逐条核对（README §2）；M4/M6/M7 与 ReleaseRun 显式标 DEFERRED（README §9），§20.1 的 BLOCKED 不被宣称关闭。四查 R1 返工：F1 `stage_package_valid` 按第 45 条改为「承载 StagePackage 的有效运行恰 1 个且包合法，不承载包的接替运行不计入包判定但须 succeeded」；F2 Gate 报告按第 46 条不落盘（`gate_reports` + CLI 打印，落盘见 `act/11.yaml` DEFERRED）。
- 覆盖性：BDD 1–9 每条对应 ACT `tests` 用例名与 TDD §1 Green 值（F3 补齐 BDD 1.2「stage 超出 m1–m8」具名用例 `test_module_stage_out_of_closed_set_detected`）；Gate 八项独立实现；验收不信任返回值（real_chain 独立重算）；退出码纪律沿用 impl-02/impl-03 先例；矩阵外篡改、桩隔离、legacy 在 ledgerd 下、`run_all.sh` 其余九条逐字不变；F4 起 unittest 回归取行统一为 `2>&1 | grep -E "^(Ran|OK|FAILED)"`。
- 可执行性：每个 ACT 有函数签名、规则、检查名、用例名、CLI 与退出码、`commit`；时长 60/80/75/75/90/90/75/90/85/45 分钟（`act/10`、`act/11` 为 DEFERRED，各 90/60 分钟，不计）。
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

### 5.1 W4-I 实现（2026-09-12，主 Agent 独立验收，`git archive` 干净树）

执行者：tmux 中的 cmd（DeepSeek V4.1 Flash），会话 `w4o`，按 K1–K4 分组停下待验收。定稿 `cd6c7a6`，四查 R1 REWORK `5ab873c`（裁定 45/46）→ 返工 `559a359` → R2 READY `d49094b`。

- K1（`8aa2ad6`、`772b44b`）：范围仅 `pipeline/contract_registry`；contract_registry 30 OK，其余四套 OK；`REGISTRY OK modules=5 ports=4`；`DirectLedgerAdapter.read_object` 经 `objects.get` 只读字节属第 36 条登记读缺口。
- K2（`8fb9189`、`0b2a947`、`74c4cbf`）：orchestrator 59 OK；`gate.py` 不复用被判模块实现；未新增 `.store/.objects` 访问。第 56 条：ACT 04 事后构造 Red 登记，K3 起纠正。
- K3（`1658a82`、`c72c90e`）：orchestrator 87 OK；Red 原文早于实现。
- K4（裁定 57 `59d5d73`、裁定 59 `8ca41e9`、ACT 07 `640ab4c`、ACT 08 `a8494a3`、ACT 09 `f79eafd`）：各提交范围在授权路径内（`59d5d73` 仅 gate.py 与其测试，`_read_package_content` 改 `yaml.safe_load` 且非映射拒绝；`8ca41e9` 仅 test_module.py；ACT 09 仅 run_all.sh 与 test_run_all.py）。干净树 `f79eafd`：ledger 74、corpus_compiler 68、validation 87、dataset_compiler 125、contract_registry 45、orchestrator 100 均 OK；gate/acceptance/conformance 独立；生产代码 `.store/.objects` 仅 ports.py 适配器与 acceptance.py 检测正则字面量；`orchestrator-gate.sh` `pass=5 fail=0 blocked=1` exit 2；`contract-registry.sh` `pass=3 fail=0 blocked=2` exit 2；m3/m5/m8 判据均 exit 2；`verify-T.sh` 0 FAIL、`mutations.sh` 109/109、`schemas/verify.sh` 0、`check_d16.py` OK、`check_interfaces.py` 24 PASS。
- `run_all.sh` 改前改后（`c72c90e` → `f79eafd`）：均 `pass=2 fail=1 blocked=8`，行数 12→12，除 20.1/20.10 外无变化。20.1 `BLOCKED 前置缺失: M4 Knowledge Extraction；Local Orchestrator 首切片已串联 m1–m3、m5 Gate，m4/m6 未登记生产 Module`（第 43 条不伪造 PASS）；20.10 `BLOCKED 前置缺失: Contract Registry；m3/m5/m8 入口直接访问 Ledger 内部（运行时列示，共 15/12/15 处）`（第 38/39 条）。
- 执行方两处实现裁量接受：acceptance.py 按第 59 条豁免 import 加工模块；端口泄漏列示入口文件命中优先、总数运行时计数。

impl-08（Local Orchestrator + Contract Registry 首切片）`ACCEPTED`。act/10（Ledger 公开读方法）、act/11（Gate 报告落盘）`DEFERRED`。§20.1、§20.10 仍 BLOCKED，不宣称关闭。
