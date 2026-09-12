#!/usr/bin/env bash
# NC-009 守卫：回归 v1.6 守卫；核对契约与六件套；--require-impl 时核对 SERVER 产物（Emulator pytest）。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"; REQ="${1:-}"
bash "$ROOT/openspec/annotation-community/review_v1_6_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
"$ROOT/.venv/bin/python" - "$ROOT" "$g1" "$g2" "$REQ" <<'PY'
import re, subprocess, sys, os
from pathlib import Path
root=Path(sys.argv[1]); g1,g2=int(sys.argv[2]),int(sys.argv[3]); req=sys.argv[4]=="--require-impl"
SPEC=root/"openspec/annotation-community"; PACK=root/"docs/blackbox-spec-rework/work-items/nc-009"
SV=Path("/Users/jingtaiwei/Git/Public/xuan-server/functions-py"); RU=Path("/Users/jingtaiwei/Git/Public/xuan-migration/xuan-server/server")
fails=0
def check(ok,name,detail=""):
    global fails
    if not ok: fails+=1
    print(("PASS  " if ok else "FAIL  ")+name+("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""
check(g1==0 and g2==0,"K01 回归：v1.6 守卫与 verify.sh 均为 0",f"{g1},{g2}")
c=read(SPEC/"contracts/community_server.md")
need=["run_command","community_commands","owner_scope__","result_compact_after","compact_once","conflict.object_missing","xfail(strict=True","community_rules.test.ts","transactional","身份 → 存在性 → 归属 → 版本 → 生命周期 → 载荷","192.168.0.165:8080","30a868c","community_pseudonym_mappings","secrets.token_hex","new_ids","internal.state_corrupted","R2-05","server_event_id","8 × 2 × 4 = 64","resolve_access(content_id, owner_scope)","jsonschema==4.26.0","invalid_argument.snapshot","D-NC009-17"]
ok02=all(n in c for n in need) and all(f"D-NC009-{i:02d}" in c for i in range(1,20)) and all(f"## {i}." in c for i in range(1,11)) and "SHA-256(owner_scope)[:32] 冒名" not in c
check(ok02,"K02 契约：账本流程、集合、判定顺序、ACL xfail、规则测试、D-NC009-01～19、十节、假名非推导",[n for n in need if n not in c])
bdd=read(PACK/"BDD.md"); tdd=read(PACK/"TDD.md"); acts=[read(PACK/"act"/f"0{i}.yaml") for i in range(1,7)]
bids=re.findall(r"^\| (B\d\d) \|",bdd,re.M); est=[int((re.search(r"^ESTIMATE_MINUTES: (\d+)",a,re.M) or [0,0])[1]) for a in acts]
deps=[(re.search(r"^DEPENDS_ON: (.*)$",a,re.M) or [0,""])[1].strip() for a in acts]
vague=re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况"); files=["README.md","BDD.md","TDD.md","ACT.yaml","PROMPT.md","ACCEPTANCE.md","act/01.yaml","act/02.yaml","act/03.yaml","act/04.yaml","act/05.yaml","act/06.yaml"]
hits=[f"{f}:{m.group(0)}" for f in files for m in vague.finditer(read(PACK/f))]
ok03=(bids==[f"B{i:02d}" for i in range(1,40)] and all(30<=e<=60 for e in est) and deps==["[]","[NC-009-A]","[NC-009-B]","[NC-009-C]","[NC-009-D]","[NC-009-E]"] and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits and "9 passed, 9 xfailed" in tdd and "DISPATCH_PRECONDITION" in read(PACK/"ACT.yaml") and "过期副本" in read(PACK/"PROMPT.md"))
check(ok03,"K03 六件套：BDD B01～B39、六个 ACT 30–60 分钟、依赖链/ON_FAIL/WORKLOAD、无模糊词、xfail 计数、派发前置",f"bids={len(bids)} est={est} deps={deps} vague={hits}")
todo=read(root/"docs/blackbox-spec-rework/SUBAGENT_TODO.md"); check("NC-009" in todo and "community_server.md" in todo,"K04 SUBAGENT_TODO 已登记 NC-009 工作包与契约","")
cs=SV/"xuan/community/command_service.py"
if not cs.exists() and not req:
    print("SKIP  K05 NC-009 产物尚不存在（验收时加 --require-impl，必须 PASS）")
else:
    det=[]; ok=True
    for f in ["xuan/community/command_service.py","xuan/community/content_service.py","xuan/community/access.py","xuan/handlers/community_contents.py","xuan/handlers/community_commands.py","tests/test_community_commands.py","tests/test_community_publications.py","tests/test_community_acl_sweep.py"]:
        if not (SV/f).is_file(): ok=False; det.append(f"missing {f}")
    ok&=(RU/"functions/test/community_rules.test.ts").is_file(); det.append(f"rules_test={(RU/'functions/test/community_rules.test.ts').is_file()}")
    comm="".join(read(p) for p in (SV/"xuan/community").glob("*.py")) if (SV/"xuan/community").exists() else ""; ok&=("with_idempotency" not in comm and "transactional" in comm); det.append(f"no_with_idempotency={'with_idempotency' not in comm}")
    tests="".join(read(SV/"tests"/f) for f in ["test_community_commands.py","test_community_publications.py","test_community_acl_sweep.py"])
    cheats=[p for p in ("skip(","skip=","status in (","MagicMock(spec=firestore") if p in tests]; ok&=not cheats; det.append(f"cheats={cheats}"); ok&=tests.count("strict=True")>=9; det.append(f"xfail_strict={tests.count('strict=True')}")
    for f in ["xuan/idempotency.py","xuan/handlers/playground_rest.py","xuan/handlers/notifications.py"]:
        r=subprocess.run(["git","-C",str(SV),"log","--format=%s","30a868c..HEAD","--",f],capture_output=True,text=True).stdout
        if r.strip(): ok=False; det.append(f"touched {f}")
    act05=(SV/"xuan/community/validation.py").is_file(); det.append(f"act05_landed={act05}")
    if req and not act05: ok=False; det.append("act/05 未落地：缺 validation.py（契约 §10）")
    act06="test_snapshot_missing_required_keys_is_400" in read(SV/"tests/test_community_validation.py"); det.append(f"act06_landed={act06}")
    need_pass=48 if act06 else (46 if act05 else 39)
    if act06:
        cst=read(SV/"xuan/community/content_service.py"); nofill=not re.search(r'dict\(body\.get\("snapshot"\)|snapshot\["(attachments|mentions|bindings)"\] = \[\]',cst); ok&=nofill; det.append(f"no_default_fill={nofill}")
        logsrc="".join(read(f) for f in list((SV/"xuan/community").glob("*.py"))+list((SV/"xuan/handlers").glob("community_*.py"))); leak=re.findall(r"\{exc\}|str\(exc\)|repr\(exc\)|exc_info",logsrc); ok&=not leak; det.append(f"log_exc_hits={len(leak)}")
    if act05:
        ok&=bool(re.search(r"^jsonschema==4\.26\.0$",read(SV/"requirements.txt"),re.M)); det.append("req_jsonschema="+str(bool(re.search(r"^jsonschema==4\.26\.0$",read(SV/"requirements.txt"),re.M))))
        diffs=[p.name for p in (SV/"xuan/community/schemas").glob("*.json") if read(p)!=read(root/"openspec/schemas"/p.name)]; n_s=len(list((SV/"xuan/community/schemas").glob("*.json")))
        ok&=(n_s==12 and not diffs); det.append(f"vendored={n_s} diffs={diffs}")
        cs=read(SV/"xuan/community/command_service.py"); ok&=("str(exc)" not in cs); det.append(f"no_str_exc={'str(exc)' not in cs}")
    py=SV/".venv/bin/python"
    if not py.exists(): ok=False; det.append("no .venv")
    else:
        env=dict(os.environ); env["XUAN_EMULATOR_HOST"]="192.168.0.165:8080"; env["FIREBASE_AUTH_EMULATOR_HOST"]="192.168.0.165:9099"
        pt=subprocess.run([str(py),"-m","pytest","tests/test_community_commands.py","tests/test_community_publications.py","tests/test_community_acl_sweep.py"]+(["tests/test_community_validation.py"] if act05 else [])+["-q"],cwd=SV,capture_output=True,text=True,env=env,timeout=1800)
        last=pt.stdout.strip().splitlines()[-1] if pt.stdout.strip() else ""; ok&=pt.returncode==0 and f"{need_pass} passed" in last and "9 xfailed" in last and "skipped" not in last; det.append(f"pytest={pt.returncode}/{last[:80]}")
    check(ok,"K05 NC-009 产物：文件齐全、无 with_idempotency/有 transactional、无作弊、xfail strict ≥9、未触碰保护文件、39 passed + 9 xfailed","; ".join(det))
print(f"\nNC-009 失败条数：{fails}"); sys.exit(fails)
PY
