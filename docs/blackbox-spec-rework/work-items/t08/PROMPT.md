# T-08 Executor Prompt

你是 T-08 文档执行 Agent。请在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支工作，禁止切换分支或进入其他 worktree。

先完整阅读并严格遵循：

- `docs/blackbox-spec-rework/work-items/t08/README.md`
- `docs/blackbox-spec-rework/work-items/t08/BDD.md`
- `docs/blackbox-spec-rework/work-items/t08/TDD.md`
- `docs/blackbox-spec-rework/work-items/t08/ACT.yaml`

【关键执行铁律与特别指示】：
1. 遇到任何照抄源冲突、规格歧义或意外失败，严禁自己做决定，必须立即停止并向上汇报！
2. 唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`；严禁修改任何代码、JSON Schema、测试、工作包文档、TODO、PLAN 或 `verify-T.sh`。
3. 先保存 Red baseline（运行 `bash docs/blackbox-spec-rework/verify-T.sh` 并确认 7 FAIL，T-08 与 T-08b 为 FAIL）。
4. 在 `openspec/learn-system-blackbox-architecture.md` 写入以下两处修改：
   - **位置 1（`§1 系统边界`）**：
     在系统边界说明中追加对外部 Tag 系统的三个承接接口声明：
     - 黑箱编译器通过 `PublicationPackage` 向外部 Tag 系统承接三个核心接口：
       1. `最小盘面概念字典`：规模约 100–200 个概念，由 `KnowledgeDataPack` 供给，仅包含稳定 `concept_id` + 名称 + 基础类象，**严格声明不含规则 DSL**，用以解除 G4 依赖倒挂；
       2. `MarkContentBinding` 内容供给：由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给，为 UI 标记提供内容与分歧数据；
       3. `EvidenceBundle` 服务：由 `EvidenceMapPack` 供给，为解盘与证据高亮提供底层的无损证据链切片。
   - **位置 2（`§16 M8 Dataset Compilation` 末尾）**：
     在小节 16.2 之后（在 `## 17. Artifact Ledger` 之前），新增小节「16.3 Tag 标记系统耦合接口与字段承接」：
     - 明确三个接口的供给子包及承接说明：
       - `最小盘面概念字典`：由 `KnowledgeDataPack` 供给。规模控制在约 100–200 个概念，仅包含稳定 ID（`concept_id`）、名称与基础类象，**严格声明不含规则 DSL**；
       - `MarkContentBinding`：由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给；
       - `EvidenceBundle`：由 `EvidenceMapPack` 供给。
     - 明确五个关键字段归属与约束：
       - `omen_carrying`（吉凶承载性）：指示该标记是否承载吉凶定性，由 M4/M5 生产，归入 `KnowledgeDataPack`；
       - `condition_affordance`（条件可供性）：指示该标记可承载的条件槽位，由 M4/M5 结构化生产，归入 `RuleIndexPack` 与 `KnowledgeDataPack`；
       - `school_variance_display`（流派分歧展示）：指示各流派对此标记的不同定性或观点分歧，由 M4/M6 审核产出，归入 `KnowledgeDataPack`；
       - `concept_id`（概念标识）：全局稳定的概念 ID，由 M4 术语判层确定，归入 `KnowledgeDataPack`；
       - 「是否改变当前判断」：明确规定属于 `MarkContentBinding` 的核心内容状态字段，必须由知识层（M4/M7/M6）通过判定状态供给，**UI 不得猜测**。
5. 完成后运行 `docs/blackbox-spec-rework/work-items/t08/TDD.md` 中的全部 Green checks、`bash docs/blackbox-spec-rework/verify-T.sh`（FAIL 数必须从 7 严格减少至 5，且 T-08 与 T-08b 为 PASS）以及 `git diff --check`。
6. 确认无误后提交修改，提交消息必须严格为：`docs: specify Tag system coupling interfaces and fields`。
7. 最终报告必须包含：commit hash、真实修改文件、Red baseline、Green 原始摘要、三接口与五字段核验对照及全局 T 结果。
