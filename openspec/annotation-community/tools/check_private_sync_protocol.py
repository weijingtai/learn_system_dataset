#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

EXPECTED_SECTIONS = [f"## {i}." for i in range(1, 10)]
EXPECTED_DECISIONS = [f"D-NC015-{i:02d}" for i in range(1, 10)]

EXPECTED_FILES = [
    "auth_valid.json",
    "auth_expired.json",
    "auth_revoked.json",
    "auth_device_mismatch.json",
    "auth_fingerprint_mismatch.json",
    "auth_scope_mismatch.json",
    "auth_dtls_mismatch.json",
    "auth_epoch_mismatch.json",
    "envelope_valid.json",
    "envelope_hash_mismatch.json",
    "envelope_bad_signature.json",
    "envelope_replay_seq.json",
    "envelope_oversize_inline.json",
    "envelope_aad_mismatch.json",
    "session_pub_bad_signature.json",
    "pairing_anonymous.json",
    "relay_ttl.json",
    "deletion_layers.json",
]

EXPECTED_CLOSED_SET = {
    "authorized",
    "deniedScopeMismatch",
    "deniedDtlsMismatch",
    "deniedBadSignature",
    "deniedRevokedOrUntrusted",
    "deniedEpochMismatch",
    "accept",
    "reject:hash_mismatch",
    "reject:bad_signature",
    "reject:aad_mismatch",
    "reject:schema_invalid",
    "reject:source_untrusted",
    "duplicate_ack",
    "session_key_unbound",
    "pairing_refused_anonymous",
    "config_ok",
    "layers_ok",
}

EXPECTED_SIGNED_FIELDS = [
    "envelope_version",
    "owner",
    "sender_device_id",
    "recipient_device_id",
    "seq",
    "note_id",
    "revision_id",
    "op",
    "created_at",
    "content_hash",
]


def check_protocol(contract_path: Path, fixtures_dir: Path) -> int:
    if not contract_path.is_file():
        sys.stderr.write(f"Contract file not found: {contract_path}\n")
        return 1

    contract_text = contract_path.read_text(encoding="utf-8")

    # 1. Check sections 1..9
    for sec in EXPECTED_SECTIONS:
        if sec not in contract_text:
            sys.stderr.write(f"Missing contract section heading: {sec}\n")
            return 1

    # 2. Check decisions D-NC015-01..09
    for dec in EXPECTED_DECISIONS:
        if dec not in contract_text:
            sys.stderr.write(f"Missing decision identifier: {dec}\n")
            return 1

    # 3. Check for TBD or 待定 outside inline code backticks
    text_without_code = re.sub(r"`[^`\n]*`", "", contract_text)
    if "TBD" in text_without_code:
        sys.stderr.write("Contract text contains placeholder: TBD\n")
        return 1
    if "待定" in text_without_code:
        sys.stderr.write("Contract text contains placeholder: 待定\n")
        return 1

    # 4. Check fixtures directory exists
    if not fixtures_dir.is_dir():
        sys.stderr.write(f"Fixtures directory not found: {fixtures_dir}\n")
        return 1

    # 5. Check all 18 files exist
    fixture_files = list(fixtures_dir.glob("*.json"))
    file_names = {f.name for f in fixture_files}

    for exp_file in EXPECTED_FILES:
        if exp_file not in file_names:
            sys.stderr.write(f"Missing fixture file: {exp_file}\n")
            return 1

    # 6. Check each fixture contains 'expected' and it belongs to CLOSED_SET
    for f in fixture_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            sys.stderr.write(f"Invalid JSON in {f.name}: {e}\n")
            return 1

        if not isinstance(data, dict):
            sys.stderr.write(f"Fixture root is not a JSON object: {f.name}\n")
            return 1

        if "expected" not in data:
            sys.stderr.write(f"Fixture missing 'expected' field: {f.name}\n")
            return 1

        exp_val = data["expected"]
        if exp_val not in EXPECTED_CLOSED_SET:
            sys.stderr.write(f"Fixture {f.name} 'expected' value '{exp_val}' not in closed set\n")
            return 1

    # 7. Check relay_ttl.json fields
    relay_ttl_path = fixtures_dir / "relay_ttl.json"
    relay_ttl_data = json.loads(relay_ttl_path.read_text(encoding="utf-8"))
    if relay_ttl_data.get("notifier_role") != "signaling_only":
        sys.stderr.write(f"relay_ttl.json notifier_role != signaling_only\n")
        return 1
    if relay_ttl_data.get("sender_fallback_seconds") != 300:
        sys.stderr.write(f"relay_ttl.json sender_fallback_seconds != 300\n")
        return 1
    if relay_ttl_data.get("storage_lifecycle_days") != 1:
        sys.stderr.write(f"relay_ttl.json storage_lifecycle_days != 1\n")
        return 1

    # 8. Check envelope_valid.json signed_fields
    env_valid_path = fixtures_dir / "envelope_valid.json"
    env_valid_data = json.loads(env_valid_path.read_text(encoding="utf-8"))
    signed_fields = env_valid_data.get("signed_fields")
    if signed_fields != EXPECTED_SIGNED_FIELDS:
        sys.stderr.write(f"envelope_valid.json signed_fields does not match contract §4.4 ten fields\n")
        return 1

    # 9. Check auth_valid.json accountBindingCertHash
    auth_valid_path = fixtures_dir / "auth_valid.json"
    auth_valid_data = json.loads(auth_valid_path.read_text(encoding="utf-8"))
    peer_auth = auth_valid_data.get("peer_auth", {})
    scope_uid = peer_auth.get("scopeUid", "")
    device_id = peer_auth.get("peerDeviceId", "")
    fingerprint = peer_auth.get("peerPublicKeyFingerprint", "")
    cert_hash = peer_auth.get("accountBindingCertHash", "")

    expected_hash = hashlib.sha256(f"{scope_uid}|{device_id}|{fingerprint}".encode("utf-8")).hexdigest()
    if cert_hash != expected_hash:
        sys.stderr.write(f"auth_valid.json accountBindingCertHash mismatch: {cert_hash} != {expected_hash}\n")
        return 1

    sample_count = len(EXPECTED_FILES)
    print(f"samples={sample_count}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check private sync protocol contract and fixtures")
    parser.add_argument("--contract", type=Path, default=None, help="Path to private_sync.md")
    parser.add_argument("--fixtures", type=Path, default=None, help="Path to fixtures/private_sync directory")
    args = parser.parse_args(argv)

    tools_dir = Path(__file__).resolve().parent
    repo_root = tools_dir.parents[2]

    contract_path = args.contract or (repo_root / "openspec/annotation-community/contracts/private_sync.md")
    fixtures_dir = args.fixtures or (repo_root / "openspec/annotation-community/fixtures/private_sync")

    return check_protocol(contract_path, fixtures_dir)


if __name__ == "__main__":
    sys.exit(main())
