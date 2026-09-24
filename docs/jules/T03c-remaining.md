# T03c 剩余部分：assembly（M7）与 review（M6）（给 Jules 的续单）

> 派单人：云端 Claude（主 Agent），2026-09-24。**先读完 `docs/jules/T03c.md` 全文**，那里的规则、禁止事项、验证方法全部照旧有效；本文件只写「做到哪了、剩什么、有哪些现成工具」。
> 沟通渠道：`docs/jules/CHANNEL.md`（简短消息）+ `docs/jules/T03c.report.md`（详细回报，**接着已有内容往下追加**）。

## 一、已完成（不要重做）

分支 `claude/wizardly-maxwell-pqrzh9`，提交如下；每一步的细节和测试原文都在 `T03c.report.md`。

| 包 | 命中 | 提交 |
|---|---|---|
| intake（M1） | 3 → 0 | `c099512` |
| digitization（M2） | 5 → 0 | `0ecf5dc` |
| knowledge_extraction（M4） | 22 → 0 | `a1ed93a` |

## 二、你要做的

1. **从分支 `claude/wizardly-maxwell-pqrzh9` 的最新提交拉你自己的分支**（例如 `jules/t03c-m7-m6`），不要从 `main` 拉——前面三个包和新增的端口方法都在这条分支上。
2. 按 `T03c.md` 第四节顺序做完：**4. `assembly`（28 处）→ 5. `review`（53 处）**，每个包清完提交一次。
3. 最后一个提交加守护用例 `test_t03c_packages_have_no_ledger_internals`（`T03c.md` 第四节末尾），做第六节的四项验证。
4. PR 目标分支是 `main`，标题照 `T03c.md` 第七节。PR 会包含前面三个包的提交，这是预期的。**不要合并。**

## 三、环境（与 `T03c.md` 第五节相比要多装两样）

```bash
bash tools/jules_setup.sh
localedef -i en_US -f UTF-8 en_US.UTF-8     # 缺它 validation 会多 1 条假红（TODO T15）
apt-get install -y sqlite3                   # 缺它 contract_registry 会多 1 条假红（TODO T15）
export LC_ALL=C.UTF-8 LANG=C.UTF-8
```

装齐后的基线：只有 T14 已知的 6 条红（contract_registry 1、orchestrator 5），skip 为 assembly 2、dataset_compiler 36。**不要修这 6 条。**

## 四、现成的端口方法（先用这些，缺了再补）

T03 已有：`get_revision`、`get_step_run`、`read_object`、`describe_revision`（含 `artifact_type`、`artifact_id`、`stage_package_id`、`step_run_id`、`status`、`sha256`）、`list_step_run_revisions(step_run_id, artifact_type, status)`、`list_artifact_revisions`、`list_frozen_inputs`、`get_processing_run`、`list_step_runs(edition_part_id, stage)`、`list_stage_packages(stage)`、`list_transformations`、`list_checkpoints`、`latest_checkpoint`。

T03c 新增（在 `pipeline/ledger/store.py` 里看 SQL 和排序）：
- `latest_processing_run(edition_part_id, kind)`
- `latest_checkpoint_step_run(edition_part_id, stage, status)`：M6 `review/inputs.py:45`、M7 `assembly/step.py:24` 的那段 `SELECT DISTINCT c.step_run_id …` 就是它，传 `"succeeded"`
- `list_revisions(artifact_type=, status=, step_run_ids=, processing_run_id=, prev_revision_id=)`：**按写入顺序（rowid）**
- `list_human_events(step_run_id=None)`：**按写入顺序（rowid）**，含 `decision_type`、`created_at`
- `list_transformation_inputs/outputs/human_events(transformation_id)`：修订号升序

在 `knowledge_extraction/inputs.py` 里有现成写法可以照抄：`_artifact_types`（逐个 `describe_revision`）、`_profile_revisions`（稳定排序）。

## 五、排序：必须保持原样（M4 里的做法，照做）

- 原 SQL **没写 ORDER BY** 的单表查询，SQLite 实际走 `SCAN`＝写入顺序（rowid）→ 用上面按写入顺序返回的方法即可。拿不准时用 `EXPLAIN QUERY PLAN` 实测，把结果写进回报。
- 原 SQL 写 `ORDER BY created_at, rowid` → 对写入顺序的结果按 `created_at` 做 **Python 稳定排序**（`sorted(rows, key=lambda r: r["created_at"])`）；`ORDER BY rowid` → 直接用。
- 原 SQL 写 `ORDER BY … DESC LIMIT 1` → 取稳定排序后的最后一个。
- 端口缺查询（例如按 `step_run_id` 查 `stage_checkpoints` 的元数据、`revision_status_events`、按 stage 列 StepRun、`get_stage_package`），照 `fd0ba6e` / 本任务的做法补**只读**方法：先在 `pipeline/ledger/tests/test_read_queries_t03c.py` 写用例确认红，再实现，并把方法名加进该文件的 `T03C_METHODS`。

## 六、已知的一处要停手：`assembly/inputs.py:173`

```python
# 回退查询：
"SELECT r.step_run_id, r.status FROM transformations t "
"JOIN step_runs r ON r.step_run_id = t.step_run_id "
"WHERE t.output_artifact_revision_id = ? AND r.stage='m4'"
```

`transformations` 表**没有** `output_artifact_revision_id` 这一列（见 `pipeline/ledger/store.py` 的 DDL；输出在 `transformation_outputs` 表）。所以只要上一条 `result_json LIKE` 查不到，这里就会抛 `sqlite3.OperationalError: no such column`。这是既有缺陷，不是本任务造成的。

**怎么做**：
1. 写一条用例证明它现在确实会抛这个错（构造一个 `result_json` 里不含该修订号的 M4 StepRun），贴输出。
2. **不要自己选修法**。在回报「待裁决」里写清证据和候选方案，例如：(a) 改为「`describe_revision(候选包)['step_run_id']` → `get_step_run`」；(b) 改为查 `transformation_outputs`；(c) 保留原样（这一处继续算后门，守护用例会红）。
3. 其余 27 处照常做完。PR 描述写明「停手待裁决：assembly/inputs.py:173」。

## 七、每个修复都要有篡改探针

改完一处重要逻辑，就临时把它改坏（例如换掉筛选条件、返回 `None`），确认有用例转红，把红的输出贴进回报，再改回来。**如果改坏后没有用例变红**（M1、M2 都遇到过），先补一条护栏用例钉住原行为，再继续。

## 八、做完后

- 在 `CHANNEL.md` 追加一条简短回报（3 行以内：做到哪、PR 链接、有没有待裁决）。
- **不要改 `TODO.md`、`HANDOFF.md`、`PLAN.md`**：主 Agent 验收后统一更新。
