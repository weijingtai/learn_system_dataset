#!/usr/bin/env bash
# NC-012a 守卫：回归 v1.6 守卫与 verify.sh；核对互动契约、API §12 补丁与六件套；
# --require-impl rest|server|client|all（可逗号组合）时核对对应仓库产物并运行测试。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"
MODE="${1:-}"; LINES="${2:-all}"
bash "$ROOT/openspec/annotation-community/review_v1_6_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
"$ROOT/.venv/bin/python" - "$ROOT" "$g1" "$g2" "$MODE" "$LINES" <<'PY'
import json, os, re, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1]); g1, g2 = int(sys.argv[2]), int(sys.argv[3]); mode = sys.argv[4]; lines = sys.argv[5]
req = set()
if mode == "--require-impl":
    req = {"rest", "server", "client"} if lines in ("", "all") else set(lines.split(","))
SPEC = root / "openspec/annotation-community"; PACK = root / "docs/blackbox-spec-rework/work-items/nc-012a"
REST = Path("/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter")
SRV = Path("/Users/jingtaiwei/Git/Public/xuan-server/functions-py")
RULES = Path("/Users/jingtaiwei/Git/Public/xuan-migration/xuan-server")
RN = Path("/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes"); FL = "/Users/jingtaiwei/flutter/bin"
H = ["09cbea8cdeff9a18a58a8eafd4227d436e3e3571120b5b35fb8e0607415181f9", "26c51836823dc9f972ade10c886b40212a0021651a8a343f237f3a6f69956b90",
     "1a8f01148eaeb612891d175ac6b14a9fca9ca89995a5582ac7b12ed9aedd6620", "481e858b66f0a48c074ef3d5e4b2dc1ea3a899a9179f6c5cac3af4aa60b970a2",
     "608dfd80e74d5f37a190ee29346c857ab7da5c707aafef094fc25018edf058af", "b6f3caec02355f0365e49b5b028368911a09fd7651206b8ab5d4b5484e4bb07a"]
SREFS = ["rct_ede12cd76c76e944120f75d6ccf424ad", "bmk_58da728e583165f3f33e853295ecf8de",
         "MjAyNi0wOS0xMVQwODowMDowMC4wMDAwMDJafHNocl8wMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMg", '"1:1:0"', '"0:1:0"']
SERVER_TESTS = """reaction_like_writes_reaction_counts_outbox_event_atomically interaction_payload_hashes_and_ids_match_reference
reaction_cancel_keeps_null_row_and_decrements_count reaction_switch_like_to_dislike_moves_count reaction_same_value_is_noop_without_version_bump
reaction_if_match_missing_400_stale_412_malformed_400_without_ledger reaction_old_like_replay_after_cancel_returns_original_and_state_stays_null
reaction_two_devices_same_baseline_one_commits_one_412 reaction_two_accounts_have_independent_values_and_shared_counts
reaction_ten_concurrent_accounts_count_exactly_ten reaction_on_non_public_content_is_404_for_others reaction_author_closed_403_and_comment_target_rules
reaction_after_target_purge_replay_does_not_revive reaction_get_etag_literal_and_304_only_after_acl reaction_invalid_target_and_body_are_400
bookmark_set_private_noop_optional_if_match_and_get bookmark_on_unreadable_target_is_404 share_create_by_author_201_others_403_closed_403
share_resolve_returns_target_and_all_failures_share_one_404 share_revoke_owner_200_idempotent_non_owner_403_missing_404
my_share_links_desc_paging_cursor_literal_and_owner_only my_share_links_rejects_invalid_limit_and_cursor
report_create_201_keyed_by_command_id_with_exact_fields report_detail_500_code_points_passes_501_is_413_and_bad_reason_400
report_on_unreadable_target_is_404 interaction_commands_replay_same_key_and_conflict_on_different_payload logs_never_contain_report_detail""".split()
CLIENT_TESTS = """reaction_api_sends_if_match_and_parses_reaction_response bookmark_api_optional_if_match_and_get_bookmark
share_and_report_api_paths_headers_and_bodies interaction_payload_hashes_match_python_reference
interaction_restart_with_real_file_close_reopen_resends_same_key interaction_lost_response_reconciles_by_get_command_without_new_report
interaction_410_and_503_never_change_key pending_queue_summarizes_interaction_commands mention_ref_is_single_public_type_for_notes_and_comments
reconcile_mentions_matches_python_reference_vectors reconcile_mentions_counts_code_points_not_utf16_units
reaction_rapid_toggle_coalesces_to_serial_commands_with_confirmed_version reaction_late_older_version_response_does_not_roll_back
reaction_412_refreshes_state_and_does_not_auto_retry reaction_restart_restores_pending_value_and_next_action_uses_read_version
bookmark_toggle_offline_restart_confirms_once report_marks_reported_locally_before_send_and_clears_on_rejection
share_controller_creates_lists_and_revokes_links resolve_share_maps_404_to_unavailable_and_transport_to_offline
interaction_bar_shows_counts_toggles_and_has_48dp_hit_targets report_sheet_submits_and_shows_accepted_then_folds_content
reported_fold_survives_restart_and_can_be_expanded share_links_page_states_revoke_confirmation_and_load_more
share_link_landing_page_unavailable_offline_and_open content_detail_page_optional_builders_keep_default_render
discussion_panel_comment_decorator_wraps_visible_comments_only""".split()
REST_TESTS = ["reaction and bookmark writes return wrapped responses with command", "my share links and bookmark read paths are declared",
              "interaction write errors declare detail too large", "interaction examples manifest has seventeen entries and validates"]
TEXTS = ["你已举报该内容", "你已举报该评论", "赞踩状态已在其他设备更新", "撤销后，已发出的链接将无法打开", "离线，无法打开分享链接",
         "补充说明不能超过 500 字", "举报未能提交，请重试", "内容未公开，无法分享", "网络恢复后将创建分享链接", "分享链接加载中"]
BASE_FAILED = {"tests/test_config.py::test_集合名与_ts_逐项一致", "tests/test_registration.py::test_全部_callable_已在入口注册",
               "tests/test_registration.py::test_三个_trigger_已注册", "tests/test_registration.py::test_与_入口总数对齐",
               "tests/test_registration.py::test_没有多余的未声明导出"}
NEW_COLS = ("community_reactions", "community_reaction_counts", "community_bookmarks", "community_share_links", "community_reports")
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

c = read(SPEC / "contracts/community_interactions.md"); api = read(SPEC / "contracts/community_api.md")
need = H + SREFS + SERVER_TESTS + CLIENT_TESTS + REST_TESTS + TEXTS + ["reconcileMentions", "ReactionResponse", "BookmarkResponse", "ShareLinkPage",
       "listMyShareLinks", "getBookmarkState", "reaction.liked", "too_large.detail", "commentDecorator", "snapshotWrapper", "interactionBuilder"]
missing = [n for n in need if n not in c]
mvec = all(f"| M{i} |" in c for i in range(1, 9))
ok02 = (not missing and mvec and all(f"D-NC012-{i:02d}" in c for i in range(1, 22)) and all(f"## {i}." in c for i in range(1, 16))
        and "## 12. NC-012a 补丁" in api and "too_large.detail" in api)
check(ok02, "K02 契约：6 哈希 + ID/游标/ETag、27+26+4 测试名、M1～M8、文案、D-NC012-01～21、十五节；API §12", f"missing={missing[:5]} mvec={mvec}")

bdd = read(PACK / "BDD.md"); tdd = read(PACK / "TDD.md"); acts = [read(PACK / "act" / f"0{i}.yaml") for i in range(1, 7)]
ids = re.findall(r"^\| ([AIJ]\d\d) \|", bdd, re.M)
exp_ids = [f"A{i:02d}" for i in range(1, 5)] + [f"I{i:02d}" for i in range(1, 28)] + [f"J{i:02d}" for i in range(1, 27)]
est = [int((re.search(r"^ESTIMATE_MINUTES: (\d+)", a, re.M) or [0, 0])[1]) for a in acts]
deps = [(re.search(r"^DEPENDS_ON: (.*)$", a, re.M) or [0, ""])[1].strip() for a in acts]
vague = re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况")
files = ["README.md", "BDD.md", "TDD.md", "ACT.yaml", "PROMPT.md", "ACCEPTANCE.md"] + [f"act/0{i}.yaml" for i in range(1, 7)]
hits = [f"{f}:{m.group(0)}" for f in files for m in vague.finditer(read(PACK / f))] + [f"contract:{m.group(0)}" for m in vague.finditer(c)]
counts = ["+27", "+77", "19 passed", "36 passed", "515 passed", "535 passed", "6 xfailed", "Tests: 129 passed", "+281", "+289", "+296"]
ok03 = (ids == exp_ids and all(30 <= e <= 60 for e in est) and deps == ["[]", "[]", "[NC-012a-B]", "[]", "[NC-012a-D]", "[NC-012a-E]"]
        and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits and all(x in tdd for x in counts)
        and all(n in tdd for n in SERVER_TESTS + CLIENT_TESTS + REST_TESTS) and "DISPATCH_PRECONDITION" in read(PACK / "ACT.yaml"))
check(ok03, "K03 六件套：BDD A01～A04/I01～I27/J01～J26、ACT 30–60 分钟、三线依赖链、ON_FAIL/WORKLOAD、无模糊词、计数与测试名",
      f"ids={len(ids)} est={est} deps={deps} vague={hits}")

todo = read(root / "docs/blackbox-spec-rework/SUBAGENT_TODO.md")
check("NC-012a" in todo and "community_interactions.md" in todo, "K04 SUBAGENT_TODO 已登记 NC-012a 工作包与契约")

if "rest" in req:
    det = []; ok = True
    t = read(REST / "test/community_openapi_contract_test.dart"); y = read(REST / "openapi/openapi.yaml")
    for s in ("ReactionResponse:", "BookmarkResponse:", "ShareLinkPage:", "/v1/community/me/share-links:", "getBookmarkState", "listMyShareLinks"):
        if s not in y: ok = False; det.append(f"openapi 缺 {s}")
    miss = [n for n in REST_TESTS if n not in t]; ok &= not miss; det.append(f"tests_missing={miss}")
    try:
        man = json.loads(read(REST / "test/fixtures/openapi/examples/manifest.json")); names = [m.get("file") for m in man]
        ok &= len(man) == 17 and all(f in names for f in ("reaction_response_like.json", "bookmark_response_active.json",
                                                         "share_link_page_with_revoked.json", "reaction_state_value_love.json"))
        det.append(f"manifest={len(man)}")
    except Exception as e:
        ok = False; det.append(f"manifest_error={type(e).__name__}")
    rc, out = run(["dart", "test"], REST, {"PATH": FL + ":" + os.environ["PATH"]})
    m = re.search(r"\+(\d+): All tests passed!", out); ok &= rc == 0 and m is not None and int(m.group(1)) >= 77; det.append(f"dart_test={rc}/{m.group(1) if m else '无'}")
    check(ok, "K05 REST 产物：openapi 增量、4 个测试、manifest 17 项、dart test ≥77", "; ".join(det))
else:
    print("SKIP  K05 REST 产物（验收时 --require-impl rest，必须 PASS）")

if "server" in req:
    det = []; ok = True
    for f in ("xuan/community/interaction_service.py", "xuan/handlers/community_interactions.py", "tests/test_community_interactions.py"):
        if not (SRV / f).is_file(): ok = False; det.append(f"missing {f}")
    t = read(SRV / "tests/test_community_interactions.py")
    miss = [n for n in SERVER_TESTS if f"def test_{n}(" not in t]; ok &= not miss; det.append(f"tests_missing={miss[:3]}")
    cheats = [p for p in ("pytest.mark.skip", "pytest.skip(", "xfail", "assert True\n") if p in t]; ok &= not cheats; det.append(f"cheats={cheats}")
    ok &= all(h in t for h in H) and all(r in t for r in SREFS); det.append(f"ref_literals={all(h in t for h in H) and all(r in t for r in SREFS)}")
    acl = read(SRV / "tests/test_community_acl_sweep.py"); ok &= "owner: NC-012" not in acl and "community_share_py" in acl; det.append(f"acl_e4_live={'owner: NC-012' not in acl}")
    prot = git(SRV, "diff-tree", "-r", "--name-only", "0fad16e", "HEAD", "--", "xuan/community/content_service.py", "xuan/community/command_service.py",
               "xuan/community/discussion_service.py", "xuan/community/access.py", "xuan/community/errors.py", "xuan/community/ids.py", "xuan/community_hash.py",
               "xuan/handlers/community_contents.py", "xuan/handlers/community_commands.py", "xuan/handlers/community_comments.py", "xuan/community/schemas",
               "tests/test_community_comments.py", "tests/test_community_commands.py")
    ok &= prot == ""; det.append(f"protected_empty={prot == ''}")
    rules_t = read(RULES / "server/functions/test/community_rules.test.ts")
    ok &= all(f"'{n}'" in rules_t for n in NEW_COLS)
    emu = {"PYTHONDONTWRITEBYTECODE": "1", "FIRESTORE_EMULATOR_HOST": "192.168.0.165:8080", "FIREBASE_AUTH_EMULATOR_HOST": "192.168.0.165:9099"}
    rc, out = run([str(SRV / ".venv/bin/python"), "-m", "pytest", "tests", "-q", "-rf", "-p", "no:cacheprovider"], SRV, emu)
    m = re.search(r"(\d+) failed, (\d+) passed, (\d+) xfailed", out); failed = set(re.findall(r"^FAILED (\S+)", out, re.M))
    ok &= m is not None and (m.group(1), m.group(2), m.group(3)) == ("5", "535", "6") and failed == BASE_FAILED
    det.append(f"pytest={m.group(0) if m else '无汇总'} failed_set_ok={failed == BASE_FAILED}")
    rc2, out2 = run(["npm", "test", "--", "community_rules"], RULES / "server/functions", emu)
    ok &= re.search(r"Tests:\s+129 passed, 129 total", out2) is not None; det.append(f"rules={rc2}")
    check(ok, "K06 SERVER 产物：27 个测试名、无作弊、参考值字面量、E4 转真、禁止清单零改动、pytest 5/535/6 且失败集合不变、规则 129", "; ".join(det))
else:
    print("SKIP  K06 SERVER 产物（验收时 --require-impl server，必须 PASS）")

if "client" in req:
    det = []; ok = True
    for f in ("lib/src/community/mention_adapter.dart", "lib/src/community/interaction_controller.dart", "lib/src/community/share_links_controller.dart",
              "lib/src/community/interaction_bar.dart", "lib/src/community/report_sheet.dart", "lib/src/community/reported_fold.dart",
              "lib/src/community/share_links_page.dart", "lib/src/community/share_link_landing_page.dart", "test/community/interactions_test.dart"):
        if not (RN / f).is_file(): ok = False; det.append(f"missing {f}")
    t = read(RN / "test/community/interactions_test.dart")
    miss = [n for n in CLIENT_TESTS if n not in t]; ok &= not miss; det.append(f"tests_missing={miss[:3]}")
    cheats = [p for p in ("skip:", "expect(true, isTrue)") if p in t]; ok &= not cheats; det.append(f"cheats={cheats}")
    ok &= all(h in t for h in H); det.append(f"hash_literals={all(h in t for h in H)}")
    single = "class MentionRef" not in read(RN / "lib/src/community/models.dart") and "hide MentionRef" not in read(RN / "lib/reading_notes.dart")
    ok &= single; det.append(f"mention_ref_single={single}")
    end_c = git(RN, "log", "--format=%h", "--grep=NC-012a-F", "-1") or "HEAD"
    prot = git(RN, "diff-tree", "-r", "--name-only", "d80703b", end_c, "--", "lib/src/domain", "lib/src/persistence", "lib/src/editor", "lib/src/history",
               "lib/src/storage", "lib/src/export", "test/persistence", "test/contracts", "test/editor", "test/history", "test/support", "test/storage",
               "test/export", "test/community/command_queue_test.dart", "test/community/community_api_test.dart", "test/community/publication_flow_test.dart",
               "test/community/seven_states_test.dart", "test/community/discussion_test.dart", "pubspec.yaml", "pubspec.lock",
               "lib/src/community/community_database.dart")
    ok &= prot == ""; det.append(f"protected_empty={prot == ''} end={end_c}")
    envf = {"PATH": FL + ":" + os.environ["PATH"]}
    rc, out = run(["flutter", "analyze"], RN, envf); ok &= rc == 0; det.append(f"analyze={rc}")
    rc, out = run(["flutter", "test"], RN, envf)
    m = re.search(r"\+(\d+): All tests passed!", out); ok &= rc == 0 and m is not None and int(m.group(1)) >= 296; det.append(f"test={rc}/{m.group(1) if m else '无'}")
    check(ok, "K07 CLIENT 产物：文件齐全、26 个测试名、无作弊、哈希字面量、MentionRef 单一、受保护路径零改动、analyze 0、flutter test ≥296", "; ".join(det))
else:
    print("SKIP  K07 CLIENT 产物（验收时 --require-impl client，必须 PASS）")

print(f"\nNC-012a 失败条数：{fails}"); sys.exit(fails)
PY
