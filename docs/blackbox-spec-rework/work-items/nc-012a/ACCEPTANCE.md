# NC-012a 独立验收

当前：未验收。派发前置：NC-003、NC-009、NC-010、NC-011、NC-016a ACCEPTED；wjt-react 四查 READY。

1. ACT 审查：未参与编写者做 wjt-react 四查（`reviews/NC-012a-REVIEW-R1.md`）。
2. 范围（`git diff-tree -r --name-only`，不用 `git diff`）：REST `4671c92` 之后恰 1 个提交、恰 7 个文件；SERVER `0fad16e` 之后恰 2 个提交、只含契约 §2.1 文件，禁止清单路径零改动，`test_community_acl_sweep.py` 的 diff 只涉及三处；RULES `dd3445f` 之后恰 1 个提交、只改规则测试；CLIENT `d80703b` 之后恰 3 个提交、只含契约 §2.2 文件，受保护路径零改动，`models.dart` 中不再有 `class MentionRef`，`reading_notes.dart` 不再含 `hide MentionRef`。
3. 重跑 TDD §1 全部命令（经 tmux 执行器只运行采集，主 Agent 读原始输出判定）；`nc012a_guard.sh --require-impl all` 为 0。
4. 主 Agent 盲测（临时文件，不入库，结束时删除并以 `git status --short` 为空证明）：
   - ① 计数可重建：两个账号对同一目标各自在 like、dislike、null 之间按 `random.Random(20260914)` 生成的 20 步序列提交（服务级 `run_command`，If-Match 取当前版本）；结束后计数文档的 like/dislike 等于按两份 reaction 文档 `value` 重建的值，两文档 `version` 等于各自值变化次数。
   - ② R4 不泄漏原因：对「已撤销」「从未存在」「目标 hidden」三个 share_id 的响应状态、体与头逐字节相同。
   - ③ If-Match 进入载荷哈希：同一 command_id、同 body、If-Match 分别为 0 与 1 的两次 W10，第二次 409 `conflict.idempotency`。
   - ④ 分享链接越权：乙对甲的 `shr_` 调 W13 → 403；乙的 R7 不含甲的链接；甲撤销后乙 R4 → 404 共用体。
   - ⑤ 客户端 mention 一致性：Python `random.Random(20260915)` 生成 300 组（文本含 emoji、CJK、组合字符与越界/负偏移）写入 scratch；临时 Dart 测试以 `reconcileMentions` 逐组输出保留下标，与 functions-py `filter_mentions` 结果逐行 `diff` 为空。
   - ⑥ 客户端快速连点：首个 PUT 挂起期间连续 `toggleReaction('like')` 10 次，放行后 PUT 总数 ≤ 2，最终 `displayReaction` 等于最后一次读取的服务器值。
   - ⑦ REST：把 `reaction_response_like.json` 去掉 `command` 键的副本登记为 valid 的临时 manifest，check_examples 退出 1。
5. 作弊扫描：新测试无 `skip`、新增 `xfail`、永真断言；参考值为字面量；I10 确有 `threading.Barrier(10)` 与重试上限；J12/J13 确以 `Completer` 挂起真实 `MockClient` 响应；J05/J15/J16/J22 确为真实文件库关闭重开；客户端测试无真实 `HttpClient`/`http.Client()`；ACL 扫描文件中不再出现 `owner: NC-012`。
6. 通过后：NC-012a `ACCEPTED`；NC-012b 仍 `BLOCKED`；NC-013 可消费 `reaction.liked` outbox 事件。
