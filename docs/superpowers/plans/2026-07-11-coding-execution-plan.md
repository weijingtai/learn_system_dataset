# Coding 执行计划：从设计语料到可执行任务

> 状态：待用户确认，2026-07-11。
> 回答的问题：现有分析文档能否转为 plans/tasks 开始编码？
> 结论：**分轨可以。** Track 0 今天就能开工（零决策依赖）；Track 1 在本轮修复（P0 落正文＋分类学决议）被确认后开工；Track 2 依赖 GATE-1（用户批准 D-001–D-014）。任何任务不得跨越其解锁门。

## 1. 解锁门（Gates）

| Gate | 内容 | 责任方 | 状态 |
|---|---|---|---|
| GATE-0 | 评审 P0-3/4/5 落回 TAG_SYSTEM_DESIGN 正文；P0-1/2 由分类学决议解决 | Claude | **本轮已完成**，待用户确认 |
| GATE-1 | v1.2 决策登记表 D-001–D-014 用户原则批准（见 §4 批准清单） | **用户** | 待办——这是唯一必须由你解锁的门 |
| GATE-2 | 分类学决议确认＋G1–G3 考据定稿 | 用户＋占卜师 | **已通过（D-022，卦师评定 2026-07-11）**：方案 A＋五条补充约束已落规格 |
| GATE-3 | 阈值预注册（D-014）：北极星、无字识别等全部"待校准"数字在 Phase A 转为预注册量化 Gate | 研究 | Phase A 内完成 |

## 2. 任务轨道

### Track 0｜立即可编码（零决策依赖，服务已在跑的 pipeline 试点）

| ID | 任务 | 验收 | 依赖 |
|---|---|---|---|
| T0-1 | ~~确定性校验器 CLI~~ | **已存在**（pipeline/validators/ 五脚本，units 校验 PASS）——计划制定时未察觉，管线先行了 | 无 |
| T0-2 | 任务包工厂脚手架：从模板生成 task.yaml／INSTRUCTIONS／input 快照与哈希 | 重新生成 000004 等价任务包，diff 仅时间戳 | 无 |
| T0-3 | ~~双路输出结构化 Diff 工具~~ | **已完成（2026-07-11）**：`validators/compare_drafts.py`，对 000004 双路草稿运行——正确复现手工仲裁结构（13/12 条、s07 拆合、s02 support_type 冲突），并新发现**系统性分歧**：8 对中 7 对 support_type 不一致（direct vs interpreted 判定标准两模型系统性不同）→ 应回写 INSTRUCTIONS 判据并进金标 | 无 |
| T0-4 | 金标回归 runner 骨架：gold/ 目录约定＋逐工位指标计算（evidence_precision 等） | 空金标可跑通，出 not_calibrated 报告 | T0-1 |
| T0-5 | MarkReleaseBundle 编译器骨架：读知识/UI 双 Registry 样例→合成只读 bundle＋内容哈希（确定性编译） | 相同输入两次编译哈希一致；手改 bundle 被校验拒绝 | 分类学决议（结构已定，可与 GATE-2 确认并行） |

### Track 1｜契约与引擎（GATE-2 确认后；纯类型/Schema/编译层，不做 UI）

| ID | 任务 | 验收 | 依赖 |
|---|---|---|---|
| T1-1 | 六层对象 Schema 定义（JSON Schema＋目标端类型；Concept/ComputedFact/RuleEvaluation/MarkInstance/…含 G1–G3 扩展点） | Schema 通过样例数据往返校验；temporal_phase、transformation、StateModifier 字段就位 | GATE-2 |
| T1-2 | UI Registry 装载器：MarkSpeciesDefinition＋MarkVisualGrammar＋required_slots 校验（D-017） | 省略 required_slot 的样式包被拒；未知物种走 fallback 不渲染＋上报 | T1-1 |
| T1-3 | TagStyleEngine 编译器 MVP（validate→sanitize→compile→bundle；无编辑器，D-018 合规） | Tag Style 规格 §17.4 安全用例（路径穿越、YAML alias bomb 等）全绿 | T1-2 |
| T1-4 | 官方预设样式包 ×3（默认／古风／暗色；同一包格式） | 三包过 T1-3 编译；语义通道全部官方值（D-015 锁定态） | T1-3 |
| T1-5 | DisplayContract＋三类 Host Geometry 的 Flutter 接口（落 metaphysics-chart-ui） | 五个既有奇门 Widget 按规格 §11 映射通过渲染 conformance 样例 | T1-1；chart-ui 仓库 |
| T1-6 | JurisdictionPolicy 降级 profile（大陆：OmenIndicator 中性化） | profile 切换测试：同一 bundle 双形态快照 | T1-2 |

### Track 2｜UI 体验（GATE-1 批准＋Phase A 验证判据后）

| ID | 任务 | 验收 | 依赖 |
|---|---|---|---|
| T2-1 | 元素详情卡（含 phase_comparison 区块、两级流派分歧、吉凶三件套、静态盘标注） | 可用性测试无重大障碍；required_slots 全渲染 | T1-2、Figma 定稿 |
| T2-2 | Insignia 能量条（灰度条＋五行角标＋F3 尺寸降级＋F2 首次提示） | 强光/OLED 实测通过降级映射；读屏 label 过五问审计 | T1-5 |
| T2-3 | 月令条（全员一致渲染＋节气切换） | 快照对所有测试用户一致；无用神高亮路径 | T2-2 |
| T2-4 | 文盘联动（确定性事实／证据卡↔盘面） | 联动协议过 registry 事件规范；高亮不带吉凶色彩 | T2-1 |
| T2-5 | L 层级 per-technique＋密度服务对接＋L1 神煞屏蔽 | 跨技法用户场景测试；降级无羞辱文案 | T2-1 |
| T2-6 | **AI 解盘服务（D-021）**：EvidenceBundle 构建（FactSet→KnowledgeHit→按流派分组证据→禁止结论清单）＋引用/混派/无据主张出口检查 | v1.1 §15 链路全通；无据主张率、引用错误率进监控（v1.1 §17） | T1-1、最小盘面概念字典 |
| T2-7 | **AI 多轮对话解盘（D-021）**：对话上下文携带盘面事实与已用证据；每轮重新过约束检查（防长对话漂移）；高风险场景拒绝（16A） | 多轮红队用例（诱导断事、诱导混派、健康财务追问）全部正确拒绝或降级 | T2-6 |
| T2-8 | **概念高亮＝验证门（D-021）**：AI 回答流式渲染时对术语做 Concept ID 绑定，绑定成功→内联 mark（可点、联动盘面），失败→普通文本＋静默上报（未编译概念候选回流管线） | 高亮精确率＝100%（宁可漏亮不可错亮）；漏亮项进 ONT_001 候选队列 | T2-6、T2-4 |

### 并行非编码线（与 Track 0/1 同期）

- Figma 点击原型：无字识别＋卡片分类＋详情卡可用性（阈值基线，GATE-3 输入）；
- 占卜师考据：G1 化气流派口径、G2 传统符号表、RelationMark 生克符号定稿；
- 阈值预注册文档（D-014 格式）。

## 3. 明确不做（当前全部冻结，防止任务蔓延）

TagStyleEditor 全功能（D-018）；Marketplace 任何交易能力；三维稀缺视觉（P0-5）；公开评论区（D-008）；规则引擎自动触发（v1.1 §11）；AI 解盘的**付费方案分析**（D-021 仅留占位）。~~AI 解盘禁令~~已由 D-021 取代——AI 解盘与对话进入 Track 2（T2-6/7/8），但必须整链绑定 EvidenceBundle 约束架构，无约束的裸 LLM 解盘仍然禁止。

## 4. GATE-1 批准清单（需要你逐项或整批表态）

D-001 证据型学习方向｜D-002 忠实度≠有效性｜D-003 禁欺骗与诱导依赖｜D-004 阶段一禁用户盘面 AI｜D-005 旧 APP 合法导入前提｜D-006 权利可验证｜D-007 阶段零验证范围｜D-008 评论冻结、只做私注｜D-009 批准后建 OpenSpec｜D-010 主张进 Evidence Ledger｜D-011 逐辖区批准｜D-012 UX 无障碍不后置｜D-013 事故 SLA 前置｜D-014 量化 Gate。

评审意见：十四条与既有全部设计语料一致、无相互冲突，**建议整批原则批准**；批准后由维护 v1.2 的 Agent 将 approval_status 更新并使 SHALL 生效（D-009 随即触发 OpenSpec 草案建立）。

## 5. OpenSpec 拆分对应（GATE-1 后执行）

`knowledge-concept-taxonomy` 与 `computed-mark-semantics` ← 分类学决议 §1–2；`mark-visual-grammar` ← TAG_SYSTEM_DESIGN §3＋Tag Style §4–10；`mark-exposure-and-learning` ← §5＋From_Buyer_To_Owner 曝光机制；`mark-safety-and-jurisdiction` ← 红线体系＋JurisdictionPolicy；Tag Style 六 capability ← 其规格 §21（Editor 两项标记 FROZEN）。
