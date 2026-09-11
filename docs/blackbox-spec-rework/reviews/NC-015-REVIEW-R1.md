# NC-015 转译审查记录

## R1（2026-09-11，Sonnet 四查 + 十二攻击/故障场景；对象 `fa15e43`）：返工 5 项（契约级）
通过：guard 判定顺序与「只收不比较」属实；`TIMPeerAuthorization`/`PairingResult` 字段与契约一致；cipher 无 AAD 属实；notifier 端点存在；BDD↔TDD↔样例映射完整；负路径可经 `--contract/--fixtures` 注入；路径/Python/守卫/估时/模糊词均通过；D-NC015-04、D-NC015-07 不冲突。
返工：① `accountBindingCertHash` 来源标注失实（S6 §3.1 无该概念，PairingResult 不产出）；② notifier 只有全局 24h TTL 且仓库只读，契约要求 300 秒落不了地；③ 被签名字段是否含 `content_hash` 未定义，`hash_mismatch` 样例会被签名校验抢先；④ 原因码缺 AAD/GCM 认证失败；⑤ 中转路径接收端会话公钥无认证绑定（MITM 可替换）。场景表：①⑧⑨为缺口，③⑩为归因/样例缺口，其余有防线。

## R1 落实（主 Agent，同日）
① D-NC015-08：该字段定义为 `SHA-256(app_user_id|peerDeviceId|peerPublicKeyFingerprint)` 本机计算；② D-NC015-01 修订：密文一律走 Storage `private/p2p/`（S6 原设计），notifier 只做 S6 步骤③信令（不含密文，包装 DEK 随会话私钥作废），发送端兜底 300 秒；③ §4.4 明列 `signed_fields` 十字段（含 `content_hash`），§6 固定顺序并改写两个样例语义（`hash_mismatch` 用 `decrypted_content_hash` 探针，`bad_signature` 改被签名字段）；④ 新增 `reject:aad_mismatch` 与样例；⑤ D-NC015-09：会话公钥带设备 Ed25519 签名，发送端验签后才包装，新增 `session_key_unbound` 与样例；另补匿名配对拦截样例 `pairing_refused_anonymous`、§1 交叉引用 R-13、ACCEPTANCE 的 NC-016 交接提醒。样例 15 → 18，自测 ≥15，守卫同步。待 R2。

## R2（2026-09-11，Sonnet；对象 `6ef2b5b`）：返工 1 项
R1 五项全部核实落地（逐条给出文件:行）；另核六项通过；十二场景重跑无遗留缺口；守卫 0；模糊词零命中。唯一缺口：`auth_valid.json` 的 `accountBindingCertHash`「按 D-NC015-08 计算」无任何测试复算（只查字段存在）。
## R2 落实（主 Agent，同日）
契约 §8 新增红条件（用 `peer_auth` 三字段 `hashlib.sha256` 复算不等即退出 1）；TDD/act02 测试清单增 `account_binding_cert_hash_matches_formula`（16 个）；BDD B02 与 ACCEPTANCE ⑦ 同步；守卫 K05 增加证书哈希篡改副本断言。判定：READY，2 个 ACT 可开工。
