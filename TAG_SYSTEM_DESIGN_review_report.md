# `TAG_SYSTEM_DESIGN.md` 评审报告

> 评审日期：2026-07-11
>
> 被评审文档：`TAG_SYSTEM_DESIGN.md`（v1.0-draft-r1）
>
> 评审性质：产品、信息架构、UI/UX、工程契约、风险与 OpenSpec 就绪度评审
>
> 评审方法：gStack CEO／Design／Engineering review 视角，Superpowers 证据优先与系统化审查，UI/UX Pro Max 的渐进披露、无障碍、触控、响应式与认知负荷检查尺度，并与 `METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md`、现有 pipeline Schema 和 glossary 样本交叉核对。

## 1. 执行结论

这份文档有很强的产品哲学和安全意识，但目前还不是一份可以直接进入实现或 OpenSpec 的 Tag 最终规范。

它当前最适合被定义为：**Marks 产品与视觉策略母稿**。

文档最有价值的两项资产是：

1. “借你师傅的眼，不替你下师傅的断”的产品边界；
2. 把专家注意力结构转译为一致视觉语法的产品方向。

最大结构性问题是：把知识分类、计算事实、视觉组件、展示实例、用户熟练度、合规策略和埋点协议装进了同一个 Tag Registry。若不先拆层，后续会出现契约漂移、错误归因、无法复现、合规 fail-open 和 UI 复杂度失控。

### 1.1 综合评分

| 维度 | 评分 | 判断 |
|---|---:|---|
| 产品哲学 | 9/10 | “借眼不代断”清晰且有差异化 |
| 安全与信任 | 8/10 | 红线完整，但部分执行机制不足 |
| 信息架构 | 5/10 | Tag、Concept、Mark、实例和样式混层 |
| UI/UX | 6/10 | 交互骨架不错，关键状态矩阵不完整 |
| 工程可实现性 | 4/10 | Schema 尚不能表达真实运行时对象 |
| 可验证性 | 4/10 | 指标方向正确，验收口径不足 |
| OpenSpec 就绪度 | 3/10 | 决策链、能力边界和场景要求尚未拆开 |

## 2. 做得好的部分

### 2.1 产品边界强

“注意＋识别，不替用户裁决”是一条可长期使用的产品原则。它同时覆盖内容、视觉、动效、无障碍文案和聚合展示，明显优于只写一条“免责声明”。

### 2.2 已识别重要认知陷阱

文档主动识别了：

- 旺不等于吉、衰不等于凶；
- 格局属性不等于个人事件结论；
- 颜色不能单独承载语义；
- 吉凶数量对比本身也可能构成聚合裁决；
- 稀缺、吉凶和付费机制不能互相借势。

这些判断应保留，并进一步转成机器可判定的不变量。

### 2.3 有良好的渐进披露雏形

Glance／Read／Tap 三层，以及“Mark 不直接点击、点击宿主元素进入详情”的思路，解决了一部分盘面密度和触控目标冲突。

### 2.4 已意识到版本治理的重要性

视觉语法一旦被用户习得，破坏性修改会清空用户资产。把它按 API 兼容性治理是正确方向。

## 3. P0 结构性缺陷

### P0-1：Tag、Concept、Mark 和运行时实例没有分开

文档同时把以下对象放在 Tag／Mark 语境中：

- `Concept`：白虎、三奇入墓等稳定知识概念；
- `Assertion`：某格局在某条件下具有某属性的主张；
- `ComputedFact`：当前盘中某元素旺、空亡、被克；
- `DisplayMark`：角标、能量条、印章、关系线；
- `UserState`：L1／L2／L3 和熟悉度；
- `PresentationToken`：颜色、纹理、尺寸；
- `TelemetryEvent`：曝光、详情到达、溯源点击；
- 用户自建的收藏标签、文件夹标签。

例如，“此盘中乙奇入墓”不是一个 Concept，而应拆成：

```text
Concept：三奇入墓
+ ChartEntity：乙奇所在宫
+ RuleEvaluation：满足入墓条件
+ CalculationProfile：所用起局与判定规则
+ SchoolView：采用哪个流派口径
= MarkInstance
```

现有 pipeline 只有 `SourceSpan`、`KnowledgeUnit`、`Assertion` 和初步 `Concept`，还没有 `ChartEntity`、`ComputedFact`、`RuleEvaluation` 和 `MarkInstance`。因此当前 Registry 没有完整的运行时承载对象。

**建议分成六层：**

```text
Knowledge layer
Concept → Assertion → Evidence / SchoolView

Runtime semantic layer
ChartEntity → ComputedFact / Relationship / PatternMatch

Presentation layer
MarkDefinition → MarkInstance → VisualToken

Experience layer
ExposurePolicy → UserProficiency → DensityDecision
```

Tag 必须被限定为其中一种正式对象，不能继续泛指全部。

### P0-2：`species_contract` 混合了不同生命周期的数据

当前 `species_contract` 同时包含：

- 类型定义：`species`、`semantic_family`；
- 具体绑定：`concept_id`；
- 本地化资源：`locale_profile`；
- 观测策略：`telemetry`；
- 用户曝光策略：`density_tier`；
- 发布政策：`compliance`；
- UI 能力：`condition_affordance`；
- 内容状态驱动的展示要求：`school_variance_display`。

这些字段的 owner、发布频率、回滚条件和权限边界不同。放在同一个 Registry 会形成“万能配置中心”，任何改动都可能同时影响知识、UI、合规、埋点和学习状态。

**建议拆成：**

- `MarkSpeciesDefinition`
- `MarkVisualGrammar`
- `MarkInstance`
- `MarkContentBinding`
- `ExposurePolicy`
- `JurisdictionPolicy`
- `TelemetryContract`

知识 Registry 和 UI Registry 不应宣称是同一个唯一数据源；它们可以各自权威，再由编译器生成不可手工编辑的 `MarkReleaseBundle`。

### P0-3：流派分歧展示与 v1.2 母稿冲突

Tag 文档把流派分歧主要放在元素详情卡 Tap 层。但 v1.2 要求：若分歧会改变用户当前判断，首层必须显示“存在分歧”，不能被默认流派静默折叠。

**建议改为两级：**

- 首层：中性地显示“存在关键分歧”；
- 详情层：展示各流派主张、条件、证据与当前选择；
- 不会改变当前判断的次要分歧，可以只在详情层呈现。

### P0-4：Phase B 仍包含被母稿禁止的 AI 文盘联动

文档顶部已承认阶段冲突，但 Phase B 仍安排“AI 解释 ↔ 盘面”。v1.2 已明确阶段零和阶段一均禁止用户盘面 AI 解释，因此属于实施计划未真正收敛。

**建议改为：**

- 阶段零：人工证据卡 ↔ 静态示例盘；
- 阶段一：确定性计算事实 ↔ 原文／证据卡；
- 阶段二候选：AI 解释联动，必须新建 Decision ID；
- 阶段一 Registry、客户端、发布包中不保留不可启用的 AI 入口、占位组件或承诺文案。

### P0-5：稀缺三维视觉与冻结项冲突

普通、稀有、极罕见的逐级纹理和高光，即便声明“不代表吉凶”，仍可能被理解为更厉害、更值得分享、更值得付费或类似抽卡稀有度。v1.2 已冻结稀缺格局的高光、召回和付费刺激。

**建议：**阶段零完全移除三维稀缺表现。若确需展示“少见”，只使用中性文本统计，并同时显示材料范围、分母和 Registry 版本，不能把“当前数据库中少见”冒充“现实中罕见”。

## 4. P1 产品与 UI/UX 缺陷

### P1-1：能量条可能系统性教错知识

文档已经意识到“满格＝好”的血条隐喻，但主要依靠 tooltip、反例和测试题纠正。前注意层隐喻发生在用户阅读解释之前，用文字解释对抗视觉直觉是弱通道对抗强通道。

同时，旺衰与十二长生未必适合被表达为同一条线性“能量”尺度。这样可能把阶段、状态和强度错误压缩为一个数值模型。

**建议 Phase A 对比：**

1. 能量条；
2. 中性序位刻度；
3. 环形阶段／周期符号。

验收不仅测“能否看懂”，还要测：

- 是否误以为旺等于吉；
- 是否误以为十二长生是线性战斗力；
- 是否理解同一状态在不同角色和条件下意义不同。

若误判率不能显著降低，应放弃能量条，而不是继续增加免责声明。

### P1-2：“Mark 不可点、元素可点”仍可能不可发现

虽然这一方案解决了小 Mark 不满足 44pt 触控目标的问题，但又产生新的心智负担：

- 用户看到 Mark，却不知道应该点宿主元素；
- 一个元素存在多个 Mark 时，不知道详情卡会落到哪一项；
- 关系线跨两个实体，不清楚应该点起点、终点还是线；
- 键盘和读屏用户无法依靠视觉附着关系推断入口。

**建议：**

- 宿主元素整体必须有明确的可交互状态；
- 点元素后自动定位到刚才关注的 Mark；
- 关系线两端提供等价入口；
- 读屏将元素与 Mark 合并成结构化摘要；
- 图例显式演示“如何查看详情”；
- Web／桌面补齐键盘 focus、focus tooltip 和深链接。

### P1-3：元素详情卡正在成为万能抽屉

当前详情卡同时承载状态、关系、角色、结构、吉凶三件套、流派、审核状态和溯源，极易在小屏、大字、繁体和英文环境下变成超长底部抽屉。

建议按照用户任务组织，而不是按照后台语义族平铺：

1. 当前最值得看的一件事；
2. 为什么值得看；
3. 成立条件与未成立条件；
4. 来源与分歧；
5. 其他状态和关系折叠。

同时补全以下状态：空、加载失败、数据过期、计算配置改变、流派切换、无来源、争议未决、大字、横屏、平板、返回后恢复焦点与缩放。

### P1-4：L1／L2／L3 把熟练度压成单一等级

用户可能熟悉九星但不熟悉格局，能够识别符号但不能迁移新盘；也可能专业水平很高，却因视力或认知负荷偏好低密度。`per-technique` 比全局等级好，但仍然过粗。

**建议改为能力向量：**

```yaml
proficiency:
  entity_recognition: 3
  state_interpretation: 2
  relationship_reasoning: 1
  pattern_transfer: 0
  provenance_literacy: 2
density_preference: compact
accessibility_profile: large_text
```

展示密度应由任务、熟练度、用户偏好、设备和无障碍设置共同决定。长期未活跃后的静默降级也需要重新评估，避免用户回归时界面在无解释情况下变化。

### P1-5：国际化不应改变基础语义色

“locale 维度下色值可按文化语义微调”会破坏“一处一义、处处同形”的学习承诺，并导致语言切换、教程截图、跨地区分享和视觉回归不一致。

建议基础语义编码全球一致，只允许出于对比度、显示设备和主题进行受控映射。文化解释属于内容层，不应改变核心视觉语法。

### P1-6：缺少明确的产品语气和目标用户约束

UI/UX Pro Max 的自动设计系统把当前产品误判为活泼、儿童教育、游戏化风格。这不是采用该风格的理由，反而证明文档没有给出足够清晰的设计输入。

建议新增设计原则：

- 产品类型：严肃的证据型术数学习工具，而非儿童教育或娱乐抽卡；
- 目标用户：从新手到进阶者，并包含中老年和低端 Android 用户；
- 视觉语气：克制、可信、内容优先、非神秘恐吓、非游戏稀缺；
- 禁止模式：儿童化字体、过度鲜艳、游戏战力条、稀有度高光、装饰性动效抢占注意。

## 5. P1 工程与治理风险

### P1-7：MarkInstance 缺少可复现计算上下文

动态角色、旺衰、格局成立和合化都不是静态知识属性。至少需要：

```yaml
mark_instance:
  mark_instance_id: mi_...
  mark_definition_id: md_...
  concept_id: co_...
  chart_id: ch_...
  entity_ids: [ce_...]
  calculation_profile_id: cp_...
  rule_id: rule_...
  rule_version: 1.0.0
  evaluation_status: matched
  matched_conditions: []
  unmet_conditions: []
  school_view_ids: []
  evidence_ids: []
  generated_at: ...
```

否则同一盘在不同设置或流派下显示不同 Mark 时，系统无法解释“为什么变了”。

### P1-8：合规不能只做大陆／海外二分

境外不是统一司法辖区。还必须定义：

- profile 缺失时默认行为；
- 账号区、设备区和实际服务地区冲突时的决策；
- 旧客户端不认识新政策时的降级；
- 缓存、离线包、分享和截图的政策继承；
- policy bundle 的版本、签名、撤回和 fail-closed。

### P1-9：Registry 版本治理不完整

除了未知物种，还应覆盖：

- Schema version 与 content version 分离；
- 最低客户端版本；
- 未知字段、未知枚举、新增必填字段；
- bundle 完整性和签名；
- 缓存失效；
- 双轨期间的事件版本；
- 旧视觉语法移除条件；
- 实验数据的版本污染隔离。

### P1-10：无障碍仍停留在 label 层

`a11y_label_policy: provenance` 过于粗糙。应分别定义：

- accessible name；
- role；
- value；
- selected／expanded／current 等 state；
- hint；
- reading order；
- 动态更新播报；
- 关系线的文本替代；
- 图形盘的线性化摘要；
- 大字模式替代布局；
- 键盘、开关控制和手势替代。

不能把全部信息塞入一段超长 label，否则读屏会产生新的认知负担。

## 6. 指标与实验缺陷

### 6.1 北极星只测视觉语法记忆，不测迁移能力

7 日无字识别率只能证明用户记住图形，不能证明用户理解概念、条件、反例、流派差异，也不能证明能迁移到新盘。

建议改成两级指标：

- 近端指标：视觉语法识别率；
- 产品北极星：新盘迁移判断正确率，并能指出关键条件、反例和来源。

更合适的 Aha 是：用户能够说出一个盘面事实、它成立的关键条件、一个来源位置，以及自己因此修正了哪一步判断。

### 6.2 “显著”“达标”“更高”不可直接验收

H28–H30 缺少：

- 最小可检测效应；
- 样本量和分层方式；
- 新老用户排除条件；
- 预注册；
- 多重检验处理；
- 负向停止线；
- 无障碍人群独立样本；
- 误导率和恐惧率阈值。

正式 OpenSpec 中不得使用“显著、达标、可接受、基本完成”作为单独验收标准。

## 7. 尚未充分挖掘的需求

建议补入需求池：

1. 用户自定义标签与系统知识 Tag 的命名空间隔离；
2. 同义词、异体字、繁简体、旧称、新称和误写治理；
3. Concept 合并、拆分、废弃后的引用迁移；
4. 多来源冲突下的默认呈现逻辑；
5. 用户选择流派与“暂不选择”的体验；
6. Mark 判错后的纠错、撤回、缓存失效和影响面定位；
7. 教师／专家模式与学习者模式；
8. 分享或截图时附带来源、流派和计算配置；
9. 打印、黑白、低对比度和色觉异常模式；
10. 盘面缩放后的聚合、隐藏与重现规则；
11. 离线模式和 Registry 版本不一致；
12. Mark 的深链接和稳定 URL；
13. “为什么没有显示某个 Mark”的可解释性；
14. 密度服务隐藏了什么、为什么隐藏；
15. 规则判定为“不确定”而不是 true／false 时的表现；
16. 多个流派对同一格局分别成立／不成立；
17. 动爻、转宫、合化等状态转换历史；
18. 埋点最小化、保留周期和退出机制；
19. 内容作者、审校者、规则维护者和设计系统维护者的权限边界；
20. 决策和视觉规则变更对既有学习测量的影响。

## 8. 推荐的 OpenSpec 拆分

不要继续在同一文件追加 G11、G12。建议拆成五个 capability：

### 8.1 `knowledge-concept-taxonomy`

定义 Concept、同义词、流派、来源、版本、合并、拆分和生命周期。

### 8.2 `computed-mark-semantics`

定义 ChartEntity、ComputedFact、关系、格局匹配、条件、RuleEvaluation 和 calculation profile。

### 8.3 `mark-visual-grammar`

定义 State／Relation／Role／Pattern 的形状语法、视觉 token、主题、降级、图例和无障碍。

### 8.4 `mark-exposure-and-learning`

定义熟练度向量、密度、用户控制、主动测验、状态恢复和学习指标。

### 8.5 `mark-safety-and-jurisdiction`

定义吉凶红线、争议首层提示、司法辖区矩阵、fail-closed、撤回和事故响应。

每个 capability 的 requirement 至少包含：

- REQ-ID；
- Decision ID；
- 当前批准状态；
- Approved by／Approved at；
- SHALL；
- 阶段、地域和用户；
- Owner；
- 依赖；
- Given／When／Then；
- Evidence IDs；
- 验证方法和测试数据集；
- 机器可判定谓词或量化阈值；
- 证据产物；
- 回滚条件。

## 9. 推荐调整顺序

1. 统一名词：Tag、Concept、MarkDefinition、MarkInstance；
2. 画出知识层—计算层—展示层—体验层的数据流；
3. 删除 Phase B 的 AI 文盘联动；
4. 暂停稀缺三维表现和自动熟练度换代；
5. 将争议展示改为“首层提示、详情展开”；
6. 将 Registry 拆成多个权威来源和一个编译产物；
7. 用真实奇门样本建立 15–20 个 `MarkInstance` 金标；
8. 对比测试能量条、中性序位刻度、周期符号三种视觉方案；
9. 原型通过后，再把用户批准的结论写入 OpenSpec。

## 10. 建议的阶段零最小范围

为避免一次设计十个物种却无法验证，阶段零建议只验证：

- 一个术数：奇门；
- 两个语义族：State、Pattern；
- 三种状态：confirmed、disputed、unknown；
- 一个静态示例盘；
- 人工精编证据卡，不使用用户盘面 AI 解释；
- 15–20 个 MarkInstance 金标；
- 三种视觉原型；
- 无字识别、误把旺当吉、新盘迁移、来源理解四类测试。

Relation、Role、ShenSha、稀缺高光、自动等级换代、多语言和 AI 文盘联动均应在阶段零证据成立后再进入候选。

## 11. 最终建议

保留文档的“注意力结构”和“借眼不代断”作为上位产品原则；把当前文档改名或重新定位为 Marks 策略母稿。下一步首先拆分知识本体、计算事实、视觉定义、运行时实例和学习曝光策略，再建立真实样本契约。完成这些工作后，文档才具备工程实施和 OpenSpec 化条件。
