# NC-014：Notification 宿主适配、去重与导航

状态：`PREPARING`（六件套与守卫草案就绪，待主 Agent 审查契约后转 `READY`）。task_id：`NC-014`。各仓 HEAD：PACKAGE（notification master）`518670b`、CLIENT（reading-notes main）`107ec90`、REST（repository-rest-adapter main）`b60bfbd`（只读）、SERVER（functions-py master）`992088e`（只读）。派发前置：NC-010、NC-013 均 `ACCEPTED`。

权威需求来源：`TASKS.md` NC-014（§226-234，范围权威）；专属契约 `openspec/annotation-community/contracts/community_notification_host.md`；API 引用 `community_api.md` §13；上游引用 `community_deliveries.md` §6/§7/§15。**执行者不做设计：端口 adapter 类名、Drift 表列、D.6 行为语义、双帧分派表、测试名、文案、决定 D-NC014-01～10 全部来自契约。**

## Goal

notification 包闭合 D.6（`timing.dedup_retention_ms` 可空解析 + `DedupRetention` 满窗即裁行为层 + barrel 导出，8 个新测试）；reading-notes 实现全部 8 个端口适配（`DeliveryLog`→Drift 持久去重表+业务 upsert 同事务、`RealtimeChannel`→SSE、`ReceiptTransport`→notifier /receipts、`ConnectionTokenSource`→notifier、`RemoteConfigSource`/`PushConfigCache`→L2/本地、`BackfillSource`→R10 空串哨兵、`MessageBodyFetcher`→R9 降级），双帧唤醒分派（notifier 帧 `type:push|resync` 走包内既有管线；community 帧 `type:community` 走业务 upsert+R10 补拉、不制造传输 ID、无来源 ACK），业务通知列表复用 social `NotificationCenterPage`（`event_count` 聚合计数、W15/W16 静音入口），导航（content 类→内容详情讨论区顶部、失权→统一文案「该内容已不可访问」占位页、账号切换 scope 分库）。落盘失败不 ACK、不推进 cursor 必须有失败 fake 分支证据；R10 补拉不产生传输 ID 或无来源 ACK。投递语义 at-least-once，红线词形（端到端恰好一次声称）零命中。

## Scope

- PACKAGE（act/01）：`lib/src/config/push_config.dart`（`_allowedKeys` + `dedupRetention` 只追加）、`lib/src/receive/dedup_store.dart`（`DedupRetention` 只追加）、`lib/notification.dart`（barrel 只追加）、`docs/from-server-coder.md`（仅 D.6 三处状态行）、`docs/integration-guide.md`（仅 §4 去重口径段）、`test/receive/dedup_retention_test.dart`（新增 8 测试）。
- CLIENT（act/02）：`pubspec.yaml`（追加 notification 与 social 两个 git 依赖）、`pubspec.lock`（pub get 自动）、`lib/src/notifications/community_notification_adapters.dart`（新增：8 adapter + Wiring + 三表 + MuteApi）、`lib/src/notifications/community_notification_adapters.g.dart`（生成）、`lib/src/notifications/notification_target_router.dart`（新增：Router + 占位页 + 列表页）、`test/notifications/community_notifications_test.dart`（新增 18 测试）。
- 禁止：上表以外任何文件（含 `lib/src/community/` 既有文件、notification 包既有测试与 pubspec、social 仓、REST/SERVER/NOTIFIER 全部）；装配遗留页（`notification_page.dart`/`notification_viewmodel.dart`/`playground_state_widgets.dart`）；`firebase_messaging` 等新插件依赖；在宿主复刻去重/ACK/退避/帧解码；`lib/` 出现 `604800000` 或 `Duration(days: 7)` 字面量；`skip`；永真断言；测试内现算参考值；红线词形；`git push`；删除文件。

## Dependencies / Baseline

| 线 | HEAD 基线 | 既有基线 |
|---|---|---|
| PACKAGE | `518670b` | `flutter test` `+194: All tests passed!`（README/integration-guide 的 189 口径过时，以 194 为准） |
| CLIENT | `107ec90` | `flutter test` `+296: All tests passed!`、`flutter analyze` `No issues found!` |
| REST/SERVER（只读） | `b60bfbd` / `992088e` | `dart test` `+81`；pytest `5 failed, 568 passed, 3 xfailed`（零写入，仅引用） |

共享守卫：`bash docs/blackbox-spec-rework/reviews/nc014_guard.sh --require-impl package|client|all`（在 learn_system 根执行）。

## Stop Conditions

- 契约参考值对不上：notification 默认分支未含 act/01 提交；social `NotificationCenterPage`/`SocialNotificationItem` 导出或构造签名与契约 §6.2 不符；L2 无 `timing.dedup_retention_ms` 键且装配停手路径被阻断。
- 既有测试变红（notification 194、reading-notes 296 之外新增任何失败）或 analyze 非 `No issues found!`。
- 需要修改白名单外文件、或契约存在歧义（含 §10.1 待裁决 1 的 comment 类导航行为被要求扩大）。
- Gitea（192.168.0.165:3000）不可达导致 pub get 失败。
- 处置：在本线交付报告追加「## 待裁决」小节说明原始输出，并单独输出一行 `NC-014-<A|B> 停手待裁决`；不改契约与既有测试，等主 Agent 裁定（裁定以 `D-NC014-<编号>` 登记于契约 §10 并同步六件套与守卫）。

## 执行顺序

PACKAGE（act/01）→ CLIENT（act/02）严格串行（CLIENT 的 pubspec git 依赖解析要求 notification 默认分支已含 act/01 提交）。每 act 一个独立提交；完成一个 act 即写本线 `DELIVERY_REPORT_<线>.md`（不入库）。

## 阅读顺序

1 本 README → 2 契约 `community_notification_host.md` 全文 → 3 `community_deliveries.md` §6、§7、§15 与 `community_api.md` §13 → 4 BDD/TDD → 5 ACT.yaml 与所属 act/*.yaml → 6 ACCEPTANCE.md → 7 PROMPT.md。
