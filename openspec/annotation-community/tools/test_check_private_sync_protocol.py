#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import check_private_sync_protocol

REPO_ROOT = TOOLS_DIR.parents[2]
CONTRACT_PATH = REPO_ROOT / "openspec/annotation-community/contracts/private_sync.md"
FIXTURES_DIR = REPO_ROOT / "openspec/annotation-community/fixtures/private_sync"
CONTENT_HASH_CASES_PATH = REPO_ROOT / "openspec/annotation-community/fixtures/community/content_hash_cases.json"


class TestCheckPrivateSyncProtocol(unittest.TestCase):

    def test_green_on_real_contract_and_fixtures(self):
        exit_code = check_private_sync_protocol.main([
            "--contract", str(CONTRACT_PATH),
            "--fixtures", str(FIXTURES_DIR)
        ])
        self.assertEqual(exit_code, 0)

    def test_auth_samples_have_required_fields(self):
        auth_files = [
            "auth_valid.json",
            "auth_expired.json",
            "auth_revoked.json",
            "auth_device_mismatch.json",
            "auth_fingerprint_mismatch.json",
            "auth_scope_mismatch.json",
            "auth_dtls_mismatch.json",
            "auth_epoch_mismatch.json"
        ]
        expected_map = {
            "auth_valid.json": "authorized",
            "auth_expired.json": "deniedRevokedOrUntrusted",
            "auth_revoked.json": "deniedRevokedOrUntrusted",
            "auth_device_mismatch.json": "deniedRevokedOrUntrusted",
            "auth_fingerprint_mismatch.json": "deniedBadSignature",
            "auth_scope_mismatch.json": "deniedScopeMismatch",
            "auth_dtls_mismatch.json": "deniedDtlsMismatch",
            "auth_epoch_mismatch.json": "deniedEpochMismatch"
        }
        req_auth_keys = {
            "scopeUid", "peerDeviceId", "peerPublicKeyFingerprint",
            "accountBindingCertHash", "keyEpoch", "trustState", "expiresAtUtcMs"
        }
        req_session_keys = {
            "localScopeUid", "peerScopeUid", "peerDeviceId", "peerFingerprint",
            "peerKeyEpoch", "dtlsBindingValid", "signatureValid", "nowUtcMs"
        }
        for fname in auth_files:
            fpath = FIXTURES_DIR / fname
            data = json.loads(fpath.read_text(encoding="utf-8"))
            self.assertIn("peer_auth", data)
            self.assertIn("session", data)
            self.assertIn("expected", data)
            self.assertEqual(set(data["peer_auth"].keys()), req_auth_keys)
            self.assertEqual(set(data["session"].keys()), req_session_keys)
            self.assertEqual(data["expected"], expected_map[fname])

        av = json.loads((FIXTURES_DIR / "auth_valid.json").read_text(encoding="utf-8"))
        pa = av["peer_auth"]
        expected_cert_hash = hashlib.sha256(
            f"{pa['scopeUid']}|{pa['peerDeviceId']}|{pa['peerPublicKeyFingerprint']}".encode("utf-8")
        ).hexdigest()
        self.assertEqual(pa["accountBindingCertHash"], expected_cert_hash)

    def test_expired_sample_now_after_expiry(self):
        data = json.loads((FIXTURES_DIR / "auth_expired.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(data["session"]["nowUtcMs"], data["peer_auth"]["expiresAtUtcMs"])
        self.assertEqual(data["expected"], "deniedRevokedOrUntrusted")

    def test_mismatch_samples_differ_in_exactly_one_field(self):
        dev_data = json.loads((FIXTURES_DIR / "auth_device_mismatch.json").read_text(encoding="utf-8"))
        self.assertNotEqual(dev_data["session"]["peerDeviceId"], dev_data["peer_auth"]["peerDeviceId"])
        self.assertEqual(dev_data["session"]["peerFingerprint"], dev_data["peer_auth"]["peerPublicKeyFingerprint"])
        self.assertEqual(dev_data["session"]["peerKeyEpoch"], dev_data["peer_auth"]["keyEpoch"])
        self.assertEqual(dev_data["session"]["peerScopeUid"], dev_data["peer_auth"]["scopeUid"])
        self.assertEqual(dev_data["session"]["localScopeUid"], dev_data["peer_auth"]["scopeUid"])
        self.assertEqual(dev_data["expected"], "deniedRevokedOrUntrusted")

        fp_data = json.loads((FIXTURES_DIR / "auth_fingerprint_mismatch.json").read_text(encoding="utf-8"))
        self.assertNotEqual(fp_data["session"]["peerFingerprint"], fp_data["peer_auth"]["peerPublicKeyFingerprint"])
        self.assertEqual(fp_data["session"]["peerDeviceId"], fp_data["peer_auth"]["peerDeviceId"])
        self.assertEqual(fp_data["session"]["peerKeyEpoch"], fp_data["peer_auth"]["keyEpoch"])
        self.assertEqual(fp_data["session"]["peerScopeUid"], fp_data["peer_auth"]["scopeUid"])
        self.assertEqual(fp_data["session"]["localScopeUid"], fp_data["peer_auth"]["scopeUid"])
        self.assertEqual(fp_data["expected"], "deniedBadSignature")

    def test_valid_envelope_hash_matches_nc002_fixture(self):
        env_data = json.loads((FIXTURES_DIR / "envelope_valid.json").read_text(encoding="utf-8"))
        hash_cases = json.loads(CONTENT_HASH_CASES_PATH.read_text(encoding="utf-8"))
        expected_nc002_hash = hash_cases["cases"][0]["expected_hash"]

        self.assertEqual(env_data["content_hash"], expected_nc002_hash)
        self.assertRegex(env_data["signature"], r"^[0-9a-f]{128}$")
        self.assertEqual(env_data["cipher"]["alg"], "AES-256-GCM")
        expected_signed_fields = [
            "envelope_version",
            "owner",
            "sender_device_id",
            "recipient_device_id",
            "seq",
            "note_id",
            "revision_id",
            "op",
            "created_at",
            "content_hash"
        ]
        self.assertEqual(env_data["signed_fields"], expected_signed_fields)
        self.assertEqual(env_data["expected"], "accept")

    def test_hash_mismatch_has_probe_and_same_signature(self):
        valid = json.loads((FIXTURES_DIR / "envelope_valid.json").read_text(encoding="utf-8"))
        mismatch = json.loads((FIXTURES_DIR / "envelope_hash_mismatch.json").read_text(encoding="utf-8"))
        self.assertEqual(mismatch["signature"], valid["signature"])
        self.assertEqual(mismatch["content_hash"], valid["content_hash"])
        self.assertIn("decrypted_content_hash", mismatch)
        self.assertNotEqual(mismatch["decrypted_content_hash"], mismatch["content_hash"])
        self.assertEqual(mismatch["expected"], "reject:hash_mismatch")

    def test_bad_signature_differs_in_signed_field(self):
        valid = json.loads((FIXTURES_DIR / "envelope_valid.json").read_text(encoding="utf-8"))
        bad_sig = json.loads((FIXTURES_DIR / "envelope_bad_signature.json").read_text(encoding="utf-8"))
        self.assertEqual(bad_sig["signature"], valid["signature"])
        self.assertNotEqual(bad_sig["content_hash"], valid["content_hash"])
        diff_count = sum(1 for a, b in zip(bad_sig["content_hash"], valid["content_hash"]) if a != b)
        self.assertEqual(diff_count, 1)
        self.assertEqual(bad_sig["expected"], "reject:bad_signature")

    def test_replay_shares_note_and_revision(self):
        valid = json.loads((FIXTURES_DIR / "envelope_valid.json").read_text(encoding="utf-8"))
        replay = json.loads((FIXTURES_DIR / "envelope_replay_seq.json").read_text(encoding="utf-8"))
        self.assertEqual(replay["note_id"], valid["note_id"])
        self.assertEqual(replay["revision_id"], valid["revision_id"])
        self.assertNotEqual(replay["seq"], valid["seq"])
        self.assertEqual(replay["expected"], "duplicate_ack")

    def test_oversize_inline_is_262145(self):
        oversize = json.loads((FIXTURES_DIR / "envelope_oversize_inline.json").read_text(encoding="utf-8"))
        self.assertEqual(oversize["inline_cipher_bytes"], 262145)
        self.assertEqual(oversize["expected"], "reject:schema_invalid")

    def test_relay_ttl_and_deletion_layers(self):
        ttl = json.loads((FIXTURES_DIR / "relay_ttl.json").read_text(encoding="utf-8"))
        self.assertEqual(ttl["notifier_role"], "signaling_only")
        self.assertEqual(ttl["sender_fallback_seconds"], 300)
        self.assertEqual(ttl["storage_lifecycle_days"], 1)
        self.assertEqual(ttl["expected"], "config_ok")

        layers = json.loads((FIXTURES_DIR / "deletion_layers.json").read_text(encoding="utf-8"))
        self.assertEqual(len(layers["layers"]), 3)
        executors = [l["executor"] for l in layers["layers"]]
        self.assertEqual(executors, ["receiver", "sender", "platform"])
        self.assertEqual(layers["expected"], "layers_ok")

    def test_missing_section_or_decision_or_tbd_fails(self):
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            tmp_contract = tmp_dir / "private_sync.md"
            contract_text = CONTRACT_PATH.read_text(encoding="utf-8")

            # Sub-assertion 1: Missing section heading ## 6.
            bad_sec = contract_text.replace("## 6. 数据验收", "## 数据验收")
            tmp_contract.write_text(bad_sec, encoding="utf-8")
            res1 = check_private_sync_protocol.main([
                "--contract", str(tmp_contract),
                "--fixtures", str(FIXTURES_DIR)
            ])
            self.assertNotEqual(res1, 0)

            # Sub-assertion 2: Missing decision D-NC015-04
            bad_dec = contract_text.replace("D-NC015-04", "D-NC015-XX")
            tmp_contract.write_text(bad_dec, encoding="utf-8")
            res2 = check_private_sync_protocol.main([
                "--contract", str(tmp_contract),
                "--fixtures", str(FIXTURES_DIR)
            ])
            self.assertNotEqual(res2, 0)

            # Sub-assertion 3: Contains 待定 outside backticks
            bad_tbd = contract_text + "\n这里包含待定事项\n"
            tmp_contract.write_text(bad_tbd, encoding="utf-8")
            res3 = check_private_sync_protocol.main([
                "--contract", str(tmp_contract),
                "--fixtures", str(FIXTURES_DIR)
            ])
            self.assertNotEqual(res3, 0)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_bad_expected_or_missing_file_or_wrong_ttl_fails(self):
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            tmp_fx = tmp_dir / "fixtures"

            # Sub-assertion 1: bad expected value
            shutil.copytree(FIXTURES_DIR, tmp_fx)
            auth_path = tmp_fx / "auth_valid.json"
            bad_auth = json.loads(auth_path.read_text(encoding="utf-8"))
            bad_auth["expected"] = "authorised"
            auth_path.write_text(json.dumps(bad_auth), encoding="utf-8")
            res1 = check_private_sync_protocol.main([
                "--contract", str(CONTRACT_PATH),
                "--fixtures", str(tmp_fx)
            ])
            self.assertNotEqual(res1, 0)

            # Sub-assertion 2: missing fixture file
            shutil.rmtree(tmp_fx)
            shutil.copytree(FIXTURES_DIR, tmp_fx)
            (tmp_fx / "auth_revoked.json").unlink()
            res2 = check_private_sync_protocol.main([
                "--contract", str(CONTRACT_PATH),
                "--fixtures", str(tmp_fx)
            ])
            self.assertNotEqual(res2, 0)

            # Sub-assertion 3: wrong TTL (sender_fallback_seconds != 300)
            shutil.rmtree(tmp_fx)
            shutil.copytree(FIXTURES_DIR, tmp_fx)
            ttl_path = tmp_fx / "relay_ttl.json"
            bad_ttl = json.loads(ttl_path.read_text(encoding="utf-8"))
            bad_ttl["sender_fallback_seconds"] = 299
            ttl_path.write_text(json.dumps(bad_ttl), encoding="utf-8")
            res3 = check_private_sync_protocol.main([
                "--contract", str(CONTRACT_PATH),
                "--fixtures", str(tmp_fx)
            ])
            self.assertNotEqual(res3, 0)

            # Sub-assertion 4: envelope_valid signed_fields missing content_hash
            shutil.rmtree(tmp_fx)
            shutil.copytree(FIXTURES_DIR, tmp_fx)
            env_path = tmp_fx / "envelope_valid.json"
            bad_env = json.loads(env_path.read_text(encoding="utf-8"))
            bad_env["signed_fields"] = [f for f in bad_env["signed_fields"] if f != "content_hash"]
            env_path.write_text(json.dumps(bad_env), encoding="utf-8")
            res4 = check_private_sync_protocol.main([
                "--contract", str(CONTRACT_PATH),
                "--fixtures", str(tmp_fx)
            ])
            self.assertNotEqual(res4, 0)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_aad_mismatch_differs_only_in_recipient(self):
        valid = json.loads((FIXTURES_DIR / "envelope_valid.json").read_text(encoding="utf-8"))
        mismatch = json.loads((FIXTURES_DIR / "envelope_aad_mismatch.json").read_text(encoding="utf-8"))
        self.assertNotEqual(mismatch["recipient_device_id"], valid["recipient_device_id"])
        for k in valid:
            if k != "recipient_device_id" and k != "expected":
                self.assertEqual(mismatch[k], valid[k])
        self.assertEqual(mismatch["expected"], "reject:aad_mismatch")

    def test_session_pub_bad_signature_fields(self):
        sig_data = json.loads((FIXTURES_DIR / "session_pub_bad_signature.json").read_text(encoding="utf-8"))
        self.assertRegex(sig_data["session_pub"], r"^[0-9a-f]{64}$")
        self.assertRegex(sig_data["session_pub_sig"], r"^[0-9a-f]{128}$")
        self.assertIn("session_id", sig_data)
        self.assertEqual(sig_data["expected"], "session_key_unbound")

    def test_pairing_anonymous_refused(self):
        pairing_data = json.loads((FIXTURES_DIR / "pairing_anonymous.json").read_text(encoding="utf-8"))
        self.assertIs(pairing_data["is_anonymous"], True)
        self.assertEqual(pairing_data["expected"], "pairing_refused_anonymous")

    def test_account_binding_cert_hash_matches_formula(self):
        av = json.loads((FIXTURES_DIR / "auth_valid.json").read_text(encoding="utf-8"))
        pa = av["peer_auth"]
        expected_hash = hashlib.sha256(
            f"{pa['scopeUid']}|{pa['peerDeviceId']}|{pa['peerPublicKeyFingerprint']}".encode("utf-8")
        ).hexdigest()
        self.assertEqual(pa["accountBindingCertHash"], expected_hash)

        tmp_dir = Path(tempfile.mkdtemp())
        try:
            tmp_fx = tmp_dir / "fixtures"
            shutil.copytree(FIXTURES_DIR, tmp_fx)
            auth_path = tmp_fx / "auth_valid.json"
            tampered = json.loads(auth_path.read_text(encoding="utf-8"))
            h = tampered["peer_auth"]["accountBindingCertHash"]
            tampered["peer_auth"]["accountBindingCertHash"] = ("0" if h[0] != "0" else "1") + h[1:]
            auth_path.write_text(json.dumps(tampered), encoding="utf-8")
            res = check_private_sync_protocol.main([
                "--contract", str(CONTRACT_PATH),
                "--fixtures", str(tmp_fx)
            ])
            self.assertNotEqual(res, 0)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
