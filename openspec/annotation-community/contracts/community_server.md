# 服务端契约：命令账本服务、发布/收回/生命周期事务与 ACL 扫描（NC-009）

状态：`FROZEN_FOR_NC-009`（2026-09-11）。权威来源：[community_api.md](community_api.md)（NC-003，端点/头/错误/Schema 唯一来源）；[DESIGN](../DESIGN.md) §4.1～§4.4、§7.3、§7.4、§11.4～§11.5；[state-machines](state-machines.md) SM-2a/2b/3/4/SM-C；[community-models](community-models.md) §2、§3.2；[PRD](../PRD.md) §6.2、R-05/R-20；[TASKS](../TASKS.md) NC-009；SERVER 现状盘点（2026-09-11）。本文把已定设计落到 functions-py 的模块、集合、事务流程与测试判据，供执行者照抄；与上游冲突以上游为准并回报主 Agent。

## 1. 仓库、环境与基线

| 项 | 实值 |
|---|---|
| SERVER（canonical，写入目标） | `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`（git 根即此目录，HEAD `30a868c`；`xuan-migration/xuan-server/server/functions-py` 是过期副本，缺 `notifications.py/follow.py/fcm.py/community_hash.py`，**不写**） |
| RULES（只读引用 + 新增一个测试文件） | `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-server/server/`（git 根 `xuan-migration/xuan-server`，gitea）：`firestore.rules`（777 行，顶层 `match /{document=**} allow read, write: if false` 默认拒绝）、`firebase.json`、`emulator/start_emulator.sh`；规则单测骨架 `functions/test/firestore.rules.test.ts`（`@firebase/rules-unit-testing`，jest，`node_modules` 已装） |
| Emulator | Firestore `192.168.0.165:8080`、Auth `192.168.0.165:9099`（局域网另一台机器，2026-09-11 实测可达；`tests/conftest.py` 默认即此地址） |
| Python | `functions-py/.venv/bin/python`（主 Agent 2026-09-11 建立，`requirements.txt`：firebase-functions~=0.4.2、firebase-admin~=6.5.0、pytest；`.venv` 在 `.gitignore`）；测试 `python -m pytest tests -q` |
| 身份 | `require_auth_uid` + `resolve_app_user_id`（`xuan/identity.py`，`identity_map/{uid}` → `appUserId`）；社区 `owner_scope = author_id = appUserId` |
| 错误 | `XuanHttpsError` 与 `_L0_MAP`（`xuan/errors.py`）；REST 层 `make_problem_details`（`playground_rest.py`）；社区新增 `xuan/community/errors.py` 输出 community_api §4.1 的 `code` 与 §4.2 的 `type` |
| 事务 | `google.cloud.firestore.transactional`（`identity.py` 已用；handlers 其余处未用）；社区命令**全部**在事务内 |

## 2. 模块与集合

### 2.1 新增/修改文件（写入白名单）

| 文件 | 内容 |
|---|---|
| `xuan/community/__init__.py` | 空 |
| `xuan/community/errors.py` | `CommunityError(code, status, **extra)`；`problem(code, status, extra)` → Problem Details 字典（`type` 按 community_api §4.2 映射） |
| `xuan/community/ids.py` | `new_id(prefix)`（`prefix + uuid4().hex`）；`is_valid(prefix, s)`；`is_command_id(s)`（DESIGN §2.1.1 正则） |
| `xuan/community/command_service.py` | §3 |
| `xuan/community/content_service.py` | §4（W1～W6 业务函数，纯事务回调） |
| `xuan/community/access.py` | §5（读路径鉴权：`resolve_access(content_id, viewer)` → `visible / not_found`） |
| `xuan/handlers/community_contents.py` | `community_contents_py`（`on_request`）：路由 W1～W6、R1、R6 |
| `xuan/handlers/community_commands.py` | `community_commands_py`（`on_request`）：R5；`compact_community_commands_py`（`on_schedule` 每日）：§3.5 |
| `xuan/config.py` | `COLLECTIONS` 追加 §2.2 六个键 |
| `main.py` | 导出上述三个函数 |
| `tests/conftest.py` | `clean_collections` 的 `names` 追加六个社区集合（**只追加**） |
| `tests/test_community_commands.py`、`tests/test_community_publications.py`、`tests/test_community_acl_sweep.py`、`tests/community_helpers.py` | §7 |
| RULES 仓 `functions/test/community_rules.test.ts` | §6 |

### 2.2 Firestore 集合（`COLLECTIONS` 键 → 集合名）与文档

| 键 | 集合 | 文档 ID | 字段 |
|---|---|---|---|
| `community_content_access` | `community_content_access` | `content_id` | community-models §2.2 全部字段 + `updated_at`（服务器时间戳） |
| `community_publications` | `community_publications` | `pub_` ID | §2.1 全部字段 + `public_snapshot_ref`（= 同 ID 的快照文档 ID，见下）+ `author_id` |
| `community_public_snapshots` | `community_public_snapshots` | `pub_` ID（与 Publication 同 ID） | `PublicSnapshot`（community_api §5.1）；**本任务只接受内联 `markdown` ≤ 262144 字节且 `attachments == []`**（D-NC009-03） |
| `community_content_bindings` | `community_content_bindings` | `cbnd_` ID | §2.3 字段；每次 publish/update 事务内删旧插新（按 `content_id` 查询） |
| `community_commands` | `community_commands` | `f"{owner_scope}__{command_id}"` | NC-002 `community_command_record.schema.json` 全部必填字段（`owner_scope, operation, command_id, payload_hash, outcome, resource_ids, applied_version, result_http_status, result_code, result_fields, committed_at, result_compact_after, result_compacted_at`） |
| `community_behavior_events` | `community_behavior_events` | `bev_` ID | DESIGN §11.2 外层字段 + `attributes`（§11.4 服务端事件） |

outbox 沿用 `COLLECTIONS["outbox"]`（`playground_outbox`），事件文档 `{id, event_type, content_id, publication_id?, actor_app_user_id, created_at}`；`event_type` 取 `content.published / content.updated / content.withdrawn / content.trashed / content.restored / content.purge_requested`。通知消费归 NC-013（`notifications.py` 现有分支不识别这些类型时必须原样忽略，本任务测试断言不抛错）。

Firestore 安全规则：以上六个集合**不新增任何 match**，由顶层默认拒绝覆盖（客户端不可直读写；全部经 HTTP 函数）。

## 3. 命令账本服务（DESIGN §7.4 逐条落地）

### 3.1 接口

```python
@dataclass
class CommandContext: owner_scope: str; command_id: str; operation: str; payload: dict; now: datetime
@dataclass
class CommandOutcome: status: int; code: str | None; resource_ids: dict; applied_version: int | None; body: dict  # code 为 None 表示 committed

def run_command(ctx: CommandContext, fn: Callable[[Transaction, CommandContext], CommandOutcome]) -> CommandResponse
```

`CommandResponse = (http_status, body, headers)`；`body` 在 committed 时为完整结果（community_api §5.3，含 `command`），rejected 时为 Problem Details（含 `code`）。

### 3.2 事务流程（单个 `@transactional` 回调，可被 Firestore 自动重跑）

1. `payload_hash = SHA-256_hex(canonical_json({"operation": ctx.operation, "payload": ctx.payload}))`，`canonical_json` = `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False)`（D-NC009-01；不复用 `hashing.hash_payload` 的插入序语义）。
2. 事务内读 `community_commands/{owner_scope}__{command_id}`：
   - 存在且 `payload_hash` 相同 → **重放**：`result_compacted_at is None` → 返回原 `result_http_status` 与 `result_fields`；已精简 → `410 gone.command_result` + `command`（最小结果）。不执行 `fn`。
   - 存在且 `payload_hash` 不同 → `409 conflict.idempotency`，`original_request_hash` = 存储值。不写任何东西。
   - 不存在 → 3。
3. 调 `fn(tx, ctx)`：`fn` **只做事务读与事务写**（业务记录、计数、outbox、行为事件），不上传、不推送、不 sleep；前置失败返回 `CommandOutcome(status≥400, code=...)`，**不抛异常**（抛出即整笔回滚且不记账）。
4. 同一事务写账本终态：`outcome = committed if status < 400 else rejected`；`result_fields` = committed 时的完整 body（不含 `command` 自身），rejected 时 `{}`；`result_code` = rejected 时的 `code`，否则 `null`；`applied_version` 按 community_api §7 表（rejected 为 `null`）；`committed_at = now`；`result_compact_after = now + 14d`；`result_compacted_at = null`。
5. 事务提交后组装响应；`command` 字段 = `CommandResult`（`compacted=false`）。
6. 事务提交前异常 → 无账本、无业务；同键重试从 2 重新开始。提交后响应前崩溃 → 账本已有终态；同键重试走重放。

### 3.3 行为事件（DESIGN §11.4/§11.5）

`fn` 在 committed 路径内写一条 `community_behavior_events`：`{event_id: bev_…, event_type: ctx.operation, actor_pseudonym: 由 owner_scope 派生（本任务用 SHA-256(owner_scope)[:32] 冒名 psn_ 前缀，D-NC009-04，NC-026 替换为真实假名表）, occurred_at, schema_version: 1, attributes}`；`attributes` 不含标题/正文/附件名/note_id 原值；rejected 不写事件。

### 3.4 R5 命令查询

`GET /v1/community/commands/{command_id}`：按认证 `owner_scope` 读账本；无记录 → `404 not_found.command`；有 → `200 CommandResult`（`compacted` = `result_compacted_at is not None`）；Firestore 异常 → `503 unavailable.command_status`。

### 3.5 精简任务

`compact_community_commands_py`（`scheduler_fn.on_schedule("every 24 hours")`）：查询 `result_compact_after <= now and result_compacted_at == null`，批量 `update({"result_fields": {}, "result_compacted_at": now})`；不删除文档（DESIGN §7.4 第 4 条：最小账本永久保留）。测试用直接调用 `compact_once(now)` 注入时间。

## 4. 内容命令（`content_service.py`，每个函数都是 §3.2 的 `fn`）

前置读取顺序固定：账本（§3.2 已读）→ `community_content_access/{content_id}` → 需要时 `community_publications/{current_publication_id}`。判定顺序固定：**身份 → 存在性 → 归属 → 版本 → 生命周期 → 载荷**（同一请求多错只报第一个）。

| 操作 | 前置（按顺序） | 事务写 | 结果 |
|---|---|---|---|
| `content.publish`（W1） | `content_id/revision_id/content_hash/snapshot` 通过 Schema；access 不存在或 `visibility=withdrawn`；存在时 `author_id == owner_scope`（否则 403 `forbidden.not_owner`）；`lifecycle == active`（否则 409 `conflict.lifecycle`）；`visibility == published` → 409 `conflict.lifecycle`（重复 publish）；`snapshot.attachments == []` 且无 `public_body_ref`（否则 409 `conflict.object_missing`，`missing_refs` 列全部 `attachment_id`/ref，D-NC009-03）；`markdown` UTF-8 ≤ 262144（否则 413 `too_large.markdown`） | 新 `pub_`（state live, version 1, published_at now）；快照文档；access 创建或更新（`visibility=published, current_publication_id, version+1`；新建时 version=1, lifecycle=active, moderation_state 保留既有或 allowed）；旧 live Publication → superseded（重新发布时旧为 retracted 不变）；bindings 删旧插新；outbox `content.published`；行为事件 `{is_republish}` | 201 `PublicationResponse`，ETag = access.version |
| `content.update`（W2） | access 存在且 `visibility == published`（否则 409 `conflict.lifecycle`；不存在 404 `not_found.content`）；归属；`If-Match == access.version`（否则 412 `conflict.version`）；`lifecycle == active`；载荷同 W1 | 新 Publication live、旧 live → superseded、access.version+1、快照、bindings、outbox `content.updated`、事件 | 200 |
| `content.withdraw`（W3） | 存在；归属；`If-Match`；`visibility == published`（否则 409） | live → retracted；`visibility=withdrawn`、`current_publication_id=null`、version+1；bindings 全删；outbox `content.withdrawn`；事件 | 200 `AccessResponse` |
| `content.trash`（W4） | 存在；归属；`If-Match`；`lifecycle == active`；`visibility != published`（否则 409，`current_state` 三元组） | `lifecycle=trashed`、`trashed_at=now`、version+1；outbox `content.trashed`；事件 | 200 |
| `content.restore`（W5） | 存在；归属；`If-Match`；`lifecycle == trashed`（`purge_pending/purged/active` → 409）；`now - trashed_at ≤ 30d`（否则 409） | `lifecycle=active`、`trashed_at=null`、version+1；`moderation_state` 不变；outbox `content.restored`；事件 | 200 |
| `content.purge`（W6） | 存在；归属；`If-Match`；`lifecycle == trashed`（`active` → 409，D-NC002-07；`purge_pending` 重复 → 409） | `lifecycle=purge_pending`、version+1；`community_purge_tasks/{content_id}`（`state=queued`，集合键 `community_purge_tasks`，**本任务只登记不执行**，清理归 NC-019）；outbox `content.purge_requested`；事件 | 202 `PurgeResponse`（`purge_task.state=queued`） |

`never_published` 内容对 W2～W6：access 不存在时 W2/W3 → 404 `not_found.content`；W4～W6 对从未发布的纯本地笔记不经服务端（客户端本地执行 SM-3），服务端收到时同样 404。

## 5. 读路径与 ACL（`access.py`；R-20 唯一扫描所有者）

`resolve_access(content_id, viewer_scope)`：
- access 不存在 → `not_found`；
- `author_id == viewer_scope` → `owner`（作者可读任何状态，用于 R6 与作者视角）；
- 否则须同时满足 `visibility == published` 且 `lifecycle == active` 且 `moderation_state == allowed` → `visible`；任一不满足 → `not_found`。

R1 `GET /contents/{content_id}`：`visible` 或 `owner` → 200 `ContentDetail`（他人视角下 `access` 只含 community_api §5.1 公共字段；`snapshot` 为当前 live 快照，无 live 时 `null`）；`not_found` → **共用同一响应体** `{"type":"not_found","title":"Not Found","status":404,"code":"not_found.content"}`，逐字节相同，无 `detail`、无原因字段。ETag = `"<access.version>"`；`If-None-Match` 相等 → 304。

R6 `GET /me/contents?cursor&limit`：`author_id == owner_scope` 的 access 列表，按 `updated_at desc, content_id` 排序，游标 = base64url(`updated_at|content_id`)；`limit` 越界 → 400 `invalid_argument.limit`。

**ACL 扫描矩阵**（`tests/test_community_acl_sweep.py`，参数化 6 入口 × 3 原因 = 18 条）：

| 入口 | 端点 | 本任务实现 | 所有者 |
|---|---|---|---|
| E1 正文 | R1 | ✔ | NC-009 |
| E2 历史 | R1 携带旧 `If-None-Match`（不得 304 泄漏存在性） | ✔ | NC-009 |
| E3 附件 | 公共媒体票据入口 | ✘ | NC-008 |
| E4 分享 | R4 `GET /share-links/{share_id}` | ✘ | NC-012 |
| E5 关联列表 | R1 响应中的 `snapshot.bindings`（404 体不得含 bindings） | ✔ | NC-009 |
| E6 通知正文 | 通知补拉端点 | ✘ | NC-013 |

原因 ∈ {withdrawn（已收回）, trashed（收回后回收站）, hidden（`moderation_state=hidden`）}。每条断言：状态 404、`code == not_found.content`、响应体逐字节等于共用体、不含快照标题/正文任意 20 字连续片段。未实现入口的 9 条用 `pytest.mark.xfail(strict=True, reason="owner: NC-0xx")`（D-NC009-05）：实现后测试转绿会因 `strict` 失败，逼迫接手任务删除标记；**禁止 `skip`**。

## 6. 安全规则测试（RULES 仓 `functions/test/community_rules.test.ts`）

用 `@firebase/rules-unit-testing` 加载 `../../firestore.rules`：对六个社区集合 + `community_purge_tasks`，分别以匿名上下文、`alice-uid` 认证上下文执行 `get/set/update/delete` → 全部 `assertFails`（默认拒绝生效，共 7 × 2 × 4 = 56 断言，可循环生成）；另断言 `identity_map/alice-uid` 对 alice 可读（回归既有规则未被破坏）。运行：`FIRESTORE_EMULATOR_HOST=192.168.0.165:8080 FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099 npm test -- community_rules`（在 RULES 仓 `functions/` 内）。

## 7. 测试判据（pytest，Emulator）

`tests/community_helpers.py`：`token_for(uid)`（复用 `test_playground_rest_writes.create_test_id_token` 的方式）、`call(handler, method, path, headers, body)`（用 `MagicMock` 构造 `req`，返回 `(status, json_body, headers)`）、`seed_access(...)`、`new_cmd()`。

| 文件 | 测试（名称逐字） |
|---|---|
| `test_community_commands.py` | `command_publish_commits_ledger_business_outbox_event_atomically`、`same_key_same_payload_replays_original_response`、`same_key_different_payload_returns_409_idempotency`、`rejected_precondition_writes_rejected_ledger_and_no_business`、`crash_before_commit_leaves_nothing_and_retry_succeeds`（在 `fn` 末尾注入异常一次）、`crash_after_commit_before_response_replays_on_retry`（提交后抛异常，再同键重试）、`compact_after_14_days_then_replay_returns_410_with_command`、`get_command_returns_minimal_result_and_404_unknown`、`command_id_format_invalid_returns_400`、`payload_hash_is_operation_bound`（同载荷不同 operation → 409） |
| `test_community_publications.py` | `publish_creates_access_publication_snapshot_bindings`、`publish_by_other_scope_is_403_not_owner`、`publish_twice_is_409_lifecycle`、`publish_with_attachment_is_409_object_missing`、`publish_oversize_markdown_is_413`、`update_requires_if_match_and_bumps_version`、`update_stale_if_match_is_412_with_current_version`、`withdraw_retracts_and_clears_bindings`、`republish_after_withdraw_keeps_content_id`、`trash_published_is_409_until_withdrawn`、`restore_after_30_days_is_409`、`restore_keeps_hidden`、`purge_from_active_is_409_and_from_trashed_queues_task`、`detail_etag_and_304`、`me_contents_pagination_limit_101_is_400`、`illegal_state_combination_reads_500`（直接写坏 access 三元组后 R1 → 500） |
| `test_community_acl_sweep.py` | 18 条参数化（§5） |
| 可观测性 | `logs_never_contain_title_or_body`（`caplog` 捕获全部 handler 日志，断言不含 fixture 标题与正文前 20 字） |

Red：每个测试文件先于实现提交；`from xuan.community import command_service` 的 ImportError 为 act/01 的 Red 原文。

## 8. 决定登记（NC-009，主 Agent 裁定，可推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC009-01 | `payload_hash` 用排序键 canonical JSON，含 `operation` | DESIGN §7.4 要求 operation 纳入；`hashing.hash_payload` 依赖插入序，不适合跨客户端 |
| D-NC009-02 | 账本文档 ID = `owner_scope__command_id` | (owner_scope, command_id) 唯一键落成单文档，事务内一次读即可判重放/冲突 |
| D-NC009-03 | 本任务只接受无附件、内联正文 ≤ 256 KiB 的发布；附件或外置正文一律 409 `conflict.object_missing` | 生产 BlobGateway（NC-025）与图片接口（NC-008）未交付，不用内存 fake 冒充 |
| D-NC009-04 | 行为事件的 `actor_pseudonym` 暂以 `psn_` + SHA-256(owner_scope)[:32] 生成 | NC-026 才冻结假名映射表；本任务保证事件与业务同事务的结构，不造假 |
| D-NC009-05 | ACL 扫描未实现入口用 `xfail(strict=True, reason="owner: NC-0xx")` | 让 18 条矩阵从本任务起就存在且可运行，接手任务实现后必须删标记，否则测试失败 |
| D-NC009-06 | `purge` 只登记 `community_purge_tasks`，不执行清理 | 清理任务与状态机 SM-6 归 NC-019 |
| D-NC009-07 | 规则测试写在 RULES 仓归档的 TS 测试目录 | 该目录仍有可用的 jest + `@firebase/rules-unit-testing`，Python admin SDK 绕过规则无法测；不复活 TS 业务代码 |
| D-NC009-08 | 限流不开启；429 不在本任务验收 | community_api §6；`rate_limit.py` 默认关闭 |
