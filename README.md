# learn_system 仓库地图

> **项目最终目标与现状总入口：[`LEARN_SYSTEM_TARGET.md`](LEARN_SYSTEM_TARGET.md)**。新接手者先阅读该文件，理解从古籍扫描、OCR、知识编译、KnowledgePack、排盘匹配、扫描追溯到注解社区的完整目标，再进入各子目录。

> **旧存储与旧路径：[`openspec/legacy-storage-transition.md`](openspec/legacy-storage-transition.md)**。修改 OCR、Pipeline、工作台的存储、导入、导出或索引代码前先读；旧路径仍在源码中不代表迁移已完成。

> **免费开源框架候选：[`docs/research/2026-09-08-open-source-framework-options.md`](docs/research/2026-09-08-open-source-framework-options.md)**。这是单人单机条件下的选型调研，不是已生效的架构规范；采用范围须经确认后再进入 OpenSpec。

> **OCR 参数化：[`openspec/ocr-profile-parameterization.md`](openspec/ocr-profile-parameterization.md)**。现有中国传统竖排古籍 OCR 与校订 UI 保持不变；每个 Edition 通过版本化 `OCRProfile` 校准、冻结并留痕。

> **Subagent 工作监控：[`docs/blackbox-spec-rework/SUBAGENT_TODO.md`](docs/blackbox-spec-rework/SUBAGENT_TODO.md)**。所有大项及其 BDD、TDD、ACT、Prompt、执行、验收小项在此勾选；准出规则见 [`openspec/subagent-delivery-gate.md`](openspec/subagent-delivery-gate.md)。

## 黑箱核心 ID 快速说明

以下六类前缀已于 2026-09-09 确认。它们用于追踪“哪个对象、哪次修订、哪次运行、哪个阶段包、哪次发布”，不是用户身份或鉴权 ID。完整约束以 [`openspec/learn-system-blackbox-architecture.md`](openspec/learn-system-blackbox-architecture.md) §8.1 为准。

| 前缀 | 代表什么 | 稳定与新建规则 |
|---|---|---|
| `art_<32hex>` | **Artifact**：一份制品的逻辑身份，例如同一份 OCR 结果、校订结果或知识结果的“对象本身” | 内容修订时保留同一个 `artifact_id`；对象语义改变或成为全新制品时才新建 |
| `rev_<32hex>` | **Artifact Revision**：某份制品一次不可变的实际内容快照 | 每次封存、修正或重新生成内容都必须新建 `artifact_revision_id`；旧 Revision 永久保留 |
| `prun_<32hex>` | **ProcessingRun**：一次完整处理运行的身份，用来汇总该次运行下的阶段和 StepRun | 每次重新发起处理都新建；使用 `prun_` 而不是 `pr_`，避免与 Proposition ID 冲突 |
| `srun_<32hex>` | **StepRun**：一个 EditionPart 在某个阶段中的一次具体任务运行 | 每次任务重跑都新建 `step_run_id`；旧运行不覆盖，通过取代关系追踪 |
| `pkg_<stage>_<32hex>` | **StagePackage**：某阶段输出包的逻辑身份；`<stage>` 只允许 `m1`–`m8` | 同一阶段包修订时保留 `stage_package_id`，每个实际版本另配一个新的 `rev_...` |
| `rel_<32hex>` | **Release**：一次正式发布的数据集身份，用于让客户端、索引和追溯信息指向同一发布 | 每次新发布都新建 `release_id`；已发布记录不得原地改写 |

`<32hex>` 是由 UUIDv4 生成的 32 位小写十六进制字符串。最重要的区别是：`art_` 与 `pkg_` 表示可跨修订保持的逻辑对象，`rev_` 表示绝不修改、绝不复用的具体内容版本。例如一个阶段包应同时携带 `pkg_m3_<32hex>` 和 `rev_<32hex>`。

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
