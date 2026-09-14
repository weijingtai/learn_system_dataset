# NC-014 验收（主 Agent 独立执行，不采信执行方自述）

当前状态：`ACCEPTED`（四查 `reviews/NC-014-REVIEW-R1.md` R1 REWORK 7 项已落实；验收记录 R1 见文末）。

1. ACT 审查：未参与编写、且不同厂商的审查者按 wjt-react 四查（忠实性、覆盖性、可执行性、独立性）判定 READY；返工不超过 2 轮；记录于 `reviews/NC-014-REVIEW-R1.md`。审查前置（**已满足**）：契约 `community_notification_host.md` 的 D-NC014-01～11 冻结裁定逐字核对；§10.1 的 comment 类 target 缺 content_id 已裁定为 D-NC014-11（本期不路由）。
2. 范围（`git diff-tree -r --name-only`，不用 `git diff`）：
   - notification `518670b..HEAD`：恰 6 个文件（push_config.dart、dedup_store.dart、barrel、from-server-coder.md、integration-guide.md、dedup_retention_test.dart）；`pubspec.yaml` 与既有 194 测试零改动。
   - reading-notes `107ec90..HEAD`：恰 7 个文件（pubspec.yaml、analysis_options.yaml、pubspec.lock、adapters、adapters.g.dart、router、测试）；`lib/src/community/` 零改动；无 `firebase_messaging`。
3. 重跑 TDD §1 全部命令：notification `flutter test` `+202: All tests passed!`；reading-notes `flutter analyze` `No issues found!`、单文件 `+18: All tests passed!`、全量 `+314: All tests passed!`；`nc014_guard.sh --require-impl all` 退出 0。
4. 主 Agent 盲测（临时文件不入库，结束删除并以两仓 `git status --short` 为空证明；清单=契约 §7 与下述七项）：① 同一 notification_id 两条 deliveryId 各自持久、ACK 批次含两 id 顺序原样；② 失败 fake 分支：`DeliveryPersistFailed` 注入后 ACK 缓冲空且 cursor 未推进（C06 原样复跑，检查 fake 不是永真 `DeliveryPersisted()`）；③ R10 页（聚合条目 event_count=3 + 独立 reply）落地恰 2 行、ACK 缓冲空、cursor 经 persistCursor 推进；④ `type:community` 帧（event_count 字符串 "2"）业务 upsert 单行、去重表零行；`type:push` 帧 → fetcher fake 收到 deliveryId；⑤ R9 fake 404 → 无 ACK、无去重行、点击仅打开内容；⑥ 四类失效 → 占位页文案逐字节一致且组件树无原因字段；⑦ 去重表满窗旧行被裁、窗口内行保留，`git grep 604800000 -- lib/` 在两仓均空。
5. 作弊扫描：无 `skip`、无永真断言；测试内无现算窗口（604800000 只出现在测试 fixture 的 L2 载荷）；`_receipts` 经 MockClient 真实拦截；无真实外部网络（真机链路归 NC-024）；红线词形（端到端恰好一次声称）在两仓新增文件与注释零命中；装配面无遗留页 import（`notification_page`/`notification_viewmodel`/`playground_state_widgets` 零命中）。
6. 通过后：NC-014 `ACCEPTED`；更新 `SUBAGENT_TODO.md`、本文件验收记录、推送两仓；NC-024（真机链路）与 comment 类导航待裁决项同步登记。

## 待裁决登记（执行中追加）

裁定全部落于契约 §10 决定表 D-NC014-12～17（本工作包作者接任主 Agent 后亲裁，理由与来源见契约）。

## 验收记录 R1（2026-09-13，buffy 主 Agent）

结论：**ACCEPTED**。

> ⚠ 独立性声明（据实登记）：本任务「实现」与「验收」由同一会话完成（act/02 由本会话编写，因用户明确指派「我直接实现」）。因此 §4 的「主 Agent 盲测」由**本会话独立重写探针**（不复用执行方 fixture、期望值按契约手算）补足，作弊扫描与范围核对以 git 与原始输出为准；若编排层要求异会话复验，建议对 act/02 追加一次盲测。

1. **ACT 审查**：`reviews/NC-014-REVIEW-R1.md`。四查 R1 判 **REWORK 7 项**（均为 D-NC014-11 裁定后「契约改了、周边未同步」：TODO/README/ACT/PROMPT/ACCEPTANCE 的「01～10」与「§10.1 待裁决」表述、§10 表缺 D-NC014-11 行、守卫 K02 覆盖面）→ 7 项落实 → R2 复核 K01～K04 全 PASS → **READY**。审查者与草案作者异厂商（草案 GLM-5.3-Flash，审查 DeepSeek）。契约引用逐条取证属实：notification `518670b`、social `1971f79`（`lib/social.dart:91` 导出 `NotificationCenterPage`）、`push_config.dart` 确无 `dedup_retention_ms`、`dedup_store.dart` 三个既有成员、`TASKS.md:226-234`、`INTEGRATION_BASELINE.md:12,66`、`from-server-coder.md` D.6 三处状态行。
2. **范围**（`git diff-tree -r --name-only --no-commit-id`，不用 `git diff`）：
   - notification `518670b..b62cd27`：**恰 6 文件**（`lib/src/config/push_config.dart`、`lib/src/receive/dedup_store.dart`、`lib/notification.dart`、`docs/from-server-coder.md`、`docs/integration-guide.md`、`test/receive/dedup_retention_test.dart`）；`pubspec.yaml` 与既有 194 测试零改动。
   - reading-notes `107ec90..19afe37`：**恰 7 文件**（`pubspec.yaml`、`pubspec.lock`、`analysis_options.yaml`（D-NC014-12 白名单 +1）、`lib/src/notifications/community_notification_adapters.dart`、`..._adapters.g.dart`、`lib/src/notifications/notification_target_router.dart`、`test/notifications/community_notifications_test.dart`）；`lib/src/community/` 零改动；无 `firebase_messaging`。
   - ⚠ 基线外干扰已核实并处理：`107ec90..HEAD` 的裸 diff 还含 `AGENTS.md`，经 `git show --stat 7f2f1f7` 证实来自**另一 agent 的 docs 提交**（`7f2f1f7 docs: 加入 xuan-handbook 台账与接入手册指针`，仅改 AGENTS.md 6 行），非 NC-014 产物；rebase 后守卫据此修严（`nc_changed_files`：文件集断言只统计主题含 `NC-014` 的提交，断言仍为**精确等于白名单**，不放宽）。
   - 执行期停手上报 1 次并裁定通过：D-NC014-13/14（业务表 NOT NULL 与 community 帧自相矛盾、`ContentDetailPage` 构造缺参）＋G-NC014-6/7/8 → 裁定为 D-NC014-13～17，实现在裁定后落地。
3. **守卫**：`nc014_guard.sh --require-impl all` **退出 0**，K01～K06 全 PASS——K01 回归（v1.6 守卫/verify.sh/nc013 规格模式均 0）；K02 契约字面量、26 测试名、D-NC014-01～17、十节、红线词形与模糊词零命中；K03 六件套结构（P01～P08/C01～C18、30–60 分钟、串行依赖链、COMMIT 尾注）；K04 TODO 登记；K05 PACKAGE 产物（文件集恰 7、8 测试名、`DedupRetention` 导出、`lib/` 无窗口字面量、`flutter test +202`）；K06 CLIENT 产物（文件集恰 7、18 测试名、双 git 依赖、无遗留页/FCM、`lib/src/community` 零改动、`flutter analyze` `No issues found!`、`flutter test +314`）。
4. **主 Agent 盲测**（临时探针 `reading-notes/test/notifications/zz_blind_nc014_probe_test.dart`，**已删除**，两仓 `git status --short` 为空）：
   - B1 满窗即裁含等于边界：窗口手算 `604800000ms`；`now−604800000ms` ⇒ 过期、`now−604799999ms` ⇒ 未过期；`cutoffOf(now) == now−604800000ms`；`seenAt` 晚于 `now`（时钟偏移）⇒ 未过期。
   - B2 L2 窗口缺失 ⇒ `DedupRetention.fromTiming` 返回 `null`（停手上报，不兜底）；下发 ⇒ `window.inMilliseconds == 604800000`。
   - B3 `PushConfig.parse`：`timing.dedup_retention_ms` 下发 ⇒ `Duration(milliseconds: 604800000)`；缺键 ⇒ `null`。
   - B4 `dedupKeyOf` 唯一入口取 `deliveryId`。
   - B5 同业务条目两条传输：`wasDuplicate` 均 `false`、业务表 1 行、去重表 2 行（去重键是传输 ID，业务条目按 `notification_id` 合并）。
   - B6 落盘失败 ⇒ `DeliveryPersistFailed`、ACK 批次空、`onDelivered` 空（cursor 未推进）。
   - B7 `type:community` 帧（`event_count` 字符串 `"2"`）⇒ 业务表恰 1 行且 `eventCount == 2`、去重表 0 行、ACK 批次空（⛔ 不制造传输 ID）。
   - B8 `type:push` 帧 ⇒ 正文经 `MessageBodyFetcher` 拉取（fetcher 收到该 `deliveryId`）。
   - B9 R10 补拉 ⇒ 页内条目落业务表 1 行、`backfill.calls > 0`、ACK 批次空（R10 无传输 ID）。
   - B10 占位页文案逐字节为 `该内容已不可访问`，组件树无 `not_found`/`withdrawn` 等可区分原因字段。
5. **作弊扫描**：两仓新增测试无 `skip:`/`skipTest`/`assert(true)`/新增 `xfail`；`604800000` 与 `Duration(days: 7)` 在两仓 `lib/` 均零命中（`git grep` 空）；`firebase_messaging` 零命中；`notification_page`/`notification_viewmodel`/`playground_state_widgets` 零命中；新增文件与注释无端到端恰好一次声称；`_notifier receipts` 经 `MockClient` 真实拦截、无真实外部网络（真机链路归 NC-024）。
6. **交付物**：notification `b62cd27`（已推送 Gitea `main`）；reading-notes `19afe37`（已推送 Gitea `main`，rebase 至 `7f2f1f7` 后）；learn_system 本提交；handbook `46d5b7a`（`integration/social.community-notification-dispatch.md` 补写 + `social.community-notification-dispatch`/`notification.client-runtime` 回写，`validate.py` P0=0）。
7. **遗留（非阻断）**：① comment 类 target 本期不路由（D-NC014-11 已登记为后续契约扩展候选，需 target 补 `content_id`）；② 真机 FCM/实时链路归 NC-024；③ actor 展示名无社区端点，列表不展示昵称（G-NC014-4）；④ handbook「done」条件③（openspec 归档）未核，两能力条目保持 `landed`。
