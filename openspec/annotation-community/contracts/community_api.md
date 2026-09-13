# 注解社区公共 API 契约（NC-003：OpenAPI 3.1、错误目录、幂等与命令账本）

状态：`FROZEN_FOR_NC-003`（2026-09-11）。权威来源：[DESIGN](../DESIGN.md) §2.1.1、§4.1～§4.4、§7.1、§7.3、§7.4；[PRD](../PRD.md) R-05、R-18、R-20、§6.2；[TASKS](../TASKS.md) NC-003；[community-models](community-models.md) §0.1、§2、§3.2、§5；[state-machines](state-machines.md) SM-2a/2b/3/4/6/SM-C；NC-001 集成基线 `integration_baseline.json`（验证器 `openapi-spec-validator 0.9.0`、REST 仓库、SERVER 仓库）；SERVER 现状盘点（2026-09-11，functions-py，见 §1.2）。本文把已定设计冻结为可直接写进 `openapi.yaml` 的端点目录、Schema 字段表、错误目录与测试判据，供执行者照抄；与上游冲突以上游为准并回报主 Agent。

## 1. 位置、方向与沿用约定

### 1.1 产物位置

- 契约文件：`/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter/openapi/openapi.yaml`（既有 3.1.0 文档，**原地修改**：修正既有非法结构并追加社区部分；`info.version` 由 `1.0.0` 升为 `1.1.0`）。
- 验证器：`openapi-spec-validator 0.9.0`，安装位置 `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community/.venv-openapi/bin/openapi-spec-validator`（NC-001 基线；主 Agent 2026-09-11 已安装并核实：既有 openapi.yaml **验证失败**——`'headers' was unexpected`；notifier 3.0.3 契约通过；故意非法文档被拒）。精确计数（PyYAML 按 `paths.*.<method>` 解析）：22 个 operation **全部**带非法 operation 级 `headers:`；全文 `grep -c headers:` 的 35 含 12 处合法 response 级与 1 处 `components/headers`，不可作判据。
- REST 仓库测试基线（改前，主 Agent 实测）：`dart test` 退出码 0，`+50: All tests passed!`；`test/openapi_validation_test.dart` 含 19 个 `test(`，其中 **14 行断言、分布在 10 个测试块**要求 operation 级 `headers:`（第 147/161/217/239/292/307/315/320/329/330/339/340/349/350 行；第 50 行的 `components['headers']` 合法，不迁移）；其余 9 个测试不涉及。
- 权威文档两份：本文对应 REST 仓 3.1.0；notifier ACK/relay 契约 `xuan-server/notifier/api/openapi.yaml`（3.0.3）只引用不复制。

### 1.2 Firebase 方向（用户 2026-09-11 指示：按 Firebase 方向写，与 functions-py 现有约定统一）

| 约定 | SERVER 现状（functions-py） | 本契约沿用方式 |
|---|---|---|
| 传输 | `@https_fn.on_request` HTTP 函数，`playground_rest.py` 已提供 REST 风格路径 | 社区端点同为 HTTP 函数，路径前缀 `/v1/community`；每个路径写 `x-xuan-function: community_<resource>_py`（信息性扩展字段，供 NC-009 实现命名） |
| 鉴权 | 只认 `Authorization: Bearer <Firebase ID token>`；`require_auth_uid` + `resolve_app_user_id` 服务端派生 `app_user_id`；匿名登录与普通登录不区分 | 全部端点 `security: [BearerAuth: []]`（复用既有 securityScheme）；`owner_scope` 由服务端从 `app_user_id` 派生，任何请求体/路径不携带 uid 或 app_user_id（D-NC003-02） |
| 错误 | RFC 9457 `application/problem+json`，`type` 为 L0 闭合码 | 沿用 `ProblemDetails` 并新增必填 `code`（§4 目录）；`type` 按 §4.2 映射到 L0 闭合码 |
| 幂等 | `Idempotency-Key` 头 → `playground_idempotency` 集合，TTL 60 分钟；`with_idempotency` 为「claim → 事务外 fn → result」 | 社区写命令**不用** `with_idempotency`（DESIGN §4.3），改由 NC-009 的 `command_service` 在同一事务内读账本 + 写业务 + 写终态；本契约只冻结 HTTP 面：`Idempotency-Key` 必填、值即 `command_id`、完整结果 14 天、`GET /v1/community/commands/{command_id}` |
| 并发 | 读用 MD5 ETag + `If-None-Match` 304；写无 `If-Match` | 读沿用 304；写引入 `If-Match`（§3.3），ETag 值改为资源 `version` 的十进制字符串（D-NC003-04） |
| 分页 | 不透明 base64url 游标（去 padding） | 同；`limit` 1～100，默认 20，101 → 400 `invalid_argument.limit`（community-models §5） |
| 限流 | 默认关闭（`XUAN_RATE_LIMIT_ENABLED`），键 `(app_user_id, action)`，1 分钟窗口，超限 `resource_exhausted` | §6 填实值；契约测试只验 429 响应 Schema，行为验收归 NC-009（服务端开启后） |
| 软删字段 | posts 用 `status="tombstoned"`，replies 用 `is_tombstoned` | 社区资源一律用枚举字段 `status` / `lifecycle` / `visibility`，禁止布尔软删字段（D-NC003-05） |
| 对外 DTO | `public_dto.py` 只暴露 `publicPresentationUserId`/`displayAlias` | 作者字段只暴露 `author: {public_id, display_alias}`（§5.1 `PublicAuthor`），不出现 `app_user_id`/uid/内部对象路径 |
| CORS | 全仓库无 CORS 头 | 契约不声明 CORS（客户端为 Flutter 原生，非浏览器）；Web 需求出现时另立任务 |
| 命名 | playground 用 camelCase（`nextCursor`） | 社区部分全部 snake_case（与 community-models、fixture、nchash 投影一致，D-NC003-06）；不改动 playground 既有字段 |

## 2. 端点目录

路径统一前缀 `/v1/community`。「写」= 命令，必带 `Idempotency-Key`（§3.2），响应体必含 `command`（§7）。`{target_type}` ∈ `content | comment`。

| # | 操作（CommandRecord.operation） | 方法与路径 | 请求体 Schema | 成功 | If-Match 比较对象 |
|---|---|---|---|---|---|
| W1 | `content.publish` | `POST /contents` | `PublishRequest` | 201 `PublicationResponse` | —（新建；重复 content_id 已 live → 409 `conflict.lifecycle`） |
| W2 | `content.update` | `PUT /contents/{content_id}` | `UpdatePublicationRequest` | 200 `PublicationResponse` | `ContentAccess.version` |
| W3 | `content.withdraw` | `POST /contents/{content_id}:withdraw` | 无 | 200 `AccessResponse` | `ContentAccess.version` |
| W4 | `content.trash` | `POST /contents/{content_id}:trash` | 无 | 200 `AccessResponse` | `ContentAccess.version` |
| W5 | `content.restore` | `POST /contents/{content_id}:restore` | 无 | 200 `AccessResponse` | `ContentAccess.version` |
| W6 | `content.purge` | `POST /contents/{content_id}:purge` | 无 | 202 `PurgeResponse` | `ContentAccess.version` |
| W7 | `comment.create` | `POST /contents/{content_id}/comments` | `CreateCommentRequest` | 201 `CommentResponse` | —（体内 `expected_access_version`） |
| W8 | `comment.edit` | `PATCH /comments/{comment_id}` | `EditCommentRequest` | 200 `CommentResponse` | `Comment.version` |
| W9 | `comment.delete` | `DELETE /comments/{comment_id}` | 无 | 200 `CommentResponse` | `Comment.version` |
| W10 | `reaction.set` | `PUT /reactions/{target_type}/{target_id}` | `SetReactionRequest` | 200 `ReactionState` | `Reaction.version`（不存在时 `"0"`） |
| W11 | `bookmark.set` | `PUT /bookmarks/{target_type}/{target_id}` | `SetBookmarkRequest` | 200 `BookmarkState` | `Bookmark.version`（不存在时 `"0"`） |
| W12 | `share.create` | `POST /share-links` | `CreateShareLinkRequest` | 201 `ShareLinkResponse` | — |
| W13 | `share.revoke` | `DELETE /share-links/{share_id}` | 无 | 200 `ShareLinkResponse` | — |
| W14 | `report.create` | `POST /reports` | `CreateReportRequest` | 201 `ReportResponse` | — |
| — | `backup.begin` / `backup.complete` / `backup.delete` | **保留枚举值，本期无路径**（v1.6 S6 模型无云端备份，PRD R-13 改为本机导出） | — | — | — |
| R1 | — | `GET /contents/{content_id}` | — | 200 `ContentDetail`（ETag）/ 304 | — |
| R2 | — | `GET /contents/{content_id}/comments?cursor&limit` | — | 200 `CommentPage`（ETag）/ 304 | — |
| R3 | — | `GET /reactions/{target_type}/{target_id}` | — | 200 `ReactionState`（ETag） | — |
| R4 | — | `GET /share-links/{share_id}` | — | 200 `ShareLinkResolution` | — |
| R5 | — | `GET /commands/{command_id}` | — | 200 `CommandResult` | — |
| R6 | — | `GET /me/contents?cursor&limit` | — | 200 `MyContentPage` | — |

操作枚举闭集（`CommandRecord.operation`，17 个，逐字）：`content.publish, content.update, content.withdraw, content.trash, content.restore, content.purge, comment.create, comment.edit, comment.delete, reaction.set, bookmark.set, share.create, share.revoke, report.create, backup.begin, backup.complete, backup.delete`。

## 3. 请求头、ETag 与并发

### 3.1 结构硬规则

- 所有请求头一律写成 `components/parameters` 下 `in: header` 的参数并在 operation 的 `parameters` 中 `$ref`；**operation 对象内禁止出现 `headers:` 键**（OpenAPI 3.1 无此字段，验证器拒绝）。既有 22 个 operation 必须全部迁移（响应级 `headers:` 与 `components/headers` 中的响应头 `ETag` 保留）；既有 14 行断言必须改为检查 `parameters` 中存在 `in: header` 且 `name` 相符的项（可经 `$ref` 解析）。
- 响应头（`ETag`、`Retry-After`）仍在 response 的 `headers:` 下声明，这是合法位置。

### 3.2 头参数（components/parameters 名 → HTTP 头名）

| 参数名 | 头 | 必填 | Schema |
|---|---|---|---|
| `IdempotencyKey` | `Idempotency-Key` | W1～W14 必填 | string，pattern `^cmd_[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$`（DESIGN §2.1.1） |
| `IfMatch` | `If-Match` | W2～W6、W8～W11 必填 | string，pattern `^"[0-9]+"$`（十进制版本加双引号） |
| `IfNoneMatch` | `If-None-Match` | R1～R3 可选 | string，同上 |
| `Traceparent` | `traceparent` | 可选 | 沿用既有 |

`Idempotency-Key` 与请求体不再重复携带 `command_id`（D-NC003-03）；服务端把头值作为 `command_id`。格式错误 → 400 `invalid_argument.command_id`。

### 3.3 ETag 与版本

- ETag 值 = 该资源 `version` 的十进制字符串加双引号（强 ETag），例如 `"7"`。
- 内容类资源（R1、W2～W6）的版本 = `ContentAccess.version`（收回/生命周期变化都提升它，DESIGN §4.3）；`Publication.version` 只在响应体内返回，不作 ETag。
- `If-Match` 不匹配 → 412 `conflict.version`，附 `current_version`。缺失必填 `If-Match` → 400 `invalid_argument.if_match`。
- R2 的 ETag = `"<ContentAccess.version>:<最新 comment 的 (created_at,id) 哈希前 16 hex>"`，形状 `^"[0-9]+:[0-9a-f]{16}"$`（D-NC003-07）。

## 4. 错误目录（唯一权威；DESIGN §7.3 基线 + 本任务补齐）

### 4.1 `ProblemDetails` Schema（`application/problem+json`）

必填：`type`（string，§4.2 的 L0 闭合码）、`title`（string）、`status`（integer）、`code`（string，下表）。可选：`detail`、`instance`。附加字段按行给出，其余附加字段禁止（`additionalProperties: false` 于每个具体错误 Schema；通用 `ProblemDetails` 允许 `additionalProperties: true` 以便 `oneOf` 组合）。

| 场景 | HTTP | `code` | 附加字段 |
|---|---|---|---|
| 未认证 / token 无效或过期 | 401 | `unauthenticated` | — |
| 读他人未发布、已收回、已删除、被隐藏、被拉黑后的内容 | 404 | `not_found.content` | **无任何可区分字段**；共用 `components/responses/NotFoundContent` |
| 非作者调用 update/withdraw/trash/restore/purge/share.create | 403 | `forbidden.not_owner` | — |
| 可读但主题不接受新评论（作者评论自己已收回/回收站内容；任何人回复已删除 root/目标） | 403 | `forbidden.thread_closed` | — |
| 目标不存在或已失效 | 404 | `not_found.comment` / `not_found.share_link` / `not_found.command` / `not_found.target` | — |
| `If-Match` 不匹配 | 412 | `conflict.version` | `current_version` (integer) |
| 幂等同键异载荷 | 409 | `conflict.idempotency` | `original_request_hash` (64 hex) |
| 评论时仍可访问但 `expected_access_version` 不匹配 | 409 | `conflict.access_version` | `current_access_version` (integer) |
| 非法生命周期/发布态转移（含重复 publish、restore 超 30 天、purge_pending 上 restore） | 409 | `conflict.lifecycle` | `current_state` (object `{visibility, lifecycle, moderation_state}`) |
| publish/update 引用的公共对象未上传完成 | 409 | `conflict.object_missing` | `missing_refs` (string 数组) |
| 输入错误（含 limit 101、cursor 非法、command_id 格式、if_match 缺失、数组重复项） | 400 | `invalid_argument.<field>` | `field` (string) |
| 体积超限（markdown 内联 > 262144 字节、body > 4000 cp、attachments > 20、mentions > 50、detail > 500 cp） | 413 | `too_large.<field>` | `limit` (integer) |
| 限流 | 429 | `rate_limited` | `retry_after_seconds` (integer 1～60)；响应头 `Retry-After` |
| 命令结果已精简且无法恢复完整响应 | 410 | `gone.command_result` | `command` (`CommandResult` 最小结果) |
| 命令恢复服务暂时无法确定结果 | 503 | `unavailable.command_status` | — |
| 暂时不可用 | 503 | `unavailable` | — |

403/404 边界：调用方已被证明拥有该资源读权限时用 403，否则一律 404（DESIGN §7.3）。

### 4.2 `type` 到 SERVER L0 闭合码的映射（逐字取自 `xuan/errors.py` 第 14～26 行 `_L0_MAP`，2026-09-11 核实）

L0 闭合码全集：`invalid_argument, not_found, unauthenticated, permission_denied, conflict.idempotency, conflict.unique, unavailable, deadline_exceeded, internal`（`failed-precondition` 归并为 `invalid_argument`，`resource-exhausted` 归并为 `unavailable`）。客户端只按 `code` 分支，`type` 仅为与既有错误层同源的粗分类。

| `code` | `type`（L0） | 对应 `XuanHttpsError` code |
|---|---|---|
| `unauthenticated` | `unauthenticated` | `unauthenticated` |
| `not_found.*` | `not_found` | `not-found` |
| `forbidden.*` | `permission_denied` | `permission-denied` |
| `conflict.idempotency` | `conflict.idempotency` | `aborted` |
| `conflict.version` / `conflict.access_version` / `conflict.lifecycle` / `conflict.object_missing` / `gone.command_result` | `invalid_argument` | `failed-precondition` |
| `invalid_argument.*` / `too_large.*` | `invalid_argument` | `invalid-argument` |
| `rate_limited` | `unavailable` | `resource-exhausted` |
| `unavailable` / `unavailable.command_status` | `unavailable` | `unavailable` |

`ProblemDetails.type` 的 enum 恰为上述 L0 全集中出现的 6 个值：`unauthenticated, not_found, permission_denied, conflict.idempotency, invalid_argument, unavailable`。

### 4.3 ACL 入口与统一 404

本契约内的公共读入口：R1、R2、R3、R4。四者对「未发布 / 已收回 / 已删除或回收站 / 被隐藏或拉黑」四种失效原因的 404 响应必须 `$ref` 同一个 `components/responses/NotFoundContent`，响应体不含正文子串、不含原因字段（R-20 的 6 入口 × 3 原因矩阵由 NC-009 用真实 HTTP 测试，附件与通知正文两个入口分别归 NC-008、NC-013）。

## 5. Schema 字段表（components/schemas；全部 snake_case；ID 格式按 community-models §0.1 正则）

### 5.1 公共对象

| Schema | 字段（类型；约束） |
|---|---|
| `PublicAuthor` | `public_id` (string)，`display_alias` (string) |
| `ContentAccessPublic` | `content_id` (`note_`)，`visibility` (SM-2a)，`lifecycle` (SM-3)，`moderation_state` (SM-4)，`current_publication_id` (`pub_`/null)，`version` (integer ≥ 0)，`author` (`PublicAuthor`) |
| `Publication` | `id` (`pub_`)，`content_id`，`published_revision_id` (`nrev_`)，`state` (SM-2b)，`version`，`published_at` (date-time/null) |
| `PublicSnapshot` | `title` (string ≤ 200 cp)，`markdown` (string，UTF-8 ≤ 262144 字节) **或** `public_body_ref` (对象键，二选一 `oneOf`)，`attachments` (`PublicAttachment[]` ≤ 20，`attachment_id` 唯一)，`mentions` (`MentionRef[]` ≤ 50)，`bindings` (`BindingRef[]`) |
| `PublicAttachment` | `attachment_id`，`object_version` (integer)，`content_digest` (64 hex)，`alt` (≤ 500 cp)，`caption` (≤ 500 cp)，`public_object_ref` (string) |
| `MentionRef` / `BindingRef` | 逐字引用 `openspec/schemas/community_*.schema.json` 中同名定义（NC-002），不重复定义字段（`$ref` 外部文件不可用时在 yaml 内复制并加注 `x-source`） |
| `Comment` | `id` (`cmt_`)，`thread_id` (`thr_`)，`root_id`，`reply_to_id`，`depth` (0/1)，`author` (`PublicAuthor`)，`status` (`visible/deleted/hidden`)，`created_at`，`version`，`current_revision` (`CommentRevisionPublic`/null：`deleted`/`hidden` 时为 null) |
| `CommentRevisionPublic` | `id` (`crev_`)，`body` (≤ 4000 cp)，`mentions`，`created_at` |
| `ReactionState` | `target_type`，`target_id`，`value` (`like/dislike/null`)，`version`，`counts` `{like: integer, dislike: integer}` |
| `BookmarkState` | `target_type`，`target_id`，`active` (bool)，`version` |
| `ShareLink` | `id` (`shr_`)，`target_type`，`target_id`，`created_at`，`revoked_at` (date-time/null) |
| `PurgeTaskState` | `state` (SM-6 `queued/running/failed/succeeded`) |
| `CommandResult` | 见 §7 |

### 5.2 请求体

| Schema | 字段 |
|---|---|
| `PublishRequest` | `content_id` (`note_`)，`revision_id` (`nrev_`)，`content_hash` (64 hex，nchash/v2)，`snapshot` (`PublicSnapshot`)；全部必填 |
| `UpdatePublicationRequest` | `revision_id`，`content_hash`，`snapshot`；全部必填 |
| `CreateCommentRequest` | `body`，`mentions` (默认 [])，`root_id` (`cmt_`/null)，`reply_to_id` (`cmt_`/null)，`expected_access_version` (integer ≥ 0，必填)；不变量：`reply_to_id` 非 null ⇒ `root_id` 非 null |
| `EditCommentRequest` | `body`，`mentions` |
| `SetReactionRequest` | `value` (`like/dislike/null`，必填，允许显式 null) |
| `SetBookmarkRequest` | `active` (bool) |
| `CreateShareLinkRequest` | `target_type`，`target_id` |
| `CreateReportRequest` | `target_type`，`target_id`，`reason` (`spam/abuse/copyright/other`)，`detail` (≤ 500 cp，默认空串) |

### 5.3 响应体

| Schema | 字段 |
|---|---|
| `PublicationResponse` | `access` (`ContentAccessPublic`)，`publication` (`Publication`)，`command` (`CommandResult`) |
| `AccessResponse` | `access`，`command` |
| `PurgeResponse` | `access`，`purge_task` (`PurgeTaskState`)，`command` |
| `CommentResponse` | `comment` (`Comment`)，`command` |
| `ShareLinkResponse` | `share_link` (`ShareLink`)，`command` |
| `ReportResponse` | `report_ref` (string = command_id)，`command` |
| `ContentDetail` | `access`，`publication` (live 的 `Publication`/null)，`snapshot` (`PublicSnapshot`/null) |
| `CommentPage` | `items` (`Comment[]`)，`next_cursor` (string/null) |
| `MyContentPage` | `items` (`ContentAccessPublic[]`)，`next_cursor` |
| `ShareLinkResolution` | `target_type`，`target_id`，`share_link` |

写响应的 `command.outcome` 恒为 `committed`；`rejected` 只经错误响应与 R5 可见。

## 6. 分页与限流实值

- `cursor`：query，可选，string，pattern `^[A-Za-z0-9_-]{1,512}$`（base64url 去 padding）；非法 → 400 `invalid_argument.cursor`。
- `limit`：query，可选，integer，`minimum: 1`，`maximum: 100`，`default: 20`；101 → 400 `invalid_argument.limit`（Schema 层由 `maximum` 表达，行为层由 NC-009 测）。
- 限流（每认证账号，滑动 60 秒窗口，与 `rate_limit.py` 的 1 分钟窗口一致；D-NC003-08）：

| 操作 | 每分钟上限 |
|---|---|
| `content.publish`、`content.update` | 10 |
| `content.withdraw/trash/restore/purge` | 20 |
| `comment.create` | 30 |
| `comment.edit/delete` | 60 |
| `reaction.set`、`bookmark.set` | 120 |
| `share.create/revoke` | 20 |
| `report.create` | 10 |
| 全部读端点合计 | 600 |

429 响应：`Retry-After` 头（秒）与体内 `retry_after_seconds` 相同，取值 1～60。服务端默认关闭限流，开启与行为验收归 NC-009。

## 7. 命令账本（DESIGN §7.4）

`CommandResult`：`command_id`，`operation`（17 枚举），`outcome` (`committed/rejected`)，`applied_version` (integer ≥ 0 / null)，`resource_ids` (object，键按下表)，`result_http_status` (integer 100～599)，`committed_at` (date-time)，`result_code` (string/null，rejected 时非空)，`compacted` (bool，精简后为 true)。

按操作的 `resource_ids` 键与完整结果 Schema（NC-002 DEFERRED 项在此关闭）：

| operation | `resource_ids` 键 | 完整结果 Schema | `applied_version` 来源 |
|---|---|---|---|
| content.publish / update | `content_id`, `publication_id` | `PublicationResponse` | `ContentAccess.version` |
| content.withdraw / trash / restore | `content_id` | `AccessResponse` | `ContentAccess.version` |
| content.purge | `content_id` | `PurgeResponse` | `ContentAccess.version` |
| comment.create / edit / delete | `comment_id`, `thread_id` | `CommentResponse` | `Comment.version` |
| reaction.set | `target_type`, `target_id`, `reaction_id` | `ReactionState` | `Reaction.version` |
| bookmark.set | `target_type`, `target_id`, `bookmark_id` | `BookmarkState` | `Bookmark.version` |
| share.create / revoke | `share_id` | `ShareLinkResponse` | 0（无版本资源） |
| report.create | `report_ref` | `ReportResponse` | 0 |
| backup.* | `backup_id` | NC-017 定义 | NC-017 定义 |

精简账本（14 天后）只保留 `CommandResult`（`compacted=true`），不含任何完整结果 Schema 字段。两条路径（DESIGN §7.4 第 3～5 条逐字落地）：
- **同键重放写命令**（W1～W14 携带既有 `Idempotency-Key`）：14 天内 → 原始完整响应（原 HTTP 状态与体）；14 天后可恢复最小结果但无法恢复完整响应 → `410 gone.command_result`，附加字段 `command`（精简 `CommandResult`）；均不重新执行。
- **命令查询 R5**：记录存在 → `200 CommandResult`（完整期含 `compacted=false`，精简后 `compacted=true`）；未见记录 → `404 not_found.command`；账本服务暂时不可用 → `503 unavailable.command_status`。R5 无任何 query 参数。
- 重放与 R5 返回的 `applied_version` 都是**原始**值，不承诺当前状态；当前状态另经 R1/R3 读取（示例 `command_replay_original_version.json` 与 `reaction_state_current.json` 成对给出 applied_version=1 与当前 version=2）。

## 8. REST 仓库产物与测试判据

| 产物 | 要求 |
|---|---|
| `openapi/openapi.yaml` | 0 处 operation 级 `headers:`；`openapi-spec-validator` 退出 0；社区路径 20 个（W1～W14、R1～R6）全部存在，方法逐字按 §2；每个写操作 `parameters` 含 `IdempotencyKey`（required）；§2 标注 If-Match 的操作含 `IfMatch`（required）；R1～R3 含 `IfNoneMatch` 与 200 响应 `ETag` 头、304 响应；R1～R4 的 404 均 `$ref` `NotFoundContent`；`ProblemDetails` 必填含 `code`；`CommandResult.operation` 枚举恰 17 个逐字；`limit` 参数 `maximum: 100`、`default: 20`；社区 Schema 属性名全部匹配 `^[a-z][a-z0-9_]*$` |
| `test/openapi_validation_test.dart` | 14 行断言（10 个测试块）迁移为「`parameters` 中存在 `in: header` 且 `name` 相符」（可经 `$ref` 到 `components/parameters` 解析）；其余 9 个测试不变；文件仍 19 个 `test(` |
| `test/community_openapi_contract_test.dart` | 上表全部结构判据各至少一个测试；另调用 `tool/validate_openapi` 对 `openapi/openapi.yaml` 期望退出 0，对 `test/fixtures/openapi/red_*.yaml` 每个期望非 0 |
| `tool/validate_openapi` | bash：优先 `$OPENAPI_VALIDATOR`，否则 §1.1 的绝对路径；不存在时退出 2 并打印 `validator not installed (ENV_BLOCKED)`；否则透传验证器退出码 |
| `tool/check_examples.py` | Python（`$PYTHON` 或 learn_system `.venv/bin/python`，需 `jsonschema`）：读 `test/fixtures/openapi/examples/manifest.json`（每项 `{file, schema, expect: valid|invalid}`），用 `components/schemas/<schema>` 校验，任一不符退出 1 |
| `test/fixtures/openapi/` | Red 文档：`red_operation_headers.yaml`（含 operation 级 `headers:`）、`red_invalid_31.yaml`（缺 `info.version`）；examples：`publish_missing_required.json`（缺 `content_hash`，invalid）、`comment_illegal_status.json`（`status: archived`，invalid）、`idempotency_conflict_409.json`（`ProblemDetails`，valid，含 `original_request_hash`）、`version_conflict_412.json`（valid，含 `current_version`）、`publish_valid.json`（valid）、`access_version_conflict_409.json`（`ProblemDetails`，valid，含 `current_access_version`）、`command_replay_original_version.json`（`CommandResult`，valid，`applied_version: 1`）、`reaction_state_current.json`（`ReactionState`，valid，`version: 2`，与前者成对表达「原始 applied_version ≠ 当前状态」） |

## 9. 决定登记（NC-003，主 Agent 裁定，可推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC003-01 | 社区端点为 `/v1/community` 前缀的 HTTP 函数，与 playground REST 同一传输形态 | 用户指示按 Firebase 方向并与 functions-py 统一；DESIGN §7.4 已用 `/v1/community/commands` 命名 |
| D-NC003-02 | 全部端点要求 Bearer ID token；匿名与登录 uid 不区分；请求不携带任何账号标识 | SERVER 现状 `resolve_app_user_id` 服务端派生，且身份策略 `HOST_SCOPE_ONLY`；账号模型变化只改 identity 层，不改契约 |
| D-NC003-03 | `command_id` 只在 `Idempotency-Key` 头出现，体内不重复 | 消除 header/body 不一致这一错误类别（DESIGN §2.1.1 仍保留该错误码给历史客户端） |
| D-NC003-04 | ETag = `"<version>"`，内容类资源以 `ContentAccess.version` 为准 | 收回与生命周期变化都提升该版本（§4.3），一个版本号覆盖所有可见性变化 |
| D-NC003-05 | 软删一律枚举字段，禁止布尔 | SERVER 两处布尔/枚举不一致的教训 |
| D-NC003-06 | 社区部分 snake_case，不改 playground | 与 community-models、fixture、nchash 投影一致，避免两套字段名 |
| D-NC003-07 | 评论列表 ETag 组合 access 版本与末条评论键 | 评论新增不改 `ContentAccess.version`，单独版本才能让 304 正确失效 |
| D-NC003-08 | 限流阈值实值如 §6，服务端默认关闭 | TASKS 要求填实值；SERVER 现状默认关闭，开启归 NC-009 |
| D-NC003-09 | backup.* 只作保留枚举值，不定义路径 | v1.6：私人数据保护改为 S6 模型，无云端备份；保留枚举以免改动 NC-002 已冻结的 Schema 与 fixture |
| D-NC003-10 | `conflict.object_missing` 新增为目录行 | DESIGN §4.3 publish 前置「图片对象已全部上传完成」需要可断言的错误码 |
| D-NC003-11 | 契约测试用 Python 验证器与 jsonschema 经进程调用 | Dart 生态无成熟 3.1 校验器（DESIGN §7.4 明令禁止再写 yaml 字段检查器充数） |
| D-NC003-13 | 社区可空字段用 3.1 类型数组，禁用 `nullable` | 3.1 忽略 `nullable`，初版被真实校验拒收 null（验收盲测发现） |
| D-NC003-14 | 社区错误体独立为 `CommunityProblemDetails`，遗留 `ProblemDetails` 恢复原样 | 初版给共享 Schema 加必填 `code`，使遗留端点契约与服务端实际响应不符（主 Agent 契约缺陷） |
| D-NC003-15 | 字节上限以 `x-max-utf8-bytes` 声明、服务端强制 | JSON Schema 只能计 code point |
| D-NC003-12 | `forbidden.not_owner` 覆盖 update/withdraw/trash/restore/purge/share.create 六个本人操作，比 DESIGN §7.3 基线（withdraw/publish/trash）多列 restore/purge/share.create | 三者同为「只有本人可做」且调用方已被证明可读，按 §7.3 边界规则归 403；基线表只列举未穷举 |

## 10. 验收返工补充（2026-09-11，NC-003 act/06 消费；同时落地 NC-009 前置补丁 P1/P2）

### 10.1 可空字段按 3.1 表达（D-NC003-13）
社区 Schema 中凡契约写作「X / null」的属性，一律写 `type: [<原类型>, "null"]`（带 `enum` 的同时把 `null` 加入 `enum`）；社区 Schema 内**禁止出现 `nullable` 键**（3.0 关键字，3.1 与 JSON Schema 2020-12 忽略它，真实校验会拒收 `null`）。`tool/check_examples.py` 删除任何对 `nullable` 的改写，按文档原样校验。遗留 playground/record Schema 的 `nullable` 不在本任务范围、不改。

### 10.2 社区错误体与遗留错误体分离（D-NC003-14）
- `components/schemas/ProblemDetails` 与 `components/responses/{400BadRequest,401Unauthorized,403Forbidden,404NotFound,409Conflict,500Internal,503Unavailable,504DeadlineExceeded}` **恢复为与 `0f8bf52` 逐项相等**（遗留端点仍不要求 `code`）。
- 新增 `components/schemas/CommunityProblemDetails`：属性 `type`（enum 沿用遗留 10 值：`not_found, conflict.version, conflict.idempotency, conflict.unique, invalid_argument, permission_denied, unauthenticated, unavailable, deadline_exceeded, internal`）、`title`、`status`、`code`、`detail`、`instance`；`required: [type, title, status, code]`。全部社区错误变体 Schema（`Problem*`）改为 `allOf` 引用 `CommunityProblemDetails`；全部社区端点的 4xx/5xx 响应只引用社区响应组件。
- §4.2 映射表不变；§4.2 末句「`ProblemDetails.type` 的 enum 恰为 6 个值」作废，由本条替代（该 enum 与遗留共用，社区 `code` 只映射到其子集）。

### 10.3 字节上限（D-NC003-15）
`PublicSnapshot.markdown` 保留 `maxLength: 262144`（code point 宽松上界），并加扩展字段 `x-max-utf8-bytes: 262144` 与描述「UTF-8 字节上限 262144；超出服务端返回 413 too_large.markdown」。JSON Schema 无法表达字节长度，字节判定归服务端（NC-009 B13）。

### 10.4 前置补丁 P1：W1 可选 If-Match（NC-009 D-NC009-09）
`POST /v1/community/contents` 的 `parameters` 增加 `$ref: IfMatch` 的**引用方式不可用**（`IfMatch` 组件为 `required: true`）；新增组件 `IfMatchOptional`（`name: If-Match`、`in: header`、`required: false`、同 pattern），描述「首次发布缺省；重新发布（visibility=withdrawn）必带且等于 ContentAccess.version」。B08 断言相应改为：`IfMatch`（required）集合恰为 W2～W6、W8～W11；W1 恰含 `IfMatchOptional`；其余操作不含任何 `If-Match`。

### 10.5 前置补丁 P2：数据损坏 500（NC-009 D-NC009-11）
新增响应组件 `500StateCorrupted`，schema `allOf CommunityProblemDetails` 且 `code: {const: internal.state_corrupted}`、`type: {const: internal}`；R1 的 `500` 引用它。§4.1 错误目录增行：数据损坏（状态组合白名单外）｜500｜`internal.state_corrupted`｜—。

## 11. NC-011 补丁（2026-09-12，评论与讨论区；逐项落地见 [community_discussion.md](community_discussion.md)）

### 11.1 R2 参数与响应（D-NC011-04、D-NC011-11）
- R2 追加 query 参数组件 `RootId`（`root_id`，可选，`^cmt_[0-9a-f]{32}$`）与 `CommentOrder`（`order`，可选，`newest | oldest`，不写 default）。无 `root_id` 为一级评论，缺省 `newest`；带 `root_id` 为楼内回复，缺省且只允许 `oldest`，显式 `newest` → 400 `invalid_argument.order`。§2 R2 行路径读作 `GET /contents/{content_id}/comments?root_id&order&cursor&limit`。
- `CommentPage` 必填为 `items, next_cursor, reply_previews, visible_comment_count, visible_commenter_count`。`reply_previews`：对象，键为本页一级评论 ID，值为新增 `CommentReplyPreview{items (Comment[] ≤ 5), next_cursor (string/null)}`；楼内查询时为 `{}`。两计数为主题内 `status=visible` 的评论数与其不同作者数（integer ≥ 0）。
- `root_id` 不存在、不属于该主题或不是一级评论 → 404 `not_found.comment`（响应仍引用 `NotFoundContent` 组件，其 Schema 不限定 code）。

### 11.2 R2 ETag（替代 §3.3 末条与 D-NC003-07，D-NC011-05）
`"<ContentAccess.version>:<h>"`，`h = SHA-256_hex(E([thread_version, root_id 或 "", order, cursor 或 "", limit]))` 前 16 位；E 为 DESIGN §7.2 编码；`thread_version` 为 Thread.version（主题无评论为 0）；`order`、`limit` 为生效值，`cursor` 为请求原串。形状仍为 `^"[0-9]+:[0-9a-f]{16}"$`。鉴权先于 304（D-NC011-06）。参考：access 3 与 `[0,"","newest","",20]` → `"3:b713c1d13d46bdb5"`；access 3 与 `[3,"cmt_00000000000000000000000000000001","oldest","",5]` → `"3:bbe031c2c1299d8c"`。

### 11.3 评论游标
`base64url 去 padding(UTF-8("<order>|<root_id 或 ->|<created_at 6 位微秒>|<comment_id>"))`；四段、order 与 root 与本次查询一致、时间与 ID 格式合法，否则 400 `invalid_argument.cursor`。仍满足 §6 的 `Cursor` pattern。

### 11.4 错误目录增补（§4.1）
- `forbidden.not_owner` 行的操作列增加 `comment.edit`、`comment.delete`（非评论作者）。
- 413 行：评论正文的 code 逐字为 `too_large.comment_body`（`limit=4000`），mentions 为 `too_large.mentions`（`limit=50`；DESIGN §7.1 同步，D-NC011-07）。
- 400 行增加：评论请求体 Schema 不通过 `invalid_argument.comment`（`field` 为 JSON Pointer）；正文去空白后为空 `invalid_argument.comment_body`；`order` 非法或与 `root_id` 冲突 `invalid_argument.order`；`root_id` 格式非法或有 `reply_to_id` 无 `root_id` 时为 `invalid_argument.root_id`。
- W7 的 409 可能为 `conflict.access_version` 或 `conflict.idempotency`：新增响应组件 `409ConflictCommentCreate`（`oneOf` 两个 Problem Schema），W7 引用它（D-NC011-18）。W7 404：主题不可见 `not_found.content`；root/回复目标不存在或跨主题 `not_found.comment`。

### 11.5 决定
本节决定编号 D-NC011-04、05、06、07、11、18，登记于 community_discussion.md §14。

## 12. NC-012a 补丁（2026-09-12，互动、分享与举报；逐项落地见 [community_interactions.md](community_interactions.md)）

### 12.1 写响应包装（替代 §2 W10/W11 成功列与 §7 表对应行，D-NC012-05）
- W10 成功为 200 `ReactionResponse{reaction: ReactionState, command}`；W11 成功为 200 `BookmarkResponse{bookmark: BookmarkState, command}`；二者 `additionalProperties: false`。§7 表 `reaction.set`、`bookmark.set` 的完整结果 Schema 相应改为这两个包装。
- W10 同值（If-Match 通过且 value 未变）不写、不升版本，`applied_version` = 当前版本；W11 同理，且 If-Match 可选（D-NC012-03、04）。

### 12.2 新增读端点（§2 端点目录追加，D-NC012-06）
- R7 `GET /me/share-links?cursor&limit` → 200 `ShareLinkPage{items: ShareLink[] ≤ 100, next_cursor}`：本人创建的链接按 `created_at desc, id desc`，含已撤销；游标 = base64url 去 padding(`"<created_at 6 位微秒>|<share_id>"`)，非法 → 400 `invalid_argument.cursor`；limit 规则同 §6。
- R8 `GET /bookmarks/{target_type}/{target_id}` → 200 `BookmarkState`（只读本人记录，无记录为 `active=false, version=0`）；目标不可读 → 404。

### 12.3 R3 与 R4
- R3 ETag = `"<viewer 的 Reaction.version>:<like>:<dislike>"`（无记录版本为 0）；ACL 先于 304（D-NC012-12）。
- R4：`share_id` 格式不符、不存在、已撤销、目标对当前读者不可读，一律 404 共用 `NotFoundContent` 体；ACL 扫描矩阵 E4 由此转为真实断言（D-NC012-07）。

### 12.4 错误目录增补（§4.1）
- `forbidden.thread_closed` 行的场景增加：作者对自己不公开的内容（或其下评论）赞踩或创建分享链接。
- 413 行增加 `too_large.detail`（`limit=500`，举报说明按 code point）。
- 400 行增加：`invalid_argument.target_type`、`invalid_argument.target_id`（路径参数 `field` 为 `target_type`/`target_id`，请求体为 `/target_type`/`/target_id`）、`invalid_argument.reaction`、`invalid_argument.bookmark`、`invalid_argument.share_link`、`invalid_argument.report`（`field` 为 JSON Pointer）、`invalid_argument.share_id`。
- `forbidden.not_owner` 行增加 `share.revoke`（非创建者）。

### 12.5 决定
本节决定编号 D-NC012-03、04、05、06、07、12，登记于 community_interactions.md §15。

## 13. NC-013 补丁（2026-09-12，通知投递、正文拉取与补拉；逐项落地见 [community_deliveries.md](community_deliveries.md)）

### 13.1 新增读端点（§2 端点目录追加，D-NC013-09）
- R9 `GET /notifications/pull?notifier_delivery_id=<原始不透明值>` → 200 `NotificationBody`；映射缺失、非本人、设备不匹配、目标内容不可读四类失败一律 404 共用 `NotFoundContent` 体（无可区分字段，R-20）；`notifier_delivery_id` 缺失 → 400 `invalid_argument.notifier_delivery_id`。
- R10 `GET /notifications?cursor&limit` → 200 `NotificationPage{items: NotificationEntry[], next_cursor}`：仅登录收件人；读时按 `(recipient, target, kind)` 滑窗 10 分钟聚合（`reply`/`mention` 不聚合）；排序 `(first_created_at, latest_notification_id)` 降序（ID 按 UTF-8 字节序）；游标 = base64url 去 padding(`"<first_created_at>|<latest_notification_id>"`)，非法 → 400 `invalid_argument.cursor`；limit 同 §6；**补拉不产生任何 ACK**。

### 13.2 非命令写（§2 端点目录注明「非命令」，D-NC013-09）
- W15 `PUT /notifications/mutes/{content_id}` → 200 `NotificationMuteState{content_id, muted: true}`；W16 `DELETE /notifications/mutes/{content_id}` → 200 `{content_id, muted: false}`。幂等直写；无 `Idempotency-Key`、不进命令账本、不写行为事件；`content_id` 非 `note_` → 400 `invalid_argument.content_id`；操作枚举闭集 17 个不变。

### 13.3 新 Schema（§5.3 追加；全部 `additionalProperties: false`，可空用 3.1 类型数组）
- `NotificationBody{notification_id ($ref community_common notificationRecordId), kind (comment|reply|mention|like), target {kind: content|comment, id, thread_id?}, body_markdown, actor_id, created_at}`。
- `NotificationEntry{kind, target, latest_notification_id, event_count (integer ≥ 1), first_created_at, last_created_at}`；`NotificationPage{items: NotificationEntry[] ≤ 100, next_cursor: string|null}`。
- `NotificationMuteState{content_id, muted (bool)}`。

### 13.4 错误目录增补（§4.1）
- 400 行增加：`invalid_argument.notifier_delivery_id`（R9 query 缺失）、`invalid_argument.content_id`（W15/W16 路径）。
- 404 行增加：R9 的四类失败统一 `not_found.content`（共用体；映射缺失/非本人/设备不匹配/内容失权不可区分——防存在性 oracle）。

### 13.5 限流（§6 表追加）
- `notifications.mute set/unset`：30/分钟。R9/R10 并入「全部读端点合计 600」。

### 13.6 示例（test/fixtures/openapi/examples/）
- 新增 `notification_body_comment.json`、`notification_page_merged.json`、`notification_mute_set.json`，`manifest.json` 17 → 20 项；NC-012a 的 seventeen 测试改为 `greaterThanOrEqualTo(17)`（D-NC013-10）。

### 13.7 决定
本节决定编号 D-NC013-01～14，登记于 community_deliveries.md §15。ACK（`/receipts`）属 notifier 3.0.3 契约，本契约**只引用不复制**，不新增任何 ACK 端点；投递语义为 at-least-once（DESIGN §6.1），不构成端到端 exactly-once。

## 14. NC-026 补丁（2026-09-13，行为事件上报与假名交付；逐项落地见 [community_behavior.md](community_behavior.md)）

### 14.1 新增端点（§2 端点目录追加，D-NC026-07、D-NC026-09）
- W17 `POST /v1/analytics/events`：**非命令写**（无 `Idempotency-Key`、不进命令账本、不写行为事件；§3.2 的 17 操作枚举**不变**）；请求体 `AnalyticsEventBatch`；200 `AnalyticsEventsAccepted`。语义 at-least-once，服务端按 `event_id` create-if-absent 去重；任何文档与注释不得声称 exactly-once。
- R11 `GET /v1/analytics/pseudonym` → 200 `ActorPseudonym`：返回本人 `actor_pseudonym`，首次调用 create-if-absent 建立映射（幂等），不写行为事件。存在理由见 community_behavior.md D-NC026-07。

### 14.2 新 Schema（§5.3 追加；全部 `additionalProperties: false`，可空用 3.1 类型数组）
- `AnalyticsEventRequest{event_id (^bev_[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$), schema_version (const 1), event_type (enum private_note.revision_saved | private_note.session_ended), occurred_at ($ref community_common timestamp), note_ref ($ref community_common hex64), platform (enum android|ios|windows|macos|linux|web), app_version (string minLength 1), attributes}`；`attributes` 按 `event_type` 分派（community_behavior.md §3.2），额外允许可选 `dropped_before`（integer ≥ 1）。
- `AnalyticsEventBatch{events (AnalyticsEventRequest[]，minItems 1，maxItems 500)}`。
- `AnalyticsEventsAccepted{accepted (integer ≥ 0), duplicates (integer ≥ 0), actor_pseudonym ($ref community_common actorPseudonym)}`；不变式 `accepted + duplicates == len(events)`。
- `ActorPseudonym{actor_pseudonym ($ref community_common actorPseudonym)}`。

### 14.3 错误目录增补（§4.1）
- 400 行增加：`invalid_argument.events`（W17 请求体 Schema 不通过，`field` 为 JSON Pointer，前缀 `/events`，例 `/events/0/attributes/char_count`）、`invalid_argument.event_type`（W17 `event_type` 非本端点接受的 2 值）。
- 413 行增加：`too_large.events`（`limit` = 500）。
- 401/429/503 沿用 §4.1 既有行（`unauthenticated`、`rate_limited`、`unavailable`）。

### 14.4 限流（§6 表追加）
- `analytics.events`：60/分钟（客户端按批上报，单账号日常远低于该值）。R11 并入「全部读端点合计 600」。

### 14.5 示例与清单（`test/fixtures/openapi/examples/`）
- 新增 `analytics_events_batch.json`（`AnalyticsEventBatch`，valid）、`analytics_pseudonym.json`（`ActorPseudonym`，valid）；`manifest.json` 20 → 22 项；NC-013 的 `notification examples manifest has twenty entries and validates` 断言由 `equals(20)` 改为 `greaterThanOrEqualTo(20)`（D-NC026-22）。

### 14.6 决定
本节决定编号 D-NC026-06、07、09、11、12、22、23，登记于 community_behavior.md §15。`/v1/analytics/*` 不在 `/v1/community` 前缀下，沿用同一 `BearerAuth` securityScheme 与同一 L0 错误层；上报端点的 400 `invalid_argument.event_type` 是**端点级**闭集，不扩展 §2 的 17 操作枚举。
