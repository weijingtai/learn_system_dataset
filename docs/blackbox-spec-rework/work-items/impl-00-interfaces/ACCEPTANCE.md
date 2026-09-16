# ACCEPTANCE：impl-00 跨模块接口契约（首纵切裁剪后）

状态：`READY_FOR_REVIEW`——W2-C1 定稿 2026-09-12，依 `G7-RULINGS.md` §9 裁剪；未经实现、未经主 Agent 验收。首纵切保留 ACT 1 个（`impl-00/10`），`act/00–09` 全部 `DEFERRED`。

## 0. 定稿审查（主 Agent 四查，待执行）

- **忠实性**：README §4 的 17 条逐条对应 `G7-RULINGS.md` §9 第 1–17 条；首纵切只保留 §9「两类 ACT」中的 (a)，(b) 因无引用不做；`act/00–09` 状态、写范围、依据均未改语义，只加 `status: DEFERRED` 并在 `ACT.yaml` 移出 `executor_groups`。
- **覆盖性**：`impl-00/10` 覆盖 §2 D4 的 6 个 M8 新类型与 §9 第 10 条的 `gate_results`/`validation_package`；`INTERFACES.md` 其余章节的同步点（M8 尾链、M5 `corpus_only`、§9 第 13/16/21 条）逐条写入 `act/10.yaml` 的 contract A–I。
- **可执行性**：`act/10.yaml` 有 scope.write、tests_first、tests（`check_interfaces.py` 的 IF01–IF18 检查名与 8 个用例名）、contract、verify（精确命令与期望）、commit；Red 可复现（§4 缺 8 个类型即 FAIL）。
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

- `python3 .../check_interfaces.py` → exit 0，末行 `fail=0` 且所需类型 PASS 行存在（第 54 条，不写死 pass 总数）；`unittest` 8 用例 OK。
- `bash openspec/schemas/verify.sh` → 0（未改 schemas）；`run_all.sh` → `SUMMARY pass=2 fail=1 blocked=8`（未改 acceptance）。
- `git status --short openspec/schemas pipeline/corpus/_fixture pipeline/ledger` 为空；只 add `commit.add` 路径；无 `__pycache__`；`git diff --check` 通过。

## 3. 语义与质量审查（主 Agent）

- `INTERFACES.md` §4 闭集与 README §5.1 逐字一致；8 个新类型行状态列无 DEFERRED/纵切后；表内无重复类型名。
- M8 卡片写清尾链四段与 `knowledge_chain: "not_compiled"`；M5 卡片写清 `corpus_only`、17 个冻结修订、`quote_sha256` 复算、`validation.passed` + 上游 `succeeded` 双条件。
- §9 第 13 条只读 SELECT 缺口清单（`frozen_inputs`/`artifacts.artifact_type`/`stage_packages`/按 `step_run_id` 取 sealed stage_package）与 README §5.2 一致；第 16 条页图字节登记进 Ledger 写明。
- 执行方未越权：不改 `ACCEPTANCE.md`，不写结论性措辞；`validator_report`/`gate_report` 未登记（§9.1 第 24/26 条）。
- 独立复算：`check_interfaces.py` 不信任 `INTERFACES.md` 的自述，按行解析 §4 表逐项判定。

## 4. 结论

定稿轮交付：`impl-00` 状态 `READY_FOR_REVIEW`；首纵切保留 ACT 1 个（`impl-00/10`，文档登记 ACT）；`DEFERRED` ACT 10 个（`impl-00/00–09`），文件内容保留。派发 `impl-00/10` 后按其报告独立验收，结论回填 §5。

## 5. 验收记录由主 Agent 填写

### 5.1 act/10（2026-09-12，主 Agent 独立验收，`git archive ea90ca8` 干净树）

执行者：tmux 中的 cmd（DeepSeek V4.1 Flash），先按 G7-RULINGS §9.1 第 24–26 条修订 act/10（`d19589b`），再执行（`ea90ca8`）。

- 范围：`ea90ca8` 恰为 `INTERFACES.md`、`check_interfaces.py`、`tests/__init__.py`、`tests/test_check_interfaces.py` 4 文件；`openspec/schemas`、fixture、`pipeline/ledger` 未动。
- 复验：`check_interfaces.py` 18 PASS、exit 0；`unittest` 8 OK；§4 表内 `gate_report`/`validator_report` 0 处。矩阵外篡改：副本删去含 `release_manifest` 的 §4 行 → `FAIL IF01 数据行=14`、`FAIL IF06 source_asset_pack 出现 0 次`，检查器能拦截漏登记。
- 执行方报告的 `schemas/verify.sh` 0、`run_all.sh` `pass=2 fail=1 blocked=8` 与主 Agent 前序门禁一致。

act/10 `ACCEPTED`。impl-00 其余 10 个 ACT 为 `DEFERRED`（纵切后）。

### 5.2 act/12（2026-09-12，主 Agent 独立验收，`git archive b8db05d` 干净树）

执行者：tmux 中的 cmd（DeepSeek V4.1 Flash），会话 `w4g`。起草 `6cd4379`/`3f32700`，审查 R1 REWORK `b401c61` → 返工 `a42259f` → R2 READY `b7c3788`；裁定 47、49、51、54、55。

- 范围：`b8db05d` 恰为 `INTERFACES.md`、`check_interfaces.py`、`tests/test_check_interfaces.py` 3 文件。
- Red（执行方原文）：检查器 `pass=19 fail=5`（IF11、IF19–IF21、IF24），unittest 13 例中 3 例失败。
- 复验：`check_interfaces.py` 末行 `I00-IF SUMMARY pass=24 fail=0`、exit 0；unittest 13 OK；INTERFACES 中旧 M4 名（`candidate_batch`/`model_run`/`candidate_diff_report`）0 处、`char_start`/`char_end` 0 处；§4 M4 行 5 条（`candidate_submission`、`candidate_lane_set`、`dispute_queue`、`candidate_set`、`candidate_package`）。矩阵外篡改：删去 `dispute_queue` 的 §4 行 → `FAIL IF11`、`FAIL IF21`、exit 1。

act/12 `ACCEPTED`。act/05（m4 金标）执行中。

### 5.3 act/05 m4 金标（2026-09-12，主 Agent 独立验收，`git archive 7d805e6` 干净树）

执行者：tmux 中的 cmd（DeepSeek V4.1 Flash），会话 `w4g`；独占 fixture ACT，不由 impl-05 实现方生成（第 48 条）。

- 范围：`7d805e6` 恰为 `mini_ed01/m4/`（README、SHA256SUMS、build_expected_m4.py、candidate_set.yaml、ruling_m4_d001.yaml、三件提交件）、`expected/m4.stage_package.yaml`、`verify.sh` 共 10 文件；m1–m3 期望包、`spans.yaml`、`manifest.yaml`、`pages/`、`tools/`、`anomalies.yaml` 变更 0；`spans.yaml` sha256 仍 `ec6d77b9…`。
- Red（执行方原文）：`verify.sh` 扩展后生成前 5 项 FAIL、exit 1。
- 复验：`verify.sh` 11 PASS、`FIXTURE OK`、exit 0；生成器两次输出相同；`shasum -a 256 -c m4/SHA256SUMS` 0；`ruling_m4_d001.yaml` 含 `synthetic_fixture: true`（第 52 条）；生成器中 `knowledge_extraction`、`uuid/time/random` 仅出现在「不 import / 无」声明的文档字符串。四件金标与 impl-05 README 附录 A 逐字相同（执行方逐字比对 IDENTICAL×4，复审 S1）。矩阵外篡改：副本 `candidate_set.yaml` 改一字节 → `FAIL expected_hash`、`FAIL m4_sha256sums`、exit 1。
- 下游不受影响：`m3-coverage.sh`、`m5-evidence-gate.sh`、`m8-span-identity.sh` 均 exit 2；`run_all.sh` `pass=2 fail=1 blocked=8`；`schemas/verify.sh` 0；`check_interfaces.py` 24 PASS。

act/05 `ACCEPTED`。W4G 组完成。

### 5.4 act/13 M6 闭集登记（2026-09-13，主 Agent 独立验收，`git archive 573c3fb` 干净树）

执行者：tmux 中的 cmd（DeepSeek V4.1 Flash），会话 `w5x`。起草 `950349b`/`af17496`，审查 R1 → R2 READY `6f2d41e`；依据 impl-06 定稿与裁定 61、67–69。

- 范围：`573c3fb` 恰为 `INTERFACES.md`、`check_interfaces.py`、`tests/test_check_interfaces.py` 3 文件；`openspec/schemas`、`pipeline/corpus/_fixture`、`pipeline/ledger` 变更 0。
- Red（执行方原文）：检查器 `I00-IF SUMMARY pass=27 fail=2`（IF29 出现 `correction_request` 等），unittest 18 例中 `test_summary_line_format` 失败。
- 复验：`check_interfaces.py` 末行 `I00-IF SUMMARY pass=29 fail=0`、exit 0，IF25–IF29 五个 PASS 行齐（第 54 条只认 `fail=0`）；unittest `Ran 18 tests` OK；§4 `| M6 ` 行 4 条（`review_queue`、`reviewed_edition`、`reviewed_edition_package`、`rework_impact_report`），M6 行含 `correction_request` 0 处（D-10 归 `human_event`）。
- 旧检查未削弱：被删行只有模块/函数 docstring 的「IF01–IF24」字样与 `for token in REQUIRED_TYPES + M4_TYPES:`，后者替换为 `REQUIRED_TYPES + M4_TYPES + M6_TYPES`（扩大覆盖）；测试文件无删行。
- 矩阵外篡改（副本）：T1 删 M6 `review_queue` 行 → `FAIL IF11`、`FAIL IF25`、exit 1；T2 复制 M6 行改名 `correction_request` → `FAIL IF29`、exit 1；T3 删 M4 `candidate_set` 行 → `FAIL IF11`、`FAIL IF22`、exit 1（旧检查仍有效）。
- 下游不受影响：`schemas/verify.sh` 0；`verify-T.sh` `FAIL 合计: 0`；fixture `verify.sh` 0；`run_all.sh` `pass=2 fail=1 blocked=8`。

act/13 `ACCEPTED`。impl-06 实现的闭集前提已满足。

### 5.5 act/14 M2 电子文本闭集与片段 ID 登记（2026-09-15，主 Agent 独立验收，`git archive ec8c3a8` 干净树）

执行者：tmux + OpenCode（MiMo V2.5 Free，会话 `oc71`；`opencode-go/deepseek-v4.1-flash` 需账号 opt-in 不可用，按用户决定改用 MiMo）。起草 `b90e3de` → 主 Agent 审出数字矛盾 → 改正 `6e19b9b` → 执行 `c6bcd9f` → 主 Agent 验收发现 IF35 检查错文件 → 返工 `ec8c3a8`。

- 范围：`c6bcd9f` 为 `INTERFACES.md`、`check_interfaces.py`、`tests/test_check_interfaces.py`、`openspec/id-prefix-registry.md`；`ec8c3a8` 为前三者中的三文件；`openspec/schemas`、`pipeline/**`、fixture、`run_all.sh` 改动 0。
- Red：执行方原文 `I00-IF SUMMARY pass=28 fail=8`、`Ran 25 tests FAILED (failures=3)`；**返工 Red 由主 Agent 独立复现**（`c6bcd9f` 树叠加 `ec8c3a8` 的测试文件 → `test_ss_offset_form_missing_fails` `AssertionError: 'PASS' != 'FAIL'`）。
- 复验（干净树）：`check_interfaces.py` 末行 `I00-IF SUMMARY pass=36 fail=0`、exit 0，IF30–IF36 七个 PASS 行（第 54 条只认 `fail=0`）；unittest `Ran 25` OK；§4 `| M2 ` 行 5 条（旧 OCR 合并行 1 + 新增 4，act/14 原写「≥ 6」已改为 ≥ 5）；登记册含 `sem_`（§3.6）与 `ss_` 偏移形态 `o<NNNNNNN>`（§3.1）。
- 矩阵外篡改五组全部命中：T1 删 §4 `raw_text` 行 → `FAIL IF11`+`FAIL IF30`；T2 删 `finding_id` 键集 → `FAIL IF11`+`IF33`+`IF34`；T3 删登记册 `o<NNNNNNN>` → `FAIL IF35`（**返工前此组不命中，是本次返工的原因**：IF35 原判 INTERFACES 正文而非登记册）；T4 删登记册 `sem_` → `FAIL IF36`；T5 删 M6 `review_queue` 行 → `FAIL IF11`+`IF25`（旧检查仍有效）。
- 回归门禁：`schemas/verify.sh` 0；`verify-T.sh` `FAIL 合计: 0`；fixture `verify.sh` 0；`run_all.sh` `pass=2 fail=1 blocked=8`。
- 执行方纪律问题（记录，不影响本次结论）：两次回报缺证据——阶段 B 未贴 `grep -c '^| M2 '` 的不达标输出（判据本身写错），返工后未写回报段。已重申「每条 verify 贴真实输出、不达标停手上报、阶段标题逐字」。

act/14 `ACCEPTED`。W7 步骤 7.1 完成，7.2（impl-09 M1+M2 电子文本）可派发。
