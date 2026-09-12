# BDD：impl-00 跨模块契约与金标

## 0. 契约检查器（ACT 00）

- 0.1 Given 当前仓库，When `check_i00.py --upto 00`，Then `PASS C00`，C01–C09 为 `SKIP`，exit 0。
- 0.2 Given 临时副本中 `spans.yaml` 改一个字节、`expected/m2` 改一个字节、或 fixture 内放入 `x.png`，Then `FAIL C00`，exit 1。
- 0.3 Given 仓库尚未落地 ACT 01，When `--upto 01`，Then `FAIL C01 …缺失`（Red 基线）。
- 0.4 Given 缺 yaml 或 jsonschema，Then exit 3，末行不出现 SUMMARY 以外的 PASS。

## 1. 公共部件与 M4 Schema（ACT 01）

- 1.1 Given `candidate_set.valid.yaml`，Then 通过 `candidate_set.schema.json`。
- 1.2 Given 主张无证据、概念 ID 为 `hg_0042`、状态为 `verified`、support_type 为 `quoted`、存在未知字段、span ID 为 `ss_sanche_ed1_p3_s19`、`applicability_rules` 非空、quote_sha256 只有 63 位，Then 8 个 invalid 样例全部校验失败。
- 1.3 `contract_common.schema.json` 中的 13 个 ID 正则与 `pipeline/ledger/ids.py` PATTERNS 逐字相同。
- 1.4 `bash openspec/schemas/verify.sh` 仍 exit 0，并新增 `PASS candidate_set_*` 行。

## 2. M5/M6 Schema（ACT 02）

- 2.1 gate_results：`stage=m5` 时门禁不是恰好 G1–G6 → 失败；出现 `G8` → 失败；`stage=m5` 带 release_checks → 失败。
- 2.2 review_decision：`verdict=modify` 但缺 `modified_revision_id` → 失败；`content_status_after=expert_verified` 且 `verdict=reject` → 失败；target 缺 `artifact_revision_id` → 失败；decision_type 不在 8 类 → 失败。
- 2.3 reviewed_edition：`unresolved_count=1` → 失败。rework_impact_report：未知队列名 → 失败。

## 3. M7/M8 Schema（ACT 03–04）

- 3.1 release_manifest：`PUBLIC_RELEASE` + `source_release=dev` → 失败；`INTERNAL_DEMO` + `watermark=false` → 失败。
- 3.2 knowledge_data_pack：entry 的 `assertion_ids` 为空 → 失败；`PUBLIC_RELEASE` 下 status 为 machine_extracted → 失败；concepts 含 `rule_dsl` 键 → 失败。
- 3.3 evidence_map_pack：chain 缺 `source_anchor` → 失败。
- 3.4 anchor_contract_pack：`retired` 却有后继 → 失败；`split` 只有 1 个后继 → 失败；SourceSpan 稳定性写成 migratable → 失败。
- 3.5 source_asset_pack：`reference_and_hash_only` 且 `bytes_included=true` → 失败。query_contract_pack：少一个接口 → 失败。
- 3.6 stage_payload_m4..m8：出现 `candidate_set_path` 等以 `_path` 结尾的键 → 失败。

## 4. 金标生成（ACT 05–07）

- 4.1 Given 生成器，When 输出到临时目录两次，Then 两次字节完全相同，且与仓库 fixture `diff -r` 无输出。
- 4.2 m4 金标：2 个概念、2 条主张、3 条证据；mention 由 spans 推出；quote 逐字等于 span 文本。
- 4.3 m5 金标：G1/G2/G3/G5 passed，G4/G6 blocked；checks_passed=17。
- 4.4 m6 金标：5 个决定，approved 4 项；m7 Snapshot 与 m6 approved 一致；m8 为 3 条证据链、6 个子包。
- 4.5 每次生成后，`manifest.yaml`、`spans.yaml`、`expected/m1..m3` 五个哈希不变；fixture 内无图像；`SHA256SUMS` 覆盖 expected 下全部其他文件。

## 5. verify 扩展（ACT 08）

- 5.1 Given 规范 fixture，When `verify.sh`，Then 12 项 PASS、`FIXTURE OK`。
- 5.2 Given 篡改矩阵 20 例，Then 每例 exit 1 且命中指定检查名，`MUTATIONS 20/20`。
- 5.3 `m3-coverage.sh` 仍 exit 2；`run_all.sh` 仍 `SUMMARY pass=2 fail=1 blocked=8`。

## 6. 金标灌入（ACT 09）

- 6.1 Given `ingest(stages=m1..m8)`，Then 8 个 StepRun 全部 succeeded、2 个 ProcessingRun（edition_run f1、release_run f7）、30 个 Checkpoint、8 个 Transformation；8 个 StagePackage 修订字节等于对应 expected 文件。
- 6.2 Given 默认 `ingest()`，Then 行为与 impl-01/impl-02 完全一致（3 个 StepRun、9 个 Checkpoint），现有测试不改即通过。
- 6.3 Given `stages=("m1","m3")` 或 `("m4",)`，Then `SchemaViolation(SCH_002)`，Ledger 无写入。
- 6.4 Given `stages=m1..m6`，Then 5 个 human_event 修订号等于常量 de1–de5，m6 Checkpoint 的 human_decisions 逐个累积。
