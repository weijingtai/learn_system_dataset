#!/usr/bin/env bash
# NC-006 守卫：回归既有守卫；核对契约与六件套；--require-impl 时核对 reading-notes 中 NC-006 产物（含 flutter test）。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"; REQ="${1:-}"
LC_ALL=C bash "$ROOT/openspec/annotation-community/review_v1_5_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
"$ROOT/.venv/bin/python" - "$ROOT" "$g1" "$g2" "$REQ" <<'PY'
import re, subprocess, sys, os
from pathlib import Path
root=Path(sys.argv[1]); g1,g2=int(sys.argv[2]),int(sys.argv[3]); req=sys.argv[4]=="--require-impl"
SPEC=root/"openspec/annotation-community"; PACK=root/"docs/blackbox-spec-rework/work-items/nc-006"
CLIENT=Path("/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes"); FL="/Users/jingtaiwei/flutter/bin"
fails=0
def check(ok,name,detail=""):
    global fails
    if not ok: fails+=1
    print(("PASS  " if ok else "FAIL  ")+name+("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""
check(g1==0 and g2==0,"K01 回归：v1.5 守卫与 annotation verify.sh 均为 0",f"{g1},{g2}")
c=read(SPEC/"contracts/editor_history.md"); ed=read(SPEC/"contracts/editor.md")
need=["Action.overridable","UndoTextIntent","RedoTextIntent","undoMergeMaxGapMs","undoMergeMaxChars","Ctrl+Y","recordTextChange","recordCommand","imeCommit","undoCount","pastUnits","_applying","handlePlatformUndo","## 5.4","RegExp(r'\\s')"]
ok02=all(n in c for n in need) and all(f"D-NC006-{i:02d}" in c for i in range(1,13)) and "editor_history.md" in ed and "3.44.6" in c
check(ok02,"K02 契约：平台事实、接口名、归组常量、Ctrl+Y、D-NC006-01～12、editor.md 指针",[n for n in need if n not in c])
bdd=read(PACK/"BDD.md"); tdd=read(PACK/"TDD.md"); acts=[read(PACK/"act"/f"0{i}.yaml") for i in range(1,4)]
bids=re.findall(r"^\| (B\d\d) \|",bdd,re.M); est=[int((re.search(r"^ESTIMATE_MINUTES: (\d+)",a,re.M) or [0,0])[1]) for a in acts]
deps=[(re.search(r"^DEPENDS_ON: (.*)$",a,re.M) or [0,""])[1].strip() for a in acts]
vague=re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况"); files=["README.md","BDD.md","TDD.md","ACT.yaml","PROMPT.md","ACCEPTANCE.md","act/01.yaml","act/02.yaml","act/03.yaml"]
hits=[f"{f}:{m.group(0)}" for f in files for m in vague.finditer(read(PACK/f))]
ok03=(bids==[f"B{i:02d}" for i in range(1,37)] and all(30<=e<=60 for e in est) and deps==["[]","[NC-006-A]","[NC-006-B]"] and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits and "+110" in tdd and "+17" in tdd and "+25" in tdd and "+10" in tdd and "DISPATCH_PRECONDITION" in read(PACK/"ACT.yaml") and "D-NC006-01" in read(PACK/"README.md") and "NC-005 已 ACCEPTED" in read(PACK/"PROMPT.md") and "UndoHistoryController" in read(PACK/"PROMPT.md"))
check(ok03,"K03 六件套：BDD B01～B36、三个 ACT 30–60 分钟且依赖链/ON_FAIL/WORKLOAD、无模糊词、计数 17/25/10/110、派发前置",f"bids={len(bids)} est={est} deps={deps} vague={hits}")
todo=read(root/"docs/blackbox-spec-rework/SUBAGENT_TODO.md"); check("NC-006" in todo and "editor_history.md" in todo,"K04 SUBAGENT_TODO 已登记 NC-006 工作包","")
ad=CLIENT/"lib/src/editor/editor_history_adapter.dart"
if not ad.exists() and not req:
    print("SKIP  K05 NC-006 产物尚不存在（验收时加 --require-impl，必须 PASS）")
else:
    det=[]; ok=ad.is_file() and (CLIENT/"test/editor/editor_history_test.dart").is_file() and (CLIENT/"test/editor/editor_shortcuts_test.dart").is_file(); det.append(f"files={ok}")
    a=read(ad); badc=re.findall(r"\b500\b|\b20\b|DateTime\.now\(|Timer\(|Stopwatch\(",a); okc=not badc and "undoMergeMaxGapMs" in a and "undoMergeMaxChars" in a; ok&=okc; det.append(f"adapter_literals={badc}")
    lib={p.name:read(p) for p in (CLIENT/"lib/src/editor").glob("*.dart")}
    sc={n:t.count("Shortcuts(")-t.count("CallbackShortcuts(") for n,t in lib.items()}; oks=sc.get("note_editor_page.dart",0)==1 and sum(sc.values())==1 and not any("UndoHistoryController" in t for t in lib.values()); ok&=oks; det.append(f"shortcuts={sc}")
    src="".join(read(p) for p in (CLIENT/"test/editor").glob("*.dart")); cheats=[p for p in ("skip:","skip(","expect(true, isTrue)") if p in src]; ok&=not cheats; det.append(f"cheats={cheats}")
    for f in ["lib/src/domain","lib/src/persistence","test/persistence","test/contracts","pubspec.yaml","pubspec.lock","lib/src/editor/save_status.dart","lib/src/editor/markdown_preview.dart","test/editor/save_status_test.dart","test/editor/markdown_preview_test.dart","test/editor/note_editor_test.dart"]:
        r=subprocess.run(["git","-C",str(CLIENT),"log","--format=%s","--",f],capture_output=True,text=True).stdout
        if "NC-006" in r: ok=False; det.append(f"NC-006 触碰了 {f}")
    pt=read(CLIENT/"test/editor/note_editor_page_test.dart"); okp="shortcuts and actions wrap only the body field" in pt and "no shortcuts registered by page" not in pt and pt.count("testWidgets(")==6; ok&=okp; det.append(f"page_test={okp}")
    env=dict(os.environ); env["PATH"]=FL+":"+env["PATH"]
    an=subprocess.run(["flutter","analyze"],cwd=CLIENT,capture_output=True,text=True,env=env); ok&=an.returncode==0; det.append(f"analyze={an.returncode}")
    ft=subprocess.run(["flutter","test"],cwd=CLIENT,capture_output=True,text=True,env=env); m=re.search(r"\+(\d+): All tests passed!",ft.stdout); ok&=ft.returncode==0 and m is not None and int(m.group(1))>=110; det.append(f"test={ft.returncode}/{m.group(1) if m else '无'}")
    check(ok,"K05 NC-006 产物：三文件、adapter 无字面量/裸时间、Shortcuts 恰 1 且无 UndoHistoryController、无作弊、未触碰 NC-004/NC-005 保护文件、页面测试唯一改动、analyze 0、flutter test ≥110","; ".join(det))
print(f"\nNC-006 失败条数：{fails}"); sys.exit(fails)
PY
