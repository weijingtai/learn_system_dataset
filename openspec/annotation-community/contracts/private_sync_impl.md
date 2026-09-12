# 私人同步实现契约：guard 补丁、AES-GCM AAD、一次一密信封与接收验收（NC-016a）

状态：`FROZEN_FOR_NC-016a`（2026-09-12）。权威来源：[private_sync.md](private_sync.md)（NC-015：身份、授权、一次一密、信封、删除、七步验收、18 个样例；本文 §10 回填其补充）；[TASKS](../TASKS.md) NC-016；[DESIGN](../DESIGN.md) 第 27、215、223、225 行；[local-persistence](local-persistence.md) §4 outbox、§5 仓储；[private_export.md](private_export.md)（`canonicalJson`、修订 13 字段映射）。S6 模型：没有长期密钥、没有云端备份、没有恢复材料；本文不涉及任何恢复材料。执行者照抄；与上游冲突以上游为准并停手上报。

## 1. 范围、仓库与基线

- **NC-016 拆分（D-NC016-01）**：本文 = **NC-016a**（进程内实现与单元/组件测试，可立即执行）。TASKS 中「`CLIENT/example/integration_test/private_device_sync_test.dart` 在设备表登记的两台真实设备上分别验证 LAN 与 WebRTC」= **NC-016b**，`BLOCKED`：INTEGRATION_BASELINE 第 59 行「两台设备 未盘点/未验证」，NC-001 总项未 ACCEPTED；中转上传、notifier 信令、宿主装配、`SyncRuntime` 注册也归 16b。

| 线 | 仓库 | 基线（2026-09-12 实测） |
|---|---|---|
| STORAGE | `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage`（`main` `8ddb877`） | 临时副本 `flutter pub get` 三包均 0；`core/test/same_account_im_reconciliation_test.dart` `+4`；`p2p/test/same_account_security_boundary_test.dart` `+3`；`drift/test/blob/aes_gcm_blob_cipher_test.dart` `+10` |
| CLIENT | `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（`main` `4a0d70a`） | `flutter test` `+253`；`flutter analyze` 0；已有 `cryptography: 2.9.0`（NC-017） |

- **STORAGE 分支纪律（D-NC016-03）**：xuan-storage `AGENTS.md` 禁止任何 agent 在 `main` 上改代码。执行者在仓库根执行 `git worktree add .worktrees/nc016-guard-aad -b fix/nc016-guard-aad 8ddb877`，全部改动与提交只在该 worktree；**不合并、不 rebase 到 main、不 push**（合并由仓库所有者决定）。worktree 内三包各执行一次 `flutter pub get`；`pubspec.lock` 已被忽略，`.dart_tool/` 未被忽略但**不得 git add**。
- CLIENT 在 `main` 上直接提交（reading-notes 无分支限制，沿用 NC-010/011/017）。

## 2. 写入白名单

### 2.1 STORAGE（仅 worktree `.worktrees/nc016-guard-aad`）

| 文件 | 允许的改动 |
|---|---|
| `core/lib/sync/same_account_im_reconciliation.dart` | 只改 `SameAccountSessionGuard.verifyPeerSession`（§3.1） |
| `core/lib/model/blob_cipher.dart` | 只给 `encryptChunk`、`decryptChunk` 各加一个带缺省值的命名参数（§3.2） |
| `drift/lib/blob/aes_gcm_blob_cipher.dart` | 把该参数传入 `encrypt`/`decrypt` 的 `aad` |
| `drift/lib/blob/identity_blob_cipher.dart` | 签名跟随接口，参数忽略 |
| `drift/test/blob/blob_cipher_test.dart` | 只改 `TestPrivateCipher` 两个方法签名跟随接口，不改任何断言 |
| `core/test/private_sync_guard_fixtures_test.dart` | 新增（§3.3） |
| `core/test/fixtures/private_sync/auth_*.json` | 新增：learn_system `openspec/annotation-community/fixtures/private_sync/` 下 8 个 `auth_*.json` 逐字节复制 |
| `drift/test/blob/aes_gcm_aad_test.dart` | 新增（§3.3） |

### 2.2 CLIENT（reading-notes）

| 文件 | 允许的改动 |
|---|---|
| `lib/src/storage/private_note_mapper.dart` | 新增（§4） |
| `lib/src/storage/private_note_sync.dart` | 新增（§6、§7） |
| `lib/src/persistence/note_repository.dart` | **只在类末尾追加** §5 两个公开方法与所需私有辅助；不改既有方法 |
| `lib/reading_notes.dart` | 追加两行导出 |
| `test/storage/private_note_sync_test.dart` | 新增（§8） |
| `test/fixtures/private_sync/` | 新增：8 个 `auth_*.json` 与 `envelope_valid.json`、`pairing_anonymous.json`、`relay_ttl.json`、`deletion_layers.json`，共 12 个，逐字节复制 |

两线禁止：白名单外任何文件；`pubspec.yaml`/`pubspec.lock` 变更；新依赖；改既有测试期望；`skip`；永真断言；测试内调用被测函数生成参考值（§9 用字面量）；先实现后补测试；`git push`；删除文件（STORAGE worktree 创建除外）。

## 3. STORAGE 补丁

### 3.1 guard（private_sync §3.3 第 6～8 条）

`verifyPeerSession` 追加可选命名参数 `int? nowUtcMs`（缺省取 `DateTime.now().toUtc().millisecondsSinceEpoch`），既有 5 步顺序与返回值不变，第 5 步之后依次追加：

6. `peerAuth.peerDeviceId != peerDeviceId` → `AuthorizationDecision.deniedRevokedOrUntrusted`
7. `peerAuth.peerPublicKeyFingerprint != peerFingerprint` → `AuthorizationDecision.deniedBadSignature`
8. `now >= peerAuth.expiresAtUtcMs` → `AuthorizationDecision.deniedRevokedOrUntrusted`

`AuthorizationDecision` 枚举不新增值；既有调用方（`SameAccountIMReconciler` 与 p2p 测试）不改。

### 3.2 BlobCipher AAD（D-NC015-05）

```dart
Future<List<int>> encryptChunk(List<int> plain, {required int chunkIndex, List<int> associatedData = const <int>[]});
Future<List<int>> decryptChunk(List<int> cipherBytes, {required int chunkIndex, required int keyVersion, List<int> associatedData = const <int>[]});
```

`AesGcmBlobCipher` 在 `_aesGcm.encrypt(..., aad: associatedData)` 与 `_aesGcm.decrypt(SecretBox(...), secretKey: _dek, aad: associatedData)` 传入；缺省空数组与改动前字节行为完全一致（既有密文仍可解）。认证失败仍抛 `BlobUndecryptableError`。

### 3.3 STORAGE 测试（名称逐字）

| ID | 文件 | 测试 | 断言 |
|---|---|---|---|
| X01 | `core/test/private_sync_guard_fixtures_test.dart` | `guard_decisions_match_private_sync_fixtures` | 8 个 `auth_*.json`：`peer_auth` → `TIMPeerAuthorization`，`session` 各字段（含 `nowUtcMs`）→ 调用参数；`decision.name == expected` |
| X02 | 同上 | `guard_patch_order_device_then_fingerprint_then_expiry` | 设备 ID、指纹均不符且已过期 → `deniedRevokedOrUntrusted`；只指纹不符且已过期 → `deniedBadSignature`；只过期 → `deniedRevokedOrUntrusted`；`nowUtcMs == expiresAtUtcMs` → `deniedRevokedOrUntrusted` |
| X03 | `drift/test/blob/aes_gcm_aad_test.dart` | `aes_gcm_aad_binds_ciphertext_and_empty_aad_is_backward_compatible` | 同 AAD 往返相等；解密时换 AAD → `BlobUndecryptableError`；两端都缺省 AAD 往返相等；加密缺省、解密带 AAD → `BlobUndecryptableError` |

计数：`core` 新文件 `+2`，`same_account_im_reconciliation_test.dart` 仍 `+4`；`drift` 新文件 `+1`，`aes_gcm_blob_cipher_test.dart` 仍 `+10`，`blob_cipher_test.dart` 通过数不变；`p2p/test/same_account_security_boundary_test.dart` 仍 `+3`。

## 4. CLIENT mapper 与纯函数（`private_note_mapper.dart`）

```dart
const String privateNoteEntityType = 'private_note_revision';
const String publicSnapshotEntityType = 'public_snapshot';
const Map<String, String> privateSyncEntityPolicies = {privateNoteEntityType: 'private', publicSnapshotEntityType: 'shared'};
const Set<String> syncedOutboxOps = {'revision_saved', 'heads_merged'};   // D-NC016-06
const String relayNotifierRole = 'signaling_only';
const int relaySenderFallbackSeconds = 300;
const int relayStorageLifecycleDays = 1;
const int authorizationValidityDays = 180;
const int maxInlinePayloadBytes = 262144;
const String pairingRefusedAnonymousMessage = '请先绑定邮箱后再配对设备';

class WireSchemaInvalid implements Exception { const WireSchemaInvalid(this.field); final String field; }

Map<String, Object?> revisionToWire(NoteRevision r);          // 13 键，嵌套元素用各自 toMap()（同 private_export §4.2）
NoteRevision revisionFromWire(Map<String, Object?> m);        // 校验见下，失败抛 WireSchemaInvalid(字段名)
Uint8List encodeSyncPayload({required Note note, required NoteRevision revision});  // UTF-8(canonicalJson({"note": {"id","kind","created_at"}, "revision": revisionToWire(revision)}))
String accountBindingCertHash(String appUserId, String peerDeviceId, String peerPublicKeyFingerprint); // SHA-256_hex(UTF8(a + "|" + d + "|" + f))

enum AuthorizationDecision { authorized, deniedScopeMismatch, deniedDtlsMismatch, deniedBadSignature, deniedRevokedOrUntrusted, deniedEpochMismatch }
class DeviceAuthorization { const DeviceAuthorization({required this.scopeUid, required this.peerDeviceId, required this.peerPublicKeyFingerprint, required this.accountBindingCertHash, required this.keyEpoch, required this.trustState, required this.expiresAtUtcMs}); /* 7 个 final 字段，与 TIMPeerAuthorization 同名 */ }
AuthorizationDecision decideAuthorization({required String localScopeUid, required String peerScopeUid, required String peerDeviceId, required String peerFingerprint, required int peerKeyEpoch, required DeviceAuthorization? peerAuth, required bool dtlsBindingValid, required bool signatureValid, required int nowUtcMs});
String pairingGate({required bool isAnonymous});   // true → 'pairing_refused_anonymous'；false → 'allowed'
```

- `canonicalJson` 从 `package:reading_notes` 的 `export_bundle_format.dart` 导入复用，不另写。
- `decideAuthorization` 的 8 步与 §3.1 修补后的 guard 完全相同（D-NC016-04）。
- `revisionFromWire` 校验：键集合恰为 13 键；`id`、`restored_from`（非 null 时）与 `parent_ids` 各元素匹配 `^nrev_[0-9a-f]{32}$` 且 `parent_ids` 无重复；`note_id` 匹配 `^note_[0-9a-f]{32}$`；`title`、`markdown`、`change_summary`、`created_at` 为字符串；`created_on_device` 为非空字符串；`content_hash` 匹配 `^[0-9a-f]{64}$`；`attachment_refs`/`mentions`/`bindings` 为列表且每个元素经 `AttachmentRef.fromMap`/`MentionRef.fromMap`/`BindingRef.fromMap` 构造不抛异常。

## 5. `NoteRepository` 追加方法（local-persistence §5 的增量，D-NC016-10）

```dart
enum RemoteApplyOutcome { applied, duplicate }
class RemoteParentMissing implements Exception { const RemoteParentMissing(this.parentId); final String parentId; }

Future<RemoteApplyOutcome> applyRemoteRevision({required String noteId, required NoteKind kind, required String noteCreatedAt, required NoteRevision revision});
Future<void> markEnvelope(int seq, OutboxState state);
```

`applyRemoteRevision` 固定步骤：① 会话代数检查（同 §5.1 第 1 条）；② `revision.noteId != noteId` → `ArgumentError`；③ `getRevision(revision.id)` 已存在 → 返回 `duplicate`，不写任何行；④ 笔记不存在：`revision.parentIds` 必须为空，否则抛 `RemoteParentMissing(第一个父 ID)`；笔记存在：每个父 ID 必须是本笔记已有修订，否则抛 `RemoteParentMissing`；⑤ `db.transaction` 内：笔记不存在时插入 `notes`（`id=noteId`、`owner_scope=ownerScope`、`kind`、`preferred_head_id=revision.id`、`lifecycle=active`、`pending_op=none`、`created_at=noteCreatedAt`、`updated_at=clock.nowUtc()`）；插入 `note_revisions`（13 字段逐字取自 `revision`，含 `content_hash` 与 `created_on_device`）；删除本笔记 `note_heads` 中 `revision_id ∈ revision.parentIds` 的行，插入 `(noteId, revision.id)`；笔记已存在时，若 `revision.parentIds` 含当前 `preferred_head_id` 则改为 `revision.id`，否则保持（分支保留，由 NC-007 冲突横幅呈现）；写 `updated_at`。**不写 outbox**（不回声）。任一语句异常 → 回滚并抛 `SaveFailed(cause)`；⑥ 返回 `applied`。

`markEnvelope`：会话代数检查；只允许 `pending→sent`、`sent→acked`、`sent→pending`，其余抛 `StateError('illegal outbox transition')`；`seq` 不存在抛 `StateError('unknown outbox seq')`。

## 6. 一次一密与信封（`private_note_sync.dart`）

### 6.1 端口与模型

```dart
abstract class DeviceSigner { String get deviceId; Future<List<int>> sign(List<int> payload); }
abstract class DeviceSignatureVerifier { Future<bool> verify({required String deviceId, required List<int> payload, required List<int> signature}); }
abstract class TrustedDeviceDirectory { Future<DeviceAuthorization?> lookup({required String appUserId, required String deviceId}); }

class SessionOffer { const SessionOffer({required this.sessionId, required this.sessionPub, required this.sessionPubSig}); final String sessionId; final List<int> sessionPub; final List<int> sessionPubSig; }
class ReceiverSession { const ReceiverSession({required this.sessionId, required this.senderDeviceId, required this.keyPair}); final String sessionId; final String senderDeviceId; final SimpleKeyPair keyPair; }
class SessionKeyUnbound implements Exception { const SessionKeyUnbound(); }
class UnsupportedSyncOp implements Exception { const UnsupportedSyncOp(this.op); final String op; }

class SealedEnvelope {  // 字段与 private_sync §4.4 同名；toJson/fromJson 用 snake_case
  final int envelopeVersion; final String owner; final String senderDeviceId; final String recipientDeviceId;
  final int seq; final String noteId; final String revisionId; final String op; final int createdAt; final String contentHash;
  final int chunkCount; final String nonceSeedHex; final String wrappedDekHex; final String ephPubHex; final String nonceWHex;
  final String payloadCipherRef;    // 16a 恒为 "inline"
  final Uint8List payload;          // JSON 中为 payload_inline_b64（标准 base64）
  final String signatureHex;
}
const List<String> signedFieldNames = ['envelope_version', 'owner', 'sender_device_id', 'recipient_device_id', 'seq', 'note_id', 'revision_id', 'op', 'created_at', 'content_hash'];
```

### 6.2 发送端 `PrivateNoteSyncSender.seal`

`PrivateNoteSyncSender({required NoteRepository repository, required DeviceSigner signer, required DeviceSignatureVerifier verifier, required String appUserId, List<int> Function(int length)? randomBytes})`；`Future<SealedEnvelope> seal({required OutboxEnvelope outbox, required String recipientDeviceId, required SessionOffer offer})`：

0. 会话公钥绑定（D-NC015-09）：`verifier.verify(deviceId: recipientDeviceId, payload: SHA256(UTF8(appUserId|recipientDeviceId|signer.deviceId|offer.sessionId)) ‖ offer.sessionPub, signature: offer.sessionPubSig)` 为 false → 抛 `SessionKeyUnbound`，不生成任何密文。
1. `outbox.op ∉ syncedOutboxOps` → `UnsupportedSyncOp`；取 `repository.getNote(outbox.noteId)` 与 `repository.getRevision(outbox.revisionId!)`。
2. `plain = encodeSyncPayload(note, revision)`。
3. 随机数（均经 `randomBytes`，缺省 `Random.secure()`）按此顺序取：`dek = randomBytes(32)`、`seed = randomBytes(16)`、`nonceW = randomBytes(16)`、`ephSeed = randomBytes(32)`；`eph = X25519().newKeyPairFromSeed(ephSeed)`。
4. `aad = UTF8(appUserId + "|" + signer.deviceId + "|" + recipientDeviceId + "|" + seq 十进制)`。按 1048576 字节切块（末块 1～1048576，不产生空块）；第 i 块：`nonce_i = SHA256(seed ‖ UTF8(i 十进制))[0:12]`，`aad_i = aad ‖ i（4 B 大端）‖ final（末块 0x01，其余 0x00）`（D-NC016-05），`box = AesGcm.with256bits(nonceLength: 12).encrypt(plain_i, secretKey: dek, nonce: nonce_i, aad: aad_i)`，块字节 = `box.cipherText ‖ box.mac.bytes`；`payload = Σ（块长 4 B 大端 ‖ 块字节）`。
5. `shared = X25519().sharedSecretKey(keyPair: eph, remotePublicKey: SimplePublicKey(offer.sessionPub, type: KeyPairType.x25519))`；`wrapKey = Hkdf(hmac: Hmac.sha256(), outputLength: 32).deriveKey(secretKey: shared, nonce: nonceW, info: UTF8("xuan-private-sync/v1/" + appUserId + "/" + seq 十进制))`；`wrapped = AesGcm.with256bits(nonceLength: 12).encrypt(dek, secretKey: wrapKey, nonce: nonceW[0:12], aad: aad)`，`wrappedDek = cipherText ‖ mac`（48 B）。
6. `signed = {signedFieldNames 各字段}`（`created_at = DateTime.parse(outbox.createdAt).toUtc().millisecondsSinceEpoch`，`content_hash = revision.contentHash`，`op = outbox.op` 数据库值）；`digest = SHA256(encode(signed))`（`encode` 为 reading-notes `nchash.dart` 的 E）；`signature = signer.sign(digest)`。
7. 返回 `SealedEnvelope`（`payloadCipherRef = "inline"`、`chunkCount`、各 hex 小写）。

### 6.3 接收端 `PrivateNoteSyncReceiver`

`PrivateNoteSyncReceiver({required NoteRepository repository, required TrustedDeviceDirectory directory, required DeviceSignatureVerifier verifier, required DeviceSigner signer, required String appUserId, required int Function() nowUtcMs, List<int> Function(int length)? randomBytes})`：

- `Future<(SessionOffer, ReceiverSession)> openSession({required String senderDeviceId})`：`sessionId = 'sess_' + 32 hex`（`randomBytes(16)`），`keyPair = X25519().newKeyPairFromSeed(randomBytes(32))`，`sessionPubSig = signer.sign(SHA256(UTF8(appUserId|signer.deviceId|senderDeviceId|sessionId)) ‖ sessionPub)`。
- `Future<String> receive(SealedEnvelope env, ReceiverSession session)` 返回结果码，判定顺序固定（private_sync §6，前置第 0 步见 D-NC016-07）：

| 步 | 判定 | 结果码 |
|---|---|---|
| 0 结构 | `envelopeVersion != 1`；`payloadCipherRef != "inline"`；`payload.length > maxInlinePayloadBytes`；`op ∉ syncedOutboxOps`；hex 长度不为 `nonceSeed 32 / wrappedDek 96 / ephPub 64 / nonceW 32 / signature 128`；`contentHash` 非 64 位小写 hex；`chunkCount < 1`；`senderDeviceId != session.senderDeviceId` | `reject:schema_invalid` |
| 1 来源 | `env.owner != appUserId`；或 `directory.lookup` 为 null；或记录 `scopeUid != appUserId`、`peerDeviceId != env.senderDeviceId`、`trustState != 'active'`、`nowUtcMs() >= expiresAtUtcMs`、`keyEpoch != 1` 任一成立（D-NC016-11） | `reject:source_untrusted` |
| 2 签名 | `verifier.verify(deviceId: env.senderDeviceId, payload: SHA256(encode(signed)), signature)` 为 false | `reject:bad_signature` |
| 3 解密 | 以本机视角 `aad = UTF8(appUserId|env.senderDeviceId|signer.deviceId|env.seq)` 解包 `wrappedDek` 与逐块解密（`aad_i` 同 §6.2）；任何认证失败、分块帧不完整、块数 ≠ `chunkCount` | `reject:aad_mismatch` |
| 4 哈希 | 明文不是 UTF-8 JSON 对象、缺 `note`/`revision`、`revisionFromWire` 抛 `WireSchemaInvalid` → `reject:schema_invalid`；`contentHash(normalizeSnapshot(六字段投影)) != env.contentHash` 或 `!= revision.contentHash` | `reject:hash_mismatch` |
| 5 一致 | `revision.id != env.revisionId`；`revision.noteId != env.noteId`；`note.id != env.noteId`；`note.kind ∉ {note, annotation}` | `reject:schema_invalid` |
| 6 去重 | `repository.getRevision(revision.id) != null` | `duplicate_ack` |
| 7 落库 | `applyRemoteRevision(...)` 返回 `applied` → `accept`；抛 `RemoteParentMissing` → `reject:schema_invalid`；抛 `SaveFailed` → 原样上抛（不 ACK） | `accept` |

## 7. 「密文无明文」（TASKS 负向断言，D-NC016-12）

对 `SealedEnvelope.toJson()` 的 UTF-8 字节与 `payload` 原始字节分别断言：不含修订标题、正文任一 20 字符片段、`change_summary` 的 UTF-8 子序列。只断言「解密后可读」不算通过。

## 8. CLIENT 测试（`test/storage/private_note_sync_test.dart`，临时目录真实 Drift 文件库，名称逐字）

| ACT | ID | 测试 | 关键断言 |
|---|---|---|---|
| 02 | S01 | `authorization_decisions_match_private_sync_fixtures` | 读 `test/fixtures/private_sync/auth_*.json` 8 个，`decideAuthorization(...).name == expected` |
| 02 | S02 | `account_binding_cert_hash_matches_fixture` | `accountBindingCertHash` 对 `auth_valid.json` 三字段 == `c2d5f307efbc443185626250f07131b798736e02c7732b1dc417171d30c30504` |
| 02 | S03 | `pairing_gate_and_relay_config_match_fixtures` | `pairingGate(isAnonymous: true) == 'pairing_refused_anonymous'`（`pairing_anonymous.json`）；三个中转常量等于 `relay_ttl.json` 字段；`deletion_layers.json` 可解析且 `expected == 'layers_ok'` |
| 02 | S04 | `apply_remote_revision_creates_note_keeps_branches_and_writes_no_outbox` | 新笔记首条远端修订建笔记；两条同父远端修订 → 两个头，preferred 为先到者；outbox 行数不变；再次应用同修订 → `duplicate` |
| 02 | S05 | `apply_remote_revision_rejects_missing_parent_and_is_atomic` | 父缺失 → `RemoteParentMissing` 且三表行数不变；`FailingInterceptor`（local-persistence §5.2 写法）在 `note_heads` 插入失败 → `SaveFailed` 且回滚 |
| 02 | S06 | `mark_envelope_allows_only_forward_transitions` | pending→sent→acked 成功；acked→sent、pending→acked 抛 `StateError` |
| 03 | S07 | `sealed_envelope_bytes_contain_no_plaintext_title_or_body` | §7 |
| 03 | S08 | `wrap_and_chunk_match_python_reference_vectors` | §9 全部参考值逐字相等 |
| 03 | S09 | `seal_receive_roundtrip_accepts_with_real_keys` | 两个仓库（发送、接收），真实 Ed25519 设备密钥与 X25519 会话；`receive` → `accept`；接收端修订 13 字段与发送端相等 |
| 03 | S10 | `signed_fields_match_fixture_and_tampered_content_hash_is_bad_signature` | `signedFieldNames` 等于 `envelope_valid.json` 的 `signed_fields`；改 `contentHash` 一位 → `reject:bad_signature` |
| 03 | S11 | `recipient_mismatch_is_aad_mismatch` | 发给 `dev_b` 的信封由 `dev_c`（同样受信、签名有效、同一会话）接收 → `reject:aad_mismatch` |
| 03 | S12 | `stored_wrong_content_hash_is_hash_mismatch` | 测试经 Drift API 把发送端修订的 `content_hash` 改为 64 个 `f` 再 `seal` → `reject:hash_mismatch` |
| 03 | S13 | `replay_same_revision_is_duplicate_ack_without_write` | 同信封第二次 `receive` → `duplicate_ack`，三表行数不变 |
| 03 | S14 | `oversize_inline_payload_is_schema_invalid` | 正文使明文 > 262144 字节 → `reject:schema_invalid`（第 0 步，未调用 verifier） |
| 03 | S15 | `untrusted_expired_or_revoked_sender_is_source_untrusted` | 目录无记录、`revoked`、`nowUtcMs == expiresAtUtcMs`、`keyEpoch 2` 各 → `reject:source_untrusted` |
| 03 | S16 | `session_pub_bad_signature_is_session_key_unbound_before_sealing` | `sessionPubSig` 改一位 → `seal` 抛 `SessionKeyUnbound`，`randomBytes` 未被调用 |
| 03 | S17 | `concurrent_branches_from_two_devices_are_kept_as_heads` | 设备 A、B 从同一修订各自保存后分别发往 C → C 两次 `accept`，C 的 `headIds` 恰 2 个，无修订被覆盖 |

计数：act/02 后 `flutter test` `+259`；act/03 后 `+270: All tests passed!`；`flutter analyze` 0。

## 9. 参考值（主 Agent 2026-09-12 以 Python `cryptography`（pyca）与 functions-py `community_hash` 计算）

输入：`app_user_id = usr_test_account_001`；`sender = dev_sender_001`；`recipient = dev_recipient_002`；`seq = 1`；`op = revision_saved`；`created_at = 1760000000000`；`note_id = note_0123456789abcdef0123456789abcdef`（`kind = note`，`created_at = 2026-09-12T00:00:00.000Z`）；`revision_id = nrev_0123456789abcdef0123456789abcdef`，修订 = `fixtures/community/content_hash_cases.json` 第一例 `C01_base` 的 `snapshot` 六字段 + `parent_ids = []`、`restored_from = null`、`created_at = 2026-09-12T00:00:00.000Z`、`created_on_device = dev_sender_001`、`content_hash = 8c883808e4347144b7a0c86e86cc3f6d1bc594f5f10cbc251bf1e61758f09cba`；发送端 Ed25519 种子 32 个 `0x77`；接收端 Ed25519 种子 32 个 `0x66`；`ephSeed` 32 个 `0x11`；会话 X25519 种子 32 个 `0x22`；`nonceW` 16 个 `0x33`；`dek` 32 个 `0x44`；`seed` 16 个 `0x55`；`session_id = sess_0001`。

| 名称 | 值 |
|---|---|
| signed digest `SHA256(E(signed))` | `dafcb7e08e8ffe64bf871fe7c3ba3dee3ea088a4c0fe57a9566dd737d51495c3` |
| 发送端 Ed25519 公钥 | `c853ad0f0cd2b619aea92ceec4fd56a24d6499d584ce79257e45cfd8139b60a7` |
| 信封签名 | `e639de16df1b7ffe67b66fb085c9a6c8ccb4ba45936a341df3e1dd21c2e0dc59b02ac7e26687d236f0abfab413c10ec3b91e0672498672336b642e7ae9e78e0b` |
| `eph_pub` | `7b4e909bbe7ffe44c465a220037d608ee35897d31ef972f07f74892cb0f73f13` |
| `session_pub` | `0faa684ed28867b97f4a6a2dee5df8ce974e76b7018e3f22a1c4cf2678570f20` |
| X25519 shared | `9e004098efc091d4ec2663b4e9f5cfd4d7064571690b4bea97ab146ab9f35056` |
| `wrap_key` | `4da4b1c9ae776786e05f9d34c8ee9147feb2a49a3634905a9aef7f449ffbddf2` |
| `wrapped_dek`（48 B） | `75fcbd72b9d90228c842a0598477dbf7a5a8d7d290b93210925fd323abc6f7415eed0d18cd17a2126b8b59f184fbf90d` |
| 明文 payload | 1919 B，SHA-256 `b8006c35e983f50fccf8f3910ef36d806649712404b41228a41ad7fdd2a367c7` |
| `nonce_0` | `0e51b2e763b667f6a87f1abc` |
| 第 0 块（单块，末块，1935 B） | SHA-256 `e776bae8f2f03865f2d31553e540d36323318e9796ca12edaec6d7f552335424` |
| 接收端 Ed25519 公钥 | `34b4d9043156cb6dcf0beb0a2949b7559c940d2bcb6dbe8c53a9b30278e3a746` |
| `session_pub_sig`（接收端签） | `9ff25742fe708b81a6cb2dbf94885c85c5d1e6be84b23856f299e7f39a3868256dc911a8200378f694ce548859075adf390c351e742d10b6f2ecd31032f31103` |
| 证书哈希（`auth_valid.json`） | `c2d5f307efbc443185626250f07131b798736e02c7732b1dc417171d30c30504` |

payload JSON 规范化同 private_export §3.1（等价 Python `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)`）。Dart 的 `X25519().newKeyPairFromSeed`、`Ed25519().newKeyPairFromSeed` 以 32 字节种子得到与 pyca `from_private_bytes` 相同的密钥；若实测不等，按停手协议上报，不得改参考值。

## 10. 决定登记（NC-016a，主 Agent 裁定，可推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC016-01 | NC-016 拆为 16a（本文，进程内）与 16b（两台真实设备 LAN/WebRTC 集成、中转上传、宿主装配，`BLOCKED` 等 NC-001 设备表） | INTEGRATION_BASELINE 第 59 行两台设备未盘点；不以模拟冒充真实设备证据 |
| D-NC016-02 | reading-notes 不依赖 xuan-storage 包，经端口注入签名、验签与可信目录 | xuan-storage core 依赖局域网 gitea 的 git 包；D-NC010-02 纯包原则 |
| D-NC016-03 | STORAGE 补丁只加带缺省值的参数，在 `fix/nc016-guard-aad` worktree 提交、不合并 | xuan-storage AGENTS.md 禁止 main 改动；非破坏性改动不影响既有调用方与既有密文 |
| D-NC016-04 | CLIENT `decideAuthorization` 与 STORAGE guard 同为 8 步，两侧都以同一组 8 个样例验证 | 宿主可能接任一侧；样例是两侧一致性的唯一判据 |
| D-NC016-05 | 块级 AAD = D-NC015-05 的 AAD ‖ 块号（4 B 大端）‖ 末块标记；包装 DEK 的 GCM nonce 取 `nonce_w` 前 12 字节，HKDF salt 用完整 16 字节 | 防块换序、截断、追加（同 D-NC017-04）；GCM 标准 nonce 为 12 字节，跨实现无歧义 |
| D-NC016-06 | 线上 `op` 用 OutboxOp 数据库值，16a 只同步 `revision_saved`、`heads_merged`；`note_trashed/restored/purged` 归 NC-019 | 生命周期与 tombstone 窗口属 NC-019；NC-015 样例中的 `op: "upsert"` 为格式级占位 |
| D-NC016-07 | 接收第 0 步做结构校验（含内联 > 262144 字节），先于来源、签名与解密 | 畸形或超大信封不应消耗密码学运算；与样例 `envelope_oversize_inline → reject:schema_invalid` 一致 |
| D-NC016-08 | 信封 `created_at` 为 UTC 毫秒整数；16a 恒内联，JSON 中 payload 为 base64 | 与 NC-015 样例类型一致；中转对象引用归 16b |
| D-NC016-09 | 明文 payload 携带笔记 `id/kind/created_at`，不同步 `lifecycle`、`pending_op` | 接收端首次收到某笔记时需要建行；生命周期同步归 NC-019 |
| D-NC016-10 | `applyRemoteRevision` 保留分支、只在父含当前 preferred 时前移、不写 outbox；父缺失拒收 | 双方分支保留（TASKS）；不回声；发送端按 outbox 顺序重发补齐 |
| D-NC016-11 | 信封层来源可信 = 目录记录存在、scope 与设备 ID 相符、active、未过期、epoch 1；DTLS 与指纹属会话层 guard | 信封本身不携带指纹与 DTLS 观测值 |
| D-NC016-12 | 新测试一律用真实 Ed25519/X25519 密钥；覆盖 NC-015 验收交接的匿名拦截、AAD 失败、会话公钥签名 | NC-015 ACCEPTANCE 4b |
| D-NC016-13 | 参考值由 pyca 计算、测试用字面量 | 跨实现核对；16b 宿主若另写实现须通过同一组值 |
