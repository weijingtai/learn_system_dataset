# NC-011 验证计划

环境前缀（每条命令都带上，不依赖上一条的 export）：
- SERVER：`PYTHONDONTWRITEBYTECODE=1 FIRESTORE_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099`，pytest 加 `-p no:cacheprovider`。
- CLIENT / REST：`PATH=/Users/jingtaiwei/flutter/bin:$PATH`。
- 服务端测试函数名 = `test_` + 下表名称；客户端与 REST 测试名逐字。

## 1. 命令

| # | 仓库目录 | 命令 | 期望 |
|---|---|---|---|
| 1 | REST | `dart test test/community_openapi_contract_test.dart` | act/01 后 `+23` 全部通过 |
| 2 | REST | `dart test` | act/01 后 `+73: All tests passed!` |
| 3 | REST | `tool/validate_openapi openapi/openapi.yaml`；`/Users/jingtaiwei/Git/Public/learn_system/.venv/bin/python tool/check_examples.py` | 均退出 0 |
| 4 | SERVER | `.venv/bin/python -m pytest tests/test_community_comments.py -q` | act/02 `20 passed`；act/03 `32 passed`；act/04 `37 passed` |
| 5 | SERVER | `.venv/bin/python -m pytest tests -q -rf` | act/02 `5 failed, 479 passed, 9 xfailed`；act/03 `5 failed, 491 passed, 9 xfailed`；act/04 `5 failed, 496 passed, 9 xfailed`；FAILED 恰为契约 §1 五个 ID |
| 6 | RULES `server/functions` | `npm test -- community_rules` | act/04 `Tests: 89 passed` |
| 7 | CLIENT | `flutter analyze` | `No issues found!` |
| 8 | CLIENT | `flutter test test/community/discussion_test.dart` | act/05 `+10`；act/06 `+25` |
| 9 | CLIENT | `flutter test` | act/05 `+224: All tests passed!`；act/06 `+239: All tests passed!` |
| 10 | 各仓 | 各 ACT VERIFICATION 中的 `git diff-tree -r --name-only <基线> HEAD -- <受保护路径>` | 空 |
| 11 | learn_system | `bash docs/blackbox-spec-rework/reviews/nc011_guard.sh --require-impl rest\|server\|client` | 对应线完成后 0 |

## 2. act/01（REST，契约 §13）

测试（4）：`comment list declares root id and order query parameters`（A01）、`comment page requires reply previews and counts`（A02）、`comment create conflict response accepts access version and idempotency problems`（A03）、`comment examples manifest has thirteen entries and validates`（A04）。

Red：先追加 4 个测试、3 个示例与 manifest 3 项，运行命令 1（期望 4 个新测试失败、既有 19 个通过）。

## 3. act/02（SERVER W7，契约 §3～§5.1、§7、§9 T01～T18）

测试（18 名，20 例）：`create_root_comment_writes_comment_revision_thread_outbox_event_atomically`、`comment_payload_hashes_match_reference`、`thread_id_is_deterministic_from_content_id`、`reply_to_root_has_depth_1_and_same_root`、`reply_to_reply_stays_depth_1_with_root_of_target`、`reply_to_id_without_root_id_is_400`、`cross_thread_root_or_target_is_404_not_found_comment`、`root_id_pointing_to_reply_is_404_not_found_comment`、`reply_to_deleted_root_or_target_is_403_thread_closed`、`reply_to_hidden_target_is_403_thread_closed`、`body_4000_code_points_of_4byte_emoji_passes_and_4001_is_413`、`blank_body_and_schema_errors_are_400`、`mentions_over_50_is_413_and_mismatched_mentions_are_dropped`、`non_author_on_non_public_content_is_404_not_found_content`（参数化 withdrawn/trashed/hidden）、`content_author_on_non_public_content_is_403_thread_closed`、`stale_expected_access_version_while_visible_is_409`、`same_key_replays_and_different_payload_is_409`、`commenter_counts_track_distinct_visible_authors`。

Red：先写 helpers 追加与测试，运行命令 4，保存 `ModuleNotFoundError: xuan.community.discussion_service`（或等价 ImportError）原文。

## 4. act/03（SERVER W8/W9/R2，契约 §5.2～§7、§9 T19～T30）

测试（12）：`edit_creates_revision_chain_and_keeps_created_at`、`edit_or_delete_by_non_author_is_403_not_owner`、`missing_if_match_is_400_and_stale_is_412`、`malformed_if_match_is_400_without_ledger`、`edit_or_delete_non_visible_comment_is_404`、`delete_root_leaves_tombstone_and_replies_visible_and_counts_drop`、`list_newest_default_20_with_cursor_and_reply_previews_of_5`、`list_replies_by_root_oldest_with_cursor_and_newest_is_400`、`list_orders_same_created_at_by_id_bytes`、`list_etag_matches_reference_and_304_only_after_acl`、`list_rejects_invalid_limit_order_root_and_cursor`、`list_author_reads_withdrawn_thread_and_others_get_404`。

Red：先追加测试，运行命令 4（期望 12 个新测试失败，T01～T18 仍通过）。

## 5. act/04（SERVER 并发与日志 + RULES，契约 §8、§9 T31～T35）

测试（5）：`withdraw_commits_first_then_comment_retries_and_gets_404`、`comment_commits_first_then_withdraw_succeeds_and_hides_thread`、`two_comments_and_withdraw_three_way_race_keeps_invariants`、`comment_new_ids_fixed_across_transaction_retry`、`logs_never_contain_comment_body`。RULES：`COMMUNITY_COLLECTIONS` 追加三项。

Red：实现在 act/02～03 已满足时这些测试可能直接通过；报告须逐个列名，并给出「临时把 `after_access_read_hook` 调用注释掉（不提交）后 T31/T32 的失败原文」证明非永真，随后恢复并以 `git -C <SERVER> status --short` 为空证明已恢复。

## 6. act/05（CLIENT 基础，契约 §11.1～§11.5、§12 K01～K10）

测试（10）：`list_comments_sends_order_root_cursor_limit_without_if_none_match`、`create_comment_sends_idempotency_and_expected_access_version_without_if_match`、`edit_and_delete_comment_send_if_match`、`comment_payload_hashes_match_python_reference`、`comment_create_same_target_does_not_conflict_but_edit_does`、`comment_restart_with_real_file_close_reopen_resends_same_key`、`comment_lost_response_reconciles_by_get_command_without_new_comment`、`comment_410_and_503_never_change_key`、`comment_count_port_reads_visible_commenter_count`、`pending_queue_summarizes_comment_commands`。

Red：先写测试，运行命令 8，保存编译失败原文。

## 7. act/06（CLIENT 讨论区，契约 §11.6、§11.7、§12 K11～K25）

测试（15）：`discussion_first_level_newest_20_then_load_more_keeps_existing_items`、`discussion_replies_preview_5_then_expand_more`、`discussion_empty_states_distinguish_no_comments_and_closed`、`discussion_offline_comment_restart_confirms_once_and_pending_mark_clears`、`discussion_body_over_4000_code_points_blocks_send`、`discussion_409_access_version_keeps_draft_and_prompts`、`discussion_late_success_after_withdraw_rereads_and_shows_not_visible`、`discussion_tombstones_show_deleted_and_hidden_texts`，以及参数化 `seven_states discussion loading`、`seven_states discussion empty`、`seven_states discussion partial`、`seven_states discussion error`、`seven_states discussion offline`、`seven_states discussion stale`、`seven_states discussion success`。

Red：先写测试，运行命令 8，保存编译失败原文。
