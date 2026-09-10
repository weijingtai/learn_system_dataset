# T-09 Local Orchestrator 只读查询契约（六项）转录：执行工作包

状态：`READY`（已按标准六件套建立，等待串行派发执行 Agent）

## Goal

依据 `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-09 规范，在黑箱架构规格中完整定义 Local Orchestrator 提供的六项只读查询契约：
1. **六项只读查询契约展开（§5）**：
   - `RunStatus`：返回指定 ProcessingRun 的当前宏观状态（running / awaiting_human / succeeded / failed 等）及总体起止时间；
   - `StageProgress`：返回各 Stage（M1–M8）的具体执行进度、已完成任务计数、进行中任务及当前 Stage Gate 达成状态；
   - `PendingQueue`：返回当前阻断或等待人工干预的待处理队列明细，必须显式列出五个专用队列：
     1. M2 异常页与低置信字
     2. M3 边界分歧
     3. M4 类别分歧
     4. M6 待签发
     5. M7 待裁决
   - `BlockingReasons`：返回当前阻断 Stage Gate 通过的具体原因、失败校验项或未满足的依赖项明细；
   - `ReworkImpact`：返回若对某历史 Artifact 或阶段发起返工时，将级联波及的下游阶段、衍生 Revision 与受影响队列范围；
   - `ThroughputEstimate`：返回基于当前单机/硬件算力及历史加工耗时测算出的阶段吞吐与预计剩余处理耗时。
2. **进度事件上报约束（§7 末尾）**：
   - 补充约束：各 Processing Module 必须在运行中向 Orchestrator 实时上报进度事件（Progress Events），否则上述查询无数据来源。

## Authority

- `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-09
- `openspec/learn-system-blackbox-architecture.md` §5 与 §7
- `docs/blackbox-spec-rework/verify-T.sh`（T-09 判据）

## Dependencies

- T-08：已 `ACCEPTED`；
- 本任务与后续 T 类修改同一架构规格，必须严格串行派发。

## Scope

- WRITE：仅 `openspec/learn-system-blackbox-architecture.md`
- 规格落点：
  1. `§5 总体组织`：在 `Local Orchestrator` 基础设施条目下展开六项只读查询契约与五个 PendingQueue 队列；
  2. `§7 统一 Module Interface` 末尾：补充 Module 运行期必须上报进度事件的强制要求。

## Forbidden

- 严禁少于六项查询契约。
- 严禁漏掉五个指定 PendingQueue 队列的任何一个。
- 严禁将契约描述为模糊的「未来可扩展」，必须完整列出闭集。
- 严禁修改任何代码、JSON Schema、测试、数据库文件、PLAN、TODO 或 `verify-T.sh`。

## Stop conditions

遇到以下情况必须立即停止并向上汇报：
1. 照抄源与现有状态机定义冲突；
2. Green checks 未通过或全局回归出现未预期退化；
3. 发现需要修改单文件作用域之外的任何文件。

## ACT review（wjt-react 四查）

- **忠实性**：通过；完全原样转录 T-transcribe.md 中规定的六项查询契约与五个待处理队列。
- **可执行性**：通过；清晰落于 §5 与 §7，命令与 grep 判据完全确定。
- **可验收性**：通过；直接对接 `verify-T.sh` 中的 T-09 判据，验收后全局 FAIL 数由 5 降至 4。
- **防越界性**：通过；单文件写作用域，禁止代码与依赖改动。

结论：工作包六件套完备，符合 G0 交付门禁，状态置为 `READY`。
