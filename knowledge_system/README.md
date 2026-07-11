# 知识编译系统（书籍知识库）— 文档区入口

> 状态：**已开工**。奇门试点管线在 `../pipeline/` 运行中（工位 1–5 已跑通四个任务包，双路比对工具已上线）。
> 最后整理：2026-07-11

## 范围规则

**属于本区**：术数文献知识编译工作流（母稿全系）、产品决策登记、市场验证、产品机制策略、本区执行计划。
**不属于本区**：Marks/Tag 视觉与样式体系（→ `tag_system/`）。
**工作区**：实际编译工作在 `../pipeline/`（任务包、units、校验器、corpus），接手 AI 必读 `../pipeline/AGENT_GUIDE.md`。原书扫描在 `../raw_books/`。

## 文件索引

| 文件 | 内容 | 状态 |
|---|---|---|
| `METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md` | **当前权威母稿**＋决策登记表 D-001–D-022（§0.2，全仓库共享权威） | D-001–014 试运行批准；D-021 AI 解盘开放 |
| `METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.1.1.md` / `_v1.1.md` / `.md` | 历史版本（v1.1 含三阶段路线与双版本合规策略） | 归档，被 v1.2 取代 |
| `DESIGN_REVIEW_v1.1.md` / `_v1.2.md` | 跨角色产品评审 | 已吸收进 v1.2 |
| `VALIDATION_REPORT_MARKET.md` | 市场向验证报告（行业、监管、竞品） | 结论有效 |
| `From_Buyer_To_Owner.md` | 产品机制头脑风暴：转化漏斗、象法记忆、轮播、人生日历、断过去、H6–H27 假设 | 讨论沉淀，机制落地时逐条立项 |
| `EXECUTION_PLAN.md` | 本区执行计划（Track 0 与试点推进） | 进行中 |

## 当前第一件事

1. 把 support_type（direct vs interpreted）判据回写进 assertions 任务模板——compare_drafts.py 实测发现两模型系统性分歧（8 对中 7 对不一致）；
2. 用 task_000004 的四条仲裁裁决做首批金标种子（gold/assertions/）；
3. 向 tag_system 供给最小盘面概念字典（Concept ID 种子集）——对方开工的前置。
