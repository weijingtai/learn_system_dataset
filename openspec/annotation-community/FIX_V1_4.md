# 注解社区线 v1.3 → v1.4 一次性修复说明

日期：2026-09-10。适用对象：提交 `bc5f397` 的 PRD / DESIGN / PLANS / TASKS v1.3，以及 REVIEW_R1、REVIEW_R2_CHECKLIST。
编写依据：R3 复核（`17f81bb`）逐句通读 DESIGN §2～§7.4 与 TASKS NC-002～NC-019 后，汇总的**全部已知问题**。

## 0. 怎么用这份文件

- 这里列的是本线文档层**目前已知的全部问题**，共 18 条，不会再分轮追加。每条都写明错在哪、为什么错、改成什么。
- 每条修改都给出「原文」和「替换为」两段。**原文是逐字复制的，在目标文件里恰好出现一次**，直接搜索、整段替换即可，不要改动原文以外的文字，也不要自行改写替换文。
- 所有文件路径都相对于 `openspec/annotation-community/`。
- 按 FIX-01 到 FIX-18 的顺序执行。每条都只动自己的原文段落，互不覆盖。
- 本说明已经过验证：在文档副本上按顺序应用全部替换后，`review_final_guard.sh` 和 `verify.sh` 都是 0 失败。

## 1. 完成判定（执行方）

全部替换完成后，在仓库根目录运行下面三条命令，结果必须全部为 0：

```bash
bash openspec/annotation-community/review_final_guard.sh
```

```bash
bash openspec/annotation-community/verify.sh
```

```bash
git diff --check
```

三条都通过后提交，提交信息写 `docs: apply FIX_V1_4 to annotation-community v1.4`。第 4 节那项需要用户决定，**执行方不要改**。

## 2. 问题总表

| 编号 | 位置 | 问题一句话 | 严重度 |
|---|---|---|---|
| FIX-01 | DESIGN §6、NC-002、NC-012 | mention 偏移没有规定单位，Python 与 Dart 算出的 hash 不同 | 必须修 |
| FIX-02 | DESIGN §7.2、NC-004 | 修改说明在新编辑会话中的初值未定义，改动后又改回原文再保存，会不会建修订取决于实现 | 必须修 |
| FIX-03 | NC-010/011/012、PRD §3.1 | 客户端离线评论、收藏、举报等命令的恢复没有具名负责任务 | 必须修 |
| FIX-04 | DESIGN §2.1.1 | 对不存在的资源执行空操作时，applied_version 没有合法取值 | 必须修 |
| FIX-05 | DESIGN §7.2、NC-002 | 重复项先静默去重再算 hash，存储内容与 hash 不一致 | 必须修 |
| FIX-06 | DESIGN §2、§2.1.1 | 用上游不透明 ID 直接作 Firestore 文档 ID，可能写入失败 | 必须修 |
| FIX-07 | DESIGN §2.1、§6、NC-013、清单 | 业务通知前缀 `dlv_` 与上游 deliveryId 的测试替身前缀 `dlv-` 只差一个字符 | 必须修 |
| FIX-08 | DESIGN §7.3、§7.4 | 两个命令错误码不符合 `<类别>.<细节>` 命名规则 | 必须修 |
| FIX-09 | DESIGN §9.1 | 命令账本永久保留，却没有容量估算 | 必须修 |
| FIX-10 | REVIEW_R1 | 历史审查记录仍载有已废止规则，且被四份文档链接为「审查缺陷登记」 | 必须修 |
| FIX-11 | DESIGN §6.3 末段 | 残留旧句「HTTP→Outcome 映射在契约任务明确」，与 §6.2 矛盾 | 必须修 |
| FIX-12 | DESIGN §7 REST 表 | REST 表缺 purge 与 share.revoke，与 operation 目录不一致 | 必须修 |
| FIX-13 | DESIGN §2、§7、§7.4、NC-003 | 命令唯一键的粒度前后矛盾（按 operation 还是按「操作域」） | 必须修 |
| FIX-14 | DESIGN §2.2/§4.2/§4.3、PRD §6.2、NC-002/019 | 客户端待办值 `purge_pending` 与服务端生命周期同名；`purge_failed` 放错枚举；状态机数目写错 | 必须修 |
| FIX-15 | DESIGN §4.4/§7.3、NC-011 | 可读主题但不接受新评论时，没有对应的错误码 | 必须修 |
| FIX-16 | PLANS §8 | 验收顺序仍指向已过时的 R2 守卫 | 必须修 |
| FIX-17 | REVIEW_R2_CHECKLIST | 复核入口仍指向 v1.3 与 R2 守卫，会把后来的复核人带偏 | 必须修 |
| FIX-18 | 四份文档头部、PRD §9 | 版本号与变更记录 | 必须修 |

## 3. 逐条修复

### FIX-01　mention 偏移按 code point 计数

**错在哪**：DESIGN.md 第 228 行用 `markdown.substring(start, start+length)` 校验 mention，但全文没有规定 `start_offset` 与 `length` 用什么单位计数。

**为什么错**：v1.3 已把这两个字段同时放进 content_hash 投影（第 305 行）和数组排序键（第 309 行）。Dart 的 `String.substring` 按 UTF-16 码元计数，Python 的 `str` 切片按 code point 计数。只要 mention 前面出现 emoji 或 CJK 扩展 B 区汉字（术数古籍很常见），两端得出的偏移、排序和 hash 就不同，R2-04 要求的「Python/Dart 共用固定期望值」无法成立。§7.1 的评论长度已统一按 code point 计数，这里保持同一口径。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
保存时逐条校验 `markdown.substring(start, start+length) == "@" + display_name_at_creation`，
```

替换为：
```text
`start_offset` 与 `length` 一律以 Unicode code point 计数（与 §7.1 评论长度口径一致）：Python 直接按 `str` 下标取值，Dart 必须先把 `markdown.runes` 转为 code point 列表再截取，禁止直接使用按 UTF-16 码元计数的 `String.substring`。保存时逐条校验「从第 start_offset 个 code point 起、长 length 个 code point 的子串」`== "@" + display_name_at_creation`，
```

**替换 2**｜文件：`TASKS.md`

原文：
```text
保存时逐条校验子串是否仍等于 `"@" + display_name_at_creation`，
```

替换为：
```text
保存时按 code point 偏移（Design §6；Dart 经 `runes` 换算，禁止直接用 `String.substring` 截取）逐条校验子串是否仍等于 `"@" + display_name_at_creation`，
```

**替换 3**｜文件：`TASKS.md`

原文：
```text
对象键序/同步进度不改变 hash；恢复同文另建修订。
```

替换为：
```text
对象键序/同步进度不改变 hash；恢复同文另建修订。另含「mention 之前有一个 4 字节字符（如 `𠀀` U+20000）」用例：写明按 code point 计数的期望 start_offset、期望 canonical hex 与期望 hash，Python 与 Dart 必须得出同一字面值。
```

### FIX-02　修改说明的会话初值与去重规则

**错在哪**：DESIGN.md 第 311 行只写了 change_summary「默认空串，保存时原样保留」，没有规定新编辑会话开始时它取什么值。

**为什么错**：两种写法都说得通，但结果不同。若会话初值置空，而 head 的说明是 X，用户改动正文后又改回原文，普通保存按完整投影比较会得出不同 hash，误建一条内容相同的修订，违反同一行的「无内容/说明变化的自动保存仍不新增修订」和 R-04。若继承 X，新修订会带上前一次的说明。修法是：初值固定为空串，另用一个只存在于会话中的标记 `summary_touched` 判断用户是否真的改过说明。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
- change_summary 是可选的用户填写修改说明，默认空串，保存时原样保留，系统不得在每次自动保存时填入或更新该字段；
```

替换为：
```text
- change_summary 是可选的用户填写修改说明，系统不得在每次自动保存时填入或更新该字段。change_summary 在新编辑会话开始时的初值固定为空串（不继承 head 的说明，避免新修订带上前一次的说明），会话内另持有本地标记 `summary_touched`（初值 false，用户编辑说明框即置 true）。普通保存去重规则：若除 change_summary 外的投影与当前 head 完全相同，且 `summary_touched=false`，视为无变化、不新增修订；其余情况按完整投影 hash 比较。`summary_touched` 只存在于编辑会话，不进入 NoteRevision、snapshot 或 hash；
```

**替换 2**｜文件：`TASKS.md`

原文：
```text
普通保存以完整语义投影去重，显式恢复/合并不按 hash 折叠。
```

替换为：
```text
普通保存以完整语义投影去重，显式恢复/合并不按 hash 折叠。按 Design §7.2 的 `summary_touched` 规则补三条用例：① head 说明为 X，新会话改动正文后改回原文再保存 → 不新增修订；② 新会话只填写说明 Y → 新增修订且 change_summary=Y；③ 新会话改动正文、未碰说明 → 新增修订且 change_summary 为空串（不继承 X）。
```

### FIX-03　客户端命令队列的所有权

**错在哪**：TASKS.md 第 167 行 NC-010 的 RW-5 只写了「发布/更新/收回等公共操作」；NC-011 只有服务端 command_service，没有客户端恢复项；NC-012 的队列与 NC-010 是不是同一个也没说。

**为什么错**：DESIGN §2.1.1 目录里由客户端发起的 `comment.create/edit/delete`、`bookmark.set`、`share.create/revoke`、`report.create` 都没有具名负责任务，而离线发评论正是 R-16 最典型的场景。「等」字会让 NC-010 与 NC-011 的执行方都以为该由对方负责。修法：由 NC-010 建唯一的客户端命令队列，NC-011、NC-012 复用，并逐一点名各自负责的 operation。

**替换 1**｜文件：`TASKS.md`

原文：
```text
发布/更新/收回等公共操作先以账号隔离的 Drift 队列持久化 command_id、operation、payload_hash、请求与状态，再发送。
```

替换为：
```text
本任务新增 `CLIENT/lib/src/community/command_queue.dart`（账号隔离的 Drift 持久命令队列），它是客户端全部社区写命令的唯一队列。本任务负责 `content.publish/update/withdraw/trash/restore/purge` 的接入；`comment.create/edit/delete` 由 NC-011、`reaction.set`、`bookmark.set`、`share.create`、`share.revoke`、`report.create` 由 NC-012 复用同一队列，并按本条三项断言验收。操作先以该队列持久化 command_id、operation、payload_hash、请求与状态，再发送。
```

**替换 2**｜文件：`TASKS.md`

原文：
```text
- [ ] 新增 `SERVER/xuan/community/discussion_service.py`、`xuan/handlers/community_comments.py`、`tests/test_community_comments.py`；新增 `CLIENT/lib/src/community/discussion_controller.dart`、`discussion_panel.dart`、`test/community/discussion_test.dart`。
```

替换为：
```text
- [ ] 新增 `SERVER/xuan/community/discussion_service.py`、`xuan/handlers/community_comments.py`、`tests/test_community_comments.py`；新增 `CLIENT/lib/src/community/discussion_controller.dart`、`discussion_panel.dart`、`test/community/discussion_test.dart`。
- [ ] **客户端命令恢复**：`comment.create/edit/delete` 复用 NC-010 的 `command_queue.dart`，按 NC-010 RW-5 的三项断言验收：真实文件库关闭重开后以原键重试；响应丢失后调用命令查询端点对账，不新建评论；收到 410/503 时不换键重放。另测离线发表评论后重启 App：该评论在服务端只出现一次，讨论区与「待处理」队列中的「待发送」标记在服务端确认后同时消失。
```

**替换 3**｜文件：`TASKS.md`

原文：
```text
| NC-011 | 两级评论/回复与编辑删除 | NC-003, NC-009 | BACKLOG |
```

替换为：
```text
| NC-011 | 两级评论/回复与编辑删除 | NC-003, NC-009, NC-010 | BACKLOG |
```

**替换 4**｜文件：`TASKS.md`

原文：
```text
客户端持久串行队列、重启恢复和迟到版本防回滚均需实现。
```

替换为：
```text
客户端持久串行队列复用 NC-010 的 `command_queue.dart`，重启恢复和迟到版本防回滚均需实现；`bookmark.set`、`share.create`、`share.revoke`、`report.create` 同样经该队列发送，并按 NC-010 RW-5 的三项断言验收。
```

**替换 5**｜文件：`PRD.md`

原文：
```text
| R-16 | NC-010, NC-014 |
```

替换为：
```text
| R-16 | NC-010, NC-011, NC-012, NC-014 |
```

### FIX-04　applied_version 在空操作时的取值

**错在哪**：DESIGN.md 第 89 行规定 applied_version「不能以 0 冒充已提交版本」，null 只留给拒绝与无版本资源。

**为什么错**：DESIGN §4.4 规定不存在的状态读作 `version=0`，且「相同值不增版本」。对从未点过赞的目标提交 `reaction.set(null, If-Match: 0)`，是一次已提交（committed）的空操作：填 0 被禁止，填 null 又只允许用于拒绝，两种取值都不合法，NC-002 的 Schema 写不出来。修法：把 applied_version 定义为命令执行后该资源的服务器版本。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
applied_version 为非负安全整数或 null（拒绝及无版本资源允许 null），不能以 0 冒充已提交版本。
```

替换为：
```text
applied_version 为命令执行后该资源的服务器版本：committed 时为非负安全整数——值有变化时为递增后的版本，无变化的空操作时为执行时的当前版本（资源不存在时为 0，例如对从未点过赞的目标提交 `reaction.set(null, If-Match: 0)`，得到 committed 且 applied_version=0）；rejected 及无版本资源为 null。
```

### FIX-05　重复项改为拒绝，不做静默去重

**错在哪**：DESIGN.md 第 310 行写「完全相同项去重后编码」。

**为什么错**：hash 按去重后的数组计算，而修订存储的仍可能是带重复项的原数组，同一条修订的存储内容与 hash 投影不一致；两个带不同数量重复项的修订还会得到相同 hash。三个顶层数组都是引用集合，重复项本身没有语义，应当在保存前直接拒绝。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
完全相同项去重后编码。
```

替换为：
```text
完全相同的重复项视为非法输入，由 NC-002 Schema 在保存前拒绝（本地保存进入 `save_failed`，HTTP 返回 400 `invalid_argument.<数组名>`），不做静默去重，保证存储的修订与 hash 投影一致；编辑器插入已存在的附件时复用原条目，不追加重复项。
```

**替换 2**｜文件：`TASKS.md`

原文：
```text
三类顶层引用集合规范排序/去重后数组换序 hash 不变；
```

替换为：
```text
三类顶层引用集合规范排序后数组换序 hash 不变，完全相同的重复项被 Schema 拒绝（需负例 fixture）；
```

### FIX-06　桥接记录的 Firestore 文档 ID

**错在哪**：DESIGN.md 第 87 行写「键为原始 notifier_delivery_id」，第 53 行写「notifier_delivery_id 唯一且原样保存」。

**为什么错**：notifier 契约（`xuan-server/notifier/api/openapi.yaml`）只规定 deliveryId 是不透明的 HMAC 值，没有约束字符集和长度。Firestore 文档 ID 不得含 `/`、不得为 `.` 或 `..`、不得超过 1500 字节，原值直接作文档 ID 可能写入失败。原值必须逐字保留以供 ACK 使用，所以只改文档 ID，不改原值。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
NotifierDeliveryBinding 没有新增本地 ID 前缀，键为原始 notifier_delivery_id。
```

替换为：
```text
NotifierDeliveryBinding 不新增业务 ID 前缀；其 Firestore 文档 ID 固定为 `SHA256_hex(UTF8(notifier_delivery_id))`（64 位小写 hex），原始 notifier_delivery_id 作为字段逐字保存，并用于 ACK 与正文端点。原因：notifier 契约只规定该值不透明，未约束字符集与长度，而 Firestore 文档 ID 不得含 `/`、不得为 `.` 或 `..`、不得超过 1500 字节。
```

**替换 2**｜文件：`DESIGN.md`

原文：
```text
notifier_delivery_id 唯一且原样保存；
```

替换为：
```text
notifier_delivery_id 唯一且作为字段原样保存，文档 ID 为其 SHA-256 hex（§2.1.1）；
```

### FIX-07　业务通知前缀 `dlv_` 改为 `ntf_`

**错在哪**：DESIGN §2.1 把本系统业务 NotificationRecord 的前缀定为 `dlv_`（delivery）。

**为什么错**：上游 notifier 的测试替身生成的 deliveryId 形如 `dlv-reopen-%d`、`dlv-replay-%d`（`xuan-server/notifier/internal/store/memory/memory.go:434`、`:470`，`internal/testutil/fakes.go:441`、`:475`），与 `dlv_` 只差一个字符。R2-01 的核心要求正是「业务通知 ID 与 notifier deliveryId 绝不能混用」，名字相近会直接诱发这个错误。§2.1 的前缀表本来就在等用户确认，现在改名没有迁移成本。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
| NotificationRecord（仅业务记录） | `dlv_` | `dlv_<32 hex>`；绝不是 notifier deliveryId |
```

替换为：
```text
| NotificationRecord（仅业务记录） | `ntf_` | `ntf_<32 hex>`；绝不是 notifier deliveryId |
```

**替换 2**｜文件：`DESIGN.md`

原文：
```text
`"dlv_" + SHA256_hex(E([event_id, recipient_id]))[:32]`
```

替换为：
```text
`"ntf_" + SHA256_hex(E([event_id, recipient_id]))[:32]`
```

**替换 3**｜文件：`DESIGN.md`

原文：
```text
`notification_id`（本系统 dlv_）
```

替换为：
```text
`notification_id`（本系统 ntf_）
```

**替换 4**｜文件：`TASKS.md`

原文：
```text
确定性生成 dlv_ ID
```

替换为：
```text
确定性生成 ntf_ ID
```

**替换 5**｜文件：`REVIEW_R2_CHECKLIST.md`

原文：
```text
不能用 dlv_ 替代
```

替换为：
```text
不能用 ntf_ 替代
```

### FIX-08　命令错误码统一为 `<类别>.<细节>`

**错在哪**：DESIGN §7.3 第 343、344 行新增的 `command.result_expired`、`command.status_unavailable`，以及 §7.4 第 367 行的同名引用。

**为什么错**：错误目录中其余 code 都是「类别在前」：`not_found.*`、`conflict.*`、`too_large.*`、`invalid_argument.*`，类别与 HTTP 语义对应，客户端可以先按前缀分支。`command.` 是资源名而不是类别，破坏了这条规则。按 HTTP 语义，410 归入 `gone`，503 归入 `unavailable`。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
`command.result_expired`
```

替换为：
```text
`gone.command_result`
```

**替换 2**｜文件：`DESIGN.md`

原文：
```text
`command.status_unavailable`
```

替换为：
```text
`unavailable.command_status`
```

**替换 3**｜文件：`DESIGN.md`

原文：
```text
410 command.result_expired
```

替换为：
```text
410 gone.command_result
```

**替换 4**｜文件：`DESIGN.md`

原文：
```text
503 command.status_unavailable
```

替换为：
```text
503 unavailable.command_status
```

### FIX-09　补命令账本容量估算

**错在哪**：DESIGN §7.4 第 367 行规定最小命令账本「仅在关联账号永久销毁后清理」，但 §9.1 非功能指标里没有任何容量数字。

**为什么错**：赞踩、收藏等高频操作每次都会留下一条永久记录，存储只增不减，却没有人估算过规模和成本。按日均 50 条写命令、每条约 1 KiB 计算：50 × 365 = 18,250 KiB，约 18 MiB/账号/年；10 万账号约 1.7 TiB/年，且逐年累加。先把估算写进文档；是否改为有界保留，属于第 4 节中需要用户决定的事项。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
| 可用性 | 完整命令结果保留 14 天、去重身份持续保留（§7.4）；重试退避 1s/2s/4s/8s 上限 5 次；`429` 阈值由 NC-003 填实值后方可测 | NC-003/010 |
```

替换为：
```text
| 可用性 | 完整命令结果保留 14 天、去重身份持续保留（§7.4）；重试退避 1s/2s/4s/8s 上限 5 次；`429` 阈值由 NC-003 填实值后方可测 | NC-003/010 |
| 命令账本规模 | 单条最小账本 ≤ 1 KiB（含索引开销）；年增量 ≈ 日均写命令数 × 365 × 1 KiB。按日均 50 条估算约 18 MiB/账号/年，10 万账号约 1.7 TiB/年，且逐年累加不回收（§7.4 规定仅在账号销毁时清理）。NC-009 上线前须以真实埋点复核该估算并登记存储成本 | NC-009 |
```

### FIX-10　给 R1 历史记录加取代注记

**错在哪**：REVIEW_R1.md 的 §1.3 BT-05 仍记载 `client_seq` 单调判定，§1.4 TC-06 仍记载「幂等键 TTL 14 天」，而四份文档头部都把这个文件链接为「审查缺陷登记」。

**为什么错**：这两条规则已被 v1.2 的 R2 修订废止。执行方顺着链接读到这里，会把旧规则当作现行要求。历史正文不改，只在头部加注记。

**替换 1**｜文件：`REVIEW_R1.md`

原文：
```text
审查对象：[PRD](PRD.md) / [Design](DESIGN.md) / [Plans](PLANS.md) / [Tasks](TASKS.md) 的 v1.0。
```

替换为：
```text
审查对象：[PRD](PRD.md) / [Design](DESIGN.md) / [Plans](PLANS.md) / [Tasks](TASKS.md) 的 v1.0。

> **注意：本文件是 v1.0 的历史审查记录，不是现行规范。** §1.3 的 BT-05（`client_seq` 单调判定）、§1.4 的 TC-06（幂等键 TTL 14 天）等处置已被 v1.2 起的 R2 修订取代；现行规则一律以 PRD / DESIGN / PLANS / TASKS 最新版正文为准。
```

### FIX-11　删除 §6.3 末段与 §6.2 矛盾的旧句

**错在哪**：DESIGN.md 第 261 行写「`ReceiptRejected` 当前行为整批结束并报告，HTTP→Outcome 映射在契约任务明确」。

**为什么错**：这是 v1.0 留下的旧句。§6.2 第 243 行已写明该映射由 notifier 冻结，NC-013 不再承担。一处说「由契约任务明确」，另一处说「上游已冻结、本系统不定义」，执行方无法判断以哪处为准。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
`ReceiptRejected` 当前行为整批结束并报告，HTTP→Outcome 映射在契约任务明确；不能照抄相互矛盾的文档。
```

替换为：
```text
`ReceiptRejected` 按 §6.2 遵守 notifier 已冻结的口径：`/receipts` 整批原子，任一 id 失败则整批 4xx，调用方无法区分具体原因；客户端整批结束并报告、不拆批探测。本系统不另行定义其 HTTP 映射。
```

### FIX-12　REST 表补齐 purge 与 share.revoke

**错在哪**：DESIGN §7 REST 表第 273 行的 content 行没有 purge；第 277 行 share 行没有 revoke。

**为什么错**：§2.1.1 的 operation 目录登记了 `content.purge` 和 `share.revoke`，§4.3 也定义了 purge 的事务边界，但 NC-003 依据的 REST 表里没有这两个端点，OpenAPI 会漏写。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
| content publish/update/withdraw/trash/restore | ID、选定公共快照/资源、Idempotency-Key、更新时 If-Match |
```

替换为：
```text
| content publish/update/withdraw/trash/restore/purge | ID、选定公共快照/资源、Idempotency-Key（即 command_id）、更新时 If-Match |
```

**替换 2**｜文件：`DESIGN.md`

原文：
```text
| share create/resolve/report | 目标、原因（举报） |
```

替换为：
```text
| share create/revoke/resolve、report create | 目标、原因（举报）、command_id（create/revoke/report） |
```

### FIX-13　命令唯一键统一为 `(owner_scope, command_id)`

**错在哪**：DESIGN.md 第 52 行写 `(owner_scope, operation, command_id)` 唯一；第 285、364 行和 TASKS.md 第 87 行写「按操作域隔离」；第 368 行查询端点带 `?operation=<域>`。

**为什么错**：「operation」和「操作域」是两种粒度，各处写法互相冲突。若按 operation 隔离，客户端出错时把同一个 key 用在两个不同操作上，两个操作都会执行。payload_hash 本来就包含 operation，改为按账号唯一后，这种情况会以同键异载荷返回 409，保护更严，也不增加实现成本。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
(owner_scope, operation, command_id) 唯一；
```

替换为：
```text
(owner_scope, command_id) 唯一，operation 作为字段保存并纳入 payload_hash，同键不同 operation 按同键异载荷返回 409 conflict.idempotency；
```

**替换 2**｜文件：`DESIGN.md`

原文：
```text
按认证账号与操作域隔离；
```

替换为：
```text
按认证账号隔离（唯一键 `(owner_scope, command_id)`，见 §2.1.1）；
```

**替换 3**｜文件：`DESIGN.md`

原文：
```text
服务器作用域由认证账号和操作域推导；
```

替换为：
```text
服务器作用域由认证账号推导，operation 纳入 payload_hash；
```

**替换 4**｜文件：`DESIGN.md`

原文：
```text
`GET /v1/community/commands/{command_id}?operation=<域>`
```

替换为：
```text
`GET /v1/community/commands/{command_id}`（按认证账号查询，响应含 operation）
```

**替换 5**｜文件：`TASKS.md`

原文：
```text
command_id=Idempotency-Key、操作域、payload_hash
```

替换为：
```text
command_id=Idempotency-Key、唯一键 (owner_scope, command_id)、payload_hash（含 operation）
```

### FIX-14　拆分客户端待办与服务端清理任务状态

**错在哪**：
- DESIGN §4.2 第 179 行把 `pending_op` 定义为「服务端确认前」的客户端字段，取值中却有 `purge_pending`，与服务端 lifecycle 的 `purge_pending` 同名。
- DESIGN §4.3 第 193 行又用 `pending_op=purge_pending` 表示「服务端已登记、清理未完成」，并把服务端清理失败 `purge_failed` 放进客户端枚举。
- DESIGN §2.2 第 95 行写「六台状态机」，表里实际有八台；TASKS.md 第 74 行写「八台」。

**为什么错**：同一个值在客户端和服务端表示两件事，NC-002 的 `state-machines.md` 无法为它写出唯一的转移边，BDD 场景也分不清「请求已发出」与「清理进行中」。清理失败是服务端清理任务的状态，不是客户端待办。修法：客户端待办统一以 `_requested` 结尾，服务端清理进度另设 `PurgeTask.state`；加上这一台，状态机共九台。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
六台状态机的完整转移表
```

替换为：
```text
九台状态机的完整转移表
```

**替换 2**｜文件：`DESIGN.md`

原文：
```text
| 客户端待办 | `none / withdraw_pending / trash_pending / purge_pending / purge_failed` | §4 |
```

替换为：
```text
| 客户端待办 | `none / withdraw_requested / trash_requested / purge_requested` | §4.2 |
| 清理任务 | `queued / running / failed / succeeded`（PurgeTask.state，服务端） | §4.3 |
```

**替换 3**｜文件：`DESIGN.md`

原文：
```text
`withdraw / trash / purge` 在服务端确认前，客户端持有独立字段 `pending_op ∈ {none, withdraw_pending, trash_pending, purge_pending, purge_failed}`。
```

替换为：
```text
`withdraw / trash / purge` 命令在客户端已入队或已发送、服务端尚未确认时，客户端持有独立字段 `pending_op ∈ {none, withdraw_requested, trash_requested, purge_requested}`。取值刻意不与服务端 lifecycle 的 `purge_pending` 同名：`purge_requested` 表示客户端已发出彻底删除、服务端尚未确认；服务端确认后客户端清回 `none`，改以服务端 `lifecycle=purge_pending` 与清理任务 `PurgeTask.state` 展示进度。
```

**替换 4**｜文件：`DESIGN.md`

原文：
```text
服务端未确认前客户端 `pending_op=trash_pending`，显示「正在停止公开」
```

替换为：
```text
服务端未确认前客户端 `pending_op=trash_requested`，显示「正在停止公开，他人可能仍可访问」
```

**替换 5**｜文件：`DESIGN.md`

原文：
```text
lifecycle→purge_pending + 清理任务登记 |
```

替换为：
```text
lifecycle→purge_pending + 清理任务登记（`PurgeTask.state=queued`） |
```

**替换 6**｜文件：`DESIGN.md`

原文：
```text
| 未完成时 `pending_op=purge_pending`；失败为 `purge_failed` 并可重试。最小无正文 tombstone 防旧设备复活 |
```

替换为：
```text
| 客户端发出后、服务端确认前为 `pending_op=purge_requested`；服务端登记后为 `lifecycle=purge_pending`，清理进度看 `PurgeTask.state`（`queued/running/failed/succeeded`），`failed` 可重试，全部成功才 `lifecycle→purged`。最小无正文 tombstone 防旧设备复活 |
```

**替换 7**｜文件：`PRD.md`

原文：
```text
| purge_pending | 正在彻底清除 | 无 |
| purge 失败 | 清除未完成 · 点此重试 | 无 |
```

替换为：
```text
| lifecycle=purge_pending 且 PurgeTask.state 为 queued 或 running | 正在彻底清除 | 无 |
| lifecycle=purge_pending 且 PurgeTask.state=failed | 清除未完成 · 点此重试 | 无 |
```

**替换 8**｜文件：`TASKS.md`

原文：
```text
八台状态机（编辑态、发布态、生命周期、审核态、客户端 `pending_op`、投递态、导入态、锚点解析）
```

替换为：
```text
九台状态机（编辑态、发布态、生命周期、审核态、客户端 `pending_op`、清理任务 `PurgeTask.state`、投递态、导入态、锚点解析）
```

**替换 9**｜文件：`TASKS.md`

原文：
```text
purge_pending 仅表示任务已登记，实际对象清理完成前不显示 purged。
```

替换为：
```text
`pending_op=purge_requested` 表示客户端已发出、服务端未确认；服务端 `lifecycle=purge_pending` 仅表示清理任务已登记，`PurgeTask.state=succeeded` 之前不显示 purged。
```

**替换 10**｜文件：`TASKS.md`

原文：
```text
已公开离线删除时客户端 `pending_op=trash_pending`
```

替换为：
```text
已公开离线删除时客户端 `pending_op=trash_requested`
```

**替换 11**｜文件：`TASKS.md`

原文：
```text
`purge_failed` 可重试
```

替换为：
```text
`PurgeTask.state=failed` 可重试且重试不产生第二个清理任务
```

### FIX-15　新增「主题不接受新评论」错误码

**错在哪**：DESIGN §4.4 第 197 行对「收回先提交后的评论」一律返回 404；DESIGN.md 第 204 行禁止回复已删除的 root，但没有给出错误码；§7.3 也没有对应条目。

**为什么错**：§7.3 的边界规则是「调用方已被证明有读权限时用 403，否则 404」。作者本人对自己已收回或已进回收站的内容仍有读权限；任何人回复已删除 root 时，也能读到这个主题。这两种情况按规则都应返回 403，但目录里没有合适的 code，`forbidden.not_owner` 的语义不对，NC-011 的「禁止新回复」用例写不出期望值。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
| 非作者调用 withdraw/publish/trash | 403 | `forbidden.not_owner` | — |
```

替换为：
```text
| 非作者调用 withdraw/publish/trash | 403 | `forbidden.not_owner` | — |
| 调用方可读该主题，但主题已不接受新评论（作者本人评论自己已收回或在回收站的内容，或任何人回复已删除的 root 或目标） | 403 | `forbidden.thread_closed` | — |
```

**替换 2**｜文件：`DESIGN.md`

原文：
```text
收回先提交时，评论事务（含自动重跑）看到不可访问，返回 `404 not_found.content`，不写评论/事件。
```

替换为：
```text
收回先提交时，评论事务（含自动重跑）看到不可访问：非作者返回 `404 not_found.content`，作者本人返回 `403 forbidden.thread_closed`，两者都不写评论/事件。
```

**替换 3**｜文件：`TASKS.md`

原文：
```text
已有回复但禁止新回复
```

替换为：
```text
已有回复但禁止新回复（返回 403 `forbidden.thread_closed`）
```

### FIX-16　PLANS §8 的验收顺序指向总守卫

**错在哪**：PLANS.md 第 126 行写「验收顺序为 review_r2_guard.sh → verify.sh → 人工语义复核」。

**为什么错**：R2 守卫早已全绿，只按它验收会漏掉 R3 与本说明新增的检查项。

**替换 1**｜文件：`PLANS.md`

原文：
```text
验收顺序为 review_r2_guard.sh → verify.sh → 人工语义复核，脚本通过不等于业务验收。
```

替换为：
```text
v1.4 起验收顺序为 `review_final_guard.sh`（内含 R2、R3 守卫回归）→ `verify.sh` → 按 [一次性修复说明](FIX_V1_4.md) §5 的抽查点确认；脚本通过不等于业务验收。
```

### FIX-17　复核入口改指 v1.4 与总守卫

**错在哪**：REVIEW_R2_CHECKLIST.md 第 3 行仍写「复核 v1.3」，第 17 行的「本轮复核重点」仍指向 R2 结果报告与 `review_r2_guard.sh`。

**为什么错**：按它复核会得出「全绿」，但 R3 与本说明的问题都不在其检查范围内。

**替换 1**｜文件：`REVIEW_R2_CHECKLIST.md`

原文：
```text
请只读复核现有 PRD、DESIGN、PLANS、TASKS v1.3
```

替换为：
```text
请只读复核现有 PRD、DESIGN、PLANS、TASKS v1.4
```

**替换 2**｜文件：`REVIEW_R2_CHECKLIST.md`

原文：
```text
本轮复核重点：按 [独立复核报告 §4](REVIEW_R2_RESULT.md) 检查 RW-1～6；先运行 `bash openspec/annotation-community/review_r2_guard.sh`。同时确认顶层集合排序没有误排有序 selector、系统摘要不污染用户说明、备份与删除任务确实消费命令服务；已通过的 R2-01/02/05 做回归核对。
```

替换为：
```text
本轮复核重点（v1.4）：先运行 `bash openspec/annotation-community/review_final_guard.sh`（内含 R2、R3 守卫回归，必须 0 失败），再按 [一次性修复说明](FIX_V1_4.md) §5 的抽查点逐条确认。修复说明列出的是本线文档层全部已知问题，按其完成判定通过即结束文档复核。
```

### FIX-18　版本号与变更记录

**错在哪**：落实以上修改后，四份文档头部仍是 1.3，PRD §9 也没有对应的变更记录。

**为什么错**：PRD §9 要求每次变更都登记并回写 R 与 NC 编号；版本号不改，复核人无法确认看的是修复后的版本。

**替换 1**｜文件：`PRD.md`

原文：
```text
版本：1.3；日期：2026-09-10（R2 六项返工补全；待独立复核）。
```

替换为：
```text
版本：1.4；日期：2026-09-10（落实 FIX_V1_4 一次性修复说明；待抽查确认）。
```

**替换 2**｜文件：`DESIGN.md`

原文：
```text
版本：1.3；2026-09-10（R2 六项返工补全；待独立复核）。
```

替换为：
```text
版本：1.4；2026-09-10（落实 FIX_V1_4 一次性修复说明；待抽查确认）。
```

**替换 3**｜文件：`PLANS.md`

原文：
```text
版本：1.3；2026-09-10（R2 六项返工补全；待独立复核）。
```

替换为：
```text
版本：1.4；2026-09-10（落实 FIX_V1_4 一次性修复说明；待抽查确认）。
```

**替换 4**｜文件：`TASKS.md`

原文：
```text
版本：1.3；2026-09-10（R2 六项返工补全；待独立复核）。
```

替换为：
```text
版本：1.4；2026-09-10（落实 FIX_V1_4 一次性修复说明；待抽查确认）。
```

**替换 5**｜文件：`PRD.md`

原文：
```text
| 2026-09-10 | v1.3：RW-1～6
```

替换为：
```text
| 2026-09-10 | v1.4：落实 FIX_V1_4 全部 18 项——mention 偏移按 code point、修改说明会话初值与 summary_touched、客户端命令队列所有权、applied_version 空操作取值、重复项拒绝、桥接文档 ID、业务通知前缀改 ntf_、错误码命名、账本容量、客户端待办与清理任务状态拆分、thread_closed、REST 表与命令唯一键 | R-04、R-11、R-14、R-16、R-20 | [FIX_V1_4](FIX_V1_4.md) |
| 2026-09-10 | v1.3：RW-1～6
```

## 4. 需要用户决定（执行方不要改）

**命令账本是否改为有界保留。**（2026-09-10 已决定：维持永久保留，即下文方案 A；命令账本不作为数据分析的数据源，分析数据源见 [FIX_V1_5](FIX_V1_5.md) 新增的行为事件表。）

- **现状**：DESIGN §7.4 规定最小命令账本在账号销毁前永久保留。FIX-09 的估算约为 18 MiB/账号/年，且只增不减。
- **为什么不能直接定为有界**：`command_id` 用的是 UUIDv4，里面不含时间。服务端收到一个查不到记录的旧 key，无法区分它是从未执行过，还是已执行但账本被删了。一旦按时间清理，就可能把一条已经执行过的命令再执行一遍，这正是 §7.4 禁止的。
- **备选方案**：
  - **A. 维持现状**：永久保留，接受存储成本线性增长。
  - **B. 有界保留**：`command_id` 改为 UUIDv7（前 48 位是毫秒时间戳），账本只保留 400 天。服务端对内嵌时间早于 400 天前、或晚于当前时间 1 天以上的 key，直接返回 410 `gone.command_result` 且不执行，这样清理后也不会重复执行。代价是客户端需要大致准确的时钟，离线超过 400 天的待办会被拒绝，需要用户重新发起。
- **建议选 B**：它能把存储上限封死，而且离线超过 400 天的待办本来就应当让用户重新确认。
- **在用户决定之前**：按 v1.4 现行规则（永久保留、UUIDv4）实现，不得自行更改。

## 5. 修复后的抽查点（复核人）

总守卫是 0 失败之后，复核人只需确认下面几处的**内容**与本说明的替换文逐字一致，不再展开新一轮全文审查：

1. DESIGN §6 mention 段：写明 code point，且禁止 Dart 直接使用 `String.substring`。
2. DESIGN §7.2 change_summary 段：初值为空串，并有 `summary_touched` 规则；TASKS NC-004 有三条对应用例。
3. TASKS NC-010 RW-5：点名 `command_queue.dart`，并逐一列出各任务负责的 operation；NC-011 总表依赖含 NC-010。
4. DESIGN §2.2 表：客户端待办为 `_requested` 系列，并新增「清理任务」一行；PRD §6.2 清理两行改为按 `PurgeTask.state` 判断。
5. DESIGN §7.3：有 `forbidden.thread_closed`、`gone.command_result`、`unavailable.command_status` 三个 code，旧的 `command.*` 已消失。
6. DESIGN §2.1.1：唯一键为 `(owner_scope, command_id)`，桥接文档 ID 为 SHA-256 hex。
