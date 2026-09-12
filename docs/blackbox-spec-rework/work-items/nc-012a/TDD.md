# NC-012a 验证计划

环境前缀（每条命令都带上，不依赖上一条的 export）：
- SERVER：`PYTHONDONTWRITEBYTECODE=1 FIRESTORE_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099`，pytest 加 `-p no:cacheprovider`。
- CLIENT / REST：`PATH=/Users/jingtaiwei/flutter/bin:$PATH`。
- 服务端测试函数名 = `test_` + 下表名称；客户端与 REST 测试名逐字。
- 本机命令工具默认 30 秒超时：pytest、flutter、dart、npm 命令一律显式设置不少于 600 秒超时，或后台运行后轮询输出文件。

## 1. 命令

| # | 仓库目录 | 命令 | 期望 |
|---|---|---|---|
| 1 | REST | `dart test test/community_openapi_contract_test.dart` | act/01 后 `+27` 全部通过 |
| 2 | REST | `dart test` | act/01 后 `+77: All tests passed!` |
| 3 | REST | `tool/validate_openapi openapi/openapi.yaml`；`/Users/jingtaiwei/Git/Public/learn_system/.venv/bin/python tool/check_examples.py` | 均退出 0 |
| 4 | SERVER | `.venv/bin/python -m pytest tests/test_community_interactions.py -q` | act/02 `19 passed`；act/03 `36 passed` |
| 5 | SERVER | `.venv/bin/python -m pytest tests -q -rf` | act/02 `5 failed, 515 passed, 9 xfailed`；act/03 `5 failed, 535 passed, 6 xfailed`；FAILED 恰为五个既有 ID |
| 6 | SERVER | `.venv/bin/python -m pytest tests/test_community_acl_sweep.py -q` | act/03 `12 passed, 6 xfailed` |
| 7 | RULES `server/functions` | `npm test -- community_rules` | act/02 `Tests: 129 passed` |
| 8 | CLIENT | `flutter analyze` | `No issues found!` |
| 9 | CLIENT | `flutter test test/community/interactions_test.dart` | act/04 `+11`；act/05 `+19`；act/06 `+26` |
| 10 | CLIENT | `flutter test` | act/04 `+281: All tests passed!`；act/05 `+289: All tests passed!`；act/06 `+296: All tests passed!` |
| 11 | 各仓 | 各 ACT VERIFICATION 中的 `git diff-tree -r --name-only <基线> HEAD -- <受保护路径>` | 空 |
| 12 | learn_system | `bash docs/blackbox-spec-rework/reviews/nc012a_guard.sh --require-impl rest\|server\|client` | 对应线完成后 0 |

## 2. act/01（REST，契约 §12）

测试（4）：`reaction and bookmark writes return wrapped responses with command`（A01）、`my share links and bookmark read paths are declared`（A02）、`interaction write errors declare detail too large`（A03）、`interaction examples manifest has seventeen entries and validates`（A04）。

Red：先追加 4 个测试、4 个示例与 manifest 4 项，运行命令 1（期望 4 个新测试失败、既有 23 个通过）。

## 3. act/02（SERVER 赞踩与收藏 + RULES，契约 §2.1、§3、§4、§5.1、§5.2、§6.1、§6.2、§7、§8.2 I01～I17、§9）

测试（17 名，19 例）：`reaction_like_writes_reaction_counts_outbox_event_atomically`、`interaction_payload_hashes_and_ids_match_reference`、`reaction_cancel_keeps_null_row_and_decrements_count`、`reaction_switch_like_to_dislike_moves_count`、`reaction_same_value_is_noop_without_version_bump`、`reaction_if_match_missing_400_stale_412_malformed_400_without_ledger`、`reaction_old_like_replay_after_cancel_returns_original_and_state_stays_null`、`reaction_two_devices_same_baseline_one_commits_one_412`、`reaction_two_accounts_have_independent_values_and_shared_counts`、`reaction_ten_concurrent_accounts_count_exactly_ten`、`reaction_on_non_public_content_is_404_for_others`（参数化 withdrawn/trashed/hidden）、`reaction_author_closed_403_and_comment_target_rules`、`reaction_after_target_purge_replay_does_not_revive`、`reaction_get_etag_literal_and_304_only_after_acl`、`reaction_invalid_target_and_body_are_400`、`bookmark_set_private_noop_optional_if_match_and_get`、`bookmark_on_unreadable_target_is_404`。RULES：`COMMUNITY_COLLECTIONS` 追加五项。

Red：先写测试，运行命令 4，保存 `ModuleNotFoundError: xuan.community.interaction_service`（或等价 ImportError）原文；RULES 先追加数组项运行命令 7，记录通过数（新集合默认拒绝规则已存在时可能直接通过，须在报告中注明）。

## 4. act/03（SERVER 分享、举报、R7、ACL E4，契约 §5.3～§5.5、§6.3、§6.4、§8.2 I18～I27、§8.3）

测试（10 名，17 例）：`share_create_by_author_201_others_403_closed_403`、`share_resolve_returns_target_and_all_failures_share_one_404`（参数化 8 例）、`share_revoke_owner_200_idempotent_non_owner_403_missing_404`、`my_share_links_desc_paging_cursor_literal_and_owner_only`、`my_share_links_rejects_invalid_limit_and_cursor`、`report_create_201_keyed_by_command_id_with_exact_fields`、`report_detail_500_code_points_passes_501_is_413_and_bad_reason_400`、`report_on_unreadable_target_is_404`、`interaction_commands_replay_same_key_and_conflict_on_different_payload`、`logs_never_contain_report_detail`。ACL 扫描：E4 三例去掉 xfail 并替换分支体。

Red：先追加测试并改 ACL 扫描文件，运行命令 4 与命令 6（期望本步新测试失败、E4 三例失败），保存原文。

## 5. act/04（CLIENT 数据层，契约 §10.1～§10.6、§11 J01～J11）

测试（11）：`reaction_api_sends_if_match_and_parses_reaction_response`、`bookmark_api_optional_if_match_and_get_bookmark`、`share_and_report_api_paths_headers_and_bodies`、`interaction_payload_hashes_match_python_reference`、`interaction_restart_with_real_file_close_reopen_resends_same_key`、`interaction_lost_response_reconciles_by_get_command_without_new_report`、`interaction_410_and_503_never_change_key`、`pending_queue_summarizes_interaction_commands`、`mention_ref_is_single_public_type_for_notes_and_comments`、`reconcile_mentions_matches_python_reference_vectors`、`reconcile_mentions_counts_code_points_not_utf16_units`。

Red：先写测试，运行命令 9，保存编译失败原文（J09 因 `hide MentionRef` 与类型不一致而编译失败为预期 Red）。

## 6. act/05（CLIENT 控制器，契约 §10.7、§10.8、§11 J12～J19）

测试（8）：`reaction_rapid_toggle_coalesces_to_serial_commands_with_confirmed_version`、`reaction_late_older_version_response_does_not_roll_back`、`reaction_412_refreshes_state_and_does_not_auto_retry`、`reaction_restart_restores_pending_value_and_next_action_uses_read_version`、`bookmark_toggle_offline_restart_confirms_once`、`report_marks_reported_locally_before_send_and_clears_on_rejection`、`share_controller_creates_lists_and_revokes_links`、`resolve_share_maps_404_to_unavailable_and_transport_to_offline`。

Red：先写测试，运行命令 9，保存编译失败原文。

## 7. act/06（CLIENT 界面与挂载，契约 §10.9～§10.11、§11 J20～J26）

测试（7）：`interaction_bar_shows_counts_toggles_and_has_48dp_hit_targets`、`report_sheet_submits_and_shows_accepted_then_folds_content`、`reported_fold_survives_restart_and_can_be_expanded`、`share_links_page_states_revoke_confirmation_and_load_more`、`share_link_landing_page_unavailable_offline_and_open`、`content_detail_page_optional_builders_keep_default_render`、`discussion_panel_comment_decorator_wraps_visible_comments_only`。

Red：先写测试，运行命令 9，保存编译失败原文。J25、J26 另须证明既有 `test/community/seven_states_test.dart` 与 `discussion_test.dart` 在改动后仍全部通过（命令 10 覆盖）。
