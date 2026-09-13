# NC-013 验收（主 Agent 独立执行，不采信执行方自述）

当前状态：`PREPARING`（四查后转 `READY`；实现交付后本文件追加「验收记录 R1」）。

1. ACT 审查：未参与编写、且不同厂商的审查者按 wjt-react 四查（忠实性、覆盖性、可执行性、独立性）判定 READY；返工不超过 2 轮；记录于 `reviews/NC-013-REVIEW-R1.md`。
2. 范围（`/usr/bin/git diff-tree -r --name-only` 或 `git diff-tree`，不用 `git diff`）：
   - REST `cb686d0..HEAD`：恰 6 个文件（openapi.yaml、测试、3 示例、manifest）。
   - SERVER `8d22451..HEAD`：恰 7 个文件（config.py、conftest.py、notification_dispatch.py、community_deliveries.py、test_community_deliveries.py、test_community_acl_sweep.py、main.py）；`notifications.py`、`test_registration.py`、`test_main_exports.py`、`community_helpers.py`、`xuan/community/` 既有文件零改动。
   - RULES `4b81d8d..HEAD`：恰 1 个文件。
3. 重跑 TDD §1 全部命令：pytest `5 failed, 568 passed, 3 xfailed`（FAILED 恰为五个既有 ID）；rules `153 passed`；dart `+81`；`nc013_guard.sh --require-impl all` 退出 0。
4. 主 Agent 盲测（临时文件不入库，结束删除并以三仓 `git status --short` 为空证明；清单=契约 §14 七项）：① 并发 create-if-absent 恰 1 记录；② 退避边界 0.9/1.0/3.9/8.0s；③ R9 四种失败响应体逐字节相同；④ E 编码向量 3组；⑤ mention 绕静音 + like 零 FCM；⑥ 游标不回退；⑦ REST 示例翻转 → check_examples 退出 1。
5. 作弊扫描：无 `skip`、无新增 `xfail`（E6 三条删除除外）、无永真断言；3 组 `ntf_` 与共享 404 体为字面量；`_send_multicast` monkeypatch 真实拦截；并发用真实双事务；无真实外部网络（FCM 经 monkeypatch）；sweep 无 `owner: NC-013` 残留；文档与注释无 exactly-once 声称。
6. 通过后：NC-013 `ACCEPTED`；更新 `SUBAGENT_TODO.md`、本文件验收记录、推送四仓；handbook 按 PROTOCOL §4 登记（能力 ID 归属与领域回填需用户先裁定——reading-notes 尚无模块领域）；NC-014 解锁（其 TDD 依赖本任务端点）。

## 待裁决登记（执行中追加）

（空）
