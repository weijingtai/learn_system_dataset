# 本地持久化契约：CLIENT 包、Drift 修订库、事务保存与 outbox 外层信封（NC-004）

状态：`FROZEN_FOR_NC-004`（2026-09-11）。权威来源：[DESIGN](../DESIGN.md) §3、§3.1、§3.2、§4.4（回收站 T0）、§5、§7.1、§7.2；[TASKS](../TASKS.md) NC-004；[community-models](community-models.md) §1、§5、§6；[state-machines](state-machines.md) SM-1/SM-3/SM-5；[INTEGRATION_BASELINE](../INTEGRATION_BASELINE.md)。本文只把已定设计落到包结构、表结构与接口签名，供执行者照抄；与 DESIGN 冲突以 DESIGN 为准并回报主 Agent。

## 1. 包与工程基线

| 项 | 冻结值 |
|---|---|
| 路径 | `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（NC-001 冻结；父目录不是 Git 仓库） |
| 版本控制 | 独立 Git 仓库：在该目录内 `git init`（默认分支 `main`），不在父目录提交；远端由用户以后指定 |
| 包名 | `reading_notes`；`environment: sdk: ^3.12.2`；Flutter 3.44.6 / Dart 3.12.2（`/Users/jingtaiwei/flutter/bin/cache/flutter.version.json`） |
| 依赖（精确锁定，`pubspec.yaml` 写 `x.y.z` 不带 `^`） | `crypto: 3.0.7`、`drift: 2.31.0`、`drift_flutter: 0.2.8`、`sqlite3: 2.9.4`、`sqlite3_flutter_libs: 0.5.42`、`path_provider: 2.1.6`；dev：`drift_dev: 2.31.0`、`build_runner: 2.15.1`、`flutter_test: sdk: flutter`、`flutter_lints: 6.0.0`（模板约束 `^6.0.0` 的 pub-cache 现有版本，精确锁定；仅 lint，不进产品）；**不**引入 `flutter_markdown_plus`（NC-005）、`persistence_drift`/`persistence_core`（宿主整包，基线明令不依赖） |
| 顶层导出 | `lib/reading_notes.dart` 导出 `src/domain/*.dart`、`src/persistence/note_database.dart`、`src/persistence/note_repository.dart`、`src/domain/nchash.dart` |
| 目录 | `lib/src/domain/`（模型、错误、nchash）、`lib/src/persistence/`（Drift 表、库、仓储、outbox）、`test/contracts/`（跨端一致性）、`test/persistence/`、`test/fixtures/`（NC-002 fixture 字节副本） |
| 代码生成 | Drift 生成文件 `lib/src/persistence/note_database.g.dart` **提交进仓库**（与 `persistence_drift` 提交 `.g.dart` 的做法一致，决定 D-NC004-02）；生成命令 `dart run build_runner build --delete-conflicting-outputs` |
| 分析 | `analysis_options.yaml`：`include: package:flutter_lints/flutter.yaml`；`flutter analyze` 零 issue |
| 忽略 | `.gitignore` 取 Flutter 包模板（`.dart_tool/`、`build/`、`.packages`、`pubspec.lock` 不忽略——包也提交 lock 以固定验收版本，决定 D-NC004-03） |

## 2. 数据库

- 每个账号作用域一个文件：`<dir>/reading_notes_<scopeUid>.sqlite`（决定 D-NC004-04，沿用 `persistence_drift` 的 `<name>_<scopeUid>.sqlite` 惯例）；`<dir>` 由宿主注入（`Future<Directory> Function()`），包内不调用 `path_provider` 以外的路径 API。
- 生产打开方式 `NativeDatabase.createInBackground(File)`；测试用 `NativeDatabase(File)` 打开临时目录中的**真文件**（不用 `NativeDatabase.memory()` 证明持久化）。
- `schemaVersion = 1`；`MigrationStrategy.onCreate` 建全部表与索引；本期无升级路径，`onUpgrade` 抛 `UnsupportedError`（后续任务显式登记迁移步骤）。
- 外键约束开启（`PRAGMA foreign_keys = ON` 于 `beforeOpen`）。

### 2.1 表

| 表 | 列（类型；约束） |
|---|---|
| `notes` | `id TEXT PK`（`note_` ID）；`owner_scope TEXT NOT NULL`；`kind TEXT NOT NULL`（`note`/`annotation`）；`preferred_head_id TEXT NOT NULL`（FK → note_revisions.id）；`lifecycle TEXT NOT NULL DEFAULT 'active'`（SM-3 枚举）；`pending_op TEXT NOT NULL DEFAULT 'none'`（SM-5 枚举）；`created_at TEXT NOT NULL`；`trashed_at TEXT NULL`；`updated_at TEXT NOT NULL` |
| `note_heads` | `note_id TEXT NOT NULL`（FK → notes.id）；`revision_id TEXT NOT NULL`（FK → note_revisions.id）；PK(`note_id`,`revision_id`) |
| `note_revisions` | `id TEXT PK`（`nrev_`）；`note_id TEXT NOT NULL`；`parent_ids_json TEXT NOT NULL`（JSON 数组，根为 `[]`）；`title TEXT NOT NULL`；`markdown TEXT NOT NULL`；`attachment_refs_json TEXT NOT NULL`；`mentions_json TEXT NOT NULL`；`bindings_json TEXT NOT NULL`；`content_hash TEXT NOT NULL`（64 hex）；`change_summary TEXT NOT NULL`；`restored_from TEXT NULL`；`created_at TEXT NOT NULL`；`created_on_device TEXT NOT NULL` |
| `outbox_envelopes` | `seq INTEGER PK AUTOINCREMENT`；`envelope_version INTEGER NOT NULL DEFAULT 1`；`owner_scope TEXT NOT NULL`；`note_id TEXT NOT NULL`；`revision_id TEXT NULL`；`op TEXT NOT NULL`（§4 枚举）；`created_at TEXT NOT NULL`；`state TEXT NOT NULL DEFAULT 'pending'`（`pending`/`sent`/`acked`）；`payload_cipher_ref TEXT NULL`；`key_epoch INTEGER NULL` |

索引：`note_revisions(note_id, created_at)`；`outbox_envelopes(state, seq)`；`notes(owner_scope, lifecycle)`。

JSON 列保存 community-models §1.2 定义的结构（AttachmentRef / MentionRef / BindingRef / AnchorRef / Selector），字段与类型校验在 Dart 模型构造函数中完成（Drift 不校验 JSON 内容）；写入前用 nchash 的规范化结果序列化（数组顺序即规范顺序），保证库内修订与 hash 投影一致。

## 3. 领域模型与错误（`lib/src/domain/`）

- `Note`、`NoteRevision`、`AttachmentRef`、`MentionRef`、`BindingRef`、`AnchorRef`、`Selector`、`SelectorRange`：字段、类型、枚举与 community-models §1 逐字一致；不可变（`final` 字段 + `const` 构造）。
- `EditorSnapshot`（community-models §1.3）：`title, text, selectionBase, selectionExtent, composing, attachmentRefs, mentionRefs, bindings, changeSummary`。`summary_touched` 不属于快照，由调用方作参数传入。
- 常量（`lib/src/domain/limits.dart`）：`noteMarkdownMaxBytes = 1048576`、`attachmentsPerRevisionMax = 20`、`mentionsPerSubmitMax = 50`、`autosaveDebounceMs = 2000`、`undoMergeMaxGapMs = 500`、`undoMergeMaxChars = 20`（community-models §1.3、§5）。
- 本地错误类（D-NC002-10 闭集，全部 `implements Exception`，类名逐字）：`NoteSizeLimitExceeded`、`AttachmentCountExceeded`、`DuplicateReferenceItem`、`IllegalEditorTransition`、`IllegalLifecycleTransition`、`TombstoneRejected`、`TrashRequiresWithdraw`、`PendingOpConflict`；另加 NC-004 新增（决定 D-NC004-05）：`StaleSessionError`（会话代数不符）、`HeadConflictError`（`expectedHeadId` 不是当前头）、`SaveFailed`（包裹底层数据库异常，携带 `cause`）。
- ID 生成：`IdGenerator` 接口 `String newId(String prefix)` → `<prefix><uuid v4 hex 32>`；默认实现用 `dart:math` `Random.secure()` 生成 UUIDv4；测试可注入固定序列。
- 时钟：`Clock` 接口 `String nowUtc()`（RFC 3339 `Z`，毫秒精度 `.fff`）；测试注入。

## 4. outbox 外层信封（决定 D-NC004-01：本期冻结外层，内容由 NC-016 填充）

TASKS NC-004 要求二选一，本文选择「冻结与加密无关的外层 schema」。

| 字段 | 含义 | 由谁填 |
|---|---|---|
| `seq` | 单调递增本地序号，即投递顺序 | NC-004 |
| `envelope_version` | 固定 1 | NC-004 |
| `owner_scope` | 账号作用域 | NC-004 |
| `note_id` / `revision_id` | 事件对象；`note_trashed`/`note_restored`/`note_purged` 时 `revision_id` 为 null | NC-004 |
| `op` | 闭集：`revision_saved`、`note_trashed`、`note_restored`、`note_purged`、`heads_merged` | NC-004 |
| `created_at` | 本地 UTC 时间 | NC-004 |
| `state` | `pending` → `sent` → `acked`；NC-004 只写 `pending`，状态推进归 NC-016 | NC-004 写初值 |
| `payload_cipher_ref` | 密文对象引用；NC-004 恒 null | NC-016 |
| `key_epoch` | 密钥纪元；NC-004 恒 null | NC-015/016 |

信封不含任何明文正文、标题或附件名（DESIGN §1「不复用明文 RecordOutboxMapper 传私人正文」）。NC-016 只允许追加列，不得改既有列含义；tombstone 窗口与 epoch 协议由 NC-015 冻结后写入 `payload_cipher_ref`/`key_epoch` 的语义。

## 5. 仓储接口（`lib/src/persistence/note_repository.dart`）

```dart
class NoteRepository {
  NoteRepository(NoteDatabase db, {
    required String ownerScope,
    required int sessionGeneration,   // 由宿主在每次账号会话启动时递增并传入
    required String deviceId,
    required IdGenerator ids,
    required Clock clock,
  });

  /// 新建笔记：写入根修订（parent_ids=[]）、notes 行、note_heads 行、outbox(revision_saved)。
  Future<Note> createNote({required NoteKind kind, required EditorSnapshot snapshot});

  /// 普通保存。返回 SaveResult(outcome: saved|unchanged)。
  Future<SaveResult> saveSnapshot({
    required String noteId,
    required EditorSnapshot snapshot,
    required bool summaryTouched,
    required String expectedHeadId,   // 调用方当前编辑所基于的头
  });

  /// 显式恢复：即使 hash 与来源相同也新建修订，restored_from=sourceRevisionId，parent_ids=[当前 preferred head]。
  Future<NoteRevision> restoreRevision({required String noteId, required String sourceRevisionId});

  /// 显式合并：parent_ids=headIds（≥2），合并后 note_heads 只剩新修订。写 outbox(heads_merged)。
  Future<NoteRevision> mergeHeads({required String noteId, required List<String> headIds, required EditorSnapshot merged});

  Future<Note?> getNote(String noteId);
  Future<List<String>> headIds(String noteId);
  Future<NoteRevision?> getRevision(String revisionId);
  Future<List<NoteRevision>> listRevisions(String noteId);       // 按 created_at, id 升序
  Future<List<OutboxEnvelope>> pendingEnvelopes({int limit = 100}); // state=pending，按 seq 升序
}

class SaveResult { final String noteId; final String? revisionId; final SaveOutcome outcome; final String contentHash; }
enum SaveOutcome { saved, unchanged }
```

### 5.1 保存规则（逐条，执行者不得自行增删）

1. **会话代数**：每个公开方法开始时比较 `sessionGeneration` 与 `db.activeGeneration`；不等则抛 `StaleSessionError`，不进入事务、不写任何行。宿主切换账号时调用 `db.retireSession()`：`activeGeneration += 1` 并关闭连接（DESIGN §3.2「旧响应不能写入新账号」）。
2. **预校验（事务外，抛错不写行）**：`utf8.encode(snapshot.text).length > noteMarkdownMaxBytes` → `NoteSizeLimitExceeded`；`attachmentRefs.length > attachmentsPerRevisionMax` → `AttachmentCountExceeded`；三类数组任一存在完全相同重复项（按 nchash 编码字节判等）→ `DuplicateReferenceItem`；`mentionRefs.length > mentionsPerSubmitMax` → `DuplicateReferenceItem` 不适用，抛 `ArgumentError`（HTTP 侧才有 400；本地由编辑器阻止，本条只作防御）。调用方保留缓冲、编辑态置 `save_failed`（SM-1）。
3. **头校验**：`expectedHeadId ∉ headIds(noteId)` → `HeadConflictError`。
4. **去重**：`projection = 六字段投影(snapshot)`；`hash = contentHash(projection)`；令 `head = getRevision(expectedHeadId)`。若 `projection 除 change_summary 外 == head 的对应字段` 且 `summaryTouched == false` → 返回 `unchanged`，不写行；否则若 `hash == head.contentHash` 且 `summaryTouched == false` → `unchanged`；其余 → 进入第 5 条（含「仅改说明且 summaryTouched」→ saved）。
5. **事务（`db.transaction`，全部成功或全部回滚）**：① 插入 `note_revisions`（`parent_ids=[expectedHeadId]`，`created_on_device=deviceId`）；② `note_heads` 删除 `expectedHeadId` 行、插入新修订行；③ `notes.preferred_head_id=新修订`，`updated_at=now`；④ 插入 `outbox_envelopes(op=revision_saved, revision_id=新修订, state=pending)`。任一语句异常 → 事务回滚 → 抛 `SaveFailed(cause)`；回滚后 `note_revisions`/`note_heads`/`outbox_envelopes` 行数与事务前相等。
6. **新会话说明初值**：`change_summary` 由调用方传入，编辑器在新会话初始化为空串（不继承 head）；仓储不做继承。
7. **恢复/合并**：不走第 4 条去重；`restoreRevision` 的快照取自来源修订六字段，`change_summary` 置空串。
8. **时间**：`created_at`/`updated_at` 一律 `clock.nowUtc()`；不用设备时间判胜负。

### 5.2 事务原子性的测试注入点

`NoteDatabase` 构造接受 `QueryExecutor`；测试用 `FailingExecutor(inner, failOnStatementContaining: 'outbox_envelopes')` 包装真文件执行器，在第 ④ 步抛 `SqliteException` 模拟磁盘失败，验证第 5 条回滚断言。不得用「先写一半再手工删」模拟。

## 6. nchash/v2 Dart 实现（`lib/src/domain/nchash.dart`）

与 SERVER `xuan/community_hash.py` 对等，独立实现，判据只来自 DESIGN §7.2 与 `test/fixtures/community_content_hash_cases.json`（NC-002 原件的字节副本）：

| 名称 | 契约 |
|---|---|
| `const domain = 'nchash/v2\n'` | UTF-8 字节 |
| `Uint8List encode(Object? value)` | E 编码；整数 `int`（拒绝 `double`、`±(2^53−1)` 外）；字符串按 UTF-8 字节；拒绝孤立 surrogate（`String.runes` 中出现 0xD800–0xDFFF 即拒绝）；对象键按 UTF-8 字节序排序 |
| `Map<String,Object?> normalizeSnapshot(Map<String,Object?>)` | 补默认值、字段全集、三数组规范排序（比较键用 `Uint8List` 逐字节无符号比较，最终平局键为 E 字节）、重复项拒绝 |
| `Uint8List canonicalBytes(Map)`、`String contentHash(Map)` | `sha256(domain 字节 + canonicalBytes)` 小写 hex；Dart 标准库无 SHA-256，用 `package:crypto`（决定 D-NC004-06：`crypto: 3.0.7`，pub-cache 现有，精确锁定，仅用于 SHA-256） |
| `Object? loadSnapshotJson(String text)` | 解析层：先用最小严格扫描器检出重复键、原始 `-0`、`NaN`/`Infinity` 字面量并抛 `SnapshotValidationError`，再 `jsonDecode`（Dart 的 `jsonDecode` 同样会静默合并重复键、把 `-0` 解析为 0） |
| `Map projectRevision(Map revision)` | 只取六个语义键，忽略其余 |
| 异常 | `CanonicalEncodingError`、`SnapshotValidationError`（均 `implements Exception`） |

mention 的 `start_offset`/`length` 与所有长度计量按 code point（`String.runes`），禁止 `String.length`/`substring`。

## 7. 决定登记（NC-004，主 Agent 裁定，可推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC004-01 | outbox 只冻结外层信封（§4），内容由 NC-016 填充 | TASKS NC-004 二选一；解除对 NC-015 的阻塞，密文与 epoch 字段留空 |
| D-NC004-02 | Drift 生成的 `.g.dart` 提交进仓库 | 与 `persistence_drift` 一致；验收者无需先生成即可 `flutter test` |
| D-NC004-03 | 提交 `pubspec.lock` | 固定验收版本；包用作应用内子模块而非发布到 pub |
| D-NC004-04 | 数据库文件 `reading_notes_<scopeUid>.sqlite`，目录由宿主注入 | 沿用宿主每 scope 一文件的隔离方案 |
| D-NC004-05 | 新增本地错误 `StaleSessionError`、`HeadConflictError`、`SaveFailed` | D-NC002-10 闭集未覆盖会话代数、头冲突与底层失败三种情况 |
| D-NC004-06 | 允许依赖 `crypto: 3.0.7`（精确锁定；2026-09-11 核对 pub-cache 现有） | Dart 标准库无 SHA-256；`crypto` 为 dart.dev 官方包 |
| D-NC004-07 | 测试用真文件 `NativeDatabase(File)`，依赖宿主机可加载 `libsqlite3` | TASKS「不只测内存 Fake」；macOS 系统自带 libsqlite3，加载失败即停止上报 |
