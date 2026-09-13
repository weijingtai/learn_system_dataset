# BDD：impl-05 M4 Knowledge Extraction 最薄接入

场景按 ACT 分节；「金标」指 README 附录 A 的四个 YAML（K1–K3 使用 `tests/data/appendix_a/` 副本，K4 使用 fixture `m4/`）。

## 1. 提交件与任务管线 Adapter（ACT 00）

- 1.1 Given 附录 A 的 A 路 assertion 提交件，When `validate_submission(doc, technique_id="qizheng")`，Then 通过，缺省字段补齐（conditions/exceptions/concept_refs/school_ids 为 `[]`，layer 为 `general` 仅在缺省时）。
- 1.2 Given 提交件的 assertion item 夹带 `name` 或 `surface` 等别类键，Then 整件拒收 SCH_002（类别混合，§12.2:572）；Given 缺 `proposition`，Then SCH_001。
- 1.3 Given `category`、`lane`、`channel`、`support_type`、`relation`、`layer` 取闭集外值，Then SCH_002；Given `lane: c` 或 `channel: model_adapter` / `legacy_workbench`，Then `validate_submission` 通过形状校验，但 `run_m4_submit` 在 begin 前拒收（见 3.4）。
- 1.4 Given item `status: cross_model_reviewed` 或 `expert_verified`，Then 整件拒收 SCH_002（状态越权，同 AST_002）。
- 1.5 Given HANDBOOK 工位 5 / SCHEMA.md §4 格式的 `assertions.yaml`（含 assertion_id、proposition_id、concept_ids、skipped_segments），When `normalize_task_output(category="assertion")`，Then 产出通过 1.1 的提交件：ID 被丢弃并记入 `adapter_notes`，`concept_ids` → `concept_refs`，`skipped_segments` → `skipped`，无 quote 的证据保持无 quote（表示整条 Span）。
- 1.6 Given 工位 4 `result.yaml` 的 `new_concept_candidates`，When `normalize_task_output(category="concept_mention")`，Then 每条成为 `concept_ref` 为空的 item，quote 等于 surface。
- 1.7 Given mini_ed01 spans.yaml 与临时空目录，When `export_task_inputs`，Then 写出 INSTRUCTIONS.md、input/segments.yaml、input/spans.yaml、task.yaml 四个文件，segments 与 Span 一一对应，两次导出字节相同；目标目录非空时拒绝。

## 2. 纯函数装配（ACT 01）

- 2.1 Given `span_char_start/end`，Then 证据 offset = Span.start_offset + 相对位置，quote 取自 Span 文本；Given 只有 quote 且在 Span 内唯一出现，Then 定位成功；Given 两者都没有，Then 证据覆盖整条 Span。
- 2.2 Given quote 不存在、quote 出现多次（如「論星曜合照命宮論星曜對照命宮」中的「宮」）、区间与 quote 不一致，Then 该 item 进 `rejected`，reason_code TXT_001；Given Span 不存在，Then REF_001；Given 证据为空，Then SEM_001。
- 2.3 Given `layer: case` 的 assertion，Then 进 `rejected`（SCH_002，G4 命例不得作为通则主张）。
- 2.4 Given `concept_refs: [co_shared_branch_05]` 且 quote 为「辰」，Then 通过（只校验不扫描，D-06）；Given 不在 canon 的 `co_shared_branch_99`，Then REF_001；Given `co_qizheng_000001` 而 profile glossary 为空，Then REF_001；Given 概念提及 surface 与 canon 字面不符，Then TXT_001。
- 2.5 Given 任何 `school_id` 而 profile schools 为空，Then REF_001；Given 合成 profile 登记 `sch_qizheng_001` 与注入的 id_factory，Then SchoolView 获得 `sv_`，相同 conflict_key 的视图共享同一 `cg_`。
- 2.6 Given A、B 两路内容相同，Then 无分歧；Given 金标 A/B（item 1 relation 不同、B 另有 1 条 TXT_001），Then 恰 1 条分歧 `m4_d001`，被拒条目不参与比对。
- 2.7 Given 存在未裁决分歧，When `assemble_candidates`，Then 拒绝（message 含「未裁决」）；Given 裁决 `both`，Then 两路条目都保留且 `content_status: disputed`；Given `neither`，Then 两路条目以 `ruled_out` 进 `rejected`。
- 2.8 Given 金标与裁决 a，Then assertions 2 条，`as_qizheng_000001` 为「宋錢如璧撰」、`pr_` 同号；new_concept_candidates 2；rejected 1；counts 与附录 A 一致；两次运行字节相同。
- 2.9 Given 条目数超出 id_range，Then ExtractionRefused ID_001（号段耗尽）。

## 3. 独立候选 Gate（ACT 02）

- 3.1 Given 金标装配出的 candidate_set，Then 12 项检查全部通过，`cross_model: not_evaluated`、`term_layering: verify_only`、`semantic_span_input: not_evaluated`。
- 3.2 Given 删证据、改 quote 一字、改 offset、改 quote_sha256、未知 Span、重复 as_ 号、as/pr 号不一致、越出 id_range、`expert_verified`、`cross_model_reviewed`、`layer: case`、悬空 claim_ref、未登记 school_id、未知 concept_ref、`evidence_level: offset_level`、`span_layer: semantic`、分歧 choice 为空、counts 错、technique_id 不符、多出顶层键，Then 每种篡改让指定检查失败、`structural` 为 `failed`。
- 3.3 gate.py 不 import assemble.py 与 submission.py，页块由 gate 自己从 spans_doc 重算。

## 4. Registry Adapter、输入解析与 submit StepRun（ACT 03）

- 4.1 Given canon 目录，When `build_technique_profile`，Then 概念数等于各文件 `closed_set_size` 之和，homographs/glossary/schools 为空，两次字节相同；`register_technique_profile` 产出运行级 sealed 修订。
- 4.2 Given ingest(m1,m2) → run_m3，When `resolve_m3_outputs`，Then 返回唯一 m3 StepRun、corpus_package、corpus_spans 与 m3 StagePackage 修订；Given 只 ingest(m1,m2,m3)（无 corpus_spans）或没有 m3，Then 拒绝且无写入。
- 4.3 Given 金标 A 路提交件字节，When `run_m4_submit`，Then StepRun succeeded、冻结输入恰为 {M3 包, corpus_spans}、1 个 Checkpoint `submit_assertion_a`、Transformation `register_submission`、提交件修订 sealed。
- 4.4 Given 同类同路重复提交、`channel: model_adapter`、`lane: c`、形状错误、M4 已封存，Then begin 之前拒绝，Ledger 的 artifact_revisions / step_runs / audit_log 行数不变。
- 4.5 Given 三件金标提交后，When `resolve_m4_inputs`，Then 列出 `assertion/a`、`assertion/b`、`concept_mention/a` 三件；Given 同一运行存在两份 technique_profile 且未显式指定，Then 拒绝。

## 5. assemble StepRun（ACT 04）

- 5.1 Given 两路逐字相同的 assertion 提交件与 concept_mention A 路，When `run_m4`，Then 无分歧、StepRun succeeded、Checkpoint 依次为 3 个 lane + reconcile + assemble 共 5 个且成链、m4 StagePackage 过 Schema、M3 包输入引用为 `artifact_kind: stage_package`、`content_sha256 == sha256(candidate_set 字节)`。
- 5.2 Given 两个独立临时 Ledger 走同样步骤，Then candidate_set 字节相同。
- 5.3 Given 金标 A/B，When `run_m4`，Then 返回 `status: awaiting_human` 与 resume_token，StepRun 为 `awaiting_human`，dispute_queue 已封存，尚无 candidate_set 与 m4 包。
- 5.4 Given 缺必需路（只有 A 路 assertion）、缺 technique_profile、M4 已封存，Then begin 之前拒绝且无写入。
- 5.5 Given corpus_spans 哈希与 M3 包 `content_sha256` 不符，Then StepRun failed、failed_check `input_contract`；Given 装配结果被篡改出 `expert_verified`，Then `candidate_gate`；Given begin 之后抛出未预期异常，Then `internal` 且失败报告已封存。
- 5.6 CLI：assemble 成功 exit 0、拒绝 exit 2、等待人工 exit 4。

## 6. 类别裁决与恢复（ACT 05）

- 6.1 Given 5.3 的等待态，When 用金标裁决 `record_category_ruling` 后 `resume_m4`，Then StepRun succeeded，结果与附录 A 期望逐项一致。
- 6.2 每条裁决被 Ledger 接受后立即写 Checkpoint，其 `human_decisions` 含该事件；`human_events` 表登记且 decision_type 为 NULL；Transformation 的 human_event_revision_ids 等于全部裁决事件。
- 6.3 Given 仍有未裁决分歧，When `resume_m4`，Then 拒绝且 token 未被消费（之后仍可继续裁决）。
- 6.4 Given 重复裁决同一 dispute、未知 dispute_id、choice 非法，Then 拒绝且无新增修订。
- 6.5 Given token 已被消费，When 再次 `resume_m4`，Then Ledger 拒绝。
- 6.6 Given 恢复时按冻结输入重算的 lane 集字节与已封存 candidate_lane_set 不一致，Then failed_check `input_contract`。

## 7. 审核决定事件契约（ACT 06）

本节全部为纯函数单测，输入为明确标注的合成事件（测试替身），不写 Ledger、不建签发 StepRun，不代表任何真实专家决定；真实签发由用户撰写决定表（P7 / README §9）。

- 7.1 Given 合法参数，When `build_review_decision`，Then 通过 `validate_review_decision`；Given decision_type 不在八类、verdict 非法、entity_id 前缀与 entity_kind 不符、所见修订格式错、rationale 为空、stage 非 m6，Then 分别 SCH_002 / SCH_002 / ID_001 / ID_001 / SCH_001 / SCH_002。
- 7.2 Given `school_ids` 为空的主张只有 `review_source_fidelity=accept`，Then `expert_verified`；Given `school_ids` 非空，Then 还需 `review_school_attribution=accept`，否则保持原状态。
- 7.3 Given 必需类型最新为 reject → `deprecated`；school_dispute → `disputed`；modify 或 request_evidence → `needs_expert`；同一类型先 reject 后 accept → 以最新为准。
- 7.4 Given 决定所见修订与当前候选修订不同，Then 该决定不计入。

## 8. 验收脚本（ACT 07）

- 8.1 Given mini_ed01 与其 `m4/` 金标，When `m4-stage-gate.sh`，Then 13 项 PASS、3 项 BLOCKED 文字逐字、exit 2。
- 8.2 Given 金标副本 expected counts 被改、裁决改为 b、准备阶段抛异常，Then exit 1；Given 缺 fixture 或缺 `m4/`，Then exit 3。
- 8.3 Given 被验副本自带 `verify.sh` 被换成假脚本且数据被改，Then 仍 `FAIL fixture_host`、exit 1。
- 8.4 acceptance.py 不 import assemble.py、gate.py、submission.py。

## 9. legacy 准入纯函数（ACT 08，可选）

- 9.1 Given 实库只读快照，When `admit_legacy_rules`，Then 496 条全部以 SCH_001 拒收、准入 0，库文件 sha256 前后不变。
- 9.2 Given 合成行 original_text 非空但无法解析到 Span，Then REF_001；可解析，Then 准入并记录所引 Span。
- 9.3 `pipeline/tools/import_legacy_candidates.py` 仍不存在，`run_all.sh 20.7` 仍 FAIL。
