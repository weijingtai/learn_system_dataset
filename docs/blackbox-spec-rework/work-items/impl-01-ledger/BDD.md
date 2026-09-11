# BDD：impl-01 Artifact Ledger

## 1. 标识与状态（ACT 01）

- 1.1 Given 17 个前缀家族，When 生成或校验任一标识，Then 完全匹配 §8.1 正则；大写、错位、`pr_` 冒充 `prun_`、`<stage>` 出闭集一律 `ID_001`。
- 1.2 Given §8.2 两张迁移表，When 请求任一 (当前, 目标) 组合，Then 表内放行、表外 `IllegalTransition`、表外取值 `SCH_002`；终态无出边。

## 2. 存储（ACT 02）

- 2.1 Given 两段相同字节，When 分别 put，Then 同一 sha256、磁盘一份（去重）；逻辑引用各自保留（由 Revision 记录）。
- 2.2 Given 已封存对象被篡改，When verify / seal，Then 检出（`SRC_003`），Revision 转 `quarantined`。
- 2.3 Given 一个写入者已持锁，When 第二个写入者启动，Then 被拒（`WriterLocked` / `ledgerd` exit 3）；只读查询不受影响。
- 2.4 Given 事务中途异常，Then 无半成品行；`var/` 不进 Git。

## 3. StepRun 事务序列与人工恢复（ACT 03）

- 3.1 Given StepRequest 引用了 `draft` 修订，When begin，Then 拒绝（`NotConsumable`）；Given 合法请求，Then 输入被冻结、状态 `running`、事件 `created`。
- 3.2 Given 任务需要人工，When await_human，Then 得到单次 `resume_token`，队列与冻结输入持久化；record_human_event 不消费 token，resume 消费且二次无效。
- 3.3 Given `awaiting_human` 被 suspend，When recover，Then 回到 `awaiting_human` 且 token 仍有效；Given 终态，When recover，Then 拒绝且不改写。
- 3.4 Given 失败，When fail_step_run，Then 失败修订封存保留、状态 `failed`、StepManifest 封存；重跑创建新 StepRun 并以 `supersedes_step_run_id` 关联，旧终态不变。
- 3.5 Given 成功，When finish，Then StepResult 过 Schema、所有产出 sealed、StepManifest 引用最后 Checkpoint。

## 4. StageCheckpoint（ACT 03）

- 4.1 每完成一个 task 落盘一个 Checkpoint，链上 prev 指针正确，同一 EditionPart×Stage 一条链（跨 StepRun 接链）。
- 4.2 恢复只重放待办，已完成与已封存人工决定不重做；失败 task 记入已完成清单并标记，恢复时须重做。
- 4.3 最后人工事件晚于最后 Checkpoint 时先补写再恢复。

## 5. 进程与客户端（ACT 04）

- 5.1 客户端经 UDS 调用与直连语义一致；异常类与错误码原样还原；bytes 经 base64 无损。
- 5.2 SIGTERM 后锁释放、socket 文件删除。

## 6. 宿主判定（ACT 05）

- 6.1 mini_ed01 经真实写路径灌入：3 StepRun、9 Checkpoint、3 Transformation，ID 与 fixture 常量相等；二次灌入 `ID_002` 且无半成品。
- 6.2 `run_all.sh` 20.2/20.3 变 `PASS`，其余 BLOCKED/FAIL 不变；删除一个 Checkpoint 或校验报告引用即变 FAIL（判据不是永真）；fixture 被篡改时宿主校验先 FAIL。
