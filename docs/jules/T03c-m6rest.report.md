# T03c —— M6 最后 9 处（`review/console.py` 6 + `review/testing/upstream_stub.py` 3）回报

执行者：本机 worktree `/Users/jingtaiwei/Git/Public/learn_system-wt-t03c-m6rest`，分支 `t03c-m6rest`（基线 `822670e`）。
派单：`/Users/jingtaiwei/tmux-agents/runs/prompts/t03c-m6rest.md`。

## 基线

动手前（未改任何代码）在 `822670e` 上跑三个包，命令
`export LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8; .venv/bin/python -m unittest discover -s pipeline/<pkg>/tests -t .`：

```
== review
Ran 171 tests in 57.930s
OK
== ledger
Ran 106 tests in 4.414s
OK
== contract_registry
Ran 46 tests in 65.096s
OK
```

检测器基线 `scan_ledger_internals(["pipeline/review"])`：

```
count: 9
pipeline/review/console.py 6 [74, 81, 92, 168, 254, 393]
pipeline/review/testing/upstream_stub.py 3 [30, 40, 872]
```

与派单命中清单完全一致。

## 进度

### 1. console.py（6）+ testing/upstream_stub.py（3）—— 提交 `7525171`

**补丁使用**：`git apply --check` 通过后整份采用 `t03c-m6-freebuff-wip.patch`，**未改其任何写法**。逐处核对结果如下；两文件最终 diff 与补丁逐字一致，我只新增了护栏用例。

改法一览（行号以 `822670e` 为准）：

| 文件:行 | 原查询 | 改法 |
|---|---|---|
| console:74/81 | cmd_queue 自拼 `review_queue`（本运行 + frozen_inputs 回退）两段 `.fetchone()` | `step._review_queue_revision(reader, args.step_run)`（与 step.py 同一套端口查询） |
| console:92 | `human_events ... AND decision_type IS NOT NULL ORDER BY rowid ASC` | `reader.list_human_events(run)` 过滤 `decision_type is not None` |
| console:168 | 自拼 `IN (...)` 取冻结输入类型 | `inputs._artifact_types(reader, frozen)` |
| console:254 | 同 92（cmd_show 的 DECISION 行） | 同 92 |
| console:393 | `service.objects.get(sha)` | `service.read_object(sha)` |
| stub:30/40 | 本地重复实现 `_artifact_ref`（两段自拼 SQL） | 删除本地实现，`from pipeline.review.step import _artifact_ref`（见下核对） |
| stub:872 | 自拼 `stage_packages` 查 `stage_package_id`（`fetchone`） | `service.describe_revision(rev)["stage_package_id"]`（None 守卫） |

**核对（补丁是否可信）**：
- 依赖的端口/辅助函数都真实存在：`LedgerReader/LedgerService.read_object`、`describe_revision`、`list_human_events`、`inputs._artifact_types`、`step._review_queue_revision`、`step._artifact_ref`（后两者是 bda5c70 随 step.py 清零新增）。
- 无循环 import：`upstream_stub` → `step`，而 `step` 不 import `upstream_stub`；`acceptance` 亦 import 二者，无环。
- `step._artifact_ref` 与 stub 删掉的本地版**逐字同形**（stage_package / artifact 两分支的键集与键序一致，`ValueError("Revision ... not found")` 文案一致）。唯一差别：原版在「artifact_type=stage_package 但无 stage_packages 行」时会 `package_row[0]` 抛 TypeError，新版返回 `stage_package_id=None`；对合法数据二者等价。
- `cmd_queue` 的 `queue_rev is None → ReviewRefused("找不到 review_queue", code="REF_001")` 与原文案、异常类型一致。
- 行为不变：返回值、排序、异常类型、错误文案原样。

**排序核对**：
- console:92/254 `list_human_events` 为 `ORDER BY rowid`，与原 `ORDER BY rowid ASC` 同序。
- console:74/81 用 `step._review_queue_revision`，其等价性在 bda5c70 已用 `EXPLAIN QUERY PLAN` 记录：主查询 `SCAN artifact_revisions`（写入序=rowid）对应 `list_revisions` 的 `ORDER BY r.rowid`；回退 `SEARCH frozen_inputs (step_run_id=?)`（复合主键内按 revision_id 升序）对应 `list_frozen_inputs` 升序。
- console:168 结果进 dict，顺序无关；stub:872 单值，顺序无关。

**探针（篡改后跑相关用例，改回即绿）**：

| 探针 | 改坏处 | 结果 |
|---|---|---|
| P1 | cmd_queue `queue_rev = None` | `FAIL ... test_queue_reflects_recorded_decisions`：`AssertionError: 2 != 0 : queue failed:` |
| P2 | cmd_queue `cur_events` 源改 `[]` | `AssertionError: 'M6 QUEUE ... pending=5' != 'M6 QUEUE ... pending=1'` |
| P3 | cmd_show `types_map = {}` | `FAIL test_show_prints_evidence_anchor_fields`：`AssertionError: 2 != 0` |
| P4 | cmd_show `he_rows = []` | `FAIL test_show_prints_decision_line_after_decide`：`AssertionError: 0 != 1` |
| P5 | cmd_close `read_object("bad_sha256_tamper")` | `FAIL test_decide_batch_full_then_close_ok`：`AssertionError: 2 != 0 : close failed:` |
| P6 | stub:872 `sp_info = None` | **无红**（该字段无既有用例钉住）→ 补护栏，见下 |
| P7 | `step._artifact_ref` 的 `stage_package_id` 改坏 | `Ran 53 tests ... FAILED (errors=53)` |

（`grep -rn "TAMPER PROBE" pipeline/` 无残留；`step.py` 探针后已还原，`git diff` 为空。）

**护栏用例（补 3 条，覆盖原先无用例的路径）**：

1. `tests/test_console.py::test_queue_reflects_recorded_decisions`：open → decide-batch（只用 accept/reject）→ `queue`，断言末行 `M6 QUEUE <run> pending=1`、5 项状态与接受/驳回/未决一致。钉住 cmd_queue（74/81/92）。
   探针 P1、P2 复测转红，改回绿。（不复用整份 m6_decisions，原因见「待裁决」第 1 条。）
2. `tests/test_console.py::test_show_prints_decision_line_after_decide`：open → decide-batch → `show`，断言恰有 1 行 `DECISION <rev> accept active`。钉住 cmd_show 的 254。
   探针 P4 复测 `AssertionError: 0 != 1`，改回绿。
3. `tests/test_rework_review.py::test_rerun_validation_package_carries_m3_stage_package_id`：跑首审→失效传播→`seed_rerun_m4_m5`，读 M5' validation_package 文档，断言其 `m3_stage_package_id == describe_revision(doc["m3_package_revision_id"])["stage_package_id"]`。钉住 stub:872。
   探针 P6 复测 `AssertionError: 'pkg_m3_6d0147...' != 'pkg_m3_398858...'`（沿用旧包 id），改回绿。

**测试原文**（改完，三包）：

```
scan count: 0 []
== review
Ran 174 tests in 62.006s
OK
== ledger
Ran 106 tests in 4.464s
OK
== contract_registry
Ran 46 tests in 62.901s
OK
```

（review 171→174 = +3 护栏；ledger/contract_registry 与基线相同。）

## 验证

1. `scan_ledger_internals(["pipeline/review"])` = **0**（console.py 与 upstream_stub.py 均归零，本包全清）。
2. 三包与基线逐包对照：review 174 OK、ledger 106 OK、contract_registry 46 OK，**不比基线新增红或 skip**。
3. `git diff --check` 无输出。
4. 稳定性观察（详见「待裁决」第 2 条）：改后全量 `review` 跑了 9 次，其中 1 次出现既有 CLI 子进程用例的偶发失败（`test_console_rework_line`）；在 `test_console+test_rework` 组合下另捕获到既有用例 `test_close_with_pending_exit_2` 的同类偶发失败；基线全量跑 10 次全绿、目标用例单跑 20 次全绿。判定为与本改动无关的既有偶发（两个用例都不执行任何被改代码路径）。

## 待裁决

1. **`cmd_queue` 遇 modify 决定会抛的既有缺陷**（非本次改动引入）。用整份 `m6_decisions.yaml`（含一条 modify）驱动 `queue`，退出码 2：
   `M6 REFUSED ReviewRefused: modify requires modified_revision_id`。
   我在**原始 `822670e` 的 cmd_queue 逻辑**上重放（同样的两段 SQL + `model.decision_entry`），复现同一异常，故为既有缺陷。因本任务要求「行为不许变」，我未修改它，护栏改用 accept/reject 数据。候选修法：(a) 在 cmd_queue 里为 modify 决定补 `modified_revision_id`（需从 reviewed_candidate 查）；(b) 明确 cmd_queue 不支持 modify 并在文档/`--help` 声明。**请主 Agent 定夺，我不动。**
2. **既有偶发（flaky），非本次引入**。证据见上「验证 4」。目标两用例（`test_console_rework_line`、`test_close_with_pending_exit_2`）均为 `.store` 时代的既有 CLI 用例，不执行任何被我改动的行；失败表现为断言（疑似子进程/写锁计时），单跑与基线均难以复现。我未改动测试逻辑去「压」它。若主 Agent 认为需要，可另开 TODO 查写锁/子进程计时。

完成：7525171
