#!/usr/bin/env bash
# NC-001 开工包 R2 守卫：回归 v1.5 守卫与 verify.sh；核对 R1 返工已在提交 aadd1fc 落实（永久为真）；
# 核对 R2 返工（契约裁定、必填键全表、31 个方法、四个 ACT）与基线事实；--require-impl 时核对校验器实现。
# 用法：bash docs/blackbox-spec-rework/reviews/nc001_r2_guard.sh [--require-impl]
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
R1_COMMIT = "aadd1fc"
fails = 0

def check(ok, name, detail=""):
    global fails
    if not ok:
        fails += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else f" — {detail}"))

def read(p):
    return p.read_text(encoding="utf-8") if p.is_file() else ""

def show(rel):  # 提交 aadd1fc 中的文件内容（R1 返工落实点，固定不变）
    r = subprocess.run(["git", "-C", str(root), "show", f"{R1_COMMIT}:{rel}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""

doc1 = read(gdir / "NC-001-REVIEW-R1.md")

# K01：既有回归
check(prev == 0 and ver == 0, "K01 回归：review_v1_5_guard.sh 与 verify.sh 均为 0", f"v1.5 守卫={prev}，verify={ver}")

# K02：R1 的 8 个整文件在 aadd1fc 中逐字一致（历史事实，与当前工作树无关）
whole = re.findall(r"\*\*整文件 (\d+)\*\*｜文件：`([^`]+)`\n\n````text\n(.*?)\n````\n", doc1, re.S)
bad = [n for n, rel, body in whole if show(rel) != body + "\n"]
check(len(whole) == 8 and not bad, f"K02 R1 的 8 个整文件在 {R1_COMMIT} 中逐字一致", f"解析 {len(whole)}，不一致={bad}")

# K03：R1 的 18 处替换在 aadd1fc 中已落实
pairs = re.findall(r"\*\*替换 (\d+)\*\*｜文件：`([^`]+)`\n\n原文：\n```text\n(.*?)\n```\n\n替换为：\n```text\n(.*?)\n```", doc1, re.S)
bad = [n for n, rel, old, new in pairs if (t := show(rel)).count(new) != 1 or (old not in new and old in t)]
check(len(pairs) == 18 and not bad, f"K03 R1 的 18 处逐字替换在 {R1_COMMIT} 中已落实", f"解析 {len(pairs)}，未落实={bad}")

# K04：基线事实可复核（与 R1 相同）
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
except Exception as e:
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

# K07：BDD 编号、TDD 方法、必填键全表、四个 ACT 粒度与依赖链
tdd, bdd = read(pack / "TDD.md"), read(pack / "BDD.md")
methods = re.findall(r"^\| (test_[a-z0-9_]+) \|", tdd, re.M)
bids = re.findall(r"^\| (B\d\d) \|", bdd, re.M)
mk = re.search(r"### 3\.1.*?```text\n(.*?)\n```", tdd, re.S)
keys = mk.group(1).split("\n") if mk else []
acts, est, deps, onfail = [], [], [], []
for i in range(1, 5):
    t = read(pack / "act" / f"0{i}.yaml")
    acts.append(bool(t))
    mm = re.search(r"^ESTIMATE_MINUTES: (\d+)", t, re.M)
    est.append(int(mm.group(1)) if mm else 0)
    dd = re.search(r"^DEPENDS_ON: (.*)$", t, re.M)
    deps.append(dd.group(1).strip() if dd else "")
    onfail.append("外部失败" in t and "ON_FAIL" in t and "WORKLOAD" in t)
want_deps = ["[]", "[NC-001-01-A]", "[NC-001-01-B]", "[NC-001-01-C]"]
ok07 = (len(methods) == 32 == len(set(methods))
        and bids == [f"B{i:02d}" for i in range(1, 24)] and all(x in tdd for x in bids)
        and len(keys) == 103 == len(set(keys))
        and all(acts) and all(30 <= x <= 60 for x in est) and deps == want_deps and all(onfail)
        and not (pack / "act" / "05.yaml").exists())
check(ok07, "K07 BDD B01～B23 全覆盖、TDD 32 个方法不重复、必填键 103 条、四个 ACT 30–60 分钟且依赖链/ON_FAIL/WORKLOAD 齐全",
      f"方法={len(methods)}，BDD={len(bids)}，必填键={len(keys)}，估时={est}，依赖={deps}，onfail={onfail}")

# K09：契约 R2 裁定句存在（歧义已封闭）
need = ["闸门只作用于 §4 的增量检查", "stdout 恰为一行 `root`", "只报该数组路径本身，不下钻"]
miss = [s for s in need if s not in contract]
check(not miss, "K09 契约含 R2 三条裁定（状态闸门范围、根类型输出、数组元素路径）", f"缺={miss}")

# K11：外部失败豁免覆盖 R2 守卫 K01，且七处措辞一致
EX = "`nc001_r2_guard.sh` 的 K01 失败同样按外部失败处理；其 K02～K11 失败仍按本任务失败停工。"
miss11 = [f for f in ["README.md", "PROMPT.md", "TDD.md", "act/01.yaml", "act/02.yaml", "act/03.yaml", "act/04.yaml"] if EX not in read(pack / f)]
check(not miss11, "K11 外部失败豁免含 R2 守卫 K01，七处逐字一致", f"缺={miss11}")

# K10：六件套无模糊词、无对 R1 守卫/两步拆分的残留引用
vague = re.compile(r"适当|优雅|合理|必要时|酌情|尽量|大致|视情况")
hits = []
for f in ["README.md", "BDD.md", "TDD.md", "VALIDATION_CONTRACT.md", "ACT.yaml", "PROMPT.md", "ACCEPTANCE.md", "act/01.yaml", "act/02.yaml", "act/03.yaml", "act/04.yaml"]:
    t = read(pack / f)
    for mm in vague.finditer(t):
        hits.append(f"{f}:{mm.group(0)}")
    if "nc001_r1_guard" in t or "两个 ACT" in t or "分两步" in t or "31 个方法" in t or "后者此时退出 2" in t:
        hits.append(f"{f}:残留 R1/两步引用")
check(not hits, "K10 六件套无模糊词、无 R1 守卫与两步拆分残留", f"{hits}")

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
    missing_keys = [k for k in keys if f'"{k}"' not in src and f"'{k}'" not in src]
    cheats = [p for p in ("skip", "assertTrue(True)", "expectedFailure") if p in src]
    has_list = "REQUIRED_KEY_PATHS" in src
    detail = (f"local={loc.returncode}/{loc.stdout.strip()!r}，integrated={itg.returncode}，"
              f"integrated 输出一致={itg.stdout == chr(10).join(golden) + chr(10)}，unittest={ut.returncode}，"
              f"用例数={ran.group(1) if ran else '无'}，缺方法={missing}，缺必填键字面量={len(missing_keys)}，"
              f"REQUIRED_KEY_PATHS={has_list}，可疑写法={cheats}")
    ok08 = (checker.exists() and loc.returncode == 0 and loc.stdout == "LOCAL_PREPARATION_PASS\n"
            and itg.returncode == 1 and itg.stdout == "\n".join(golden) + "\n"
            and ut.returncode == 0 and ran is not None and int(ran.group(1)) >= 32
            and not missing and not missing_keys and has_list and not cheats)
    check(ok08, "K08 校验器：local 通过、integrated 输出与契约 §7 逐字相同、32 个方法与 103 条必填键字面量齐全且无跳过", detail)

print(f"\nNC-001 R2 失败条数：{fails}")
sys.exit(fails)
PY
