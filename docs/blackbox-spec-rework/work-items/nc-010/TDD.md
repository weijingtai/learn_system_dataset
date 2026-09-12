# NC-010 验证计划

所有命令在 `export PATH=/Users/jingtaiwei/flutter/bin:$PATH` 下、仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes` 内运行。

## 1. 命令

| # | 命令 | 期望 |
|---|---|---|
| 1 | `flutter analyze` | 0 issues |
| 2 | `flutter test test/community/community_api_test.dart` | act/01 后 `+6` |
| 3 | `flutter test test/community/command_queue_test.dart` | act/02 后 `+14`；act/06 后 `+16` |
| 4 | `flutter test test/community/publication_flow_test.dart` | act/03 后 `+9`；act/04 后 `+17` |
| 5 | `flutter test test/community/seven_states_test.dart` | act/05 后 `+25` |
| 6 | `flutter test` | act/01 `+156`；act/02 `+170`；act/03 `+179`；act/04 `+187`；act/05 `+212: All tests passed!`；act/06 `+214: All tests passed!` |
| 7 | `git diff 9b35e97 HEAD --stat -- lib/src/domain lib/src/persistence lib/src/editor lib/src/history test/persistence test/contracts test/editor test/history test/support` | 空 |
| 8 | `grep -rn "firebase_auth\|cloud_firestore" lib/src/community` | 无输出 |
| 9 | `bash docs/blackbox-spec-rework/reviews/nc010_guard.sh --require-impl`（learn_system 内） | 0 |

## 2. act/01：端口、模型与 API 客户端（契约 §2、§3）

文件：`pubspec.yaml`（追加 `http: 1.6.0`）、`pubspec.lock`、`lib/src/community/{ports,models,community_api}.dart`、`lib/reading_notes.dart`（导出）、`test/community/community_api_test.dart`。

6 个测试（名称逐字）：`publish_sends_auth_idempotency_and_no_if_match_on_first_publish`（B11）、`republish_sends_if_match`（B12）、`versioned_writes_send_if_match`（B13）、`get_content_304_returns_not_modified`（B14）、`problem_without_code_is_transport`（B15）、`parses_nullable_fields_as_null`（B16）。

Red：先写测试与抛 `UnimplementedError` 的客户端骨架，运行命令 2 取得失败原文。

## 3. act/02：CommunityDatabase 与命令队列（契约 §1 存储、§4、§8）

文件：`lib/src/community/{community_database,community_database.g,command_queue,command_id}.dart`、`test/community/command_queue_test.dart`。生成代码命令：`dart run build_runner build --delete-conflicting-outputs`；生成后 `git diff -- lib/src/persistence/note_database.g.dart` 必须为空。

14 个测试：`enqueue_persists_before_send_and_generates_valid_command_id`（B01）、`payload_hash_matches_python_reference`（B02）、`same_target_second_command_throws_pending_op_conflict`（B03）、`transport_error_requeues_with_same_key_and_backoff`（B04）、`restart_with_sending_row_queries_command_then_resends_same_key`（B05）、`unavailable_command_status_becomes_unknown_then_resolves_by_get_command`（B06）、`rejected_4xx_is_terminal_and_keeps_problem`（B07）、`gone_410_is_rejected_with_minimal_command_and_triggers_refresh`（B08）、`cancel_only_before_first_send`（B09）、`drain_noop_without_id_token`（B10）、`restart_with_real_file_close_reopen_resends_same_key`（B31）、`concurrent_drain_calls_send_request_once`（B32）、`backoff_1_2_4_8_then_paused_and_manual_retry_keeps_key`（B33）、`stale_over_14_days_queries_command_before_resend`（B34）。

Red：先写测试与抛 `UnimplementedError` 的队列骨架（表先定义并生成代码），运行命令 3 取得原文。

## 4. act/03：缓存、作者文案与发布控制器（契约 §5）

文件：`lib/src/community/{content_access_cache,author_labels,publication_controller,attachment_readiness,pending_op_writer}.dart`、`test/community/publication_flow_test.dart`（前 9 个）。

9 个测试：`author_labels_follow_priority_table`（B17）、`preview_switch_revision_recomputes_readiness`（B18）、`attachment_not_ready_disables_publish_with_reason`（B19）、`success_only_after_committed`（B20）、`version_conflict_keeps_private_revision_and_refreshes`（B21）、`offline_publish_stays_in_pending_queue`（B22）、`trash_published_locally_rejected_before_enqueue`（B23）、`pending_op_column_mirrors_queue_and_recovers_after_restart`（B35）、`late_older_access_version_does_not_overwrite_cache`（B36）。

Red：先写 9 个测试，运行命令 4 取得原文。

## 5. act/04：页面与确认层（契约 §5.3 第 3/5 条、§6 页面与确认层）

文件：`lib/src/community/{note_list_page,content_detail_page,publish_preview_page,pending_queue_page,confirmation_dialogs}.dart`、`test/community/publication_flow_test.dart`（追加 8 个）。

8 个测试：`first_publish_shows_consequence_once`（B24）、`public_view_excludes_unpublished_revision`（B25）、`pending_queue_terminated_item_offers_copy_text`（B26）、`pending_queue_empty_text`（B27）、`withdraw_confirmation_text_uses_runtime_or_generic_count`（B28）、`purge_confirmation_counts_revisions_and_attachments`（B29）、`hidden_by_admin_shows_appeal_entry`（B37）、`pending_queue_paused_item_retries_with_same_key`（B38）。

Red：先写 8 个测试，运行命令 4 取得原文。

## 6. act/05：四屏七状态（契约 §6 表）

文件：`test/community/seven_states_test.dart`（参数化生成 25 个 `testWidgets`，名称形如 `seven_states <屏> <状态>`）；如某状态文案在 act/04 页面中缺失，只允许修改 act/04 的页面文件补齐文案，不改其测试。

Red：先写 25 例，运行命令 5 取得原文（act/04 已实现的状态可能部分已绿，报告逐例列出一开始即绿的名称与原因）。

## 6b. act/06：验收返工（契约 §10）

文件：`lib/src/community/command_queue.dart`（仅 `computePayloadHash` 与 `_canonicalJson`）、`test/community/command_queue_test.dart`（追加 2 个）。

2 个测试（名称逐字，期望值为字面量，禁止测试内计算）：
- `payload_hash_null_if_match_matches_python_reference`（B39）：契约 §10.1 样例二 → `074958695bdd875ce11b8bdf379ca335f81e5e8a1be90a276e18fd0eec450c17`。
- `payload_hash_sorts_keys_by_code_point`（B40）：契约 §10.1 样例三 → `822219839fdd8fac8dce019ba46d82944403ade090ed6e8089480af57b40bfda`。

Red：先写 2 个测试，对 `46a5ebf` 运行命令 3，期望 `+14 -2`（两个新测试红，既有 `payload_hash_matches_python_reference` 仍绿）。Green：命令 3 为 `+16`，命令 6 为 `+214: All tests passed!`，命令 1 为 0 issues。

## 7. 禁止

`skip`、永真断言、真实网络、`firebase_auth`/`cloud_firestore`、改 NC-004～NC-007 文件、在测试内计算 payload_hash 期望值、新增契约外依赖。命令 6 最终 `+212`。
