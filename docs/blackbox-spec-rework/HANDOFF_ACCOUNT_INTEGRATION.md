# 交接：Account 集成进展（2026-09-15）

更新时间：2026-09-15

## 已完成

1. **NC-020a** ✅ 已完成并推送
   - `BOOK_CONTRACT_ACCEPTANCE.md`：28 项核对清单
   - `check_book_contract.py`：校验脚本退出 0
   - 六件套 `work-items/nc-020a/`

2. **Account 需求文档** ✅ 已提交推送
   - `ACCOUNT_DECOUPLING_REQUIREMENTS.md`

3. **Account 回复已收到**
   - `server-account/docs/account-auth/2026-09-15-learn-system-account-reply.md`
   - JWT 验签用 `authkit_py`，联调地址 `http://192.168.0.165:8081`

4. **authkit_py 集成（functions-py）** ✅ 已提交推送
   - `requirements.txt`：添加 authkit_py、PyJWT[crypto]、redis
   - `xuan/identity_account.py`：Account JWT 身份解析器
   - 提交 `950ffca`

## 待完成

1. **更新 handlers 使用 Account JWT**
   - 所有 handlers 的 `uid = require_auth_uid(uid)` 改为从 Account JWT 获取
   - 需要更新约 30 个 handlers

2. **环境变量配置**
   - `ACCOUNT_ISSUER=http://192.168.0.165:8081`
   - `ACCOUNT_AUDIENCE=xuan-api`
   - `ACCOUNT_JWKS_URL=http://192.168.0.165:8081/.well-known/jwks.json`
   - `ACCOUNT_REDIS_URL=redis://192.168.0.165:6379`
   - `ACCOUNT_INTERNAL_BASE_URL=http://192.168.0.165:8081`
   - `ACCOUNT_INTERNAL_TOKEN=<token>`

3. **NC-001-02 联调**
   - 需要设备表（NC 线自己维护）
   - Firebase Auth 被完全替代
   - Firestore 客户端直连路径废弃

4. **待用户裁决 D62**
   - Firestore 客户端直连路径是否全部废弃？
   - 建议全部经 REST 走 `authkit_py` 验签

## 解锁的任务

Account 集成完成后，以下任务可以解封：
- NC-001-02：设备/后端联调
- NC-012b：宿主社交注入
- NC-016b：真实设备集成
- NC-025：生产 BlobGateway
- NC-008：图片适配

## 关键文件

- `learn_system/docs/blackbox-spec-rework/ACCOUNT_DECOUPLING_REQUIREMENTS.md`
- `learn_system/docs/blackbox-spec-rework/ACCOUNT_INTEGRATION_PLAN.md`
- `server-account/docs/account-auth/2026-09-15-learn-system-account-reply.md`
- `server-account/authkit_py/README.md`
- `functions-py/xuan/identity_account.py`
