# impl-04 · F1 实现 Prompt（ACT 00–08：M8 Dataset Compilation 首切片——证据尾链发布包）

你是执行 Agent，运行在 tmux，无人实时看屏幕。所有回复、注释、docstring、提交信息使用中文。

工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。

先完整阅读（只读）：本目录 `README.md`（§1 目标、§3 范围、§4 主 Agent 决定、§5 已固化默认、§6/§7 契约）、`ACT.yaml`、`BDD.md`、`TDD.md`、`act/00.yaml`–`act/08.yaml`、`docs/blackbox-spec-rework/G7-RULINGS.md`、`impl-02-corpus/act/03.yaml`（Ledger 事务模板）、`pipeline/corpus_compiler/step.py`（`run_m3` 事务与异常分层模板）、`pipeline/ledger/service.py`（公开方法）、`pipeline/ledger/ids.py`、`pipeline/corpus/_fixture/mini_ed01/`（`manifest.yaml`、`pages/*.json`、`anomalies.yaml`、`spans.yaml`）。

## 只允许写

- `pipeline/dataset_compiler/**`（新建，含 `shim/` 与 `tests/`）
- `openspec/acceptance/m8-span-identity.sh`（ACT 07 新建）
- `openspec/acceptance/run_all.sh`（**仅 ACT 08**，仅 20.4/20.8 两段与一个辅助函数）

其余一律禁止写入：规格正文、`openspec/schemas/**`、fixture 目录、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`HANDOFF.md`、`PLAN.md`、`SUBAGENT_TODO.md`、`G7-PLAN.md`、`G7-RULINGS.md`、任何 `ACCEPTANCE.md`、其他 work-items。不得改代码草案的函数名/返回键/检查名/artifact_type/task_id 去迁就实现。

## 台账纪律（硬性）

你是执行者，不是验收者。不得修改 `HANDOFF.md`、`PLAN.md`、`SUBAGENT_TODO.md`、任何 `ACCEPTANCE.md`、`G7-*.md`；不得在任何文件或提交信息里写「ACCEPTED」「验收通过」「主 Agent 审查」之类的结论。台账由主 Agent 写。

## 测试纪律（硬性）

- 每个 ACT 先写测试（用例名与 ACT `tests` 逐字）并运行取得 **Red 原文**，再实现；Red 原文与 Green 的 `Ran/OK` 行写进最终报告。
- 不得修改测试断言去迁就实现；不得删改已有断言。
- 只用标准库 + PyYAML + jsonschema；不新增依赖、不新增 ID 前缀、不调用模型 API。
- 测试只用 tempfile 目录；集成测试依赖真实页图时用 `skipUnless(assets_available())`，K2 起本机必须 0 skipped；合成 PNG 不得与 fixture 登记哈希同值。

## 开工前提（任一不符，停手上报）

```bash
cd /Users/jingtaiwei/Git/Public/learn_system
export LC_ALL=en_US.UTF-8
git status --short pipeline/dataset_compiler openspec/acceptance/m8-span-identity.sh   # 空
bash docs/blackbox-spec-rework/verify-T.sh | tail -1                                   # FAIL 合计: 0
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all | tail -1             # 109/109
bash openspec/schemas/verify.sh >/dev/null; echo $?                                    # 0
python3 docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py                        # D16 OK
.venv/bin/python -m unittest discover -s pipeline/ledger/tests -t . 2>&1 | tail -1     # OK
.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -t . 2>&1 | tail -1   # OK
bash openspec/acceptance/m8-span-identity.sh >/dev/null 2>&1; echo $?                  # 127（尚未创建）
ls ocr/data_work/sanche_pages/page_001.png ocr/data_work/sanche_pages/page_002.png ocr/data_work/sanche_pages/page_003.png | wc -l   # 3
grep -n 'impl-04' docs/blackbox-spec-rework/SUBAGENT_TODO.md | head -1                 # 记录现状
```

另需确认：本包新增 artifact_type（`source_asset_page`、`source_asset_register`、`source_asset_pack`、`evidence_map_pack`、`release_manifest`、`publication_package`）已由 W2-C 登记 ACT 写入 `impl-00-interfaces/INTERFACES.md` §4 临时闭集（P2/D4）。`grep -n 'source_asset_pack' docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md` 无输出 → 停手上报，不得先行实现。

## 逐步

按 `ACT.yaml` 的 K1 → K2 → K3 顺序串行：

1. **K1（ACT 00 → 01 → 02）**：纯函数。ACT 00 建包骨架、规范化 JSON、消费级别准入；ACT 01 `packs.py`（尾链子包、完整 `span_id` 键、已知缺陷、ReleaseManifest）；ACT 02 独立发布 Gate。每个 ACT 一个提交，`commit.add` / `commit.message` 逐字照 act 文件。
2. **K1 全部 Green 后进 K2（ACT 03 → 04 → 05 → 06）**：ACT 03 薄 M1 页图登记（`shim/m1_shim_source_assets.py`，D2；文件与 CLI 名显式标 `m1_shim`）；ACT 04 `resolve_m8_inputs`；ACT 05 `run_m8`；ACT 06 CLI 与失败路径。前置 impl-02 `ACCEPTED`。
3. **K2 全部 Green 后进 K3（ACT 07 → 08）**：ACT 07 `acceptance.py` 与 `openspec/acceptance/m8-span-identity.sh`（7 PASS + `mentions_mapping` BLOCKED，exit 2）；ACT 08 `run_all.sh` 20.4/20.8（永不 PASS）。
4. 每个 ACT 后运行该 ACT `verify` 全部与 `TDD.md` §3 回归；`git add` 只加该 ACT `commit.add` 列出的路径，一个提交。
5. 每个 ACT 完成后在 `~/tmux-agents/runs/<会话>.report.md` 追加一行「- [x] ACT <id>」，并附该 ACT 的 Red/Green 原文。

## 停手规则

遇下列任一，停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定：

- 基线任一门禁不符；本机缺三页页图（集成测试会 skip，但 K2 起要求 0 skipped）。
- 上游 `run_m3` 实际输出与 README §6 表不符（字段名、artifact_type、`manifest.input_artifacts` 组成）。
- 新 artifact_type 尚未入 `INTERFACES.md` §4 闭集。
- 某个测试无法按 ACT `tests` 定义写出；contract 有两种理解；需要改范围外文件。
- `run_all.sh` 存在并发写入者（P4）；任一门禁变红；`m8-span-identity.sh` 不再是 7 PASS + 1 BLOCKED、exit 2。

## 最终报告（写 `~/tmux-agents/runs/<会话>.report.md`）

- 各 ACT 提交 hash 与 `git show --stat --oneline <hash>`；
- 基线原文；各 ACT 的 Red 原文与 Green 的 `Ran/OK` 行；
- 各 ACT `verify` 输出（命令 + 末行）；
- `git status --short`；末行「等待主 Agent 独立验收」。

