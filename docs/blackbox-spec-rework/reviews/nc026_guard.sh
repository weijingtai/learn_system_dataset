#!/usr/bin/env bash
# NC-026 守卫：回归 v1.6 守卫与 verify.sh；核对行为事件契约、API §14 补丁、六件套与规格侧 Schema/示例；
# --require-impl rest|server|client|rules|all（可逗号组合）时核对对应仓库产物并运行测试。
# 路径布局与 Windows 适配沿用 nc013_guard.sh（D-NC012-23）。
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
    req = {"rest", "server", "client", "rules"} if lines in ("", "all") else set(lines.split(","))
SPEC = root / "openspec/annotation-community"; PACK = root / "docs/blackbox-spec-rework/work-items/nc-026"
SCHEMAS = root / "openspec/schemas"
REST = Path("D:/Programme/xuan/repository-rest-adapter")
SRV = Path("D:/Programme/xuan-server/functions-py")
CLI = Path("D:/Programme/xuan/reading-notes")
RULES = Path("D:/Programme/xuan-server/xuan-server")
FL = "D:/apps/apps/flutter/bin"
WIN = os.name == "nt"
EXE = lambda name: (shutil.which(name) or name) if WIN else name
SCHEMA_SHA = "f3467224ddafa5ff3ac2a43011521a5cc0b8acf6293244d632fa291c97451e42"
BEV = ["bev_7238cb94b108c5479b32e4259ed4e147", "bev_35a1484fbe53c4b9c5c5f0ab19508dc2", "bev_0cf02e53b9c67b679b53567c01484371"]
NOTE_REF = "2be56a4060534a55fda8d1767be56a551743236f617bfec52d4f0178fff80673"
REST_TESTS = ["analytics paths and methods match the catalog", "analytics schemas are closed objects with pseudonym and batch bounds",
              "analytics examples manifest has twenty two entries and validates", "analytics rate limit and error rows are declared"]
SERVER_TESTS = """behavior_event_schema_is_closed_and_matches_frozen_copy
frozen_behavior_event_schema_sha256_matches_contract_literal
server_event_document_matches_frozen_schema_after_command
server_event_carries_object_type_and_object_id_per_operation_map
server_event_note_ref_is_null_and_platform_is_server
client_event_id_format_is_bev_prefixed_uuid_v4
attributes_allowlist_rejects_unknown_keys_per_event_type
private_note_event_requires_all_six_revision_attributes
private_note_event_rejects_server_only_attributes
behavior_event_examples_validate_two_valid_and_twenty_one_invalid
analytics_events_ingests_client_events_and_fills_received_at
analytics_events_is_idempotent_by_event_id_and_counts_duplicates
analytics_events_batch_over_500_is_413
analytics_events_rejects_server_event_type_on_client_endpoint
analytics_events_invalid_schema_reports_json_pointer
analytics_events_batch_splits_into_transactions_of_hundred
analytics_events_unauthenticated_is_401
analytics_events_rate_limit_row_matches_contract
analytics_events_does_not_touch_ledger_or_notifications
analytics_events_partial_failure_returns_503_and_retry_dedupes
pseudonym_endpoint_returns_stable_random_pseudonym
pseudonym_endpoint_creates_mapping_once_without_behavior_event
pseudonym_is_shared_between_command_and_client_event_paths
pseudonym_is_random_across_two_independent_projects
event_documents_never_contain_account_id
server_code_has_no_update_or_delete_on_behavior_events""".split()
CLIENT_TESTS = """revision_saved_emits_six_attribute_event
char_count_counts_code_points_not_utf16_or_bytes
session_ended_emits_duration_and_revision_count
event_id_is_bev_prefixed_uuid_v4
note_ref_is_sha256_of_pseudonym_and_note_id
raw_report_bytes_never_contain_note_id_title_body_or_attachment_name
pseudonym_is_fetched_once_and_cached
pseudonym_cache_is_cleared_on_account_switch
queue_keeps_events_when_flush_fails
queue_drops_oldest_beyond_ten_thousand
dropped_before_is_attached_to_next_report_only
dropped_before_absent_when_nothing_was_dropped
flush_sends_batches_of_at_most_five_hundred
flush_removes_only_acknowledged_events
flush_reports_failed_without_throwing
events_persist_across_store_restart
revision_saved_does_not_block_save_on_transport_failure
report_payload_has_no_extra_keys""".split()
PROTECTED = ("xuan/community/content_service.py", "xuan/community/discussion_service.py", "xuan/community/interaction_service.py",
             "xuan/community/access.py", "xuan/community/errors.py", "xuan/community/ids.py", "xuan/community_hash.py",
             "xuan/push.py", "xuan/identity.py", "xuan/handlers/community_contents.py", "xuan/handlers/community_comments.py",
             "xuan/handlers/community_interactions.py", "xuan/handlers/community_deliveries.py", "xuan/handlers/community_commands.py",
             "tests/test_community_interactions.py", "tests/test_community_comments.py", "tests/test_community_publications.py",
             "tests/test_registration.py", "tests/test_main_exports.py", "tests/community_helpers.py")
BASE_FAILED = {"tests/test_config.py::test_集合名与_ts_逐项一致", "tests/test_registration.py::test_全部_callable_已在入口注册",
               "tests/test_registration.py::test_三个_trigger_已注册", "tests/test_registration.py::test_与_入口总数对齐",
               "tests/test_registration.py::test_没有多余的未声明导出"}
fails = 0
def check(ok, name, detail=""):
    global fails
    if not ok: fails += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""
def run(cmd, cwd, extra=None, timeout=1800):
    env = dict(os.environ); env.update(extra or {})
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout)
    return r.returncode, r.stdout + r.stderr
def git(repo, *args): return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout.strip()

check(g1 == 0 and g2 == 0, "K01 回归：v1.6 守卫与 verify.sh 均为 0", f"{g1},{g2}")

c = read(SPEC / "contracts/community_behavior.md"); api = read(SPEC / "contracts/community_api.md")
need = BEV + [NOTE_REF, SCHEMA_SHA] + SERVER_TESTS + REST_TESTS + CLIENT_TESTS + [
    "/v1/analytics/events", "/v1/analytics/pseudonym", "AnalyticsEventBatch", "AnalyticsEventRequest",
    "AnalyticsEventsAccepted", "ActorPseudonym", "community_analytics_rejections", "private_note.revision_saved",
    "private_note.session_ended", "invalid_argument.events", "invalid_argument.event_type", "too_large.events",
    "MAX_EVENTS_PER_BATCH", "dropped_before", "tx.create(", "at-least-once", "只追加", "UUIDv4",
    "note_ref", "SERVER_PLATFORM", "DEFERRED"]
missing = [n for n in need if n not in c]
ok02 = (not missing and all(f"D-NC026-{i:02d}" in c for i in range(1, 24)) and all(f"## {i}." in c for i in range(1, 16))
        and "## 14. NC-026 补丁" in api and "invalid_argument.events" in api and "too_large.events" in api
        and "greaterThanOrEqualTo(20)" in api)
check(ok02, "K02 契约：Schema SHA、3 组 bev_、note_ref、44 测试名、路径/Schema/错误码、D-NC026-01～23、十五节；API §14",
      f"missing={missing[:6]}")

bdd = read(PACK / "BDD.md"); tdd = read(PACK / "TDD.md"); acts = [read(PACK / "act" / f"0{i}.yaml") for i in range(1, 6)]
ids = re.findall(r"^\| ([ASCR]\d\d) \|", bdd, re.M)
exp_ids = ([f"A{i:02d}" for i in range(1, 5)] + [f"S{i:02d}" for i in range(1, 27)]
           + [f"C{i:02d}" for i in range(1, 19)] + [f"R{i:02d}" for i in range(1, 4)])
est = [int((re.search(r"^ESTIMATE_MINUTES: (\d+)", a, re.M) or [0, 0])[1]) for a in acts]
deps = [(re.search(r"^DEPENDS_ON: (.*)$", a, re.M) or [0, ""])[1].strip() for a in acts]
vague = re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况")
files = ["README.md", "BDD.md", "TDD.md", "ACT.yaml", "PROMPT.md", "ACCEPTANCE.md"] + [f"act/0{i}.yaml" for i in range(1, 6)]
hits = [f"{f}:{m.group(0)}" for f in files for m in vague.finditer(read(PACK / f))] + [f"contract:{m.group(0)}" for m in vague.finditer(c)]
ok03 = (ids == exp_ids and all(30 <= e <= 60 for e in est) and deps == ["[]", "[]", "[NC-026-B]", "[]", "[]"]
        and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits
        and all(x in tdd for x in ("+85", "5 failed, 594 passed, 3 xfailed", "157 passed", "157 total", "+332"))
        and all(n in tdd for n in SERVER_TESTS + REST_TESTS + CLIENT_TESTS)
        and "DISPATCH_PRECONDITION" in read(PACK / "ACT.yaml") and "DEFERRED" in read(PACK / "ACT.yaml"))
check(ok03, "K03 六件套：BDD A01～A04/S01～S26/C01～C18/R01～R03、ACT 30–60 分钟、四线依赖链、ON_FAIL/WORKLOAD、无模糊词、计数与测试名",
      f"ids={len(ids)} est={est} deps={deps} vague={hits}")

todo = read(root / "docs/blackbox-spec-rework/SUBAGENT_TODO.md")
nc026_row = next((ln for ln in todo.splitlines() if "NC-026：" in ln), "")
check(bool(nc026_row) and ("`PREPARING`" in nc026_row or "`ACCEPTED`" in nc026_row) and "community_behavior.md" in nc026_row,
      "K04 SUBAGENT_TODO 已登记 NC-026（PREPARING 或 ACCEPTED）且含契约文件名",
      f"row={'found' if nc026_row else 'missing'}")

# K05 规格侧：冻结 Schema 与行为事件示例（Windows 经 check-jsonschema.exe + file:///D:/ base-uri，D-NC026-21）
det = []; ok = True
sfile = SCHEMAS / "community_behavior_event.schema.json"
if sfile.is_file():
    if sfile.read_bytes().decode("utf-8") and SCHEMA_SHA:
        import hashlib
        actual = hashlib.sha256(sfile.read_bytes()).hexdigest()
        # 期望值取契约字面量（常量比对，不在契约外现算）
        ok &= actual == SCHEMA_SHA; det.append(f"sha={actual[:12]}")
    cj = root / (".venv/Scripts/check-jsonschema.exe" if WIN else ".venv/bin/check-jsonschema")
    base = "file:///D:/Programme/learn_system/openspec/schemas/" if WIN else f"file://{root}/openspec/schemas/"
    exdir = SCHEMAS / "examples"
    valid = sorted(exdir.glob("community_behavior_event*.valid*.yaml"))
    invalid = sorted(exdir.glob("community_behavior_event.invalid_*.yaml"))
    ok &= len(valid) == 2 and len(invalid) == 21; det.append(f"valid={len(valid)} invalid={len(invalid)}")
    if cj.is_file():
        for f in valid:
            rc, _ = run([str(cj), "--base-uri", base, "--schemafile", str(sfile), str(f)], root, timeout=120)
            if rc != 0: ok = False; det.append(f"valid_rejected={f.name}")
        for f in invalid:
            rc, _ = run([str(cj), "--base-uri", base, "--schemafile", str(sfile), str(f)], root, timeout=120)
            if rc == 0: ok = False; det.append(f"invalid_accepted={f.name}")
    else:
        ok = False; det.append("check-jsonschema 缺失")
else:
    ok = False; det.append("schema 缺失")
check(ok, "K05 规格侧产物：冻结 Schema SHA 字面量、2 正 21 负示例全部符合判定", "; ".join(det))

if "rest" in req:
    det = []; ok = True
    t = read(REST / "test/community_openapi_contract_test.dart"); y = read(REST / "openapi/openapi.yaml")
    for s in ("AnalyticsEventBatch:", "AnalyticsEventRequest:", "AnalyticsEventsAccepted:", "ActorPseudonym:",
              "/analytics/events:", "/analytics/pseudonym:"):
        if s not in y: ok = False; det.append(f"openapi 缺 {s}")
    miss = [n for n in REST_TESTS if n not in t]; ok &= not miss; det.append(f"tests_missing={miss}")
    try:
        man = json.loads(read(REST / "test/fixtures/openapi/examples/manifest.json")); names = [m.get("file") for m in man]
        ok &= len(man) == 22 and all(f in names for f in ("analytics_events_batch.json", "analytics_pseudonym.json"))
        det.append(f"manifest={len(man)}")
    except Exception as e:
        ok = False; det.append(f"manifest_error={type(e).__name__}")
    env = {"PATH": FL + os.pathsep + os.environ["PATH"]}
    if WIN:
        env["PYTHON"] = str(root / ".venv/Scripts/python.exe")
        env["OPENAPI_VALIDATOR"] = str(root / "openspec/annotation-community/.venv-openapi/Scripts/openapi-spec-validator.exe")
    rc, out = run([EXE("dart"), "test"], REST, env, timeout=1800)
    m = re.search(r"\+(\d+): All tests passed!", out); ok &= rc == 0 and m is not None and int(m.group(1)) >= 85
    det.append(f"dart_test={rc}/{m.group(1) if m else '无'}")
    check(ok, "K06 REST 产物：openapi 增量、4 个测试、manifest 22 项、dart test ≥85", "; ".join(det))
else:
    print("SKIP  K06 REST 产物（验收时 --require-impl rest，必须 PASS）")

if "server" in req:
    det = []; ok = True
    for f in ("xuan/community/pseudonyms.py", "xuan/community/behavior_events.py", "xuan/handlers/analytics_events.py",
              "tests/test_behavior_events.py"):
        if not (SRV / f).is_file(): ok = False; det.append(f"missing {f}")
    t = read(SRV / "tests/test_behavior_events.py")
    miss = [n for n in SERVER_TESTS if f"def test_{n}(" not in t]; ok &= not miss; det.append(f"tests_missing={miss[:3]}")
    cheats = [p for p in ("pytest.mark.skip", "pytest.skip(", "xfail", "assert True\n") if p in t]; ok &= not cheats; det.append(f"cheats={cheats}")
    src = read(SRV / "xuan/community/pseudonyms.py") + read(SRV / "xuan/community/behavior_events.py") + read(SRV / "xuan/handlers/analytics_events.py")
    eo = "exactly-once" in t or "exactly-once" in src; ok &= not eo; det.append(f"exactly_once={eo}")
    ok &= all(h in t for h in BEV) and NOTE_REF in t and SCHEMA_SHA in t; det.append(f"ref_literals={all(h in t for h in BEV)}")
    copied = read(SRV / "xuan/community/schemas/community_behavior_event.schema.json")
    ok &= copied == read(SCHEMAS / "community_behavior_event.schema.json"); det.append(f"schema_copy_identical={copied == read(SCHEMAS / 'community_behavior_event.schema.json')}")
    prot = git(SRV, "diff-tree", "-r", "--name-only", "992088e", "HEAD", "--", *PROTECTED)
    ok &= prot == ""; det.append(f"protected_empty={prot == ''}")
    emu = {"PYTHONDONTWRITEBYTECODE": "1", "FIRESTORE_EMULATOR_HOST": "192.168.0.165:8080", "FIREBASE_AUTH_EMULATOR_HOST": "192.168.0.165:9099"}
    rc, out = run([str(SRV / (".venv/Scripts/python.exe" if WIN else ".venv/bin/python")), "-m", "pytest", "tests", "-q", "-rf", "-p", "no:cacheprovider"], SRV, emu, timeout=3600)
    m = re.search(r"(\d+) failed, (\d+) passed, (\d+) xfailed", out); failed = set(re.findall(r"^FAILED (\S+)", out, re.M))
    ok &= m is not None and (m.group(1), m.group(2), m.group(3)) == ("5", "594", "3") and failed == BASE_FAILED
    det.append(f"pytest={m.group(0) if m else '无汇总'} failed_set_ok={failed == BASE_FAILED}")
    check(ok, "K07 SERVER 产物：26 个测试名、无作弊、参考字面量、Schema 副本逐字节一致、禁止清单零改动、pytest 5/594/3 且失败集合不变、新文件 exactly-once 零命中",
          "; ".join(det))
else:
    print("SKIP  K07 SERVER 产物（验收时 --require-impl server，必须 PASS）")

if "client" in req:
    det = []; ok = True
    f = CLI / "lib/src/analytics/private_note_metrics.dart"; t = read(CLI / "test/analytics/private_note_metrics_test.dart")
    if not f.is_file(): ok = False; det.append("missing private_note_metrics.dart")
    miss = [n for n in CLIENT_TESTS if n not in t]; ok &= not miss; det.append(f"tests_missing={miss[:3]}")
    ok &= "exactly-once" not in read(f) and "exactly-once" not in t; det.append("exactly_once=False")
    ok &= NOTE_REF in t; det.append(f"note_ref_literal={NOTE_REF in t}")
    prot = git(CLI, "diff-tree", "-r", "--name-only", "19afe37", "HEAD", "--",
               "lib/src/persistence/note_database.dart", "lib/src/persistence/note_repository.dart", "lib/src/editor", "pubspec.yaml")
    ok &= prot == ""; det.append(f"protected_empty={prot == ''}")
    env = {"PATH": FL + os.pathsep + os.environ["PATH"]}
    rc, out = run([EXE("flutter"), "analyze"], CLI, env, timeout=1800)
    ok &= rc == 0 and "No issues found!" in out; det.append(f"analyze={rc}")
    rc2, out2 = run([EXE("flutter"), "test"], CLI, env, timeout=3600)
    m = re.search(r"\+(\d+): All tests passed!", out2); ok &= rc2 == 0 and m is not None and int(m.group(1)) >= 332
    det.append(f"flutter_test={rc2}/{m.group(1) if m else '无'}")
    check(ok, "K08 CLIENT 产物：18 个测试名、note_ref 字面量、保护文件零改动、analyze 0、flutter test ≥332", "; ".join(det))
else:
    print("SKIP  K08 CLIENT 产物（验收时 --require-impl client，必须 PASS）")

if "rules" in req:
    det = []; ok = True
    rules_t = read(RULES / "server/functions/test/community_rules.test.ts")
    ok &= "NC-026" in rules_t and "community_behavior_events" in rules_t; det.append(f"append_only_cases={'NC-026' in rules_t}")
    rfile = git(RULES, "diff-tree", "-r", "--name-only", "a354463", "HEAD", "--", "server/firestore.rules")
    ok &= rfile == ""; det.append(f"rules_untouched={rfile == ''}")
    emu = {"FIRESTORE_EMULATOR_HOST": "192.168.0.165:8080", "FIREBASE_AUTH_EMULATOR_HOST": "192.168.0.165:9099"}
    rc, out = run([EXE("npm"), "test", "--", "community_rules"], RULES / "server/functions", emu, timeout=1800)
    ok &= re.search(r"Tests:\s+157 passed, 157 total", out) is not None; det.append(f"rules={rc}")
    check(ok, "K09 RULES 产物：只追加用例、firestore.rules 零改动、npm test 157", "; ".join(det))
else:
    print("SKIP  K09 RULES 产物（验收时 --require-impl rules，必须 PASS）")

print(f"\nNC-026 失败条数：{fails}"); sys.exit(fails)
PY
