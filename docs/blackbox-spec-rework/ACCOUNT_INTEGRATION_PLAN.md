# NC 线 Account 集成计划

状态：`IN_PROGRESS`；2026-09-15
依据：`server-account/docs/account-auth/2026-09-15-learn-system-account-reply.md`

## 1. 当前状态

Account 线已交付：
- `authkit_py`：Python 验签库，14 个用例绿
- 联调地址：`http://192.168.0.165:8081`
- JWKS：`http://192.168.0.165:8081/.well-known/jwks.json`（ES256，双 key）
- 内网回查：`GET http://192.168.0.165:8081/internal/v1/sessions/{sid}`

## 2. 集成步骤

### 2.1 添加依赖

在 `functions-py/requirements.txt` 添加：
```
authkit_py @ git+http://192.168.0.165:3000/xuan/server-account.git@codex/account-handoff#subdirectory=authkit_py
PyJWT[crypto]
redis
```

### 2.2 创建 Account 身份解析器

新文件 `xuan/identity_account.py`：
- 从 `Authorization: Bearer <token>` 头提取 token
- 用 `authkit_py.Verifier` 验签
- 返回 `principal.app_user_id`

### 2.3 更新现有身份解析器

修改 `xuan/identity.py`：
- `resolve_app_user_id(uid)` 保留向后兼容
- 新增 `resolve_app_user_id_from_account(principal)` 从 Account JWT 获取

### 2.4 更新 handlers

所有 handlers 的 `uid = require_auth_uid(uid)` 改为从 Account JWT 获取 `app_user_id`。

### 2.5 环境变量

```
ACCOUNT_ISSUER=http://192.168.0.165:8081
ACCOUNT_AUDIENCE=xuan-api
ACCOUNT_JWKS_URL=http://192.168.0.165:8081/.well-known/jwks.json
ACCOUNT_REDIS_URL=redis://192.168.0.165:6379
ACCOUNT_INTERNAL_BASE_URL=http://192.168.0.165:8081
ACCOUNT_INTERNAL_TOKEN=<token>
```

## 3. 解锁的任务

集成完成后，以下任务可以解封：
- NC-001-02：设备/后端联调
- NC-012b：宿主社交注入
- NC-016b：真实设备集成
- NC-025：生产 BlobGateway
- NC-008：图片适配

## 4. 待用户裁决

**D62**：Firestore 客户端直连路径是否全部废弃？建议全部经 REST 走 `authkit_py` 验签。
