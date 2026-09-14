#!/usr/bin/env bash
# NC-014 守卫：K01 回归（v1.6 守卫、verify.sh、nc013_guard.sh 规格模式）；K02 契约字面量
# （八端口、dedup_retention_ms、26 测试名、D-NC014-01～11、十节计数、红线词形零命中）；
# K03 六件套结构与模糊词零命中；K04 SUBAGENT_TODO 登记；K05 PACKAGE 产物；K06 CLIENT 产物。
# --require-impl package|client|all（可逗号组合）时核对对应仓库产物并运行测试；基线期 K05/K06 SKIP。
# 路径布局与 Windows 适配沿用 nc013_guard.sh（D-NC012-23）。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"
MODE="${1:-}"; LINES="${2:-all}"
bash "$ROOT/openspec/annotation-community/review_v1_6_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
bash "$ROOT/docs/blackbox-spec-rework/reviews/nc013_guard.sh" >/dev/null 2>&1; g3=$?
"$ROOT/.venv/Scripts/python.exe" - "$ROOT" "$g1" "$g2" "$g3" "$MODE" "$LINES" <<'PY'
import json, os, re, shutil, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1]); g1, g2, g3 = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
mode = sys.argv[5]; lines = sys.argv[6]
req = set()
if mode == "--require-impl":
    req = {"package", "client"} if lines in ("", "all") else set(lines.split(","))
SPEC = root / "openspec/annotation-community"; PACK = root / "docs/blackbox-spec-rework/work-items/nc-014"
NOTIF = Path("D:/Programme/xuan/notification")
CLIENT = Path("D:/Programme/xuan/reading-notes")
FL = "D:/apps/apps/flutter/bin"
WIN = os.name == "nt"
EXE = lambda name: (shutil.which(name) or name) if WIN else name
PKG_TESTS = """push_timing_parses_dedup_retention_ms_from_l2_timing
push_timing_parses_absent_dedup_retention_ms_as_null_without_fallback
push_timing_rejects_non_positive_dedup_retention_ms
package_sources_contain_no_hardcoded_dedup_window_literal
dedup_retention_marks_entry_expired_exactly_at_window_boundary
dedup_retention_keeps_entries_strictly_inside_window
dedup_retention_trim_forgets_expired_ids_only
dedup_retention_is_exported_from_package_barrel""".split()
CLIENT_TESTS = """community_frame_dispatch_routes_notifier_push_and_resync_to_package_pipeline
community_frame_dispatch_routes_community_data_to_business_upsert_without_delivery_id
community_delivery_log_adapter_persists_and_reports_was_duplicate
community_delivery_log_acks_each_device_and_purpose_delivery_verbatim
community_delivery_log_acks_new_delivery_when_business_entry_already_exists
community_persist_failure_sends_no_ack_and_advances_no_cursor
community_delivery_log_trims_dedup_rows_by_package_retention_window
community_receipt_transport_sends_batch_verbatim_to_notifier_receipts
community_receipt_rejection_settles_batch_observable_without_probing
community_connection_token_source_obtains_authorized_channels
community_backfill_source_maps_r10_page_without_transport_ids
community_backfill_entries_upsert_business_list_by_notification_id
community_message_body_fetcher_degrades_when_r9_is_unauthorized_404
community_notification_list_shows_event_count_aggregation
community_notification_tap_opens_content_detail_discussion_top
community_notification_tap_inaccessible_target_lands_unified_placeholder
community_notification_tables_are_scoped_by_account_switch
community_mute_entry_puts_and_deletes_content_mute""".split()
PORTS = ["RemoteConfigSource", "PushConfigCache", "DeliveryLog", "RealtimeChannel", "ReceiptTransport",
         "ConnectionTokenSource", "BackfillSource", "MessageBodyFetcher", "PushTokenRegistry",
         "NotifierRemoteConfigSource", "LocalPushConfigCache", "DriftDeliveryLog", "SseRealtimeChannel",
         "NotifierReceiptTransport", "NotifierConnectionTokenSource", "CommunityBackfillSource",
         "CommunityMessageBodyFetcher", "NotificationTargetRouter", "CommunityUnreadableTargetPage",
         "CommunityNotificationListPage", "CommunityNotificationWiring", "CommunityNotificationDatabase",
         "DedupRetention", "NotificationCenterPage", "SocialNotificationItem", "ContentDetailPage",
         "BodyFetchWakeHandler", "ReceivePipeline", "AckPipeline", "ConnectionManager", "FrameDecoder"]
PKG_FILES = {"lib/src/config/push_config.dart", "lib/src/receive/dedup_store.dart", "lib/notification.dart",
             "docs/from-server-coder.md", "docs/integration-guide.md", "test/receive/dedup_retention_test.dart"}
CLIENT_FILES = {"pubspec.yaml", "pubspec.lock", "analysis_options.yaml",
                "lib/src/notifications/community_notification_adapters.dart",
                "lib/src/notifications/community_notification_adapters.g.dart",
                "lib/src/notifications/notification_target_router.dart",
                "test/notifications/community_notifications_test.dart"}
NOTIF_GITEA = "http://192.168.0.165:3000/xuan/notification.git"
SOCIAL_GITEA = "http://192.168.0.165:3000/xuan/social.git"
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
def dart_src_literal_hits(repo):
    hits = []
    lib = repo / "lib"
    if lib.is_dir():
        for p in lib.rglob("*.dart"):
            t = p.read_text(encoding="utf-8", errors="replace")
            if "604800000" in t or "Duration(days: 7)" in t:
                hits.append(str(p))
    return hits

check(g1 == 0 and g2 == 0 and g3 == 0, "K01 回归：v1.6 守卫、verify.sh、nc013_guard 规格模式均为 0", f"{g1},{g2},{g3}")

c = read(SPEC / "contracts/community_notification_host.md")
need = PORTS + PKG_TESTS + CLIENT_TESTS + ["dedup_retention_ms", "timing.dedup_retention_ms", "604800000",
       "NotificationBody", "NotificationEntry", "NotificationPage", "NotificationMuteState",
       "/v1/community/notifications/pull", "/v1/community/notifications/mutes/", "notifier_delivery_id",
       "latest_notification_id", "event_count", "空串哨兵", "满窗即裁", "该内容已不可访问",
       "不构成端到端恰好一次", "INTEGRATION_BASELINE"] + [f"D-NC014-{i:02d}" for i in range(1, 12)]
missing = [n for n in need if n not in c]
ok02 = (not missing and all(f"## {i}. " in c for i in range(1, 11))
        and "exactly-once" not in c
        and not re.search(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况", c))
check(ok02, "K02 契约：八端口/adapter 类名、dedup_retention_ms、26 测试名、路径/Schema、D-NC014-01～11、十节、红线词形与模糊词零命中",
      f"missing={missing[:5]}")

bdd = read(PACK / "BDD.md"); tdd = read(PACK / "TDD.md"); readme = read(PACK / "README.md")
acts = [read(PACK / "act" / f"0{i}.yaml") for i in range(1, 3)]
ids = re.findall(r"^\| ([PC]\d\d) \|", bdd, re.M)
exp_ids = [f"P{i:02d}" for i in range(1, 9)] + [f"C{i:02d}" for i in range(1, 19)]
est = [int((re.search(r"^ESTIMATE_MINUTES: (\d+)", a, re.M) or [0, 0])[1]) for a in acts]
deps = [(re.search(r"^DEPENDS_ON: (.*)$", a, re.M) or [0, ""])[1].strip() for a in acts]
vague = re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况")
files = ["README.md", "BDD.md", "TDD.md", "ACT.yaml", "PROMPT.md", "ACCEPTANCE.md", "act/01.yaml", "act/02.yaml"]
hits = [f"{f}:{m.group(0)}" for f in files for m in vague.finditer(read(PACK / f))]
redline = [f for f in files if "exactly-once" in read(PACK / f)]
acts_ok = all(("ON_FAIL" in a and "WORKLOAD" in a and "TESTS_FIRST" in a and "BASELINE_EXIT_CODES" in a
               and "Co-Authored-By: GLM-5.3-Flash <noreply@z.ai>" in a) for a in acts)
ok03 = (ids == exp_ids and all(30 <= e <= 60 for e in est) and deps == ["[]", "[NC-014-A]"]
        and acts_ok and not hits and not redline
        and all(x in tdd for x in ("+202: All tests passed!", "+8: All tests passed!", "+314: All tests passed!",
                                   "+18: All tests passed!", "No issues found!", "+194", "+296"))
        and all(n in tdd for n in PKG_TESTS + CLIENT_TESTS)
        and "DISPATCH_PRECONDITION" in read(PACK / "ACT.yaml")
        and all(h in readme for h in ("518670b", "107ec90", "b60bfbd", "992088e", "community_notification_host.md")))
check(ok03, "K03 六件套：BDD P01～P08/C01～C18、ACT 30–60 分钟、串行依赖链、ON_FAIL/WORKLOAD/COMMIT 尾注、无模糊词与红线词形、计数与 26 测试名、README 四 HEAD",
      f"ids={len(ids)} est={est} deps={deps} vague={hits} redline={redline}")

todo = read(root / "docs/blackbox-spec-rework/SUBAGENT_TODO.md")
check("NC-014" in todo and "community_notification_host.md" in todo, "K04 SUBAGENT_TODO 已登记 NC-014 工作包与契约")

if "package" in req:
    det = []; ok = True
    for f in ("lib/src/config/push_config.dart", "lib/src/receive/dedup_store.dart", "lib/notification.dart",
              "test/receive/dedup_retention_test.dart"):
        if not (NOTIF / f).is_file(): ok = False; det.append(f"missing {f}")
    t = read(NOTIF / "test/receive/dedup_retention_test.dart")
    miss = [n for n in PKG_TESTS if n not in t]; ok &= not miss; det.append(f"tests_missing={miss}")
    pc = read(NOTIF / "lib/src/config/push_config.dart"); ds = read(NOTIF / "lib/src/receive/dedup_store.dart")
    ok &= "dedup_retention_ms" in pc and "DedupRetention" in ds and "DedupRetention" in read(NOTIF / "lib/notification.dart")
    lit = dart_src_literal_hits(NOTIF); ok &= not lit; det.append(f"lib_literal_hits={lit}")
    cheats = [w for w in ("skip:", "skipTest", "assert(true)") if w in t]; ok &= not cheats; det.append(f"cheats={cheats}")
    ok &= "exactly-once" not in t and not vague.search(t); det.append("redline_vague_clean")
    changed = set(git(NOTIF, "diff-tree", "-r", "--name-only", "518670b", "HEAD").splitlines())
    ok &= changed == PKG_FILES; det.append(f"files={sorted(changed) if changed != PKG_FILES else 'exact_6'}")
    envf = {"PATH": FL + os.pathsep + os.environ["PATH"]}
    rc, out = run([EXE("flutter"), "test"], NOTIF, envf, timeout=2400)
    m = re.search(r"\+(\d+): All tests passed!", out); ok &= rc == 0 and m is not None and int(m.group(1)) >= 202
    det.append(f"flutter_test={rc}/{m.group(1) if m else '无'}")
    check(ok, "K05 PACKAGE 产物：文件集恰 6、8 测试名、dedup_retention_ms 解析与 DedupRetention 导出、lib/ 无窗口字面量、既有零改动、flutter test ≥202",
          "; ".join(det))
else:
    print("SKIP  K05 PACKAGE 产物（验收时 --require-impl package，必须 PASS）")

if "client" in req:
    det = []; ok = True
    for f in ("lib/src/notifications/community_notification_adapters.dart",
              "lib/src/notifications/notification_target_router.dart",
              "test/notifications/community_notifications_test.dart"):
        if not (CLIENT / f).is_file(): ok = False; det.append(f"missing {f}")
    t = read(CLIENT / "test/notifications/community_notifications_test.dart")
    miss = [n for n in CLIENT_TESTS if n not in t]; ok &= not miss; det.append(f"tests_missing={miss[:3]}")
    pub = read(CLIENT / "pubspec.yaml")
    ok &= NOTIF_GITEA in pub and SOCIAL_GITEA in pub; det.append(f"pub_deps={NOTIF_GITEA in pub and SOCIAL_GITEA in pub}")
    ad = read(CLIENT / "lib/src/notifications/community_notification_adapters.dart")
    rt = read(CLIENT / "lib/src/notifications/notification_target_router.dart")
    src = ad + rt
    ok &= all(k in src for k in ("DriftDeliveryLog", "CommunityBackfillSource", "CommunityMessageBodyFetcher",
                                 "CommunityUnreadableTargetPage", "CommunityNotificationListPage"))
    legacy = [w for w in ("notification_page.dart", "notification_viewmodel.dart", "playground_state_widgets.dart", "firebase_messaging") if w in src or w in rt]
    ok &= not legacy; det.append(f"legacy_or_fcm={legacy}")
    cheats = [w for w in ("skip:", "skipTest", "assert(true)") if w in t]; ok &= not cheats; det.append(f"cheats={cheats}")
    ok &= "exactly-once" not in t and "exactly-once" not in src and not vague.search(t) and not vague.search(src)
    changed = set(git(CLIENT, "diff-tree", "-r", "--name-only", "107ec90", "HEAD").splitlines())
    ok &= changed == CLIENT_FILES; det.append(f"files={sorted(changed) if changed != CLIENT_FILES else 'exact_6'}")
    prot = git(CLIENT, "diff-tree", "-r", "--name-only", "107ec90", "HEAD", "--", "lib/src/community")
    ok &= prot == ""; det.append(f"community_untouched={prot == ''}")
    envf = {"PATH": FL + os.pathsep + os.environ["PATH"]}
    rc, out = run([EXE("flutter"), "analyze"], CLIENT, envf, timeout=1800)
    ok &= rc == 0 and "No issues found!" in out; det.append(f"analyze={rc}/{'clean' if 'No issues found!' in out else 'dirty'}")
    rc, out = run([EXE("flutter"), "test"], CLIENT, envf, timeout=3600)
    m = re.search(r"\+(\d+): All tests passed!", out); ok &= rc == 0 and m is not None and int(m.group(1)) >= 314
    det.append(f"flutter_test={rc}/{m.group(1) if m else '无'}")
    check(ok, "K06 CLIENT 产物：文件集恰 6、18 测试名、pubspec 双 git 依赖、无遗留页/FCM 插件、lib/src/community 零改动、analyze 0、flutter test ≥314、红线词形与模糊词零命中",
          "; ".join(det))
else:
    print("SKIP  K06 CLIENT 产物（验收时 --require-impl client，必须 PASS）")

print(f"\nNC-014 失败条数：{fails}"); sys.exit(fails)
PY
