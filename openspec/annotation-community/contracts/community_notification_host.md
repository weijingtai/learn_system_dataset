# 宿主契约：Notification 宿主适配、去重与导航（NC-014）

状态：`DRAFT_FOR_NC-014`（2026-09-13 规格草案，主 Agent 审查通过后转 `FROZEN_FOR_NC-014`）。权威来源：[TASKS](../TASKS.md) NC-014（:226-234，**范围权威**）；[DESIGN](../DESIGN.md) §6、§6.1、§6.2、§6.2.1、§6.3；[PRD](../PRD.md) R-11、R-16、E-DEDUP、E-WIRING、E-NOTIFIER；[community_deliveries.md](community_deliveries.md)（§6、§7、§15，R9/R10/W15/W16 与 D-NC013-01～16）；[community_api.md](community_api.md) §13（R9/R10/W15/W16 端点与 Schema 唯一来源）；[INTEGRATION_BASELINE.md](../INTEGRATION_BASELINE.md):12,66（NC-001 预备记录：通知表现层复用 social 普通中心组件、不挂遗留页）；notification 包 `docs/integration-guide.md`、`docs/from-server-coder.md`（D.6/§S6.1）、`README.md` 归属铁律；主 Agent 冻结裁定 D-NC014-01～08（§10）。本文把已定设计落到 notification 包的 D.6 实现与 reading-notes 的八端口适配、装配、导航与测试判据，供执行者照抄；与上游冲突以上游为准并回报主 Agent。语义红线：**投递为 at-least-once；客户端按原样 `deliveryId` 去重（保留窗口读 L2 `timing.dedup_retention_ms`，当前下发值 604800000 毫秒=7 天，投影自服务端 `retention.ackAcceptWindow`，禁止把该值写进任何 lib/ 源码）；「原子」仅指同一 Drift 事务内写入一次，不构成端到端恰好一次；红线词形由守卫机械扫描，本契约与全部产物零命中**。

## 1. 仓库、环境与基线

| 项 | 实值 |
|---|---|
| PACKAGE（写入目标） | Windows：`D:/Programme/xuan/notification`（HEAD `518670b`；macOS 按 D-NC012-23 同布局 `/Users/jingtaiwei/Git/Public/xuan-migration/notification`，开工不符即停手上报） |
| CLIENT（写入目标） | Windows：`D:/Programme/xuan/reading-notes`（HEAD `107ec90`；macOS `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`） |
| REST（全程只读） | Windows：`D:/Programme/xuan/repository-rest-adapter`（HEAD `b60bfbd`），唯一 3.1 OpenAPI，`dart test` `+81: All tests passed!` |
| SERVER（全程只读） | Windows：`D:/Programme/xuan-server/functions-py`（HEAD `992088e`，含 NC-013 `5800a23`），pytest `5 failed, 568 passed, 3 xfailed` |
| NOTIFIER（全程只读） | `D:/Programme/xuan-server/server-notifier`；`api/openapi.yaml` 3.0.3 权威，⛔ 不复制契约正文 |
| SOCIAL（全程只读） | `D:/Programme/xuan/social`（HEAD `1971f79`）；`lib/social.dart:90-93` 公开导出 `NotificationCenterPage` 与 `SocialNotificationItem`，仅作依赖消费，不改其仓 |
| 基线测试 | notification `flutter test` `+194: All tests passed!`（2026-09-13 实测；包内 README/integration-guide 的 189 口径已过时，以 194 为准）；reading-notes `flutter test` `+296: All tests passed!`、`flutter analyze` `No issues found!` |
| Flutter | Windows flutter 在 `D:/apps/apps/flutter/bin`（守卫经 `shutil.which` 与 `os.pathsep` 解析，D-NC012-23） |
| Gitea | `192.168.0.165:3000`（pub get 拉 notification/social git 依赖必须可达；不可达为停手条件） |
| 派发前置 | NC-010、NC-013 均 `ACCEPTED`（TASKS.md:27 总表：NC-014 依赖 NC-010, NC-013；NC-013 已交付 R9/R10/W15/W16，TDD 前置满足） |

## 2. 模块与文件（两线写入白名单）

### 2.1 PACKAGE 线（act/01，notification 包，D.6 范围）

| 仓库 | 文件 | 内容 |
|---|---|---|
| notification | `lib/src/config/push_config.dart` | `PushTiming._allowedKeys` 追加 `'dedup_retention_ms'`；`PushTiming` 追加 `Duration? dedupRetention` 字段与解析（**只追加**）：键存在时取正整数（非正数抛 `FormatException`，与 `_requirePositiveInt` 惯例一致），键缺失时为 `null`、不设兜底值（D-NC014-10）；既有 11 个键与耦合校验零改动 |
| notification | `lib/src/receive/dedup_store.dart` | 追加 `DedupRetention`（**只追加**）：`static DedupRetention? fromTiming(PushTiming timing)`（`dedupRetention == null` 时返回 `null`）、`bool isExpired(DateTime seenAt, DateTime now)`（`now − seenAt ≥ window` 即过期，**满窗即裁**、含等于）、`DateTime cutoffOf(DateTime now)`（`now − window`）；`dedupKeyOf`/`DedupStore`/`InMemoryDedupStore` 既有成员签名零改动 |
| notification | `lib/notification.dart` | barrel 追加 `DedupRetention` 导出（**只追加**；宿主 adapter 消费入口） |
| notification | `docs/from-server-coder.md` | 仅 D.6 三处状态行同步：:269-274 段、:290 解阻塞对照表行、:300-303 收尾行——`⬜ 未实现` 改为已实现并注明实现入口（`PushTiming.dedupRetention` + `DedupRetention`）；其余行禁改 |
| notification | `docs/integration-guide.md` | 仅 §4 去重口径段：宿主「短期 InMemoryDedupStore」方案更新为「本包 `DedupRetention` 行为层 + 宿主 `DeliveryLog` adapter 持久表」口径，删除与 D.6 已实现矛盾的表述；其余行禁改 |
| notification | `test/receive/dedup_retention_test.dart`（新增） | §7 PACKAGE 测试 8 个（名称逐字） |

**禁止**（PACKAGE 线）：改 `pubspec.yaml` 与既有 194 个测试的任何一行；改上表以外任何文件；把 `604800000` 或 `Duration(days: 7)` 写进 `lib/`（P04 源码扫描）；在包内实现宿主业务（业务通知列表、`notification_id` upsert、R9/R10/W15/W16 调用、FCM 插件）；装配遗留页；新依赖；`skip`；永真断言；测试内现算参考值；红线词形；`git push`；learn_system 写入（交付报告除外）。

### 2.2 CLIENT 线（act/02，reading-notes，八端口适配与导航）

| 仓库 | 文件 | 内容 |
|---|---|---|
| reading-notes | `pubspec.yaml` | `dependencies` 追加两个 git 依赖（**只追加**）：`notification: git: url: http://192.168.0.165:3000/xuan/notification.git` 与 `social: git: url: http://192.168.0.165:3000/xuan/social.git`（不写 `ref`，由 `pubspec.lock` 钉解析提交；开工时 notification 默认分支必须已含 act/01 提交） |
| reading-notes | `pubspec.lock` | `flutter pub get` 自动更新并提交（白名单内，禁手改） |
| reading-notes | `lib/src/notifications/community_notification_adapters.dart`（新增） | ① §3 八端口 adapter（类名逐字）；② `CommunityNotificationWiring`：装配链 integration-guide.md:129-145 五步（①PushConfigResolver→②AckPipeline→③ReceivePipeline→④ConnectionManager→⑤BodyFetchWakeHandler，④⑤交同一个 ③）、`handleWakeData(Map<String, Object?> data)` 双帧分派（§5.1）、`handleDelivery` 分派点（§4.3）；③ Drift 三表与 `CommunityNotificationDatabase`（`openScoped({dir, scopeUid})`，文件名 `reading_notes_notifications_$scopeUid.sqlite`，`schemaVersion 1`，onCreate 建表；表列见 §6.1；D-NC014-09：不扩既有 `lib/src/community/community_database.dart`）；④ `CommunityNotificationMuteApi`（W15/W16，§6.4） |
| reading-notes | `lib/src/notifications/community_notification_adapters.g.dart` | `build_runner`（drift_dev）生成物，随实现提交（白名单内，禁手改） |
| reading-notes | `lib/src/notifications/notification_target_router.dart`（新增） | `NotificationTargetRouter`（§5.2）、`CommunityUnreadableTargetPage`（统一占位页：文案「该内容已不可访问」+ 返回按钮，**构造函数无任何失效原因字段**）、`CommunityNotificationListPage`（表现层：复用 `NotificationCenterPage`（social 导出），`SocialNotificationItem` 映射见 §6.2） |
| reading-notes | `test/notifications/community_notifications_test.dart`（新增） | §7 CLIENT 测试 18 个（名称逐字）；测试形态：`package:http/testing` 的 `MockClient` + `Directory.systemTemp.createTemp` 临时目录真实 Drift 文件库 + 注入式时钟与 `IdTokenProvider`（`lib/src/community/ports.dart:3` 范式）；包内 `test/support/fakes.dart` 拿不到（integration-guide.md:314-321），宿主自写 fake，`FakeReceiptTransport` 存批次副本（`List.of(ids)`，不存引用） |

**禁止**（CLIENT 线）：改 `lib/src/community/` 既有文件与上表以外任何文件；装配 notification 包遗留页（`notification_page.dart`/`notification_viewmodel.dart`/`playground_state_widgets.dart`，D-NC014-01）；新增 `firebase_messaging` 等推送插件依赖（真机链路归 NC-024，D-NC014-07）；在宿主复刻包内职责（帧解码、ACK 批次/退避/lifecycle、通知栏组装、去重裁剪算法）；`lib/`（含生成文件）出现 `604800000` 字面量（测试 fixture 引用 from-server-coder.md §6 下发值不算）；`skip`；永真断言；测试内现算参考值；红线词形；`git push`；learn_system 写入（交付报告除外）。

## 3. 八端口适配矩阵

| 端口（包内定义） | 宿主 adapter（类名冻结，均在 `community_notification_adapters.dart`） | 绑定来源 | 红线 |
|---|---|---|---|
| `RemoteConfigSource`（`ports/push_config_source.dart`） | `NotifierRemoteConfigSource` | L2 `GET /v1/client-config`（Bearer Firebase ID token；ETag/304） | sealed 三态（`RemoteConfigReceived`/`RemoteConfigNotModified`/`RemoteConfigUnavailable`）零改动；L1 bootstrap 只提供 host/config_path/timeout |
| `PushConfigCache`（同上） | `LocalPushConfigCache` | `CommunityNotificationDatabase` meta 表（key=`push_config_cache`），读写 `CachedPushConfig{json, etag?}` | 非法 L2 文档不进缓存（包内 resolver 既有行为，宿主不兜底） |
| `DeliveryLog`（`ports/delivery.dart`） | `DriftDeliveryLog` | 宿主 Drift：`community_notification_dedup` 去重行 + `community_business_notifications` 业务 upsert **同一事务**（DESIGN §6.2.1「接收时原子持久化本次传输去重记录及业务 notification_id upsert，再 ACK 原始 ID」） | `wasDuplicate` 由持久层派生；`DeliveryPersistFailed` 时不 ACK、不推进 cursor（A30，§4.2）；裁剪按 §4.1 |
| `RealtimeChannel`（`ports/realtime_channel.dart`） | `SseRealtimeChannel` | L2 `sse_connect`（SSE 流）；连接/token 刷新由包内 `ConnectionManager` 驱动 | `RealtimeUndecodable` 丢弃不终止流；`RealtimeResync` 永不落盘、不进 ACK 流（realtime_channel.dart:36） |
| `ReceiptTransport`（`ports/receipt_transport.dart`） | `NotifierReceiptTransport` | notifier `POST /receipts`（3.0.3，整批原子；任一 id 失败整批 4xx → `ReceiptRejected`） | 不暴露数字状态码；批次存副本原样发送、不重排不去重不拆批探测（A45）；`ReceiptRejected` 整批结束并报告（§4.4） |
| `ConnectionTokenSource`（`ports/connection_token_source.dart`） | `NotifierConnectionTokenSource` | notifier `POST /auth/rt/connection-token`（Bearer Firebase ID token；channels 服务端返回） | `ConnectionToken.subjectAppUserId` 恒 appUserId；persona 切换重连走包内既有路径 |
| `BackfillSource`（`ports/backfill_source.dart`） | `CommunityBackfillSource` | R10 `GET /v1/community/notifications?cursor&limit`（Bearer，REST 3.1）；L2 键 `cursor_backfill` | `NotificationEntry` 无传输 ID：映射为 `IncomingDelivery(deliveryId: '', domain: 'community', envelopeId: '', messageId: entry.latest_notification_id, payload: <entry 字段>)`，**空串哨兵=无传输 ID**（D-NC014-03）；`nextCursor` 透传 R10 `next_cursor` 不透明串；`hasMore==true ⇒ nextCursor 必非 null` 不变量保持 |
| `MessageBodyFetcher`（`ports/message_body_fetcher.dart`） | `CommunityMessageBodyFetcher` | R9 `GET /v1/community/notifications/pull?notifier_delivery_id=<原始值>`（逐字不透明，禁前缀/截断/重算/解码 HMAC） | 四类失败共用 404 共用体 → 抛「正文不可用」降级（D-NC014-04，§5.3）；响应 `NotificationBody{notification_id, kind, target, body_markdown, actor_id, created_at}` |
| （另算）`PushTokenRegistry`（`ports/push_token_registry.dart`） | 本期不适配 | notifier `POST/DELETE /push/tokens` | FCM token 获取与注册随真机链路归 NC-024（D-NC014-07）；TASKS:228 的「8 个端口」按 integration-guide.md:54-65 清单计，不含 `PushTokenRegistry`（integration-guide.md:71「另算」） |

## 4. 接收管线与 D.6 去重

### 4.1 D.6（PACKAGE 线实现；from-server-coder.md:269-274「★ 契约已到位，代码还没接」就此闭合）

- 解析：键名 `timing.dedup_retention_ms`（int，毫秒；当前 L2 下发值 604800000=7 天，**投影**自服务端 `retention.ackAcceptWindow`，不是第二份常量）。`PushTiming` 键缺失 → `dedupRetention == null`，无兜底值（D-NC014-10）；键存在但非正整数 → `FormatException`。
- 裁剪行为层 `DedupRetention`：`isExpired(seenAt, now)` 满窗即裁（`now − seenAt ≥ window`，含等于）；`cutoffOf(now) = now − window` 为裁剪线。`lib/` 禁止 `604800000` 与 `Duration(days: 7)` 字面量（P04 源码扫描，先例 `test/config/no_hardcoded_values_test.dart`）。
- 宿主持久去重表（CLIENT）：`community_notification_dedup(delivery_id PK, owner_scope, first_seen_at)`；`DriftDeliveryLog.persist` 单事务内写去重行（INSERT 冲突 → `wasDuplicate: true`）+ 业务 upsert（§6.1），并按 `DedupRetention.cutoffOf(now)` 删除过期行（窗口取自装配时 L2 配置的 `timing.dedupRetention`；为 `null` 时装配中止并停手上报，宿主不编窗口——integration-guide.md:246-267 旧口径「宿主侧不做带 TTL 实现」由本包 D.6 交付后口径取代）。登记时机在落盘成功之后（D.4）；`DedupStore` 只管 UI 可见性、绝不管 ACK 资格（重复消息仍要 ACK，D.2）。

### 4.2 落盘失败不 ACK（TASKS:231/232；包内既有行为，宿主不得重写）

`AckPipeline.handle`（`lib/src/ack/ack_pipeline.dart:77-88`，A30）：只有 `DeliveryPersisted` 的 deliveryId 进入 ACK 流；`DeliveryPersistFailed` 不 ACK、不标记已投递。cursor 推进挂在 `DeliveryPersisted`（`ack_pipeline.dart:72-75`），整页补拉中途失败不保存 cursor（`connection_manager.dart:156-179`）。CLIENT 判据 C06：**必须有返回失败的 fake 分支**，断言 ACK 未发出且 cursor 未推进；「永远返回 `DeliveryPersisted()` 的 fake 不算通过」（TASKS:232 逐字）。

### 4.3 同一管线与 R10 旁路（D-NC014-03）

- notifier 域投递（SSE 帧、wake 经 R9 落地、两设备/用途的各 deliveryId）全部经宿主 `handleDelivery` 分派委派包内 `ReceivePipeline.handleDelivery` 同一条管线（TASKS:231「同一持久接收管线处理实时/唤醒/补拉」；integration-guide.md:143-144「不要另写处理路径」）。
- R10 业务条目按 D-NC014-03 **不产生传输 ID、不进 AckPipeline**：宿主分派点识别空串哨兵条目后走「单 Drift 事务业务 upsert」即完成，返回 `DeliveryPersisted(wasDuplicate: …)` 支撑包内「整页处理完毕才推进游标」；对 integration-guide.md:143-144 的单一入口规则，此处按主 Agent 裁定 D-NC014-03 在业务域边界收窄，登记于 §10。
- 同业务通知已存在仍须持久当前传输并 ACK 新 ID；同事件两设备/同设备不同用途各得独立 deliveryId，各自原样 ACK（DESIGN §6.2.1 逐字；判据 C04/C05）。

### 4.4 ReceiptRejected（TASKS:231；DESIGN §6.2）

`/receipts` 整批原子，任一 id 失败整批 4xx，调用方无法区分具体原因；客户端整批结束并报告（`ack_pipeline.dart:147-152` 的放弃+计数+`onRejected` 回调，宿主把回调接到可观察痕迹）、不任意重试 4xx、不拆批探测（判据 C09）。`ReceiptTransport` 实现不对入参重排或去重（`receipt_transport.dart:40-42`；判据 C08）。

## 5. 唤醒分派与导航（D-NC014-01/05/08）

### 5.1 双帧形状分派（`CommunityNotificationWiring.handleWakeData`）

| FCM data `type` | 携带 | 路径 |
|---|---|---|
| `push` / `resync`（notifier 帧） | `deliveryId`（HMAC hex，键集恰好两个） | 包内 `FrameDecoder` 解码（domain 取自 channel 名，不来自载荷）→ `push` 为 `RealtimeWake` → `BodyFetchWakeHandler.handleWake(deliveryId)` → `CommunityMessageBodyFetcher`（R9）→ 注入 ③ 同一 ReceivePipeline；`resync` 为 `RealtimeResync` → 触发一次 R10 业务补拉（经 `CommunityBackfillSource` 与宿主 cursor），不落盘、不 ACK |
| `community`（NC-013 FCM data） | `notification_id`（`ntf_<32 hex>`）+ `event_count`（**字符串化**整数） | 业务 upsert by notification_id（§6.1）+ R10 业务补拉刷新；不制造传输 ID、无来源 ACK（D-NC014-03） |
| 其余/缺键/`event_count` 非十进制非负整数 | — | 计数丢弃、不抛错（`FrameDecoder` 对 `RealtimeUndecodable` 同口径） |

真机 FCM 入口（插件注册、后台消息桥）归 NC-024；本任务的 `handleWakeData` 以纯函数接 `Map`，测试直接喂 data（D-NC014-07）。

### 5.2 导航路由（`NotificationTargetRouter`；D-NC014-01/05）

- 表现层挂靠：`CommunityNotificationListPage` 复用 social `NotificationCenterPage` 作业务表现层，`onNotificationTapped` 交 `NotificationTargetRouter`；导航路由归宿主；**不装配** notification 包遗留 `PlaygroundNotificationPage`（D-NC014-01）。
- `target.kind == content`：经注入的可读性判定（装配时接宿主既有内容读取路径）后 `ContentDetailPage(contentId: target.id)`（`lib/src/community/content_detail_page.dart:15-33` 现有构造），即本期「内容详情讨论区顶部」（D-NC014-05；按 `comment_id` 深链定位楼层 DEFERRED，上游扩展候选见 D-NC014-11）。
- 目标不可读（收回/删除/隐藏/拉黑，四类）：`CommunityUnreadableTargetPage`，统一文案「该内容已不可访问」+ 返回按钮，**四种失效原因页面文案完全一致、构造与渲染不含可区分原因的字段**（TASKS:233；PRD §6.2 决策）。可读性判定失败（网络/异常）与四类失效同口径落占位页，不区分原因。
- 判据 C15（content 类点击）与 C16（四类失效占位页）。`target.kind == comment` 的导航本期不路由（content_id 缺口，D-NC014-11），C15/C16 不涉及 comment 类条目的导航断言。

### 5.3 R9 降级（D-NC014-04）

`CommunityMessageBodyFetcher` 照常实现；生产绑定缺失（上游 G2，D-NC013-08）时 R9 必 404（四类失败共用 `NotFoundContent` 体，无可区分字段）→ 按「正文不可用」降级：不 ACK、不写传输去重行、业务条目后续经 R10/community 帧落地，点击仅打开内容（判据 C13）。验收取证用受控 fake 传输，不构造 Fake 映射宣称生产接通；上游扩展依赖已登记（community_deliveries.md §7）。

## 6. 业务通知列表与聚合/静音 UI（D-NC014-03/06）

### 6.1 业务表（宿主业务数据，包不负责；D-NC014-02）

`community_business_notifications` 列（冻结）：`notification_id`（PK，`ntf_<32 hex>`）、`owner_scope`、`kind`（comment|reply|mention|like）、`target_kind`（content|comment）、`target_id`、`thread_id`（可空）、`event_count`（integer ≥1）、`first_created_at`、`last_created_at`、`is_read`（bool，默认 false）、`body_markdown`（可空）、`actor_id`（可空）、`updated_at`。upsert 唯一键 `notification_id`：跨设备/用途重投不增加业务条目（DESIGN §6.1）；`event_count` 以最近一次 R10/community 帧值为准覆盖。同库另建 `community_notification_dedup`（§4.1）与 `community_notification_meta`（key PK、value、updated_at；存 R10 cursor 与 `push_config_cache`）。

### 6.2 列表映射（social `NotificationCenterPage` 复用）

`SocialNotificationItem{id, title, body, createdAt, isRead, isAnonymous, targetRoute?}`（`social/lib/src/notification/social_notification_models.dart:7-24`）映射：`id`=`notification_id`、`createdAt`=`last_created_at`、`isRead`=`is_read`、`isAnonymous` 恒 `false`（INTEGRATION_BASELINE.md:12 注解系统不启用匿名入口）、`targetRoute` 不使用（导航由 `onNotificationTapped`→router 承担）、`title` 按 kind 固定文案 comment→「收到新评论」、reply→「收到回复」、mention→「有人@了我」、like→「收到赞」，且 `event_count > 1` 时追加「（N 条）」展示聚合计数（N=`event_count`，D-NC014-06）、`body`=`body_markdown`（空则空串）。条目点击后宿主写 `is_read=true`（ACK 与已读分离）。actor 展示名无现成端点（REST 3.1 无按 actor_id 取展示名的社区端点），列表不展示昵称（§9 缺口 4）。

### 6.3 聚合

列表条目按 R10 读时聚合口径呈现：`event_count` 计数 + `last_created_at` 排序；`reply`/`mention` 恒单条（服务端已保证）。宿主不二次聚合、不新增合并窗口常量（10 分钟窗口属服务端 R10 行为，community_deliveries.md §6.2）。

### 6.4 静音入口（W15/W16）

`CommunityNotificationMuteApi`：`PUT/DELETE /v1/community/notifications/mutes/{content_id}`（Bearer 头同 `community_api.dart:103-110` 范式；`content_id` 非 `note_` → 400 `invalid_argument.content_id`；幂等、非命令写、限流 30/min，community_api.md §13.2/§13.5）。入口位于内容详情页的「不再接收此内容的通知」（DESIGN §6.3）。宿主聚合/静音粒度的 NC-001 核实记录归 NC-001（E-WIRING，D-NC014-06；判据 C18）。

## 7. 测试判据（名称逐字；两线合计 26 个 = PACKAGE 8 + CLIENT 18）

| # | 仓库目录 | 命令 | 期望 |
|---|---|---|---|
| 1 | notification | `flutter test` | `+202: All tests passed!`（194 既有 + 8 新增；既有零变红） |
| 2 | notification | `flutter test test/receive/dedup_retention_test.dart` | `+8: All tests passed!` |
| 3 | reading-notes | `flutter analyze` | `No issues found!` |
| 4 | reading-notes | `flutter test test/notifications/community_notifications_test.dart` | `+18: All tests passed!` |
| 5 | reading-notes | `flutter test` | `+314: All tests passed!`（296 既有 + 18 新增；既有零变红） |
| 6 | learn_system | `bash docs/blackbox-spec-rework/reviews/nc014_guard.sh --require-impl all` | 退出 0 |

### 7.1 PACKAGE（`test/receive/dedup_retention_test.dart`，P01～P08）

```
push_timing_parses_dedup_retention_ms_from_l2_timing
push_timing_parses_absent_dedup_retention_ms_as_null_without_fallback
push_timing_rejects_non_positive_dedup_retention_ms
package_sources_contain_no_hardcoded_dedup_window_literal
dedup_retention_marks_entry_expired_exactly_at_window_boundary
dedup_retention_keeps_entries_strictly_inside_window
dedup_retention_trim_forgets_expired_ids_only
dedup_retention_is_exported_from_package_barrel
```

### 7.2 CLIENT（`test/notifications/community_notifications_test.dart`，C01～C18）

```
community_frame_dispatch_routes_notifier_push_and_resync_to_package_pipeline
community_frame_dispatch_routes_community_data_to_business_upsert_without_delivery_id
community_delivery_log_adapter_persists_and_reports_was_duplicate
community_delivery_log_acks_each_device_and_purpose_delivery_verbatim
community_delivery_log_acks_new_delivery_when_business_entry_already_exists
community_persist_failure_sends_no_ack_and_advances_no_cursor
community_delivery_log_trims_dedup_rows_by_package_retention_window
community_receipt_transport_sends_batch_verbatim_to_notifier_receipts
community_receipt_rejection_settles_batch_observable_without_probing
community_connection_token_source_obtains_authorized_channels
community_backfill_source_maps_r10_page_without_transport_ids
community_backfill_entries_upsert_business_list_by_notification_id
community_message_body_fetcher_degrades_when_r9_is_unauthorized_404
community_notification_list_shows_event_count_aggregation
community_notification_tap_opens_content_detail_discussion_top
community_notification_tap_inaccessible_target_lands_unified_placeholder
community_notification_tables_are_scoped_by_account_switch
community_mute_entry_puts_and_deletes_content_mute
```

C06 即 TASKS:232 的「落盘失败不 ACK」失败分支判据：fake 按注入返回 `DeliveryPersistFailed`，断言 receipt 缓冲为空（ACK 未发出）且 cursor 未推进；全程不存在「永远返回 `DeliveryPersisted()` 的 fake」充当该证据。Red 要求：act/01 先写 8 测试跑 `flutter test test/receive/dedup_retention_test.dart` 保存编译错原文（`dedupRetention`/`DedupRetention` 未定义）；act/02 先写 pubspec 依赖跑 `flutter pub get`、再写 18 测试跑单文件，保存「依赖缺失/文件未建」失败原文。

## 8. REST/服务端引用（全程只读，不新增任何端点）

- R9 `GET /v1/community/notifications/pull?notifier_delivery_id=<原始值>` → 200 `NotificationBody`；四类失败 404 共用 `NotFoundContent`；`notifier_delivery_id` 缺失 400 `invalid_argument.notifier_delivery_id`（community_api.md §13.1/§13.4）。
- R10 `GET /v1/community/notifications?cursor&limit` → 200 `NotificationPage{items: NotificationEntry[], next_cursor}`；游标 `^[A-Za-z0-9_-]{1,512}$`，非法 400 `invalid_argument.cursor`；limit 1..100 默认 20；补拉不产生任何 ACK（§13.1）。
- W15/W16 `PUT|DELETE /v1/community/notifications/mutes/{content_id}` → 200 `NotificationMuteState{content_id, muted}`（§13.2）。
- `NotificationBody`/`NotificationEntry` 字段与 `additionalProperties: false` 以 REST `openapi/openapi.yaml:3777-3904` 为准；`target` 仅 `kind/id/thread_id?` 三字段。
- notifier 3.0.3 端点（`/v1/client-config`、`/receipts`、`/auth/rt/connection-token`、`/push/tokens`）只引用不复制；REST 仓与 functions-py 仓本任务零写入、零新端点。

## 9. 已知缺口

| 编号 | 缺口 | 处置 |
|---|---|---|
| G-NC014-1 | R9 生产绑定写入通道缺证（上游 G2，D-NC013-08）：生产环境绑定零写入，R9 必 404 | adapter 照常实现；验收用受控 fake 传输（D-NC014-04）；上游扩展依赖登记于 community_deliveries.md §7 |
| G-NC014-2 | comment 类 target（reply/mention/评论赞）缺 `content_id`（`target` 仅 kind/id/thread_id，thread_id 为 SHA256 不可逆），内容详情页无法构造 | D-NC014-11；本期仅 content 类导航，comment 维度降级为不路由 |
| G-NC014-3 | 真机 FCM 链路（插件、后台消息、`PushTokenRegistry`/token 获取） | 归 NC-024，用 NC-001 登记设备单独验证（TASKS:234；D-NC014-07） |
| G-NC014-4 | actor 展示名无社区端点（`NotificationBody.actor_id` 为 appUserId） | 列表按 kind 固定文案 + `event_count` 计数呈现，不展示昵称（§6.2） |
| G-NC014-5 | 宿主聚合/静音粒度的 NC-001 核实记录（E-WIRING） | 归 NC-001 记录（D-NC014-06）；本期粒度按 §6.3/§6.4 交付 |

## 10. 决定登记（主 Agent 裁定冻结；草案增补可推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC014-01 | 回跳挂靠：复用 social 普通通知中心组件（`NotificationCenterPage`）作业务表现层；不装配 notification 包遗留 `PlaygroundNotificationPage`；导航路由归宿主 | INTEGRATION_BASELINE.md:12,66 预备记录；TASKS:230 裁定权归 NC-001，主 Agent 冻结采纳其预备记录 |
| D-NC014-02 | 归属边界：行为层/帧解码/`dedup_retention_ms` 解析与裁剪（from-server-coder D.6）归 notification 包；宿主只做端口 adapter（`DeliveryLog`→宿主 Drift 持久去重表、`RealtimeChannel`→FCM/SSE、`ReceiptTransport`→notifier /receipts、`BackfillSource`→R10、`MessageBodyFetcher`→R9、`RemoteConfigSource`/`PushConfigCache`/`ConnectionTokenSource`→notifier L2/本地）、装配与导航路由；宿主另建「业务通知列表 upsert by notification_id」Drift 表 | integration-guide.md:8-14「本包⛔不含任何具体 adapter」+ README 归属铁律的组合边界；业务表无包内落点 |
| D-NC014-03 | 补拉旁路 ACK：R10 补拉条目不产生传输 ID、不进 AckPipeline；落宿主业务表即完成 | TASKS:229「业务补拉不制造传输 ID 或无来源 ACK」；R10 `NotificationEntry` 无 deliveryId 字段（openapi.yaml:3826-3874） |
| D-NC014-04 | R9 生产降级：adapter 照常实现；生产绑定缺失（上游 G2，D-NC013-08）时 R9 必 404，客户端按「正文不可用」降级（点击仅打开内容）；验收取证用受控 fake 传输；登记上游扩展依赖 | community_deliveries.md §7/§12 G2；不存在性 oracle 共用体不可区分 |
| D-NC014-05 | 楼层定位：本期导航到内容详情讨论区顶部；按 `comment_id` 深链定位楼层 DEFERRED（无按 id 取单评论端点） | R2 为唯一评论读入口且按 content 分页；DESIGN §6.3 楼层定位依赖上游能力 |
| D-NC014-06 | 聚合/静音 UI：列表条目按 `NotificationEntry.event_count` 展示聚合计数；详情页「不再接收此内容的通知」入口接 W15/W16；E-WIRING 核实项登记归 NC-001 记录 | DESIGN §6.3；TASKS:66 ⑨；community_deliveries.md §12 G4「展示侧归 NC-014」 |
| D-NC014-07 | 真机链路：FCM 真机验证归 NC-024；本任务全部经接口 fake/monkeypatch 验收 | TASKS:234；NC-001-02 设备联调未完成 |
| D-NC014-08 | 双帧形状：宿主唤醒入口分派 notifier 帧（`type:push|resync`，含 `deliveryId`，走包内既有管线）与 NC-013 FCM data（`type:community`，仅 `notification_id`+`event_count`，走「业务 upsert+R10 补拉」路径，不制造传输 ID） | 两类闭集形状事实（`notification_dispatch.py:332-340` 与 from-server-coder §S1.1）；按 `type` 字段区分 |
| D-NC014-09 | CLIENT 表落点与依赖：三表（去重/业务/meta）落新库 `CommunityNotificationDatabase`（独立文件 `reading_notes_notifications_$scopeUid.sqlite`，`schemaVersion 1`，onCreate 建表），不改既有 `community_database.dart`；`pubspec.yaml` 除 `notification` 外追加 `social` git 依赖（`NotificationCenterPage` 经 `lib/social.dart:91` 公开导出） | TASKS:228 白名单三文件不扩；D-NC014-01 复用 social 组件的机械后果是 social 依赖；避免动既有库迁移 |
| D-NC014-10 | `dedup_retention_ms` 可空解析：键进 `PushTiming._allowedKeys`，`dedupRetention` 可空（缺→`null`、无兜底），宿主装配遇 `null` 停手上报 | 改必填将打破既有 `push_config_resolver_test` fixture（194 全绿约束）；符合包内「无兜底值」惯例（`test/config/push_config_test.dart`） |

### 10.1 裁定记录（主 Agent 审查裁定，2026-09-13）

1. **comment 类 target 缺 `content_id`** → **D-NC014-11**：本期维持降级（仅 content 类导航，comment 类条目展示不路由）；「3.1 契约扩展 `target.content_id`」登记为上游契约扩展候选（候选评估：服务端组装 NotificationEntry 时可经 `community_comments` 反查 content_id，属可实现的后续小改），候选并入下一个写 openapi.yaml 的串行棒（NC-026 §14 或后续）评估，本期不动已关单的 NC-013 面。裁定理由：改动需重开 NC-013 契约/实现/示例/验收，成本与本期价值不成比例；宿主本地映射（候选②）覆盖不全被否。
2. **D-NC014-09/10**：主 Agent 审查通过、正式冻结（编号不变）。09 的 social 依赖链风险与 10 的可空解析交四查覆盖复核。
3. **D-NC014-01 门禁状态**：维持按 NC-001 预备记录冻结执行；NC-001 走完门禁后如推翻，导航路由按新裁定返工（仅 router 一处，隔离成本可控）。
