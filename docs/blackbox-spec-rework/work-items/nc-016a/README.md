# NC-016a：私人同步实现——guard 补丁、AES-GCM AAD、一次一密信封与接收验收

状态：`READY`（2026-09-12：cmd（deepseek-v4.1-flash）四查 R1 返工 2 项（外键顺序、盲测入口）+ 建议与待裁决，R2 READY，见 `reviews/NC-016a-REVIEW-R1.md`）。派发前置：NC-004、NC-007、NC-015、NC-017 均 `ACCEPTED`（已满足）。task_id：`NC-016a`。NC-016b（两台真实设备 LAN/WebRTC 集成、中转上传、宿主装配）`BLOCKED`，等 NC-001 设备表（D-NC016-01）。权威需求来源：TASKS NC-016；契约 `contracts/private_sync_impl.md`（本任务专属）与 `contracts/private_sync.md`（含 §10）。

## Goal

两条线交付 S6 私人同步的进程内实现：STORAGE 在功能分支上给 `SameAccountSessionGuard` 补上设备 ID、指纹、过期三条实际比较，并给 `BlobCipher` 接口加可选 AAD；CLIENT 在 reading-notes 实现 mapper、授权判定、一次一密封装（X25519 + HKDF + 分块 AES-GCM）、Ed25519 信封签名、接收端七步验收与 `NoteRepository.applyRemoteRevision`，以真实密钥测试与 pyca 参考值核对。执行者不做设计。

## Scope

- STORAGE：xuan-storage worktree `.worktrees/nc016-guard-aad`（分支 `fix/nc016-guard-aad`，基于 `8ddb877`），契约 §2.1 白名单；**不合并、不 push**。
- CLIENT：reading-notes `main`，契约 §2.2 白名单。
- 禁止：白名单外任何文件；pubspec 变更与新依赖；改既有测试期望；`skip`；永真断言；测试内生成参考值；先实现后补测试；`git push`；删除文件。

## Dependencies / Baseline（2026-09-12 实测）

| 线 | HEAD | 基线 |
|---|---|---|
| STORAGE | `main` `8ddb877` | 临时副本 `pub get` 三包 0；core `same_account_im_reconciliation_test.dart` `+4`；p2p `same_account_security_boundary_test.dart` `+3`；drift `aes_gcm_blob_cipher_test.dart` `+10` |
| CLIENT | `main` `4a0d70a` | `flutter test` `+253`；`flutter analyze` 0 |

共享守卫：`bash docs/blackbox-spec-rework/reviews/nc016a_guard.sh [--require-impl client|storage|all]`（learn_system 内，只读）。

## Stop Conditions

契约两种解释；参考值（§9）按契约实现后对不上（含 Dart `newKeyPairFromSeed` 与 pyca 不一致）；需改白名单外文件；既有测试变红；STORAGE worktree 内 `flutter pub get` 失败或需改 `pubspec.yaml`；需要在 xuan-storage `main` 上操作。遇到即停：在本线交付报告追加「## 待裁决」，对话最后单独输出 `NC-016a-<A|B|C> 停手待裁决`。

## 执行顺序（两线并行）

- STORAGE：`act/01`（NC-016a-A，guard 补丁与 AAD，X01～X03）。
- CLIENT：`act/02`（NC-016a-B，mapper、授权判定、仓储追加方法，S01～S06，+253 → +259）→ `act/03`（NC-016a-C，一次一密、信封、接收验收，S07～S17，→ +270）。

交付报告写入本目录（不入库）：`DELIVERY_REPORT_STORAGE.md`、`DELIVERY_REPORT_CLIENT.md`。

## 阅读顺序

1. 本 README；2. `openspec/annotation-community/contracts/private_sync_impl.md`；3. `private_sync.md` §2～§7、§10；4. [BDD](BDD.md)、[TDD](TDD.md)；5. [ACT](ACT.yaml) 与本线 act；6. [ACCEPTANCE](ACCEPTANCE.md)；7. [PROMPT](PROMPT.md) 本线一节。
