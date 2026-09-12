# NC-009 验证计划

SERVER：`cd /Users/jingtaiwei/Git/Public/xuan-server/functions-py && export XUAN_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099`；`PY=.venv/bin/python`。RULES：`cd /Users/jingtaiwei/Git/Public/xuan-migration/xuan-server/server/functions && export FIRESTORE_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099`。

## 1. 命令

| # | 命令 | 期望 |
|---|---|---|
| 1 | `$PY -m pytest tests/test_community_commands.py -q` | act/01 后 `12 passed` |
| 2 | `$PY -m pytest tests/test_community_publications.py -q` | act/02 后 `9 passed`；act/03 后 `16 passed`；act/04 后 `18 passed` |
| 3 | `$PY -m pytest tests/test_community_acl_sweep.py -q` | act/04 后 `9 passed, 9 xfailed`（无 skipped） |
| 4 | `$PY -m pytest tests -q` | 既有通过数 + 39 passed + 9 xfailed，0 failed |
| 5 | `npm test -- community_rules`（RULES 仓） | 1 suite passed，≥ 65 断言 |
| 6 | `$PY -c "import main"` | 无异常（导出注册） |
| 7 | `git -C <SERVER> diff 30a868c HEAD --stat -- xuan/idempotency.py xuan/handlers/playground_rest.py xuan/handlers/notifications.py` | 空 |
| 8 | `bash docs/blackbox-spec-rework/reviews/nc009_guard.sh --require-impl`（learn_system 内） | 0 |

## 2. act/01：命令账本服务与注册

文件：`xuan/community/{__init__,errors,ids,command_service}.py`；`xuan/config.py`（追加 8 键）；`tests/conftest.py`（追加 8 集合）；`main.py`（先导出 `community_commands_py` 壳，R5 在 act/03 完成前返回 503）；`tests/community_helpers.py`；`tests/test_community_commands.py` 12 个测试（名称逐字契约 §7）：B01～B10、B29、B30 → `command_publish_commits_ledger_business_outbox_event_atomically`（用一个最小 `fn` 替身写一条业务文档，不依赖 content_service）、`same_key_same_payload_replays_original_response`、`same_key_different_payload_returns_409_idempotency`、`rejected_precondition_writes_rejected_ledger_and_no_business`、`crash_before_commit_leaves_nothing_and_retry_succeeds`、`crash_after_commit_before_response_replays_on_retry`、`compact_after_14_days_then_replay_returns_410_with_command`、`get_command_returns_minimal_result_and_404_unknown`（此步对 `command_service.get_command` 直接断言）、`command_id_format_invalid_returns_400`、`payload_hash_is_operation_bound`、`pseudonym_is_random_and_stable_per_scope`、`new_object_ids_are_fixed_across_transaction_retry`。

Red：先写测试与 helpers，运行命令 1 取得 `ImportError` 原文。

## 3. act/02：publish / update / withdraw、access 与 R1

文件：`xuan/community/{content_service,access}.py`（W1～W3）、`xuan/handlers/community_contents.py`（路由 W1～W3、R1）、`main.py` 追加导出；`tests/test_community_publications.py` 前 9 个：`publish_creates_access_publication_snapshot_bindings`、`publish_by_other_scope_is_403_not_owner`、`publish_twice_is_409_lifecycle`、`publish_with_attachment_is_409_object_missing`、`publish_oversize_markdown_is_413`、`update_requires_if_match_and_bumps_version`、`update_stale_if_match_is_412_with_current_version`、`withdraw_retracts_clears_bindings_and_bumps_access_version`、`republish_after_withdraw_requires_if_match_and_keeps_content_id`。

Red：先写 9 个测试，运行命令 2 取得原文。

## 4. act/03：trash / restore / purge、R5 / R6、精简任务

文件：`content_service.py`（W4～W6）、`community_contents.py`（W4～W6、R6）、`community_commands.py`（R5 + `compact_community_commands_py`/`compact_once`）；`test_community_publications.py` 追加 7 个：`trash_published_is_409_until_withdrawn`、`restore_after_30_days_is_409`、`restore_keeps_hidden`、`purge_from_active_is_409_and_from_trashed_queues_task`、`detail_etag_304_and_returns_published_snapshot_not_later_revision`、`me_contents_pagination_limit_101_is_400`、`illegal_state_combination_reads_500`。

Red：先写 7 个测试，运行命令 2 取得原文。

## 5. act/04：ACL 扫描、规则测试、可观测性

文件：`tests/test_community_acl_sweep.py`（参数化 `[(entry, reason)]` 18 条；E1/E2/E5 真实请求，E3/E4/E6 `pytest.mark.xfail(strict=True, reason="owner: NC-0xx")`）、`test_community_publications.py` 追加 `logs_never_contain_title_or_body` 与 `outbox_unknown_event_type_is_ignored`（B27/B28）；RULES 仓 `functions/test/community_rules.test.ts`（8 个集合 × 匿名/alice × get/set/update/delete 循环生成 64 个 `assertFails` + 1 个 `assertSucceeds`）。

Red：ACL 9 条真实用例在 access 层未按契约 §5 共用响应体前应红（先用一个故意含 `reason` 字段的响应验证测试能抓到差异，再实现）。

## 6. 禁止

`skip`；`assert status in (...)`；`with_idempotency`；事务回调内网络/推送/sleep；改 `firestore.rules`；改既有测试期望；内存 fake 代替 Emulator；新增依赖。
