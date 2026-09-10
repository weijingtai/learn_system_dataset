# T-12 §19 增「层级」列并按拓扑标注：执行工作包

状态：`READY`（已按标准六件套建立，等待串行派发执行 Agent）

## Goal

依据 `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-12 规范，在黑箱架构规格 `§19` 差距表格中增加「层级」列，并补充施工顺序说明：
1. **依赖拓扑图展示**：
   在 §19 表格前明确展示工程拓扑依赖结构：
   ```text
   L0 内核契约(ArtifactRef + §7 接口 + §8 信封)
     └─ L1 Artifact Ledger(Object Store + Metadata + §17 StepRun 事务) ─ L1' LineageGraph
          ├─ L2  Local Orchestrator(状态机/Gate/Checkpoint/失效传播)
          ├─ L2' Contract Registry 完整体(Package Schema/TechniqueProfile/迁移器)
          └─ M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8
   ```
2. **增加「层级」列**：
   在表格中为每一行增加「层级」列（标注 `L1`、`L2`、`L2'`、`Module` 或横向支撑），严禁重排既有表行顺序（避免打乱引用）；
3. **施工顺序说明**：
   在表下显式写入说明文字：「本表行序为盘点顺序，非施工顺序；施工顺序见上方拓扑，三个基础设施是前置层。」

## Authority

- `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-12
- `openspec/learn-system-blackbox-architecture.md` §19
- `docs/blackbox-spec-rework/verify-T.sh`（T-12 判据）

## Dependencies

- T-11：已 `ACCEPTED`；
- 本任务与后续 T 类修改同一架构规格，必须严格串行派发。

## Scope

- WRITE：仅 `openspec/learn-system-blackbox-architecture.md`
- 规格落点：`§19 当前实现映射与差距`。

## Forbidden

- 严禁重排现有表格行顺序。
- 严禁遗漏「本表行序为盘点顺序，非施工顺序；施工顺序见上方拓扑，三个基础设施是前置层。」这句关键说明。
- 严禁修改任何代码、JSON Schema、测试、数据库文件、PLAN、TODO 或 `verify-T.sh`。

## Stop conditions

遇到以下情况必须立即停止并向上汇报：
1. 照抄源与现有 §19 结构冲突；
2. Green checks 未通过或全局回归出现未预期退化；
3. 发现需要修改单文件作用域之外的任何文件。

## ACT review（wjt-react 四查）

- **忠实性**：通过；原样搬运拓扑分层（L0/L1/L2/Module）及施工顺序说明。
- **可执行性**：通过；仅在 §19 表格加列与说明，修改点集中。
- **可验收性**：通过；对接 `verify-T.sh` 中的 T-12 判据，验收后全局 FAIL 数由 2 降至 1。
- **防越界性**：通过；单文件写作用域，禁止代码与依赖改动。

结论：工作包六件套完备，符合 G0 交付门禁，状态置为 `READY`。
