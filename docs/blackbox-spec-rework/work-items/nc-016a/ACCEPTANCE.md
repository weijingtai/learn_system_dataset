# NC-016a 独立验收

当前：**ACCEPTED**（2026-09-12 R1，见文末「验收记录 R1」）。派发前置：NC-004、NC-007、NC-015、NC-017 ACCEPTED；wjt-react 四查 READY。

1. ACT 审查：未参与编写者做 wjt-react 四查（`reviews/NC-016a-REVIEW-R1.md`）。
2. 范围（`git diff-tree -r --name-only`）：STORAGE 分支 `fix/nc016-guard-aad` 在 `8ddb877` 之后恰 1 个提交、只含契约 §2.1 文件，`main` 仍为 `8ddb877`；CLIENT 在 `4a0d70a` 之后恰 2 个提交、只含 §2.2 文件，`note_repository.dart` 删除行数为 0；12 个样例副本与 learn_system 原件 SHA-256 相同。
3. 重跑 TDD §1 全部命令（经 tmux 执行器只运行，主 Agent 读原始输出判定）；`nc016a_guard.sh --require-impl all` 为 0。
4. 主 Agent 盲测（临时文件执行后删除，工作树恢复干净）：
   - ① 用 pyca 独立解开 Dart `seal` 产出的一个**多块**（明文 > 1 MiB，经 relay 以外的测试入口构造，不走内联上限）信封：按契约 §6.2 复算 wrap_key、解包 DEK、逐块解密与签名验证。
   - ② 用 ① 的多块信封，以 `PrivateNoteSyncReceiver(maxInlineBytes: 8 * 1048576, …)` 接收：原信封 `accept`（另建新接收仓库）；交换 payload 中两块顺序、删除末块，均 `reject:aad_mismatch`（审查 R1 返工项 2）。
   - ③ `SealedEnvelope.toJson` → `fromJson` 往返后 `receive` 仍 `accept`。
   - ④ 旧会话代数的仓储调用 `applyRemoteRevision` → `StaleSessionError`，零写入。
   - ⑤ STORAGE worktree 内 `core`、`drift`、`p2p` 三包 `flutter analyze` 的问题数与改动前相同。
   - ⑥ 主 Agent 用 Python（`random.Random(20260912)`）生成 200 组 guard 参数写入 scratch 下 `nc016a_auth_cases.json`；reading-notes 与 STORAGE worktree（core）各放一个临时 Dart 测试，经环境变量读取该文件，逐行输出 `<序号> <判定名>` 到各自结果文件；两份结果与 Python 按契约 §3.1 八步独立计算的第三份逐行 `diff` 均为空（审查 R1 待裁决 C3）。
5. 作弊扫描：测试无 `skip`、永真断言；§9 参考值为字面量；S09～S17 使用真实 Ed25519/X25519 密钥（非替身签名）；S14 断言未调用验签；无真实网络。
6. 通过后：NC-016a `ACCEPTED`；NC-016b 仍 `BLOCKED`；NC-018 解锁条件之一（NC-016）按 16a 交付裁定。

## 验收记录 R1（2026-09-12，主 Agent）

结论：**ACCEPTED**。执行方自述未采信，以下均为 git 与原始输出核对结果。

1. **ACT 审查**：`reviews/NC-016a-REVIEW-R1.md`，R1 返工 2 项、R2 READY。执行中两次裁定：STORAGE 建树超时（半成品改名 `.worktrees/nc016-guard-aad.partial-20260912`，主 Agent 以既有分支重建）；既有测试到期占位值 D-NC016-14（`c791d94`）。
2. **范围**：
   - STORAGE：分支 `fix/nc016-guard-aad` 在 `8ddb877` 之后恰 1 个提交 `755a8fc`，`main` 仍为 `8ddb877`；`diff-tree` 17 个文件均在契约 §2.1 内（含 D-NC016-14 两个既有测试各 1 增 1 删）。
   - CLIENT：`4a0d70a` 之后恰 2 个提交 `a9a9621`、`d80703b`，17 个文件均在 §2.2 内；`note_repository.dart` `+127 -0`；`reading_notes.dart` `+2 -0`。
3. **守卫**：`nc016a_guard.sh --require-impl all` 退出 0，K01～K06 全部 PASS（K05 flutter test ≥270、analyze 0；K06 core +2/+4、p2p +3、drift +1、样例逐字节）。
4. **盲测**（临时文件经 `scratchpad/nc016a_blind/run_blind.sh` 复制、运行后立即删除；RN 与 STORAGE worktree 前后 `git status --short` 均为空）：
   - ① pyca 独立解开 Dart `seal` 的两块信封（明文 1049103 B，markdown 1048576 B）：HKDF 派生 wrap_key 解包 DEK、两块逐块 AES-GCM 解密（1048592 B、543 B）、明文 SHA-256 与 Dart `encodeSyncPayload` 一致、Ed25519 签名验证通过。
   - ② `maxInlineBytes: 8 MiB` 接收端：交换两块顺序、删除末块均 `reject:aad_mismatch` 且零写入；原信封在新接收仓库 `accept`；缺省上限接收端 `reject:schema_invalid`。
   - ③ `toJson` → JSON 文本 → `fromJson` 往返后 `toJson` 相等，新仓库 `accept`。
   - ④ `retireSession()` 后旧代数仓储 `applyRemoteRevision` 抛 `StaleSessionError`，重开文件库三表 0 行。
   - ⑤ STORAGE worktree 三包 `flutter analyze`：core 1502、drift 286、p2p 1 个问题；命中本分支改动文件的仅 `same_account_im_reconciliation.dart:3:8 unused_import`，该 import 在 `8ddb877` 已存在且本分支对该文件只增不删，非本补丁引入。判据说明：主检出未 `pub get`，为不污染 `main` 工作区，未直接测改动前总数，以「改动文件无新增问题」代替。
   - ⑥ `random.Random(20260912)` 生成 200 组参数（六种判定均覆盖：authorized 10、deniedScopeMismatch 52、deniedDtlsMismatch 20、deniedBadSignature 32、deniedEpochMismatch 30、deniedRevokedOrUntrusted 56）；Python 按 `8ddb877` 五步 + 契约 §3.1 三步独立计算，与 CLIENT `decideAuthorization`、STORAGE `verifyPeerSession` 两份结果逐行 `diff` 均为空（两个临时 Dart 测试以 scratch 绝对路径常量读取参数文件，替代原定的环境变量传参，读取内容相同）。
5. **作弊扫描**：三个测试文件无 `skip`、永真断言、真实网络；§9 参考值为字面量；S09～S17 使用真实 Ed25519/X25519 密钥（`TestDeviceSigner` 包装真实 `Ed25519().sign`）；S14 以 `ThrowingSignatureVerifier` 证明第 0 步未调用验签；S16 断言 `randomBytes` 调用次数。

**后续**：NC-016b 仍 `BLOCKED`（NC-001 设备表）。STORAGE 分支 `fix/nc016-guard-aad` 未合并，合并由仓库所有者决定；`.worktrees/nc016-guard-aad.partial-20260912` 为超时残留，可由用户删除。
