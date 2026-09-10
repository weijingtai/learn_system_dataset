#!/usr/bin/env bash
# 注解社区线四份文档的结构与交叉引用校验器。
# 用法：bash openspec/annotation-community/verify.sh
# 退出码 = FAIL 条数；0 表示全部通过。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 - "$DIR" <<'PY'
import os, re, sys

d = sys.argv[1]
fails = 0

def check(ok, name, detail=""):
    global fails
    if ok:
        print(f"PASS  {name}")
    else:
        fails += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))

REQUIRED = ["PRD.md", "DESIGN.md", "PLANS.md", "TASKS.md", "REVIEW_R1.md"]
for f in REQUIRED:
    check(os.path.exists(os.path.join(d, f)), f"必需文件存在：{f}")

docs = {}
for f in REQUIRED:
    p = os.path.join(d, f)
    docs[f] = open(p, encoding="utf-8").read() if os.path.exists(p) else ""

# 1. 相对链接可达
broken = []
for f, s in docs.items():
    for m in re.finditer(r"\]\((?!https?://)([^)#]+?)(?:#[^)]*)?\)", s):
        target = m.group(1).strip()
        if target.endswith(".sh") or target.startswith("<"):
            continue
        if not os.path.exists(os.path.normpath(os.path.join(d, target))):
            broken.append(f"{f} -> {target}")
check(not broken, "相对链接全部可达", "; ".join(broken))

# 2. R-01～R-20 在 PRD 定义且在 TASKS 以完整 ID 出现
prd_r = set(re.findall(r"^\| (R-\d\d) \|", docs["PRD.md"], re.M))
check(prd_r == {f"R-{i:02d}" for i in range(1, 22)}, "PRD 定义 R-01～R-21",
      f"实际 {sorted(prd_r)}")
tasks_r = set(re.findall(r"R-\d\d", docs["TASKS.md"]))
missing = sorted(prd_r - tasks_r)
check(not missing, "每个 R-xx 在 TASKS 以完整 ID 出现（禁止 R-09/10 压缩写法）",
      f"缺 {missing}")

# 3. PRD §3.1 断言点索引覆盖全部 R
sec = docs["PRD.md"].split("## 3.1")[-1].split("## 4.")[0]
idx_r = set(re.findall(r"^\| (R-\d\d) \|", sec, re.M))
check(prd_r <= idx_r, "PRD §3.1 断言点索引覆盖全部 R", f"缺 {sorted(prd_r - idx_r)}")

# 4. TASKS 总表：状态值属于 gate §7 七值枚举
GATE = {"BACKLOG", "PREPARING", "READY", "DISPATCHED", "REVIEWING", "ACCEPTED", "BLOCKED"}
rows = re.findall(r"^\| (NC-\d+\w?) \|([^|]*)\|([^|]*)\|([^|]*)\|", docs["TASKS.md"], re.M)
bad = [(nc, st.strip()) for nc, _sc, _dep, st in rows if st.strip() not in GATE]
check(rows and not bad, "TASKS 状态值属于门禁 §7 七值枚举", f"越界 {bad}")

# 5. NC 依赖：被引用的任务都已定义，且依赖图无环
defined = {nc for nc, *_ in rows}
deps = {}
for nc, _sc, dep, _st in rows:
    deps[nc] = [x for x in re.findall(r"NC-\d+\w?", dep)]
undef = sorted({d for ds in deps.values() for d in ds if d not in defined})
check(not undef, "NC 依赖全部已定义", f"未定义 {undef}")

color = {}
cycles = []
def dfs(n, path):
    color[n] = 1
    for x in deps.get(n, []):
        if color.get(x) == 1:
            cycles.append(" -> ".join(path + [n, x]))
        elif color.get(x, 0) == 0:
            dfs(x, path + [n])
    color[n] = 2
for n in deps:
    if color.get(n, 0) == 0:
        dfs(n, [])
check(not cycles, "NC 依赖图无环", "; ".join(cycles))

# 6. 无 BACKLOG 任务依赖 BLOCKED 任务的隐藏阻塞
status = {nc: st.strip() for nc, _sc, _dep, st in rows}
hidden = [f"{nc}->{x}" for nc, ds in deps.items() for x in ds
          if status.get(nc) == "BACKLOG" and status.get(x) == "BLOCKED"]
check(not hidden, "无 BACKLOG 依赖 BLOCKED 的隐藏阻塞", "; ".join(hidden))

# 7. 每个 NC 在总表登记后都有对应详细章节
sections = set(re.findall(r"^### (NC-\d+\w?)[：:]", docs["TASKS.md"], re.M))
check(defined <= sections, "总表每个 NC 都有详细章节", f"缺 {sorted(defined - sections)}")

# 8. 外部依赖 ID 有承接任务（不能全仓只出现一次）
for eid in re.findall(r"^\| (E-[A-Z]+) \|", docs["PRD.md"], re.M):
    row = [l for l in docs["PRD.md"].splitlines() if l.startswith(f"| {eid} |")][0]
    check(bool(re.search(r"NC-\d+", row)), f"外部依赖 {eid} 标注了承接任务")

# 9. 占位符扫描（剔除反引号内的代码片段与 SUBAGENT_TODO 文件名，
#    这些是对占位符的「引用」而非占位符本身）
ph = []
for f, s in docs.items():
    stripped = re.sub(r"`[^`]*`", "", s).replace("SUBAGENT_TODO", "")
    for pat in ("TODO", "TBD", "FIXME", "XXX", "待定"):
        for m in re.finditer(re.escape(pat), stripped):
            line = stripped[:m.start()].count("\n") + 1
            ph.append(f"{f}:{line}:{pat}")
check(not ph, "无未决占位符", "; ".join(ph))

print(f"\n{'-'*44}\nFAIL 条数：{fails}")
sys.exit(fails)
PY
