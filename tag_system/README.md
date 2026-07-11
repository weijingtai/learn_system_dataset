# Tag/Marks 系统 — 文档区入口

> 状态：设计已收敛，**准备开工**（Phase A）。与 knowledge_system 并行推进，两区文档不得互混。
> 最后整理：2026-07-11

## 范围规则

**属于本区**：Marks/Tag 的哲学与红线、视觉语法、物种体系、样式定制、渲染契约、相关评审与执行计划。
**不属于本区**：书籍知识编译管线、产品母稿与市场验证（→ `knowledge_system/`）、管线工作区（→ `pipeline/`）。
**共享权威**：产品决策登记表（D-001–D-022）在 `knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md` §0.2——两区共用，Tag 相关为 D-015–D-020、D-022。

## 文件索引（阅读顺序）

| 文件 | 内容 | 状态 |
|---|---|---|
| `TAG_SYSTEM_DESIGN.md` | 主规范 v1.0-draft-r1：哲学红线、需求、交互模型、视觉语法、物种、治理、验收 | 已收敛，P0 已落正文 |
| `specs/mark-taxonomy-and-registry-split.md` | 六层对象模型、Registry 七对象拆分、G1–G3 定稿（D-022） | 已定稿 |
| `specs/tag-style-system-design.md` | 个人样式定制与 Marketplace 接口（受 D-015–D-020 约束） | 已修订，Editor 冻结 |
| `TAG_SYSTEM_DESIGN_review_report.md` | 主规范评审（P0/P1 清单） | P0 已处置 |
| `TAG_STYLE_SPEC_review_report.md` | 样式规格交叉评审（R1–R6 → D-015–D-020） | 决议已登记 |
| `EXECUTION_PLAN.md` | 本区执行计划：Phase A → 契约 → UI | 待开工 |

## 当前第一件事

Phase A-1：Figma 点击原型（无字识别＋卡片分类＋元素详情卡可用性）——不写代码即可开始；工程侧第一件事是六层对象 Schema（依赖已满足：分类学已定稿、G1–G3 已闭合）。

## 依赖 knowledge_system 的接口（唯一允许的跨区耦合）

1. 最小盘面概念字典（Concept ID 种子集，约 100–200 个）——G4 依赖倒挂的解法，需管线侧提前供给；
2. MarkContentBinding 的内容字段（吉凶三件套、流派分歧标记）由知识发布包供给；
3. AI 解盘（D-021）的 EvidenceBundle 由知识侧服务供给。
