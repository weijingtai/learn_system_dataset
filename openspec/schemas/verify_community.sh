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

echo "PASS community_all"
