# NC-016a 可观察行为

ID 与契约 `private_sync_impl.md` §3.3（X）、§8（S）一一对应，期望逐字以契约为准。CLIENT 测试用临时目录真实 Drift 文件库与真实 Ed25519/X25519 密钥；STORAGE 测试在 worktree 内运行。

## STORAGE

| ID | Given | When | Then |
|---|---|---|---|
| X01 | 8 个 `auth_*.json` | 以样例字段调用 `verifyPeerSession(..., nowUtcMs:)` | 决定名等于 `expected` |
| X02 | 设备 ID/指纹/过期多项同时不符的授权 | 调用 guard | 第 6 步先于第 7 步先于第 8 步；`now == expiresAt` 视为过期 |
| X03 | AES-GCM cipher | 同/异 AAD、缺省 AAD 往返 | 同 AAD 与双缺省成功；异 AAD 或单侧缺省抛 `BlobUndecryptableError` |

## CLIENT

| ID | Given | When | Then |
|---|---|---|---|
| S01 | 8 个 `auth_*.json` 副本 | `decideAuthorization` | 决定名等于 `expected` |
| S02 | `auth_valid.json` 三字段 | `accountBindingCertHash` | 等于 `c2d5f307…0504` |
| S03 | `pairing_anonymous.json`、`relay_ttl.json`、`deletion_layers.json` | 调用 `pairingGate` 并读常量 | 匿名拒绝码；三常量等于样例；删除分层样例 `layers_ok` |
| S04 | 本机无该笔记 | 应用远端首条修订，再应用两条同父修订，再重复应用 | 建笔记；两个头、preferred 为先到者；outbox 不变；重复返回 `duplicate` |
| S05 | 父修订缺失 / 头表插入被拦截失败 | `applyRemoteRevision` | `RemoteParentMissing` 且零写入 / `SaveFailed` 且回滚 |
| S06 | outbox 行 | `markEnvelope` 各转移 | 只允许 pending→sent→acked 与 sent→pending |
| S07 | 含独特标题与正文的修订 | `seal` 后检查 JSON 字节与 payload | 不含标题、正文片段、修改说明 |
| S08 | 契约 §9 固定输入 | 计算签名摘要、密钥、包装、首块 | 全部等于参考值 |
| S09 | 发送与接收两个仓库，真实密钥 | `openSession` → `seal` → `receive` | `accept`，修订 13 字段一致 |
| S10 | 合法信封 | 比较签名字段并改 `contentHash` 一位 | 字段表等于样例；`reject:bad_signature` |
| S11 | 发给 dev_b 的信封 | dev_c 接收 | `reject:aad_mismatch` |
| S12 | 发送端修订被写成错误 content_hash | `seal` 后接收 | `reject:hash_mismatch` |
| S13 | 已接收的信封 | 再次接收 | `duplicate_ack`，零写入 |
| S14 | 明文 > 262144 字节 | 接收 | `reject:schema_invalid`，未调用验签 |
| S15 | 目录无记录/revoked/到期/epoch 2 | 接收 | 各 `reject:source_untrusted` |
| S16 | 会话公钥签名被改一位 | `seal` | 抛 `SessionKeyUnbound`，未取随机数 |
| S17 | A、B 从同一修订各自保存 | 分别发往 C | C 两次 `accept`，恰 2 个头 |
