# 注解社区线 v1.4 → v1.5 修订说明：行为事件数据源

日期：2026-09-10。适用对象：提交 `dab5970` 的 PRD / DESIGN / PLANS / TASKS v1.4，以及 verify.sh、review_final_guard.sh、REVIEW_R2_CHECKLIST、FIX_V1_4、SUBAGENT_TODO。

## 0. 为什么要改

未来要做数据统计与数据挖掘，数据源必须长期保留、不能被删。核查四份文档后发现，**分析数据源根本没有定义**：
- 业务数据只存**当前状态**，例如点赞表里只有最终值；
- 行为**过程**（点赞 → 取消 → 再点赞）只存在于事件里，而现有的 outbox 事件只用来发通知，发完保留多久没写；
- 全文没有任何关于埋点、数据分析、去标识化或账号注销的条款。

照 v1.4 实现，行为过程会随通知发送完成而丢失，以后也补不回来。

命令账本不能充当分析数据源：它只存操作编号、请求指纹、成功与否和资源 ID，按设计不含正文，回答不了"谁在什么时候做了什么"。

## 1. 用户已确认的决定（2026-09-10）

1. 新增行为事件表，作为统计与数据挖掘的永久数据源；**命令账本也维持永久保留**（DESIGN §7.4 现行规则不变）。
2. 私人笔记**默认上报**不含内容的元数据（保存次数、字数、编辑时长），需在隐私政策中写明。
3. 账号注销或本人彻底删除账号时，**删除假名映射，行为事件保留**。

## 2. 为使决定 3 真正生效而写死的规则

- **假名必须随机生成**，禁止由账号 ID 哈希或加密推导。否则删除映射后，拿账号 ID 重算一遍就能重新关联。
- **注销时，本系统业务数据中也不再保留该账号 ID**：本人公开内容与评论的作者字段改为统一的「已注销用户」，点赞、收藏、分享、通知、命令账本等以该账号为主体的记录删除。否则事件里的对象 ID（比如某条评论）一关联业务表，就能反查出作者，假名化失效。
- **私人笔记的元数据只报数字**，不报标题、正文、任何内容指纹、@ 的目标、注解的是哪一句，也不报 note_id 原值。

## 3. 执行方式与完成判定

- 所有路径都相对于 `openspec/annotation-community/`。每处修改都给出「原文」和「替换为」两段，原文逐字复制，在目标文件中恰好出现一次。按 V5-01 到 V5-11 的顺序整段替换，不要改动原文以外的文字，也不要自行改写替换文。
- 本说明已在保持相对路径的镜像目录中验证：按顺序应用全部替换后，`review_v1_5_guard.sh`（内含全部既有回归）与 `verify.sh` 均为 0 失败。
- **提交注意**：`../../docs/blackbox-spec-rework/SUBAGENT_TODO.md` 在工作区里另有其他 Agent 尚未提交的改动。提交时用 `git add -p` 只暂存本说明替换出的两处，不要把他人的改动一并提交。

全部替换完成后，在仓库根目录运行下面三条命令，结果必须全部为 0：

```bash
bash openspec/annotation-community/review_v1_5_guard.sh
```

```bash
bash openspec/annotation-community/verify.sh
```

```bash
git diff --check
```

提交信息写 `docs: add behavior event data source to annotation-community v1.5`。

## 4. 修改清单

| 编号 | 位置 | 内容 |
|---|---|---|
| V5-01 | PRD §3、§3.1、§7 | 新增 R-21 需求与断言点，划清本期范围 |
| V5-02 | DESIGN §2、§2.1 | 新增 BehaviorEvent、PseudonymMapping 模型行与 `bev_`、`psn_` 前缀 |
| V5-03 | DESIGN §4.3、§7.4 | 行为事件与业务记录同事务写入 |
| V5-04 | DESIGN §9、§9.1、§10 | 覆盖范围、容量估算、注销事件外部依赖 |
| V5-05 | DESIGN §11（新增） | 行为事件数据源的完整规则 |
| V5-06 | TASKS 头部、总表、§1.2、NC-001、NC-003、NC-024 | 登记 NC-026，补依赖、串行顺序与覆盖范围 |
| V5-07 | TASKS NC-026（新增） | 行为事件、假名化与私人笔记元数据的验收 |
| V5-08 | PLANS §1.2、§2、§7、§8 | 阶段、串行写入顺序、验收入口 |
| V5-09 | verify.sh、review_final_guard.sh | 接受 R-21 与 1.5 版本号，避免升版后误报 |
| V5-10 | REVIEW_R2_CHECKLIST、FIX_V1_4 §4、SUBAGENT_TODO | 复核入口、已决定标记、监控表登记 |
| V5-11 | 四份文档头部、PRD §9 | 版本号与变更记录 |

## 5. 逐条修改

### V5-01　PRD：新增 R-21

**替换 1**｜文件：`PRD.md`

原文：
```text
| R-20 | 隐私与审核一致性 | 私有/收回/隐藏内容不得经历史、附件、分享、关联索引或通知正文绕过权限；公开数据不回写官方知识 |
```

替换为：
```text
| R-20 | 隐私与审核一致性 | 私有/收回/隐藏内容不得经历史、附件、分享、关联索引或通知正文绕过权限；公开数据不回写官方知识 |
| R-21 | 行为事件数据源 | 社区与笔记的用户行为以只追加事件永久保存，作为未来统计与数据挖掘的数据源；事件不含标题、正文等任何内容，账号以随机假名表示；私人笔记默认上报不含内容的元数据（保存次数、字数、编辑时长），并在隐私政策写明；账号注销或本人彻底删除账号时删除假名映射、本系统业务数据去标识化，事件保留且无法再关联到人；本期只保证事件记全、存好，不做分析功能 |
```

**替换 2**｜文件：`PRD.md`

原文：
```text
| R-20 | NC-009（ACL 全入口扫描所有者） | 6 入口 × 3 失效原因 = 18 条，响应体不含正文子串 | NC-002, NC-003 |
```

替换为：
```text
| R-20 | NC-009（ACL 全入口扫描所有者） | 6 入口 × 3 失效原因 = 18 条，响应体不含正文子串 | NC-002, NC-003 |
| R-21 | NC-026 | 事件字段白名单与禁止字段负例、服务端事件与业务同事务、只追加（规则拒绝 update 与 delete）、注销后全库不再出现该 account_id 且事件条数不变、私人笔记上报原始字节不含内容 | NC-002, NC-003 |
```

**替换 3**｜文件：`PRD.md`

原文：
```text
命主反馈、应验、终局反馈、推荐算法、Embedding 和自动知识回写不属于本期。
```

替换为：
```text
命主反馈、应验、终局反馈、推荐算法、Embedding 和自动知识回写不属于本期；行为事件的采集与保存属于本期（R-21），基于事件的统计、挖掘与推荐不属于本期。
```

### V5-02　DESIGN：模型行与前缀

**替换 1**｜文件：`DESIGN.md`

原文：
```text
见 §6.2.1 |

内容 hash 按固定版本编码后
```

替换为：
```text
见 §6.2.1 |
| BehaviorEvent | event_id, schema_version, event_type, occurred_at, received_at, actor_pseudonym, object_type?, object_id?, note_ref?, platform, app_version, attributes | 只追加、永久保留、不含任何内容；禁止 update 与 delete；见 §11 |
| PseudonymMapping | account_id, actor_pseudonym, created_at | 一账号一假名；假名随机生成，不可由账号 ID 推导；账号注销时删除，行为事件保留；见 §11.3 |

内容 hash 按固定版本编码后
```

**替换 2**｜文件：`DESIGN.md`

原文：
```text
本期新增 15 类对象的前缀如下
```

替换为：
```text
本期新增 17 类对象的前缀如下
```

**替换 3**｜文件：`DESIGN.md`

原文：
```text
| NotificationRecord（仅业务记录） | `ntf_` | `ntf_<32 hex>`；绝不是 notifier deliveryId |
```

替换为：
```text
| NotificationRecord（仅业务记录） | `ntf_` | `ntf_<32 hex>`；绝不是 notifier deliveryId |
| BehaviorEvent | `bev_` | `bev_<32 hex>` |
| 行为假名（actor_pseudonym） | `psn_` | `psn_<32 hex>`，随机生成 |
```

### V5-03　DESIGN：行为事件与业务同事务

**为什么**：事件若在事务外另写，业务成功而事件丢失、或事件存在而业务回滚，统计数据就会与真实业务不一致，且无法事后对账。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
下表所有服务器写命令的事务内列均隐含命令账本终态写入。
```

替换为：
```text
下表所有服务器写命令的事务内列均隐含命令账本终态写入与行为事件追加（§11.5）。
```

**替换 2**｜文件：`DESIGN.md`

原文：
```text
| 评论/发布/互动写命令 | 业务记录、计数、outbox、命令结果同事务 |
```

替换为：
```text
| 评论/发布/互动写命令 | 业务记录、计数、outbox、命令结果、行为事件同事务 |
```

### V5-04　DESIGN：覆盖范围、容量与外部依赖

**为什么**：永久保留的事件表需要容量估算；注销事件来自宿主账号系统，是本系统之外的依赖，必须登记负责任务。

**替换 1**｜文件：`DESIGN.md`

原文：
```text
## 9. 测试与可观测性（覆盖 R-01～R-20）
```

替换为：
```text
## 9. 测试与可观测性（覆盖 R-01～R-21）
```

**替换 2**｜文件：`DESIGN.md`

原文：
```text
并登记存储成本 | NC-009 |
```

替换为：
```text
并登记存储成本 | NC-009 |
| 行为事件规模 | 单条事件 ≤ 0.5 KiB；按日均 50 条估算约 9 MiB/账号/年，10 万账号约 870 GiB/年，永久累加。本期存 Firestore；是否迁移到分析仓库由后续数据分析立项决定 | NC-026 |
```

**替换 3**｜文件：`DESIGN.md`

原文：
```text
| D-07/D-08 知识查询/流派 | E-BOOK | 既有上游任务，由 NC-020a 登记 | 需要该关系的知识入口，不阻断独立笔记 |
```

替换为：
```text
| D-07/D-08 知识查询/流派 | E-BOOK | 既有上游任务，由 NC-020a 登记 | 需要该关系的知识入口，不阻断独立笔记 |
| 宿主账号注销与本人彻底删除账号事件：来源、送达语义与测试方式 | E-WIRING | NC-001 登记，NC-026 消费 | 假名映射删除与业务数据去标识化；缺证时只阻断 NC-026 的注销子项 |
```

### V5-05　DESIGN：新增 §11 行为事件数据源

**替换 1**｜文件：`DESIGN.md`

原文：
```text
本期完整键盘方案不是阻断项，而是明确未做的后续 F-01。进一步工程方案若改变 PRD 可见性/数据安全/删除语义，须作为显式变更记录；不由执行 Agent 临时决定。
```

替换为：
```text
本期完整键盘方案不是阻断项，而是明确未做的后续 F-01。进一步工程方案若改变 PRD 可见性/数据安全/删除语义，须作为显式变更记录；不由执行 Agent 临时决定。

## 11. 行为事件数据源（覆盖 R-21）

### 11.1 定位

`BehaviorEvent` 是统计与数据挖掘的唯一数据源：只追加、永久保留、不含任何内容。它与另外三类记录职责分离，互不替代：命令账本负责防重复执行（§7.4），outbox 负责通知投递（§6），运维日志负责排障（§9）。数据分析不得读取命令账本或 outbox，这两者也不得充当事件表。

### 11.2 字段白名单

| 字段 | 规则 |
|---|---|
| event_id | `bev_<32 hex>`。服务端事件为 `"bev_" + SHA256_hex(E([owner_scope, command_id, event_type]))[:32]`（E 见 §7.2），事务回调重跑与同键重试得到同一 ID，以 create-if-absent 写入；客户端上报事件为客户端生成的 UUIDv4 去掉连字符后的 32 位小写 hex，服务端按 event_id 去重 |
| schema_version | 整数，从 1 开始；字段变化只升版本，不改写历史事件 |
| event_type | §11.4 目录中的封闭字符串 |
| occurred_at | 服务端事件为事务提交时的服务器 UTC 时间；客户端事件为设备 UTC 时间 |
| received_at | 服务器接收时间（UTC），用于校正客户端时钟偏差 |
| actor_pseudonym | `psn_<32 hex>`，见 §11.3 |
| object_type、object_id | 公开对象的类型与业务 ID；私人笔记事件两者均为 null |
| note_ref | 仅私人笔记事件使用：`SHA256_hex(UTF8(actor_pseudonym + "/" + note_id))`，用于按笔记聚合且不暴露 note_id 原值；其他事件为 null |
| platform、app_version | 宿主提供的平台枚举与版本字符串 |
| attributes | 按 event_type 定义的有类型小对象，字段全集由 NC-026 的 Schema 冻结，未知字段拒绝；所有客户端事件额外允许可选字段 `dropped_before` |

事件中**禁止出现**（Schema 负例逐项覆盖）：标题、正文、评论文本、修改说明、原文引文与 selector、附件文件名与图片、content_hash 等任何内容指纹、@ 的目标账号、私人笔记的 note_id 原值与绑定目标、account_id、token、IP、设备指纹、精确位置。

### 11.3 假名与账号注销

- `PseudonymMapping` 保存 account_id 到 actor_pseudonym 的对应关系，一账号一假名。actor_pseudonym 在该账号首次产生事件时由密码学安全随机数生成，**禁止由账号 ID 哈希或加密推导**：否则删除映射后，拿账号 ID 重算一遍即可重新关联。
- 事件表只写 actor_pseudonym，不写 account_id。PseudonymMapping 只有事件写入服务可读，数据分析侧无读取权限。
- 宿主账号注销，或本人彻底删除账号时，按顺序执行：
  1. 删除该账号的 PseudonymMapping 记录及其备份副本；
  2. 本系统业务数据中不再保留该 account_id：本人公开内容与评论的作者字段改为统一的「已注销用户」标识；Reaction、Bookmark、ShareLink、NotificationRecord、NotifierDeliveryBinding、CommandRecord 等以该账号为主体的记录删除；其余含该 account_id 的字段删除或改为注销标识；
  3. 行为事件保留不动。
- 第 2 步不能省略：否则事件里的 object_id 可以关联业务表反查出作者，假名化失效。注销事件的来源由 NC-001 登记（§10）。

### 11.4 事件目录

- **服务端事件**：§2.1.1 operation 目录中的每个 operation 在命令 committed 时产生一条同名事件（例如 `comment.create`）；rejected 不产生事件。attributes 只含非内容维度，例如 `reaction.set` 为 `{value, previous_value}`，`content.publish` 为 `{is_republish, image_count}`。
- **私人笔记元数据事件**（客户端上报，默认开启，隐私政策须写明）：
  - `private_note.revision_saved`：`{char_count, attachment_count, mention_count, binding_count, is_restore, is_merge}`，char_count 按 Unicode code point 计数；
  - `private_note.session_ended`：`{edit_duration_seconds, revisions_saved}`。
  私人笔记事件上报请求的原始字节中不得出现标题、正文片段、附件名或 note_id 原值。
- **上报端点**：`POST /v1/analytics/events`，进本系统 3.1 契约（OpenAPI 串行写入排在 NC-021 之后）。语义为至少一次，服务端按 event_id 去重。客户端离线时在本地暂存，上限 10,000 条；超出时丢弃最旧的事件，并在下一条上报事件的 attributes 中带 `dropped_before`（已丢弃条数）。

### 11.5 写入与只追加

- 服务端事件与业务记录、计数、outbox、命令终态在同一 Firestore 事务内追加（§4.3、§7.4）：业务提交成功当且仅当事件存在。
- 只追加：Firestore 安全规则对 BehaviorEvent 集合禁止 update 与 delete，服务端代码不提供更新或删除路径；需要修正时升级 schema_version 并记录新事件，不改写历史。
- 保留：永久，不设 TTL。
```

### V5-06　TASKS：登记 NC-026 并补依赖与覆盖范围

**替换 1**｜文件：`TASKS.md`

原文：
```text
NC-001～NC-025 须在该表登记
```

替换为：
```text
NC-001～NC-026 须在该表登记
```

**替换 2**｜文件：`TASKS.md`

原文：
```text
| NC-025 | **生产 BlobGateway（公共 + 私有）** | NC-001, NC-003 | BACKLOG | BDD 可写，TDD 待 NC-003 | R-15, R-13, R-20 |
```

替换为：
```text
| NC-025 | **生产 BlobGateway（公共 + 私有）** | NC-001, NC-003 | BACKLOG | BDD 可写，TDD 待 NC-003 | R-15, R-13, R-20 |
| NC-026 | 行为事件数据源、假名化与私人笔记元数据上报 | NC-002, NC-003, NC-005, NC-009 | BACKLOG | 仅 BDD，TDD 待 NC-002/003 | R-21 |
```

**替换 3**｜文件：`TASKS.md`

原文：
```text
NC-023, NC-025 | BLOCKED | 待全部前置 | R-01～R-20 |
```

替换为：
```text
NC-023, NC-025, NC-026 | BLOCKED | 待全部前置 | R-01～R-21 |
```

**替换 4**｜文件：`TASKS.md`

原文：
```text
纳入 NC-009/011/012/013/017/019/021 的白名单
```

替换为：
```text
纳入 NC-009/011/012/013/017/019/021/026 的白名单
```

**替换 5**｜文件：`TASKS.md`

原文：
```text
不支持则登记为 E-WIRING 缺口。
```

替换为：
```text
不支持则登记为 E-WIRING 缺口；⑩ 宿主账号注销与本人彻底删除账号事件的来源、送达语义（至少一次还是恰好一次）与测试方式，供 NC-026 消费。
```

**替换 6**｜文件：`TASKS.md`

原文：
```text
或上述九项必填项任一缺失
```

替换为：
```text
或上述十项必填项任一缺失
```

**替换 7**｜文件：`TASKS.md`

原文：
```text
**该文件由四个任务串行写入：NC-003 → NC-013 → NC-017 → NC-021**
```

替换为：
```text
**该文件由五个任务串行写入：NC-003 → NC-013 → NC-017 → NC-021 → NC-026**
```

**替换 8**｜文件：`TASKS.md`

原文：
```text
逐项映射 R-01～R-20 到提交
```

替换为：
```text
逐项映射 R-01～R-21 到提交
```

**替换 9**｜文件：`TASKS.md`

原文：
```text
红条件：R-01～R-20 中任一项
```

替换为：
```text
红条件：R-01～R-21 中任一项
```

### V5-07　TASKS：新增 NC-026 章节

**替换 1**｜文件：`TASKS.md`

原文：
```text
## 5. 通知
```

替换为：
```text
### NC-026：行为事件数据源与假名化

- [ ] 新增 `SERVER/xuan/community/behavior_events.py`、`xuan/community/pseudonyms.py`、`xuan/handlers/analytics_events.py`、`tests/test_behavior_events.py`；新增 `CLIENT/lib/src/analytics/private_note_metrics.dart`、`test/analytics/private_note_metrics_test.dart`。在同一 3.1 OpenAPI 中增加 `POST /v1/analytics/events`（串行写入排在 NC-021 之后，见 [Plans §1.2](PLANS.md)）。写入白名单含 `SERVER/tests/conftest.py`（仅追加 `COLLECTIONS` 键）与 Firestore 安全规则文件。
- [ ] 沿用 NC-002 的机器 Schema 范式，为 BehaviorEvent、PseudonymMapping 补正反 Schema：负例逐项覆盖 [Design §11.2](DESIGN.md) 的禁止字段；`bev_`、`psn_` 前缀随 Design §2.1 一并取得用户确认。
- [ ] **服务端事件**：由 NC-009 的 command_service 在同一事务内追加，event_id 按 Design §11.2 确定性派生。测试：注入「业务写入后、事务提交前」异常，断言既无业务记录也无事件；事务回调重跑与同键重试后事件只有一条；rejected 命令不产生事件；Design §2.1.1 目录中每个 operation 在 committed 后恰有一条同名事件。
- [ ] **只追加**：Firestore 安全规则测试断言对 BehaviorEvent 的 update 与 delete 均被拒绝；静态扫描断言服务端代码中不存在对该集合的更新或删除调用。
- [ ] **假名**：断言 actor_pseudonym 由密码学安全随机数生成（同一 account_id 在两个独立测试库中得到不同假名）；事件集合中没有任何字段等于 account_id。
- [ ] **注销**：模拟宿主注销事件后，断言该账号的 PseudonymMapping 已删除、行为事件条数不变；扫描本系统全部集合，不再有任何字段等于该 account_id（公开内容与评论作者显示为「已注销用户」，Design §11.3 列出的个人记录已删除）；把逐集合处理清单写入工作包 README。注销事件来源取自 NC-001 登记的第⑩项，缺证时本子项保持 BLOCKED，其余子项继续。
- [ ] **私人笔记元数据（默认上报）**：`private_note.revision_saved` 与 `private_note.session_ended` 只含 Design §11.4 列出的字段；对上报请求的原始字节断言不含 fixture 笔记的标题、正文片段、附件名与 note_id 原值；char_count 按 code point 计数（含一个 4 字节字符的用例）；离线暂存超过 10,000 条时丢弃最旧事件，并在下一条上报事件中带 `dropped_before`；服务端按 event_id 去重，重复上报只存一条。
- [ ] 运行 `python3 -m pytest tests/test_behavior_events.py -q`（需 Emulator）与 `flutter test test/analytics/private_note_metrics_test.dart`。

## 5. 通知
```

### V5-08　PLANS：阶段、串行顺序与验收入口

**为什么**：新增的上报端点要写同一份 OpenAPI，新增的集合要进 `conftest.py` 清理清单，这两个文件都有既定的串行写入顺序，不登记会与其他任务冲突。

**替换 1**｜文件：`PLANS.md`

原文：
```text
| `REST/openapi/openapi.yaml` | NC-003 → NC-013 → NC-017 → NC-021 |
```

替换为：
```text
| `REST/openapi/openapi.yaml` | NC-003 → NC-013 → NC-017 → NC-021 → NC-026 |
```

**替换 2**｜文件：`PLANS.md`

原文：
```text
| NC-009 → NC-011 → NC-012 → NC-013 → NC-017 → NC-019 → NC-021 |
```

替换为：
```text
| NC-009 → NC-011 → NC-012 → NC-013 → NC-017 → NC-019 → NC-021 → NC-026 |
```

**替换 3**｜文件：`PLANS.md`

原文：
```text
| P2 媒体与公开社交 | NC-025, NC-008～012 |
```

替换为：
```text
| P2 媒体与公开社交 | NC-025, NC-008～012, NC-026 |
```

**替换 4**｜文件：`PLANS.md`

原文：
```text
所有 R-01～R-20 在 Tasks 有映射
```

替换为：
```text
所有 R-01～R-21 在 Tasks 有映射
```

**替换 5**｜文件：`PLANS.md`

原文：
```text
v1.4 起验收顺序为 `review_final_guard.sh`（内含 R2、R3 守卫回归）→ `verify.sh` → 按 [一次性修复说明](FIX_V1_4.md) §5 的抽查点确认；
```

替换为：
```text
v1.5 起验收顺序为 `review_v1_5_guard.sh`（内含 review_final_guard.sh 及 R2、R3 守卫回归）→ `verify.sh` → 按 [FIX_V1_5](FIX_V1_5.md) §6 的抽查点确认；
```

### V5-09　检查脚本：接受 R-21 与 1.5 版本号

**为什么**：`verify.sh` 写死了 PRD 只能定义 R-01～R-20，`review_final_guard.sh` 写死了版本号必须是 1.4。不改的话，一新增 R-21、一升版就会报红，而文档本身并没有错。

**替换 1**｜文件：`verify.sh`

原文：
```text
range(1, 21)
```

替换为：
```text
range(1, 22)
```

**替换 2**｜文件：`verify.sh`

原文：
```text
PRD 定义 R-01～R-20
```

替换为：
```text
PRD 定义 R-01～R-21
```

**替换 3**｜文件：`review_final_guard.sh`

原文：
```text
bad = [k for k, h in heads.items() if "版本：1.4" not in h]
```

替换为：
```text
bad = [k for k, h in heads.items() if not re.search(r"版本：1\.[4-9]", h)]
```

### V5-10　复核入口、FIX_V1_4 §4 与监控表

**替换 1**｜文件：`REVIEW_R2_CHECKLIST.md`

原文：
```text
请只读复核现有 PRD、DESIGN、PLANS、TASKS v1.4
```

替换为：
```text
请只读复核现有 PRD、DESIGN、PLANS、TASKS v1.5
```

**替换 2**｜文件：`REVIEW_R2_CHECKLIST.md`

原文：
```text
本轮复核重点（v1.4）：先运行 `bash openspec/annotation-community/review_final_guard.sh`（内含 R2、R3 守卫回归，必须 0 失败），再按 [一次性修复说明](FIX_V1_4.md) §5 的抽查点逐条确认。
```

替换为：
```text
本轮复核重点（v1.5）：先运行 `bash openspec/annotation-community/review_v1_5_guard.sh`（内含 review_final_guard.sh 及 R2、R3 守卫回归，必须 0 失败），再按 [FIX_V1_5](FIX_V1_5.md) §6 的抽查点逐条确认。
```

**替换 3**｜文件：`FIX_V1_4.md`

原文：
```text
**命令账本是否改为有界保留。**
```

替换为：
```text
**命令账本是否改为有界保留。**（2026-09-10 已决定：维持永久保留，即下文方案 A；命令账本不作为数据分析的数据源，分析数据源见 [FIX_V1_5](FIX_V1_5.md) 新增的行为事件表。）
```

**替换 4**｜文件：`../../docs/blackbox-spec-rework/SUBAGENT_TODO.md`

原文：
```text
- [ ] NC-025：生产 BlobGateway（公共 + 私有）（状态：`BACKLOG`；R1 新增，NC-008/017 的硬前置）
```

替换为：
```text
- [ ] NC-025：生产 BlobGateway（公共 + 私有）（状态：`BACKLOG`；R1 新增，NC-008/017 的硬前置）
- [ ] NC-026：行为事件数据源、假名化与私人笔记元数据上报（状态：`BACKLOG`；v1.5 新增）
```

**替换 5**｜文件：`../../docs/blackbox-spec-rework/SUBAGENT_TODO.md`

原文：
```text
R-01～R-20 全部在
```

替换为：
```text
R-01～R-21 全部在
```

### V5-11　版本号与变更记录

**替换 1**｜文件：`PRD.md`

原文：
```text
版本：1.4；日期：2026-09-10（落实 FIX_V1_4 一次性修复说明；待抽查确认）。
```

替换为：
```text
版本：1.5；日期：2026-09-10（新增 R-21 行为事件数据源，见 FIX_V1_5；待抽查确认）。
```

**替换 2**｜文件：`DESIGN.md`

原文：
```text
版本：1.4；2026-09-10（落实 FIX_V1_4 一次性修复说明；待抽查确认）。
```

替换为：
```text
版本：1.5；2026-09-10（新增 R-21 行为事件数据源，见 FIX_V1_5；待抽查确认）。
```

**替换 3**｜文件：`PLANS.md`

原文：
```text
版本：1.4；2026-09-10（落实 FIX_V1_4 一次性修复说明；待抽查确认）。
```

替换为：
```text
版本：1.5；2026-09-10（新增 R-21 行为事件数据源，见 FIX_V1_5；待抽查确认）。
```

**替换 4**｜文件：`TASKS.md`

原文：
```text
版本：1.4；2026-09-10（落实 FIX_V1_4 一次性修复说明；待抽查确认）。
```

替换为：
```text
版本：1.5；2026-09-10（新增 R-21 行为事件数据源，见 FIX_V1_5；待抽查确认）。
```

**替换 5**｜文件：`PRD.md`

原文：
```text
| 2026-09-10 | v1.4：落实 FIX_V1_4 全部 18 项
```

替换为：
```text
| 2026-09-10 | v1.5：新增 R-21 行为事件数据源（DESIGN §11、NC-026），并同步 verify.sh 与总守卫的 R 编号和版本判定 | R-21 | [FIX_V1_5](FIX_V1_5.md) |
| 2026-09-10 | 决策：命令账本维持永久保留；命令账本不作为分析数据源，分析以行为事件表为准 | DESIGN §7.4、§11 | 用户确认 |
| 2026-09-10 | 决策：私人笔记默认上报不含内容的元数据，隐私政策须写明 | R-21、DESIGN §11.4 | 用户确认 |
| 2026-09-10 | 决策：账号注销或彻底删除时删除假名映射，行为事件保留；业务数据同步去标识化 | R-21、DESIGN §11.3 | 用户确认 |
| 2026-09-10 | v1.4：落实 FIX_V1_4 全部 18 项
```

## 6. 修改后的抽查点（复核人）

`review_v1_5_guard.sh` 为 0 失败之后，复核人只需确认下面几处的内容与本说明的替换文逐字一致：

1. DESIGN §11.3：假名随机生成且禁止由账号 ID 推导；注销三步中的第 2 步（业务数据去标识化）完整存在。
2. DESIGN §11.2：禁止字段清单完整；私人笔记事件的 object_id 为 null，note_ref 为哈希而非 note_id 原值。
3. DESIGN §4.3 与 §7.4：行为事件与业务记录同事务。
4. TASKS NC-026：含故障注入、只追加规则测试、注销后全库 account_id 扫描、上报原始字节不含内容四项验收；总表依赖含 NC-009。
5. PRD §9：v1.5 记录与三项用户决策各占一行。
