#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

VENV_BIN="$REPO_ROOT/.venv/bin"
CHECK_JSONSCHEMA="$VENV_BIN/check-jsonschema"
PYTHON="$VENV_BIN/python"

if [ ! -x "$CHECK_JSONSCHEMA" ] || [ ! -x "$PYTHON" ]; then
    echo "ERROR: .venv environment not found or check-jsonschema not installed" >&2
    exit 1
fi

SCHEMA_DIR="openspec/schemas"
EXAMPLE_DIR="openspec/schemas/examples"

# Schema existence check
for schema in artifact_ref.schema.json stage_package.schema.json step_request.schema.json step_result.schema.json; do
    if [ ! -f "$SCHEMA_DIR/$schema" ]; then
        echo "ERROR: Required schema missing: $SCHEMA_DIR/$schema" >&2
        exit 1
    fi
done

# 1. Metaschema validation
"$CHECK_JSONSCHEMA" --check-metaschema "$SCHEMA_DIR"/*.schema.json > /dev/null
echo "PASS metaschema"

# 2. ArtifactRef validation
"$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/artifact_ref.schema.json" "$EXAMPLE_DIR/artifact_ref.valid.yaml" > /dev/null
echo "PASS artifact_ref_valid"

"$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/artifact_ref.schema.json" "$EXAMPLE_DIR/artifact_ref.stage_package.valid.yaml" > /dev/null
echo "PASS artifact_ref_stage_package_valid"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/artifact_ref.schema.json" "$EXAMPLE_DIR/artifact_ref.invalid_mixed_ids.yaml" > /dev/null 2>&1; then
    echo "FAIL: artifact_ref.invalid_mixed_ids.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS artifact_ref_invalid_mixed_ids"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/artifact_ref.schema.json" "$EXAMPLE_DIR/artifact_ref.invalid_missing_logical_id.yaml" > /dev/null 2>&1; then
    echo "FAIL: artifact_ref.invalid_missing_logical_id.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS artifact_ref_invalid_missing_logical_id"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/artifact_ref.schema.json" "$EXAMPLE_DIR/artifact_ref.invalid_unknown_field.yaml" > /dev/null 2>&1; then
    echo "FAIL: artifact_ref.invalid_unknown_field.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS artifact_ref_invalid_unknown_field"

# 3. StagePackage validation
"$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/stage_package.schema.json" "$EXAMPLE_DIR/qtbj_ed01.m1.stage_package.valid.yaml" > /dev/null
echo "PASS stage_package_valid"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/stage_package.schema.json" "$EXAMPLE_DIR/stage_package.invalid_stage_mismatch.yaml" > /dev/null 2>&1; then
    echo "FAIL: stage_package.invalid_stage_mismatch.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS stage_package_invalid_stage_mismatch"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/stage_package.schema.json" "$EXAMPLE_DIR/stage_package.invalid_missing_lineage.yaml" > /dev/null 2>&1; then
    echo "FAIL: stage_package.invalid_missing_lineage.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS stage_package_invalid_missing_lineage"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/stage_package.schema.json" "$EXAMPLE_DIR/stage_package.invalid_transformation.yaml" > /dev/null 2>&1; then
    echo "FAIL: stage_package.invalid_transformation.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS stage_package_invalid_transformation"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/stage_package.schema.json" "$EXAMPLE_DIR/stage_package.invalid_nested_ref.yaml" > /dev/null 2>&1; then
    echo "FAIL: stage_package.invalid_nested_ref.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS stage_package_invalid_nested_ref"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/stage_package.schema.json" "$EXAMPLE_DIR/stage_package.invalid_unknown_field.yaml" > /dev/null 2>&1; then
    echo "FAIL: stage_package.invalid_unknown_field.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS stage_package_invalid_unknown_field"

# 4. qtbj_manifest_binding
"$PYTHON" -c '
import yaml, sys

with open("pipeline/corpus/bazi/qtbj_ed01/manifest.yaml") as f:
    real_manifest = yaml.safe_load(f)

with open("openspec/schemas/examples/qtbj_ed01.m1.stage_package.valid.yaml") as f:
    stage_pkg = yaml.safe_load(f)

real_source_id = real_manifest.get("source_id")
pkg_source_id = stage_pkg.get("payload", {}).get("source_manifest", {}).get("source_id")
manifest_path = stage_pkg.get("payload", {}).get("source_manifest", {}).get("source_manifest_path")

assert real_source_id, "Real manifest missing source_id"
assert pkg_source_id == real_source_id, f"source_id mismatch: {pkg_source_id} != {real_source_id}"
assert manifest_path == "pipeline/corpus/bazi/qtbj_ed01/manifest.yaml", f"Invalid manifest path: {manifest_path}"
'
echo "PASS qtbj_manifest_binding"

# 5. stage_package_yaml_json_roundtrip
"$PYTHON" -c '
import yaml, json, tempfile, subprocess, sys, os

with open("openspec/schemas/examples/qtbj_ed01.m1.stage_package.valid.yaml") as f:
    data = yaml.safe_load(f)

with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp:
    json.dump(data, tmp)
    tmp_path = tmp.name

try:
    with open(tmp_path) as f:
        reloaded = json.load(f)

    assert reloaded.get("payload", {}).get("source_manifest", {}).get("source_id") == "src_qtbj_ed01"

    res = subprocess.run(["'"$CHECK_JSONSCHEMA"'", "--schemafile", "openspec/schemas/stage_package.schema.json", tmp_path], capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        sys.exit(1)
finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
'
echo "PASS stage_package_yaml_json_roundtrip"

# 6. StepRequest validation
"$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/step_request.schema.json" "$EXAMPLE_DIR/step_request.empty_inputs.valid.yaml" > /dev/null
echo "PASS step_request_empty_inputs"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/step_request.schema.json" "$EXAMPLE_DIR/step_request.invalid_missing_inputs.yaml" > /dev/null 2>&1; then
    echo "FAIL: step_request.invalid_missing_inputs.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS step_request_missing_inputs"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/step_request.schema.json" "$EXAMPLE_DIR/step_request.invalid_latest.yaml" > /dev/null 2>&1; then
    echo "FAIL: step_request.invalid_latest.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS step_request_invalid_latest"

"$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/step_request.schema.json" "$EXAMPLE_DIR/step_request.supersedes.valid.yaml" > /dev/null
echo "PASS step_request_supersedes"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/step_request.schema.json" "$EXAMPLE_DIR/step_request.invalid_supersedes.yaml" > /dev/null 2>&1; then
    echo "FAIL: step_request.invalid_supersedes.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS step_request_invalid_supersedes"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/step_request.schema.json" "$EXAMPLE_DIR/step_request.invalid_unknown_field.yaml" > /dev/null 2>&1; then
    echo "FAIL: step_request.invalid_unknown_field.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS step_request_invalid_unknown_field"

# 7. StepResult validation
"$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/step_result.schema.json" "$EXAMPLE_DIR/step_result.awaiting_human.valid.yaml" > /dev/null
echo "PASS step_result_awaiting_human"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/step_result.schema.json" "$EXAMPLE_DIR/step_result.invalid_missing_resume_token.yaml" > /dev/null 2>&1; then
    echo "FAIL: step_result.invalid_missing_resume_token.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS step_result_missing_resume_token"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/step_result.schema.json" "$EXAMPLE_DIR/step_result.invalid_missing_pending_queue.yaml" > /dev/null 2>&1; then
    echo "FAIL: step_result.invalid_missing_pending_queue.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS step_result_missing_pending_queue"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/step_result.schema.json" "$EXAMPLE_DIR/step_result.invalid_stale_token.yaml" > /dev/null 2>&1; then
    echo "FAIL: step_result.invalid_stale_token.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS step_result_stale_token"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/step_result.schema.json" "$EXAMPLE_DIR/step_result.invalid_failed_without_evidence.yaml" > /dev/null 2>&1; then
    echo "FAIL: step_result.invalid_failed_without_evidence.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS step_result_failed_without_evidence"

if "$CHECK_JSONSCHEMA" --schemafile "$SCHEMA_DIR/step_result.schema.json" "$EXAMPLE_DIR/step_result.invalid_unknown_field.yaml" > /dev/null 2>&1; then
    echo "FAIL: step_result.invalid_unknown_field.yaml should have failed schema validation" >&2
    exit 1
fi
echo "PASS step_result_invalid_unknown_field"

# 8. Schema structure assertions
"$PYTHON" -c '
import json, sys

with open("openspec/schemas/artifact_ref.schema.json") as f:
    aref = json.load(f)
with open("openspec/schemas/stage_package.schema.json") as f:
    spkg = json.load(f)
with open("openspec/schemas/step_request.schema.json") as f:
    sreq = json.load(f)
with open("openspec/schemas/step_result.schema.json") as f:
    sres = json.load(f)

defs = aref.get("$defs", {})

# Artifact 5 states
expected_artifact_statuses = {"draft", "sealed", "quarantined", "invalidated", "superseded"}
assert set(defs.get("artifactStatus", {}).get("enum", [])) == expected_artifact_statuses, "artifactStatus enum mismatch"

# StepRun 6 states
expected_step_statuses = {"running", "awaiting_human", "suspended", "succeeded", "failed", "superseded"}
assert set(defs.get("stepRunStatus", {}).get("enum", [])) == expected_step_statuses, "stepRunStatus enum mismatch"

# status_version.minimum = 1
assert sres.get("properties", {}).get("status_version", {}).get("minimum") == 1, "status_version minimum must be 1"

# All revision ID arrays have uniqueItems: true
assert sreq.get("properties", {}).get("input_artifact_ids", {}).get("uniqueItems") is True, "StepRequest input_artifact_ids uniqueItems must be true"
for field in ["output_artifact_ids", "validation_report_ids", "log_artifact_ids", "failure_artifact_ids", "pending_queue_artifact_ids"]:
    prop = sres.get("properties", {}).get(field, {})
    assert prop.get("uniqueItems") is True, f"StepResult {field} uniqueItems must be true"

trans_items = spkg.get("properties", {}).get("lineage", {}).get("properties", {}).get("transformations", {}).get("items", {})
assert trans_items.get("properties", {}).get("input_artifact_revision_ids", {}).get("uniqueItems") is True, "transformation input_artifact_revision_ids uniqueItems must be true"
assert trans_items.get("properties", {}).get("output_artifact_revision_ids", {}).get("uniqueItems") is True, "transformation output_artifact_revision_ids uniqueItems must be true"

# StagePackage top-level required
expected_spkg_required = {
    "schema_version", "stage_package_id", "artifact_revision_id", "stage",
    "status", "payload", "manifest", "validation", "lineage", "logs", "failures"
}
assert set(spkg.get("required", [])) == expected_spkg_required, "StagePackage required mismatch"

# All 4 top-levels additionalProperties: false
for name, s in [("artifact_ref", aref), ("stage_package", spkg), ("step_request", sreq), ("step_result", sres)]:
    assert s.get("additionalProperties") is False, f"{name} top-level must have additionalProperties: false"

# Closed envelopes additionalProperties: false
manifest_prop = spkg.get("properties", {}).get("manifest", {})
assert manifest_prop.get("additionalProperties") is False, "manifest must have additionalProperties: false"

validation_prop = spkg.get("properties", {}).get("validation", {})
assert validation_prop.get("additionalProperties") is False, "validation must have additionalProperties: false"

lineage_prop = spkg.get("properties", {}).get("lineage", {})
assert lineage_prop.get("additionalProperties") is False, "lineage must have additionalProperties: false"

assert trans_items.get("additionalProperties") is False, "transformation must have additionalProperties: false"

# Payload and counts allow extensions
counts_prop = manifest_prop.get("properties", {}).get("counts", {})
assert counts_prop.get("additionalProperties") is not False, "counts should allow stage-defined keys"
payload_prop = spkg.get("properties", {}).get("payload", {})
assert payload_prop.get("additionalProperties") is not False, "payload should allow stage-defined keys"
'
echo "PASS schema_structure"
echo "PASS d02_contracts"
