# 私人导出契约：口令加密导出文件格式与本机原子写入（NC-017）

状态：`FROZEN_FOR_NC-017`（2026-09-12）。权威来源：[TASKS](../TASKS.md) NC-017；[PRD](../PRD.md) R-13、旅程 7；[DESIGN](../DESIGN.md) 第 50 行 BackupManifest、§5 设备同步与导出（S6，D13）、§7.4 导出文件写入；[community-models](community-models.md) §0.1（`bkm_`）与 AttachmentRef（`content_digest` = 加密前明文 SHA-256）；[local-persistence](local-persistence.md)（Notes / NoteRevisions 表）；[private_sync](private_sync.md) D-NC015-02（scopeUid 不出设备）。本文把格式、密码参数、写入流程、错误语义与测试判据写死，执行者照抄；与上游冲突以上游为准并停手上报。

S6 前提：没有长期密钥、没有云端备份、没有恢复材料。口令派生的密钥只用于这一个文件，不保存、不上传；忘记口令则文件无法打开，这是产品明示的设计，不是缺陷。

## 1. 仓库与基线

| 项 | 实值 |
|---|---|
| 仓库 | `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（独立 git；分支 `main`） |
| 基线 | NC-011 CLIENT 线 act/06 提交之后（`flutter test` `+239`、`flutter analyze` 0）；NC-011 CLIENT 线未完成前不得开工（同一工作树，D-NC017-11） |
| 新依赖 | `cryptography: 2.9.0`（精确锁定；2026-09-12 在副本上 `flutter pub get --offline` 实测：`pubspec.lock` 只新增 `cryptography 2.9.0` 一项，无其他包变化） |
| 不依赖 | 服务端、OpenAPI、BlobGateway、`xuan-storage`（只复用其 AES-GCM 分块 nonce 规则，不引入包依赖） |

## 2. 写入白名单

| 文件 | 内容 |
|---|---|
| `pubspec.yaml` | `dependencies` 在 `http: 1.6.0` 行之后追加 `  cryptography: 2.9.0` 一行 |
| `pubspec.lock` | 仅由 `flutter pub get --offline` 生成的 cryptography 一段 |
| `lib/src/export/export_bundle_format.dart` | §3～§5：常量、规范 JSON、清单、记录流、分块加解密、读取 |
| `lib/src/export/export_writer.dart` | §6：附件端口、写入器、原子写入 |
| `lib/reading_notes.dart` | 追加两行导出 |
| `test/export/export_bundle_test.dart` | §8 |

禁止：其他任何文件（含 NC-004～NC-011 全部 lib 与 test）；修改 `note_database.dart` 或表；除 cryptography 外的新依赖；真实网络；`skip`；永真断言；在测试内调用被测函数生成参考值；先实现后补测试。

## 3. 容器格式

文件字节依次为：

```
magic         8 B   ASCII "RNEXPORT"
header_len    4 B   无符号大端整数
header        header_len B   UTF-8 规范 JSON（§3.2），明文
chunk*        每块：chunk_len（4 B 无符号大端）‖ chunk（chunk_len B）
```

- 至少 1 块；最后一块即末块（§4.3 AAD 末块标记为 1，其余为 0）。
- 文件扩展名建议 `.rnexport`（写入器不强制）。

### 3.1 规范 JSON（`canonicalJson`）

对象键按 Unicode 码点升序（逐个比较 `String.runes`，与 community_client §10.1 同规则），分隔符为 `,` 与 `:`，无空白；字符串用 `jsonEncode` 转义（非 ASCII 原样输出）；数值只允许整数；`null`、`true`、`false` 原样。等价于 Python `json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`。

### 3.2 清单（BackupManifest，明文头）

未签名清单 `H` 的键恰为：

| 键 | 值 |
|---|---|
| `format` | `"reading-notes-export"` |
| `protocol_version` | `1` |
| `backup_id` | `"bkm_" + 32 hex`（`IdGenerator.newId('bkm_')`） |
| `scope` | `"account_notes"`（恒定；**不写** scopeUid、owner_scope、账号或设备标识，D-NC017-03） |
| `created_at` | `Clock` 输出（`YYYY-MM-DDTHH:MM:SS.mmmZ`） |
| `note_count`、`revision_count`、`attachment_count` | 本文件包含的条数（整数） |
| `kdf` | `{"name": "argon2id", "memory_kib": 65536, "iterations": 3, "parallelism": 1, "key_length": 32, "salt_hex": <32 位小写 hex>}` |
| `cipher` | `{"name": "aes-256-gcm", "chunk_plain_bytes": 1048576, "nonce_rule": "aes_gcm_blob_cipher_v1"}` |

`digest = SHA-256_hex(canonicalJson(H))`；头部字节 = `canonicalJson(H ∪ {"digest": digest})`。

读取时清单校验失败的全部情形 → `ExportFormatError`：magic 不符；`header_len` 超出文件长度；头部不是 UTF-8 JSON 对象；键集合不等于上表加 `digest`；`format`/`protocol_version`/`scope`/`kdf` 除 `salt_hex` 外各值/`cipher` 各值与上表不逐字相等；`salt_hex` 不匹配 `^[0-9a-f]{32}$`；`backup_id` 不匹配 `^bkm_[0-9a-f]{32}$`；三个计数不是非负整数；重算 `digest` 不等。

## 4. 密钥与分块加密

### 4.1 口令派生（D-NC017-01、D-NC017-02）

`key = Argon2id(memory: 65536, iterations: 3, parallelism: 1, hashLength: 32).deriveKey(secretKey: SecretKey(utf8.encode(passphrase)), nonce: salt)`（`package:cryptography`）。口令按输入原样 UTF-8 编码，不做 Unicode 归一化、不去空白；空串拒绝（§6）。`salt` 为每个文件 16 个随机字节。派生出的 32 字节直接作为 AES-256-GCM 密钥，不保存、不写日志。

### 4.2 明文记录流

明文是若干记录的串接：`type（1 B）‖ length（4 B 无符号大端）‖ payload（length B）`。

| type | payload |
|---|---|
| `0x01` 笔记 | `canonicalJson`，键恰为 `id, kind, head_revision_ids, preferred_head_id, lifecycle, created_at, trashed_at, updated_at`（`kind` 为 `note`/`annotation`；`head_revision_ids` 按 UTF-8 字节序升序；不含 `owner_scope`、`pending_op`） |
| `0x02` 修订 | `canonicalJson`，键恰为 `community_note_revision.schema.json` 的 13 个必填字段（`id, note_id, parent_ids, title, markdown, attachment_refs, mentions, bindings, content_hash, change_summary, restored_from, created_at, created_on_device`），嵌套结构的键与 NC-002 Schema 一致（snake_case）。`NoteRevision` 本身没有 `toMap`：按 13 个字段显式映射，`attachment_refs`/`mentions`/`bindings` 各元素调用 `AttachmentRef`/`MentionRef`/`BindingRef` 已有的 `toMap()`（审查 R1 建议 1） |
| `0x03` 附件元数据 | `canonicalJson`，键恰为 `attachment_id, object_version, content_digest, byte_length` |
| `0x04` 附件字节 | 原始字节；紧跟在对应 `0x03` 之后，长度等于其 `byte_length` |
| `0x7F` 结束 | `canonicalJson({"note_count", "revision_count", "attachment_count"})`，恰出现一次且为最后一条 |

顺序：笔记按 `id` UTF-8 字节序升序，每条笔记后紧跟其全部修订（按 `(created_at, id)` 升序）；全部笔记之后是附件（按 `attachment_id` 字节序、再按 `object_version` 升序，每个附件为一对 `0x03`、`0x04`）；最后是 `0x7F`。

### 4.3 分块（D-NC017-04）

- 明文流按 `1048576` 字节切块；末块长度 1～1048576（明文恰为整数倍时末块为满块，不产生空块）。
- 第 `i` 块（从 0 起）：`seed = randomBytes(16)`；`nonce = SHA-256(seed ‖ UTF-8(i 的十进制字符串))[0:12]`（与 `xuan-storage/drift/lib/blob/aes_gcm_blob_cipher.dart` 的 `_deriveNonce` 同规则）；`aad = digest 的 32 字节 ‖ i（4 B 无符号大端）‖ final（1 B，末块 0x01，其余 0x00）`；`box = AesGcm.with256bits(nonceLength: 12).encrypt(plain_i, secretKey: key, nonce: nonce, aad: aad)`；`chunk = nonce ‖ box.cipherText ‖ box.mac.bytes`（tag 16 B）。
- 编码器 `ExportChunkEncoder` 最多缓冲 1 块明文加 1 字节以判定末块：`add` 只在缓冲 > 1048576 字节时输出满块，`close` 输出剩余部分作为末块。

### 4.4 读取与统一失败（D-NC017-05）

`Future<ExportContents> decodeExportFile(Uint8List fileBytes, String passphrase)`：

1. 按 §3.2 解析并校验清单，失败 → `ExportFormatError`。
2. 派生密钥；逐块解析 `chunk_len` 与块（末尾不足 4 字节、`chunk_len` 小于 28 或越界、零块）→ `ExportUndecryptable`。
3. 逐块以 §4.3 的 AAD（最后一块 final=1，其余 0）解密；任一块认证失败 → `ExportUndecryptable`。口令错误、块被篡改、块换序、截断、在末尾追加块，一律只抛同一个 `ExportUndecryptable`（`toString()` 恒为 `ExportUndecryptable`，不携带块号或原因）。
4. **全部块认证通过之后**才解析明文记录流；记录类型未知、长度越界、`0x04` 未紧跟 `0x03`、字节长度不符、结束记录缺失/重复/不在最后、结束记录或实际条数与清单计数不等 → `ExportFormatError`。
5. 返回 `ExportContents{header, notes, revisions, attachments}`；任何异常路径都不返回部分内容。

## 5. `export_bundle_format.dart` 公开接口

```dart
const String exportMagic = 'RNEXPORT';
const int exportProtocolVersion = 1;
const int exportChunkPlainBytes = 1048576;
const int exportArgon2MemoryKib = 65536;
const int exportArgon2Iterations = 3;
const int exportArgon2Parallelism = 1;
const int exportKeyLength = 32;
const int exportSaltLength = 16;
const int exportSeedLength = 16;

class ExportFormatError implements Exception { const ExportFormatError(this.reason); final String reason; }
class ExportUndecryptable implements Exception { const ExportUndecryptable(); @override String toString() => 'ExportUndecryptable'; }

String canonicalJson(Object? value);
Future<List<int>> deriveExportKey(String passphrase, List<int> salt);

class ExportHeader {
  const ExportHeader({required this.backupId, required this.createdAt, required this.noteCount,
      required this.revisionCount, required this.attachmentCount, required this.saltHex});
  final String backupId; final String createdAt; final int noteCount; final int revisionCount;
  final int attachmentCount; final String saltHex;
  Map<String, Object?> unsignedMap();   // §3.2 表 H
  String digestHex();                    // SHA-256_hex(canonicalJson(unsignedMap()))
  Uint8List encode();                    // canonicalJson(H ∪ {digest}) 的 UTF-8
  static ExportHeader decode(Uint8List bytes);  // §3.2 校验，失败抛 ExportFormatError
}

sealed class ExportRecord { const ExportRecord(); }
final class NoteRecord extends ExportRecord { const NoteRecord(this.json); final Map<String, Object?> json; }
final class RevisionRecord extends ExportRecord { const RevisionRecord(this.json); final Map<String, Object?> json; }
final class AttachmentRecord extends ExportRecord { const AttachmentRecord(this.meta, this.bytes); final Map<String, Object?> meta; final Uint8List bytes; }
final class EndRecord extends ExportRecord { const EndRecord(this.noteCount, this.revisionCount, this.attachmentCount); final int noteCount; final int revisionCount; final int attachmentCount; }

Uint8List encodeRecord(ExportRecord record);   // AttachmentRecord 输出 0x03 与 0x04 两条
List<ExportRecord> decodeRecords(Uint8List plain);

class ExportChunkEncoder {
  ExportChunkEncoder({required List<int> key, required List<int> headerDigest, required List<int> Function(int length) randomBytes});
  Future<List<Uint8List>> add(List<int> plain);  // 每个元素为带 4 B 长度前缀的完整块
  Future<Uint8List> close();                      // 末块（带长度前缀）
}

class ExportContents {
  const ExportContents({required this.header, required this.notes, required this.revisions, required this.attachments});
  final ExportHeader header; final List<NoteRecord> notes; final List<RevisionRecord> revisions; final List<AttachmentRecord> attachments;
}
Future<ExportContents> decodeExportFile(Uint8List fileBytes, String passphrase);
```

## 6. `export_writer.dart`

```dart
abstract class AttachmentBytesSource { Future<Uint8List?> read(String attachmentId, int objectVersion); }

class ExportTargetExists implements Exception { const ExportTargetExists(this.path); final String path; }
class ExportEmptyPassphrase implements Exception { const ExportEmptyPassphrase(); }
class ExportAttachmentMissing implements Exception { const ExportAttachmentMissing(this.attachmentId, this.objectVersion); final String attachmentId; final int objectVersion; }
class ExportAttachmentDigestMismatch implements Exception { const ExportAttachmentDigestMismatch(this.attachmentId, this.objectVersion); final String attachmentId; final int objectVersion; }
class ExportWriteVerificationFailed implements Exception { const ExportWriteVerificationFailed(); }

class ExportProgress { const ExportProgress(this.done, this.total); final int done; final int total; }
class ExportResult {
  const ExportResult({required this.path, required this.fileSha256, required this.backupId, required this.createdAt,
      required this.noteCount, required this.revisionCount, required this.attachmentCount});
  final String path; final String fileSha256; final String backupId; final String createdAt;
  final int noteCount; final int revisionCount; final int attachmentCount;
}

class ExportWriter {
  ExportWriter({required NoteRepository repository, required AttachmentBytesSource attachments,
      required Clock clock, required IdGenerator ids, List<int> Function(int length)? randomBytes,
      @visibleForTesting Future<void> Function(String stage)? debugHook});
  Future<ExportResult> write({required String targetPath, required String passphrase, void Function(ExportProgress)? onProgress});
}
```

`randomBytes` 缺省为 `Random.secure()` 逐字节生成。`write` 固定步骤：

1. `passphrase.isEmpty` → `ExportEmptyPassphrase`；`File(targetPath).existsSync()` → `ExportTargetExists`。两者都在任何文件写入之前。
2. 收集（D-NC017-06）：经 `repository.db` 的 Drift API 只读查询该仓库作用域下 `lifecycle ∈ {active, trashed}` 的笔记（不含 `purge_pending`、`purged`），按 `id` 升序；每条笔记的修订取 `repository.listRevisions(noteId)`，头取 `repository.headIds(noteId)`；附件为所含修订 `attachmentRefs` 中去重的 `(attachmentId, objectVersion)`，排序同 §4.2。
3. 生成 `salt = randomBytes(16)`、`backupId = ids.newId('bkm_')`、`createdAt = clock` 当前值，构造 `ExportHeader`，派生密钥。
4. 临时文件 `tmp = '$targetPath.partial'`（若已存在先删除）。依次写 magic、`header_len`、头部、经 `ExportChunkEncoder` 的记录流，写入同时对全部字节做流式 SHA-256。每写完一条笔记及其修订调用 `onProgress(ExportProgress(已完成笔记数, 笔记总数))`。附件在写入其记录时才 `read`：返回 null → 删除 `tmp` 后抛 `ExportAttachmentMissing`；`SHA-256_hex(bytes) != content_digest` → 删除 `tmp` 后抛 `ExportAttachmentDigestMismatch`。
5. `flush` 并关闭后，重新流式读取 `tmp` 计算 SHA-256；与写入时的摘要不等 → 删除 `tmp`，抛 `ExportWriteVerificationFailed`。
6. `File(tmp).rename(targetPath)`，返回 `ExportResult(fileSha256 = 该摘要)`。
7. `debugHook` 调用点逐字为：写完头部后 `'after_header'`；每写出一块后 `'after_chunk:<i>'`；步骤 5 之前 `'before_verify'`；步骤 6 之前 `'before_rename'`。hook 抛出的异常原样上抛且**不删除** `tmp`（模拟进程中断：只留临时文件，D-NC017-07）。

## 7. 参考值（主 Agent 2026-09-12 计算：Argon2id 用 OpenSSL 3.6.3 `openssl kdf ARGON2ID`，AES-GCM 用 Python `cryptography` AESGCM；纯 Dart `cryptography 2.9.0` 的派生结果与 OpenSSL 逐字相等）

输入：口令 `correct horse battery staple 中文口令`；`salt` 为 16 个 `0x01`；第 0 块 `seed` 为 16 个 `0x02`；`backup_id = bkm_00000000000000000000000000000001`；`created_at = 2026-09-12T00:00:00.000Z`；计数 1/1/0；记录为：

- 笔记：`{"id": "note_00000000000000000000000000000001", "kind": "note", "head_revision_ids": ["nrev_00000000000000000000000000000001"], "preferred_head_id": "nrev_00000000000000000000000000000001", "lifecycle": "active", "created_at": "2026-09-12T00:00:00.000Z", "trashed_at": null, "updated_at": "2026-09-12T00:00:00.000Z"}`
- 修订：`{"id": "nrev_00000000000000000000000000000001", "note_id": "note_00000000000000000000000000000001", "parent_ids": [], "title": "标题", "markdown": "正文", "attachment_refs": [], "mentions": [], "bindings": [], "content_hash": <64 个小写 a>, "change_summary": "", "restored_from": null, "created_at": "2026-09-12T00:00:00.000Z", "created_on_device": "device-a"}`
- 结束：`{"note_count": 1, "revision_count": 1, "attachment_count": 0}`

| 名称 | 值 |
|---|---|
| K 派生密钥 | `51b48cd57443dc0a219081bbe73dc6e97a75c474eb2c15d7f557c0044c07d6a3` |
| D 清单摘要 | `2951a806b37bb65622017f6507fd20fae909485d3626963b92f08d136ef5b472` |
| 头部字节（536 B） | `{"attachment_count":0,"backup_id":"bkm_00000000000000000000000000000001","cipher":{"chunk_plain_bytes":1048576,"name":"aes-256-gcm","nonce_rule":"aes_gcm_blob_cipher_v1"},"created_at":"2026-09-12T00:00:00.000Z","digest":"2951a806b37bb65622017f6507fd20fae909485d3626963b92f08d136ef5b472","format":"reading-notes-export","kdf":{"iterations":3,"key_length":32,"memory_kib":65536,"name":"argon2id","parallelism":1,"salt_hex":"01010101010101010101010101010101"},"note_count":1,"protocol_version":1,"revision_count":1,"scope":"account_notes"}` |
| 明文记录流 | 764 B，SHA-256 `61a5be5312ceb845fe7d4cccaff78ddbd74fc480f1584bb2b6ce578dc19d4886` |
| 第 0 块 nonce | `3a65508b4842461f25b17142` |
| 第 0 块（792 B） | SHA-256 `37ccbe5f88cb425abc90f869b7d2c9229d6c63fb6a3b2519ca20c6317b828a98` |
| 整个文件（1344 B） | SHA-256 `85df88a1f217a8d3d6dcf5f8b8c5fd87f89c4b397bbc72a8ec98cb320eb12564` |
| 反例 | 同一块以 final=0 的 AAD 解密 → 认证失败 |

## 8. 测试判据（`test/export/export_bundle_test.dart`，临时目录真实 Drift 文件库，名称逐字）

| ID | 测试 | 关键断言 |
|---|---|---|
| E01 | `argon2id_key_matches_openssl_reference` | `deriveExportKey` 输出等于 K |
| E02 | `header_digest_and_bytes_match_reference` | `digestHex()` 等于 D；`encode()` 的 UTF-8 解码等于 §7 头部字面量 |
| E03 | `single_chunk_file_matches_reference_sha256` | 以 §7 输入经 `ExportHeader`、`encodeRecord`、`ExportChunkEncoder`（randomBytes 固定返回 16 个 0x02）拼出文件：明文 SHA-256、nonce、第 0 块 SHA-256、文件长度 1344 与文件 SHA-256 均等于字面量 |
| E04 | `decode_reference_file_roundtrips_records` | 对 E03 文件 `decodeExportFile` 得 1 笔记 1 修订 0 附件，JSON 与 §7 输入深相等 |
| E05 | `raw_bytes_contain_no_plaintext_title_body_attachment_or_ids` | 写入器导出含标题 `独特标题XYZ`、正文 `独特正文片段ABCDEFGHIJ`、附件字节 `ATTACHMENT-PLAINTEXT-MARKER` 的笔记；文件原始字节中不含这三者的 UTF-8 子序列，也不含该笔记 `note_` ID 与仓库 ownerScope |
| E06 | `wrong_passphrase_tamper_reorder_truncate_append_raise_same_undecryptable` | 错口令、改块内 1 字节、交换两块、删末块、追加一块（用 3 块文件），五种都抛 `ExportUndecryptable` 且 `toString()` 相同，无返回值 |
| E07 | `tampered_header_or_changed_kdf_params_raise_format_error` | 改 `created_at` 不改 digest、`memory_kib` 改 19456 并重算 digest、magic 改 1 字节 → 均 `ExportFormatError` |
| E08 | `chunk_boundary_exact_multiple_and_plus_one` | 明文 2 MiB 恰好 → 2 块；2 MiB + 1 字节 → 3 块；两者解密往返逐字节相等 |
| E09 | `writer_exports_active_and_trashed_with_full_revision_chain_excluding_pending_op` | 仓库含 active（3 个修订：含 `restored_from`、非空 `change_summary`、两父合并）、trashed、purge_pending 三条笔记，`pending_op` 设为 `withdraw_requested`；导出后解码得 2 条笔记、全部修订 13 字段与仓库一致；任何记录无 `pending_op`、`owner_scope` 键 |
| E10 | `writer_crash_leaves_only_partial_file` | `debugHook` 在 `after_chunk:0` 抛异常 → 异常上抛；目标文件不存在，`.partial` 存在 |
| E11 | `writer_verification_failure_deletes_partial` | `debugHook` 在 `before_verify` 翻转 `.partial` 一个字节 → `ExportWriteVerificationFailed`；目标与 `.partial` 均不存在 |
| E12 | `writer_rejects_existing_target_empty_passphrase_missing_or_mismatched_attachment` | 四种情形各抛对应异常；目标不被创建或覆盖；附件两种情形 `.partial` 已删除 |
| E13 | `writer_reports_progress_and_result_sha256` | 2 条笔记 → `onProgress` 依次 `(1,2)`、`(2,2)`；`fileSha256` 等于测试对落盘文件重算的 SHA-256；计数与清单一致 |
| E14 | `passphrase_is_utf8_without_normalization` | 以 `"café"` 导出，用 `"café"` 解码 → `ExportUndecryptable`；原口令解码成功 |

计数：`flutter test test/export/export_bundle_test.dart` `+14`；全量 `+253: All tests passed!`；`flutter analyze` 0。

## 9. 决定登记（NC-017，主 Agent 裁定，可推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC017-01 | KDF 为 Argon2id（m=65536 KiB、t=3、p=1、32 B），每文件 16 B 随机盐 | RFC 9106 推荐参数之一；桌面 Dart VM 实测 358 ms，PBKDF2-600000 为 1863 ms；Dart 结果与 OpenSSL 3.6.3 逐字相等 |
| D-NC017-02 | 口令 UTF-8 原样、不归一化；只拒绝空串，强度策略归 NC-018 | 与 DESIGN §7.2 字符串不归一化一致；UI 负责二次输入与提示 |
| D-NC017-03 | 明文头不含 scopeUid、账号、设备、笔记 ID 或标题 | D-NC015-02 scopeUid 不出设备；R-20 导出文件离开设备后不得泄漏 |
| D-NC017-04 | AAD 绑定清单摘要、块号与末块标记；nonce 复用 AesGcmBlobCipher 规则但不依赖 xuan-storage | 防头部篡改、块换序、截断与追加；reading-notes 不引入存储包 |
| D-NC017-05 | 全部块认证通过后才解析；口令错误与密文损坏统一为 `ExportUndecryptable` | TASKS「无部分解密、无错位提示」 |
| D-NC017-06 | 导出 active 与 trashed 笔记的全部修订与附件；不含 purge_pending/purged、pending_op、owner_scope、同步状态 | TASKS「选定 scope 的全部 Note/NoteRevision…不含 pending_op 与同步状态」；已请求彻底删除的内容不应借导出复活 |
| D-NC017-07 | `.partial` 写完后重读校验 SHA-256 再原子改名；目标已存在即拒绝 | DESIGN §7.4；不覆盖用户已有文件 |
| D-NC017-08 | 附件字节经注入的 `AttachmentBytesSource` 读取，并按 `content_digest` 校验 | reading-notes 无附件字节存储（NC-008/NC-025 未交付）；损坏附件不得静默进入导出 |
| D-NC017-09 | 本任务的读取为整文件内存解码，流式导入归 NC-018 | TASKS NC-017 只要求格式与写入；读取用于往返验证 |
| D-NC017-10 | 新增依赖 `cryptography 2.9.0`，NC-016 沿用同一版本 | 离线解析实测只新增该包 |
| D-NC017-11 | 在 NC-011 CLIENT 线完成后开工，不与其并行 | 同一工作树只允许一个执行者写 |
