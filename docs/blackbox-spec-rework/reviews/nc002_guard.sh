#!/usr/bin/env bash
# NC-002 守卫：回归既有守卫；核对契约、fixture、参考编码器自洽与六件套结构；--require-impl 时核对执行产物。
# 用法：bash docs/blackbox-spec-rework/reviews/nc002_guard.sh [--require-impl]
# 退出码 = 失败条数。只做结构与事实核对，不代替语义审查。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../../.." && pwd)"
REQ="${1:-}"
LC_ALL=C bash "$ROOT/openspec/annotation-community/review_v1_5_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
bash "$ROOT/openspec/schemas/verify.sh" >/dev/null 2>&1; g3=$?
"$ROOT/.venv/bin/python" - "$ROOT" "$g1" "$g2" "$g3" "$REQ" <<'PY'
import json, re, subprocess, sys, importlib.util, tempfile, shutil
from pathlib import Path
root = Path(sys.argv[1]); g1, g2, g3 = map(int, sys.argv[2:5]); req = sys.argv[5] == "--require-impl"
SPEC = root / "openspec/annotation-community"; PACK = root / "docs/blackbox-spec-rework/work-items/nc-002"
SERVER = Path("/Users/jingtaiwei/Git/Public/xuan-server/functions-py")
fails = 0
def check(ok, name, detail=""):
    global fails
    if not ok: fails += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""

check(g1 == 0 and g2 == 0 and g3 == 0, "K01 回归：v1.5 守卫、annotation verify.sh、schemas/verify.sh 均为 0", f"{g1},{g2},{g3}")

# K02 契约
models = read(SPEC / "contracts/community-models.md"); sm = read(SPEC / "contracts/state-machines.md")
m_enum = re.search(r"## 枚举总表.*?\n\|.*?\n\|[-| ]+\n((?:\|[^\n]*\n)+)", sm, re.S)
enum_rows = [r for r in (m_enum.group(1).split("\n") if m_enum else []) if r.startswith("|")]
ENUM = set()
for r in enum_rows:
    cells = [c.strip() for c in r.strip("|").split("|")]
    ENUM |= set(re.findall(r"`([^`]+)`", cells[3] if len(cells) > 3 else ""))
sm_heads = re.findall(r"^## SM-(\d)\w? ", sm, re.M)
prefix_rows = len(re.findall(r"\| `[a-z]+_` \|", models))
ok02 = (len(enum_rows) == 11 and len(ENUM) == 41 and sorted(set(sm_heads)) == [str(i) for i in range(1, 10)]
        and all(f"D-NC002-0{i}" in models for i in range(1, 7)) and "D-NC002-10" in models and "D-NC002-11" in models and all(f"D-NC002-0{i}" in sm for i in range(7, 10)) and "D-NC002-10" in sm
        and prefix_rows >= 17 and "17 个操作字符串闭集" in models)
check(ok02, "K02 契约：枚举总表 11 行且恰 41 值、SM-1～9 齐全、前缀 17 行、决定 D-NC002-01～11 登记", f"rows={len(enum_rows)} enum={len(ENUM)} heads={sorted(set(sm_heads))} prefix_rows={prefix_rows}")

# K03 fixture 结构（独立实现，不依赖 validate_fixtures.py）
FX = SPEC / "fixtures/community"
WANT = {"content_hash_cases.json","id_format_cases.json","command_id_cases.json","limit_cases.json","mention_cases.json","state_combinations.json","lifecycle_transition_cases.json","comment_reply_cases.json","revision_cases.json"}
files = {p.name for p in FX.glob("*.json")}
STATE_KEYS = {"visibility","lifecycle","moderation_state","state","from","to","editor_state","delivery_state","pending_op","status","content_visibility","head_becomes"}
ALLOW_EXTRA = {"new"}
NONBIZ = {"user_id","account_id","actor_id","author_id","recipient_id","block_id","entity_id","device_id","attachment_id","command_id","event_id","object_id","reporter_id","target_id","target_ref","notifier_delivery_id","public_profile_id"}
BIZ = re.compile(r"^(note|nrev|pub|cacc|cbnd|anc|ares|thr|cmt|crev|rct|bmk|shr|bkm|ntf|bev|psn)_[0-9a-f]{32}$")
problems = []; total = 0
def walk(o, path, fname, skip_keys):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in skip_keys: continue
            if k in STATE_KEYS and isinstance(v, str) and v not in ENUM and v not in ALLOW_EXTRA: problems.append(f"{fname}:{path}.{k} unknown state {v}")
            if (k.endswith("_id") or k.endswith("_ids") or k in ("heads","heads_after")) and k not in NONBIZ:
                vals = v if isinstance(v, list) else [v]
                for x in vals:
                    if isinstance(x, str):
                        okid = BIZ.match(x) or (k == "artifact_revision_id" and re.match(r"^rev_[0-9a-f]{32}$", x)) or (k == "release_id" and re.match(r"^rel_[0-9a-f]{32}$", x))
                        if not okid: problems.append(f"{fname}:{path}.{k} bad id {x}")
            walk(v, f"{path}.{k}", fname, skip_keys)
    elif isinstance(o, list):
        for i, v in enumerate(o): walk(v, f"{path}[{i}]", fname, skip_keys)
for fname in sorted(files & WANT):
    d = json.loads(read(FX / fname))
    skip = {"value"} if fname == "id_format_cases.json" else ({"value","header","body"} if fname == "command_id_cases.json" else set())
    if fname == "content_hash_cases.json":
        for c in d["cases"]:
            total += 1
            if not re.fullmatch(r"[0-9a-f]{64}", c.get("expected_hash","")) or not re.fullmatch(r"([0-9a-f]{2})+", c.get("expected_canonical_hex","")): problems.append(f"{fname}:{c.get('name')} bad expected")
        for v in d["encoding_vectors"]:
            total += 1
            if "expected_bytes_hex" not in v: problems.append(f"{fname}:vector missing expected_bytes_hex")
        for v in d["invalid_snapshots"]:
            total += 1
            if "reason" not in v: problems.append(f"{fname}:invalid missing reason")
        for v in d.get("invalid_json_texts", []):
            total += 1
            if "reason" not in v or not isinstance(v.get("text"), str): problems.append(f"{fname}:invalid_json_text missing text/reason")
        byname = {c["name"]: c for c in d["cases"]}
        for c in d["cases"]:
            t = c.get("equal_hash_to")
            if t and (t not in byname or byname[t]["expected_hash"] != c["expected_hash"]): problems.append(f"{fname}:{c['name']} equal_hash_to")
    else:
        for i, c in enumerate(d["cases"]):
            total += 1
            if not isinstance(c, dict) or "expected" not in c: problems.append(f"{fname}#{i} missing expected")
    walk(d, "", fname, skip)
check(files == WANT and total == 198 and not problems, "K03 fixture：9 个文件、198 项、每项有 expected、状态值 ⊆ 枚举总表、业务 ID 格式合法、equal_hash_to 自洽", f"files={sorted(files ^ WANT)} total={total} problems={problems[:5]}")

# K04 参考编码器复算 fixture 期望
spec_ref = importlib.util.spec_from_file_location("nchash_reference", SPEC / "tools/nchash_reference.py"); R = importlib.util.module_from_spec(spec_ref); spec_ref.loader.exec_module(R)
d = json.loads(read(FX / "content_hash_cases.json")); bad04 = []
for c in d["cases"]:
    snap = c["snapshot"] if c["snapshot"] is not None else {k: c["revision"][k] for k in R.SNAPSHOT_FIELDS}
    if R.canonical_bytes(snap).hex() != c["expected_canonical_hex"] or R.content_hash(snap) != c["expected_hash"]: bad04.append(c["name"])
for v in d["encoding_vectors"]:
    if R.encode(v["value"]).hex() != v["expected_bytes_hex"]: bad04.append(v["name"])
for v in d["invalid_snapshots"]:
    try: R.content_hash(v["snapshot"]); bad04.append(v["name"])
    except ValueError: pass
for v in d["invalid_json_texts"]:
    try: R.content_hash_from_text(v["text"]); bad04.append(v["name"])
    except ValueError: pass
    try: json.loads(v["text"])
    except ValueError: bad04.append(v["name"] + ":裸 json.loads 也拒绝，用例失去意义")
check(not bad04 and R.encode({"x": None}) == b"o1:s1:xn;", "K04 参考编码器复算：18 case + 16 向量 + 7 非法对象 + 3 非法 JSON 文本与 fixture 一致", f"{bad04}")

# K05 六件套结构
bdd = read(PACK / "BDD.md"); tdd = read(PACK / "TDD.md"); acts = [read(PACK / "act" / f"0{i}.yaml") for i in range(1, 7)]
bids = re.findall(r"^\| (B\d\d) \|", bdd, re.M)
est = [int((re.search(r"^ESTIMATE_MINUTES: (\d+)", a, re.M) or [0, 0])[1]) for a in acts]
deps = [(re.search(r"^DEPENDS_ON: (.*)$", a, re.M) or [0, ""])[1].strip() for a in acts]
vague = re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况")
hits = [f"{f}:{m.group(0)}" for f in ["README.md","BDD.md","TDD.md","ACT.yaml","PROMPT.md","ACCEPTANCE.md","act/01.yaml","act/02.yaml","act/03.yaml","act/04.yaml","act/05.yaml","act/06.yaml"] for m in vague.finditer(read(PACK / f))]
ok05 = (bids == [f"B{i:02d}" for i in range(1, 24)] and all(30 <= e <= 60 for e in est) and deps == ["[]","[NC-002-A]","[NC-002-B]","[NC-002-C]","[NC-002-D]","[NC-002-E]"]
        and all("外部失败" in a and "WORKLOAD" in a and "ON_FAIL" in a for a in acts) and not hits and "198" in tdd and "196" not in tdd and "155" not in tdd
        and read(PACK / "ACT.yaml").count("- act/0") == 6 and read(PACK / "ACT.yaml").count("DEFERRED") == 1 and "NC-003" in read(PACK / "ACT.yaml")
        and not any("verify.sh 末尾追加" in a or "追加一行" in a for a in acts) and not (PACK / "act" / "07.yaml").exists())
check(ok05, "K05 六件套：BDD B01～B23、六个 ACT 30–60 分钟且依赖链/ON_FAIL/WORKLOAD 齐全、无模糊词、计数 198、两项推迟登记、不改 verify.sh", f"bids={len(bids)} est={est} deps={deps} vague={hits}")

# K06 前缀结论两处登记
todo = read(root / "docs/blackbox-spec-rework/SUBAGENT_TODO.md"); rr = read(SPEC / "READINESS_REVIEW.md")
check("前缀整表采用" in todo and "NC-002" in todo and "前缀整表采用" in rr, "K06 §2.1 前缀结论已写入 SUBAGENT_TODO 与 READINESS_REVIEW §3", "")

# K08 执行产物
schemas = sorted(p.name for p in (root / "openspec/schemas").glob("community_*.schema.json"))
vs = read(root / "openspec/schemas/verify.sh")
vs_head = subprocess.run(["git", "-C", str(root), "show", "437571b:openspec/schemas/verify.sh"], capture_output=True, text=True).stdout
check("verify_community" not in vs and vs == vs_head, "K07 openspec/schemas/verify.sh 未被本线改动（D-NC002-11）", "与 437571b 版本不同或含 verify_community")
if not schemas and not req:
    print("SKIP  K08 执行产物尚未存在（验收时加 --require-impl，必须 PASS）")
else:
    det = []
    ok08 = len(schemas) == 12
    det.append(f"schemas={len(schemas)}")
    r = subprocess.run(["bash", "openspec/schemas/verify_community.sh"], cwd=root, capture_output=True, text=True); ok08 &= r.returncode == 0 and "PASS community_all" in r.stdout; det.append(f"verify_community={r.returncode}")
    r = subprocess.run([sys.executable, str(SPEC / "tools/validate_fixtures.py"), str(FX)], capture_output=True, text=True); ok08 &= r.returncode == 0 and r.stdout.strip().endswith("FIXTURES_OK 9 files 198 cases"); det.append(f"validate={r.returncode}/{r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ''}")
    # 变异：临时副本
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "spec"; (base / "contracts").mkdir(parents=True); shutil.copytree(FX, base / "fixtures/community"); shutil.copy(SPEC / "contracts/state-machines.md", base / "contracts/")
        fxd = base / "fixtures/community"
        j = json.loads(read(fxd / "state_combinations.json")); j["cases"][0]["lifecycle"] = "Purged"; (fxd / "state_combinations.json").write_text(json.dumps(j)); r1 = subprocess.run([sys.executable, str(SPEC / "tools/validate_fixtures.py"), str(fxd)], capture_output=True, text=True)
        shutil.copy(FX / "state_combinations.json", fxd); j = json.loads(read(fxd / "comment_reply_cases.json")); j["cases"][0]["request"]["thread_id"] = "rev_" + "0" * 32; (fxd / "comment_reply_cases.json").write_text(json.dumps(j)); r2 = subprocess.run([sys.executable, str(SPEC / "tools/validate_fixtures.py"), str(fxd)], capture_output=True, text=True)
        shutil.copy(FX / "comment_reply_cases.json", fxd); j = json.loads(read(fxd / "limit_cases.json")); del j["cases"][0]["expected"]; (fxd / "limit_cases.json").write_text(json.dumps(j)); r3 = subprocess.run([sys.executable, str(SPEC / "tools/validate_fixtures.py"), str(fxd)], capture_output=True, text=True)
    ok08 &= r1.returncode == 1 and "unknown state value" in r1.stdout and r2.returncode == 1 and "bad id" in r2.stdout and r3.returncode == 1 and "missing expected" in r3.stdout; det.append(f"mut={r1.returncode},{r2.returncode},{r3.returncode}")
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(SPEC / "tools"), "-p", "test_validate_fixtures.py"], cwd=root, capture_output=True, text=True); ran = re.search(r"Ran (\d+)", r.stderr); ok08 &= r.returncode == 0 and ran is not None and int(ran.group(1)) == 7; det.append(f"validate_tests={r.returncode}/{ran.group(1) if ran else '无'}")
    # SERVER
    ch = SERVER / "xuan/community_hash.py"; tf = SERVER / "tests/test_community_hash_parity.py"; fcopy = SERVER / "tests/fixtures/community_content_hash_cases.json"
    ok08 &= ch.is_file() and tf.is_file() and fcopy.is_file() and fcopy.read_bytes() == (FX / "content_hash_cases.json").read_bytes(); det.append("server_files+cmp=" + str(ch.is_file() and tf.is_file() and fcopy.is_file() and fcopy.read_bytes() == (FX / 'content_hash_cases.json').read_bytes()))
    src = read(ch); tsrc = read(tf)
    ok08 &= "nchash_reference" not in src and "json.dumps" not in src and "nchash_reference" not in tsrc and "skip" not in tsrc and "firebase" not in tsrc; det.append("no_reference/json.dumps/skip=" + str("nchash_reference" not in src and "json.dumps" not in src and "skip" not in tsrc))
    r = subprocess.run([sys.executable, "-m", "unittest", "tests.test_community_hash_parity"], cwd=SERVER, capture_output=True, text=True); ran = re.search(r"Ran (\d+)", r.stderr); ok08 &= r.returncode == 0 and ran is not None and int(ran.group(1)) == 8; det.append(f"server_tests={r.returncode}/{ran.group(1) if ran else '无'}")
    # 交叉复算
    xbad = []
    if ch.is_file():
        sp = importlib.util.spec_from_file_location("community_hash", ch); S = importlib.util.module_from_spec(sp)
        try:
            sp.loader.exec_module(S)
            for c in d["cases"]:
                snap = c["snapshot"] if c["snapshot"] is not None else S.project_revision(c["revision"])
                if S.canonical_bytes(snap) != R.canonical_bytes(snap) or S.content_hash(snap) != R.content_hash(snap): xbad.append(c["name"])
            for v in d["encoding_vectors"]:
                if S.encode(v["value"]) != R.encode(v["value"]): xbad.append(v["name"])
            for v in d["invalid_json_texts"]:
                try: S.load_snapshot_json(v["text"]); xbad.append(v["name"])
                except ValueError: pass
        except Exception as e: xbad.append(repr(e))
    ok08 &= not xbad; det.append(f"cross={xbad[:3]}")
    check(ok08, "K08 执行产物：12 Schema、verify_community 0、校验器 0/198 且三变异非零、7+8 测试、SERVER 副本一致、交叉复算（含解析层拒绝）一致、无参考引用", "; ".join(det))

print(f"\nNC-002 失败条数：{fails}")
sys.exit(fails)
PY
