# BDD：impl-07 M7 增量汇编

## G0. 创世薄切片（W5-L0，本波）

输入为合成 ReviewedEditionPackage（`tests/data/genesis_package.json`，标 `synthetic: true`）与其冻结血缘 M4 `candidate_set`；空基底。以下场景对应 `act/g0-01.yaml`–`act/g0-05.yaml`。

- G0.1 Given 空基底与单个 ReviewedEditionPackage，When `assemble_genesis` 两次，Then `knowledge` 规范 JSON 字节相同，`knowledge_sha256` 可复算，全部提案 `resolution == "auto"`。
- G0.2 Given 候选 Pattern 一个带合法 `pat_`、一个 `pattern_id: null`，Then 前者保留原号（R02），后者按 `(source_id, candidate_key)` 升序发 `pat_`（R03e）、号 > 候选既有最大号；`id_allocation` 等于最大号。
- G0.3 Given 已绑定 `concept_mentions` 与无号 `new_concept_candidates`，Then Snapshot `concepts` 只含绑定项（按 `concept_ref` 聚合，`name` 取 surface 升序首个），无号项进 `assembly_package.report.excluded_unbound`，不进 Snapshot。
- G0.4 Given `reviewed_edition.approved` 的 Assertion 与 `evidence_links`，Then `knowledge.assertions[].proposition` 与候选 NFC 后一致、`text_sha256` 可复算、`evidence[]` 的 `source_span_id/start_offset/end_offset/quote_sha256` 取自 `evidence_links`、`subject_entity_id` 为解析后的正式号。
- G0.5 Given SchoolView 带 `conflict_group_id` 且成员 `changes_current_judgment`，Then `conflict_groups` 恰一组、`first_layer_display == true`，`school_views[].source_conflict_group_id` 保留原值。
- G0.6 Given 创世 knowledge，Then `relations == []`、`retired_entity_ids == []`、`meta.base_snapshot_revision_id == null`、Pattern/Concept 顶层无 `content_status`、`decision_refs == {}`。
- G0.7 Given 独立 Gate `evaluate_genesis`，Then 合法输入 10 项检查全过；篡改矩阵每例命中指定检查（去掉 approved Assertion→`provenance_complete`、重复发号/低于候选最大号→`allocation_monotonic`、复活 retired→`identity_preserved`、relations 非空或 meta 有 base→`genesis_only`、删 SchoolView→`no_silent_fold`、`first_layer_display` 置假、合成 `content_status`、改 proposition→`view_objects_unaltered`）。
- G0.8 Given 临时 Ledger 与合成 m6 输入，When `run_m7`，Then StepRun `succeeded`；ProcessingRun `kind == release_run` 且 `edition_part_id == reviewed_edition.edition_part_artifact_id`；Snapshot 修订 `knowledge` 字节等于纯函数结果；`assembly_package` 与 `validation_report` 封存；m7 StagePackage 过 `stage_package.schema.json` 且 `lineage` 输入集合 == `frozen_inputs`；Checkpoint 链 `propose_r1 → seal_snapshot`。
- G0.9 Given `base_snapshot_revision_id` 非 `None`、或上游 m6/m4 所属 StepRun 非 `succeeded`、或同一 technique 已有 Snapshot，When `run_m7`，Then 在 `begin_step_run` 之前拒绝，`artifact_revisions`/`step_runs`/`audit_log` 行数不变。
- G0.10 Given 同一 Part 已有一个 succeeded 的 m7 运行，When `begin_or_supersede`，Then 经 `supersede_step_run` 接替最近一个 succeeded 运行（经读接口查出、不写死号，第 58 条），不被阶段封存守卫拒绝。
- G0.11 Given `m7-assembler.sh`，Then 10 项 PASS + 6 项 BLOCKED（`incremental_multi_edition`/`edition_collation`/`identity_delta`/`rework_replacement`/`upstream_m6_real`/`run_all_20_5`）+ 末行 `SUMMARY pass=10 fail=0 blocked=6`、exit 2；宿主 `.venv` 缺失 → `SUMMARY blocked=1`、exit 3；金标改一字节 → `FAIL genesis_snapshot`、exit 1。

## 完整增量汇编（DEFERRED，下一波）

场景中的对象号、候选键、规则哈希取自 `act/00.yaml` 的场景表；s1/s2/s3 指三个 Snapshot 金标（`act/01.yaml`）。

## 1. fixture mini_release01（ACT 00–01，F 组）

- 1.1 Given mini_ed01 `spans.yaml` sha256 为 `ec6d77b9…44ef`，When 运行 `tools/build_fixture.py --out <tmp>`，Then `diff -r --exclude=tools --exclude=README.md <tmp> mini_release01` 无输出，且 `verify.sh` 末行 `FIXTURE OK`、退出 0。
- 1.2 Given ed01 视图中 `as_qizheng_900001` 的 `text` 被改一个字，Then `verify.sh` 打印 `FAIL host_binding` 并退出 1。
- 1.3 Given 任一 `editions/`、`decisions/`、`expected/` 文件改一个字节，Then `FAIL manifest_sha256`、退出 1。
- 1.4 Given 视图或金标里任一对象号不符合 §8.1 家族正则，或某个 `proposal_key`/`relation_key` 能被前缀家族识别，Then `FAIL ids`。
- 1.5 Given 目录内出现 png/jpg/pdf，Then `FAIL no_images`。

## 2. 规范化与视图校验（ACT 02）

- 2.1 Given 同一对象两次序列化，Then `canonical_json` 字节相同；键序与插入顺序无关；`nfc_key` 把组合字符规范为 NFC 并去首尾空白。
- 2.2 Given 任一合法 kind 与主体元组，Then `make_key` 结果匹配 `^[a-z_]+:[0-9a-f]{32}$`，且 `pipeline.ledger.ids.kind_of` 返回 None；非法 kind → `SCH_002`。
- 2.3 Given 视图缺 `unresolved_count` 或其值非 0、`pattern_id` 格式非法、同视图 `as_` 重复、Assertion 主体在视图中不存在、SchoolView `claim_refs` 悬空、候选既无 `pattern_id` 又无 `candidate_key`、`collation_units` 键重复、`content_status` 不在 §8.2 闭集，Then 分别拒绝并给出 `SCH_001`/`ID_001`/`ID_002`/`REF_001`/`SCH_002`。
- 2.4 Given Snapshot knowledge 列表未排序、关系端点悬空、已退役号仍作为活对象出现、`id_allocation` 小于现存最大号，Then `validate_snapshot_knowledge` 拒绝。

## 3. 提案（ACT 03）

- 3.1 Given 基底 s1 与 ed99，When `propose` 第 1 轮，Then 自动：c1 attach、c4 admit_new、两个 Concept attach、u001 alignment、u002 variant_reading、u003 omission、u004 addition；人工：c2（R03b）、c3（R03c）、sv_b1 冲突组（R06）；阻塞：c5（R03f，依赖 c2 的提案）；u006 进 `not_comparable`。提案集合与 `expected/proposals_r2.json` 第 1 轮逐项相等。
- 3.2 Given c2 裁决为 attach，When 回流第 2 轮，Then c5 变为 AliasProposal（R03c，人工），其余已裁决提案不再出现为待决。
- 3.3 规则 R01、R01b、R02、R03a–R03g、R04、R06、R07、R07b、R08、R09、R10 各有一个最小合成用例，得到约定的 kind、rule_id 与 resolution。
- 3.4 Given 候选只与基底某 Pattern 同名、规则不同，Then 永远不是 auto（同名异义保留）。
- 3.5 Given 一侧未声明某 `collation_key`，Then 不产生 omission 或 addition，只进 `not_comparable`。
- 3.6 Given 候选绑定已退役的 `pat_`，Then `AssemblyRefused(ID_001)`；Given 新视图的 `as_` 已被基底中其他 source 占用，Then `AssemblyRefused(ID_002)`。
- 3.7 Given 视图与基底中同一 source 的 part 集合部分重叠，Then `AssemblyRefused(SCH_002)`；Given 视图对象哈希与 provenance 全等，Then `AssemblyRefused`（消息含「已汇编」）。

## 4. 应用（ACT 04）

- 4.1 Given 空基底与 ed01，When 全部自动裁定后 `apply_resolutions`，Then knowledge 字节等于 `expected/snapshot_s1.knowledge.json`。
- 4.2 Given s1、ed99、`r2` 与 `r2b` 决定，Then knowledge 字节等于 `snapshot_s2.knowledge.json`；新号按 (source_id, candidate_key) 升序为 c3→900003、c4→900004、c5→900005；`id_allocation` 为 900005。
- 4.3 Given 决定的 `choice` 不在提案 `options`、人工提案无决定、同一提案两条决定、决定引用不存在的 `proposal_key`，Then 拒绝。
- 4.4 Given 人工 `merge_entities` 合并两个正式 Pattern，Then 新号大于高水位，两个旧号进 `retired_entity_ids`，IdentityDelta 两条 `merged` 且 `reason_ref` 指向该提案；Given `split` 的 `span_allocation` 未覆盖旧对象全部 Span 或有重叠，Then 拒绝；合法 `split` → 一条 `split` 且携带 `span_allocation`。
- 4.5 Given 两个来源的 `content_status` 不同，Then Pattern 的 `provenance` 逐来源保留原状态，不出现合成状态字段。

## 5. 增量（ACT 05）

- 5.1 Given s1 + ed99 + 决定，Then `affected_closure` 等于 `expected/affected_s2.json`（9 个对象）；`as_qizheng_900004` 的规范 JSON 字节与 s1 中相同。
- 5.2 Given 增量路径（闭包内重算）与全量路径（每一步 `affected=None` 全部重算），Then 两者 `knowledge_sha256` 相等（s2 与 s3 各一次）。
- 5.3 Given s2 + ed01r2 + `r3` 决定，Then knowledge 字节等于 `snapshot_s3.knowledge.json`；闭包等于 `affected_s3.json`（11 个对象）；IdentityDelta 等于 `identity_delta_s3.json`（`as_qizheng_900004` retired）；u002 由 variant_reading 变为 alignment；两条 `distinct_from` 与 c2 attach 裁决 `carried_forward`；冲突组 unify 裁决降级 `needs_review` 并重新入队。
- 5.4 Given 在闭包实现中人为漏掉一个对象，Then 等价性测试失败（防「报告对、实际漏算」）。
- 5.5 Given 同一 source 的不相交新 part，Then 视为扩展：`editions[].edition_part_ids` 追加，不触发替换。
- 5.6 Given 有未决人工提案，Then `assemble` 返回 `awaiting_human` 与待决 `proposal_key` 列表，不产出 knowledge。

## 6. 独立 Gate（ACT 06）

- 6.1 Given s1、s2、s3 三组金标输入输出，Then 全部检查通过。
- 6.2 篡改矩阵各让指定检查失败：删一个基底对象且无 delta（`identity_preserved`）；复用退役号或新号不大于高水位（`allocation_monotonic`）；改一个闭包外对象字节（`untouched_byte_identical`）；报告闭包少一个或多一个（`affected_scope_exact`）；为未声明单元写 omission（`collation_comparable_only`）；删一个 SchoolView 或冲突组成员（`no_silent_fold`）；成员含 `changes_current_judgment=true` 却 `first_layer_display=false`（`first_layer_display`）；delta `change_type` 越界、`reason_ref` 不可解析、split 缺 `span_allocation`（`identity_delta_contract`）；provenance 状态被改（`maturity_not_synthesized`）；provenance 哈希与视图对象不符（`view_objects_unaltered`）；人工提案无决定却有结果（`decisions_consistent`）。
- 6.3 `gate.py` 不 import `matcher`、`apply`、`incremental`。

## 7. Ledger 自动路径（ACT 07）

- 7.1 Given Ledger 只 seed ed01，When `run_m7(technique_id="qizheng", reviewed_package_revision_ids=[ed01 包修订], base_snapshot_revision_id=None)`，Then StepRun `succeeded`；ProcessingRun kind 为 `release_run`，其 `edition_part_id` 等于本次配置 Artifact 的 `artifact_id`；Snapshot 修订内容的 `knowledge` 字节等于 s1；m7 StagePackage 过 Schema 且血缘输入等于冻结输入；m7 Checkpoint 依次为 `propose_r1`、`seal_snapshot`。
- 7.2 Given 引用的修订不是 m6 StagePackage、包未 sealed、technique 不一致、已存在该 technique 的 Snapshot 却要求创世、基底已 superseded、视图已汇编，Then `run_m7` 在 `begin_step_run` 之前拒绝，Ledger 行数不变。
- 7.3 Given Gate 被注入失败，Then StepRun `failed`、失败报告封存、无 m7 StagePackage、基底 Snapshot 仍 `sealed`。
- 7.4 CLI `run` 成功末行以 `M7 OK` 开头、退出 0；begin 前被拒退出 2。

## 8. 人工回路、替换与并发（ACT 08）

- 8.1 Given seed ed01、ed99 且已有 s1，When `run_m7`，Then 返回 `awaiting_human`，待决 3 个提案，Checkpoint `pending_queue` 为这 3 个 `proposal_key`；逐条 `record_m7_decision`（每条后一个 Checkpoint）；`resume_m7` 返回第 2 轮 `awaiting_human`（c5）；记 `r2b` 后 `resume_m7` 返回 `succeeded`；Snapshot `knowledge` 字节等于 s2；s1 修订变为 `superseded`，新修订 `prev_revision_id` 为 s1。
- 8.2 Given 还有未决提案时调用 `resume_m7`，Then 拒绝，StepRun 仍 `awaiting_human`，token 未被消费（之后仍可用）。
- 8.3 Given 决定引用其他 StepRun 的提案集修订，或 `choice` 不在 options，或同一提案重复决定，Then `record_m7_decision` 在写入任何修订之前拒绝。
- 8.4 Given 两个 ReleaseRun 都以 s1 为基底，第一个 succeeded，Then 第二个在 begin 之前 `NotConsumable`。
- 8.5 Given s2 + ed01r2，Then 第 1 轮待决仅冲突组 unify（`needs_review`）；记 `r3` 后 succeeded，`knowledge` 等于 s3，`identity_delta` 修订内容等于 `identity_delta_s3.json`（补 refs 后）。
- 8.6 Given 记完 2 条决定后中断，Then 最新 m7 Checkpoint 的 `human_decisions` 有 2 个修订、`pending_queue` 剩 1 项。

## 9. 验收脚本（ACT 09）

- 9.1 Given 两个规范 fixture，When `m7-assembler.sh`，Then 13 项 PASS、`upstream_m6_real` BLOCKED、`SUMMARY pass=13 fail=0 blocked=1`、退出 2。
- 9.2 Given 金标副本 `snapshot_s2.knowledge.json` 改一个字节，Then 对应项 FAIL、退出 1；准备阶段抛异常，Then 首行 `FAIL m7_acceptance 宿主准备失败: …`、退出 1；fixture 不存在，Then 退出 3。
- 9.3 Given fixture 副本数据被改且其自带 `verify.sh` 被换成 `exit 0` 的假脚本，Then 仍 `FAIL fixture_host`、退出 1。

## 10. run_all 接线（ACT 10，按 D-13 裁决）

- 10.1 Given D-13 选 A，When `run_all.sh 20.5`，Then `BLOCKED  20.5  前置缺失: M6 Review Workbench；…`；`run_all.sh` 全量末行 `SUMMARY pass=2 fail=1 blocked=8`。
- 10.2 Given `FIXTURE_RELEASE_DIR` 指向金标被改的副本，Then `FAIL  20.5  …`，退出码加 1。
