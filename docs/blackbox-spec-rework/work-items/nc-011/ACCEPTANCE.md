# NC-011 独立验收

当前：**ACCEPTED**（2026-09-12 R1，见文末「验收记录 R1」）。派发前置：NC-003、NC-009、NC-010 ACCEPTED（已满足）；wjt-react 四查 READY。

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

## 验收记录 R1（2026-09-12，主 Agent）

结论：**ACCEPTED**。执行方自述未采信，以下均为 git 与原始输出核对结果。

1. **ACT 审查**：`reviews/NC-011-REVIEW-R1.md`，R1 返工 4 项，R2 READY。执行中 §8 线程屏障改为确定性 `Aborted` 注入（§8.1，`5552e92`），T32/T33 的 503 归因更正为测试种子缺陷。
2. **范围**（`/usr/bin/git diff-tree -r --name-only`）：
   - REST `5730ed9..4671c92`：1 个提交，恰 6 个文件（openapi.yaml、契约测试、3 个示例、manifest）。
   - SERVER `df5c3da..0fad16e`：3 个提交（`7d1163c`、`b278e16`、`0fad16e`），8 个文件，均在契约 §2.1 内；禁止清单零改动（守卫 K06）。
   - RULES `ea8c9b8..dd3445f`：1 个提交，只改 `server/functions/test/community_rules.test.ts`。
   - CLIENT `4588f78..463835e`：2 个提交（`59cd50a`、`463835e`），10 个文件，受保护路径零改动（守卫 K07；终点取 NC-011-F 提交，排除其后 NC-017 提交）。
3. **守卫**：`nc011_guard.sh --require-impl all` 退出 0，K01～K07 全部 PASS。其中 K06 为 pytest `5/496/9` 且失败集合与基线一致、规则 89；K07 为 analyze 0、flutter test ≥239；K05 为 dart test ≥73。
4. **盲测**（tmux + cmd 会话 nc011v 只运行采集，原始输出在 `~/tmux-agents/runs/nc011v/`；第一轮因磁盘写满全部无效，清理后重跑）：
   - ①②③④⑤⑧ 服务端：`zz_nc011_blind_test.py` 6 passed，EXIT=0（V2）。
   - ⑥ 客户端：首跑为盲测文件自身缺陷（公开入口 `hide MentionRef`，未带前缀导入社区版）编译失败（V5）；主 Agent 修正导入后重跑 `+1: All tests passed!`，EXIT=0，payload_hash = `8166cf0b…24f8` 与 Python 逐字相等。
   - ⑦ REST：原示例 valid、`visible_commenter_count = -1` 副本被 `CommentPage` 拒绝（`-1 is less than the minimum of 0`），临时示例已删（V7）。判据说明：盲测脚本在临时 manifest 中把该副本登记为「应 invalid」，故期望 check_examples 退出 0；与本文第 15 行「登记为 valid 时退出 1」检验的是同一事实（schema 拒绝负计数）。
   - 并发稳定性：T31～T34 连跑 5 轮，每轮 `4 passed`、EXIT=0（V8_run1～5）。
   - 临时文件均已删除，SRV、RN、REST 三仓库 `git status --short` 为空（V3、V6、V7 与主 Agent 复核）。
5. **作弊扫描**：服务端、客户端、规则测试均无 `skip`/`xfail`/永真断言（`isTrue` 命中均为真实条件，`skipOffstage` 为 finder 参数）；T31/T34 以 monkeypatch `Transaction._commit` 注入并断言 `len(hook_calls)`；T33 为 `threading.Barrier(3)` 三线程；客户端测试无真实 `HttpClient`/`http.Client()`。

**遗留（不阻塞，移交 NC-012）**：reading-notes 存在两个同名 `MentionRef`（`src/domain/note_revision.dart` 与 `src/community/models.dart`，字段相同、序列化方法名不同），`reading_notes.dart` 以 `hide MentionRef` 隐藏社区版，宿主仅经公开入口时无法构造带 mentions 的 `CreateCommentRequest`。契约 §11.1 未考虑既有 domain 类，属规格遗漏；由 NC-012（@ 与 mention 深度校验）契约统一为单一类型。
