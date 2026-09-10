# T-08 BDD 验收场景

## B1 Tag 三个耦合接口完整承接

Given 权威源 `tag_system/README.md:30-32` 确立了 Tag 系统依赖知识系统的三个唯一接口，
When 执行者查看架构规格 §1 与 §16，
Then 规格完整承接：
1. `最小盘面概念字典`：规模约 100–200 个概念，由 `KnowledgeDataPack` 供给，仅包含稳定 ID、名称与基础类象，**严格声明不含规则 DSL**，用以解除 G4 依赖倒挂；
2. `MarkContentBinding` 内容供给：由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给，为 UI 标记提供内容与分歧数据；
3. `EvidenceBundle` 服务：由 `EvidenceMapPack` 供给，为解盘与证据高亮提供完整的无损证据链切片。

## B2 五个关键字段与内容状态约束

Given 权威源 `tag_system/TAG_SYSTEM_DESIGN.md` 规定了语义物种的元数据字段，
When 执行者查看架构规格 §16，
Then 规格逐项明确各个关键字段的生产 Module 与归属子包：
- `omen_carrying`（吉凶承载性）：由 M4/M5 生产，落于 `KnowledgeDataPack`；
- `condition_affordance`（条件可供性）：由 M4/M5 结构化生产，落于 `RuleIndexPack` 与 `KnowledgeDataPack`；
- `school_variance_display`（流派分歧展示）：由 M4/M6 审核产出，落于 `KnowledgeDataPack`；
- `concept_id`（概念标识）：由 M4 术语判层产出，落于 `KnowledgeDataPack`；
- 「是否改变当前判断」：明确规定属于 MarkContentBinding 的内容状态字段，由知识层（M4/M7/M6）通过 ReviewDecision 供给，UI 不得猜测。

## B3 边界清晰声明

Given Tag 系统为外部独立消费端，
When 执行者查看架构规格 §1 系统边界，
Then 规格清晰声明黑箱编译器与 Tag 系统的交互边界，明确黑箱通过 PublicationPackage 承接上述三个外部接口。
