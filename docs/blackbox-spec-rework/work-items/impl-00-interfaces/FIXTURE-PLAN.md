# FIXTURE-PLAN：mini_ed01 的 m4–m8 金标、verify 扩展与 §19.0 判据草案

状态：`DRAFT`（按 README §4 各条「推荐」项撰写；D-01、D-05、D-06、D-09、D-15 任一取其他选项，本文件 §2–§5 需重写）

## 1. 现状基线（2026-09-11 本机实测）

| 项 | 值 |
|---|---|
| 页面 | page_001 书名页 4 行；page_002 无文字（`known_unrecognizable`）；page_003 目录 39 行；合计 43 span、5 批 |
| 可用素材 | `ocr/data_work/sanche_pages/` 与 `ocr/data_work/data/` 只有 page_001..010；page_004–009 仍为目录，page_010 为 `irregular_layout` |
| `verify.sh` | 8 项 PASS（manifest_sha256, ids, coverage, anchors, expected_schema, expected_hash, assets, no_images），`FIXTURE OK` |
| 生成器重放 | `build_fixture.py --out <tmp>` 后执行 `diff -r --exclude=tools --exclude=README.md` 无输出 |
| 冻结哈希 | `manifest.yaml` 613d33e0772fa737c3ad161760f3720efbc4c681e9317983c65cdb7971e364c7；`spans.yaml` ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef；`expected/m1` 65bd10f595259685806d7ad7597cb92cab4fd4bc4c9b97aaa95c5271dc91e6d2；`expected/m2` f327fda69027be903b7389117a9ba0970173d4578a4d88f831e575b345d561f6；`expected/m3` e016c3fe4aa38b19b8026adb801eee241668957d977a8d6110837db8b57be935 |
| 会变化的文件 | `verify.sh`（当前 3456c28a…，ACT 08 重新生成）、`tools/build_fixture.py`（当前 cddf43d3…，ACT 05–08 修改） |

**不变量（每个 ACT 都要验证）**：上表五个冻结哈希不变；`manifest.yaml` 的 `files` 仍只登记 6 个非 expected 文件（避免 README §6 所说的哈希环）；fixture 内无图像；重放 `diff -r` 仍然为空。

## 2. 生成原则

### 2.1 由谁生成

- **唯一生成者**：`pipeline/corpus/_fixture/mini_ed01/tools/build_fixture.py`（fixture 工具）。金标内容由主 Agent 裁定后，以**常量表**的形式写进生成器（常量表逐字列在 act/05–07 的 contract 中）；生成器只做确定性派生（从 spans 求 mention、从文本求 quote 哈希、从文件字节求 sha）。
- **不得**由 M4–M8 的实现代码产出金标，也不得调用模型：否则实现与期望同错同过。
- **独立复算**：`verify.sh`（同样由生成器模板产出，但代码路径与生成逻辑分开写）重新计算哈希、计数、证据闭合与发布链，任何不一致都判 FAIL。

### 2.2 确定性

- 复用生成器现有的 `dump_yaml`（117–125）与 `Quoted` 表示器；新文件一律 `sort_keys=False`，键序由常量表的字典字面量决定；
- 不写时间戳、绝对路径、随机值；UUID 家族一律使用 §2.3 的常量 ID；
- 派生值只来自 fixture 内已有文件：`spans.yaml`、`manifest.yaml`、`pages/*.json`；
- 生成顺序：m4 → m5 → m6 → m7 → m8 子包 → release_manifest → m8 包 → `SHA256SUMS`（后者依赖前者字节）。

### 2.3 常量 ID 表（构造规则：`前缀 + 后缀.rjust(32, "0")`）

| 对象 | m4 | m5 | m6 | m7 | m8 |
|---|---|---|---|---|---|
| ProcessingRun | `prun_` f1（沿用 EditionRun） | `prun_` f1 | `prun_` f1 | `prun_` f7（release_run，D-04） | `prun_` f7 |
| StepRun | `srun_` f4 | `srun_` f5 | `srun_` f6 | `srun_` f7 | `srun_` f8 |
| StagePackage | `pkg_m4_` f4 | `pkg_m5_` f5 | `pkg_m6_` f6 | `pkg_m7_` f7 | `pkg_m8_` f8 |
| 包修订 | `rev_` f4 | `rev_` f5 | `rev_` f6 | `rev_` f7 | `rev_` f8 |
| 阶段输出索引 | `art_` f4 / `rev_` a4 `candidate_package` | `art_` f5 / `rev_` a5 `validation_package` | `art_` f6 / `rev_` a6 `reviewed_edition_package` | `art_` f7 / `rev_` a7 `assembly_package` | `art_` f8 / `rev_` a8 `publication_package` |
| 主内容 | `rev_` b4 `candidate_set` | `rev_` b5 `gate_results` | `rev_` b6 `reviewed_edition` | `rev_` b7 `canonical_snapshot` | `rev_` b8 `release_manifest` |
| 配置修订 | `rev_` c4 | `rev_` c5 | `rev_` c6 | `rev_` c7 | `rev_` c8 |
| 其他 | — | — | 人工事件 `rev_` de1…de5 | — | 子包 `rev_` 81…86；`rel_` f8；`ent_` e1、e2 |

人工闭集 ID：`co_qizheng_000001`（官祿宮）、`co_qizheng_000002`（福德宮）、`as_qizheng_000001/000002`、`pr_qizheng_000001/000002`。

## 3. 逐阶段最小金标内容（D-01 取 A：目录型直接主张，零伪造）

所有内容均可在 `source/transcript_v1.md` 与 `spans.yaml` 中逐字核对。目录行号：`s19`=「論官祿宮」、`s29`=「論福德宮」、`s34`=「再論福德宮變格」。

### 3.1 m4 `expected/m4.candidate_set.yaml`

- 顶层：`schema_version "1.0.0"`、`source_id src_sanche_ed01`、`edition_part_artifact_id art_…e1`、`technique_id qizheng`、`corpus_package_revision_id rev_…a3`、`span_layer structural`、`extraction_mode fixture_rule`；
- `concepts`（常量表 `(concept_id, canonical_name)`，派生 `mention_span_ids = [span_id for span in spans if canonical_name in span.text]`，按 spans 顺序）：
  - `co_qizheng_000001` 官祿宮 → `[ss_sanche_ed01_p0003_s19]`
  - `co_qizheng_000002` 福德宮 → `[ss_sanche_ed01_p0003_s29, ss_sanche_ed01_p0003_s34]`
  - 每项 `aliases []`、`layer L3`、`homograph_id null`、`omen_carrying null`、`status machine_extracted`；
- `term_layers`：`l1_hits []`、`l2_hits []`、`l3_new_concept_candidates` 每个概念一项 `{surface, span_ids}`（与 mention 相同）；
- `assertions`（常量表）：
  - `as_qizheng_000001` / `pr_qizheng_000001` / 主体 `co_qizheng_000001` / 命题「《三辰通載》目錄列有「論官祿宮」一目」/ 证据 `[s19]`
  - `as_qizheng_000002` / `pr_qizheng_000002` / 主体 `co_qizheng_000002` / 命题「《三辰通載》目錄列有「論福德宮」「再論福德宮變格」二目」/ 证据 `[s29, s34]`
  - 每条证据派生：`{source_span_id, support_type: direct, char_start: 0, char_end: len(text), quote: text, quote_sha256: sha256(text.encode("utf-8"))}`；另有 `relation supports, conditions [], exceptions [], school_ids [], canon_refs [], layer general, status machine_extracted`；
- `patterns / applicability_rules / school_views / cases / editorial_notes / uncertainties / model_run_revision_ids` 全部为 `[]`；
- `expected/m4.stage_package.yaml`：输入 `[ref(art_…f3, rev_…a3, corpus_package)]`；输出 `[ref(art_…f4, rev_…a4, candidate_package)]`；payload `{candidate_set_revision_id: rev_…b4, span_layer: structural, extraction_mode: fixture_rule, unresolved_disputes: 0}`；counts `{concepts: 2, assertions: 2, evidence_links: 3, applicability_rules: 0, school_views: 0, cases: 0}`；content_sha256 = sha256(m4.candidate_set.yaml)；operation `extract_knowledge`；config `rev_…c4`。

### 3.2 m5 `expected/m5.gate_results.yaml`

- `stage m5`、`technique_id qizheng`、`target_consumption_level INTERNAL_DEMO`、`subject_revision_id rev_…a4`、`validators [{name: generic, version: "1.0.0"}, {name: technique_profile_qizheng, version: "1.0.0"}]`；
- `gates`（每个 check `{check, status, error_code: null, detail: "", subject_ids: []}`）：
  - G1 passed：`hash_chain_pages, hash_chain_spans, quote_hashes, no_pua_or_unresolved_chars`
  - G2 passed：`section_coverage, no_overlap, concat_equals_block, expected_actual_counts`
  - G3 passed：`id_format, id_unique, no_dangling_refs, evidence_within_span, glyphbox_anchor, evidence_level_for_target`
  - G4 blocked：`case_layer, editorial_layer, conditions_structured, school_ids_present`；`blocked_reason`「school_ids 为空且流派尚未登记（D-09）」
  - G5 passed：`concept_mention_recall, concept_mention_precision, candidate_concept_not_released`
  - G6 blocked：`rule_executability, factset_ast_complete`；`blocked_reason`「applicability_rules 为 0（D-01/D-08）」
- `release_checks []`、`broken_relations []`、`rework_tasks []`；`summary {critical_errors 0, failed_checks 0, blocked_checks 6, warnings 0, broken_relations 0, rework_tasks 0}`；`gate_passed true`（D-09 取 A）；
- 包：输入 `[a4]`；输出 `a5 validation_package`；payload `{gate_results_revision_id b5, target_consumption_level INTERNAL_DEMO, gate_status {G1 passed, G2 passed, G3 passed, G4 blocked, G5 passed, G6 blocked}, m5_gate_passed true}`；counts `{checks_passed 17, checks_failed 0, checks_blocked 6, warnings 0, broken_relations 0, rework_tasks 0}`；operation `validate_candidates`。

### 3.3 m6 `expected/m6.review_decision_01..05.yaml` + `m6.reviewed_edition.yaml`

| 序 | 事件修订 | decision_type | target.entity_id | target.artifact_revision_id | rationale |
|---|---|---|---|---|---|
| 01 | de1 | review_source_fidelity | co_qizheng_000001 | rev_…b4 | 概念字面与目錄行逐字一致 |
| 02 | de2 | review_source_fidelity | co_qizheng_000002 | rev_…b4 | 概念字面与目錄行逐字一致 |
| 03 | de3 | review_source_fidelity | as_qizheng_000001 | rev_…b4 | 引文与目錄行逐字一致 |
| 04 | de4 | review_source_fidelity | as_qizheng_000002 | rev_…b4 | 引文与目錄行逐字一致 |
| 05 | de5 | review_rights | src_sanche_ed01 | rev_…a1 | 文字公版；扫描件分发权未确认，仅限 INTERNAL_DEMO 派生页图 |

每条：`verdict accept`、`stage m6`、`scope_consumption_level INTERNAL_DEMO`、`modified_revision_id null`、`content_status_after null`、`actor_ref local_owner`。

`reviewed_edition`：`approved` = 四个 co_/as_ 实体（`artifact_revision_id rev_…b4`、`content_status machine_extracted`，顺序 co1, co2, as1, as2）；`rejected []`；`decision_revision_ids [de1..de5]`；`correction_request_revision_ids []`；`unresolved_count 0`。包：输入 `[a4, a5, a3]`；输出 `a6 reviewed_edition_package`；counts `{approved 4, rejected 0, decisions 5, correction_requests 0}`；operation `review_candidates`。

### 3.4 m7 `expected/m7.canonical_snapshot.yaml`（ReleaseRun `prun_…f7`）

`technique_id qizheng`、`previous_snapshot_revision_id null`、`reviewed_edition_package_revision_ids [a6]`、`edition_part_artifact_ids [art_…e1]`；`concepts` 两项（`source_entity_revisions [{entity_id, artifact_revision_id: rev_…b4}]`）；`assertions` 两项（evidence 与 m4 逐字相同）；`school_views []`、`conflict_groups []`；`proposals {merge [], alias [], conflict [], evidence_relation []}`；`release_decision_revision_ids []`；`canonical_hash` 按 INTERFACES §3.7 规则计算。包：输入 `[a6]`；输出 `a7 assembly_package`；counts `{concepts 2, assertions 2, proposals_auto 0, proposals_human 0, decisions 0}`；operation `assemble_knowledge`。

### 3.5 m8 `expected/m8/*.yaml` + `m8.stage_package.yaml`

- `knowledge_data_pack`：`release_id rel_…f8`、`consumption_level INTERNAL_DEMO`、`watermark`「INTERNAL_DEMO · machine_extracted · 未经专家签发」；`entries`：`ent_…e1` 官祿宮（主体 co1，`assertion_ids [as1]`）、`ent_…e2` 福德宮（主体 co2，`[as2]`），`mark_binding` 四字段全 null；`concepts` 两项（`basic_imagery null`）；`assertions` 两项；`school_views []`、`conflict_groups []`；
- `evidence_map_pack`：3 条 chain `(e1, as1, s19)`、`(e2, as2, s29)`、`(e2, as2, s34)`；`source_span` 与 `source_anchor` 从 spans.yaml 原样复制；`ocr_page.glyph_ids` = anchor.chars 的 glyph_id；`source_asset.image_sha256` = manifest 中 page_003 的 sha；
- `source_asset_pack`：`policy derived_page_images_only`；只登记被引用的 page_003（`width 1203, height 1654, ref {object_store local, path_ref ocr/data_work/sanche_pages/page_003.png}`, `rights_note` = manifest.rights_status, `bytes_included false`）；
- `query_contract_pack`：`contract_version "1.0.0"`，四个接口，`backward_compatible true`；
- `anchor_contract_pack`：白名单 4 项、稳定性映射、`anchor_required_fields`、`identity_migration_map {release_id rel_…f8, previous_release_id null, entries []}`；
- `release_validation_report`（gate_results 结构，`stage m8`）：G6 blocked（无 RuleIndexPack）；G7 passed（`consumption_level_admission, release_manifest_complete, watermark_for_machine_state, expert_signoff_not_required_for_internal_demo`）；`release_checks` 全部 passed：`evidence_chain_closure, anchor_contract_present, source_release_not_dev, coordinate_space_consistent`；
- `release_manifest`：`source_release internal`、`canonical_snapshot_revision_id b7`、`canonical_hash` 同 m7、`schema_versions` 列出本包 13 份内容 Schema 均为 "1.0.0"、`profile_versions {fact_set_profile null, ast_schema_version null}`、`min_app_version "0.0.0"`、`release_policy derived_page_images_only`、`rights [{src_sanche_ed01, manifest.rights_status, "INTERNAL_DEMO 派生页图，不取得公开分发权（§16 723）"}]`、`subpacks` 6 项 `{artifact_type, artifact_revision_id rev_…81..86, sha256, byte_size}`（顺序同上列）、`source_revision_reconciliation [{src_sanche_ed01, art_…e1, ec6d77b9…, a6}]`、`known_defects`「机器转录未人工校对」「G4 blocked：school_ids 为空」「G6 blocked：无 ApplicabilityRule」、`watermark true`、`retired_anchor_disclosures []`、`anchor_migration_rate null`、`previous_release_id null`；
- 包：输入 `[a7, a3, a1]`（D-03）；输出 `a8 publication_package`；payload `{release_id, consumption_level, release_manifest_revision_id b8, subpack_revision_ids {6 项}, canonical_snapshot_revision_id b7}`；counts `{entries 2, assertions 2, evidence_chains 3, source_assets 1, subpacks 6}`；content_sha256 = sha256(release_manifest.yaml)；operation `compile_dataset`。

## 4. 金标投影与哈希冻结

### 4.1 身份归一化投影 `golden_projection(doc)`（D-06 取 A）

1. 以 `yaml.safe_load` 解析；深度优先、字典按键插入顺序、列表按下标顺序遍历；
2. 字符串若**整串**匹配 `^(art|rev|prun|srun|rel|ent|sv|cg)_[0-9a-f]{32}$` 或 `^pkg_m[1-8]_[0-9a-f]{32}$`，替换为 `<前缀#n>`，n 为该值首次出现的序号（同一值始终映射为同一占位）；
3. 删除键：以 `_path` 结尾的键、`validators[].version`；
4. 以 `json.dumps(sort_keys=True, ensure_ascii=False, separators=(",", ":"))` 序列化，sha256 即投影哈希；
5. 人工闭集 ID（`src_ ss_ as_ pr_ co_ hg_ pat_ sch_`）与所有内容值保持原样。

模块验收判定为「实际主内容投影 == 金标主内容投影」「实际 StagePackage 的 counts == 金标 counts」。fixture `verify.sh` 不做投影（金标自身使用常量 ID）。投影函数的生产实现归 Contract Registry 包（D-13）。

### 4.2 哈希冻结

- 生成器最后写 `expected/SHA256SUMS`：每行 `<sha256>  <相对 expected/ 的路径>`，按路径字节序排序，覆盖 `expected/` 下除自身外的全部文件（含 m1–m3）；
- `verify.sh` V12 `expected_sums` 逐行复算；
- 主 Agent 验收时把 `sha256(expected/SHA256SUMS)` 记入 impl-00 ACCEPTANCE；下游包在 TDD §0 基线中只钉这一个哈希（沿用 impl-02 钉 spans.yaml 的做法）；
- `manifest.yaml` 的 `files` 不收录 expected，m1 的 content_sha256 不变。

## 5. `verify.sh` 扩展判定项（在生成器 `VERIFY_SH` 模板中修改后重新生成）

### 5.1 检查项（8 → 12）

| 检查 | 变更 | 判定 |
|---|---|---|
| V2 `ids` | 扩展 | ID_RULES 增加 `co_shared_`（先于 `co_`）、`co_`、`as_`、`pr_`、`ent_`、`rel_`、`sch_`、`sv_`、`cg_`、`pat_`；收集所有以 `_id` / `_ids` 结尾的键以及 `entity_id` 的字符串值，排除 `technique_id, line_id, glyph_id, glyph_ids, task_id` |
| V5 `expected_schema` | 扩展 | m1–m8 StagePackage 过 `stage_package.schema.json`；m4–m8 payload 过 `stage_payload_mN`；每个内容文件过对应 Schema（m6 决定过 review_decision，m8 子包过同名 Schema，release_validation_report 过 gate_results） |
| V6 `expected_hash` | 扩展 | m4–m8 的 `content_sha256` = sha256(主内容文件字节)；counts 由内容独立重算；m7 与 release_manifest 的 `canonical_hash` 按 INTERFACES §3.7 重算且相等 |
| V9 `stage_chain`（新） | — | m2–m8 各自 `manifest.input_artifacts` 含上一阶段 `output_artifacts[0]`；`lineage.transformations[0].input_artifact_revision_ids` == `[x.artifact_revision_id for x in input_artifacts]`；m1–m6 的 processing_run_id 为 f1，m7–m8 为 f7；每个 payload 中的 `*_revision_id` 能在 §2.3 常量表中找到 |
| V10 `evidence_closure`（新） | — | 证据 span 存在；`0 ≤ char_start < char_end ≤ len(text)`；quote 等于切片；quote_sha256 正确；每条主张至少 1 条证据（SEM_001）；co_/as_/pr_ 不重复（ID_002）；主体存在；mention 召回与精确均为 100%；m6 决定的 target 存在且修订号正确；approved 集合 == 被接受的 co_/as_ 目标；m7 的 concepts/assertions 与 m6 approved 一致且逐字等于 m4 |
| V11 `publication_chain`（新） | — | entries 的 assertion_ids 非空且属于 m7；chain 键序恰为 7 段固定顺序；chain 集合 == 由 entries×evidence 推出的集合；source_span/source_anchor 等于 spans.yaml；glyph_id 属于 `pages/<页>.json`；image_sha256 等于 manifest；所有 bbox 与字框落在 `[0,width]×[0,height]`；subpacks 的 sha256/byte_size 等于文件且恰 6 项；INTERNAL_DEMO 须带水印且 known_defects 非空；`source_release != dev`；锚点稳定性映射逐字相同 |
| V12 `expected_sums`（新） | — | SHA256SUMS 覆盖集合 == expected/ 实际文件集合（不含自身），每行哈希相等 |

V1、V3、V4、V7、V8 不变。检查输出顺序：V1…V8、V9、V10、V11、V12。

### 5.2 篡改矩阵（`fixture_mutations.sh`，20 例）

执行方式：把规范 fixture 复制到临时目录 → 施加篡改 →（除标注「不修哈希」者外）**按规则修复**受影响阶段包的 `content_sha256` 与 `SHA256SUMS`，模拟「改了内容也改了哈希」的攻击者 → 执行 `FIXTURE_DIR=<副本> bash <仓库>/pipeline/corpus/_fixture/mini_ed01/verify.sh` → 要求退出码 1，且指定检查名出现在 FAIL 行中。

| # | 篡改 | 期望 FAIL |
|---|---|---|
| 01 | m4 as1 证据 quote 改一字 | evidence_closure |
| 02 | m4 as2 第二条证据 char_end = len(text)+1 | evidence_closure |
| 03 | m4 as1 证据 span 改为 `ss_sanche_ed01_p0003_s99` | evidence_closure |
| 04 | m4 as1 evidence 置空 | expected_schema |
| 05 | m4 co2 的 mention_span_ids 删去 s34 | evidence_closure |
| 06 | m4 as2 的 assertion_id 改成 as1（重复） | evidence_closure |
| 07 | m4 包 input_artifacts 改为 m2 的输出 | stage_chain |
| 08 | m5 payload gate_status.G4 改为 passed | expected_hash |
| 09 | m5 gate_results 改一个 detail 字符（不修哈希） | expected_hash |
| 10 | m6 decision_03 的 decision_type 改为 `expert_verified` | expected_schema |
| 11 | m6 decision_04 删除 target.artifact_revision_id | expected_schema |
| 12 | m6 reviewed_edition unresolved_count 改为 1 | expected_schema |
| 13 | m7 canonical_hash 改一位（不修哈希） | expected_hash |
| 14 | m8 evidence chain[0] 的 source_anchor.bbox.x 加 1 | publication_chain |
| 15 | m8 chain[1] 的 source_span 与 source_anchor 键序对调 | publication_chain |
| 16 | m8 entry e1 的 assertion_ids 置空 | expected_schema |
| 17 | m8 release_manifest subpacks[0].sha256 改一位 | publication_chain |
| 18 | m8 source_asset_pack 的 image_sha256 改一位 | publication_chain |
| 19 | m8 chain[2] 首个字框 box.x 改为 1300（超出页宽 1203） | publication_chain |
| 20 | SHA256SUMS 第一行哈希改一位（不修哈希） | expected_sums |

输出：每例一行 `PASS Mnn <检查名>` 或 `FAIL Mnn <原因>`；末行 `MUTATIONS <通过数>/20`；全部通过 exit 0，否则 exit 1；`.venv` 缺失 exit 3。

## 6. §19.0 判据脚本判定项草案（归各模块包实现，本包只给草案）

公共纪律：`set -u`、`LC_ALL=en_US.UTF-8`；永远调用仓库内规范 `verify.sh`，不执行被验目录自带脚本；每项输出 `PASS/FAIL/BLOCKED <名>`，末行 `SUMMARY pass= fail= blocked=`；退出码 0 全 PASS / 1 有 FAIL（含准备与运行异常）/ 2 无 FAIL 有 BLOCKED / 3 仅限宿主缺失；BLOCKED 说明中的差距行名逐字取 §19 主表第一列。

### 6.1 `m5-evidence-gate.sh`（差距「M5 全书与证据校验不足」879：无法阻断全书漏编、错误证据范围和零命中假绿）

准备：临时 Ledger → `ingest(stages=m1..m4)` → `run_m5(target=INTERNAL_DEMO)`。

1. `fixture_host`：规范 verify.sh 返回 0 或 3；
2. `inputs_frozen`：冻结输入 == 6 个修订（D-02），全部 sealed；
3. `gate_results_golden`：主内容投影 == `m5.gate_results.yaml` 投影；counts 相等；
4. `replay_identical`：两个临时 Ledger 各跑一次，主内容字节相同（G1 重放，52–53）；
5. `rejects_dropped_span`：从 corpus_spans 删一条 span 后重跑 → G2 failed，`m5_gate_passed=false`（857–859 漏编假绿）；
6. `rejects_evidence_out_of_span`：证据 char_end 越界 → G3 failed，`TXT_001`（G3 68）；
7. `rejects_quote_mismatch`：quote 改字 → G3 failed，`TXT_001`；
8. `rejects_dangling_span`：证据引用不存在的 ss_ → `REF_001`；
9. `rejects_zero_hit`：删去概念 mention → G5 failed（81–84 零命中假绿）；
10. `rejects_offset_level_for_public`：`target=PUBLIC_RELEASE` 且 spans 去掉字框 → G3 failed（590）；
11. `blocked_semantics`：INTERNAL_DEMO 时 G4/G6 为 blocked 且 gate_passed=true；DEV_SEARCH 时 gate_passed=false（D-09）；
12. `no_candidate_mutation`：运行前后 candidate_set 修订字节不变（580）；
13. `package_lineage`：StagePackage 过 Schema，payload 过 stage_payload_m5，lineage 输入 == 冻结输入。

修复后 exit 0 的条件：1–13 全 PASS（G4/G6 的 blocked 属于正确判定，不计 BLOCKED 行）。

### 6.2 `m8-span-identity.sh`（差距「M8 映射键碰撞」882：148 span 塌缩成 18 键、6 组碰撞，修好解析后会链到错误页）

准备：临时 Ledger → `ingest(stages=m1..m7)` → `run_m8(consumption_level=INTERNAL_DEMO)`。

1. `fixture_host`；
2. `inputs_frozen`：a7 + corpus_spans + source_manifest；
3. `span_key_unique`：EvidenceMapPack 与 KnowledgeDataPack 中的 span 键全部为完整 `ss_` ID；去重后键数 == 被引 span 数；不存在「页+行前缀」之类的截断键；
4. `span_page_binding`：每个 ss_ 的 `p<NNNN>` == source_span.page 的页号 == source_anchor.page == ocr_page.page（防止链到错误页）；
5. `chain_closure_order`：七段齐全、顺序固定、无悬空（705–713）；
6. `anchor_equals_corpus`：source_anchor 与冻结的 corpus_spans 逐字段相等（713 锚点随包发布）；
7. `coordinate_space`：字框落在 SourceAssetPack 登记的页尺寸内（714）；
8. `release_manifest_hashes`：每个子包 sha256 与字节相等（697）；
9. `consumption_level_gate`：以 PUBLIC_RELEASE 运行时，因 machine_extracted 被拒绝（678），且 `source_release=dev` 被拒绝（697）；
10. `anchor_contract`：白名单、稳定性、IdentityMigrationMap 存在（729–734）；
11. `collision_mutation`：注入两条 page_003 的 span，其新 ID 仅行号不同、截断后相同 → 编译必须保持两键，或以 `ID_002` fail-closed，不得静默合并；
12. `golden_match`：6 个子包与 release_manifest 投影 == 金标；
13. `graph_same_snapshot`：BLOCKED（GraphProjectionPack 纵切后，D-15），说明逐字「前置缺失: M8 Dataset Compilation；GraphProjectionPack 未实现」。

注意：第 13 项在首纵切中恒为 BLOCKED，因此该脚本首纵切返回 2。若主 Agent 要求 exit 0，需把 20.9 的 Graph 验收移出本脚本（待 D-15 一并裁决）。

### 6.3 其余三条（简要）

- `m4-stage-gate.sh`（878）：`category_isolation`（每个 candidate_batch 只含一个 category）、`ab_independence`（A/B model_run 的输入不含对方输出修订）、`c_rereads_source`（C 的输入含 corpus_spans）、`disputes_resolved`（未决分歧 0 才有 m4 包）、`raw_model_artifacts_complete`（574 七类留痕齐全）、`evidence_present`、`l2_no_bare_surface`（550）、`golden_match`（投影）。
- `m6-data-fields.sh`（880）：workbench 库 `original_text` 非空数 > 0 才允许导入为 Candidate（943 准入）；ReviewedEditionPackage 中每条 approved 均有 decision；`decision_anchor_pair`；8 类 decision_type 闭集；不存在「保存即 verified」（889 回归）；`golden_match`。
- `m7-assembler.sh`（881）：同一 ReviewedEditionPackage 重跑 Snapshot 字节相同；第二个 Edition 加入不改旧 entity_id（941 20.5）；冲突保留，不以默认流派折叠（570、653）；已封存 ReviewedEditionPackage 不变（175）；`golden_match`。
