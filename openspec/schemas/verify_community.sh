#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

VENV_BIN="$REPO_ROOT/.venv/bin"
CJ="$VENV_BIN/check-jsonschema"
PY="$VENV_BIN/python"

if [ ! -x "$CJ" ] || [ ! -x "$PY" ]; then
    echo "ERROR: .venv environment not found or check-jsonschema not installed" >&2
    exit 1
fi

SCHEMA_DIR="openspec/schemas"
EXAMPLE_DIR="openspec/schemas/examples"
BASE_URI="file://$REPO_ROOT/openspec/schemas/"

# 1. Metaschema validation
"$CJ" --check-metaschema "$SCHEMA_DIR"/community_*.schema.json > /dev/null
echo "PASS community_metaschema"

# 2. Valid examples (excluding community_pair_*)
for file in $(find "$EXAMPLE_DIR" -maxdepth 1 -name "community_*.valid*.yaml" | sort); do
    fname="$(basename "$file")"
    case "$fname" in
        community_pair_*)
            continue
            ;;
    esac

    schema_name="${fname%%.*}"
    schema_file="$SCHEMA_DIR/${schema_name}.schema.json"
    tag="${fname%.yaml}"
    tag="${tag//./_}"

    "$CJ" --base-uri "$BASE_URI" --schemafile "$schema_file" "$file" > /dev/null
    echo "PASS ${tag}"
done

# 3. Invalid examples (excluding community_pair_*, community_note.invalid_preferred_head_not_in_heads.yaml, community_note_revision.invalid_range_end_le_start.yaml)
for file in $(find "$EXAMPLE_DIR" -maxdepth 1 -name "community_*.invalid_*.yaml" | sort); do
    fname="$(basename "$file")"
    case "$fname" in
        community_pair_*|community_note.invalid_preferred_head_not_in_heads.yaml|community_note_revision.invalid_range_end_le_start.yaml)
            continue
            ;;
    esac

    schema_name="${fname%%.*}"
    schema_file="$SCHEMA_DIR/${schema_name}.schema.json"
    tag="${fname%.yaml}"
    tag="${tag//./_}"

    if "$CJ" --base-uri "$BASE_URI" --schemafile "$schema_file" "$file" > /dev/null 2>&1; then
        echo "FAIL: ${fname} should have failed schema validation" >&2
        exit 1
    fi
    echo "PASS ${tag}"
done

# 4. Structure block
"$PY" - <<'PY'
import sys, os, glob, json, yaml, warnings
warnings.filterwarnings("ignore")
import jsonschema
from pathlib import Path
from jsonschema.validators import validator_for

REPO_ROOT = os.getcwd()
SCHEMA_DIR = os.path.join(REPO_ROOT, "openspec/schemas")
EXAMPLE_DIR = os.path.join(REPO_ROOT, "openspec/schemas/examples")
all_ok = True

# 4(a) Schema additionalProperties: false check with 3 exemptions
exempt_pointers = [
    ("community_command_record.schema.json", "#/properties/resource_ids"),
    ("community_command_record.schema.json", "#/properties/result_fields"),
    ("community_behavior_event.schema.json", "#/properties/attributes"),
]

def check_schema_objects(sf_path):
    sf_name = os.path.basename(sf_path)
    with open(sf_path, "r", encoding="utf-8") as f:
        schema_data = json.load(f)

    errs = []
    def check_node(node, path):
        is_exempt = False
        for ex_file, ex_prefix in exempt_pointers:
            if sf_name == ex_file and path.startswith(ex_prefix):
                is_exempt = True
                break

        if isinstance(node, dict):
            if node.get("type") == "object":
                if is_exempt:
                    if node.get("additionalProperties") is False:
                        errs.append(f"{path}: exempt must not be false")
                else:
                    if node.get("additionalProperties") is not False:
                        errs.append(f"{path}: must be false")
            for k, v in node.items():
                check_node(v, f"{path}/{k}")
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                check_node(item, f"{path}/{idx}")

    check_node(schema_data, "#")
    return errs

for sf in sorted(glob.glob(os.path.join(SCHEMA_DIR, "community_*.schema.json"))):
    sf_name = os.path.basename(sf)
    errs = check_schema_objects(sf)
    if not errs:
        print(f"CHECK 4(a) {sf_name} PASS")
    else:
        print(f"CHECK 4(a) {sf_name} FAIL: {errs}")
        all_ok = False

# 4(b) Note preferred_head_id in head_revision_ids
# Evaluated strictly on valid.yaml (must hold) and invalid_preferred_head_not_in_heads.yaml (must not hold)
with open(os.path.join(EXAMPLE_DIR, "community_note.valid.yaml"), "r", encoding="utf-8") as f:
    note_valid = yaml.safe_load(f)
ok_4b_valid = note_valid.get("preferred_head_id") in note_valid.get("head_revision_ids", [])
if ok_4b_valid:
    print("CHECK 4(b) community_note.valid.yaml PASS")
else:
    print("CHECK 4(b) community_note.valid.yaml FAIL")
    all_ok = False

with open(os.path.join(EXAMPLE_DIR, "community_note.invalid_preferred_head_not_in_heads.yaml"), "r", encoding="utf-8") as f:
    note_inv = yaml.safe_load(f)
ok_4b_inv = note_inv.get("preferred_head_id") not in note_inv.get("head_revision_ids", [])
if ok_4b_inv:
    print("CHECK 4(b) community_note.invalid_preferred_head_not_in_heads.yaml PASS")
else:
    print("CHECK 4(b) community_note.invalid_preferred_head_not_in_heads.yaml FAIL")
    all_ok = False

# 4(c) Paired files: note.kind=annotation => revision.bindings has anchor with object
schema_dir_path = Path(SCHEMA_DIR).resolve()
def load_validator(schema_path):
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    cls = validator_for(schema)
    resolver = jsonschema.RefResolver(base_uri=f"file://{schema_dir_path}/", referrer=schema)
    return cls(schema, resolver=resolver)

v_note = load_validator(schema_dir_path / "community_note.schema.json")
v_nrev = load_validator(schema_dir_path / "community_note_revision.schema.json")

def check_pair(pair_file, must_satisfy):
    with open(pair_file, "r", encoding="utf-8") as f:
        pair_data = yaml.safe_load(f)
    n = pair_data.get("note", {})
    r = pair_data.get("revision", {})
    v_note.validate(n)
    v_nrev.validate(r)
    has_anchor = False
    if n.get("kind") == "annotation":
        has_anchor = any(isinstance(b.get("anchor"), dict) for b in r.get("bindings", []))
    else:
        has_anchor = True
    return has_anchor if must_satisfy else (not has_anchor)

pair_valid_file = os.path.join(EXAMPLE_DIR, "community_pair_annotation.valid.yaml")
pair_inv_file = os.path.join(EXAMPLE_DIR, "community_pair_annotation.invalid_no_anchor.yaml")

if check_pair(pair_valid_file, True):
    print("CHECK 4(c) community_pair_annotation.valid.yaml PASS")
else:
    print("CHECK 4(c) community_pair_annotation.valid.yaml FAIL")
    all_ok = False

if check_pair(pair_inv_file, False):
    print("CHECK 4(c) community_pair_annotation.invalid_no_anchor.yaml PASS")
else:
    print("CHECK 4(c) community_pair_annotation.invalid_no_anchor.yaml FAIL")
    all_ok = False

# 4(d) Selector ranges end > start
def ranges_valid(rev):
    for b in rev.get("bindings", []):
        if not isinstance(b, dict): continue
        anc = b.get("anchor")
        if isinstance(anc, dict):
            sel = anc.get("selector")
            if isinstance(sel, dict):
                for r in sel.get("ranges", []):
                    if isinstance(r, dict) and "start" in r and "end" in r:
                        try:
                            if not (float(r["end"]) > float(r["start"])):
                                return False
                        except (ValueError, TypeError):
                            return False
    return True

for rf in sorted(glob.glob(os.path.join(EXAMPLE_DIR, "community_note_revision.*.yaml"))):
    rf_name = os.path.basename(rf)
    with open(rf, "r", encoding="utf-8") as f:
        rev_data = yaml.safe_load(f)
    if rf_name == "community_note_revision.invalid_range_end_le_start.yaml":
        ok_4d = not ranges_valid(rev_data)
    else:
        ok_4d = ranges_valid(rev_data)
    if ok_4d:
        print(f"CHECK 4(d) {rf_name} PASS")
    else:
        print(f"CHECK 4(d) {rf_name} FAIL")
        all_ok = False

for pf in [pair_valid_file, pair_inv_file]:
    pf_name = os.path.basename(pf)
    with open(pf, "r", encoding="utf-8") as f:
        rev_data = yaml.safe_load(f).get("revision", {})
    ok_4d = ranges_valid(rev_data)
    if ok_4d:
        print(f"CHECK 4(d) {pf_name} PASS")
    else:
        print(f"CHECK 4(d) {pf_name} FAIL")
        all_ok = False

if all_ok:
    print("PASS community_structure")
else:
    sys.exit(1)
PY

echo "PASS community_all"
