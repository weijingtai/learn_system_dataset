#!/usr/bin/env bash
# R2 复核的回归守卫：R0 防止已废止规则回流；RW-1～RW-6 对应 REVIEW_R2_RESULT.md 的返工项。
# 用法：bash openspec/annotation-community/review_r2_guard.sh
# 退出码 = 失败条数。只做存在性与结构判定，不代替语义复核。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 - "$DIR" <<'PY'
import re, sys, os

d = sys.argv[1]
read = lambda f: open(os.path.join(d, f), encoding="utf-8").read()
prd, design, plans, tasks = (read(f) for f in ("PRD.md", "DESIGN.md", "PLANS.md", "TASKS.md"))
fails = 0

def check(ok, name, detail=""):
    global fails
    if not ok:
        fails += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else f" — {detail}"))

def section(text, start_pat, end_pat):
    m = re.search(start_pat, text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    e = re.search(end_pat, rest, re.M)
    return rest[: e.start()] if e else rest

# R0：已废止规则不得回流到现行正文（历史审查记录不在扫描范围内）
banned = ["client_seq", "last_applied_seq", "取消即删除", "视为新请求", "冲突方一律失败", "sha256(event_id"]
hits = [f"{name}:{b}" for name, t in (("PRD", prd), ("DESIGN", design), ("PLANS", plans), ("TASKS", tasks))
        for b in banned if b in t]
check(not hits, "R0 四份正文无已废止规则", "; ".join(hits))

# RW-1：§7.2 为三个数组给出规范顺序，并写明数组换序对 hash 的期望
s72 = section(design, r"^### 7\.2 ", r"^### ")
order_line = next((l for l in s72.splitlines() if l.startswith("- 数组规范顺序：")), "")
has_all = all(k in order_line for k in ("attachment_refs", "mentions", "bindings"))
has_expect = re.search(r"数组换序[^。\n]*hash\s*(不变|改变)", s72) is not None
check(has_all and has_expect, "RW-1 §7.2 数组规范顺序与换序期望",
      f"规范顺序行={'有' if order_line else '无'}，三数组齐全={has_all}，换序期望={has_expect}")

# RW-2：change_summary 的来源有明确定义
check(re.search(r"change_summary[^。\n]*(用户填写|用户输入|系统生成|自动生成)", design) is not None,
      "RW-2 change_summary 来源已定义")

# RW-3：§2 模型表含 CommandRecord 与 NotifierDeliveryBinding，且 command_id 有格式定义
s2 = section(design, r"^## 2\. ", r"^### 2\.1 ")
rows = all(re.search(rf"^\| {k} \|", s2, re.M) for k in ("CommandRecord", "NotifierDeliveryBinding"))
fmt = re.search(r"command_id[^。\n]*(<32 hex>|UUIDv4|UUIDv7|ULID|格式)", design) is not None
check(rows and fmt, "RW-3 命令与传输桥接模型行及 command_id 格式", f"模型行={rows}，格式={fmt}")

# RW-4：NC-017 依赖 NC-009，且章节接入 §7.4
row17 = next((l for l in tasks.splitlines() if l.startswith("| NC-017 |")), "")
dep17 = "NC-009" in (row17.split("|")[3] if row17.count("|") > 4 else "")
sec17 = section(tasks, r"^### NC-017", r"^### ")
v16 = ("NC-015" in (row17.split("|")[3] if row17.count("|") > 4 else "")) and "导出" in sec17  # v1.6：NC-017 改为本机导出（FIX_V1_6）
check((dep17 and "§7.4" in sec17) or v16, "RW-4 NC-017 依赖 NC-009 并含命令恢复验收（v1.6 起：依赖 NC-015 且为导出文件）", f"依赖={dep17}，§7.4={'§7.4' in sec17}，v16={v16}")

# RW-5：NC-010 含客户端持久 command_id 验收
check("command_id" in section(tasks, r"^### NC-010", r"^### "), "RW-5 NC-010 含持久 command_id 验收")

# RW-6：NC-019 含 §7.4 命令恢复验收
check("§7.4" in section(tasks, r"^### NC-019", r"^## |^### "), "RW-6 NC-019 含命令恢复验收")

print(f"\n{'-'*44}\n失败条数：{fails}")
sys.exit(fails)
PY
