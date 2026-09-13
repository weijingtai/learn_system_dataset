# NC-012a 独立验收

当前：**ACCEPTED**（2026-09-12 R1，见文末「验收记录 R1」）。派发前置：NC-003、NC-009、NC-010、NC-011、NC-016a ACCEPTED；wjt-react 四查 READY。

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

## 验收记录 R1（2026-09-12，主 Agent）

结论：**ACCEPTED**。执行方自述未采信，以下均为 git 与原始输出核对结果。

1. **ACT 审查**：`reviews/NC-012a-REVIEW-R1.md`（agy），R1 READY、返工 0 项；主 Agent 采纳建议 1～3（`0a2359b`）。执行中一次裁定 D-NC012-22（`7002996`）：REST 两条既有测试写死端点目录与示例数，只授权改这两处断言。
2. **范围**（`/usr/bin/git diff-tree -r --numstat`）：
   - REST `4671c92..cb686d0`：1 个提交、恰 7 个文件；测试文件 `-3` 行恰为 D-NC012-22 授权的目录行与示例数两行。
   - SERVER `0fad16e..8d22451`：2 个提交（`db52847` 7 个文件只增、`8d22451` 5 个文件），均在契约 §2.1 内；禁止清单零改动（守卫 K06）。`test_community_acl_sweep.py` 只改 import、E4 三项去 xfail、E4 分支体。
   - RULES `dd3445f..4b81d8d`：1 个提交、只改规则测试 +5 行。
   - CLIENT `d80703b..107ec90`：3 个提交（`e1655a4` 7 个文件、`59d5218` 4 个文件、`107ec90` 9 个文件），受保护路径零改动；`content_detail_page.dart` 在 `snapshotWrapper == null` 时原样展开三项、`discussion_panel.dart` 在 `commentDecorator == null` 时保持原 `Text`（主 Agent 读 diff 核对）。
3. **守卫**：`nc012a_guard.sh --require-impl all` 退出 0，K01～K07 全部 PASS（K05 manifest 17、dart test ≥77；K06 pytest `5/535/6` 且失败集合不变、规则 129、E4 转真；K07 MentionRef 单一、analyze 0、flutter test ≥296）。CLIENT 线另由主 Agent 单独复跑 `--require-impl client` 为 0。
4. **盲测**（`scratchpad/nc012a_blind/`，临时测试复制进仓运行后删除，三仓前后 `git status --short` 均为空）：
   - ① `random.Random(20260914)` 两账号 20 步：值变化次数 6/4，计数 `like=1, dislike=1` 与按 reaction 文档重建一致，两文档 `version` 等于各自变化次数。
   - ② 已撤销、从未存在、目标 hidden 三个 share_id 的 R4：状态 404、体与头（`Content-Length: 87`、`Content-Type: application/problem+json`）逐字节相同，等于共用体。
   - ③ 同一 command_id、同 body、If-Match 0 → 200，If-Match 1 → 409 `conflict.idempotency`。
   - ④ 乙撤销甲的链接 403 `forbidden.not_owner`；乙 R7 不含甲的链接；甲撤销 200 后乙 R4 为 404 共用体。
   - ⑤ `random.Random(20260915)` 300 组（118 组有保留、182 组全丢弃，含 emoji、国旗、组合字符、越界与负偏移）：Dart `reconcileMentions` 与 functions-py `filter_mentions` 保留下标逐行 `diff` 为空。
   - ⑥ 有状态假服务器，首个 PUT 挂起期间连续 `toggleReaction('like')` 10 次：PUT 恰 2 个，最终 `displayReaction == null`、确认版本 2，与服务器一致，`load()` 后不变。
   - ⑦ 去掉 `command` 的 `ReactionResponse` 副本登记为 valid，check_examples 报 `'command' is a required property` 并退出 1。
5. **作弊扫描**：SERVER 与 CLIENT 新测试无 `skip`、新增 `xfail`、永真断言、真实网络；§9 六个哈希、RID、BID、SCUR、两个 ETag 为字面量；I10 为 `threading.Barrier(10)` 且 503 同 ctx 重试上限 5 次、间隔按契约；J12/J13 以 `Completer` 挂起 `MockClient`；J05/J06/J22 为真实文件库关闭重开；J20 以 `tester.getSize` 断言 ≥ 48；ACL 扫描文件无 `owner: NC-012`；控制器 `refreshPending` 先取出再清空待发标志、412 不自动重发、`version >=` 防回滚（主 Agent 读源码核对）。

**遗留（非阻断）**：`test_community_acl_sweep.py` 模块文档字符串中 Implemented/Unimplemented 两行未按契约 §2.1 ③ 更新（仍写 E4 未实现），不影响断言，留待下次改动该文件时顺带修正。SERVER 线 act/02 交付报告经主 Agent 提醒后补写。

**推送**：四仓已推送 Gitea（REST 与 RULES 各合并远端 AGENTS.md 文档提交后推送：`3f34f0f`、`ca92902`；functions-py `8d22451`；reading-notes `107ec90` 为 Gitea 新仓首推）。
