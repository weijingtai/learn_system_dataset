# BDD：impl-06 M6 Review & Curation（READY_FOR_REVIEW）

场景使用 `pipeline/review/testing/data/` 合成数据（D-11，非生产）。候选对象取自 M4 `candidate_set`：`assertion` `as_qizheng_000001`（证据 p0003_s04、s08）、`as_qizheng_000002`（p0003_s03、s05）、`as_qizheng_000003`（p0001_s02）、`school_view` `sv_00000000000000000000000000000001`（主体 as_qizheng_000001，来源 p0003_s08）。

**队列推导（第 67 条）**：必审维度以已验收 `pipeline.knowledge_extraction.review_events.required_decision_types` 为唯一来源（P9），M6 不另立映射。逐对象推导：

| 对象 | kind | school_ids / 来源 | required_decision_types |
|---|---|---|---|
| as_qizheng_000001 | assertion | `school_ids=[]` | `review_source_fidelity` |
| as_qizheng_000002 | assertion | `school_ids=[]` | `review_source_fidelity` |
| as_qizheng_000003 | assertion | `school_ids=[]` | `review_source_fidelity` |
| sv_…1 | school_view | 流派视图 | `review_source_fidelity`, `review_school_attribution` |

→ 队列 **5 项**（3 个 assertion 各 1 + school_view 2）；首审 5 条决定、Checkpoint 6 个（1 建队 + 5 决定）。

合成人工决定一律标注 `synthetic_fixture: true`（写在外层测试数据，不进入 `review_decision` 顶层键，第 52/53 条）；验收不得把它计为真实 `expert_verified`（P7）。

## 1. 队列、决定与内容哈希（ACT 01）

- 1.1 Given 4 个候选（3 assertion + 1 school_view）与上述推导，When `build_review_queue(candidates=…, seen_revision_id=…)`，Then 队列 5 项、项号为 `<entity_id>#<decision_type>`、`seen_artifact_revision_id` 等于传入 `seen_revision_id`，两次调用结果相同。
- 1.2 Given 非法 `entity_id`、重复 `entity_id`、未知 kind，Then 分别 `ID_001`、`ID_002`、`SCH_002`。
- 1.3 Given `accept` 带 `modified_revision_id`、`modify` 缺 `modified_revision_id`、carried 缺 `carried_from_revision_id`、空 rationale、`school_dispute` 配非流派维度、表外 verdict，Then `review_events.build_review_decision` 与 `model.decision_entry` 一律拒绝（不新造事件形态；第 68 条）。
- 1.4 Given 同一队列项先 `request_evidence` 后 `accept`，When `fold_decisions`，Then 立场为 accept、历史两条都保留；Given 队列外项号或 seen 修订不符，Then `REF_001`。
- 1.5 Given 只改字框几何的 Span，Then 引用它的候选 `content_hash` 不变；Given 改一个字，Then 哈希改变；Given 证据 offset 越界或 Span 不存在，Then 拒绝。

## 2. 独立 Review Gate（ACT 02）

- 2.1 Given 首审金标（3 获批、1 驳回、5 决定），Then 9 项检查全过、`review=passed`。
- 2.2 Given M5 `validation.passed` 非真、队列漏项、决定 seen 锚错、modify 缺 `modified_revision_id`、accept 带 `modified_revision_id`、decision_type 表外、有未决/补证/待复核项、获批对象含 reject 维度、驳回对象被删、获批证据引文哈希不符、计数错，Then 各自指定检查失败、Gate `failed`。
- 2.3 Gate 模块不 import `model`、`propagation`、`step`、`rework`。

## 3. 精确失效传播（ACT 03）

- 3.1 Given 修正 p0003_s08 一个字、p0003_s05 字框 x+1，When `propagate`，Then 变更 Span = {s05, s08}；可达对象 = {as_qizheng_000001, as_qizheng_000002, sv_…1}。**推导**：invalidated = 可达候选 3（as_…001/as_…002/sv_…1）+ 校验条目 0（首切片 M5 `scope: corpus_only`，`validation_entries=[]`）= **3**；carried_forward = 不可达候选 1（as_…003）+ 内容等价的可达决定 1（as_…002 reject，仅字框几何变化）+ 不可达决定 1（as_…003）= **3**；needs_review = 内容变化的决定 **3**（as_…001 的 source_fidelity、sv_…1 的 source_fidelity 与 school_attribution）；valid_object_count = 候选 4 + 校验条目 0 = **4**；ratio = 3/4 = **0.75**；warnings = `[rework_threshold_exceeded]`（round 1，ratio ≥ 0.30）。
- 3.2 Then as_…001 与 sv_…1 的决定降级 `needs_review`（原因 `content_changed`，sv_…1 两条各计）；as_…002 的 reject 决定 `carried_forward`（可达但内容等价）；as_…003 对象与其决定 `carried_forward`（不可达），均记 `carried_from_revision_id` 与触发 CorrectionRequest。
- 3.3 Given p0003_s06 文字变长导致其后 Span offset 平移，Then 只有 s06 算变更，s07 以后不算。
- 3.4 Given 被引 Span 被删除，Then 相关决定降级 `needs_review`（原因 `target_removed`）。
- 3.5 Given `rework_round_before=2`，Then `rework_round=3` 且即使比例 < 30% 也告警；Given 比例 29%，round 1，Then 无告警。
- 3.6 `propagate` 签名中不存在由操作者提供对象清单的参数；M6 不逐对象 `invalidate_revision`（D-08 推荐 B）。

## 4. 上游桩与输入解析（ACT 04）

- 4.1 Given 空 Ledger，When `seed_upstream`，Then m1、m2 灌入、真实 `run_m3` 成功、真实 `run_m5` 成功、合成 `candidate_set`（4 对象，含 school_view）经真实 Ledger 写路径注入为 succeeded 的 m4 运行、`candidate_package`/`validation_package` 绑定。
- 4.2 When `resolve_m6_inputs`，Then 返回 corpus/spans/候选对象索引/校验包/血缘修订，本函数零写入。
- 4.3 Given 缺 m5、M5 `validation.passed=false`、M5 包与 m3 血缘不符、M4 包与 m3 血缘不符、M6 已被 succeeded 运行封存，Then 分别拒绝且 Ledger 无新增写入；同阶段后续运行经 `supersede_step_run`（第 58 条）。

## 5. 开审、逐条决定与恢复（ACT 05）

- 5.1 When `open_review`，Then StepRun `awaiting_human`、冻结输入（m3 包、spans、m4 包、candidate_set、m5 包、gate_results 等）、`review_queue` 5 项且 sealed、1 个 Checkpoint、返回 token。
- 5.2 When 逐条 `record_decision` 5 次，Then 5 个 `human_event` sealed、`human_events` 表 5 行且 decision_type 与队列项一致、Checkpoint 共 6 个成链、`human_decisions` 每次 +1、`pending_queue` 每次 -1；事件形态由 `review_events.build_review_decision` 产出。
- 5.3 Given 错 token、队列外项号、非法 verdict，Then 拒绝且不写修订、不写 Checkpoint。
- 5.4 Given 第 2 条决定已被 Ledger 接受但 Checkpoint 未写（注入异常），When `recover_review`，Then 先补写 Checkpoint、新 StepRun supersedes 旧运行、2 条旧决定作为冻结输入不重录、队列只剩 3 项、返回新 token；旧运行保持 `awaiting_human`（D-15 A，断言现状）。
- 5.5 `modify` 决定先封存 `reviewed_candidate`（`entity_id` 与 kind 不变）；决定事件的 `target.artifact_revision_id` 恒为 seen 修订，`decision_entry.modified_revision_id` 指向 `reviewed_candidate`（第 68 条），`reviewed_edition.decisions.current_target_revision_id` 取其值。

## 6. 结审与 ReviewedEdition（ACT 06）

- 6.1 Given 5 条决定齐全，When `close_review`，Then token 被消费、Gate 通过、`reviewed_edition` sealed（3 获批、1 驳回）与 `reviewed_edition_package` sealed、m6 StagePackage 过 Schema、Transformation `review_candidates` 的 `human_event_revision_ids` 等于全部决定、StepRun `succeeded`。
- 6.2 Given 仍有未决项或补证项，Then `close_review` 拒绝、token 未消费、StepRun 仍 `awaiting_human`。
- 6.3 Given 注入 Gate 失败，Then StepRun `failed`、失败报告 sealed、无 m6 StagePackage。
- 6.4 获批 assertion 的证据链接能在 `corpus_spans` 中按 offset 截出引文且哈希一致；驳回对象保留在包内。

## 7. 命令行 Review Console（ACT 07）

- 7.1 `open` 输出末行 `M6 AWAITING <srun> token=<token> pending=5`，退出 0；无上游时 `M6 REFUSED …` 退出 2。
- 7.2 `show` 打印目标内容、每条证据的 span_id、页、line_id、行框、image_sha256、引文和 M5 条目；执行前后 Ledger 各表行数不变。
- 7.3 `decide` 与 `decide-batch --from-file` 每条输出 `M6 DECIDED <rev> remaining=<n>`；批文件第 3 条非法时停在第 3 条，前 2 条已落盘。
- 7.4 `close` 成功 `M6 OK <srun> approved=3 rejected=1 decisions=5` 退出 0；有未决 退出 2；Gate 失败 退出 1。

## 8. CorrectionRequest 与失效传播运行（ACT 08）

- 8.1 Given 审核中对 p0003_s08 发起 `request_correction`，Then 记为 `human_event`（`event_kind=correction_request`）、Checkpoint +1、不阻断后续决定；`close_review` 后 `reviewed_edition.correction_request_revision_ids` 含该修订（D-10 A）。
- 8.2 Given 首审已 succeeded 且桩生成修正后的 m3 修订，When `run_rework_propagation`，Then 新 StepRun supersedes 首审、3.1 的计数成立（3/3/3/4/0.75）、报告 `invalidated` 含 3 个可达候选对象、`rework_impact_report` sealed、Checkpoint 引用该报告、Transformation `propagate_invalidation` 的人工事件含 CorrectionRequest；**M6 不调用 `invalidate_revision`，Ledger 中无任何修订 status='invalidated'**（D-08 推荐 B）；旧 `candidate_set` 的物理替换由 M4' 重跑以 `supersede_revision` 完成（ACT 09）。
- 8.3 Given CorrectionRequest 列出的 Span 在新旧 corpus 中没有变化，Then StepRun `failed`、检查名 `correction_scope`。

## 9. 复审只重放待复核项（ACT 09）

- 9.1 Given 报告有告警且未确认，When `open_rework_review`，Then 拒绝且零写入；确认后先写 `rework_threshold_ack` 事件。
- 9.2 Then 复审队列只有 3 项（as_…001#source_fidelity、sv_…1#source_fidelity、sv_…1#school_attribution），`seen_artifact_revision_id` 指向 M4' 新修订；2 条继承决定（as_…002、as_…003）不重录。**carried 条目（第 69 条）**：`seen_revision_id` 保持首审审核者实际所见的**旧**修订（不得改写为新修订），`carried_to_revision_id` = 复审队列项当前（新）修订，`carried_from_revision_id` = 首审决定事件修订，`carried_content_hash` = 该对象旧修订哈希（与当前修订相等，故 carried）。
- 9.3 When 三项重新 accept 并 `close_review`，Then 新 `reviewed_edition` 中 5 条立场决定：3 `active`、2 `carried_forward`（carried 项 `seen_revision_id` 为首审旧修订，带 `carried_from_revision_id`/`carried_to_revision_id` 与 `trigger_correction_request_id`（第 69 条）），`rework_impact_report_revision_id` 非空。

## 10. Snapshot 直通投影（已撤回，第 61 条）

- WITHDRAWN：`CanonicalKnowledgeSnapshot` 归 M7（M7 创世汇编薄切片由 impl-07 先行），本包删除 ACT 10；Snapshot 验收项 `snapshot_projection` 在 M7 落地前恒 BLOCKED（前置缺失: M7 创世汇编）。

## 11. 验收脚本（ACT 11）

- 11.1 Given 规范 fixture，When `m6-data-fields.sh`，Then 11 PASS、`snapshot_projection`（第 61 条）、`legacy_workbench_seed` 与 `upstream_real` 三项 BLOCKED、exit 2。
- 11.2 Given 桩期望文件被改、决定修订被删一条、准备阶段异常，Then exit 1；缺 fixture exit 3。
- 11.3 Given 副本 `verify.sh` 被换成假脚本且数据被改，Then 仍 `FAIL fixture_host`、exit 1。
