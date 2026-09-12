# 互动契约：赞踩、收藏、分享、举报与 mention 文本校验（NC-012a）

状态：`READY`（2026-09-12：agy 四查 R1 READY、返工 0 项，见 `docs/blackbox-spec-rework/reviews/NC-012a-REVIEW-R1.md`；主 Agent 采纳其建议 1～3，写死 `resource_ids` 字典写法、`refreshPending` 防重入顺序与 I10 重试间隔）。权威来源：[TASKS](../TASKS.md) NC-012；[community_api.md](community_api.md)（W10～W14、R3、R4、§4.1 错误目录、§5 Schema、§6 限流、§7 账本；本任务补丁见其 §12）；[community_server.md](community_server.md)（`run_command` 事务、§5 ACL 扫描矩阵 E4）；[community_client.md](community_client.md)（命令队列、payload_hash）；[community_discussion.md](community_discussion.md)（NC-011 已交付的集合、handler 写法、403/404 边界，本文照抄其范式）；[DESIGN](../DESIGN.md) §2（Reaction/Bookmark/ShareLink 行）、§6（计数投影、mention 三元组与 code point）、§7.3；[community-models](community-models.md) §2.5；[PRD](../PRD.md) R-09、R-10、§5（踩/收藏/分享默认不通知）、§6「我的」分享链接管理与举报折叠、§6.2「该内容已不可访问」统一文案。执行者照抄；与上游冲突以上游为准并停手上报主 Agent。

## 1. 拆分、仓库、基线与线

- **拆分（D-NC012-01）**：本文 = **NC-012a**（互动命令、分享解析与管理、举报与本地折叠、mention 文本校验纯函数、客户端 `MentionRef` 单一化），可立即执行。TASKS NC-012 中依赖宿主社交注入点的部分 = **NC-012b**，`BLOCKED`（等 NC-001-02 联调取证）：资料/关注/私信/拉黑跳转（`social_navigation_adapter.dart`）、mention 候选来源与编辑器 @ 插入（`MentionInputEnhancer` 接入）、保存时解除 mention 的编辑器接线、「账号已注销」「已被目标拉黑」「user_id 不存在」三类无效 mention、两账号真实宿主关系验收。
- 派发前置：NC-003、NC-009、NC-010、NC-011 ACCEPTED；NC-016a ACCEPTED（CLIENT 与 NC-016a 同仓串行）。

| 线 | 仓库（git 根） | 基线（2026-09-12，派发前执行器复测，不符即停手） | ACT |
|---|---|---|---|
| REST | `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter` | HEAD `4671c92`；`dart test` `+73: All tests passed!` | act/01 |
| SERVER | `/Users/jingtaiwei/Git/Public/xuan-server/functions-py` | HEAD `0fad16e`；`pytest tests -q -rf`：`5 failed, 496 passed, 9 xfailed`（五个既有失败 ID 同 community_discussion §1） | act/02 → 03 |
| RULES | `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-server`（测试在 `server/functions/`） | HEAD `dd3445f`；`npm test -- community_rules` `Tests: 89 passed` | act/02 |
| CLIENT | `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes` | HEAD `d80703b`；`flutter test` `+270: All tests passed!`；`flutter analyze` 0 | act/04 → 05 → 06 |

- 三线互不依赖，均以本文为准。同一仓库内 ACT 严格串行。Emulator、环境前缀、容器目录禁令同 community_discussion §1。

## 2. 写入白名单

### 2.1 SERVER（functions-py）

| 文件 | 允许的改动 |
|---|---|
| `xuan/config.py` | `COLLECTIONS` 末尾追加五键：`"community_reactions"`、`"community_reaction_counts"`、`"community_bookmarks"`、`"community_share_links"`、`"community_reports"`（值与键同名） |
| `xuan/community/validation.py` | 只追加 §4.1 四个 Schema 常量与 `validate_reaction_set`、`validate_bookmark_set`、`validate_share_create`、`validate_report_create`（返回首个错误的 JSON Pointer，规则同 `validate_comment_create`） |
| `xuan/community/interaction_service.py` | 新增，§3～§6 |
| `xuan/handlers/community_interactions.py` | 新增，函数 `community_reaction_py`、`community_bookmark_py`、`community_share_py`、`community_report_py`（§7） |
| `main.py` | 追加一行 `from xuan.handlers.community_interactions import (community_reaction_py, community_bookmark_py, community_share_py, community_report_py,)  # noqa: F401` |
| `tests/conftest.py` | `clean_collections` 的 `names` 末尾追加 §2.1 五个集合（只追加） |
| `tests/community_helpers.py` | 只追加 `seed_share_link(...)`（§8.1） |
| `tests/test_community_interactions.py` | 新增，§8.2 |
| `tests/test_community_acl_sweep.py` | 只改三处：① `CASES` 中 E4 三项删除 `marks=...` 参数；② 模块文档字符串中 `Implemented entries` 与 `Unimplemented entries` 两行改为 `E1, E2, E4, E5 (12 live assertions)` 与 `E3, E6 (6 strict xfail assertions marked with owner)`；③ E4 分支体替换为 §8.3 写法（含所需 import） |
| RULES `server/functions/test/community_rules.test.ts` | `COMMUNITY_COLLECTIONS` 数组末尾追加五项（16 × 2 × 4 + 1 = 129 断言） |

禁止：修改 `content_service.py`、`command_service.py`、`discussion_service.py`、`access.py`、`errors.py`、`ids.py`、`community_hash.py`、`handlers/community_contents.py`、`handlers/community_commands.py`、`handlers/community_comments.py`、既有 Schema、除上表外的既有测试；新增依赖；`skip`；新增 `xfail`；永真断言；测试内调用被测函数生成期望值（参考值写字面量）。

### 2.2 CLIENT（reading-notes）

| 文件 | 允许的改动 |
|---|---|
| `lib/src/community/models.dart` | ① 删除 `class MentionRef`（社区副本）并在文件头追加 `import '../domain/note_revision.dart' show MentionRef;`，文件内 `MentionRef.fromJson(x)` 改为 `MentionRef.fromMap((x as Map).cast<String, Object?>())`、mention 的 `.toJson()` 改为 `.toMap()`（D-NC012-13）；② 末尾追加 §10.2 的类 |
| `lib/reading_notes.dart` | 第 23 行删除 ` hide MentionRef`；追加导出 `mention_adapter.dart`、`interaction_controller.dart`、`share_links_controller.dart`、`interaction_bar.dart`、`report_sheet.dart`、`reported_fold.dart`、`share_links_page.dart`、`share_link_landing_page.dart` |
| `lib/src/community/community_api.dart` | `CommunityApi` 内追加 §10.3 九个方法 |
| `lib/src/community/command_queue.dart` | 只在 `_executeApiCall` 的 `switch` 中 `default` 之前追加 §10.4 五个 `case` |
| `lib/src/community/pending_queue_page.dart` | 只在 `_extractSummary` 的 `comment.delete` 分支之后追加 §10.5 的分支 |
| `lib/src/community/content_detail_page.dart` | 只追加可选参数 `interactionBuilder`、`snapshotWrapper`（§10.10） |
| `lib/src/community/discussion_panel.dart` | 只追加可选参数 `commentDecorator`（§10.10） |
| `lib/src/community/mention_adapter.dart` | 新增，§10.6 |
| `lib/src/community/interaction_controller.dart` | 新增，§10.7 |
| `lib/src/community/share_links_controller.dart` | 新增，§10.8 |
| `lib/src/community/interaction_bar.dart`、`report_sheet.dart`、`reported_fold.dart`、`share_links_page.dart`、`share_link_landing_page.dart` | 新增，§10.9 |
| `test/community/interactions_test.dart` | 新增，§11 |

禁止：`lib/src/{domain,persistence,editor,history,storage,export}`、`test/{persistence,contracts,editor,history,support,storage,export}`、既有 `test/community/*.dart`、`community_database.dart`（不加表）、`pubspec.yaml`、`pubspec.lock`；新依赖；真实网络（一律 `MockClient`）；`skip`；永真断言；测试内计算 payload_hash 期望值；新增 §10.11 闭集外的文案。

### 2.3 REST（repository-rest-adapter）

`openapi/openapi.yaml`（§12.1）；`test/community_openapi_contract_test.dart`（只在末尾 `group` 内追加 §12.2 四个测试；另按 D-NC012-22 只改两处既有断言：① 测试 `community paths and methods match the catalog` 的 `expectedCatalog` 中 bookmarks 行方法集合由 `{'put'}` 改为 `{'get', 'put'}`，并在 `'/v1/community/me/contents': {'get'},` 之后新增一行 `'/v1/community/me/share-links': {'get'},`；② 测试 `comment examples manifest has thirteen entries and validates` 的 `expect(manifestList.length, equals(13), reason: 'manifest.json 必须恰好包含 13 项');` 改为 `expect(manifestList.length, greaterThanOrEqualTo(13), reason: 'manifest.json 至少包含 NC-011 登记的 13 项');`，其余行不动）；`test/fixtures/openapi/examples/` 新增 §12.3 四个文件并在 `manifest.json` 末尾追加四项。其他文件禁止。

## 3. 集合与文档（SERVER）

时间字段一律 `ctx.now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")`（6 位微秒，同 D-NC011-03）；读端点无 `ctx` 时用 `datetime.now(timezone.utc)` 同格式。`E` 为 `xuan.community_hash.encode`。

### 3.1 Reaction：`community_reactions/{reaction_id}`

- `reaction_id = "rct_" + sha256(E(["reaction", target_type, target_id, actor_id])).hexdigest()[:32]`（D-NC012-02）。
- 字段恰为 NC-002 `community_reaction.schema.json` 的 7 个：`id`、`target_type`、`target_id`、`actor_id`（= `ctx.owner_scope`）、`value`（`"like"`/`"dislike"`/`None`）、`version`、`updated_at`。存储文档必须通过该 Schema（测试以 `Draft202012Validator({"$ref": "community_reaction.schema.json"}, registry=validation._REGISTRY)` 断言）。
- 首次写入 `version=1`；取消保留 `value=None` 的行（DESIGN Reaction 行）。

### 3.2 计数投影：`community_reaction_counts/{target_type}__{target_id}`

字段恰为 `target_type`、`target_id`、`like`（int ≥ 0）、`dislike`（int ≥ 0）、`updated_at`。首次有 reaction 值变化时创建。文档不存在时读取按两计数 0。

### 3.3 Bookmark：`community_bookmarks/{bookmark_id}`

`bookmark_id = "bmk_" + sha256(E(["bookmark", target_type, target_id, actor_id])).hexdigest()[:32]`。字段恰为 `id`、`actor_id`、`target_type`、`target_id`、`active`（bool）、`version`、`updated_at`。

### 3.4 ShareLink：`community_share_links/{share_id}`

`share_id = ctx.new_ids["share_id"]`（handler 以 `extra_new_ids={"share_id": ids.new_id("shr_")}` 传入）。字段恰为 `id`、`target_type`、`target_id`、`created_by`（= owner_scope）、`created_at`、`revoked_at`（新建 `None`）。

### 3.5 Report：`community_reports/{command_id}`

文档键 = `ctx.command_id`（D-NC002-03）。字段恰为 `command_id`、`reporter_id`（= owner_scope）、`target_type`、`target_id`、`reason`、`detail`（缺省 `""`）、`created_at`。

### 3.6 outbox 与行为事件

- outbox（`COLLECTIONS["outbox"]`，写法照抄 `content_service`）：**只在** reaction 新值为 `"like"` 且旧值不是 `"like"` 时追加一条，字段恰为 `id`、`event_type`（`"reaction.liked"`）、`target_type`、`target_id`、`actor_app_user_id`（= owner_scope）、`created_at`。踩、取消、收藏、分享、举报不写 outbox（PRD §5，D-NC012-11）。
- 行为事件由 `run_command` 写。`CommandOutcome.body` 一律不含 `attributes` 键（同 D-NC011-12）。

### 3.7 DTO

- `reaction_state(target_type, target_id, reaction_doc_or_None, counts_doc_or_None)` = `{"target_type", "target_id", "value": doc.value 或 None, "version": doc.version 或 0, "counts": {"like": counts.like 或 0, "dislike": counts.dislike 或 0}}`。
- `bookmark_state(...)` = `{"target_type", "target_id", "active": doc.active 或 False, "version": doc.version 或 0}`。
- `share_link_dto(doc)` = `{"id", "target_type", "target_id", "created_at", "revoked_at"}`（不含 `created_by`）。

## 4. 载荷校验与目标解析

### 4.1 Schema（`validation.py` 追加，Draft 2020-12，复用 `_REGISTRY`）

```python
REACTION_SET_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["value"],
  "properties": {"value": {"enum": ["like", "dislike", None]}}}
BOOKMARK_SET_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["active"],
  "properties": {"active": {"type": "boolean"}}}
SHARE_CREATE_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["target_type", "target_id"],
  "properties": {"target_type": {"enum": ["content", "comment"]},
                 "target_id": {"type": "string", "pattern": "^(note|cmt)_[0-9a-f]{32}$"}}}
REPORT_CREATE_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["target_type", "target_id", "reason"],
  "properties": {"target_type": {"enum": ["content", "comment"]},
                 "target_id": {"type": "string", "pattern": "^(note|cmt)_[0-9a-f]{32}$"},
                 "reason": {"enum": ["spam", "abuse", "copyright", "other"]},
                 "detail": {"type": "string"}}}
```

### 4.2 目标参数校验 `check_target(target_type, target_id, pointer_prefix)`

| # | 条件 | 结果 |
|---|---|---|
| G1 | `target_type not in ("content", "comment")` | 400 `invalid_argument.target_type`，`field = pointer_prefix + "target_type"` |
| G2 | `content` 且 `target_id` 不匹配 `^note_[0-9a-f]{32}$`；或 `comment` 且不匹配 `^cmt_[0-9a-f]{32}$` | 400 `invalid_argument.target_id`，`field = pointer_prefix + "target_id"` |

路径参数（W10、W11、R3、R8）的 `pointer_prefix` 为 `""`；请求体（W12、W14，Schema 通过之后）为 `"/"`。

### 4.3 目标解析 `resolve_target(target_type, target_id, viewer, client, tx=None) -> tuple[str, dict]`

返回 `(kind, info)`，`kind ∈ {"public", "closed", "not_found"}`，`info = {"content_id", "author_id"}`（`author_id` 为**目标**作者：内容作者或评论作者）：

- `content`：`r, acc = access.resolve_access(target_id, viewer, client=client, tx=tx)`。`not_found` → `not_found`；`visible` → `public`；`owner` → 三元组为 `published/active/allowed` 时 `public`，否则 `closed`。`author_id = acc["author_id"]`，`content_id = target_id`。
- `comment`：读评论文档（传 `tx`）不存在 → `not_found`；读 `community_threads/{comment.thread_id}` 不存在 → `not_found`；`r, acc = resolve_access(thread.canonical_subject_key, viewer, ...)` 为 `not_found` → `not_found`；`comment.status != "visible"` → `not_found`；`r == "visible"` → `public`；`r == "owner"` → 三元组公开时 `public` 否则 `closed`。`author_id = comment.author_id`，`content_id = thread.canonical_subject_key`。

`not_found` 的响应（W10、W11、W12、W14、R3、R8）：`content` → `errors.problem("not_found.content", 404)`（共用体）；`comment` → `errors.problem("not_found.comment", 404)`。

## 5. 写命令判定顺序（`interaction_service.py`，每个函数都是 `run_command` 的 `fn(tx, ctx)`；全部读在写之前）

### 5.1 `reaction_set`（W10，200）

| # | 判定 | 结果 |
|---|---|---|
| 0 | `check_target(path.target_type, path.target_id, "")` | 见 §4.2 |
| 1 | `validate_reaction_set(body)` 非 None | 400 `invalid_argument.reaction`，`field` = JSON Pointer |
| 2 | `resolve_target(..., tx=tx)` 为 `not_found` | 404（§4.3） |
| 3 | `closed` | 403 `forbidden.thread_closed` |
| 4 | `ctx.if_match is None` | 400 `invalid_argument.if_match`，`field="if_match"` |
| 5 | 读 reaction 文档与计数文档；`cur = doc.version 或 0`；`ctx.if_match != cur` | 412 `conflict.version`，`current_version=cur` |
| 6 | `old = doc.value 或 None`；`new = body["value"]`；`old == new` | 不写任何文档；`CommandOutcome(200, None, ids, cur, {"reaction": reaction_state(当前)})`（D-NC012-03） |
| 7 | 写 reaction（7 字段，`version=cur+1`）；计数：`old` 非 None 则该键 −1，`new` 非 None 则该键 +1，写计数文档 5 字段；§3.6 条件成立时写 outbox | `CommandOutcome(200, None, ids, cur+1, {"reaction": reaction_state(新)})` |

`ids = {"target_type": target_type, "target_id": target_id, "reaction_id": reaction_id}`（Python dict，值为字符串；`run_command` 以 `.items()` 读取）。

### 5.2 `bookmark_set`（W11，200）

| # | 判定 | 结果 |
|---|---|---|
| 0 | `check_target(..., "")` | §4.2 |
| 1 | `validate_bookmark_set(body)` 非 None | 400 `invalid_argument.bookmark`，`field` |
| 2 | `resolve_target` 为 `not_found` | 404（`closed` 允许收藏） |
| 3 | 读收藏文档；`cur = doc.version 或 0`；`ctx.if_match is not None and ctx.if_match != cur` | 412 `conflict.version`，`current_version=cur`（If-Match 可选，D-NC012-04） |
| 4 | `(doc.active 或 False) == body["active"]` | 不写；200，`applied_version=cur`，`{"bookmark": bookmark_state(当前)}` |
| 5 | 写收藏文档（7 字段，`version=cur+1`） | 200，`applied_version=cur+1`，`{"bookmark": bookmark_state(新)}`；`ids = {"target_type": target_type, "target_id": target_id, "bookmark_id": bookmark_id}`（dict） |

### 5.3 `share_create`（W12，201）

| # | 判定 | 结果 |
|---|---|---|
| 1 | `validate_share_create(body)` 非 None | 400 `invalid_argument.share_link`，`field` |
| 2 | `check_target(body.target_type, body.target_id, "/")` | §4.2 |
| 3 | `resolve_target` 为 `not_found` | 404 |
| 4 | `info.author_id != ctx.owner_scope` | 403 `forbidden.not_owner` |
| 5 | `closed` | 403 `forbidden.thread_closed` |
| 6 | 写分享文档（§3.4） | `CommandOutcome(201, None, {"share_id": id}, 0, {"share_link": share_link_dto})` |

同一目标可多次创建，各得新链接（D-NC012-08）。

### 5.4 `share_revoke`（W13，200）

| # | 判定 | 结果 |
|---|---|---|
| 0 | `share_id` 不匹配 `^shr_[0-9a-f]{32}$` | 400 `invalid_argument.share_id`，`field="share_id"` |
| 1 | 文档不存在 | 404 `not_found.share_link` |
| 2 | `created_by != ctx.owner_scope` | 403 `forbidden.not_owner` |
| 3 | `revoked_at` 非 None | 不写；200，`{"share_link": dto}`（D-NC012-09） |
| 4 | 写 `revoked_at = now` | 200，`{"share_link": dto}`；`ids = {"share_id": share_id}`（dict），`applied_version=0` |

目标当前是否可读不影响撤销。

### 5.5 `report_create`（W14，201）

| # | 判定 | 结果 |
|---|---|---|
| P1 | 请求体是对象、`detail` 是字符串且 `len(detail) > 500`（code point） | 413 `too_large.detail`，`limit=500` |
| 1 | `validate_report_create(body)` 非 None | 400 `invalid_argument.report`，`field` |
| 2 | `check_target(body.target_type, body.target_id, "/")` | §4.2 |
| 3 | `resolve_target` 为 `not_found` | 404（`closed` 允许举报） |
| 4 | 写举报文档（§3.5，`detail = body.get("detail", "")`） | `CommandOutcome(201, None, {"report_ref": ctx.command_id}, 0, {"report_ref": ctx.command_id})` |

服务端不对同一举报人同一目标去重（D-NC012-10）。

## 6. 读端点

### 6.1 R3 `get_reaction(target_type, target_id, viewer, if_none_match, client=None) -> (status, body, headers)`

1. `check_target(..., "")` → 400；2. `resolve_target`（无 tx）为 `not_found` → 404（`closed` 允许读）；3. 读 viewer 的 reaction 文档与计数文档，`state = reaction_state(...)`；4. `etag = f'"{state.version}:{state.counts.like}:{state.counts.dislike}"'`（D-NC012-12）；5. `if_none_match == etag` → `(304, {}, {"ETag": etag})`；6. `(200, state, {"ETag": etag})`。ACL 先于 304。

### 6.2 R8 `get_bookmark(target_type, target_id, viewer, client=None)`

`check_target` → 400；`resolve_target` 为 `not_found` → 404；返回 `(200, bookmark_state(viewer 的文档), {})`。只读 viewer 本人的文档（收藏私有）。无 ETag。

### 6.3 R4 `resolve_share(share_id, viewer, client=None)`

以下任一成立 → `(404, errors.problem("not_found.content", 404), {})`（共用体，逐字节相同，D-NC012-07）：`share_id` 格式不符；文档不存在；`revoked_at` 非 None；`resolve_target(doc.target_type, doc.target_id, viewer)` 为 `not_found`（评论目标不可见也用此共用体）。否则（`public` 或 `closed`，后者即作者本人）→ `(200, {"target_type", "target_id", "share_link": share_link_dto}, {})`。

### 6.4 R7 `list_my_share_links(owner_scope, query_args, client=None)`

- `limit`：缺省 20；非整数字符串、< 1 或 > 100 → 400 `invalid_argument.limit`，`field="limit"`。
- `cursor`：缺省无；否则 base64url 去 padding 解码为 UTF-8 `"<created_at>|<share_id>"`，须恰两段、`created_at` 匹配 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$`、`share_id` 匹配 `^shr_[0-9a-f]{32}$`，任一不符（含解码失败）→ 400 `invalid_argument.cursor`，`field="cursor"`。
- 查询：`where("created_by", "==", owner_scope).order_by("created_at", DESCENDING).order_by("id", DESCENDING)`，有游标时 `.start_after([created_at, share_id])`，`.limit(limit + 1)`。
- 返回 `{"items": 前 limit 个 dto, "next_cursor": 多于 limit 时对第 limit 个编码，否则 None}`；包含已撤销链接。

## 7. Handler（`handlers/community_interactions.py`）

- 四个函数的鉴权、owner_scope 解析、前缀剥离、query 合并照抄 `community_comments.py` 第 26～75 行写法；`_extract_auth_uid` 从 `xuan.handlers.playground_rest` 导入；`_parse_if_match` 与 `_make_response` 从 `xuan.handlers.community_contents` 导入（不复制、不修改）。`body = req.get_json(silent=True)`，为 None 时用 `{}`。
- 路由（`path` 为剥离 `/v1/community` 前缀后的路径）：

| 函数 | 方法与路径 | 处理 |
|---|---|---|
| `community_reaction_py` | `GET /reactions/{target_type}/{target_id}` | `get_reaction(..., If-None-Match 头)`；304 用 `https_fn.Response(response="", status=304, headers={"ETag": etag})` |
| 同上 | `PUT /reactions/{target_type}/{target_id}` | 畸形 If-Match → 调 `run_command` 之前 400 `invalid_argument.if_match`（无账本）；`payload={"path": {"target_type", "target_id"}, "body": body, "if_match": if_match}`，operation `reaction.set` |
| `community_bookmark_py` | `GET /bookmarks/{target_type}/{target_id}` | `get_bookmark` |
| 同上 | `PUT /bookmarks/{target_type}/{target_id}` | 畸形 If-Match 同上；payload 同 reaction，operation `bookmark.set` |
| `community_share_py` | `POST /share-links` | `payload={"path": {}, "body": body, "if_match": None}`，operation `share.create`，`extra_new_ids={"share_id": ids.new_id("shr_")}` |
| 同上 | `GET /share-links/{share_id}` | `resolve_share` |
| 同上 | `DELETE /share-links/{share_id}` | `payload={"path": {"share_id": share_id}, "body": {}, "if_match": None}`，operation `share.revoke`；忽略请求体 |
| 同上 | `GET /me/share-links` | `list_my_share_links` |
| `community_report_py` | `POST /reports` | `payload={"path": {}, "body": body, "if_match": None}`，operation `report.create` |
| 任一函数 | 其他 | 404 `not_found.target` |

- 日志只记 `type(exc).__name__`、command_id 与 ID 类字段；不得出现举报 `detail`、请求体或异常文本。

## 8. SERVER 测试判据（`tests/test_community_interactions.py`，Emulator）

### 8.1 辅助（`community_helpers.py` 追加）

`seed_share_link(client, share_id, target_type, target_id, created_by, created_at="2026-09-11T08:00:00.000001Z", revoked_at=None) -> dict`：按 §3.4 写文档；`created_by` 不以 `app-` 开头时经 `app_user_id_for` 转换（同 `seed_access`）。

### 8.2 测试表（名称逐字，函数名加 `test_` 前缀；HTTP 测试经 `call(<handler>, ...)`）

| ACT | ID | 测试 | 关键断言 |
|---|---|---|---|
| 02 | I01 | `reaction_like_writes_reaction_counts_outbox_event_atomically` | 200；响应键恰 `{reaction, command}`；`command.resource_ids` 恰三键且 `reaction_id` 等于按 §3.1 派生；reaction 文档通过 NC-002 Schema；计数文档字段恰 5 键 `like=1`；outbox `reaction.liked` 一条且字段恰 §3.6；行为事件一条 `attributes == {}` |
| 02 | I02 | `interaction_payload_hashes_and_ids_match_reference` | `compute_payload_hash` 对 §9 R1、R2、B1、S1、S2、P1 六组输入等于字面量；RID、BID 派生等于字面量 |
| 02 | I03 | `reaction_cancel_keeps_null_row_and_decrements_count` | like v1 → `value=null`（If-Match 1）→ 200 v2；文档仍在且 `value is None`；`like=0`；outbox `reaction.liked` 仍恰 1 条 |
| 02 | I04 | `reaction_switch_like_to_dislike_moves_count` | like v1 → dislike（If-Match 1）→ `like=0, dislike=1`，v2；outbox 不新增 |
| 02 | I05 | `reaction_same_value_is_noop_without_version_bump` | like v1 后同键外新命令 like（If-Match 1）→ 200、`version=1`、`applied_version=1`；文档 `updated_at` 不变；`like=1`；outbox 1 条 |
| 02 | I06 | `reaction_if_match_missing_400_stale_412_malformed_400_without_ledger` | 缺 → 400 `invalid_argument.if_match`；`"0"` 对 v1 → 412 `current_version=1`；`If-Match: abc` → 400 且无账本文档 |
| 02 | I07 | `reaction_old_like_replay_after_cancel_returns_original_and_state_stays_null` | 命令 A like(If-Match 0) → v1；命令 B null(If-Match 1) → v2；以 A 的键与原载荷重放 → 200 且响应体与 A 首响应相等（`version=1`、`applied_version=1`）；文档 `value=None, version=2`；R3 `version=2`、`value=null` |
| 02 | I08 | `reaction_two_devices_same_baseline_one_commits_one_412` | 同账号两命令均 If-Match 0：like → 200 v1；dislike → 412 `current_version=1`；文档 like v1；`dislike=0` |
| 02 | I09 | `reaction_two_accounts_have_independent_values_and_shared_counts` | 甲 like、乙 dislike → 计数 1/1；甲 R3 `value=like`、乙 R3 `value=dislike`，两者 `counts` 相同 |
| 02 | I10 | `reaction_ten_concurrent_accounts_count_exactly_ten` | 10 个账号经 `threading.Barrier(10)` 同时 `run_command(ctx_i, interaction_service.reaction_set)`（If-Match 0，like）；返回 503 时同一 ctx 重试，最多 5 次，第 k 次（k=1..5）重试前 `time.sleep(0.05 * k + random.Random(线程序号 * 10 + k).uniform(0, 0.05))`；最终全部 200；`like=10`；reaction 文档 10 份；outbox `reaction.liked` 10 条；行为事件 `reaction.set` 10 条 |
| 02 | I11 | `reaction_on_non_public_content_is_404_for_others` | 参数化 withdrawn / trashed / hidden：非作者 W10 → 404、响应体等于 `SHARED_NOT_FOUND_CONTENT_BODY`；无 reaction 文档、无计数文档 |
| 02 | I12 | `reaction_author_closed_403_and_comment_target_rules` | 作者对自己 withdrawn 内容 W10 → 403 `forbidden.thread_closed`；公开内容下 visible 评论 → 200；deleted 评论 → 404 `not_found.comment` |
| 02 | I13 | `reaction_after_target_purge_replay_does_not_revive` | like v1 后测试直接：access 改 `visibility=withdrawn, lifecycle=purge_pending`，删除 reaction 与计数文档；A 键重放 → 200 且体同首响应，reaction 文档仍不存在；新命令 like(If-Match 0) → 404 `not_found.content`，仍不存在 |
| 02 | I14 | `reaction_get_etag_literal_and_304_only_after_acl` | 甲 like 后：甲 R3 ETag `"1:1:0"`、乙 R3 ETag `"0:1:0"`；乙带 `"0:1:0"` → 304；内容 withdrawn 后乙带同值 → 404 共用体 |
| 02 | I15 | `reaction_invalid_target_and_body_are_400` | `target_type=post` → 400 `invalid_argument.target_type`；`content` + `cmt_…` → 400 `invalid_argument.target_id`；`{"value": "love"}` → 400 `invalid_argument.reaction` 且 `field="/value"`；`{}` → `field="/"` |
| 02 | I16 | `bookmark_set_private_noop_optional_if_match_and_get` | 无 If-Match active true → 200 v1；同值 → v1 不变；If-Match `"0"` → 412；甲 R8 `active=true, version=1`；乙 R8 `active=false, version=0`；存储文档字段恰 §3.3 七键 |
| 02 | I17 | `bookmark_on_unreadable_target_is_404` | 非作者对 hidden 内容 W11 → 404 共用体；不存在的评论 → 404 `not_found.comment` |
| 03 | I18 | `share_create_by_author_201_others_403_closed_403` | 作者 → 201、响应键恰 `{share_link, command}`、`share_link` 恰五键、`revoked_at` null；非作者 → 403 `forbidden.not_owner`；作者对自己 withdrawn 内容 → 403 `forbidden.thread_closed`；评论作者分享自己的 visible 评论 → 201 |
| 03 | I19 | `share_resolve_returns_target_and_all_failures_share_one_404` | 参数化 8 例：`public`（公开内容）→ 200 `{target_type, target_id, share_link}`；`missing`（未种）、`bad_format`（`shr_xyz`）、`revoked`、`withdrawn`、`trashed`、`hidden`、`comment_deleted` 七例 → 404 且 `json.dumps(body, sort_keys=True)` 等于共用体 |
| 03 | I20 | `share_revoke_owner_200_idempotent_non_owner_403_missing_404` | 创建者 → 200 `revoked_at` 非 null；再撤销（新命令）→ 200 且 `revoked_at` 不变；非创建者 → 403 `forbidden.not_owner`；未种 ID → 404 `not_found.share_link`；`share_id=abc` → 400 `invalid_argument.share_id` |
| 03 | I21 | `my_share_links_desc_paging_cursor_literal_and_owner_only` | 种甲的 `shr_…0001/0002/0003`（created_at `…000001Z/000002Z/000003Z`，0001 已撤销）与乙的一条；`limit=2` → `[0003, 0002]`、`next_cursor` 等于 §9 SCUR；带 SCUR → `[0001]`（含 `revoked_at`）、`next_cursor` null；乙的链接从不出现 |
| 03 | I22 | `my_share_links_rejects_invalid_limit_and_cursor` | `limit=101`、`limit=0`、`limit=abc` → 400 `invalid_argument.limit`；`cursor=!!`、`cursor` 为 base64url(`"x|y"`) → 400 `invalid_argument.cursor` |
| 03 | I23 | `report_create_201_keyed_by_command_id_with_exact_fields` | 201、响应键恰 `{report_ref, command}`、`report_ref == command_id`；文档键为 command_id、字段恰 §3.5 七键；缺 `detail` → 存 `""`；不写 outbox |
| 03 | I24 | `report_detail_500_code_points_passes_501_is_413_and_bad_reason_400` | `"\U0001F600" * 500` → 201；`* 501` → 413 `too_large.detail`、`limit=500`；`reason="rude"` → 400 `invalid_argument.report`、`field="/reason"` |
| 03 | I25 | `report_on_unreadable_target_is_404` | 非作者对 trashed 内容 → 404 共用体；作者对自己 withdrawn 内容 → 201 |
| 03 | I26 | `interaction_commands_replay_same_key_and_conflict_on_different_payload` | share.create 同键同载荷 → 同 201 体、分享文档仍 1 份；report.create 同键重放 → 举报文档 1 份；bookmark.set 同键异载荷 → 409 `conflict.idempotency` |
| 03 | I27 | `logs_never_contain_report_detail` | `caplog.at_level("DEBUG")` 覆盖 W14 201、W14 413、W10 412、R4 404；`detail` 文本 `这是一段不应出现在日志里的举报说明XYZ` 不在 `caplog.text` |

计数：I11 参数化 3 例；I19 参数化 8 例（`public` 1 例断言 200，其余 7 例断言共用 404）。27 个测试名共 36 例：本文件 act/02 后 `19 passed`；act/03 后 `36 passed`。全量 `pytest tests -q -rf`：act/02 后 `5 failed, 515 passed, 9 xfailed`；act/03 后 `5 failed, 535 passed, 6 xfailed`（本文件 +17，ACL 扫描 E4 三例由 xfail 转为通过 +3）；FAILED 恰为 §1 五个 ID。RULES act/02 后 `Tests: 129 passed`。

### 8.3 ACL 扫描 E4 分支（`test_community_acl_sweep.py`）

```python
    elif entry == "E4":
        # 分享链接解析（NC-012a）：作者建链后内容进入 reason 态，他人解析得共用 404
        share_id = "shr_" + note_id[5:]
        seed_share_link(client, share_id, "content", note_id, author_id)
        status, body, _ = call(
            community_share_py,
            method="GET",
            path=f"/v1/community/share-links/{share_id}",
            headers=headers,
        )
```

import 追加：`from xuan.handlers.community_interactions import community_share_py`；`tests.community_helpers` 的 import 行追加 `seed_share_link`。

## 9. 参考值（主 Agent 2026-09-12 以 functions-py `.venv` 计算；载荷结构 `{"path", "body", "if_match"}` 已用 NC-011 H1 复核一致）

| 名称 | 输入 | 值 |
|---|---|---|
| R1 like | operation `reaction.set`；path `{"target_type": "content", "target_id": "note_00000000000000000000000000000001"}`；body `{"value": "like"}`；if_match 0 | `09cbea8cdeff9a18a58a8eafd4227d436e3e3571120b5b35fb8e0607415181f9` |
| R2 cancel | 同上 path；body `{"value": null}`；if_match 1 | `26c51836823dc9f972ade10c886b40212a0021651a8a343f237f3a6f69956b90` |
| B1 bookmark | `bookmark.set`；path `{"target_type": "comment", "target_id": "cmt_00000000000000000000000000000001"}`；body `{"active": true}`；if_match null | `1a8f01148eaeb612891d175ac6b14a9fca9ca89995a5582ac7b12ed9aedd6620` |
| S1 share.create | `share.create`；path `{}`；body `{"target_type": "content", "target_id": "note_00000000000000000000000000000001"}`；if_match null | `481e858b66f0a48c074ef3d5e4b2dc1ea3a899a9179f6c5cac3af4aa60b970a2` |
| S2 share.revoke | `share.revoke`；path `{"share_id": "shr_00000000000000000000000000000001"}`；body `{}`；if_match null | `608dfd80e74d5f37a190ee29346c857ab7da5c707aafef094fc25018edf058af` |
| P1 report | `report.create`；path `{}`；body `{"target_type": "comment", "target_id": "cmt_00000000000000000000000000000001", "reason": "spam", "detail": "广告😀"}`；if_match null | `b6f3caec02355f0365e49b5b028368911a09fd7651206b8ab5d4b5484e4bb07a` |
| RID | `["reaction", "content", "note_…0001", "app-00000000000000000000000000000001"]` | `rct_ede12cd76c76e944120f75d6ccf424ad` |
| BID | `["bookmark", "comment", "cmt_…0001", "app-00000000000000000000000000000001"]` | `bmk_58da728e583165f3f33e853295ecf8de` |
| SCUR | `"2026-09-11T08:00:00.000002Z|shr_00000000000000000000000000000002"` | `MjAyNi0wOS0xMVQwODowMDowMC4wMDAwMDJafHNocl8wMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMg` |

mention 文本校验向量（`discussion_service.filter_mentions` 实测保留下标；Dart `reconcileMentions` 必须逐条相同，D-NC012-14）：

| 名称 | 文本 | mentions（user_id, display_name, start_offset, length） | 保留下标 |
|---|---|---|---|
| M1 | `😀@甲 hi` | (u_1, 甲, 1, 2) | [0] |
| M2 | `@甲 和 @甲` | (u_1, 甲, 0, 2)、(u_1, 甲, 5, 2) | [0, 1] |
| M3 | `@甲 和 @甲` | (u_1, 甲, 0, 2)、(u_2, 乙, 5, 2) | [0] |
| M4 | `@ 和` | (u_1, 甲, 0, 2) | [] |
| M5 | `@甲` | (u_1, 甲, 10, 2) | [] |
| M6 | `@甲` | (u_1, 甲, -1, 2) | [] |
| M7 | `@小明😀 你好` | (u_ming, 小明😀, 0, 4) | [0] |
| M8 | `你好@乙😀@甲` | (u_1, 甲, 5, 2)、(u_2, 乙, 2, 2) | [0, 1] |

`…` 表示补零到 32 位 hex。

## 10. CLIENT 实现

### 10.1 `MentionRef` 单一化（D-NC012-13）

按 §2.2 `models.dart` ①、`reading_notes.dart` 改动后，`package:reading_notes/reading_notes.dart` 只暴露 domain 的 `MentionRef`，`CreateCommentRequest(mentions: [MentionRef(...)])` 可直接编译；社区模型 JSON 形状不变（`toMap` 与原 `toJson` 键值相同）。

### 10.2 模型（`models.dart` 末尾追加；手写 `fromJson`/`toJson`，snake_case ↔ lowerCamel；`toJson` 恒输出全部键，null 不省略）

`ReactionState{targetType, targetId, String? value, int version, int likeCount, int dislikeCount}`（JSON `counts: {like, dislike}`）；`ReactionResponse{ReactionState reaction, CommandResult command}`；`BookmarkState{targetType, targetId, bool active, int version}`；`BookmarkResponse{BookmarkState bookmark, CommandResult command}`；`ShareLink{id, targetType, targetId, createdAt, String? revokedAt}`；`ShareLinkResponse{ShareLink shareLink, CommandResult command}`；`ShareLinkResolution{targetType, targetId, ShareLink shareLink}`；`ShareLinkPage{List<ShareLink> items, String? nextCursor}`；`ReportResponse{String reportRef, CommandResult command}`；`CreateReportRequest{targetType, targetId, reason, String detail = ''}`（`toJson` 恒四键）。

### 10.3 API（`CommunityApi` 追加，写法照抄 `createComment`/`editComment`：超时 15 秒，异常 → `ApiResult.transport`）

| 方法 | 请求 |
|---|---|
| `Future<ApiResult<ReactionState>> getReaction(String targetType, String targetId)` | `GET /reactions/$targetType/$targetId`；只发 `Authorization`，不发 `If-None-Match` |
| `Future<ApiResult<ReactionResponse>> setReaction(String commandId, String targetType, String targetId, String? value, {required int ifMatch})` | `PUT` 同路径；头 `idempotency-key`、`content-type`、`if-match: "<v>"`；体 `{"value": value}`（null 键保留） |
| `Future<ApiResult<BookmarkState>> getBookmark(String targetType, String targetId)` | `GET /bookmarks/$targetType/$targetId` |
| `Future<ApiResult<BookmarkResponse>> setBookmark(String commandId, String targetType, String targetId, bool active, {int? ifMatch})` | `PUT` 同路径；`ifMatch` 非 null 时才发 `if-match`；体 `{"active": active}` |
| `Future<ApiResult<ShareLinkResponse>> createShareLink(String commandId, String targetType, String targetId)` | `POST /share-links`；体 `{"target_type", "target_id"}` |
| `Future<ApiResult<ShareLinkResponse>> revokeShareLink(String commandId, String shareId)` | `DELETE /share-links/$shareId`；无体 |
| `Future<ApiResult<ShareLinkResolution>> resolveShareLink(String shareId)` | `GET /share-links/$shareId` |
| `Future<ApiResult<ShareLinkPage>> listMyShareLinks({String? cursor, int limit = 20})` | `GET /me/share-links`；query 恒含 `limit`，`cursor` 非 null 才加 |
| `Future<ApiResult<ReportResponse>> createReport(String commandId, CreateReportRequest body)` | `POST /reports`；体 `body.toJson()` |

### 10.4 命令队列（`_executeApiCall` 追加五个 case）与入队约定

```dart
case 'reaction.set':
  return await api.setReaction(commandId, path['target_type'] as String, path['target_id'] as String, body['value'] as String?, ifMatch: ifMatch ?? 0);
case 'bookmark.set':
  return await api.setBookmark(commandId, path['target_type'] as String, path['target_id'] as String, body['active'] as bool, ifMatch: ifMatch);
case 'share.create':
  return await api.createShareLink(commandId, body['target_type'] as String, body['target_id'] as String);
case 'share.revoke':
  return await api.revokeShareLink(commandId, path['share_id'] as String);
case 'report.create':
  return await api.createReport(commandId, CreateReportRequest.fromJson(body));
```

入队约定：`targetKey = '$targetType:$targetId'`。`reaction.set`：`path={'target_type','target_id'}`、`targetId=targetKey`、`body={'value': v}`、`ifMatch` = 已确认版本；`bookmark.set`：同 path 与 targetId、`body={'active': a}`、`ifMatch=null`；`share.create`：`path={}`、`targetId=targetKey`、`body={'target_type','target_id'}`；`share.revoke`：`path={'share_id': id}`、`targetId=id`、`body={}`；`report.create`：`path={}`、`targetId=targetKey`、`body=CreateReportRequest(...).toJson()`。同 target 非终态冲突规则不变（不豁免）。

### 10.5 待处理页摘要（`_extractSummary` 追加分支）

`reaction.set`：`body['value']` 为 `'like'` → `'赞'`，`'dislike'` → `'踩'`，null → `'取消赞踩'`；`bookmark.set`：`body['active'] == true` → `'收藏'`，否则 `'取消收藏'`；`share.create` → `'创建分享链接'`；`share.revoke` → `'撤销分享链接'`；`report.create` → `'举报'`。

### 10.6 `mention_adapter.dart`

```dart
List<MentionRef> reconcileMentions(String text, List<MentionRef> mentions);
```

`final cps = text.runes.toList();` 逐条保留同时满足 `m.startOffset >= 0`、`m.length >= 0`、`m.startOffset + m.length <= cps.length`、`String.fromCharCodes(cps.sublist(m.startOffset, m.startOffset + m.length)) == '@${m.displayName}'` 的项，保持输入顺序，返回新列表（元素为原对象）。禁止 `String.substring` 与 `text.length`。本期不接入编辑器与讨论区输入（D-NC012-14）。

### 10.7 `InteractionController extends ChangeNotifier`

构造：`InteractionController({required CommunityApi api, required CommandQueue queue, required CommunityDatabase db, required String targetType, required String targetId})`。`targetKey = '$targetType:$targetId'`；本 owner 取 `queue.ownerScope`。

公开状态：`InteractionViewState viewState`（枚举恰 `loading, ready, notVisible, error, offline`）；`ReactionState? reaction`（已确认）；`String? displayReaction`；`BookmarkState? bookmark`（已确认）；`bool displayBookmarked`；`bool reported`；`bool revealed`（初值 false）；`String? notice`；派生 `int get displayLikeCount` = `reaction.likeCount - (reaction.value == 'like' ? 1 : 0) + (displayReaction == 'like' ? 1 : 0)`，`displayDislikeCount` 同理（`reaction` 为 null 时为 0）。私有：`final Set<String> _tracked = {}`；`bool _hasPendingReaction = false; String? _pendingReaction`；`bool _hasPendingBookmark = false; bool _pendingBookmark = false`。

**采纳规则（D-NC012-16）**：`applyReaction(ReactionState s)`：`reaction == null || s.version >= reaction!.version` 时 `reaction = s`，否则忽略；`applyBookmark` 同理。

| 方法 | 行为 |
|---|---|
| `load()` | `viewState = loading`；并发请求 `getReaction` 与 `getBookmark`。二者都 ok → `applyReaction`/`applyBookmark`，`displayReaction = reaction.value`、`displayBookmarked = bookmark.active`，`viewState = ready`；任一为 problem 且 `status == 404` → `notVisible`；任一 transport → `offline`；其他 → `error`。读 `community_meta` 中键 `reported:<targetKey>` 是否存在 → `reported`。随后 `refreshPending()` |
| `toggleReaction(String v)` | `v` 只接受 `like`/`dislike`，且 `viewState == ready`；`desired = displayReaction == v ? null : v`；`displayReaction = desired`；`notifyListeners()`；库中存在本 owner、`targetId == targetKey`、`operation == 'reaction.set'` 的非终态行 → `_hasPendingReaction = true; _pendingReaction = desired`，返回；否则 `_sendReaction(desired)` |
| `_sendReaction(String? d)` | `enqueue('reaction.set', ..., ifMatch: reaction!.version)`，加入 `_tracked`；`await queue.drain()`；`await refreshPending()` |
| `toggleBookmark()` | 同上结构：`desired = !displayBookmarked`；有非终态 `bookmark.set` 行则记入 `_pendingBookmark`；否则入队（`ifMatch: null`）、drain、`refreshPending()` |
| `report(String reason, String detail)` | `reported` 为 true 直接返回；`detail.runes.length > 500` → `notice = '补充说明不能超过 500 字'` 返回；入队 `report.create` 得 `commandId`；写 `community_meta`（`key = 'reported:<targetKey>'`、`value = commandId`、`updated_at = clock 现时 ISO`）；`reported = true`；`notice = '举报已提交，待发送'`；`notifyListeners()`；drain；`refreshPending()` |
| `unfold()` | `revealed = true`；`notifyListeners()` |
| `refreshPending()` | 读本 owner、`targetId == targetKey`、`operation ∈ {reaction.set, bookmark.set, report.create}` 的行：非终态 → 加入 `_tracked`；`reaction.set` 非终态 → `displayReaction` = 该行请求体 `value`（重启恢复）；`bookmark.set` 非终态 → `displayBookmarked` = 请求体 `active`。**仅对 `_tracked` 中的行**判定终态并移出：`reaction.set` committed → `applyReaction(ReactionResponse.fromJson(resultJson).reaction)`，然后先取 `final had = _hasPendingReaction; final next = _pendingReaction;` 并立即清空两个标志（`_hasPendingReaction = false; _pendingReaction = null;`），再判断：`had && next != reaction.value` → `await _sendReaction(next)`；否则 `displayReaction = reaction.value`（防止 `_sendReaction` 末尾的 `refreshPending()` 重入时再次读到旧标志）；`reaction.set` rejected 且 `lastProblemCode == 'conflict.version'` → 清标志，`notice = '赞踩状态已在其他设备更新'`，`getReaction` ok 时**直接赋值** `reaction = 新状态`（不经采纳规则）、`displayReaction = reaction.value`，不自动重发（D-NC012-15）；`lastProblemCode` 以 `not_found.` 开头 → `viewState = notVisible`；其他 rejected → `displayReaction = reaction?.value`、`notice = '操作未能完成'`。`bookmark.set` 同构（412 文案同为「操作未能完成」并以 `getBookmark` 直接赋值）。`report.create` committed → `notice = '举报已受理'`；rejected → 删除该 meta 行、`reported = false`、`notice = '举报未能提交，请重试'`。最后 `notifyListeners()` |

### 10.8 `share_links_controller.dart`

`ShareLinksController extends ChangeNotifier`，构造 `({required CommunityApi api, required CommandQueue queue, required CommunityDatabase db})`。状态：`ShareLinksViewState viewState`（恰 `loading, empty, error, offline, partial, success`）；`List<ShareLink> items`；`String? nextCursor`；`ShareLink? lastCreated`；`String? notice`。

| 方法 | 行为 |
|---|---|
| `load()` | `listMyShareLinks()`：ok → 替换 `items`/`nextCursor`，`empty` 或 `success`；transport → `offline`；problem → `error` |
| `loadMore()` | `nextCursor` 为 null 返回；ok → 追加；失败 → `partial`（保留列表） |
| `create(String targetType, String targetId)` | 入队 `share.create`、drain；读该行：committed → `lastCreated = ShareLinkResponse.fromJson(resultJson).shareLink`，随后 `load()`；rejected：`forbidden.not_owner` → `'只能分享自己的内容'`，`forbidden.thread_closed` → `'内容未公开，无法分享'`，`not_found.` 开头 → `'该内容已不可访问'`；仍非终态 → `'网络恢复后将创建分享链接'` |
| `revoke(ShareLink link)` | 入队 `share.revoke`、drain；committed → 以响应中的 `shareLink` 替换 `items` 中同 id 项；rejected → `'撤销未能完成'`；仍非终态 → `'网络恢复后将撤销'` |

顶层函数 `Future<ShareResolutionResult> resolveShare(CommunityApi api, String shareId)`；`sealed class ShareResolutionResult`，子类恰 `ShareOpened{targetType, targetId}`、`ShareUnavailable`、`ShareOffline`、`ShareError`：ok → `ShareOpened`；problem 404 → `ShareUnavailable`；transport → `ShareOffline`；其他 → `ShareError`。

### 10.9 界面

- `InteractionBar({Key? key, required InteractionController controller, bool compact = false, bool isOwner = false, VoidCallback? onShare, VoidCallback? onReport})`：`ListenableBuilder`。`viewState != ready` 时渲染 `SizedBox.shrink()`。按钮均为 `IconButton`，`constraints: const BoxConstraints(minWidth: 48, minHeight: 48)`，`tooltip` 与键：「赞」`ValueKey('reaction-like')`、「踩」`ValueKey('reaction-dislike')`（各自后跟计数 `Text('${displayLikeCount}')`/`Text('${displayDislikeCount}')`）；非 `compact` 时「收藏」/「已收藏」`ValueKey('bookmark-toggle')`；`isOwner && !compact` 时「分享」`ValueKey('share-button')`（调用 `onShare`）；`!isOwner` 时「举报」`ValueKey('report-button')`（调用 `onReport`）。`notice` 非 null 时下方 `Text(notice)`。
- `ReportSheet({Key? key, required InteractionController controller})`：四个 `RadioListTile<String>`：「垃圾广告」spam、「辱骂攻击」abuse、「侵犯版权」copyright、「其他」other；`TextField`（`hintText: '补充说明（可选）'`）下方计数 `Text('${detail.runes.length}/500')`；「提交举报」按钮未选原因时禁用，点击调用 `controller.report(reason, detail)` 后 `Navigator.of(context).maybePop()`。
- `ReportedFold({Key? key, required InteractionController controller, required Widget child, required String foldedText})`：`controller.reported && !controller.revealed` 时渲染 `Column[Text(foldedText), TextButton(「仍要查看」→ controller.unfold())]`，否则 `child`。内容用 `'你已举报该内容'`，评论用 `'你已举报该评论'`。
- `ShareLinksPage({Key? key, required ShareLinksController controller, required Future<String?> Function(String targetType, String targetId) titleLookup, required String Function(String shareId) shareUrlBuilder})`：`initState` 调 `load()`。状态：loading `CircularProgressIndicator` +「分享链接加载中」；empty「还没有分享链接」；error「分享链接读取失败」+「重试」；offline「离线，无法加载分享链接」+「重试」；partial 列表 +「更多分享链接加载失败」+「重试」（调 `loadMore`）；success 列表。列表项 `key: ValueKey('share-<id>')`：标题为 `titleLookup` 结果，null 时 `targetType == 'comment' ? '评论' : '内容'`；副标题 `shareUrlBuilder(id)`；`revokedAt != null` 显示「已撤销」，否则「撤销」按钮 → `AlertDialog`（标题「撤销分享链接」、正文「撤销后，已发出的链接将无法打开」、按钮「取消」「撤销」），确认后 `controller.revoke(link)`。`nextCursor != null` 时底部「加载更多」。`notice` 非 null 时以 `Text` 显示。
- `ShareLinkLandingPage({Key? key, required CommunityApi api, required String shareId, required void Function(String targetType, String targetId) onOpen})`：`initState` 调 `resolveShare`；加载中 `CircularProgressIndicator`；`ShareOpened` → 调用 `onOpen` 恰一次；`ShareUnavailable` →「该内容已不可访问」；`ShareOffline` →「离线，无法打开分享链接」+「重试」；`ShareError` →「分享链接打开失败」+「重试」。

### 10.10 挂载（缺省渲染不变，D-NC012-18）

- `ContentDetailPage` 追加 `final Widget Function(String contentId)? interactionBuilder;` 与 `final Widget Function(String contentId, Widget snapshot)? snapshotWrapper;`。`success` 分支：把「标题 `Text` + `SizedBox(height: 16)` + `MarkdownPreview`」三者包成 `Column(crossAxisAlignment: CrossAxisAlignment.start, children: [...])` 记为 `snapshotWidget`；`snapshotWrapper` 非 null 时渲染 `snapshotWrapper!(contentId, snapshotWidget)`，否则直接展开原三项（与现状逐项相同）；其后 `interactionBuilder` 非 null 时渲染之；最后是既有 `discussionBuilder`。
- `DiscussionPanel` 追加 `final Widget Function(Comment comment, Widget content)? commentDecorator;`。`_buildCommentItem` 中 `if (isVisible) Text(comment.currentRevision?.body ?? '')` 一项改为：`commentDecorator` 为 null 时保持原 `Text`；非 null 时为 `commentDecorator!(comment, Text(comment.currentRevision?.body ?? ''))`。deleted/hidden 不经装饰。

### 10.11 文案闭集（逐字，不得增删改）

「赞」「踩」「收藏」「已收藏」「分享」「举报」「垃圾广告」「辱骂攻击」「侵犯版权」「其他」「补充说明（可选）」「/500」「提交举报」「补充说明不能超过 500 字」「举报已提交，待发送」「举报已受理」「举报未能提交，请重试」「你已举报该内容」「你已举报该评论」「仍要查看」「赞踩状态已在其他设备更新」「操作未能完成」「只能分享自己的内容」「内容未公开，无法分享」「该内容已不可访问」「网络恢复后将创建分享链接」「网络恢复后将撤销」「撤销未能完成」「分享链接加载中」「还没有分享链接」「分享链接读取失败」「重试」「离线，无法加载分享链接」「更多分享链接加载失败」「加载更多」「已撤销」「撤销」「撤销分享链接」「撤销后，已发出的链接将无法打开」「取消」「评论」「内容」「离线，无法打开分享链接」「分享链接打开失败」「取消赞踩」「取消收藏」「创建分享链接」。

## 11. CLIENT 测试判据（`test/community/interactions_test.dart`，`MockClient` + 临时目录真实 Drift 文件库）

| ACT | ID | 测试（名称逐字） | 关键断言 |
|---|---|---|---|
| 04 | J01 | `reaction_api_sends_if_match_and_parses_reaction_response` | PUT 路径逐字、`if-match` 为 `"3"`、体 `{"value": null}` 含 null 键；解析 `ReactionResponse` 计数；GET 无 `if-none-match` |
| 04 | J02 | `bookmark_api_optional_if_match_and_get_bookmark` | `ifMatch: null` 时无 `if-match` 头；`ifMatch: 2` 时为 `"2"`；`getBookmark` 解析 `active` |
| 04 | J03 | `share_and_report_api_paths_headers_and_bodies` | `POST /share-links` 体两键、`DELETE /share-links/<id>` 无体、`GET /me/share-links?limit=20` 与带 cursor；`POST /reports` 体恰四键；均带 `idempotency-key`（GET 除外） |
| 04 | J04 | `interaction_payload_hashes_match_python_reference` | `CommandQueue.computePayloadHash` 对 §9 R1、R2、B1、S1、S2、P1 等于字面量 |
| 04 | J05 | `interaction_restart_with_real_file_close_reopen_resends_same_key` | RW-5 ①（`reaction.set`）：首发 `SocketException`，关库、同路径重开、新队列 `recover(); drain()`，PUT 的 `Idempotency-Key` 与首发相同，`if-match` 相同 |
| 04 | J06 | `interaction_lost_response_reconciles_by_get_command_without_new_report` | RW-5 ②（`report.create`）：假服务器记录 POST 后测试把行改为 `sending`，关库重开；`recover()` 先 `GET /commands/{id}` 得 committed，不再 POST；假服务器举报仍 1 条 |
| 04 | J07 | `interaction_410_and_503_never_change_key` | RW-5 ③（`bookmark.set`）：503 `unavailable.command_status` → `unknown` → R5 404 → 以原键重发；410 `gone.command_result` → rejected；全程 key 唯一 |
| 04 | J08 | `pending_queue_summarizes_interaction_commands` | §10.5 七种摘要逐字 |
| 04 | J09 | `mention_ref_is_single_public_type_for_notes_and_comments` | 仅 `import 'package:reading_notes/reading_notes.dart'`：同一个 `MentionRef` 实例同时放入 `CreateCommentRequest.mentions` 与 `NoteRevision.mentions`；`CreateCommentRequest.toJson()['mentions'][0]` 恰四键；`CommentRevisionPublic.fromJson` 解析出的元素 `is MentionRef` |
| 04 | J10 | `reconcile_mentions_matches_python_reference_vectors` | §9 M1～M8 保留下标逐字相等 |
| 04 | J11 | `reconcile_mentions_counts_code_points_not_utf16_units` | 文本 `😀😀@甲`：offset 2 length 2 保留；offset 4 length 2（UTF-16 下标）丢弃 |
| 05 | J12 | `reaction_rapid_toggle_coalesces_to_serial_commands_with_confirmed_version` | 首个 PUT 由 `Completer` 挂起；等假服务器收到首个 PUT 后依次 `toggleReaction('like')`（撤回意图）、`toggleReaction('dislike')`；放行首个 PUT 返回 like v1 → 随后恰一个 PUT，`if-match` 为 `"1"`、体 `value=dislike`；全程 PUT 恰 2 个、无 `value=null` 的 PUT；最终 `displayReaction == 'dislike'` |
| 05 | J13 | `reaction_late_older_version_response_does_not_roll_back` | 首个 PUT 挂起期间 `load()` 得 R3 `version=2, value=dislike`；放行 PUT 返回 v1 like → `reaction.version == 2`、`displayReaction == 'dislike'` |
| 05 | J14 | `reaction_412_refreshes_state_and_does_not_auto_retry` | PUT 412 `conflict.version` → `notice == '赞踩状态已在其他设备更新'`；随后 GET 一次，状态为服务器值；PUT 总数 1 |
| 05 | J15 | `reaction_restart_restores_pending_value_and_next_action_uses_read_version` | 离线点赞（transport）→ 关库重开、新控制器 `load()`（R3 v0 null）→ `displayReaction == 'like'`；换可用假服务器 `drain()` → PUT 原键、`if-match "0"` → v1；再点踩 → PUT `if-match "1"` |
| 05 | J16 | `bookmark_toggle_offline_restart_confirms_once` | 离线收藏 → 重启恢复 `displayBookmarked == true` → drain 后假服务器收到 PUT 恰 1 次、同一键 |
| 05 | J17 | `report_marks_reported_locally_before_send_and_clears_on_rejection` | POST 挂起时 `reported == true`、meta 行存在、`notice == '举报已提交，待发送'`；201 后 `'举报已受理'`；另一目标 404 `not_found.content` → meta 行删除、`reported == false`、`'举报未能提交，请重试'`；`detail` 501 个 emoji → `'补充说明不能超过 500 字'` 且库中无 `report.create` 行 |
| 05 | J18 | `share_controller_creates_lists_and_revokes_links` | `create` → POST、`lastCreated.id` 等于响应、随后 GET `/me/share-links`；`revoke` → DELETE、该项 `revokedAt` 非 null；403 `forbidden.not_owner` → `'只能分享自己的内容'` |
| 05 | J19 | `resolve_share_maps_404_to_unavailable_and_transport_to_offline` | 200 → `ShareOpened`（字段相等）；404 → `ShareUnavailable`；`SocketException` → `ShareOffline`；500 → `ShareError` |
| 06 | J20 | `interaction_bar_shows_counts_toggles_and_has_48dp_hit_targets` | 计数文本；点「赞」后计数 +1 且发 PUT；四个按钮 `tester.getSize` 宽高均 ≥ 48；`isOwner: true` 显示分享不显示举报；`compact: true` 无收藏与分享 |
| 06 | J21 | `report_sheet_submits_and_shows_accepted_then_folds_content` | 打开 `ReportSheet`，选「垃圾广告」、输入说明、点「提交举报」→ POST 体 `reason=spam`；`'举报已受理'` 出现；`ReportedFold` 显示「你已举报该内容」且 child 文本不在树中 |
| 06 | J22 | `reported_fold_survives_restart_and_can_be_expanded` | 关库重开、新控制器 `load()` 后仍折叠；点「仍要查看」→ child 出现 |
| 06 | J23 | `share_links_page_states_revoke_confirmation_and_load_more` | loading/empty/error/offline/partial/success 文案逐字；点「撤销」出现对话框标题与正文逐字，点「撤销」→ DELETE 且该项显示「已撤销」；「加载更多」请求带 cursor |
| 06 | J24 | `share_link_landing_page_unavailable_offline_and_open` | 404 →「该内容已不可访问」；离线 →「离线，无法打开分享链接」+「重试」；200 → `onOpen` 恰一次且参数为 `('content', 'note_…0001')` |
| 06 | J25 | `content_detail_page_optional_builders_keep_default_render` | 不传两参数时标题与正文可见、无 `reaction-like` 键；传入后 `interactionBuilder` 的 bar 出现，`snapshotWrapper` 包裹的 `ReportedFold` 生效 |
| 06 | J26 | `discussion_panel_comment_decorator_wraps_visible_comments_only` | 装饰器返回带 `ValueKey('decorated-<id>')` 的组件：visible 评论有、deleted/hidden 评论无；不传装饰器时无任何 `decorated-` 键 |

计数：act/04 `+281`；act/05 `+289`；act/06 `+296: All tests passed!`；`flutter analyze` 0。

## 12. REST 产物

### 12.1 `openapi.yaml`

1. `components/schemas` 新增：`ReactionResponse`（`type: object`、`required: [reaction, command]`、`reaction: $ref ReactionState`、`command: $ref CommandResult`、`additionalProperties: false`）；`BookmarkResponse`（同构，键 `bookmark` 引用 `BookmarkState`）；`ShareLinkPage`（`required: [items, next_cursor]`、`items: {type: array, maxItems: 100, items: {$ref: ShareLink}}`、`next_cursor: {type: [string, "null"]}`、`additionalProperties: false`）。
2. W10 `PUT /v1/community/reactions/{target_type}/{target_id}`：`'200'` 的 schema 改为 `ReactionResponse`；追加 `'403': $ref '#/components/responses/403ForbiddenThreadClosed'`。W11 `PUT /v1/community/bookmarks/{target_type}/{target_id}`：`'200'` 改为 `BookmarkResponse`。
3. `/v1/community/bookmarks/{target_type}/{target_id}` 追加 `get`（R8）：`summary: 查询收藏状态 (R8)`、`operationId: getBookmarkState`、`x-xuan-function: community_bookmark_py`、`tags: [CommunityBookmarks]`、parameters `TargetType`、`TargetId`、`Traceparent`；responses `'200'`（`BookmarkState`）、`'400'`、`'401'`、`'404'`（`NotFoundContent`）、`'429'`，组件引用照抄同路径 `put`。
4. 新增路径 `/v1/community/me/share-links`（放在 `/v1/community/share-links/{share_id}` 之后）：`get`（R7）`summary: 列出我的分享链接 (R7)`、`operationId: listMyShareLinks`、`x-xuan-function: community_share_py`、`tags: [CommunityShareLinks]`；parameters 照抄 R6 `/v1/community/me/contents` 的 `get.parameters` 列表；responses `'200'`（`ShareLinkPage`）、`'400'`、`'401'`、`'429'`，组件引用照抄 R6。
5. W12 `POST /v1/community/share-links` 的 `description` 追加一句「作者本人对不公开目标创建为 403 forbidden.thread_closed。」；W14 `POST /v1/community/reports` 追加 `'413': $ref '#/components/responses/413TooLarge'`，`description` 追加「detail 超过 500 个 code point 为 413 too_large.detail。」；R4 `description` 追加「不存在、已撤销、格式不符与目标不可读一律 404 共用 NotFoundContent。」
6. 不改其他路径、方法与组件。

### 12.2 追加测试（名称逐字，73 → 77）

- `reaction and bookmark writes return wrapped responses with command`：W10/W11 的 200 分别引用 `ReactionResponse`/`BookmarkResponse`，二者 `required` 与 `additionalProperties: false` 逐字；W10 含 `'403'` 引用 `403ForbiddenThreadClosed`。
- `my share links and bookmark read paths are declared`：`/v1/community/me/share-links` 的 `get.operationId == listMyShareLinks`、200 引用 `ShareLinkPage`；bookmarks 路径 `get.operationId == getBookmarkState`、200 引用 `BookmarkState`；`ShareLinkPage` 结构逐字。
- `interaction write errors declare detail too large`：W14 含 `'413'` 引用 `413TooLarge`。
- `interaction examples manifest has seventeen entries and validates`：manifest 长度 17，含 §12.3 四项及 expect；`tool/check_examples.py` 退出 0。

### 12.3 示例（`test/fixtures/openapi/examples/`，manifest 末尾追加 `{file, schema, expect}` 四项）

- `reaction_response_like.json`（`ReactionResponse`，valid）：`{"reaction": {"target_type": "content", "target_id": "note_00000000000000000000000000000001", "value": "like", "version": 1, "counts": {"like": 1, "dislike": 0}}, "command": {"command_id": "cmd_00000000000040008000000000000001", "operation": "reaction.set", "outcome": "committed", "applied_version": 1, "resource_ids": {"target_type": "content", "target_id": "note_00000000000000000000000000000001", "reaction_id": "rct_ede12cd76c76e944120f75d6ccf424ad"}, "result_http_status": 200, "committed_at": "2026-09-11T08:00:00.000001Z", "result_code": null, "compacted": false}}`
- `bookmark_response_active.json`（`BookmarkResponse`，valid）：`bookmark` 为 `{"target_type": "comment", "target_id": "cmt_00000000000000000000000000000001", "active": true, "version": 1}`；`command` 同上但 `command_id` 末位 `2`、`operation: bookmark.set`、`resource_ids` 为 `{"target_type": "comment", "target_id": "cmt_…0001", "bookmark_id": "bmk_58da728e583165f3f33e853295ecf8de"}`。
- `share_link_page_with_revoked.json`（`ShareLinkPage`，valid）：`items` 两条：`shr_…0002`（content `note_…0001`，created_at `2026-09-11T08:00:00.000002Z`，`revoked_at` null）与 `shr_…0001`（同目标，created_at `…000001Z`，`revoked_at` `2026-09-11T09:00:00.000000Z`）；`next_cursor` null。
- `reaction_state_value_love.json`（`ReactionState`，invalid）：同第一例的 `reaction` 对象但 `value` 为 `"love"`。

若 `check_examples.py` 对前两例报 `CommandResult.resource_ids` 键不被接受，按停手协议上报，不得改 Schema。

## 13. community_api 补丁

本任务对 community_api 的增补登记于其 §12（D-NC012-05、06、07、12）：W10/W11 响应包装、R7/R8 新读端点、R4 统一 404、R3 ETag、错误目录 403 thread_closed 适用面扩展与 `too_large.detail`、`invalid_argument.{target_type, target_id, reaction, bookmark, share_link, share_id, report}`。

## 14. NC-012b 边界（`BLOCKED`，等 NC-001-02）

`CLIENT/lib/src/community/social_navigation_adapter.dart`（资料、关注、私信、拉黑经宿主注入）；mention 候选 Source 与 `MentionInputEnhancer` 接入编辑器与讨论区输入；保存时调用 §10.6 `reconcileMentions` 解除关系；服务端 mention 的 user_id 存在性、注销、拉黑三类无效判定与 mention 事件（与 NC-013 投递衔接）；「两账号计数、失权目标、空候选、名字重复但 ID 不同、四类无效 mention」中依赖宿主关系的用例；关系与互动经实际宿主注入的验收。

## 15. 决定登记（NC-012a，主 Agent 裁定，可推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC012-01 | NC-012 拆为 12a（本文）与 12b（宿主社交注入与 mention 深度校验，`BLOCKED`） | TASKS 要求关系与互动业务结果走实际宿主注入，NC-001-02 联调取证未完成；互动命令与分享举报不依赖宿主 |
| D-NC012-02 | Reaction/Bookmark 文档 ID 由 `(target_type, target_id, actor_id)` 经 E 确定性派生；计数投影键 `<target_type>__<target_id>` | 同目标同账号唯一（DESIGN §6）在事务内以文档键保证，不需查找索引 |
| D-NC012-03 | W10 必带 If-Match，版本比较先于同值判定；同值不写、不升版本 | DESIGN「reaction 必带 If-Match」；两设备同基线必须一个 412（TASKS 基准反例）；相同值不重复计数 |
| D-NC012-04 | W11 If-Match 可选，带则比较 | DESIGN 只要求 reaction 必带；收藏私有、冲突只来自本人多设备 |
| D-NC012-05 | W10/W11 的 200 响应改为 `ReactionResponse`/`BookmarkResponse` 包装 | community_api §2「写响应必含 command」与 `ReactionState`/`BookmarkState` 的 `additionalProperties: false` 冲突；同 `CommentResponse` 范式 |
| D-NC012-06 | 新增 R7 `GET /me/share-links` 与 R8 `GET /bookmarks/{target_type}/{target_id}` | PRD「我的」分享链接管理需要列表；收藏按钮需要读取本人状态 |
| D-NC012-07 | R4 一切失败共用 `NotFoundContent` 体 | PRD §6.2 不区分失效原因；避免以 404 码区分「链接不存在」与「内容已收回」 |
| D-NC012-08 | 分享只允许目标作者创建；作者本人不公开目标 403 `forbidden.thread_closed`；同目标可建多条 | D-NC003-12 `share.create` 属本人操作；不公开内容的链接必然解析失败 |
| D-NC012-09 | 撤销幂等：已撤销再撤销 200 不写 | 客户端离线重试与多设备撤销不应报错 |
| D-NC012-10 | 举报以 command_id 为键，服务端不去重，客户端本地折叠 | D-NC002-03；PRD 以折叠避免重复举报，审核处置不在本期 |
| D-NC012-11 | outbox 只追加 `reaction.liked`；踩、收藏、分享、举报不写 | PRD §5「赞进入站内通知；踩/收藏/分享默认不通知」；投递与合并归 NC-013 |
| D-NC012-12 | R3 ETag = `"<viewer version>:<like>:<dislike>"`，ACL 先于 304；不可读目标：内容共用体、评论 `not_found.comment`，作者不公开为 403 | 他人计数变化须改变 ETag；403/404 边界沿用 DESIGN §7.3 与 D-NC011-06 |
| D-NC012-13 | 客户端删除社区版 `MentionRef`，统一为 domain 类，公开入口不再 hide | NC-011 验收遗留：宿主经公开入口无法构造带 mentions 的评论请求；两类字段与 JSON 形状相同 |
| D-NC012-14 | `reconcileMentions` 纯函数以服务端 `filter_mentions` 实测向量对齐，本期不接入编辑器 | @ 插入与保存接线依赖 NC-012b 的候选来源；先固化跨端一致的判定 |
| D-NC012-15 | 每目标至多一个非终态 reaction/bookmark 命令，快速切换合并为最终意图、按确认版本串行；412 只刷新不自动重发 | TASKS「禁止自动换版本抢写」「快速切换乱序/重试」；避免同 target 冲突异常 |
| D-NC012-16 | 迟到响应防回滚：仅采纳 version ≥ 当前确认版本的状态；412 后以服务器读值直接覆盖 | TASKS「UI 不被旧 v1 响应覆盖」；412 表明本地确认值已过期 |
| D-NC012-17 | 举报折叠记录存 `community_meta`（`reported:<target_type>:<target_id>`），入队即折叠，被拒撤销折叠 | 不加表（NC-010 数据库不变）；离线举报也应立即避免重复 |
| D-NC012-18 | 界面经 `ContentDetailPage.interactionBuilder/snapshotWrapper` 与 `DiscussionPanel.commentDecorator` 可选挂载 | 不改 NC-010/011 已验收页面的缺省渲染与其测试 |
| D-NC012-19 | 规则测试纳入（89 → 129）；ACL 扫描 E4 转为真实断言（xfail 9 → 6） | 新集合须证明默认拒绝；community_server §5 E4 所有者为 NC-012 |
| D-NC012-20 | 延后：复合索引部署、限流开启、收藏列表页、分享 URL 格式（宿主注入 `shareUrlBuilder`）、举报进入审核队列、目标 purge 时清理互动文档（NC-019） | 本任务验收命令为 Emulator pytest 与 flutter test；URL 与审核由宿主与运营侧决定 |
| D-NC012-21 | 10 并发 reaction 测试以同一 ctx 重试 503 最多 5 次 | 同 D-NC011-22；Emulator 事务竞争会以 503 结束，客户端本就以同键重试 |
| D-NC012-22 | REST 既有路径目录测试同步新增 R7、R8；NC-011 示例清单测试的恰 13 项改为至少 13 项，恰好项数由本任务 A04（17 项）断言；nc011_guard K05 同步为 ≥13 | act/01 执行中实测两条既有测试把端点目录与示例数写死，契约新增端点与示例必然使其变红（主 Agent 规格遗漏，执行方停手正确）；目录测试编码的就是 community_api §2 目录，随 §12.2 更新属同步而非放宽 |
