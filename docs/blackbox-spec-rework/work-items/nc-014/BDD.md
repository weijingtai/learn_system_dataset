# NC-014 可观察行为

ID 与契约 `community_notification_host.md` 一一对应：PACKAGE 行为 P01～P08（契约 §4.1、§7.1）、CLIENT 行为 C01～C18（契约 §4、§5、§6、§7.2）。「期望」逐字以契约为准，本表只给 Given/When/Then 摘要。

测试基建口径：PACKAGE 用 notification 包内既有测试范式（直接构造 `PushTiming`/解析 L2 文档、源码扫描先例 `a4_factory_lock_test`）；CLIENT 用 `MockClient`（package:http/testing）+ 临时目录真实 Drift 文件库 + 注入式时钟与 `IdTokenProvider` + 宿主自写 fake（包内 `test/support/fakes.dart` 拿不到；`FakeReceiptTransport` 存批次副本 `List.of(ids)`）。全部经接口 fake 验收，真机链路归 NC-024。

## PACKAGE（P）

| ID | Given | When | Then |
|---|---|---|---|
| P01 | L2 timing 段含 `dedup_retention_ms: 604800000` | 解析 | `PushTiming.dedupRetention == Duration(days: 7)`（值来自 L2 fixture，非 lib/ 常量） |
| P02 | L2 timing 段缺 `dedup_retention_ms` | 解析 | `dedupRetention == null`，不抛错、无兜底值 |
| P03 | `dedup_retention_ms: 0` 与负数 | 解析 | 各抛 `FormatException` |
| P04 | `lib/` 全部 .dart 源码 | 扫描 | 不含 `604800000`、不含 `Duration(days: 7)`（D.6 窗口只从 L2 读） |
| P05 | seenAt 距 now 恰等于 window | `isExpired(seenAt, now)` | `true`（满窗即裁，含等于） |
| P06 | seenAt 距 now 严格小于 window | `isExpired(seenAt, now)` | `false` |
| P07 | 混合过期/未过期的 id 集合 | 裁剪 | 仅过期 id 被遗忘（`hasSeen == false`），未过期全部保留 |
| P08 | 包 barrel `lib/notification.dart` | import | `DedupRetention` 可从包级导出消费（宿主 adapter 入口） |

## CLIENT（C）

| ID | Given | When | Then |
|---|---|---|---|
| C01 | `handleWakeData` 分别喂 `{"type":"push","deliveryId":"d1"}` 与 `{"type":"resync","deliveryId":"d2"}` | 分派 | push → fetcher fake 收到 `d1`（`BodyFetchWakeHandler` 路径）；resync → 不落盘、ACK 缓冲空、R10 刷新被触发 |
| C02 | `{"type":"community","notification_id":"ntf_a…","event_count":"2"}` | 分派 | 业务表恰 1 行（upsert by notification_id）、去重表零行、无传输 ID 写入、ACK 缓冲空 |
| C03 | 同一 deliveryId 首投与重投（at-least-once） | `DriftDeliveryLog.persist` | 首投 `wasDuplicate: false`、重投 `wasDuplicate: true`；业务表仍 1 行 |
| C04 | 同一 notification_id 的两条不同 deliveryId（两设备/两用途） | 依次 persist | 两条去重行各自落盘，ACK 缓冲含两 id、顺序原样无去重 |
| C05 | 业务行已存在的 notification_id 携新 deliveryId 再投 | persist + ACK | 新去重行落盘、业务行不新增、新 deliveryId 仍进 ACK 批次 |
| C06 | `DriftDeliveryLog` fake 注入按 id 返回 `DeliveryPersistFailed` | persist 后断言 | ACK 缓冲为空且 cursor 未推进（失败 fake 分支；永真 fake 不算通过） |
| C07 | 去重表含 seen_at 满窗旧行与窗口内行；窗口取 L2 `timing.dedupRetention` | persist 新投递 | 满窗旧行被裁（再投视为新）、窗口内行保留 |
| C08 | 待 ACK 批次 [b1,b2,b3] | `NotifierReceiptTransport.send` | MockClient 收到同一批次原样（副本、无重排、无去重、无拆分） |
| C09 | 服务端整批 4xx（`ReceiptRejected`） | 批次上报 | 整批结束、`onRejected` 可观察回调含原批次与 cause、无重试无拆批探测 |
| C10 | notifier 返回含 authorizedChannels 的 token | `NotifierConnectionTokenSource.obtain` | `ConnectionToken` 字段透传、`subjectAppUserId == appUserId` |
| C11 | MockClient 返回 R10 页（聚合条目 event_count=3 + 独立 reply） | `CommunityBackfillSource.fetchSince` | 每条目 deliveryId 为空串哨兵、messageId=`latest_notification_id`、nextCursor 透传；全程无传输 ID 制造 |
| C12 | 同 R10 页经分派点落地 | 业务 upsert | 恰 2 行、按 notification_id 唯一、ACK 缓冲空、cursor 经 persistCursor 推进 |
| C13 | R9 MockClient 返回 404 共用体 | fetcher + 点击 | 抛「正文不可用」、无 ACK、业务行 body_markdown 为空；列表条目仅打开内容 |
| C14 | 业务行 target.kind=content | 列表渲染 | 条目标题按 kind 固定文案且 `event_count=3` 显示「（3 条）」，reply/mention 条目恒单条 |
| C15 | 可读 content 类条目 | 点击 | `ContentDetailPage(contentId: target.id)` 入栈（内容详情讨论区顶部） |
| C16 | 目标 withdrawn/trashed/hidden/拉黑 四类 | 点击 | 四类落同一 `CommunityUnreadableTargetPage`，文案逐字节「该内容已不可访问」+ 返回按钮，组件树无原因字段 |
| C17 | 两个 scopeUid 各自 openScoped | 账号切换 | 两库文件隔离、行互不可见 |
| C18 | 详情页静音入口 | PUT/DELETE mutes | MockClient 收到 `PUT`/`DELETE /v1/community/notifications/mutes/{content_id}` 与 Bearer 头；重复调用结果不变 |
