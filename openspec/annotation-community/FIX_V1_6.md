# FIX_V1_6：私人数据保护改为 xuan-storage S6 模型（2026-09-11，用户确认）

## 1. 决定

| 编号 | 决定 | 依据 |
|---|---|---|
| V16-01 | 私人数据保护采用 xuan-storage S6 已生效裁决：直连 DTLS 临时密钥、中转一次一密（临时 X25519 + HKDF 包装 DEK）、同步完即删（接收端主删 / 发送端兜底 / 存储生命周期 1 天）、双方在线、无长期云端密文、无长期密钥 | `xuan-storage/docs/superpowers/specs/2026-08-02-s6-p2p-sync-third-party-design.md` D1/D9/D13～D21、§4.0～§4.2；用户 2026-09-11 两次口述「绕过保存密钥」 |
| V16-02 | 不做恢复材料、密钥轮换、escrow、口令派生长期密钥；设备全丢且无导出文件即数据丢失，产品明示 | S6 D13、D14；`docs/plans/2026-08-17-e2ee-key-envelope-plan.md` 已作废 |
| V16-03 | R-13 由「加密云备份」改为「手动导出与导入」：口令加密的本机文件，口令不保存；导入到另一设备 | S6 §四「单设备用户由 S3a 手动导出兜底」 |
| V16-04 | PRD §6.1 第三维度由「云备份」改为「导出备份」；NC-005 已交付的 `CloudBackupStatus` 由 NC-018 迁移 | 避免返工已验收产物；NC-018 白名单含该三文件 |
| V16-05 | NC-015 改为接入型（契约 `contracts/private_sync.md` 待写）；NC-017 改为导出文件格式；NC-018 改为导出/导入 UI；NC-017 退出 openapi/conftest/config 串行链；NC-019 去掉「备份清理」 | TASKS/PLANS 相应改写 |
| V16-06 | `CommandRecord.operation` 的 backup.* 三值保留为枚举值，本期无端点 | 避免改动 NC-002 冻结 Schema 与 fixture；NC-003 D-NC003-09 |
| V16-07 | 旧守卫放宽：`review_v1_5_guard.sh` V09 接受版本 1.5～1.9；`review_r2_guard.sh` RW-4 接受「NC-017 依赖 NC-015 且为导出文件」；`nc005_guard.sh` K02 只核 PRD 前 8 个文案 | 守卫属规格线文件，改动在此登记 |

## 2. 受影响文档

PRD（§1、§2、§3 R-13/R-14、§3.1、§4、§4.1 A11Y-04、§5、§5.1、§6 旅程 1/7/8、§6.1、§6.3、§6.4 PARTIAL、§8 E-CRYPTO、§9）；DESIGN（§1 图、§2 BackupManifest、§5、§7 表、§7.4 表、§10 依赖表）；TASKS（总表 NC-015/017/018 与四节）；PLANS（Goal、仓库表、串行链、P4、§6、§7）；contracts/community-models §3.2/§4、state-machines SM-3、editor.md §3、community_api §2/§9；nc-003 ACT.yaml。

## 2.1 勘误（NC-003 R1 审查发现）

- REST 仓 `openapi/openapi.yaml` 非法 operation 级 `headers:` 为 **22 个 operation（全部）**，非 35（原计数把 response 级与 components 级一并算入）；既有 `test/openapi_validation_test.dart` 要求该非法形式的断言为 **14 行、12 个测试块**，非 8 处。DESIGN §7.4、TASKS NC-003、NC-003 六件套已同步。

## 3. 未变

R-12 设备同步语义；NC-016 目标（加密 mapper 与双设备同步）；NC-002 Schema 与 fixture；NC-004～NC-007 产物。

## 4. 待办

- NC-015 契约 `private_sync.md` 与六件套（本次未写）。
- NC-018 派发时迁移 `CloudBackupStatus`。
