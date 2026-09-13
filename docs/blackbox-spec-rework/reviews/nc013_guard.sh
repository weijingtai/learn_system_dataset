#!/usr/bin/env bash
# NC-013 守卫：回归 v1.6 守卫与 verify.sh；核对投递契约、API §13 补丁与六件套；
# --require-impl rest|server|rules|all（可逗号组合）时核对对应仓库产物并运行测试。
# 路径布局与 Windows 适配沿用 nc012a_guard.sh（D-NC012-23）。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"
MODE="${1:-}"; LINES="${2:-all}"
bash "$ROOT/openspec/annotation-community/review_v1_6_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
"$ROOT/.venv/Scripts/python.exe" - "$ROOT" "$g1" "$g2" "$MODE" "$LINES" <<'PY'
import json, os, re, shutil, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1]); g1, g2 = int(sys.argv[2]), int(sys.argv[3]); mode = sys.argv[4]; lines = sys.argv[5]
req = set()
if mode == "--require-impl":
    req = {"rest", "server", "rules"} if lines in ("", "all") else set(lines.split(","))
SPEC = root / "openspec/annotation-community"; PACK = root / "docs/blackbox-spec-rework/work-items/nc-013"
REST = Path("D:/Programme/xuan/repository-rest-adapter")
SRV = Path("D:/Programme/xuan-server/functions-py")
RULES = Path("D:/Programme/xuan-server/xuan-server")
FL = "D:/apps/apps/flutter/bin"
WIN = os.name == "nt"
EXE = lambda name: (shutil.which(name) or name) if WIN else name
NTF = ["ntf_f5b00f127444e70d78789b777bc91a51", "ntf_71b0cac6b3574748b597eff5f3f28ee5", "ntf_424a8073ca566cf03707ddc40bbb3878"]
SERVER_TESTS = """dispatch_comment_created_notifies_content_author_with_deterministic_ntf_id
dispatch_comment_reply_notifies_reply_target_not_content_author
dispatch_comment_mention_notifies_mentioned_user
dispatch_mention_and_reply_overlap_creates_single_reply_record
dispatch_reaction_like_notifies_content_author
dispatch_reaction_like_notifies_comment_author
dispatch_self_event_never_notifies_actor
dispatch_same_event_twice_creates_single_record_create_if_absent
dispatch_concurrent_same_event_two_transactions_single_record
dispatch_unknown_event_type_is_idempotent_noop
dispatch_comment_edited_and_deleted_are_noop_without_records
dispatch_content_and_legacy_events_are_noop_without_records
dispatch_transaction_replay_leaves_no_partial_records
notification_id_matches_e_encoding_reference_vectors
notification_record_validates_frozen_schema
like_notification_is_in_app_only_delivered_without_push
comment_notification_attempts_fcm_wakeup_without_body
push_failure_marks_failed_with_backoff_1_2_4_8
retry_after_backoff_advances_and_fifth_failure_abandons
push_success_marks_delivered_and_readvance_is_stable
blocked_pair_abandons_without_push_attempt
muted_content_abandons_comment_but_mention_still_dispatches
inaccessible_target_abandons_without_push_attempt
notification_pull_returns_body_for_trusted_binding
notification_pull_unresolved_binding_is_shared_404
notification_pull_non_recipient_is_shared_404
notification_pull_deleted_comment_is_shared_404
notification_list_returns_merged_windows_and_single_mentions
notification_list_cursor_never_regresses_and_limit_bounds
notification_mute_set_unset_is_idempotent_non_command""".split()
REST_TESTS = ["notification paths and methods match the catalog", "notification schemas are closed objects with notificationRecordId",
              "notification examples manifest has twenty entries and validates", "notification mutes are non command writes with rate limit row"]
NEW_COLS = ("community_notifications", "community_notifier_delivery_bindings", "community_notification_mutes")
BASE_FAILED = {"tests/test_config.py::test_集合名与_ts_逐项一致", "tests/test_registration.py::test_全部_callable_已在入口注册",
               "tests/test_registration.py::test_三个_trigger_已注册", "tests/test_registration.py::test_与_入口总数对齐",
               "tests/test_registration.py::test_没有多余的未声明导出"}
fails = 0
def check(ok, name, detail=""):
    global fails
    if not ok: fails += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""
def run(cmd, cwd, extra=None, timeout=1500):
    env = dict(os.environ); env.update(extra or {})
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout)
    return r.returncode, r.stdout + r.stderr
def git(repo, *args): return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout.strip()

check(g1 == 0 and g2 == 0, "K01 回归：v1.6 守卫与 verify.sh 均为 0", f"{g1},{g2}")

c = read(SPEC / "contracts/community_deliveries.md"); api = read(SPEC / "contracts/community_api.md")
need = NTF + SERVER_TESTS + REST_TESTS + list(NEW_COLS) + ["notification_pull", "/v1/community/notifications/pull",
       "/v1/community/notifications/mutes/", "NotificationBody", "NotificationPage", "NotificationEntry", "NotificationMuteState",
       "notifier_delivery_id", "create-if-absent", "tx.create()", "trusted_ingress", "trusted_delivery_callback",
       "invalid_argument.notifier_delivery_id", "不构成端到端 exactly-once", "滑窗", "无正文唤醒", "缺证阻断"]
missing = [n for n in need if n not in c]
ok02 = (not missing and all(f"D-NC013-{i:02d}" in c for i in range(1, 15)) and all(f"## {i}." in c for i in range(1, 16))
        and "## 13. NC-013 补丁" in api and "invalid_argument.notifier_delivery_id" in api and "greaterThanOrEqualTo(17)" in api)
check(ok02, "K02 契约：3 组 ntf_ 字面量、30+4 测试名、路径/Schema/错误码、D-NC013-01～14、十五节；API §13", f"missing={missing[:5]}")

bdd = read(PACK / "BDD.md"); tdd = read(PACK / "TDD.md"); acts = [read(PACK / "act" / f"0{i}.yaml") for i in range(1, 5)]
ids = re.findall(r"^\| ([ASR]\d\d) \|", bdd, re.M)
exp_ids = [f"A{i:02d}" for i in range(1, 5)] + [f"S{i:02d}" for i in range(1, 33)] + [f"R{i:02d}" for i in range(1, 4)]
est = [int((re.search(r"^ESTIMATE_MINUTES: (\d+)", a, re.M) or [0, 0])[1]) for a in acts]
deps = [(re.search(r"^DEPENDS_ON: (.*)$", a, re.M) or [0, ""])[1].strip() for a in acts]
vague = re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况")
files = ["README.md", "BDD.md", "TDD.md", "ACT.yaml", "PROMPT.md", "ACCEPTANCE.md"] + [f"act/0{i}.yaml" for i in range(1, 5)]
hits = [f"{f}:{m.group(0)}" for f in files for m in vague.finditer(read(PACK / f))] + [f"contract:{m.group(0)}" for m in vague.finditer(c)]
ok03 = (ids == exp_ids and all(30 <= e <= 60 for e in est) and deps == ["[]", "[]", "[NC-013-B]", "[]"]
        and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits
        and all(x in tdd for x in ("+81", "5 failed, 568 passed, 3 xfailed", "153 passed", "153 total"))
        and all(n in tdd for n in SERVER_TESTS + REST_TESTS) and "DISPATCH_PRECONDITION" in read(PACK / "ACT.yaml"))
check(ok03, "K03 六件套：BDD A01～A04/S01～S32/R01～R03、ACT 30–60 分钟、三线依赖链、ON_FAIL/WORKLOAD、无模糊词、计数与测试名",
      f"ids={len(ids)} est={est} deps={deps} vague={hits}")

todo = read(root / "docs/blackbox-spec-rework/SUBAGENT_TODO.md")
check("NC-013" in todo and "community_deliveries.md" in todo, "K04 SUBAGENT_TODO 已登记 NC-013 工作包与契约")

if "rest" in req:
    det = []; ok = True
    t = read(REST / "test/community_openapi_contract_test.dart"); y = read(REST / "openapi/openapi.yaml")
    for s in ("NotificationBody:", "NotificationPage:", "NotificationEntry:", "NotificationMuteState:",
              "/notifications/pull:", "/notifications/mutes/{content_id}:", "notifier_delivery_id"):
        if s not in y: ok = False; det.append(f"openapi 缺 {s}")
    miss = [n for n in REST_TESTS if n not in t]; ok &= not miss; det.append(f"tests_missing={miss}")
    try:
        man = json.loads(read(REST / "test/fixtures/openapi/examples/manifest.json")); names = [m.get("file") for m in man]
        ok &= len(man) == 20 and all(f in names for f in ("notification_body_comment.json", "notification_page_merged.json", "notification_mute_set.json"))
        det.append(f"manifest={len(man)}")
    except Exception as e:
        ok = False; det.append(f"manifest_error={type(e).__name__}")
    envf = {"PATH": FL + os.pathsep + os.environ["PATH"]}
    if WIN:
        envf["PYTHON"] = str(root / ".venv/Scripts/python.exe")
        envf["OPENAPI_VALIDATOR"] = str(root / "openspec/annotation-community/.venv-openapi/Scripts/openapi-spec-validator.exe")
    rc, out = run([EXE("dart"), "test"], REST, envf, timeout=1800)
    m = re.search(r"\+(\d+): All tests passed!", out); ok &= rc == 0 and m is not None and int(m.group(1)) >= 81; det.append(f"dart_test={rc}/{m.group(1) if m else '无'}")
    check(ok, "K05 REST 产物：openapi 增量、4 个测试、manifest 20 项、dart test ≥81", "; ".join(det))
else:
    print("SKIP  K05 REST 产物（验收时 --require-impl rest，必须 PASS）")

if "server" in req:
    det = []; ok = True
    for f in ("xuan/community/notification_dispatch.py", "xuan/handlers/community_deliveries.py", "tests/test_community_deliveries.py"):
        if not (SRV / f).is_file(): ok = False; det.append(f"missing {f}")
    t = read(SRV / "tests/test_community_deliveries.py")
    miss = [n for n in SERVER_TESTS if f"def test_{n}(" not in t]; ok &= not miss; det.append(f"tests_missing={miss[:3]}")
    cheats = [p for p in ("pytest.mark.skip", "pytest.skip(", "xfail", "assert True\n") if p in t]; ok &= not cheats; det.append(f"cheats={cheats}")
    src = read(SRV / "xuan/community/notification_dispatch.py") + read(SRV / "xuan/handlers/community_deliveries.py")
    exactly_once = [w for w in ("exactly-once",) if w in t or w in src]; ok &= not exactly_once; det.append(f"exactly_once={exactly_once}")
    ok &= all(h in t for h in NTF); det.append(f"ref_literals={all(h in t for h in NTF)}")
    acl = read(SRV / "tests/test_community_acl_sweep.py")
    ok &= "owner: NC-013" not in acl and "community_deliveries_py" in acl and "E1, E2, E4, E5, E6" in acl
    det.append(f"acl_e6_live={'owner: NC-013' not in acl}")
    prot = git(SRV, "diff-tree", "-r", "--name-only", "8d22451", "HEAD", "--", "xuan/handlers/notifications.py", "tests/test_registration.py",
               "tests/test_main_exports.py", "tests/community_helpers.py", "xuan/community/command_service.py", "xuan/community/content_service.py",
               "xuan/community/discussion_service.py", "xuan/community/interaction_service.py", "xuan/community/access.py", "xuan/community/errors.py",
               "xuan/community/ids.py", "xuan/community_hash.py", "xuan/push.py", "xuan/identity.py", "xuan/community/schemas")
    ok &= prot == ""; det.append(f"protected_empty={prot == ''}")
    emu = {"PYTHONDONTWRITEBYTECODE": "1", "FIRESTORE_EMULATOR_HOST": "192.168.0.165:8080", "FIREBASE_AUTH_EMULATOR_HOST": "192.168.0.165:9099"}
    rc, out = run([str(SRV / ".venv/Scripts/python.exe" if WIN else SRV / ".venv/bin/python"), "-m", "pytest", "tests", "-q", "-rf", "-p", "no:cacheprovider"], SRV, emu, timeout=3600)
    m = re.search(r"(\d+) failed, (\d+) passed, (\d+) xfailed", out); failed = set(re.findall(r"^FAILED (\S+)", out, re.M))
    ok &= m is not None and (m.group(1), m.group(2), m.group(3)) == ("5", "568", "3") and failed == BASE_FAILED
    det.append(f"pytest={m.group(0) if m else '无汇总'} failed_set_ok={failed == BASE_FAILED}")
    check(ok, "K06 SERVER 产物：30 个测试名、无作弊、ntf_ 字面量、E6 转真、禁止清单零改动、pytest 5/568/3 且失败集合不变、三新文件 exactly-once 零命中", "; ".join(det))
else:
    print("SKIP  K06 SERVER 产物（验收时 --require-impl server，必须 PASS）")

if "rules" in req:
    det = []; ok = True
    rules_t = read(RULES / "server/functions/test/community_rules.test.ts")
    cols_ok = all(("'" + n + "'") in rules_t for n in NEW_COLS)
    ok &= cols_ok; det.append(f"cols={cols_ok}")
    emu = {"FIRESTORE_EMULATOR_HOST": "192.168.0.165:8080", "FIREBASE_AUTH_EMULATOR_HOST": "192.168.0.165:9099"}
    rc2, out2 = run([EXE("npm"), "test", "--", "community_rules"], RULES / "server/functions", emu, timeout=1800)
    ok &= re.search(r"Tests:\s+153 passed, 153 total", out2) is not None; det.append(f"rules={rc2}")
    check(ok, "K07 RULES 产物：三集合清单、npm test 153", "; ".join(det))
else:
    print("SKIP  K07 RULES 产物（验收时 --require-impl rules，必须 PASS）")

print(f"\nNC-013 失败条数：{fails}"); sys.exit(fails)
PY
