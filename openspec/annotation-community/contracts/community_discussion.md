# 讨论区契约：两级评论、排序分页、修改历史与收回并发（NC-011）

状态：`FROZEN_FOR_NC-011`（2026-09-12）。权威来源：[community_api.md](community_api.md)（端点、头、错误、Schema；本任务补丁见其 §11）；[community_server.md](community_server.md)（`run_command` 事务、§10 校验与日志规则）；[community_client.md](community_client.md)（API 客户端、命令队列、§10 payload_hash 规范化）；[DESIGN](../DESIGN.md) §4.3 表 comment 两行、§4.4 R2-05、§6 排序与 mention、§7.1 限额、§7.3 错误目录、§11.4；[community-models](community-models.md) §2.4；[PRD](../PRD.md) §5.1 收回确认层、§6.3 讨论区分页、§6.4 七状态；[TASKS](../TASKS.md) NC-011 与 NC-009「R2-05 提交顺序」原文。本文把已定设计落到三个仓库的文件、集合、判定顺序、参考值与测试名，执行者照抄；与上游冲突以上游为准并停手上报主 Agent。

## 1. 仓库、基线与三线

| 线 | 仓库（git 根） | 基线（2026-09-12 Haiku 实测） | ACT |
|---|---|---|---|
| REST | `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter` | HEAD `5730ed9`；`dart test` `+69: All tests passed!` | act/01 |
| SERVER | `/Users/jingtaiwei/Git/Public/xuan-server/functions-py` | HEAD `df5c3da`；`pytest tests -q`：`5 failed, 459 passed, 9 xfailed`（既有失败恰为 `tests/test_config.py::test_集合名与_ts_逐项一致`、`tests/test_registration.py::test_全部_callable_已在入口注册`、`test_三个_trigger_已注册`、`test_与_入口总数对齐`、`test_没有多余的未声明导出`） | act/02 → 03 → 04 |
| RULES | `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-server`（测试在 `server/functions/`） | HEAD `ea8c9b8`；`npm test -- community_rules` `Tests: 65 passed` | act/04 |
| CLIENT | `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes` | HEAD `4588f78`；`flutter test` `+214: All tests passed!`；`flutter analyze` 0 | act/05 → 06 |

- 三线互不依赖：SERVER 与 CLIENT 以本文为准，不等 REST 提交（D-NC011-01）。同一仓库内的 ACT 严格串行。
- Emulator：Firestore `192.168.0.165:8080`、Auth `192.168.0.165:9099`。Python 命令一律带 `PYTHONDONTWRITEBYTECODE=1`；Flutter 命令一律带 `PATH=/Users/jingtaiwei/flutter/bin:$PATH`。
- `xuan-migration` 是容器目录不是 git 仓库，绝不在其根目录执行 git。

## 2. 写入白名单

### 2.1 SERVER（functions-py）

| 文件 | 允许的改动 |
|---|---|
| `xuan/config.py` | `COLLECTIONS` 末尾追加三键：`"community_threads": "community_threads"`、`"community_comments": "community_comments"`、`"community_comment_revisions": "community_comment_revisions"` |
| `xuan/community/validation.py` | 只追加：`COMMENT_CREATE_SCHEMA`、`COMMENT_EDIT_SCHEMA`（§4.1）与 `validate_comment_create(body) -> Optional[str]`、`validate_comment_edit(body) -> Optional[str]`（返回首个错误的 JSON Pointer，规则同 `validate_snapshot`，前缀为空：根错误返回 `"/"`，例 `"/mentions/0/length"`） |
| `xuan/community/discussion_service.py` | 新增，§3～§6 |
| `xuan/handlers/community_comments.py` | 新增，函数 `community_comment_py`（`@https_fn.on_request`，装饰器参数照抄 `community_contents.py`），§7 |
| `main.py` | 追加 `from xuan.handlers.community_comments import (community_comment_py,)  # noqa: F401` |
| `tests/conftest.py` | `clean_collections` 的 `names` 末尾追加三项 `COLLECTIONS["community_threads"]`、`COLLECTIONS["community_comments"]`、`COLLECTIONS["community_comment_revisions"]`（只追加） |
| `tests/community_helpers.py` | 只追加 `seed_thread(...)`、`seed_comment(...)`（§9.1） |
| `tests/test_community_comments.py` | 新增，§9 表 |
| RULES `server/functions/test/community_rules.test.ts` | `COMMUNITY_COLLECTIONS` 数组末尾追加 `'community_threads'`、`'community_comments'`、`'community_comment_revisions'`（11 × 2 × 4 + 1 = 89 断言） |

禁止：修改 `content_service.py`、`command_service.py`、`access.py`、`errors.py`、`ids.py`、`community_hash.py`、`handlers/community_contents.py`、`handlers/community_commands.py`、既有测试与既有 Schema；新增依赖；`skip`/`xfail`；永真断言；在测试内调用被测函数生成期望值（参考值写字面量）。

### 2.2 CLIENT（reading-notes）

| 文件 | 允许的改动 |
|---|---|
| `lib/src/community/models.dart` | 末尾追加 §11.1 八个类 |
| `lib/src/community/community_api.dart` | `CommunityApi` 内追加 §11.2 四个方法 |
| `lib/src/community/command_queue.dart` | 只改 §11.3 列出的四处 |
| `lib/src/community/pending_queue_page.dart` | 只改 §11.4 列出的三处 |
| `lib/src/community/content_detail_page.dart` | 只追加可选参数 `discussionBuilder`（§11.7） |
| `lib/src/community/comment_count_port.dart` | 新增，§11.5 |
| `lib/src/community/discussion_controller.dart` | 新增，§11.6 |
| `lib/src/community/discussion_panel.dart` | 新增，§11.7 |
| `lib/reading_notes.dart` | 追加导出上述三个新文件 |
| `test/community/discussion_test.dart` | 新增，§12 |

禁止：`lib/src/{domain,persistence,editor,history}`、`test/{persistence,contracts,editor,history,support}`、既有 `test/community/*.dart`、`pubspec.yaml`、`pubspec.lock`、`community_database.dart`（不加表）；新依赖；真实网络；`skip`；永真断言；测试内计算 payload_hash 期望值。

### 2.3 REST（repository-rest-adapter）

`openapi/openapi.yaml`（§13.1）；`test/community_openapi_contract_test.dart`（只在末尾 `group` 内追加 §13.2 四个测试，不改既有测试）；`test/fixtures/openapi/examples/` 新增三个文件并在 `manifest.json` 末尾追加三项（§13.3）。其他文件禁止。

## 3. 集合与文档（SERVER）

### 3.1 Thread：`community_threads/{thread_id}`

- `thread_id = "thr_" + sha256(community_hash.encode(["content", content_id])).hexdigest()[:32]`。参考：`note_00000000000000000000000000000001` → `thr_29d9aa55fe9a6205547731ea3b3dc1a7`。
- 字段恰为：`id`、`subject_kind`（恒 `"content"`）、`canonical_subject_key`（= content_id）、`visible_comment_count`（int）、`visible_commenter_count`（int）、`commenter_counts`（map：author_id → 该作者 `status=visible` 的评论数，≥ 1；降到 0 时删除该键）、`version`（int）、`created_at`、`updated_at`。
- 首个成功的 W7 创建（`version=1`）；此后该主题每个成功的 W7/W8/W9 使 `version += 1` 并写 `updated_at`。主题无文档时一切读取按 `version=0`、两计数为 0 处理（D-NC011-02、D-NC011-11）。

### 3.2 Comment：`community_comments/{comment_id}`

字段恰为 NC-002 `community_comment.schema.json` 的 11 个必填字段，存储文档必须通过该 Schema（测试以 `Draft202012Validator({"$ref": "community_comment.schema.json"}, registry=validation._REGISTRY)` 断言）：
`id`（`ctx.new_ids["comment_id"]`）、`thread_id`、`root_id`、`reply_to_id`（均取请求值）、`depth`（`root_id` 为 null → 0，否则 1）、`author_id`（= `ctx.owner_scope`）、`current_revision_id`、`observed_publication_id`（= 事务内读到的 `access.current_publication_id`）、`status`（新建 `"visible"`）、`created_at`、`version`（新建 1）。

时间格式（本任务全部时间字段）：`ctx.now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")`，恒 6 位微秒（D-NC011-03）。`ctx.now` 在事务外确定，回调重跑不变。

### 3.3 CommentRevision：`community_comment_revisions/{revision_id}`

字段恰为 `community_comment_revision.schema.json` 的 6 个：`id`（新建取 `ctx.new_ids["comment_revision_id"]`）、`comment_id`、`body`、`mentions`（§4.3 过滤后）、`parent_id`（W7 为 null；W8 为编辑前的 `current_revision_id`）、`created_at`。存储文档必须通过该 Schema。

### 3.4 outbox 与行为事件

- outbox（`COLLECTIONS["outbox"]`，写法照抄 `content_service.content_withdraw`）：字段恰为 `id`、`event_type`（`comment.created` / `comment.edited` / `comment.deleted`）、`content_id`、`thread_id`、`comment_id`、`actor_app_user_id`（= owner_scope）、`created_at`。不含正文与 mentions。
- 行为事件由 `run_command` 写（`event_type` = operation）。`CommandOutcome.body` **不含 `attributes` 键**，事件 `attributes` 因而为 `{}`，HTTP 响应体恰为 `{"comment", "command"}` 两键（D-NC011-12）。

### 3.5 新 ID

handler 调用 `build_command_context(..., extra_new_ids={"comment_id": ids.new_id("cmt_"), "comment_revision_id": ids.new_id("crev_")})`（W7、W8 都传；W9 不需要）。

## 4. 载荷校验

### 4.1 Schema（`validation.py` 追加，Draft 2020-12，复用 `_REGISTRY`）

```python
COMMENT_CREATE_SCHEMA = {"type": "object", "additionalProperties": False,
  "required": ["body", "expected_access_version"],
  "properties": {
    "body": {"type": "string"},
    "mentions": {"type": "array", "uniqueItems": True, "items": {"$ref": "community_comment_revision.schema.json#/$defs/mentionRef"}},
    "root_id": {"oneOf": [{"$ref": "community_common.schema.json#/$defs/commentId"}, {"type": "null"}]},
    "reply_to_id": {"oneOf": [{"$ref": "community_common.schema.json#/$defs/commentId"}, {"type": "null"}]},
    "expected_access_version": {"type": "integer", "minimum": 0}}}
COMMENT_EDIT_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["body"],
  "properties": {"body": {"type": "string"},
    "mentions": {"type": "array", "uniqueItems": True, "items": {"$ref": "community_comment_revision.schema.json#/$defs/mentionRef"}}}}
```

服务端不补默认值：`mentions` 缺省时按 `[]` 处理，但 payload_hash 以原始请求体计算（`build_command_context` 已如此）。

### 4.2 载荷阶段固定顺序（W7 与 W8 相同；W9 无载荷）

| # | 条件 | 结果 |
|---|---|---|
| P1 | 请求体是对象、`mentions` 是列表且条数 > 50 | 413 `too_large.mentions`，`limit=50` |
| P2 | `body` 是字符串且 `len(body) > 4000`（Python code point） | 413 `too_large.comment_body`，`limit=4000` |
| P3 | Schema 不通过（含请求体非对象） | 400 `invalid_argument.comment`，`field` = JSON Pointer |
| P4 | `body.strip() == ""` | 400 `invalid_argument.comment_body`，`field="body"` |
| P5 | （仅 W7）`reply_to_id` 非 null 且 `root_id` 为 null | 400 `invalid_argument.root_id`，`field="root_id"` |

全部拒绝经 `run_command` 记拒绝终态（与 NC-009 相同）。

### 4.3 mention 过滤（DESIGN §6，D-NC011-08）

P1～P5 通过后，逐条保留满足 `0 <= m["start_offset"]` 且 `body[m["start_offset"] : m["start_offset"] + m["length"]] == "@" + m["display_name"]` 的项，保持输入顺序，其余静默丢弃。不校验用户存在、注销与拉黑，不产生 mention 事件（归 NC-012）。

## 5. 写命令判定顺序（`discussion_service.py`，每个函数都是 `run_command` 的 `fn(tx, ctx)`）

### 5.1 `comment_create`（W7，201）

| # | 判定 | 结果 |
|---|---|---|
| 0 | `ctx.payload["path"]["content_id"]` 不匹配 `^note_[0-9a-f]{32}$` | 400 `invalid_argument.content_id`，`field="content_id"` |
| 1 | §4.2 P1～P5 | 见表 |
| 2 | `access.resolve_access(content_id, ctx.owner_scope, client=firestore_client, tx=tx)` 为 `not_found` | 404 `not_found.content`（无附加字段） |
| — | 读完 access 后立即：`if after_access_read_hook is not None: after_access_read_hook(ctx)` | 并发测试注入点（§8） |
| 3 | 结果为 `owner`，且 access 不满足 `visibility=="published" and lifecycle=="active" and moderation_state=="allowed"` | 403 `forbidden.thread_closed` |
| 4 | `body["expected_access_version"] != access["version"]` | 409 `conflict.access_version`，`current_access_version=access["version"]` |
| 5 | `root_id` 非 null：root 文档不存在、`root.thread_id != thread_id` 或 `root.depth != 0` | 404 `not_found.comment` |
| 6 | `reply_to_id` 非 null：目标不存在、`target.thread_id != thread_id`，或 `target.id != root_id and target.root_id != root_id` | 404 `not_found.comment` |
| 7 | root 的 `status != "visible"`；否则目标的 `status != "visible"` | 403 `forbidden.thread_closed` |
| 8 | 读 thread 文档（`tx`；全部读在写之前） | — |
| 9 | 写：comment、revision、thread（§3.1 计数：`visible_comment_count+1`；`commenter_counts[author]+1`，从 0 变 1 时 `visible_commenter_count+1`；`version+1` 或新建 1）、outbox `comment.created` | `CommandOutcome(201, None, {"comment_id", "thread_id"}, 1, {"comment": dto})` |

### 5.2 `comment_edit`（W8，200）与 `comment_delete`（W9，200）

| # | 判定 | 结果 |
|---|---|---|
| 0 | `comment_id` 不匹配 `^cmt_[0-9a-f]{32}$` | 400 `invalid_argument.comment_id`，`field="comment_id"` |
| 1 | （仅 W8）§4.2 P1～P4 | 见表 |
| 2 | 评论文档不存在；或其 thread 文档不存在 | 404 `not_found.comment` |
| 3 | `resolve_access(thread.canonical_subject_key, owner_scope, tx=tx)` 为 `not_found` | 404 `not_found.comment` |
| 4 | 结果为 `owner` 且 access 不公开（同 5.1 第 3 行条件） | 403 `forbidden.thread_closed` |
| 5 | `comment.status != "visible"` | 404 `not_found.comment` |
| 6 | `comment.author_id != ctx.owner_scope` | 403 `forbidden.not_owner` |
| 7 | `ctx.if_match is None` | 400 `invalid_argument.if_match`，`field="if_match"` |
| 8 | `ctx.if_match != comment.version` | 412 `conflict.version`，`current_version=comment.version` |
| 9W8 | 写：新 revision（`parent_id` = 旧 `current_revision_id`，body 相同也新建）；comment `current_revision_id` 更新、`version+1`，`created_at` 不变；thread `version+1`；outbox `comment.edited` | 200，`applied_version` = 新 version |
| 9W9 | 写：comment `status="deleted"`、`version+1`（revision 不动）；thread `visible_comment_count-1`、`commenter_counts[author]-1`（到 0 删键并 `visible_commenter_count-1`）、`version+1`；outbox `comment.deleted` | 200，`applied_version` = 新 version |

### 5.3 响应 DTO（W7～W9 与 R2 共用）

`comment_dto(doc)` = `{"id","thread_id","root_id","reply_to_id","depth","author": access.resolve_public_author(author_id),"status","created_at","version","current_revision"}`；`current_revision` 仅当 `status=="visible"` 时为 `{"id","body","mentions","created_at"}`（读当前 revision），否则为 `None`（不读 revision，正文不出现在响应中）。同一请求内按 author_id 缓存 `resolve_public_author` 结果。

## 6. 读端点 R2：`list_comments`

签名：`list_comments(content_id: str, viewer_scope: str, query: dict[str, str], if_none_match: Optional[str], client: Any = None) -> tuple[int, Optional[dict], dict[str, str]]`。

### 6.1 判定顺序

| # | 判定 | 结果 |
|---|---|---|
| 1 | `content_id` 格式非法 | 400 `invalid_argument.content_id` |
| 2 | `limit` 存在且不匹配 `^[0-9]+$` 或不在 1～100 | 400 `invalid_argument.limit`，`field="limit"`；缺省 20 |
| 3 | `order` 存在且不在 `{"newest","oldest"}` | 400 `invalid_argument.order`，`field="order"` |
| 4 | `root_id` 存在且不匹配 `^cmt_[0-9a-f]{32}$` | 400 `invalid_argument.root_id`，`field="root_id"` |
| 5 | `root_id` 存在且 `order == "newest"` | 400 `invalid_argument.order`；生效 order：有 root_id 为 `oldest`，否则 `order` 或 `newest` |
| 6 | `cursor` 存在且解码失败（§6.3） | 400 `invalid_argument.cursor`，`field="cursor"` |
| 7 | `resolve_access(content_id, viewer_scope)` 为 `not_found` | 404 `not_found.content`；`owner` 与 `visible` 均继续（内容作者可读自己已收回主题，D-NC011-06） |
| 8 | SM-C 状态组合非法（`access.is_valid_sm_c_state`） | 500 `internal.state_corrupted`，日志含 `COMMUNITY_STATE_CORRUPTED`（同 R1） |
| 9 | `root_id` 存在：root 不存在、`thread_id` 不符或 `depth != 0` | 404 `not_found.comment` |
| 10 | 计算 ETag（§6.2）；`if_none_match == etag` | 304，空体，头 `ETag` |
| 11 | 查询并组装 | 200，头 `ETag`、`Content-Type: application/json` |

### 6.2 ETag（替代 community_api §3.3 末条，D-NC011-05）

`'"%d:%s"' % (access_version, sha256(community_hash.encode([thread_version, root_id or "", order, cursor or "", limit])).hexdigest()[:16])`；`order` 与 `limit` 为生效值（整数），`cursor` 为请求原串。参考：access 3、无 thread、默认参数 → `"3:b713c1d13d46bdb5"`；access 3、thread version 3、`root_id=cmt_00000000000000000000000000000001`、`limit=5` → `"3:bbe031c2c1299d8c"`。

### 6.3 游标

- 编码：`base64.urlsafe_b64encode(f"{order}|{root_id or '-'}|{created_at}|{comment_id}".encode()).decode().rstrip("=")`。
- 解码失败的全部情形：不匹配 `^[A-Za-z0-9_-]{1,512}$`；补齐 `=` 后 base64url 或 UTF-8 解码失败；`split("|")` 不是 4 段；第 1 段 ≠ 生效 order；第 2 段 ≠ `root_id or "-"`；第 3 段不匹配 `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z$`；第 4 段不匹配 `^cmt_[0-9a-f]{32}$`。
- 参考：`newest|-|2026-09-11T08:00:00.000001Z|cmt_00000000000000000000000000000001` → `bmV3ZXN0fC18MjAyNi0wOS0xMVQwODowMDowMC4wMDAwMDFafGNtdF8wMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMQ`。

### 6.4 查询与组装

- 一级：`thread_id == T`、`depth == 0`；楼内：`root_id == R`。均 `order_by("created_at", d).order_by("id", d)`（newest 为 DESCENDING，oldest 为 ASCENDING），有游标时 `start_after({"created_at": c, "id": i})`，`limit(limit + 1)`。取回 > limit 条时截断到 limit，`next_cursor` 为第 limit 条的游标，否则 null。评论 ID 为 ASCII，Firestore 字符串序即 UTF-8 字节序（DESIGN §6）。复合索引归部署（D-NC011-20）。
- 一级查询时对本页每个一级评论（任何 status）做楼内查询 `oldest`、`limit(6)`：`reply_previews[root.id] = {"items": 前 5 条 dto, "next_cursor": 取回 6 条时第 5 条的游标，否则 None}`；楼内查询时 `reply_previews = {}`。
- 响应体恰为：`{"items", "next_cursor", "reply_previews", "visible_comment_count", "visible_commenter_count"}`，两计数取 thread 文档（无文档为 0）。

## 7. Handler：`community_comment_py`

- 鉴权与 owner_scope 解析、`/v1/community` 前缀剥离、query 合并照抄 `community_contents_py` 第 42～90 行写法；`_extract_auth_uid` 从 `xuan.handlers.playground_rest` 导入；`_parse_if_match` 与 `_make_response` 从 `xuan.handlers.community_contents` 导入（不复制、不修改该文件）。
- 路由（`path` 为剥离前缀后的路径）：

| 方法与路径 | 处理 |
|---|---|
| `GET /contents/{content_id}/comments` | `discussion_service.list_comments(content_id, owner_scope, query_args, If-None-Match 头)`；304 用 `https_fn.Response(response="", status=304, headers={"ETag": etag})` |
| `POST /contents/{content_id}/comments` | `payload={"path": {"content_id": content_id}, "body": body, "if_match": None}`，operation `comment.create` |
| `PATCH /comments/{comment_id}` | 畸形 If-Match → 调 `run_command` 之前返回 400 `invalid_argument.if_match`（D-NC009-16）；`payload={"path": {"comment_id": comment_id}, "body": body, "if_match": if_match}`，operation `comment.edit` |
| `DELETE /comments/{comment_id}` | 畸形 If-Match 同上；`payload={"path": {"comment_id": comment_id}, "body": {}, "if_match": if_match}`，operation `comment.delete`；忽略请求体 |
| 其他 | 404 `not_found.target` |

- `body = req.get_json(silent=True)`；为 None 时用 `{}`。日志只记 `type(exc).__name__`、command_id、content_id/comment_id，不得出现正文、mentions 或异常文本（D-NC009-19）。

## 8. 收回并发受控屏障（R2-05，D-NC011-13）

`discussion_service.py` 模块级变量 `after_access_read_hook: Optional[Callable[[CommandContext], None]] = None`，只在 `comment_create` 第 2 行读完 access 后调用。测试用 `monkeypatch.setattr(discussion_service, "after_access_read_hook", hook)` 注入，直接调用 `run_command`（服务级，不经 HTTP）。

- **withdraw 先提交**（测试 T31）：线程 W 执行 `run_command(wctx, wrapped_withdraw)`，`wrapped_withdraw(tx, ctx)` 先调用 `content_service.content_withdraw(tx, ctx)` 取得结果；首次调用时 `w_reads_done.set()` 并 `release.wait(10)`；返回结果。W 的 `run_command` 返回后 `w_done.set()`。主线程 `assert w_reads_done.wait(10)` 后执行 `run_command(cctx, discussion_service.comment_create)`；hook 首次调用时 `release.set()` 并 `w_done.wait(10)`，第二次及以后直接返回。期望：W 为 200；评论为 404 `not_found.content`；hook 调用恰 2 次（证明回调重跑）；该主题零评论、零 revision、无 thread 文档、outbox 无 `comment.created`、行为事件无 `comment.create`；评论命令账本 `outcome=rejected`、`result_code=not_found.content`。
- **comment 先提交**（T32）：线程 C 执行 `run_command(cctx, comment_create)`，hook 首次调用时 `c_read.set()` 并 `release.wait(10)`。主线程 `assert c_read.wait(10)`，启动线程 W 执行普通 `run_command(wctx, content_service.content_withdraw)`，`time.sleep(0.3)` 后 `release.set()`，join 两线程。期望：评论 201、W 200、hook 调用恰 1 次；随后非作者 R2 → 404 `not_found.content`；内容作者 R2 → 200 且含该评论；评论 `observed_publication_id` 等于收回前的 `current_publication_id`。
- **三方竞争**（T33）：连续 3 轮，每轮新内容；`threading.Barrier(3)` 同步两个非作者评论线程与一个作者收回线程后各自调用 `run_command`。每轮不变式：收回 200；每个评论 ∈ {201, 404 `not_found.content`}；评论文档数 = revision 数 = thread `visible_comment_count` = outbox `comment.created` 条数 = 行为事件 `comment.create` 条数 = 201 个数（为 0 时 thread 文档不存在）；每个 201 评论的 `observed_publication_id` 等于收回前的 publication id。
- **回调重跑新 ID 固定**（T34）：照抄 `test_community_commands.py` 第 513 行附近 `new_object_ids_are_fixed_across_transaction_retry` 的竞争线程写法，竞争对象为已有 thread 文档（竞争事务读后 `sleep(0.5)`，再 `tx.update(thread_ref, {"updated_at": <原值>})`，不改变字段集合）；被测回调包装 `comment_create` 并记录每次的 `ctx.new_ids`。期望：回调 ≥ 2 次；前两次 `comment_id`、`comment_revision_id` 相同；该 ID 评论恰一份；thread `visible_comment_count` 恰加 1。
- **停手条件**：若 hook 中任一 `wait(10)` 超时（Emulator 锁语义与 wound-wait 不符）或期望的提交顺序不出现，立即停手上报原始输出与 Emulator 日志，不得改屏障设计、不得放宽断言。

## 9. SERVER 测试判据（`tests/test_community_comments.py`，Emulator）

### 9.1 辅助（`community_helpers.py` 追加）

- `seed_thread(client, content_id, version=1, visible_comment_count=0, commenter_counts=None, created_at="2026-09-11T08:00:00.000000Z") -> dict`：按 §3.1 写 thread 文档，`visible_commenter_count = len(commenter_counts or {})`。
- `seed_comment(client, comment_id, content_id, author_id, depth=0, root_id=None, reply_to_id=None, status="visible", created_at="2026-09-11T08:00:00.000001Z", version=1, body="种子评论", observed_publication_id=None) -> dict`：写 §3.2 评论文档与 §3.3 revision 文档（revision id = `"crev_" + comment_id[4:]`，`parent_id=None`，`mentions=[]`）；不改 thread 计数。

### 9.2 测试表（名称逐字；HTTP 测试经 `call(community_comment_py, ...)`）

| ACT | ID | 测试 | 关键断言 |
|---|---|---|---|
| 02 | T01 | `create_root_comment_writes_comment_revision_thread_outbox_event_atomically` | 201；响应键恰 `{comment, command}`；`command.resource_ids` 恰 `{comment_id, thread_id}`；头 `ETag: "1"`；comment/revision 通过 NC-002 Schema；thread 字段集合恰 §3.1 九键且 `version=1`、两计数 1；outbox `comment.created` 一条且字段恰 §3.4；行为事件一条 `attributes == {}` |
| 02 | T02 | `comment_payload_hashes_match_reference` | `command_service.compute_payload_hash` 对 §10 三组输入等于三个字面量 |
| 02 | T03 | `thread_id_is_deterministic_from_content_id` | `discussion_service.thread_id_for("note_…0001") == "thr_29d9aa55fe9a6205547731ea3b3dc1a7"`，且 T01 的 `thread_id` 等于按其 content_id 派生值 |
| 02 | T04 | `reply_to_root_has_depth_1_and_same_root` | depth 1、root_id=R、reply_to_id null |
| 02 | T05 | `reply_to_reply_stays_depth_1_with_root_of_target` | reply_to_id=楼内回复 X、root_id=R → depth 1 |
| 02 | T06 | `reply_to_id_without_root_id_is_400` | 400 `invalid_argument.root_id`，账本 rejected |
| 02 | T07 | `cross_thread_root_or_target_is_404_not_found_comment` | root 属另一内容 → 404 `not_found.comment`；target 属另一楼 → 同 |
| 02 | T08 | `root_id_pointing_to_reply_is_404_not_found_comment` | root_id 指向 depth 1 → 404 |
| 02 | T09 | `reply_to_deleted_root_or_target_is_403_thread_closed` | root 已删 → 403；target 已删 → 403；均零写入 |
| 02 | T10 | `reply_to_hidden_target_is_403_thread_closed` | 目标 hidden → 403 |
| 02 | T11 | `body_4000_code_points_of_4byte_emoji_passes_and_4001_is_413` | `"\U0001F600" * 4000` → 201；`* 4001` → 413 `too_large.comment_body`、`limit=4000` |
| 02 | T12 | `blank_body_and_schema_errors_are_400` | `"  \n"` → 400 `invalid_argument.comment_body`；缺 `expected_access_version` → 400 `invalid_argument.comment` 且 `field="/"`；`mentions[0].length=1` → `field="/mentions/0/length"` |
| 02 | T13 | `mentions_over_50_is_413_and_mismatched_mentions_are_dropped` | 51 条 → 413 `too_large.mentions`；body `"@甲 你好 @乙"`，mentions 为甲（offset 0，length 2，匹配）与乙（offset 0，length 2，不匹配）→ revision 只存甲 |
| 02 | T14 | `non_author_on_non_public_content_is_404_not_found_content` | 参数化 withdrawn / trashed / hidden 三态，非作者 → 404、无附加字段、零评论零 outbox |
| 02 | T15 | `content_author_on_non_public_content_is_403_thread_closed` | 作者对自己 withdrawn 内容评论 → 403 |
| 02 | T16 | `stale_expected_access_version_while_visible_is_409` | access v2 已公开，请求 1 → 409 `conflict.access_version`、`current_access_version=2` |
| 02 | T17 | `same_key_replays_and_different_payload_is_409` | 同键同载荷 → 同 201 体、评论仍一份；同键异载荷 → 409 `conflict.idempotency` |
| 02 | T18 | `commenter_counts_track_distinct_visible_authors` | 甲 2 条、乙 1 条 → `visible_comment_count=3`、`visible_commenter_count=2` |
| 03 | T19 | `edit_creates_revision_chain_and_keeps_created_at` | 200；version 2；新 revision `parent_id` = 旧 id；comment `created_at` 不变；thread version +1、计数不变；outbox `comment.edited` |
| 03 | T20 | `edit_or_delete_by_non_author_is_403_not_owner` | 他人 W8、W9 → 403 `forbidden.not_owner` |
| 03 | T21 | `missing_if_match_is_400_and_stale_is_412` | 缺 → 400 `invalid_argument.if_match`；`"1"` 对 version 2 → 412 `current_version=2` |
| 03 | T22 | `malformed_if_match_is_400_without_ledger` | `If-Match: abc` → 400 且无账本文档 |
| 03 | T23 | `edit_or_delete_non_visible_comment_is_404` | deleted、hidden 评论的 W8/W9 → 404 `not_found.comment` |
| 03 | T24 | `delete_root_leaves_tombstone_and_replies_visible_and_counts_drop` | W9 200、`current_revision` null；R2 该 root 仍在、status deleted、`reply_previews` 仍含回复；计数各减 1；再回复该 root → 403 |
| 03 | T25 | `list_newest_default_20_with_cursor_and_reply_previews_of_5` | 种 21 个一级（id `cmt_…0001`～`…0021`，created_at `08:00:00.0000NNZ` 与 id 同号）＋ `…0021` 下 6 条回复（id `cmt_…0101`～`…0106`，created_at `2026-09-11T08:00:01.00000NZ`）；默认请求 items 为 `…0021` 到 `…0002` 共 20 条，`next_cursor` 等于 §10 字面量 C2；`reply_previews["cmt_…0021"].items` 为 `…0101`～`…0105`，`next_cursor` 等于字面量 C3；带 C2 再请求得 `…0001` 且 `next_cursor` null |
| 03 | T26 | `list_replies_by_root_oldest_with_cursor_and_newest_is_400` | `root_id` + `limit=5` → 5 条正序，带游标再取余 1 条；`root_id` + `order=newest` → 400 `invalid_argument.order`；游标与 root 不符 → 400 `invalid_argument.cursor` |
| 03 | T27 | `list_orders_same_created_at_by_id_bytes` | 同 created_at 的 `…0009` 与 `…00a0`：oldest 前者在先、newest 相反 |
| 03 | T28 | `list_etag_matches_reference_and_304_only_after_acl` | §6.2 两个参考 ETag 逐字；带该值 → 304；新增评论后旧 ETag → 200；非作者对 withdrawn 内容带合法 ETag → 404 |
| 03 | T29 | `list_rejects_invalid_limit_order_root_and_cursor` | `limit=101`、`limit=0`、`order=hot`、`root_id=abc`、`cursor=!!` 各 400 且 code 逐字 |
| 03 | T30 | `list_author_reads_withdrawn_thread_and_others_get_404` | 作者 200 含评论；他人 404 |
| 04 | T31 | `withdraw_commits_first_then_comment_retries_and_gets_404` | §8 |
| 04 | T32 | `comment_commits_first_then_withdraw_succeeds_and_hides_thread` | §8 |
| 04 | T33 | `two_comments_and_withdraw_three_way_race_keeps_invariants` | §8 |
| 04 | T34 | `comment_new_ids_fixed_across_transaction_retry` | §8 |
| 04 | T35 | `logs_never_contain_comment_body` | `caplog.at_level("DEBUG")` 覆盖 W7、W8、W9、R2 与一次 403、一次 409；正文 `这是一段不应出现在日志里的评论正文ABC` 及其编辑后正文的前 20 字均不在 `caplog.text` |

计数（T14 参数化 3 例，故 35 个测试名共 37 例）：本文件 act/02 后 `20 passed`、act/03 后 `32 passed`、act/04 后 `37 passed`；全量 `pytest tests -q -rf`：act/02 后 `479 passed`；act/03 后 `491 passed`；act/04 后 `496 passed`；每步 `5 failed` 恰为 §1 五个既有 ID、`9 xfailed` 不变。RULES：`Tests: 89 passed`。

## 10. 参考值（主 Agent 2026-09-12 以 functions-py `.venv` 计算）

| 名称 | 输入 | 值 |
|---|---|---|
| H1 create | operation `comment.create`；path `{"content_id": "note_00000000000000000000000000000001"}`；body `{"body": "第一条评论", "mentions": [], "root_id": null, "reply_to_id": null, "expected_access_version": 3}`；if_match null | `abe571820b1717be2379d8a60bfa8fc454b6e5158591f62fe1d31876b7eab428` |
| H2 edit | `comment.edit`；path `{"comment_id": "cmt_00000000000000000000000000000001"}`；body `{"body": "改过的评论", "mentions": []}`；if_match 2 | `fdbb995205743586e29d5b1bf187b09cd71e332d25059345532ab76991dc37fb` |
| H3 delete | `comment.delete`；同上 path；body `{}`；if_match 2 | `d65171fd03000501a18ad405e805a494b9a6717e27c03306a51fe5ada9dc7bb2` |
| TID | `note_00000000000000000000000000000001` | `thr_29d9aa55fe9a6205547731ea3b3dc1a7` |
| E1 | access 3，`[0, "", "newest", "", 20]` | `"3:b713c1d13d46bdb5"` |
| E2 | access 3，`[3, "cmt_00000000000000000000000000000001", "oldest", "", 5]` | `"3:bbe031c2c1299d8c"` |
| C1 | `newest\|-\|2026-09-11T08:00:00.000001Z\|cmt_00000000000000000000000000000001` | `bmV3ZXN0fC18MjAyNi0wOS0xMVQwODowMDowMC4wMDAwMDFafGNtdF8wMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMQ` |
| C2 | `newest\|-\|2026-09-11T08:00:00.000002Z\|cmt_00000000000000000000000000000002` | `bmV3ZXN0fC18MjAyNi0wOS0xMVQwODowMDowMC4wMDAwMDJafGNtdF8wMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMg` |
| C3 | `oldest\|cmt_00000000000000000000000000000021\|2026-09-11T08:00:01.000005Z\|cmt_00000000000000000000000000000105` | `b2xkZXN0fGNtdF8wMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAyMXwyMDI2LTA5LTExVDA4OjAwOjAxLjAwMDAwNVp8Y210XzAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMTA1` |

H1～H3 的 JSON 规范化同 community_client §10.1（键按码点序、无空白、`ensure_ascii=False`、`if_match` 键恒在）。客户端 `CreateCommentRequest.toJson()` 必须输出全部五键（null 与 `[]` 不省略），否则 H1 对不上。

## 11. CLIENT 实现

### 11.1 模型（`models.dart`，手写 `fromJson`/`toJson`，snake_case ↔ lowerCamel）

`MentionRef{userId, displayName, startOffset, length}`；`CommentRevisionPublic{id, body, mentions, createdAt}`；`Comment{id, threadId, rootId?, replyToId?, depth, author(PublicAuthor), status, createdAt, version, currentRevision?}`；`CommentReplyPreview{items, nextCursor?}`；`CommentPage{items, nextCursor?, replyPreviews(Map<String, CommentReplyPreview>), visibleCommentCount, visibleCommenterCount}`；`CreateCommentRequest{body, mentions(默认 const []), rootId?, replyToId?, expectedAccessVersion}`（`toJson` 恒输出五键）；`EditCommentRequest{body, mentions}`（`toJson` 恒两键）；`CommentResponse{comment, command(CommandResult)}`。

### 11.2 API（`CommunityApi`，写法照抄 `withdraw`，超时 15 秒，异常 → `ApiResult.transport`）

| 方法 | 请求 |
|---|---|
| `Future<ApiResult<CommentPage>> listComments(String contentId, {String? rootId, String? order, String? cursor, int limit = 20})` | `GET /contents/$contentId/comments`；query 恒含 `limit`，`root_id`/`order`/`cursor` 非 null 才加；只发 `Authorization`，**不发 `If-None-Match`**（D-NC011-15） |
| `Future<ApiResult<CommentResponse>> createComment(String commandId, String contentId, CreateCommentRequest body)` | `POST /contents/$contentId/comments`；头 `Authorization`、`idempotency-key`、`content-type: application/json`；无 `if-match` |
| `Future<ApiResult<CommentResponse>> editComment(String commandId, String commentId, EditCommentRequest body, {required int ifMatch})` | `PATCH /comments/$commentId`；另加 `if-match: "<v>"` |
| `Future<ApiResult<CommentResponse>> deleteComment(String commandId, String commentId, {required int ifMatch})` | `DELETE /comments/$commentId`；`if-match: "<v>"`；无体 |

### 11.3 命令队列（`command_queue.dart` 恰四处）

1. `enqueue`：`operation == 'comment.create'` 时跳过同 target 非终态冲突检查（同一内容可连续发多条评论，D-NC011-14）；`comment.edit`/`comment.delete` 以 comment_id 为 `targetId`，冲突规则不变。
2. `_executeApiCall` 追加三个 case：`comment.create` → `api.createComment(commandId, targetId, CreateCommentRequest.fromJson(body))`；`comment.edit` → `api.editComment(commandId, targetId, EditCommentRequest.fromJson(body), ifMatch: ifMatch ?? 0)`；`comment.delete` → `api.deleteComment(commandId, targetId, ifMatch: ifMatch ?? 0)`。
3. `_handleExecutionResult` 的 ok 分支：删除 `(result.value as dynamic).access` 写法，改为仅当 `result.value` 是 `PublicationResponse`、`AccessResponse` 或 `PurgeResponse` 时取其 `access` 更新缓存。
4. 410 分支：仅当 `row.operation.startsWith('content.')` 时调用 `onGone410`。

入队约定：`comment.create` 的 `path = {'content_id': contentId}`、`targetId = contentId`、`ifMatch = null`；`comment.edit/delete` 的 `path = {'comment_id': id}`、`targetId = id`、`ifMatch = comment.version`；delete 的 `body = {}`。`PendingOpWriter` 不改（comment 操作不映射 pending_op）。

### 11.4 待处理队列页（`pending_queue_page.dart` 恰三处）

1. `_extractSummary` 改为 `_extractSummary(String operation, String requestJson)`：`comment.create`/`comment.edit` → `'评论：' + String.fromCharCodes(body['body'].runes.take(20))`；`comment.delete` → `'删除评论'`；其余保持原逻辑。
2. `_extractMarkdown`：`comment.create`/`comment.edit` 返回 `body['body']`；其余不变。
3. `canCopyText` 的 code 集合追加 `forbidden.thread_closed`、`not_found.comment`、`conflict.access_version`。

### 11.5 评论计数端口（`comment_count_port.dart`，D-NC011-16）

```dart
class CommentCountUnavailable implements Exception { const CommentCountUnavailable(); }
class ApiCommentCountPort implements CommentCountPort {
  ApiCommentCountPort(this.api);
  final CommunityApi api;
  // listComments(contentId, limit: 1)；ok → visibleCommenterCount（PRD §5.1「N 人的评论」）；其他 → throw CommentCountUnavailable
  @override Future<int> countComments(String contentId);
}
Future<int?> resolveWithdrawCommentCount(CommentCountPort? port, String contentId); // port 为 null 或抛异常 → null
```

### 11.6 `DiscussionController extends ChangeNotifier`

构造：`DiscussionController({required CommunityApi api, required CommandQueue queue, required CommunityDatabase db, required String contentId, required Future<ContentAccessPublic?> Function(String contentId) accessLookup, required CommunityClock clock})`。

公开状态：`DiscussionViewState viewState`（枚举恰 `loading, empty, emptyClosed, partial, error, notVisible, offline, stale, success`）；`List<Comment> roots`；`Map<String, List<Comment>> replies`；`Map<String, String?> replyCursors`；`String? rootCursor`；`String order`（初值 `'newest'`）；`Set<String> failedReplyRoots`；`DateTime? lastLoadedAt`；`List<PendingComment> pending`（`PendingComment{commandId, body, rootId?}`，同文件定义）；`bool closed`；`String? notice`；`String? restoredDraft`。

| 方法 | 行为 |
|---|---|
| `load()` | `accessLookup` 算 `closed`（access 为 null 或非 published/active/allowed 为 true）；`listComments(contentId, order: order)`。ok：替换 `roots`，由 `replyPreviews` 填 `replies`/`replyCursors`，`lastLoadedAt = clock.nowUtc()`；无评论且无 pending → `closed ? emptyClosed : empty`，否则 `success`。problem 404 `not_found.content` → `notVisible`；其他 problem → `error`；transport：`roots` 为空 → `offline`，否则 `stale`（保留列表）。随后调用 `refreshPending()` |
| `loadMore()` | `rootCursor` 为 null 直接返回；带游标请求，ok 时**追加**到 `roots` 末尾（不替换既有对象）并合并预览；失败 → `partial`，保留列表 |
| `expandReplies(String rootId)` | `listComments(contentId, rootId: rootId, order: 'oldest', cursor: replyCursors[rootId], limit: 5)`；ok 追加并更新游标、移出 `failedReplyRoots`；失败加入 `failedReplyRoots`，`viewState` 不变 |
| `setOrder(String o)` | 只接受 `newest`/`oldest`；清空后 `load()` |
| `send(String body, {String? rootId, String? replyToId})` | `body.trim().isEmpty` → 返回；`body.runes.length > 4000` → `notice = '评论不能超过 4000 字'`，不入队；`closed` → `notice = '该内容不接受新评论'`，不入队；否则 `enqueue(comment.create, …, body: CreateCommentRequest(body, rootId, replyToId, expectedAccessVersion: access.version).toJson())`，加入 `pending`，`notifyListeners()`，`await queue.drain()`，`await refreshPending()` |
| `edit(Comment c, String body)` / `delete(Comment c)` | 入队 edit/delete；捕获 `PendingOpConflict` → `notice = '该评论有未完成的操作'`；随后 drain 与 `refreshPending()` |
| `refreshPending()` | 读 `db.communityCommands` 中本 owner、`operation` 以 `comment.` 开头、与本内容相关（create 的 `targetId == contentId`；edit/delete 的 targetId 属于已加载评论）的行：非终态 → `pending`（仅 create）；自上次调用以来变为 `committed` → `load()`；`rejected`：`conflict.access_version` → `notice = '内容状态已变化，请确认后重新发送'`、`restoredDraft` = 请求正文；`forbidden.thread_closed` → `notice = '该内容不接受新评论'`、`restoredDraft`；`not_found.content` → `viewState = notVisible`；其他 → 只设 `restoredDraft` |

构造后首次 `load()` 由面板 `initState` 触发；重启后新建控制器即从库中恢复 `pending`。

### 11.7 `DiscussionPanel` 与挂载

- `DiscussionPanel({Key? key, required DiscussionController controller, ScrollController? scrollController})`，`ListenableBuilder` 监听控制器；列表为单个 `ListView`（使用传入的 `scrollController`），每条评论 `key: ValueKey('comment-<id>')`，待发送项 `key: ValueKey('pending-<commandId>')`。
- 顶部两个 `ChoiceChip`：「最新」「最早」→ `setOrder`。评论项：`author.displayAlias`；visible 显示正文；deleted 显示「该评论已删除」；hidden 显示「该评论已被隐藏」；仅 visible 且未 `closed` 时显示「回复」。楼内回复缩进；`replyCursors[root]` 非 null 显示「展开更多回复」；root 在 `failedReplyRoots` 中显示「回复加载失败，点此重试」。`rootCursor` 非 null 显示「加载更多评论」。待发送项显示正文与「待发送」。
- 底部输入：`TextField`（`restoredDraft` 非 null 时写入并清空该字段）+「发送」；`closed` 时输入禁用并显示「该内容不接受新评论」。`notice` 非 null 时以 `Text` 显示。
- 七状态文案（§12 逐字断言）：

| 状态 | 显示 |
|---|---|
| loading | `CircularProgressIndicator` +「评论加载中」 |
| empty | 「还没有人评论，来写第一条」+ 输入框与「发送」 |
| emptyClosed | 「该内容不接受新评论」，无可用「发送」 |
| partial | 既有列表 +「更多评论加载失败」+「重试」（调用 `loadMore`） |
| error | 「评论读取失败」+「重试」（调用 `load`） |
| notVisible | 「内容已不可见」 |
| offline | 「离线，无法加载评论」+「重试」 |
| stale | 既有列表 + `'评论更新于 ' + HH:mm`（`lastLoadedAt.toLocal()` 两位补零）+「重试」 |
| success | 列表 |

- `ContentDetailPage` 追加可选参数 `final Widget Function(String contentId)? discussionBuilder;`，仅在成功渲染快照时于快照下方渲染 `discussionBuilder!(contentId)`；为 null 时渲染结果与现状完全相同（D-NC011-17）。

文案闭集（逐字，不得增删改）：「还没有人评论，来写第一条」「该内容不接受新评论」「该评论已删除」「该评论已被隐藏」「内容已不可见」「评论读取失败」「重试」「内容状态已变化，请确认后重新发送」「评论不能超过 4000 字」「待发送」「加载更多评论」「展开更多回复」「最新」「最早」「回复」「发送」「评论加载中」「更多评论加载失败」「离线，无法加载评论」「评论更新于 」「回复加载失败，点此重试」「该评论有未完成的操作」「评论：」「删除评论」。

## 12. CLIENT 测试判据（`test/community/discussion_test.dart`，`MockClient` + 临时目录真实 Drift 文件库）

| ACT | ID | 测试（名称逐字） | 关键断言 |
|---|---|---|---|
| 05 | K01 | `list_comments_sends_order_root_cursor_limit_without_if_none_match` | 路径逐字；query 恰 `{limit, root_id, order, cursor}`；无 `if-none-match`；解析 `replyPreviews` 与两计数 |
| 05 | K02 | `create_comment_sends_idempotency_and_expected_access_version_without_if_match` | 头含 `idempotency-key`、无 `if-match`；体键集合恰五键且 null 键存在 |
| 05 | K03 | `edit_and_delete_comment_send_if_match` | PATCH 与 DELETE 的 `if-match` 为 `"2"` |
| 05 | K04 | `comment_payload_hashes_match_python_reference` | 以 `CreateCommentRequest(...).toJson()`、`EditCommentRequest(...).toJson()`、`{}` 为 body 计算，等于 §10 H1～H3 字面量 |
| 05 | K05 | `comment_create_same_target_does_not_conflict_but_edit_does` | 同内容两次 create 均入队；同评论两次 edit 第二次抛 `PendingOpConflict` |
| 05 | K06 | `comment_restart_with_real_file_close_reopen_resends_same_key` | RW-5 ①：首发 `SocketException`，关库、同路径重开、新队列 `recover(); drain()`，POST 的 `Idempotency-Key` 与首发相同 |
| 05 | K07 | `comment_lost_response_reconciles_by_get_command_without_new_comment` | RW-5 ②：假服务器记录 POST 后，测试把行改为 `sending`，关库重开；`recover()` 先 `GET /commands/{id}` 得 committed，不再 POST；假服务器评论仍 1 条 |
| 05 | K08 | `comment_410_and_503_never_change_key` | RW-5 ③：503 `unavailable.command_status` → `unknown` → R5 404 → 以原键重发；410 `gone.command_result` → rejected，`onGone410` 调用次数 0；全程 key 唯一 |
| 05 | K09 | `comment_count_port_reads_visible_commenter_count` | 200 → 3；404 时 `resolveWithdrawCommentCount` 返回 null，`withdrawMessage(commentCount: null)` 为通用句式 |
| 05 | K10 | `pending_queue_summarizes_comment_commands` | 21 个 code point（含 emoji）正文 → 「评论：」+ 前 20 个 code point；delete →「删除评论」；rejected `forbidden.thread_closed` 可「复制正文」 |
| 06 | K11 | `discussion_first_level_newest_20_then_load_more_keeps_existing_items` | 20 条 + 游标；「加载更多评论」后 40 条；首批 20 个 `ValueKey` 仍在且为同一 Element；`scrollController.offset` 不变；第二次请求带 cursor |
| 06 | K12 | `discussion_replies_preview_5_then_expand_more` | 预览 5 条 +「展开更多回复」；点击请求 `root_id`、`order=oldest`、`limit=5`、`cursor`；追加后第 6 条出现 |
| 06 | K13 | `discussion_empty_states_distinguish_no_comments_and_closed` | 已公开空页 →「还没有人评论，来写第一条」且「发送」可用；access withdrawn 空页 →「该内容不接受新评论」且无可用发送 |
| 06 | K14 | `discussion_offline_comment_restart_confirms_once_and_pending_mark_clears` | 离线发送 → 面板与 `PendingQueuePage` 均见「待发送」/条目；关库重开，新控制器仍见「待发送」；换可用假服务器 drain 后服务器评论恰 1 条，面板无「待发送」，待处理页显示「所有操作都已完成同步」 |
| 06 | K15 | `discussion_body_over_4000_code_points_blocks_send` | 4001 个 emoji →「评论不能超过 4000 字」且库中 0 行；4000 个 → 1 行 |
| 06 | K16 | `discussion_409_access_version_keeps_draft_and_prompts` | 409 → 「内容状态已变化，请确认后重新发送」，输入框文本等于原草稿 |
| 06 | K17 | `discussion_late_success_after_withdraw_rereads_and_shows_not_visible` | POST 201 后 R2 返回 404 → 「内容已不可见」，该评论正文不出现 |
| 06 | K18 | `discussion_tombstones_show_deleted_and_hidden_texts` | deleted/hidden 文案逐字；deleted root 下无「回复」、其回复仍显示 |
| 06 | K19～K25 | `seven_states discussion loading`、`… empty`、`… partial`、`… error`、`… offline`、`… stale`、`… success` | 按 §11.7 表逐字断言；empty 同时断言「发送」存在（回答下一步做什么） |

计数：act/05 `+224`；act/06 `+239: All tests passed!`；`flutter analyze` 0。

## 13. REST 产物

### 13.1 `openapi.yaml`

1. `components/parameters` 新增 `RootId`（`name: root_id`、`in: query`、`required: false`、`schema: {type: string, pattern: '^cmt_[0-9a-f]{32}$'}`）与 `CommentOrder`（`name: order`、`in: query`、`required: false`、`schema: {type: string, enum: [newest, oldest]}`，不写 default）；R2 `parameters` 在 `Limit` 之后追加两者的 `$ref`。R2 `description` 追加三句：「无 root_id 为一级评论，order 缺省 newest；带 root_id 为楼内回复，只允许 oldest。」「ETag 见 community_api §11.2。」「root_id 不属于该主题时 404 not_found.comment。」
2. `CommentPage.required` 改为 `[items, next_cursor, reply_previews, visible_comment_count, visible_commenter_count]`；新增属性 `reply_previews: {type: object, propertyNames: {pattern: '^cmt_[0-9a-f]{32}$'}, additionalProperties: {$ref: '#/components/schemas/CommentReplyPreview'}}`、`visible_comment_count: {type: integer, minimum: 0}`、`visible_commenter_count: {type: integer, minimum: 0}`。
3. 新增 schema `CommentReplyPreview`：`type: object`、`required: [items, next_cursor]`、`items: {type: array, maxItems: 5, items: {$ref: Comment}}`、`next_cursor: {type: [string, "null"]}`、`additionalProperties: false`。
4. 新增响应组件 `409ConflictCommentCreate`（description「评论创建冲突：访问版本或幂等」，schema `oneOf: [$ref ProblemAccessVersionConflict, $ref ProblemIdempotencyConflict]`）；W7 的 `'409'` 改为引用它。W7 `description` 追加「主题不可见 404 not_found.content；root/回复目标不存在或跨主题 404 not_found.comment。」
5. 不改路径集合、方法、其他端点。

### 13.2 追加测试（名称逐字，69 → 73）

- `comment list declares root id and order query parameters`：R2 parameters 含两个 `$ref`；两组件字段逐字如 13.1。
- `comment page requires reply previews and counts`：`CommentPage.required` 集合逐字；`reply_previews` 结构；`CommentReplyPreview` 的 `maxItems: 5`、`additionalProperties: false`。
- `comment create conflict response accepts access version and idempotency problems`：W7 409 引用 `409ConflictCommentCreate`，其 `oneOf` 恰两项且目标逐字。
- `comment examples manifest has thirteen entries and validates`：manifest 长度 13，含 13.3 三项及 expect；`tool/check_examples.py` 退出 0。

### 13.3 示例（`test/fixtures/openapi/examples/`）

- `comment_page_with_reply_previews.json`（`CommentPage`，valid）：`items` 1 条一级评论（id `cmt_…0001`、thread `thr_29d9aa55fe9a6205547731ea3b3dc1a7`、root/reply null、depth 0、author `{"public_id": "author_example_1", "display_alias": "玄友"}`、visible、created_at `2026-09-11T08:00:00.000001Z`、version 1、current_revision `{"id": "crev_…0001", "body": "第一条评论", "mentions": [], "created_at": 同上}`）；`next_cursor` null；`reply_previews` 键 `cmt_…0001` → `{"items": [1 条回复 cmt_…0002，depth 1，root_id cmt_…0001，revision crev_…0002 正文「回复」], "next_cursor": null}`；`visible_comment_count` 2；`visible_commenter_count` 1。
- `comment_page_reply_previews_six.json`（`CommentPage`，invalid）：同上，但回复预览 `items` 为 6 条（id `cmt_…0002`～`…0007`）。
- `comment_tombstone_deleted.json`（`Comment`，valid）：status `deleted`、`current_revision` null，其余同一级评论。

ID 中的 `…` 表示补零到 32 位 hex。

## 14. 决定登记（NC-011，主 Agent 裁定，可推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC011-01 | REST、SERVER、CLIENT 三线并行，均以本文为准 | 三个仓库无文件交集；REST 只是契约文档与结构测试 |
| D-NC011-02 | Thread 惰性创建，ID 由 content_id 经 E 编码确定性派生 | 同主体原子去重（DESIGN Thread 行）；不需另建查找索引 |
| D-NC011-03 | 评论时间一律 6 位微秒 UTC | 定宽字符串的字典序即时间序，游标与排序跨端一致 |
| D-NC011-04 | R2 追加 `root_id`、`order`；楼内只允许 oldest；一级页附每楼前 5 条预览 | DESIGN §6「一级默认倒序、支持正序，楼内正序，各层独立分页」；PRD 一级 20、楼内 5 |
| D-NC011-05 | R2 ETag 改为 access 版本 + `E([thread_version, root_id, order, cursor, limit])` 截断哈希，替代 D-NC003-07 | 原「末条评论键」无法反映编辑与删除；不同分页参数必须有不同 ETag |
| D-NC011-06 | ACL 判定先于 304；内容作者可读自己不公开的主题 | R-20：不可见者不得凭旧 ETag 得知「未变化」；作者需看到已收回主题下的讨论 |
| D-NC011-07 | mentions > 50 为 413 `too_large.mentions`；DESIGN §7.1 第 303 行同步改为 413 | 与 community_api §4.1 目录、NC-009 §10.1 已实现一致；DESIGN 原写 400 与二者冲突 |
| D-NC011-08 | 不匹配的 mention 静默丢弃；用户存在性、拉黑与 mention 事件归 NC-012 | DESIGN §6 判定规则只需正文；其余三类无效 mention 需 NC-012 的关系数据 |
| D-NC011-09 | 去空白后为空的正文 400 `invalid_argument.comment_body` | 空评论无意义；客户端同样禁发，避免仅服务端拒绝 |
| D-NC011-10 | W8/W9 对不可见主题、非 visible 评论一律 404 `not_found.comment`，作者本人不公开主题为 403 | 与 W7 的 403/404 边界一致（DESIGN §7.3）；已删除评论不可再编辑 |
| D-NC011-11 | Thread 维护 `visible_comment_count` 与 `visible_commenter_count`（按作者计数 map），R2 返回二者 | PRD §5.1 收回确认层是「N 人的评论」；hidden 的计数维护归审核任务 |
| D-NC011-12 | 评论命令的行为事件 attributes 为空，`CommandOutcome.body` 不含 `attributes` | `run_command` 会把 body 原样放进响应，而 `CommentResponse` 禁止额外属性 |
| D-NC011-13 | 并发屏障：`discussion_service.after_access_read_hook` + 测试内包装 `content_withdraw`；锁语义不符即停手 | TASKS R2-05 要求受控屏障与回调重跑；不改 NC-009 已验收的 `content_service` |
| D-NC011-14 | `comment.create` 豁免同 target 冲突；edit/delete 以 comment_id 为 target | 同一内容下连续发多条评论是正常操作；同一评论的并发编辑仍需串行 |
| D-NC011-15 | 客户端 R2 不发 If-None-Match | 讨论区无后台轮询，刷新由用户触发；304 行为由服务端 T28 覆盖 |
| D-NC011-16 | `CommentCountPort` 读 `visible_commenter_count`，失败回退通用句式 | 与 D-NC010-05 衔接；PRD 禁止未替换占位符，宁缺数也不写假数 |
| D-NC011-17 | 讨论区经 `ContentDetailPage.discussionBuilder` 可选挂载 | 不改 NC-010 已验收页面的缺省渲染与其七状态测试 |
| D-NC011-18 | W7 409 改为 access_version 与 idempotency 的 oneOf 组件 | 原组件要求 `current_access_version`，幂等冲突体会被契约拒收 |
| D-NC011-19 | 规则测试纳入本任务（65 → 89） | 新增三集合须证明默认拒绝仍生效（沿用 NC-009 §6） |
| D-NC011-20 | 延后：网关路由、复合索引部署、限流开启、通知（NC-013）、mention 深度校验（NC-012）、审核隐藏的计数维护 | 本任务 TASKS 验收命令为 Emulator pytest 与 flutter test |
