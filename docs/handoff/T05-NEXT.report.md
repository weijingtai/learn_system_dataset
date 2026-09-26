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
