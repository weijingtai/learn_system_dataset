# T05-NEXT 推进汇报（Windows 本机）

## 一、T05f 核实（M8 构建函数接线与全栈产出）

### 1. 判据对照与核实结论
- **完成判据**：
  1. `run_m8` 以 M7 Snapshot 为输入，实际产出 KnowledgeDataPack、GraphProjectionPack 与证据链并封存进 Ledger；
  2. 有一条真实形状输入走完全栈的用例（R15）；
  3. 三个函数在非测试代码里都有调用点。
- **核实结果**：全部满足，标记为「完成」。

### 2. 实测证据
1. **非测试代码调用点**：
   - `packs.build_evidence_chain` -> `pipeline/dataset_compiler/step.py:317`
   - `packs.build_knowledge_data_pack` -> `pipeline/dataset_compiler/step.py:378`
   - `packs.build_graph_projection_pack` -> `pipeline/dataset_compiler/step.py:683`
2. **R15 全栈用例执行**：
   - 命令：`.venv/Scripts/python -m unittest pipeline/dataset_compiler/tests/test_t04b_m7_to_m8.py`
   - 输出：
```text
....................
----------------------------------------------------------------------
Ran 20 tests in 12.065s

OK
```
3. **真书全线产出核实**：
   - 真书《乾元秘旨》（`qianyuan_t04` 与 `qianyuan_t04b`）中，M8 成功产出全部三样子包，`knowledge_chain=compiled`，在验收中实测：
     - `PASS knowledge_chain 知识链闭合：2 个词条、26 条断言；2 条七段证据链逐条回指 span（I-11 绝对偏移、quote_sha256 重算一致）；无主体断言 24 条已按 §3.8 披露`
     - `PASS graph_projection GraphProjectionPack 与 KnowledgeDataPack 同源（release_id/canonical_hash/consumption_level 一致），往返无损：28 节点、2 条关系逐一可由移动端数据重建`

## 二、T18 核实与篡改探针（M5 自述门禁按 step_run_id 去重）

### 1. 修复与判据对照
- **完成判据**：
  1. `pipeline/validation/adapter_notes.py` 的 `submission_documents` 按 `step_run_id` 去重；
  2. 先写用例证明 384→12、192→6 转红再修（`test_adapter_notes.py` 中的 `RepeatedRegistrationTest`）；
  3. 不动词表、不动 error 级别、不动 `test_real_book_submission_notes_are_flagged`；
  4. 篡改探针证明破坏修复后测试精准转红；
  5. 真书账本实跑 warnings=12 errors=0。
- **核实结果**：代码已由提交 `4cbac32` 修复并完整接线；本机复核测试与篡改探针全部通过，标记为「完成」。

### 2. 实测证据与篡改试验
1. **测试回归**：
   - 命令：`.venv/Scripts/python -m unittest pipeline/validation/tests/test_adapter_notes.py`
   - 输出：
```text
...............
----------------------------------------------------------------------
Ran 15 tests in 0.392s

OK
```
2. **篡改试验（故意抹去去重逻辑）**：
   - 篡改：将 `pipeline/validation/adapter_notes.py:248` 中的 `or step_run_id in seen_step_runs` 移除。
   - 探针测试输出（精准转红）：
```text
FFF............
======================================================================
FAIL: test_distinct_step_runs_are_still_counted_separately (pipeline.validation.tests.test_adapter_notes.RepeatedRegistrationTest)
AssertionError: 384 != 12
======================================================================
FAIL: test_each_m4_step_run_is_counted_once (pipeline.validation.tests.test_adapter_notes.RepeatedRegistrationTest)
AssertionError: 192 != 6 : 同一 StepRun 重复登记 32 次只计一次
======================================================================
FAIL: test_repeated_checkpoint_does_not_change_findings (pipeline.validation.tests.test_adapter_notes.RepeatedRegistrationTest)
AssertionError: 384 != 12
----------------------------------------------------------------------
FAILED (failures=3)
```
3. **恢复代码后复测**：
   - 恢复 `or step_run_id in seen_step_runs` 后，`pipeline/validation/tests/test_adapter_notes.py` 15 条全部恢复通过；全量 `validation` 包 123 条测试全部 PASS。
4. **真书实跑结果**：
   - 在真书全线运行（`qianyuan_t04b`）中，M5 阶段披露项统计为：`warnings=12 errors=0`，与预期严格一致。

## 三、T22 修复与验证（返工传播经 pattern 的 assertion_ids 传递）

### 1. 缺陷根因与修复方案
- **缺陷表现**：`review/rework.py`、`propagation.py` 与 M6 验收的可达性闭包此前只遍历了 `evidence`、`source_refs`、`subject_entity_id`、`claim_refs`。由于 `pattern` 自身无 evidence，其证据均通过 `assertion_ids` 挂接在断言上；当断言所在 span 发生变动被返工时，`pattern` 没有被纳入可达闭包，且由于缺乏自身 evidence，`content_hash` 计算前后一致，导致其旧审核决定被错误沿用（carried），未按规范进入 `needs_review`。
- **修复方案**：
  1. `pipeline/review/propagation.py`：在 `reachable_entities` 的传递闭包中加入对 `assertion_ids` 的检查；在 `propagate` 的决策分流中，若 `target` 引用的任一断言在 `reachable_set` 中（`has_reworked_assertion`），明确进入 `needs_review`（`reason="assertion_reworked"`），阻止其被误沿用；
  2. `pipeline/review/acceptance.py`：在 `_reachable_entities` 中纳入 `patterns` 列表，并在传递闭包中加入 `assertion_ids`；
  3. `pipeline/review/tests/test_propagation.py`：新增用例 `test_t22_pattern_assertion_rework_propagates_to_pattern`。
- **提交号**：`1c8027f`。

### 2. 先红后绿与篡改探针证据
1. **测试先红**：
   - 在未改动业务代码前执行 `test_t22_pattern_assertion_rework_propagates_to_pattern`，输出明确失败：
```text
FAIL: test_t22_pattern_assertion_rework_propagates_to_pattern
AssertionError: 'pat_qizheng_000001' not found in ['as_qizheng_000001', 'sv_00000000000000000000000000000001']
```
2. **改动后转绿**：
   - 修复后复测 `test_propagation.py`：16 条用例全部 PASS（0.002s）。
   - 全量 `review` 包回归：180 条测试全部 PASS（337.459s OK）。
3. **篡改探针验证**：
   - 故意注释掉 `propagation.py` 中遍历 `assertion_ids` 的逻辑，复跑 `test_propagation.py`，测试再次精准转红（`AssertionError: 'pat_qizheng_000001' not found in ...`）；
   - 恢复代码后复测，16 条再次全绿。

## 四、20.6（T05c）与 20.9（T05d）宿主与判据查清报告

### 1. 为什么是 BLOCKED？（根因查明）

#### (1) 20.9（T05d - GraphProjectionPack 往返无损）：
- **根本原因**：宿主配置与调用方式导致缺少真实的 M7 Snapshot 输入数据！
- **机制追踪**：
  1. `openspec/acceptance/run_all.sh` 第 360 行调用 `m8_item_one "$n" publication graph_projection "..."`，依赖 `m8_prime publication`；
  2. `m8_prime` 在 `run_all.sh:72` 执行的命令是：
     `python -m pipeline.dataset_compiler.acceptance --fixture "$FIXTURE_DIR" --check publication`；
  3. 环境变量 `$FIXTURE_DIR` 默认为 `pipeline/corpus/_fixture/mini_ed01`，且**完全没有传递 `--ledger`** 参数；
  4. `pipeline.dataset_compiler.acceptance` 在未指定 `--ledger` 时，通过 `_prepare_ledger` 在临时目录中现场装配账本；
  5. 但 `_prepare_ledger` 仅执行了 M1 入库、M2 清洗与 M3 分段（无论 glyphbox 还是 offset 路线），**完全未装配或执行 M4 抽取、M6 审核与 M7 增量汇编**；
  6. 导致临时账本中没有任何 M7 Checkpoint 与 `canonical_snapshot` 修订；
  7. `run_m8` 在缺少 M7 Snapshot 时，按规范降级只产出基础的 SourceAssetPack 和 EvidenceMapPack，不产出 KnowledgeDataPack 与 GraphProjectionPack；
  8. `dataset_compiler.acceptance` 的 `_check_graph_projection` 发现缺少 `graph_projection_pack`，输出：
     `BLOCKED graph_projection 实测发布包无 graph_projection_pack（子包: ['evidence_map_pack', 'source_asset_pack']）；run_m8 尚未产出 GraphProjectionPack（TODO.md T05d）`；
  9. `run_all.sh 20.9` 捕获到这一行，遂将 20.9 判定为 BLOCKED。
- **判据是否已写？**
  - **已完整实现**！`pipeline/dataset_compiler/acceptance.py:940-1030` 的 `_verify_graph_projection` 包含了：
    ① 同源标识一致性比对（`release_id`、`canonical_hash`、`consumption_level` 跨发布包、清单、图投影、知识包三者一致）；
    ② 图结构形状比对（节点按 `node_id` 升序去重、边按三元组升序去重、无独立边 ID）；
    ③ 往返无损比对（由 KnowledgeDataPack 独立反向重建应有的概念、断言、格局、流派视图节点，以及 `has_assertion`、`belongs_to_concept` 等关系边，与图投影逐一严格相等）。
  - **实证**：在跑通 M1→M8 全线的真书账本 `var/ledgers/qianyuan_t04b` 上运行只读验收时，该判据直接输出：
    `PASS graph_projection GraphProjectionPack 与 KnowledgeDataPack 同源（release_id/canonical_hash/consumption_level 一致），往返无损：28 节点、2 条关系逐一可由移动端数据重建`。

#### (2) 20.6（T05c - Pattern 逐项补全与 not_captured）：
- **根本原因**：**两层叠加——既缺全线输入数据，又缺专项判据代码**！
- **机制追踪**：
  1. **第一层（数据/宿主缺失）**：同 20.9，在现行无 `--ledger` 装配下，无 M7 Snapshot，`knowledge_chain` 为 `not_compiled`，输出 BLOCKED；
  2. **第二层（判据未实现）**：即便在拥有完整 M7 Snapshot 的账本（如真书 `var/ledgers/qianyuan_t04b`）上，`knowledge_chain` 成功产出并评为 PASS，`run_all.sh:318-322` 明确写着守卫代码：
     ```bash
     case "$(m8_lines publication | grep -m1 '^[A-Z_]* knowledge_chain ')" in
       "PASS knowledge_chain "*) fail_line "$n" "判据未实现" "KnowledgeDataPack 已产出，但 not_captured 逐项补全的专项判据尚未实现（TODO.md T05c）" ;;
       *) m8_item_one "$n" publication knowledge_chain "-" ;;
     esac
     ```
     即当前若 `knowledge_chain` 为 PASS，`run_all.sh 20.6` 会直接抛出 `FAIL 20.6 判据未实现`。
- **判据缺什么？**
  - 《黑箱架构规格》§4:77 与 §20.6 明确要求：“Pattern 名称、规则、解释和出处可逐项补全；`not_captured` 不被误判为不存在。”
  - 当前 `pipeline/dataset_compiler/acceptance.py` 的 `_verify_knowledge_chain` 仅检查了词条、断言与证据链是否闭合，**从未检查**：
    ① Pattern 对象的 `interpretation_status` 与 `recognition_rule_status` 是否正确承载 `not_captured` 语义；
    ② 在没有录入解释或识别规则时，`not_captured` 不被视为该 Pattern 不存在或被丢弃；
    ③ 补全机制：当后续版次或增量阶段录入了解释（`interpretation`）或规则时，其状态能由 `not_captured` 正确更新为 `captured`，且名称、规则、解释与出处能逐项完备补齐并在 KnowledgeDataPack 中体现。

---

### 2. 测试宿主候选方案分析

| 候选方案 | 实现路径 | 优势 | 局限/成本 |
|---|---|---|---|
| **方案 A：真书账本（`var/ledgers/qianyuan_t04b`）** | 在 `run_all.sh` 传入 `--ledger var/ledgers/qianyuan_t04b --fixture .../qianyuan_ed01_text` | ① 零伪造，全真古籍全线加工数据；<br>② 20.9 现有判据实测立即可转 PASS；<br>③ 真实 Pattern（去官留煞、贪合忘煞）恰处于出处已验、规则 `not_captured` 的典型状态，与 §4:77 业务场景完全吻合。 | `var/` 目录被 `.gitignore` 忽略，未克隆/无真书账本的机器（如云端 CI）会报 `BLOCKED 宿主缺失`（同 20.5）。 |
| **方案 B：夹具扩展（`mini_release01` 或轻量 sqlite 夹具）** | 在 `pipeline/corpus/_fixture/` 补充带 M7 Snapshot 的轻量夹具，或扩展 `_prepare_ledger` 允许直接封存 M7 Snapshot | ① 完全自包含，不依赖 Git 外的 `var/` 目录；<br>② 任何干净环境 clone 后均可跑通；<br>③ 严格符合 §20 开头「统一验收宿主为 `_fixture`」的字面要求。 | 需要构造合成夹具数据并维护其多 stage 规范性；不如真书数据真实。 |
| **方案 C：双轨自适应（推荐方案）** | `run_all.sh` 优先探测是否存在本地全线账本（如 `var/ledgers/qianyuan_t04b` 或 `$LEDGER_PATH`）；存在则走真书全栈验，不存在则报宿主缺失 BLOCKED | 兼顾端到端验证的真实度，又保持规格框架对缺失宿主 fail-closed 的纪律性。 | 需要在 `run_all.sh` 明确宿主探测与环境变量契约。 |

---

### 3. 20.6（T05c）需要实现的专项判据清单

待用户拍板宿主方案后，T05c 将实现如下检查项：
1. **`not_captured` 状态合法性与未误判存在性**：
   - 检查 Snapshot/Publication 中 Pattern 的 `recognition_rule_status` 与 `interpretation_status` 严格处于 `{"not_captured", "captured"}` 闭集；
   - 证明 `not_captured` 不被误判为不存在：即使 Pattern 的规则或解释为 `not_captured`，该 Pattern 仍作为合法主体生成 `KnowledgeEntry`（如 `pat_qizheng_000001` 生成 `ent_...` 词条，未被遗弃）。
2. **四要素逐项补全能力**：
   - **名称（Name）**：非空字符串，映射到词条 `title`；
   - **出处（Provenance/Evidence）**：Pattern 自身 `provenance` 或关联断言的证据链可完全追溯；
   - **规则（RecognitionRule）**：未录入时列表为空且状态为 `not_captured`；录入后状态置 `captured` 且规则有效；
   - **解释（Interpretation）**：未录入时为 None 且状态为 `not_captured`；录入后状态置 `captured` 且解释有效。
3. **演进稳定性**：
   - 补全过程保持稳定 `pattern_id` 与既有断言引用一致性。
