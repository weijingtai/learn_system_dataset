# impl-07 · L0 实现 Prompt（G0：M7 创世汇编薄切片——空基底 + 单个 ReviewedEditionPackage → CanonicalKnowledgeSnapshot 修订）

你是执行 Agent，运行在 tmux，无人实时看屏幕。所有回复、注释、docstring、提交信息使用中文。

工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree、不删除文件。

先完整阅读（只读）：本目录 `README.md`（**§0 首切片：创世汇编** 是唯一范围；§0.3 上游契约、§0.4 下游契约、§0.5 主 Agent 决定、§0.6 待主 Agent 裁决；§1–§8 标 `DEFERRED`，不在本波）、`ACT.yaml`、`BDD.md`（§G0）、`TDD.md`（§G0）、`act/g0-01.yaml`–`act/g0-05.yaml`、`docs/blackbox-spec-rework/G7-RULINGS.md`（§1 P1–P9、§5 impl-07、§9.12 第 61 条、§9.11 第 58 条）、`docs/blackbox-spec-rework/work-items/impl-06-review/README.md` §5.3（**上游 ReviewedEditionPackage 契约，只读，另一 Agent 正在修订**）、`docs/blackbox-spec-rework/work-items/impl-05-knowledge/`（先例与定稿样式，`PROMPT-G1.md`）、`docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md`（§2.7 M7 卡片、§4 闭集、§6 I-13）、`openspec/learn-system-blackbox-architecture.md` §6.2、§8.1、§15、§16、§17.1、§19.0、§20.5、`pipeline/ledger/service.py`（公开方法签名与返回二元组）、`pipeline/ledger/ids.py`、`pipeline/ledger/states.py`。

## 只允许写

- `pipeline/assembly/**`（新建，含 `tests/` 与 `tests/data/`）
- `openspec/acceptance/m7-assembler.sh`（G0-05 新建）

其余一律禁止写入：规格正文、`openspec/schemas/**`、`openspec/id-prefix-registry.md`、`pipeline/corpus/_fixture/**`、`openspec/acceptance/run_all.sh`、`m3-coverage.sh`、`pipeline/ledger/**`、`pipeline/review/**`、`pipeline/dataset_compiler/**`、`pipeline/orchestrator/**`、`pipeline/contract_registry/**`、`pipeline/knowledge_extraction/**`、`pipeline/validation/**`、`pipeline/corpus_compiler/**`、`HANDOFF.md`、`PLAN.md`、`SUBAGENT_TODO.md`、`G7-*.md`、任何 `ACCEPTANCE.md`、其他 work-items。不得改代码草案的函数名/返回键/检查名/artifact_type/rule_id 去迁就实现。

## 台账与人工决定纪律（硬性）

- 你只写 `pipeline/assembly/**` 与 `openspec/acceptance/m7-assembler.sh`；台账与验收记录由主 Agent 写。
- 不得在任何文件或提交信息里写「ACCEPTED」「验收通过」「主 Agent 审查」之类的结论。
- **P7/P2**：本切片无人工回路，不产出 `human_event`；合成输入标 `synthetic: true`（§9.7 第 52 条口径），不得计为真实 `expert_verified` 或任何发布依据。
- **P5**：解析上游 m6 StagePackage 及其血缘 candidate_package 时，只接受所属 StepRun `succeeded` 的包。
- **P3**：内容结构以代码草案表达 `schema_version: "0.1.0-draft"`；不新增 `openspec/schemas/` 文件、不新增 artifact_type 名。

## 测试纪律（硬性）

- 每个 ACT 先写测试（用例名与 ACT `tests` 逐字）并运行取得 **Red 原文**，再实现；Red 原文与 Green 的 `Ran/OK` 行写进最终报告。
- 不得修改测试断言去迁就实现；不得删改已有断言。
- 只用标准库 + PyYAML + jsonschema；不新增依赖、不新增 ID 前缀、不调用模型 API、不做模糊文本相似度。
- 测试只用 tempfile 目录下的临时 Ledger；`tests/data/` 只放合成输入与金标，标 `synthetic: true`。
- 回归取行统一 `2>&1 | grep -E "^(Ran|OK|FAILED)"`（G7-RULINGS §9.2 第 27 条）。

## 开工前提（任一不符，停手上报）

```bash
cd /Users/jingtaiwei/Git/Public/learn_system
export LC_ALL=en_US.UTF-8
git status --short pipeline/assembly openspec/acceptance/m7-assembler.sh   # 空
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                       # FAIL 合计: 0
bash openspec/schemas/verify.sh >/dev/null; echo $?                        # 0
python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py; echo exit=$?   # 末行 fail=0 且 exit 0（第 54 条）
bash pipeline/corpus/_fixture/mini_ed01/verify.sh >/dev/null; echo $?      # 0 或 3
.venv/bin/python -m unittest discover -s pipeline/ledger/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)"   # OK
bash openspec/acceptance/run_all.sh | tail -1                              # SUMMARY pass=2 fail=1 blocked=8
```

另需确认：

- **上游契约（§0.3）**：`impl-06-review/README.md §5.3` 的 `reviewed_edition` 键与 §0.3 表逐字一致；若另一 Agent 的修订使键名变化 → 停手上报（不得自行改契约）。
- **P2/D-0-3**：本切片只用已登记名 `canonical_snapshot`、`assembly_package`；`check_interfaces.py` 末行 `fail=0` 且 exit 0。若需新增类型名 → 停手上报，等 impl-00 登记 ACT。
- **M6 未实现**：用 `tests/data/genesis_package.json` 合成输入；`m7-assembler.sh` 保留 `BLOCKED upstream_m6_real`，本切片返回 2。

## 逐步

按 `ACT.yaml` 的 G0-01 → G0-02 → G0-03 → G0-04 → G0-05 串行；**每个 ACT 完成后停下待主 Agent 验收**，不得跨 ACT 连做。

1. **G0-01**：包骨架、`canonical.py`、`model.py`（ReviewedEditionPackage / candidate_set / Snapshot knowledge 校验）。先红后绿，`commit.add` / `commit.message` 逐字照 act 文件。
2. **G0-02**：`genesis.py` 创世汇编纯函数（`propose_genesis` / `assemble_genesis`），空基底、只走自动分支。
3. **G0-03**：`gate.py` 独立创世 Gate（不 import genesis），含篡改矩阵。
4. **G0-04**：`inputs.py`（P5 上游解析）+ `step.py`（`run_m7` 最小事务 + `begin_or_supersede`，第 58 条）+ `fixture_seed.py` + `__main__.py` + 合成输入 `tests/data/genesis_package.json`。
5. **G0-05**：`acceptance.py`（10 PASS + 6 BLOCKED）+ `tests/data/genesis_expected_knowledge.json` + `openspec/acceptance/m7-assembler.sh`（chmod 755）。

每个 ACT 后运行该 ACT `verify` 全部与 `TDD.md` §G0.3 回归；`git add` 只加该 ACT `commit.add` 列出的路径，一个提交。每个 ACT 完成后在 `~/tmux-agents/runs/w5l.report.md` 追加一行「- [x] ACT <id>」，并附该 ACT 的 Red/Green 原文；每个 ACT 结束停下等待主 Agent 验收。

## 停手规则

遇下列任一，停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定：

- 基线任一门禁不符；`check_interfaces.py` 末行非 `fail=0` 或 exit ≠ 0。
- 上游 `impl-06-review/README.md §5.3` 契约与 §0.3 不一致，或 M6 实际输出与 §0.3 不符（字段名、artifact_type、lineage）。
- 某个测试无法按 ACT `tests` 定义写出；contract 有两种理解；需要改 scope 外文件；需要改 `pipeline/ledger`、`openspec/schemas` 或共享 fixture。
- 需要伪造人工决定、或把 DEFERRED/BLOCKED 写成 PASS。
- 任一门禁变红；`m7-assembler.sh` 不再是 `SUMMARY pass=10 fail=0 blocked=6`、exit 2。

## 最终报告（写 `~/tmux-agents/runs/w5l.report.md`）

- 各 ACT 提交 hash 与 `git show --stat --oneline <hash>`；
- 基线原文；各 ACT 的 Red 原文与 Green 的 `Ran/OK` 行；
- 各 ACT `verify` 输出（命令 + 末行）；
- `git status --short`；末行「等待主 Agent 独立验收」。
