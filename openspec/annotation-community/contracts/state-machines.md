# 注解社区状态机契约（NC-002）

状态：`FROZEN_FOR_NC-002`（2026-09-10）。权威来源：[DESIGN](../DESIGN.md) §2.2、§3、§3.1、§4.1～§4.4、§6、§6.1、§8；错误码取自 §7.3 基线目录。本文给出九台状态机的**完整**转移表：每条边标注触发事件、前置条件、目标态与失败结果；表中未列出的 (当前态, 事件) 组合一律为非法转移，服务端返回 `409 conflict.lifecycle`（附 `current_state`），客户端本地机器抛出表内指定的本地错误且状态不变。BDD 场景按边生成；`tools/validate_fixtures.py` 以本文的枚举表为唯一状态值来源。

记号：`→` 目标态；`✘` 非法（状态不变）；「本地错误」为客户端异常类名，不是 HTTP；HTTP 失败写为 `状态码 code`。

## 枚举总表（validate_fixtures.py 读取本表）

| 机器 | 归属 | 字段 | 枚举 |
|---|---|---|---|
| SM-1 编辑态 | CLIENT | EditorState | `clean` `dirty` `saving` `save_failed` `ime_composing` |
| SM-2a 发布态 | SERVER | ContentAccess.visibility | `never_published` `published` `withdrawn` |
| SM-2b 发布记录 | SERVER | Publication.state | `draft` `live` `superseded` `retracted` |
| SM-3 生命周期 | SERVER（曾公开）/ CLIENT（从未公开） | lifecycle | `active` `trashed` `purge_pending` `purged` |
| SM-4 审核态 | SERVER | ContentAccess.moderation_state | `allowed` `hidden` |
| SM-5 客户端待办 | CLIENT | Note.pending_op | `none` `withdraw_requested` `trash_requested` `purge_requested` |
| SM-6 清理任务 | SERVER | PurgeTask.state | `queued` `running` `failed` `succeeded` |
| SM-7 投递态 | SERVER | NotificationRecord.delivery_state | `created` `dispatching` `delivered` `failed` `abandoned` |
| SM-8 导入态 | SERVER | LibraryImport.state | `received` `validating` `ready` `active` `rejected` `retained` |
| SM-9 锚点解析 | CLIENT/SERVER | AnchorResolution.state | `resolved` `ambiguous` `missing` `degraded` |
| （附）评论状态 | SERVER | Comment.status | `visible` `deleted` `hidden` |

## SM-1 编辑态（DESIGN §3，逐字转录 + 非法边）

初态 `clean`。

| 当前态 | 事件 | 前置条件 | 目标态 | 失败 / 说明 |
|---|---|---|---|---|
| clean | onTextChanged | — | dirty | 启动 2000 ms 去抖 |
| clean / dirty | IME 开始组合 | — | ime_composing | 半成品不当最终修订 |
| dirty | 去抖到期 / 失焦 / 返回 | — | saving | flush |
| dirty | 应用被杀 | — | （无承诺） | 不伪称逐键持久化 |
| saving | 持久化成功 | 事务（新增修订→更新头→记录待同步）全部成功 | clean | 无内容变化则不新增修订 |
| saving | 持久化失败 | — | save_failed | 保留缓冲，不清 undo 栈；无半个 head、无 outbox 行 |
| saving | 持久化失败：Markdown > 1048576 B | — | save_failed | 本地错误 `NoteSizeLimitExceeded`，无新修订 |
| saving | 持久化失败：第 21 张附件 | — | save_failed | 本地错误 `AttachmentCountExceeded`，前 20 引用不变 |
| saving | 持久化失败：数组含完全相同重复项 | — | save_failed | 本地错误 `DuplicateReferenceItem`（不静默去重） |
| saving | onTextChanged | — | saving（置 pending_dirty） | 本次保存完成后立即再触发一次 |
| save_failed | onTextChanged | — | save_failed（内容更新） | 不自动重试 |
| save_failed | 点击重试 / 失焦 / 返回 | — | saving | — |
| save_failed | 用户选择「复制全文」后离开 | — | save_failed（保留） | 内容不丢弃 |
| ime_composing | 组合提交 | — | dirty | 整段组合为一个编辑步骤 |
| ime_composing | 返回且无法完成输入 | — | ime_composing | 保持编辑页与未保存提示，不允许离开 |
| clean | 去抖到期 / 点击重试 | — | ✘ | 本地错误 `IllegalEditorTransition` |
| saving | 点击重试 | — | ✘ | 同上（保存进行中不可重入） |
| ime_composing | 去抖到期 | — | ✘ | 组合期间不保存 |

保存去重（DESIGN §7.2）：除 change_summary 外投影与 head 相同且 `summary_touched=false` → 无变化、不新增修订；其余按完整投影 hash 比较；恢复/合并即使 hash 相同也新建修订。

## SM-2a 发布态 ContentAccess.visibility（DESIGN §4.1、§4.3）

初态：内容从未发布时**不存在** ContentAccess 行，`never_published` 是派生表达。

| 当前态 | 事件（命令） | 前置条件 | 目标态 | 失败 |
|---|---|---|---|---|
| never_published | content.publish | 本人；lifecycle=active；选定修订已保存；图片对象全部上传并校验；`If-Match` 缺省 | published（创建 ContentAccess、Publication live、绑定索引、outbox、账本、事件同事务） | 非本人 `403 forbidden.not_owner`；lifecycle≠active `409 conflict.lifecycle`；对象未就绪 `400 invalid_argument.attachment_refs` |
| published | content.update | 本人；lifecycle=active；`If-Match` = ContentAccess.version | published（新 Publication live，旧 live→superseded，version+1） | 版本不符 `412 conflict.version`；非本人 403；lifecycle≠active 409 |
| published | content.withdraw | 本人；`If-Match` = version | withdrawn（live→retracted，version+1，current_publication_id=null） | 412 / 403 |
| withdrawn | content.publish（重新发布） | 本人；lifecycle=active；`If-Match` = version | published（新 Publication，沿用 content_id，讨论身份不变） | 412 / 403 / 409 conflict.lifecycle |
| never_published | content.withdraw / update | — | ✘ | `404 not_found.content`（无 ContentAccess 行） |
| withdrawn | content.withdraw / update | — | ✘ | `409 conflict.lifecycle`（current_state=withdrawn） |
| 任意 | 命令 command_id 已有终态 | — | 状态不变 | 返回原结果（§7.4）；同键异载荷 `409 conflict.idempotency` |

hidden 不影响本机器：作者对 hidden 内容仍可 withdraw；moderation 见 SM-4。

## SM-2b 发布记录 Publication.state

| 当前态 | 事件 | 前置条件 | 目标态 | 说明 |
|---|---|---|---|---|
| （无） | 上传会话开始 | 本人 | draft | 事务外；不可经任何公共入口访问 |
| draft | publish/update 事务提交 | 对象全部就绪 | live | 与 ContentAccess 同事务 |
| draft | 上传失败 / 事务拒绝 / 超时 | — | （丢弃） | 孤儿对象由清理任务回收 |
| live | 新 Publication 提交（update / 重新发布） | — | superseded | 同事务 |
| live | content.withdraw | — | retracted | 同事务 |
| superseded / retracted | 任意 | — | ✘ | 终态；历史只对作者可见 |
| live | 审核 hide | — | live（不变） | 可见性由 ContentAccess.moderation_state 控制 |

## SM-3 生命周期 lifecycle（DESIGN §4.1、§4.3、§4.4）

初态 `active`。曾公开的内容由服务端权威；从未公开的纯本地笔记由客户端本地执行同一张表，HTTP 失败列按下表映射为本地结果（`lifecycle_transition_cases.json` 中 `local: true` 的用例只取 409 分支）：

| 服务端失败 | 本地等价 |
|---|---|
| `409 conflict.lifecycle` | 本地错误 `IllegalLifecycleTransition`，状态不变 |
| `404 not_found.content`（purged tombstone） | 本地错误 `TombstoneRejected`；同步收到旧头时静默忽略、不复活 |
| `403 forbidden.not_owner` | 本地不适用（本地库只有本人 scope） |

| 当前态 | 事件 | 前置条件 | 目标态 | 失败 |
|---|---|---|---|---|
| active | content.trash | 本人；若曾公开，`visibility=withdrawn`（服务器已确认收回） | trashed（记录 trash 事件 server_time；本地记 trashed_at） | visibility=published → `409 conflict.lifecycle`（须先 withdraw）；非本人 403 |
| trashed | content.restore | 本人；距 T0 ≤ 30 天；lifecycle=trashed | active（保持 private；moderation 不变） | 超期 `409 conflict.lifecycle`；purge_pending `409 conflict.lifecycle` |
| trashed | content.purge（本人明确彻底删除） | 本人 | purge_pending（PurgeTask queued） | 403 |
| trashed | 30 天到期（服务端定时 / 本地定时） | T0 + 30 天 ≤ now | purge_pending（PurgeTask queued） | — |
| purge_pending | PurgeTask succeeded | 正文/引用/附件/备份全部删除成功 | purged（保留无正文 tombstone） | — |
| purge_pending | content.restore | — | ✘ | `409 conflict.lifecycle`（current_state=purge_pending） |
| active | content.purge | — | ✘ | `409 conflict.lifecycle`（决定 D-NC002-07：彻底删除只能从回收站发起） |
| active | content.restore | — | ✘ | 409 |
| purged | 任意写命令 | — | ✘ | `404 not_found.content`（tombstone 防复活） |
| 任意 | 同步收到旧设备的 active 头 | 本地为 purge_pending / purged | 状态不变 | 以 tombstone 为准，不复活 |

T0：曾公开 = 服务端 trash 事件 server_time；从未公开 = 本地 trashed_at，首次上线以服务器时间校正且只允许推后。

## SM-4 审核态 moderation_state（DESIGN §4.1）

| 当前态 | 事件 | 前置条件 | 目标态 | 失败 |
|---|---|---|---|---|
| allowed | moderation.hide | 审核角色；visibility ∈ {published, withdrawn} | hidden | 非审核角色 `403 forbidden.moderation_role`（**候选码**，NC-003 冻结前不得写入验收）；visibility=never_published `409 conflict.lifecycle` |
| hidden | moderation.unhide | 审核角色 | allowed | 同上 |
| hidden | 作者 restore / update / 重新发布 | — | hidden（不变） | 作者操作不清除审核态 |
| allowed / hidden | 作者任何命令 | — | 不变 | 只由审核角色改变 |

## SM-5 客户端待办 pending_op（DESIGN §4.2）

初态 `none`。本地字段，不上传，不改变他人可见性。

| 当前态 | 事件 | 前置条件 | 目标态 | 失败 |
|---|---|---|---|---|
| none | 入队 withdraw 命令 | 本地 visibility=published | withdraw_requested | — |
| none | 入队 trash 命令 | 曾公开须本地 visibility=withdrawn；从未公开直接本地执行 SM-3，不入队 | trash_requested | 本地错误 `TrashRequiresWithdraw` |
| none | 入队 purge 命令 | 本地 lifecycle=trashed | purge_requested | 本地错误 `IllegalLifecycleTransition` |
| X_requested | 服务端返回 committed | — | none（同时按响应更新 visibility / lifecycle） | — |
| X_requested | 服务端返回 rejected（4xx 终态） | — | none（展示错误，状态按 GET 刷新） | — |
| X_requested | 入队另一命令 | — | ✘ | 本地错误 `PendingOpConflict`（同目标串行，先恢复结果） |
| X_requested | 应用重启 | 持久化的 command_id 与待办仍在 | X_requested（恢复，同键重试或查询） | 不生成新键 |
| X_requested | 用户取消本地待办 | 命令尚未发送 | none | 已发送则不可取消，先核实结果（§7.4 第 6 条） |

UI：`pending_op ≠ none` 显示「正在停止公开，他人可能仍可访问」并进入「待处理」队列。

## SM-6 清理任务 PurgeTask.state（DESIGN §4.3）

| 当前态 | 事件 | 目标态 | 说明 |
|---|---|---|---|
| queued | worker 领取 | running | — |
| running | 全部子任务成功 | succeeded | 触发 SM-3 purge_pending → purged |
| running | 任一子任务失败 | failed | 记录失败类别，不含正文 |
| failed | 重试 | queued | 可重复；无上限（人工可见） |
| succeeded | 任意 | ✘ | 终态 |

## SM-7 投递态 NotificationRecord.delivery_state（DESIGN §6、§9.1）

初态 `created`（doc ID 确定性派生，create-if-absent；并发第二次写入 already-exists，不新建）。

| 当前态 | 事件 | 前置条件 | 目标态 | 说明 |
|---|---|---|---|---|
| created | 投递器领取 | 收件人当前仍有权访问目标；未拉黑；偏好允许 | dispatching（attempt_count+1） | 无权/拉黑/偏好拒绝 → abandoned |
| dispatching | notifier 接受 | — | delivered | 记录 NotifierDeliveryBinding（可多条） |
| dispatching | notifier 拒绝 / 超时 | attempt_count < 5 | failed | 退避 1s/2s/4s/8s |
| failed | 重试到期 | attempt_count < 5 | dispatching（attempt_count+1） | — |
| failed | attempt_count = 5 | — | abandoned | 终态 |
| delivered | 重复推送（at-least-once） | — | delivered（不变） | 客户端按 deliveryId 去重 7 天 |
| abandoned / delivered | 任意 | — | ✘ | 终态 |

## SM-8 导入态 LibraryImport.state（DESIGN §8）

每个 release 一条记录；同作用域只有一个 `active`。

| 当前态 | 事件 | 前置条件 | 目标态 | 失败 |
|---|---|---|---|---|
| （无） | library.import | manifest/hash 齐全 | received | `400 invalid_argument.manifest` |
| received | 开始校验 | — | validating | — |
| validating | 对象/引用/发布级别/报告/能力全部通过 | — | ready | — |
| validating | 任一校验失败 | — | rejected（终态，附报告；旧 active 不受影响） | — |
| ready | library.activate | 隔离写入完成 | active（原 active → retained，原子切换指针） | 指针切换失败 → ready（不变） |
| active | 新 release 激活 | — | retained | 一次查询固定 Release，不受切换影响 |
| rejected / retained | library.activate | — | ✘ | `409 conflict.lifecycle`（决定 D-NC002-08：不支持回滚到 retained，需重新导入） |

## SM-9 锚点解析 AnchorResolution.state（DESIGN §2、§8）

不是随时间迁移的机器：每次针对 `(anchor_id, target_release)` 解析产生一条**不可变** AnchorResolution 记录，原始 AnchorRef 永不改写；重解析新增记录。状态由判定规则唯一决定：

| 判定顺序 | 条件 | state | targets |
|---|---|---|---|
| 1 | target_release 中 selector 全部 ranges 的 block_id + text_hash 精确命中且唯一 | resolved | 1 个 |
| 2 | 精确命中 > 1 处（拆分/重复段落） | ambiguous | ≥ 2 个，不自动猜 |
| 3 | 精确命中 0 处，但 context.before/after 在 mapping_ref 指示的迁移映射中命中 | degraded | 1 个，reason 记录退化原因 |
| 4 | 以上皆无 | missing | 空 |

`degraded` 与 `missing` 的迁移映射 `mapping_ref` 来自上游 IdentityMigrationMap（D-06），未交付时不得伪造映射：只能给出 resolved / ambiguous / missing。

## SM-C 状态组合白名单（DESIGN §4.1；fixture `state_combinations.json`）

`visibility × lifecycle × moderation` = 3 × 4 × 2 = 24 组合，合法 14 项：

| visibility | lifecycle | moderation | 合法 |
|---|---|---|---|
| never_published | active | allowed | ✔ |
| never_published | trashed / purge_pending / purged | allowed | ✔（3 项） |
| never_published | 任意 | hidden | ✘（4 项） |
| published | active | allowed / hidden | ✔（2 项） |
| published | trashed / purge_pending / purged | allowed / hidden | ✘（6 项） |
| withdrawn | active | allowed / hidden | ✔（2 项） |
| withdrawn | trashed / purge_pending / purged | allowed / hidden | ✔（6 项） |

非法组合：读取 `500` 并告警；写入拒绝 `409 conflict.lifecycle`。

## 决定登记（补 community-models.md §6）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC002-07 | purge 只能从 trashed 发起（active → purge_pending 非法） | PRD 回收站 30 天模型；DESIGN §4.3「到期或本人明确彻底删除」在回收站语境内 |
| D-NC002-08 | 导入态不支持 retained → active 回滚 | DESIGN §8 只定义「替换后旧版 retained」；回滚需重新导入，避免两个 active |
| D-NC002-09 | SM-4 非审核角色的错误码 `403 forbidden.moderation_role` 为候选，NC-003 冻结前不进验收 | DESIGN §7.3 基线目录无此场景，不得由执行者发明 |
| D-NC002-10 | 本文使用的本地错误类名闭集见 community-models.md §6 D-NC002-10（八个类名） | 类名是客户端可断言标识，不是 HTTP 错误码 |
