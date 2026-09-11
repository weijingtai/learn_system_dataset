#!/usr/bin/env bash
# NC-007 守卫：回归既有守卫；核对契约与六件套；--require-impl 时核对 reading-notes 中 NC-007 产物（含 flutter test）。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"; REQ="${1:-}"
LC_ALL=C bash "$ROOT/openspec/annotation-community/review_v1_5_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
"$ROOT/.venv/bin/python" - "$ROOT" "$g1" "$g2" "$REQ" <<'PY'
import re, subprocess, sys, os
from pathlib import Path
root=Path(sys.argv[1]); g1,g2=int(sys.argv[2]),int(sys.argv[3]); req=sys.argv[4]=="--require-impl"
SPEC=root/"openspec/annotation-community"; PACK=root/"docs/blackbox-spec-rework/work-items/nc-007"
CLIENT=Path("/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes"); FL="/Users/jingtaiwei/flutter/bin"
fails=0
def check(ok,name,detail=""):
    global fails
    if not ok: fails+=1
    print(("PASS  " if ok else "FAIL  ")+name+("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""
check(g1==0 and g2==0,"K01 回归：v1.5 守卫与 annotation verify.sh 均为 0",f"{g1},{g2}")

c=read(SPEC/"contracts/revision_history.md")
need=["DiffBlockType","DiffBlock","collapseThreshold","1 MiB","restoreRevision","restoredFrom","保留本机","采用对方","手动合并","稍后处理"]
ok02=all(n in c for n in need) and all(f"D-NC007-0{i}" in c for i in range(1,6))
check(ok02,"K02 契约：差异模型、折叠阈值、四选项文案闭集、D-NC007-01～05 齐全",[n for n in need if n not in c])

bdd=read(PACK/"BDD.md"); tdd=read(PACK/"TDD.md"); acts=[read(PACK/"act"/f"0{i}.yaml") for i in range(1,5)]
bids=re.findall(r"^\| (B\d\d) \|",bdd,re.M); est=[int((re.search(r"^ESTIMATE_MINUTES: (\d+)",a,re.M) or [0,0])[1]) for a in acts]
deps=[(re.search(r"^DEPENDS_ON: (.*)$",a,re.M) or [0,""])[1].strip() for a in acts]
vague=re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况"); files=["README.md","BDD.md","TDD.md","ACT.yaml","PROMPT.md","ACCEPTANCE.md","act/01.yaml","act/02.yaml","act/03.yaml","act/04.yaml"]
hits=[f"{f}:{m.group(0)}" for f in files for m in vague.finditer(read(PACK/f))]
ok03=(bids==[f"B{i:02d}" for i in range(1,33)] and all(30<=e<=60 for e in est) and deps==["[]","[NC-007-A]","[NC-007-B]","[NC-007-C]"] and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits and "+145" in tdd and "DISPATCH_PRECONDITION" in read(PACK/"ACT.yaml") and "NC-006 已 ACCEPTED" in read(PACK/"PROMPT.md"))
check(ok03,"K03 六件套：BDD B01～B32、四个 ACT 30–60 分钟且依赖链/ON_FAIL/WORKLOAD、无模糊词、计数 145、派发前置",f"bids={len(bids)} est={est} deps={deps} vague={hits}")

todo=read(root/"docs/blackbox-spec-rework/SUBAGENT_TODO.md"); check("NC-007" in todo and "revision_history.md" in todo,"K04 SUBAGENT_TODO 已登记 NC-007 工作包与契约","")

ad=CLIENT/"lib/src/history/revision_compare.dart"
if not ad.exists() and not req:
    print("SKIP  K05 NC-007 产物尚不存在（验收时加 --require-impl，必须 PASS）")
else:
    det=[]; ok=True
    for f in ["revision_compare.dart","revision_history_page.dart","revision_conflict_controller.dart","conflict_banner.dart"]:
        ok&=(CLIENT/"lib/src/history"/f).is_file()
    det.append("files="+str(ok))
    for f in ["revision_compare_test.dart","revision_history_test.dart","revision_conflict_test.dart"]:
        ok&=(CLIENT/"test/history"/f).is_file()
    det.append("tests="+str(ok))
    src="".join(read(p) for p in (CLIENT/"test/history").glob("*.dart")) if (CLIENT/"test/history").exists() else ""
    cheats=[p for p in ("skip:","skip(","expect(true, isTrue)") if p in src]
    ok&=not cheats; det.append(f"cheats={cheats}")
    http=[p for p in (CLIENT/"lib/src/history").glob("*.dart") if "http:" in read(p) or "https:" in read(p) or "HttpClient" in read(p)]
    ok&=not http; det.append(f"http={bool(http)}")
    for f in ["lib/src/domain","lib/src/persistence","lib/src/editor","test/persistence","test/contracts","test/editor","pubspec.yaml","pubspec.lock"]:
        r=subprocess.run(["git","-C",str(CLIENT),"log","--format=%s","--",f],capture_output=True,text=True).stdout
        if "NC-007" in r: ok=False; det.append(f"NC-007 触碰了保护路径 {f}")
    env=dict(os.environ); env["PATH"]=FL+":"+env["PATH"]
    an=subprocess.run(["flutter","analyze"],cwd=CLIENT,capture_output=True,text=True,env=env); ok&=an.returncode==0; det.append(f"analyze={an.returncode}")
    ft=subprocess.run(["flutter","test"],cwd=CLIENT,capture_output=True,text=True,env=env); m=re.search(r"\+(\d+): All tests passed!",ft.stdout); ok&=ft.returncode==0 and m is not None and int(m.group(1))>=145; det.append(f"test={ft.returncode}/{m.group(1) if m else '无'}")
    check(ok,"K05 NC-007 产物：四文件+三测试、无作弊、无外部网络、未触碰保护文件、analyze 0、flutter test ≥145","; ".join(det))
print(f"\nNC-007 失败条数：{fails}"); sys.exit(fails)
PY
