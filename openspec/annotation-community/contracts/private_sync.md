# 私人同步接入契约：设备授权、传输一次一密、中转删除与数据验收（NC-015，v1.6）

状态：`FROZEN_FOR_NC-015`（2026-09-11）。权威来源：xuan-storage S6 设计稿 `xuan-storage/docs/superpowers/specs/2026-08-02-s6-p2p-sync-third-party-design.md`（已生效裁决 D1/D9/D13～D21，§3.2、§4.0～§4.3、§5.3）；[PRD](../PRD.md) v1.6 R-12/R-13/R-14、§8 E-CRYPTO；[DESIGN](../DESIGN.md) v1.6 §5；[TASKS](../TASKS.md) NC-015/016；[local-persistence](local-persistence.md) §3 outbox；P2P-EVAL 结论 `xuan-migration/docs/dispatch/P2P-EVAL-CONCLUSION-2026-08-23.md`；xuan-storage 现状盘点（2026-09-11，主 Agent）。本文**只做接入**：把 S6 的裁决落到接口、字段、判定顺序与可验证样例，**不重写密码学**；与 S6 冲突处以 S6 为准并回报主 Agent。

## 1. 范围与不做清单

- 本任务产物（学习系统仓库内）：本契约、`fixtures/private_sync/*.json` 正反样例、`tools/check_private_sync_protocol.py` 检查器；不改 xuan-storage、reading-notes、xuan-server。
- 实现归属：§3 guard 补丁、§4 一次一密包装、§5 删除、§6 验收 → NC-016（CLIENT + STORAGE 薄层）；中转通道配置 → NC-016 与运维；导出文件 → NC-017/018。
- **不做**（PRD v1.6、S6 D13/D14）：恢复材料、密钥轮换、escrow/助记词/分片、口令派生长期密钥、云端长期密文、离线接收（接收方不在线则本次同步失败，稍后重试）、Web 端（D18）、匿名账号同步（D1）。

## 2. 身份与作用域

| 名称 | 取值 | 来源 |
|---|---|---|
| `app_user_id` | 服务端派生的账号 ID | functions-py `resolve_app_user_id`（`identity_map/{uid}`），经既有 callable `resolve_my_identity_py` 取得；两设备登录同一账号时相同 |
| `device_id` | 设备安装级随机 ID | `p2p/lib/device_key_store.dart`（`PeerIdentity.deviceId`） |
| `fingerprint` | `SHA-256(设备 Ed25519 公钥)` hex，`:` 分组 | `device_key_store.dart` |
| `key_epoch` | 整数，初值 1；本期不轮换（恒 1） | `TIMPeerAuthorization.keyEpoch` |
| 本地 `scopeUid` | 设备内分区键（每设备各自铸造，互不相同） | `xuan-storage/drift/lib/scope/`（P2P-EVAL §1.2） |

**同步身份 = `app_user_id`**（D-NC015-02）：`SameAccountSessionGuard.verifyPeerSession` 的 `localScopeUid/peerScopeUid` 传入 `app_user_id`，不传本地 `scopeUid`；`OutboxEnvelope.ownerScope` 与传输信封的 `owner` 字段均为 `app_user_id`。本地 `scopeUid` 只用于 Drift 分区，不出设备。匿名登录（Firebase Anonymous）的账号不启用同步（S6 D1）：`app_user_id` 对应 uid 为匿名时，配对入口不可用，guard 返回 `deniedScopeMismatch` 之外不新增状态——由 NC-016 在进入配对前拦截。

## 3. 设备授权

### 3.1 配对（复用 `DevicePairingProtocol.pair`）

流程按 `p2p/lib/device_pairing.dart` 现状：rendezvous → nonce 挑战 → 双方 Ed25519 签名 → channel binding 强制比对（`enforceChannelBindingMatches`，不过即抛错）→ 得到 `PairingResult{remote(deviceId, fingerprint), outOfBandFingerprint, localPublicKeyFingerprint}` → 用户在两端**肉眼或扫码比对** `outOfBandFingerprint` 一致后确认。确认前不得写入授权记录。

### 3.2 授权记录（`TIMPeerAuthorization`，现有字段全部沿用）

| 字段 | 取值 |
|---|---|
| `scopeUid` | `app_user_id` |
| `peerDeviceId` / `peerPublicKeyFingerprint` | 来自 `PairingResult.remote` |
| `accountBindingCertHash` | 配对时对端出示的账号绑定证书哈希（S6 §3.1） |
| `keyEpoch` | 1 |
| `trustState` | `active`；用户在「已授权设备」列表点「移除」后置 `revoked`（持久化在本地授权表，并写 Firestore `users/{uid}/devices/{deviceId}.trustState` 供其他设备同步；D-NC015-03） |
| `expiresAtUtcMs` | 授权时刻 + 180 天（D-NC015-04）；到期需重新配对 |

### 3.3 guard 判定顺序（对 `same_account_im_reconciliation.dart` 的补丁要求，实现归 NC-016）

现有顺序 ①scope 相同 ②`dtlsBindingValid` ③`signatureValid` ④`trustState != revoked` ⑤`keyEpoch` 相同。**必须补三条**（盘点确认现有实现收下参数却不比较）：

6. `peerAuth.peerDeviceId == peerDeviceId`，否则 `deniedRevokedOrUntrusted`；
7. `peerAuth.peerPublicKeyFingerprint == peerFingerprint`，否则 `deniedBadSignature`；
8. `nowUtcMs < peerAuth.expiresAtUtcMs`，否则 `deniedRevokedOrUntrusted`（`AuthorizationDecision` 枚举不新增值；到期归入该值，日志区分原因）。

`dtlsBindingValid` 与 `signatureValid` 由调用方计算：前者 = DTLS 观测指纹与配对声明指纹相等（`device_pairing.dart` 已有）；后者 = 用 `peerAuth.peerPublicKeyFingerprint` 对应公钥验证会话挑战签名。**类名不是证据**：任一为 false 即拒绝，且拒绝发生在交换任何清单/oplog 之前。

## 4. 传输与一次一密

### 4.1 直连（LAN / WebRTC）

WebRTC DataChannel 强制 DTLS，每次连接 ECDHE 临时密钥（S6 §4.2）；应用层不再加密，但**必须**做 §6 的验收。LAN 发现用 `bonsoir`（S6 §3.2），跨网段发现用 Firestore `users/{uid}/devices/{deviceId}`（`{publicKey, lastSeenAt, platform, trustState}`）。TURN 本期不做（P2P-EVAL 缺口③），跨网走 §4.2 中转。

### 4.2 中转（两端无法直连时；D-NC015-01 通道裁定）

| 载荷 | 通道 | 存活上限 | 删除 |
|---|---|---|---|
| 信封（修订元数据 + 正文密文，单条 ≤ 256 KiB） | xuan-server notifier 阅后即焚信箱：`POST /v1/messages/relay` → 对端 SSE 唤醒 → `GET /v1/messages/relay/{id}` → `POST /v1/receipts` 即物理销毁；离线补拉 `GET /v1/messages/relay/backfill` | 中继 TTL 配置为 **300 秒**（`Relay.TTL`），超时未取即销毁 | ACK 主删 + TTL 兜底 |
| 附件对象（> 256 KiB 或二进制） | Firebase Storage `private/p2p/{uid}/{随机UUID}`（S6 §4.2.3，对象名随机、禁用内容哈希；安全规则 `request.auth.uid == uid`） | 接收端下载即删；发送端超时/取消兜底删；GCS 生命周期规则 `age: 1` 天终极兜底 | 三层（S6 §4.2.2） |

两通道都只见密文；正文明文永不进入 notifier 与 Storage。

### 4.3 一次一密包装（每次会话、每个信封独立）

```
发送端：
  1. dek = random(32)                                   # 仅本信封使用
  2. ct  = AES-256-GCM(chunk_i, dek, nonce_i, aad)      # 复用 AesGcmBlobCipher 分块与 nonce 规则（SHA-256(seed‖i)[0:12]）
  3. (eph_priv, eph_pub) = X25519.keygen()              # cryptography 2.9.0 X25519；本会话临时，用完即弃
  4. shared = X25519(eph_priv, recipient_session_pub)   # 接收端会话公钥在 DTLS 会话或配对确认后交换，非持久设备密钥
  5. wrap_key = HKDF-SHA256(ikm=shared, salt=nonce_w(16), info="xuan-private-sync/v1/" + app_user_id + "/" + envelope_seq)
  6. wrapped_dek = AES-256-GCM(dek, wrap_key, nonce_w, aad)
  7. 投递 {ct, wrapped_dek, eph_pub, nonce_w, aad 明文字段}
接收端：
  8. shared = X25519(session_priv, eph_pub) → wrap_key 同上 → dek → 逐块解密 → §6 验收 → 落库 → ACK/删除
```

- `aad = UTF8(app_user_id + "|" + sender_device_id + "|" + recipient_device_id + "|" + envelope_seq)`；现有 `AesGcmBlobCipher` 不传 AAD（盘点确认），NC-016 须增加 `associatedData` 参数（D-NC015-05）。
- Ed25519 设备密钥**只签名不加密**（S6 §五）；X25519 密钥对独立生成，不从 Ed25519 seed 转换。
- 接收端离线：步骤 4 无法取得会话公钥 → 本次同步失败，不落中转（D9）。

### 4.4 信封格式（与 NC-004 `OutboxEnvelope` 对齐）

`SyncEnvelope`（明文字段 + 密文体）：`envelope_version: 1`、`owner: app_user_id`、`sender_device_id`、`recipient_device_id`、`seq`（发送端 outbox seq）、`note_id`、`revision_id`、`op ∈ OutboxOp`、`created_at`、`content_hash`（nchash/v2，与 `NoteRevision.contentHash` 相同）、`signature`（发送端 Ed25519 对 `SHA-256(E(明文字段))` 的签名）、`cipher: {alg: "AES-256-GCM", chunk_count, nonce_seed, wrapped_dek, eph_pub, nonce_w}`、`payload_cipher_ref`（内联密文或 Storage 对象名）。`OutboxEnvelope.payloadCipherRef` 存该引用，`keyEpoch` 存 1（D-NC015-06）。

## 5. 删除与时限

| 层 | 执行者 | 时机 | 判据 |
|---|---|---|---|
| 主删除 | 接收端 | §6 验收通过并落库后立即 ACK/删除 | 落库事务提交前不得 ACK |
| 兜底删除 | 发送端 | 会话超时（300 秒）或用户取消 | 发送端记录已投递对象 ID，超时后逐个删除 |
| 终极兜底 | 平台 | notifier TTL 300 秒；Storage 生命周期 1 天 | 配置项，进 NC-016 验收 |

任何一层失败不影响其他层；三层都失败只造成残留密文，不造成明文泄露。

## 6. 数据验收（接收端；每条信封，缺一不落库）

1. **来源**：`sender_device_id` 与 `fingerprint` 在本机授权表中 `active` 且未过期（§3.3）。
2. **签名**：用该设备公钥验证 `signature`。
3. **AAD 绑定**：解密成功即证明 `app_user_id/sender/recipient/seq` 未被篡改。
4. **内容哈希**：解密后按 nchash/v2 复算 `content_hash`，与信封字段相等；不等即拒收（P2P-EVAL 缺口②的补法）。
5. **Schema**：`NoteRevision` 六字段与 NC-002 Schema 校验通过。
6. **去重与冲突**：`(note_id, revision_id)` 已存在 → 幂等忽略并 ACK；`parent_ids` 不含本机 head → 作为新 head 保留（NC-007 冲突旅程），不覆盖。
7. **落库**：经 `NoteRepository` 公开接口（不直写表）；事务成功后才 ACK。

拒收的信封记录原因码（`source_untrusted / bad_signature / hash_mismatch / schema_invalid`），不 ACK，由 TTL 销毁。

## 7. 正反样例（`fixtures/private_sync/`，每项含 `expected`）

| 文件 | 内容 | expected |
|---|---|---|
| `auth_valid.json` | 授权记录 active、未过期、deviceId/指纹匹配、epoch 1 | `authorized` |
| `auth_expired.json` | `expiresAtUtcMs` < now | `deniedRevokedOrUntrusted` |
| `auth_revoked.json` | `trustState: revoked` | `deniedRevokedOrUntrusted` |
| `auth_device_mismatch.json` | `peerDeviceId` 与记录不同 | `deniedRevokedOrUntrusted` |
| `auth_fingerprint_mismatch.json` | 指纹不同 | `deniedBadSignature` |
| `auth_scope_mismatch.json` | `app_user_id` 不同 | `deniedScopeMismatch` |
| `auth_dtls_mismatch.json` | `dtlsBindingValid: false` | `deniedDtlsMismatch` |
| `auth_epoch_mismatch.json` | `keyEpoch` 2 | `deniedEpochMismatch` |
| `envelope_valid.json` | 完整信封，`content_hash` 逐字取自 `fixtures/community/content_hash_cases.json` 第一个 case 的 `expected_hash`，`signature` 为 128 hex（格式级，见 D-NC015-07） | `accept` |
| `envelope_hash_mismatch.json` | `content_hash` 改一位 | `reject:hash_mismatch` |
| `envelope_bad_signature.json` | 签名改一位 | `reject:bad_signature` |
| `envelope_replay_seq.json` | 与 `envelope_valid` 同 `(note_id, revision_id)` | `duplicate_ack` |
| `envelope_oversize_inline.json` | 内联密文 262145 字节 | `reject:schema_invalid` |
| `relay_ttl.json` | notifier TTL 300 与 Storage age 1 | `config_ok` |
| `deletion_layers.json` | 三层删除时机与执行者 | `layers_ok` |

## 8. 检查器 `tools/check_private_sync_protocol.py`

红条件（任一即退出 1）：本契约缺 §1～§9 任一节标题；缺 `D-NC015-01`～`D-NC015-07`；正文出现 `TBD`/`待定`（扫描前先剔除反引号内的行内代码，本句不算）；`fixtures/private_sync/` 缺 §7 表任一文件；任一样例缺 `expected`；`expected` 不在闭集 `{authorized, deniedScopeMismatch, deniedDtlsMismatch, deniedBadSignature, deniedRevokedOrUntrusted, deniedEpochMismatch, accept, reject:hash_mismatch, reject:bad_signature, reject:schema_invalid, reject:source_untrusted, duplicate_ack, config_ok, layers_ok}`；`relay_ttl.json` 的 `notifier_ttl_seconds != 300` 或 `storage_lifecycle_days != 1`。绿：退出 0 并打印样例计数（恰 15）。检查器用 `unittest` 自测（本机无 pytest）。

## 9. 决定登记（NC-015，主 Agent 裁定，可推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC015-01 | 中转双通道：信封走 notifier 阅后即焚信箱（TTL 300 秒），附件走 Storage `private/p2p/`（生命周期 1 天） | notifier 已实现 ACK 即销毁与 backfill，天然符合 S6「同步完即删」；大附件不适合 Redis 信箱；S6 §4.2.3 已定 Storage 目录与规则 |
| D-NC015-02 | 同步身份为 `app_user_id`，本地 `scopeUid` 不出设备 | P2P-EVAL §1.2：scopeUid 为设备内分区键；guard 需要两端相同的账号标识；`resolve_app_user_id` 已存在 |
| D-NC015-03 | 吊销 = 本地授权表 `revoked` + Firestore 设备文档 `trustState` | 盘点确认无吊销持久化；用既有设备表字段即可，零新集合 |
| D-NC015-04 | 授权有效期 180 天，到期重新配对 | guard 现有 `expiresAtUtcMs` 字段从未比较；必须有一个实值才能测 |
| D-NC015-05 | AES-GCM 增加 AAD 绑定账号/设备/序号 | 盘点确认现有 cipher 无 AAD；防跨账号/跨设备密文误用 |
| D-NC015-06 | `OutboxEnvelope.keyEpoch` 恒 1，`payloadCipherRef` 存中转引用 | 本期不轮换；对齐 NC-004 已冻结字段，不改表 |
| D-NC015-07 | 样例中的签名与密文为格式级（hex 长度、字段齐全、哈希与 NC-002 fixture 逐字一致），密码学有效性由 NC-016 的 Dart 测试用真实 Ed25519/X25519 密钥生成并验证 | 规格仓 Python 环境无 Ed25519/X25519 库；检查器只守契约结构与闭集，不冒充密码学验证 |
