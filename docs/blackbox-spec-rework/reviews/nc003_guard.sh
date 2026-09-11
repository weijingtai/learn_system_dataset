#!/usr/bin/env bash
# NC-003 守卫：回归既有守卫；核对契约与六件套；--require-impl 时核对 REST 仓库中 NC-003 产物（验证器、dart test）。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"; REQ="${1:-}"
LC_ALL=C bash "$ROOT/openspec/annotation-community/review_v1_5_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
"$ROOT/.venv/bin/python" - "$ROOT" "$g1" "$g2" "$REQ" <<'PY'
import re, subprocess, sys, os
from pathlib import Path
root=Path(sys.argv[1]); g1,g2=int(sys.argv[2]),int(sys.argv[3]); req=sys.argv[4]=="--require-impl"
SPEC=root/"openspec/annotation-community"; PACK=root/"docs/blackbox-spec-rework/work-items/nc-003"
REST=Path("/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter"); FL="/Users/jingtaiwei/flutter/bin"
VAL=SPEC/".venv-openapi/bin/openapi-spec-validator"
fails=0
def check(ok,name,detail=""):
    global fails
    if not ok: fails+=1
    print(("PASS  " if ok else "FAIL  ")+name+("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""
check(g1==0 and g2==0,"K01 回归：v1.5 守卫与 annotation verify.sh 均为 0",f"{g1},{g2}")
c=read(SPEC/"contracts/community_api.md")
ops=["content.publish","content.update","content.withdraw","content.trash","content.restore","content.purge","comment.create","comment.edit","comment.delete","reaction.set","bookmark.set","share.create","share.revoke","report.create","backup.begin","backup.complete","backup.delete"]
codes=["unauthenticated","not_found.content","forbidden.not_owner","forbidden.thread_closed","conflict.version","conflict.idempotency","conflict.access_version","conflict.lifecycle","conflict.object_missing","rate_limited","gone.command_result","unavailable.command_status"]
need=["/v1/community","IdempotencyKey","IfMatch","IfNoneMatch","NotFoundContent","ProblemDetails","CommandResult","openapi-spec-validator 0.9.0","in: header","snake_case","x-xuan-function","retry_after_seconds","GET /commands/{command_id}"]
ok02=all(o in c for o in ops) and all(k in c for k in codes) and all(n in c for n in need) and all(f"D-NC003-{i:02d}" in c for i in range(1,12)) and VAL.is_file()
check(ok02,"K02 契约：17 操作、错误目录、头参数、验证器实值、D-NC003-01～11、验证器已安装",f"missing={[x for x in ops+codes+need if x not in c]} validator={VAL.is_file()}")
bdd=read(PACK/"BDD.md"); tdd=read(PACK/"TDD.md"); acts=[read(PACK/"act"/f"0{i}.yaml") for i in range(1,5)]
bids=re.findall(r"^\| (B\d\d) \|",bdd,re.M); est=[int((re.search(r"^ESTIMATE_MINUTES: (\d+)",a,re.M) or [0,0])[1]) for a in acts]
deps=[(re.search(r"^DEPENDS_ON: (.*)$",a,re.M) or [0,""])[1].strip() for a in acts]
vague=re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况"); files=["README.md","BDD.md","TDD.md","ACT.yaml","PROMPT.md","ACCEPTANCE.md","act/01.yaml","act/02.yaml","act/03.yaml","act/04.yaml"]
hits=[f"{f}:{m.group(0)}" for f in files for m in vague.finditer(read(PACK/f))]
ok03=(bids==[f"B{i:02d}" for i in range(1,24)] and all(30<=e<=60 for e in est) and deps==["[]","[NC-003-A]","[NC-003-B]","[NC-003-C]"] and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits and "+64" in tdd and "+52" in tdd and "+58" in tdd and "+63" in tdd and "DISPATCH_PRECONDITION" in read(PACK/"ACT.yaml") and "0f8bf52" in read(PACK/"README.md") and "openapi-spec-validator" in read(PACK/"PROMPT.md"))
check(ok03,"K03 六件套：BDD B01～B23、四个 ACT 30–60 分钟且依赖链/ON_FAIL/WORKLOAD、无模糊词、计数 52/58/63/64、基线 hash",f"bids={len(bids)} est={est} deps={deps} vague={hits}")
todo=read(root/"docs/blackbox-spec-rework/SUBAGENT_TODO.md"); check("NC-003" in todo and "community_api.md" in todo,"K04 SUBAGENT_TODO 已登记 NC-003 工作包与契约","")
tool=REST/"tool/validate_openapi"
if not tool.exists() and not req:
    print("SKIP  K05 NC-003 产物尚不存在（验收时加 --require-impl，必须 PASS）")
else:
    det=[]; ok=True
    for f in ["tool/validate_openapi","tool/check_examples.py","test/community_openapi_contract_test.dart","test/fixtures/openapi/red_operation_headers.yaml","test/fixtures/openapi/red_invalid_31.yaml","test/fixtures/openapi/examples/manifest.json"]:
        if not (REST/f).is_file(): ok=False; det.append(f"missing {f}")
    y=read(REST/"openapi/openapi.yaml"); ok&=("/v1/community/commands/{command_id}" in y and "info:\n" in y and "version: 1.1.0" in y); det.append(f"yaml_community={'/v1/community/commands' in y}")
    ts=read(tool); ok&=("openapi-spec-validator" in ts); det.append(f"tool_uses_validator={'openapi-spec-validator' in ts}")
    ce=read(REST/"tool/check_examples.py"); ok&=("jsonschema" in ce); det.append(f"check_examples_uses_jsonschema={'jsonschema' in ce}")
    src=read(REST/"test/community_openapi_contract_test.dart")+read(REST/"test/openapi_validation_test.dart"); cheats=[p for p in ("skip:","skip(","expect(true, isTrue)") if p in src]; ok&=not cheats; det.append(f"cheats={cheats}")
    for f in ["lib","pubspec.yaml","pubspec.lock","test/rest_contract_suite_test.dart","test/wire_test.dart"]:
        r=subprocess.run(["git","-C",str(REST),"log","--format=%s","--",f],capture_output=True,text=True).stdout
        if "NC-003" in r: ok=False; det.append(f"NC-003 触碰了 {f}")
    if VAL.is_file():
        v=subprocess.run([str(VAL),str(REST/"openapi/openapi.yaml")],capture_output=True,text=True); ok&=v.returncode==0; det.append(f"validator={v.returncode}")
        for rf in ["red_operation_headers.yaml","red_invalid_31.yaml"]:
            p=REST/"test/fixtures/openapi"/rf
            if p.is_file():
                r=subprocess.run([str(VAL),str(p)],capture_output=True,text=True); ok&=r.returncode!=0; det.append(f"{rf}={r.returncode}")
    else: ok=False; det.append("validator not installed")
    env=dict(os.environ); env["PATH"]=FL+":"+env["PATH"]
    dt=subprocess.run(["dart","test"],cwd=REST,capture_output=True,text=True,env=env); m=re.search(r"\+(\d+): All tests passed!",dt.stdout); ok&=dt.returncode==0 and m is not None and int(m.group(1))>=64; det.append(f"dart_test={dt.returncode}/{m.group(1) if m else '无'}")
    check(ok,"K05 NC-003 产物：工具与 fixture、社区路径与 1.1.0、真实验证器 0/红文档非 0、无作弊、未触碰 lib/pubspec、dart test ≥64","; ".join(det))
print(f"\nNC-003 失败条数：{fails}"); sys.exit(fails)
PY
