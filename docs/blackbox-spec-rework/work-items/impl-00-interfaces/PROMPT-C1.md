# impl-00 · C1 Prompt（ACT 10：INTERFACES §4 临时闭集登记与首纵切裁决对齐）

你是执行 Agent。工作目录 `/Users/jingtaiwei/Git/Public/learn_system`，分支 `codex/docs/knowledge-compilation`（HEAD 祖先必须含 `ef7f9fd` 与本提示词所在提交）。不切分支、不 stash、不 reset、不 clean、不 rebase、不 push、不 merge、不创建 worktree。所有回复、注释、docstring 使用中文。

背景：`G7-RULINGS.md` §9「impl-00 的首纵切裁剪」把 impl-00 裁到只保留 1 个 ACT：`impl-00/10`（INTERFACES §4 临时闭集登记 + 首纵切裁决对齐）。原 `act/00–09`（Schema、金标、`verify.sh` 扩项、`fixture_ingest` 灌入 m1–m8）已标 `DEFERRED`，本次不执行、不改。本 ACT 是 impl-03（M5）与 impl-04（M8）实现的前置：`gate_results`/`validation_package` 与 6 个 M8 新类型须先入 `INTERFACES.md` §4 闭集，实现方才能使用这些 artifact_type（P2）。

先完整阅读（只读）：

- `AGENTS.md`；`docs/blackbox-spec-rework/G7-RULINGS.md` §1（P1–P9）、§2（impl-04 D4）、§9（23 条）。
- `docs/blackbox-spec-rework/work-items/impl-00-interfaces/README.md`（§1、§3、§4、§5，特别是 §5.1 闭集清单与 §5.2 待裁决）、`ACT.yaml`、`act/10.yaml`、`INTERFACES.md`（全文，§2.5/§2.8/§1/§3/§5 是改写对象）、`ACCEPTANCE.md`。
- 对账（只读）：`work-items/impl-03-validation/ACT.yaml`、`act/05.yaml`；`work-items/impl-04-dataset/README.md` §4/§6/§7。

只允许写（`scope.write`，精确四个路径）：

- `docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md`
- `docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py`
- `docs/blackbox-spec-rework/work-items/impl-00-interfaces/tests/__init__.py`
- `docs/blackbox-spec-rework/work-items/impl-00-interfaces/tests/test_check_interfaces.py`

其余一切禁止写入：`openspec/schemas/**`、`pipeline/corpus/_fixture/**`、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`pipeline/validation/**`、`pipeline/dataset_compiler/**`、`openspec/acceptance/**`、规格正文、`id-prefix-registry.md`、其他 work-items，以及 `HANDOFF.md`/`PLAN.md`/`SUBAGENT_TODO.md`/`G7-PLAN.md`/`G7-RULINGS.md`。

**台账纪律（硬性）**：你是执行者，不是验收者。不得修改任何 `ACCEPTANCE.md`，不得在任何文件或提交信息里写「ACCEPTED」「验收通过」「主 Agent 审查」之类的结论。

**测试纪律（硬性）**：先写 `check_interfaces.py` 与 `tests/test_check_interfaces.py`，运行取得 Red（§4 缺 8 个新类型）再改 `INTERFACES.md`；不得为了让测试通过而放宽断言。`check_interfaces.py` 只用标准库（`pathlib`/`re`/`sys`），不 import `yaml`/`jsonschema`。

严格执行：

0. 开工前提：`git status --short docs/blackbox-spec-rework/work-items/impl-00-interfaces` 无输出（本提示词所在提交已落地）；`bash openspec/schemas/verify.sh` exit 0；`bash openspec/acceptance/run_all.sh | tail -1` 为 `SUMMARY pass=2 fail=1 blocked=8`。任一不符停手。
1. `export LC_ALL=en_US.UTF-8`。
2. 按 `act/10.yaml` 的 `tests_first`/`tests` 写 `check_interfaces.py` 与 7 个用例，运行 `python3 check_interfaces.py` 与 `unittest`，记录 Red 原文。
3. 按 `act/10.yaml` 的 `contract` A–I 改 `INTERFACES.md`：
   - §4 表新增 8 行（M5：`gate_results`/`validation_package`；薄 M1：`source_asset_page`/`source_asset_register`；M8：`source_asset_pack`/`evidence_map_pack`/`release_manifest`/`publication_package`），名称逐字取 README §5.1，状态列不得标 DEFERRED/纵切后；其余纵切后类型保留并标「纵切后」；表头下加闭集说明；顶部状态行改 `READY_FOR_REVIEW`。
   - §2.8 M8 卡片写入尾链（`knowledge_chain: not_compiled`）与首切片子包集合；§2.5 M5 卡片写入 `corpus_only`（17 个冻结修订）、`quote_sha256` 复算、`validation.passed` 与 upstream `succeeded` 双条件；§2.4/§2.6/§2.7 标「纵切后」。
   - §1.1/§1.3 写入 §9 第 13 条（`fixture_ingest.py` 不改、`reader.store.conn` 只读 SELECT 缺口清单）、第 16 条（页图字节登记进 Ledger）；§3 整节加 P3 注；§5 批次图改为「批次 0 = impl-00/10，Schema/金标/ingest 纵切后」。
   - 不改 m1–m3 的【实际】事实。
4. 运行 `act/10.yaml` 的 `verify` 全部；再跑 README §1 完成判据。
5. `git add` 只加 `commit.add` 列出的路径（`INTERFACES.md`、`check_interfaces.py`、`tests/`），按 `commit.message` 提交。一个提交。
6. 停手规则：开工前提不符；§4 闭集名称与 README §5.1 不一致；impl-03/impl-04 引用到未登记类型（`validator_report`、`gate_report` 均不得登记，见 §9.1 第 24/26 条与 README §5.2）；需要写 scope 外文件；需要改 schemas/fixture/ledger 才能通过。一律停止、不自行决定，把原始输出与 `git status --short` 交主 Agent 裁定。

最终报告：提交 hash 与 `git show --stat --oneline HEAD`；开工前提原文；Red 原文；Green 的 `I00-IF SUMMARY` 行与 `unittest` 的 `Ran/OK` 行；`verify` 各项输出；`git status --short`；以及一句「等待主 Agent 独立验收」。
