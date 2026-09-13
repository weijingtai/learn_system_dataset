# NC-013 验证计划

环境前缀：pytest 一律 `PYTHONDONTWRITEBYTECODE=1 FIRESTORE_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099`，Windows 用 `.venv/Scripts/python.exe`、macOS 用 `.venv/bin/python`；dart/npm 命令带 `PATH`（Windows 经 `shutil.which` 由守卫解析，手动执行时 flutter 在 `D:/apps/apps/flutter/bin`）。命令行默认短超时：一律显式设置不少于 600 秒或后台运行后轮询。测试函数名 = `test_` + 下表名称。

## 1. 全量命令与期望

| # | 仓库目录 | 命令 | 期望 |
|---|---|---|---|
| 1 | functions-py | `.venv/Scripts/python.exe -m pytest tests -q -rf -p no:cacheprovider`（带 Emulator 变量） | `5 failed, 568 passed, 3 xfailed`；FAILED 恰为五个既有 ID |
| 2 | xuan-server/server/functions | `npm test -- community_rules`（带 Emulator 变量） | `Tests: 153 passed, 153 total` |
| 3 | repository-rest-adapter | `dart test`（PYTHON/OPENAPI_VALIDATOR 已在环境） | `+81: All tests passed!` |
| 4 | learn_system | `bash docs/blackbox-spec-rework/reviews/nc013_guard.sh --require-impl all` | 退出 0 |

既有失败（不得修复、不得新增）：`tests/test_config.py::test_集合名与_ts_逐项一致`、`tests/test_registration.py::test_全部_callable_已在入口注册`、`tests/test_registration.py::test_三个_trigger_已注册`、`tests/test_registration.py::test_与_入口总数对齐`、`tests/test_registration.py::test_没有多余的未声明导出`。

## 2. act/01（REST，A01～A04）

测试（`test/community_openapi_contract_test.dart` 末尾追加，名称逐字）：

```
notification paths and methods match the catalog
notification schemas are closed objects with notificationRecordId
notification examples manifest has twenty entries and validates
notification mutes are non command writes with rate limit row
```

另按契约 §2.1 授权改两处既有断言：`expectedCatalog` 追加 `'/v1/community/notifications/pull': {'get'},`、`'/v1/community/notifications': {'get'},`、`'/v1/community/notifications/mutes/{content_id}': {'put', 'delete'}` 三行；`interaction examples manifest has seventeen entries and validates` 的 `equals(17)` 改 `greaterThanOrEqualTo(17)`。

Red：先追加 4 个测试与 3 个示例、manifest 3 项，运行 `dart test test/community_openapi_contract_test.dart`，保存「路径/Schema 不存在」失败原文。

## 3. act/02（SERVER 消费与投递纯函数，S01～S19）

测试（`tests/test_community_deliveries.py`，名称 = `test_` + 下名，前 19 个）：

```
dispatch_comment_created_notifies_content_author_with_deterministic_ntf_id
dispatch_comment_reply_notifies_reply_target_not_content_author
dispatch_comment_mention_notifies_mentioned_user
dispatch_mention_and_reply_overlap_creates_single_reply_record
dispatch_reaction_like_notifies_content_author
dispatch_reaction_like_notifies_comment_author
dispatch_self_event_never_notifies_actor
dispatch_same_event_twice_creates_single_record_create_if_absent
dispatch_concurrent_same_event_two_transactions_single_record
dispatch_unknown_event_type_is_idempotent_noop
dispatch_comment_edited_and_deleted_are_noop_without_records
dispatch_content_and_legacy_events_are_noop_without_records
dispatch_transaction_replay_leaves_no_partial_records
notification_id_matches_e_encoding_reference_vectors
notification_record_validates_frozen_schema
like_notification_is_in_app_only_delivered_without_push
comment_notification_attempts_fcm_wakeup_without_body
push_failure_marks_failed_with_backoff_1_2_4_8
retry_after_backoff_advances_and_fifth_failure_abandons
```

Red：`python -c "from xuan.community import notification_dispatch"` 的 ImportError 原文。

## 4. act/03（SERVER 端点与 E6 转真，S20～S32）

测试（同文件追加后 11 个）：

```
push_success_marks_delivered_and_readvance_is_stable
blocked_pair_abandons_without_push_attempt
muted_content_abandons_comment_but_mention_still_dispatches
inaccessible_target_abandons_without_push_attempt
notification_pull_returns_body_for_trusted_binding
notification_pull_unresolved_binding_is_shared_404
notification_pull_non_recipient_is_shared_404
notification_pull_deleted_comment_is_shared_404
notification_list_returns_merged_windows_and_single_mentions
notification_list_cursor_never_regresses_and_limit_bounds
notification_mute_set_unset_is_idempotent_non_command
```

（前 19 + 后 11 = 30 个测试；S30/S31 各对应 1 个测试，S32 为 sweep E6 三例转真，不在 30 个之内。）`tests/test_community_acl_sweep.py` 仅改 E6 三条 param、E6 分支与 docstring 两行（契约 §6.4）。

Red：`from xuan.handlers.community_deliveries import community_deliveries_py` 的 ImportError 原文；E6 三例在标记删除后先以实现缺失失败原文入报告。

## 5. act/04（RULES，R01～R03）

`server/functions/test/community_rules.test.ts` 追加 `community_notifications`、`community_notifier_delivery_bindings`、`community_notification_mutes` 三集合各 8 用例（照 `community_reactions` 现有 8 用例逐字仿写）。Red：先追加用例，运行 `npm test -- community_rules`，保存「未新增 match 前默认拒绝已成立」的 24 用例通过 + 新集合文档缺失断言的原文（如 harness 报集合不存在/拒绝原因不符，以实际输出为准登记）。

## 6. 守卫

`bash docs/blackbox-spec-rework/reviews/nc013_guard.sh --require-impl all` 退出 0（K01～K07 全 PASS）。K06 断言 pytest 计数 `5/568/3` 且 FAILED 集合不变；K07 断言规则 `153 passed`。

## 7. 全量回归边界

本任务落线后：`nc012a_guard.sh --require-impl all` 的 K06 计数（5/535/6）属时代钉死（先例 nc011_guard 496/9），除 K05 manifest 放宽 ≥17（D-NC013-10）外不再更新；learn_system 基线改以 `nc013_guard.sh --require-impl all` 为准。
