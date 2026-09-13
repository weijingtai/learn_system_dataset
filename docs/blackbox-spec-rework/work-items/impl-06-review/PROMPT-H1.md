# impl-06 · H1 实现 Prompt（ACT 01–11：M6 Review & Curation 最薄接入与精确失效传播）

你是执行 Agent，运行在 tmux，无人实时看屏幕。所有回复、注释、docstring、提交信息使用中文。

工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree、不删除文件。

先完整阅读（只读）：本目录 `README.md`（§1 目标、§4 主 Agent 决定与 §4.1 待裁决、§4.2 对账、§5 契约、§9 用户待办）、`ACT.yaml`、`BDD.md`、`TDD.md`、`act/01.yaml`–`act/11.yaml`、`docs/blackbox-spec-rework/G7-RULINGS.md`（§1 P1–P9、§4、§9.3 第 34–43 条、§9.5 第 45–46 条、§9.6–§9.11 第 47–58 条）、`impl-05-knowledge/PROMPT-G1.md`（先例）、`impl-02-corpus/act/03.yaml`（Ledger 事务模板）、`pipeline/knowledge_extraction/{__init__,review_events,inputs,step,submit}.py`（M4 已落地契约）、`pipeline/validation/{step,package,findings}.py`（M5 已落地契约）、`pipeline/dataset_compiler/{packs,gate}.py`（M8 知识链 `not_compiled`）、`pipeline/orchestrator/{gate,module}.py` 与 `pipeline/contract_registry/{catalog.py,registry.yaml}`（Module 描述符与 Stage Gate carrier）、`pipeline/ledger/{service,states,store}.py`（公开方法与状态闭集）、`docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md`（§2.6/§4/§6）、`pipeline/corpus/_fixture/mini_ed01/`（`spans.yaml`、`m4/` 金标、`expected/m4.stage_package.yaml`、`verify.sh`）。

## 只允许写

- `pipeline/review/**`（新建，含 `testing/` 非生产子包与 `tests/`）
- `openspec/acceptance/m6-data-fields.sh`（ACT 11 新建）

其余一律禁止写入：规格正文、`openspec/schemas/**`、`openspec/id-prefix-registry.md`、fixture 目录、`openspec/acceptance/run_all.sh`、`m3-coverage.sh`、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`pipeline/knowledge_extraction/**`、`pipeline/validation/**`、`pipeline/dataset_compiler/**`、`pipeline/orchestrator/**`、`pipeline/contract_registry/**`、`pattern_knowledge_workbench/`、`HANDOFF.md`、`PLAN.md`、`SUBAGENT_TODO.md`、`G7-*.md`、任何 `ACCEPTANCE.md`、其他 work-items。不得改代码草案的函数名/返回键/检查名/artifact_type/task_id 去迁就实现。

## 台账与人工决定纪律（硬性）

- 你只写 `pipeline/review/**` 与 `openspec/acceptance/m6-data-fields.sh`；台账与验收记录由主 Agent 写。
- 不得在任何文件或提交信息里写「ACCEPTED」「验收通过」「主 Agent 审查」之类结论。
- **P7：不得伪造人工签发**。`expert_verified` 只能由用户撰写的决定表产生；本包测试只用非生产合成数据并显式标注 `synthetic_fixture`，不代表真实专家决定。依赖真实签发的判定一律 BLOCKED，不得写成 PASS。
- `review_decision` 事件逐字复用 `pipeline.knowledge_extraction.review_events.build_review_decision`，不新造顶层键、不把 `standing` 写进事件。

## 测试纪律（硬性）

- 每个 ACT 先写测试（用例名与 ACT `tests` 逐字）并运行取得 **Red 原文**，再实现；Red 原文与 Green 的 `Ran/OK` 行写进最终报告。
- 不得修改测试断言去迁就实现；不得删改已有断言。
- 只用标准库 + PyYAML + jsonschema；不新增依赖、不新增 ID 前缀、不调用模型 API。
- 测试只用 tempfile 目录；读 fixture `spans.yaml`/`m4/` 仅作只读输入。
- 回归取行统一 `2>&1 | grep -E "^(Ran|OK|FAILED)"`（G7-RULINGS §9.2 第 27 条）。

## 开工前提（任一不符，停手上报）

```bash
cd /Users/jingtaiwei/Git/Public/learn_system
export LC_ALL=en_US.UTF-8
git status --short pipeline/review openspec/acceptance/m6-data-fields.sh   # 空
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                        # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1  # 与基线相同
bash openspec/schemas/verify.sh >/dev/null; echo $?                         # 0
python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py; echo exit=$?   # 末行 fail=0 且 exit 0，且本包新类型 PASS 行存在（第 54 条）
.venv/bin/python -m unittest discover -s pipeline/ledger/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)"             # OK
.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)"    # OK
.venv/bin/python -m unittest discover -s pipeline/knowledge_extraction/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)"  # OK
.venv/bin/python -m unittest discover -s pipeline/validation/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)"         # OK
bash openspec/acceptance/m6-data-fields.sh >/dev/null 2>&1; echo $?         # K1–K3: 127（尚未创建）
```

另需确认：

- **P2**：本包新增 artifact_type（`review_queue`、`reviewed_edition`、`reviewed_edition_package`、`rework_impact_report`）已由 impl-00 `act/13.yaml` 登记写入 `INTERFACES.md` §4 临时闭集；`check_interfaces.py` 末行 `fail=0` 且 exit 0，且上述类型各自 PASS 行存在（第 54 条，不写死 pass 总数）。未登记不得实现。
- **K2 前置**：impl-05（M4）、impl-03（M5）状态 `ACCEPTED`。
- **第 61 条（D-01）**：Snapshot 归 M7，ACT 10 已 WITHDRAWN，不派发；ACT 11 第 12 项 `snapshot_projection` 恒 BLOCKED（前置缺失: M7 创世汇编）。**第 62 条（D-08）**：M6 不改 M4 修订状态。
- **fixture m6 金标（若需）**：如需 fixture 金标，属 impl-00 目录下的独占 ACT（P4），与本包实现分离；本包不写 fixture。

## 逐步

按 `ACT.yaml` 的 K1 → K2 → K3 顺序串行；**每组完成后停下待主 Agent 验收**，不得跨组连做。

1. **K1（ACT 01 → 02 → 03）**：纯函数。ACT 01 `model.py`（队列、事件复用 review_events、规范化内容哈希、fold/outcome）；ACT 02 独立 M6 Review Gate（九项，不 import model/propagation/step/rework）；ACT 03 §14.1 失效传播（不写 Ledger、不调用 invalidate_revision）。每个 ACT 一个提交，`commit.add`/`commit.message` 逐字照 act 文件。
2. **K2（ACT 04 → 05 → 06 → 07）**：ACT 04 非生产 `testing/` 桩（驱动真实 M3/M4/M5）+ `resolve_m6_inputs`；ACT 05 `open_review`/`record_decision`/`recover_review`（每条决定即时 Checkpoint）；ACT 06 `close_review`（Gate、`reviewed_edition` + `reviewed_edition_package`、m6 StagePackage）；ACT 07 CLI Console。前置 impl-05/impl-03 `ACCEPTED`。
3. **K3（ACT 08 → 09 → 11）**：ACT 08 CorrectionRequest + `run_rework_propagation`（第 62 条：不改 M4 修订状态）；ACT 09 `open_rework_review` 只重放待复核项；ACT 11 `acceptance.py`（14 项：11 PASS + 3 BLOCKED、exit 2）与 `m6-data-fields.sh`。ACT 10 已 WITHDRAWN（第 61 条）。
4. 每个 ACT 后运行该 ACT `verify` 全部与 `TDD.md` §3 回归；`git add` 只加该 ACT `commit.add` 列出的路径，一个提交。
5. 每个 ACT 完成后在 `~/tmux-agents/runs/w5h.report.md` 追加一行「- [x] ACT <id>」，并附该 ACT 的 Red/Green 原文；每组结束停下等待主 Agent 验收。

## 停手规则

遇下列任一，停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定：

- 基线任一门禁不符；`check_interfaces.py` 末行非 `fail=0` 或 exit ≠ 0，或 §4 未登记本包新类型。
- impl-05/impl-03 非 `ACCEPTED`（K2 起）。
- 上游 `run_m4`/`run_m5` 实际输出与 README §5.1 不符（字段名、artifact_type、`candidate_package`/`validation_package` 键）。
- 某个测试无法按 ACT `tests` 定义写出；contract 有两种理解；需要改 scope 外文件；需要改 `pipeline/ledger` 或 `openspec/schemas`。
- 需要伪造人工签发或把 BLOCKED 写成 PASS。
- 任一门禁变红；`m6-data-fields.sh` 不再是 11 PASS + 3 BLOCKED、exit 2。

## 最终报告（写 `~/tmux-agents/runs/w5h.report.md`）

- 各 ACT 提交 hash 与 `git show --stat --oneline <hash>`；
- 基线原文；各 ACT 的 Red 原文与 Green 的 `Ran/OK` 行；
- 各 ACT `verify` 输出（命令 + 末行）；
- `git status --short`；末行「等待主 Agent 独立验收」。
