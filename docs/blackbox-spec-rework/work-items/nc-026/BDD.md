# NC-026 可观察行为

ID 与契约 `community_behavior.md` 一一对应：REST 行为 A01～A04（§10）、SERVER 行为 S01～S26（§3～§5、§8.3）、CLIENT 行为 C01～C18（§6、§8.4）、RULES 行为 R01～R03（§7）。「期望」逐字以契约为准，本表只给 Given/When/Then 摘要。

测试基建口径：SERVER 经 `community_helpers.call` 直调 handler、纯函数直调 `ingest_client_events`（注入 `now`）、Emulator 真事务；REST 仅 dart 结构测试；CLIENT 用 `MockClient` + 真实临时目录文件库；RULES 经 jest rules harness。

## REST（A）

| ID | Given | When | Then |
|---|---|---|---|
| A01 | openapi.yaml 3.1 | 校验 W17/R11 两条路径与方法 | `analytics paths and methods match the catalog` 通过；`expectedCatalog` 含 analytics 两行 |
| A02 | 4 个新 Schema | 校验必填、`additionalProperties: false`、`event_id` UUIDv4-beV 形态、`events` maxItems 500 | `analytics schemas are closed objects with pseudonym and batch bounds` 通过；validator 接受 openapi |
| A03 | 示例 2 个 + manifest 22 项 | 运行 `tool/check_examples.py` | 退出 0；翻转 `analytics_pseudonym.json` 任一字段后退出 1 |
| A04 | 错误目录与限流 | 校验 §14.3/§14.4 增补行 | `invalid_argument.events`、`invalid_argument.event_type`、`too_large.events`、`analytics.events` 60/分钟 出现在 yaml |

## SERVER（S）

| ID | Given | When | Then |
|---|---|---|---|
| S01 | 规格侧冻结 Schema | SERVER 副本与契约 §9.1 的 SHA 字面量比对 | 逐字节相同、SHA = `SCHEMA_SHA` |
| S02 | 契约 §9.1 的 SHA | 对 SERVER 副本实算 SHA-256 | 等于字面量（不在测试内现算期望值，用常量比对） |
| S03 | 真跑一次 `content.publish` 命令 | 读事件文档并按冻结 Schema 校验 | 12 必填字段齐全，Schema 通过 |
| S04 | 6 个内容 operation 与 comment/reaction/bookmark/share/report | 逐 operation 真跑一次 committed 命令 | `object_type`/`object_id` 与契约 §3.1 映射表逐字一致 |
| S05 | 服务端事件 | 读事件文档 | `note_ref == null`、`platform == "server"`、`received_at == occurred_at`、`app_version == "0.0.0"` |
| S06 | 客户端事件 ID 生成 | 生成 100 个 | 全部匹配 `^bev_[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$` |
| S07 | 各 event_type 的 attributes | 逐 event_type 注入未知键校验 | 未知键被拒；允许键通过 |
| S08 | `private_note.revision_saved` | 缺任一必填 members 校验 | 拒绝；齐全时通过 |
| S09 | `private_note.*` | attributes 带 `is_republish` | 拒绝（服务端专用键） |
| S10 | 契约 §9.2 的 23 个示例 | 用冻结 Schema 校验 | 2 正例通过、21 负例全部被拒 |
| S11 | 合法 3 条批 | W17 | 200 `{accepted:3, duplicates:0, actor_pseudonym}`；事件文档 `received_at` 为服务器时间、`actor_pseudonym` 来自映射 |
| S12 | 同一批重复提交 | W17 | `accepted:0, duplicates:3`，事件表条数不变 |
| S13 | 501 条批 | W17 | 413 `too_large.events`（`limit:500`） |
| S14 | `event_type = content.publish` | W17 | 400 `invalid_argument.event_type` |
| S15 | `events[0].attributes.char_count` 非法 | W17 | 400 `invalid_argument.events`，`field` 指向 `/events/0/attributes/char_count` |
| S16 | 250 条合法批 | W17 | 拆分为 3 个事务（100/100/50），`accepted:250` |
| S17 | 无 token | W17 | 401 `unauthenticated` |
| S18 | 契约 §14.4 的限流行 | 校验 handler 与契约 | `analytics.events` 60/分钟一致 |
| S19 | W17 成功 | 读命令账本与通知集合 | 账本零行、`community_notifications` 零行、outbox 零行 |
| S20 | 第 2 个事务注入失败 | 以同批重试 | 首次 503 `unavailable`；重试后事件总条数 = 唯一 event_id 数（不重复落盘） |
| S21 | 无映射的新账号 | R11 两次 | 两次同一 `psn_`；一次调用只建一条映射；事件表零行 |
| S22 | R11 首次调用 | 读 `community_pseudonym_mappings` | 恰一条，`account_id == owner_scope`，`actor_pseudonym` 匹配 `^psn_[0-9a-f]{32}$` |
| S23 | 同账号先走命令路径再走客户端上报 | 读两条事件 | `actor_pseudonym` 相同 |
| S24 | 两个独立项目各建一次映射 | 比对假名 | 不相等；且都 ≠ `psn_` + SHA-256(scope)[:32] |
| S25 | 任意事件文档 | 全字段扫描 | 无任何字段值等于 owner_scope，且不含 `owner_scope`/`app_user_id`/`account_id` 键 |
| S26 | 服务端源码 | 静态扫描 `xuan/**/*.py` | `community_behavior_events` 上不存在 update/delete/merge 调用 |

## CLIENT（C）

| ID | Given | When | Then |
|---|---|---|---|
| C01 | `onRevisionSaved` | 取队列首条 | `attributes` 恰 6 键且值与入参一致 |
| C02 | markdown = `"a𠀀b"`（一个 4 字节字符） | 取 `char_count` | `== 3`；且 ≠ `String.length`(4) ≠ UTF-8 字节数(6) |
| C03 | `onSessionEnded` | 取队列首条 | `{edit_duration_seconds, revisions_saved}` 与入参一致 |
| C04 | 生成 100 个事件 | 校验 event_id | 全部匹配 `^bev_[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$` |
| C05 | 固定假名与 note_id | 取 `note_ref` | 等于契约 §9.3 字面量 `2be56a40…0673` |
| C06 | 上报请求原始字节 | 扫描 | 不含 fixture 的 note_id、标题、正文片段、附件名 |
| C07 | 假名未缓存 | `flush` 两次 | `fetchActorPseudonym` 恰调用 1 次 |
| C08 | 已缓存假名 | `clearPseudonymCache()` 后 flush | 重新调用一次 `fetchActorPseudonym`，新事件用新假名 |
| C09 | transport 抛错 | `flush` | 返回 `FlushResult.failed`、不抛穿；`pendingCount` 不变 |
| C10 | 入队 10001 条 | 读队列 | 长度恰 10000，最旧一条被丢 |
| C11 | 丢弃 1 条后入队新事件 | 取队列首条 | `attributes.dropped_before == 1`；其余事件无该键 |
| C12 | 未发生丢弃 | flush | 所有事件均无 `dropped_before` |
| C13 | 1200 条待发 | `flush` | 只发 1 批且 `len(events) == 500` |
| C14 | 批内 1 条服务端已存在 | flush | 只删除被确认的 `event_id`（`accepted + duplicates`） |
| C15 | 服务端 503 | flush | 返回 `FlushResult.failed`，不抛异常 |
| C16 | 入队后重建 Store | 读 `pendingCount` | 与重启前一致（真实文件库） |
| C17 | `onRevisionSaved` 且 transport 抛错 | 调用返回 | 不抛异常、不改变编辑器保存结果 |
| C18 | 一条上报 payload | 键集合 | 恰为契约 §5.1 的 8 键，无额外键 |

## RULES（R）

| ID | Given | When | Then |
|---|---|---|---|
| R01 | `community_behavior_events` × 2 上下文 | update 与 delete | 全部 `assertFails`（新增 4 用例） |
| R02 | 顶层默认拒绝 match | 审视 `server/firestore.rules` | 行为事件与假名映射集合未新增任何 match（文件零改动） |
| R03 | rules harness | `npm test -- community_rules` | `Tests: 157 passed, 157 total` |
