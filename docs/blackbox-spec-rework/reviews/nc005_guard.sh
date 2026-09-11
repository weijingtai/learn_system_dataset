#!/usr/bin/env bash
# NC-005 守卫：回归既有守卫；核对契约与六件套；--require-impl 时核对 reading-notes 中 NC-005 产物（含 flutter test）。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"; REQ="${1:-}"
LC_ALL=C bash "$ROOT/openspec/annotation-community/review_v1_5_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
"$ROOT/.venv/bin/python" - "$ROOT" "$g1" "$g2" "$REQ" <<'PY'
import re, subprocess, sys, os
from pathlib import Path
root=Path(sys.argv[1]); g1,g2=int(sys.argv[2]),int(sys.argv[3]); req=sys.argv[4]=="--require-impl"
SPEC=root/"openspec/annotation-community"; PACK=root/"docs/blackbox-spec-rework/work-items/nc-005"
CLIENT=Path("/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes"); FL="/Users/jingtaiwei/flutter/bin"
fails=0
def check(ok,name,detail=""):
    global fails
    if not ok: fails+=1
    print(("PASS  " if ok else "FAIL  ")+name+("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""
check(g1==0 and g2==0,"K01 回归：v1.5 守卫与 annotation verify.sh 均为 0",f"{g1},{g2}")
c=read(SPEC/"contracts/editor.md"); prd=read(SPEC/"PRD.md")
labels=["未保存","保存中","已保存本机","保存失败","未开启","无其他设备","同步失败","对方版本待处理","排队中","备份失败","已关闭（存量保留）"]
ok02=all(l in c for l in labels) and all(f"D-NC005-0{i}" in c for i in range(1,6)) and "kDefaultImageBuilder" in c and "imageBuilder" in c and "1.0.12" in c
ok02=ok02 and all(l in prd for l in labels[:8]) and "400 ms" in c and "IllegalEditorTransition" in c and "## 5.1" in c
check(ok02,"K02 契约：三态文案闭集与 PRD §6.1 一致、D-NC005-01～05、§5.1 已填、400 ms、非法转移","")
bdd=read(PACK/"BDD.md"); tdd=read(PACK/"TDD.md"); acts=[read(PACK/"act"/f"0{i}.yaml") for i in range(1,5)]
bids=re.findall(r"^\| (B\d\d) \|",bdd,re.M); est=[int((re.search(r"^ESTIMATE_MINUTES: (\d+)",a,re.M) or [0,0])[1]) for a in acts]
deps=[(re.search(r"^DEPENDS_ON: (.*)$",a,re.M) or [0,""])[1].strip() for a in acts]
vague=re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况"); hits=[f"{f}:{m.group(0)}" for f in ["README.md","BDD.md","TDD.md","ACT.yaml","PROMPT.md","ACCEPTANCE.md","act/01.yaml","act/02.yaml","act/03.yaml","act/04.yaml"] for m in vague.finditer(read(PACK/f))]
ok03=(bids==[f"B{i:02d}" for i in range(1,32)] and all(30<=e<=60 for e in est) and deps==["[]","[NC-005-A]","[NC-005-B]","[NC-005-C]"] and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits and "+75" in tdd and "+74" not in tdd and "Timer(" in tdd and "TextScaler" in tdd and "DISPATCH_PRECONDITION" in read(PACK/"ACT.yaml") and "方案 b" in read(PACK/"README.md") and "NC-004 已 ACCEPTED" in read(PACK/"PROMPT.md"))
check(ok03,"K03 六件套：BDD B01～B31、四个 ACT 30–60 分钟且依赖链/ON_FAIL/WORKLOAD、无模糊词、计数 75、派发前置与撤销裁定",f"bids={len(bids)} est={est} deps={deps} vague={hits}")
todo=read(root/"docs/blackbox-spec-rework/SUBAGENT_TODO.md"); check("NC-005" in todo and "editor.md" in todo,"K04 SUBAGENT_TODO 已登记 NC-005 工作包","")
ed=CLIENT/"lib/src/editor"
if not ed.exists() and not req:
    print("SKIP  K05 NC-005 产物尚不存在（验收时加 --require-impl，必须 PASS）")
else:
    det=[]; ok=True
    for f in ["note_editor_controller.dart","save_status.dart","markdown_preview.dart","note_editor_page.dart"]: ok&=(ed/f).is_file()
    det.append("files="+str(all((ed/f).is_file() for f in ["note_editor_controller.dart","save_status.dart","markdown_preview.dart","note_editor_page.dart"])))
    lock=read(CLIENT/"pubspec.lock"); okl=bool(re.search(r"^  flutter_markdown_plus:\n(?:    .*\n)*?    version: \"1\.0\.12\"",lock,re.M)) and bool(re.search(r"^  drift:\n(?:    .*\n)*?    version: \"2\.31\.0\"",lock,re.M)); ok&=okl; det.append(f"lock={okl}")
    src="".join(read(p) for p in (CLIENT/"test/editor").rglob("*.dart")) if (CLIENT/"test/editor").exists() else ""; lib="".join(read(p) for p in ed.rglob("*.dart"))
    # D-NC006-12：NC-006 落地（adapter 文件存在）后，Shortcuts 禁令由 nc006_guard 接管，本处不再扫描
    scan=("Image.network","NetworkImage","Timer(","textScaleFactor") if (ed/"editor_history_adapter.dart").is_file() else ("Image.network","NetworkImage","Shortcuts(","CallbackShortcuts(","Timer(","textScaleFactor")
    cheats=[p for p in ("skip:","skip(","expect(true, isTrue)") if p in src]; bad=[p for p in scan if (re.search(r"(?<![A-Za-z0-9_])Timer\(",lib) if p=="Timer(" else p in lib)]  # Timer( 只匹配裸构造，不匹配 _fooTimer(
    ok&=not cheats and not bad; det.append(f"cheats={cheats} bad={bad}")
    for f in ["lib/src/domain","lib/src/persistence","test/persistence","test/contracts"]:
        r=subprocess.run(["git","-C",str(CLIENT),"log","--format=%s","--",f],capture_output=True,text=True).stdout
        if "NC-005" in r: ok=False; det.append(f"NC-005 触碰了 {f}")
    env=dict(os.environ); env["PATH"]=FL+":"+env["PATH"]
    an=subprocess.run(["flutter","analyze"],cwd=CLIENT,capture_output=True,text=True,env=env); ok&=an.returncode==0; det.append(f"analyze={an.returncode}")
    ft=subprocess.run(["flutter","test"],cwd=CLIENT,capture_output=True,text=True,env=env); m=re.search(r"\+(\d+): All tests passed!",ft.stdout); ok&=ft.returncode==0 and m is not None and int(m.group(1))>=75; det.append(f"test={ft.returncode}/{m.group(1) if m else '无'}")
    check(ok,"K05 NC-005 产物：四文件、lock 1.0.12 且 NC-004 版本不变、无作弊/无 Image.network/无 Shortcuts、未触碰 NC-004 文件、analyze 0、flutter test ≥75","; ".join(det))
print(f"\nNC-005 失败条数：{fails}"); sys.exit(fails)
PY
