#!/usr/bin/env bash
# NC-001 开工包 R1 守卫：回归 v1.5 守卫与 verify.sh，再核对 NC-001-REVIEW-R1.md 的整文件、逐字替换与基线事实。
# 用法：bash docs/blackbox-spec-rework/reviews/nc001_r1_guard.sh [--require-impl]
#   --require-impl：校验器必须已实现，且对当前输入给出契约 §7 的期望输出（主线程验收 NC-001-01 时使用）。
# 退出码 = 失败条数。只做结构与事实核对，不代替语义审查。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../../.." && pwd)"
REQ="${1:-}"

LC_ALL=C bash "$ROOT/openspec/annotation-community/review_v1_5_guard.sh" >/dev/null 2>&1
prev=$?
bash "$ROOT/openspec/annotation-community/verify.sh" >/dev/null 2>&1
ver=$?

python3 - "$ROOT" "$DIR" "$prev" "$ver" "$REQ" <<'PY'
import json, re, subprocess, sys
from pathlib import Path

root, gdir = Path(sys.argv[1]), Path(sys.argv[2])
prev, ver, req = int(sys.argv[3]), int(sys.argv[4]), sys.argv[5] == "--require-impl"
pack = root / "docs/blackbox-spec-rework/work-items/nc-001"
fails = 0

def check(ok, name, detail=""):
    global fails
    if not ok:
        fails += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else f" — {detail}"))

def read(p):
    return p.read_text(encoding="utf-8") if p.is_file() else ""

doc = read(gdir / "NC-001-REVIEW-R1.md")

# K01：既有回归
check(prev == 0 and ver == 0, "K01 回归：review_v1_5_guard.sh 与 verify.sh 均为 0", f"v1.5 守卫={prev}，verify={ver}")

# K02：整文件逐字一致
whole = re.findall(r"\*\*整文件 (\d+)\*\*｜文件：`([^`]+)`\n\n````text\n(.*?)\n````\n", doc, re.S)
declared = len(re.findall(r"\*\*整文件 \d+\*\*｜文件：", doc))
bad = [n for n, rel, body in whole if read(root / rel) != body + "\n"]
check(len(whole) == declared == 8 and not bad, "K02 8 个整文件与说明逐字一致", f"解析 {len(whole)}/{declared}，不一致={bad}")

# K03：逐字替换已落实（新文字恰好一次；原文不是新文字一部分时，原文已不存在）
pairs = re.findall(r"\*\*替换 (\d+)\*\*｜文件：`([^`]+)`\n\n原文：\n```text\n(.*?)\n```\n\n替换为：\n```text\n(.*?)\n```", doc, re.S)
declared = len(re.findall(r"\*\*替换 \d+\*\*｜文件：", doc))
bad = []
for n, rel, old, new in pairs:
    t = read(root / rel)
    if t.count(new) != 1 or (old not in new and old in t):
        bad.append(n)
check(len(pairs) == declared == 18 and not bad, "K03 18 处逐字替换已落实", f"解析 {len(pairs)}/{declared}，未落实={bad}")

# K04：基线事实可复核
issues = []
try:
    b = json.loads(read(root / "openspec/annotation-community/integration_baseline.json"))
    c = b["client"]
    cp = Path(c["path"])
    if c["state"] == "PLANNED_NEW" and (cp.exists() or not cp.parent.is_dir()):
        issues.append("client.path")
    if c["state"] == "EXISTING" and not (cp / "pubspec.yaml").is_file():
        issues.append("client.path")
    fv = json.loads(read(Path(b["sdk"]["evidence"])) or "{}")
    if fv.get("frameworkVersion") != b["sdk"]["flutter"] or fv.get("dartSdkVersion") != b["sdk"]["dart"]:
        issues.append("sdk")
    lock = read(Path("/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage/drift/pubspec.lock"))
    for k in ("drift", "drift_dev", "drift_flutter", "sqlite3", "sqlite3_flutter_libs", "path_provider", "build_runner"):
        m = re.search(r"^  " + re.escape(k) + r":\n(?:    .*\n)*?    version: \"([^\"]+)\"", lock, re.M)
        if not m or m.group(1) != b["dependencies"][k]:
            issues.append(f"dependencies.{k}")
    md = Path.home() / ".pub-cache/hosted/pub.dev" / ("flutter_markdown_plus-" + b["dependencies"]["flutter_markdown_plus"])
    if not md.is_dir():
        issues.append("dependencies.flutter_markdown_plus")
    want = sorted(["HOST_INIT", "ACCOUNT_SCOPE", "HTTP", "STORAGE", "IM_NAVIGATION", "MENTION", "NOTIFICATION_RECEIVE", "SERVER_IDENTITY"])
    if sorted(p["name"] for p in b["ports"]) != want:
        issues.append("ports")
    np_ = b["integration"]["notification_presentation"]
    targets = [(f"ports[{p['name']}]", p["file"], p["symbol"]) for p in b["ports"]]
    targets.append(("integration.notification_presentation", np_["file"], np_["symbol"]))
    for label, f, s in targets:
        text = read(Path(f))
        if not text:
            issues.append(label + ".file")
            continue
        for seg in s.split("."):
            if not re.search(r"\b" + re.escape(seg) + r"\b", text):
                issues.append(f"{label}.symbol({seg})")
except Exception as e:  # 结构缺失时记为失败而不是崩溃
    issues.append(f"无法解析基线：{e!r}")
    b = {}
check(not issues, "K04 基线事实可复核（客户端路径、SDK、锁文件版本、端口与通知页符号）", f"{issues}")

# K05：HEAD 新鲜度，只提示
for r in b.get("repositories", []):
    if "head" not in r:
        continue
    h = subprocess.run(["git", "-C", r["git_root"], "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if h != r["head"]:
        print(f"WARN  K05 {r['name']} 当前 HEAD {h[:7] or '无'} ≠ 采样值 {r['head'][:7]}（仅提示，新鲜度由 NC-001-02 重新取证）")

# K06：契约 §7 期望输出
contract = read(pack / "VALIDATION_CONTRACT.md")
m = re.search(r"^## 7\..*?```text\n(.*?)\n```", contract, re.S | re.M)
golden = m.group(1).split("\n") if m else []
check(len(golden) == 23 and golden == sorted(set(golden)), "K06 契约 §7 期望输出为 23 行、去重且已排序", f"行数={len(golden)}")

# K07：BDD 编号、TDD 方法与 ACT 粒度
tdd, bdd = read(pack / "TDD.md"), read(pack / "BDD.md")
methods = re.findall(r"^\| (test_[a-z0-9_]+) \|", tdd, re.M)
bids = re.findall(r"^\| (B\d\d) \|", bdd, re.M)
est = []
for f in ("01.yaml", "02.yaml"):
    mm = re.search(r"^ESTIMATE_MINUTES: (\d+)", read(pack / "act" / f), re.M)
    est.append(int(mm.group(1)) if mm else 0)
ok07 = (len(methods) == 21 == len(set(methods)) and bids == [f"B{i:02d}" for i in range(1, 18)]
        and all(x in tdd for x in bids) and all(30 <= x <= 60 for x in est))
check(ok07, "K07 BDD B01～B17 全部被 TDD 覆盖，TDD 21 个方法不重复，两个 ACT 均在 30–60 分钟", f"方法={len(methods)}，BDD={len(bids)}，估时={est}")

# K08：校验器实现核对
tools = root / "openspec/annotation-community/tools"
checker, testf = tools / "check_integration_baseline.py", tools / "test_check_integration_baseline.py"
if not checker.exists() and not req:
    print("SKIP  K08 校验器尚未实现（验收 NC-001-01 时加 --require-impl，必须 PASS）")
else:
    inp = "openspec/annotation-community/integration_baseline.json"
    run = lambda prof: subprocess.run([sys.executable, str(checker), "--profile", prof, "--input", inp], cwd=root, capture_output=True, text=True)
    loc, itg = run("local"), run("integrated")
    ut = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(tools), "-p", "test_check_integration_baseline.py"],
                        cwd=root, capture_output=True, text=True)
    ran = re.search(r"Ran (\d+) tests?", ut.stderr)
    src = read(testf)
    missing = [x for x in methods if f"def {x}(" not in src]
    cheats = [p for p in ("skip", "assertTrue(True)", "expectedFailure") if p in src]
    detail = (f"local={loc.returncode}/{loc.stdout.strip()!r}，integrated={itg.returncode}，"
              f"integrated 输出一致={itg.stdout == chr(10).join(golden) + chr(10)}，unittest={ut.returncode}，"
              f"用例数={ran.group(1) if ran else '无'}，缺方法={missing}，可疑写法={cheats}")
    ok08 = (checker.exists() and loc.returncode == 0 and loc.stdout == "LOCAL_PREPARATION_PASS\n"
            and itg.returncode == 1 and itg.stdout == "\n".join(golden) + "\n"
            and ut.returncode == 0 and ran is not None and int(ran.group(1)) >= 21 and not missing and not cheats)
    check(ok08, "K08 校验器：local 通过、integrated 输出与契约 §7 逐字相同、21 个方法齐全且无跳过", detail)

print(f"\nNC-001 R1 失败条数：{fails}")
sys.exit(fails)
PY
