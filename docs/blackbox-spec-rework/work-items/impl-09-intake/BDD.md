# BDD：impl-09 M1 电子文本入库 + M2 电子文本清洗

场景按 ACT 编号分组。「乾元秘旨片段」指殆知阁《乾元秘旨》md 文件的前若干节（约 5000 字符），source_site=daizhige.org。

## 1. M1 纯函数（ACT 00）

- 1.1 Given 合法 source_info（含 11 个必填键：source_id, work_title, edition_note, technique_id, rights_status, release_policy, edition_part, source_site, source_url, file_sha256, pages + 可选 repo_commit/yaml_metadata），When `load_source`，Then 返回键序固定的新 dict。Given 缺必填键、非法 URL、非法 SHA-256、重复页名、表外键，Then 分别以 SCH_001 / SCH_002 拒绝。
- 1.2 Given 合成文本文件（UTF-8），When `read_source_files`，Then 每项含 page, data, sha256, size。Given 缺文件，Then 一次性抛出 `SourceAssetMissing`，paths 按序列出全部缺失路径。
- 1.3 Given 合法 source_info 与文件列表，When `build_source_manifest`，Then 顶层键序固定（10 个键）；source_assets 键序固定（12 个键：page, path_ref, sha256, size, width, height, object_store, in_git, yaml_metadata, source_site, source_url, repo_commit）；顶层不含 source_sites；files == []。
- 1.4 Given dump_manifest_yaml 写出后 safe_load 回来，Then 字节相同；全局 SafeDumper 未被修改。

## 2. M1 事务（ACT 01）

- 2.1 Given 合法 source_info 与文件，When `run_m1`，Then：manifest_revision_id 非空；raw_text_revision_ids 非空；step_run_id 非空。
- 2.2 Given 同一 edition_part_id 已跑过 M1，Then 第二次 `IntakeRefused("M1 已封存")`，零写入。
- 2.3 Given begin 后文件被改，Then StepRun `failed`，failed_check 为 `input_contract`；无 StagePackage。
- 2.4 Given CLI：成功 exit 0，末行 "M1 OK"；缺文件 exit 3，"BLOCKED_SOURCE_ASSET_MISSING"。

## 3. M2 清洗纯函数（ACT 02）

- 3.1 Given 含 `?` 的文本，When `clean_text`，Then findings 含 kind=replacement_char 的记录，raw_start/raw_end 指向 `?` 位置。
- 3.2 Given 含 PUA 字符（U+E000–U+F8FF）的文本，Then findings 含 kind=private_use_area。
- 3.3 Given 含 Markdown 转义残留（`\-`、`\[`）的文本，Then findings 含 kind=escape_residue。
- 3.4 Given 含零宽字符（U+200B）的文本，Then findings 含 kind=control_char。
- 3.5 Given 含繁简混杂的文本，Then findings 含 kind=variant_mixed。
- 3.6 Given 含疑似形近误字（「日」与「曰」上下文）的文本，Then findings 含 kind=suspected_error。
- 3.7 Given 无问题文本，Then findings 为空。
- 3.8 Given 含 deferred 终态的 findings，Then summary.deferred_count > 0。
- 3.9 When `build_patches`，Then patches 与 findings 的 patch_id 一一对应；apply_patches(raw, patches) == cleaned（可逆性）。
- 3.10 When `build_sanitization_report`，Then finding 键序固定；summary 各 kind 计数 == 实际 findings 数。

## 4. M2 Gate（ACT 03）

- 4.1 Given 无 deferred findings 的 report，Then `evaluate_m2_gate` 返回 passed=True。
- 4.2 Given 含 deferred findings 的 report，Then passed=False，"no_deferred"。
- 4.3 Given findings 含非法 kind，Then passed=False，"findings_valid"。
- 4.4 Given findings 的 patch_id 不在 patches 中，Then passed=False，"patches_consistent"。
- 4.5 Given summary 计数不符，Then passed=False，"summary_consistent"。
- 4.6 Given 缺 findings 键的 report，Then passed=False，"report_valid"。
- 4.7 gate.py 不 import cleaner/patcher/reporter/raw_text。

## 5. M2 事务（ACT 04）

- 5.1 Given M1 已成功、raw_text_revision_id 有效，When `run_m2`，Then：cleaned_revision_id, patch_revision_id, report_revision_id 非空；gate_result.passed=True。
- 5.2 Given raw_text 不存在，Then `DigitizationRefused`。
- 5.3 Given 同一 edition_part_id 已跑过 M2，Then `DigitizationRefused`，零写入。
- 5.4 Given begin 后 raw_text 被改，Then failed_check 为 `input_contract`。
- 5.5 Given CLI：成功 exit 0，"M2 OK"；Gate 失败 exit 1。

## 6. M2 决定表（ACT 05）

- 6.1 Given 合法决定表（schema_version=1.0.0, entries 含 page/terminal_state/reason/decided_by），When `load_decisions`，Then 返回键序固定。
- 6.2 Given 缺键、非法 terminal_state、空 reason，Then 分别以 SCH_001 / SCH_002 拒绝。
- 6.3 Given deferred findings 有对应决定，When `check_decisions_coverage`，Then 返回空列表。
- 6.4 Given deferred findings 无对应决定，Then 返回缺决定的 finding_id 列表。

## 7. 来源不可区分（ACT 06）

- 7.1 Given M1→M2 在 Ledger 上成功，When `resolve_m3_inputs`，Then 解析出 source_manifest 与 cleaned_text_revision。
- 7.2 M2 运行后 raw_text 修订不变（冻结保证）。
- 7.3 cleaned_text != raw_text（清洗有实际效果）。

## 8. 验收脚本（ACT 07）

- 8.1 Given 无真实素材，When `m1-intake.sh`，Then BLOCKED 行，exit 2。
- 8.2 Given 无真实素材，When `m2-sanitization.sh`，Then BLOCKED 行，exit 2。
- 8.3 Given 真实素材齐全（乾元秘旨片段），When `m1-intake.sh`，Then 全 PASS，exit 0。
- 8.4 Given 真实素材齐全，When `m2-sanitization.sh`，Then 全 PASS，exit 0；§4.4 十三项各至少一条 finding。
