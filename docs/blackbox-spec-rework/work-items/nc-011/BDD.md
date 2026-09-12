# NC-011 可观察行为

ID 与契约 `community_discussion.md` §9.2（T）、§12（K）、§13.2（A）一一对应；「期望」逐字以契约为准，本表只给 Given/When/Then 摘要。服务端 HTTP 测试经 `community_helpers.call(community_comment_py, ...)`，并发测试直接调用 `run_command`；客户端一律 `MockClient` + 临时目录真实 Drift 文件库。

## REST

| ID | Given | When | Then |
|---|---|---|---|
| A01 | 修改后的 openapi.yaml | 读 R2 parameters 与 components/parameters | 含 `RootId`（root_id，query，可选，cmt pattern）与 `CommentOrder`（order，query，可选，enum newest/oldest，无 default） |
| A02 | 同上 | 读 `CommentPage`、`CommentReplyPreview` | required 恰五键；reply_previews 为 propertyNames + additionalProperties 结构；预览 items maxItems 5 且 additionalProperties false |
| A03 | 同上 | 读 W7 `409` | 引用 `409ConflictCommentCreate`，其 oneOf 恰为 ProblemAccessVersionConflict 与 ProblemIdempotencyConflict |
| A04 | manifest 追加 3 项 | 运行 check_examples.py | 共 13 项；带预览页 valid、6 条预览 invalid、墓碑 valid；退出 0 |

## SERVER

| ID | Given | When | Then |
|---|---|---|---|
| T01 | 已公开内容、非作者 | W7 发一级评论 | 201，响应恰 comment/command，comment/revision 过 NC-002 Schema，thread 九键 version 1 计数 1，outbox 与行为事件各一条，attributes 为空 |
| T02 | 契约 §10 三组输入 | `compute_payload_hash` | 等于 H1～H3 字面量 |
| T03 | `note_…0001` | `thread_id_for` | `thr_29d9aa55fe9a6205547731ea3b3dc1a7` |
| T04 | 已有一级 R | 回复 R（reply_to 为 null） | depth 1、root R |
| T05 | R 下已有回复 X | reply_to_id=X、root_id=R | depth 1、root R |
| T06 | — | 有 reply_to_id 无 root_id | 400 `invalid_argument.root_id`，账本 rejected |
| T07 | root 或 target 属于别的内容/别的楼 | W7 | 404 `not_found.comment` |
| T08 | root_id 指向 depth 1 | W7 | 404 `not_found.comment` |
| T09 | root 或目标已删除 | W7 回复 | 403 `forbidden.thread_closed`，零写入 |
| T10 | 目标 hidden | W7 回复 | 403 `forbidden.thread_closed` |
| T11 | 4000 / 4001 个 U+1F600 | W7 | 201 / 413 `too_large.comment_body` limit 4000 |
| T12 | 空白正文、缺必填、mention length 1 | W7 | 400 `invalid_argument.comment_body` / `invalid_argument.comment` field `/` / field `/mentions/0/length` |
| T13 | 51 条 mention；或一条匹配一条不匹配 | W7 | 413 `too_large.mentions`；revision 只存匹配项 |
| T14 | 内容 withdrawn / trashed / hidden，非作者 | W7 | 404 `not_found.content` 无附加字段，零写入 |
| T15 | 作者自己的 withdrawn 内容 | W7 | 403 `forbidden.thread_closed` |
| T16 | access v2 已公开 | expected 1 | 409 `conflict.access_version`，current_access_version 2 |
| T17 | 已成功一次 | 同键同载荷 / 同键异载荷 | 原 201 体且评论仍一份 / 409 `conflict.idempotency` |
| T18 | 甲 2 条、乙 1 条 | 读 thread | 评论数 3、评论人数 2 |
| T19 | visible 评论 v1 | 作者 W8 If-Match "1" | 200 v2，新 revision parent 指旧，created_at 不变，thread version+1，outbox edited |
| T20 | 他人评论 | W8、W9 | 403 `forbidden.not_owner` |
| T21 | 评论 v2 | 缺 If-Match / "1" | 400 `invalid_argument.if_match` / 412 current_version 2 |
| T22 | — | `If-Match: abc` | 400 且无账本文档 |
| T23 | deleted、hidden 评论 | W8、W9 | 404 `not_found.comment` |
| T24 | 有回复的一级 R | W9 删除 R | 200 墓碑 current_revision null；R2 仍列 R 与回复；计数各减 1；再回复 R → 403 |
| T25 | 21 个一级 + 最新一级下 6 回复 | 默认 R2，再带 C2 | 20 条、next_cursor=C2、预览 5 条且游标 C3；第二页 1 条、游标 null |
| T26 | 6 条回复 | root_id+limit 5，再带游标；root_id+newest；游标 root 不符 | 5 条正序、余 1 条；400 order；400 cursor |
| T27 | 同 created_at 的 …0009 与 …00a0 | oldest / newest | 前者在先 / 后者在先 |
| T28 | access 3 | 默认 R2；root_id+limit 5（thread v3）；带 ETag；新增评论后；他人对 withdrawn 带合法 ETag | E1；E2；304；200；404 |
| T29 | — | limit 101、0，order hot，root_id abc，cursor !! | 各 400，code 逐字 |
| T30 | withdrawn 内容已有评论 | 作者 / 他人 R2 | 200 含评论 / 404 |
| T31 | 评论事务第 1 次提交被注入 `Aborted`，回滚后同步执行收回（契约 §8.1） | 回调重跑 | 收回 200；评论 404 `not_found.content`；hook 2 次；零评论零事件；评论账本 rejected |
| T32 | 已公开内容 | 先评论后收回（顺序执行） | 评论 201、收回 200、hook 1 次；他人 R2 404、作者 R2 含该评论 |
| T33 | 3 轮，每轮 2 评论线程 + 1 收回线程同步起跑 | 竞争；503 以同键重试 ≤ 3 次 | 收回 200；评论 ∈ {201, 404}；评论/revision/计数/outbox/事件条数均等于 201 个数；每键账本一条 |
| T34 | 评论事务第 1 次提交被注入 `Aborted` | 回调重跑 | 回调恰 2 次，新 ID 不变，评论一份，计数 +1 |
| T35 | 固定正文 | W7/W8/W9/R2 与一次 403、一次 409 | caplog 不含正文及编辑后正文前 20 字 |

## CLIENT

| ID | Given | When | Then |
|---|---|---|---|
| K01 | MockClient 返回含预览的页 | `listComments(rootId, order, cursor)` | 路径与 query 逐字，无 if-none-match，解析预览与两计数 |
| K02 | — | `createComment` | idempotency-key 有、if-match 无；体恰五键含 null |
| K03 | — | `editComment`/`deleteComment` ifMatch 2 | PATCH/DELETE 带 `"2"` |
| K04 | §10 三组输入 | 计算 payload_hash | 等于 H1～H3 |
| K05 | — | 同内容两次 create；同评论两次 edit | 两行入队；第二次 edit 抛 PendingOpConflict |
| K06 | 首发 SocketException | 关库重开后 recover+drain | 原键重发 |
| K07 | 假服务器已记录 POST，行被置 sending | 关库重开后 recover | 先 R5 得 committed，不再 POST，评论 1 条 |
| K08 | 503 command_status；另一条 410 | drain | unknown → R5 404 → 原键重发；410 rejected 且 onGone410 0 次 |
| K09 | R2 返回人数 3；另一次 404 | `countComments`/`resolveWithdrawCommentCount` | 3 / null 且确认层用通用句式 |
| K10 | 队列含 comment.create（21 code point 含 emoji）、delete、thread_closed 拒绝 | 打开待处理页 | 「评论：」+前 20 code point、「删除评论」、可复制正文 |
| K11 | 第一页 20 条 + 游标 | 点「加载更多评论」 | 40 条；滚动到底后的 pixels 与第 20 条的屏幕位置不变；请求带 cursor |
| K12 | 预览 5 条 + 游标 | 点「展开更多回复」 | 请求 root_id/oldest/limit 5/cursor，第 6 条出现 |
| K13 | 空页：已公开 / 已收回 | 打开面板 | 「还没有人评论，来写第一条」可发送 / 「该内容不接受新评论」不可发送 |
| K14 | 离线发送后关库重开 | 恢复联网 drain | 服务器评论 1 条，面板无「待发送」，待处理页「所有操作都已完成同步」 |
| K15 | 4001 / 4000 个 emoji | 发送 | 提示「评论不能超过 4000 字」且 0 行 / 入队 1 行 |
| K16 | POST 返回 409 access_version | 发送后刷新 | 「内容状态已变化，请确认后重新发送」，输入框保留草稿 |
| K17 | POST 201，随后 R2 404 | 发送 | 「内容已不可见」，评论正文不出现 |
| K18 | deleted root（含回复）与 hidden 评论 | 渲染 | 「该评论已删除」「该评论已被隐藏」；deleted 下无「回复」，回复仍显示 |
| K19 | 首次加载未返回 | 渲染 | 「评论加载中」 |
| K20 | 空页、已公开 | 渲染 | 「还没有人评论，来写第一条」与「发送」 |
| K21 | 已有列表，加载更多失败 | 渲染 | 列表 +「更多评论加载失败」+「重试」 |
| K22 | problem 500 | 渲染 | 「评论读取失败」+「重试」 |
| K23 | 首次 transport 失败 | 渲染 | 「离线，无法加载评论」+「重试」 |
| K24 | 已有列表，刷新 transport 失败 | 渲染 | 列表 +「评论更新于 HH:mm」 |
| K25 | 正常页 | 渲染 | 正文与「回复」 |
