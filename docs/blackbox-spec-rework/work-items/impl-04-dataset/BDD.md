# BDD：impl-04 M8 Dataset Compilation 首切片

## 1. 准入与规范化（ACT 00）

- 1.1 Given `INTERNAL_DEMO`、`{machine_extracted}`、`glyphbox_level`、`derived_page_images_only`，When `evaluate_admission`，Then `admitted` 为真、`watermark_required` 为真、`source_release == "dev"`、`isolation == "internal_only"`。
- 1.2 Given 级别写成 `internal_demo`、未知证据级别、未知内容状态，Then 各自 `SCH_002`；Given 状态含 `deprecated`，Then 拒绝；Given 空状态集合，Then `SCH_001`。
- 1.3 Given `DEV_SEARCH`，Then 不准入，`unmet == ["dev_search_gates_not_implemented"]`。
- 1.4 Given `PUBLIC_RELEASE` 与 fixture 同型输入，Then `unmet` 恰为 `content_not_expert_verified, draft_schema, min_app_version_unset, public_release_gates_not_implemented, rights_unconfirmed, source_release_dev`；Given 全部 `expert_verified`、非草案 Schema、有 `min_app_version`、权利已确认，Then 仍不准入且 `unmet == ["public_release_gates_not_implemented"]`（fail-closed）。
- 1.5 Given 含中文与嵌套修订号的对象，Then 规范化字节键序稳定、中文不转义、无多余空白；`normalized_sha256` 对修订号取值不敏感。

## 2. 子包编译（ACT 01）

- 2.1 Given fixture 清单与三页资产记录，When `build_source_asset_pack`，Then 按页序产出 3 页、`content_level == "derived_page_images_only"`、哈希与宽高等于清单。
- 2.2 Given 资产哈希不符、尺寸不符、缺页、页序外多页、清单为其他发布策略，Then 分别 `SRC_003`、`SRC_003`、`REF_001`、`SCH_002`、拒绝。
- 2.3 Given fixture `spans.yaml` 与页 JSON，When `build_evidence_map_pack`，Then 43 条 entry 以完整 `span_id` 为键；41 条 `glyph` 高亮、2 条 `line_bbox`（`ss_sanche_ed01_p0001_s03`、`ss_sanche_ed01_p0001_s04`）；字框共 230 个；`page_index == {page_001: 4 条, page_002: [], page_003: 39 条}`。
- 2.4 Given 同一批 span 按 `pipeline/rag/build_index.py:133-138` 规则以 `(source_id, sNN)` 取键，Then 塌缩为 39 键、4 组碰撞（宿主能暴露缺陷）；而 EvidenceMapPack 键数仍为 43。
- 2.5 Given span_id 页号与 `page` 不符、行序与 `line_index` 不符、重复 span_id、锚点页与 span 页不符、锚点图像哈希与资产包不符、页 JSON 宽高与资产包不符、字框越出页框、排除页上出现 span，Then 分别 `ID_001`、`ID_001`、`ID_002`、拒绝、`SRC_003`、拒绝、拒绝、拒绝。
- 2.6 两次编译字节相同；只换 OCR 页与页图修订号时字节不同、`normalized_sha256` 相同。
- 2.7 `compute_known_defects` 在 fixture 上恰为六个代码；`build_release_manifest` 的 `canonical_hash` 可按规则重算；admission 未准入、或伪造 `admitted: true` 但级别为 `DEV_SEARCH`、或 pack_type 重复，Then 拒绝。

## 3. 独立发布 Gate（ACT 02）

- 3.1 Given fixture 编译结果，When `evaluate_publication`，Then 13 项检查全部 `ok`、`knowledge_chain` 为 `not_evaluated`、`passed` 为真。
- 3.2 Given 下列任一篡改，Then 指定检查 `ok == False` 且 `passed == False`：删一条 entry；把 p0001 条目键改为 p0003 同行序键；按行序塌缩键；改 entry.page；改 text；改 quote 哈希；改字框；改字；改行框；把 `line_bbox` 伪造成 `glyph`；换 OCR 页修订；改 entry 图像哈希；改资产包哈希；改 frame；反向索引缺 span；排除页挂 span；篡改子包字节；篡改 `canonical_hash`；对账少一项；清单级别改 `DEV_SEARCH`；`authoritative: true`；某 entry `watermark: false`；删一个披露代码；声称 `knowledge_chain: compiled`。
- 3.3 Given 检查内部抛异常（页 JSON 缺页），Then 该项 `ok == False` 且函数不抛出；`gate.py` 不 import `packs`/`canonical`/`levels`/`step`。

## 4. 薄 M1 页图登记（ACT 03）

模块 `pipeline/dataset_compiler/shim/m1_shim_source_assets.py`，CLI `python -m pipeline.dataset_compiler.shim.m1_shim_source_assets`（D2：文件名与 CLI 名显式标 `m1_shim`；impl-09 M1 落地后替换）。

- 4.1 Given Ledger 中一个合成 M1 清单与临时目录中的合成 PNG，When `register_source_assets`，Then 每页一个 `source_asset_page` sealed 修订（`rights_scope == "internal"`）与一个 m1 Checkpoint、登记文档与 Transformation 封存、StepRun `succeeded`。
- 4.2 Given 缺一页、哈希不符、尺寸不符、非 PNG，Then begin 之前拒绝且 Ledger 行数不变；缺页时异常消息以 `BLOCKED_SOURCE_ASSET_MISSING` 开头并列出全部缺失 `path_ref`。
- 4.3 Given 已登记过、或 M1 未灌入，Then 拒绝；Given begin 之后 Ledger 写方法抛错，Then `failed_check == "internal"` 且失败报告封存。
- 4.4 Given 本机真实页图与 fixture m1，Then 三页登记哈希等于清单；CLI 成功退出 0、缺图退出 3。

## 5. 输入解析（ACT 04）

- 5.1 Given ingest m1,m2 → `run_m3` → 登记页图，When `resolve_m8_inputs`，Then 解析出 m3 包、corpus_spans、清单、ocr_page_set、三页 OCR 修订、三页页图修订、`m3_gate_profile == "structural_only"`、`excluded_pages == {"page_002": "known_unrecognizable"}`，且无写入。
- 5.2 Given 未跑 M3、M3 为 `fixture_ingest` 灌入的包、页图未登记、M8 已封存，Then 分别拒绝（消息含「M3 未编译」、`spans_revision_id`、「SourceAsset 未登记」、「M8 已封存」）。

## 6. Ledger 上真实编译（ACT 05）

- 6.1 Given 5.1 的 Ledger，When `run_m8(consumption_level="INTERNAL_DEMO")`，Then：
  - StepRun `succeeded`，冻结 10 个输入；
  - 4 个 m8 Checkpoint 依次为 `source_asset_pack`、`evidence_map_pack`、`release_manifest`、`validation_report` 且成链；
  - `source_asset_pack`/`evidence_map_pack`/`release_manifest`/`validation_report`/`publication_package` 各为独立 sealed Artifact；
  - ReleaseManifest 中的子包哈希与 Ledger 对象字节重算一致；
  - m8 StagePackage 过 Schema，`lineage.upstream_artifacts` 含 m3 StagePackage 引用，`counts == {spans:43, pages:3, source_assets:3, glyph_highlights:41, line_bbox_highlights:2, packs:2}`。
- 6.2 Given 两个独立 Ledger 各跑一遍，Then 两份 EvidenceMapPack 的 `normalized_sha256` 相同。
- 6.3 Given 级别为非法值，Then `SCH_002` 且无任何写入；Given 同一 EditionPart 第二次 `run_m8`，Then 拒绝。
- 6.4 Given 页图对象、或 corpus_spans 对象被改一个字节，Then `failed_check == "input_contract"`、失败报告 sealed、无 m8 StagePackage。
- 6.5 Given 编译结果被删一条 entry，Then `failed_check == "publication_gate"`、无 publication_package 与 m8 StagePackage。

## 7. 准入失败与异常分层（ACT 06）

- 7.1 Given `DEV_SEARCH`，Then StepRun `failed`、`failed_check == "admission"`；Ledger 中无 `source_asset_pack`/`evidence_map_pack`/`release_manifest`/`publication_package` 修订；该 EditionPart 的 m8 StepRun 恰 1 个（不降级重试）。
- 7.2 Given `PUBLIC_RELEASE`，Then `admission` 失败，失败报告 detail 含全部六个 unmet 代码；给 `min_app_version="1.0.0"` 后 detail 不含 `min_app_version_unset`，但仍失败。
- 7.3 Given 子包编译抛错、Ledger 写方法抛错，Then `failed_check` 分别为 `compile`、`internal`，StepRun `failed`；Given begin 之前的拒绝，Then 抛出原异常类型（不被重新包装）。
- 7.4 CLI：成功退出 0；`PUBLIC_RELEASE` 退出 1；页图未登记退出 2；非法级别退出 2。

## 8. 验收脚本（ACT 07）

- 8.1 Given mini_ed01 与本机页图，When `m8-span-identity.sh`，Then 7 项 PASS、`mentions_mapping` BLOCKED、exit 2；`legacy_collision_exposed` 的说明含 `legacy_keys=39 collision_groups=4 pack_keys=43`。
- 8.2 Given `--check publication`，Then 8 项 PASS、`knowledge_chain` BLOCKED、exit 2；其中 `fail_closed_levels` 在两个另起的 Ledger 上证明 `DEV_SEARCH`/`PUBLIC_RELEASE` 失败且无子包修订。
- 8.3 Given fixture 副本的 span 金标被改、编译结果被删条目、准备阶段崩溃，Then exit 1；Given 缺 fixture、缺页图，Then exit 3。
- 8.4 Given 被验副本自带的 `verify.sh` 被换成假脚本且数据被改，Then 仍 `FAIL fixture_host`、exit 1。

## 9. run_all（ACT 08）

- 9.1 Given 本机宿主，When `run_all.sh 20.4` 与 `run_all.sh 20.8`，Then 均为 `BLOCKED  20.N  前置缺失: M4 Knowledge Extraction；…`（说明写明已判定段），全量 `SUMMARY pass=2 fail=1 blocked=8`。
- 9.2 Given 把一份 fixture 副本的 `spans.yaml` 删一条 span（`FIXTURE_DIR` 指该副本），Then 20.4 为 `FAIL`，落点为 `fixture_host`（仓库内规范 `verify.sh` 先在 `manifest_sha256` 拦截被改副本，D-18）；直接调用 `python -m pipeline.dataset_compiler.acceptance --fixture <副本> --check span_identity` 时落点为 `span_key_unique` 的 fixture 金标比对（G7-RULINGS 第 44 条订正）。
- 9.3 Given `FIXTURE_ASSET_ROOT=/nonexistent`，Then 20.4、20.8 为 `BLOCKED … 测试宿主匮乏；…`。
