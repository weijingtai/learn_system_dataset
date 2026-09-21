# NC-014 验证计划

环境前缀：flutter 命令在 Windows 下把 `D:/apps/apps/flutter/bin` 加入 `PATH`（守卫经 `shutil.which` 解析，D-NC012-23）；命令行默认短超时一律显式设置不少于 600 秒或后台运行后轮询。测试名 = 下表名称逐字；两线合计 26 个（PACKAGE 8 + CLIENT 18）。基线（2026-09-13 实测）：notification `518670b` +194、reading-notes `107ec90` +296/analyze 0。

## 1. 全量命令与期望

| # | 仓库目录 | 命令 | 期望 |
|---|---|---|---|
| 1 | notification | `flutter test` | `+202: All tests passed!`（194 既有 + 8 新增；既有零变红） |
| 2 | notification | `flutter test test/receive/dedup_retention_test.dart` | `+8: All tests passed!` |
| 3 | reading-notes | `flutter analyze` | `No issues found!` |
| 4 | reading-notes | `flutter test test/notifications/community_notifications_test.dart` | `+18: All tests passed!` |
| 5 | reading-notes | `flutter test` | `+314: All tests passed!`（296 既有 + 18 新增；既有零变红） |
| 6 | learn_system | `bash docs/blackbox-spec-rework/reviews/nc014_guard.sh --require-impl all` | 退出 0（K01～K06 全 PASS） |

## 2. act/01（PACKAGE，P01～P08）

测试（`test/receive/dedup_retention_test.dart` 新建，名称逐字）：

```
push_timing_parses_dedup_retention_ms_from_l2_timing
push_timing_parses_absent_dedup_retention_ms_as_null_without_fallback
push_timing_rejects_non_positive_dedup_retention_ms
package_sources_contain_no_hardcoded_dedup_window_literal
dedup_retention_marks_entry_expired_exactly_at_window_boundary
dedup_retention_keeps_entries_strictly_inside_window
dedup_retention_trim_forgets_expired_ids_only
dedup_retention_is_exported_from_package_barrel
```

Red：先写 8 个测试，运行 `flutter test test/receive/dedup_retention_test.dart`，保存编译错原文（`dedupRetention`/`DedupRetention` 未定义）。P04 源码扫描断言 `lib/` 递归不含 `604800000` 与 `Duration(days: 7)`（先例 `test/config/no_hardcoded_values_test.dart`/`a4_factory_lock_test`）。P01 的 L2 fixture 值 `604800000` 抄自 notification/docs/from-server-coder.md §6 下发值（:249-266），不属自造。

## 3. act/02（CLIENT，C01～C18）

测试（`test/notifications/community_notifications_test.dart` 新建，名称逐字）：

```
community_frame_dispatch_routes_notifier_push_and_resync_to_package_pipeline
community_frame_dispatch_routes_community_data_to_business_upsert_without_delivery_id
community_delivery_log_adapter_persists_and_reports_was_duplicate
community_delivery_log_acks_each_device_and_purpose_delivery_verbatim
community_delivery_log_acks_new_delivery_when_business_entry_already_exists
community_persist_failure_sends_no_ack_and_advances_no_cursor
community_delivery_log_trims_dedup_rows_by_package_retention_window
community_receipt_transport_sends_batch_verbatim_to_notifier_receipts
community_receipt_rejection_settles_batch_observable_without_probing
community_connection_token_source_obtains_authorized_channels
community_backfill_source_maps_r10_page_without_transport_ids
community_backfill_entries_upsert_business_list_by_notification_id
community_message_body_fetcher_degrades_when_r9_is_unauthorized_404
community_notification_list_shows_event_count_aggregation
community_notification_tap_opens_content_detail_discussion_top
community_notification_tap_inaccessible_target_lands_unified_placeholder
community_notification_tables_are_scoped_by_account_switch
community_mute_entry_puts_and_deletes_content_mute
```

Red：先改 pubspec 加两个 git 依赖跑 `flutter pub get`（保存依赖缺失原文），再写 18 个测试跑 `flutter test test/notifications/community_notifications_test.dart`，保存 adapters/router 未建编译错原文。C06 为 TASKS:232「落盘失败不 ACK」失败分支：fake 按注入返回 `DeliveryPersistFailed`，断言 ACK 缓冲空且 cursor 未推进。C11/C12 的 R10 条目字段抄契约 §3/§6.1（`latest_notification_id` 用 `ntf_<32 hex>` 占位值）。C15/C16 经 `NotificationTargetRouter` 驱动；占位页文案「该内容已不可访问」逐字断言。C17 用 `CommunityDatabase.openScoped` 同款临时目录范式开两个 scope。

## 4. 守卫

`bash docs/blackbox-spec-rework/reviews/nc014_guard.sh --require-impl all` 退出 0（K01～K06 全 PASS）。K05 断言 PACKAGE 文件集恰 6 个、8 测试名、`lib/` 无 `604800000`、`flutter test ≥202`；K06 断言 CLIENT 文件集恰 6 个、18 测试名、pubspec 双 git 依赖、`lib/src/community` 零改动、`flutter analyze` `No issues found!`、`flutter test ≥314`。基线期（实现未落地）K05/K06 以 `--require-impl` 控制 SKIP。

## 5. 全量回归边界

本任务落线后：notification 包基线由 `+194` 变 `+202`、reading-notes 由 `+296` 变 `+314`（后续工作包以新基线为准）；`nc013_guard.sh --require-impl all` 的计数串（5/568/3、+81、153）属时代钉死，不受本任务影响（REST/SERVER 零写入）；learn_system 守卫链 K01 同时回归 `nc013_guard.sh` 规格模式为 0。
