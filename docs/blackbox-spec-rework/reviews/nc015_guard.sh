#!/usr/bin/env bash
# NC-015 守卫：回归 v1.6 守卫；核对契约与六件套；--require-impl 时核对样例与检查器。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$DIR/../../.." && pwd)"; REQ="${1:-}"
bash "$ROOT/openspec/annotation-community/review_v1_6_guard.sh" >/dev/null 2>&1; g1=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1; g2=$?
"$ROOT/.venv/bin/python" - "$ROOT" "$g1" "$g2" "$REQ" <<'PY'
import re, subprocess, sys, json, shutil, tempfile
from pathlib import Path
root=Path(sys.argv[1]); g1,g2=int(sys.argv[2]),int(sys.argv[3]); req=sys.argv[4]=="--require-impl"
SPEC=root/"openspec/annotation-community"; PACK=root/"docs/blackbox-spec-rework/work-items/nc-015"; PY=root/".venv/bin/python"
fails=0
def check(ok,name,detail=""):
    global fails
    if not ok: fails+=1
    print(("PASS  " if ok else "FAIL  ")+name+("" if ok or not detail else f" — {detail}"))
def read(p): return p.read_text(encoding="utf-8") if p.is_file() else ""
check(g1==0 and g2==0,"K01 回归：v1.6 守卫与 verify.sh 均为 0",f"{g1},{g2}")
c=read(SPEC/"contracts/private_sync.md")
need=["2026-08-02-s6-p2p-sync-third-party-design.md","app_user_id","verifyPeerSession","expiresAtUtcMs","X25519","HKDF-SHA256","associatedData","/v1/messages/relay","private/p2p/","300 秒","age: 1","nchash/v2","duplicate_ack","reject:hash_mismatch","reject:aad_mismatch","session_key_unbound","pairing_refused_anonymous","session_pub_sig","signed_fields","不重写密码学"]
secs=all(f"## {i}." in c for i in range(1,10))
c_nocode=re.sub(r"`[^`\n]*`","",c)
ok02=secs and all(n in c for n in need) and all(f"D-NC015-{i:02d}" in c for i in range(1,10)) and "TBD" not in c_nocode and "待定" not in c_nocode
check(ok02,"K02 契约：九节、S6 引用、身份/授权/一次一密/中转/删除/验收要素、D-NC015-01～09、无占位",f"missing={[n for n in need if n not in c]} secs={secs}")
bdd=read(PACK/"BDD.md"); tdd=read(PACK/"TDD.md"); acts=[read(PACK/"act"/f"0{i}.yaml") for i in range(1,3)]
bids=re.findall(r"^\| (B\d\d) \|",bdd,re.M); est=[int((re.search(r"^ESTIMATE_MINUTES: (\d+)",a,re.M) or [0,0])[1]) for a in acts]
deps=[(re.search(r"^DEPENDS_ON: (.*)$",a,re.M) or [0,""])[1].strip() for a in acts]
vague=re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况"); files=["README.md","BDD.md","TDD.md","ACT.yaml","PROMPT.md","ACCEPTANCE.md","act/01.yaml","act/02.yaml"]
hits=[f"{f}:{m.group(0)}" for f in files for m in vague.finditer(read(PACK/f))]
ok03=(bids==[f"B{i:02d}" for i in range(1,17)] and all(30<=e<=60 for e in est) and deps==["[]","[NC-015-A]"] and all("ON_FAIL" in a and "WORKLOAD" in a for a in acts) and not hits and "samples=18" in tdd and "攻击/故障场景" in read(PACK/"ACCEPTANCE.md") and "D-NC015-07" in read(PACK/"PROMPT.md"))
check(ok03,"K03 六件套：BDD B01～B16、两个 ACT 30–60 分钟、依赖链/ON_FAIL/WORKLOAD、无模糊词、samples=18、攻击场景审查项",f"bids={len(bids)} est={est} deps={deps} vague={hits}")
todo=read(root/"docs/blackbox-spec-rework/SUBAGENT_TODO.md"); check("NC-015" in todo and "private_sync.md" in todo,"K04 SUBAGENT_TODO 已登记 NC-015 工作包与契约","")
tool=SPEC/"tools/check_private_sync_protocol.py"; fx=SPEC/"fixtures/private_sync"
if not tool.exists() and not req:
    print("SKIP  K05 NC-015 产物尚不存在（验收时加 --require-impl，必须 PASS）")
else:
    det=[]; ok=tool.is_file() and (SPEC/"tools/test_check_private_sync_protocol.py").is_file(); det.append(f"files={ok}")
    n=len(list(fx.glob("*.json"))) if fx.exists() else 0; ok&=n==18; det.append(f"samples={n}")
    r=subprocess.run([str(PY),str(tool)],capture_output=True,text=True,cwd=root); ok&=r.returncode==0 and "samples=18" in r.stdout; det.append(f"checker={r.returncode}")
    t=subprocess.run([str(PY),"-m","unittest",str(SPEC/"tools/test_check_private_sync_protocol.py")],capture_output=True,text=True,cwd=root); m=re.search(r"Ran (\d+) tests",t.stderr); ok&=t.returncode==0 and m is not None and int(m.group(1))>=16; det.append(f"unittest={t.returncode}/{m.group(1) if m else '无'}")
    src=read(SPEC/"tools/test_check_private_sync_protocol.py"); cheats=[p for p in ("skip","assertTrue(True)") if p in src]; ok&=not cheats; det.append(f"cheats={cheats}")
    if fx.exists() and n==18:
        tmp=Path(tempfile.mkdtemp()); shutil.copytree(fx,tmp/"fx"); (tmp/"fx"/"relay_ttl.json").write_text(json.dumps({"notifier_role":"signaling_only","sender_fallback_seconds":299,"storage_lifecycle_days":1,"expected":"config_ok"}),encoding="utf-8")
        r2=subprocess.run([str(PY),str(tool),"--contract",str(SPEC/"contracts/private_sync.md"),"--fixtures",str(tmp/"fx")],capture_output=True,text=True,cwd=root); ok&=r2.returncode!=0; det.append(f"tamper_ttl={r2.returncode}")
        shutil.rmtree(tmp/"fx"); shutil.copytree(fx,tmp/"fx"); av=json.loads((tmp/"fx"/"auth_valid.json").read_text(encoding="utf-8")); h=av["peer_auth"]["accountBindingCertHash"]; av["peer_auth"]["accountBindingCertHash"]=("0" if h[0]!="0" else "1")+h[1:]; (tmp/"fx"/"auth_valid.json").write_text(json.dumps(av),encoding="utf-8")
        r3=subprocess.run([str(PY),str(tool),"--contract",str(SPEC/"contracts/private_sync.md"),"--fixtures",str(tmp/"fx")],capture_output=True,text=True,cwd=root); ok&=r3.returncode!=0; det.append(f"tamper_cert_hash={r3.returncode}")
        shutil.rmtree(tmp,ignore_errors=True)
    check(ok,"K05 NC-015 产物：检查器与自测存在、18 样例、检查器 0 且 samples=18、unittest ≥16、无作弊、TTL/证书哈希篡改副本被拒","; ".join(det))
print(f"\nNC-015 失败条数：{fails}"); sys.exit(fails)
PY
