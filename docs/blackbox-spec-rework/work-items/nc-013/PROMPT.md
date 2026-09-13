# NC-013 执行提示（三线并行：REST act/01 ∥ SERVER act/02→03 ∥ RULES act/04）

发送前提：工作包 `READY`（四查通过）；本文件 `---` 分隔线以下每线一节，全文可直接发给对应执行 Agent。

---

## REST 线（NC-013-A）

你是 NC-013-A 执行者，只做 act/01。先读（按序）：`work-items/nc-013/README.md` → 契约 `contracts/community_deliveries.md` §6/§9/§10/§15 → `community_api.md` §2/§3.1/§4.1/§5.3/§6/§13 → `BDD.md` A01～A04 → `TDD.md` §2 → `act/01.yaml` 全文。

开工前：`git -C <REST 仓> status --short` 必须为空、HEAD = `cb686d0`（分叉即停手）。命令默认超时一律放大到 ≥600 秒。

先写测试再改实现（TESTS_FIRST 顺序），Red 原文进交付报告。只允许写 act/01.yaml `WRITE_NEW` 清单中的 6 个文件；其中既有测试文件只允许「末尾追加 4 个测试」与「两处既有断言同步（expectedCatalog 三行、seventeen ≥17）」，其他行禁改。

遇到下列情况立即停止，不要自己决定：参考值/示例对不上契约；既有测试变红（两处授权改动导致的预期红除外）；`validate_openapi` 报 ENV_BLOCKED；需改白名单外文件。处置：`DELIVERY_REPORT_REST.md` 追加「## 待裁决」并单独输出一行 `NC-013-A 停手待裁决`。

提交：单提交，消息 `feat(openapi): 通知正文拉取、补拉与按内容静音端点契约（NC-013-A）`，末尾空一行加 `Co-Authored-By: <执行模型> <厂商域>`。不推送。

交付报告：`DELIVERY_REPORT_REST.md`（不入库）写 commit、实际改动文件、测试原始摘要、Red 原文、跳过项、剩余风险；完成输出一行 `NC-013-A 完成 <commit>`。

---

## SERVER 线（NC-013-B → NC-013-C，同仓严格串行，同一执行者依次完成两 act）

你是 NC-013-B/C 执行者，先做 act/02 再做 act/03。先读（按序）：`work-items/nc-013/README.md` → 契约 `contracts/community_deliveries.md` 全文 → `BDD.md` S01～S32 → `TDD.md` §3/§4 → `act/02.yaml`、`act/03.yaml` 全文。

开工前：`git -C <SERVER 仓> status --short` 必须为空、HEAD = `8d22451`。Emulator `192.168.0.165:8080/9099` 必须可达，否则停手。

铁律：ntf_ 参考值抄契约 §9 字面量，**禁止在测试内现算**；写操作全部在事务内、ntf_ 用 `tx.create()`（create-if-absent，AlreadyExists 视为成功）；`xuan/handlers/notifications.py`、`tests/test_registration.py`、`tests/test_main_exports.py`、`tests/community_helpers.py` 一律只读；`main.py` 只在 act/03 追加注册；注释不得声称 exactly-once。

先写测试再实现（每 act 各自 TESTS_FIRST），Red 原文进交付报告。act/02 白名单 4 个文件；act/03 白名单 4 个文件（含 sweep 的 E6 限定改动）。两 act 各一个独立提交。

遇到下列情况立即停止：参考值对不上；既有 5 个 FAILED 之外新增失败；E6 转真导致其他 15 例变红；需改白名单外文件；契约歧义（如收件人矩阵边界）。处置：`DELIVERY_REPORT_SERVER.md` 追加「## 待裁决」并单独输出一行 `NC-013-B 停手待裁决` 或 `NC-013-C 停手待裁决`。

提交消息：act/02 `feat(community): outbox 消费、ntf_ 确定性通知记录与投递状态机（NC-013-B）`；act/03 `feat(community): 通知正文拉取、补拉、静音端点与 ACL E6 转真（NC-013-C）`；各末尾空一行加 Co-Authored-By。不推送。

交付报告：`DELIVERY_REPORT_SERVER.md`（每 act一节）写 commit、实际改动文件、pytest 原始摘要（全量 + FAILED 列表）、Red 原文、跳过项、剩余风险；每 act 完成输出一行 `NC-013-<B|C> 完成 <commit>`。

---

## RULES 线（NC-013-D）

你是 NC-013-D 执行者，只做 act/04。先读：`work-items/nc-013/README.md` → 契约 §2.2/§8/§15 → `BDD.md` R01～R03 → `TDD.md` §5 → `act/04.yaml` 全文。

开工前：`git -C <RULES 仓> status --short` 为空、HEAD = `4b81d8d`。

只允许写 `server/functions/test/community_rules.test.ts`（清单数组 + 三集合 describe 区追加）；`firestore.rules` 禁改（默认拒绝已覆盖）。先加用例跑 Red，再核对 153 passed。

停止条件：harness 报错无法归因于用例写法；既有 129 例变红。处置：`DELIVERY_REPORT_RULES.md`「## 待裁决」+ 输出 `NC-013-D 停手待裁决`。

提交：`test(rules): 通知三集合默认拒绝用例（NC-013-D）`，末尾空一行加 Co-Authored-By。不推送。

交付报告：`DELIVERY_REPORT_RULES.md` 写 commit、npm 原始摘要、完成输出一行 `NC-013-D 完成 <commit>`。
