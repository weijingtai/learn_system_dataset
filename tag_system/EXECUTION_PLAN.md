# Tag/Marks 执行计划

> 拆分自 docs/superpowers/plans/2026-07-11-coding-execution-plan.md（Track 1/2 与 Phase A 部分），2026-07-11。
> 门槛状态：GATE-1 试运行批准通过；GATE-2（分类学＋G1–G3）已通过（D-022）；GATE-3（阈值预注册）Phase A 内完成。

## Phase A：验证与契约定稿（先于 UI 代码）

| ID | 任务 | 验收 | 依赖 |
|---|---|---|---|
| A-1 | Figma 点击原型：无字识别＋卡片分类＋元素详情卡可用性测试 | 阈值基线产出（GATE-3 输入）；详情卡无重大障碍 | 无 |
| A-2 | 灰度梯度强光／OLED 实测；五行色真机出样锁定 | 尺寸降级映射分档定稿 | 无 |
| A-3 | RelationMark 生克符号考据定稿（占卜师＋设计） | 符号表进 MarkVisualGrammar | 无 |
| A-4 | 六层对象 Schema（含 G1–G3 扩展点、corner_semantics 字段） | 样例数据往返校验通过 | 已解锁 |
| A-5 | 接收最小盘面概念字典（knowledge_system 供给） | 约 100–200 个 Concept ID 可绑定 | 跨区接口 1 |

## Track 1：契约与引擎（A-4 后）

T1-2 UI Registry 装载器（required_slots／未知物种 fallback）→ T1-3 TagStyleEngine 编译器 MVP（无编辑器，D-018）→ T1-4 官方预设样式包 ×3 → T1-5 DisplayContract＋Host Geometry Flutter 接口（落 metaphysics-chart-ui）→ T1-6 JurisdictionPolicy 降级 profile。验收标准见原计划，不变。

## Track 2：UI 体验（Phase A 判据后）

T2-1 元素详情卡 → T2-2 Insignia 能量条 → T2-3 月令条 → T2-4 文盘联动（确定性内容源）→ T2-5 L 分级＋密度服务 → T2-6/7/8 AI 解盘＋对话＋概念高亮验证门（D-021，依赖知识侧 EvidenceBundle 服务）。

## 冻结（本区）

TagStyleEditor 全功能（D-018）；Marketplace 交易；三维稀缺视觉（P0-5）；无约束裸 LLM 解盘（D-021 只允许 EvidenceBundle 约束链路内的 AI）。
