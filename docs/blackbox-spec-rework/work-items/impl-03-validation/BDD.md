# BDD：impl-03 M5 Automatic Validation 首切片

记号：「fixture 上下文」= `tests/helpers.py` 的 `fixture_context()` 从 mini_ed01 文件合成的纯函数输入（ACT 00 定义）；「真实链路」= 临时 Ledger → `ingest(stages=("m1","m2"))` → `run_m3` → `run_m5`。

## 1. 骨架、注册与分级（ACT 00）

- 1.1 Given 注册表，Then 恰 14 个 Validator，顺序与 `validator_id` 逐字等于 act/00 清单，G 代号只出现 G1/G2/G3，版本号均为 `M5_TOOL_VERSION`。
- 1.2 Given 一条严重度为 `{INTERNAL_DEMO: warning, DEV_SEARCH: error, PUBLIC_RELEASE: error}` 的发现，When `level_verdicts`，Then `{passed, failed, failed}`；Given 任一 Validator `skipped_fail_closed`，Then 三级全部 `failed`。
- 1.3 Given 错误码 `XYZ_001`，When `make_finding`，Then `SchemaViolation(SCH_002)`；错误码只允许 §8.2 九码或 `None`。
- 1.4 `canonical_json` 两次输出字节相同；导入前后 `yaml.SafeDumper` 表示器不变。

## 2. G1 来源与可重放性（ACT 01）

- 2.1 Given fixture 上下文，Then `g1_frozen_bytes`、`g1_page_registry`、`g1_content_hashes`、`g1_replay` 发现为 0；`g1_unresolved_chars` 恰 4 条（2 条 `unresolved_glyph`、2 条 `unproofread_glyphs`），主体与计数逐字等于 README §1 表。
- 2.2 Given 某冻结修订字节改一字节 / 对象缺失，Then `hash_mismatch`（SRC_003）/ `object_missing`（SRC_001），三级均 error。
- 2.3 Given `ocr_page_set` 页哈希被改、页集合少一页、终态与 m2 Checkpoint 不一致，Then 分别 `page_hash_mismatch` / `page_set_mismatch` / `terminal_state_mismatch`。
- 2.4 Given m3 包 `content_sha256` 被改、`corpus_package.spans_revision_id` 指向别的修订，Then `g1_content_hashes` 报错。
- 2.5 Given Span 文本含 U+E000、U+FFFD、`□`，Then `forbidden_char_in_text` 三级均 error。
- 2.6 Given 配置 `tool_version` 与已安装 M3 不同，Then `replay_tool_mismatch`；Given `corpus_spans` 字节被改（哈希同步改），Then 重放 `replay_bytes_mismatch`。

## 3. G2 全书覆盖（ACT 02）

- 3.1 Given fixture 上下文，Then 4 个 G2 Validator 发现为 0，覆盖报告 `{page_001: 1.0, page_003: 1.0}`、排除 `{page_002: known_unrecognizable}`。
- 3.2 Given 删一条 Span、制造重叠、制造缺口、改文字、页序中有页既无 Span 也无终态、`deferred` 页、排除页无人工事件证据，Then 各自命中指定检查。
- 3.3 Given Span 同时出现在两个批次、批次漏一条 Span、批次含语料外 Span、批次超长，Then `g2_batch_partition` 命中对应检查。
- 3.4 Given 表头 `span_count` 错、m3 包 `counts.batches` 错、页行数合计 ≠ Span 数、页字框合计 ≠ 锚点字框数，Then `count_mismatch`。
- 3.5 `g2_coverage.py` 不 import `pipeline.corpus_compiler`。

## 4. G3 身份、引用与证据锚点（ACT 03）

- 4.1 Given fixture 上下文，Then G3 发现恰 3 条：`quote_hash_not_stored` 1、`glyph_text_misaligned` 2（s03、s04）。
- 4.2 Given Span 号格式错、重复、页号/行序与字段不符、`source_id` 与 manifest 不符、`content_status` 表外，Then `g3_span_identity` 命中（ID_001/ID_002/REF_001/SCH_002）。
- 4.3 Given m3 包 ArtifactRef 指向不存在修订、未封存修订、类型不符，Then `g3_references` 命中 `dangling_ref` / `not_consumable` / `ref_type_mismatch`，并进入 `broken_relations`。
- 4.4 Given offset 偏移一位、越界、Span 自带 `quote_sha256` 与文本哈希不符，Then `offset_mismatch` / `offset_out_of_range` / `quote_hash_mismatch`（TXT_001）。
- 4.5 Given 页图哈希错、行框错、字框错、字框越出页宽高或宽高 ≤ 0、锚点缺字段，Then `g3_glyphbox_anchor` 命中；轴对齐框（`angle == 0`）按四点等价接受。
- 4.6 Given `evidence_level: offset_level`，Then `evidence_level_insufficient` 严重度 `{info, info, error}`；Given 声明 `glyphbox_level` 却缺 `chars`，Then `glyphbox_incomplete` 三级 error；Given 表外取值，Then `evidence_level_invalid`。
- 4.7 `g3_evidence.py` 不 import `pipeline.corpus_compiler`。

## 5. Ledger 输入解析（ACT 04）

- 5.1 Given 真实链路到 run_m3，When `resolve_m5_inputs`，Then 冻结修订恰 17 个且角色映射正确、全部 sealed、函数不写入。
- 5.2 Given 无 m3 Checkpoint、M3 StepRun `failed`（或 m3 StagePackage 所属 StepRun 为 `failed`）、M5 已 succeeded，Then `ValidationRefused`（输入契约拒绝，严禁消费失败运行遗留的上游包，impl-02 ACCEPTANCE §5.3）且 Ledger 行数不变。
- 5.3 Given `build_context` 读到哈希不符的对象，Then 不抛异常，`raw.frozen[rev].actual_sha256` 与登记值不同、`doc` 为 `None`。

## 6. run_m5 事务序列（ACT 05）

- 6.1 Given 真实链路，When `run_m5`，Then StepRun `succeeded`、14 个 Validator 报告（artifact_type `validation_report`）与 14 个 m5 Checkpoint 成链、`gate.passed` 为真、`level_verdicts` 为 `{passed, failed, failed}`、m5 StagePackage 过 Schema 且 `validation.passed == true`、血缘上游含 m3 包。
- 6.2 Given `target_consumption_level=PUBLIC_RELEASE`，Then StepRun 仍 `succeeded`，但 `gate.passed` 为假、`validation.passed == false`、`rework_tasks` 非空。
- 6.3 Given `corpus_spans` 对象被改一字节，Then 13 个 Validator `skipped_fail_closed`、三级全 failed、`failed_task_count == 13`。
- 6.4 Given begin 之后 `record_transformation` 抛异常，Then StepRun `failed`、`failed_check == "internal"`、失败报告 sealed、无 m5 StagePackage。
- 6.5 CLI：gate 通过 exit 0 并以 `M5 OK` 开头；gate 未通过 exit 1 并以 `M5 GATE_FAILED` 开头；begin 前拒绝 exit 2 并以 `M5 REFUSED` 开头。

## 7. 验收脚本（ACT 06）

- 7.1 Given mini_ed01，When `m5-evidence-gate.sh`，Then 9 行 PASS、5 行 BLOCKED、exit 2。
- 7.2 Given 对抗场景（M3 编译与结构 Gate 被 mock 放行）：offset 偏移、页图哈希错、删末条 Span、声明 `offset_level`，Then M5 分别以指定检查命中，`adversarial_bypass` PASS；任一未命中则 FAIL、exit 1。
- 7.3 Given 准备阶段崩溃，Then exit 1；缺 fixture 或 `manifest.yaml`，Then exit 3；被验目录自带 `verify.sh` 被换成假脚本且数据被改，Then `FAIL fixture_host`、exit 1。
- 7.4 BLOCKED 行的差距行名逐字取自 §19 第一列（`M4 Knowledge Extraction`、`M3 Corpus Compilation`）。

## 8. BDD ↔ ACT tests ↔ TDD Red/Green 对齐表

每个 BDD 场景至少对应一个 ACT `tests` 用例名；「TDD 行」指 `TDD.md` §1 的 ACT Red→Green 行（Red 为实现前该用例失败/报错，Green 为实现后通过）。

| BDD 场景 | ACT | 对应 tests 用例名（至少一个） | TDD 行 |
|---|---|---|---|
| 1.1 | 00 | `test_validators_count_and_order_exact_14`、`test_all_gates_in_g1_g2_g3` | ACT 00 |
| 1.2 | 00 | `test_level_verdicts_internal_demo_warn_passes_but_public_fails`、`test_level_verdicts_fail_closed_on_skipped_or_errored_task` | ACT 00 |
| 1.3 | 00 | `test_make_finding_validates_code_and_severity`、`test_error_code_mapping_strictly_in_spec_subset` | ACT 00 |
| 1.4 | 00 | `test_canonical_json_determinism` | ACT 00 |
| 2.1 | 01 | `test_fixture_context_g1_clean_except_four_unresolved_char_findings` | ACT 01 |
| 2.2 | 01 | `test_frozen_byte_tamper_yields_src_003_hash_mismatch` | ACT 01 |
| 2.3 | 01 | `test_page_registry_detects_hash_mismatch_and_missing_pages` | ACT 01 |
| 2.4 | 01 | `test_content_hashes_catches_package_sha_mismatch` | ACT 01 |
| 2.5 | 01 | `test_unresolved_chars_flags_pua_and_unrecognized_boxes` | ACT 01 |
| 2.6 | 01 | `test_replay_fails_on_tool_version_mismatch`、`test_replay_fails_on_tampered_corpus_spans_bytes` | ACT 01 |
| 3.1 | 02 | `test_fixture_context_passes_all_g2_validators` | ACT 02 |
| 3.2 | 02 | `test_missing_page_or_unregistered_page_fails_accounting`、`test_deferred_page_fails_accounting`、`test_dropped_span_creates_gap_and_fails_contiguous_coverage`、`test_overlapped_span_fails_contiguous_coverage`、`test_modified_span_text_fails_contiguous_coverage` | ACT 02 |
| 3.3 | 02 | `test_batch_span_leak_or_duplicate_fails_batch_partition` | ACT 02 |
| 3.4 | 02 | `test_count_mismatch_fails_reconciliation` | ACT 02 |
| 3.5 | 02 | `grep -rnE 'corpus_compiler' pipeline/validation/g2_coverage.py \| wc -l`（verify 断言 0） | ACT 02 |
| 4.1 | 03 | `test_fixture_context_g3_clean_except_three_findings`、`test_quote_hash_not_stored_is_single_with_warning_error_error` | ACT 03 |
| 4.2 | 03 | `test_span_identity_flags_illegal_format`、`test_span_identity_flags_duplicate_span_id`、`test_span_identity_flags_page_line_mismatch`、`test_span_identity_flags_source_id_mismatch`、`test_span_identity_flags_illegal_content_status` | ACT 03 |
| 4.3 | 03 | `test_references_flags_dangling_revision`、`test_references_flags_unsealed_revision`、`test_references_flags_artifact_type_mismatch`、`test_references_carry_artifact_ref_relation_for_broken_relations` | ACT 03 |
| 4.4 | 03 | `test_strict_offset_flags_shifted_offset`、`test_strict_offset_flags_out_of_range`、`test_quote_hash_mismatch_when_span_carries_quote_sha256` | ACT 03 |
| 4.5 | 03 | `test_glyphbox_anchor_flags_page_image_hash_mismatch`、`test_glyphbox_anchor_flags_line_and_glyph_box_mismatch`、`test_glyphbox_anchor_flags_out_of_page_box`、`test_glyphbox_anchor_accepts_axis_aligned_as_four_point_equivalent`、`test_glyphbox_anchor_flags_missing_anchor_field`、`test_glyph_text_misaligned_lists_subject_and_difference` | ACT 03 |
| 4.6 | 03 | `test_evidence_level_insufficient_on_offset_level`、`test_evidence_level_glyphbox_incomplete_when_chars_empty`、`test_evidence_level_invalid_on_unknown_value` | ACT 03 |
| 4.7 | 03 | `test_g3_module_has_no_corpus_compiler_import` | ACT 03 |
| 5.1 | 04 | `test_resolve_returns_seventeen_sealed_revisions_with_roles`、`test_resolve_frozen_order_and_page_keys_match_manifest` | ACT 04 |
| 5.2 | 04 | `test_resolve_refuses_when_m3_checkpoint_missing`、`test_resolve_refuses_when_m3_step_run_failed`、`test_resolve_refuses_when_package_owned_by_failed_step_run` | ACT 04 |
| 5.3 | 04 | `test_build_context_records_hash_mismatch_without_raising`、`test_build_context_missing_object_doc_is_none` | ACT 04 |
| 6.1 | 05 | `test_run_m5_on_fixture_succeeds`、`test_gate_results_level_verdicts_passed_failed_failed`、`test_stage_package_validates_schema_and_lineage` | ACT 05 |
| 6.2 | 05 | `test_target_public_release_gate_failed` | ACT 05 |
| 6.3 | 05 | `test_tampered_corpus_spans_yields_thirteen_skipped_and_all_levels_failed` | ACT 05 |
| 6.4 | 05 | `test_after_begin_exception_seals_failure_and_no_stage_package` | ACT 05 |
| 6.5 | 05 | `test_cli_exit_codes` | ACT 05 |
| 7.1 | 06 | `test_fixture_yields_nine_pass_five_blocked_exit_2` | ACT 06 |
| 7.2 | 06 | `test_adversarial_offset_mismatch_hits_g3`、`test_adversarial_page_hash_mismatch_hits_g1`、`test_adversarial_dropped_last_span_hits_g2`、`test_adversarial_offset_level_for_public_hits_g3`、`test_adversarial_bypass_requires_all_four` | ACT 06 |
| 7.3 | 06 | `test_prepare_failure_exits_1`、`test_missing_fixture_exit_3`、`test_shell_never_trusts_copy_verify` | ACT 06 |
| 7.4 | 06 | `test_blocked_lines_use_section19_names` | ACT 06 |
