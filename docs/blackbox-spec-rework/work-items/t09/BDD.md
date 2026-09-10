# T-09 BDD 验收场景

## B1 Local Orchestrator 六项只读查询契约完备性

Given 权威源 `docs/blackbox-spec-rework/T-transcribe.md` 规定了 Local Orchestrator 的六项只读查询契约，
When 执行者查看架构规格 §5，
Then 规格在 `Local Orchestrator` 基础设施条目下逐项明确定义：
- `RunStatus`：查询 ProcessingRun 宏观生命周期状态与耗时；
- `StageProgress`：查询 M1–M8 各阶段的执行进度、任务计数与 Stage Gate 状态；
- `PendingQueue`：查询当前待人工介入的任务队列；
- `BlockingReasons`：查询阻断当前阶段 Gate 的具体原因与失败校验；
- `ReworkImpact`：评估特定 Artifact 或阶段返工对下游阶段、Revision 及队列的级联影响；
- `ThroughputEstimate`：测算阶段吞吐量与预计剩余耗时。

## B2 PendingQueue 五个指定队列显式列出

Given 知识加工生命周期存在多处人工介入节点，
When 执行者查看 `PendingQueue` 查询说明，
Then 规格必须显式列出五个专用待处理队列：
1. M2 异常页与低置信字
2. M3 边界分歧
3. M4 类别分歧
4. M6 待签发
5. M7 待裁决
不得使用「等等」或「未来扩展」等模糊用语。

## B3 Module 进度事件上报强制约束

Given 查询契约依赖 Module 运行期间的实时状态反馈，
When 执行者查看架构规格 §7，
Then 规格末尾明确补充约束：Module 必须在运行中向 Orchestrator 上报进度事件（Progress Events），否则上述查询无数据来源。
