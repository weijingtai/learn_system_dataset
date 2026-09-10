# R3 六项返工独立语义复核结果

日期：2026-09-10。复核对象：提交 `bc5f397` 的 PRD/DESIGN/PLANS/TASKS v1.3。依据：[REVIEW_R2_RESULT](REVIEW_R2_RESULT.md) §4 的六条通过标准与更新后的 [REVIEW_R2_CHECKLIST](REVIEW_R2_CHECKLIST.md)。
方式：只读；亲自运行验收命令；核对检查脚本未被放宽；实测正则；对照上游源码。未修改任何规范正文。

## 决定记录

审查R3：**不通过**。RW-1～RW-6 按原通过标准逐条满足，R2-01/02/05 回归无退化；但 R2-04 的跨端固定期望值仍不可得（mention 偏移单位未定义、修改说明会话初值未定义），R2-03 的客户端评论恢复无明确所有者。返工 3 项，`review_r3_guard.sh` 当前 3 项红。

## 1. 亲自运行的命令

| 命令 | 结果 |
|---|---|
| `bash openspec/annotation-community/review_r2_guard.sh` | 退出 0，七项全绿 |
| `bash openspec/annotation-community/verify.sh` | 退出 0 |
| `git diff --check 29c4ba3 bc5f397` | 退出 0 |
| `git diff --stat 29c4ba3 bc5f397 -- review_r2_guard.sh verify.sh` | 空：**两个检查脚本未被改动**，绿灯不是改松装置换来的 |
| `git diff 29c4ba3 bc5f397 -- REVIEW_R2_RESULT.md` | 空：R2 历史结论未被改写 |
| 以 Python 实测 DESIGN.md:87 的 `command_id` 正则 | 文档合法例与真实 `uuid4().hex` 通过；大写、缺前缀、31 位、33 位、版本位非 4、variant 非 89ab、带连字符 7 类负例全部拒绝 |
| `bash openspec/annotation-community/review_r3_guard.sh`（本次新增） | 退出 3：R2 回归 0 失败，RW3-1～3 红 |

## 2. 六项返工逐条核对

| 项 | 结论 | 证据（v1.3） |
|---|---|---|
| RW-1 数组顺序 | **通过** | DESIGN.md:309 以 `- 数组规范顺序：` 给出三个数组的排序键，以 E 编码作最终平局键、不依赖语言 sort 稳定性；DESIGN.md:310 写明顶层数组换序 hash 不变，嵌套 `selector.ranges` 保持上游顺序、换序 hash 改变，且「不能递归排序全部数组」——清单要求的「没有误排有序 selector」成立 |
| RW-2 修改说明来源 | **通过** | DESIGN.md:311：用户填写、系统不得在自动保存时填入或更新；系统差异摘要为只读派生、不写回、不进投影——清单要求的「系统摘要不污染用户说明」成立。TASKS.md:71 补「仅 change_summary 不同则新增修订」fixture 期望 |
| RW-3 模型与格式 | **通过** | DESIGN.md:52-53 新增 CommandRecord、NotifierDeliveryBinding 两行；DESIGN.md:85-91 §2.1.1 给出 command_id 正则、7 类负例及错误 code、operation 封闭目录、outcome 无 running、精简时间字段；桥接记录的写入来源限两类可信来源，缺证仍阻断 |
| RW-4 NC-017 | **通过** | TASKS.md:31 依赖含 NC-009；TASKS.md:242 起 backup.begin/complete/delete 各在命令事务写终态、对象传输在事务外、提交后响应前崩溃同键只产生一次效果——清单要求的「备份任务确实消费命令服务」成立 |
| RW-5 NC-010 | **通过（有残余）** | TASKS.md:167：账号隔离 Drift 队列、真实文件库重开后原键重试、响应丢失调用查询端点对账、410/503 不换键，满足原三条断言。残余见 RW3-3 |
| RW-6 NC-019 | **通过** | TASKS.md:260 起 trash/restore/purge 复用命令服务，purge 提交后响应前中断同键只产生一个清理任务与一条请求事件；纯本地 trash/restore 不伪造云命令——清单要求的「删除任务确实消费命令服务」成立 |

回归：R2-01（§6.2.1）、R2-02、R2-05（§4.4）在 `29c4ba3..bc5f397` 间正文未改动，R0 守卫绿，**无退化**。

## 3. 清单五项总判定

| 项 | 结论 | 理由 |
|---|---|---|
| R2-01 通知 ID | 通过 | 回归无退化；建议 P3-2 |
| R2-02 赞踩 | 通过 | 回归无退化；建议 P3-3 |
| R2-03 命令恢复 | **不通过** | 服务器侧与 NC-017/019 已闭环；客户端离线评论这一 R-16 核心场景的恢复验收无明确所有者（RW3-3） |
| R2-04 完整修订 | **不通过** | 投影与排序已完整，但 Python/Dart 共用固定期望值仍不可得（RW3-1），且普通保存去重存在未定义分支（RW3-2） |
| R2-05 提交顺序 | 通过 | 回归无退化 |

## 4. 计划：返工项

- [ ] 修复: DESIGN.md:228 mention 以 `markdown.substring(start, start+length)` 校验，但全文未定义 `start_offset`/`length` 的计量单位；v1.3 已把两者同时放进 content_hash 投影（DESIGN.md:305）与数组排序键（DESIGN.md:309）。Dart `String.substring` 按 UTF-16 码元计数，Python 切片按 code point 计数，只要 mention 之前出现 emoji 或 CJK 扩展 B 区等补充平面字符（术数古籍常见），两端得出的偏移、排序与 hash 就不同 ｜ 通过标准: `review_r3_guard.sh` 的 RW3-1 变绿，且 DESIGN 在含 `start_offset` 的同一句中定义单位为 Unicode code point（并写明 Dart 侧须经 `runes` 换算），NC-002 fixture 增加「mention 之前含一个 4 字节字符」用例，写明期望偏移、期望 canonical hex 与期望 hash
- [ ] 修复: DESIGN.md:311 只写 change_summary「默认空串，保存时原样保留」，没有定义**新编辑会话开始时**的初值。若初值置空，而 head 说明为 X，用户改动正文后又改回原文，普通保存按完整投影比较得出不同 hash，会误建一条内容相同的修订，违反同句「无内容/说明变化的自动保存仍不新增修订」与 R-04；若继承 X，新修订会带上前一次的说明。两种实现都说得通，去重结果因人而异 ｜ 通过标准: RW3-2 变绿，且 DESIGN 在含 `change_summary` 的同一句中写明会话初值规则（继承 head 值或置空二选一）及其对普通保存去重的影响；NC-002 或 NC-004 增加「head 说明为 X，改正文后改回原文再保存」用例并写明是否新增修订
- [ ] 修复: TASKS.md:167 的 RW-5 客户端命令恢复只写「发布/更新/收回等公共操作」，TASKS.md:177 起的 NC-011 只有服务器端 command_service，没有客户端持久 command_id 恢复验收。DESIGN.md:89 目录中客户端发起的 `comment.create/edit/delete`、`report.create`、`bookmark.set`、`share.create/revoke` 没有具名所有者，而离线评论正是 R-16 的核心场景 ｜ 通过标准: RW3-3 变绿，即 NC-010 或 NC-011 章节显式列出 `comment.create`；并写明除 `reaction.set`（NC-012 已覆盖）外，§2.1.1 operation 目录中所有客户端发起的操作均按 RW-5 的三条断言验收

## 5. 建议（不阻断）

- P3-1：DESIGN.md:87 写「键为原始 notifier_delivery_id」。notifier 契约 `api/openapi.yaml` 只规定其为不透明 HMAC 值，未规定字符集与长度；上游测试替身生成的是 `dlv-reopen-%d` 形式（`xuan-server/notifier/internal/store/memory/memory.go:434`）。若实现直接把原值用作 Firestore 文档 ID，一旦编码含 `/` 或超过 1500 字节就会失败。建议原值只作字段保存，文档 ID 用其 SHA-256 hex。（编码方式在 notifier 生产源码中未定位到，属未证实风险。）
- P3-2：上游测试替身的 deliveryId 以 `dlv-` 开头，本系统业务 NotificationRecord 以 `dlv_` 开头，仅差一个字符，为 R2 的 P2-1 提供了实证。§2.1 前缀仍待用户确认，建议改为 `ntf_`。
- P3-3：DESIGN.md:89 规定 applied_version「不能以 0 冒充已提交版本」，null 只留给拒绝与无版本资源。对从未点过赞的目标提交 `reaction.set(null, If-Match: 0)` 属于已提交的空操作，此时两种取值都不合法。NC-002 需给出该用例的期望。
- P3-4：DESIGN.md:310 规定「完全相同项去重后编码」，但修订存储本身可能保留重复项，导致存储内容与 hash 不一致。建议 Schema 直接拒绝重复项。
- R2 遗留建议 P2-3（最小账本增长）、P2-4（`command.*` 命名）、P2-5（REVIEW_R1 取代注记）本轮未处理，仍保留。

## 6. 验收装置加固

新增 `review_r3_guard.sh`：先运行 `review_r2_guard.sh` 作回归，再检查 RW3-1～3；退出码为两者失败条数之和。守卫只做存在性与结构判定，转绿后仍需复核人确认补充内容满足上面的通过标准。
