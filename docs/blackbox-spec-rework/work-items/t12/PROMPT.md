# T-12 Executor Prompt

你是 T-12 文档执行 Agent。请在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支工作，禁止切换分支或进入其他 worktree。

先完整阅读并严格遵循：

- `docs/blackbox-spec-rework/work-items/t12/README.md`
- `docs/blackbox-spec-rework/work-items/t12/BDD.md`
- `docs/blackbox-spec-rework/work-items/t12/TDD.md`
- `docs/blackbox-spec-rework/work-items/t12/ACT.yaml`

【关键执行铁律与特别指示】：
1. 遇到任何照抄源冲突、规格歧义或意外失败，严禁自己做决定，必须立即停止并向上汇报！
2. 唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`；严禁修改任何代码、JSON Schema、测试、工作包文档、TODO、PLAN 或 `verify-T.sh`。
3. 先保存 Red baseline（运行 `bash docs/blackbox-spec-rework/verify-T.sh` 并确认 2 FAIL，T-12 为 FAIL）。
4. 在 `openspec/learn-system-blackbox-architecture.md` 的 `## 19. 当前实现映射与差距` 做以下两处修改：
   - **位置 1（表格前增加依赖拓扑图）**：
     在 `## 19. 当前实现映射与差距` 标题后，插入拓扑说明与 ASCII 图：
     ```text
     架构依赖拓扑与施工前置关系如下：

     ```text
     L0 内核契约(ArtifactRef + §7 接口 + §8 信封)
       └─ L1 Artifact Ledger(Object Store + Metadata + §17 StepRun 事务) ─ L1' LineageGraph
            ├─ L2  Local Orchestrator(状态机/Gate/Checkpoint/失效传播)
            ├─ L2' Contract Registry 完整体(Package Schema/TechniqueProfile/迁移器)
            └─ M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8
     ```
     ```
   - **位置 2（表格增加「层级」列并保持原有行序）**：
     - 表头扩展为：`| 目标 Module | 层级 | 当前实现 | 当前差距 |`
     - 逐行增加层级标注（例如 M1–M8 为 `Module`，Artifact Ledger 为 `L1`，Local Orchestrator 为 `L2`，Contract Registry 为 `L2'`，工作台相关为 `Workbench` 或 `UI`，其他项标 `Cross-cutting` 或 `Quality` 等）；
     - **严禁重排现有行顺序**（避免打乱既有引用）；
   - **位置 3（表格下方写入施工顺序说明）**：
     在表格下方显式写入一段声明文字：
     `注：本表行序为盘点顺序，非施工顺序；施工顺序见上方拓扑，三个基础设施是前置层。`
5. 完成后运行 `docs/blackbox-spec-rework/work-items/t12/TDD.md` 中的全部 Green checks、`bash docs/blackbox-spec-rework/verify-T.sh`（FAIL 数必须从 2 严格减少至 1，且 T-12 为 PASS）以及 `git diff --check`。
6. 确认无误后提交修改，提交消息必须严格为：`docs: add hierarchy column and construction order to gap table`。
7. 最终报告必须包含：commit hash、真实修改文件、Red baseline、Green 原始摘要、拓扑与层级核验对照及全局 T 结果。
