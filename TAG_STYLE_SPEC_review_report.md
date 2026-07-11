# Tag Style 个人定制规格 交叉评审报告

> 评审对象：`docs/superpowers/specs/2026-07-11-tag-style-system-design.md`
> 评审日期：2026-07-11
> 评审视角：学习系统哲学守护（TAG_SYSTEM_DESIGN 红线体系）× gStack CEO/PM（阶段纪律与市场）× OpenSpec（契约治理）× UI/UX Pro Max
> 性质：交叉评审——重点检查该规格与既有设计语料（TAG_SYSTEM_DESIGN v1.0-draft-r1、v1.2 母稿、From_Buyer_To_Owner）的冲突与缺口，不重复其自身已完成的两轮工程自洽评审。

## 1. 总体判断

工程设计成熟：DisplayContract 把"样式不得篡改语义值"工程化，是"断象不断事"哲学在渲染层的正确投影；原子回退、规范化 AST、Marketplace 权威外置、SVG 允许列表均为高质量决策，予以确认。

但该规格存在**一处与学习系统地基的正面冲突（R1）**、**一个可绕过全部红线的样式后门（R2）**、**一次阶段纪律违规（R3）**，以及 Marketplace 预留中的**内容治理缺位（R4）**。这些都不是工程瑕疵，是产品决策级问题，按 v1.2 治理规则应各建 Decision ID，不应在工程规格内静默裁决。

### 1.1 同步状态（2026-07-11）

本报告已同步当前主规格与 v1.2 决策登记状态：

- 工程复审发现的 Capability Registry、Host Geometry、坐标与变换、Draft/Preview/Active、AST、作用域、Marketplace 信任边界、原子 fallback、字体、安全和 OpenSpec 拆分已经进入主规格正文；
- R1–R5 已形成 D-015–D-020，并在 v1.2 登记为用户原则批准；
- 当前主规格只在顶部状态说明中引用 D-015–D-020，§12、§14、§19、§20 等正文尚未逐条按决策重写；
- 因此必须区分：**决策已批准**、**工程基础已补齐**、**产品裁决尚待回写正文**。在正文回写完成前，主规格仍不具备直接转 OpenSpec 的条件。

## 2. 主要发现

### R1｜定制自由与视觉语法习得的正面冲突（P0，产品决策级）

**同步状态：D-015、D-016 已批准；主规格正文待回写。**

规格 §12 明确："用户可以把旺设为绿色、衰设为红色……系统不能替用户决定个人审美"；§20 非目标列有"强制用户遵循官方旺衰颜色"。

这与学习系统的全部前提正面相撞。TAG_SYSTEM_DESIGN 的总纲是"让旺衰生克像交通标志一样被习得——靠形状语法的绝对一致性"；红线 4 明令"状态中性于吉凶，永不红绿"，其理由不是审美而是**认知安全**：旺=绿=好的映射会系统性教错知识（忌神旺是坏事）。交通标志之所以有效，恰恰因为**没有人能自定义它**。允许 L1 用户把旺设绿衰设红，等于亲手把我们花整个设计对抗的认知陷阱交还给最没有防御力的人群；且截图分享、帮朋友看盘、评论区嵌图都会把碎片化的私人语法扩散进共享语境。

但规格的自由派立场对成年用户也是成立的，且定制是真实的留存与商业化需求（排盘类产品用户对自定义配色的偏好已被竞品验证）。**这是权衡，不是对错**，故必须升为产品决策。建议的调和方案：

1. **分层定制权**：装饰通道（Vessel、背景、贴图、字色之外的一切）第一天全开放；**语义通道**（状态梯度的方向映射、关系方向符号、类别形状语法、吉凶槽的呈现）默认锁定，通过"视觉语法毕业测试"（无字识别达标）后解锁。定制权成为学习激励——"通过毕业测试解锁完全自定义"本身就是 From_Buyer_To_Owner 转化漏斗的一级台阶。
2. **场景豁免清单**：学习练习、测试、月令条、分享物截图、评论区嵌入强制官方样式（或显著标注"自定义样式"）——测试场景若允许自定义样式，北极星指标直接失效。
3. **实验隔离**：定制用户在 H28／北极星 cohort 中单独标记，防污染。
4. 若用户仍选择完全自由：至少在用户首次做出"旺=绿"类反转映射时给一次性认知提示（可关闭），此后尊重选择。

### R2｜必渲染槽未定义：红线可被样式后门绕过（P0，需硬约束）

**同步状态：D-017 已批准；`required_slots` 与上游契约链待写入主规格 Capability Registry。**

规格保证"样式不能篡改语义值"，回退链处理的是**失败**场景——但没有任何条款禁止样式**故意省略语义槽**。具体攻击面：

- ShenShaSymbol 的 `dispute_state` 是独立槽——样式变体可以干脆不渲染它 → 流派争议标识消失（违反准则 8）；
- OmenIndicator 的条件可及入口（吉凶三件套的 Tap 通道）若被纯图片背景样式覆盖省略 → **禁区三"无条件裸奔"经由样式层实现**；
- Counter 的 overflow 语义被 state_asset 映射规避后，精确值的可达通道是否保留仅由 DisplayContract 决定，但 DisplayContract 由 Host 业务声明——规格没有要求 Host 声明必须遵守上游知识契约。

修复：Capability Registry 为每个物种定义 `required_slots`（如 ShenShaSymbol.dispute_state、OmenIndicator.condition_affordance），由 Host 强制渲染，样式不可省略、不可遮挡（机制上与 interaction_overlay 同级）。同时明确契约链的单向依赖：**知识语义契约（species_contract/MarkInstance）→ DisplayContract → TagTemplate 能力**，DisplayContract 的字段取值范围由上游契约约束，Host 不得声明低于知识契约要求的 DisplayContract。

### R3｜阶段纪律违规：编辑器是又一座提前动工的教堂（P0，排期级）

**同步状态：D-018 已批准并标为 `FROZEN_PENDING_EVIDENCE`；主规格 Phase B 与编辑器章节待改为候选设计，不得作为当前承诺。**

产品当前处于阶段 0：H1/H2（学习需求、付费意愿）未验证，管线试点刚跑通两三个工位。而本规格的 Phase B 是一个完整的编辑器产品：可视化编辑＋YAML 面板＋AST 双向同步＋实时预览＋undo/redo＋导入导出＋原子激活回滚＋安全编译管线。这是数月级的重投入，服务的假设（"用户想深度定制 Tag 外观"）本身未经任何验证——与 v1.1/v1.2 确立的"三阶段验证式开发、判据未过不扩建"纪律直接冲突。

建议的验证式替代路径：

1. **保留 Phase A 全部契约设计**（TagRenderModel、DisplayContract、Host Geometry、坐标系、Registry Schema）——架构预留成本低，防止未来返工，值得现在做；
2. **用官方预设样式包先行验证需求**：官方制作 3–5 套主题皮肤（古风、极简、暗色等），走同一 TagStylePackage 格式与引擎，无编辑器。观察启用率、切换率、留存差异——这是"换肤需求"的十分之一成本验证；
3. 编辑器（Phase B）押后至产品阶段 1 出留存数据、且预设包使用率达标之后，立项时建 Decision ID；
4. Marketplace 元数据预留照旧（成本近零）。

### R4｜Marketplace 内容治理预留缺位（P1，预留字段级）

**同步状态：D-019 已批准；内容治理占位和 reserved capability 待回写主规格。**

规格正确地把审核、支付等推迟到未来，但 MarketplaceMetadata 预留字段只覆盖商品识别（ID、版本、许可、兼容性、预览），没有为**内容治理**预留任何占位。在这个行业的污名背景下，未来分发场景有三类可预见的具体滥用：

1. **恐吓风格包**：把全部凶类 Tag 做成血腥、骷髅、火焰风格出售——行业的神煞恐吓套路以 UGC 商品形式回流，且平台收了钱；
2. **权威伪装风格包**："大师专业版"式样式增强诈骗引流者的可信度装备；
3. **官方稀缺纹理伪造**：用户样式复制官方"极罕见格局"的三维稀缺纹理（立体纹理＋高光），汇聚签的稀缺诚实性（红线 11：稀缺只能来自格局罕见度）被样式伪造击穿。

修复成本极低：MarketplaceMetadata 预留 `content_rating`、`expression_tendency` 占位字段；**官方稀缺分级纹理声明为保留能力（reserved capability）**，用户样式不得复制——第三条建议现在就做，不等 Marketplace，因为个人样式的截图分享同样能伪造稀缺感。

### R5｜上游未稳，字段先冻（P1，时序级）

**同步状态：D-020 已批准；Registry 冻结顺序和 MarkInstance 合一关系待回写主规格。**

本规格的 TagRenderModel 字段表（species、omen、state、disputeState…）实质上就是 `TAG_SYSTEM_DESIGN_review_report.md` P0-1/P0-2 呼吁建立的运行时实例对象（MarkInstance/computed-mark-semantics）。但上游评审的 P0（Tag/Concept/Mark 未分离、species_contract 混合生命周期）尚未收敛，此时冻结 TagRenderModel 字段清单，等于在沙地上打桩——上游分类学一动，Registry 1.0 立即面临 breaking change（而视觉语法版本治理规定破坏性变更代价极高）。

同理，TAG_SYSTEM_DESIGN 第三轮的 G1–G3（合化变性、空亡类非序数状态修饰、变爻双态）在本规格的模板清单中无载体：`meter` 承载不了空亡"○"符号（布尔修饰非梯度），十二长生 12 段对 meter 模板的支持未声明。

修复：明确排序——上游 P0 分类学收敛 → G1–G3 术理考据 → 再冻结 Capability Registry 1.0 与 TagRenderModel 字段表。让 TagRenderModel 直接实现为上游 `computed-mark-semantics` 的运行时对象，不另造平行体系。

### R6｜UX 补充（P2）

1. 样式切换的习得成本未提示：切换样式包＝用户自己的视觉习惯重置，编辑器应在切换时提示（尤其从官方切走时）；
2. 作用域允许 per-technique 覆盖：同一用户八字一套皮肤、奇门另一套，进一步碎片化个人语法——建议默认跟随全局、technique 覆盖作为高级选项渐进披露；
3. 预览矩阵应加"学习场景对照"：若 R1 的场景豁免被采纳，用户须在启用前看到"练习/分享场景仍为官方样式"的预览，避免认知落差。

## 3. 工程复审已落实事项

以下问题已在当前主规格中给出解决方案，不再列为开放缺陷：

| 已解决问题 | 主规格中的解决方案 | 当前判断 |
|---|---|---|
| 模板与 Renderer 枚举漂移 | 单一版本化 `CapabilityRegistry`，未知 ID 报 `CAP_UNKNOWN` | 已落实 |
| RelationMark 不适合矩形容器 | `BoxHostGeometry`、`PathHostGeometry`、`AnchorHostGeometry` | 已落实 |
| safe area、cover、nine-slice 顺序不明 | `asset_space`、`normalized_space`、`container_space` 与固定变换管线 | 已落实 |
| 编辑即影响 ACTIVE、半编译风险 | Draft → Validated → Previewable → Active → Rolled Back，原子启用与 last-known-good | 已落实 |
| YAML 与可视化编辑双 source of truth | 规范化 AST 为唯一真源，YAML 是序列化表示 | 已落实 |
| Style 作用域与覆盖冲突 | account/device/technique/scene/species/density/accessibility 固定优先级 | 已落实 |
| Marketplace 权威字段由用户自报 | Manifest 仅保留 `publisher_claim`；Listing 与签名 Attestation 外置 | 已落实 |
| 逐槽 fallback 造成混搭 | `slot_fallback` 与 `variant_atomic_fallback` | 已落实 |
| 用户字体权利和跨平台风险 | 首期只允许 Host/官方字体稳定 ID | 已落实 |
| Counter 仅支持正整数 | 补齐 zero、negative、decimal、unknown、overflow、locale digits | 已落实 |
| ZIP/SVG/PNG/YAML 供应链检查不足 | 允许列表、MIME 检测、路径/链接/碰撞/alias bomb 与元数据净化 | 已落实 |
| “稳定渲染”不可验证 | 区分 deterministic compilation 与分平台 rendering conformance | 已落实 |
| 编辑器恢复与无障碍不足 | autosave、undo/redo、三态比较、StyleHealthReport、safe area 非拖动操作 | 已落实，但受 D-018 冻结 |
| 单体 OpenSpec 过大 | 拆成 package、compilation、rendering、asset safety、editor、host integration 六项 | 已落实，暂不创建 change |

这些工程修正提升了“未来如何安全实现”的完整度，但不推翻 R1–R5 对“允许什么、何时实施、先冻结哪个上游对象”的产品裁决。

## 4. 确认与肯定

- DisplayContract 机制：语义值保护的正确工程化，且"未读数可用状态图案"的模糊表达设计与 Counter 禁精确吉凶对比的既有方向暗合——官方样式亦可反向采用；
- Marketplace 权威状态外置（Listing/Attestation 与用户 manifest 分离）：正确且有远见；
- 原子回退（variant_atomic_fallback）防混搭失真：直接服务视觉语法一致性；
- 安全体系（SVG 允许列表、ZIP 防护、内容哈希）：无需修改；
- 命名空间隔离（TagStyle* 前缀避让全局 Theme）：多 Agent 协作下的正确防御。

## 5. 决策清单与落实门槛

| 建议 Decision | 内容 | 本报告立场 | 状态 |
|---|---|---|---|
| D-015 | 语义通道定制权：分层锁定＋毕业解锁 | 分层锁定（R1） | **用户批准 2026-07-11**，已登记 v1.2 |
| D-016 | 场景豁免清单（学习／测试／分享强制官方样式） | 采纳（R1） | **用户批准 2026-07-11**，已登记 v1.2 |
| D-017 | required_slots 硬约束进 Registry | 采纳（R2） | **用户批准 2026-07-11**，已登记 v1.2 |
| D-018 | 编辑器排期：Phase B 押后，预设包先行 | 押后（R3） | **用户批准 2026-07-11**，已登记 v1.2（FROZEN_PENDING_EVIDENCE） |
| D-019 | 官方稀缺纹理列为保留能力＋内容治理占位 | 立即采纳（R4） | **用户批准 2026-07-11**，已登记 v1.2 |
| D-020 | TagRenderModel 与 MarkInstance 合一，冻结顺序后置 | 采纳（R5） | **用户批准 2026-07-11**，已登记 v1.2 |

### 5.1 从“批准”到“完成”的门槛

D-015–D-020 不能只停留在文档顶部状态说明。至少完成以下回写后，才可把 Tag Style 规格标记为 OpenSpec-ready：

1. §3/§12：写入装饰通道与语义通道的权限模型、毕业解锁和一次性认知提示；
2. §4/§6：写入上游 knowledge contract → DisplayContract → Template 的单向约束与 `required_slots`；
3. §14/§19：把完整 Editor 标为冻结候选，当前 Phase B 改为 3–5 套官方预设包实验；
4. §13/§15：加入内容治理自述占位，平台权威治理仍留在 Listing/Attestation；
5. §6/§7：声明官方稀缺纹理 reserved capability；
6. §4/§19：声明 TagRenderModel 直接实现上游 MarkInstance，Capability Registry 1.0 冻结后置；
7. §17/§18：补定制 cohort 隔离、官方样式豁免场景和对应验收证据。

## 6. 一句话结论

这份规格已经较完整地回答“未来如何安全地做”，D-015–D-020 也已经回答“自由边界和实施时机”；当前剩余工作是把这些裁决逐条回写主规格正文。在回写完成、上游分类学和 G1–G3 收敛、预设样式实验门槛明确之前，不创建六项 OpenSpec change，也不启动 TagStyleEditor 实施。
