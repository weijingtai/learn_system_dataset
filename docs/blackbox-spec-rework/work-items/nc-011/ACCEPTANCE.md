# NC-011 独立验收

当前：未验收。派发前置：NC-003、NC-009、NC-010 ACCEPTED（已满足）；wjt-react 四查 READY。

1. ACT 审查：未参与编写者做 wjt-react 四查（`reviews/NC-011-REVIEW-R1.md`）。
2. 范围（`git diff-tree -r --name-only`，不用 `git diff`）：REST `5730ed9` 之后恰 1 个提交、恰 6 个文件；SERVER `df5c3da` 之后恰 3 个提交、只含契约 §2.1 文件，禁止清单路径零改动；RULES `ea8c9b8` 之后恰 1 个提交、只改规则测试；CLIENT `4588f78` 之后恰 2 个提交、只含契约 §2.2 文件，受保护路径零改动。
3. 重跑 TDD §1 全部命令（经 tmux 执行器或 Haiku 只运行采集，主 Agent 读原始输出判定）；`nc011_guard.sh --require-impl all` 为 0。
4. 主 Agent 盲测（临时文件，不入库，结束时删除并以 `git status --short` 为空证明）：
   - ① 同键重放 W7：重放响应体键恰为 `comment`、`command`，与首响应逐字节相等（D-NC011-12）。
   - ② 编辑一条评论后，同参数 R2 的 ETag 改变；删除后再次改变（D-NC011-05）。
   - ③ 篡改游标：root 段换成另一 root、order 段换成 newest、时间段少一位微秒，三者均 400 `invalid_argument.cursor`。
   - ④ 同一作者两条评论删一条，`visible_commenter_count` 不变；再删一条减 1 且 `commenter_counts` 无该键。
   - ⑤ 非作者对 hidden 内容带正确 ETag 请求 R2 得 404，响应不含 ETag 头。
   - ⑥ 客户端：带非空 mentions（含 emoji 的 display_name）的 create 请求，Dart payload_hash 与 Python `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False)` 的 SHA-256 逐字相等。
   - ⑦ REST：把 `comment_page_with_reply_previews.json` 的 `visible_commenter_count` 改成 -1，check_examples 以该临时 manifest 退出 1。
   - ⑧ 服务端日志：对 W7 注入 Firestore 异常（monkeypatch `discussion_service.after_access_read_hook` 抛 `RuntimeError("正文泄漏测试")`），503 响应 detail 固定、caplog 不含该异常文本。
5. 作弊扫描：新测试无 `skip`/`xfail`/`skip:`、永真断言；参考值为字面量；T31～T34 确有线程与 Event/Barrier 且断言 hook 调用次数；K06/K07/K14 确为真实文件库关闭重开；客户端测试无真实 `HttpClient`/`http.Client()`。
6. 通过后：NC-011 `ACCEPTED`；NC-012（互动与 mention 深度校验）、NC-013（评论通知）可消费本任务的集合与 outbox 事件。
