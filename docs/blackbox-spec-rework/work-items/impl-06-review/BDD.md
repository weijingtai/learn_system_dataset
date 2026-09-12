# BDD：impl-06 M6 Review & Curation（草案）

场景使用 `pipeline/review/testing/data/` 合成数据（D-11）：候选 `as_qizheng_000001`（证据 p0003_s04、s08）、`as_qizheng_000002`（p0003_s03、s05）、`as_qizheng_000003`（p0001_s02）、`sv_00000000000000000000000000000001`（主体 as_…001，来源 p0003_s08）；必审维度按 D-04 默认映射，队列 4 项。

## 1. 队列、决定与内容哈希（ACT 01）

- 1.1 Given 4 个候选与默认映射，When `build_review_queue`，Then 队列 4 项、项号为 `<entity_id>#<decision_type>`、`seen_artifact_revision_id` 等于候选修订，两次调用结果相同。
- 1.2 Given 非法 `entity_id`、重复 `entity_id`、未知 kind、映射含表外 decision_type，Then 分别 `ID_001`、`ID_002`、`SCH_002`、`SCH_002`。
- 1.3 Given `amend` 缺 `amended_revision_id`、`accept` 带 `amended_revision_id`、空 rationale、流派归属 accept 缺 `changes_current_judgment`、非流派决定带该字段、表外 verdict，Then `decision_event` 一律拒绝。
- 1.4 Given 同一队列项先 `request_evidence` 后 `accept`，When `fold_decisions`，Then 立场为 accept、历史两条都保留；Given 队列外项号或 seen 修订不符，Then `REF_001`。
- 1.5 Given 只改字框几何的 Span，Then 引用它的候选 `content_hash` 不变；Given 改一个字，Then 哈希改变；Given 证据 offset 越界或 Span 不存在，Then 拒绝。

## 2. 独立 Review Gate（ACT 02）

- 2.1 Given 首审金标（3 获批、1 驳回、4 决定），Then 9 项检查全过、`review=passed`。
- 2.2 Given M5 未通过、队列漏项、决定锚点修订错、decision_type 表外、有未决/补证/待复核项、获批对象含 reject 维度、驳回对象被删、获批证据引文哈希不符、流派视图获批但 `changes_current_judgment` 为空、计数错，Then 各自指定检查失败、Gate `failed`。
- 2.3 Gate 模块不 import `model`、`propagation`、`step`。

## 3. 精确失效传播（ACT 03）

- 3.1 Given 修正 p0003_s08 一个字、p0003_s05 字框 x+1，When `propagate`，Then 变更 Span = {s05, s08}；可达对象 = {as_…001, as_…002, sv_…1}；`invalidated_count=6`、`carried_forward_count=3`、`needs_review_count=2`、`valid_object_count=8`、`invalidated_ratio=0.75`、`warnings=[rework_threshold_exceeded]`。
- 3.2 Then as_…001 与 sv_…1 的 accept 决定降级 `needs_review`（原因 `content_changed`）；as_…002 的 reject 决定 `carried_forward`（可达但内容等价）；as_…003 对象与其 amend 决定 `carried_forward`（不可达），均记 `carried_from_revision_id` 与触发 CorrectionRequest。
- 3.3 Given p0003_s06 文字变长导致其后 Span offset 平移，Then 只有 s06 算变更，s07 以后不算。
- 3.4 Given 被引 Span 被删除，Then 相关决定降级 `needs_review`（原因 `target_removed`）。
- 3.5 Given `rework_round_before=2`，Then `rework_round=3` 且即使比例 < 30% 也告警；Given 比例 29%，round 1，Then 无告警。
- 3.6 `propagate` 签名中不存在由操作者提供对象清单的参数。

## 4. 上游桩与输入解析（ACT 04）

- 4.1 Given 空 Ledger，When `seed_upstream`，Then m1、m2 灌入、真实 `run_m3` 成功、m4/m5 StepRun `succeeded`、4 个 `knowledge_candidate` 修订 sealed、`validation_package` 绑定候选包。
- 4.2 When `resolve_m6_inputs`，Then 返回 corpus/spans/候选包/4 候选修订/校验包，本函数零写入。
- 4.3 Given 缺 m5、M5 `gate.passed=false`、M5 绑定的候选包不同、候选修订被 invalidated、M6 已被 succeeded 运行封存，Then 分别拒绝且 Ledger 无新增写入。

## 5. 开审、逐条决定与恢复（ACT 05）

- 5.1 When `open_review`，Then StepRun `awaiting_human`、冻结 8 个输入、`review_queue` sealed、1 个 Checkpoint、返回 token。
- 5.2 When 逐条 `record_decision` 4 次，Then 4 个 `human_event` sealed、`human_events` 表 4 行且 decision_type 与队列项一致、Checkpoint 共 5 个成链、`human_decisions` 每次 +1、`pending_queue` 每次 -1。
- 5.3 Given 错 token、队列外项号、非法 verdict，Then 拒绝且不写修订、不写 Checkpoint。
- 5.4 Given 第 2 条决定已被 Ledger 接受但 Checkpoint 未写（注入异常），When `recover_review`，Then 先补写 Checkpoint、新 StepRun supersedes 旧运行、2 条旧决定作为冻结输入不重录、队列只剩 2 项、返回新 token；旧运行 `superseded`（依 D-15 B）。
- 5.5 `amend` 决定先封存 `reviewed_candidate`（`entity_id` 与 kind 不变），决定的 `amended_revision_id` 指向它。

## 6. 结审与 ReviewedEditionPackage（ACT 06）

- 6.1 Given 4 条决定齐全，When `close_review`，Then token 被消费、Gate 通过、`reviewed_edition_package` sealed（3 获批、1 驳回）、m6 StagePackage 过 Schema、Transformation `review_curate` 的 `human_event_revision_ids` 等于全部决定、StepRun `succeeded`。
- 6.2 Given 仍有未决项或补证项，Then `close_review` 拒绝、token 未消费、StepRun 仍 `awaiting_human`。
- 6.3 Given 注入 Gate 失败，Then StepRun `failed`、失败报告 sealed、无 m6 StagePackage。
- 6.4 获批 assertion 的证据链接能在 `corpus_spans` 中按 offset 截出引文且哈希一致；驳回对象保留在包内。

## 7. 命令行 Review Console（ACT 07）

- 7.1 `open` 输出末行 `M6 AWAITING <srun> token=<token> pending=4`，退出 0；无上游时 `M6 REFUSED …` 退出 2。
- 7.2 `show` 打印目标内容、每条证据的 span_id、页、line_id、行框、image_sha256、引文和 M5 条目；执行前后 Ledger 各表行数不变。
- 7.3 `decide` 与 `decide-batch --from-file` 每条输出 `M6 DECIDED <rev> remaining=<n>`；批文件第 3 条非法时停在第 3 条，前 2 条已落盘。
- 7.4 `close` 成功 `M6 OK <srun> approved=3 rejected=1 decisions=4` 退出 0；有未决 退出 2；Gate 失败 退出 1。

## 8. CorrectionRequest 与失效传播运行（ACT 08）

- 8.1 Given 审核中对 p0003_s08 发起 `request_correction`，Then 记为 `human_event`（`event_kind=correction_request`）、Checkpoint +1、不阻断后续决定；`close_review` 后 `reviewed_edition_package.correction_request_revision_ids` 含该修订（D-10 A）。
- 8.2 Given 首审已 succeeded 且桩生成修正后的 m3 修订，When `run_rework_propagation`，Then 新 StepRun supersedes 首审、3.1 的计数成立、as_…001/as_…002/sv_…1 的候选修订 `invalidated`、as_…003 候选修订仍 sealed、m1–m3 无任何修订被 invalidated、`rework_impact_report` sealed、Checkpoint 引用该报告、Transformation `propagate_invalidation` 的人工事件含 CorrectionRequest。
- 8.3 Given CorrectionRequest 列出的 Span 在新旧 corpus 中没有变化，Then StepRun `failed`、检查名 `correction_scope`。

## 9. 复审只重放待复核项（ACT 09）

- 9.1 Given 报告有告警且未确认，When `open_rework_review`，Then 拒绝且零写入；确认后先写 `rework_threshold_ack` 事件。
- 9.2 Then 复审队列只有 2 项（as_…001、sv_…1），`seen_artifact_revision_id` 指向 M4' 新修订；2 条继承决定不重录。
- 9.3 When 两项重新 accept 并 `close_review`，Then 新 `reviewed_edition_package` 中 4 条立场决定：2 `active`、2 `carried_forward`（带 `carried_from_revision_id` 与 `trigger_correction_request_id`），`rework_impact_report_revision_id` 非空。

## 10. Snapshot 直通投影（ACT 10，依 D-01）

- 10.1 Given 首审包，When `project_snapshot`，Then entities 只含 3 个获批对象、conflict_groups 含 cg_…1、`canonical_hash` 两次相同、改任一实体修订则哈希变。
- 10.2 Given `previous_snapshot` 非空，Then 拒绝（增量汇编属 M7）；Given 获批对象修订已 invalidated，Then `run_snapshot` 拒绝。
- 10.3 `run_snapshot` 产出 `release_run` 下 stage m7 StepRun、`canonical_knowledge_snapshot` sealed、m7 StagePackage 过 Schema。

## 11. 验收脚本（ACT 11）

- 11.1 Given 规范 fixture，When `m6-data-fields.sh`，Then 12 PASS、`legacy_workbench_seed` 与 `upstream_real` BLOCKED、exit 2。
- 11.2 Given 桩期望文件被改、决定修订被删一条、准备阶段异常，Then exit 1；缺 fixture exit 3。
- 11.3 Given 副本 `verify.sh` 被换成假脚本且数据被改，Then 仍 `FAIL fixture_host`、exit 1。
