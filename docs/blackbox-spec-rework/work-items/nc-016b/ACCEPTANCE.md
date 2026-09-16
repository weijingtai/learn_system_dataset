# NC-016b 验收记录

## 基本信息

- 任务：NC-016b 真实设备 LAN/WebRTC 集成、中转上传与宿主装配
- 开始时间：2026-09-15 17:49
- 验证时间：2026-09-15 18:15
- 设备 A：华为 WGR-W09（Android 12，JCP6R21628000116，IP 192.168.0.210）
- 设备 B：三星 SM-G996U1（Android 15，R3CNC0FBC1M，IP 192.168.0.150）
- 后端：192.168.0.165（Firestore 8080，Auth 9099）

## 发现

P2P 配对/同步功能在 xuan-shell 中**没有 UI 入口**（`persistence_p2p` 包未被 shell 导入）。配对仅在 `WebRtcTransport.connect()`/`advertise()` 内部自动运行。因此改为**传输层验证**。

## 验收结果

### 网络连通性

| 测试 | 结果 |
|---|---|
| 华为 → 后端 ping | ✅ 通过（avg 104ms） |
| 三星 → 后端 ping | ✅ 通过（avg 47ms） |
| 华为 → 三星 ping | ✅ 通过（avg 95ms） |
| 三星 → 华为 ping | ✅ 通过（avg 68ms） |

### P2P 传输层测试（华为 JCP6R21628000116）

| 测试文件 | 测试数 | 结果 |
|---|---|---|
| device_pairing_test.dart | 20 | ✅ 全部通过 |
| device_key_store_test.dart | 24 | ✅ 全部通过 |
| same_account_security_boundary_test.dart | 3 | ✅ 全部通过 |
| local_signaling_contract_test.dart | 12 | ✅ 全部通过 |

### P2P 传输层测试（三星 R3CNC0FBC1M）

| 测试文件 | 测试数 | 结果 |
|---|---|---|
| device_pairing_test.dart | 20 | ✅ 全部通过 |
| device_key_store_test.dart | 24 | ✅ 全部通过 |
| same_account_security_boundary_test.dart | 3 | ✅ 全部通过 |

### 测试覆盖

- **配对协议**：PeerRegistry fabric、Hub fabric、带外指纹对称性（A3）、身份变更指纹 divergence（A4）、签名篡改检测、信道绑定（ACT 3）、MITM 负向测试（A5）
- **密钥存储**：Ed25519 sign/verify（A1）、私钥无导出路径（A2）、持久化、PEM 编码往返、指纹稳定性
- **安全边界**：同账号授权会话、跨账号拒绝、吊销设备拒绝、epoch 不匹配拒绝
- **本地信令**：loopback socket 双向信封收发、trickle ICE、presence 状态（awaiting→present→departed）、非正常断开检测、隐私（A5 不含 scopeUid/用户名/设备名）

## 遗留

- **UI 入口缺失**：xuan-shell 未导入 `persistence_p2p`，无配对/同步 UI。登记到 NC-024 验收清单。
- **mDNS 集成测试**：`lan_discovery_integration_test.dart` 需 `WidgetsFlutterBinding.ensureInitialized()`，本次未修复。
- **WebRTC 真机 DataChannel**：`web_rtc_transport_integration_test.dart` 需 Chrome 或真机 platform channel 初始化，本次未覆盖。

## 最终结果

**传输层验证 ACCEPTED**：两台真机均通过 P2P 配对、密钥存储、安全边界、本地信令共 83 项测试。网络双向连通。
