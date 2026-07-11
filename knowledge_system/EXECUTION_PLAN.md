# 知识编译系统执行计划

> 拆分自 docs/superpowers/plans/2026-07-11-coding-execution-plan.md（Track 0 部分），2026-07-11。工作区：`../pipeline/`。

## Track 0：管线工具与试点推进

| ID | 任务 | 验收 | 状态 |
|---|---|---|---|
| T0-1 | 确定性校验器 | units 校验 PASS | **已存在**（validators/ 五脚本） |
| T0-3 | 双路草稿结构化比对 | 复现 000004 手工仲裁结构 | **已完成**（compare_drafts.py，2026-07-11） |
| T0-6 | support_type 判据回写任务模板 | direct/interpreted 给出可判定规则＋正反例；重跑一个双路任务分歧率显著下降 | **下一件事**（compare_drafts 实测：8 对中 7 对系统性分歧） |
| T0-4 | 金标种子与回归 runner | 以 000004 四条仲裁裁决为首批金标（gold/assertions/）；runner 可对任一草稿打分 | 待做 |
| T0-2 | 任务包工厂脚手架 | 再生成 000004 等价任务包，diff 仅时间戳 | 待做 |
| T0-5 | MarkReleaseBundle 编译器骨架 | 确定性编译哈希一致；手改 bundle 被拒 | 待做 |
| T0-7 | **最小盘面概念字典**（十天干、十二地支、九星、八门、八神等，仅稳定 ID＋名称＋基础类象，不含规则 DSL） | tag_system 可绑定 Concept ID（跨区接口 1） | 待做，tag_system 开工前置 |

## 试点推进（与工具并行）

继续 yanbo 文本后续段落的工位 3–5 任务包；escalations 队列处理（现有 ESC_task_qimen_000002_seg_01）；lessons 持续沉淀。

## 冻结（本区）

公开评论区（D-008）；规则引擎自动触发；AI 解盘付费方案分析（D-021 占位）。
