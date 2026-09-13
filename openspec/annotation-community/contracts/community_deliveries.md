# 服务端契约：事务事件消费、通知投递、正文拉取与补拉端点（NC-013）

状态：`FROZEN_FOR_NC-013`（2026-09-12）。权威来源：[community_api.md](community_api.md)（§13 为本任务 API 补丁；端点/头/错误/Schema 唯一来源）；[DESIGN](../DESIGN.md) §6、§6.1、§6.2、§6.2.1、§6.3、§2.1.1、§7.2；[state-machines](state-machines.md) SM-7；[community-models](community-models.md) §3.1、§3.2；[PRD](../PRD.md) R-11、R-20、E-NOTIFIER、E-DEDUP；[TASKS](../TASKS.md) NC-013；SERVER 现状（2026-09-12，HEAD `8d22451`）；上游 notifier 权威契约只读（`xuan-server/notifier/api/openapi.yaml`，3.0.3）。本文把已定设计落到 functions-py 的模块、集合、消费流程与测试判据，供执行者照抄；与上游冲突以上游为准并回报主 Agent。语义红线：**投递为 at-least-once；「原子」仅指投递记录终态在同一事务内写入一次，不构成端到端 exactly-once；任何文档、注释、测试名不得出现 exactly-once**。

## 1. 仓库、环境与基线

| 项 | 实值 |
|---|---|
| SERVER（写入目标） | Windows：`D:/Programme/xuan-server/functions-py`（master，HEAD `8d22451`；macOS 对应 `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`，D-NC012-23） |
| RULES | Windows：`D:/Programme/xuan-server/xuan-server`（main，HEAD `4b81d8d`），规则测试在 `server/functions/test/` |
| REST | Windows：`D:/Programme/xuan/repository-rest-adapter`（main，HEAD `cb686d0`），唯一 3.1 OpenAPI |
| NOTIFIER | **全程只读**：Windows `D:/Programme/xuan-server/server-notifier`；`api/openapi.yaml` 3.0.3 权威，⛔ 不复制契约正文 |
| Emulator | Firestore `192.168.0.165:8080`、Auth `192.168.0.165:9099`（pytest 必须） |
| Python | `functions-py/.venv/Scripts/python.exe`（Windows）/ `.venv/bin/python`（macOS） |
| 既有基线 | 全量 pytest `5 failed, 535 passed, 6 xfailed`，FAILED 恰为 `tests/test_config.py::test_集合名与_ts_逐项一致` 与 `tests/test_registration.py` 四项（**test_registration 在 HEAD 上已红为既有缺口**，D-NC013-13）；规则 `Tests: 129 passed`；REST `dart test` `+77: All tests passed!` |
| 时间戳 | 社区域一律 UTC ISO 字符串 `%Y-%m-%dT%H:%M:%S.%fZ`（D-NC013-14），不用 `SERVER_TIMESTAMP` |

## 2. 模块与集合

### 2.1 新增/修改文件（写入白名单）

| 仓库 | 文件 | 内容 |
|---|---|---|
| SERVER | `xuan/config.py` | `COLLECTIONS` 追加 §2.2 三个键（**只追加**） |
| SERVER | `main.py` | 追加 import 与注册 `community_deliveries_py`、`community_outbox_dispatch_py`、`advance_community_deliveries_py`（**只追加**） |
| SERVER | `xuan/community/notification_dispatch.py`（新增） | §3、§4、§5：事件消费纯函数、收件人判定、ntf_ ID、投递状态机、聚合 |
| SERVER | `xuan/handlers/community_deliveries.py`（新增） | §6：`community_deliveries_py`（on_request：R9/R10/W15/W16）、`community_outbox_dispatch_py`（on_document_created 薄壳 ≤12 行）、`advance_community_deliveries_py`（on_schedule every 1 minutes 薄壳） |
| SERVER | `tests/test_community_deliveries.py`（新增） | §9 测试 |
| SERVER | `tests/conftest.py` | `clean_collections` 的 `names` 追加三个新集合（**只追加**） |
| SERVER | `tests/test_community_acl_sweep.py` | **仅 E6 转真**（D-NC013-12）：删 E6 三条 `xfail(strict=True)`、E6 分支改调 `community_deliveries_py` 并先 seed 通知与绑定、模块 docstring Implemented/Unimplemented 两行同步 |
| RULES | `server/functions/test/community_rules.test.ts` | §8：三个新集合的默认拒绝用例（只追加） |
| REST | `openapi/openapi.yaml` | §10：R9/R10/W15/W16 三条路径、`NotificationEntry/NotificationPage/NotificationBody/NotificationMuteState` 四个 Schema、`NotifierDeliveryId` 头外查询参数、§13 错误行与限流行 |
| REST | `test/community_openapi_contract_test.dart` | 末尾追加 4 个测试；`expectedCatalog` 追加三行；`interaction examples manifest has seventeen entries and validates` 的 `equals(17)` 改 `greaterThanOrEqualTo(17)`（D-NC013-10） |
| REST | `test/fixtures/openapi/examples/` | 新增 3 个示例 JSON 并在 `manifest.json` 末尾追加 3 项（§10.4） |

**禁止**：改 `xuan/handlers/notifications.py`（既有消费者，不识别的类型必须原样忽略，本任务测试断言其 no-op 不抛错）；改 `tests/test_registration.py`、`tests/test_main_exports.py`（注册闸门既有红，D-NC013-13）；改 `openspec/schemas/`（NC-002 冻结）；改 NOTIFIER 仓任何文件；新依赖；`skip`；新增 `xfail`（E6 三条删除除外）；永真断言；测试内计算参考值；`git push`；learn_system 写入（交付报告除外）。

### 2.2 新增 Firestore 集合（`COLLECTIONS` 键 → 集合名）与文档

| 键 | 集合 | 文档 ID | 字段 |
|---|---|---|---|
| `community_notifications` | `community_notifications` | `notification_id`（`ntf_<32 hex>`，§3.3 确定性派生） | NC-002 `community_notification_record.schema.json` 全部 8 个必填字段（`notification_id, event_id, recipient_id, target{kind,id,thread_id?}, delivery_state, attempt_count, created_at, updated_at`；`additionalProperties: false`，**禁止**加任何字段，含聚合计数、已读、next_attempt_at） |
| `community_notifier_delivery_bindings` | `community_notifier_delivery_bindings` | `SHA256_hex(UTF8(notifier_delivery_id))`（64 hex，DESIGN §2.1.1） | NC-002 `community_notifier_delivery_binding.schema.json` 全部 8 个必填字段；`notifier_delivery_id` 为上游原始不透明值**逐字保存**（禁前缀/截断/重算）；`write_source ∈ {trusted_ingress, trusted_delivery_callback}` |
| `community_notification_mutes` | `community_notification_mutes` | `nmute_ + SHA256_hex(community_hash.encode(["mute", recipient_id, content_id]))[:32]` | `mute_id, recipient_id, content_id, created_at` |

outbox 沿用 `COLLECTIONS["outbox"]`（`playground_outbox`），既有事件文档字段与类型见 `community_server.md` §2.2 末段；本任务消费闭集见 §3.1。Firestore 安全规则：三个新集合**不新增任何 match**，由顶层默认拒绝覆盖（§8 用规则单测证明）。

## 3. 事件消费与收件人判定（`xuan/community/notification_dispatch.py`）

### 3.1 订阅轨道与纯函数（D-NC013-01）

- 触发薄壳 `community_outbox_dispatch_py`：`@firestore_fn.on_document_created(document=COLLECTIONS["outbox"] + "/{docId}", region=REGION)`，函数体 ≤12 行，只做取参数与转发纯函数 `dispatch_outbox_event(event_id, data, now, client=None)`（范式同 `xuan/handlers/notifications.py:151-160` 与 `tests/test_notifications.py` 的源码断言）。
- 调度薄壳 `advance_community_deliveries_py`：`@scheduler_fn.on_schedule(schedule="every 1 minutes", region=REGION)`，转发 `advance_deliveries(now, client=None)`。
- **pytest 一律直接调用纯函数**（Emulator 不触发 trigger/scheduler；`now` 显式注入，范式 `tests/test_community_commands.py:353`）；触发器端到端验证归 tools/replay 体系，不在本任务测试判据内。
- `dispatch_outbox_event` 幂等：同一 `(event_id, data)` 重复投递（at-least-once）产出与首次完全一致；全部写操作在单个 Firestore 事务内（Aborted 重跑无半成品，§9 T 名 `dispatch_transaction_replay_leaves_no_partial_records`）。

### 3.2 消费闭集与 no-op（D-NC013-02）

| event_type | 语义 |
|---|---|
| `comment.created` | §3.3 收件人判定 → §3.4 创建通知记录（kind=comment/reply/mention） |
| `reaction.liked` | §3.3 → 创建（kind=like） |
| `comment.edited` / `comment.deleted` | 解析成功但**无通知语义**：幂等 no-op（编辑不重复提醒、删除不产生通知；上游保证重复保存相同 mention 不反复提醒） |
| `content.*`（六类）与旧广场事件（`like_added/like_removed/user_followed/user_unfollowed/dm_accepted/dm_message/reply_verified/verification_revoked`） | 不识别即原样忽略，**不抛错**（沿 `community_server.md` §2.2 末段既有义务） |

### 3.3 收件人矩阵（D-NC013-03）

事件载荷不含作者/mentions，消费侧必须回读：评论作者与 `reply_to_id`/`root_id` 读 `community_comments`，评论 mentions 读 `community_comment_revisions`（当前修订），内容作者读 `community_content_access.author_id`。

| 事件 | kind | 收件人 | 备注 |
|---|---|---|---|
| `comment.created` 且 `reply_to_id` 非空 | `reply` | 直接回复目标评论的作者 | 定位楼层（target.kind=comment, id=reply_to_id, thread_id） |
| `comment.created` 且 `reply_to_id` 为空 | `comment` | 内容作者 | target.kind=content, id=content_id |
| `comment.created` 的每个有效 mention | `mention` | 该 mention 的 `user_id` | target 同所在评论（kind=comment, id=comment_id, thread_id）；无效 mention（文本不匹配）生产端已过滤 |
| `reaction.liked` 且 `target_type=content` | `like` | 内容作者 | |
| `reaction.liked` 且 `target_type=comment` | `like` | 评论作者 | |

合并规则（DESIGN §6「作者/回复对象/@ 重叠合并」）：同一事件的收件人集合**先去重后建记录**；同一 recipient 命中 reply 与 mention 时**只留 reply**（单条、定位楼层）；命中 comment（内容作者）与 reply/mention 时按上表行优先级取**一种** kind（reply > mention > comment > like 的判定顺序：按行自上而下首个命中）。`actor_app_user_id == recipient` 一律跳过（无自通知）。回读失败（评论/作者/修订缺失）→ 该 recipient 跳过并继续其余 recipient，不抛错。

### 3.4 创建记录（D-NC013-04）

- `notification_id = "ntf_" + SHA256_hex(community_hash.encode([event_id, recipient_id]))[:32]`；E 编码逐字按 DESIGN §7.2（数组 `a2:s<len>:...s<len>:...`，字符串取 UTF-8 字节数前缀）。实现复用 `xuan/community_hash.py::encode`（先例 `ids.server_event_id`）。
- 写入用事务内 **`tx.create()`（create-if-absent）**：文档已存在（含并发双写第二次）→ 捕获 `AlreadyExists`，视为成功且**不修改**既有文档；禁止「先 query 查重再写」（DESIGN §6 明令禁止照抄 `notifications.py`）。
- `target.thread_id` 仅评论类事件填写（`thr_` 由 `thread_id_for(content_id)` 同构推导）；like 的 target 无 thread_id。
- `delivery_state` 初值 `created`，`attempt_count = 0`，`created_at = updated_at = now`。
- §9 提供 M 向量测试：3 组固定 `(event_id, recipient_id)`（含 emoji 与 CJK 字节）对照期望 `ntf_` 32 hex **字面量**（主 Agent 独立复算后写死在契约与测试中，见 §9 参考值）。

## 4. 投递状态机（SM-7 落地；`advance_deliveries`）

`advance_deliveries(now, client=None)` 单次 pass，处理 `community_notifications` 中非终态记录；**推送重试状态与记录创建分离**（创建只发生在 §3.4）。

| 转移 | 判定（顺序即实现顺序） | 动作 |
|---|---|---|
| created → dispatching | 领用成功：目标 `resolve_access`/评论可见性 = 可见（作者本人 owner 亦通过）；双向拉黑不存在；非静音（mention 记录绕过静音）；attempt_count+1 | 写 `dispatching` 与 `updated_at=now` |
| created → abandoned | 上述任一前置不满足 | 写 `abandoned`（attempt_count 保持 0），**无推送尝试** |
| dispatching → delivered | 投递尝试成功：kind=`like` 为**站内语义**（记录已可经 R10 读出，零 NotifierDeliveryBinding、无外部推送，D-NC013-07）；kind=`reply/mention/comment` 为 FCM 无正文唤醒尝试成功（§4.1） | 写 `delivered` |
| dispatching → failed | FCM 尝试失败/超时 | 写 `failed`，`updated_at=now` |
| failed → dispatching | 重试到期：`now >= updated_at + [1,2,4,8][attempt_count-1]` 秒（退避由 `updated_at` 与 `attempt_count` **推导**，不新增字段）；attempt_count+1 | 写 `dispatching` |
| failed → abandoned | `attempt_count >= 5` | 写 `abandoned`（终态） |
| delivered / abandoned | 任意后续 pass | 终态不变（重复推送不回滚，客户端按原样 deliveryId 去重 7 天——口径引用，实现属 NC-014） |

4.1 FCM 唤醒：复用 `xuan/push.py::send_push_notification(recipient_app_user_id, title, body, data)`，`title=""`、`body=""`（**无正文唤醒**，DESIGN「系统推送沿用无正文唤醒，点击重新鉴权」），`data={"type": "community", "notification_id": <ntf_>, "event_count": <窗口内同类事件数，首试=1>}`（服务端内部负载，不属冻结 Schema）；测试经既有 `_send_multicast` monkeypatch 拦截（`tests/test_notifications.py:14-22` 范式）。单一 recipient 多设备由 push.py 既有 token 查询承担，本任务不校验设备归属（D-NC013-08，上游缺口）。**本 pass 内每条记录至多一次尝试**；pass 之间经调度器每分钟驱动，p95<5 s 的时延设计以「触发器同步首试」满足（§3.1 触发器调用 `dispatch_outbox_event` 后立即对新建记录执行一次 `advance_deliveries`；Emulator 无 p95 测量，登记为运维验证项）。

## 5. 聚合与静音（DESIGN §6.3）

- **聚合（D-NC013-06）**：kind ∈ `comment`、`like` 参与合并；`reply`、`mention` **永不合并**。聚合窗口 = 10 分钟，滑窗锚定该 recipient+target+kind 的窗口首事件 `created_at`；窗口内后续事件**仍创建独立记录**（记录逐事件、确定性 ID），但**不重复推送**（`advance_deliveries` 对窗口内已有同锚 delivered 记录的新记录直接置 `delivered`，attempt_count=1，无 FCM 尝试）；「合并为一条」的展示由 R10 读取端点窗口聚合返回（§6.2）与客户端渲染（NC-014，宿主聚合粒度由 NC-001 核实，E-WIRING 缺口不在本任务）。推送文案的「张三等 N 人」计数在推送 data 中携带 `event_count`（现算）并写入推送 data 的 `event_count` 字段（§4.1）。
- **静音（D-NC013-05）**：W15/W16 写 `community_notification_mutes`（§6.3）；领用判定时，`kind=comment/like` 命中静音 → abandoned，`kind=mention` **绕过静音**仍送达。
- **拉黑**：读 `COLLECTIONS["blocks"]`（键 `block_${a}_${b}`），actor 与 recipient 任一方向存在即拒绝（社区自身无拉黑写端点，数据由宿主社交注入产生——NC-012b 范围）。
- **偏好**：社区通知本期无「系统提醒」事件源，偏好过滤函数签名预留（`preference_allows(recipient, kind, now)` 返回 True）但不接数据源（D-NC013-05；接偏好归 NC-014/上游）。

## 6. HTTP 端点（`xuan/handlers/community_deliveries.py`）

认证同既有 `_authenticate_and_resolve` 范式（Bearer → `owner_scope`）；失败 401 `unauthenticated`。

### 6.1 R9 通知正文拉取（`GET /v1/community/notifications/pull?notifier_delivery_id=<原始值>`）

1. `notifier_delivery_id` 缺失 → 400 `invalid_argument.notifier_delivery_id`；**逐字**当作不透明值（禁前缀/截断/重算/解码 HMAC，D-NC013-08）。
2. 以 `SHA256_hex(UTF8(delivery_id))`查 `community_notifier_delivery_bindings`；缺失 → 统一 404 共用体。
3. 取绑定 `notification_id` → 读 `community_notifications`；缺失或 `recipient_scope != owner_scope` → 统一 404 共用体（设备归属校验待上游接口，D-NC013-08；本期仅校验登录接收人）。
4. 按 target 解析当前内容 ACL（content → `resolve_access`；comment → `resolve_target` 同构），不可读（withdrawn/trashed/hidden/删除）→ 统一 404 共用体；**四种失败共用同一响应体与状态**，`$ref NotFoundContent`（防存在性 oracle，R-20）。
5. 成功 → 200 `NotificationBody`：`{notification_id, kind, target, body_markdown, actor_id, created_at}`；`body_markdown` = comment 类取当前修订 `body`（修订缺失/被删 → 404 共用体），like取快照 `title`。

### 6.2 R10 业务通知补拉（`GET /v1/community/notifications?cursor&limit`）

- 仅返回登录人 `recipient_id` 的记录；`cursor`/`limit` 实值沿 community_api §6（limit 1～100 默认 20；非法 → 400 `invalid_argument.cursor|limit`）。
- **读时聚合**：按 `(recipient, target.kind+target.id, kind)` 分组，滑窗 10 分钟（锚=窗口首 `created_at`；`reply/mention` 不分组）；`reply/mention` 单条呈现。窗口分组内：`latest_notification_id` = 窗口内最新记录（定位楼层）、`event_count` = 窗口内记录数、`first_created_at/last_created_at`。
- 排序与游标：按 `(first_created_at, latest_notification_id)` 降序（ID 按 UTF-8 字节序比较，跨端稳定）；`next_cursor` = base64url(`"{first_created_at}|{latest_notification_id}"`)，`^[A-Za-z0-9_-]{1,512}$`；**游标不回退**（同游标重复请求结果集不包含已返回项的更早项）。不产生任何 ACK（D-NC013-11）。

### 6.3 W15/W16 按内容静音（非命令直写；D-NC013-09）

- `PUT /v1/community/notifications/mutes/{content_id}` → 200 `{"content_id": ..., "muted": true}`；`DELETE` 同路径 → 200 `{"content_id": ..., "muted": false}`。幂等（重复 PUT/DELETE 结果不变）；无 `Idempotency-Key`、不进命令账本、不写行为事件（`content_id` 非 `note_` 格式 → 400 `invalid_argument.content_id`）。操作枚举闭集 17 个**不变**。限流并入读端点 600/min 桶之外单列 30/min（community_api §13.5）。

### 6.4 E6 转真（D-NC013-12）

`tests/test_community_acl_sweep.py` E6 三例删除 `xfail(strict=True, reason="owner: NC-013")`，分支改为：seed 内容至对应 reason 态 → 以 seed 直写为 viewer 建 `community_notifications` 记录与 `trusted_ingress` 绑定（模拟可信来源）→ `call(community_deliveries_py, "GET", f"/v1/community/notifications/pull?notifier_delivery_id={delivery_id}", headers=...)` → 断言 404、`code == not_found.content`、响应体逐字节等于 `SHARED_NOT_FOUND_CONTENT_BODY`、不含标题/正文任意 20 字连续片段。模块 docstring 两行同步为 `E1, E2, E4, E5, E6 (15 live assertions)` / `Unimplemented entries: E3 (3 strict xfail assertions marked with owner)`。

## 7. 桥接映射与缺证阻断（DESIGN §6.2.1 / R2-01 落地）

- 本任务交付：`community_notifier_delivery_bindings` 集合与 Schema 落库、R9 的映射**读取**路径、绑定文档 ID 规则（SHA-256 hex）。
- **生产写入通道缺证阻断（D-NC013-08）**：现上游 notifier 契约（12 端点穷举）无任何「把 deliveryId 关联到业务事件/收件人」的回推或查询接口（`OPENSPEC-PUSH-CELL.md:83-94,301`：S1.6/S1.7 属上游业务子系统；deliveryId 为 HMAC 不透明值）。所需上游扩展（登记，不实现）：①投递回执回调（notifier → functions-py，携带原始 deliveryId + eventId + deviceId + channelPurpose，即 `write_source=trusted_delivery_callback`）；或 ②入站投递声明接口（`trusted_ingress`）。缺此接口前：生产环境绑定零写入，`trusted_ingress/trusted_delivery_callback` 仅为本地允许类别；测试以 seed 直写模拟可信来源；**不得**构造 Fake 映射宣称接通、不得假设客户端回传即可信。此停点由主 Agent 在验收时核对为「已登记的阻断」而非「遗漏」。
- 客户端不能声明所属账号、不能经猜 ID 取得正文（R9 步骤 3 的接收人校验）。补拉与已读用 `notification_id`，不伪造传输 ID；**ACK 属 notifier 契约，本任务不实现、不复制、不在 3.1 中重定义**（D-NC013-11）。

## 8. Firestore 安全规则（RULES）

三个新集合不新增 match，由顶层 `match /{document=**} allow read, write: if false` 默认拒绝覆盖。`server/functions/test/community_rules.test.ts` 按既有 per-collection 模式追加 3 集合 × 8 用例（authenticated/unauthenticated × read/write × owner/other 语境，照 `community_reactions` 现有 8 用例逐字仿写），合计 129 + 24 = **153**。

## 9. 测试判据（`tests/test_community_deliveries.py`）

命令（Emulator 必须）：`PYTHONDONTWRITEBYTECODE=1 FIRESTORE_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099 .venv/Scripts/python.exe -m pytest tests -q -rf -p no:cacheprovider`。期望：`5 failed, 568 passed, 3 xfailed`（= 基线 535 + 本任务 30（act/02 19 + act/03 11）+ E6 转真 3；FAILED 恰为五个既有 ID；E3 三例 xfail 保留）。Red：`from xuan.community import notification_dispatch` 的 ImportError 为 act/02 的 Red 原文。

测试名（逐字，30 个）：

```
dispatch_comment_created_notifies_content_author_with_deterministic_ntf_id
dispatch_comment_reply_notifies_reply_target_not_content_author
dispatch_comment_mention_notifies_mentioned_user
dispatch_mention_and_reply_overlap_creates_single_reply_record
dispatch_reaction_like_notifies_content_author
dispatch_reaction_like_notifies_comment_author
dispatch_self_event_never_notifies_actor
dispatch_same_event_twice_creates_single_record_create_if_absent
dispatch_concurrent_same_event_two_transactions_single_record
dispatch_unknown_event_type_is_idempotent_noop
dispatch_comment_edited_and_deleted_are_noop_without_records
dispatch_content_and_legacy_events_are_noop_without_records
dispatch_transaction_replay_leaves_no_partial_records
notification_id_matches_e_encoding_reference_vectors
notification_record_validates_frozen_schema
like_notification_is_in_app_only_delivered_without_push
comment_notification_attempts_fcm_wakeup_without_body
push_failure_marks_failed_with_backoff_1_2_4_8
retry_after_backoff_advances_and_fifth_failure_abandons
push_success_marks_delivered_and_readvance_is_stable
blocked_pair_abandons_without_push_attempt
muted_content_abandons_comment_but_mention_still_dispatches
inaccessible_target_abandons_without_push_attempt
notification_pull_returns_body_for_trusted_binding
notification_pull_unresolved_binding_is_shared_404
notification_pull_non_recipient_is_shared_404
notification_pull_deleted_comment_is_shared_404
notification_list_returns_merged_windows_and_single_mentions
notification_list_cursor_never_regresses_and_limit_bounds
notification_mute_set_unset_is_idempotent_non_command
```

参考值（字面量，测试内禁止现算，主 Agent 用 `xuan/community_hash.py::encode` 于 2026-09-12 复算后写死）：M 向量 3 组——
- `["evt_m1", "app-recipient1"]` → E 字节 `a2:s6:evt_m1s14:app-recipient1` → `ntf_f5b00f127444e70d78789b777bc91a51`
- `["evt_😀中文2", "app-recv2"]` → E 字节 `a2:s15:evt_😀中文2s9:app-recv2`（😀/中/文 各按 UTF-8 字节计长，合计 15）→ `ntf_71b0cac6b3574748b597eff5f3f28ee5`
- `["evt_zz3", "app-recipient3"]` → E 字节 `a2:s7:evt_zz3s14:app-recipient3` → `ntf_424a8073ca566cf03707ddc40bbb3878`

共享 404 体 = `xuan/community/errors.py:68-73` `SHARED_NOT_FOUND_CONTENT_BODY` 逐字节。Aborted 注入范式照 `tests/test_community_comments.py:1550-1640`（monkeypatch `Transaction._commit` + `raise Aborted("injected by test")`）。

## 10. REST §13 补丁内容（community_api.md §13；openapi.yaml 落地）

REST 结构测试（`test/community_openapi_contract_test.dart` 末尾追加，名称逐字）：`notification paths and methods match the catalog`、`notification schemas are closed objects with notificationRecordId`、`notification examples manifest has twenty entries and validates`、`notification mutes are non command writes with rate limit row`。

- **§13.1 新增读端点（R9/R10，目录追加）**：`R9 GET /notifications/pull?notifier_delivery_id → 200 NotificationBody / 失败 404 NotFoundContent`；`R10 GET /notifications?cursor&limit → 200 NotificationPage`。
- **§13.2 非命令写（W15/W16，目录注明「非命令」）**：`PUT /notifications/mutes/{content_id}`、`DELETE /notifications/mutes/{content_id}` → 200 `NotificationMuteState{content_id, muted}`。
- **§13.3 新 Schema（§5.3 追加）**：`NotificationBody{notification_id, kind(comment|reply|mention|like), target{kind,id,thread_id?}, body_markdown, actor_id, created_at}`；`NotificationEntry{kind, target, latest_notification_id, event_count, first_created_at, last_created_at}`；`NotificationPage{items, next_cursor}`；`NotificationMuteState{content_id, muted}`。可空写 3.1 类型数组；游标/limit 沿 §6；`notification_id` `$ref community_common.schema.json#/$defs/notificationRecordId`。
- **§13.4 错误目录增补（§4.1 追加行）**：`R9 notifier_delivery_id 缺失 → 400 invalid_argument.notifier_delivery_id`；`R9/R10 四类失败（映射缺失/非本人/设备不匹配/内容失权）→ 404 not_found.content 共用体（无可区分字段）`；`W15/W16 content_id 非法 → 400 invalid_argument.content_id`。
- **§13.5 限流（§6 表追加）**：`notifications.mute set/unset 30`；R9/R10 并入「全部读端点合计 600」。
- **§13.6 示例**：`notification_body_comment.json`、`notification_page_merged.json`、`notification_mute_set.json` 入 `manifest.json`（17 → 20 项；NC-012a 的 seventeen 测试改 ≥17，D-NC013-10）。
- **§13.7 决定**：本节决定编号 D-NC013-01～14，登记于 [community_deliveries.md](community_deliveries.md) §15。

## 11. 可观测性与不变量

- 投递记录创建到首次推送尝试：触发器同步首试（§4.1：触发器薄壳在 `dispatch_outbox_event` 后立即执行一次 `advance_deliveries`）；测试断言 `advance_deliveries` 首试后记录 `delivery_state ∈ {dispatching, delivered, failed, abandoned}`（不再是 `created`；`dispatch_outbox_event` 本身只建记录，BDD S01 的 `created` 初值不变）。
- 补拉游标不回退：§9 `notification_list_cursor_never_regresses_and_limit_bounds` 以「取页→插入更旧记录→同游标再取」断言结果集不变。
- 措辞红线扫描：守卫对三份新文件（`notification_dispatch.py`、`community_deliveries.py`、`test_community_deliveries.py`）机械扫描 `exactly-once` 零命中（K06）；含否定语境的红线表述仅存于本契约与 community_api §13.7，代码与测试不得出现该词。
- 不得在任何文档或注释声称 exactly-once（措辞禁区见文首红线；守卫机械扫描）。

## 12. 已知缺口与停手条件登记

| 编号 | 缺口 | 处置 |
|---|---|---|
| G1 | `tests/test_registration.py` 4 项在基线已红（main 导出 49 vs 清单 37），且与 `test_main_exports.py` 对 `on_outbox_created_py` 的断言矛盾 | 不修（不在白名单，D-NC013-13）；本任务新增入口经 main.py 注册后该 4 项仍红，FAILED 集合不变 |
| G2 | notifier→functions-py 的可信映射生产通道缺失 | §7 登记上游扩展并阻断；测试以 seed 模拟可信来源 |
| G3 | 设备归属校验无设备注册表 | R9 仅校验登录接收人；设备维度等上游接口（G2 一并登记） |
| G4 | 宿主聚合/静音粒度支持未知 | 展示侧归 NC-014；NC-001 核实（E-WIRING） |
| G5 | 偏好过滤无社区事件源 | §5 预留函数不接数据 |

执行者遇到下列情形**停手上报**（写入 DELIVERY_REPORT 并输出 `NC-013-<字母> 停手待裁决`）：参考值对不上；既有测试变红（5 个既有 FAILED 之外）；需改白名单外文件；Emulator 不可达；契约歧义。

## 13. 交付物与提交拆分

三线并行、同仓串行：REST act/01（`NC-013-A`）∥ SERVER act/02→03（`NC-013-B`→`NC-013-C`）∥ RULES act/04（`NC-013-D`）。每 act 独立提交；提交消息末尾空一行加 `Co-Authored-By: <执行模型> <厂商域>`。执行者不推送。

## 14. 主 Agent 盲测清单（验收用，临时文件不入库，结束删除并以三仓 `git status --short` 为空证明）

1. 并发 create-if-absent：两线程同 event 同 recipient → 恰 1 记录，第二事务无异常。
2. 退避边界精确：对 attempt_count=1..4 的 failed 记录分别注入 `now = updated_at + 0.9/1.9/3.9/7.9s`（四档均不到期）与 `+1.0/2.0/4.0/8.0s`（四档均到期，退避 1/2/4/8）。
3. R9 四种失败（无绑定/非本人/绑定但评论已删/内容 withdrawn）响应体逐字节相同。
4. E 编码向量 3 组与 §9 字面量一致。
5. mention 绕过静音、like 零 FCM 调用（`_send_multicast` 调用计数 0）。
6. 游标不回退：同游标重取在插入更旧记录后结果不变。
7. REST：`notification_page_merged.json` 翻转一字段登记为 valid 的临时 manifest → `check_examples.py` 退出 1。

## 15. 决定登记（主 Agent 裁定）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC013-01 | 消费轨道 = 新增 `community_outbox_dispatch_py` 触发薄壳 + `dispatch_outbox_event`/`advance_deliveries` 纯函数；pytest 仅测纯函数 | 既有 `on_outbox_created_py` 休眠且其消费者 `notifications.py` 不在白名单；Emulator 不能触发 trigger/scheduler（先例 `compact_once(now)`） |
| D-NC013-02 | 消费闭集：`comment.created`/`reaction.liked` 产通知；`comment.edited/deleted` 与 `content.*`/旧广场事件幂等 no-op | 编辑不重复提醒、删除无通知语义（记录无删除态）；不识别类型必须不抛错（community_server §2.2 既有义务） |
| D-NC013-03 | 收件人矩阵 §3.3；重叠合并取行优先级（reply > mention > comment）；自通知跳过；回读失败跳过该 recipient | 事件载荷无作者/mentions，回读是唯一事实源；DESIGN §6「作者/回复对象/@ 重叠合并」 |
| D-NC013-04 | `ntf_` doc ID 确定性派生 + `tx.create()` create-if-absent；禁先查后写 | DESIGN §6 逐字；并发幂等唯一正确实现 |
| D-NC013-05 | 过滤时点在领用；拉黑双向读 `blocks`；静音 mention 绕过；偏好预留不接源 | SM-7 领用前置；社区无拉黑写端点（NC-012b）；系统提醒无生产者 |
| D-NC013-06 | 记录逐事件；聚合在读时窗口分组 + 窗口内不重推；comment/like 可合并，reply/mention 永不合并 | 冻结 Schema `additionalProperties:false` 无聚合字段，「合并为一条」只能落在读取与推送层；DESIGN §6.3 |
| D-NC013-07 | like 站内零绑定 delivered；评论/回复/@ FCM 无正文唤醒（title/body 空串，data 携 notification_id）；退避由 updated_at+attempt_count 推导 | 冻结 Schema 无 next_attempt_at；PRD「赞站内」；DESIGN「无正文唤醒」 |
| D-NC013-08 | 桥接映射生产写入通道缺证阻断；交付读取路径与集合；测试 seed 模拟可信来源 | DESIGN §6.2.1「缺证阻断，不接受客户端回填」；上游 12 端点无关联接口 |
| D-NC013-09 | R9/R10 读端点 + W15/W16 非命令直写静音；操作枚举闭集 17 不变 | 静音幂等无审计需求，扩枚举需动 NC-002 冻结 Schema，收益不成比例 |
| D-NC013-10 | 示例 17→20；NC-012a seventeen 测试与 nc012a_guard K05 同步 ≥17 | 同 D-NC012-22 先例：清单型断言随任务同步而非放宽语义 |
| D-NC013-11 | 已读不落服务端；ACK 不实现不复制；补拉不产生 ACK | 冻结 Schema 无已读字段；ACK 属 notifier 3.0.3；TASKS NC-013 R1 修正 |
| D-NC013-12 | E6 三例删 xfail 转真并改调 `community_deliveries_py`；docstring 两行同步 | D-NC009-05 strict xfail 机制要求接手任务删标记 |
| D-NC013-13 | 注册闸门既有红不修；FAILED 集合断言仍为五个既有 ID | test_registration 不在白名单；新增入口不改变其失败集合 |
| D-NC013-14 | 时间戳 UTC ISO 字符串；拉黑键复用 playground `block_${a}_${b}` 惯例 | 社区域既有惯例；游标稳定性依赖字符串排序 |
| D-NC013-15 | `community_notification_mutes` 文档 ID 前缀 `nmute_`（`nmute_<32 hex>`）为本任务新增的服务端内部对象前缀，已在 DESIGN §2.1 前缀表登记（2026-09-12 主 Agent） | DESIGN §2.1 前缀表原为 17 类闭集；静音集合无既有前缀可复用，内部对象不经 REST 暴露 ID，登记即闭环 |
| D-NC013-16 | REST 开工基线认可 `3f34f0f`（= `cb686d0` + 2 个仅改 AGENTS.md 的文档合并提交）及其后继 `dc0792c`（validator Windows bash 适配，D-NC012-23 范围，主 Agent 提交推送）；act/01 的 diff-tree 核对基线相应为 `dc0792c` | 两文档提交为 NC-012a 验收期合入，不触及任何产物文件；executor 按停手协议上报基线不符，裁定通过（2026-09-13） |
