# 注解社区数据模型契约（NC-002）

状态：`FROZEN_FOR_NC-002`（2026-09-10）。权威来源：[DESIGN](../DESIGN.md) §2、§2.1、§2.1.1、§4、§6、§7、§11；[PRD](../PRD.md)。本文只把 DESIGN 已定的对象落到字段级，供 `openspec/schemas/community_*.schema.json`、`fixtures/community/` 与 SERVER/CLIENT 实现照抄；凡本文与 DESIGN 冲突，以 DESIGN 为准并回报主 Agent。本文不新增产品行为。

## 0. 通用约定

| 约定 | 规则 |
|---|---|
| 业务 ID | `<前缀><32 位小写 hex>`，前缀见 §0.1；正则 `^<前缀>[0-9a-f]{32}$`。上游保留前缀 `art_ / rev_ / rel_ / pr_ / prun_` 只能出现在引用上游对象的字段（`artifact_revision_id`、`release_id`），不得用于本系统对象 |
| 命令 ID | `cmd_` + UUIDv4 去连字符的 32 位小写 hex，正则见 DESIGN §2.1.1 |
| 宿主账号 ID | `account_id` / `author_id` / `actor_id` / `recipient_id` / `user_id` 为宿主不透明字符串（PlaygroundUserId），非空、≤ 128 字节、不含 `/`；本系统不解释其格式 |
| owner_scope | 服务器由认证推导的非空字符串，客户端不可写 |
| 时间戳 | RFC 3339 UTC，格式 `YYYY-MM-DDTHH:MM:SS(.fff)?Z`；私人本地记录设备时间，公开排序/审计用服务器时间 |
| 哈希 | 64 位小写 hex |
| 文本长度 | 一律 Unicode code point 计数（Dart `runes.length`，Python `len(str)`） |
| 整数 | JSON integer，范围 ±(2^53−1)，布尔不当整数 |
| 未知字段 | 全部 Schema `additionalProperties: false`；未知字段拒绝 |
| 版本号 | `version` 为非负安全整数，服务器单调递增，客户端只读 |

### 0.1 业务 ID 前缀（DESIGN §2.1，2026-09-10 由用户托管主 Agent 整表采用，冻结）

| 对象 | 前缀 | 对象 | 前缀 |
|---|---|---|---|
| Note | `note_` | Bookmark | `bmk_` |
| NoteRevision | `nrev_` | ShareLink | `shr_` |
| Publication | `pub_` | BackupManifest | `bkm_` |
| ContentAccess | `cacc_` | NotificationRecord | `ntf_` |
| ContentBinding | `cbnd_` | BehaviorEvent | `bev_` |
| AnchorRef | `anc_` | 行为假名 actor_pseudonym | `psn_` |
| AnchorResolution | `ares_` | Reaction | `rct_` |
| Thread | `thr_` | Comment | `cmt_` |
| CommentRevision | `crev_` | | |

非法格式五类（fixture `id_format_cases.json` 逐类给负例）：① 前缀不在表中；② hex 段长度 ≠ 32；③ 含大写或非 hex 字符；④ 使用上游保留前缀（含 `rev_` 误用作 NoteRevision）；⑤ 前缀与所在字段不匹配（如 `thread_id` 收到 `cmt_`）。

`content_id` 是 Note 与其公共记录共享的稳定身份，取值即 `note_<32 hex>`（不另设前缀）：Publication / ContentAccess / ContentBinding / Thread 的 `content_id` 与本人 Note.id 相同；服务端不得把它当私人信息，它只标识身份，不泄漏正文。

## 1. 私人域（CLIENT 本地 Drift；正文只以密文离开设备）

### 1.1 Note

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | `note_` ID | ✔ | 即 content_id |
| owner_scope | string | ✔ | 账号作用域；跨 scope 不可见 |
| kind | enum `note` / `annotation` | ✔ | annotation 必须至少有一个带 anchor 的 binding（校验在 NoteRevision） |
| head_revision_ids | `nrev_` ID 数组，≥ 1，去重 | ✔ | 允许多头 |
| preferred_head_id | `nrev_` ID | ✔ | 必须 ∈ head_revision_ids |
| lifecycle | enum §SM-3 | ✔ | 本地镜像，权威见 ContentAccess（曾公开）或本地（从未公开） |
| pending_op | enum §SM-5 | ✔ | 客户端本地字段，默认 `none`，不上传 |
| created_at | timestamp | ✔ | 设备时间 |
| trashed_at | timestamp / null | ✔ | 进入 trashed 的时间；从未公开的笔记以此起算 30 天，首次同步时只允许被服务器时间推后 |

### 1.2 NoteRevision（不可变）

| 字段 | 类型 | 必填 | 进 content_hash |
|---|---|---|---|
| id | `nrev_` ID | ✔ | 否 |
| note_id | `note_` ID | ✔ | 否 |
| parent_ids | `nrev_` ID 数组（根为空数组；合并可多个；去重） | ✔ | 否 |
| title | string，≤ 200 code points | ✔（默认空串） | 是 |
| markdown | string，UTF-8 ≤ 1048576 B | ✔（默认空串） | 是 |
| attachment_refs | AttachmentRef 数组，≤ 20，无完全相同重复项 | ✔（默认 []） | 是 |
| mentions | MentionRef 数组，≤ 50，无完全相同重复项 | ✔（默认 []） | 是 |
| bindings | BindingRef 数组，无完全相同重复项 | ✔（默认 []） | 是 |
| content_hash | 64 hex，nchash/v2 | ✔ | —（输出） |
| change_summary | string，≤ 500 code points | ✔（默认空串） | 是 |
| restored_from | `nrev_` ID / null | ✔ | 否 |
| created_at | timestamp | ✔ | 否 |
| created_on_device | string（设备 ID，宿主格式） | ✔ | 否 |

语义投影 `snapshot` = 上表「进 content_hash = 是」的六个字段；规范化与编码见 DESIGN §7.2 与 `tools/nchash_reference.py`。

**AttachmentRef**（`attachment_id` 是唯一规范字段名）：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| attachment_id | string，`^[A-Za-z0-9_-]{1,128}$` | ✔ | 对象存储的不透明键；**不设业务前缀**（决定 D-NC002-01）；Markdown 内引用形式 `attachment://<attachment_id>` |
| object_version | integer ≥ 1 | ✔ | 对象版本 |
| content_digest | 64 hex | ✔ | 加密前明文 SHA-256 |
| alt | string，≤ 200 code points | 默认空串 | 可编辑 |
| caption | string，≤ 500 code points | 默认空串 | 可编辑 |

**MentionRef**：

| 字段 | 类型 | 必填 |
|---|---|---|
| user_id | 宿主账号 ID | ✔ |
| display_name | string，1–64 code points | ✔ |
| start_offset | integer ≥ 0（code point） | ✔ |
| length | integer ≥ 2（`@` + 至少 1 字符） | ✔ |

有效性：`markdown` 从第 `start_offset` 个 code point 起长 `length` 的子串必须等于 `"@" + display_name`，否则该条 mention 无效（DESIGN §6）。无效不等于格式非法：Schema 只校验格式，有效性由保存逻辑判定并解除关系。

**BindingRef**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| relation | enum `about` / `quotes` | ✔ | about＝笔记关于该对象；quotes＝引用该对象的原文片段（决定 D-NC002-02） |
| target_kind | enum `knowledge_entry` / `assertion` / `source_span` / `source_anchor` | ✔ | 与 LEARN_SYSTEM_TARGET §3.2 可注解对象一致；正式白名单以 D-06 为准，D-06 定稿后若收窄，本枚举只删不增 |
| target_ref | string，1–200 字节 | ✔ | 上游稳定 entity_id（如 `ku_…`、`ss_…`） |
| anchor | AnchorRef / null | 默认 null | `quotes` 必须带 anchor；`about` 允许 null |

**AnchorRef**（创建时固定，永不改写）：

| 字段 | 类型 | 必填 |
|---|---|---|
| anchor_id | `anc_` ID | ✔ |
| target_type | 同 target_kind 枚举 | ✔ |
| entity_id | string | ✔ |
| artifact_revision_id | `rev_` + 32 hex | ✔ |
| release_id | `rel_` + 32 hex | ✔ |
| context | object `{before: string ≤ 64 cp, after: string ≤ 64 cp}` | ✔ |
| selector | Selector | ✔ |

**Selector（临时结构，`schema` 固定为 `selector/v0-provisional`）**：D-06 与 NC-020b 尚未冻结坐标类型；本期只允许下列整数/字符串字段，禁止浮点。D-06 定稿后由 NC-002 增补版本 `selector/v1` 并评估 nchash 版本，之前不宣称原句 hash 跨端已互通（DESIGN §7.2）。

| 字段 | 类型 |
|---|---|
| schema | 常量 `selector/v0-provisional` |
| ranges | 有序数组，≥ 1，每项 `{block_id: string, artifact_revision_id: rev_ ID, text_hash: 64 hex, start: integer ≥ 0, end: integer > start}`；顺序即上游文本顺序，换序改变 hash |

### 1.3 EditorSnapshot（内存态，不持久化、不进 Schema）

`title, text, selection{base, extent}, composing(bool), attachmentRefs, mentionRefs, bindings, changeSummary, summary_touched(bool)`。`summary_touched` 只存在于编辑会话（DESIGN §7.2）。Undo 归组常量：`UNDO_MERGE_MAX_GAP_MS = 500`、`UNDO_MERGE_MAX_CHARS = 20`；自动保存去抖 `AUTOSAVE_DEBOUNCE_MS = 2000`（DESIGN §3、§3.1；NC-005/006 引用本节常量，不另写数字）。

## 2. 公共域（SERVER Firestore；客户端只经鉴权命令写入）

### 2.1 Publication

| 字段 | 类型 | 必填 |
|---|---|---|
| id | `pub_` ID | ✔ |
| content_id | `note_` ID | ✔ |
| published_revision_id | `nrev_` ID | ✔ |
| public_snapshot_ref | string（对象存储键，同 attachment_id 正则） | ✔ |
| state | enum §SM-2b `draft / live / superseded / retracted` | ✔ |
| version | integer | ✔ |
| published_at | timestamp（服务器） / null（draft 时） | ✔ |

公共快照只含选定修订的 title / markdown / 公共附件引用 / 有效 mention / bindings；**不含** parent_ids、私人历史、change_summary。

### 2.2 ContentAccess

| 字段 | 类型 | 必填 |
|---|---|---|
| id | `cacc_` ID | ✔ |
| content_id | `note_` ID | ✔（同 content_id 唯一） |
| author_id | 宿主账号 ID | ✔ |
| visibility | enum §SM-2a `never_published / published / withdrawn` | ✔ |
| lifecycle | enum §SM-3 | ✔ |
| moderation_state | enum §SM-4 `allowed / hidden` | ✔ |
| current_publication_id | `pub_` ID / null | ✔ |
| version | integer | ✔ |

三元组组合白名单见 state-machines.md §SM-C；非法组合读 500、写拒绝。

### 2.3 ContentBinding（公共关联索引，仅来自当前 live publication）

| 字段 | 类型 |
|---|---|
| id | `cbnd_` ID |
| content_id | `note_` ID |
| revision_id | `nrev_` ID（= published_revision_id） |
| target_kind / target_ref / relation | 同 BindingRef |

### 2.4 Thread / Comment / CommentRevision

**Thread**：`id (thr_)`, `subject_kind ∈ {content, source_span}`, `canonical_subject_key (string，content 为 content_id；source_span 为上游 entity_id + "@" + artifact_revision_id)`；同主体唯一，跨 Edition 不合并。

**Comment**：

| 字段 | 类型 | 必填 |
|---|---|---|
| id | `cmt_` ID | ✔ |
| thread_id | `thr_` ID | ✔ |
| root_id | `cmt_` ID / null | ✔（depth 0 为 null） |
| reply_to_id | `cmt_` ID / null | ✔（depth 0 为 null） |
| depth | integer 0 / 1 | ✔ |
| author_id | 宿主账号 ID | ✔ |
| current_revision_id | `crev_` ID | ✔ |
| observed_publication_id | `pub_` ID / null | ✔ |
| status | enum `visible / deleted / hidden` | ✔ |
| created_at | timestamp（服务器） | ✔ |
| version | integer | ✔ |

不变量：depth=1 时 root_id 非 null 且 root 的 depth=0、同 thread；reply_to_id 非 null 时其 thread_id 相同且 root 相同；不得回复 status≠visible 的目标。排序键 `(created_at, id)`，id 按 UTF-8 字节序。

**CommentRevision**：`id (crev_)`, `comment_id`, `body (string, ≤ 4000 code points)`, `mentions (MentionRef 数组 ≤ 50)`, `parent_id (crev_ / null)`, `created_at`。

### 2.5 Reaction / Bookmark / ShareLink / Report

| 对象 | 字段 |
|---|---|
| Reaction | `id (rct_)`, `target_type ∈ {content, comment}`, `target_id`, `actor_id`, `value ∈ {like, dislike, null}`, `version (integer ≥ 0)`, `updated_at`。同 (target_type, target_id, actor_id) 唯一；取消保留 value=null 行 |
| Bookmark | `id (bmk_)`, `actor_id`, `target_type`, `target_id`, `active (bool)`, `version`, `updated_at` |
| ShareLink | `id (shr_)`, `target_type`, `target_id`, `created_by`, `created_at`, `revoked_at (timestamp/null)` |
| Report | **无业务 ID 前缀**（决定 D-NC002-03）：以创建它的 `command_id` 为文档键；字段 `command_id`, `reporter_id`, `target_type`, `target_id`, `reason ∈ {spam, abuse, copyright, other}`, `detail (string ≤ 500 cp)`, `created_at` |

## 3. 通知、命令与事件域

### 3.1 NotificationRecord

| 字段 | 类型 |
|---|---|
| notification_id | `ntf_` + SHA256_hex(E([event_id, recipient_id]))[:32]（DESIGN §6） |
| event_id | string（outbox 事件 ID） |
| recipient_id | 宿主账号 ID |
| target | object `{kind ∈ {content, comment}, id, thread_id?}` |
| delivery_state | enum §SM-7 |
| attempt_count | integer ≥ 0 |
| created_at / updated_at | timestamp |

### 3.2 NotifierDeliveryBinding、CommandRecord、BehaviorEvent、PseudonymMapping

字段与类型逐字取自 DESIGN §2.1.1（CommandRecord、NotifierDeliveryBinding）与 §11.2（BehaviorEvent）；本文不复制以免两处漂移。Schema 约束补充：

- CommandRecord.operation 取 DESIGN §2.1.1 列出的 17 个操作字符串闭集（content.publish/update/withdraw/trash/restore/purge、comment.create/edit/delete、reaction.set、bookmark.set、share.create/revoke、report.create、backup.begin/complete/delete）；`outcome ∈ {committed, rejected}`；`applied_version` 为 integer ≥ 0 或 null；`result_http_status` integer 100–599；`payload_hash` 64 hex。
- NotifierDeliveryBinding 文档 ID = `SHA256_hex(UTF8(notifier_delivery_id))`；`write_source ∈ {trusted_ingress, trusted_delivery_callback}`。
- BehaviorEvent.attributes 的字段全集由 NC-026 冻结；NC-002 的 Schema 只约束 §11.2 的外层字段与 `event_id` 格式，`attributes` 暂为 `type: object`（NC-026 收紧）。
- PseudonymMapping：`account_id`, `actor_pseudonym (psn_)`, `created_at`。

## 4. 字段归属与可见性（唯一性）

| 归属 | 对象 / 字段 | 规则 |
|---|---|---|
| P 私人 | Note 全部、NoteRevision 全部（含 parent_ids、change_summary、restored_from）、EditorSnapshot、Note.pending_op、Note.trashed_at | 只在本地 Drift 与密文备份；任何公共查询、公共快照、通知正文、命令账本都不得包含 |
| U 公共 | Publication、ContentAccess（除 author 私人信息）、ContentBinding、Thread、Comment、CommentRevision、Reaction、Bookmark（仅本人可读）、ShareLink | 服务器权威；读路径每次按 ContentAccess 重新鉴权 |
| S 服务端内部 | CommandRecord、NotifierDeliveryBinding、PseudonymMapping、Report、PurgeTask | 客户端不可直读；CommandRecord 只经命令查询端点返回最小结果 |
| A 分析 | BehaviorEvent | 只追加；不含任何内容字段（DESIGN §11.2 禁止清单） |

同一字段名只属于一个域：`change_summary` 只在 P；`version` 在 U/S 各对象独立计数；`content_id` 是跨域身份但不携带内容。

## 5. 限额常量（DESIGN §7.1，Schema 与测试共用）

| 常量 | 值 | 计量 |
|---|---|---|
| NOTE_MARKDOWN_MAX_BYTES | 1048576 | UTF-8 字节 |
| PUBLIC_BODY_INLINE_MAX_BYTES | 262144 | UTF-8 字节 |
| COMMENT_BODY_MAX_CODEPOINTS | 4000 | code point |
| ATTACHMENTS_PER_REVISION_MAX | 20 | 张 |
| ATTACHMENT_PLAINTEXT_MAX_BYTES | 10485760 | 加密前字节 |
| MENTIONS_PER_SUBMIT_MAX | 50 | 去重后有效条数 |
| LIST_LIMIT_DEFAULT / MAX | 20 / 100 | 整数；101 → 400 `invalid_argument.limit` |

全部闭区间：恰好等于通过，超一个单位拒绝，无静默截断。

## 6. 决定登记（NC-002，主 Agent 裁定，可被用户推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC002-01 | attachment_id 为对象存储不透明键 `^[A-Za-z0-9_-]{1,128}$`，不新增业务前缀 | DESIGN §2.1 的 17 项前缀已由用户确认，不再扩表；附件字节沿用既有对象存储 |
| D-NC002-02 | BindingRef.relation 枚举 `about / quotes`；target_kind 四值取自 LEARN_SYSTEM_TARGET §3.2 | 满足 PRD「对词条、主张、原句、扫描位置写注解」；D-06 定稿后只删不增 |
| D-NC002-03 | Report 无业务 ID，以 command_id 为键 | 避免新增前缀；举报天然一命令一记录 |
| D-NC002-04 | Selector 用 `selector/v0-provisional`，只含整数/字符串 | D-06 未冻结坐标类型；先保证编码可跨端复算，不宣称原句锚点已互通 |
| D-NC002-05 | Note.trashed_at 记设备时间，首次同步只允许被服务器时间推后 | DESIGN §4.4 回收站 T0 两类起算 |
| D-NC002-06 | Comment.created_at 为服务器时间；编辑不改 created_at | DESIGN §4.4 排序不跳动 |
