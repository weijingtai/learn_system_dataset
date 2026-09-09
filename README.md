# learn_system 仓库地图

> **项目最终目标与现状总入口：[`LEARN_SYSTEM_TARGET.md`](LEARN_SYSTEM_TARGET.md)**。新接手者先阅读该文件，理解从古籍扫描、OCR、知识编译、KnowledgePack、排盘匹配、扫描追溯到注解社区的完整目标，再进入各子目录。

> **旧存储与旧路径：[`openspec/legacy-storage-transition.md`](openspec/legacy-storage-transition.md)**。修改 OCR、Pipeline、工作台的存储、导入、导出或索引代码前先读；旧路径仍在源码中不代表迁移已完成。

> 2026-07-11 重组：文档按两条并行工作线拆分，**两区文档不得互混**。新文件落位规则：先问"这是关于 Marks/Tag 的，还是关于书籍知识编译/产品的？"

```text
tag_system/          Marks/Tag 系统（设计已收敛，准备开工）→ 入口 tag_system/README.md
knowledge_system/    书籍知识编译＋产品母稿＋市场验证（已开工）→ 入口 knowledge_system/README.md
pipeline/            知识编译实际工作区（任务包、units、校验器）→ AI 必读 pipeline/AGENT_GUIDE.md
pattern_knowledge_workbench/  多术数格局知识审核与发布工作台（七政四余为首个迁移 profile）
raw_books/           原书扫描（只读证据）
docs/superpowers/    历史 specs/plans 位置——Tag 相关已迁至 tag_system/specs/，旧混合计划仅存指针
AGENTS.md / PLAN.md / HANDOFF.md / SOLO_WORKPLAN.md   跨区协调文件（保留根目录）
LEARN_SYSTEM_TARGET.md                               全系统最终目标、端到端运行方式、工具成熟度与缺口
```

共享权威：产品决策登记表（D-001–D-022）位于 `knowledge_system/METAPHYSICS_KNOWLEDGE_COMPILATION_WORKFLOW_v1.2.md` §0.2。

两区唯一允许的耦合是三个已声明接口（见 tag_system/README.md"依赖接口"）：最小盘面概念字典、MarkContentBinding 内容供给、EvidenceBundle 服务。除此之外的跨区引用视为文档放错了位置。
