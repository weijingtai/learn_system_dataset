# NC-013 验收（主 Agent 独立执行，不采信执行方自述）

当前状态：`PREPARING`（四查后转 `READY`；实现交付后本文件追加「验收记录 R1」）。

1. ACT 审查：未参与编写、且不同厂商的审查者按 wjt-react 四查（忠实性、覆盖性、可执行性、独立性）判定 READY；返工不超过 2 轮；记录于 `reviews/NC-013-REVIEW-R1.md`。
2. 范围（`/usr/bin/git diff-tree -r --name-only` 或 `git diff-tree`，不用 `git diff`）：
   - REST `dc0792c..HEAD`：恰 6 个文件（openapi.yaml、测试、3 示例、manifest）。
   - SERVER `8d22451..HEAD`：恰 7 个文件（config.py、conftest.py、notification_dispatch.py、community_deliveries.py、test_community_deliveries.py、test_community_acl_sweep.py、main.py）；`notifications.py`、`test_registration.py`、`test_main_exports.py`、`community_helpers.py`、`xuan/community/` 既有文件零改动。
   - RULES `4b81d8d..HEAD`：恰 1 个文件。
3. 重跑 TDD §1 全部命令：pytest `5 failed, 568 passed, 3 xfailed`（FAILED 恰为五个既有 ID）；rules `153 passed`；dart `+81`；`nc013_guard.sh --require-impl all` 退出 0。
4. 主 Agent 盲测（临时文件不入库，结束删除并以三仓 `git status --short` 为空证明；清单=契约 §14 七项）：① 并发 create-if-absent 恰 1 记录；② 退避边界 0.9/1.0/3.9/8.0s；③ R9 四种失败响应体逐字节相同；④ E 编码向量 3组；⑤ mention 绕静音 + like 零 FCM；⑥ 游标不回退；⑦ REST 示例翻转 → check_examples 退出 1。
5. 作弊扫描：无 `skip`、无新增 `xfail`（E6 三条删除除外）、无永真断言；3 组 `ntf_` 与共享 404 体为字面量；`_send_multicast` monkeypatch 真实拦截；并发用真实双事务；无真实外部网络（FCM 经 monkeypatch）；sweep 无 `owner: NC-013` 残留；文档与注释无 exactly-once 声称。
6. 通过后：NC-013 `ACCEPTED`；更新 `SUBAGENT_TODO.md`、本文件验收记录、推送四仓；handbook 按 PROTOCOL §4 登记（能力 ID 归属与领域回填需用户先裁定——reading-notes 尚无模块领域）；NC-014 解锁（其 TDD 依赖本任务端点）。

## 待裁决登记（执行中追加）

（空）

## 验收记录 R1（2026-09-13，主 Agent）

结论：**ACCEPTED**。执行方自述未采信，以下均为 git 与原始输出核对结果。

1. **ACT 审查**：`reviews/NC-013-REVIEW-R1.md`，四查 R1 REWORK（阻断 F1 计数族/F2 状态断言矛盾/F17 文件数，同轮 F3/F8/F9/F14）→ 返工 7 项落实（含 2 处必要派生：守卫 K03 计数串、K06 标签）→ R2 复核 8/8 PASS → **READY**。参考值 3 组 ntf_ 实机复算 MATCH、19 处文件:行抽查属实、三仓基线实跑复现。
2. **范围**（`git diff-tree -r --name-only`）：
   - REST `dc0792c..b60bfbd`：恰 6 文件（openapi.yaml、契约测试、3 示例、manifest）。
   - SERVER `8d22451..5800a23`：恰 4+3 提交，文件恰 7 个（config.py、conftest.py、notification_dispatch.py、community_deliveries.py、test_community_deliveries.py、test_community_acl_sweep.py、main.py）；`notifications.py`、`test_registration.py`、`test_main_exports.py`、`community_helpers.py`、`xuan/community/` 既有文件零改动（守卫 K06 protected_empty=True）。
   - RULES `4b81d8d..a354463`：恰 1 文件（基线偏差 `ca92902` 为 AGENTS.md 文档合并，按 D-NC013-16 先例认可，executor 停手纪律合规）。
   - 执行中停手上报 1 次：REST 线开工基线不符（AGENTS.md 前继 + 主 Agent 未提交的 validator Windows 适配）→ 裁定为 D-NC013-16（认可新基线，主 Agent 补提交 `dc0792c`）。
3. **守卫**：`nc013_guard.sh --require-impl all` 退出 0，K01～K07 全 PASS——K05 manifest 20、dart ≥81；K06 pytest `5 failed, 568 passed, 3 xfailed` 且 FAILED 集合恰为五个既有 ID、30 测试名、ntf_ 字面量、E6 转真、受保护路径零改动、三新文件 exactly-once 零命中；K07 rules `153 passed`。期间一次 K06 FAIL（docstring 含红线词）由主 Agent 裁定修正（`5800a23`，措辞不改语义）。
4. **盲测**（`scratchpad/nc013/blind-results.md`，981 行原始日志；临时文件已删除，三仓 `git status --short` 为空）：
   - ① 双线程 Barrier(2) 同 event/recipient：未捕获异常 0、最终记录恰 1（create-if-absent 生效）。
   - ② 退避边界：attempt=1..4 注入 +0.9/1.9/3.9/7.9s 四档均不到期；+1.0/2.0/4.0/8.0s 四档均到期（attempt_count 2/3/4/5），第 5 次失败即 abandoned。
   - ③ R9 四类失败（无绑定/非本人/评论已删/内容 withdrawn）六组两两逐字节相同，均为 `not_found.content` 共用体。
   - ④ E 编码 3 组独立复算 match=True。
   - ⑤ like 零 FCM 调用；静音内容 comment → abandoned(attempt 0)，mention → delivered（FCM 恰 1 次，data.notification_id 正确）。
   - ⑥ 游标不回退（插入更旧记录后同游标取页不变；event_count 2→3 属窗口内预期）；limit=101 → 400 invalid_argument.limit。
   - ⑦ REST manifest 翻转副本（去 next_cursor）→ check_examples EXIT=1 且报 required property；对照 EXIT=0；仓库 manifest 未触碰（check_examples 原生支持 argv[1]）。
5. **作弊扫描**：守卫 K06/K07 无 skip/新增 xfail/永真断言/真实网络；`_send_multicast` 真实 monkeypatch（盲测⑤）；并发为真实双事务（盲测①）；参考值字面量入测试（K06 ref_literals=True）；桥接映射生产写入维持缺证阻断（D-NC013-08），测试以 seed 模拟可信来源，未发现 Fake 映射宣称接通。
6. **交付物**：REST `b60bfbd`（已推送 Gitea）；SERVER `783fb0d`/`731ebfb`/`5800a23`；RULES `a354463`；learn_system `052e5e1`/`dd826e7`/本提交。执行者交付报告 3 份（SERVER 线因平台中断缺正式报告，以本记录的独立核验为准）。
7. **遗留（非阻断）**：①桥接映射上游扩展未提供（G2，已按 D-NC013-08 登记阻断，对应通知工作包 NC-014 客户端侧 ACK 链路不受影响）；②设备归属校验无设备注册表（G3）；③偏好过滤无社区事件源（G5）；④handbook 能力条目回写待用户裁定领域后执行。
