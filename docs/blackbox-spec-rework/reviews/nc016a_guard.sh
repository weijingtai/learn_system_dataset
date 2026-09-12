#!/usr/bin/env bash
# NC-016a 守卫：回归 v1.6 守卫与 verify.sh；核对私人同步实现契约与六件套；
# --require-impl client|storage|all 时核对对应仓库产物并运行测试。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"
MODE="${1:-}"; LINES="${2:-all}"
bash "$ROOT/openspec/annotation-community/review_v1_6_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
"$ROOT/.venv/bin/python" - "$ROOT" "$g1" "$g2" "$MODE" "$LINES" <<'PY'
import hashlib, os, re, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1]); g1, g2 = int(sys.argv[2]), int(sys.argv[3]); mode = sys.argv[4]; lines = sys.argv[5]
req = set()
if mode == "--require-impl":
    req = {"client", "storage"} if lines in ("", "all") else set(lines.split(","))
SPEC = root / "openspec/annotation-community"; PACK = root / "docs/blackbox-spec-rework/work-items/nc-016a"
FIX = SPEC / "fixtures/private_sync"
RN = Path("/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes")
XS = Path("/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage"); WT = XS / ".worktrees/nc016-guard-aad"
FL = "/Users/jingtaiwei/flutter/bin"
REFS = ["dafcb7e08e8ffe64bf871fe7c3ba3dee3ea088a4c0fe57a9566dd737d51495c3", "c853ad0f0cd2b619aea92ceec4fd56a24d6499d584ce79257e45cfd8139b60a7",
        "e639de16df1b7ffe67b66fb085c9a6c8ccb4ba45936a341df3e1dd21c2e0dc59b02ac7e26687d236f0abfab413c10ec3b91e0672498672336b642e7ae9e78e0b",
        "7b4e909bbe7ffe44c465a220037d608ee35897d31ef972f07f74892cb0f73f13", "0faa684ed28867b97f4a6a2dee5df8ce974e76b7018e3f22a1c4cf2678570f20",
        "9e004098efc091d4ec2663b4e9f5cfd4d7064571690b4bea97ab146ab9f35056", "4da4b1c9ae776786e05f9d34c8ee9147feb2a49a3634905a9aef7f449ffbddf2",
        "75fcbd72b9d90228c842a0598477dbf7a5a8d7d290b93210925fd323abc6f7415eed0d18cd17a2126b8b59f184fbf90d",
        "b8006c35e983f50fccf8f3910ef36d806649712404b41228a41ad7fdd2a367c7", "0e51b2e763b667f6a87f1abc",
        "e776bae8f2f03865f2d31553e540d36323318e9796ca12edaec6d7f552335424", "34b4d9043156cb6dcf0beb0a2949b7559c940d2bcb6dbe8c53a9b30278e3a746",
        "9ff25742fe708b81a6cb2dbf94885c85c5d1e6be84b23856f299e7f39a3868256dc911a8200378f694ce548859075adf390c351e742d10b6f2ecd31032f31103",
        "c2d5f307efbc443185626250f07131b798736e02c7732b1dc417171d30c30504"]
STORAGE_TESTS = ["guard_decisions_match_private_sync_fixtures", "guard_patch_order_device_then_fingerprint_then_expiry",
                 "aes_gcm_aad_binds_ciphertext_and_empty_aad_is_backward_compatible"]
CLIENT_TESTS = """authorization_decisions_match_private_sync_fixtures account_binding_cert_hash_matches_fixture pairing_gate_and_relay_config_match_fixtures
apply_remote_revision_creates_note_keeps_branches_and_writes_no_outbox apply_remote_revision_rejects_missing_parent_and_is_atomic
mark_envelope_allows_only_forward_transitions sealed_envelope_bytes_contain_no_plaintext_title_or_body wrap_and_chunk_match_python_reference_vectors
seal_receive_roundtrip_accepts_with_real_keys signed_fields_match_fixture_and_tampered_content_hash_is_bad_signature recipient_mismatch_is_aad_mismatch
stored_wrong_content_hash_is_hash_mismatch replay_same_revision_is_duplicate_ack_without_write oversize_inline_payload_is_schema_invalid
untrusted_expired_or_revoked_sender_is_source_untrusted session_pub_bad_signature_is_session_key_unbound_before_sealing
concurrent_branches_from_two_devices_are_kept_as_heads""".split()
AUTH = sorted(p.name for p in FIX.glob("auth_*.json"))
CLIENT_FIX = AUTH + ["envelope_valid.json", "pairing_anonymous.json", "relay_ttl.json", "deletion_layers.json"]
fails = 0
def check(ok, name, detail=""):
    global fails
    if not ok: fails += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def run(cmd, cwd, timeout=900):
    env = dict(os.environ); env["PATH"] = FL + ":" + env["PATH"]
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout)
    return r.returncode, r.stdout + r.stderr
def git(repo, *args): return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout.strip()

check(g1 == 0 and g2 == 0, "K01 回归：v1.6 守卫与 verify.sh 均为 0", f"{g1},{g2}")
c = read(SPEC / "contracts/private_sync_impl.md"); ps = read(SPEC / "contracts/private_sync.md")
need = REFS + STORAGE_TESTS + CLIENT_TESTS + ["fix/nc016-guard-aad", "8ddb877", "applyRemoteRevision", "markEnvelope", "SessionKeyUnbound",
       "reject:source_untrusted", "duplicate_ack", "maxInlinePayloadBytes", "xuan-private-sync/v1/"]
miss = [n for n in need if n not in c]
check(not miss and len(AUTH) == 8 and all(f"D-NC016-{i:02d}" in c for i in range(1, 14)) and all(f"## {i}." in c for i in range(1, 11))
      and "## 10. NC-016a 实现补充" in ps and "D-NC016-05" in ps,
      "K02 契约：14 个参考值、3+17 测试名、分支与关键符号、D-NC016-01～13、十节；private_sync §10 回填", f"missing={miss[:4]} auth={len(AUTH)}")
bdd = read(PACK / "BDD.md"); tdd = read(PACK / "TDD.md"); acts = [read(PACK / "act" / f"0{i}.yaml") for i in (1, 2, 3)]
ids = re.findall(r"^\| ([XS]\d\d) \|", bdd, re.M)
est = [int((re.search(r"^ESTIMATE_MINUTES: (\d+)", a, re.M) or [0, 0])[1]) for a in acts]
deps = [(re.search(r"^DEPENDS_ON: (.*)$", a, re.M) or [0, ""])[1].strip() for a in acts]
vague = re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况")
files = ["README.md", "BDD.md", "TDD.md", "ACT.yaml", "PROMPT.md", "ACCEPTANCE.md", "act/01.yaml", "act/02.yaml", "act/03.yaml"]
hits = [f"{f}:{m.group(0)}" for f in files for m in vague.finditer(read(PACK / f))] + [f"contract:{m.group(0)}" for m in vague.finditer(c)]
ok03 = (ids == [f"X{i:02d}" for i in range(1, 4)] + [f"S{i:02d}" for i in range(1, 18)] and all(30 <= e <= 60 for e in est)
        and deps == ["[]", "[]", "[NC-016a-B]"] and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits
        and all(t in tdd for t in STORAGE_TESTS + CLIENT_TESTS) and all(x in tdd for x in ("+6", "+17", "+259", "+270", "+2", "+4", "+3"))
        and "DISPATCH_PRECONDITION" in read(PACK / "ACT.yaml"))
check(ok03, "K03 六件套：BDD X01～X03/S01～S17、三个 ACT 30–60 分钟、依赖链、ON_FAIL/WORKLOAD、无模糊词、测试名与计数", f"ids={len(ids)} est={est} deps={deps} vague={hits}")
todo = read(root / "docs/blackbox-spec-rework/SUBAGENT_TODO.md")
check("NC-016a" in todo and "private_sync_impl.md" in todo, "K04 SUBAGENT_TODO 已登记 NC-016a 工作包与契约")

if "storage" in req:
    det = []; ok = True
    ok &= WT.is_dir() and git(WT, "rev-parse", "--abbrev-ref", "HEAD") == "fix/nc016-guard-aad"; det.append(f"branch={git(WT, 'rev-parse', '--abbrev-ref', 'HEAD') if WT.is_dir() else '无 worktree'}")
    ok &= git(XS, "rev-parse", "main").startswith("8ddb877"); det.append(f"main={git(XS, 'rev-parse', '--short', 'main')}")
    allowed = {"core/lib/sync/same_account_im_reconciliation.dart", "core/lib/model/blob_cipher.dart", "drift/lib/blob/aes_gcm_blob_cipher.dart",
               "drift/lib/blob/identity_blob_cipher.dart", "drift/test/blob/blob_cipher_test.dart", "core/test/private_sync_guard_fixtures_test.dart",
               "drift/test/blob/aes_gcm_aad_test.dart"} | {f"core/test/fixtures/private_sync/{n}" for n in AUTH}
    # D-NC016-14：两条既有测试只允许把授权记录到期时间换成 4102444800000，恰 1 增 1 删
    old_tests = ("core/test/same_account_im_reconciliation_test.dart", "p2p/test/same_account_security_boundary_test.dart")
    allowed |= set(old_tests)
    changed = set(git(WT, "diff-tree", "-r", "--name-only", "8ddb877", "HEAD").split()) if WT.is_dir() else {"<无>"}
    ok &= bool(changed) and changed <= allowed; det.append(f"extra={sorted(changed - allowed)[:3]}")
    for f in old_tests:
        if f in changed:
            ns = git(WT, "diff", "--numstat", "8ddb877", "HEAD", "--", f).split("\t")[:2]
            d = git(WT, "diff", "-U0", "8ddb877", "HEAD", "--", f)
            good = (ns == ["1", "1"] and re.search(r"^-\s+expiresAtUtcMs: 1724720400000 \+ 86400000,$", d, re.M) is not None
                    and re.search(r"^\+\s+expiresAtUtcMs: 4102444800000,$", d, re.M) is not None)
            ok &= good; det.append(f"{f.split('/')[-1]}_expiry_only={good}")
    ok &= all(sha(WT / "core/test/fixtures/private_sync" / n) == sha(FIX / n) for n in AUTH)
    t = read(WT / "core/test/private_sync_guard_fixtures_test.dart") + read(WT / "drift/test/blob/aes_gcm_aad_test.dart")
    ok &= all(n in t for n in STORAGE_TESTS) and "skip:" not in t
    for sub, files_, want in (("core", ["test/private_sync_guard_fixtures_test.dart"], 2), ("core", ["test/same_account_im_reconciliation_test.dart"], 4),
                              ("p2p", ["test/same_account_security_boundary_test.dart"], 3), ("drift", ["test/blob/aes_gcm_aad_test.dart"], 1)):
        rc, out = run(["flutter", "test", *files_], WT / sub) if WT.is_dir() else (1, "")
        m = re.search(r"\+(\d+): All tests passed!", out); good = rc == 0 and m is not None and int(m.group(1)) == want
        ok &= good; det.append(f"{sub}:{files_[0].split('/')[-1]}={m.group(1) if m else rc}")
    check(ok, "K06 STORAGE 产物：功能分支、main 未动、只改白名单、样例逐字节、测试名、core +2/+4、p2p +3、drift +1", "; ".join(det))
else:
    print("SKIP  K06 STORAGE 产物（验收时 --require-impl storage，必须 PASS）")

if "client" in req:
    det = []; ok = True
    for f in ("lib/src/storage/private_note_mapper.dart", "lib/src/storage/private_note_sync.dart", "test/storage/private_note_sync_test.dart"):
        if not (RN / f).is_file(): ok = False; det.append(f"missing {f}")
    t = read(RN / "test/storage/private_note_sync_test.dart")
    miss = [n for n in CLIENT_TESTS if n not in t]; ok &= not miss; det.append(f"tests_missing={miss[:3]}")
    ok &= "skip:" not in t and "expect(true, isTrue)" not in t and all(r in t for r in REFS); det.append(f"ref_literals={all(r in t for r in REFS)}")
    ok &= all(sha(RN / "test/fixtures/private_sync" / n) == sha(FIX / n) for n in CLIENT_FIX); det.append("fixtures_checked")
    allowed = {"lib/src/storage/private_note_mapper.dart", "lib/src/storage/private_note_sync.dart", "lib/src/persistence/note_repository.dart",
               "lib/reading_notes.dart", "test/storage/private_note_sync_test.dart"} | {f"test/fixtures/private_sync/{n}" for n in CLIENT_FIX}
    changed = set(git(RN, "diff-tree", "-r", "--name-only", "4a0d70a", "HEAD").split())
    ok &= bool(changed) and changed <= allowed; det.append(f"extra={sorted(changed - allowed)[:3]}")
    ns = git(RN, "diff", "--no-ext-diff", "--numstat", "4a0d70a", "HEAD", "--", "lib/src/persistence/note_repository.dart").split()
    ok &= len(ns) >= 2 and ns[1] == "0"; det.append(f"repo_numstat={ns[:2]}")
    rc, _ = run(["flutter", "analyze"], RN); ok &= rc == 0; det.append(f"analyze={rc}")
    rc, out = run(["flutter", "test"], RN)
    m = re.search(r"\+(\d+): All tests passed!", out); ok &= rc == 0 and m is not None and int(m.group(1)) >= 270; det.append(f"test={rc}/{m.group(1) if m else '无'}")
    check(ok, "K05 CLIENT 产物：文件齐全、17 个测试名、参考值字面量、样例逐字节、只改白名单、仓储只追加、analyze 0、flutter test ≥270", "; ".join(det))
else:
    print("SKIP  K05 CLIENT 产物（验收时 --require-impl client，必须 PASS）")
print(f"\nNC-016a 失败条数：{fails}"); sys.exit(fails)
PY
