# NC-016b：真实设备 LAN/WebRTC 集成、中转上传与宿主装配

状态：`PREPARING`（2026-09-15，设备已连接，开始执行）

## Goal

在两台真实设备上验证私人同步的完整链路：
1. LAN 直连同步（同一局域网内设备发现与数据传输）
2. WebRTC 信令与中转上传（跨网络设备通过中转服务器同步）
3. Notifier 信令通道（配对请求、会话密钥交换）
4. 宿主装配（接收端数据解密与本地存储写入）
5. SyncRuntime entityType 注册（同步实体类型在运行时注册）

## Scope

- 设备：华为 WGR-W09（Android 12，设备 ID `JCP6R21628000116`）+ 模拟器（Android 14，设备 ID `emulator-5554`）
- 仓库：reading-notes（客户端）、functions-py（服务端）、xuan-storage（存储层）
- 禁止：修改生产环境配置、删除用户数据、绕过认证

## Dependencies / Baseline

| 项 | 状态 | 说明 |
|---|---|---|
| NC-016a | ACCEPTED | 进程内实现与单元/组件测试已完成 |
| NC-001-02 | ACCEPTED | 联调取证完成，设备表已更新 |
| 真实设备 | CONNECTED | 华为 WGR-W09 已通过 ADB 连接 |
| Account JWT | INTEGRATED | functions-py 已集成 authkit_py |

## Stop Conditions

- 设备未连接或认证失败
- LAN 发现超时（30 秒内未找到对端）
- WebRTC 信令通道建立失败
- 数据解密失败（密钥不匹配）
- 既有测试变红

## 执行顺序

1. **act/01**：设备发现与配对（LAN）
2. **act/02**：会话密钥交换与数据加密传输
3. **act/03**：中转上传与 WebRTC 信令
4. **act/04**：接收端解密与宿主装配
5. **act/05**：SyncRuntime entityType 注册验证

## 验收标准

- 两台设备能发现彼此并完成配对
- 数据能在设备间加密传输
- 中转服务器能正确转发信令
- 接收端能解密并存储数据
- 所有既有测试保持通过
