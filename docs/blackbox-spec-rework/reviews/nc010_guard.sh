#!/usr/bin/env bash
# NC-010 守卫：回归 v1.6 守卫；核对契约与六件套；--require-impl 时核对 reading-notes 中 NC-010 产物（flutter test）。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"; REQ="${1:-}"
bash "$ROOT/openspec/annotation-community/review_v1_6_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
"$ROOT/.venv/bin/python" - "$ROOT" "$g1" "$g2" "$REQ" <<'PY'
import re, subprocess, sys, os
from pathlib import Path
root=Path(sys.argv[1]); g1,g2=int(sys.argv[2]),int(sys.argv[3]); req=sys.argv[4]=="--require-impl"
SPEC=root/"openspec/annotation-community"; PACK=root/"docs/blackbox-spec-rework/work-items/nc-010"
RN=Path("/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes"); FL="/Users/jingtaiwei/flutter/bin"
HASH="c8e2c2b0a842ece53f90cbf84e64fbacf274745a42bf4fb389b670fb0b3b72b5"
fails=0
def check(ok,name,detail=""):
    global fails
    if not ok: fails+=1
    print(("PASS  " if ok else "FAIL  ")+name+("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""
check(g1==0 and g2==0,"K01 回归：v1.6 守卫与 verify.sh 均为 0",f"{g1},{g2}")
c=read(SPEC/"contracts/community_client.md")
need=["CommunityDatabase","IdTokenProvider","http: 1.6.0","PendingOpConflict","CommandAlreadySent","unavailable.command_status","gone.command_result","正在停止公开，他人可能仍可访问","已公开 · 有未发布的修改","所有操作都已完成同步","含图片的笔记暂不能发布，请移除图片后再发布",HASH,"paused","AppealHandler","PendingOpWriter","14 天"]
ok02=all(n in c for n in need) and all(f"D-NC010-{i:02d}" in c for i in range(1,10)) and all(f"## {i}." in c for i in range(1,10))
check(ok02,"K02 契约：库/端口/队列状态/作者文案/确认层/参考哈希、D-NC010-01～09、九节",[n for n in need if n not in c])
bdd=read(PACK/"BDD.md"); tdd=read(PACK/"TDD.md"); acts=[read(PACK/"act"/f"0{i}.yaml") for i in range(1,6)]
bids=re.findall(r"^\| (B\d\d) \|",bdd,re.M); est=[int((re.search(r"^ESTIMATE_MINUTES: (\d+)",a,re.M) or [0,0])[1]) for a in acts]
deps=[(re.search(r"^DEPENDS_ON: (.*)$",a,re.M) or [0,""])[1].strip() for a in acts]
vague=re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况"); files=["README.md","BDD.md","TDD.md","ACT.yaml","PROMPT.md","ACCEPTANCE.md"]+[f"act/0{i}.yaml" for i in range(1,6)]
hits=[f"{f}:{m.group(0)}" for f in files for m in vague.finditer(read(PACK/f))]
ok03=(bids==[f"B{i:02d}" for i in range(1,38)] and all(30<=e<=60 for e in est) and deps==["[]","[NC-010-A]","[NC-010-B]","[NC-010-C]","[NC-010-D]"] and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits and all(x in tdd for x in ["+156","+170","+179","+186","+211"]) and HASH in bdd and "DISPATCH_PRECONDITION" in read(PACK/"ACT.yaml"))
check(ok03,"K03 六件套：BDD B01～B37、五个 ACT 30–60 分钟、依赖链/ON_FAIL/WORKLOAD、无模糊词、计数 156→211、参考哈希",f"bids={len(bids)} est={est} deps={deps} vague={hits}")
todo=read(root/"docs/blackbox-spec-rework/SUBAGENT_TODO.md"); check("NC-010" in todo and "community_client.md" in todo,"K04 SUBAGENT_TODO 已登记 NC-010 工作包与契约","")
cq=RN/"lib/src/community/command_queue.dart"
if not cq.exists() and not req:
    print("SKIP  K05 NC-010 产物尚不存在（验收时加 --require-impl，必须 PASS）")
else:
    det=[]; ok=True
    for f in ["lib/src/community/community_api.dart","lib/src/community/command_queue.dart","lib/src/community/community_database.dart","lib/src/community/publication_controller.dart","lib/src/community/pending_queue_page.dart","test/community/community_api_test.dart","test/community/command_queue_test.dart","test/community/publication_flow_test.dart","test/community/seven_states_test.dart"]:
        if not (RN/f).is_file(): ok=False; det.append(f"missing {f}")
    pub=read(RN/"pubspec.yaml"); ok&=bool(re.search(r"^  http: 1\.6\.0$",pub,re.M)); det.append(f"http_pinned={bool(re.search(r'^  http: 1\\.6\\.0$',pub,re.M))}")
    libc="".join(read(p) for p in (RN/"lib/src/community").glob("*.dart")) if (RN/"lib/src/community").exists() else ""
    ok&=("firebase_auth" not in libc and "cloud_firestore" not in libc); det.append(f"no_firebase={'firebase_auth' not in libc and 'cloud_firestore' not in libc}")
    tests="".join(read(p) for p in (RN/"test/community").glob("*.dart")) if (RN/"test/community").exists() else ""
    cheats=[p for p in ("skip:","skip(","expect(true, isTrue)") if p in tests]; ok&=not cheats; det.append(f"cheats={cheats}"); ok&=HASH in tests; det.append(f"hash_literal={HASH in tests}")
    d=subprocess.run(["git","-C",str(RN),"diff","9b35e97","HEAD","--stat","--","lib/src/domain","lib/src/persistence","lib/src/editor","lib/src/history","test/persistence","test/contracts","test/editor","test/history","test/support"],capture_output=True,text=True).stdout.strip()
    ok&=(d==""); det.append(f"protected_diff_empty={d==''}")
    env=dict(os.environ); env["PATH"]=FL+":"+env["PATH"]
    an=subprocess.run(["flutter","analyze"],cwd=RN,capture_output=True,text=True,env=env); ok&=an.returncode==0; det.append(f"analyze={an.returncode}")
    ft=subprocess.run(["flutter","test"],cwd=RN,capture_output=True,text=True,env=env); m=re.search(r"\+(\d+): All tests passed!",ft.stdout); ok&=ft.returncode==0 and m is not None and int(m.group(1))>=211; det.append(f"test={ft.returncode}/{m.group(1) if m else '无'}")
    check(ok,"K05 NC-010 产物：文件齐全、http 精确锁定、无 Firebase、无作弊、参考哈希字面量、未触碰 NC-004～007、analyze 0、flutter test ≥211","; ".join(det))
print(f"\nNC-010 失败条数：{fails}"); sys.exit(fails)
PY
