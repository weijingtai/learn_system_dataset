# NC-026 验证计划

环境前缀：pytest 一律 `PYTHONDONTWRITEBYTECODE=1 FIRESTORE_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099`，Windows 用 `.venv/Scripts/python.exe`、macOS 用 `.venv/bin/python`；dart/npm/flutter 经 `shutil.which` 由守卫解析（手动执行时 flutter 在 `D:/apps/apps/flutter/bin`）。命令行默认短超时：一律显式设置不少于 600 秒或后台运行后轮询。测试函数名 = `test_` + 下表名称。

## 1. 全量命令与期望

| # | 仓库目录 | 命令 | 期望 |
|---|---|---|---|
| 1 | functions-py | `.venv/Scripts/python.exe -m pytest tests -q -rf -p no:cacheprovider`（带 Emulator 变量） | `5 failed, 594 passed, 3 xfailed`；FAILED 恰为五个既有 ID |
| 2 | xuan-server/server/functions | `npm test -- community_rules`（带 Emulator 变量） | `Tests: 157 passed, 157 total` |
| 3 | repository-rest-adapter | `dart test`（`PYTHON`/`OPENAPI_VALIDATOR` 已注入） | `+85: All tests passed!` |
| 4 | reading-notes | `flutter analyze`；`flutter test` | `No issues found!`；`+314: All tests passed!` |
| 5 | learn_system | `bash docs/blackbox-spec-rework/reviews/nc026_guard.sh --require-impl all` | 退出 0 |

计数推导：SERVER act/02 后 `5 failed, 578 passed, 3 xfailed`（568+10）；act/03 后 `5 failed, 594 passed, 3 xfailed`（568+26）。REST `81+4=85`。CLIENT `296+18=314`。RULES `153+4=157`。

既有失败（不得修复、不得新增）：`tests/test_config.py::test_集合名与_ts_逐项一致`、`tests/test_registration.py::test_全部_callable_已在入口注册`、`tests/test_registration.py::test_三个_trigger_已注册`、`tests/test_registration.py::test_与_入口总数对齐`、`tests/test_registration.py::test_没有多余的未声明导出`。

## 2. act/01（REST，A01～A04）

测试（`test/community_openapi_contract_test.dart` 末尾追加，名称逐字）：

```
analytics paths and methods match the catalog
analytics schemas are closed objects with pseudonym and batch bounds
analytics examples manifest has twenty two entries and validates
analytics rate limit and error rows are declared
```

另按契约 §10 授权改两处既有断言：`expectedCatalog` 追加 `'/v1/analytics/events': {'post'},`、`'/v1/analytics/pseudonym': {'get'},` 两行；`notification examples manifest has twenty entries and validates` 的 `equals(20)` 改 `greaterThanOrEqualTo(20)`（D-NC026-22）。

Red：先追加 4 个测试与 2 个示例、manifest 2 项，运行 `dart test test/community_openapi_contract_test.dart`，保存「路径/Schema 不存在」失败原文。

## 3. act/02（SERVER Schema 与信封，S01～S05、S06、S07～S10）

测试（`tests/test_behavior_events.py`，名称 = `test_` + 下名，前 10 个）：

```
behavior_event_schema_is_closed_and_matches_frozen_copy
frozen_behavior_event_schema_sha256_matches_contract_literal
server_event_document_matches_frozen_schema_after_command
server_event_carries_object_type_and_object_id_per_operation_map
server_event_note_ref_is_null_and_platform_is_server
client_event_id_format_is_bev_prefixed_uuid_v4
attributes_allowlist_rejects_unknown_keys_per_event_type
private_note_event_requires_all_six_revision_attributes
private_note_event_rejects_server_only_attributes
behavior_event_examples_validate_two_valid_and_twenty_one_invalid
```

`frozen_behavior_event_schema_sha256_matches_contract_literal` 的比对值为**常量** `SCHEMA_SHA = f3467224ddafa5ff3ac2a43011521a5cc0b8acf6293244d632fa291c97451e42`（契约 §9.1），不得在测试内用 `hashlib` 现算期望值；`tests/test_community_validation.py` 的字典字面量同步改为该值。`bev_` 参考字面量同样禁止现算。

Red：先复制 Schema 并写 10 个测试，运行 `pytest tests/test_behavior_events.py -q`，保存「`from xuan.community import behavior_events` ImportError」与「Schema SHA / 外层字段不符」原文。

## 4. act/03（SERVER 端点与假名，S11～S26）

测试（同文件追加后 16 个）：

```
analytics_events_ingests_client_events_and_fills_received_at
analytics_events_is_idempotent_by_event_id_and_counts_duplicates
analytics_events_batch_over_500_is_413
analytics_events_rejects_server_event_type_on_client_endpoint
analytics_events_invalid_schema_reports_json_pointer
analytics_events_batch_splits_into_transactions_of_hundred
analytics_events_unauthenticated_is_401
analytics_events_rate_limit_row_matches_contract
analytics_events_does_not_touch_ledger_or_notifications
analytics_events_partial_failure_returns_503_and_retry_dedupes
pseudonym_endpoint_returns_stable_random_pseudonym
pseudonym_endpoint_creates_mapping_once_without_behavior_event
pseudonym_is_shared_between_command_and_client_event_paths
pseudonym_is_random_across_two_independent_projects
event_documents_never_contain_account_id
server_code_has_no_update_or_delete_on_behavior_events
```

（前 10 + 后 16 = 26。）Red：`from xuan.handlers.analytics_events import analytics_events_py` 的 ImportError 原文。

## 5. act/04（CLIENT，C01～C18）

测试（`test/analytics/private_note_metrics_test.dart`，名称逐字）：

```
revision_saved_emits_six_attribute_event
char_count_counts_code_points_not_utf16_or_bytes
session_ended_emits_duration_and_revision_count
event_id_is_bev_prefixed_uuid_v4
note_ref_is_sha256_of_pseudonym_and_note_id
raw_report_bytes_never_contain_note_id_title_body_or_attachment_name
pseudonym_is_fetched_once_and_cached
pseudonym_cache_is_cleared_on_account_switch
queue_keeps_events_when_flush_fails
queue_drops_oldest_beyond_ten_thousand
dropped_before_is_attached_to_next_report_only
dropped_before_absent_when_nothing_was_dropped
flush_sends_batches_of_at_most_five_hundred
flush_removes_only_acknowledged_events
flush_reports_failed_without_throwing
events_persist_across_store_restart
revision_saved_does_not_block_save_on_transport_failure
report_payload_has_no_extra_keys
```

`note_ref_is_sha256_of_pseudonym_and_note_id` 与 `char_count_counts_code_points_not_utf16_or_bytes` 的期望值为**字面量**（契约 §9.3、`"a𠀀b"` → 3），不得在测试内现算。

Red：`flutter test test/analytics/private_note_metrics_test.dart` 的「文件不存在 / 未定义符号」原文。

## 6. act/05（RULES，R01～R03）

`server/functions/test/community_rules.test.ts` 追加 `describe('BehaviorEvent is append-only (NC-026)')`：两个上下文（`unauthenticated`、`alice (authenticated)`）× 2 用例（`deny update on community_behavior_events`、`deny delete on community_behavior_events`）= 4 用例，153 → 157。`server/firestore.rules` 禁改。Red：先加用例运行 `npm test -- community_rules`，保存实际输出（默认拒绝已生效时红值为用例尚未落入清单前的计数差）。

## 7. 守卫

`bash docs/blackbox-spec-rework/reviews/nc026_guard.sh --require-impl all` 退出 0。K05 REST（manifest 22、dart ≥85）；K06 SERVER（26 测试名、无作弊、`bev_` 与 `note_ref` 字面量、保护路径零改动、pytest `5/594/3` 且 FAILED 集合不变、三新文件 `exactly-once` 零命中）；K07 CLIENT（18 测试名、analyze 0、`+314`）；K08 RULES（4 新用例、`157 passed`）。

## 8. Windows 适配（D-NC026-21）

`openspec/schemas/verify_community.sh` 是 NC-002 产物（`.venv/bin` 与 `file:///d/...` base-uri 在 Windows 不可用），本任务不改它；守卫用 `.venv/Scripts/check-jsonschema.exe --base-uri "file:///D:/Programme/learn_system/openspec/schemas/" --schemafile ...` 对 §9.2 的 23 个示例做 2 正 21 负校验（2026-09-13 已实跑通过）。

## 9. 全量回归边界

本任务落线后：`nc013_guard.sh --require-impl all` 的 K06 计数（5/568/3）属时代钉死（先例 nc011_guard），按 D-NC013-10 口径只放宽清单条数与计数断言，不逐条重写；learn_system 基线改以 `nc026_guard.sh --require-impl all` 为准。
