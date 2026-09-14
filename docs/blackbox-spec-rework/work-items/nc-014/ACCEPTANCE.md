# NC-014 验收（主 Agent 独立执行，不采信执行方自述）

当前状态：`READY`（四查 `reviews/NC-014-REVIEW-R1.md` R1 REWORK 7 项已落实；实现交付后本文件追加「验收记录 R1」）。

1. ACT 审查：未参与编写、且不同厂商的审查者按 wjt-react 四查（忠实性、覆盖性、可执行性、独立性）判定 READY；返工不超过 2 轮；记录于 `reviews/NC-014-REVIEW-R1.md`。审查前置（**已满足**）：契约 `community_notification_host.md` 的 D-NC014-01～11 冻结裁定逐字核对；§10.1 的 comment 类 target 缺 content_id 已裁定为 D-NC014-11（本期不路由）。
2. 范围（`git diff-tree -r --name-only`，不用 `git diff`）：
   - notification `518670b..HEAD`：恰 6 个文件（push_config.dart、dedup_store.dart、barrel、from-server-coder.md、integration-guide.md、dedup_retention_test.dart）；`pubspec.yaml` 与既有 194 测试零改动。
   - reading-notes `107ec90..HEAD`：恰 6 个文件（pubspec.yaml、pubspec.lock、adapters、adapters.g.dart、router、测试）；`lib/src/community/` 零改动；无 `firebase_messaging`。
3. 重跑 TDD §1 全部命令：notification `flutter test` `+202: All tests passed!`；reading-notes `flutter analyze` `No issues found!`、单文件 `+18: All tests passed!`、全量 `+314: All tests passed!`；`nc014_guard.sh --require-impl all` 退出 0。
4. 主 Agent 盲测（临时文件不入库，结束删除并以两仓 `git status --short` 为空证明；清单=契约 §7 与下述七项）：① 同一 notification_id 两条 deliveryId 各自持久、ACK 批次含两 id 顺序原样；② 失败 fake 分支：`DeliveryPersistFailed` 注入后 ACK 缓冲空且 cursor 未推进（C06 原样复跑，检查 fake 不是永真 `DeliveryPersisted()`）；③ R10 页（聚合条目 event_count=3 + 独立 reply）落地恰 2 行、ACK 缓冲空、cursor 经 persistCursor 推进；④ `type:community` 帧（event_count 字符串 "2"）业务 upsert 单行、去重表零行；`type:push` 帧 → fetcher fake 收到 deliveryId；⑤ R9 fake 404 → 无 ACK、无去重行、点击仅打开内容；⑥ 四类失效 → 占位页文案逐字节一致且组件树无原因字段；⑦ 去重表满窗旧行被裁、窗口内行保留，`git grep 604800000 -- lib/` 在两仓均空。
5. 作弊扫描：无 `skip`、无永真断言；测试内无现算窗口（604800000 只出现在测试 fixture 的 L2 载荷）；`_receipts` 经 MockClient 真实拦截；无真实外部网络（真机链路归 NC-024）；红线词形（端到端恰好一次声称）在两仓新增文件与注释零命中；装配面无遗留页 import（`notification_page`/`notification_viewmodel`/`playground_state_widgets` 零命中）。
6. 通过后：NC-014 `ACCEPTED`；更新 `SUBAGENT_TODO.md`、本文件验收记录、推送两仓；NC-024（真机链路）与 comment 类导航待裁决项同步登记。

## 待裁决登记（执行中追加）

（空）
