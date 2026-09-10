# 笔记、原句注解与讨论：服务端数据契约协作草案

状态：`DRAFT_FOR_CROSS_AGENT_REVIEW`。更新：2026-09-10。

用途：交给负责书籍元数据、正文与 PublicationPackage 生成的 Agent 回执。本文不是已冻结 Schema，也不是实施授权；字段为消费侧提案，现有 OpenSpec 的身份与发布语义优先。双方确认后再生成正式 OpenAPI、JSON Schema、BDD 与执行工作包。

## 1. 请上游 Agent 先完成的回执

1. 阅读 §2–§5，以及 [原件与阅读资产直接入库协议](BOOK_ASSET_DELIVERY_CONTRACT_DRAFT.md)，对 §9 的 U-01～U-09 和资产协议 A-01～A-06 逐项回复 `ACCEPT`、`CHANGE` 或 `UNAVAILABLE`。
2. 每项附上真实生成代码、Schema、样例包路径；给出实际字段名、类型、必填性、版本规则和修改建议。
3. 提供一份可由另一台机器读取的最小样例：一个 Work、一个 Edition、一个分部、两个重复句子所在的不同位置、一个知识对象与原文关系；另给一次修订和一次拆分的前后包与迁移记录。样例缺失要明确报告，不用伪造正式 ID 或发布状态。
4. 双方统一字段映射后，才能冻结导入和锚点协议。回执建议写入同目录 `UPSTREAM_DATA_CONTRACT_REPLY.md`，由用户安排对应 Agent 执行。

## 2. 已确认范围与边界

- 客户端 Flutter，Markdown 渲染采用 `flutter_markdown_plus`，本地持久化沿用 Drift / Repository 分层；业务请求沿用 REST/JSON 和 OpenAPI 3.1，Swagger UI 从同一契约生成文档。
- 后端沿用 `/Users/jingtaiwei/Git/Public/xuan-server/functions-py` 的 Python Firebase Functions 组织与现有 Firestore；不新增一套数据库服务。
- 正式 UI 覆盖原书阅读、原句注解和独立 Markdown 笔记。Tooltip 交付可接真实后端的原型、数据契约和互动链路，不处理最终样式或在占卜盘面中的嵌入。
- 原句注解与明确关联的笔记在阅读端、知识关联的 Tooltip 端互通；按关系查询同一内容，不复制讨论。整部书关联不能推导为每个知识点都应展示。
- 笔记、注解默认私密，可显式公开、更新发布、收回私密；评论与两级回复随公开讨论可见。账号昵称身份可追溯，不支持匿名；私密内容不因此变为公开。
- 保存编辑历史，作者读取完整历史，公众只读取当前仍允许公开访问的已发布版本。恢复旧版生成新修订。
- 点赞/点踩、收藏、分享、@、作者资料、关注、举报、拉黑、私信及通知联动属于范围；排盘应验、终局反馈等专属功能排除。
- 下一版才做原书/Markdown 分屏、Markdown 引用跳转与圈画。当前原句注解必须保存准确位置；基础原句定位不后置。
- 私人笔记云端备份与跨设备同步是否本期启用：等待用户决策；本地保存不受此决策阻断。

## 3. 数据所有权与服务端存储分区

| 数据 | 权威生产者 | 服务端角色 | 修改权限 |
|---|---|---|---|
| Work、Edition、分部/章节、正文、来源定位 | 上游知识编译与发布模块 | 验证后导入只读投影，提供查询 | 社区接口无修改权 |
| KnowledgeEntry、Assertion、证据与知识到原文关系 | 上游发布模块 | 导入并维护可验证的关联查询 | 仅通过新发布包更新 |
| 发布版本与身份迁移映射 | 上游发布模块 | 校验、激活、保留旧版本查询 | 导入身份受限；普通用户不可写 |
| Markdown 笔记、注解、评论、互动 | APP 用户经 Python 后端授权 | 独立 UGC 集合持久化 | 作者/审核者按具体操作鉴权 |
| 本地草稿、修订和待同步操作 | 客户端 Repository | 只有启用同步且鉴权通过才接收 | 按账号隔离 |
| 通知记录、投递事件 | 业务事务及现有通知系统 | 持久化、投递、补拉、回执 | 接收者仅能读自己的通知 |

Firestore 存可索引的元数据、关系、权限和内容记录；大文件沿用既有媒体/对象存储能力。正文按发布块组织，完整长文修订若超过文档限制则写不可变对象并保存受控引用和哈希。具体大小门槛及既有对象存储接口在实施前核实，不把整部书或无限历史放进单个文档。

书籍投影与 UGC 分离；UGC 不写回 PublicationPackage。用户纠错只能成为未来审核候选。上游包的位置不能直接是面向客户端的本机工作目录或未受控 URL。

## 4. 上游发布数据的消费需求

下表是消费侧最小逻辑字段，不要求上游改成同名物理表。共同交付字段在生成前冻结；保留必要的存储类型映射，但不把书籍格式转换、拆章、重编码或重新切句留给服务端。身份值必须保留。PDF/影印/EPUB/TXT 的原件、派生阅读数据及入库存储详见 [资产交付协议](BOOK_ASSET_DELIVERY_CONTRACT_DRAFT.md)。

| 对象 | 要求的逻辑字段 | 必须确认的语义 |
|---|---|---|
| Release | `release_id`, `schema_version`, `canonical_hash`, `manifest_ref`, `validation_ref`, `consumption_level`, `published_at` | 正式/开发包隔离；哈希算法、验证方式与依赖清单 |
| Work | `work_id`, `title`；作者、别名、语言可选 | 稳定作品身份；未知元数据用明确缺失状态，不臆造 |
| Edition | `edition_id`, `work_id`, `label`, `artifact_revision_id`, `release_id`, `rights_ref` | 底本与一次数字修订分开；ID 是否映射既有 Source |
| ReadingUnit | `unit_id`, `edition_id`, `parent_unit_id?`, `kind`, `title`, `order_key` | 面向阅读的卷/章结构；不能直接假定等于 Gate 的 EditionPart |
| TextBlock | `block_id`, `edition_id`, `unit_id`, `artifact_revision_id`, `release_id`, `text`, `text_hash`, `order_key` | 可稳定排序并精确选择的正文范围；block 与 SourceSpan 的映射、Unicode 计数规则 |
| SourceSpan | `entity_id`, `edition_id`, `artifact_revision_id`, `release_id`, `block_ranges`, `source_anchor_refs` | 原句证据切片与阅读块允许不同粒度；不能依据显示行号猜 ID |
| SourceAnchor / SourceAsset | 身份、修订、页身份、资源哈希、坐标/文本映射、尺寸/旋转、权利和资源档位 | 引用可解析时才承诺打开原书；本期不新增任意圈画 |
| KnowledgeReference | 类型、稳定 `entity_id`, `artifact_revision_id`, `release_id`, `technique_id` | KnowledgeEntry/Assertion 到 SourceSpan 的显式关系及基数 |
| IdentityMigrationMap | 来源/目标 Release，旧身份，新身份列表，变化类型，证据/规则版本 | 保持、迁移、合并、拆分、废弃的确定规则；无唯一目标时需人工处理 |

Work、Edition、ReadingUnit、TextBlock 的字段名和 ID 格式尚未由本草案冻结。`entity_id`、`artifact_revision_id`、`release_id` 按现有架构 §8.1；不重命名现有前缀。`artifact_revision_id` 若指向整个包而非单实体，需要上游提供“该修订内按 entity_id 取记录”的确定契约。

### 4.1 导入、激活与旧版本

提案：`received → validating → ready → active`；校验失败进入 `rejected`，被替换的激活版本保留为 `retained`。这些是 APP 导入状态，与知识成熟度状态分开。

- 以 `release_id + manifest_hash` 判定重试：同 ID 同哈希幂等，同 ID 异哈希拒绝。
- 在隔离导入区核对 Schema、对象数量、引用闭合、哈希、权利、兼容版本及所需查询能力后，才原子切换当前 Release 指针。
- 验证失败保持旧版服务；读取一次请求固定一个 Release，不能混合新版正文与旧版锚点。
- 导入大包不假设一次 Functions HTTP 请求足够。注册/分批导入/校验/激活的任务方式按现有任务能力选择，状态必须可恢复。
- 历史注解固定其创建时 Revision；新包只改变“当前定位结果”，不覆盖原始锚点。
- 因权利撤回无法继续提供旧正文时，保留身份和不可访问原因；不保证永久分发受限原件。

## 5. 共同锚点契约（提案）

`AnchorRef` 核心字段：

| 字段 | 类型/要求 | 含义 |
|---|---|---|
| `anchor_ref_id` | UGC 稳定 ID | 本次引用记录身份，非上游知识身份 |
| `target_type` | `knowledge_entry / assertion / source_span / source_anchor` | 来自 D-06 白名单候选；以最终 AnchorContractPack 为准 |
| `entity_id` | 非空字符串 | 上游稳定业务身份 |
| `artifact_revision_id`, `release_id` | 非空字符串 | 作者当时看到的修订及发布版本 |
| `work_id`, `edition_id`, `technique_id` | 按目标条件必填 | 原文目标必须有 Work/Edition；跨书知识目标不伪造唯一 Edition |
| `selector` | 原句选区时必填 | 见下方；知识对象整体注解可以省略 |
| `source_anchor_refs` | 引用数组 | 可选扫描位置；不可解析时显示明确状态 |
| `created_at` | 服务端 UTC 时间 | 创建记录，不替代发布版本 |

`selector` 提案：`text_block_id`, `text_hash`, `offset_unit`, `start`, `end`, `exact`, `prefix`, `suffix`。区间为 `[start,end)`，建议 Unicode code point；Dart UTF-16 下标必须显式换算，不能直接上传。规范化规则、跨块选区表示和原文逐字一致性由 U-04/U-05 联合冻结。保留权威原文，不私自繁简转换或去标点。

解析结果另存 `AnchorResolution`：`anchor_ref_id`, `target_release_id`, `state`, `resolved_targets`, `migration_map_ref`, `resolver_version`, `reason`。候选状态：`unchanged / migrated / merged / split / retired / needs_review / unavailable`。

文本引文和前后文仅用于核验与辅助定位，不能替代稳定身份或授权任意跨版本模糊匹配；多处同句、拆分或歧义不自动选第一个。范围变换需要上游映射或显式人工确认。

独立笔记使用 `ContentBinding` 关联 Work/Edition/ReadingUnit/KnowledgeReference/AnchorRef；这是笔记分类/关联，不擅自扩大 D-06 原文锚点白名单。无关联笔记仍可保存和发布。

## 6. APP 服务端 UGC 数据结构（候选集合）

以下 `community_*` 名称仅为隔离建议，实际前缀经现有集合注册约定确认。ID 为不透明稳定值；UGC 的 `content_revision_id` 与上游 `artifact_revision_id` 分开。

| 逻辑集合 | 主要字段 | 约束 |
|---|---|---|
| `community_contents` | `content_id`, `kind: note/annotation`, `author_app_user_id`, `visibility: private/public`, `lifecycle: active/deleted`, `moderation_state: pending/allowed/hidden`, `head_revision_id`, `published_revision_id?`, `concurrency_rev`, 时间 | 容器不存未发布正文；身份由现有服务端认证解析，不信任客户端作者字段 |
| `community_content_revisions` | `content_revision_id`, `content_id`, `parent_revision_id?`, `title`, `body_format: markdown/plain_text`, `body_inline` 或 `body_ref`, `body_hash`, `editor_id`, `change_summary?`, `created_at`, `restored_from?` | 不可变；每次有效保存新增修订；自动保存可归组展示但不覆盖已持久修订；引用和 @ 随修订保存 |
| `community_publications` | `publication_id`, `content_id`, `content_revision_id`, `published_at`, `withdrawn_at?` | 记录曾发布事实；允许公众读取仍须当前容器公开且审核允许，不能只检查曾经发布过 |
| `community_bindings` | `binding_id`, `content_id`, `content_revision_id`, `target_kind`, `target_ref`, `relation` | 草稿关联仅作者可查；公共关联索引从当前发布修订生成，不能提前暴露未发布引用 |
| `community_anchors` / `community_anchor_resolutions` | §5 字段 | 原始引用与迁移结果分开 |
| `community_threads` | `thread_id`, `subject_kind: content/knowledge_anchor`, `subject_ref`, `created_at` | 内容讨论按 content_id；知识讨论按明确类型及锚点语境的规范键去重。最终跨版本聚合键依赖 U-06 |
| `community_comments` | `comment_id`, `thread_id`, `root_comment_id?`, `reply_to_comment_id?`, `depth: 0/1`, `author_app_user_id`, `head_revision_id`, `observed_publication_id?`, `observed_release_id?`, 状态/时间 | root 为 0；楼内均为 1，可回复同楼任意有效对象；服务端检查同 thread/root；读写继承主题访问权限 |
| `community_comment_revisions` | `revision_id`, `comment_id`, `parent_revision_id?`, `body`, `mentions`, `edited_at`, `editor_id` | 编辑留痕，删除保留墓碑；审核隐藏正文不因历史接口而泄漏 |
| `community_reactions` | `target_type`, `target_id`, `actor_id`, `value: like/dislike`, `updated_at` | 唯一键为目标+用户；取消则无当前记录；切换互斥，变更留事件；计数为可重建投影 |
| `community_bookmarks` | `actor_id`, `target_type`, `target_id`, `created_at` | 个人收藏；目标收回后只显示不可见占位，不返回旧正文 |
| `community_share_links` | `share_id`, `target_ref`, `creator_id`, `created_at`, `revoked_at?` | 分享链接不绕过当前 ACL；不将私密对象 URL 当作访问授权 |
| 现有关系/举报/媒体模块的扩展 | 关注、拉黑、举报、媒体授权 | 优先复用；增加 content/comment 目标适配，不能直接塞成普通 post 丢掉锚点 |
| 现有 outbox / 通知投影的扩展 | `event_id`, `event_type`, `actor_id`, `recipient_id`, `target_ref`, `content_revision_id?`, `dedup_key`, 时间 | 评论/回复/@ 产生事件；UI 来源不影响通知语义；投递 ID 与事件 ID 不混同 |

独立 Markdown 文档不限制只能写读书内容。附件需要与当前访问者和内容可见性绑定；媒体库原有公共 URL 不能直接用于私人附件。长文、评论和附件限额在规格阶段结合现有媒体规则冻结。

### 6.1 写入与可见性事务

- 私密保存：新增不可变修订并更新 head；不触发公共索引、@ 通知或公开正文变化。
- 已公开内容保存：只更新作者 head；公众继续读取 published 指向的修订。
- 发布：校验作者、预期版本、正文/附件权限、绑定和内容策略；原子记录 publication、更新公开指针，并持久化 outbox。大附件必须先就绪，不能在事务中上传。
- 收回：原子关闭公开权限，记录事件，再异步清理派生索引/缓存。即便清理未完成，所有公共读取仍以当前 ACL 拦截；正文、历史、关联查询、附件及分享入口都受限。
- 评论/回复：检查主题当前可见/可写，原子持久内容与通知事件；避免收回并发时落入无权限讨论。客户端不能把两个 REST 请求当成事务。
- 相同命令重试使用现有 `Idempotency-Key`；编辑使用现有版本前置条件；本地保存与远端发布状态分开。
- 原子 outbox 后由消费者幂等扇出；同事件同接收人（作者、回复对象、@对象重合）只创建一次通知；不通知自己，检查拉黑、偏好和事件时/投递时访问资格。
- 接收落盘成功才 ACK，ACK 不等于已读；实时、唤醒拉取和补拉共用现有接收管线。系统通知栏沿用无正文唤醒策略。
- 撤回无法抹去别人已合法下载、截图或离线持有的字节。承诺为服务端立即拒绝后续访问，在线客户端失效、离线端重连对账；公共缓存离线可读策略须另行冻结，不能承诺瞬间远程擦除。

## 7. REST、Schema 与本地 Repository 对应

沿用现有 `repository-rest-adapter/openapi/openapi.yaml`（OpenAPI 3.1.0）；最终文件拆分方式跟随该工程，保持一个权威契约入口。下表为逻辑操作族，URL/operationId 冻结时沿用当前资源及 `:action` 约定。

| 操作族 | 输入/输出要求 | 持久化边界 |
|---|---|---|
| 书目/版本/阅读块/知识关系查询 | 固定 Release、分页游标、来源与可用性；禁止返回未激活导入区 | 服务端只读投影；Drift 本地阅读投影 |
| 锚点创建校验/解析 | AnchorRef、当前解析结果、缺失或歧义原因 | 原始锚点与解析结果分存 |
| 私人内容创建/保存/历史/恢复 | 内容修订、版本前置条件、幂等键；明确私人 DTO | Drift 持久草稿；是否远端备份待用户决定 |
| 发布/更新发布/收回/删除 | 原子业务命令与权威结果，不接受直接改可见性字段绕过校验 | Python 服务端事务；Drift 操作日志和回填 |
| 公共内容/关联讨论/发布历史查询 | 仅已发布版本，查询时 ACL，分页 | 公共投影缓存与私人数据隔离 |
| 评论/楼内回复/编辑/删除 | 同楼校验、版本、结构化 mentions、观察时版本 | 内容+outbox；楼内分页不压成一整条文档 |
| Reaction/收藏/分享/举报 | 通用目标、当前用户状态、命令结果 | 复用现有能力并扩展目标类型 |
| 通知正文/游标补拉/已读 | delivery_id、授权接收者、不透明 cursor、目标定位 | 对接 MessageBodyFetcher/BackfillSource；DeliveryLog 本地可靠保存 |

OpenAPI 覆盖身份要求、请求/响应、错误、枚举、空值、分页、幂等、版本冲突和实例。Swagger UI 为其展示，不另写不同步的接口事实。Domain Model、REST DTO、Firestore 文档、Drift 行各有映射，不直接暴露数据库行作为公共 DTO。

复用 Repository 的 CRUD/软删/分页语义；发布、跨记录权限和通知事务保留业务命令。Drift 区分私有持久数据、公共缓存、待同步命令与通知投递记录；登出/换账号不能把前一账号草稿和 ACK 队列交给新账号。不同设备冲突保留分支/显式处理，不静默覆盖修订。

## 8. 已知接入依赖与验收边界

- D-06 的 AnchorContractPack / IdentityMigrationMap 尚待联合冻结；现有 ID 规则不能替代选区和迁移规则。
- `notification/docs/integration-guide.md` 指出业务正文拉取、补拉及具体适配缺口；不可把“存在端口”当作推送已通。指南关于 ReceiptRejected 存在矛盾，当前 `ack_pipeline.dart` 是整批停止并报告，冻结前需通知维护者确认。
- 现有旧 Firestore 通知 Repository 已弃用；不要恢复该路径来伪装已完成。
- 已有 Social 的点踩/分享/订阅部分只是展示或本地状态，须逐项映射现有真实服务端能力。
- 本草案只有设计检查，不代表真实存储、权限、Swagger 页面或推送已部署。

联合验收必须证明：导入失败不换当前包；历史 Revision 可定位；重复引文不误绑；拆分不自动猜；私密草稿和草稿关联不泄漏；公开后编辑不提前公开；收回后正文/历史/分享/附件都拒绝新访问；评论与通知事件同成败；重试不重复互动或通知；接收落盘失败不 ACK；两个入口查询相同内容；Drift 重启可恢复私人保存。

## 9. 上游待回执表

| 编号 | 要确认的事项 | 当前消费侧建议/未决点 |
|---|---|---|
| U-01 | Work / Edition / Source 的实际 ID、字段和生成代码 | 保留上游 ID，显式映射，不根据书名拼 ID |
| U-02 | 卷、章、EditionPart、阅读块之间的关系 | 阅读结构与加工 Gate 粒度分开 |
| U-03 | SourceSpan / SourceAnchor 白名单与稳定性 | 提供 AnchorContractPack 和最终 D-06 定义 |
| U-04 | 正文 offset、Unicode、规范化与 text_hash | 明确 Python/Dart 一致规则及繁简/异体/换行处理 |
| U-05 | 用户任选片段不等于一个 SourceSpan 时如何定位 | 范围锚定既有稳定对象，跨块/跨 Span 范围的合法表示 |
| U-06 | KnowledgeEntry/Assertion 到原文关系；跨版本讨论聚合 | 显式发布关系；不同 Edition 同文不自动合并讨论 |
| U-07 | 拆分/合并/废弃迁移表及精确修订查询 | 旧版可回看；歧义进入待处理，不仅给新旧 ID 名单 |
| U-08 | 包获取、激活、权限与原书资源服务 | 包格式、清单/哈希验证、授权资源引用、历史保留和撤权行为 |
| U-09 | 可运行真实样例与可用时间 | 给实际路径、版本与缺口；不能用开发包冒充正式发布 |

## 10. 来源与后续步骤

本地权威：`openspec/learn-system-blackbox-architecture.md` §8.1/§16，`docs/blackbox-spec-rework/D-design.md` D-06，`openspec/legacy-storage-transition.md`，`openspec/subagent-delivery-gate.md`。最新用户决议覆盖冷启动文档中“本期无 UI”和单机优先的范围假设。

现有接入参考：
- `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter/openapi/openapi.yaml`
- `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter/README.md`
- `/Users/jingtaiwei/Git/Public/xuan-migration/notification/docs/integration-guide.md`
- `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage/drift/lib/playground/playground_post_cache_store.dart`
- `/Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/handlers/playground_rest.py`

外部参考仅用于借鉴，不替代本项目契约：[W3C 文本选区与状态](https://www.w3.org/TR/selectors-states/)、[Notion 发布及撤销链接访问](https://www.notion.com/help/public-pages-and-web-publishing)。

顺序：上游回执 → 对齐数据与锚点 → 用户确定私人云同步范围 → 冻结正式规格/OpenAPI/Drift 映射 → 制作 BDD/TDD/ACT 工作包 → 审查 READY → 分阶段实现与真实链路验收。阅读 UI 与不依赖未决字段的原型讨论可继续；不得先实现互不兼容的两套书籍模型。
