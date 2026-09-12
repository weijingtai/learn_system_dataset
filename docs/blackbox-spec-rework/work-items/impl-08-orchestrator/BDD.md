# BDD：impl-08 Local Orchestrator + Contract Registry

## 1. 登记表目录（ACT 00）

- 1.1 Given 仓库 `registry.yaml`，When 执行 `check_registry(load_registry())`，Then 问题清单为空。四份 L0 Schema 的 sha256 与文件一致；八个 stage 行名逐字等于规格 §19 第一列；五个专用队列名逐字等于 §5。
- 1.2 Given 分别出现以下篡改：Schema sha256 被改、Schema 路径不存在、`schema_version` 不是 "1.0.0"、stage 超出 m1–m8、行名少一字、`module_id` 重复、`binding: imported` 却带 `entry`、`consumes.from_stage` 不早于本 stage、生产表出现 `kind: stub`、端口不在 {ocr, model, index, storage}，Then 每种篡改都返回对应问题码。
- 1.3 Given 同一 stage 登记两个非桩 Module，When 调用 `module_for(stage)`，Then 抛出 `RegistryInvalid`；Given 该 stage 未登记，Then 返回 `None`。
- 1.4 Given 两份描述只在 `version` 上不同，Then 两者的 `interface_fingerprint` 相同；Given `produces` 不同，Then 指纹不同。
- 1.5 When 运行 `python -m pipeline.contract_registry check`，Then 末行为 `REGISTRY OK modules=3 ports=4`，exit 0；登记表损坏时 exit 1。

## 2. 端口与替换判定（ACT 01）

- 2.1 Given `DirectLedgerAdapter` 与 `LedgerdClientAdapter`，Then 两者的公开方法集都等于 `LEDGER_PORT_METHODS`，并且都能 `read_object`。
- 2.2 Given 用 `PortGuard` 包装的端口，When 访问 `store`、`objects` 或闭集外的方法，Then 抛出 `AttributeError`。
- 2.3 Given 两个假 Adapter 跑出的规范化结果相等、指纹相同，Then `substitutable` 为 true；Given 只有一个 Adapter，或结果不等，或指纹不同，或任一套件抛异常，Then `substitutable` 为 false，并在 `problems` 中写明原因。

## 3. Module 接口与桩（ACT 02）

- 3.1 Given 合法的 succeeded / failed / awaiting_human 三种 `StepOutcome`，Then `validate_outcome` 为空；Given 状态值非法、缺键、awaiting_human 缺待办、非 awaiting_human 却带待办、带 `resume_token` 或 `step_run_id` 等保留键、failed 无失败修订，Then 各返回问题。
- 3.2 Given 登记条目 `entry` 与注入的 `modules`，Then `bind_module` 解析出三种绑定；`imported` 绑定不可执行；缺少 `plan`/`execute` 的 `step_request` 对象被拒。
- 3.3 Given 在临时 Ledger 上建好 StepRun 的 `StubModule("m1")`，When `execute`，Then 每个 task 一个 Checkpoint、恰 1 个 StagePackage 过 Schema，返回的 outcome 合法。
- 3.4 Orchestrator 非测试源码不出现 `corpus_compiler`，也不 import 任何 `pipeline.<加工模块>`。

## 4. Stage Gate（ACT 03）

- 4.1 Given 桩 m1 成功，Then m1 Gate 八项全过，结果为 `passed`。
- 4.2 分别 Given 以下情形：无 StepRun、StepRun 为 failed、awaiting_human、StagePackage 缺失、StagePackage 的 stage 写错、`validation.passed=false`、`failures` 非空、输出缺少登记的 produces 类型、最新 Checkpoint 仍有待办、m2 冻结输入不含 m1 产出。Then 每种情形都让指定检查失败，Gate 为 `blocked`。
- 4.3 Given failed 的旧 StepRun 已被 succeeded 的新 StepRun 取代，Then 有效 StepRun 只剩新运行，Gate 为 `passed`。
- 4.4 Gate 不 import `runner`、`module`、`stubs`，也不 import 任何加工 Module。

## 5. EditionRun 串联（ACT 04）

- 5.1 Given 桩 m1–m6 的登记表，When 执行 `run_until("m6")`，Then 六个阶段依次 `executed`、最终 `complete`。m2–m6 每个 StepRun 的首个 artifact 是上游 `stage_gate_report`（内容为 `passed`），冻结输入包含上游产出。
- 5.2 Given m3 桩失败，When `advance`，Then m3 为 `executed` 且 StepResult 为 failed；再次 `advance` 返回 `blocked`。整个过程中 m4 没有 StepRun；`blocked` 前后 `artifact_revisions`、`step_runs`、`audit_log` 行数不变。
- 5.3 Given m2 桩返回 awaiting_human，Then StepResult 过 Schema，并带 `resume_token` 与待办；再次 `advance` 返回 `waiting`，且零写入。
- 5.4 Given m4 未登记，Then m4 返回 `refused`，原因含 `M4 Knowledge Extraction`；Given m2 为 `imported` 且无任务，Then 返回 `refused`。
- 5.5 Given 桩 `execute` 抛异常，Then 封存 `failure_report`（check `module_exception`），StepRun 为 failed；Given 返回违约 outcome，Then check 为 `outcome_contract`。
- 5.6 Given 计划的配置 `stage` 与登记不符，或输入修订未封存，Then 在任何写入之前 `refused`。
- 5.7 Given 一个假的 `legacy_self_driving` 入口（自建 StepRun 并 finish），Then Orchestrator 从 Ledger 重建出的 StepResult 过 Schema；Given 入口在建 StepRun 之前抛异常，Then 返回 `refused` 且零写入；Given `LedgerdClientAdapter`，Then legacy 绑定被拒。
- 5.8 Given 两个 EditionPart，一个 `complete`、一个停在 m3，Then `edition_status` 的 `complete` 为 false；两个都完成则为 true。

## 6. 人工暂停与恢复（ACT 05）

- 6.1 Given m2 桩 awaiting_human，When 写入人工事件并调用 `record_human_event`，Then 立即多出一个 Checkpoint，其 `human_decisions` 含该事件；此时 token 未被消费，同一 token 仍可调用 `resume`。
- 6.2 When `resume`，Then 以 `mode="resumed"` 再次执行，`context.human_event_revision_ids` 等于已登记事件，StepResult 为 succeeded。再用旧 token → `InvalidResumeToken`，且无新写入。
- 6.3 Given 创建时间很早的 awaiting_human StepRun，When 多次 `advance` 或查询，Then 状态保持 awaiting_human（没有超时自动失败）。
- 6.4 Given 操作者对 awaiting_human 调用 `suspend`，When `recover`，Then 回到 awaiting_human，原 token 仍可 `resume`；Given 对 running 调用 `suspend`，When `recover`，Then 以 `mode="recovered"` 再次执行，已完成 task 不重做。
- 6.5 Given 进程中断后遗留的 running StepRun，When `reconcile_after_outage`，Then 转为 `suspended`（source 为 infrastructure）；已处于终态的 StepRun 不被改写。
- 6.6 Given m4 桩在第 2 个 task 失败且 `supports_recovery=true`，When `rerun_from_checkpoint("m4")`，Then 新 StepRun 以 supersedes 指向旧运行，第 1 个 task 不重做，旧 failed 运行及其失败修订保留，m4 Gate 为 `passed`；Given `supports_recovery=false`，Then 返回 `refused`。

## 7. 只读查询与 CLI（ACT 06）

- 7.1 Given 链停在 m2 awaiting_human，Then PendingQueue 的五个队列键齐全，「M2 异常页与低置信字」下恰有 1 项；其余队列为空列表。
- 7.2 Then BlockingReasons 列出 m2 未通过的检查；Given supersedes 链已达 3 轮，Then 出现 `rework_threshold_exceeded` 告警。
- 7.3 Then StageProgress 对 m1–m6 全部列出，m1 为 `passed`、m2 为 `blocked`、m3 为 `not_started`；RunStatus 返回 Ledger 聚合状态与 `edition_part_complete=false`。
- 7.4 Given m1 的产出修订，Then ReworkImpact 为 `estimate: true`，`affected_stages` 包含 m2 及之后已执行的阶段。Given 没有 succeeded 历史，Then ThroughputEstimate 的 `estimated_remaining_seconds` 为 null。
- 7.5 查询前后 Ledger 三表行数不变。
- 7.6 CLI：`advance` 执行一步，末行 `ORCH EXECUTED …`，exit 0；阻断时 `ORCH BLOCKED …` exit 1；拒绝时 `ORCH REFUSED …` exit 2；`status` 输出 JSON。

## 8. 20.1 验收（ACT 07）

- 8.1 Given mini_ed01 与生产登记表，When 运行 `orchestrator-gate.sh`，Then 5 项 PASS，`registered_modules_m1_m6` 为 BLOCKED 且行名为 `M4 Knowledge Extraction`，exit 2。
- 8.2 Given 注入「Gate 放行未完成任务」的缺陷（打补丁让 `evaluate_stage_gate` 恒为 passed），Then `gate_blocks_incomplete` 为 FAIL，exit 1；Given 准备阶段崩溃，Then exit 1；Given 缺 fixture，Then exit 3。
- 8.3 Given 被验目录自带的 `verify.sh` 被换成假脚本且数据被改，Then 首行为 `FAIL fixture_host`，exit 1。
- 8.4 Given 只灌入 m1，Then 真实链返回 `refused`（m2 为 imported 且无任务），m3 没有 StepRun。

## 9. 20.10 验收（ACT 08）与 run_all（ACT 09）

- 9.1 Given 仓库现状，When 运行 `contract-registry.sh`，Then 3 项 PASS、2 项 BLOCKED，exit 2；`modules_port_clean` 的说明列出 `step.py` 的行号。
- 9.2 Given `registry.yaml` 中 Schema 哈希被改（副本），Then `registry_consistent` 为 FAIL，exit 1；Given 打补丁让 ledgerd 套件结果与直连不同，Then `storage_port_substitutable` 为 FAIL。
- 9.3 Given `pipeline/orchestrator` 非测试源码中出现 `.store.conn`，Then 为 FAIL，而不是 BLOCKED。
- 9.4 `run_all.sh 20.1 20.10` 输出两行 BLOCKED，行名分别取自 acceptance 的首个 BLOCKED 行；`run_all.sh` 全量 SUMMARY 仍为 pass=2 fail=1 blocked=8；其余九条输出逐字不变。
