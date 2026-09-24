# T03c —— M6 `pipeline/review/acceptance.py`（20 处）回报

执行者：本机 worktree `/Users/jingtaiwei/Git/Public/learn_system-wt-t03c-m6acc`，分支 `t03c-m6acc`（基线 `bda5c70`）。
派单：`/Users/jingtaiwei/tmux-agents/runs/prompts/t03c-m6acc.md`（先读 `t03c-common.md`）。

## 基线

动手前（未改任何代码）在 `bda5c70` 上跑三个包，
命令 `export LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8; .venv/bin/python -m unittest discover -s pipeline/<pkg>/tests -t .`：

```
== review
Ran 169 tests in 54.888s
OK
== ledger
Ran 100 tests in 4.141s
OK
== contract_registry
Ran 46 tests in 59.087s
OK
```

（本机有页图与真书账本；无云端那 6 条已知红，无多出 skip。）

检测器基线 `scan_ledger_internals(["pipeline/review"])`：

```
count: 29
pipeline/review/acceptance.py 20 [80, 92, 104, 115, 132, 142, 253, 297, 388, 444, 469, 479, 490, 502, 550, 599, 611, 620, 678, 714]
pipeline/review/console.py 6 [74, 81, 92, 168, 254, 393]
pipeline/review/testing/upstream_stub.py 3 [30, 40, 872]
```

与派单命中清单完全一致。

## 进度

### 1. acceptance.py（20 → 0）—— 提交 `d4c380c`

一次提交（20 处同属一个文件）。改法一览（行号以 `bda5c70` 为准）：

| 行 | 原查询 | 改法 |
|---|---|---|
| 80 | `service.objects.get(sha)` | `service.read_object(sha)` |
| 92 | 自拼 `artifact_revisions⋈artifacts` 取 `artifact_type` | `service.describe_revision(id)["artifact_type"]`（None → None） |
| 104 | `frozen_inputs ... ORDER BY artifact_revision_id` | `service.list_frozen_inputs(step_run_id)`（已升序） |
| 115 | `SELECT DISTINCT step_run_id FROM stage_checkpoints WHERE stage='m6'` | **新方法** `list_stage_checkpoint_step_runs("m6")` |
| 132 | `human_events ... ORDER BY rowid` | `service.list_human_events(step_run_id)` |
| 142 | 自拼 `review_queue` 修订 | `service.list_revisions(artifact_type="review_queue")`（按 rowid） |
| 253 | `revision_status_events ... to_status='sealed' ORDER BY created_at LIMIT 1` | **新方法** `first_sealed_event_created_at(id)` |
| 297 | `SELECT event_revision_id, step_run_id, decision_type FROM human_events` | `service.list_human_events()` |
| 388 | 自拼 `stage_packages⋈artifact_revisions WHERE stage='m6'` | `service.list_stage_packages("m6")` |
| 444 | 自拼 `step_manifest AND step_run_id=?`（`fetchone`） | `service.list_step_run_revisions(step_run_id, artifact_type="step_manifest")`（判空） |
| 469 | `transformation_inputs WHERE transformation_id=?` | `service.list_transformation_inputs(id)` |
| 479 | `artifact_revisions WHERE step_run_id=? AND status='sealed'` | `service.list_revisions(status="sealed", step_run_ids=[run])` |
| 490 | `transformation_outputs WHERE transformation_id=?` | `service.list_transformation_outputs(id)` |
| 502 | `transformation_human_events WHERE transformation_id=?` | `service.list_transformation_human_events(id)` |
| 550 | `human_events WHERE step_run_id=?` | `service.list_human_events(step_run_id)` |
| 599 | `SELECT count(*) FROM stage_checkpoints WHERE rework_impact_report_revision_id=?` | **新方法** `count_checkpoints_by_rework_report(id)` |
| 611 | `artifact_revisions WHERE status='invalidated'` | `service.list_revisions(status="invalidated")` |
| 620 | `artifact_revisions WHERE prev_revision_id=?`（`fetchone`） | `service.list_revisions(prev_revision_id=...)`（判空） |
| 678 | `stage_packages ... WHERE stage='m6' ORDER BY ar.rowid DESC LIMIT 1` | `service.list_stage_packages("m6")[-1]` |
| 714 | `service.objects.get(sha)` | `service.read_object(sha)` |

返回值、异常类型、错误文案均原样（`_revision_bytes` 的 `KeyError`、`Manifest is None`→`not manifest` 的语义等价、
`successor is None`→`not successor` 等价）。

**新增端口方法（3 个，只读）**：块首注释 `# —— T03c M6-acceptance 新增 ——`，集中在 `store.py` / `service.py` / `client.py` / `ports.py` 同一块。
- `list_stage_checkpoint_step_runs(stage)`：`SELECT DISTINCT step_run_id FROM stage_checkpoints WHERE stage=?`（与原 SQL 逐字一致，无 ORDER BY）。
- `first_sealed_event_created_at(artifact_revision_id)`：原「最早 sealed 事件」SQL 原样，无命中返回 `None`。
- `count_checkpoints_by_rework_report(revision_id)`：原 `count(*)` SQL 原样。

加前先查过现成方法（`grep -n "def " pipeline/ledger/store.py` + T03c-remaining 第四节）：其余 17 处全用现成方法，未重复造轮子；
`list_step_run_checkpoints`（同包 step.py 新增）与本文件需求不同（那是按 StepRun 取元数据行），无关。

**用例**：新文件 `pipeline/ledger/tests/test_read_queries_t03c_m6acc.py`（自己的 `METHODS` 元组，照 `test_read_queries_t03c.py:160` 断言进闭集且三后端同名）。
先写用例确认红（`Ran 4 tests ... FAILED (failures=3, errors=3)`，`AttributeError: 'LedgerService' object has no attribute 'list_stage_checkpoint_step_runs'` 等），再实现，后 `Ran 4 ... OK`。未改 `test_read_queries_t03c.py`。

**排序核对**（`EXPLAIN QUERY PLAN` 实测，临时空库）：

| 处 | 原 SQL 计划 | 端口方法 | 结论 |
|---|---|---|---|
| 142 | `SCAN r`（artifact_revisions）= rowid 序 | `list_revisions` → `ORDER BY r.rowid` | 同序 |
| 444 | `SCAN r` = rowid 序 | `list_step_run_revisions` → `ORDER BY r.created_at, r.rowid`；调用方只判「有没有」 | 等价 |
| 388 | `SCAN sp`（stage_packages 写入序） | `list_stage_packages` → `ORDER BY r.created_at, r.rowid`；调用方只数个数、逐包独立校验 | 等价 |
| 678 | `SCAN ar ... ORDER BY ar.rowid DESC LIMIT 1`（最后写入的 m6 包） | `list_stage_packages("m6")[-1]`（created_at,rowid 升序末行）；stage_package 修订按序写入，created_at 与 rowid 同序 | 取到同一行 |
| 115 | `SELECT DISTINCT ... WHERE stage='m6'` 无 ORDER BY | 新方法逐字同 SQL | 同序 |
| 253/599/611/620/550/297/104 | 集合/存在性/count/最早一条 | — | 顺序无关 |

**探针（篡改后跑 `TestAcceptance.test_fixture_yields_thirteen_pass_two_blocked_exit_2`，改回即绿）**：

| 探针 | 改坏处 | 结果 |
|---|---|---|
| A | `_m6_step_runs` → `return []` | `AssertionError: 1 != 2` / `Ran 1 ... FAILED (failures=1)` |
| B | 388 `packages = []` | `AssertionError: 1 != 2` / FAILED |
| C | 599 `referenced = 0` | `AssertionError: 1 != 2` / FAILED |
| D | 678 `packages[-1]` → `packages[0]` | **单跑 13-PASS 用例不变红**（该 else 分支仅在 world 无 first_close/rework_close 时走到，原未被钉住）→ 见下护栏 |
| E | 104 `_frozen_inputs` → `[]` | `AssertionError: 1 != 2` / FAILED |
| F | 444 `manifest = []` | `AssertionError: 1 != 2` / FAILED |
| G | 611 `list_revisions()`（去掉 status 过滤） | `AssertionError: 1 != 2` / FAILED |
| H | 620 `successor = []` | `AssertionError: 1 != 2` / FAILED |
| I | 550 human_events 源改 `[]` | `AssertionError: 1 != 2` / FAILED |
| J | 297 `rows = []` | **13-PASS 不变红**（该判定的正例未被钉住）→ 见下护栏 |
| K | 92 `info = None` | `AssertionError: 1 != 2` / FAILED |

**护栏用例（补 `pipeline/review/tests/test_acceptance.py`，2 条）**：

1. `test_snapshot_projection_else_branch_picks_latest_m6_package`：克隆 world → 先把「较早写入的 m6 包」
   的 `payload.reviewed_edition_revision_id` 置空 → 抹掉 `first_close`/`rework_close` 逼出 else 分支，
   保留既有 snapshot；只有选中「最近写入的 m6 包」才 `errors == []`。
   探针 D 复测：`AssertionError: Lists differ: ['m6 StagePackage payload 缺少 reviewed_edition_revision_id'] != []` / FAILED；改回后 OK。
2. `test_decisions_as_human_events_detects_empty_rationale`：克隆 world → 取一条 `review_decision` 事件把
   `rationale` 置空 → 断言 `_check_decisions_as_human_events` 报「rationale 为空」。
   探针 J 复测：`AssertionError: False is not true : []` / FAILED；改回后 OK。

（其余 9 处探针均一变红即改回，`grep "TAMPER PROBE"` 无残留。）

**测试原文**（改完，三包）：

```
== review
Ran 171 tests in 66.746s
OK
== ledger
Ran 104 tests in 4.802s
OK
== contract_registry
Ran 46 tests in 61.466s
OK
```

（review 169→171 = +2 护栏；ledger 100→104 = +4 端口用例；无新增 FAIL/ERROR/skip。）

## 验证

1. 本包 `scan_ledger_internals(["pipeline/review"])`：

```
count: 9
pipeline/review/console.py 6 [74, 81, 92, 168, 254, 393]
pipeline/review/testing/upstream_stub.py 3 [30, 40, 872]
```

`acceptance.py` 已 0；只剩派单预期的 `console.py` 与 `testing/upstream_stub.py`（由另一执行器在其 worktree 处理）。

2. 三个包与基线逐包对照：review 171 OK、ledger 104 OK、contract_registry 46 OK——**不比基线新增红或 skip**（详上）。

3. `git diff --check` 无输出。

## 待裁决

无。

完成：d4c380c
