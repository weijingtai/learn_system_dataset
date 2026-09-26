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
