# impl-02：M3 Corpus Compilation（§11）结构层首切片

状态：`REVIEWING`（J1 `ACCEPTED`；J2 独立验收发现 5 处缺陷，返工 ACT 05 / `PROMPT-J3.md` 待派发）

## 1. 目标

在 `pipeline/corpus_compiler/` 落地规格 §11 的 M3 **结构层**：从 Artifact Ledger 中已封存的 M1 来源清单与 M2 OCR 页读取冻结输入，确定性地编译 StructuralSpan（一行 OCR = 一个 Span）、SourceAnchor（`glyphbox_level`：页、图像哈希、行框、逐字字框）、批次与每批 StageCheckpoint、CoverageReport 和 m3 StagePackage，并以独立实现的结构 Gate 判定全页覆盖、无缺口、无重叠、严格 offset、拼接等于原文、异常页受控排除。

完成判据（本批唯一的「做完」定义）：

```bash
bash openspec/acceptance/m3-coverage.sh; echo exit=$?
# 期望：8 行 PASS + 1 行 BLOCKED semantic_layer + SUMMARY pass=8 fail=0 blocked=1；exit=2
bash openspec/acceptance/run_all.sh | tail -1     # 仍为 SUMMARY pass=2 fail=1 blocked=8（本批不改 run_all.sh）
```

`m3-coverage.sh` 是规格 §19.0 已登记的「M3 整书漏编/无双层锚点」差距判据（修复后应 exit 0）。本批只关闭结构层，语义层未做，所以它返回 **2**（无 FAIL、有 BLOCKED），差距仍标记为未关闭。返回 0 必须等语义层落地。

## 2. 依据（只读来源）

- 规格 §7（Module 只读冻结输入）、§8.1（`ss_` 格式）、§10.1（`known_unrecognizable` 必须附证据、`deferred` 阻断）、§11（M3 链路与 Gate）、§11.1（`glyphbox_level`）、§17/§17.1（事务序列、每 task 一个 Checkpoint）、§19.0（`m3-coverage.sh`）、§22.1（首纵切宿主）
- `pipeline/ledger/`（impl-01 已验收的服务 API；不改其行为）
- `pipeline/corpus/_fixture/mini_ed01/`：`manifest.yaml`、`pages/*.json`、`anomalies.yaml`、`spans.yaml`（金标，sha256 `ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef`）、`source/transcript_v1.md`、`expected/m3.stage_package.yaml`
- `pipeline/corpus/_fixture/mini_ed01/tools/build_fixture.py` 的 `build_spans`/`dump_yaml`（只作规则参照，生产代码**不得 import** fixture 工具）

## 3. 范围

写：`docs/blackbox-spec-rework/work-items/g4-r3/check_d16.py`（ACT 00，只改 R5）、`pipeline/corpus_compiler/**`（新建）、`pipeline/ledger/fixture_ingest.py` 与 `pipeline/ledger/tests/test_ingest.py`（ACT 03，只加 `stages` 参数与一个测试）、`openspec/acceptance/m3-coverage.sh`（ACT 04 新建）。

禁止：改 `openspec/acceptance/run_all.sh`、规格正文、`openspec/schemas/**`、fixture 目录、`pipeline/ledger/` 除上述两文件外的任何文件、`PLAN.md`；新增依赖；新增 ID 前缀；生产代码读 fixture 路径或工作目录文件（只读 Ledger 冻结修订）；调用任何模型 API。

## 4. 主 Agent 决定（执行者不重议）

1. **只做结构层**。SemanticSpan（§11 第 2–5 条：双模型边界提议、分歧人工裁决）本批不做；配置修订写 `gate_profile: structural_only`，校验报告写 `semantic: not_evaluated`；`m3-coverage.sh` 的 `semantic_layer` 恒为 BLOCKED，行名「M3 Corpus Compilation」逐字属 §19 第一列。M4 未实现，不存在误消费风险；语义层落地时再把 `gate_profile` 升级。
2. **结构切段规则**（与金标一致）：每个非排除页按 OCR `lines` 顺序一行一个 Span；页内文本块 = 行文本以 `"\n"` 连接，offset 相对页块、`end` 不含；批次按页内每 `batch_size`（默认 10）行切一组，批号跨页全局递增 `<work>_b<3位>`；`span_id = ss_<work>_ed<NN>_p<4位页号>_s<2位行序>`。
3. **排除页**：`known_unrecognizable` 且 0 行且有人工事件证据 → 排除并记入 `excluded_pages`；`deferred` → 拒绝编译；有文字行却无 Span、0 行却无终态 → 失败（漏编/裸标）。
4. **输入解析**：M3 的冻结输入 = M2 阶段输出 `ocr_page_set` 修订 + M1 来源清单（`manifest.yaml`）修订 + 各页 `ocr_page` 修订 + M2 人工事件修订；通过 Ledger 读接口从 m1/m2 Checkpoint 链与 Transformation 解析，不读文件路径。每页修订哈希必须等于 `ocr_page_set` 内容里登记的哈希。
5. **Gate 独立实现**：`gate.py` 不得 import `compiler.py`，从页 JSON 重新计算页块与字框，防止编译器与判定同错同过。
6. **金标比对**：Ledger 中 `corpus_spans` 修订字节必须与 fixture `spans.yaml` 逐字节相同；序列化规则照抄 `build_fixture.dump_yaml`（私有 Dumper，不改全局 `SafeDumper`）。
7. **退出码纪律**（impl-01 ACT 06 教训）：`acceptance.py` 只在「fixture 不存在或缺 yaml/jsonschema」时返回 3；准备/运行/判定抛异常一律 FAIL 退出 1。`m3-coverage.sh` 永远调用仓库内规范 fixture `verify.sh`，不执行被验目录自带脚本（D-18 教训）。
8. 本批不改 `run_all.sh`：§20 没有任何一条会因 M3 结构层单独落地而由 BLOCKED 变 PASS（20.1 缺 Orchestrator，20.4 缺 M8）。
9. 分两轮派发：J1 = ACT 00–02（检查脚本、纯函数编译器、独立 Gate），J2 = ACT 03–04（Ledger 集成、验收脚本）。

## 5. 目录（落地后）

```text
pipeline/corpus_compiler/
  __init__.py        M3_TOOL / M3_TOOL_VERSION
  errors.py          CompileRefused
  serialize.py       dump_yaml（与金标同规则，私有 Dumper）
  compiler.py        compile_structural（纯函数）
  gate.py            evaluate_structural（纯函数，不依赖 compiler）
  inputs.py          resolve_m3_inputs（Ledger 读接口）
  step.py            run_m3（Ledger 写路径，§17 事务序列）
  __main__.py        python -m pipeline.corpus_compiler
  acceptance.py      m3-coverage 九项判定
  tests/             test_compiler.py test_gate.py test_step.py test_acceptance.py
openspec/acceptance/m3-coverage.sh
```
