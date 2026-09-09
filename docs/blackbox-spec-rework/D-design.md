# D 类返工指令 — 设计型（需做判断，**必须用较强模型执行**）

> 对应 PLAN.md「黑箱架构规格 R1 审查返工项」中无法机械转译的部分。
> 每条给出：**约束边界**（不可越）、**判据**（做完怎么算对）、**已否决方案**（别再走）、
> **是否需要用户拍板**。
>
> **通用铁律**：
> 1. 标了「⚠ 需用户拍板」的，在拿到答复前**不得开工**，也不得选一个默认值往下做。
> 2. 「已否决方案」是审查中已经推演过并判死的路径，**重走一遍是纯浪费**。
> 3. 不得扩大范围：本文件之外的规格章节不要顺手改。
> 4. 每条改完在 PLAN.md 对应 checkbox 勾选，并追加一行「依据：<你写在规格哪一节>」。

---

## D-01 ｜ 拆分 `entity_id` 与 `artifact_revision_id`

- **返工项**：RA 组第 1 条 ｜ **落点**：`§2 原则 7` 改写 + `§8.1` 补定义
- **问题**：现原则 7「任何修改产生新 Revision；不覆盖旧 Artifact，不复用旧 ID」把两种 ID 混为一谈。
  后果有二：返工时历史 ReviewDecision 失去指向对象；发版后下游注解集体断锚。
- **约束边界**：
  - `entity_id`：跨 Revision 稳定的业务身份，**要求复用**。适用于 Pattern / Assertion / SourceSpan /
    Concept / SchoolView / KnowledgeEntry 等领域对象。
  - `artifact_revision_id`：物理修订标识，**禁止复用**。适用于 Artifact / StagePackage / StepRun。
  - 原则 7 改为只约束后者，措辞必须明确到不会被再次误读。
  - ReviewDecision、EvidenceLink、下游 Annotation 一律锚定 `entity_id`。
- **判据**：
  ```bash
  grep -c "entity_id" openspec/learn-system-blackbox-architecture.md       # >= 5
  grep -A3 "原则 7\|^7\." openspec/learn-system-blackbox-architecture.md | grep -q "artifact_revision_id"
  ```
- **已否决**：不要用「加一个 stable_key 字段」绕过——那等于承认原则 7 写错却不改它，
  后来的读者仍会按原则 7 行事。必须直接改原则 7 的正文。
- **拍板**：不需要。这是修正内部矛盾，方向唯一。

---

## D-02 ｜ 冻结 L0 内核契约（阻断其余全部条目）

- **返工项**：RA 组第 2 条 ｜ **落点**：新建 `openspec/schemas/` 四个文件 + `§7 §8` 引用它们
- **约束边界**：
  - 四个 schema：`ArtifactRef`、`StepRequest`、`StepResult`、`StagePackage`。
  - `StepRequest` 至少含 `§7` 已列五项，`StepResult` 至少含 `§7` 已列五项，只可增不可减。
  - `StagePackage` 必须含 `§8` 六段：payload / manifest / validation / lineage / logs / failures。
  - ID 格式引用 `§8.1`（见 `T-transcribe.md` T-02），不要在 schema 里重新定义。
  - 必须提供一个 round-trip 示例：用现有 `pipeline/corpus/bazi/qtbj_ed01/manifest.yaml`
    构造一份 ArtifactRef + StagePackage，能通过自己的 schema 校验。
- **判据**：
  ```bash
  ls openspec/schemas/{artifact_ref,step_request,step_result,stage_package}.*   # 四个文件存在
  # 且 round-trip 示例校验通过（用你选的校验器，命令写进规格）
  ```
- **已否决**：不要先写 Ledger 实现再回头补 schema——审查已确认 L0 是 L1 的前置，
  倒过来做会让 M1 自造一套 ID 与 manifest 约定后返工。
- **拍板**：不需要，但 `§8.1` 里新对象的 ID 前缀（Artifact / ProcessingRun / StepRun / Release 等）
  做完后要单独列出请用户确认一次。

---

## D-03 ｜ Artifact status 与 StepRun status 状态机

- **返工项**：RA 组第 3 条（剩余部分）、第 4 条 ｜ **落点**：`§8.2` 补两张表 + `§7` 补状态机
- **约束边界**：
  - `StepRun status` 必须能表达四处长时人工阶段（M2 校对、M3 分歧裁决、M4 人工队列、M6 工作台）。
    至少含：`running / awaiting_human / suspended / succeeded / failed / superseded`。
  - `awaiting_human` 必须定义 `resume_token`、人工事件写回接口、超时策略。
  - 必须画出合法迁移（哪些态可到哪些态），不能只列枚举。
  - 必须明确：一次 `execute()` 覆盖的是整个人工阶段，还是单条人工决定。二选一写死。
  - 内容状态沿用 `SCHEMA.md` 七值（T-03 已处理），**不要与本状态机混用**——
    一个是内容成熟度，一个是运行生命周期，必须分开两张表。
- **判据**：
  ```bash
  for s in running awaiting_human suspended succeeded failed superseded; do
    grep -q "$s" openspec/learn-system-blackbox-architecture.md || echo "缺: $s"; done
  grep -c "resume_token" openspec/learn-system-blackbox-architecture.md   # >= 1
  ```
- **已否决**：不要把人工阶段拆成「Module 返回 pending，外部轮询」——`§7` 规定 Module 只能读取
  请求中冻结的 Artifact，轮询模型会诱导 Module 去读工作目录最新文件，违反该条。
- **拍板**：不需要。

---

## D-04 ｜ Artifact Ledger 访问契约与跨语言边界

- **返工项**：RA 组第 5 条 ｜ **落点**：`§17` 展开
- **实测约束（三个消费者，跨三种运行时）**：
  - `pipeline/` — Python
  - `ocr/local/app.py` — FastAPI（Python，但独立进程，带 Web UI）
  - `pattern_knowledge_workbench/` — Flutter / Dart + Drift
- **约束边界**：
  - 三选一并写死：库内调用 / 本地服务 / 文件协议。
  - 必须逐一说明三个消费者各自怎么接入。Dart 侧无法 import Python 库，这一点会直接淘汰「库内调用」，
    除非同时定义一个 Dart 侧的独立实现（那就要处理两套实现的一致性问题，成本要在规格里写明）。
  - 必须定义并发写入与锁策略（单人单机也会有 OCR 工具与工作台同时在跑）。
  - 必须与 `§2 原则 2`「Module 不直接读取或修改其他 Module 的数据库」自洽。
- **判据**：规格中出现进程模型的明确选择 + 三个消费者的接入说明 + 锁策略。
  ```bash
  grep -c "本地服务\|库内调用\|文件协议" openspec/learn-system-blackbox-architecture.md  # >= 1
  grep -c "Flutter\|Dart" openspec/learn-system-blackbox-architecture.md                  # >= 1
  ```
- **已否决**：不要让工作台直接读写 Ledger 的 SQLite 文件——`§14` 已规定工作台 SQLite
  只能作 UI 查询投影，直连会重演「两个 Module 共用一个库」的问题。
- **决议（2026-09-08）**：选择单机本地进程；三个消费者使用统一客户端，单写入者串行写事务，SQLite WAL 支持并发读取。

---

## D-05 ｜ Pattern / Concept / KnowledgeEntry 三者关系

- **返工项**：RB 组第 1 条 ｜ **落点**：`§4` 新增一节 + `CONTEXT.md` 补词条
- **冲突现状**：
  - `CONTEXT.md:11` 称 Pattern 是「跨术数使用的产品级总称」
  - `LEARN_SYSTEM_TARGET.md:121` 称 KnowledgeEntry 是「面向产品的词条聚合」，且 `:264` 的 P1 首条
    要求「把一 span 一 unit 聚合为稳定 KnowledgeEntry」
  - 规格 `§12` 又把 `Concept / Pattern` 并列为两类候选
  - 规格全文 `KnowledgeEntry` 出现 0 次
- **约束边界**：三者关系必须唯一确定，且必须回答：M7 汇编的产出物是什么？M8 发布的主键对象是什么？
  可选形态（不限于）：Pattern 是 Concept 的子类型且 KnowledgeEntry 是二者的发布视图；
  或 Pattern 取代 KnowledgeEntry（则须在 TARGET 侧写取代声明）。
  无论选哪个，都要给出三者的 ID 前缀、字段清单、基数约束（一个 Pattern 聚合 N 条 Assertion）。
- **判据**：
  ```bash
  grep -c "KnowledgeEntry" openspec/learn-system-blackbox-architecture.md   # 从 0 变为 >= 3
  grep -c "KnowledgeEntry\|Concept" CONTEXT.md                              # 两个词条都要有
  ```
- **已否决**：不要「两者并存、各管一段」——审查已确认这会让 M4/M6/M7/M8 四个 Module
  都无法确定主键对象，是当前最大的术语债。
- **决议（2026-09-08）**：Pattern 是 Technique 范围内可规则识别的 Concept 子类型；KnowledgeEntry 是 M8 面向 APP 的发布聚合视图。

---

## D-06 ｜ Annotation 锚点契约与跨 Release 迁移

- **返工项**：RB 组第 3 条 ｜ **落点**：`§16` 新增 `AnchorContractPack` + `§18` 补边类型 + `§20` 补验收项
- **约束边界**：
  - 可锚定对象白名单：KnowledgeEntry / Assertion / SourceSpan / SourceAnchor（依 D-05 结论调整）。
  - 每类给出 `entity_id` 稳定性承诺等级（永久稳定 / 可迁移 / 不保证）。
  - `IdentityMigrationMap` 必须覆盖四类变化：迁移、合并、拆分、废弃。
  - `§18` 双图中加「锚点迁移关系」边类型。
  - `§20` 加一条可验收项：跨 Release 注解锚点可迁移率。
- **判据**：
  ```bash
  grep -c "AnchorContractPack\|IdentityMigrationMap" openspec/learn-system-blackbox-architecture.md  # >= 2
  ```
- **依赖**：DEPENDS_ON D-01（没有 `entity_id` 就没有可锚定的稳定身份）、D-05（白名单含哪些对象取决于它）。
- **拍板**：不需要（前两条定了之后此条唯一）。

---

## D-07 ｜ TechniqueProfilePack 与 QueryContractPack

- **返工项**：RB 组第 4 条 ｜ **落点**：`§16` 新增两个子包 + `§13` 补校验项
- **照抄源打底（先读，能省一半设计）**：
  - `DATASET_ACCEPTANCE_STANDARD §4-G6` 已定义要求：查询输入必须是版本化 `FactSet`，
    规则必须是可执行 `ApplicabilityRule`；给定事实必须返回全部且仅返回适用规则，
    并说明已满足条件、缺失条件和触发例外；任一条件不全或例外成立时不得输出肯定判断。
  - `LEARN_SYSTEM_TARGET.md §7` 已给 FactSet 的 YAML 示例与五个 Profile 名
    （BaziFactSet / QizhengFactSet / ZiweiFactSet / QimenFactSet / LiuRenFactSet）。
- **约束边界**：
  - `TechniqueProfilePack` 至少含：FactSet Profile、事实字段与枚举、operator 集合、规则 AST schema 版本。
  - `QueryContractPack` 至少含 `getEntry / getSourceSpan / searchKnowledge / matchFacts` 四个接口与兼容声明。
  - `RuleIndexPack` 中每条规则必须声明所依据的 Profile 版本。
  - `§13` M5 增加「规则对 FactSet 可执行性」校验，判据直接引 G6。
  - **规则不得是可执行 Python**（`§13` 已明令），必须是结构化 AST/YAML/JSON。
- **判据**：
  ```bash
  grep -c "TechniqueProfilePack\|QueryContractPack\|FactSet" openspec/learn-system-blackbox-architecture.md  # >= 3
  grep -q "matchFacts" openspec/learn-system-blackbox-architecture.md && echo OK
  ```
- **拍板**：不需要。首纵切用 `QizhengFactSet`（依 2026-09-08 裁定）。

---

## D-08 ｜ SchoolView 对象与 SchoolViewPack

- **返工项**：RB 组第 5 条 ｜ **落点**：`§12` `§14` `§16`
- **照抄源打底**：
  - `METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md §3.3`：争议若会改变用户当前判断，
    首层必须显示存在分歧；不得用默认流派静默折叠。
  - `TAG_SYSTEM_DESIGN.md:307`：「是否改变当前判断」属 MarkContentBinding 内容状态字段，
    由知识层供给，UI 不得猜测。
- **约束边界**：SchoolView 至少含 `school_id`、主张归属、冲突组 ID、`changes_current_judgment`（布尔）。
  `§14` 增「流派归属审核」为独立 ReviewDecision 类型（与 T-03 的八类审核表合并，不要另起一套）。
  注意现状陷阱：工作台 `ge_ju_schools` 把 book 与 school 混存同表（实测 book 1 / school 2），
  规格必须明确 Work/Edition 身份**不得**折叠进 School。
- **判据**：
  ```bash
  grep -c "SchoolView\|changes_current_judgment" openspec/learn-system-blackbox-architecture.md  # >= 2
  ```
- **拍板**：不需要。

---

## D-09 ｜ Gate 最小单位（六处口径统一）★核心

- **返工项**：RC 组第 1 条 ｜ **落点**：`§2 原则 5`、`§6.1`、`§10`、`§11`、`§20.1`、`§21` 六处
- **实测依据（不要重新统计）**：
  - 真实 10 页：584 行 / 2,749 字，低置信字 296 个（10.7%），2 页需纯人工
  - 密度：每千字原文 ≈4 个 Span、≈38 条 assertion
  - 折算 300 页：≈330 SemanticSpan、≈3,150 assertion 候选
  - **单部 Edition 合计 1.2 万–2 万次人工决策**，乐观 48 小时，真实 200 小时量级
- **约束边界**：
  - 定义一个子集单位（`EditionPart`：卷 / 册 / 篇 / 页区间，四选一并给判定规则）。
  - 每个 EditionPart 各自封 `StageManifest`、各自过 Gate；Edition 级 Gate 是其**合取**。
  - 覆盖率分母必须随之明确（`§11` 的「同层 Span 全文覆盖 100%」中的「全文」指哪一层）。
  - 必须说明 `DATASET_ACCEPTANCE_STANDARD G2`「全书覆盖 100%」在该单位下如何分层验收。
  - 六处口径改到一致，`§21` 里那条「一次性处理整本三百页书籍」必须删除或改写。
- **判据**：
  ```bash
  grep -c "EditionPart" openspec/learn-system-blackbox-architecture.md   # >= 4
  grep -n "整本\|三百页" openspec/learn-system-blackbox-architecture.md   # 人工确认无残留矛盾
  ```
- **已否决**：
  - 不要「按页推进」——`§2 原则 5` 明确禁止按页或 SourceSpan 推进下游阶段，且跨页语义会被切断。
  - 不要「保留整本 Gate，只是允许分批做」——那只是把问题推到最后一批，第一个可交付物仍是整本。
- **决议（2026-09-08）**：优先按卷；没有稳定卷界时使用连续页区间。《三辰通载三十卷》按卷建立 EditionPart。

---

## D-10 ｜ 精确失效传播（保护已完成的人工劳动）★核心

- **返工项**：RC 组第 2 条 ｜ **落点**：`§14` 改写 + 新增一节
- **问题**：现 `§14` 规定 M6 发现 OCR 错误 → 退回 M2 →「该 Edition 的 M3 至 M6 全部失效重跑」。
  按 D-09 的实测量级，这意味着审到第 280 条发现一个错字，前 279 条 ReviewDecision
  连同全部模型运行报废。这与 `§20.2`「从最近 StageCheckpoint 恢复」直接冲突，
  且 `§19` 表已把「失效传播」列为 Orchestrator 缺口——说明精确失效本就是预期能力。
- **约束边界**：
  - 以 SourceSpan / StructuralSpan 为影响面单位，沿 LineageGraph 判定失效范围。
  - 血缘可达被修正 span 的 Candidate → 失效；不可达的 → 继承到新 Revision，标 `carried_forward` 与来源 Revision。
  - 判定规则写死：**内容等价则决定自动继承，内容变化则降级为待复核**。
  - 必须产出 `ReworkImpactReport`：失效 N 条 / 继承 M 条 / 待复核 K 条 / 累计返工轮次。
  - 累计轮次要有告警阈值（`§13` 或 `§14`），给操作者收敛信号。
- **判据**：
  ```bash
  grep -c "carried_forward\|ReworkImpactReport" openspec/learn-system-blackbox-architecture.md  # >= 2
  grep -n "M3 至 M6 全部失效" openspec/learn-system-blackbox-architecture.md                     # 期望 0 命中
  ```
- **已否决**：不要「让操作者手工挑哪些决定还有效」——1.2 万次决策的量级下不可行，
  必须由 LineageGraph 机器判定。
- **依赖**：DEPENDS_ON D-01（继承靠 `entity_id`）、D-02（LineageGraph 靠 ArtifactRef）。
- **拍板**：不需要。

---

## D-11 ｜ StageCheckpoint 定义

- **返工项**：RC 组第 3 条 ｜ **落点**：`§5` 或 `§17`（与 `§8` 的 StagePackage 关系也要写清）
- **约束边界**：落盘粒度（每 EditionPart / 每 N 次人工决定）、必含内容（已完成任务清单、已封存人工决定、
  待办队列剩余项、下一步指针）、恢复语义（恢复后已完成的人工决定不重做）。
  必须规定 M2/M3/M4/M6 在**每次人工决定后即时持久化**，不允许以阶段结束为唯一落盘点。
  必须写清 StageCheckpoint 与 StagePackage 的关系（前身 / 子集 / 独立对象，三选一）。
- **判据**：`grep -c "StageCheckpoint" openspec/...md` 从 1 增至 >= 4
- **拍板**：不需要。

---

## D-12 ｜ M3 / M4 人工队列的归属工具

- **返工项**：RC 组第 4 条 ｜ **落点**：`§11` `§12` `§14` 或 `§5`
- **约束边界**：二选一并写死，不得含糊：
  - **(a)** 把 M6 工作台提升为跨阶段 `Review Console`，`§14` 增列 M3 边界分歧、M4 类别候选分歧
    两种工作模式及各自输入 Package。
  - **(b)** `§5` Module 列表新增独立分歧裁决工具，定义其 Package 输入输出。
  参考：`§15` 已明文让 M7 复用 M6 工作台做提案裁决，故 (a) 与既有表述更一致。
- **判据**：`§11` 与 `§12` 各出现一次明确的工具归属句。
- **决议（2026-09-08）**：选择 (a)，把现有工作台提升为跨阶段 Review Console；决定仍归属原 Stage/Run。

---

## D-13 ｜ ReleaseRun 补 M6 回路

- **返工项**：RC 组第 5 条 ｜ **落点**：`§6.2`
- **约束边界**：补含 `M7 → M6 裁决 → M7 回流` 的完整流程图；规定该次 M6 运行产出的 ReviewDecision
  挂在哪个 Run 下；规定它是否影响原 EditionRun 的 ReviewedEditionPackage 封存状态
  （建议不影响——已封存者不可变，是 `§8` 的既定原则；但必须写明）。
- **判据**：`§6.2` 的流程图中出现 M6。
- **拍板**：不需要。

---

## D-14 ｜ 实施分期与首个纵切（新增章节）

- **返工项**：RF 组第 1 条 ｜ **落点**：新增 `§22`
- **约束边界**：
  - `§19` 十二行每行标注 `{首纵切内 / 首纵切后 / 本阶段暂缓}` 之一。
  - 标为「首纵切内」的**不超过 4 行**（硬上限，超了说明没在做取舍）。
  - 首纵切三元组已裁定：`technique_id=qizheng` + `Work=三辰通载三十卷` + `Edition=影宋鈔本`
    + `SourceAsset=ocr/data_work/sanche_pages/page_001..010.png`；`evidence_level=glyphbox_level`。
  - 纵切终点沿用 `LEARN_SYSTEM_TARGET.md:283-294`，但把「八字」改为七政，并同步在 TARGET 侧加一行说明，
    避免两份文档再次分叉。
- **判据**：
  ```bash
  grep -c "首纵切内\|首纵切后\|本阶段暂缓" openspec/learn-system-blackbox-architecture.md   # >= 12
  grep -c "首纵切内" openspec/learn-system-blackbox-architecture.md                          # <= 4
  ```
- **已否决**：不要按 `§19` 行序逐行拆 epic——审查已确认那会得到 12 条并行大工程，
  各推进 30% 时纵切仍为 0。
- **拍板**：不需要（三元组已裁定，分期由你按上限提议，做完请用户过目）。

---

## D-15 ｜ 最小可跑 fixture Edition

- **返工项**：RF 组第 3 条 ｜ **落点**：新建 `pipeline/corpus/_fixture/mini_ed01/` + `§19 §20` 引用它
- **约束边界**：≤3 页、≤5 batch；在**无内网、无 GPU、无外部模型 API** 条件下可跑完 M1→M6。
  建议直接取《三辰通载》page_001..003 的子集，与首纵切同源，避免再引入一套素材。
  必须被 `§20` 的判据命令引用为统一宿主。
- **判据**：`ls pipeline/corpus/_fixture/mini_ed01/` 非空，且 `§20` 中出现该路径。
- **拍板**：不需要。

---

## D-16 ｜ PLAN.md 只增补不重写 + 三列映射表

- **返工项**：RF 组第 4 条 ｜ **落点**：`PLAN.md`
- **绝对禁令**：**不得删除 PLAN.md 中任何未勾选项。** 审查已核出重写会丢失现有 26 条未完成项中
  至少 6 条（pipeline 环境检查、四本手册状态回写、《烟波钓叟歌》扩批模板、奇门试点材料、
  奇门金标集、旧 APP 迁移策略），以及整条 Tag 线与整条 OCR 线。
  规格 `§21` 并未把它们列为非目标，所以它们不是「已裁掉」，而是「会消失」。
- **约束边界**：
  - 建「差距行 ↔ 既有条目 ↔ owner 文件」三列映射表。
  - `§19` 每行必须有归属；每条既有未完成项标注 `mapped / superseded-by / out-of-scope` 之一。
  - 5 处重复登记收敛到唯一 owner 文件（`KnowledgeReleaseCompiler` 现存于 `PLAN.md:18`、
    `pipeline/TODO.md`、`pattern_knowledge_workbench/TODO.md`、`LEARN_SYSTEM_TARGET.md:258` 四处）。
  - 根 PLAN.md 只保留顺序与 Gate 状态，细节留在子计划，其余位置改为引用而非复制。
- **判据**：
  ```bash
  git diff PLAN.md | grep "^-" | grep -c "^-- \[ \]"   # 期望 0（未勾选项零删除）
  ```
- **拍板**：不需要。

---

## D-17 ｜ 五处既有存储的处置决议

- **返工项**：RF 组第 5 条 ｜ **落点**：`§17` 或 `§19`
- **约束边界**：对以下五处每处给出 `迁移 / 重跑 / 冻结为历史快照` 三选一，并写明理由：
  | 存储 | 现状 |
  |---|---|
  | `ocr/data_work/index.db` | OCR 工作库，10 页真实数据 |
  | `pipeline/units/` | 139 个知识单元，1331 条 assertion（1317 机器态） |
  | `pipeline/rag/index.sqlite` | dev 索引，已知 span_map 键碰撞 |
  | `pipeline/corpus/` | 八字与奇门试点语料 |
  | `pattern_knowledge_workbench/assets/ge_ju_database.sqlite` | 496 rules，知识字段全空 |
- **判据**：五行各有一个明确结论词。
- **决议（2026-09-08）**：校订事实与 corpus 迁移；可重建索引重跑；旧 units 与 496 条工作台库冻结。精确地图见 `openspec/legacy-storage-transition.md`。

---

## D-18 ｜ §20 十条完成标准判据化

- **返工项**：RE 组第 5 条 ｜ **落点**：`§20` 改写 + 新建 `openspec/acceptance/run_all.sh`
- **现状**：经逐条核验，十条中 **0 条**可用一条命令判定；第 3、5 条有部分基础；
  第 7 条按字面现在就能「通过」而构成新的假绿（496 行 original_text 全空，导入的是无证据空壳）。
- **约束边界**：
  - 每条改写为「命令 + 期望退出码 / 期望输出」二元组。
  - `bash openspec/acceptance/run_all.sh` 逐条打印 `PASS / FAIL / BLOCKED(前置缺失)`。
  - **允许 BLOCKED，不允许「无法执行」**——前置没就绪要能说出缺什么。
  - 第 7 条必须加阈值（Candidate 的必填字段与 fail-closed 拒绝规则），否则它会自己变绿。
  - 不改条目编号与条数，只改表述。
- **判据**：
  ```bash
  bash openspec/acceptance/run_all.sh; echo "exit=$?"    # 十条各有一行输出
  ```
- **依赖**：DEPENDS_ON D-15（多条判据要靠 fixture 才能跑）。
- **拍板**：不需要。

---

## D-19 ｜ 版权与存储三层边界（R1 审查后新发现）

- **返工项**：RG 组两条 ｜ **落点**：`§9` `§16` `§17` `§20.8`
- **冲突事实**：`.gitignore` 明令「版权源书:扫描/电子原书不进公开仓(只提取转录文本与派生产物)」，
  `*.pdf` 与 `raw_books/**/*.pdf` 均被忽略；首纵切源 PDF 实测 **247M**，物理与法律上均不可入仓。
  而 `§9` 要求 M1 输出「原始文件及哈希」、`§16` 含 `SourceAssetPack`、`§20.8` 要求发布物
  「同时包含原始资料」、`LEARN_SYSTEM_TARGET.md:140` 要求「客户端最终应能打开原始扫描件」。
- **约束边界**：
  - 明确三层存储边界：**Git 仓库**（转录与派生产物）/ **本地 Object Store**（`§17`，含受版权限制的原件，
    不进 Git）/ **PublicationPackage**（对外分发物）。
  - 规定 SourceAsset 在源书不可分发时的登记形态：外部路径引用 + SHA-256 + 页数 + 页图派生物清单，
    使 `§9` 的「原始文件及哈希」可在不入仓的前提下满足。
  - 为 `SourceAssetPack` 定义至少两档内容级别（如 `full_scan` / `derived_page_images_only` /
    `reference_and_hash_only`），并写明各档下客户端高亮功能的可用性。
  - 在 `§21` 或 ReleasePolicy 中写明首纵切采用哪一档。
  - 注意：现有 10 页 PNG（10M）**未被 .gitignore 忽略**，说明「派生页图」可入仓、「源书」不可，
    这条既成事实可以直接作为规则依据。
- **判据**：
  ```bash
  grep -c "Object Store\|不进 Git\|派生页图" openspec/learn-system-blackbox-architecture.md  # >= 2
  grep -c "full_scan\|derived_page_images_only\|reference_and_hash_only" openspec/...md      # >= 2
  ```
- **决议（2026-09-08）**：源 PDF 放本地 Object Store、不进 Git；APP 保留打开原书能力，实际分发档位由 ReleasePolicy 与权利状态决定。

---

## 执行顺序（依赖已排好，照此推进即可）

```
第 1 轮（无依赖，可并行）
  ACT 01  本地库不再被覆盖
  ACT 02  保存不再自动 verified
  ACT 03  删 enumeration
  T-11    §19 差距表修正（纯事实搬运）
  D-16    PLAN.md 映射表（防止后续丢项）

第 2 轮（拍板后开工）
  已拍板：D-04 / D-05 / D-09 / D-12 / D-17 / D-19 / ACT 04
  D-01 → D-02 → D-03            内核契约链，严格按序
  T-02 T-03                     依赖 D-02/D-03 的产出

第 3 轮
  D-09 → D-10 → D-11            Gate 与失效传播链
  D-13 D-14 D-15
  T-01 T-04 T-05 T-06 T-09 T-10 T-12 T-13   （彼此独立，可并行）

第 4 轮
  D-06 D-07 D-08                依赖 D-01/D-05
  T-07 T-08                     依赖 D-05/D-07
  D-18                          依赖 D-15
```
