# ACCEPTANCE：impl-06 M6 Review & Curation 最薄接入（Review & Curation 与精确失效传播）

本文件只写**审查要点与判据**，不写任何验收结论；结论与验收记录由主 Agent 填写（§5）。

## 0. 转译审查要点（主 Agent 四查）

- **忠实性**：`README.md` §1 目标、`BDD.md` 1–11、各 `act/*.yaml` 的 contract 与 `G7-RULINGS.md` §1 P1–P9、§4 impl-06、§9.3 第 34–43 条、§9.5 第 45–46 条、§9.6–§9.11 第 47–58 条逐条对应。
  - P1/第 43 条：M6 最薄接入、首纵切后；`legacy_workbench_seed`、`upstream_real` 恒 BLOCKED，不伪造 PASS。
  - P2/D-13：新 artifact_type **只提名**（`review_queue`、`reviewed_edition`、`reviewed_edition_package`、`rework_impact_report`），登记由 impl-00 `act/13.yaml` 写 `INTERFACES.md` §4；实现前 `check_interfaces.py` 末行 `fail=0` 且 exit 0、所需类型 PASS 行存在（第 54 条）。
  - P3：内容 Schema 代码草案 `0.1.0-draft`；不新增 `openspec/schemas/` 文件。
  - P5：只认 succeeded 上游；M5 另须 `validation.passed == true`（第 21 条）。
  - P6：零模型调用。
  - P7：`expert_verified` 不得伪造；依赖真实签发的判定 BLOCKED（README §9）。
  - P9：不改已验收模块（`pipeline/knowledge_extraction`、`pipeline/validation`、`pipeline/orchestrator`、`pipeline/contract_registry`）。
  - 第 47/52/53/54/58 条：新类型登记模式、合成事件标注、闭集前提 `fail=0`、同阶段后续运行经 supersede。
  - 第 61 条（D-01）：Snapshot 归 M7；本包删 ACT 10（`act/10.yaml` 标 WITHDRAWN），`snapshot_projection` 恒 BLOCKED（前置缺失: M7 创世汇编）。
  - 第 62 条（D-08）：采纳 B——M6 不改 M4 修订状态（`rework.py` 不含 `invalidate_revision`），旧 candidate_set 由 M4' 以 `supersede_revision` 替换。
  - 第 67 条（F1/D-04）：队列以 `review_events.required_decision_types` 为唯一来源，M6 不另立映射；BDD/期望/计数按推导重算（队列 5、失效计数 3/3/3/4/0.75）。
  - 第 68 条（F2）：事件锚点恒为 `seen_revision_id`；`modify` 另携 `modified_revision_id`（纳入 `decision_entries` 键集，Gate `decision_anchoring` 校验）。
  - 第 69 条（N1）：carried 条目 `seen_revision_id` 保持首审旧修订，另携 `carried_to_revision_id`/`carried_from_revision_id`/`carried_content_hash`；Gate `decision_anchoring` 条件式；`fold_decisions` 对 carried 不以 seen 不等报 REF_001。
- **覆盖性**：BDD 各条都能在某个 `act/*.yaml` 的 `tests` 用例名或 `verify` 命令上找到落点；K1–K3 串行前置与 `depends_on` 一致；`README.md` §1 完成判据覆盖单测（≥145，第 72、74、75 条）、`m6-data-fields.sh`、`run_all.sh` 基线、`m3-coverage.sh` 基线四项。
- **可执行性**：每个 ACT 有 `scope.write`、先红后绿的具名用例名、contract（函数签名/规则/检查名/退出码）、精确 `verify`、`commit.add`/`message`；用例数阈值等于具名用例实际累计（23/48/63/71/86/98/107/109(06a，第 72 条)/121/124(09a，第 74 条)/135/136(09b，第 75 条)/145，F4）；ACT 时长 ≤ 110 分钟；回归取行用 `2>&1 | grep -E "^(Ran|OK|FAILED)"`。ACT 10 已 WITHDRAWN（第 61 条），不计入阈值累计。
- **独立性**：`gate.py` 不 import `model`/`propagation`/`step`/`rework`；`acceptance.py` 不 import `gate`/`model`/`propagation`/`step`/`rework`，不读 `close_review` 返回的 gate 报告；`propagation.py` 与 `rework.py` 不调用 `invalidate_revision`。
- **写范围**：仅 `pipeline/review/**` 与 `openspec/acceptance/m6-data-fields.sh`；与 impl-08 零交集；不写 `run_all.sh`、fixture、已验收模块。

派发前核对（主 Agent 脚本）：11 份 act YAML（含 WITHDRAWN 的 `act/10.yaml`）可解析；`ACT.yaml` 的 `acts` 与 `act/*.yaml` 一一对应；impl-05/impl-03 状态 `ACCEPTED`；`check_interfaces.py` 末行 `fail=0` 且 exit 0 且 §4 已含本包新类型（第 54 条）；`m6-data-fields.sh` 尚不存在（exit 127）；fixture `spans.yaml` sha256 = `ec6d77b9…44ef`；第 61/62 条已裁定（ACT 10 不派发、M6 不改 M4 状态）。

## 1. 范围核对

每个提交只含该 ACT `commit.add` 路径；`pipeline/review/` 之外仅 `openspec/acceptance/m6-data-fields.sh`（ACT 11）；`run_all.sh`、`m3-coverage.sh`、规格、Schema、fixture、`pipeline/ledger`、`pipeline/corpus_compiler`、`pipeline/knowledge_extraction`、`pipeline/validation`、`pipeline/dataset_compiler`、`pipeline/orchestrator`、`pipeline/contract_registry`、台账文件未动；无 `var/`、`__pycache__`；`git diff --check` 通过。

## 2. 门禁与判据（`git archive` 干净树）

- `ACT.yaml` 全部 `gates` 绿；四套 `unittest`（ledger、corpus_compiler、knowledge_extraction、validation）与 `pipeline/review/tests` 全过且用例数达 `TDD.md` §1 阈值；`m6-data-fields.sh` → `SUMMARY pass=11 fail=0 blocked=3`、exit 2；`run_all.sh` → 与 `BASELINE_RUN_ALL` 逐字相同；`m3-coverage.sh` → 与 `BASELINE_M3` 相同。
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

- K1、K2、K3 各自通过后，由主 Agent 在 §5 记名并写 `ACCEPTED`；执行者不得自记。ACT 10 已 WITHDRAWN（第 61 条），不派发。
- 任一 FAIL 视为未通过，返工另立 ACT；`snapshot_projection`（第 61 条，M7 落地前）、`legacy_workbench_seed`、`upstream_real` 三项 BLOCKED 不视为失败，但必须确属 §19 第一列差距；`run_all.sh` 的既有 BLOCKED/FAIL 不视为失败。
- 全部通过后，由主 Agent 同步 `SUBAGENT_TODO.md`、`HANDOFF.md` 并据此勾选 `PLAN`/`G7-PLAN` 相应项。

## 5. 验收记录

§5 验收记录由主 Agent 填写。

### 5.1 K1（2026-09-13，主 Agent 独立验收，`git archive 4a5e86f` 干净树）

执行者：agy 会话 `w5h1`（ACT 03 中途按用户要求由 Gemini 3.1 Pro High 切换为 Gemini 3.8 Flash Medium，续接原对话）；工作包 R3 READY `4390b6c`，前置 impl-00 act/13 `ACCEPTED`。

- 范围：ACT 01 `bc75e87`（`__init__`、`errors`、`model`、`tests/__init__`、`tests/test_model`）、ACT 02 `6904e5a`（`gate`、`tests/test_gate`）、ACT 03 `4a5e86f`（`propagation`、`tests/test_propagation`），全部在 `pipeline/review/` 内；Ledger/M3/M4/M5/M8/Orchestrator/Schema/fixture/`run_all.sh` 改动 0。
- Red（执行方原文）：ACT 01、02、03 各 `FAILED (errors=1)`（新测试模块导入失败）；Green 分别 `Ran 23`、`Ran 48`、`Ran 63` OK。执行方开工基线初写「run_all 未执行，假设一致」，经主 Agent 更正后补跑原文（`schemas/verify.sh` 0、`run_all` `pass=2 fail=1 blocked=8`）。
- 复验：`pipeline/review/tests` `Ran 63` OK（阈值 23/48/63）；具名用例 63 个与 act/01–03 `tests` 逐字一致（无缺无多）；ledger 74、corpus_compiler 68、knowledge_extraction 133、validation 87 均 OK。
- 独立性与纯函数：`gate.py` 不 import `model/propagation/step/rework`（0 处）；`propagation.py` 不写 Ledger、不调 `invalidate_revision`（0 处）；`model.py` 复用 `review_events.build_review_decision` 与 `required_decision_types`（第 67 条）；各源文件副作用/网络、`_fixture`、裸 except 均 0。
- 门禁：`check_interfaces` `pass=29 fail=0`；`schemas/verify.sh` 0；`verify-T.sh` `FAIL 合计: 0`；`mutations.sh` `109/109 rejected`；`run_all.sh` `pass=2 fail=1 blocked=8`。

K1 `ACCEPTED`。K2 已放行。

### 5.2 K2（2026-09-13，主 Agent 独立验收，`git archive 5f32628` 干净树）

执行者：agy 会话 `w5h1`（Gemini 3.8 Flash Medium）。

- 范围：ACT 04 `811b137`（`inputs.py`、`testing/` 桩与合成数据、`tests/test_inputs.py`）、ACT 05 `27bcbf7`（`step.py`、`tests/test_step_open.py`）、ACT 06 `9c28d96`（`step.py`、`tests/test_step_close.py`）、ACT 07 `5f32628`（`console.py`、`__main__.py`、`tests/test_console.py`），全部在 `pipeline/review/` 内；共享面改动 0。
- Red（执行方原文）：各 ACT `FAILED (errors=1)`；Green 递增至 `Ran 107` OK。
- 复验：`pipeline/review/tests` `Ran 107` OK（阈值 107）；具名用例 107 个与 act/01–07 逐字一致；ledger 74、corpus_compiler 68、knowledge_extraction 133、validation 87 OK；Gate 独立性、propagation 不写 Ledger 保持；各源文件副作用/网络、`_fixture`、裸 except 0；生产代码不 import `testing/`；`testing/data` 五个合成文件均标 `synthetic_fixture: true`（P7）；`check_interfaces` `fail=0`；`mutations` 109/109；`run_all` `pass=2 fail=1 blocked=8`。
- 矩阵外端到端（复用 `test_step_close` setUp，真实 M3/M4/M5 桩驱动）：开审前 Ledger 81 条修订状态在关审后全部不变（第 62 条成立）；未决项直接关审 → `ReviewRefused(REF_001)`；关审成功，approved `as_…001/as_…003/sv_…1`、rejected `as_…002`、`unresolved_count 0`，与合成金标一致。**但**真实 `reviewed_edition` 经 M7 `validate_reviewed_edition` → `SCH_001`，缺 5 个 §5.3 顶层键；`reviewed_edition_package` 键为 `{schema_version, reviewed_edition_revision_id, edition_part_id, counts}`，与 §5.3 索引不符。
- 结论：K2 功能与事务正确，但下游契约键不符 → 裁定 72，返工提交 06a（先于 K3）。

K2 `REWORK`（06a）。

### 5.3 返工 06a（2026-09-13，主 Agent 独立验收，`git archive 3753034` 干净树）

执行者：agy 会话 `w5h1`（Gemini 3.8 Flash Medium），依裁定 72。

- 范围：`3753034` 恰为 `pipeline/review/step.py`、`pipeline/review/tests/test_step_close.py`；测试文件无删除行（改动断言清单：无）；`console.py` 未改。
- 报告：执行方只写了「06a 完成」标题，未附 Red/Green 原文。主 Agent 独立复现 Red：在 `5f32628`（修正前）树上叠加 `3753034` 的测试文件，只跑两个新增具名用例 → 两例 `FAIL`（`Lists differ`：旧 `reviewed_edition` 顶层键起于 `approved`；旧包键为 `counts`/`edition_part_id`/…），`FAILED (failures=2)`，证明新用例确实检验修正点。
- 复验：`pipeline/review/tests` `Ran 109` OK（阈值 109）；具名用例 = act/01–07 的 107 个 + 第 72 条授权新增 `test_reviewed_edition_top_level_keys_match_contract`、`test_reviewed_edition_package_keys_match_contract`；ledger 74、corpus_compiler 68、knowledge_extraction 133、validation 87 OK；Gate 独立性、propagation 不写 Ledger、副作用/网络/`_fixture`/裸 except 均 0；共享面改动 0；`check_interfaces` `fail=0`；`schemas/verify.sh` 0；`verify-T.sh` `FAIL 合计: 0`；`mutations` 109/109；`run_all` `pass=2 fail=1 blocked=8`。
- 跨模块端到端（真实 M3/M4/M5 桩 → M6 `close_review`）：`reviewed_edition` 顶层键序与 §5.3 逐字相同（`schema_version "0.1.0-draft"`、`edition_part_artifact_id art_…e1`、三个上游修订号取自冻结输入）；`reviewed_edition_package` 键序与 §5.3 逐字相同（`decision_count 5`、`approved_count 3`、`rejected_count 1`、`unresolved_count 0`、`decision_revision_ids` 5 条）；二者分别通过 M7 `model.validate_reviewed_edition` 与 `validate_reviewed_package`。

06a `ACCEPTED`，K2 连同 06a 视为 `ACCEPTED`。K3 已放行。

### 5.4 K3（2026-09-13，主 Agent 独立验收，`git archive caf599e`/`4e0cf93`/`b5be811` 干净树）

执行者：K3 放行后 agy 额度耗尽（「Individual quota reached」，零产出），按用户决定改由 tmux + `cmd --yolo` DeepSeek V4.1 Flash，会话 `w5h3`。执行中两次停手上报 → 裁定 74（carried × modify）、75（恢复后结审折叠继承决定）。

- 范围：ACT 08 `caf599e`（`rework.py`、`tests/test_rework.py` 等）；09a `cb6ea8e`（`model.py`、`gate.py`、`tests/test_model.py`、`tests/test_gate.py`）；ACT 09 `4e0cf93`（`console.py`、`rework.py`、`step.py`、`testing/upstream_stub.py`、`tests/test_rework_review.py`）；09b `feb99df`（`step.py`、`tests/test_step_open.py`）；ACT 11 `b5be811`（`acceptance.py`、`tests/test_acceptance.py`、`openspec/acceptance/m6-data-fields.sh` 100755）。全部在授权范围内；测试文件删除行仅 09b 的 1 行 import 扩写（加 `close_review`），无既有断言删改；`run_all.sh` 与共享面改动 0。
- Red（执行方原文）：ACT 08 `FAILED (errors=1)`；09a `Ran 3 … FAILED (failures=1, errors=1)`；ACT 09 `FAILED (errors=1)`（另记裁定前 `failures=1, errors=4` 阻断原文）；09b `FAILED (errors=1)`；ACT 11 见回报。Green 依次 121、124、135、136、145 OK。
- 复验：`pipeline/review/tests` 依次 `Ran 121`（caf599e）、`Ran 135`（4e0cf93）、`Ran 145`（b5be811）OK，阈值 121/135/145 达标；具名用例 143 个与 act/01–09、11 逐字一致，另 2 个为第 72 条授权；ledger 74、corpus_compiler 68、knowledge_extraction 133、validation 87 OK；Gate 独立性、propagation 不写 Ledger、各源文件副作用/网络/`_fixture`/裸 except 0；`acceptance.py` 不 import `gate/model/propagation/step/rework`、不读 `close_review` 的 gate 报告；`m6-data-fields.sh` 调仓库内规范 `mini_ed01/verify.sh`；`check_interfaces` `fail=0`；`schemas/verify.sh` 0；`verify-T.sh` `FAIL 合计: 0`；`mutations` 109/109；`m6-data-fields.sh` `SUMMARY pass=11 fail=0 blocked=3`、exit 2（BLOCKED：`snapshot_projection`、`legacy_workbench_seed`、`upstream_real`）；`run_all` `pass=2 fail=1 blocked=8`。
- 裁定 74 端到端（`4e0cf93` 干净树，复用 `TestReworkReview`）：复审中首审 modify 的 `as_qizheng_000003` 为 carried，`modified_revision_id` 与 `current_target_revision_id` 等于首审人工修订，复审 approved 指向该修订且其 `artifact_type == reviewed_candidate`（人工修订未丢失）；复审 `reviewed_edition`/package 通过 M7 两个校验（第 72 条在返工模式下未回退），`rework_impact_report_revision_id` 已填；standings 3 active + 2 carried。复审过程中旧 M4 `candidate_set` 修订由测试桩驱动的 M4' 以 `supersede_revision` 置 superseded（第 62 条口径：M6 生产代码不含 `supersede_revision`/`invalidate_revision`）。
- ACT 08 说明：act/08 要求 `rework.request_correction` 带 span 存在性前置，K2 已验收的实现落在 `step.py` 且无该检查；执行方以 `rework.request_correction` 薄封装先校验再委托 `step.request_correction`，真实人工路径 `console.py:425` 走封装——采纳，不另立裁定。
- 矩阵外篡改（`b5be811` 副本，改合成金标 `expected_review.yaml`）：T1 改 `first_review.decisions 5→6` → 仍全过（acceptance 不比对该计数，见观察）；T2 改 `rereview.carried_forward 2→3` → `FAIL rework_rereview_scope`、exit 1；T3 从 `first_review.approved` 删 `as_qizheng_000003` → `FAIL reviewed_edition_contract`、exit 1。
- 观察（建议，不阻断）：金标 `first_review.decisions`/`checkpoints` 未被 acceptance 直接比对（`checkpoint_per_decision` 另按 Ledger 独立重算）；`cb6ea8e` 在 `model.py` 留 1 处尾随空白；`snapshot_projection` 的 BLOCKED 文案「前置缺失: M7 创世汇编」在 impl-07 G0 已验收后已过时，`upstream_real` 文案仍写「M4 Knowledge Extraction」前置缺失，均宜在转判 ACT 中更新。

K3 `ACCEPTED`。**impl-06 M6 最薄接入（K1、K2+06a、K3+09a/09b）全部 `ACCEPTED`**。

### 5.5 act/12（2026-09-15，主 Agent 独立验收，`git archive dc83cf9` 干净树）

判定：**ACCEPTED**。执行器：agy / Gemini 3.8 Flash Medium（前一执行器 OpenCode/MiMo 免费额度耗尽后切换）。

范围（5 文件）：`pipeline/review/acceptance.py`、`model.py`、`tests/test_acceptance.py`、`openspec/acceptance/m6-data-fields.sh`、外加第 87 条授权的 `act/12.yaml` 与 `TDD.md`。第 87 条授权范围外文件数 **0**。

第 87 条落地核对：

- `first_review_counts` 为 `COMPUTED_CHECKS` 的**独立条目**（`acceptance.py:872`），未被折进任何别的检查。`COMPUTED` 13 项、`BLOCKED` 2 项（`legacy_workbench_seed`、`upstream_real`）。
- 三处断言（`test_acceptance.py:60`、`:163`、`:360`）全部为 `SUMMARY pass=13 fail=0 blocked=2`；旧名 `pass_12_fail_0_blocked_2` 与 `eleven_pass_three_blocked` 残留 **0**（已按裁决分别更名为 `test_shell_summary_pass_13_fail_0_blocked_2`、`test_fixture_yields_thirteen_pass_two_blocked_exit_2`）。
- 11 条具名用例逐条存在（四条正向投影 + 四条反向篡改 + `first_review_counts` 正反 + shell）。
- 独立性（第 83 条）：`_check_snapshot_projection` 只用 `run_m7` 返回值定位 `snapshot_revision_id`，判据取自 Ledger 回读的 Snapshot 与 `reviewed_edition`，未复用 `run_m7` 的 gate/report。

测试与脚本：`pipeline/review/tests Ran 156 OK`（阈值 ≥155 达标）；`pipeline/assembly/tests Ran 96 OK`（g0-06 未回退）；`m6-data-fields.sh SUMMARY pass=13 fail=0 blocked=2` exit=2；`m7-assembler.sh SUMMARY pass=11 fail=0 blocked=5` exit=2；`check_interfaces pass=36 fail=0`；`schemas/verify.sh` exit 0；`run_all.sh SUMMARY pass=2 fail=1 blocked=8`。

矩阵外篡改（主 Agent 自建）：

| 篡改 | 结果 | 结论 |
|---|---|---|
| 金标 `expected_review.yaml` 的 `approved` 改为不存在的对象号 | `FAIL reviewed_edition_contract 首审 approved 与 expected 不符`；`snapshot_projection` 仍 PASS | 正确：`snapshot_projection` 比对的是「M6 产出 → M7 投影」这一步，不与金标比对，改金标本就不应令其转红；金标漂移由 `reviewed_edition_contract` 兜住 |
| `m6_decisions.yaml` 把一条 `accept` 改为 `reject` | 同上 | 正确：该改动同时改变比对两侧，两侧仍自洽 |
| **主 Agent 在进程内直接篡改 Ledger 中的 Snapshot 修订**（删去一条 assertion 并改写 `sha256`），重跑 `_check_snapshot_projection` | 由 `[]` 转为 2 条错误：`approved assertions 与 Snapshot assertions 不符: approved=['as_qizheng_000001','as_qizheng_000003'] vs snap=['as_qizheng_000001']`、`evidence_links 不一致: …` | **判定load-bearing，非空转**；该篡改点与执行方的反向用例一致，但由主 Agent 独立构造 |

接手情况：本 ACT 由前一执行器做到一半（约 185 行未提交改动）后因额度耗尽中断，agy 接手续做。接手方自行发现并修复了前者两处实现缺陷（`_check_snapshot_projection` 取到被 superseded 的 candidate_set；`_check_first_review_counts` 对 `int` 执行 `len()`），并把前者「只断言 CLI 输出字符串」的空转测试全部重写为真实 Ledger 上的正反断言。Red 原文、七条门槛输出、改名对照表均贴入回报，纪律达标。

**至此 impl-06 的 K3 四个 ACT（08、09、11、12）全部完成，impl-06 M6 全部 `ACCEPTED`。** `snapshot_projection` 由 BLOCKED 转判 PASS，M6 剩余 BLOCKED 两项（`legacy_workbench_seed`、`upstream_real`）依赖旧工作台数据迁入与第 80 条真实签发决定表，属用户待办与后续波次。
