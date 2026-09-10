# 学习注解、读书笔记与评论系统：AI Agent 冷启动 Prompt

> 将本文件全文作为新 AI Agent 的首条任务输入。它用于调研、制定计划和后续受控开发，不代表已经批准任何具体技术实现。

> 开发文档已产出：先读 `openspec/annotation-community/PRD.md` → `DESIGN.md` → `PLANS.md` → `TASKS.md`。用户已确认默认规则与本期 Undo/Redo；完整键盘操作设计当前缺失，后续 F-01 承接，本期不扩展其他快捷键。下面历史调研顺序保留为背景，不能覆盖新版需求；Tasks 不等于 READY 执行包。

> 2026-09-10 范围更新：以下内容已按用户后续决议修正。本期包含真实账号下的私人端到端同步/云备份、公开社区、Flutter 阅读与 Markdown 笔记 UI，以及接真实后端的 Tooltip 原型。先读同目录 `SERVER_DATA_CONTRACT_DRAFT.md`、`BOOK_ASSET_DELIVERY_CONTRACT_DRAFT.md`、`PRIVATE_NOTES_STORAGE_DRAFT.md`；这些仍是草案，不是已实现能力。书籍上游协议待联合冻结，其他模块依据现存代码调查，不等待已离场的开发 Agent。

## 你的角色

你负责为 Learn System 规划并分阶段实现“学习注解、读书笔记与公开讨论”能力。你面对的不是一个孤立的通用评论区，而是一个消费 Learn System 发布数据、能够稳定锚定古籍原文和知识对象的学习社区系统。

第一阶段只做调研、规格、BDD、TDD、ACT 和执行工作包。工作包达到 `READY` 并经主 Agent 审查前，不得编写业务实现。后续实施必须由执行 Agent 严格按已批准工作包进行。

## 先理解总体数据流

```text
原始资料
→ Learn System 黑箱［识别、校验、整理；每阶段数据均留存］
→ 版本化 PublicationPackage
→ APP 后端
→ 客户端
   ├─ 排盘结果对应知识展示
   ├─ 古籍阅读／经典品读
   ├─ 私人注解与读书笔记
   └─ 公开分享、评论、回复与互动
```

Learn System 黑箱是知识编译工具。它不承载用户社区，也不直接保存评论。它输出带版本、查询契约、证据链和稳定身份的 `PublicationPackage`。APP 后端和客户端通过正式协议消费该发布包；不得直接读取黑箱工作目录、模型候选区或旧原型数据库作为线上知识源。

## 必读资料与顺序

在提出设计前完整阅读：

1. 根目录 `AGENTS.md`、`HANDOFF.md`、`PLAN.md`。
2. `README.md` 与 `LEARN_SYSTEM_TARGET.md`，理解最终产品与黑箱边界。
3. `openspec/learn-system-blackbox-architecture.md`，重点阅读 §1、§4、§8.1、§16、§17、§18。
4. `docs/blackbox-spec-rework/D-design.md` 的 D-06。
5. `openspec/subagent-delivery-gate.md`。
6. `openspec/legacy-storage-transition.md`。
7. `knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md` 的 UI、社区、私人注解和公开评论章节。
8. `pattern_knowledge_workbench/CONTEXT.md`、`GAP_ANALYSIS.md`、`TODO.md`、`MIGRATION.md`。
9. 调研 `/Users/jingtaiwei/Git/Public/xuan-migration/social`、`notification`、`xuan-storage`、`repository-rest-adapter` 及 `/Users/jingtaiwei/Git/Public/xuan-server/functions-py`；只把实际实现当作复用证据，不把其“普通帖子”模型直接当成知识锚定模型。

遇到文档冲突时，先列出冲突和来源，不自行静默裁定。最终 OpenSpec 高于历史讨论稿；尚处 `BACKLOG` 的设计不得写成“已经可用”。

## 已确认的产品目标

系统至少支持以下场景：

1. 用户在排盘知识详情、古籍阅读页或原始扫描页点击一个知识对象或原句，查看与它关联的注解和讨论。
2. 用户可对契约允许的知识对象与原句写私人注解；私人内容只能本人授权设备解密。扫描来源可作为证据定位，本期不新增任意圈画或区域标记工具。
3. 用户可以把自己的注解或读书笔记设为公开，让其他用户阅读、评论和回复。
4. 读书笔记是独立对象，不等同于一句原文后的短注解。它可以面向一本 `Work`、一个 `Edition`、章节或多个知识／原文锚点组织长篇学习内容。
5. 公开讨论支持两级 `Thread → Comment → Reply`；点赞/点踩互斥并可取消，收藏、分享、@、关注、资料、私信、举报、拉黑、通知、撤回和编辑历史均纳入本期；排盘命主、应验与终局反馈排除。
6. 不同书籍、版本和流派对同一格局或概念可能命名不同、解释不同甚至结论相反。讨论内容必须保留其所见版本、来源锚点和可选流派语境。
7. 用户内容与官方知识严格分层。评论、点赞和受欢迎程度不能改变 `Assertion`、`ReviewDecision` 或发布资格；高质量纠错只能生成 `EditorialIssue` 候选，重新进入知识审核流程。
8. 本期复用宿主真实账号，不另造登录系统；不支持匿名发表。私人内容本地优先，并支持端到端设备同步和加密云备份；公开发布和社交通知需要真实服务端链路。公开昵称身份不等于私人内容公开。
9. Embedding、向量召回和端侧模型不属于本任务前置。先保证确定性查询、稳定锚点、权限边界和版本迁移正确。

## Learn System 发布协议的接入规则

设计必须以 `PublicationPackage` 为唯一规范知识入口，并明确使用以下能力：

- `KnowledgeDataPack`：提供 `KnowledgeEntry`、`Concept`、`Pattern`、`Assertion`、流派视图等结构化知识。
- `RuleIndexPack`：提供排盘事实到适用知识的确定性查询材料。
- `EvidenceMapPack`：提供 `Assertion → SourceSpan → SourceAnchor → OCR 页／字框 → SourceAsset` 的证据链。
- `SourceAssetPack`：按 ReleasePolicy 提供原图、派生页图或可解析的受控引用。
- `QueryContractPack`：定义消费端如何按 FactSet、知识身份和来源条件查询；若尚未落地，必须作为依赖报告。
- `AnchorContractPack` 与 `IdentityMigrationMap`：计划由 D-06 冻结，用于注解跨 Release 迁移。它们当前仍是前置设计任务，不得假定已经实现。

所有锚定记录至少要在领域语义上区分：

- 稳定业务身份 `entity_id`；
- 用户创建内容时所见的不可变 `artifact_revision_id`；
- 发布版本 `release_id`；
- 锚点类型与锚点所属 Technique／Work／Edition；
- 锚点迁移结果：保持、迁移、合并、拆分、废弃或需要人工处理。

禁止只保存显示文本、书名、页码字符串或数据库行号作为长期锚点。旧工作台的 `notes` 字段不是 `Annotation` 或 `ReadingNote`，不得直接沿用其语义。

## 必须分开的领域能力

调研并给出清晰边界，至少覆盖：

- `Annotation`：锚定单个或少量知识／原文位置的短附注。
- `ReadingNote`：围绕书籍、版本、章节或多个锚点组织的长篇学习笔记。
- `DiscussionThread`：某个公开锚点或公开笔记的讨论容器。
- `Comment` 与 `Reply`：可审计的讨论内容与回复层级。
- `Reaction`：点赞/点踩互斥并可取消；不能替代知识证据或审核。
- `ModerationEvent`：举报、隐藏、恢复、封禁、申诉等可追踪处置。
- `VisibilityPolicy`：至少区分 `private` 与 `public`；如建议增加其他状态，必须说明真实产品价值和权限语义。
- `ActorProvider`：适配宿主身份与账号切换；线上动作不能用固定 local_owner 冒充鉴权身份。
- `AnchorResolver`：解析 PublicationPackage 锚点、显示创建时版本，并处理新 Release 的身份迁移。

不得把上述对象压缩成一张“帖子表”，也不得让一个可见性布尔值同时承担发布状态、审核状态和删除状态。

## 推荐的交付分期

### A. 契约前置

先完成 D-06 的 `AnchorContractPack` 和 `IdentityMigrationMap`，并定义 APP 消费端的只读 Anchor Resolver 接口。完成标准是：对每一种允许锚点，都能说明如何定位当前内容、如何回看创建时 Revision、以及合并／拆分／废弃时如何处理。

### B. 本地优先的私人学习

实现账号隔离的私人 Annotation 和 ReadingNote，包含 Markdown 输入、预览、保存和修订历史。已登录设备可离线编辑；端到端同步与加密云备份按 xuan-storage 实际协议接入。三个状态分开：本地已保存、设备已同步、云端已备份。Tooltip 只交付可接真实服务端的原型，不嵌入具体排盘模块。

### C. 公开分享与讨论

复用 `social` 中合适的帖子／回复基础能力，通过适配层接入知识锚点。公开能力必须同时具备后端持久化、权限检查、编辑历史、举报审核、隐私检查和删除／恢复审计；显式发布所选修订，不能把整条私人版本链直接公开。评论、回复与 @ 接入现有 notification。

### D. 本期验收与后续演进

本期验收离线保存、设备同步、云备份恢复、冲突留痕、跨 Release 锚点解析和真实社交链路。下一版增加原书/Markdown 分屏、Markdown 引用跳转和圈画；Embedding 与 EditorialIssue 回流不作为本期交付前置。上述阶段是实施顺序，不把已确认本期能力重新降为未来预留。

## 第一阶段必须产出的文档

先调研，随后提交以下内容，不写实现代码：

1. 现状调查：现有 Learn System 发布协议、工作台缺口和 `social`/`notification`/`xuan-storage` 可复用／不可复用清单。
2. 正式规格草案：建议路径 `openspec/annotation-notes-community.md`，包含领域模型、状态机、权限、锚点协议、API 边界、存储边界、同步与审核。
3. 架构决策记录：明确“单机私人内容”和“在线公共内容”的分界，以及为何不把 UGC 写回 PublicationPackage。
4. 实施计划：按可独立验收的纵切拆分，列出真实文件路径、依赖、风险和先后顺序。
5. 工作总表：在现有 Subagent 监控体系中登记大项和小项。
6. 第一个执行工作包：按 `openspec/subagent-delivery-gate.md` 建立 README、BDD、TDD、ACT、PROMPT、ACCEPTANCE 六件套，并通过 `wjt-react` 达到 `READY`。

## BDD 必须覆盖的核心行为

- 私人注解只能由本人读取，任何公共查询都不能返回。
- 公开笔记可被其他用户查看并进入 Thread／Comment／Reply。
- 从排盘知识或古籍原句创建内容后，可以返回对应 KnowledgeEntry、Assertion、原文和扫描位置。
- 新 Release 到来后，旧内容仍显示创建时 Revision，并根据 IdentityMigrationMap 解析当前锚点。
- 锚点被合并、拆分或废弃时不得静默错绑；无法自动迁移时进入明确的待处理状态。
- 评论、Reaction 和热度不会修改官方知识、证据等级或发布审核状态。
- PublicationPackage 缺失、版本不兼容或证据引用不可解析时 fail closed，并向用户显示可理解状态。
- 已登录账号离线可保存；换账号不泄漏前一账号正文、密钥、待同步操作或通知回执。
- 旧 `notes` 数据未经显式迁移和校验时不能冒充新注解或读书笔记。

## 调研与设计约束

- 优先复用开源组件和 `social` 已有能力，先证明可复用边界，再决定自研。Markdown 渲染指定 `flutter_markdown_plus`。
- 本期设计 Flutter 阅读、原句注解和独立笔记 UI；Tooltip 设计真实交互原型及 UI 调用协议，不制作最终业务嵌入组件。
- 正规知识数据只读；UGC 使用独立存储、独立 API 和独立审核状态机。
- 私密到公开必须是显式用户动作，并经过服务端权限与内容策略检查。
- 删除采用可审计语义；公开内容、回复和 Reaction 的计数变化不得破坏历史追踪。
- 不把“用户可以公开”误写成“当前阶段立即无条件开放公共评论”。公开阶段必须明确列出运行前置和验收门禁。
- 不设计微服务。以单体后端／模块化单机方案为默认，同时保留可替换 Provider 与 Repository 接口。

## 停手条件

出现以下任一情况时停止设计或实施并报告：

- D-06 锚点白名单或迁移语义仍有相互冲突的权威定义；
- 实际接线与公开文档矛盾，且缺少可验证的实现依据；记录具体缺口，不把存在接口当作已接通；
- 需要新增用户尚未批准的外部服务、付费依赖或身份系统；
- 必须改写 PublicationPackage 才能实现评论功能；
- 任务范围扩张到用户未授权的推荐算法、Embedding 或具体排盘模块嵌入；
- 测试只能依赖临时 Mock 而不能证明真实权限、锚点和迁移语义。

## 首次汇报格式

首次回复只提交调研与计划，不提交业务实现：

```text
已理解的系统边界：
现有协议中可直接使用的部分：
仍未完成的前置协议：
social/notification/storage 可复用／不可复用部分：
建议的领域对象与边界：
分期计划与严格依赖顺序：
第一个准备制作的工作包：
需要用户拍板的问题（只列会实质改变方案的事项）：
```

最终目标是让用户从排盘知识或古籍原文出发，稳定保存私人学习成果、选择公开分享、参与基于同一证据锚点的讨论，并确保这些用户内容在知识版本升级后仍然可解释、可迁移、可审计。
