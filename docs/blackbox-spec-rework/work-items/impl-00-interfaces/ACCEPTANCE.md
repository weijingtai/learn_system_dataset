# ACCEPTANCE：impl-00 跨模块接口契约（首纵切裁剪后）

状态：`READY_FOR_REVIEW`——W2-C1 定稿 2026-09-12，依 `G7-RULINGS.md` §9 裁剪；未经实现、未经主 Agent 验收。首纵切保留 ACT 1 个（`impl-00/10`），`act/00–09` 全部 `DEFERRED`。

## 0. 定稿审查（主 Agent 四查，待执行）

- **忠实性**：README §4 的 17 条逐条对应 `G7-RULINGS.md` §9 第 1–17 条；首纵切只保留 §9「两类 ACT」中的 (a)，(b) 因无引用不做；`act/00–09` 状态、写范围、依据均未改语义，只加 `status: DEFERRED` 并在 `ACT.yaml` 移出 `executor_groups`。
- **覆盖性**：`impl-00/10` 覆盖 §2 D4 的 6 个 M8 新类型与 §9 第 10 条的 `gate_results`/`validation_package`；`INTERFACES.md` 其余章节的同步点（M8 尾链、M5 `corpus_only`、§9 第 13/16/21 条）逐条写入 `act/10.yaml` 的 contract A–I。
- **可执行性**：`act/10.yaml` 有 scope.write、tests_first、tests（`check_interfaces.py` 的 IF01–IF17 检查名与 7 个用例名）、contract、verify（精确命令与期望）、commit；Red 可复现（§4 缺 8 个类型即 FAIL）。
- **独立性**：`impl-00/10` 只写 `INTERFACES.md`、`check_interfaces.py`、`tests/`，与 impl-03（`pipeline/validation/**`）、impl-04（`pipeline/dataset_compiler/**`）写范围不重叠；不触 `openspec/schemas/`、fixture、`pipeline/ledger/`、`openspec/acceptance/`。

## 1. 范围核对

定稿轮只改本目录：`README.md`、`ACT.yaml`、`act/00–09.yaml`（仅加 `status: DEFERRED`）、`act/10.yaml`（新建）、`FIXTURE-PLAN.md`/`TDD.md`/`BDD.md`（加「纵切后」小节）、`PROMPT-C1.md`、`ACCEPTANCE.md`；`INTERFACES.md` 留待 `impl-00/10` 改写，未动其【实际】事实。

**fixture 期望产物引用证据（步骤 2(b)）——结论：无引用。** 逐文件排查并 `grep -n "mini_ed01/expected"`（`-r` 两目录）均为 0 命中：

| 排查对象 | 命令 | 结果 |
|---|---|---|
| impl-03（`pipeline/validation/**`） | `grep -rn "mini_ed01/expected" work-items/impl-03-validation` | 0 命中 |
| impl-04（`pipeline/dataset_compiler/**`） | `grep -rn "mini_ed01/expected" work-items/impl-04-dataset` | 0 命中 |

关键反证（file:line）：

- `impl-03-validation/README.md:86`：D-01 的 B 选项「在 mini_ed01 增补 `expected/m4` 金标候选」**未被采纳**；采纳 A「首切片 `scope: corpus_only`，冻结 m3 包与 M3 全部输出，共 17 个」。
- `impl-03-validation/act/06.yaml:44,47`：验收只把 `FIXTURE_DIR` 指向 `pipeline/corpus/_fixture/mini_ed01` 并执行其 `verify.sh`，不读 `expected/` 金标。
- `impl-04-dataset/README.md:143`：M8 找 M3 用 `list_checkpoints(ep,"m3")` → `run_m3` **真实产出**，并明确「`fixture_ingest` 灌入的 m3 包没有 `spans_revision_id`，必须拒绝」。
- `impl-04-dataset/README.md:92,138-140`：生产代码禁读 fixture 路径（唯一例外薄 M1 shim），消费对象是 `run_m3` 输出与 `manifest.yaml`/页 JSON，不含 `expected/`。
- `impl-04-dataset/act/03.yaml:45`：`FIXTURE = 仓库根 / "pipeline/corpus/_fixture/mini_ed01"`，无 `expected/` 引用。

故按 `G7-RULINGS.md` §9「若无引用则不做」，不保留任何生成 `expected/m5`、`expected/m8` 的 ACT；ACT 05–07 全部 `DEFERRED`。

## 2. 门禁与判据

定稿轮（本提交）：`git diff --check` 无输出；本目录全部 YAML 可解析（`yaml.safe_load`）；`run_all.sh` 与 `schemas/verify.sh` 未受影响（未运行、未改）。

`impl-00/10` 执行后（见其 `verify`，`git archive` 干净树）：

- `python3 .../check_interfaces.py` → exit 0，末行 `I00-IF SUMMARY pass=17 fail=0`；`unittest` 7 用例 OK。
- `bash openspec/schemas/verify.sh` → 0（未改 schemas）；`run_all.sh` → `SUMMARY pass=2 fail=1 blocked=8`（未改 acceptance）。
- `git status --short openspec/schemas pipeline/corpus/_fixture pipeline/ledger` 为空；只 add `commit.add` 路径；无 `__pycache__`；`git diff --check` 通过。

## 3. 语义与质量审查（主 Agent）

- `INTERFACES.md` §4 闭集与 README §5.1 逐字一致；8 个新类型行状态列无 DEFERRED/纵切后；表内无重复类型名。
- M8 卡片写清尾链四段与 `knowledge_chain: "not_compiled"`；M5 卡片写清 `corpus_only`、17 个冻结修订、`quote_sha256` 复算、`validation.passed` + 上游 `succeeded` 双条件。
- §9 第 13 条只读 SELECT 缺口清单（`frozen_inputs`/`artifacts.artifact_type`/`stage_packages`/按 `step_run_id` 取 sealed stage_package）与 README §5.2 一致；第 16 条页图字节登记进 Ledger 写明。
- 执行方未越权：不改 `ACCEPTANCE.md`，不写结论性措辞；`validator_report` 未自行登记（列 README §5.2 待裁决 1）。
- 独立复算：`check_interfaces.py` 不信任 `INTERFACES.md` 的自述，按行解析 §4 表逐项判定。

## 4. 结论

定稿轮交付：`impl-00` 状态 `READY_FOR_REVIEW`；首纵切保留 ACT 1 个（`impl-00/10`，文档登记 ACT）；`DEFERRED` ACT 10 个（`impl-00/00–09`），文件内容保留。派发 `impl-00/10` 后按其报告独立验收，结论回填 §5。

## 5. 验收记录由主 Agent 填写
