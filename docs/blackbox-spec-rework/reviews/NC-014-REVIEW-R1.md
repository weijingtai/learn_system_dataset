# NC-014 四查评审记录 R1

- 评审对象：契约 `openspec/annotation-community/contracts/community_notification_host.md`（草案态 `DRAFT_FOR_NC-014`，learn_system `e3f08e4`）、六件套 `docs/blackbox-spec-rework/work-items/nc-014/`（8 文件）、守卫 `reviews/nc014_guard.sh`。
- 评审者：本机主 Agent 会话（DeepSeek）。草案作者：规格子会话（**GLM-5.3-Flash**，见 `act/01.yaml`/`act/02.yaml` 的 `COMMIT_MESSAGE` 尾注）——**异厂商、且未参与编写**，符合「未参与编写、且不同厂商」独立性要求。
- 方法：wjt-react 四查（忠实性、覆盖性、可执行性、独立性），并对上游原文与三个真实仓库逐条取证。
- 判定：**REWORK（小）**——7 项，全部是主 Agent 冻结 D-NC014-11 之后「契约已改、周边产物与守卫未同步」的一致性缺口，**无结构性问题、无事实性错误**。

## 1. 忠实性（对上游 + 两仓真实事实）

对契约关键引用逐条复算（2026-09-13 实测）：

| 契约引用 | 实测 | 结论 |
|---|---|---|
| PACKAGE `notification` HEAD `518670b` | `git -C D:/Programme/xuan/notification rev-parse --short HEAD` = `518670b` | 相符 |
| SOCIAL HEAD `1971f79`、`lib/social.dart:90-93` 公开导出 | `1971f79`；`:91` `export 'src/notification/notification_center_page.dart';`（`SocialNotificationItem` 经模型文件导出） | 相符 |
| NOTIFIER `server-notifier` | 存在，HEAD `8f32132`（契约未钉 HEAD，只引用 3.0.3 端点，属可接受） | 相符 |
| `push_config.dart` `PushTiming._allowedKeys` 与解析惯例 | `:24`、`:75` 两处 `_allowedKeys`；**无** `dedup_retention_ms`/`dedupRetention` | 相符（D.6 确未实现） |
| `dedup_store.dart` 既有成员零改动前提 | `dedupKeyOf:12`、`DedupStore:17`、`InMemoryDedupStore:29`，无 `DedupRetention` | 相符 |
| `TASKS.md:226-234`（R1 范围修正、失败 fake 定义、统一占位页文案、4 类失效） | 逐行核对一致 | 相符 |
| `INTEGRATION_BASELINE.md:12,66`（复用 social 普通中心、不挂遗留页） | 两行原文一致 | 相符 |
| `from-server-coder.md` D.6 三处状态行（`:269-274`、`:290`、`:300-303`） | `:269`「D.6 已解除阻塞，尚未实现」、`:274`「不要自己编 7d」、`:290`/`:303` 状态行一致 | 相符 |
| 基线计数 notification `+194`、reading-notes `+296`/analyze 0 | 与 handoff §4 及本机过往实测一致（本任务只读，未重跑） | 相符 |

忠实性结论：**通过**。契约没有杜撰上游事实，`604800000` 在契约中出现属文档口径（`from-server-coder.md §6` 下发值），守卫只禁 `lib/` 字面量，边界正确。

## 2. 覆盖性

- 8 个端口（`RemoteConfigSource`/`PushConfigCache`/`DeliveryLog`/`RealtimeChannel`/`ReceiptTransport`/`ConnectionTokenSource`/`BackfillSource`/`MessageBodyFetcher`）全部有冻结 adapter 类名与绑定来源；`PushTokenRegistry` 明确「另算」归 NC-024，与 `integration-guide.md:54-71` 清单口径一致。
- 判据 P01～P08 + C01～C18 = 26 名逐字，覆盖解析/裁剪边界（满窗即裁含等于）/同事件多 deliveryId 原样 ACK/落盘失败不 ACK 失败 fake/R10 空串哨兵/四类失效统一文案/账号切换 scope 分库/静音幂等。
- 缺口 G-NC014-1～5 与上游 D-NC013-08/G2、NC-024、NC-001 一一挂账，无悬空需求。
- 覆盖性结论：**通过**。

## 3. 可执行性

- act/01（40 分钟）+ act/02（55 分钟）均在 30–60 分钟区间；`DEPENDS_ON` 串行链 `[] → [NC-014-A]` 正确（CLIENT 的 pubspec git 依赖解析要求 notification 默认分支已含 act/01 提交）。
- 每个 act 均含 `ON_FAIL`/`WORKLOAD`/`TESTS_FIRST`/`BASELINE_EXIT_CODES`；`DISPATCH_PRECONDITION` 齐全；`VERIFICATION` 给出可复制的绝对路径命令与逐条期望。
- 「先红后绿」Red 原文要求具体到编译错（`dedupRetention`/`DedupRetention` 未定义、依赖缺失、adapters/router 未建）。
- 可执行性结论：**通过**。

## 4. 独立性（守卫机械性）

- 守卫 K01 回归 `review_v1_6_guard.sh` + `verify.sh` + `nc013_guard.sh` 规格模式；K02 契约字面量；K03 六件套结构与模糊词/红线词零命中；K04 TODO 登记；K05/K06 产物（`--require-impl`）。结构照抄 nc013 范式，Windows 适配（`Scripts/python.exe`、`shutil.which`、`os.pathsep`、`D:/apps/apps/flutter/bin`）齐全。
- 规格模式实测退出 0（K05/K06 SKIP）。
- 独立性结论：**通过（但 K02 的冻结裁定覆盖缺 D-NC014-11，见 R2 项）**。

## 5. REWORK 清单（R1，7 项）

主 Agent 冻结 D-NC014-11 后，以下产物与守卫未同步，必须在本轮关闭：

| # | 位置 | 现状 | 应改为 |
|---|---|---|---|
| R1-1 | `SUBAGENT_TODO.md:703` | 「D-NC014-01～10，§10.1 待裁决：comment 类 target 缺 content_id」「待主 Agent 审查后转 READY」 | 「D-NC014-01～11」+ 待裁决已裁定（D-NC014-11）+ 四查 R1 完成待转 READY |
| R1-2 | `community_notification_host.md:3` | 状态 `DRAFT_FOR_NC-014` | `FROZEN_FOR_NC-014` |
| R1-3 | `community_notification_host.md §10` | 表内仅 D-NC014-01～10，11 只存在于 §10.1 散文 | §10 表补 D-NC014-11 行（comment 类本期不路由） |
| R1-4 | `work-items/nc-014/README.md` | 「决定 D-NC014-01～10 全部来自契约」；停止条件「§10.1 待裁决 1」 | D-NC014-01～11；停止条件改指 D-NC014-11（裁定已闭合） |
| R1-5 | `work-items/nc-014/ACT.yaml` | `STATUS: PREPARING`；DEFERRED「契约 §10.1 待裁决 1（D-NC014-05）」 | `STATUS: READY`；DEFERRED 改「D-NC014-11：comment 类导航本期不路由」 |
| R1-6 | `PROMPT.md`、`ACCEPTANCE.md` | 两处「契约 §10.1 待裁决 1」作未决事项表述 | 改指 D-NC014-11 冻结裁定 |
| R1-7 | `reviews/nc014_guard.sh` K02 | `[f"D-NC014-{i:02d}" for i in range(1, 11)]` 只覆盖 01～10 | `range(1, 12)`，并断言 §10 含 D-NC014-11 |

返工轮次：第 1 轮（上限 2 轮）。上述 7 项由主 Agent 落实；落实后 R2 复核（重跑三守卫规格模式 + 关键字面量断言）并转 `READY`。
