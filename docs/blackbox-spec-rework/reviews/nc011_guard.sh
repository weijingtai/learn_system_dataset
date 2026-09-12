#!/usr/bin/env bash
# NC-011 守卫：回归 v1.6 守卫与 verify.sh；核对讨论区契约、API §11 补丁、DESIGN 修正与六件套；
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
SPEC = root / "openspec/annotation-community"; PACK = root / "docs/blackbox-spec-rework/work-items/nc-011"
REST = Path("/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter")
SRV = Path("/Users/jingtaiwei/Git/Public/xuan-server/functions-py")
RULES = Path("/Users/jingtaiwei/Git/Public/xuan-migration/xuan-server")
RN = Path("/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes"); FL = "/Users/jingtaiwei/flutter/bin"
H = ["abe571820b1717be2379d8a60bfa8fc454b6e5158591f62fe1d31876b7eab428",
     "fdbb995205743586e29d5b1bf187b09cd71e332d25059345532ab76991dc37fb",
     "d65171fd03000501a18ad405e805a494b9a6717e27c03306a51fe5ada9dc7bb2"]
# C1（…0001 的游标）只作契约 §6.3 编码示例，§9.2 无测试断言它（T25 夹具不可能产生），故不列入测试字面量要求（act/04 执行方指出，验收 R1 裁定 B）
REFS = ["thr_29d9aa55fe9a6205547731ea3b3dc1a7", "3:b713c1d13d46bdb5", "3:bbe031c2c1299d8c",
        "bmV3ZXN0fC18MjAyNi0wOS0xMVQwODowMDowMC4wMDAwMDJafGNtdF8wMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMg",
        "b2xkZXN0fGNtdF8wMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAyMXwyMDI2LTA5LTExVDA4OjAwOjAxLjAwMDAwNVp8Y210XzAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMTA1"]
SERVER_TESTS = """create_root_comment_writes_comment_revision_thread_outbox_event_atomically comment_payload_hashes_match_reference
thread_id_is_deterministic_from_content_id reply_to_root_has_depth_1_and_same_root reply_to_reply_stays_depth_1_with_root_of_target
reply_to_id_without_root_id_is_400 cross_thread_root_or_target_is_404_not_found_comment root_id_pointing_to_reply_is_404_not_found_comment
reply_to_deleted_root_or_target_is_403_thread_closed reply_to_hidden_target_is_403_thread_closed body_4000_code_points_of_4byte_emoji_passes_and_4001_is_413
blank_body_and_schema_errors_are_400 mentions_over_50_is_413_and_mismatched_mentions_are_dropped non_author_on_non_public_content_is_404_not_found_content
content_author_on_non_public_content_is_403_thread_closed stale_expected_access_version_while_visible_is_409 same_key_replays_and_different_payload_is_409
commenter_counts_track_distinct_visible_authors edit_creates_revision_chain_and_keeps_created_at edit_or_delete_by_non_author_is_403_not_owner
missing_if_match_is_400_and_stale_is_412 malformed_if_match_is_400_without_ledger edit_or_delete_non_visible_comment_is_404
delete_root_leaves_tombstone_and_replies_visible_and_counts_drop list_newest_default_20_with_cursor_and_reply_previews_of_5
list_replies_by_root_oldest_with_cursor_and_newest_is_400 list_orders_same_created_at_by_id_bytes list_etag_matches_reference_and_304_only_after_acl
list_rejects_invalid_limit_order_root_and_cursor list_author_reads_withdrawn_thread_and_others_get_404 withdraw_commits_first_then_comment_retries_and_gets_404
comment_commits_first_then_withdraw_succeeds_and_hides_thread two_comments_and_withdraw_three_way_race_keeps_invariants
comment_new_ids_fixed_across_transaction_retry logs_never_contain_comment_body""".split()
CLIENT_TESTS = """list_comments_sends_order_root_cursor_limit_without_if_none_match create_comment_sends_idempotency_and_expected_access_version_without_if_match
edit_and_delete_comment_send_if_match comment_payload_hashes_match_python_reference comment_create_same_target_does_not_conflict_but_edit_does
comment_restart_with_real_file_close_reopen_resends_same_key comment_lost_response_reconciles_by_get_command_without_new_comment
comment_410_and_503_never_change_key comment_count_port_reads_visible_commenter_count pending_queue_summarizes_comment_commands
discussion_first_level_newest_20_then_load_more_keeps_existing_items discussion_replies_preview_5_then_expand_more
discussion_empty_states_distinguish_no_comments_and_closed discussion_offline_comment_restart_confirms_once_and_pending_mark_clears
discussion_body_over_4000_code_points_blocks_send discussion_409_access_version_keeps_draft_and_prompts
discussion_late_success_after_withdraw_rereads_and_shows_not_visible discussion_tombstones_show_deleted_and_hidden_texts""".split()
SEVEN = ["seven_states discussion " + s for s in ("loading", "empty", "partial", "error", "offline", "stale", "success")]
REST_TESTS = ["comment list declares root id and order query parameters", "comment page requires reply previews and counts",
              "comment create conflict response accepts access version and idempotency problems",
              "comment examples manifest has thirteen entries and validates"]
TEXTS = ["还没有人评论，来写第一条", "该内容不接受新评论", "该评论已删除", "该评论已被隐藏", "内容已不可见", "评论读取失败",
         "内容状态已变化，请确认后重新发送", "评论不能超过 4000 字", "待发送", "加载更多评论", "展开更多回复", "评论加载中",
         "更多评论加载失败", "离线，无法加载评论", "评论更新于 ", "回复加载失败，点此重试", "该评论有未完成的操作"]
BASE_FAILED = {"tests/test_config.py::test_集合名与_ts_逐项一致", "tests/test_registration.py::test_全部_callable_已在入口注册",
               "tests/test_registration.py::test_三个_trigger_已注册", "tests/test_registration.py::test_与_入口总数对齐",
               "tests/test_registration.py::test_没有多余的未声明导出"}
fails = 0
def check(ok, name, detail=""):
    global fails
    if not ok: fails += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""
def run(cmd, cwd, extra=None, timeout=900):
    env = dict(os.environ); env.update(extra or {})
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout)
    return r.returncode, r.stdout + r.stderr
def tree_changes(repo, base, paths):
    return subprocess.run(["git", "-C", str(repo), "diff-tree", "-r", "--name-only", base, "HEAD", "--", *paths], capture_output=True, text=True).stdout.strip()

check(g1 == 0 and g2 == 0, "K01 回归：v1.6 守卫与 verify.sh 均为 0", f"{g1},{g2}")

c = read(SPEC / "contracts/community_discussion.md"); api = read(SPEC / "contracts/community_api.md"); design = read(SPEC / "DESIGN.md")
need = H + REFS + SERVER_TESTS + CLIENT_TESTS + REST_TESTS + TEXTS + ["after_access_read_hook", "too_large.comment_body", "forbidden.thread_closed",
       "visible_commenter_count", "reply_previews", "409ConflictCommentCreate", "seven_states discussion"]
missing = [n for n in need if n not in c]
ok02 = (not missing and all(f"D-NC011-{i:02d}" in c for i in range(1, 21)) and all(f"## {i}." in c for i in range(1, 15))
        and "## 11. NC-011 补丁" in api and "3:b713c1d13d46bdb5" in api
        and "413 + `too_large.mentions`" in design and "400 + `invalid_argument.mentions`" not in design)
check(ok02, "K02 契约：参考值、35+18+4 测试名、文案闭集、D-NC011-01～20、十四节；API §11；DESIGN mention 上限改 413", f"missing={missing[:5]}")

bdd = read(PACK / "BDD.md"); tdd = read(PACK / "TDD.md"); acts = [read(PACK / "act" / f"0{i}.yaml") for i in range(1, 7)]
ids = re.findall(r"^\| ([ATK]\d\d) \|", bdd, re.M)
exp_ids = [f"A{i:02d}" for i in range(1, 5)] + [f"T{i:02d}" for i in range(1, 36)] + [f"K{i:02d}" for i in range(1, 26)]
est = [int((re.search(r"^ESTIMATE_MINUTES: (\d+)", a, re.M) or [0, 0])[1]) for a in acts]
deps = [(re.search(r"^DEPENDS_ON: (.*)$", a, re.M) or [0, ""])[1].strip() for a in acts]
vague = re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况")
files = ["README.md", "BDD.md", "TDD.md", "ACT.yaml", "PROMPT.md", "ACCEPTANCE.md"] + [f"act/0{i}.yaml" for i in range(1, 7)]
hits = [f"{f}:{m.group(0)}" for f in files for m in vague.finditer(read(PACK / f))] + [f"contract:{m.group(0)}" for m in vague.finditer(c)]
counts = ["+23", "+73", "20 passed", "32 passed", "37 passed", "479 passed", "491 passed", "496 passed", "Tests: 89 passed", "+224", "+239"]
ok03 = (ids == exp_ids and all(30 <= e <= 60 for e in est) and deps == ["[]", "[]", "[NC-011-B]", "[NC-011-C]", "[]", "[NC-011-E]"]
        and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits and all(x in tdd for x in counts)
        and all(n in tdd for n in SERVER_TESTS + CLIENT_TESTS + REST_TESTS + SEVEN) and "DISPATCH_PRECONDITION" in read(PACK / "ACT.yaml"))
check(ok03, "K03 六件套：BDD A01～A04/T01～T35/K01～K25、ACT 30–60 分钟、三线依赖链、ON_FAIL/WORKLOAD、无模糊词、计数与测试名",
      f"ids={len(ids)} est={est} deps={deps} vague={hits}")

todo = read(root / "docs/blackbox-spec-rework/SUBAGENT_TODO.md")
check("NC-011" in todo and "community_discussion.md" in todo, "K04 SUBAGENT_TODO 已登记 NC-011 工作包与契约")

if "rest" in req:
    det = []; ok = True
    t = read(REST / "test/community_openapi_contract_test.dart"); y = read(REST / "openapi/openapi.yaml")
    for s in ("RootId:", "CommentOrder:", "CommentReplyPreview:", "409ConflictCommentCreate:", "visible_commenter_count"):
        if s not in y: ok = False; det.append(f"openapi 缺 {s}")
    miss = [n for n in REST_TESTS if n not in t]; ok &= not miss; det.append(f"tests_missing={miss}")
    try:
        man = json.loads(read(REST / "test/fixtures/openapi/examples/manifest.json")); names = [m.get("file") for m in man]
        ok &= len(man) == 13 and all(f in names for f in ("comment_page_with_reply_previews.json", "comment_page_reply_previews_six.json", "comment_tombstone_deleted.json"))
        det.append(f"manifest={len(man)}")
    except Exception as e:
        ok = False; det.append(f"manifest_error={type(e).__name__}")
    rc, out = run(["dart", "test"], REST, {"PATH": FL + ":" + os.environ["PATH"]})
    m = re.search(r"\+(\d+): All tests passed!", out); ok &= rc == 0 and m is not None and int(m.group(1)) >= 73; det.append(f"dart_test={rc}/{m.group(1) if m else '无'}")
    check(ok, "K05 REST 产物：openapi 增量、4 个测试、manifest 13 项、dart test ≥73", "; ".join(det))
else:
    print("SKIP  K05 REST 产物（验收时 --require-impl rest，必须 PASS）")

if "server" in req:
    det = []; ok = True
    for f in ("xuan/community/discussion_service.py", "xuan/handlers/community_comments.py", "tests/test_community_comments.py"):
        if not (SRV / f).is_file(): ok = False; det.append(f"missing {f}")
    t = read(SRV / "tests/test_community_comments.py")
    miss = [n for n in SERVER_TESTS if f"def test_{n}(" not in t]; ok &= not miss; det.append(f"tests_missing={miss[:3]}")
    cheats = [p for p in ("pytest.mark.skip", "pytest.skip(", "xfail", "assert True\n") if p in t]; ok &= not cheats; det.append(f"cheats={cheats}")
    ok &= "after_access_read_hook" in read(SRV / "xuan/community/discussion_service.py")
    ok &= all(h in t for h in H) and all(r in t for r in REFS); det.append(f"ref_literals={all(h in t for h in H) and all(r in t for r in REFS)}")
    prot = tree_changes(SRV, "df5c3da", ["xuan/community/content_service.py", "xuan/community/command_service.py", "xuan/community/access.py",
                        "xuan/community/errors.py", "xuan/community/ids.py", "xuan/community_hash.py", "xuan/handlers/community_contents.py",
                        "xuan/handlers/community_commands.py", "xuan/community/schemas"])
    ok &= prot == ""; det.append(f"protected_empty={prot == ''}")
    rules_t = read(RULES / "server/functions/test/community_rules.test.ts")
    ok &= all(f"'{n}'" in rules_t for n in ("community_threads", "community_comments", "community_comment_revisions"))
    emu = {"PYTHONDONTWRITEBYTECODE": "1", "FIRESTORE_EMULATOR_HOST": "192.168.0.165:8080", "FIREBASE_AUTH_EMULATOR_HOST": "192.168.0.165:9099"}
    rc, out = run([str(SRV / ".venv/bin/python"), "-m", "pytest", "tests", "-q", "-rf", "-p", "no:cacheprovider"], SRV, emu)
    m = re.search(r"(\d+) failed, (\d+) passed, (\d+) xfailed", out); failed = set(re.findall(r"^FAILED (\S+)", out, re.M))
    ok &= m is not None and (m.group(1), m.group(2), m.group(3)) == ("5", "496", "9") and failed == BASE_FAILED
    det.append(f"pytest={m.group(0) if m else '无汇总'} failed_set_ok={failed == BASE_FAILED}")
    rc2, out2 = run(["npm", "test", "--", "community_rules"], RULES / "server/functions", emu)
    ok &= re.search(r"Tests:\s+89 passed, 89 total", out2) is not None; det.append(f"rules={rc2}")
    check(ok, "K06 SERVER 产物：35 个测试名、无作弊、参考值字面量、禁止清单零改动、pytest 5/496/9 且失败集合不变、规则 89", "; ".join(det))
else:
    print("SKIP  K06 SERVER 产物（验收时 --require-impl server，必须 PASS）")

if "client" in req:
    det = []; ok = True
    for f in ("lib/src/community/discussion_controller.dart", "lib/src/community/discussion_panel.dart", "lib/src/community/comment_count_port.dart", "test/community/discussion_test.dart"):
        if not (RN / f).is_file(): ok = False; det.append(f"missing {f}")
    t = read(RN / "test/community/discussion_test.dart")
    miss = [n for n in CLIENT_TESTS if n not in t]; ok &= not miss; det.append(f"tests_missing={miss[:3]}")
    cheats = [p for p in ("skip:", "expect(true, isTrue)") if p in t]; ok &= not cheats; det.append(f"cheats={cheats}")
    ok &= all(h in t for h in H); det.append(f"hash_literals={all(h in t for h in H)}")
    # 终点固定为 NC-011-F 提交：之后的 NC-017 等任务可合法修改 pubspec（验收 R1 发现 HEAD 比较会误判）
    end_c = subprocess.run(["git", "-C", str(RN), "log", "--format=%h", "--grep=NC-011-F", "-1"], capture_output=True, text=True).stdout.strip() or "HEAD"
    prot = subprocess.run(["git", "-C", str(RN), "diff-tree", "-r", "--name-only", "4588f78", end_c, "--", "lib/src/domain", "lib/src/persistence", "lib/src/editor", "lib/src/history", "test/persistence", "test/contracts",
                        "test/editor", "test/history", "test/support", "test/community/command_queue_test.dart", "test/community/community_api_test.dart",
                        "test/community/publication_flow_test.dart", "test/community/seven_states_test.dart", "pubspec.yaml", "pubspec.lock",
                        "lib/src/community/community_database.dart"], capture_output=True, text=True).stdout.strip()
    ok &= prot == ""; det.append(f"protected_empty={prot == ''} end={end_c}")
    envf = {"PATH": FL + ":" + os.environ["PATH"]}
    rc, out = run(["flutter", "analyze"], RN, envf); ok &= rc == 0; det.append(f"analyze={rc}")
    rc, out = run(["flutter", "test", "test/community/discussion_test.dart", "--reporter", "expanded"], RN, envf)
    miss7 = [n for n in SEVEN if n not in out]; ok &= rc == 0 and not miss7; det.append(f"seven_missing={miss7}")
    rc, out = run(["flutter", "test"], RN, envf)
    m = re.search(r"\+(\d+): All tests passed!", out); ok &= rc == 0 and m is not None and int(m.group(1)) >= 239; det.append(f"test={rc}/{m.group(1) if m else '无'}")
    check(ok, "K07 CLIENT 产物：文件齐全、18 个测试名 + 七状态、无作弊、H1～H3 字面量、受保护路径零改动、analyze 0、flutter test ≥239", "; ".join(det))
else:
    print("SKIP  K07 CLIENT 产物（验收时 --require-impl client，必须 PASS）")

print(f"\nNC-011 失败条数：{fails}"); sys.exit(fails)
PY
