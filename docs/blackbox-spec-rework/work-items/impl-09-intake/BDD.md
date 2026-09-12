# BDD：impl-09 M1 Source Intake + M2 Digitization 真实最薄接入

场景按 ACT 编号分组。「fixture 常量申报件」指：source_id、work_title、edition_note、technique_id、rights_status、release_policy、edition_part 全部取自 `pipeline/corpus/_fixture/mini_ed01/manifest.yaml`，`asset_root_ref: ocr/data_work/sanche_pages`。「真实页图」指 `ocr/data_work/sanche_pages/page_001..010.png`。

## 1. M1 纯函数（ACT 00）

- 1.1 Given fixture `manifest.yaml`，When `yaml.safe_load` 后经 `dump_manifest_yaml` 写出，Then 字节与原文件相同，且全局 `yaml.SafeDumper` 未被注册任何 representer。
- 1.2 Given 合法申报件，Then `load_submission` 返回键序固定的新 dict。Given 缺键、多键、非法 source_id、非法 release_policy、重复或非法页名、绝对路径或含 `..` 的 asset_root_ref，Then 分别以 SCH_001 / SCH_002 / ID_001 拒绝。
- 1.3 Given 页图目录缺多页，When `read_assets`，Then 一次性抛出 `SourceAssetMissing`，`paths` 按页序列出**全部**缺失路径，且不写任何文件。
- 1.4 Given 合成 PNG（1203×1654），When `build_source_manifest`，Then 顶层键序与 fixture manifest 相同；`source_assets[].path_ref/width/height/object_store/in_git` 与 fixture 相同；`files == []`。

## 2. M1 在 Ledger 上（ACT 01）

- 2.1 Given 三张合成页图与 fixture 常量申报件，When `run_m1`，Then：
  - StepRun `succeeded`；
  - Checkpoint 共 4 个，依次为 `asset_page_001`、`asset_page_002`、`asset_page_003`、`ingest_source`，prev 成链；
  - 每个 `source_asset` 修订的 sha256 等于文件哈希，Object Store 取回的字节相同；
  - m1 StagePackage 过 Schema，`content_sha256 == sha256(manifest 字节)`。
- 2.2 Given 上述 Ledger，When 调用 `corpus_compiler.inputs.resolve_m3_inputs`，Then 抛「M2 未灌入」（证明 M3 的 m1 解析段已通过）。
- 2.3 Given 页图缺失，Then 抛 `SourceAssetMissing`，且 Ledger 中 processing_runs、artifact_revisions、step_runs、audit_log 行数不变。
- 2.4 Given 同一 EditionPart 已跑过 M1，Then 第二次 `IntakeRefused`「M1 已封存」，且零写入。
- 2.5 Given begin 后资产哈希被篡改或 manifest 少一页，Then StepRun `failed`，failed_check 分别为 `asset_register` / `m1_gate`；失败报告已封存；无 m1 StagePackage。
- 2.6 Given CLI：成功 exit 0，末行以 `M1 OK` 开头；缺页图 exit 3，每个缺失路径一行 `BLOCKED_SOURCE_ASSET_MISSING`；重复运行 exit 2，`M1 REFUSED`。
- 2.7 Given 本机有真实十页页图，When 以 page_001..010 申报跑 `run_m1`，Then 成功，十个 sha256 等于 README §9 所列哈希。

## 3. M2 读取、决定表与规划（ACT 02）

- 3.1 Given 由 fixture 三页构造的 OCR 工作根，Then `read_ocr_work` 读出的页 sha256 等于 fixture manifest `files` 所登记的值。Given 缺页、缺 `anomalies.jsonl`、缺 `audit.jsonl`，Then 一次性 `OcrWorkMissing` 列出全部缺失。Given 坏 jsonl 行，Then SCH_001（不静默跳过）。
- 3.2 Given 决定表与 edition_part_artifact_id 不符、终态非法、页不在 Part 内、reason 为空，Then 分别以 SCH_002 / SCH_002 / REF_001 / SCH_001 拒绝。
- 3.3 Given 页 0 行、或页在异常登记中，Then 该页为必需终态页。Given Part 外页面的异常记录，Then 忽略。
- 3.4 Given fixture 三页与 page_002 的 fixture 决定，When `plan_digitization`，Then：
  - counts 等于 expected m2 的 `{ocr_pages:3, lines:43, chars:230, anomalies:1}`；
  - content_sha256 等于 expected m2 的 `b9125209…`；
  - ocr_page_set 的 page、sha256、terminal_states 等于 expected m2 payload；
  - human_event 与 fixture anomalies 条目的公共键值相等。
- 3.5 Given 异常页缺决定，Then 该页进入 `missing_decisions`（不抛）。Given 正常页标 known_unrecognizable，Then 以「裸标」拒绝。Given manually_transcribed 页无审计事件且无人工字框，Then 以「无人工校订证据」拒绝。
- 3.6 Given known_unrecognizable 且原始有行，Then 派生排除字节：lines、chars 为空；键序与原 doc 相同；`extra.m2_exclusion` 记原哈希与原行数、字数；两次生成字节相同。
- 3.7 Given 含 deferred 的决定，Then `deferred_pages` 非空，`ocr_page_set is None`。
- 3.8 Given 合成页含孤儿字框、行文本≠字拼接、120 行，Then 只写入 quality 计数与警告，不拒绝。

## 4. 独立 M2 Gate（ACT 03）

- 4.1 Given fixture 三页与 page_002 人工事件，Then 8 项检查全过；`proofreading == "not_evaluated"`、`ocr_profile == "not_captured"`。
- 4.2 Given 以下篡改，Then 各自让指定检查失败，Gate 为 `failed`：
  - 缺页 → `page_set`；
  - 页名、图名或尺寸不符 → `page_identity`；
  - 异常页无终态 → `anomaly_terminal`；
  - deferred → `no_deferred`；
  - 无事件、reason 空、证据被改 → `evidence_attached`；
  - 排除页仍有行、原哈希错、正常页有效字节≠原始 → `exclusion_consistent`；
  - 人工转录无证据 → `manual_evidence`；
  - 框缺数值 → `glyph_structure`。
- 4.3 Given 孤儿字框与行文本不一致，Then 只进 warnings，Gate 仍为 passed。
- 4.4 `gate.py` 不 import plan、decisions、ocr_work。

## 5. M2 在 Ledger 上：成功路径（ACT 04）

- 5.1 Given M1 已在 Ledger 成功、OCR 工作根由 fixture 三页构造、决定表含 page_002，When `run_m2`，Then：
  - StepRun `succeeded`；
  - 每页一个 Checkpoint，page_002 的 terminal_state 为 known_unrecognizable；
  - ocr_page 修订字节等于 fixture 页字节；
  - m2 StagePackage 过 Schema，lineage 输入为 [manifest]。
- 5.2 Then StepRun 事件中 `await_human`、`human_event`、`resume` 各 1 条；human_events 表 1 行；Transformation 的 human_event_revision_ids 等于末个 Checkpoint 的 human_decisions。
- 5.3 Then `ocr_anomaly_log`、`ocr_audit_log` 修订字节等于工作根文件字节；OCR 工作根文件在运行前后哈希不变。
- 5.4 Given 上述 Ledger，When `resolve_m3_inputs`，Then 解析出 3 页修订、`terminal_states == {"page_002": "known_unrecognizable"}`、1 个人工事件。
- 5.5 Given page_003 被标 known_unrecognizable 且有异常记录，Then：原始 ocr_page 修订 superseded；派生修订 prev 指向原始；Checkpoint 与 ocr_page_set 引用派生修订。
- 5.6 Given 无 M1、异常页缺决定、同 Part 已有 M2、OCR 工作根缺失，Then 均在 begin 前被拒，Ledger 行数不变（最后一项 exit 3 语义）。

## 6. M2 在 Ledger 上：deferred 与失败（ACT 05）

- 6.1 Given 决定表把 page_002 标 deferred，Then：StepRun 停在 `awaiting_human`；无 ocr_page_set、无 m2 StagePackage；`resolve_m3_inputs` 抛「M2 未通过」。
- 6.2 Given begin 后 OCR 工作根文件被改，Then failed_check 为 `input_contract`。
- 6.3 Given 有效字节被篡改导致 Gate 失败，Then failed_check 为 `m2_gate`。
- 6.4 Given begin 后发生未预期异常，Then failed_check 为 `internal`。
- 6.2–6.4 共同：失败报告已封存，无 StagePackage。
- 6.5 Given CLI：OK exit 0；缺决定 exit 2（REFUSED）；deferred exit 2（AWAITING_HUMAN）；缺工作根 exit 3（BLOCKED_SOURCE_ASSET_MISSING）。
- 6.6 Given 本机有十张页图、OCR 工作根、主 Agent 申报件与用户决定表，Then 真实十页 M1→M2 成功，ocr_page_set 为 10 页。缺任一则 skip，并在 skip 原因中写明缺什么。

## 7. 来源不可区分（ACT 06，需真实前三页页图）

- 7.1 Given 真实前三页页图、fixture 常量申报件、fixture 三页构造的 OCR 工作根、fixture 决定，When M1→M2，Then：
  - source_manifest 的 source_assets 与 fixture manifest 逐项相等；
  - m2 counts、content_sha256、ocr_page_set 关键字段等于 expected m2。
- 7.2 Given 另一临时 Ledger 由 `fixture_ingest(stages=("m1","m2"))` 灌入，Then 两边的「M3 可见投影」相同：ingest_source 修订的 artifact_type、m2 各页 task_id 与 terminal_state、ocr_page 字节、ocr_page_set 关键字段、human_event 公共键。
- 7.3 When 在本包 Ledger 上 `run_m3`，Then corpus_spans 字节等于 fixture `spans.yaml`（sha256 `ec6d77b9…`）；两次独立运行字节相同。

## 8. m1-replay 验收（ACT 07）

- 8.1 Given 本机有十张页图，When `m1-replay.sh`，Then 5 PASS + `BLOCKED epub_txt_replay`，exit 2。
- 8.2 Given 页图目录为空，Then 缺失路径各一行 `BLOCKED_SOURCE_ASSET_MISSING`，末行 `SUMMARY pass=0 fail=0 blocked=1`，exit 3。
- 8.3 Given 十张合成页图（哈希与 fixture 不同），Then `manifest_shape` FAIL，exit 1。Given 准备阶段抛异常，Then `FAIL m1_acceptance 宿主准备失败`，exit 1。
- 8.4 Given fixture 副本自带假 `verify.sh` 且 manifest 被改，Then 仍 `FAIL fixture_host`，exit 1。

## 9. m2-export-integrity 验收（ACT 08）

- 9.1 Given 页图、OCR 工作根、申报件、用户决定表齐全，Then 6 PASS + 3 BLOCKED，exit 2。Given 缺申报件或决定表，Then `real10_chain` 报 BLOCKED 而非 FAIL，5 PASS + 4 BLOCKED，exit 2。
- 9.2 Given OCR 工作根缺失，Then exit 3。
- 9.3 Given fixture 副本 expected/m2 的 counts 被改，Then `fixture_parity` FAIL，exit 1。Given 准备阶段异常，Then exit 1。
- 9.4 `gate_recomputed` 的判定代码不 import `pipeline.digitization.gate` 或 `plan`。
- 9.5 Given fixture 副本自带假 `verify.sh`，Then `FAIL fixture_host`，exit 1。
