# NC-004 可观察行为

「测试」指在 `reading-notes` 根运行 `flutter test <文件>`；「库」指临时目录中的真文件 `reading_notes_<scope>.sqlite`。

| ID | Given | When | Then |
|---|---|---|---|
| B01 | 全新目录 | act/01 完成 | `reading-notes/.git` 存在且 `git -C reading-notes rev-parse --show-toplevel` 等于该目录；父目录仍无 `.git` |
| B02 | `pubspec.yaml` | 读取 | name=`reading_notes`；drift/drift_flutter/sqlite3/sqlite3_flutter_libs/path_provider/crypto/drift_dev/build_runner 均为契约 §1 精确版本且不带 `^`；无 persistence_drift/flutter_markdown_plus |
| B03 | NC-002 fixture 的 44 项 | `test/contracts/content_hash_parity_test.dart` | 16 向量字节相等、18 case 规范字节与 hash 相等（C17 先投影）、等价对相等、6 例不等于 C01、7 非法对象抛 `SnapshotValidationError`/`CanonicalEncodingError`、3 非法 JSON 文本 `loadSnapshotJson` 抛且 `jsonDecode` 不抛 |
| B04 | `test/fixtures/community_content_hash_cases.json` | `cmp` 与 learn_system 原件 | 字节相同 |
| B05 | 打开库 | 关闭再打开同一文件 | 表与索引存在；`PRAGMA foreign_keys`=1；`schemaVersion`=1 |
| B06 | 新建笔记 | `createNote` | `notes` 1 行、`note_revisions` 1 行（parent_ids `[]`）、`note_heads` 1 行、`outbox_envelopes` 1 行（op=revision_saved, state=pending, payload_cipher_ref null） |
| B07 | 同一快照再次保存，summaryTouched=false | `saveSnapshot` | 返回 `unchanged`；四表行数不变 |
| B08 | 改正文两次保存 | 两次 `saveSnapshot` | 三个修订链式 parent，`preferred_head_id` 为最新，`note_heads` 恰 1 行 |
| B09 | 快照含 2 个附件引用与 1 个 mention | 保存后重开库读取 | `attachment_refs_json`/`mentions_json` 解析回对象与输入相等（顺序为 nchash 规范顺序） |
| B10 | 正文 UTF-8 恰 1048576 字节 | 保存 | saved |
| B11 | 正文 1048577 字节 | 保存 | 抛 `NoteSizeLimitExceeded`；四表行数不变（缓冲由调用方保留） |
| B12 | 附件 21 个 / mention 完全重复 | 保存 | 分别抛 `AttachmentCountExceeded` / `DuplicateReferenceItem`；行数不变 |
| B13 | head 说明为 X；新会话改正文再改回原文，summaryTouched=false | 保存 | `unchanged`（summary_touched ①） |
| B14 | 新会话只填写说明 Y，summaryTouched=true | 保存 | `saved` 且新修订 change_summary=Y（②） |
| B15 | 新会话改正文、未碰说明（传入空串） | 保存 | `saved` 且 change_summary 为空串，不继承 X（③） |
| B16 | expectedHeadId 不是当前头 | 保存 | 抛 `HeadConflictError`，行数不变 |
| B17 | 执行器在 `outbox_envelopes` 插入时抛异常 | 保存 | 抛 `SaveFailed`；`note_revisions`/`note_heads`/`outbox_envelopes` 行数与事务前相等，`preferred_head_id` 未变 |
| B18 | 三次保存后关闭库 | 重新打开同文件 | 修订数、头、附件引用、outbox 全部不丢 |
| B19 | 仓储 sessionGeneration=1；库 `retireSession()` 后 | 任一公开方法（含只读） | 抛 `StaleSessionError`，无新行 |
| B20 | 显式恢复到与当前 head 同文的旧修订 | `restoreRevision` | 新修订产生，`restored_from` 指向来源，hash 与来源相同 |
| B21 | 两个头 | `mergeHeads` | 新修订 parent_ids 恰为两头，`note_heads` 只剩新修订，`preferred_head_id` 为新修订，outbox 增 `heads_merged` |
| B22 | 任意写操作后 | `pendingEnvelopes` | 按 seq 升序；每行 op ∈ 闭集；无标题/正文/附件名字段 |
| B23 | `flutter analyze` | 运行 | 0 issue |
| B24 | head 说明为 X；新会话碰过说明框（summaryTouched=true）但最终六字段与 head 全等 | 保存 | `unchanged`（去重规则 ①） |
| B25 | 注入固定 Clock `2026-09-11T00:00:00.000Z` | 保存 | `created_at`/`updated_at` 逐字等于该值，匹配 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$` |
| B26 | 51 个 mention / title 201 code point / change_summary 501 code point | 保存 | 分别抛 `MentionCountExceeded` / `FieldLengthExceeded('title')` / `FieldLengthExceeded('change_summary')`，行数不变 |
| B27 | 快照 title 为字符串 `"NaN"`、markdown 含 `-0 Infinity` 文字 | `loadSnapshotJson` 与 `contentHash` | 解析成功且可计算 hash（字符串内容不受扫描器影响） |
