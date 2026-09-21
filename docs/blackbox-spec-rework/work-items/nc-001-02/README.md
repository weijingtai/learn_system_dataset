# NC-001-02 完整联调取证

状态：`IN_PROGRESS`（2026-09-15）
前置：NC-001-01 已 ACCEPTED（2026-09-11）
依赖：Account JWT 已集成（authkit_py）

## 任务目标

完成 NC-001 十项完整联调基线，将 `scope` 从 `LOCAL_PREPARATION` 升级为 `INTEGRATED`。

## 十项证据

| 项 | 证据要求 | 责任 |
|---|---|---|
| 设备 | 至少两台 device_id、平台、OS 版本、P2P 用途和探测输出 | NC-016/018 |
| 后端/账号 | project_id、隔离命名空间、两组 uid/app_user_id、凭据注入方式 | NC-001-02 |
| Emulator | 实值、启动方式、连通及隔离输出 | NC-001-02 |
| 仓库与范围 | 新鲜 HEAD、现有测试输出/数量、每仓允许写入路径 | NC-001-02 |
| OpenAPI | 安装锁、运行输出、合法/非法 3.1 文档成对结果 | NC-001-02 |
| Markdown Plus | 实际 lock、依赖解析、渲染 Widget 验证 | NC-004/005 |
| Firestore rules | 权威文件与部署依据、隔离环境规则测试 | NC-001-02 |
| 通知回跳 | 普通通知中心真实 Repository 注入及导航证据 | NC-014 |
| 静音/聚合 | 宿主支持范围、缺口和持久化/聚合测试 | NC-013/014 |
| 注销事件 | 源文件/符号、删号事件语义、送达保证、真实触发测试 | NC-001-02 |

## 执行步骤

1. 验证 OpenAPI 工具安装并运行合法/非法文档测试
2. 验证 Flutter/Dart SDK 版本与依赖
3. 运行各仓库测试并收集输出
4. 更新 integration_baseline.json 为 INTEGRATED 状态
5. 运行 check_integration_baseline.py --profile integrated
6. 提交并推送

## 输出

- 更新后的 `integration_baseline.json`
- 更新后的 `INTEGRATION_BASELINE.md`
- `check_integration_baseline.py` 输出 `INTEGRATED_STRUCTURE_PASS`
