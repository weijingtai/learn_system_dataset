# PLAN

## 注解社区线：跨 Agent 数据契约（2026-09-10）

- [x] 补充 `docs/annotation-community/BOOK_ASSET_DELIVERY_CONTRACT_DRAFT.md`：影印/PDF/EPUB/TXT 原件与阅读材料、对象存储/Firestore 分工、统一生成交付格式、A-01～A-06 回执；仅草案。
- [ ] 上游确认资产交付 A-01～A-06，确保下游不再二次 OCR、拆章、重编码或重分块。

- [x] 整理服务端数据结构协作草案：`docs/annotation-community/SERVER_DATA_CONTRACT_DRAFT.md`，包含上游书目/正文/版本消费要求、UGC 结构、REST/Drift/通知边界和 U-01～U-09 回执表；状态仅为讨论草案。
- [ ] 收到上游 Agent 的真实 Schema、生成代码和样例包回执，对齐书目 ID、选区、版本与迁移契约。
- [ ] 用户确认私人笔记云备份/跨设备同步是否本期启用。
- [ ] 对齐后冻结正式规格与 OpenAPI，准备可审查工作包；此前不实施业务代码。

本节为独立讨论线，不取代下方黑箱返工执行序列。

更新时间：2026-09-09（Subagent 交付闸门启用）

## 黑箱架构规格 R1 审查返工项（阻断进入 tasks 阶段）

> 审查对象：`openspec/learn-system-blackbox-architecture.md`（commit `6e30031`）
> 审查日期：2026-09-08；四角色独立审查（架构 / 验收 / 用户体验 / 规划）
> 结论：**不通过**。规格骨架正确，但缺少拆解 tasks 所必需的可判定性、粒度定义与素材裁定。
> 本节全部结清前，不得启动 M1-M8 任何 Module 的实现任务。

### RN 决议落地后新产生的耦合（R1 复核 2026-09-08 追加，3 条）

> 这三条不是原 40 条的重复，是 7 项架构决议写入规格**之后**才出现的内部不一致。
> 均已逐条验证存在。建议与第一批返工一并处理。

- [x] 修复: `openspec/learn-system-blackbox-architecture.md:388（§20 第 8 条）` 与 `:318（§16 SourceAssetPack）` 冲突：完成标准仍写「PublicationPackage 同时包含结构化知识、**原始资料**及其关系」，而新增的 `reference_and_hash_only` 档只携带引用、SHA-256、页标识和权利说明，并不携带原始资料本身；该档下第 8 条是算满足还是算不满足，规格未答 ｜ 通过标准: §20 第 8 条改写为按 SourceAssetPack 档位分别表述（例如：`full_scan`/`derived_page_images_only` 视为满足，`reference_and_hash_only` 需同时提供可解析该引用的本地或受权后端才视为满足），且 `grep -n "原始资料" openspec/learn-system-blackbox-architecture.md` 的每一处都能对应到一个明确档位
- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§2 原则 7` 与 `:83（§4 KnowledgeEntry 字段）` 冲突加剧：原则 7 仍写「不复用旧 ID」，而 D-05 决议已引入 `concept_id`、`pattern_id`、`entry_id`、`subject_entity_id` 与「身份迁移状态」——若 Pattern 每次 Revision 换 `pattern_id`，`subject_entity_id` 即刻断链，KnowledgeEntry 无法稳定指向其主体。**D-01（entity_id / artifact_revision_id 拆分）由「应做」升级为「必须先于其余 D 类完成」** ｜ 通过标准: 见 `docs/blackbox-spec-rework/D-design.md` D-01 判据；追加一条 `grep -A3 "原则 7\|^7\. 任何修改" openspec/learn-system-blackbox-architecture.md | grep -q "artifact_revision_id"` ｜ 依据：§2 原则 7、§8.1「标识与修订语义」
- [x] 修复: `openspec/learn-system-blackbox-architecture.md:108（§5 Review Console）` 要求「人工决定始终归属发起该队列的 ProcessingRun、StepRun 和 Stage」，且 §14 定义了 M3/M4/M6/M7 四种人工模式，但 `§7` 的 `execute(StepRequest)→StepResult` 仍是单次同步语义、无挂起态——StepRun 无法表达「正在等人」。注意 `:331` 已经在 Ledger 故障场景用了「挂起 StepRun」这一措辞，说明该概念已被隐式引入却从未定义。**D-03（StepRun 生命周期状态机）由「应做」升级为「Review Console 的前置」** ｜ 通过标准: 见 `docs/blackbox-spec-rework/D-design.md` D-03 判据；追加 `grep -c "awaiting_human" openspec/learn-system-blackbox-architecture.md` >= 1，且 §17:331 的「挂起」改为引用该状态机的正式术语 ｜ 依据：§7.1「StepRun 生命周期与人工恢复」、§8.2 两张独立状态全集表、§17 `suspended` 持久恢复语义

### 执行入口（2026-09-08 转译 v1）

**不要直接照本节的 40 条开工**——它们是「要求」，不是「怎么做」。
已转译为可直接执行的指令，见 `docs/blackbox-spec-rework/`：

| 文件 | 内容 | 执行者要求 |
|---|---|---|
| `docs/blackbox-spec-rework/README.md` | 入口、已定事项、已批准架构决议、转译说明 | 先读这个 |
| `docs/blackbox-spec-rework/act/01.yaml` | R0-1 本地库不再被启动覆盖 | 便宜模型 |
| `docs/blackbox-spec-rework/act/02.yaml` | R0-2 保存与 AI 产物不再自动 verified | 便宜模型 |
| `docs/blackbox-spec-rework/act/03.yaml` | R0-3 前半：删零引用的 enumeration | 最便宜模型 |
| `docs/blackbox-spec-rework/act/04.yaml` | R0-3 后半：剥离 ai_core 聊天，ACT 03 后开工 | 较强模型 |
| `docs/blackbox-spec-rework/T-transcribe.md` | RA/RB/RD/RE/RF 中 13 条转录型，答案已在既有文档，给了精确坐标 | 中等模型 |
| `docs/blackbox-spec-rework/D-design.md` | 19 条设计型，含约束边界、判据、已否决方案、执行顺序 | 较强模型 |
| `docs/blackbox-spec-rework/verify-T.sh` | T 类机器判据，退出码 = FAIL 数 | — |

**2026-09-08 初始基线**：`bash docs/blackbox-spec-rework/verify-T.sh` → 19 FAIL / 1 PASS。每完成一条 T 类，FAIL 减一。

**2026-09-09 G3 交叉验收 R1**：机器门禁已到 0 FAIL，但语义审查结论为 6 通过 / 6 返工或阻断。通过：T-01/T-03/T-05/T-09/T-10/T-12；返工：T-04/T-06/T-11/T-13；阻断：T-07/T-08（先完成 D-07）。证据见 `docs/blackbox-spec-rework/reviews/G3-REVIEW-R1.md`。

**当前第一执行序列**：`D-01`、`D-03`、`T-02`、`D-02` 已验收。下一步先准备 R0 依赖解锁工作包，严格按 `ACT 03 → ACT 04` 执行；因既有 `ai_core` 传递依赖冲突，ACT 03 只做引用与精确差异检查，待 ACT 04 移除全部内网依赖后，对两项合并执行 `flutter pub get`、`flutter analyze` 与 `flutter test` 准出门禁。随后再分别准备并执行 ACT 01、ACT 02 的真实 Red→Green 工作包。主 Agent 只制作规格、BDD、TDD、ACT、Prompt 并独立验收，不编写业务实现。

**7 项架构决议已由用户于 2026-09-08 批准**：单机 Ledger 本地进程；Pattern 是 Concept 的可规则识别子类、KnowledgeEntry 是发布视图；EditionPart 优先按卷；现有工作台提升为 Review Console；校订事实/corpus 迁移、派生索引重跑、旧知识库冻结；原件进入本地 Object Store 且分发受 ReleasePolicy 控制；工作台 AI 聊天剥离并在未来由 M4 Model Adapter 取代。旧存储和旧路径的权威说明见 `openspec/legacy-storage-transition.md`。

**转译覆盖对照 v1**：R0→ACT 01/02/03/04（含 1 条异议）；RA→D-01~D-04 + T-02/T-03；
RB→D-05~D-08 + T-01/T-06/T-07/T-08；RC→D-09~D-13 + T-09/T-10；RD→T-04/T-05 + D-08；
RE→T-11 + D-18；RF→D-14~D-17 + T-12/T-13；RG→D-19。**覆盖完整，无遗漏条目。**

**转译者异议已裁定**（见 README）：① 工作台 AI 聊天选择剥离，R0-3 原通过标准恢复可达；② RG 版权与存储边界正式纳入本轮，采用 Git / 本地 Object Store / PublicationPackage 三层方案。

### R0 零号批次（不依赖任何前置，可立即开工）

- [x] 修复: `pattern_knowledge_workbench/lib/database/drift_database.dart:28-29` 启动时用 asset SQLite 覆盖本地库，人工校订与审计历史被静默销毁，直接否定规格 §20 第 2、3 条 ｜ 通过标准: `grep -c "rootBundle.load('assets/ge_ju_database.sqlite')" lib/database/drift_database.dart` 返回 0；且新增 widget test「写入本地库 → 重启 → 数据仍在」由红转绿
- [x] 修复: `pattern_knowledge_workbench/lib/pages/rule_list_page.dart:1202,1802` 规则保存与 AI 产物直接写 `isVerified: const Value(true)`，绕过审核状态机 ｜ 通过标准: `grep -c "isVerified: const Value(true)" lib/pages/rule_list_page.dart` 返回 0；AI 产物落入 candidate 态的测试转绿
- [x] 修复: `pattern_knowledge_workbench/pubspec.yaml:62,66,86` 依赖私有内网 Git `192.168.0.165:3000`，干净环境无法构建，导致后续任何验收命令在他人机器不可执行 ｜ 通过标准: `grep -c "192.168" pattern_knowledge_workbench/pubspec.yaml` 返回 0，且干净容器内 `flutter pub get` 成功

### RA 身份与内核契约（L0，阻断其余全部条目）

- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§2 原则7` 把「版本 ID」与「业务身份 ID」混为一谈，导致返工时历史 ReviewDecision 失去指向对象、发版后下游注解集体断锚 ｜ 通过标准: 规格中出现 `entity_id`（跨 Revision 稳定、要求复用）与 `artifact_revision_id`（不可复用）两类标识的定义，原则7 改为只约束后者，并声明 ReviewDecision / EvidenceLink / Annotation 一律锚定 `entity_id` ｜ 依据：§2 原则 7、§8.1「标识与修订语义」
- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§7,§8` StepRequest/StepResult/Package 信封只有「至少包含」的散文，无字段全集与机器可读 schema，任何 Module 任务连输入都无法定义 ｜ 通过标准: 提交 `openspec/schemas/` 下 ArtifactRef、StepRequest、StepResult、StagePackage 四个 schema 文件；并用现有 `pipeline/corpus/bazi/qtbj_ed01/manifest.yaml` 构造 round-trip 示例通过校验
- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§4,§8,§13,§14` 状态枚举散落且不成集（全文只有孤立的 `not_captured`），且未声明与 `pipeline/schemas/core/SCHEMA.md` v0.2 已冻结的 7 个内容状态、9 个错误码的关系 ｜ 通过标准: 规格含四张枚举全集表（Artifact status / Stage-StepRun status / ReviewDecision 类型 / failure 分类），取值为英文小写下划线，每条标注与 SCHEMA.md v0.2 的关系（沿用 / 扩展 / 取代 / 冲突待裁）
- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§7` 单次同步 `execute()` 语义无法表达 M2 校对、M3 分歧裁决、M4 人工队列、M6 工作台四处长时人工阶段，且 `StepResult.status` 无取值集合 ｜ 通过标准: 规格含 StepRun 生命周期状态机（至少 running / awaiting_human / suspended / succeeded / failed / superseded），挂起态定义 resume_token、人工事件写回接口与超时策略 ｜ 依据：§7.1 定义跨人工队列的单一 StepRun、冻结输入、`resume_token`、事件写回与提醒式 deadline；§8.2 穷举六状态及合法迁移
- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§17` Artifact Ledger 未定义访问接口与进程模型，而其三个消费者跨语言（pipeline=Python、`ocr/local/app.py`=FastAPI、工作台=Flutter/Dart），M6 任务在此裁定前无法给出可实现接口 ｜ 通过标准: 规格写明进程模型（库内调用 / 本地服务 / 文件协议三选一）、并发写入与锁策略，并逐一说明三个消费者的接入方式

### RB 术语双轨（阻断 M4-M8 全部任务）

- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§4,§12` Pattern / Concept / KnowledgeEntry 三者关系未定义——`CONTEXT.md:11` 称 Pattern 为产品级总称，`LEARN_SYSTEM_TARGET.md:121` 的产品级聚合却是 KnowledgeEntry（规格全文 0 次出现），§12 又把 Concept 与 Pattern 并列为两类候选，导致 M4/M6/M7/M8 无法确定主键对象 ｜ 通过标准: 规格写明三者的从属关系、各自 ID 前缀、字段清单与「一个 Pattern 聚合 N 条 Assertion」的基数约束；`CONTEXT.md` 补 Concept、KnowledgeEntry 词条
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§16` PublicationPackage 八个子包与 `LEARN_SYSTEM_TARGET.md:185-202` 已确认的 KnowledgePack 十四个目录无映射，客户端契约名 KnowledgePack 在规格中 0 次出现 ｜ 通过标准: §16 含双向映射表，逐条覆盖 concepts/entries/assertions/applicability-rules/school-views/evidence-links/source-spans/source-anchors/query-contract；若属更名则写出取代声明
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§16` Annotation 完全缺席，而 `LEARN_SYSTEM_TARGET.md:307` 要求注解「稳定锚定到可版本迁移的知识/原文对象」；按现 §2 原则7，每次发版用户全部注解变孤儿 ｜ 通过标准: §16 新增 `AnchorContractPack`，含可锚定对象白名单、`entity_id` 稳定性承诺等级、`IdentityMigrationMap`（迁移/合并/拆分/废弃四类）；§20 加入「跨 Release 注解锚点可迁移率」验收项
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§16` FactSet 与 Matcher 全文 0 次出现，RuleIndexPack 只有名字无内容，TechniqueProfile 只作 M8 输入未作输出发布，下游拿到规则也不知合法字段与取值 ｜ 通过标准: §16 新增 `TechniqueProfilePack`（FactSet Profile、事实字段与枚举、operator 集合、规则 AST schema 版本）与 `QueryContractPack`（getEntry/getSourceSpan/searchKnowledge/matchFacts）；每条规则声明所依据的 Profile 版本
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§12,§18` 流派只以裸词 School 出现，无 SchoolView 对象、无 school_id 命名空间、无「该分歧是否改变当前判断」字段，与 `knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md:263` 及 `tag_system/TAG_SYSTEM_DESIGN.md:299-307` 已定稿内容冲突 ｜ 通过标准: 规格定义 SchoolView 对象（school_id、主张归属、冲突组 ID、changes_current_judgment）与 SchoolViewPack 子包；§14 增列「流派归属审核」为独立 ReviewDecision 类型
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§16` EvidenceMapPack 只有名字无内容，SourceAnchor 仅在 §11（M3 内部）出现，客户端拿到扫描图不知高亮哪块 ｜ 通过标准: §16 写出 `EvidenceLink → Assertion → SourceSpan → SourceAnchor → OcrPage/字框坐标 → SourceAsset 页标识` 完整链路，坐标系与 SourceAssetPack 页图像素尺寸同源可换算，并列为 ValidationReport 的 fail-closed 检查项
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§1,§16` 仓库已声明知识区与 Tag 区唯一允许的三个耦合接口（盘面概念字典、MarkContentBinding、EvidenceBundle，见 `README.md:20`、`tag_system/README.md:29-33`），§16 八个子包无一承接 ｜ 通过标准: §16 给出承载点，逐项写出 MarkContentBinding 所需 concept_id / omen_carrying / condition_affordance / school_variance_display / changes_current_judgment 五字段的来源 Module 与 Package；或在 §21 明确本期不产出
- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§12` 未吸收 `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md:19-66` 已定稿的术语三层模型（L1 闭集 / L2 同形异义 / L3 技法私有）与三步判层，按现规格写 M4 任务会重演该文档已判定的缺陷 ｜ 通过标准: §12 写入三步判层为 M4 强制前置步骤并声明 L1 为确定性免模型路径；§5 Contract Registry 登记 `schemas/shared/canon`、`schemas/shared/homographs` 为 M4 冻结输入

### RC Gate 与运行语义（阻断第一条纵切）

- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§2原则5,§6.1,§10,§11,§20.1 与 §21` Gate 粒度自相矛盾——四处要求整本 Edition 完成才过 Gate，§21 却把「一次性处理整本三百页书籍」列为非目标，且规格未定义任何可 Gate 的最小单位；实测单部 300 页 Edition 需 1.2 万–2 万次人工决策（依据：`ocr/data_work/` 真实 10 页 584 行 2749 字、低置信字 10.7%、异常页 20%；`pipeline/corpus/bazi/qtbj_ed01/` 每千字≈4 Span≈38 assertion），单人不可完成 ｜ 通过标准: 规格定义 `EditionPart`（卷/册/页区间，含判定规则）作为 Gate 与发布最小单位，各自封 StageManifest 各自过 Gate，Edition 级 Gate 为其合取；§2原则5、§6.1、§10、§11、§20.1、§21 六处口径改到一致，`grep -n "整本\|三百页" openspec/learn-system-blackbox-architecture.md` 无矛盾表述
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§14` 失效传播粒度为整个 Edition（一页 OCR 改字 → M3-M6 全部重跑），审到第 280 条发现错字则前 279 条 ReviewDecision 连同全部模型运行报废；与 §20.2「从最近 StageCheckpoint 恢复」冲突，且 §19 表已把「失效传播」列为 Orchestrator 缺口 ｜ 通过标准: 规格给出按 LineageGraph 的精确失效算法（以 SourceSpan 为影响面单位，血缘不可达者继承并标 `carried_forward`），定义「内容等价则继承、内容变化则降级待复核」判定规则，并要求产出 `ReworkImpactReport`（失效 N / 继承 M / 待复核 K / 累计轮次）
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§20.2` StageCheckpoint 全文仅出现 1 次，§5 与 §17 均未定义其落盘粒度与内容——承诺了断点续做但没规定断点里有什么 ｜ 通过标准: 规格定义 StageCheckpoint 的落盘粒度（每 EditionPart / 每 N 次人工决定）、必含内容（已完成任务清单、已封存人工决定、待办队列剩余、下一步指针）、恢复语义（已完成人工决定不重做），并规定 M2/M3/M4/M6 每次人工决定后即时持久化
- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§11,§12` M3 边界分歧与 M4 类别分歧要求人工裁决且不裁决不能过 Gate，但工作台在 M6，操作者在 M3/M4 无任何界面可用；§15 已明文让 M7 复用 M6 工作台，M3/M4 无对应表述属遗漏 ｜ 通过标准: 二选一写死——(a) §14 把 M6 提升为跨阶段 `Review Console` 并增列 M3/M4 两种工作模式及各自输入 Package；或 (b) §5 Module 列表新增独立分歧裁决工具并定义其 Package 输入输出
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§6.2` ReleaseRun 流程图无 M6，但 §15 要求「不能确定的关系使用 M6 工作台人工裁决」，跨 Run 复用 M6 的运行归属、Gate 归属、Artifact 归属三者均未定义 ｜ 通过标准: §6.2 补含 M7 → M6 裁决 → M7 回流的完整流程图，并规定该次 ReviewDecision 挂在哪个 Run 下、是否影响原 EditionRun 的 ReviewedEditionPackage 封存状态
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§5,§7` 操作者无法回答「我在哪、还剩多少、卡在哪」——Local Orchestrator 职责无查询能力，§7 接口无状态读取，§8 manifest 仅在封存后存在 ｜ 通过标准: §5 增只读查询契约，覆盖 RunStatus / StageProgress / PendingQueue（M2 异常页与低置信字、M3 边界分歧、M4 类别分歧、M6 待签发、M7 待裁决五个队列）/ BlockingReasons / ReworkImpact / ThroughputEstimate 六项；§7 补 Module 运行中进度事件上报
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§10` 异常版面页无终态定义（`ocr/data_work/logs/anomalies.jsonl` 已登记 page_002、page_010，弧线字切分仍是 `ocr/experiments/curve_segment.py` 原型），操作者不知该逐字录入还是可标记放行，与 §6.1「失败为零」冲突 ｜ 通过标准: §10 给出异常页合法终态枚举（如 manually_transcribed / known_unrecognizable / deferred）并明确哪些终态可让 M2 Gate 通过

### RD 既有已定稿标准未吸收

- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§13,§16` 未吸收 `pipeline/DATASET_ACCEPTANCE_STANDARD.md:38-99` 已定稿的三级消费级别（INTERNAL_DEMO / DEV_SEARCH / PUBLIC_RELEASE）与 G1-G7 一票否决门禁，该文档要求「编译器必须显式接收目标级别并 fail-closed」，而 §16 的 M8 输入不含此参数 ｜ 通过标准: 消费级别列为 M8 显式输入参数，§16 写明各级别准入状态门槛（引用 G7），§13 的 Validator 清单逐条对应 G1-G6 并指出哪些在 M5、哪些延到 M8；全规格不新造门禁名
- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§14` 仍只写「专家签发」单一动作，未吸收 `knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md:248-259` 已定稿的「禁止用一个 expert_verified 覆盖所有含义」与八类审核拆分 ｜ 通过标准: 八类审核（来源忠实度 / 版本校勘 / 流派归属 / 解释质量 / 案例真实性 / 现实效度 / 安全 / 权利）落为 ReviewDecision 子类型枚举，与 RA 状态枚举表合并处理
- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§11,§19` 证据等级未裁定——`LEARN_SYSTEM_TARGET.md:140` 明确「纯文本引用只能算开发级证据」，而 §11 允许电子来源仅回到 EPUB offset，现有 `ku_bazi_000046` 全部走 offset 路径，M3/M5 任务会在「offset 够」与「必须字框」之间反复返工 ｜ 通过标准: 规格给出 `evidence_level` 枚举（至少 offset 级 / 字框级）、各级可发布性结论，并写入 M5 validator 判定条件与首纵切验收接受档位；**首纵切档位已由用户裁定为「字框级」**，本条只需补枚举与 validator 条件

### RE 差距表本身失真（§19 三行低估、十二项遗漏）

- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§19 M1行` 低估：漏写 `pipeline/registry/works/` 与 `tools/ingest_epub.py`，且未记「转录不可重放」——manifest 记录 `conversion.tool: tools/ingest_epub.py`，但该工具无 PUA 勘误逻辑，用记录的 raw+tool 重跑得不到记录的 transcript hash，§20 第 3、4 条的可追溯在 M1 即断 ｜ 通过标准: 该行补上述两项，并附判据命令 `python3 tools/ingest_epub.py --raw raw/穷通宝鉴.epub --out /tmp/t.md && shasum -a 256 /tmp/t.md` 输出等于 `manifest.yaml:22` 记录的 hash（当前必 FAIL，即差距的机器证据）
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§19 M6行` 低估：只写能力缺失，未写数据体全空——496 条 rule 的 original_text / assertion / brief / explanation / notes 全部 0 条非空，is_verified=1 为 0 条，ge_ju_versions 表 0 行 ｜ 通过标准: 该行含上述数字，并附复核命令 `sqlite3 pattern_knowledge_workbench/assets/ge_ju_database.sqlite "select count(*) from ge_ju_rules where trim(coalesce(original_text,''))<>''"` 预期当前为 0
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§19 M8行` 低估：把问题写成「零命中假绿」，实际是证据错链——`pipeline/rag/build_index.py:135-138` 的 span_map 只按 seg 序号建键，148 个 span 塌缩为 18 键、6 组碰撞；`:148-152` 对完整 span ID 抛 ValueError 后静默 continue 才是八字 mentions=0 的真根因，解析修好后 mentions 将链到错误页 ｜ 通过标准: 该行文字含「span→mentions 映射键碰撞（148 span 塌缩为 18 键）」，并附判据断言 span_map 键数 == spans 行数
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§19` 缺十二项已知重大缺口，其中四项为结构性阻断：`ge_ju_rules` 唯一键 `{patternId, schoolId}`（`tables.dart:68-70`，结构上禁止同一格局同一流派有多本书多主张，与 §4/§18 多主张模型冲突）、`ge_ju_schools` 把 book(1) 与 school(2) 混存同表（Work/Edition 身份被折叠进 School）、干净环境不可构建、测试宿主匮乏（全仓非 OCR 部分仅 1 个 748B 脚手架测试，goldens 只有 bazi/qtbj 三组无非八字 fixture）；另需登记 OCR R7 与 `pipeline/TODO.md:12-14` 的三项 P0 语义阻断 ｜ 通过标准: §19 补齐上述各行，每行附一条「当前必 FAIL、修好后必 PASS」的判据命令；注意 `pipeline/requirements.txt` 已存在，「无依赖声明」不再成立，不得计入
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§20` 十条完成标准全为散文断言，经逐条核验 0 条可用一条命令判定，2 条（第 3、5）有部分基础，第 7 条按字面现在就能「通过」而构成新的假绿 ｜ 通过标准: 每条改写为「命令 + 期望退出码/期望输出」二元组；`bash openspec/acceptance/run_all.sh` 逐条打印 PASS / FAIL / BLOCKED(前置缺失)，允许 BLOCKED，不允许「无法执行」

### RF 规划前置（不解决则拆出的 tasks 无法验收）

- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§19,§20,§21` 全文无任何分期、优先级或 MVP 表述，§19 十二行全「缺」、§20 十条全为终态；而 `LEARN_SYSTEM_TARGET.md:278-296` 已确认第一阶段是一条纵切，该纵切横跨 §19 的 8 行，不独占任何一行——按差距表逐行拆将得到 12 条并行 epic，各推进 30% 时纵切仍为 0 ｜ 通过标准: 规格新增「实施分期与首个纵切」一节，§19 每行标注 {首纵切内 / 首纵切后 / 本阶段暂缓} 之一，且标为「首纵切内」的不超过 4 行
- [x] 裁定（2026-09-08 用户）：首纵切改用**七政《三辰通载三十卷》影宋鈔本**。三元组 = `technique_id=qizheng` + `Work=三辰通载三十卷` + `Edition=影宋鈔本` + 本地 `SourceAsset=ocr/data_work/sanche_pages/page_001..010.png`（派生页图位于工作目录但被 Git 忽略，克隆不可恢复）+ 源 PDF 外部引用（247M，按 `.gitignore` 策略不入仓，见 RG 组）。连带确定：`evidence_level=字框级`；M6 复用现有七政工作台原型；496 条空 rule 不作为纵切输入，知识从原文重新抽取。迁移前必须按 `openspec/legacy-storage-transition.md` 登记到本地 Object Store。
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md:§4` 与 `LEARN_SYSTEM_TARGET.md:289`、`PLAN.md` 首纵切术数冲突，且素材物理不存在——`raw_books/` 全仓仅 2 个文件（`bazi/qiongtongbaojian/穷通宝鉴.epub`、`qimendunjia/yanbodiaosou.md`），无任何八字扫描件；唯一扫描物料是七政《三辰通载》10 页 PNG，其源 PDF 位于 `$HOME/Downloads/`（见 `ocr/run_sanche10.sh:14`）不在仓库、无哈希登记，违反 §9；而七政侧 496 条 rule 知识字段全空。即「八字有文无图、七政有图无文」，`LEARN_SYSTEM_TARGET.md:292` 的高亮终点当前对两者皆不可达 ｜ 通过标准: 裁定并写入规格一组三元组 `technique_id + Work/Edition + SourceAsset 仓库内路径`，该路径真实存在且可计算哈希；若选择需新引入的扫描件，则「取得并登记该扫描件」成为首纵切第 1 号任务
- [ ] 修复: 缺最小可跑 fixture Edition，导致 §20 第 1/2/4/9 条无验收宿主，且第一批 tasks 写不出「跑哪条命令算过」 ｜ 通过标准: 建立 `pipeline/corpus/_fixture/mini_ed01`（≤3 页、≤5 batch），在无内网、无 GPU、无外部模型 API 条件下可跑完 M1→M6，并被 §19/§20 引用为统一验收宿主
- [ ] 修复: `PLAN.md:7` 提议「按差距矩阵重写本节」，但差距表覆盖不到本文件现有 26 条未完成项中的至少 6 条（pipeline 环境检查、四本手册状态回写、《烟波钓叟歌》扩批模板、奇门试点材料、奇门金标集、旧 APP 迁移策略）及整条 Tag 线与 OCR 线，规格 §21 也未将其列为非目标，重写将静默丢失；另有 5 处重复登记（KnowledgeReleaseCompiler 见 `PLAN.md:18` / `pipeline/TODO.md` / `pattern_knowledge_workbench/TODO.md` / `LEARN_SYSTEM_TARGET.md:258`）会漂移成第 6 处 ｜ 通过标准: PLAN.md 只做增补与映射不做替换；新增「差距行 ↔ 既有条目 ↔ owner 文件」映射表，§19 每行有归属，现有未完成项被删除数量为 0 且每条标注 mapped / superseded-by / out-of-scope，重复项收敛到唯一 owner 文件
- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§17,§19` 未对既有五处存储给出处置结论，Ledger 落地后将全部返工，且违反 §2 原则2「Module 不直接读取或修改其他 Module 的数据库」 ｜ 通过标准: 对 `ocr/data_work/index.db`、`pipeline/units/`（139 单元）、`pipeline/rag/index.sqlite`、`pipeline/corpus/`、`pattern_knowledge_workbench/assets/ge_ju_database.sqlite`（496 rules）每处给出 {迁移 / 重跑 / 冻结为历史快照} 三选一结论
- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§19` 行序为 M1→M8→三个基础设施，恰是真实依赖拓扑的逆序（L0 内核契约 → Artifact Ledger → Local Orchestrator / Contract Registry → M1-M8），执行者自上而下开工时 Ledger 尚不存在，M1 必然自造 ID 与 manifest 约定后返工 ｜ 通过标准: §19 增「层级」列标出 L0/L1/L2/Module 四层，或按拓扑重排行序，并显式标注三个基础设施为前置层
- [ ] 修复: `openspec/learn-system-blackbox-architecture.md` 全文 21 节仅 §2 带「已确认原则」标签，其余以确定语气陈述，违反 `AGENTS.md:39`「明确区分已确认设计 / 讨论候选 / 待验证假设 / 最终规范」；§16 的「建议一个 Technique 一个 Release」混入正文，读者无法判断其对 task 是否有约束力 ｜ 通过标准: §3-§18 每节带状态标签，`grep -c "^状态：" openspec/learn-system-blackbox-architecture.md` ≥ 16，且「建议」类表述归入「讨论候选」或升格为规范

### RG 版权与存储边界（R1 审查后追加，新发现）

- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§9,§16,§17,§20.8` 与 `.gitignore:3-12` 冲突：仓库策略明令「版权源书不进公开仓，只提取转录文本与派生产物」（`*.pdf` / `raw_books/**/*.pdf` 均被忽略），而 §9 要求 M1 输出「原始文件及哈希」、§16 含 `SourceAssetPack`、§20.8 要求发布物「同时包含原始资料」、`LEARN_SYSTEM_TARGET.md:140` 要求「客户端最终应能打开原始扫描件」；首纵切源 PDF 实测 247M，物理与法律上均不可入仓 ｜ 通过标准: 规格明确区分三层存储边界——Git 仓库（转录与派生产物）/ 本地 Object Store（§17，含受版权限制的原件，不进 Git）/ PublicationPackage（对外分发物）；并规定 SourceAsset 在源书不可分发时的登记形态（外部路径引用 + SHA-256 + 页数 + 页图派生物清单），使 §9 的「原始文件及哈希」可在不入仓的前提下满足
- [x] 修复: `openspec/learn-system-blackbox-architecture.md:§16 SourceAssetPack` 未定义版权受限来源的降级形态，导致 `LEARN_SYSTEM_TARGET.md:140`「打开原始扫描件并高亮」这一终点在首纵切上无法交付 ｜ 通过标准: §16 为 SourceAssetPack 定义至少两档内容级别（full_scan / derived_page_images_only / reference_and_hash_only）及各档下客户端高亮功能的可用性结论，并在 §21 或 ReleasePolicy 中写明首纵切采用哪一档

## Learn System 系统集成主线

- [x] 确认主 Agent 的工作边界：只负责规格、BDD、TDD、ACT、Executor Prompt 和独立验收，不代替执行 Agent 编写业务实现。准出规范见 `openspec/subagent-delivery-gate.md`，总进度见 `docs/blackbox-spec-rework/SUBAGENT_TODO.md`。
- [x] 复核并启用 `openspec/subagent-delivery-gate.md`；所有新派发任务必须先达到 `READY`。
- [x] 完成 D-03 追溯工作包和独立验收；证据见 `docs/blackbox-spec-rework/work-items/d03/ACCEPTANCE.md`。
- [x] 将 T-02 准备到 `READY`；工作包与可直接派发 Prompt 见 `docs/blackbox-spec-rework/work-items/t02/`。
- [x] 用户确认 T-02 的六类新增前缀；返工 `376e78c` 已解决 StagePackage 的 `pkg_`/`rev_` 语义冲突并冻结 `<stage>=m1–m8`，T-02 已 `ACCEPTED`。
- [x] 调研单人单机条件下可直接复用的免费开源框架；候选组合与自研边界见 `docs/research/2026-09-08-open-source-framework-options.md`，尚待确认后写入正式 OpenSpec。
- [x] 明确当前不实现登录鉴权；只保留固定返回 `local_owner` 的 `ActorProvider` 接口，未来可替换线上身份适配器。业务对象稳定 ID 不属于登录身份系统，仍按 D-01 处理。
- [x] 确认 OCR 参数化设计：现有中国传统竖排古籍 OCR/FastAPI/Vue 保持主链，不引入 Kraken；每个 Edition 使用经代表页校准、人工验收和冻结的版本化 `OCRProfile`。设计见 `openspec/ocr-profile-parameterization.md`。
- [ ] 在黑箱 R1 规格复审通过后，以最薄实现让现有 OCR `run` 路径读取并封存 `OCRProfile`；不得借机重写算法、增加调参 UI 或接入第二引擎。
- [ ] 完成 `openspec/learn-system-blackbox-architecture.md` 的 R1 返工并复审；PLAN 只增补映射，不重写或删除既有未完成项。
- [x] 确认并记录 Learn System 最终目标、端到端运行方式、现有工具成熟度和缺口。
- [x] 审计《穷通宝鉴》现有拆书数据，并形成 `pipeline/DATASET_ACCEPTANCE_STANDARD.md` 验收草案；当前结论为 `NOT_READY`。
- [x] 将七政四余 `companion_system` 原样迁入通用独立项目 `pattern_knowledge_workbench/`，建立 README、领域词汇、扩展计划、缺口分析和待办。
- [ ] 修复《穷通宝鉴》约 7.5% 源文漏编与八字 concept mentions 为 0 的两项假绿问题。
- [ ] 修复工作台启动覆盖数据库、保存即 verified、无版本审计和 AI 候选绕过审核的 P0 风险。
- [ ] 将工作台从七政硬编码演进为 `TechniqueProfile`，七政作为首个 profile，随后接入八字、紫微、大六壬和奇门。
- [ ] 定义第一条八字纵切的 KnowledgePack、FactSet、ApplicabilityRule、SourceAnchor 和 Annotation 契约。
- [ ] 打通一页扫描件到 `SourceSpan → OCR 字框 → PDF/PNG` 的无损证据链。
- [ ] 泛化 taskgen，移除八字/《穷通宝鉴》硬编码，并建立非八字 fixture。
- [ ] 修复完整 span ID 索引和 `concept → assertion → evidence` 查询链。
- [ ] 实现发布级 KnowledgeReleaseCompiler、ReleaseManifest、validator 和只读 AppKnowledgeAdapter。
- [ ] 用 `丙日干 + 亥月` FactSet 验收“十月丙火”全部相关主张召回、原文展示与扫描定位。
- [ ] 实现锚定到词条/主张/原句/扫描区域的私人及公开 Annotation 最小模型。
- [ ] 在首条纵切通过后，扩展十干十二月、十神、格局和其他术数 FactSet Profile。

## 既有知识编译与 Tag 计划

- [x] 保存术数文献知识编译与学习系统讨论草案。
- [x] 将 `learn_system` 初始化为独立 Git 工作区。
- [x] 继续补充未知领域问题与决策清单。
- [x] 汇总跨角色产品评审并保存 v1.2 产品决策母稿。
- [x] 完成 Tag/Marks 系统专题评审并保存独立评审报告。
- [x] 收敛十种 Tag 的个人样式定制与 Marketplace 接口设计规格。
- [x] 完成 Tag Style 规格跨角色复审并落实问题修订。
- [x] 同步 Tag Style 交叉评审报告与 D-015–D-020 落实门槛。
- [x] 将 D-015–D-020 回写到 Tag Style 主规格正文并同步评审报告状态。
- [x] 新增 Official Tag Starter Kit v0.1 规格并接入 Tag 执行计划。
- [x] 完成 `pipeline/` 首轮真实生命周期全面评审并保存 `PIPELINE_REVIEW_v1.md`。
- [ ] 为 `pipeline/` 增加依赖声明与环境检查，保证 validators/RAG 可复现运行。
- [ ] 增加 assertion task、glossary、RAG index 的确定性校验器。
- [ ] 按 `PIPELINE_REVIEW_v1.md` 回写四本手册的当前状态与扩批规则。
- [ ] 为《烟波钓叟歌》s13-s110 扩批建立 batches/id_range/metrics/review 模板。
- [ ] 用户确认 v1.2 推荐项、冻结项和阶段零范围。
- [ ] 确认旧 APP 类型并定稿迁移策略。
- [ ] 选择一段具有正文、注文、条件、例外和术语的奇门试点材料。
- [ ] 建立首个 `SourcePackage` 与连续工位 `TaskPackage` 示例。
- [ ] 建立奇门分工位金标集并比较不同模型表现。
- [ ] 根据试点修订 Schema、错误码和自动放行门槛。
- [ ] 将用户批准的最终设计转入 OpenSpec。
- [ ] 编写实施计划并开始校验器与编译器实现。

当前 Tag 线优先制作 `official_starter_clear` 第一版官方基础包、TechniqueProfile 和 Preview Catalog；随后用它作为 TagStyleCompiler MVP 的 golden input。不得直接启动 `TagStyleEditor`、Marketplace 或用户 Dart/Flutter 插件实施。pipeline 线仍按 `PIPELINE_REVIEW_v1.md` 继续补依赖、环境检查和确定性校验器。

### OCR 线（ocr/ 子目录，与上表并行）
- [x] 修复单字切分「不丢字/不错位」两条根因并建立契约测试（2026-08-22）
- [ ] R7 `segment_block` 横排分支墨迹掩码与取轴错误
- [ ] 清掉 `_find_gaps` 未被使用的 `min_gap` 死参
- [ ] 收紧 `tests/test_segment.py` 的宽松断言（`>= 2` 类）
