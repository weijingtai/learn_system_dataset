# NC-026 执行提示（四线并行：REST act/01 ∥ SERVER act/02→03 ∥ CLIENT act/04 ∥ RULES act/05）

发送前提：工作包 `READY`（四查通过）；本文件 `---` 分隔线以下每线一节，全文可直接发给对应执行 Agent。

---

## REST 线（NC-026-A）

你是 NC-026-A 执行者，只做 act/01。先读（按序）：`work-items/nc-026/README.md` → 契约 `contracts/community_behavior.md` §5/§9.3/§10/§14 → `community_api.md` §2/§3.1/§4.1/§5.3/§6/§14 → `BDD.md` A01～A04 → `TDD.md` §2 → `act/01.yaml` 全文。

开工前：`git -C <REST 仓> status --short` 必须为空、HEAD = `b60bfbd`（分叉即停手）。命令默认超时一律放大到 ≥600 秒。

先写测试再改实现（TESTS_FIRST 顺序），Red 原文进交付报告。只允许写 act/01.yaml `WRITE_NEW` 清单中的 5 个文件；其中既有测试文件只允许「末尾追加 4 个测试」与「两处既有断言同步（expectedCatalog 两行、twenty ≥20）」，其他行禁改。

遇到下列情况立即停止，不要自己决定：参考值/示例对不上契约；既有测试变红（两处授权改动导致的预期红除外）；`validate_openapi` 报 ENV_BLOCKED；需改白名单外文件。处置：`DELIVERY_REPORT_REST.md` 追加「## 待裁决」并单独输出一行 `NC-026-A 停手待裁决`。

提交：单提交，消息 `feat(openapi): 行为事件上报与假名交付端点契约（NC-026-A）`，末尾空一行加 `Co-Authored-By: <执行模型> <厂商域>`。不推送。

交付报告：`DELIVERY_REPORT_REST.md`（不入库）写 commit、实际改动文件、测试原始摘要、Red 原文、跳过项、剩余风险；完成输出一行 `NC-026-A 完成 <commit>`。

---

## SERVER 线（NC-026-B → NC-026-C，同仓严格串行，同一执行者依次完成两 act）

你是 NC-026-B/C 执行者，先做 act/02 再做 act/03。先读（按序）：`work-items/nc-026/README.md` → 契约 `community_behavior.md` 全文 → `BDD.md` S01～S26 → `TDD.md` §3/§4 → `act/02.yaml`、`act/03.yaml` 全文。

开工前：`git -C <SERVER 仓> status --short` 必须为空、HEAD = `992088e`。Emulator `192.168.0.165:8080/9099` 必须可达，否则停手。

铁律：`SCHEMA_SHA` 与 `bev_`/`note_ref` 参考值抄契约 §9 字面量，**禁止在测试内现算**；Schema 副本必须与 learn_system 规格侧文件逐字节相同；`command_service.py` 只在 Step 3.3 一处补六个外层字段；`content_service.py`、`discussion_service.py`、`interaction_service.py`、`access.py`、`ids.py`、`tests/test_community_interactions.py`、`tests/test_community_comments.py`、`tests/community_helpers.py` 一律零改动；`main.py` 只在 act/03 追加注册；注释不得声称 exactly-once。

先写测试再实现（每 act 各自 TESTS_FIRST），Red 原文进交付报告。act/02 白名单 4 个文件；act/03 白名单 7 个文件。两 act 各一个独立提交。

遇到下列情况立即停止：参考值对不上；既有 5 个 FAILED 之外新增失败；Schema SHA 比对不符；需改白名单外文件；契约歧义。处置：`DELIVERY_REPORT_SERVER.md` 追加「## 待裁决」并单独输出一行 `NC-026-B 停手待裁决` 或 `NC-026-C 停手待裁决`。

提交消息：act/02 `feat(community): 冻结行为事件 Schema 并补齐服务端事件外层字段（NC-026-B）`；act/03 `feat(community): 行为事件上报端点、假名交付与只追加固化（NC-026-C）`；各末尾空一行加 Co-Authored-By。不推送。

交付报告：`DELIVERY_REPORT_SERVER.md`（每 act 一节）写 commit、实际改动文件、pytest 原始摘要（全量 + FAILED 列表）、Red 原文、跳过项、剩余风险；每 act 完成输出一行 `NC-026-<B|C> 完成 <commit>`。

---

## CLIENT 线（NC-026-D）

你是 NC-026-D 执行者，只做 act/04。先读（按序）：`work-items/nc-026/README.md` → 契约 `community_behavior.md` §5/§6/§9.3 → `BDD.md` C01～C18 → `TDD.md` §5 → `act/04.yaml` 全文。

开工前：`git -C <CLIENT 仓> status --short` 为空、HEAD = `107ec90`。

只允许新建 `lib/src/analytics/private_note_metrics.dart` 与 `test/analytics/private_note_metrics_test.dart`；`note_database.dart`、`note_repository.dart`、`pubspec.yaml` 禁改（不新增依赖，不新建 Drift 表）。`note_ref` 与 `char_count` 的期望值抄契约 §9.3 与 `"a𠀀b"` → 3 字面量，禁止在测试内现算。

先写测试跑 Red（18 passed 目标，基线 +296），再核对 `flutter analyze` 0 与 `flutter test` `+314`。

停止条件：参考值对不上；既有 +296 变红；需要改白名单外文件。处置：`DELIVERY_REPORT_CLIENT.md`「## 待裁决」+ 输出 `NC-026-D 停手待裁决`。

提交：`feat(analytics): 私人笔记元数据上报队列与假名缓存（NC-026-D）`，末尾空一行加 Co-Authored-By。不推送。

交付报告：`DELIVERY_REPORT_CLIENT.md` 写 commit、flutter 原始摘要（analyze + test）、Red 原文、完成输出一行 `NC-026-D 完成 <commit>`。

---

## RULES 线（NC-026-E）

你是 NC-026-E 执行者，只做 act/05。先读：`work-items/nc-026/README.md` → 契约 §3.4/§7/§12.4 → `BDD.md` R01～R03 → `act/05.yaml` 全文。

开工前：`git -C <RULES 仓> status --short` 为空、HEAD = `a354463`。

只允许向 `server/functions/test/community_rules.test.ts` 末尾追加一个 `describe` 与 4 个用例（2 上下文 × update/delete）；`server/firestore.rules` 与 `COMMUNITY_COLLECTIONS` 清单数组禁改。先加用例跑 Red，再核对 `157 passed`。

停止条件：harness 报错无法归因于用例写法；既有 153 例变红；计数不等于 157。处置：`DELIVERY_REPORT_RULES.md`「## 待裁决」+ 输出 `NC-026-E 停手待裁决`。

提交：`test(rules): 行为事件只追加显式用例（NC-026-E）`，末尾空一行加 Co-Authored-By。不推送。

交付报告：`DELIVERY_REPORT_RULES.md` 写 commit、npm 原始摘要、完成输出一行 `NC-026-E 完成 <commit>`。

---

## 全线通用

- 不派发注销子项（DEFERRED，D-NC026-13）。
- 遇到参考值对不上、既有测试变红、需要扩大授权时**停手上报**，不改契约、不改既有测试。
- 禁止 `skip`、新增 `xfail`、永真断言、测试内现算参考值、真实外部网络、`git push`。
