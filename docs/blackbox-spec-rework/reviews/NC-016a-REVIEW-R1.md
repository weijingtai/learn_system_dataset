# NC-016a 转译审查 R1（wjt-react 四查）

- 审查日期：2026-09-12
- 审查者：转译审查者（未参与 NC-016a 契约与六件套编写；只读，不改 ACT/契约/验收标准）
- 被审：契约 `openspec/annotation-community/contracts/private_sync_impl.md`（全文）与 `private_sync.md`（含 §10）；六件套 `docs/blackbox-spec-rework/work-items/nc-016a/`（README/BDD/TDD/ACT.yaml/act/01～03/ACCEPTANCE/PROMPT）；守卫 `reviews/nc016a_guard.sh`
- 计划区：`TASKS.md` NC-016 节（248～253 行）、NC-015 节 241～242 行；`DESIGN.md` 27/215/223/225～227 行；`INTEGRATION_BASELINE.md` 59 行；`nc-015/ACCEPTANCE.md` 9 行（4b 交接）
- 判定：**READY**（最终判定；R1 曾判「返工 2 项」，R2 复核已闭合，见文末「## R2 复核」）

---

## 一查 忠实性：通过（附 1 项越界冲突，见返工 R1）

**拆分的 TASKS 覆盖（无遗漏）**：TASKS NC-016 四个 checkbox 逐项落位——
- 250 行「新增 mapper/sync/test，私有/public 不同 entityType」→ 契约 §4 常量与 §6；`每设备注册`实际落位登记给 16b（ACT.yaml `DEFERRED`、D-NC016-01），常量本身无测试（见建议 A1）。
- 251 行「密文无明文负向断言（原始字节）」→ §7 + S07。
- 252 行「去重 / 双方分支保留 / 错误账号指纹过期吊销在交换正文前拒绝 / 实际比较 peerDeviceId 与 peerFingerprint」→ S13、S04+S17、X01+X02+S01+S15、X02。
- 253 行「两台真实设备 LAN/WebRTC 集成测试」→ 明确登记 16b（`BLOCKED`，等 NC-001 设备表）。
命令行与守卫由 TDD §1 + nc016a_guard.sh 承接。**无凭空新增项**；`DEFERRED` 三项（16b 集成/中转/宿主装配、`fix/nc016a-guard-aad` 合并、生命周期 op→NC-019）与 `private_sync_impl.md` §1/§10 一致。

**与上游契约逐条核对**：
- `private_sync.md` §3.3（guard 三步比较）＝ 契约 §3.1；第 8 步 `now >= expiresAt` 与 §3.3 第 8 条 `nowUtcMs < expiresAt` 语义相同。**无冲突**。
- §4.3 包装公式：契约 §6.2 第 5 步（GCM nonce 取 `nonceW[0:12]`、HKDF salt 用完整 16 字节）＝ §10 + D-NC016-05。**无冲突（§10 已回填）**。
- §4.4 签名字段：契约 §6.1 `signedFieldNames` 10 个字段与顺序 ＝ §4.4 ＝ `envelope_valid.json.signed_fields`（逐字核对）。**无冲突**。
- §6 七步顺序与结果码闭集：契约 §6.3 第 0～7 步与 §6 的 AAD→哈希→Schema→去重→落库顺序一致；所用结果码 `reject:schema_invalid/source_untrusted/bad_signature/aad_mismatch/hash_mismatch`、`duplicate_ack`、`accept`、`session_key_unbound`、`pairing_refused_anonymous`、`config_ok`、`layers_ok` 全部落在 §8 闭集内。**无冲突**。
- D-NC015-08：契约 §4 `accountBindingCertHash = SHA-256_hex(UTF8(a|d|f))`；S02 期望 `c2d5f307…0504` 已用 fixture 三字段独立复算吻合。**无冲突**。
- D-NC015-09：契约 §6.2 第 0 步 / §6.3 `openSession` 的消息拼接 `appUserId|recipient|sender|sessionId` 与 §4.3 会话公钥绑定一致。**无冲突**。
- `private_export.md`：`canonicalJson` 复用（契约 §4 第 103 行）、修订 13 键映射（§4 第 92 行）与 §4.2 一致；参考值 payload 1919 B 已复算吻合。**无冲突**。
- `local-persistence.md` §4：outbox 状态推进归 NC-016；契约 §5 `markEnvelope` 在 `pending→sent→acked` 之外增设 `sent→pending`（重发）。属 §4 授权的「推进归 NC-016」范围内，**非冲突**（见待裁决 C2）。
- `local-persistence.md` §5/§5.1：**冲突**——契约 §5 第⑤步事务内先插 `notes` 再插 `note_revisions`，与 §5.1 第 5 条及既有 `createNote`（先 revisions 后 notes）相反，且违反外键约束（见返工 R1）。
- `local-persistence.md` §5.2：S05 复用 `FailingInterceptor` 写法一致。**无冲突**。

---

## 二查 覆盖性：通过

| TASKS NC-016 要求 | 覆盖测试 | 核对 |
|---|---|---|
| 私有/public 不同 entityType | 无直接测试（常量在 §4；注册归 16b） | 建议 A1 |
| 「密文无明文」原始字节负向断言 | S07（§7，JSON 字节 + payload 原始字节） | ✓ |
| 重复投递去重 | S13（`duplicate_ack`，零写入）；S04 二次应用同修订→`duplicate` | ✓ |
| 双方分支保留 | S04（两头、preferred 先到）、S17（C 两头） | ✓ |
| 错误账号/指纹/过期/吊销在交换正文前拒绝 | X01（scope/expired/revoked/device/fingerprint 夹具）、S01、S15（无记录/revoked/到期/epoch2） | ✓ |
| 实际比较 peerDeviceId 与 peerFingerprint | X02 `guard_patch_order_device_then_fingerprint_then_expiry` | ✓ |
| guard 补丁偏离既有五步 | X01 8 夹具 + X02 顺序/边界（`now==expires`） | ✓ |
| AAD 绑定（含块级） | X03（同/异/缺省 AAD、单侧缺省）、S11、S12、S14 | ✓ |
| NC-015 交接 4b：匿名拦截 | S03 `pairingGate(isAnonymous:true)` | ✓ |
| NC-015 交接 4b：AAD 失败 | S11 `reject:aad_mismatch` | ✓ |
| NC-015 交接 4b：会话公钥签名 | S16 `SessionKeyUnbound`（未取随机数） | ✓ |
| 参考值跨实现 | S08（§9 全部 14 项字面量） | ✓ |
| 服务端/存储不越界 | 白名单（§2）+ 守卫 K06/K05 范围核对 | ✓ |

只覆盖 happy path 的问题不存在：负向用例（X02、X03、S07、S10～S16）齐备，且每条验收标准至少一个 ACT 的 `TESTS_FIRST`/`VERIFICATION` 覆盖（BDD/TDD/契约 §3.3、§8 映射逐条对上，`nc016a_guard.sh` K03 亲验通过）。

---

## 三查 可执行性：返工 2 项

**SCOPE 路径逐一存在（亲验）**：
- STORAGE：`core/lib/sync/same_account_im_reconciliation.dart`、`core/lib/model/blob_cipher.dart`、`drift/lib/blob/aes_gcm_blob_cipher.dart`、`drift/lib/blob/identity_blob_cipher.dart`、`drift/test/blob/blob_cipher_test.dart` 全部存在；新文件父目录 `core/test/`、`drift/test/blob/` 存在（`core/test/fixtures/` 与 `drift/test/blob/aes_gcm_aad_test.dart` 为新，父级在）。
- CLIENT：`lib/src/`、`test/`、`test/fixtures/` 存在；`lib/src/storage/`、`test/storage/`、`test/fixtures/private_sync/` 为新（父级在）；`lib/reading_notes.dart`、`lib/src/persistence/note_repository.dart` 存在。
- READ 依赖：`core/lib/model/im_models.dart`（`TIMPeerAuthorization` 7 字段同名，555～572 行）、`test/persistence/`、`fixtures/community/content_hash_cases.json`、`~/.pub-cache/.../cryptography-2.9.0/lib/src/cryptography/` 均在。

**契约假定符号真实存在且签名核对通过**：
- `SameAccountSessionGuard.verifyPeerSession`（xuan-storage `core/lib/sync/same_account_im_reconciliation.dart:26`，`final class` 不可继承；追加可选命名参数不破坏 `SameAccountIMReconciler` 与 p2p 测试调用）。
- `BlobCipher.encryptChunk/decryptChunk`（`core/lib/model/blob_cipher.dart`）；全仓 `implements BlobCipher` 仅 3 处：`AesGcmBlobCipher`、`IdentityBlobCipher`、`TestPrivateCipher`——**全部在契约 §2.1 白名单内**，接口加可选命名参数不会漏改实现者。
- reading-notes：`NoteRepository` 的 `ownerScope`/`clock`/`db`/`_checkSession`（`note_repository.dart:47`）/`getRevision`/`headIds`/`getNote` 均在；`OutboxEnvelope`/`OutboxState`、`Note`/`NoteKind`、`NoteRevision` 13 字段均在；`nchash.encode/normalizeSnapshot/contentHash`、`export_bundle_format.canonicalJson`、`SaveFailed`、`StaleSessionError` 均在；`cryptography: 2.9.0`、`crypto: 3.0.7` 在 `pubspec.yaml`。
- pub-cache `cryptography-2.9.0`：`X25519().newKeyPairFromSeed`（`algorithms.dart:2220`）、`sharedSecretKey({keyPair:, remotePublicKey:})`（`key_exchange_algorithm.dart:135`）、`Ed25519().newKeyPairFromSeed`（`algorithms.dart:1184` 区）、`Hkdf(hmac:, outputLength:)`（`:1281`）且 `Hkdf.deriveKey({secretKey:, nonce:, info:})`（`:1304`，`info` 存在）、`AesGcm.with256bits({nonceLength=12})`（`:391`）、`SimplePublicKey(..., type: KeyPairType.x25519)`（`x25519.dart` 内）。**签名全部成立**。

**参考值独立复算（全部逐字吻合）**：脚本 `/private/tmp/nc016r/recompute.py`，用 `xuan-server/functions-py/.venv`（pyca 50.0.1 + `xuan.community_hash`），按契约 §6、§9 用 nchash `E` 编码与 pyca AESGCM/HKDF/X25519/Ed25519 复算 14 项，与 §9 表逐项相等：

```
signed digest   dafcb7e0…95c3   = §9
sender ed pub   c853ad0f…60a7   = §9
envelope sig    e639de16…e78e0b = §9
eph_pub         7b4e909b…3f13   = §9
session_pub     0faa684e…0f20   = §9
x25519 shared   9e004098…5056   = §9
wrap_key        4da4b1c9…ddf2   = §9
wrapped_dek     75fcbd72…f90d   = §9
plaintext 1919B b8006c35…67c7   = §9
nonce_0         0e51b2e763b667f6a87f1abc = §9
chunk0 1935B    e776bae8…5424   = §9
receiver ed pub 34b4d904…a746   = §9
session_pub_sig 9ff25742…1103   = §9
cert hash       c2d5f307…0504   = §9
```

**Dart 种子语义与 pyca 一致性（给出行号）**：`DartX25519.newKeyPairFromSeed` → `modifiedPrivateKeyBytes`（`cryptography-2.9.0/lib/src/dart/x25519.dart:54`）：`result[0] &= 0xf8; result[31] |= 0x40; result[31] &= 0x7f`，即 RFC 7748 clamp；pyca `X25519PrivateKey.from_private_bytes` 在 `public_key()`/`exchange()` 内部由 `_decode_scalar` 做同一 clamp。故 `newKeyPairFromSeed(32B种子)` 与 `from_private_bytes` 产出一致（种子 `0x22×32` → `session_pub=0faa684e…`，种子 `0x11×32` → `eph_pub=7b4e909b…`，已复算吻合）。`sharedSecretKey` 内对已 clamp 字节再 clamp 幂等（`x25519.dart:64` 调 `modifiedPrivateKeyBytes(keyPairData.bytes)`）。Ed25519：`DartEd25519.newKeyPairFromSeed` 直接以 32 字节种子为私钥（`lib/src/dart/ed25519.dart:34`），签名时 SHA-512 后取半并置位（`:64`～），即 RFC 8032，与 pyca 相同（种子 `0x77×32`→`c853ad0f…`、`0x66×32`→`34b4d904…` 已复算吻合）。契约 §9 末句「若实测不等按停手上报」成立。

**VERIFICATION 命令合法**：`flutter` 在 `/Users/jingtaiwei/flutter/bin/flutter`（存在）；`git worktree add … 8ddb877`、`git diff --numstat HEAD~1 HEAD`、守卫 `--require-impl storage|client` 参数解析正确（`MODE=$1; LINES=$2; req=storage` 或 `client`）。**计数一致**：契约 §3.3（+2/+4/+1，+10 不变，+3 不变）、§8（+259/+270）、README（baseline +253，+4/+3/+10）、TDD §1（+2/+4/+3/+1、+6/+17、+259/+270）、act/01（+2/+4/+3/+1）、守卫 K03（要求 TDD 含 `+2/+4/+3/+6/+17/+259/+270`）**逐项一致**；`nc016a_guard.sh`（无参）实跑 K01～K04 全 PASS、失败 0。**ON_FAIL** 三个 ACT 均有。**时长** act/01=45、act/02=55、act/03=60，均 30～60。**模糊词**：按守卫正则（`适当|优雅|合理|必要时|酌情|尽量|大致|视情况`）对六件套 + 契约扫描，命中 0。

**技术可行性**：
- xuan-storage 新 worktree + `flutter pub get`：`AGENTS.md`（38～45 行「新 worktree 必须先 flutter pub get」）满足条件已备；包内跨包路径依赖为 `../core`（worktree 内 `drift/../core` 指向 worktree 自身 `core`，成立），外部依赖均为 gitea `git:`（基线已实测三包 `pub get` 0）。无 `pubspec_overrides.yaml` 也能解析，不触发停手条件。
- `applyRemoteRevision` 在 Drift 事务中实现：**不可行**（第⑤步顺序违反外键，见返工 R1）。`FailingInterceptor` 复用可行（`note_database_test.dart` 已用同一套 `QueryInterceptor`，且 `note_database.dart:41` `PRAGMA foreign_keys = ON`）。
- S11「同一会话由 dev_c 接收」：**可构造但歧义**——第 0 步要求 `sessionPubSig` 在 `recipientDeviceId=dev_b` 下验签通过，而 dev_c 的 `openSession` 签的是 dev_c 绑定；测试须用「permissive 验签替身」或另造一把关联 dev_b 的签名密钥。可行，但契约未点明（见建议 A2）。
- S14「未调用验签」：可行（验签端口用记账替身，断言未被调用）。
- S16「未调用 randomBytes」：可行（`randomBytes` 注入记账/抛错替身；第 0 步在取随机数之前，契约 §6.2 第 0 步 vs 第 3 步）。
- ACCEPTANCE 盲测 ①「多块信封」：**可构造**——`seal` 不施加内联上限，正文 markdown 取 `noteMarkdownMaxBytes=1048576`（`limits.dart`）即令明文 payload > 1048576 → 2 块（参考单块 1919 B 不冲突）。① 只要求 pyca 独立解密，不需 `receive`。
- ACCEPTANCE 盲测 ②「交换两块顺序/删末块 → `reject:aad_mismatch`」：**不可执行**（见返工 R2）。

### 返工项（按严重程度排序）

1. **契约 §5 第⑤步 / ACT NC-016a-B**：`applyRemoteRevision` 在笔记不存在时**先插 `notes`（`preferred_head_id = revision.id`）再插 `note_revisions`**，违反 `notes.preferred_head_id REFERENCES note_revisions(id)` 外键（reading-notes `note_database.dart:41` 开 `PRAGMA foreign_keys = ON`，`note_database_test.dart` 断言 fk=1），且与 `local-persistence.md` §5.1 第 5 条及既有 `createNote`（先 revisions 后 notes）相反。执行者照抄合同即令 S04/S05/S09/S13/S17 在建笔记处 `FOREIGN KEY constraint failed` → 回滚为 `SaveFailed`，S05 的注入拦截点也永远到不了 `note_heads`。 ｜ 修正标准: 契约 §5 第⑤步与 act/02 顺序改为 **`note_revisions` → `notes` → `note_heads`**（与 §5.1 及 `createNote` 一致）；验证：`/private/tmp/nc016r/fk_check.py` 复现——notes-first 抛 `IntegrityError: FOREIGN KEY constraint failed`，revision-first 通过；改后 S04 建笔记步骤变绿。

2. **ACCEPTANCE 盲测 ②（及 §6.3 第 0 步）**：② 要求对**多块**信封换序/删末块并断言 `reject:aad_mismatch`，但多块意味着 `payload.length ≥ 2×1048576`，而 `receive` 第 0 步先执行 `payload.length > maxInlinePayloadBytes(262144) → reject:schema_invalid`，且 `payloadCipherRef != "inline"` 也被拒；契约未提供任何绕过第 0 步的入口（`PrivateNoteSyncReceiver` 构造无 `maxInlinePayloadBytes` 覆写参数，白名单也不允许新增旁路），故 ② 在 Dart 侧**不可达**（① 仅需 seal 产物 + pyca，可行）。 ｜ 修正标准: 二者其一——(a) 契约给 `PrivateNoteSyncReceiver`（或一个 `@visibleForTesting` 载荷解密入口）增加可覆写的内联上限/解密入口，并在 ACCEPTANCE ② 写明用该入口，使换序/删末块仍能到达第 3 步认证失败；或 (b) 删除 ② 并换成对单块 ≤262144 信封的帧篡改用例（并注明测不到「多块换序」语义）。验证：盲测脚本能对同一多块信封产出 `reject:aad_mismatch` 而非 `reject:schema_invalid`。

### 建议（非阻断）

- **A1 契约 §4 / ACT-02**：`privateNoteEntityType`/`publicSnapshotEntityType`/`privateSyncEntityPolicies` 无任何测试断言（S01～S17 均未覆盖），守卫 K02 也不检查；TASKS 250 行「私有/public 注册不同 entityType」的实际注册已归 16b。建议在 S03 或新增断言钉死 `privateSyncEntityPolicies` 两个 entityType 不同且策略分别为 `private`/`shared`，避免只靠评审看代码。
- **A2 ACT-03 / 契约 §6.3 第 0 步**：S11 的构造须点明「验签端口用 permissive 替身或另造 dev_b 绑定密钥」，否则便宜模型会在「签名必须有效 vs 收件人必须是 dev_b」之间卡住。
- **A3 契约 §6.2 第 4 步伪代码**：`_aesGcm.encrypt(plain_i, secretKey: dek, …)` 中 `dek` 为 `List<int>`，需写作 `SecretKey(dek)`（同仓 `export_bundle_format.dart` 的做法）。
- **A4 ACT-01 VERIFICATION 第 4 条 vs TDD §1 第 7 条**：一条命令含新文件期望「改动前 +1」，另一条只跑两个既有文件期望「不变」，二者自洽但易读混；建议统一为「新文件单独 +1，既有文件不变」两句。
- **A5 ACCEPTANCE ③/⑤**：`SealedEnvelope.toJson→fromJson` 往返后 `receive` 仍 `accept`、三包 `flutter analyze` 问题数不变，均由主 Agent 执行、无脚本，建议补一段可复跑命令（与 TDD §1 对齐）。

### 待裁决

- **C1 NC-017 派发前置**：NC-016a `README.md:3`、`ACT.yaml DISPATCH_PRECONDITION`、`ACCEPTANCE.md:3` 称「NC-004、NC-007、NC-015、NC-017 均 ACCEPTED（已满足）」，但 `work-items/nc-017/ACCEPTANCE.md:3` 仍写「当前：未验收」；同文件 R1 记录（20、34 行）与 `nc-017/README.md:3`、`nc-017/ACT.yaml:2` 均为 `ACCEPTED`。实为 NC-017 头部行陈旧。请裁决是否顺手订正 NC-017 ACCEPTANCE 头部（不影响 NC-016a 派发，已满足）。
- **C2 `markEnvelope` 增加 `sent→pending`**：`local-persistence.md` §4 只写 `pending→sent→acked`，契约 §4「状态推进归 NC-016」授权扩展；请确认重发边是否为 16a 期望语义（S06 已断言）。
- **C3 ACCEPTANCE ⑥ 的跨实现比对装置**：D-NC016-02 禁止 reading-notes 依赖 xuan-storage，而 ⑥ 要求 `decideAuthorization` 与 STORAGE guard 对 200 组随机参数「完全一致」；契约未给同一种子/参数的共享方式。请裁决具体 harness（两侧各自输出规范化判定行、主 Agent diff），否则该条不可机械执行。
- **C4 三层删除的执行落位**：TASKS 242 行④「中转对象删除三层」在 16a 仅以常量 + S03（`deletion_layers.json`）体现，执行逻辑随「中转」隐含归 16b；`ACT.yaml DEFERRED` 未逐字列出，请确认是否需要显式登记给 16b。

### 审查证据索引
- 守卫实跑：`bash docs/blackbox-spec-rework/reviews/nc016a_guard.sh` → K01～K04 全 PASS，失败 0（K05/K06 SKIP 属无 `--require-impl`）。
- 参考值复算：`/private/tmp/nc016r/recompute.py`（14/14 吻合）。
- 外键复现：`/private/tmp/nc016r/fk_check.py`（contract order → `FOREIGN KEY constraint failed`；createNote order → ok）。
- 关键行号：`xuan-storage/core/lib/sync/same_account_im_reconciliation.dart:26`；`core/lib/model/blob_cipher.dart`（`encryptChunk`/`decryptChunk`）；`reading-notes/lib/src/persistence/note_database.dart:41`；`lib/src/domain/limits.dart`（`noteMarkdownMaxBytes=1048576`）；`cryptography-2.9.0/lib/src/dart/x25519.dart:54,64`；`lib/src/dart/ed25519.dart:34`；`lib/src/cryptography/key_exchange_algorithm.dart:135`；`lib/src/cryptography/algorithms.dart:391,1281,1304,2220`。

---

## R2 复核（2026-09-12）

主 Agent 已按 R1 逐项修改；本复核只判「是否达到 R1 修正标准 + 是否引入新歧义」，未改 ACT/契约/验收标准。**结论：READY，返工 0 项。**

### 返工项复核

- **返工项 1（契约 §5 第⑤步外键顺序）— 达标。** `private_sync_impl.md:117` 已改为事务内依次「插入 `note_revisions` → 笔记不存在时插入 `notes`（`preferred_head_id=revision.id`）→ `note_heads` 删父/插新」，并显式注明「外键 `notes.preferred_head_id REFERENCES note_revisions(id)` 已开启，顺序同既有 `createNote`」。与 `local-persistence.md` §5.1 及 `createNote` 一致，`fk_check.py` 的「revision-first → ok」路径成立。**修正标准达成，无新歧义。**
- **返工项 2（多块信封不可达）— 达标。** `private_sync_impl.md:161` 接收器构造新增 `@visibleForTesting int maxInlineBytes = maxInlinePayloadBytes`（显式注明「只供盲测构造多块信封以到达第 3 步，生产装配不得传入」），`:168` 第 0 步改用 `payload.length > maxInlineBytes`；`ACCEPTANCE.md` ② 改为「以 `PrivateNoteSyncReceiver(maxInlineBytes: 8 * 1048576, …)` 接收：原信封 `accept`（另建新接收仓库）；交换两块顺序、删除末块，均 `reject:aad_mismatch`」。默认值仍是 `maxInlinePayloadBytes=262144`，故 S14 与 `envelope_oversize_inline` 语义不变；升限后第 3 步可达，换序/删末块按 `aad_i`/帧完整性归 `reject:aad_mismatch` 亦与 §6.3 第 3 行一致。**修正标准达成，无新歧义**（② 隐含复用 ① 的同一 `ReceiverSession`，属 `seal`/`receive` 的自然构造，不构成二义）。
- **A1（entityType 策略断言）— 达标。** 契约 `:187` S03 增加「`privateSyncEntityPolicies` 恰两键、两 entityType 不同，且分别为 `'private'`、`'shared'`」；`BDD.md` S03 Then 增加「两个 entityType 分别为 private/shared」。与 §4 常量定义自洽。
- **A2（S11 构造歧义）— 达标。** 契约 `:195` S11 改写为「dev_b 的接收器 `openSession` 得 offer 与 `ReceiverSession`，发送端据此 `seal` 给 dev_b；另建 `signer.deviceId=dev_c` 的接收器（目录同样信任发送端），把**同一个** `ReceiverSession` 对象传入其 `receive`」，并注明「不需替身验签」；`BDD.md` S11 同步。复推：dev_b 签名对 `recipientDeviceId=dev_b` 成立 → seal 成功；dev_c 侧第 0/1/2 步通过，第 3 步 AAD 以 `dev_c` 组 → 认证失败 → `reject:aad_mismatch`（若解包即失败亦归同一码）。**构造唯一且可行，歧义消除。**
- **A3（伪代码类型）— 达标。** §6.2 第 4 步 `:154` 改为 `secretKey: SecretKey(dek)`。参考值不受影响（AES-GCM 输出与密钥封装方式无关；R1 复算值仍成立）。
- **C1（NC-017 头部）— 达标。** `nc-017/ACCEPTANCE.md:3` 已订正为「当前：`ACCEPTED`（2026-09-12 主 Agent 验收 R1，见文末）」，与 R1 记录及 `nc-017/README.md`、`nc-017/ACT.yaml` 一致。NC-016a 派发前置「NC-017 ACCEPTED」现为真。
- **C2（`sent→pending` 语义）— 达标。** 契约 `:119` 已写明该边为「发送端超时未获 ACK 后退回重发，扩展 local-persistence §4 的状态推进，审查 R1 待裁决 C2 确认」。S06 断言不变。
- **C3（ACCEPTANCE ⑥ 装置）— 达标。** `ACCEPTANCE.md` ⑥ 已写死：Python `random.Random(20260912)` 生成 200 组写入 scratch 下 `nc016a_auth_cases.json`；reading-notes 与 STORAGE worktree(core) 各一临时 Dart 测试经环境变量读该文件、逐行输出 `<序号> <判定名>`；两份结果与 Python 按 §3.1 八步独立计算的第三份逐行 `diff` 为空。机制自洽、可机械执行，且不违反 D-NC016-02（两侧各自进程内跑，无跨包依赖）。
- **C4（三层删除落位）— 达标。** `ACT.yaml DEFERRED` 新增「中转对象三层删除的执行…：NC-016b；16a 只落常量与 `deletion_layers.json` 断言（审查 R1 待裁决 C4）」。

### 新歧义/回归扫描

- 守卫复跑：`bash docs/blackbox-spec-rework/reviews/nc016a_guard.sh`（无参）→ K01～K04 全 PASS、失败 0（K05/K06 SKIP 属无 `--require-impl`）；K02 的 14 参考值/3+17 测试名/D-NC016-01～13/十节、K03 的 BDD X01～X03+S01～S17、ESTIMATE 30–60、依赖链、ON_FAIL/WORKLOAD、模糊词 0 命中、TDD 测试名与计数（+2/+4/+3/+6/+17/+259/+270）均仍成立。
- 计数与依赖链未被改动：act/01=45、act/02=55、act/03=60；`DEPENDS_ON` 仍 `[]/[]/[NC-016a-B]`；`ORDER` 与 `DISPATCH_PRECONDITION` 不变。
- `maxInlineBytes` 新参数：`@visibleForTesting` 由 `package:flutter/foundation.dart`（经 `package:meta`）提供，reading-notes 已用 `@immutable`，**不引入新依赖**；默认值为 const `maxInlinePayloadBytes`，构造默认参数合法。
- 模糊词/新增词扫描：`适当|优雅|合理|必要时|酌情|尽量|大致|视情况` 命中 0（守卫 K03 亲验）；扩展扫出的 `可能` 仅见于 `D-NC016-04` 既有决定理由（「宿主可能接任一侧」），非执行步骤，R1 即存在，不构成对执行者的模糊指令。
- 未发现 R2 改动与 `private_sync.md`、`local-persistence.md`、`private_export.md`、TASKS/DESIGN 的新冲突。

### R2 判定

R1 两条返工项与全部建议/待裁决项（A1、A2、A3、C1～C4）均已闭合，未引入新歧义，守卫全绿。**判定：READY，K=3 个 ACT 可开工**（ACT NC-016a-A/‑B/‑C，两线并行，CLIENT 串行且与其他 reading-notes 任务不并行）。A4、A5（非阻断建议）未改，保留。
