# BDD：impl-10 M3 语义层

fixture 场景固定（ACT 00 手写录制）：两个窗口
- `sanche_w001` = `ss_sanche_ed01_p0001_s04`「三辰通載三十卷宋錢如璧撰據静嘉堂藏」：A、B 都切成 `[0,7) [7,12) [12,17)`（理由不同）→ 一致采纳
- `sanche_w002` = `ss_sanche_ed01_p0003_s13`「論星曜合照命宮論星曜對照命宮」：A 切 `[0,7) [7,14)`，B 给 `[0,14)` → 分歧 → 人工选 `proposal_a`

期望：46 条 SemanticSpan（page_001 6 条，page_003 40 条），glyphbox_level 42 / offset_level 4，窗口 2、分歧 1、人工裁决 1，m3 Checkpoint 10 个。

## 0. 语义金标宿主（ACT 00）

- 0.1 Given `mini_ed01_semantic`，When 跑其 `verify.sh`，Then 全部 PASS、末行 `SEMANTIC FIXTURE OK`、exit 0。
- 0.2 Given 删掉生成物后重跑生成器，Then 与仓库内文件逐字节相同。
- 0.3 Given 副本里 `recordings.yaml` 的 `synthetic` 改成 false、某条 `window_text_sha256` 改一个字符、`human_decisions.yaml` 裁决了非分歧窗口、`semantic_spans.yaml` 改一个字，或 `mini_ed01/spans.yaml` 的钉住哈希不符，Then 对应检查 FAIL、exit 1。

## 1. Proposer 与提议解析（ACT 01）

- 1.1 Given 回放录制，When A、B 对同一窗口 `propose`，Then 返回字节等于录制 `response_text`，`model_id` 分别为 `replay_model_a`/`replay_model_b`。
- 1.2 Given B 的请求字节，Then 不含 A 的响应内容、不含其他窗口原文（初次互不可见，§12.2）。
- 1.3 Given 录制缺该窗口，Then `RecordingMiss`；录制 `synthetic` 不为 true、`template_id` 不符、键重复，Then `RecordingSetInvalid`。
- 1.4 Given 未设 `LEARN_SYSTEM_ALLOW_MODEL_CALLS=1`，When 构造 `LiveProposer`，Then `ModelCallDisabled`；设了之后调用 `propose`，Then 仍抛 `ModelCallDisabled`；整个过程没有任何 socket 连接。
- 1.5 Given 响应非 JSON、缺 `segments`、offset 为 bool/负数/越界、有缺口、有重叠、有空片段，Then `parse_proposal` 返回 `valid: false` 并给出对应 `error`；响应里带的 `text` 字段被忽略，片段原文由程序截取。
- 1.6 Given 两份合法且边界相同的提议，Then `agreed`（理由不同不影响）；边界不同，Then `disputed/boundary_mismatch`；任一非法，Then `disputed/proposal_invalid`。

## 2. 规则、锚点、裁决合成（ACT 02）

- 2.1 Given fixture 结构 Span、`model_min_chars=12`，Then 恰好选出 `sanche_w001`、`sanche_w002` 两个窗口。
- 2.2 Given 两个窗口的比较结果与 `human_decisions.yaml`，When `compile_semantic`，Then 序列化字节 == `semantic_spans.yaml`，两次运行字节相同。
- 2.3 Given `p0001_s03`、`p0001_s04`，Then 其语义片段为 `offset_level`、`glyphs: []`；`p0003_s13` 拆出的两片为 `glyphbox_level`，glyph 分别是该行非空字框的第 0–6 个、第 7–13 个。
- 2.4 Given 分歧窗口没有裁决，Then `DisputesUnresolved`；裁决了一致窗口、`choice` 非法、`custom` 片段不铺满、`proposal_b` 却给出 A 的片段、`decision_type` 不在八类、`reason` 为空，Then `DecisionRejected`。

## 3. 独立语义 Gate（ACT 03）

- 3.1 Given 金标语义文档与原始录制、裁决，Then 九项检查全过，`semantic: passed`。
- 3.2 Given 删一片、两片重叠、改 offset、改文字、改 `quote_sha256`、改 `structural_refs`、窗口外一行拆两片、一致窗口的边界被改、分歧窗口无裁决或片段与裁决不符、把 offset_level 改成 glyphbox_level、改 glyph、重复 ID、序号跳号、表头计数错，Then 每种篡改都让指定检查失败，Gate 为 `failed`。
- 3.3 Gate 不 import `compiler`、`serialize` 及语义子包的 `rules/proposals/proposer/reconcile/anchors/assemble`。

## 4. Ledger 集成到人工队列（ACT 04）

- 4.1 Given Ledger 只灌入 m1、m2，When `run_m3_full`（回放 A/B），Then StepRun `awaiting_human`，返回 `resume_token`、`disputed_window_ids == ["sanche_w002"]`；结构产物 `corpus_spans` 字节 == 金标；已写 8 个 m3 Checkpoint（5 批次 + `semantic_rules` + 2 窗口）；`model_request`/`model_response`/`boundary_proposal` 各 4 个；`propose_boundaries` Transformation 4 条且带 `model_ref`。
- 4.2 Given 录制把 w002 的 B 改成与 A 相同，Then 不进入人工队列，直接 succeeded（无分歧路径）。
- 4.3 Given M3 已封存、M3 有进行中的 StepRun、A/B `model_id` 相同、传入 `LiveProposer`，Then begin 前拒绝，Ledger 无新增写入。
- 4.4 Given 录制缺 w001 的 B，Then StepRun `failed`、`failed_check == "proposer"`、失败报告封存。
- 4.5 Given 冻结输入对象被篡改，Then `failed_check == "input_contract"`。

## 5. 人工裁决、恢复与封存（ACT 05）

- 5.1 Given 4.1 的状态，When 按 `human_decisions.yaml` 调 `submit_boundary_decision`，Then 封存一个 `human_event`，`record_human_event` 以 `review_source_fidelity` 登记，并立即写第 9 个 Checkpoint（`human_decisions` 含该事件）；token 不被消费。
- 5.2 When `resume_m3_full`，Then StepRun succeeded；`semantic_spans` 字节 == 金标；m3 StagePackage 过 Schema，`gate_profile == structural_and_semantic`、`counts` 为 43/5/46/2/1/1；共 10 个 Checkpoint；`reconcile_semantic_spans` 的人工事件 == 该裁决。
- 5.3 Given 分歧未裁决就恢复，Then `DisputesUnresolved`，token 仍有效，StepRun 仍 `awaiting_human`。
- 5.4 Given 错误 token、同一窗口重复裁决、裁决非分歧窗口、恢复后再次恢复，Then 分别拒绝，Ledger 状态不变。
- 5.5 Given 恢复时冻结输入被篡改、审核队列对象被篡改、语义 Gate 失败（patch 合成结果删一片），Then StepRun `failed`，检查名分别为 `resume_contract`、`resume_contract`、`semantic_gate`，不产出 m3 StagePackage。
- 5.6 Given 另开一个 Python 进程执行 `decide`、`resume`，Then 结果与同进程相同（恢复只依赖 Ledger）。
- 5.7 CLI：`run` 有分歧时 exit 4，末行以 `M3S AWAITING` 开头；`decide` exit 0；`resume` exit 0，末行以 `M3S OK` 开头；`--live` exit 2，末行以 `M3S REFUSED ModelCallDisabled` 开头。

## 6. 验收（ACT 06）

- 6.1 Given mini_ed01 + mini_ed01_semantic，When `m3-coverage.sh`，Then 9 行 PASS、`SUMMARY pass=9 fail=0 blocked=0`、exit 0。
- 6.2 Given 不传 `--semantic-fixture`，Then 仍是 8 PASS + BLOCKED `semantic_layer`（新说明文字）、exit 2。
- 6.3 Given 语义金标副本改一个字（数据）并把副本 `verify.sh` 换成假脚本，Then `FAIL semantic_fixture_host`、exit 1。
- 6.4 Given 准备阶段 `run_m3_full` 抛异常，Then `FAIL semantic_layer 宿主准备失败: …`、exit 1；语义金标目录缺 `recordings.yaml`，Then exit 3。
- 6.5 Given 验收全程 socket 连接被补丁拦截，Then 拦截计数为 0，`zero_network` PASS。
