# impl-03 四查审查 R1（独立审查者，W3-E 前四查）

- 审查对象：提交 `1a189ae` 的 `docs/blackbox-spec-rework/work-items/impl-03-validation/`（全部文件；经 `git diff 1a189ae HEAD` 核对与工作树一致）。
- 依据：`G7-RULINGS.md` §1 P1–P9 与 §9 第 2/6/8/9/10/12/13/17/18/19/20/21/22/23 条（工作树版，含未另提交的 §9 补全）；规格 §6.1/§7/§8/§8.1/§8.2/§11.1/§13/§13.1/§17/§17.1/§19/§19.0/§20/§22（分段读取）；`pipeline/ledger/service.py`、`store.py`、`errors.py`；`pipeline/corpus_compiler/step.py`；`pipeline/corpus/_fixture/mini_ed01/`；模板 `impl-02-corpus/`。
- 实测手段：fixture 数字用 `.venv/bin/python` 独立复算；`m3-coverage.sh`、`run_all.sh` 实跑；`$TL`/`$TC` 实跑统计用例数；`git grep quote_hash` 复测。

## 判定：REWORK

阻断 3 条、重要 1 条、建议 2 条（见发现清单）。阻断均为「执行者按包内纪律走到必停/必红」的硬矛盾，修复后可再审。

## 一、忠实性 —— 通过

- §9 逐条落地核对：第 2 条 `corpus_only` 17 修订（README §5.1、act/04，算术 1+1+1+1+1+1+5+1+1+3+1=17 ✓）；第 19 条只有 `replay.py` 可 import compiler（README §3 纪律 2、act/01、ACT.yaml、TDD §2 grep 三重约束）；第 21 条 `validation.passed` 如实等于 `gate.passed` 且下游须同时满足 succeeded + passed（README §5.3 加框注、act/05 step 10、BDD 6.2、ACT.yaml、TDD §2、ACCEPTANCE §3 五处一致）；第 22 条 G4/G5/G6 `not_evaluated` + 验收 BLOCKED、行名逐字 §19（act/05 gates/not_evaluated、act/06 四行 BLOCKED 逐字含「M4 Knowledge Extraction」「M3 Corpus Compilation」）；第 23 条只接受 succeeded StepRun 的包（act/04 D-15，含「同 stage 多包只取 succeeded」与「全失败即拒」两档）；第 12/18/20/17/13/10/8/6/9 条分别落在 D-02/D-03/D-07/D-10/D-14/D-09/D-11/D-13/D-04，与裁决表逐字对应。
- P1–P9：M4 缺席项不伪造（BLOCKED/not_evaluated）；新类型仅 `gate_results`/`validation_package` 且须 W2-C 入 §4 闭集；`schema_version "0.1.0-draft"`、不新增 schemas 文件；不改 `run_all.sh`/`m3-coverage.sh`（README §3 禁止 + §88 行影响分析）；不改 `pipeline/ledger/**`、`corpus_compiler/**`、fixture（§9 第 13 条 fixture_ingest 不改 ✓）；零模型调用；无新 ID 前缀（§9 第 8 条）。
- 规格引用行号抽核全部命中：§13:580/582、§13.1:588–608（G1 含「无未决字符」、G3 含 evidence_level 判定）、§8.2 第 3 表 366–380（9 码与 `errors.py ERROR_CODES` 逐一吻合）、§11.1:525–528、§19:877–879、§19.0:909、§22.2:978。
- README §1 实测表全部独立复算成立：230 字框 = 5 `unrecognized`（c0036/c0037/c0038/c0040/c0041）+ 225 `pending`（page_001 32、page_003 193）；lines `angle` 全 0（D-03 前提成立）；m3 `counts.batches=5`；人工事件恰 1（anomalies page_002）；`m3-coverage.sh` → `SUMMARY pass=8 fail=0 blocked=1`；s03/s04 字框拼接 ≠ 文本 2 条。唯一措辞过期项见 R3-05。
- 无超出裁决的新决定；CLI 退出码 0/1/2/3、验收脚本 0/1/2/3 自洽且沿用 impl-01/02 教训。

## 二、覆盖性 —— 通过（BDD §8 显式对齐表）

- `BDD.md` §8 给出场景 ↔ ACT tests 用例名 ↔ TDD Red/Green 行的三列对齐表，1.1–7.4 每条至少一个具名用例；对抗四场景（D-13）有 4+1 个用例；BLOCKED 行名专项用例（7.4）。
- §19.0 `m5-evidence-gate.sh` 由 ACT 06 产出：9 PASS + 5 BLOCKED、exit 2，README §1 明示返回 0 须等 M4 与 quote hash 归属落地，差距未宣称关闭；`run_all.sh` 不改且 20.4/20.8 归 impl-04（P4 无冲突）。
- fail-closed 路径（g1_frozen_bytes error → 13 skipped）、errored 路径、CLI 三出口均有用例。

## 三、可执行性 —— 发现 3 阻断、1 重要

- 通过项：act/04–05 引用的 Ledger 方法与参数全部真实（`list_checkpoints:150`、`get_step_run:121`（SELECT * 含 `request_json`/`result_json`，store.py:88–103 两列存在）、`get_revision:117`、`list_transformations:129`、`read_object:1606`、`put_run_artifact/put_artifact/seal_revision/write_checkpoint/record_transformation/register_stage_package/finish_step_run/fail_step_run` 同 impl-04 已核）；`stage_packages`（store.py:71–75）、`frozen_inputs`（119–124）表结构支持三个只读 SELECT 私有函数；`ERROR_CODES` 恰 9 码（errors.py:11–23）与 §5.5 映射一致。
- M3 实际写入对账全部成立：9 个 artifact_type 与 `corpus_compiler/step.py` 写入一致；`result_json.output_artifact_ids` 四项各型恰 1、`validation_report_ids` 恰 1；配置内容 `stage m3/tool/tool_version/batch_size/gate_profile`（step.py:78–88）；批次 Checkpoint `completed_tasks` 形状一致；`compile_structural`/`evaluate_structural` 在 step 命名空间导入（step.py:16/18），D-13 的 `mock.patch("pipeline.corpus_compiler.step.…")` 目标有效；「失败 StepRun 名下的 m3 包」可经「running 时 register → fail_step_run」合法构造，D-15 测试可写（`_live_step_run` 限 running/awaiting_human，service.py:253–260）。
- 基线实测：`$TL`=74（≥74 ✓）、`$TC`=68（≥67 ✓）、`step.py` 裸 `pass` 0、`m5-evidence-gate.sh` 不存在（exit 127 Red 成立）；ACT 时长 75/85/80/80/75/90/80 全部 ≤110。
- 阻断/重要：R3-01（阈值逐 ACT 不可达）、R3-02（fail_closed_tamper 与 D-08 A 矛盾）、R3-03（counts.findings==3 与 7 条实测发现矛盾）、R3-04（K2 目录计数错）。

## 四、独立性 —— 通过

- 依赖无环：00→01→02→03；04←03、05←04、06←05；K1 全 ACCEPTED 才开 K2，与 ACT.yaml 分组一致。
- 写范围：`pipeline/validation/**` + `m5-evidence-gate.sh` 全新建，与 impl-04（`pipeline/dataset_compiler/**`、`m8-span-identity.sh`、ACT 08 的 `run_all.sh`）及 impl-00（INTERFACES/schemas/fixture 期望产物）零交集；包内各 ACT 写文件互不重叠（act/00 commit.add 含整个 tests/ 目录，但当时仅有其文件）。
- 防同错同过：g1/g2/g3 禁 import corpus_compiler（contract + 各 act verify grep + TDD §2 grep #2，tests/replay/inputs/acceptance 的豁免各有 act 级补充判据）；`replay.py` 独占 import compiler（§9 第 19 条）；acceptance.py 不 import 内部验证器（TDD grep #3）、判定一律独立重算、不信任 run_m5 返回；acceptance 对 corpus_compiler 的引用仅限 D-13 mock 所需，与豁免一致。

## 发现清单

| 编号 | 严重度 | 位置 | 问题 | 依据 | 修改建议 |
|---|---|---|---|---|---|
| R3-01 | 阻断 | TDD.md:29–35（§1 Green 阈值）；ACCEPTANCE.md:19 | 用例数阈值逐 ACT 不可达：act/00 枚举 8<10、累计 16<26（01）、24<40（02）、48<57（03）、60<63（04）、70<75（05）、83<84（06）；补足需凭空新增 46 个未列名用例，与 act/03–06「用例名与下文逐字」及 BDD §8 映射直接冲突，act/00 Green 即触停 | act/00.yaml:60–67（8 例）、act/01.yaml:29–36（8）、act/02.yaml:26–33（8）、act/03.yaml:55–78（24）、act/04.yaml:51–62（12）、act/05.yaml:91–100（10）、act/06.yaml:54–66（13） | 按枚举数重定阈值（如 ≥8/16/24/48/60/70/83），或补列具名用例补足差额后同步 BDD §8 |
| R3-02 | 阻断 | act/06.yaml:26（fail_closed_tamper） | 「corpus_spans 改一字节 → …无 m5 StagePackage」与 act/05 设计矛盾：build_context 哈希不符不抛异常（BDD 5.3）→ g1_frozen_bytes 报 error → 13 skipped → gate 失败，但 D-08 A/§9 第 21 条规定 gate 未过仍 StepRun succeeded 并照常封存 m5 StagePackage（`validation.passed=false`）；按 act/06 原文该判定必 FAIL，m5-evidence-gate 变 exit 1，9 PASS 期望被破坏 | act/05.yaml:63–65、72–74；BDD.md:49（6.3 同场景无此说）；G7-RULINGS.md:81 | 删去「无 m5 StagePackage」，改为「m5 StagePackage 仍封存且 `validation.passed == false`、无第二个 m5 StepRun」 |
| R3-03 | 阻断 | act/05.yaml:91（test_run_m5_on_fixture_succeeds） | 「counts.findings == 3」与包内实测矛盾：README §1 表合计 7 条发现（2 unresolved_glyph + 2 unproofread_glyphs + 1 quote_hash_not_stored + 2 glyph_text_misaligned），BDD 2.1（G1 恰 4 条）+ 4.1（G3 恰 3 条）；3 只是 G3 子集，测试按此断言必失败且不得改断言 | README.md:38–42；BDD.md:14、31；act/05.yaml:24（counts.findings 键义） | 改为 `counts.findings == 7`（如需细分另断言 `counts.failures == 0`、`counts.warnings == 5`） |
| R3-04 | 重要 | TDD.md:9（§0 K2 行） | K2 基线目录计数错误：ACT 00–03 后 `pipeline/validation` 为 9 个文件 + tests/ = 10 个条目（`ls | grep -v __pycache__ | wc -l`），文档写「K2: 11（ACT 00–03 的 10 个文件 + tests）」；K2 开工核对必假，触发停手（K3: 16 复核无误） | act/00–03 scope.write 合计 9 个顶层文件 + tests/ | 改为「K2: 10（ACT 00–03 的 9 个文件 + tests）」 |
| R3-05 | 建议 | README.md:40；act/03.yaml:37 | 「全仓 git grep quote_hash 为 0」已过期：当前 HEAD 全仓 21 处（均在本仓库 work-items 文档内）；实质结论（fixture、openspec/schemas、pipeline 代码内 0 处，实测 0）成立，`quote_hash_not_stored` 判定不受影响 | 实测 `git grep -n quote_hash`（21 处，全在 docs/blackbox-spec-rework/） | 措辞改为「pipeline/ 代码、fixture 与 schemas 内 0 处」 |
| R3-06 | 建议 | PROMPT-E1.md:7；README.md:78 | P2 入闭集缺可执行探针（对照 impl-04 PROMPT-F1:45 的 grep 前置）；且 `INTERFACES.md` §4:330 的 M5 草案行仍提名任务级类型 `gate_report`，本包明确弃用（每 Validator 报告复用 `validation_report`），W2-C 登记 ACT 落地时需对账删改 | G7-RULINGS.md:70（第 10 条）、:73（第 13 条）；INTERFACES.md:330 | 增补探针（如对 §4 M5 行匹配「gate_results、validation_package 且不含 gate_report」），并在 README §5.3 注明与 §4 草案行的差异供 W2-C 对账 |

## 自检与提交

- 本文件只新增 `docs/blackbox-spec-rework/reviews/IMPL-03-REVIEW-R1.md`；未修改被审工作包、G7-RULINGS、规格、Schema、fixture、台账及 impl-00/impl-04/注解社区线文件；`git diff --check` 无输出。
