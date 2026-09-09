# D-02 TDD 与验证门禁

## ACT 01：ArtifactRef 与 StagePackage

1. 先建立正反 fixture 与 `verify.sh`，但不创建两份 Schema。
2. 运行 `bash openspec/schemas/verify.sh`，必须因 Schema 缺失而非环境原因失败。
3. 添加 JSON Schema，直到元 Schema、正例、反例、真实 manifest 对照和 YAML→JSON round-trip 全部通过。

## ACT 02：StepRequest 与 StepResult

1. 先把全部 ACT02 Step 正反 fixture 登记到 `verify.sh`，但不创建两份 Schema。
2. 运行验证，必须因 Step Schema 缺失失败。
3. 添加 JSON Schema，直到空输入正例、非法 latest、人工等待缺 token、失败无证据等门禁全部符合预期。

## Required commands

```bash
python3 -m pip install -r pipeline/requirements.txt
bash openspec/schemas/verify.sh
git diff --check
```

期望：`verify.sh` 退出 0，并逐项输出以下 PASS 标签：

```text
PASS metaschema
PASS artifact_ref_valid
PASS artifact_ref_stage_package_valid
PASS artifact_ref_invalid_mixed_ids
PASS artifact_ref_invalid_missing_logical_id
PASS artifact_ref_invalid_unknown_field
PASS stage_package_valid
PASS stage_package_invalid_stage_mismatch
PASS stage_package_invalid_missing_lineage
PASS stage_package_invalid_transformation
PASS stage_package_invalid_nested_ref
PASS stage_package_invalid_unknown_field
PASS qtbj_manifest_binding
PASS stage_package_yaml_json_roundtrip
PASS step_request_empty_inputs
PASS step_request_missing_inputs
PASS step_request_invalid_latest
PASS step_request_supersedes
PASS step_request_invalid_supersedes
PASS step_request_invalid_unknown_field
PASS step_result_awaiting_human
PASS step_result_missing_resume_token
PASS step_result_missing_pending_queue
PASS step_result_stale_token
PASS step_result_failed_without_evidence
PASS step_result_invalid_unknown_field
PASS schema_structure
PASS d02_contracts
```

## Global regression

```bash
set +e
output=$(bash docs/blackbox-spec-rework/verify-T.sh 2>&1)
code=$?
set -e
count=$(printf '%s\n' "$output" | sed -n 's/^FAIL 合计: \([0-9][0-9]*\)$/\1/p')
test "$(printf '%s\n' "$output" | grep -c '^FAIL 合计: ')" -eq 1
test -n "$count"
test "$code" -eq "$count"
test "$count" -le 17
```

D-02 不负责清除其他 T 类失败；只要求没有新增失败。最终还必须检查：

```bash
test "$(find openspec/schemas -maxdepth 1 -name '*.schema.json' | wc -l | tr -d ' ')" = 4
rg -n 'artifact_ref.schema.json|step_request.schema.json|step_result.schema.json|stage_package.schema.json|openspec/schemas/verify.sh' openspec/learn-system-blackbox-architecture.md
```

## Anti-fake-green review

- 每个 invalid fixture 必须在 `check-jsonschema` 返回非零时才打印 PASS；若反例反而通过，脚本必须退出非零。
- round-trip 必须实际生成临时 JSON 并再次校验，不能只做 YAML parse。
- `qtbj_manifest_binding` 必须实际读取真实 manifest，不能把两边期望值都硬编码在脚本里。
- 不允许 `|| true` 吞掉有效 fixture 的失败。
