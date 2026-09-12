#!/usr/bin/env bash
# NC-017 守卫：回归 v1.6 守卫与 verify.sh；核对导出契约与六件套；--require-impl 时核对 reading-notes 产物并运行测试。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"; REQ="${1:-}"
bash "$ROOT/openspec/annotation-community/review_v1_6_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
"$ROOT/.venv/bin/python" - "$ROOT" "$g1" "$g2" "$REQ" <<'PY'
import os, re, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1]); g1, g2 = int(sys.argv[2]), int(sys.argv[3]); req = sys.argv[4] == "--require-impl"
SPEC = root / "openspec/annotation-community"; PACK = root / "docs/blackbox-spec-rework/work-items/nc-017"
RN = Path("/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes"); FL = "/Users/jingtaiwei/flutter/bin"
REFS = ["51b48cd57443dc0a219081bbe73dc6e97a75c474eb2c15d7f557c0044c07d6a3", "2951a806b37bb65622017f6507fd20fae909485d3626963b92f08d136ef5b472",
        "61a5be5312ceb845fe7d4cccaff78ddbd74fc480f1584bb2b6ce578dc19d4886", "3a65508b4842461f25b17142",
        "37ccbe5f88cb425abc90f869b7d2c9229d6c63fb6a3b2519ca20c6317b828a98", "85df88a1f217a8d3d6dcf5f8b8c5fd87f89c4b397bbc72a8ec98cb320eb12564"]
TESTS = ["argon2id_key_matches_openssl_reference", "header_digest_and_bytes_match_reference", "single_chunk_file_matches_reference_sha256",
         "decode_reference_file_roundtrips_records", "raw_bytes_contain_no_plaintext_title_body_attachment_or_ids",
         "wrong_passphrase_tamper_reorder_truncate_append_raise_same_undecryptable", "tampered_header_or_changed_kdf_params_raise_format_error",
         "chunk_boundary_exact_multiple_and_plus_one", "writer_exports_active_and_trashed_with_full_revision_chain_excluding_pending_op",
         "writer_crash_leaves_only_partial_file", "writer_verification_failure_deletes_partial",
         "writer_rejects_existing_target_empty_passphrase_missing_or_mismatched_attachment", "writer_reports_progress_and_result_sha256",
         "passphrase_is_utf8_without_normalization"]
ALLOWED = {"pubspec.yaml", "pubspec.lock", "lib/reading_notes.dart", "lib/src/export/export_bundle_format.dart",
           "lib/src/export/export_writer.dart", "test/export/export_bundle_test.dart"}
fails = 0
def check(ok, name, detail=""):
    global fails
    if not ok: fails += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""

check(g1 == 0 and g2 == 0, "K01 回归：v1.6 守卫与 verify.sh 均为 0", f"{g1},{g2}")
c = read(SPEC / "contracts/private_export.md")
need = REFS + TESTS + ["RNEXPORT", "account_notes", "aes_gcm_blob_cipher_v1", "cryptography: 2.9.0", "ExportUndecryptable", "ExportFormatError",
       "after_chunk:", "before_verify", "before_rename", ".partial", "bkm_"]
miss = [n for n in need if n not in c]
check(not miss and all(f"D-NC017-{i:02d}" in c for i in range(1, 12)) and all(f"## {i}." in c for i in range(1, 10)),
      "K02 契约：六个参考值、14 个测试名、容器/异常/hook 关键字、D-NC017-01～11、九节", f"missing={miss[:4]}")
bdd = read(PACK / "BDD.md"); tdd = read(PACK / "TDD.md"); acts = [read(PACK / "act" / f"0{i}.yaml") for i in (1, 2)]
ids = re.findall(r"^\| (E\d\d) \|", bdd, re.M)
est = [int((re.search(r"^ESTIMATE_MINUTES: (\d+)", a, re.M) or [0, 0])[1]) for a in acts]
deps = [(re.search(r"^DEPENDS_ON: (.*)$", a, re.M) or [0, ""])[1].strip() for a in acts]
vague = re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况")
files = ["README.md", "BDD.md", "TDD.md", "ACT.yaml", "PROMPT.md", "ACCEPTANCE.md", "act/01.yaml", "act/02.yaml"]
hits = [f"{f}:{m.group(0)}" for f in files for m in vague.finditer(read(PACK / f))] + [f"contract:{m.group(0)}" for m in vague.finditer(c)]
ok03 = (ids == [f"E{i:02d}" for i in range(1, 15)] and all(30 <= e <= 60 for e in est) and deps == ["[]", "[NC-017-A]"]
        and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits and all(t in tdd for t in TESTS)
        and all(x in tdd for x in ("+8", "+14", "+247", "+253")) and "DISPATCH_PRECONDITION" in read(PACK / "ACT.yaml"))
check(ok03, "K03 六件套：BDD E01～E14、两个 ACT 30–60 分钟、依赖链、ON_FAIL/WORKLOAD、无模糊词、测试名与计数", f"ids={len(ids)} est={est} deps={deps} vague={hits}")
todo = read(root / "docs/blackbox-spec-rework/SUBAGENT_TODO.md")
check("NC-017" in todo and "private_export.md" in todo, "K04 SUBAGENT_TODO 已登记 NC-017 工作包与契约")

if not req:
    print("SKIP  K05 NC-017 产物（验收时加 --require-impl，必须 PASS）")
else:
    det = []; ok = True
    for f in ("lib/src/export/export_bundle_format.dart", "lib/src/export/export_writer.dart", "test/export/export_bundle_test.dart"):
        if not (RN / f).is_file(): ok = False; det.append(f"missing {f}")
    ok &= re.search(r"^  cryptography: 2\.9\.0$", read(RN / "pubspec.yaml"), re.M) is not None
    lock = read(RN / "pubspec.lock"); ok &= re.search(r'cryptography:\n(?:.*\n){5}\s+version: "2\.9\.0"', lock) is not None
    t = read(RN / "test/export/export_bundle_test.dart")
    miss = [n for n in TESTS if n not in t]; ok &= not miss; det.append(f"tests_missing={miss[:3]}")
    cheats = [p for p in ("skip:", "expect(true, isTrue)") if p in t]; ok &= not cheats; det.append(f"cheats={cheats}")
    ok &= all(r in t for r in REFS); det.append(f"ref_literals={all(r in t for r in REFS)}")
    base = subprocess.run(["git", "-C", str(RN), "log", "--format=%h", "--grep=NC-011-F", "-1"], capture_output=True, text=True).stdout.strip()
    changed = set(subprocess.run(["git", "-C", str(RN), "diff-tree", "-r", "--name-only", base, "HEAD"], capture_output=True, text=True).stdout.split()) if base else {"<无 NC-011-F 基线>"}
    ok &= bool(base) and changed <= ALLOWED; det.append(f"base={base} extra={sorted(changed - ALLOWED)}")
    env = dict(os.environ); env["PATH"] = FL + ":" + env["PATH"]
    an = subprocess.run(["flutter", "analyze"], cwd=RN, capture_output=True, text=True, env=env); ok &= an.returncode == 0; det.append(f"analyze={an.returncode}")
    ft = subprocess.run(["flutter", "test"], cwd=RN, capture_output=True, text=True, env=env)
    m = re.search(r"\+(\d+): All tests passed!", ft.stdout); ok &= ft.returncode == 0 and m is not None and int(m.group(1)) >= 253
    det.append(f"test={ft.returncode}/{m.group(1) if m else '无'}")
    check(ok, "K05 NC-017 产物：文件齐全、cryptography 精确锁定、14 个测试名、无作弊、参考值字面量、只改白名单、analyze 0、flutter test ≥253", "; ".join(det))
print(f"\nNC-017 失败条数：{fails}"); sys.exit(fails)
PY
