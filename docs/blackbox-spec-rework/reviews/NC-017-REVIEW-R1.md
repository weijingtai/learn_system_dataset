# NC-017 规格与六件套转译审查报告（R1）

- 审查对象：NC-017 口令加密导出文件格式与本机原子写入
- 审查日期：2026-09-12
- 审查类型：wjt-react 四查（忠实性、覆盖性、可执行性、独立性）
- 审查判定：**`READY`**（四查全部通过，无阻断缺陷，返工 0 项）

---

## 1. 被审材料与基线

| 材料类别 | 文件路径 | 状态 / 版本 |
|---|---|---|
| 契约 | `learn_system/openspec/annotation-community/contracts/private_export.md` | `FROZEN_FOR_NC-017`（2026-09-12） |
| 六件套 | `learn_system/docs/blackbox-spec-rework/work-items/nc-017/` 下 `README.md`、`BDD.md`、`TDD.md`、`ACT.yaml`、`act/01.yaml`、`act/02.yaml`、`ACCEPTANCE.md`、`PROMPT.md` | `READY_FOR_REVIEW` |
| 共享守卫 | `learn_system/docs/blackbox-spec-rework/reviews/nc017_guard.sh` | 本地执行 PASS（0 fails） |
| 需求来源 | `learn_system/openspec/annotation-community/TASKS.md`（NC-017 第 255～260 行、NC-018 第 262～267 行） | v1.6 |
| 产品需求 | `learn_system/openspec/annotation-community/PRD.md`（R-13 第 39/67 行、旅程 7 第 154 行） | v1.6 |
| 技术设计 | `learn_system/openspec/annotation-community/DESIGN.md`（第 50 行 BackupManifest、§5 第 225～227 行、§7.4 第 366 行） | v1.6 |
| 关联契约 | `contracts/private_sync.md`（§1 第 8～9 行、D-NC015-02）、`contracts/community-models.md`（§0.1 前缀表、AttachmentRef） | 已冻结 |

---

## 2. 一查：忠实性（Faithfulness）

### 2.1 TASKS NC-017 逐项追溯

| TASKS.md NC-017 原始条款（行号） | 契约与六件套对应落实位置 | 忠实性核验结论 |
|---|---|---|
| 新增 `CLIENT/lib/src/export/export_bundle_format.dart`、`export_writer.dart`、`test/export/export_bundle_test.dart`（L257） | 契约 §2（L18-25）；act/01 WRITE_NEW（L19-21）；act/02 WRITE_NEW（L19-21）；TDD §2-§3 | **通过**：路径与文件名逐字相符。 |
| 格式：外层 `BackupManifest`（DESIGN §2 字段）明文 JSON（L257） | 契约 §3.2 清单字段定义表 H（L51-61）；ExportHeader 结构体与 decode/encode（L121-130） | **通过**：包含 DESIGN §2 字段并具体化，明文外层 JSON 结构明确。 |
| 口令派生密钥（Argon2id 或 PBKDF2-HMAC-SHA256，参数写死并进契约）（L257） | 契约 §3.2（L59）、§4.1（L68-71）、D-NC017-01；选用 Argon2id（m=65536 KiB, t=3, p=1, key_len=32, salt=16 B） | **通过**：二选一完成裁决，参数全部写死进契约与清单，无未定占位符。 |
| AES-256-GCM 分块密文（复用 `AesGcmBlobCipher` 分块与 nonce 规则，AAD 绑定 manifest digest）（L257） | 契约 §4.3（L86-91）；D-NC017-04；nonce 为 `SHA-256(seed ‖ UTF-8(i))[0:12]`；AAD 为 `digest ‖ i ‖ final` | **通过**：完全复用指定分块与 nonce 规则，AAD 显式绑定清单 digest。 |
| 口令不落盘、不上传（L257） | 契约 §4.1（L70-71）、§5；E05（L218）；D-NC017-01、D-NC017-02 | **通过**：明文口令派生出密钥后即在内存销毁，不写入任何持久层。 |
| 写入原子性（DESIGN §7.4）：临时文件写完并校验摘要后原子改名；中断只留临时文件（L258） | 契约 §6 写入步骤 4～6（L186-189）；D-NC017-07；E10/E11/E12 测试用例 | **通过**：`.partial` 写入 -> 重读校验流式 SHA-256 -> 原子 rename；中断（debugHook）留临时文件。 |
| 导出内容 = 选定 scope 的全部 Note/NoteRevision（含 parent_ids/restored_from/change_summary）与附件对象；不含 pending_op 与同步状态（L258） | 契约 §4.2 记录流（L74-84）、§6 步骤 2（L184）；D-NC017-06；E09（L222） | **通过**：纳入 active/trashed 全部修订 13 必填字段与去重附件，明确排除 purge_pending/purged、pending_op、owner_scope 与同步字段。 |
| 「密文无明文」负向断言：对导出文件原始字节断言不含明文标题/正文片段/附件字节（L259） | 契约 §8 E05（L218）；BDD E05；TDD §2（L20）；ACT E05 | **通过**：在原始文件字节流上直接断言不含明文标题、正文片段、附件标记字节及私有标识。 |
| 错误口令只得到统一失败（无部分解密、无错位提示）（L259） | 契约 §4.4 步骤 3（L98）、§5（L116）、D-NC017-05；E06（L219） | **通过**：错口令、篡改、换序、截断、追加统一抛出无状态的 `ExportUndecryptable`，不返回部分数据。 |
| 不依赖服务端与 BlobGateway；本任务不改 SERVER、不进 OpenAPI。运行 `flutter test test/export/export_bundle_test.dart`（L260） | 契约 §1 表（L14）；README §Scope（L11-12）；ACT.yaml DEFERRED（L14）；TDD §1 命令 3（L11） | **通过**：纯客户端本地包，无服务端/OpenAPI 侵入；以注入的 `AttachmentBytesSource` 解耦对象网关。 |

### 2.2 上游设计与跨契约一致性核查

1. **与 PRD R-13 / 旅程 7 对照**：
   - PRD R-13（L39）与旅程 7（L154）要求：以口令加密写入本机文件、无云端备份、口令不上传不可找回、导出进度 N/M、完成后显示导出时间与文件摘要、可随时再次导出。
   - 契约落实：`ExportWriter.write` 提供 `onProgress(ExportProgress(done, total))` 回调（§6 L177）；返回 `ExportResult` 含 `path`, `fileSha256`, `backupId`, `createdAt`, `noteCount`, `revisionCount`, `attachmentCount`（§6 L166-171）；完全吻合。
2. **与 DESIGN.md 对照**：
   - DESIGN L50 `BackupManifest`: `backup_id, scope, protocol_version, created_at, revision_count, attachment_count, digest`。
   - 契约 §3.2 在此基础上补充 `note_count`（支撑 N/M 进度与笔记实体统计）、`format`（识别容器格式）、`kdf` 与 `cipher`（写死算法套件与参数）。字段属于技术落地的必要具体化，无语义冲突。
   - DESIGN §5 L225-227: S6 模型明确「手动导出：客户端把修订链与附件按 NC-017 格式写成口令加密文件（口令派生密钥仅用于该文件，不保存）」。契约 §4.1 与 D-NC017-01 完全一致。
   - DESIGN §7.4 L366: 「临时文件写完、摘要校验通过后原子改名 \| 中断只留临时文件，不产生半份导出」。契约 §6 步骤 4～6 逐字吻合。
3. **与 contracts/private_sync.md 对照**：
   - `private_sync.md` §1 L8-9 明确导出文件实现归属为 NC-017/018；§2 D-NC015-02 明确 `scopeUid` 仅用于本地 Drift 分区，不出设备。
   - 契约 §3.2 与 D-NC017-03 将导出清单的 `scope` 恒定为 `"account_notes"`，禁止将本地 `scopeUid`、`owner_scope` 或设备 ID 写入导出文件明文头部。完全一致。
4. **与 contracts/community-models.md 对照**：
   - §0.1 前缀表：`BackupManifest` 前缀为 `bkm_`。契约 §3.2 `backup_id` 正则限定为 `^bkm_[0-9a-f]{32}$`。
   - `AttachmentRef`：`attachment_id` 无前缀，`content_digest` 为 64 位小写 hex（明文 SHA-256）。契约 §4.2 记录 0x03 键名及 §6 步骤 4 校验完全匹配。
5. **历史条款分析（TASKS §1.1 L48）**：
   - TASKS §1.1 L48 出现注记「NC-008/NC-017 补 NC-025 依赖：生产 BlobGateway 此前无任何任务拥有」。
   - 但在 TASKS §1 总表（L32）中 NC-017 依赖已锁定为 `NC-004, NC-015`（未列 NC-025），且 TASKS NC-017 专节（L260）与 v1.6 S6 模型明确声明「不依赖服务端与 BlobGateway」。
   - 契约 D-NC017-08 与 ACT.yaml 第 14 行采用抽象端口 `AttachmentBytesSource` 注入附件字节，成功解耦生产 BlobGateway。该设计忠实于 v1.6 最终意图，处理严谨合理。
6. **S6 背景确认**：
   - 契约在全文前提明确申明「没有长期密钥、没有云端备份、没有恢复材料。口令派生的密钥只用于这一个文件，不保存、不上传；忘记口令则文件无法打开，这是产品明示的设计，不是缺陷」。审查确认为有效设计，不作问题提出。

---

## 3. 二查：覆盖性（Coverage）

### 3.1 需求条目与测试/验收覆盖矩阵

| TASKS 需求 / 验收要求 | 契约测试用例（§8） | BDD 场景 | TDD 覆盖 | 负向 / 边界覆盖细节 |
|---|---|---|---|---|
| Argon2id 口令派生（参数写死） | E01 `argon2id_key_matches_openssl_reference`<br>E14 `passphrase_is_utf8_without_normalization` | E01, E14 | §2（8 测试之一）<br>§3 | 负向：E14 验证非归一化 Unicode（`café` 预组合 vs 分解形式）拒绝解密；空口令拒绝（E12）。 |
| 清单格式与摘要校验 | E02 `header_digest_and_bytes_match_reference`<br>E07 `tampered_header_or_changed_kdf_params_raise_format_error` | E02, E07 | §2 | 负向：E07 覆盖改 created_at、改 memory_kib（重算摘要仍被拒）、改 magic 字节，均抛 `ExportFormatError`。 |
| AES-256-GCM 单块/整文件参考值 | E03 `single_chunk_file_matches_reference_sha256`<br>E04 `decode_reference_file_roundtrips_records` | E03, E04 | §2 | 包含明文 SHA-256、nonce、块 SHA-256、文件总长 1344 B 与文件 SHA-256 的全链路比对与往返解密。 |
| 密文无明文与私密性断言 | E05 `raw_bytes_contain_no_plaintext_title_body_attachment_or_ids` | E05 | §2 | 负向：断言原始字节不含明文标题、正文片段、附件标记、note ID 与 ownerScope。 |
| 统一失败语义（错口令与密文损坏） | E06 `wrong_passphrase_tamper_reorder_truncate_append_raise_same_undecryptable` | E06 | §2 | 负向：覆盖 5 类攻击/破坏（错口令、改 1 字节、交换两块、删末块、追加一块），断言均抛同类型同 toString() 异常且无部分内容。 |
| 分块与末块边界判定 | E08 `chunk_boundary_exact_multiple_and_plus_one` | E08 | §2 | 边界：测试 2 MiB 恰好（2 满块）与 2 MiB + 1 字节（2 满块 + 1 字节末块），解密往返逐字节一致。 |
| 仓库内容收集（完整修订链与排除项） | E09 `writer_exports_active_and_trashed_with_full_revision_chain_excluding_pending_op` | E09 | §3 | 业务覆盖：包含 active（多父合并、restored_from、change_summary）、trashed、排除 purge_pending；校验 13 个字段完整性；断言无 pending_op / owner_scope。 |
| 原子写入与崩溃遗留临时文件 | E10 `writer_crash_leaves_only_partial_file` | E10 | §3 | 异常/中断：经 `debugHook('after_chunk:0')` 注入崩溃，断言目标不存在、`.partial` 完好遗留。 |
| 写入后自检失败删除临时文件 | E11 `writer_verification_failure_deletes_partial` | E11 | §3 | 故障自愈：经 `debugHook('before_verify')` 篡改 `.partial`，断言捕获自检失败且 `.partial` 已被删除清理。 |
| 前置校验与附件异常捕获 | E12 `writer_rejects_existing_target_empty_passphrase_missing_or_mismatched_attachment` | E12 | §3 | 边界/负向：覆盖目标已存在（不覆盖）、口令为空、附件缺失、附件 SHA-256 摘要不符 4 类情形，断言各自专属异常及磁盘清理。 |
| 导出进度与文件摘要计算 | E13 `writer_reports_progress_and_result_sha256` | E13 | §3 | 覆盖：真实 2 篇笔记触发进度 `(1,2)`、`(2,2)` 回调；返回值 `fileSha256` 与测试独立重算完全一致。 |

覆盖性结论：TASKS NC-017 的全部功能点与异常路径均已映射至具名测试与 BDD 场景，无仅覆盖 happy path 现象，二查**通过**。

---

## 4. 三查：可执行性（Actionability）

### 4.1 目录与文件系统存在性核验

1. 新文件父目录：
   - `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/lib/src`：**存在**（drwxr-xr-x）。`lib/src/export/` 尚未创建，写入时作为新目录自动创建。
   - `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/test`：**存在**（drwxr-xr-x）。`test/export/` 尚未创建，写入时作为新目录自动创建。
2. 既有修改目标：
   - `pubspec.yaml`：**存在**，第 18 行为 `http: 1.6.0`，第 19 行为空行，定位点明确。
   - `pubspec.lock`：**存在**，当前无 `cryptography` 包记录。
   - `lib/reading_notes.dart`：**存在**（36 行），末尾无导出冲突。

### 4.2 代码符号与外部库真实性核验

1. **`reading-notes` 内部符号核对**（实地查阅 `lib/src/persistence/` 与 `lib/src/domain/`）：
   - `NoteRepository`（`note_repository.dart`）：
     - `db` 字段：`final NoteDatabase db;`（第 41 行，真实存在）。
     - `ownerScope` 字段：`final String ownerScope;`（第 42 行，真实存在）。
     - `listRevisions(noteId)`：`Future<List<NoteRevision>> listRevisions(String noteId)`（第 516 行，按 `createdAt asc, id asc` 排序，真实存在）。
     - `headIds(noteId)`：`Future<List<String>> headIds(String noteId)`（第 473 行，真实存在）。
     - Drift 表：`Notes` 包含 `ownerScope`、`lifecycle` 联合索引 `idx_notes_owner_scope_lifecycle`（`tables.dart` 第 28 行），支持按 `lifecycle IN ('active', 'trashed')` 只读过滤。
   - `Clock` 接口（`clock.dart`）：
     - 方法：`String nowUtc();`（第 2 行，返回 RFC 3339 毫秒精度 UTC，真实存在）。
   - `IdGenerator`（`ids.dart`）：
     - 方法：`String newId(String prefix);`（第 4 行，真实存在）。
   - `NoteRevision` 与 `AttachmentRef`（`note_revision.dart`）：
     - `AttachmentRef.toMap()`：返回包含 `attachment_id`、`object_version`、`content_digest`、`alt`、`caption` 的 Map（第 19 行，真实存在）。
     - `MentionRef.toMap()`、`BindingRef.toMap()`、`AnchorRef.toMap()` 均真实存在。
     - `NoteRevision` 具备 13 个只读属性（`id`, `noteId`, `parentIds`, `title`, `markdown`, `attachmentRefs`, `mentions`, `bindings`, `contentHash`, `changeSummary`, `restoredFrom`, `createdAt`, `createdOnDevice`），由写入器将其属性组合为 Schema 对应的 Map。
2. **`cryptography 2.9.0` 库接口核对**（查阅 `~/.pub-cache/hosted/pub.dev/cryptography-2.9.0`）：
   - `Argon2id` 构造参数（`algorithms.dart` 第 503 行）：
     `factory Argon2id({required int parallelism, required int memory, required int iterations, required int hashLength})`，完全匹配契约的 `memory: 65536, iterations: 3, parallelism: 1, hashLength: 32`。
   - `deriveKey` 参数（`kdf_algorithm.dart` 第 34 行）：
     `Future<SecretKey> deriveKey({required SecretKey secretKey, required List<int> nonce})`，完全匹配。
   - `AesGcm.with256bits`（`algorithms.dart` 第 391 行）：
     `factory AesGcm.with256bits({int nonceLength = AesGcm.defaultNonceLength})`，支持 `nonceLength: 12`，完全匹配。
   - `encrypt` 与 AAD（`cipher.dart` 第 293 行）：
     `Future<SecretBox> encrypt(List<int> clearText, {required SecretKey secretKey, List<int>? nonce, List<int> aad = const <int>[], Uint8List? possibleBuffer})`，完全匹配。

### 4.3 参考值独立复算验证

审查者在 `/private/tmp/nc017r/` 下执行双独立工具链复算：
1. **Argon2id 密钥推导**：调用系统 OpenSSL 3.6.3：
   ```bash
   /opt/homebrew/opt/openssl@3/bin/openssl kdf -keylen 32 \
     -kdfopt pass:"correct horse battery staple 中文口令" \
     -kdfopt hexsalt:01010101010101010101010101010101 \
     -kdfopt iter:3 -kdfopt memcost:65536 -kdfopt lanes:1 ARGON2ID
   ```
   输出：`51:b4:8c:d5:74:43:dc:0a:21:90:81:bb:e7:3d:c6:e9:7a:75:c4:74:eb:2c:15:d7:f5:57:c0:04:4c:07:d6:a3`。
2. **容器与 AES-256-GCM 分块加密**：使用 `xuan-server/functions-py/.venv/bin/python` 独立编写 `recalc.py` 复算清单、规范 JSON、明文流、nonce、AAD 与分块密文。

#### 契约 §7 参考值与独立复算结果逐项比对表

| 项目 | 契约 §7 字面量 | 独立复算实测输出 | 结论 |
|---|---|---|---|
| K（派生密钥） | `51b48cd57443dc0a219081bbe73dc6e97a75c474eb2c15d7f557c0044c07d6a3` | `51b48cd57443dc0a219081bbe73dc6e97a75c474eb2c15d7f557c0044c07d6a3` | **100% 吻合** |
| D（清单摘要） | `2951a806b37bb65622017f6507fd20fae909485d3626963b92f08d136ef5b472` | `2951a806b37bb65622017f6507fd20fae909485d3626963b92f08d136ef5b472` | **100% 吻合** |
| 头部字节长度与内容 | 536 字节，键按码点排序，无空白 | 536 字节，UTF-8 字符序列完全一致 | **100% 吻合** |
| 明文记录流长度与摘要 | 764 B，SHA-256: `61a5be5312ceb845fe7d4cccaff78ddbd74fc480f1584bb2b6ce578dc19d4886` | 764 B，SHA-256: `61a5be5312ceb845fe7d4cccaff78ddbd74fc480f1584bb2b6ce578dc19d4886` | **100% 吻合** |
| 第 0 块 nonce | `3a65508b4842461f25b17142` | `3a65508b4842461f25b17142` | **100% 吻合** |
| 第 0 块长度与摘要 | 792 B，SHA-256: `37ccbe5f88cb425abc90f869b7d2c9229d6c63fb6a3b2519ca20c6317b828a98` | 792 B，SHA-256: `37ccbe5f88cb425abc90f869b7d2c9229d6c63fb6a3b2519ca20c6317b828a98` | **100% 吻合** |
| 整个文件长度与摘要 | 1344 B，SHA-256: `85df88a1f217a8d3d6dcf5f8b8c5fd87f89c4b397bbc72a8ec98cb320eb12564` | 1344 B，SHA-256: `85df88a1f217a8d3d6dcf5f8b8c5fd87f89c4b397bbc72a8ec98cb320eb12564` | **100% 吻合** |
| AAD 认证负例（final=0） | 解密抛认证失败异常 | Python AESGCM decrypt 抛 `InvalidTag` 异常 | **100% 吻合** |

### 4.4 验证计数、门禁与模糊词核查

1. **测试计数链条一致性**：
   - 基线：NC-011 CLIENT 提交后，`flutter test` 239 个通过。
   - act/01：实现 8 个测试（E01～E08），测试子集为 `+8`，全量为 `+247`。
   - act/02：追加 6 个测试（E09～E14），测试子集为 `+14`，全量为 `+253`。
   - 核对契约 §8、README、TDD、act/01、act/02、ACCEPTANCE 与 `nc017_guard.sh`，数值完全一致闭环。
2. **ON_FAIL 与工期**：
   - act/01 与 act/02 均包含具体的 ON_FAIL 停止条件与处置指引。
   - 单 ACT 预估工期均为 50 分钟（处于 30～60 分钟标准区间）。
3. **模糊词扫描**：
   - 全文正则扫描 `适当|优雅|合理|必要时|酌情|尽量|大致|视情况`，命中数为 0。

### 4.5 技术细节与边界可行性分析

1. **E10/E11 中 `debugHook` 与 `.partial` 实现机理**：
   - `ExportWriter` 显式注入 `@visibleForTesting Future<void> Function(String stage)? debugHook`。
   - 在 E10 中，hook 于 `'after_chunk:0'` 阶段抛出异常，写入器捕获未受控中断语义，不执行删除清理代码直接上抛，`.partial` 完好留存；
   - 在 E11 中，hook 于 `'before_verify'` 篡改 `.partial` 字节，步骤 5 对比流式哈希与重读哈希发现不符，执行删除清理并抛出 `ExportWriteVerificationFailed`。
   - 该机制在纯 Dart 单元测试中 100% 确定性可控，无需启动系统级 kill。
2. **E05 在 act/01 阶段的构造方式**：
   - act/01 尚无 `ExportWriter`，TDD §2 第 22 行明确规范：`E05 在 act/01 以格式层直接编码实现（构造含独特标题/正文/附件字节的记录，经 ExportChunkEncoder 得到文件字节后断言）；act/02 不再改该测试`。
   - 该说明完全消除了 act/01 执行者因缺少写入器而卡住的风险，分阶段安排合理。
3. **Argon2id 耗时与测试套件性能**：
   - 桌面 Dart VM 单次 Argon2id（m=65536, t=3, p=1）实测耗时约 358 ms。
   - 测试套件中涉密推导约 12～15 次（E06 中 5 次，其余用例各自 1 次），总纯计算耗时约为 4.5～5.5 秒，远低于 Flutter 测试单用例 30 秒超时门禁，不会引发 flakiness。
4. **`ExportChunkEncoder` 末块判定逻辑**：
   - 编码器内部最大缓冲 1 块（1048576 字节）加 1 字节。`add` 仅在 `buffer.length > 1048576` 时输出 1048576 满块（final=0）；`close` 将剩余 1～1048576 字节输出为末块（final=1）。
   - 明文记录流末尾必定包含 `0x7F EndRecord`（长度 > 40 字节），因此整体明文流永不为 0 字节。当明文恰为 1 MiB 整数倍时，末块即为满块，不会输出多余的 0 字节空块。规则数学严谨。
5. **`decodeExportFile` 的零块与截断判定**：
   - 一个合法块的最小长度为 28 字节（12 字节 nonce + 0 字节 ciphertext + 16 字节 tag）。
   - 契约明确规定：头部解析后若剩余字节数为 0（零块）、末尾不足 4 字节读取 `chunk_len`、或 `chunk_len < 28`、或 `chunk_len` 超出剩余文件范围，均直接抛出 `ExportUndecryptable`。边界无任何歧义。

可执行性结论：符号、路径、算法、参考值、异常路径与运行耗时均通过严密核验，三查**通过**。

---

## 5. 四查：独立性（Independence）

### 5.1 ACT 拆分与依赖链

- `act/01.yaml`（NC-017-A）：`DEPENDS_ON: []`。目标为格式层编解码与基础容器。
- `act/02.yaml`（NC-017-B）：`DEPENDS_ON: [NC-017-A]`。目标为仓库收集、原子写入与进度回调。
- 依赖关系单向无环。

### 5.2 符号闭包性

- `act/02` 仅使用 `act/01` 交付的 `ExportHeader`, `ExportRecord`, `encodeRecord`, `ExportChunkEncoder`, `ExportContents`, `decodeExportFile`, `ExportFormatError`, `ExportUndecryptable` 等公开导出，以及 `reading-notes` 既有基础领域模型与仓储。
- 未引用任何未交付或虚构的跨任务符号。

### 5.3 跨工作包工作树并发冲突防御

- 冲突风险点：`reading-notes` 的 `pubspec.yaml` 与 `lib/reading_notes.dart` 为共享文件，同时涉及 NC-011 CLIENT 线与 NC-016。
- 规避机制：
  1. 契约 D-NC017-11 明确规定「在 NC-011 CLIENT 线完成后开工，不与其并行（同一工作树只允许一个执行者写）」。
  2. ACT.yaml 第 6 行将 `NC-011 CLIENT 线 act/06 已提交` 列为硬性派发前置门禁（`DISPATCH_PRECONDITION`）。
  3. act/01 VERIFICATION 第 1 条要求执行前核对 `git log --oneline -1` 包含 `NC-011-F`，否则立即停手。
  4. 依赖版本保持单一共识：D-NC017-10 明确 `cryptography: 2.9.0` 版本锁定，供后续 NC-016 沿用。

独立性结论：任务划分清晰，交付物闭包，跨任务串行门禁可靠，四查**通过**。

---

## 6. 守卫脚本运行证据

在 `learn_system` 根目录执行 `bash docs/blackbox-spec-rework/reviews/nc017_guard.sh`：
```
Created At: 2026-09-12T11:24:34-07:00
Completed At: 2026-09-12T11:24:34-07:00

PASS  K01 回归：v1.6 守卫与 verify.sh 均为 0
PASS  K02 契约：六个参考值、14 个测试名、容器/异常/hook 关键字、D-NC017-01～11、九节
PASS  K03 六件套：BDD E01～E14、两个 ACT 30–60 分钟、依赖链、ON_FAIL/WORKLOAD、无模糊词、测试名与计数
PASS  K04 SUBAGENT_TODO 已登记 NC-017 工作包与契约
SKIP  K05 NC-017 产物（验收时加 --require-impl，必须 PASS）

NC-017 失败条数：0
```

---

## 7. 建议（非阻断）与待裁决事项

### 7.1 建议（非阻断）

1. **`NoteRevision` 属性导出辅助函数**：
   - 现行 `NoteRevision` 未自带 `.toMap()` 方法（其嵌套的 `AttachmentRef`、`MentionRef` 等自带 `.toMap()`）。
   - 建议在 `export_bundle_format.dart` 或 `export_writer.dart` 中实现一个私有/公用映射辅助函数 `Map<String, Object?> _revisionToExportMap(NoteRevision rev)`，将 13 个字段转换为契约规定的 snake_case Map，避免在多处重复展开。
2. **E06 测试中 Argon2id 派生开销优化（可选）**：
   - E06 包含 5 种篡改解密负例。如果直接调用 5 次 `decodeExportFile` 会执行 5 次 Argon2id 派生（总计约 1.8 秒）。
   - 现行设计已在可接受耗时内；执行者如希望进一步加快测试执行，可保持规范语义，无需特殊 hack。

### 7.2 待裁决事项

- **无**。所有需求口径、密码学参数、前置依赖及写入白名单均已闭合冻结。

---

## 8. 审查总结

NC-017 契约与六件套在**忠实性、覆盖性、可执行性、独立性**四查中全部达标：
- 密码学参数与参考值经 OpenSSL 与 Python 双重独立复算，完全吻合；
- 既有代码符号真实存在，数据模型与索引支撑良好；
- 负向路径与异常安全（原子改名、崩溃残留 `.partial`、自检失败删除）覆盖完备；
- 派发前置与工作树互斥门禁清晰。

判定：**`READY`**（返工 0 项）。可待 NC-011 CLIENT 线提交后依序派发执行。
