# NC-015 独立验收

当前：`ACCEPTED`（2026-09-11，R1）。

1. ACT 审查：未参与编写者做 wjt-react 四查；另按 TASKS 要求做**攻击/故障场景审查**（契约 §3～§6 对：中间人替换会话公钥、重放旧信封、跨账号密文投递、过期授权、吊销后残留会话、中转对象未删、接收端崩溃于 ACK 前、哈希碰撞式篡改），每个场景给出契约中的对应防线或标注缺口。
2. 范围：learn_system 恰 2 个提交，只含 `fixtures/private_sync/` 18 文件与 `tools/` 两文件；契约未改。
3. 重跑 TDD §1 全部命令；`nc015_guard.sh --require-impl` 0。
4. 主 Agent 盲测（临时副本）：① 把 `envelope_valid.json` 的 `content_hash` 与 `content_hash_cases.json` 第一个 case 逐字比对；② 在契约副本删掉 `## 6.` 标题、删掉 `D-NC015-04`、插入 `待定`，检查器各自退出 1；③ 样例副本改 `expected` 为 `authorised`（拼写）退出 1；④ `relay_ttl.json` 副本把 `sender_fallback_seconds` 改 299 退出 1；⑤ 删除任一样例文件退出 1；⑥ `envelope_valid.json` 副本的 `signed_fields` 去掉 `content_hash` 退出 1；⑦ `auth_valid.json` 副本的 `accountBindingCertHash` 改一位退出 1。
4b. 交接提醒：NC-016 须自行为「匿名账号拦截」「AAD 失败」「会话公钥签名」补真实密钥测试；本任务样例为格式级。
5. 作弊扫描：自测无 `skip`、永真断言；检查器不含硬编码「通过」分支。
6. 通过后：NC-015 `ACCEPTED`，解锁 NC-016（实现）；NC-017/018 按 v1.6 准备。

---

## 验收记录 R1（主 Agent，2026-09-11）

**提交**：learn_system `2d3a366`（NC-015-A，18 个样例）、`b39d4f6`（NC-015-B，检查器与 unittest）。`git diff-tree -r --name-only` 核对：前者恰为 `fixtures/private_sync/` 下 18 个文件，文件名与契约 §7 表逐字相符；后者恰为 `tools/check_private_sync_protocol.py`、`tools/test_check_private_sync_protocol.py`；两提交均未改契约。

**命令**：清单 V0～V8 由 tmux 执行器跑完，原始输出在 `~/tmux-agents/runs/nc015v/`。agy 额度耗尽，本轮换用 cmd 执行器，清单相同。

| # | 命令 | 结果 |
|---|---|---|
| V0 | `git log` / `git status` | 头部为两执行提交之后的 `9cc7277`；工作树只有未跟踪的 `DELIVERY_REPORT.md` |
| V1 | `check_private_sync_protocol.py` | `samples=18`，EXIT=0 |
| V2 | `unittest -v` | `Ran 16 tests … OK`，EXIT=0 |
| V3 | 样例文件计数 | 18 |
| V4 | `verify.sh` | FAIL 条数 0 |
| V5 | `nc015_guard.sh --require-impl` | K01～K05 全 PASS，失败条数 0 |
| V6 | 主 Agent 盲测脚本 `nc015_blind.py` | 见下 |
| V7 | 作弊 grep（`skip`/`expectedFailure`/永真断言） | 零命中（grep EXIT=1，无输出） |
| V8 | 复检 `git status` | 多出 `openspec/annotation-community/tools/__pycache__/`，执行器按铁律停手上报 |

**V8 停手裁定**：`__pycache__/` 是 V1/V2/V6 用 `.venv/bin/python` 导入 `tools/` 模块时由解释器生成的字节码缓存，与交付无关，**不是**执行方缺陷。处理方式：在 `.gitignore` 登记 `openspec/annotation-community/tools/__pycache__/`，不改检查器。执行器没有自行删除，也没有做 git 操作，停手方式正确。

**盲测**（临时副本，脚本结束时 `tmp_removed=True`）：
- BT0 基线退出 0，`samples=18`。
- BT1 `envelope_valid.json.content_hash` 与 `content_hash_cases.json` 第一个 case 的 `expected_hash` 逐字相等（`8c883808…09cba`）。
- BT2a 删除 `## 6.`、BT2b 删除 `D-NC015-04`、BT2c 插入 `待定`，三项均退出 1，报错指向对应项；BT2d 行内代码里写 `待定` 时退出 0，反引号剔除规则生效。
- BT3 把 `expected` 拼成 `authorised`、BT3b 删除 `expected` 字段，均退出 1。
- BT4 把 `sender_fallback_seconds` 改为 299、BT4b 改成字符串 `"300"`、BT4c 把 `notifier_role` 改掉，均退出 1。
- BT5 逐个删除 18 个样例文件，18 次全部退出 1。
- BT6 从 `signed_fields` 去掉 `content_hash`、BT6b 调换字段顺序，均退出 1。
- BT7 把 `accountBindingCertHash` 改一位、BT7b 改公式分量，均退出 1，报错给出复算值与实际值。

**源码审阅**：检查器每条红条件都从契约和样例现读、现算，没有硬编码「通过」分支。证书哈希按 D-NC015-08 用 `peer_auth` 自身三个字段复算；`signed_fields` 与 §4.4 的十个字段做有序比较；`expected` 按 §8 闭集判定。

**攻击/故障场景审查**（契约 §3～§6）：

| 场景 | 契约防线 | 样例 | 结论 |
|---|---|---|---|
| 中间人替换会话公钥 | §4.3 D-NC015-09：`session_pub_sig` 由接收端设备 Ed25519 私钥签名；发送端在 X25519 之前用授权表公钥验证，失败即 `session_key_unbound`，不上传任何密文；直连也执行 | `session_pub_bad_signature.json` | 有防线 |
| 重放旧信封 | §6 第 6 步按 `(note_id, revision_id)` 幂等忽略并 ACK；AAD 绑定 `envelope_seq`，改序号会在第 3 步失败 | `envelope_replay_seq.json` → `duplicate_ack` | 有防线 |
| 跨账号密文投递 | §3.3 ① scope 比较（`deniedScopeMismatch`）；§6 第 3 步 AAD 含 `app_user_id` 与收发设备，误投即 `reject:aad_mismatch` | `auth_scope_mismatch.json`、`envelope_aad_mismatch.json` | 有防线 |
| 过期授权 | §3.3 第 8 条 `nowUtcMs < expiresAtUtcMs`，否则 `deniedRevokedOrUntrusted`；D-NC015-04 规定 180 天 | `auth_expired.json` | 有防线 |
| 吊销后残留会话 | §3.3 ④ `trustState != revoked`，经 Firestore 同步到其他设备（D-NC015-03）；§6 第 1 步对**每条信封**重新检查来源为 `active`，已建立会话的后续信封同样被拒 | `auth_revoked.json` | 有防线；「会话进行中吊销」的实时性归 NC-016 实测 |
| 中转对象未删 | §5 三层删除：接收端主删、发送端 300 秒兜底、平台 TTL/生命周期；三层都失败也只残留密文 | `deletion_layers.json`、`relay_ttl.json` | 有防线；**发现第 95 行文案缺陷，见下** |
| 接收端崩溃于 ACK 前 | §5 主删除要求「落库事务提交前不得 ACK」；§6 第 7 步事务成功后才 ACK；未 ACK 的对象由发送端兜底删除，下次重发时由第 6 步幂等处理 | `deletion_layers.json` | 有防线 |
| 哈希碰撞式篡改 | §4.4 `signed_fields` 含 `content_hash`，篡改该字段在 §6 第 2 步以 `bad_signature` 拒收；第 4 步对解密正文复算 nchash/v2，不符即 `hash_mismatch`；SHA-256 碰撞不在威胁模型 | `envelope_bad_signature.json`、`envelope_hash_mismatch.json` | 有防线 |

**发现与修正（契约）**：§5 表「终极兜底」行（第 95 行）写的是「notifier TTL 300 秒」，与 §4.2 表及 D-NC015-01 冲突：R1 审查已裁定 notifier 只承载信令，且只有全局 24 小时 TTL，仓库只读。§4.2、§7 `relay_ttl.json` 和检查器都按新裁定执行，只有这一行在返工时漏改。主 Agent 已改为「notifier 信令 TTL 24 小时（全局配置，只含对密文无用的包装材料，见 §4.2）；Storage 密文生命周期 1 天」。改动不涉及检查器的红条件、样例和决定编号。修正后已复跑检查器与守卫。

**判定**：`ACCEPTED`。解锁 NC-016。交接提醒 4b 仍然有效。
