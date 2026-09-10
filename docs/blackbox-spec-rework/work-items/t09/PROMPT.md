# T-09 Executor Prompt

你是 T-09 文档执行 Agent。请在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支工作，禁止切换分支或进入其他 worktree。

先完整阅读并严格遵循：

- `docs/blackbox-spec-rework/work-items/t09/README.md`
- `docs/blackbox-spec-rework/work-items/t09/BDD.md`
- `docs/blackbox-spec-rework/work-items/t09/TDD.md`
- `docs/blackbox-spec-rework/work-items/t09/ACT.yaml`

【关键执行铁律与特别指示】：
1. 遇到任何照抄源冲突、规格歧义或意外失败，严禁自己做决定，必须立即停止并向上汇报！
2. 唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`；严禁修改任何代码、JSON Schema、测试、工作包文档、TODO、PLAN 或 `verify-T.sh`。
3. 先保存 Red baseline（运行 `bash docs/blackbox-spec-rework/verify-T.sh` 并确认 5 FAIL，T-09 为 FAIL）。
4. 在 `openspec/learn-system-blackbox-architecture.md` 写入以下两处修改：
   - **位置 1（`§5 总体组织`）**：
     在基础设施 `Local Orchestrator` 条目下展开其对外提供的六项只读查询契约（各一行说明其返回什么，严禁少于六项，严禁写成未来可扩展）：
     - `RunStatus`：返回指定 ProcessingRun 的当前宏观生命周期状态（running / awaiting_human / succeeded / failed 等）及总体起止耗时；
     - `StageProgress`：返回各 Stage（M1–M8）的具体执行进度、已完成任务计数、进行中任务及当前 Stage Gate 达成状态；
     - `PendingQueue`：返回当前阻断或等待人工干预的待处理队列明细，必须显式列出五个专用队列：
       1. M2 异常页与低置信字
       2. M3 边界分歧
       3. M4 类别分歧
       4. M6 待签发
       5. M7 待裁决
     - `BlockingReasons`：返回当前阻断 Stage Gate 通过的具体原因、失败校验项或未满足的依赖项明细；
     - `ReworkImpact`：返回若对某历史 Artifact 或阶段发起返工时，将级联波及的下游阶段、衍生 Revision 与受影响队列范围；
     - `ThroughputEstimate`：返回基于当前算力及历史加工耗时测算出的阶段吞吐与预计剩余处理耗时。
   - **位置 2（`§7 统一 Module Interface` 末尾）**：
     在小节 7.1 之后（在 `## 8. Package 公共结构` 之前），追加一句关于进度事件上报的强制约束：
     - 各 Processing Module 必须在运行中向 Local Orchestrator 实时上报进度事件（Progress Events），否则上述只读查询契约无实时数据来源。
5. 完成后运行 `docs/blackbox-spec-rework/work-items/t09/TDD.md` 中的全部 Green checks、`bash docs/blackbox-spec-rework/verify-T.sh`（FAIL 数必须从 5 严格减少至 4，且 T-09 为 PASS）以及 `git diff --check`。
6. 确认无误后提交修改，提交消息必须严格为：`docs: define Local Orchestrator read queries`。
7. 最终报告必须包含：commit hash、真实修改文件、Red baseline、Green 原始摘要、六项查询与五队列核验对照及全局 T 结果。
