# NC-014 执行提示（两线串行：PACKAGE act/01 → CLIENT act/02）

发送前提：工作包 `READY`（主 Agent 审查契约并四查通过）；本文件 `---` 分隔线以下每线一节，全文可直接发给对应执行 Agent。

---

## PACKAGE 线（NC-014-A）

你是 NC-014-A 执行者，只做 act/01。先读（按序）：`work-items/nc-014/README.md` → 契约 `contracts/community_notification_host.md` §1/§2.1/§4.1/§7.1/§10 → `community_deliveries.md` §6/§7/§15 → `BDD.md` P01～P08 → `TDD.md` §2 → `act/01.yaml` 全文。

开工前：`git -C D:/Programme/xuan/notification status --short` 必须为空、HEAD = `518670b`。命令默认超时一律放大到 ≥600 秒。

铁律：`lib/` 禁止出现 `604800000` 与 `Duration(days: 7)`（窗口只从 L2 `timing.dedup_retention_ms` 读，from-server-coder.md:274）；键缺失 → `dedupRetention == null` 无兜底值（D-NC014-10）；`dedupKeyOf`/`DedupStore`/`InMemoryDedupStore` 既有成员零改动；docs 只同步 D.6 三处状态行与 integration-guide §4 去重口径段；只允许写 act/01.yaml `WRITE_NEW` 的 6 个文件。

先写测试再改实现（TESTS_FIRST 顺序），Red 原文进交付报告。

遇到下列情况立即停止，不要自己决定：既有 194 个测试变红；D.6 语义与 from-server-coder §S6.1/§6 冲突；P04 扫描命中 lib/ 字面量；需改白名单外文件。处置：`DELIVERY_REPORT_PACKAGE.md` 追加「## 待裁决」并单独输出一行 `NC-014-A 停手待裁决`。

提交：单提交，消息 `feat(receive): D.6 去重保留窗口解析与裁剪（NC-014-A）`，末尾空一行加 `Co-Authored-By: GLM-5.3-Flash <noreply@z.ai>`。不推送。

交付报告：`DELIVERY_REPORT_PACKAGE.md`（不入库）写 commit、实际改动文件、测试原始摘要（`+202: All tests passed!`）、Red 原文、跳过项、剩余风险；完成输出一行 `NC-014-A 完成 <commit>`。

---

## CLIENT 线（NC-014-B，严格后于 act/01）

你是 NC-014-B 执行者，只做 act/02。先读（按序）：`work-items/nc-014/README.md` → 契约 `contracts/community_notification_host.md` 全文（§3 矩阵、§4 管线、§5 分派与导航、§6 列表与静音、§7.2 测试名、§10 决定） → `community_deliveries.md` §6/§7/§15 与 `community_api.md` §13 → `BDD.md` C01～C18 → `TDD.md` §3 → `act/02.yaml` 全文。

开工前：`git -C D:/Programme/xuan/reading-notes status --short` 必须为空、HEAD = `107ec90`；notification 默认分支已含 act/01 提交（`git -C D:/Programme/xuan/notification log --oneline -1` 对照交付报告），否则停手。

铁律：宿主只做端口 adapter、装配与导航，去重/ACK/退避/帧解码全在包内（不得复刻）；R10 条目 `deliveryId` 空串哨兵、不进 AckPipeline、无来源 ACK（D-NC014-03）；C06 必须是失败 fake 分支（TASKS:232 逐字：永远返回 `DeliveryPersisted()` 的 fake 不算通过）；占位页统一文案「该内容已不可访问」+ 返回按钮且无原因字段；comment 类条目点击暂不路由（D-NC014-11 冻结裁定，不得自行扩大）；不装配遗留页、不加 firebase_messaging；只允许写 act/02.yaml `WRITE_NEW` 的 6 个文件，`lib/src/community/` 零改动。

先写依赖与测试再实现（TESTS_FIRST 顺序），Red 原文进交付报告。

遇到下列情况立即停止：social `NotificationCenterPage`/`SocialNotificationItem` 导出或构造签名与契约 §6.2 不符；pub 解析冲突；既有 296 个测试变红或 analyze 非 `No issues found!`；需改白名单外文件；契约歧义。处置：`DELIVERY_REPORT_CLIENT.md` 追加「## 待裁决」并单独输出一行 `NC-014-B 停手待裁决`。

提交：单提交，消息 `feat(notifications): 通知八端口适配、业务通知列表与回跳导航（NC-014-B）`，末尾空一行加 `Co-Authored-By: GLM-5.3-Flash <noreply@z.ai>`。不推送。

交付报告：`DELIVERY_REPORT_CLIENT.md` 写 commit、实际改动文件、flutter test/analyze 原始摘要（`+314: All tests passed!`、`No issues found!`）、Red 原文、跳过项、剩余风险；完成输出一行 `NC-014-B 完成 <commit>`。
