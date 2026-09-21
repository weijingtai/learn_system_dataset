# NC-013 可观察行为

ID 与契约 `community_deliveries.md` 一一对应：REST 行为 A01～A04（§10）、SERVER 行为 S01～S32（§3～§7、§6.4）、RULES 行为 R01～R03（§8）。「期望」逐字以契约为准，本表只给 Given/When/Then 摘要。

测试基建口径：SERVER 经 `community_helpers.call` 直调 handler、纯函数直调 `dispatch_outbox_event`/`advance_deliveries`（`now` 注入）、并发用 `threading` 双事务、Aborted 注入 monkeypatch `Transaction._commit`；REST 仅 dart 结构测试；RULES经 jest rules harness。

## REST（A）

| ID | Given | When | Then |
|---|---|---|---|
| A01 | openapi.yaml 3.1 | 校验 R9/R10/W15/W16 三条路径与四个 Schema | `notification paths and methods match the catalog` 通过；`expectedCatalog` 含 notifications 三行；seventeen 测试以 ≥17 通过 |
| A02 | `NotificationBody/NotificationEntry/NotificationPage/NotificationMuteState` Schema | 校验必填、`additionalProperties: false`、`notification_id` 引用 notificationRecordId | 4 个结构断言通过；validator 接受 openapi |
| A03 | 示例 3 个 + manifest 20 项 | 运行 `tool/check_examples.py` | 退出 0；翻转 `notification_page_merged.json` 任一字段后退出 1 |
| A04 | 错误目录与限流 | 校验 §13.4/§13.5 增补行 | `invalid_argument.notifier_delivery_id`、`invalid_argument.content_id`、mutes 30/min 出现在 yaml |

## SERVER（S）

| ID | Given | When | Then |
|---|---|---|---|
| S01 | outbox `comment.created`（root） | `dispatch_outbox_event` | 内容作者得 1 条 `comment` 记录；`ntf_` = 契约 M 向量字面量；`delivery_state=created`、`attempt_count=0` |
| S02 | outbox `comment.created`（reply） | 同上 | 回复目标作者得 `reply` 记录（target.kind=comment、id=reply_to_id）；内容作者不得记录 |
| S03 | 有效 mention | 同上 | mention 用户得 `mention` 记录 |
| S04 | 同一事件 recipient 同时命中 reply 与 mention | 同上 | 恰 1 条 `reply`（重叠合并） |
| S05 | `reaction.liked`（content） | 同上 | 内容作者得 `like` 记录 |
| S06 | `reaction.liked`（comment） | 同上 | 评论作者得 `like` 记录 |
| S07 | actor == recipient | 同上 | 零记录（无自通知） |
| S08 | 同一事件已消费过 | 再次 `dispatch_outbox_event` | 仍恰 1 条记录，字段与首次完全一致（create-if-absent 幂等） |
| S09 | 两事务并发消费同一事件 | Barrier 同步 | 恰 1 条记录；第二事务捕获 AlreadyExists 不抛错 |
| S10 | 未知 event_type | `dispatch_outbox_event` | 返回 None、零写入、不抛错 |
| S11 | `comment.edited`/`comment.deleted` | 同上 | 幂等 no-op、零记录 |
| S12 | `content.published` 与 `like_added` | 同上 | 幂等 no-op、零记录 |
| S13 | 消费事务被 Aborted 中断 | 注入后重跑 | comment/notification/无半成品，重跑后记录恰 1 条 |
| S14 | 3 组 M 向量 | 计算 `ntf_` | 与契约字面量逐字一致（含 emoji/CJK 字节长） |
| S15 | 任意新记录 | JSON Schema 校验 | 通过 `community_notification_record.schema.json`（8 必填、additionalProperties false） |
| S16 | `like` 记录 | `advance_deliveries` | created→dispatching→delivered；零 FCM 调用、零绑定 |
| S17 | `comment` 记录 + 可达 FCM | 同上 | `_send_multicast` 收到 title=""/body=""/data 携 notification_id 与 event_count；delivered |
| S18 | FCM 失败 | 同上 | `failed`；attempt_count=1 |
| S19 | failed 记录 4 档 attempt_count | 注入 now = updated_at+{0.9,1.0,3.9,8.0}s | 前组注入 `updated_at+0.9/1.9/3.9/7.9s` 四档均不到期；后组注入 `+1.0/2.0/4.0/8.0s` 四档均到期（退避 1/2/4/8） |
| S20 | failed 且第 5 次尝试再失败 | `advance_deliveries` | `abandoned`（终态）；attempt_count=5 |
| S21 | delivered 记录 | 再次 `advance_deliveries` | 状态不变（终态稳定） |
| S22 | actor 与 recipient 双向拉黑 | 领用 | created→abandoned、attempt_count=0、零 FCM |
| S23 | 内容被静音：comment 与 mention 各一条 | 领用 | comment → abandoned；mention → dispatching（绕过静音） |
| S24 | 目标内容 withdrawn/trashed/hidden | 领用 | abandoned、零推送 |
| S25 | seed trusted_ingress 绑定 + 可读内容 | R9 | 200 `NotificationBody`，字段按契约 |
| S26 | 无绑定 delivery_id | R9 | 404 共用体逐字节 |
| S27 | 绑定存在但登录人 ≠ recipient_scope | R9 | 404 共用体逐字节 |
| S28 | 绑定 + 评论已删除 | R9 | 404 共用体逐字节 |
| S29 | 同窗多条 comment/like + 独立 reply/mention | R10 | 窗口聚合条目（event_count、latest_notification_id）；reply/mention 单条 |
| S30 | 取页后插入更旧记录 | 同游标再取 | 结果不变（游标不回退）；limit=0/101 → 400 |
| S31 | PUT/DELETE mutes 幂等 | 重复调用 | `muted` 翻转正确、重复调用结果不变、无命令账本行 |
| S32 | ACL 扫描 E6 三例（withdrawn/trashed/hidden） | `GET /notifications/pull` | 404 + `not_found.content` + 逐字节共用体（xfail 已删转真） |

## RULES（R）

| ID | Given | When | Then |
|---|---|---|---|
| R01 | 三新集合 × authenticated/unauthenticated | 客户端直读/直写 | 全部拒绝（每集合 8 用例，129→153） |
| R02 | 顶层默认拒绝 match | 审视 firestore.rules | 三集合未新增任何 match |
| R03 | rules harness | `npm test -- community_rules` | `Tests: 153 passed` |
