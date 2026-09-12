# 客户端社区契约：命令队列、公共 API 客户端、发布状态与页面（NC-010）

状态：`FROZEN_FOR_NC-010`（2026-09-11）。权威来源：[community_api.md](community_api.md)（端点、头、错误、Schema，含 §10）；[community_server.md](community_server.md)（服务端判定顺序与 payload_hash，D-NC009-01/09/12/13）；[DESIGN](../DESIGN.md) §4.2、§7.4；[state-machines](state-machines.md) SM-2a、SM-3、SM-5；[PRD](../PRD.md) 旅程 1/3/5/9、§5.1、§6.2、§6.4；[TASKS](../TASKS.md) NC-010；knowledge_system 工作流 v1.2 §11.3 七状态矩阵；NC-004～NC-007 已交付的 reading-notes 包。本文把已定设计落到 Dart 接口、Drift 表、状态派生、文案闭集与测试判据，供执行者照抄；与上游冲突以上游为准并回报主 Agent。

## 1. 包、依赖与存储

| 项 | 实值 |
|---|---|
| 仓库 | `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（独立 Git；NC-007 末提交 `9b35e97`，`flutter test +150`） |
| 新增依赖 | `http: 1.6.0`（精确锁定；pub-cache 已有，与 repository-rest-adapter、social 锁定版本一致）；`package:http/testing.dart` 的 `MockClient` 作测试替身，不新增其他包 |
| 复用依赖 | `crypto 3.0.7`（SHA-256）、`drift 2.31.0`/`drift_dev`/`build_runner`（新库生成代码）、`fake_async`（已为传递依赖） |
| 新目录 | `lib/src/community/`、`test/community/` |
| 存储 | **独立 Drift 数据库** `CommunityDatabase`，文件 `reading_notes_community_<scopeUid>.sqlite`，与 `NoteDatabase` 同目录；`schemaVersion 1`（D-NC010-01：不改 NC-004 的 `NoteDatabase` 表与 `user_version==1` 断言） |
| 禁止 | 引入 `firebase_auth`/`cloud_firestore`；修改 NC-004～NC-007 的 `lib/src/{domain,persistence,editor,history}` 与其测试；真实网络（测试一律 `MockClient`） |

## 2. 宿主端口（`lib/src/community/ports.dart`）

```dart
typedef IdTokenProvider = Future<String?> Function();   // 宿主传 () => FirebaseAuth.instance.currentUser?.getIdToken()
class CommunityEndpoint { final Uri baseUri; const CommunityEndpoint(this.baseUri); }  // 例：https://<region>-<project>.cloudfunctions.net/community_contents_py 前缀，路径拼 /v1/community/...
abstract class CommunityClock { DateTime nowUtc(); }
abstract class ClipboardPort { Future<void> copyText(String text); }   // 复用 NC-005 同名语义，本包内新定义以免跨目录依赖
typedef AppealHandler = void Function(String contentId);   // 宿主接入既有申诉/举报渠道；笔记列表与作者详情必须注入
```

`IdTokenProvider` 返回 `null` → 客户端不发请求，命令保持 `queued`，界面按 §6 OFFLINE/未登录处理（D-NC010-02）。

## 3. 公共 API 客户端（`community_api.dart`）

`class CommunityApi { CommunityApi({required http.Client client, required CommunityEndpoint endpoint, required IdTokenProvider idToken}); }`

| 方法 | 端点 | 请求头 | 成功返回 |
|---|---|---|---|
| `Future<ApiResult<PublicationResponse>> publish(String commandId, PublishRequest body, {int? ifMatch})` | W1 | `Authorization`、`Idempotency-Key`、`If-Match`（仅重新发布时，D-NC009-09） | 201 |
| `update(commandId, contentId, UpdatePublicationRequest, {required int ifMatch})` | W2 | 同上（If-Match 必带） | 200 |
| `withdraw / trash / restore(commandId, contentId, {required int ifMatch})` | W3/W4/W5 | 同上 | 200 `AccessResponse` |
| `purge(commandId, contentId, {required int ifMatch})` | W6 | 同上 | 202 `PurgeResponse` |
| `getContent(contentId, {int? ifNoneMatchVersion})` | R1 | `If-None-Match: "<v>"` | 200 / 304（`ApiResult.notModified`） |
| `getCommand(commandId)` | R5 | — | 200 `CommandResult` |
| `listMyContents({String? cursor, int limit = 20})` | R6 | — | 200 |

- `ApiResult<T>` 为 sealed：`ok(T value, int status, String? etag)`、`notModified()`、`problem(CommunityProblem p)`、`transport(Object error)`（连接失败/超时/非 JSON）。
- `CommunityProblem { int status; String code; String type; Map<String,Object?> extra; }`，从 `application/problem+json` 按 community_api §10.2 `CommunityProblemDetails` 解析；缺 `code` 的错误体视为 `transport`（契约违约，不猜测）。
- 请求体与响应体 Dart 类型逐字段对应 community_api §5（snake_case JSON 键 ↔ lowerCamel Dart 字段，手写 `fromJson/toJson`，不引入代码生成包）；可空字段对应 `type: [T, "null"]`。
- 超时 15 秒；不自动重试（重试由 §4 队列负责）。

## 4. 命令队列（`command_queue.dart` + `community_database.dart` 表 `community_commands`）

### 4.1 表

| 列 | 类型 | 约束 |
|---|---|---|
| `command_id` | text PK | DESIGN §2.1.1 正则，入队时生成一次（`uuid` 不引入：`'cmd_' + 32 hex`，第 13 位固定 `4`、第 17 位取 `8/9/a/b`，随机源 `Random.secure()`） |
| `owner_scope` | text | 本地 scopeUid |
| `operation` | text | `content.publish/update/withdraw/trash/restore/purge`（本任务 6 个；NC-011/012 追加） |
| `target_id` | text | `content_id` |
| `request_json` | text | `{"path": {...}, "body": {...}}`（body 为请求体 JSON，无体为 `{}`） |
| `if_match` | int nullable | 入队时确定，重试不变 |
| `payload_hash` | text | `SHA-256_hex(canonical_json({"operation": op, "payload": {"path": ..., "body": ..., "if_match": ...}}))`，`canonical_json` 键按码点排序、无空白、UTF-8（与 D-NC009-01 逐字节一致；测试以 Python 参考值断言） |
| `state` | text | §4.2 闭集 |
| `attempt_count` | int | 默认 0；累计全部发送次数 |
| `auto_attempts` | int | 默认 0；当前自动重试窗口内的发送次数，用户「重试」时归 0 |
| `next_attempt_at` | text nullable | ISO UTC；退避到期时间 |
| `last_problem_code` | text nullable | |
| `result_json` | text nullable | committed 时完整响应体；rejected 时 Problem Details |
| `created_at` / `updated_at` | text | ISO UTC |

索引 `(owner_scope, target_id, state)`。第二张表 `content_access_cache`（§5.1）同库。

### 4.2 状态机（`CommandState`）

| 当前 | 事件 | 目标 | 说明 |
|---|---|---|---|
| — | `enqueue` | `queued` | 同 `target_id` 已有非终态命令 → 抛 `PendingOpConflict`（复用 NC-004 errors），不入队 |
| `queued` | 发送开始 | `sending` | 先落库再发请求；`attempt_count += 1` |
| `sending` | 2xx | `committed` | 存 `result_json`；更新 §5.1 缓存 |
| `sending` | 4xx 且 `code ≠ unavailable.*`（含 409/412/403/404/410） | `rejected` | 存 Problem；410 `gone.command_result` 另存 `command` 字段并按其 `resource_ids` 触发 R1 刷新 |
| `sending` | 503 `unavailable.command_status` | `unknown` | 保留键；下一次 `drain` 先 R5 查询，查到终态按其结果落定，查无（404）→ `queued` 同键重发 |
| `sending` | `transport` 或 503 `unavailable` / 5xx，且 `auto_attempts < 5` | `queued` | 退避逐次为 1s / 2s / 4s / 8s（DESIGN §9.1），写 `next_attempt_at`，不生成新键 |
| `sending` | 同上，且 `auto_attempts == 5` | `paused` | 非终态，保留键，不再自动发送；待处理队列显示「发送失败，点此重试」 |
| `paused` | 用户「重试」 | `queued` | `auto_attempts = 0`，同键 |
| `sending` | 应用在响应前被杀 | （重启后仍为 `sending`） | `recover()` 把 `sending` 视同 `unknown`：先 R5，再按上一行 |
| `queued` 且 `attempt_count == 0` | 用户取消 | `cancelled` | 已发送过（attempt ≥ 1）不可取消（SM-5 末行），抛 `CommandAlreadySent` |
| `queued/unknown/paused` 且 `now − created_at > 14 天` | `drain` 取到该行 | （先 R5） | DESIGN §7.4 第 5 条：先 `GET /commands/{id}` 对账；查到终态按其落定，404 → 按原状态继续（同键） |
| `committed/rejected/cancelled` | 任意 | ✘ | 终态 |

`drain()`：按 `created_at` 串行发送同 owner 的 `queued/unknown` 命令（`next_attempt_at` 未到的跳过，`paused` 不发）；同一时刻只运行一个 `drain`（并发调用返回同一个进行中的 `Future`，写请求只发一次）；`IdTokenProvider` 返回 null 时立即返回不改状态。

### 4.3 与 pending_op（SM-5）

`pending_op` 的持久字段是 NC-004 `notes.pending_op`（SM-5 所有者列为 `Note.pending_op`；community-models §1.1；NC-019 验收读它），命令队列是其来源（D-NC010-03）：
- 入队 `content.withdraw/trash/purge` 成功落库后，`PendingOpWriter` 把对应笔记的 `notes.pending_op` 写为 `withdraw_requested/trash_requested/purge_requested`；该命令到达 `committed/rejected/cancelled` 后写回 `none`。
- 写入经 `NoteRepository.db`（公开字段）的 Drift `update(db.notes)`，写前比较 `repository.sessionGeneration == repository.db.activeGeneration`，不等抛 NC-004 `StaleSessionError`；不修改 NC-004 任何文件。
- 两库非同一事务：以社区库为真源，`recover()` 时对该 owner 全部笔记按队列重算并回写 `pending_op`（幂等），修复崩溃造成的不一致。

## 5. 发布状态与控制器（`publication_controller.dart`）

### 5.1 缓存表 `content_access_cache`

列：`content_id` PK、`owner_scope`、`visibility`、`lifecycle`、`moderation_state`、`current_publication_id`、`published_revision_id`、`access_version`、`fetched_at`。写入来源只有 committed 响应与 R1/R6 返回；404 `not_found.content` → 删除该行（视为 never_published）。**版本单调**（DESIGN §7.4 第 6 条）：写入前比较 `access_version`，新值 `<` 缓存值则丢弃本次写入（迟到的旧响应不回滚 UI）；相等则只更新 `fetched_at`。

### 5.2 作者视角状态派生（PRD §6.2 文案闭集，逐字）

输入：本地 `Note`（NC-004）+ 缓存行 + §4.3 pending_op。按优先级取第一条命中：

| 条件 | `AuthorPublicationLabel` | 文案 |
|---|---|---|
| `pending_op ≠ none` 且操作为 withdraw/trash | `stoppingPublic` | 正在停止公开，他人可能仍可访问 |
| `lifecycle == purge_pending`（缓存）或 `pending_op == purge_requested` | `purging` | 正在彻底清除 |
| `lifecycle == trashed` | `inTrash(daysLeft)` | 在回收站 · 剩余 N 天（N = `ceil((trashed_at + 30d − now) / 1d)`，N 取运行时值） |
| `moderation_state == hidden` 且 visibility ∈ {published, withdrawn} | `hiddenByAdmin` | 已被管理员暂停展示（附申诉入口：文案旁「申诉」按钮，调用宿主注入的 `AppealHandler(contentId)`） |
| `visibility == withdrawn` | `stopped` | 已停止公开 |
| `visibility == published` 且 `Note.preferredHeadId ≠ published_revision_id` | `publishedWithChanges` | 已公开 · 有未发布的修改 |
| `visibility == published` | `published` | 当前公开版本 |
| 无缓存行 | `privateOnly` | 仅自己可见 |

「清除未完成 · 点此重试」依赖 PurgeTask.state，归 NC-019，本任务不产出。

### 5.3 发布流程（PRD 旅程 3）

`PublicationController`：
1. `openPreview(noteId)`：默认选中 `Note.preferredHeadId`；可调用 `selectRevision(revisionId)` 在该笔记全部修订间切换（NC-007 `listRevisions`），每次切换重算 `PublishReadiness`。
2. `PublishReadiness`：`title` 非空、`markdown` UTF-8 ≤ 262144 字节、`attachmentRefs` 每项经 `AttachmentReadinessPort.stateOf(ref)`（`ready / uploading(pct) / failed / missing`）；任一非 `ready` → 发布按钮禁用，预览在该图位置显示 `上传中 x%` / `上传失败` / `文件已丢失`（PRD 旅程 3 原词）。本任务的生产端口不存在（NC-008）：宿主未注入端口时，含附件的修订一律视为不可发布并显示「含图片的笔记暂不能发布，请移除图片后再发布」（D-NC010-04）。
3. 首次发布（该 content 无缓存行且本机未确认过）→ 先显示一次性后果说明（PRD §5.1 原文逐字），确认后记 `first_publish_ack` 到 `community_meta` 键值表，同 owner 不再显示。
4. `confirmPublish()`：由选中修订构造 `PublishRequest`（`content_id = noteId`、`revision_id`、`content_hash = NoteRevision.contentHash`、`snapshot = {title, markdown, attachments: [], mentions, bindings}`），缓存行存在且 `visibility == withdrawn` 时带 `if_match = access_version`；入队并 `drain()`。**服务器确认前不显示成功**：命令为 `queued/sending/unknown` 时显示「正在发布…」进行中指示（PRD §6.3），`committed` 后进入成功页。
5. 成功页：「查看公开效果（他人视角）」调 R1（不带作者身份的渲染模式：仅用响应中的 `snapshot` 渲染 `MarkdownPreview(mode: publicView)`），断言不含未发布修订正文、未选中修订的标题；「返回笔记」。
6. `update / withdraw / trash / restore / purge`：入队前按 SM-2a/SM-3 本地前置检查（不满足抛 NC-004 `IllegalLifecycleTransition` / `TrashRequiresWithdraw`，不入队）；If-Match 取缓存 `access_version`；412 `conflict.version` → 命令 `rejected`，控制器调 R1 刷新缓存并提示「内容已在其他设备更新，请确认后重试」，**本地私人修订不受影响**（版本冲突保留私人稿）。

## 6. 页面与七状态（`note_list_page.dart`、`content_detail_page.dart`、`publish_preview_page.dart`、`pending_queue_page.dart`）

| 屏 | LOADING | EMPTY | PARTIAL | ERROR | OFFLINE | STALE | SUCCESS |
|---|---|---|---|---|---|---|---|
| 我的笔记列表 | 骨架行 + 可取消 | 「这里放你自己的笔记和对原书的注解，只有你能看到」+「新建笔记」「去读书」两个按钮 | 发布状态未能刷新的条目显示本地状态并标「状态待刷新」 | 「笔记加载失败」+「重试」 | 仅本地数据，顶部「离线，公开状态可能不是最新」 | 「公开状态更新于 <HH:mm>」+ 下拉刷新 | 列表，每项含 §5.2 文案与冲突标记（NC-007） |
| 公开详情（他人视角） | 骨架 | —（404 走 ERROR） | —（本任务无附件） | 404 → 「该内容已不可访问」（PRD §6.2 统一文案，不区分原因）；其他 → 「加载失败」+「重试」 | 「离线，无法查看公开内容」 | ETag 304 时显示「内容未变化 · <HH:mm>」 | 渲染快照 |
| 发布预览 | 修订加载中 | 该笔记无已保存修订 → 「还没有已保存的版本，先回到编辑页保存」 | 部分图片未就绪 → 就绪 m/n 与各图原因 | 发布被拒 → 按 `code` 显示原因与动作（409 lifecycle → 「当前状态不能发布」+ 刷新；412 → §5.3 第 6 条文案） | 「离线，发布将在联网后发送」且按钮仍可入队 | — | 成功页 |
| 待处理队列 | 读取中 | 「所有操作都已完成同步」 | — | 读取失败 +「重试」 | 条目保留，显示「等待联网」 | 「最后同步 <HH:mm>」 | 列表：目标、摘要（标题前 20 字）、发起时间、状态、动作（重试 / 取消 / 复制正文） |

- 待处理队列（PRD 旅程 9）：列出 `queued/sending/unknown/paused/rejected`（rejected 保留到用户关闭）；`paused` 条目显示「发送失败，点此重试」，点击调用 `CommandQueue.retry(commandId)`（同键、`auto_attempts` 归 0，§4.2）并立即 `drain()`；`rejected` 且 `code ∈ {not_found.content, forbidden.not_owner, conflict.lifecycle, conflict.version}` 显示终止原因并提供「复制正文」（经 `ClipboardPort` 复制该命令对应修订的 markdown），**不得静默丢弃**。
- 收回确认层（PRD §5.1）：「N 人的评论将无法访问，你的私人稿件与历史不受影响；已被截图或离线保存的内容无法收回」+「可以再次发布」；本任务无评论计数来源（NC-011），N 由注入的 `CommentCountPort` 提供，未注入时整句改为「该内容下的评论将无法访问，…」（D-NC010-05）。
- 彻底删除确认层（PRD §5.1）：N = `listRevisions(noteId).length`，M = 全部修订 `attachmentRefs` 去重后的数量，均为运行时值；需二次点击。
- 本任务实现的确认层：首次发布后果说明、收回、彻底删除（3 个）；导出/导入归 NC-018，拉黑归 NC-012。

## 7. 测试判据（`flutter test`，全部 `MockClient` + 临时目录 Drift 库）

| 文件 | 测试（名称逐字） |
|---|---|
| `test/community/command_queue_test.dart` | `enqueue_persists_before_send_and_generates_valid_command_id`、`payload_hash_matches_python_reference`（常量来自 §8 样例）、`same_target_second_command_throws_pending_op_conflict`、`transport_error_requeues_with_same_key_and_backoff`、`restart_with_sending_row_queries_command_then_resends_same_key`、`unavailable_command_status_becomes_unknown_then_resolves_by_get_command`、`rejected_4xx_is_terminal_and_keeps_problem`、`gone_410_is_rejected_with_minimal_command_and_triggers_refresh`、`cancel_only_before_first_send`、`drain_noop_without_id_token`、`restart_with_real_file_close_reopen_resends_same_key`（关闭真实文件库后以同一路径重开）、`concurrent_drain_calls_send_request_once`、`backoff_1_2_4_8_then_paused_and_manual_retry_keeps_key`、`stale_over_14_days_queries_command_before_resend` |
| `test/community/community_api_test.dart` | `publish_sends_auth_idempotency_and_no_if_match_on_first_publish`、`republish_sends_if_match`、`versioned_writes_send_if_match`、`get_content_304_returns_not_modified`、`problem_without_code_is_transport`、`parses_nullable_fields_as_null` |
| `test/community/publication_flow_test.dart` | `author_labels_follow_priority_table`（8 行逐字）、`preview_switch_revision_recomputes_readiness`、`attachment_not_ready_disables_publish_with_reason`、`first_publish_shows_consequence_once`、`success_only_after_committed`、`public_view_excludes_unpublished_revision`、`version_conflict_keeps_private_revision_and_refreshes`、`offline_publish_stays_in_pending_queue`、`pending_queue_terminated_item_offers_copy_text`、`pending_queue_empty_text`、`withdraw_confirmation_text_uses_runtime_or_generic_count`、`purge_confirmation_counts_revisions_and_attachments`、`trash_published_locally_rejected_before_enqueue`、`pending_op_column_mirrors_queue_and_recovers_after_restart`、`late_older_access_version_does_not_overwrite_cache`、`hidden_by_admin_shows_appeal_entry`、`pending_queue_paused_item_retries_with_same_key` |
| `test/community/seven_states_test.dart` | 参数化：笔记列表 × 7、公开详情 × 6（PARTIAL 不适用）、发布预览 × 6（STALE 不适用）、待处理队列 × 6（PARTIAL 不适用）= 25 例，逐例断言 §6 表文案逐字出现 |

## 8. payload_hash 参考样例（跨端逐字节一致）

`operation = "content.withdraw"`，`path = {"content_id": "note_00000000000000000000000000000001"}`，`body = {}`，`if_match = 3` → canonical JSON `{"operation":"content.withdraw","payload":{"body":{},"if_match":3,"path":{"content_id":"note_00000000000000000000000000000001"}}}`；SHA-256 = `c8e2c2b0a842ece53f90cbf84e64fbacf274745a42bf4fb389b670fb0b3b72b5`（主 Agent 2026-09-11 以 Python `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False)` 计算）。Dart 测试以该字面量断言，不得在测试内调用被测函数生成期望值；NC-009 act/01 以同一输入须得同值，验收时交叉比对。

## 9. 决定登记（NC-010，主 Agent 裁定，可推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC010-01 | 社区命令队列与缓存用独立 `CommunityDatabase` 文件 | 不改 NC-004 已验收的 `NoteDatabase` 表与 `user_version==1` 断言；社区数据与私人修订库生命周期不同 |
| D-NC010-02 | 包内不依赖 Firebase，宿主注入 `IdTokenProvider` | reading-notes 是纯包；宿主现有 playground 仓储即以 `currentUser.getIdToken()` 取 token |
| D-NC010-03 | 队列为 `pending_op` 的来源，同步回写 NC-004 `notes.pending_op`，重启时按队列重算 | SM-5 所有者为 `Note.pending_op`，NC-019 验收读该列（R1 审查指出初稿不写违背 DESIGN §4.2）；经 `NoteRepository.db` 写，不改 NC-004 文件 |
| D-NC010-04 | 含附件修订在无 `AttachmentReadinessPort` 时不可发布并明示原因 | NC-008/NC-025 未交付；服务端 D-NC009-03 同样拒绝，不造「上传中」假象 |
| D-NC010-05 | 收回确认层的评论数由 `CommentCountPort` 注入，缺省用不含数量的句式 | 评论计数属 NC-011；PRD §5.1 禁止未替换占位符，宁可不写数也不写假数 |
| D-NC010-06 | 真实宿主 `example/` 与 Emulator 端到端归 NC-024 | 需 NC-009 部署到 Functions Emulator；本任务 TASKS 验收命令只要求 `publication_flow_test.dart` |
| D-NC010-07 | 自动重试退避 1s/2s/4s/8s、上限 5 次，之后 `paused`（非终态、同键、需用户点重试） | DESIGN §9.1 冻结指标；命令不能丢，暂停而非丢弃 |
| D-NC010-08 | PRD §5.1 五个确认层中本任务交付收回、彻底删除两个（另加首次发布后果说明），导出/导入归 NC-018、拉黑归 NC-012 | TASKS NC-010 字面要求五个，但导出/导入与拉黑的功能本体不在本任务，确认层随功能交付 |
| D-NC010-09 | `trashed` 与 `hidden` 同时成立时作者看到「在回收站 · 剩余 N 天」 | SM-C 允许 withdrawn+trashed+hidden；PRD §6.2 未规定重叠优先级；回收站剩余天数对作者更紧迫，审核态在恢复后仍按 SM-4 保留并再次显示 |
