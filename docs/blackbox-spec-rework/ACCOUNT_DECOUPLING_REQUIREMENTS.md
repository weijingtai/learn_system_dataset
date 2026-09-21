# Account 解耦需求文档：注解社区线需要的接口与信息

状态：`DRAFT`；2026-09-14
用途：转交 Account 解耦 AI Agent，明确注解社区（NC）线需要 Account 后端提供的接口与信息

## 1. 背景

注解社区（NC）线有 5 个任务因 Account 后端未就绪而 BLOCKED：

| 任务 | 依赖 Account 的原因 |
|---|---|
| NC-001-02 | 设备/后端/Emulator 联调取证——需要真实 Account 后端 + 设备表 |
| NC-012b | 宿主社交注入——需要 Account 认证身份 |
| NC-016b | 两台真实设备 LAN/WebRTC 集成——需要 Account 会话 |
| NC-025 | 生产 BlobGateway——需要 Account 认证的上传通道 |
| NC-008 | 本地图片与公共资源适配——依赖 NC-025 |

**解除条件**：Account 后端/前端可供联调 + Firebase 去留口径明确。

## 2. 注解社区线需要的 Account 接口

### 2.1 认证相关（最小集）

| 接口 | 用途 | 当前状态 |
|---|---|---|
| `signInAnonymously()` | 匿名登录（社区浏览无需实名） | v2 已定义 |
| `signInWithEmailPassword()` | 邮箱登录 | v2 已定义 |
| `signOut()` | 登出 | v2 已定义 |
| `currentAccessToken()` | 获取当前 token（调用 REST API 必需） | v2 已定义 |
| `sessionChanges` | 监听会话变化（切换账号时刷新数据） | v2 已定义 |

### 2.2 身份解析

| 接口 | 用途 | 当前状态 |
|---|---|---|
| `AppUserIdResolver.resolve()` | 获取当前用户的 `app_user_id`（无参数，会话驱动） | v2 已定义 |
| `GET /v1/me` | 服务端返回当前用户信息（JWT sub = app_user_id） | 已实现（account_http） |

### 2.3 REST API 基址

| 项目 | 值 | 说明 |
|---|---|---|
| Account 服务基址 | `http://192.168.0.165:8081` | 本地开发环境 |
| REST API 基址 | `http://192.168.0.165:8082` | 注解社区 REST 服务 |
| Firestore Emulator | `192.168.0.165:8080` | 规则测试 |
| Auth Emulator | `192.168.0.165:9099` | 认证测试 |

## 3. 注解社区线需要的信息

### 3.1 设备表（NC-001-02 必需）

NC-001-02 需要一份设备表，包含：
- 设备 ID
- 设备类型（iOS/Android/Web）
- Flutter 版本
- 操作系统版本
- 是否支持 WebRTC
- 是否支持本地存储

**问题**：这份设备表是否已由 Account 线维护？格式是什么？

### 3.2 Firebase 去留口径

以下问题需要明确：
1. 新 Account 后端是否完全替代 Firebase Auth？
2. Firestore 是否保留？如果保留，哪些集合继续使用？
3. 现有 `192.168.0.165:8080/9099` Emulator 是否继续工作？
4. 新 Account 后端的认证流程是什么？（JWT？Session？）

### 3.3 端口装配方式

Account v2 的 `AccountDependencies` 注入包如何装配到注解社区的宿主中？
- `xuan-shell` 的 `shell_account_bootstrap.dart` 是否是参考实现？
- 注解社区宿主（`reading-notes`）需要如何接入？

## 4. 注解社区线可以提供的接口

### 4.1 REST API（`repository-rest-adapter`）

| 端点 | 方法 | 用途 |
|---|---|---|
| `/v1/notes` | GET/POST | 笔记 CRUD |
| `/v1/comments` | GET/POST | 评论 CRUD |
| `/v1/interactions` | GET/POST | 赞踩/收藏/分享 |
| `/v1/notifications` | GET | 通知列表 |
| `/v1/analytics/events` | POST | 行为事件上报 |
| `/v1/analytics/pseudonym` | GET | 假名查询 |

### 4.2 Firestore 集合（规则测试）

已定义的集合：
- `community_content_access`
- `community_publications`
- `community_commands`
- `community_behavior_events`
- `community_comments`
- `community_threads`
- `community_reactions`
- `community_bookmarks`
- `community_notifications`

## 5. 建议的联调顺序

1. **Account 后端提供 JWT 验证接口**（REST API 可以验证 token）
2. **注解社区 REST 服务接入 Account JWT 验证**（`repository-rest-adapter`）
3. **提供设备表或等价配置**
4. **Firebase 去留口径明确后，更新 Firestore 规则**
5. **NC-001-02 开始联调**

## 6. 待 Account Agent 回复

1. 新 Account 后端的 JWT 验证接口是否已就绪？
2. 设备表格式和内容是什么？
3. Firebase 去留的最终决定是什么？
4. `AccountDependencies` 注入包如何装配到非 `xuan-shell` 宿主？
5. 有哪些已知的接口变更需要注解社区线适配？

---

本文档可由用户转交 Account 解耦 AI Agent；没有自动发送消息。回复请引用本节编号。
