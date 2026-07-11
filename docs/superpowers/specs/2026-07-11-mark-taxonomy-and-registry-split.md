# Mark 分类学与 Registry 拆分决议

> 状态：决议稿，2026-07-11。解决 `TAG_SYSTEM_DESIGN_review_report.md` P0-1（对象未分层）与 P0-2（契约混合生命周期），并为 G1–G3 术理问题给出带扩展点的默认处置（PENDING_EXPERT）。
> 效力：本规格通过后，"Tag"一词退役；`TAG_SYSTEM_DESIGN.md` §4.2 单一契约作废；Tag Style 规格的 `TagRenderModel` 即本规格 `MarkInstance` 的只读投影（D-020）。
> 本规格是 Registry 1.0 冻结与一切契约编码的前置条件。

## 1. 六层对象模型

```text
知识层（管线产出，修订治理见 v1.1 §6.2）
  Concept        稳定知识概念（白虎猖狂、三奇入墓、天蓬）
  Assertion      有出处的主张（含条件、例外、立场）
  SchoolView     流派口径（含"是否改变当前判断"标记）
  Evidence       SourceSpan 引用

运行时语义层（排盘引擎产出，确定性、可复现）
  ChartEntity    盘中实体（某宫、某爻、某干支），含 temporal_phase
  ComputedFact   计算事实（乙奇在坤宫、月令未土、旬空）
  RuleEvaluation 判定结果（满足入墓条件）＋ CalculationProfile（起局与判定规则版本）
  PatternMatch   格局命中

展示层（UI Registry 治理）
  MarkDefinition 物种定义（形状语法族、注意层、必渲染槽）
  MarkInstance   一次具体渲染的语义载体 =
                 Concept + ChartEntity + RuleEvaluation
                 + CalculationProfile + SchoolView
  VisualToken    颜色、纹理、尺寸、动效（官方或用户样式）

体验层（产品策略治理）
  ExposurePolicy    曝光策略（轮播选牌、日历排期）
  UserProficiency   per-technique 熟悉度（L 层级）
  DensityDecision   密度裁剪结果
```

示例："此盘中乙奇入墓" ≠ 一个 Concept，而是：

```text
Concept(三奇入墓) + ChartEntity(乙奇@坤宫) + RuleEvaluation(入墓条件满足)
+ CalculationProfile(qimen_engine_v2/转盘/拆补) + SchoolView(某派口径)
= MarkInstance → 由 MarkDefinition 决定形状语法 → 由 VisualToken 决定外观
```

层间依赖单向向下：体验层可读展示层，展示层可读语义层，语义层可读知识层；反向引用禁止。

## 2. Registry 拆分

原 `species_contract` 按 owner 与生命周期拆为七个对象。知识 Registry 与 UI Registry **各自权威**，由编译器合成不可手工编辑的 `MarkReleaseBundle`（沿用 v1.1 ReleaseBundle 机制与哈希）。

| 对象 | Owner | 发布节奏 | 原契约字段迁移 |
|---|---|---|---|
| `MarkSpeciesDefinition` | 工程＋设计 | 慢（破坏性变更走视觉语法版本治理） | species、semantic_family、attention_layer、verdict_capability(恒 none)、required_slots |
| `MarkVisualGrammar` | 设计 | 中 | 形状语法、尺寸降级档、模板与 Renderer 白名单（含 Tag Style Capability Registry） |
| `MarkContentBinding` | 知识负责人 | 随知识发布 | concept_id、omen_carrying、condition_affordance、school_variance_display、"是否改变当前判断" |
| `MarkInstance` | 运行时生成，不入库配置 | — | （运行时对象，Tag Style 的 TagRenderModel 是其只读投影） |
| `ExposurePolicy` | 产品 | 快 | density_tier、L 层级放开表 |
| `JurisdictionPolicy` | 合规 | 独立、可紧急发布 | compliance 降级 profile（大陆／海外／未来分辖区） |
| `TelemetryContract` | 数据 | 中 | telemetry 事件 Schema |
| （横切）`LocaleResource` | 本地化 | 随内容 | locale_profile、a11y label 文案（走溯源管线的知识文案部分） |

拆分裁决规则：一个字段改动需要谁批准、影响哪层回滚，就归谁。任何"同时影响知识、UI、合规、埋点"的万能配置一律拒绝进入单一对象。

## 3. G1–G3 处置【EXPERT_REVIEWED，已定稿（D-022，卦师评定 2026-07-11）】

默认方案经占卜师评定通过，以下为定稿内容（含评定补充的五条约束）：

**评定补充的硬约束**：

1. `transformation_overlay` 的视觉权重**必须低于**本体五行色与能量条——防止新手把合化临时状态误认为主体属性；
2. 全部修饰 overlay（化标、空亡圈、有变指示）**统一中性灰度，禁止高饱和彩色与吉凶向色**，仅作识别符号；
3. `phase_comparison` 区块自动挂载 SchoolView 溯源（伏吟反吟判定各派不同）；
4. 三个扩展点（transformation_overlay、StateModifier、phase_comparison）全部接入 telemetry，统计详情卡查看频次，作为未来是否放开盘面全量展示的依据；
5. minimal 尺寸档下隐藏全部修饰标记，只保留核心 OrdinalState 能量条（对齐尺寸降级映射）。

**G1 合化变性**（乙庚合化金）：
- 语义层：`ComputedFact` 支持 `transformation`（本相 concept_id、化后 concept_id、化之判定 RuleEvaluation、SchoolView——化与不化本身有流派分歧）；
- 展示层默认：**本相色保持＋"化"修饰标记叠加**（保留"它本是乙木"的教学线索），不直接改身份色；
- 扩展点：MarkVisualGrammar 预留 `transformation_overlay` 槽。

**G2 非序数状态修饰**（空亡、入墓、被冲破）：
- 状态族拆两个子型：`OrdinalState`（旺衰五级／十二长生，能量条）＋ `StateModifier`（布尔修饰，继承传统符号，如空亡"○"）；
- **已定稿（方案 A）**：StateModifier 挂载为 CornerMark 子语义，`MarkSpeciesDefinition` 中 CornerMark 增加子语义区分字段 `corner_semantics ∈ {role_corner, state_modifier_corner}`，防止与用神／值符角色语义混淆；物种总数保持十个不变。

**G3 变动双态**（六爻变爻、伏吟反吟）：
- 语义层：`ChartEntity.temporal_phase ∈ {original, transformed}`，同位双实体合法；
- 展示层默认：盘面只显本态＋"有变"指示符，双态并置在元素详情卡内展开；
- 扩展点：详情卡规格含 `phase_comparison` 区块。

## 4. 命名退役表

| 退役词 | 正式对象 |
|---|---|
| Tag（泛指） | 按层取名：Concept／ComputedFact／MarkInstance／VisualToken |
| Tag Registry（单一数据源） | 知识 Registry＋UI Registry＋MarkReleaseBundle 编译产物 |
| species_contract | §2 七对象 |
| TagRenderModel | MarkInstance 只读投影（Tag Style 规格内保留该名作投影类型名） |

## 5. 生效条件与下游动作

1. 用户确认本决议 → `TAG_SYSTEM_DESIGN.md` §4.2 标注作废（已完成）、Tag Style 规格 §4.1/§6.2 引用本规格对象名；
2. Registry 1.0 冻结解锁条件 = 本决议确认 ＋ G1–G3 考据完成或接受默认处置（D-020）；
3. OpenSpec capability 对应关系：本规格覆盖评审报告建议的 `knowledge-concept-taxonomy` 与 `computed-mark-semantics` 的对象定义部分，实施拆分见执行计划。
