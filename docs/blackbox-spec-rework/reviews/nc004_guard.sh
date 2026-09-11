#!/usr/bin/env bash
# NC-004 守卫：回归既有守卫；核对契约与六件套结构；--require-impl 时核对 reading-notes 仓库产物（含 flutter test）。
# 用法：bash docs/blackbox-spec-rework/reviews/nc004_guard.sh [--require-impl]
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"; REQ="${1:-}"
LC_ALL=C bash "$ROOT/openspec/annotation-community/review_v1_5_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
"$ROOT/.venv/bin/python" - "$ROOT" "$g1" "$g2" "$REQ" <<'PY'
import re, subprocess, sys, json
from pathlib import Path
root=Path(sys.argv[1]); g1,g2=int(sys.argv[2]),int(sys.argv[3]); req=sys.argv[4]=="--require-impl"
SPEC=root/"openspec/annotation-community"; PACK=root/"docs/blackbox-spec-rework/work-items/nc-004"
CLIENT=Path("/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes"); FL="/Users/jingtaiwei/flutter/bin"
fails=0
def check(ok,name,detail=""):
    global fails
    if not ok: fails+=1
    print(("PASS  " if ok else "FAIL  ")+name+("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""
check(g1==0 and g2==0,"K01 回归：v1.5 守卫与 annotation verify.sh 均为 0",f"{g1},{g2}")
c=read(SPEC/"contracts/local-persistence.md")
PINS={"crypto":"3.0.7","drift":"2.31.0","drift_flutter":"0.2.8","sqlite3":"2.9.4","sqlite3_flutter_libs":"0.5.42","path_provider":"2.1.6","drift_dev":"2.31.0","build_runner":"2.15.1","flutter_lints":"6.0.0"}
ok02=all(f"`{k}: {v}`" in c for k,v in PINS.items()) and all(f"D-NC004-0{i}" in c for i in range(1,8)) and all(s in c for s in ["## 2.1 表","## 4. outbox 外层信封","## 5. 仓储接口","### 5.1 保存规则","## 6. nchash/v2 Dart"]) and c.count("| `notes` |")==1 and "outbox_envelopes" in c
check(ok02,"K02 契约：9 个精确版本、D-NC004-01～07、表/信封/仓储/nchash 各节齐全","")
bdd=read(PACK/"BDD.md"); tdd=read(PACK/"TDD.md"); acts=[read(PACK/"act"/f"0{i}.yaml") for i in range(1,6)]
bids=re.findall(r"^\| (B\d\d) \|",bdd,re.M); est=[int((re.search(r"^ESTIMATE_MINUTES: (\d+)",a,re.M) or [0,0])[1]) for a in acts]
deps=[(re.search(r"^DEPENDS_ON: (.*)$",a,re.M) or [0,""])[1].strip() for a in acts]
vague=re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况"); hits=[f"{f}:{m.group(0)}" for f in ["README.md","BDD.md","TDD.md","ACT.yaml","PROMPT.md","ACCEPTANCE.md","act/01.yaml","act/02.yaml","act/03.yaml","act/04.yaml","act/05.yaml"] for m in vague.finditer(read(PACK/f))]
ok03=(bids==[f"B{i:02d}" for i in range(1,28)] and all(30<=e<=60 for e in est) and deps==["[]","[NC-004-A]","[NC-004-B]","[NC-004-C]","[NC-004-D]"] and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits and "+35" in tdd and "+30" not in tdd and "+11" not in tdd and read(PACK/"ACT.yaml").count("- act/0")==5 and "DEFERRED" in read(PACK/"ACT.yaml") and "二选一" in read(PACK/"README.md") and all(s in c for s in ["D-NC004-08","D-NC004-09","MentionCountExceeded","FieldLengthExceeded","interceptWith"]))
check(ok03,"K03 六件套：BDD B01～B27、五个 ACT 30–60 分钟且依赖链/ON_FAIL/WORKLOAD、无模糊词、测试计数 35、README 二选一、契约 D-08/09 与注入点",f"bids={len(bids)} est={est} deps={deps} vague={hits}")
todo=read(root/"docs/blackbox-spec-rework/SUBAGENT_TODO.md")
check("NC-004" in todo and ("local-persistence" in todo or "NC-004-A" in todo),"K04 SUBAGENT_TODO 已登记 NC-004 工作包","")
if not CLIENT.exists() and not req:
    print("SKIP  K05 reading-notes 尚不存在（验收时加 --require-impl，必须 PASS）")
else:
    det=[]; ok=True
    top=subprocess.run(["git","-C",str(CLIENT),"rev-parse","--show-toplevel"],capture_output=True,text=True).stdout.strip()
    ok&= top==str(CLIENT) and not (CLIENT.parent/".git").exists(); det.append(f"toplevel={top==str(CLIENT)}")
    import yaml
    ps=yaml.safe_load(read(CLIENT/"pubspec.yaml")) or {}; deps_all={**(ps.get("dependencies") or {}),**(ps.get("dev_dependencies") or {})}
    okp=ps.get("name")=="reading_notes" and all(str(deps_all.get(k))==v for k,v in PINS.items()) and not any(k in deps_all for k in ("persistence_drift","persistence_core","flutter_markdown_plus"))
    ok&=okp; det.append(f"pubspec={okp}")
    lock=read(CLIENT/"pubspec.lock"); okl=all(re.search(rf"^  {re.escape(k)}:\n(?:    .*\n)*?    version: \"{re.escape(v)}\"",lock,re.M) for k,v in PINS.items()); ok&=okl; det.append(f"lock={okl}")
    okf=(CLIENT/"test/fixtures/community_content_hash_cases.json").is_file() and (CLIENT/"test/fixtures/community_content_hash_cases.json").read_bytes()==(SPEC/"fixtures/community/content_hash_cases.json").read_bytes(); ok&=okf; det.append(f"fixture={okf}")
    tracked=subprocess.run(["git","-C",str(CLIENT),"ls-files"],capture_output=True,text=True).stdout.split(); okg="lib/src/persistence/note_database.g.dart" in tracked and "pubspec.lock" in tracked; ok&=okg; det.append(f"g.dart+lock tracked={okg}")
    ncommits=len(subprocess.run(["git","-C",str(CLIENT),"log","--format=%h"],capture_output=True,text=True).stdout.split()); ok&= ncommits==5; det.append(f"commits={ncommits}")
    src="".join(read(p) for p in (CLIENT/"test").rglob("*.dart")) if (CLIENT/"test").exists() else ""
    cheats=[p for p in ("skip:","skip(","expect(true, isTrue)") if p in src]; nch=read(CLIENT/"lib/src/domain/nchash.dart")
    libsrc="".join(read(p) for p in (CLIENT/"lib").rglob("*.dart")) if (CLIENT/"lib").exists() else ""
    okc=not cheats and "jsonEncode" not in nch and "JsonEncoder" not in nch and "NativeDatabase.memory" not in src and "NativeDatabase.memory" not in libsrc; ok&=okc; det.append(f"cheats={cheats} memory={('NativeDatabase.memory' in src)}")
    env=dict(__import__("os").environ); env["PATH"]=FL+":"+env["PATH"]
    an=subprocess.run(["flutter","analyze"],cwd=CLIENT,capture_output=True,text=True,env=env); ok&= an.returncode==0; det.append(f"analyze={an.returncode}")
    ft=subprocess.run(["flutter","test"],cwd=CLIENT,capture_output=True,text=True,env=env); m=re.search(r"\+(\d+): All tests passed!",ft.stdout); ok&= ft.returncode==0 and m is not None and int(m.group(1))>=35; det.append(f"test={ft.returncode}/{m.group(1) if m else '无'}")
    check(ok,"K05 reading-notes：独立仓库、pubspec/lock 精确版本、fixture 副本一致、生成文件与 lock 已提交、恰 5 提交、无作弊、analyze 0、flutter test ≥35 全过","; ".join(det))
print(f"\nNC-004 失败条数：{fails}"); sys.exit(fails)
PY
