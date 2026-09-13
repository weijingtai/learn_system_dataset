# ACCEPTANCE：impl-06 M6 Review & Curation 最薄接入（Review & Curation 与精确失效传播）

本文件只写**审查要点与判据**，不写任何验收结论；结论与验收记录由主 Agent 填写（§5）。

## 0. 转译审查要点（主 Agent 四查）

- **忠实性**：`README.md` §1 目标、`BDD.md` 1–11、各 `act/*.yaml` 的 contract 与 `G7-RULINGS.md` §1 P1–P9、§4 impl-06、§9.3 第 34–43 条、§9.5 第 45–46 条、§9.6–§9.11 第 47–58 条逐条对应。
  - P1/第 43 条：M6 最薄接入、首纵切后；`legacy_workbench_seed`、`upstream_real` 恒 BLOCKED，不伪造 PASS。
  - P2/D-13：新 artifact_type **只提名**（`review_queue`、`reviewed_edition`、`reviewed_edition_package`、`rework_impact_report`；D-01=A 时 `canonical_knowledge_snapshot`），登记由该波独占 ACT 写 `INTERFACES.md` §4；实现前 `check_interfaces.py` 末行 `fail=0` 且 exit 0、所需类型 PASS 行存在（第 54 条）。
  - P3：内容 Schema 代码草案 `0.1.0-draft`；不新增 `openspec/schemas/` 文件。
  - P5：只认 succeeded 上游；M5 另须 `validation.passed == true`（第 21 条）。
  - P6：零模型调用。
  - P7：`expert_verified` 不得伪造；依赖真实签发的判定 BLOCKED（README §9）。
  - P9：不改已验收模块（`pipeline/knowledge_extraction`、`pipeline/validation`、`pipeline/orchestrator`、`pipeline/contract_registry`）。
  - 第 47/52/53/54/58 条：新类型登记模式、合成事件标注、闭集前提 `fail=0`、同阶段后续运行经 supersede。
  - D-08：推荐 B——M6 不改 M4 修订状态（`rework.py` 不含 `invalidate_revision`）；D-01 待裁。
- **覆盖性**：BDD 各条都能在某个 `act/*.yaml` 的 `tests` 用例名或 `verify` 命令上找到落点；K1–K3 串行前置与 `depends_on` 一致；`README.md` §1 完成判据覆盖单测（≥116）、`m6-data-fields.sh`、`run_all.sh` 基线、`m3-coverage.sh` 基线四项。
- **可执行性**：每个 ACT 有 `scope.write`、先红后绿的具名用例名、contract（函数签名/规则/检查名/退出码）、精确 `verify`、`commit.add`/`message`；用例数阈值等于具名用例累计（16/36/50/58/70/80/88/98/104/110/116）；ACT 时长 ≤ 110 分钟；回归取行用 `2>&1 | grep -E "^(Ran|OK|FAILED)"`。
- **独立性**：`gate.py` 不 import `model`/`propagation`/`step`/`rework`；`acceptance.py` 不 import `gate`/`model`/`propagation`/`step`/`rework`，不读 `close_review` 返回的 gate 报告；`propagation.py` 与 `rework.py` 不调用 `invalidate_revision`。
- **写范围**：仅 `pipeline/review/**` 与 `openspec/acceptance/m6-data-fields.sh`；与 impl-08 零交集；不写 `run_all.sh`、fixture、已验收模块。

派发前核对（主 Agent 脚本）：11 份 ACT YAML 可解析；`ACT.yaml` 的 `acts` 与 `act/*.yaml` 一一对应；impl-05/impl-03 状态 `ACCEPTED`；`check_interfaces.py` 末行 `fail=0` 且 exit 0 且 §4 已含本包新类型（第 54 条）；`m6-data-fields.sh` 尚不存在（exit 127）；fixture `spans.yaml` sha256 = `ec6d77b9…44ef`；D-01 已裁定（决定 ACT 10 是否实施）。

## 1. 范围核对

每个提交只含该 ACT `commit.add` 路径；`pipeline/review/` 之外仅 `openspec/acceptance/m6-data-fields.sh`（ACT 11）；`run_all.sh`、`m3-coverage.sh`、规格、Schema、fixture、`pipeline/ledger`、`pipeline/corpus_compiler`、`pipeline/knowledge_extraction`、`pipeline/validation`、`pipeline/dataset_compiler`、`pipeline/orchestrator`、`pipeline/contract_registry`、台账文件未动；无 `var/`、`__pycache__`；`git diff --check` 通过。

## 2. 门禁与判据（`git archive` 干净树）

- `ACT.yaml` 全部 `gates` 绿；四套 `unittest`（ledger、corpus_compiler、knowledge_extraction、validation）与 `pipeline/review/tests` 全过且用例数达 `TDD.md` §1 阈值；`m6-data-fields.sh` → `SUMMARY pass=12 fail=0 blocked=2`、exit 2（D-01=A）；`run_all.sh` → 与 `BASELINE_RUN_ALL` 逐字相同；`m3-coverage.sh` → 与 `BASELINE_M3` 相同。
- `TDD.md` §2 附加判据逐条实跑；`README.md` §1 完成判据逐条复现。

## 3. 语义与质量审查清单

- 事件形态：`review_decision` 事件逐字由 `review_events.build_review_decision` 产出，顶层键恰为 `review_events._TOP_KEYS`（无多余键）。
- 纯函数性：`model.py`/`gate.py`/`propagation.py`/`snapshot.project_snapshot` 不读文件、不访问 Ledger、不取时间；无随机数。
- 状态上限 / P7：全路径后 Ledger 中 m6 修订字节不含真实 `expert_verified` 来源（测试合成事件在数据层标注 `synthetic_fixture`，不计为真实签发）；无真实签发 StepRun。
- 事务序列与 §17 一致；首审冻结输入恰 7 项；begin 之前拒绝无写入；begin 之后失败封存完整（检查名 ∈ {`input_contract`,`review_gate`,`correction_scope`,`internal`}）。
- 上游定位：`resolve_m6_inputs` 只认 succeeded 且符合 README §5.1 的 m3/m4/m5 运行；`candidate_package` 与 m3 血缘不符、M5 `gate.passed` 非真即拒绝。
- 人工决定粒度：每个 m6 运行的 Checkpoint 数 == 1 + 该运行 human_event 数；同阶段后续运行经 `supersede_step_run`/`recover_from_checkpoint`。
- D-08：M6 不调用 `invalidate_revision`；`no_cross_module_status_change` 判定 Ledger 无修订被 M6 置为 invalidated。
- 独立重算：Gate 与验收判定均不依赖被验实现自身产出的 gate 报告；`acceptance.py` 不信任被验目录自带 `verify.sh`（永远调用仓库内规范脚本）。
- 中文注释；无 `except: pass`；不新增依赖、ID 前缀、模型调用。

## 4. 结论规则

- K1、K2、K3 各自通过后，由主 Agent 在 §5 记名并写 `ACCEPTED`；执行者不得自记。ACT 10（Snapshot）依 D-01 裁定可选。
- 任一 FAIL 视为未通过，返工另立 ACT；`legacy_workbench_seed`、`upstream_real` 两项 BLOCKED 不视为失败，但必须确属 §19 第一列差距；`run_all.sh` 的既有 BLOCKED/FAIL 不视为失败。
- 全部通过后，由主 Agent 同步 `SUBAGENT_TODO.md`、`HANDOFF.md` 并据此勾选 `PLAN`/`G7-PLAN` 相应项。

## 5. 验收记录

§5 验收记录由主 Agent 填写。
