# NC-009 可观察行为

「测试」指 SERVER 内 `.venv/bin/python -m pytest <文件> -q`（Emulator）；「规则测试」指 RULES 仓 `functions/` 内 `npm test -- community_rules`。响应体全部为 HTTP 层 JSON（经 `community_helpers.call`），断言唯一 `code`。

| ID | Given | When | Then |
|---|---|---|---|
| B01 | 新 `command_id`，合法 publish 载荷 | W1 | 201；`community_commands/{scope}__{cmd}` 存在且 `outcome=committed`、`result_fields` 为完整响应体（不含 `command`）；access/publication/snapshot/bindings/outbox/behavior_event 各一条，全部在同一次事务后出现 |
| B02 | B01 后 | 同键同载荷再次 W1 | 201，响应体逐字节等于首次；业务文档数不变 |
| B03 | B01 后 | 同键、`snapshot.title` 改动 | 409 `conflict.idempotency`，`original_request_hash` 等于账本 `payload_hash`；无写入 |
| B04 | 他人 scope 对已发布内容 W2 | — | 403 `forbidden.not_owner`；账本 `outcome=rejected`、`result_code=forbidden.not_owner`、`applied_version=null`；无业务写入 |
| B05 | `fn` 末尾注入一次异常 | W1 | 首次 503 `unavailable`，账本与业务均不存在；同键重试 201 且只有一份业务 |
| B06 | 事务提交后、响应前注入异常 | W1 再同键重试 | 首次异常；重试 201，业务仍只有一份，响应等于账本 `result_fields` |
| B07 | B01 后把账本 `result_compact_after` 改为过去，跑 `compact_once(now)` | 同键 W1 | `result_fields=={}`、`result_compacted_at` 非 null；重放 410 `gone.command_result`，体内 `command.compacted=true` 且含 `resource_ids/applied_version` |
| B08 | R5 | 已知/未知 command_id | 200 `CommandResult`（`compacted` 正确）/ 404 `not_found.command` |
| B09 | `Idempotency-Key` 格式非法（大写、31 位、带连字符） | 任一写 | 400 `invalid_argument.command_id`，`field=command_id` |
| B10 | 同载荷不同 operation（W1 与 W2 共用同键） | — | 409 `conflict.idempotency`（`payload_hash` 含 operation） |
| B11 | 已发布 | 再次 W1 | 409 `conflict.lifecycle`，`current_state={published,active,allowed}` |
| B12 | `snapshot.attachments` 非空 | W1 | 409 `conflict.object_missing`，`missing_refs` 列全部 attachment_id |
| B13 | `markdown` 262145 字节 | W1 | 413 `too_large.markdown`，`limit=262144`；262144 字节 → 201 |
| B14 | 已发布，`If-Match` 缺失 / 过时 | W2 | 400 `invalid_argument.if_match` / 412 `conflict.version` 且 `current_version` 正确；正确 → 200，`access.version` +1，旧 Publication `superseded`，新 `live` |
| B15 | 已发布 | W3 | 200；`visibility=withdrawn`、`current_publication_id=null`、live→`retracted`、bindings 为空、outbox `content.withdrawn`；`ContentAccess.version` +1（NC-011 R2-05 前提） |
| B16 | 已收回 | W1 缺 If-Match / 过时 If-Match / 正确 If-Match | 400 `invalid_argument.if_match` / 412 `conflict.version` / 201；新 `pub_`，`content_id` 不变，旧 retracted 不变 |
| B17 | 已发布 | W4 | 409 `conflict.lifecycle`；收回后 W4 → 200 `lifecycle=trashed` |
| B18 | trashed 且 `trashed_at` 31 天前 / 30 天前 | W5 | 409 / 200 |
| B19 | trashed 且 `moderation_state=hidden` | W5 | 200 且 `moderation_state` 仍 hidden |
| B20 | active | W6 | 409；trashed → 202，`community_purge_tasks/{content_id}.state=queued`，`lifecycle=purge_pending`；再 W5 → 409 |
| B21 | 已发布修订 A，未调用 W2 | R1 无头 / 带相等 `If-None-Match` | 200 ETag=`"<version>"` 且快照为 A（私改不公开）/ 304 空体 |
| B22 | 作者 3 篇 | R6 `limit=2` 两页 / `limit=101` | 两页拼接恰 3 篇、`next_cursor` 末页 null / 400 `invalid_argument.limit` |
| B23 | access 三元组写成 `published/trashed/allowed` | R1 | 500 `internal.state_corrupted` 且日志含 `COMMUNITY_STATE_CORRUPTED` |
| B24 | 入口 E1/E2/E5 × 原因 withdrawn/trashed/hidden（9 条） | 他人视角请求 | 404；`code=not_found.content`；响应体逐字节等于共用体；不含标题/正文任意 20 字连续片段 |
| B25 | 入口 E3/E4/E6 × 3 原因（9 条） | — | `xfail(strict=True, reason="owner: NC-008/NC-012/NC-013")`；运行结果为 `x`（不是 `s`） |
| B26 | 规则测试 | 匿名与 alice 对 8 个社区集合 get/set/update/delete | 全部拒绝（64 断言）；`identity_map/alice-uid` 对 alice 可读 |
| B27 | 全流程日志 | `caplog` | 不含 fixture 标题、正文前 20 字、`Idempotency-Key` 原值 |
| B28 | outbox 新事件类型 | 现有 `handle_outbox_event` 收到 `content.published` | 返回 None，不抛错（已核 `notifications.py` 末尾「未知事件类型：静默忽略」） |
| B29 | 同 scope 两次命令、另一 scope 一次命令 | 查映射与事件 | 同 scope 同一 `actor_pseudonym`；两 scope 不同；假名 ≠ `psn_`+SHA-256(scope)[:32]；事件文档无 `owner_scope`/`app_user_id` 字段 |
| B30 | `fn` 首次执行时由另一客户端改写其事务读过的文档 | W1 | 回调被重跑；两次回调的 `new_ids` 相同；最终 Publication/事件各一份 |
