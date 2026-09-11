# NC-004 验证计划

工作目录：`/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（act/01 创建）。`export PATH=/Users/jingtaiwei/flutter/bin:$PATH`。判据只来自 `contracts/local-persistence.md`（下称契约）。

## 1. 命令

| # | 命令（在 reading-notes 根） | 期望 | 自哪一步起 |
|---|---|---|---|
| 1 | `flutter pub get` | 退出 0；`pubspec.lock` 中契约 §1 列出的 9 个包版本与契约逐字相同 | act/01 |
| 2 | `flutter analyze` | 退出 0，`No issues found!` | act/01 |
| 3 | `flutter test test/contracts/content_hash_parity_test.dart` | 退出 0，`+8: All tests passed!` | act/01 |
| 4 | `dart run build_runner build --delete-conflicting-outputs` | 退出 0；生成 `lib/src/persistence/note_database.g.dart` 并提交 | act/02 |
| 5 | `flutter test test/persistence/note_database_test.dart` | 退出 0，`+4` | act/02 |
| 6 | `flutter test test/persistence/note_repository_test.dart` | 退出 0；act/03 `+12`，act/04 `+18` | act/03 |
| 7 | `flutter test` | 退出 0；act/04 后 `+30: All tests passed!`（8+4+18） | 每步 |
| 8 | `cmp test/fixtures/community_content_hash_cases.json /Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/fixtures/community/content_hash_cases.json` | 退出 0 | act/01 |
| 9 | `git -C /Users/jingtaiwei/Git/Public/xuan-migration/reading-notes status --short` | 提交后为空 | 每步 |
| 10 | `cd /Users/jingtaiwei/Git/Public/learn_system && bash docs/blackbox-spec-rework/reviews/nc004_guard.sh --require-impl` | 退出 0 | act/04 之后 |

## 2. act/01：建仓、nchash Dart、一致性测试

文件：`pubspec.yaml`、`analysis_options.yaml`、`.gitignore`（Flutter 包模板，去掉 `pubspec.lock` 行）、`README.md`（一句话 + 契约链接）、`lib/reading_notes.dart`、`lib/src/domain/nchash.dart`、`test/fixtures/community_content_hash_cases.json`（`cp` 原件）、`test/contracts/content_hash_parity_test.dart`。

`pubspec.yaml` 精确内容要点：`name: reading_notes`；`publish_to: none`；`environment: sdk: ^3.12.2`；`dependencies: flutter: {sdk: flutter}, crypto: 3.0.7, drift: 2.31.0, drift_flutter: 0.2.8, sqlite3: 2.9.4, sqlite3_flutter_libs: 0.5.42, path_provider: 2.1.6`；`dev_dependencies: flutter_test: {sdk: flutter}, drift_dev: 2.31.0, build_runner: 2.15.1, flutter_lints: 6.0.0`。

`nchash.dart` 公开 API 见契约 §6。测试文件 8 个 `test()`（名称逐字）：

| 测试名 | 断言 |
|---|---|
| `domain constant` | `utf8.encode(domain)` 等于 `nchash/v2\n` 的字节 |
| `encoding vectors` | 16 向量：`hex(encode(value)) == expected_bytes_hex` |
| `cases canonical and hash` | 18 case：`snapshot` 非 null 时 `hex(canonicalBytes) == expected_canonical_hex` 且 `contentHash == expected_hash`；`snapshot` null 时先 `projectRevision(revision)` |
| `equal hash pairs` | 所有 `equal_hash_to` 非 null 的 case，两者 hash 相等 |
| `unequal vs base` | C06～C11 六例各不等于 C01 |
| `invalid snapshots throw` | 7 例：`contentHash` 抛 `SnapshotValidationError` 或 `CanonicalEncodingError` |
| `invalid json texts throw at parse layer` | 3 例：`loadSnapshotJson(text)` 抛 `SnapshotValidationError`，且 `jsonDecode(text)` **不抛**（J03 的 `NaN` 在 Dart `jsonDecode` 下会抛 FormatException——对 J03 只断言 `loadSnapshotJson` 抛，不断言 `jsonDecode` 不抛；对 J01/J02 两者都断言） |
| `no json encode in implementation` | 读取 `lib/src/domain/nchash.dart` 源码，不含 `jsonEncode`、`json.encode`、`JsonEncoder` |

Red：`nchash.dart` 先只定义 `domain` 常量与抛 `UnimplementedError` 的函数，运行命令 3 得到失败原文。

## 3. act/02：模型、错误、常量、Drift 库

文件：`lib/src/domain/{models.dart,limits.dart,errors.dart,editor_snapshot.dart,ids.dart,clock.dart}`、`lib/src/persistence/{note_database.dart,note_database.g.dart,tables.dart}`、`test/persistence/note_database_test.dart`、`test/support/temp_db.dart`（打开临时目录真文件库的辅助）。

`NoteDatabase`（契约 §2）：`NoteDatabase(QueryExecutor executor)`；`static Future<NoteDatabase> openScoped({required Directory dir, required String scopeUid})` 打开 `reading_notes_<scopeUid>.sqlite`；`int get activeGeneration`（初值 1）；`Future<void> retireSession()`（`activeGeneration += 1` 后 `close()`）；`schemaVersion => 1`；`beforeOpen` 执行 `PRAGMA foreign_keys = ON`；`onUpgrade` 抛 `UnsupportedError`。

测试 4 个：

| 测试名 | 断言 |
|---|---|
| `opens real file and creates tables` | 打开后 `sqlite_master` 含 4 表 3 索引；文件存在于临时目录 |
| `foreign keys are enabled` | `PRAGMA foreign_keys` 返回 1；向 `note_heads` 插入不存在的 note_id 抛异常 |
| `reopen keeps schema version 1` | 关闭重开，`PRAGMA user_version` = 1，无 onUpgrade |
| `retireSession bumps generation and closes` | `activeGeneration` 1→2；随后 `customSelect` 抛（已关闭） |

Red：先写测试与只含空 `@DriftDatabase(tables: [])` 的类，运行命令 5 取得失败原文，再写表与生成。

## 4. act/03：仓储保存规则（契约 §5.1 第 1～6 条）

文件：`lib/src/persistence/note_repository.dart`、`lib/src/persistence/outbox.dart`（`OutboxEnvelope` 模型与 op/state 枚举）、`test/persistence/note_repository_test.dart`（本步 11 个测试）。

| 测试名 | 断言（对应 BDD） |
|---|---|
| `createNote writes root revision head and outbox` | B06 四表行数 1/1/1/1；parent_ids `[]`；outbox op=revision_saved、state=pending、payload_cipher_ref null、key_epoch null |
| `same snapshot save is unchanged` | B07 |
| `two edits chain revisions` | B08：三修订、parent 链、head 唯一 |
| `attachment and mention refs roundtrip` | B09：重开库后解析回相等；顺序为规范顺序 |
| `markdown exactly 1MiB saves` | B10 |
| `markdown 1MiB plus one throws and writes nothing` | B11 |
| `21 attachments throws` | B12 前半 |
| `duplicate mention throws` | B12 后半 |
| `summary touched rule 1 revert text unchanged` | B13 |
| `summary touched rule 2 only summary saves` | B14 |
| `summary touched rule 3 text change summary empty` | B15 |

另加 `head conflict throws`（B16）。本步固定 **12** 个测试（上表 11 + `head conflict throws`）；命令 6 在 act/03 后期望 `+12`。

Red：先写 12 个测试与只抛 `UnimplementedError` 的仓储，运行命令 6 取得失败原文。

## 5. act/04：恢复/合并、回滚、重开、会话隔离、outbox

追加到 `note_repository_test.dart` 6 个测试（合计 18 = 12 + 6）；新增 `test/support/failing_executor.dart`。

| 测试名 | 断言 |
|---|---|
| `restore same content creates new revision` | B20：`restored_from` 正确、hash 相等、parent_ids=[当前头] |
| `merge two heads` | B21：先用两个不同 expectedHeadId 各保存一次得到两个头（第二次保存前直接向 `note_heads` 插入第二头模拟同步到达），合并后 heads 只剩新修订，outbox 增 `heads_merged` |
| `disk failure rolls back whole save` | B17：`FailingExecutor(failOnStatementContaining: 'outbox_envelopes')`；抛 `SaveFailed`；三表行数与 `preferred_head_id` 不变 |
| `close and reopen keeps everything` | B18 |
| `stale session is rejected` | B19：`retireSession()` 后 `saveSnapshot`/`createNote` 抛 `StaleSessionError`，无新行（用新连接读） |
| `pending envelopes ordered and content free` | B22：seq 升序；每行字段集合恰为契约 §4 十列；无 `title`/`markdown` 键 |

Red：先写 6 个测试（仓储方法 `restoreRevision`/`mergeHeads` 先抛 `UnimplementedError`），运行命令 6 取得失败原文。

## 6. Red→Green 与禁止

- 每步先测试后实现；报告贴出 Red 原文（至少一条真实断言失败或 `UnimplementedError`）。
- 禁止：`skip`、`expect(true, isTrue)` 类永真、从被测输出生成期望、`NativeDatabase.memory()` 用于 B05/B09/B18、修改 fixture 副本、放宽版本锁。
- 命令 7 最终 `+30`（8 + 4 + 18）。
