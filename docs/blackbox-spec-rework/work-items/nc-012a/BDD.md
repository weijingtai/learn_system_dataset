# NC-012a 可观察行为

ID 与契约 `community_interactions.md` §8.2（I）、§11（J）、§12.2（A）一一对应；「期望」逐字以契约为准，本表只给 Given/When/Then 摘要。服务端 HTTP 测试经 `community_helpers.call(<handler>, ...)`，并发测试直接调用 `run_command`；客户端一律 `MockClient` + 临时目录真实 Drift 文件库。

## REST

| ID | Given | When | Then |
|---|---|---|---|
| A01 | 修改后的 openapi.yaml | 读 W10/W11 的 200 与 W10 的 403 | 分别引用 `ReactionResponse`/`BookmarkResponse`（required 两键、additionalProperties false）；W10 含 403 thread_closed |
| A02 | 同上 | 读 `/v1/community/me/share-links` 与 bookmarks 路径 get | operationId `listMyShareLinks`（200 `ShareLinkPage`）与 `getBookmarkState`（200 `BookmarkState`） |
| A03 | 同上 | 读 W14 responses | 含 `'413'` 引用 `413TooLarge` |
| A04 | manifest 追加 4 项 | 运行 check_examples.py | 共 17 项；两个包装与分享页 valid、`value=love` invalid；退出 0 |

## SERVER

| ID | Given | When | Then |
|---|---|---|---|
| I01 | 公开内容 | 他人 W10 like（If-Match 0） | 200 `{reaction, command}`；reaction、计数、outbox `reaction.liked`、行为事件同事务写入 |
| I02 | §9 输入 | 计算 payload_hash 与文档 ID | 六个哈希、RID、BID 等于字面量 |
| I03 | 已 like v1 | W10 null（If-Match 1） | v2，行保留 value null，like 计数 0 |
| I04 | 已 like v1 | W10 dislike | 计数由 like 移到 dislike |
| I05 | 已 like v1 | 新命令 like（If-Match 1） | 200 版本仍 1，不写、不重复计数 |
| I06 | 已 like v1 | 缺 If-Match / 旧 If-Match / 畸形 If-Match | 400 / 412 current_version 1 / 400 且无账本 |
| I07 | like v1 → cancel v2 | 重放 like 原键 | 返回原响应（v1）；数据库与 R3 仍 null v2 |
| I08 | 同账号两设备同基线 v0 | like 与 dislike 先后提交 | 一个 200，一个 412 |
| I09 | 两账号 | 甲 like、乙 dislike | 计数 1/1，各自 R3 value 不同 |
| I10 | 10 个账号 | 同时 like（503 同 ctx 重试 ≤ 5） | 全部 200，like 计数恰 10 |
| I11 | 内容 withdrawn/trashed/hidden | 非作者 W10 | 404 共用体，零写入 |
| I12 | 作者不公开内容；评论目标 | 作者 W10；visible/deleted 评论 W10 | 403 thread_closed；200；404 not_found.comment |
| I13 | like v1 后目标 purge、互动文档被删 | 原键重放；新命令 | 原响应且不复活；404 |
| I14 | 甲 like | 甲/乙 R3；乙带 ETag；内容收回后乙带 ETag | `"1:1:0"`/`"0:1:0"`；304；404 |
| I15 | — | 非法 target_type / target_id / value / 空体 | 400 且 code 与 field 逐字 |
| I16 | 公开内容 | W11 无 If-Match、同值、旧 If-Match；甲乙 R8 | v1、v1 不变、412；甲 active 乙 inactive |
| I17 | hidden 内容；不存在评论 | 非作者 W11 | 404 共用体；404 not_found.comment |
| I18 | 公开内容与评论 | 作者/非作者/作者不公开 W12 | 201 / 403 not_owner / 403 thread_closed；评论作者 201 |
| I19 | 八种链接状态 | R4 | public 200；其余七种 404 且逐字节等于共用体 |
| I20 | 已建链接 | 创建者撤销两次、非创建者撤销、未知 ID、格式错 | 200 / 200 不变 / 403 / 404 / 400 |
| I21 | 甲三条（含撤销）乙一条 | R7 limit 2 翻页 | 倒序、SCUR 游标、含撤销、无乙的链接 |
| I22 | — | R7 非法 limit 与 cursor | 400 limit / 400 cursor |
| I23 | 公开评论 | W14 | 201 `{report_ref, command}`；文档键 command_id、七字段、无 outbox |
| I24 | — | detail 500 / 501 个 emoji；reason 非法 | 201 / 413 too_large.detail / 400 field /reason |
| I25 | trashed 内容 | 非作者 W14；作者对自己 withdrawn 内容 W14 | 404 共用体；201 |
| I26 | — | share/report 同键重放；bookmark 同键异载荷 | 同体一份；409 conflict.idempotency |
| I27 | 含说明文字的举报 | W14 201/413、W10 412、R4 404 | 日志不含说明文字 |

## CLIENT

| ID | Given | When | Then |
|---|---|---|---|
| J01 | MockClient | setReaction / getReaction | if-match `"3"`、体含 null 键、无 if-none-match、解析计数 |
| J02 | MockClient | setBookmark 有无 ifMatch；getBookmark | 头有无 if-match；解析 active |
| J03 | MockClient | 分享四方法与举报 | 路径、头、体键逐字 |
| J04 | §9 输入 | computePayloadHash | 六个字面量 |
| J05 | reaction.set 首发 SocketException | 关库重开后 recover+drain | 同一 Idempotency-Key 与 if-match |
| J06 | report.create 响应丢失 | 行改 sending 后重开 recover | 先查命令、不再 POST，举报 1 条 |
| J07 | bookmark.set | 503 → unknown → 404 → 重发；410 → rejected | key 唯一 |
| J08 | 七种互动命令行 | 待处理页摘要 | 文案逐字 |
| J09 | 仅公开入口 | 同一 MentionRef 用于评论请求与笔记修订 | 编译通过、JSON 四键、解析类型一致 |
| J10 | §9 M1～M8 | reconcileMentions | 保留下标逐字 |
| J11 | `😀😀@甲` | code point 与 UTF-16 偏移 | 前者保留、后者丢弃 |
| J12 | 首个 PUT 挂起 | 连续切换 like→撤回→dislike 后放行 | PUT 恰 2 个，第二个 if-match 1、dislike |
| J13 | PUT 挂起期间 load 得 v2 | 放行 v1 响应 | 保持 v2 |
| J14 | PUT 412 | refreshPending | 提示文案、刷新一次、不重发 |
| J15 | 离线点赞后重启 | load、drain、再点踩 | 显示 like；原键 if-match 0；新命令 if-match 1 |
| J16 | 离线收藏后重启 | drain | PUT 恰一次同键 |
| J17 | POST 挂起 / 404 / 说明超长 | report | 先折叠与待发送；受理；撤销折叠；超长提示且不入队 |
| J18 | 分享控制器 | create / revoke / 403 | lastCreated、revokedAt、提示文案 |
| J19 | resolveShare | 200/404/Socket/500 | Opened/Unavailable/Offline/Error |
| J20 | InteractionBar | 渲染、点赞、owner/compact | 计数、PUT、四按钮 ≥ 48、按钮显隐 |
| J21 | ReportSheet | 选原因、填说明、提交 | POST spam、受理文案、内容折叠 |
| J22 | 已举报 | 重启后 load；点「仍要查看」 | 仍折叠；展开 |
| J23 | ShareLinksPage | 六态、撤销确认、加载更多 | 文案逐字、DELETE、已撤销、cursor |
| J24 | ShareLinkLandingPage | 404/离线/200 | 统一文案、离线文案、onOpen 恰一次 |
| J25 | ContentDetailPage | 不传/传两个 builder | 缺省渲染不变；bar 与折叠生效 |
| J26 | DiscussionPanel | 传/不传 commentDecorator | 只装饰 visible 评论；不传无装饰 |
