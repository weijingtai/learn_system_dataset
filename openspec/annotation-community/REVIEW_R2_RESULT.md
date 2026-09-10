# R2 五项修订独立复核结果

日期：2026-09-10。复核对象：提交 `ccc55ff` 的 PRD/DESIGN/PLANS/TASKS v1.2。复核入口：[REVIEW_R2_CHECKLIST](REVIEW_R2_CHECKLIST.md)。
方式：只读；亲自运行验收命令；对照上游源码核验断言；逐项反证清单场景。未修改任何规范正文。

## 决定记录

审查R2：**不通过**。R2-01、R2-02、R2-05 通过；R2-03、R2-04 不通过，返工 6 项，均为文档层可直接修补。机器守卫 `review_r2_guard.sh` 当前 6 项红。

## 1. 亲自运行的命令

| 命令 | 结果 |
|---|---|
| `bash openspec/annotation-community/verify.sh` | 退出 0，FAIL 0 |
| `git diff --check ccc55ff~1 ccc55ff` | 退出 0 |
| `git log ccc55ff..HEAD -- openspec/annotation-community/` | 无后续改动，复核对象即 `ccc55ff` |
| 四份正文残留旧规则扫描（`client_seq`、`last_applied_seq`、`取消即删除`、`视为新请求`、`冲突方一律失败`、`sha256(event_id` 等） | 零命中；`with_idempotency`、`nchash/v1`、`事务外 result` 三处命中均为否定表述 |
| `bash openspec/annotation-community/review_r2_guard.sh`（本次新增） | 退出 6：R0 绿，RW-1～RW-6 红 |

## 2. 上游断言核验

| 断言 | 结果 | 证据 |
|---|---|---|
| notifier deliveryId 是不透明 HMAC | 属实 | `xuan-server/notifier/api/openapi.yaml` 的 `ReceiptsRequest.ids.items`：`HMAC(key, eventId\|deviceId\|channelPurpose)`，且写明「⛔ 不可用纯随机」 |
| 既有 `with_idempotency` 无法提供提交后崩溃恢复 | 属实 | `functions-py/xuan/idempotency.py`：事务内写 `state: running` 占位 → 事务外 `fn()` → 事务外 `set(result)`；fn 成功后、result 回填前崩溃会留下 running，重试走分支 4 返回 unavailable |

## 3. 逐项结论

| 项 | 结论 | 证据 | 残余问题 |
|---|---|---|---|
| R2-01 通知 ID | **通过** | DESIGN §6.2.1：`notification_id` 与 `notifier_delivery_id` 分字段；一对多；禁止加前缀/截断/重算；正文端点经可信映射校验账号、设备与 ACL；可信映射缺证「阻断对应通知工作包」。§6.1 业务列表按 notification_id upsert、传输按原样 deliveryId 去重。NC-014 覆盖两设备/两用途各自 ACK、业务已存在仍 ACK 新传输 ID | P2-1 前缀命名易混 |
| R2-02 赞踩 | **通过** | DESIGN §4.4：服务器 `Reaction.version` + `If-Match`，取消保留 null 状态行与版本；like(v0)→v1→cancel(v1)→v2→旧命令重放只返回原 applied_version=1，客户端不得覆盖已知 v2；两设备同基线一成功一 412 且不自动抢写；重启恢复 command_id 不重新生成序号；purge 后墓碑防复活。NC-012 基准反例逐条对应 | 无 |
| R2-03 命令恢复 | **不通过** | 恢复语义本身完整：§7.4 步骤 2 账本与业务同事务、不持久 running；步骤 3 区分提交前/提交后崩溃；步骤 4 超期精简但不删去重身份，返回原结果或 410，不重新执行。NC-009 注入四种故障。**但**模型与覆盖面有缺口，执行者无法据此写 Schema，且三个写命令任务未接入 | RW-3、RW-4、RW-5、RW-6 |
| R2-04 完整修订 | **不通过** | nchash/v2 投影已含 binding/selector/mention 位置/图片 alt；E 编码对象键按字节序排序、键序不改 hash；同步进度与派生迁移结果排除；恢复/合并不按 hash 折叠；fixture 双消费者读字面 expected_hash 与 expected_canonical_hex。**但**数组顺序与 change_summary 来源两处未定，跨端固定期望值无法唯一确定 | RW-1、RW-2 |
| R2-05 提交顺序 | **通过** | DESIGN §4.4：收回先提交→评论事务（含重跑）见不可访问→`404 not_found.content` 且不写评论/事件；评论先提交→成功，随后收回隐藏主题；仍可访问但 `expected_access_version` 不匹配才 409；「事务竞争本身不强制产生 409」。§7.3 旧「权限版本竞争」行已替换。NC-009 用受控屏障分别强制两种提交顺序并含回调重跑，NC-011 同步 | 无 |

## 4. 计划：返工项

- [ ] 修复: DESIGN.md:302 数组编码写「保持数组顺序」，但 `attachment_refs`/`mentions`/`bindings` 三个数组没有规范顺序；DESIGN.md:307 要求 fixture 覆盖「数组换序」却未写期望。Python 与 Dart 生产者只要数组顺序不同，同一语义内容就得出不同 hash，普通保存还会误建修订 ｜ 通过标准: `review_r2_guard.sh` 的 RW-1 变绿，且 §7.2 以一行 `- 数组规范顺序：` 为三个数组各给出排序键（例如 mentions 按 `(start_offset, length, user_id)`），并在同一节写明「数组换序后 hash 不变」或「hash 改变」之一
- [ ] 修复: DESIGN.md:295 与 DESIGN.md:303 把 `change_summary` 纳入 hash 投影，但全文没有定义其来源（用户填写的修改说明，还是每次保存自动生成的摘要）。若为自动生成，内容完全相同的保存也会得到不同 hash，直接违反 R-04「相同内容不重复建版本」 ｜ 通过标准: RW-2 变绿（DESIGN 出现 `change_summary` 与「用户填写/用户输入/系统生成/自动生成」之一在同一句）；若定为自动生成则必须移出投影；NC-002 fixture 增加「仅 change_summary 不同」用例并写明期望
- [ ] 修复: DESIGN.md:38-51 的 §2 模型表缺 `CommandRecord` 与 `NotifierDeliveryBinding` 两行，而 TASKS.md:72 已要求 NC-002 为这两个对象建模；DESIGN.md:348 对 `command_id` 只写「随机」，没有格式与非法判定，NC-002/003 写不出 Schema 负例 ｜ 通过标准: RW-3 变绿；两行各含最小字段与不变量（CommandRecord 至少含作用域、command_id、payload_hash、outcome、applied_version、结果精简时间；NotifierDeliveryBinding 至少含 notification_id、notifier_delivery_id、接收账号、设备、用途、写入来源）；command_id 格式可写成正反 fixture
- [ ] 修复: TASKS.md:31 与 TASKS.md:237 的 NC-017 是备份写命令任务，受 DESIGN §4.3「所有服务器写命令隐含命令账本终态写入」与 NC-015「遵循 §7.4」约束，但依赖列没有 command_service 的所有者 NC-009，章节里也没有命令恢复验收项，属隐藏依赖 ｜ 通过标准: RW-4 变绿（总表 NC-017 依赖含 NC-009，章节含 `§7.4`）；`verify.sh` 仍为 FAIL 0
- [ ] 修复: TASKS.md:163 的 NC-010 没有客户端持久 command_id 队列与恢复验收项，但 PRD §3.1 的 R-16 行把「持久 command_id、同事务可恢复结果、超期不重放新写入」指派给了 NC-010 ｜ 通过标准: RW-5 变绿；新增验收项至少含三条断言：重启后以原键重试、响应丢失后调用命令查询端点对账、收到 410/503 时不换键重放
- [ ] 修复: TASKS.md:252 的 NC-019 中 trash/restore/purge 都是服务器写命令，但没有 §7.4 命令恢复验收项 ｜ 通过标准: RW-6 变绿；新增验收项含「purge 提交后、响应前中断，以同键重试只产生一个清理任务与一条事件」

## 5. 建议（不阻断本轮通过）

- P2-1：DESIGN.md:72 前缀 `dlv_` 现在指业务 NotificationRecord，而另有字段 `notifier_delivery_id`，名称互相误导。§2.1 前缀本就待用户确认，建议借此改为 `ntf_`。
- P2-2：DESIGN.md:300 整数编码范围含负数，但没有定义负号写法与 `-0` 是否拒绝；NC-002 需补对应成对 fixture。
- P2-3：DESIGN.md:351 最小命令账本只在账号永久销毁后清理，高频赞踩下会持续增长；§9.1 缺增长估算或容量上限。
- P2-4：DESIGN §7.3 新增的 `command.result_expired`、`command.status_unavailable` 偏离其余 code 的 `<类别>.<细节>` 命名（`conflict.*`、`not_found.*`、`too_large.*`）。
- P2-5：REVIEW_R1.md 的 BT-05、TC-06 行仍记载已被 v1.2 废止的 `client_seq` 与「TTL 14 天」规则，且四份文档头部把它链接为「审查缺陷登记」。建议在该文件顶部加一句「规则以 v1.2 正文为准，§1.3/§1.4 部分处置已被 R2 取代」，不改历史正文。

## 6. 验收装置加固

新增 `review_r2_guard.sh`，退出码为失败条数：

- R0（回归网，当前绿）：四份正文不得重新出现已废止规则。
- RW-1～RW-6（当前红）：一一对应上面的返工项。

守卫只做存在性与结构判定，属回归网，不代替语义复核；RW 项转绿后仍需复核人确认所补内容满足对应「通过标准」。
