# NC-016a 验证计划

环境前缀：每条 flutter 命令带 `PATH=/Users/jingtaiwei/flutter/bin:$PATH`。STORAGE 路径 `W=/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage/.worktrees/nc016-guard-aad`；CLIENT 路径 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`。

## 1. 命令

| # | 目录 | 命令 | 期望 |
|---|---|---|---|
| 1 | xuan-storage 根 | `git worktree add .worktrees/nc016-guard-aad -b fix/nc016-guard-aad 8ddb877` | 退出 0（act/01 开工时一次） |
| 2 | `W/core`、`W/drift`、`W/p2p` | `flutter pub get` | 各退出 0 |
| 3 | `W/core` | `flutter test test/private_sync_guard_fixtures_test.dart` | act/01 后 `+2` |
| 4 | `W/core` | `flutter test test/same_account_im_reconciliation_test.dart` | 前后均 `+4`（改动后含 D-NC016-14 的到期时间替换） |
| 5 | `W/p2p` | `flutter test test/same_account_security_boundary_test.dart` | 前后均 `+3`（改动后含 D-NC016-14 的到期时间替换） |
| 6 | `W/drift` | `flutter test test/blob/aes_gcm_aad_test.dart` | act/01 后 `+1` |
| 7 | `W/drift` | `flutter test test/blob/aes_gcm_blob_cipher_test.dart test/blob/blob_cipher_test.dart` | 通过数与改动前相同（改动前在 act/01 Red 段记录） |
| 8 | CLIENT | `flutter analyze` | `No issues found!` |
| 9 | CLIENT | `flutter test test/storage/private_note_sync_test.dart` | act/02 后 `+6`；act/03 后 `+17` |
| 10 | CLIENT | `flutter test` | act/02 后 `+259: All tests passed!`；act/03 后 `+270: All tests passed!` |
| 11 | learn_system | `bash docs/blackbox-spec-rework/reviews/nc016a_guard.sh --require-impl storage` / `client` | 对应线完成后 0 |

## 2. act/01（STORAGE，契约 §3）

测试（3，名称逐字）：`guard_decisions_match_private_sync_fixtures`、`guard_patch_order_device_then_fingerprint_then_expiry`、`aes_gcm_aad_binds_ciphertext_and_empty_aad_is_backward_compatible`。

Red：建 worktree 并 `pub get` 后，先运行命令 4、5、7 记录改动前通过数；复制样例、写 3 个测试，运行命令 3 与 6 取得失败原文（X01 中至少 `auth_device_mismatch`、`auth_fingerprint_mismatch`、`auth_expired` 三例失败；X03 因参数不存在编译失败）。

## 3. act/02（CLIENT 基础，契约 §4、§5、§8 S01～S06）

测试（6）：`authorization_decisions_match_private_sync_fixtures`、`account_binding_cert_hash_matches_fixture`、`pairing_gate_and_relay_config_match_fixtures`、`apply_remote_revision_creates_note_keeps_branches_and_writes_no_outbox`、`apply_remote_revision_rejects_missing_parent_and_is_atomic`、`mark_envelope_allows_only_forward_transitions`。

Red：先复制 12 个样例、写 6 个测试，运行命令 9 取得编译失败原文。

## 4. act/03（CLIENT 一次一密与验收，契约 §6、§7、§9、§8 S07～S17）

测试（11）：`sealed_envelope_bytes_contain_no_plaintext_title_or_body`、`wrap_and_chunk_match_python_reference_vectors`、`seal_receive_roundtrip_accepts_with_real_keys`、`signed_fields_match_fixture_and_tampered_content_hash_is_bad_signature`、`recipient_mismatch_is_aad_mismatch`、`stored_wrong_content_hash_is_hash_mismatch`、`replay_same_revision_is_duplicate_ack_without_write`、`oversize_inline_payload_is_schema_invalid`、`untrusted_expired_or_revoked_sender_is_source_untrusted`、`session_pub_bad_signature_is_session_key_unbound_before_sealing`、`concurrent_branches_from_two_devices_are_kept_as_heads`。

Red：先写 11 个测试（S07「密文无明文」写在最前），运行命令 9 取得失败原文。
