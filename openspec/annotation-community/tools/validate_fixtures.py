#!/usr/bin/env python3
import sys
import os
import json
import re
from pathlib import Path

WANT_FILES = {
    "command_id_cases.json",
    "comment_reply_cases.json",
    "content_hash_cases.json",
    "id_format_cases.json",
    "lifecycle_transition_cases.json",
    "limit_cases.json",
    "mention_cases.json",
    "revision_cases.json",
    "state_combinations.json"
}

STATE_KEYS = {
    "visibility", "lifecycle", "moderation_state", "state", "from", "to",
    "editor_state", "delivery_state", "pending_op", "status",
    "content_visibility", "head_becomes"
}

ALLOW_EXTRA = {"new"}

NON_BUSINESS = {
    "user_id", "account_id", "actor_id", "author_id", "recipient_id",
    "block_id", "entity_id", "device_id", "attachment_id", "command_id",
    "event_id", "object_id", "reporter_id", "target_id", "target_ref",
    "notifier_delivery_id", "public_profile_id"
}

BIZ_ID_RE = re.compile(r"^(note|nrev|pub|cacc|cbnd|anc|ares|thr|cmt|crev|rct|bmk|shr|bkm|ntf|bev|psn)_[0-9a-f]{32}$")
CMD_ID_RE = re.compile(r"^cmd_[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CANONICAL_HEX_RE = re.compile(r"^([0-9a-f]{2})+$")

def load_enum_table(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"state-machines.md not found at {path}")
    content = path.read_text(encoding="utf-8")
    m_enum = re.search(r"## 枚举总表.*?\n\|.*?\n\|[-| ]+\n((?:\|[^\n]*\n)+)", content, re.S)
    if not m_enum:
        raise ValueError("Could not find enum table in state-machines.md")
    rows = [r for r in m_enum.group(1).split("\n") if r.startswith("|")]
    enum_values = set()
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]
        if len(cells) > 3:
            tokens = re.findall(r"`([^`]+)`", cells[3])
            enum_values.update(tokens)
    return rows, enum_values

def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: validate_fixtures.py <fixture_dir>\n")
        sys.exit(2)

    fix_dir = Path(sys.argv[1])
    if not fix_dir.is_dir():
        sys.stderr.write(f"Error: fixture directory does not exist or is not a directory: {fix_dir}\n")
        sys.exit(2)

    sm_path = (fix_dir / "../../contracts/state-machines.md").resolve()
    if not sm_path.is_file():
        sys.stderr.write(f"Error: state-machines.md not found at {sm_path}\n")
        sys.exit(2)

    try:
        rows, enum_values = load_enum_table(sm_path)
    except Exception as e:
        sys.stderr.write(f"Error parsing state-machines.md: {e}\n")
        sys.exit(2)

    actual_files = {p.name for p in fix_dir.glob("*.json")}
    problems = []

    # V7
    if actual_files != WANT_FILES:
        problems.append("unexpected fixture set")

    total_files = len(actual_files & WANT_FILES)
    total_cases = 0

    for fname in sorted(actual_files & WANT_FILES):
        fpath = fix_dir / fname
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            problems.append(f"{fname}: invalid json")
            continue

        if not isinstance(data, dict):
            problems.append(f"{fname}: invalid json")
            continue

        skip_keys = set()
        if fname == "id_format_cases.json":
            skip_keys = {"value"}
        elif fname == "command_id_cases.json":
            skip_keys = {"value", "header", "body"}

        def walk(obj, path, case_id):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in skip_keys:
                        continue
                    # V3
                    if k in STATE_KEYS and isinstance(v, str):
                        if v not in enum_values and v not in ALLOW_EXTRA:
                            problems.append(f"{fname}#{case_id}: unknown state value '{v}' at {path}.{k}")
                    # V4
                    if (k.endswith("_id") or k.endswith("_ids") or k in ("heads", "heads_after")) and k not in NON_BUSINESS:
                        vals = v if isinstance(v, list) else [v]
                        for val in vals:
                            if isinstance(val, str):
                                ok_id = bool(BIZ_ID_RE.match(val))
                                if not ok_id and k == "artifact_revision_id":
                                    ok_id = bool(re.match(r"^rev_[0-9a-f]{32}$", val))
                                if not ok_id and k == "release_id":
                                    ok_id = bool(re.match(r"^rel_[0-9a-f]{32}$", val))
                                if not ok_id:
                                    problems.append(f"{fname}#{case_id}: bad id '{val}' at {path}.{k}")
                    # V5
                    if k == "command_id" and isinstance(v, str):
                        if not CMD_ID_RE.match(v):
                            problems.append(f"{fname}#{case_id}: bad command_id at {path}.{k}")
                    walk(v, f"{path}.{k}", case_id)
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    walk(item, f"{path}[{idx}]", case_id)

        if fname == "content_hash_cases.json":
            cases = data.get("cases", [])
            for idx, c in enumerate(cases):
                total_cases += 1
                cid = c.get("name", idx) if isinstance(c, dict) else idx
                if not isinstance(c, dict) or "expected_hash" not in c or not HEX64_RE.match(str(c.get("expected_hash", ""))):
                    problems.append(f"{fname}#{cid}: missing expected_hash")
                if not isinstance(c, dict) or "expected_canonical_hex" not in c or not CANONICAL_HEX_RE.match(str(c.get("expected_canonical_hex", ""))):
                    problems.append(f"{fname}#{cid}: missing expected_canonical_hex")
                walk(c, "", cid)

            # V6 equal_hash_to
            by_name = {c["name"]: c for c in cases if isinstance(c, dict) and "name" in c}
            for c in cases:
                if isinstance(c, dict):
                    eq = c.get("equal_hash_to")
                    cid = c.get("name")
                    if eq is not None:
                        if eq not in by_name:
                            problems.append(f"{fname}#{cid}: equal_hash_to missing target")
                        elif by_name[eq].get("expected_hash") != c.get("expected_hash"):
                            problems.append(f"{fname}#{cid}: equal_hash_to mismatch")

            vectors = data.get("encoding_vectors", [])
            for idx, v in enumerate(vectors):
                total_cases += 1
                vid = v.get("name", idx) if isinstance(v, dict) else idx
                if not isinstance(v, dict) or "expected_bytes_hex" not in v:
                    problems.append(f"{fname}#{vid}: missing expected_bytes_hex")
                walk(v, "", vid)

            inv_snaps = data.get("invalid_snapshots", [])
            for idx, v in enumerate(inv_snaps):
                total_cases += 1
                vid = v.get("name", idx) if isinstance(v, dict) else idx
                if not isinstance(v, dict) or "reason" not in v:
                    problems.append(f"{fname}#{vid}: missing reason")
                walk(v, "", vid)

            inv_texts = data.get("invalid_json_texts", [])
            for idx, v in enumerate(inv_texts):
                total_cases += 1
                vid = v.get("name", idx) if isinstance(v, dict) else idx
                if not isinstance(v, dict) or "text" not in v or not isinstance(v.get("text"), str):
                    problems.append(f"{fname}#{vid}: missing text")
                if not isinstance(v, dict) or "reason" not in v:
                    problems.append(f"{fname}#{vid}: missing reason")
                walk(v, "", vid)
        else:
            cases = data.get("cases", [])
            for idx, c in enumerate(cases):
                total_cases += 1
                cid = c.get("name", idx) if isinstance(c, dict) else idx
                if not isinstance(c, dict) or "expected" not in c:
                    problems.append(f"{fname}#{cid}: missing expected")
                walk(c, "", cid)

    if problems:
        for p in sorted(set(problems)):
            print(p)
        sys.exit(1)

    print(f"FIXTURES_OK {total_files} files {total_cases} cases")
    sys.exit(0)

if __name__ == "__main__":
    main()
