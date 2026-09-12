# NC-017 验证计划

所有命令在 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes` 内运行，每条带 `PATH=/Users/jingtaiwei/flutter/bin:$PATH`。

## 1. 命令

| # | 命令 | 期望 |
|---|---|---|
| 1 | `flutter pub get --offline` | 退出 0；`pubspec.lock` 相对基线只新增 `cryptography` 一段（`version: "2.9.0"`） |
| 2 | `flutter analyze` | `No issues found!` |
| 3 | `flutter test test/export/export_bundle_test.dart` | act/01 后 `+8`；act/02 后 `+14` |
| 4 | `flutter test` | act/01 后 `+247: All tests passed!`；act/02 后 `+253: All tests passed!` |
| 5 | `git diff-tree -r --name-only <NC-011-F 提交> HEAD` | 恰为契约 §2 白名单内实际改动的文件 |
| 6 | `bash docs/blackbox-spec-rework/reviews/nc017_guard.sh --require-impl`（learn_system 内） | act/02 后 0 |

## 2. act/01：格式层（契约 §3～§5、§7、§8 E01～E08）

文件：`pubspec.yaml`、`pubspec.lock`、`lib/src/export/export_bundle_format.dart`、`lib/reading_notes.dart`（导出格式文件）、`test/export/export_bundle_test.dart`。

测试（8，名称逐字）：`argon2id_key_matches_openssl_reference`、`header_digest_and_bytes_match_reference`、`single_chunk_file_matches_reference_sha256`、`decode_reference_file_roundtrips_records`、`raw_bytes_contain_no_plaintext_title_body_attachment_or_ids`、`wrong_passphrase_tamper_reorder_truncate_append_raise_same_undecryptable`、`tampered_header_or_changed_kdf_params_raise_format_error`、`chunk_boundary_exact_multiple_and_plus_one`。

E05 在 act/01 以格式层直接编码实现（构造含独特标题/正文/附件字节的记录，经 `ExportChunkEncoder` 得到文件字节后断言）；act/02 不再改该测试。

Red：先追加依赖并 `flutter pub get --offline`，再写 8 个测试与抛 `UnimplementedError` 的接口骨架，运行命令 3，保存失败原文。

## 3. act/02：写入器（契约 §6、§8 E09～E14）

文件：`lib/src/export/export_writer.dart`、`lib/reading_notes.dart`（导出写入器）、`test/export/export_bundle_test.dart`（追加）。

测试（6，名称逐字）：`writer_exports_active_and_trashed_with_full_revision_chain_excluding_pending_op`、`writer_crash_leaves_only_partial_file`、`writer_verification_failure_deletes_partial`、`writer_rejects_existing_target_empty_passphrase_missing_or_mismatched_attachment`、`writer_reports_progress_and_result_sha256`、`passphrase_is_utf8_without_normalization`。

Red：先追加 6 个测试，运行命令 3（期望 6 个新测试失败或编译失败，E01～E08 不受影响时逐条说明），保存原文。
