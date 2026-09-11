# NC-015 可观察行为

「检查器」指 `.venv/bin/python openspec/annotation-community/tools/check_private_sync_protocol.py`；「自测」指 `.venv/bin/python -m unittest openspec/annotation-community/tools/test_check_private_sync_protocol.py`。

| ID | Given | When | Then |
|---|---|---|---|
| B01 | 契约与 18 个样例齐全 | 检查器 | 退出 0，打印 `samples=18` |
| B02 | 8 个 `auth_*.json` | 读取 | 每个含 `peer_auth`（`scopeUid, peerDeviceId, peerPublicKeyFingerprint, accountBindingCertHash, keyEpoch, trustState, expiresAtUtcMs`）、`session`（`localScopeUid, peerScopeUid, peerDeviceId, peerFingerprint, peerKeyEpoch, dtlsBindingValid, signatureValid, nowUtcMs`）与 `expected`；`expected` 逐字等于契约 §7 |
| B03 | `auth_expired.json` | 读取 | `session.nowUtcMs >= peer_auth.expiresAtUtcMs` |
| B04 | `auth_device_mismatch.json` / `auth_fingerprint_mismatch.json` | 读取 | 分别只有 `peerDeviceId` / `peerFingerprint` 与 `peer_auth` 不同，其余字段相同 |
| B05 | `envelope_valid.json` | 读取 | 含契约 §4.4 全部明文字段与 `signed_fields`（恰为 §4.4 十个字段名、顺序一致）；`content_hash` 逐字等于 `content_hash_cases.json` 第一个 case 的 `expected_hash`；`signature` 匹配 `^[0-9a-f]{128}$`；`cipher.alg == "AES-256-GCM"`；`expected == "accept"` |
| B06 | `envelope_hash_mismatch.json` | 读取 | `signature` 与 `content_hash` 均与 `envelope_valid` 相同，只多 `decrypted_content_hash` 且与 `content_hash` 不同；`expected == "reject:hash_mismatch"` |
| B07 | `envelope_bad_signature.json` | 读取 | 仅 `content_hash` 一个字符不同（被签名字段被改）；`expected == "reject:bad_signature"` |
| B08 | `envelope_replay_seq.json` | 读取 | `note_id`、`revision_id` 与 `envelope_valid` 相同、`seq` 不同；`expected == "duplicate_ack"` |
| B09 | `envelope_oversize_inline.json` | 读取 | `inline_cipher_bytes == 262145`；`expected == "reject:schema_invalid"` |
| B10 | `relay_ttl.json` / `deletion_layers.json` | 读取 | 前者 `notifier_role == "signaling_only"`、`sender_fallback_seconds == 300`、`storage_lifecycle_days == 1`；后者三层 `executor` 为 `receiver/sender/platform` |
| B11 | 契约缺任一节标题、缺任一 D 编号、含 `TBD`/`待定` | 检查器（自测用临时副本注入） | 退出 1 并打印缺失项 |
| B12 | 样例缺 `expected`、`expected` 不在闭集、缺任一文件、`sender_fallback_seconds` 不为 300 | 检查器（自测临时副本） | 退出 1 |
| B13 | 自测 | `unittest` | ≥ 15 个测试全过，覆盖 B01～B16 每条 |
| B14 | `envelope_aad_mismatch.json` | 读取 | 仅 `recipient_device_id` 与 `envelope_valid` 不同；`expected == "reject:aad_mismatch"` |
| B15 | `session_pub_bad_signature.json` | 读取 | 含 `session_pub`（64 hex）、`session_pub_sig`（128 hex）、`session_id`；`expected == "session_key_unbound"` |
| B16 | `pairing_anonymous.json` | 读取 | `is_anonymous == true`；`expected == "pairing_refused_anonymous"` |
