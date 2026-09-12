# NC-010 可观察行为

「测试」指 reading-notes 内 `flutter test <文件>`；HTTP 一律 `package:http/testing.dart` 的 `MockClient`（记录请求方法、路径、头、体）；数据库用临时目录真实 Drift 文件库；时间经 `CommunityClock` 替身与 `FakeAsync`。

| ID | Given | When | Then |
|---|---|---|---|
| B01 | 空队列 | `enqueue(content.withdraw, ...)` 后在 `MockClient` 被调用前读库 | 库中已有该行 `state=queued`；`command_id` 匹配 `^cmd_[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$`；1000 次生成无重复 |
| B02 | 契约 §8 输入 | 计算 payload_hash | 等于字面量 `c8e2c2b0a842ece53f90cbf84e64fbacf274745a42bf4fb389b670fb0b3b72b5` |
| B03 | 某 content 已有非终态命令 | 再 `enqueue` 同 target | 抛 `PendingOpConflict`，库中只有一行 |
| B04 | `MockClient` 抛 `SocketException` | `drain` | 行回到 `queued`、`attempt_count=1`、`auto_attempts=1`；下一次请求的 `Idempotency-Key` 与首次相同；时钟未到 1 秒前不重发 |
| B05 | 库中残留 `sending` 行（写入后**关闭真实文件库**，再以同一文件路径重开并新建队列） | 新建队列并 `recover(); drain()` | 先发 `GET /v1/community/commands/{id}`；R5 返回 404 → 以同键重发写请求；R5 返回 200 committed → 不重发、行 `committed` |
| B06 | 写请求返回 503 `unavailable.command_status` | `drain` 两次 | 首次后行为 `unknown`；第二次先 R5 查询再落定 |
| B07 | 写请求返回 409 `conflict.lifecycle` | `drain` | 行 `rejected`，`last_problem_code=conflict.lifecycle`，不再发送 |
| B08 | 写请求返回 410 `gone.command_result`（体含 `command`） | `drain` | 行 `rejected` 且 `result_json` 含 `command`；随后对 `resource_ids.content_id` 发 R1 |
| B09 | `queued` 且未发送 / 已发送过一次 | `cancel` | 前者 `cancelled`；后者抛 `CommandAlreadySent`，状态不变 |
| B10 | `IdTokenProvider` 返回 null | `drain` | `MockClient` 零调用，行仍 `queued`、`attempt_count=0` |
| B11 | 首次发布 | `publish(cmd, body)` | `POST /v1/community/contents`；头含 `Authorization: Bearer <token>`、`Idempotency-Key: <cmd>`，不含 `If-Match`；体为 snake_case 且字段集合等于 `PublishRequest` |
| B12 | 重新发布 | `publish(cmd, body, ifMatch: 4)` | 头 `If-Match: "4"` |
| B13 | W2～W6 | 各调用一次 | 路径与方法逐字等于 community_api §2；均带 `If-Match: "<v>"` |
| B14 | `getContent(id, ifNoneMatchVersion: 7)`，服务器 304 | — | 请求头 `If-None-Match: "7"`；返回 `ApiResult.notModified` |
| B15 | 错误体为 `application/problem+json` 但缺 `code` | 任一调用 | 返回 `ApiResult.transport` |
| B16 | R1 响应中 `current_publication_id: null`、`published_at: null` | 解析 | Dart 字段为 null，不抛 |
| B17 | 契约 §5.2 八行条件各构造一例（含 N 天的运行时计算）＋ `trashed` 与 `hidden` 同时成立一例 | 派生作者文案 | 文案逐字等于表格；`inTrash` 的 N 按注入时钟计算；重叠例为「在回收站 · 剩余 N 天」（D-NC010-09） |
| B18 | 笔记有 3 个修订，其中 1 个含附件 | 预览中切换选中修订 | 每次切换 `PublishReadiness` 重算；含附件修订（无端口）不可发布并显示「含图片的笔记暂不能发布，请移除图片后再发布」 |
| B19 | 注入端口：两图分别 `uploading(40)`、`missing` | 打开预览 | 发布禁用；两图位置分别显示「上传中 40%」「文件已丢失」 |
| B20 | 发布命令入队，`MockClient` 延迟响应 | 发送期间与 201 返回后 | 期间显示进行中且无成功页；201 后才进入成功页 |
| B21 | 已发布内容，更新时服务器返回 412 | 确认更新 | 命令 `rejected`；控制器发 R1 刷新缓存；本地 `NoteRepository.listRevisions` 数量与内容不变；提示「内容已在其他设备更新，请确认后重试」 |
| B22 | `MockClient` 始终 `SocketException` | 确认发布 | 命令保留 `queued`，出现在待处理队列，笔记不显示已公开 |
| B23 | 缓存 `visibility=published` | 调 `trash` | 抛 `TrashRequiresWithdraw`，队列无新行 |
| B24 | 同 owner 首次发布、第二次发布 | 两次打开发布确认 | 首次出现 PRD §5.1 一次性后果说明原文；第二次不出现 |
| B25 | 修订 A 已发布，本地另存修订 B（标题含「私密草稿」） | 成功页点「查看公开效果（他人视角）」 | 渲染内容来自 R1 快照，含 A 的标题，不含「私密草稿」 |
| B26 | 队列中一条 `rejected` 且 `code=not_found.content` | 打开待处理队列 | 该条显示终止原因与「复制正文」；点击后 `ClipboardPort` 收到对应修订 markdown |
| B27 | 队列为空 | 打开待处理队列 | 显示「所有操作都已完成同步」 |
| B28 | 注入 `CommentCountPort` 返回 12 / 未注入 | 打开收回确认层 | 前者含「12 人的评论将无法访问」；后者含「该内容下的评论将无法访问」；两者都不含字面量「N 人」 |
| B29 | 笔记 4 个修订、附件去重后 3 张 | 打开彻底删除确认层 | 含「及其 4 个历史版本、3 张图片」，需二次点击才入队 |
| B30 | 契约 §6 表四屏 | 逐状态构造 | 25 例各自断言表中文案逐字出现 |
| B31 | 真实文件库中写入 `sending` 行后关闭数据库 | 同一路径重开、新建队列、`recover(); drain()` | 先 R5，R5 404 后以同键重发；`MockClient` 记录的两次写请求 `Idempotency-Key` 相同 |
| B32 | 一条 `queued` 命令，`MockClient` 延迟 200 ms | 同时调用两次 `drain()` | 写请求恰 1 次；两次调用返回的 `Future` 都完成 |
| B33 | `MockClient` 连续抛 `SocketException` | 推进 `FakeAsync` 并反复 `drain` | 五次发送之间的间隔依次为 1s/2s/4s/8s；第 5 次失败后 `paused`，再推进 60 s 无请求；用户 `retry()` 后 `queued`、`auto_attempts=0`、键不变 |
| B34 | `queued` 命令 `created_at` 为 14 天 + 1 秒前 | `drain` | 第一个请求是 `GET /v1/community/commands/{id}`；返回 200 committed → 不发写请求，行 `committed` |
| B35 | 已发布笔记入队 `content.withdraw` | 查询 `NoteRepository.getNote` | `pendingOp == withdraw_requested`；命令 committed 后为 `none`；手动把 `notes.pending_op` 改为 `none` 后重启 `recover()` 且命令仍 `queued` → 恢复为 `withdraw_requested` |
| B36 | 缓存 `access_version=5` | 迟到的 committed 响应携带 `access_version=4` | 缓存仍为 5，作者文案不回退 |
| B37 | 作者笔记 `moderation_state=hidden` | 渲染笔记列表 | 文案「已被管理员暂停展示」旁有「申诉」按钮；点击后注入的 `AppealHandler` 收到 contentId |
| B38 | 待处理队列中一条 `paused` 命令 | 打开队列并点击该条 | 显示「发送失败，点此重试」；点击后命令 `queued`、`auto_attempts=0`，随后 `MockClient` 收到的写请求 `Idempotency-Key` 与暂停前相同 |
| B39 | 首次发布命令，`ifMatch` 为 null | `computePayloadHash`（契约 §10.1 样例二） | 等于 `074958695bdd875ce11b8bdf379ca335f81e5e8a1be90a276e18fd0eec450c17` |
| B40 | body 键为 U+FF41 与 U+1F600 | `computePayloadHash`（契约 §10.1 样例三） | 等于 `822219839fdd8fac8dce019ba46d82944403ade090ed6e8089480af57b40bfda`；§8 样例一仍等于 `c8e2c2b0a842ece53f90cbf84e64fbacf274745a42bf4fb389b670fb0b3b72b5` |
