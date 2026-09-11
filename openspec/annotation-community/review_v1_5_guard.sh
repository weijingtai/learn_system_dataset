#!/usr/bin/env bash
# v1.5 守卫：先回归 review_final_guard.sh（其内含 R2、R3 回归），再检查 FIX_V1_5.md 的行为事件数据源修订。
# 用法：bash openspec/annotation-community/review_v1_5_guard.sh
# 退出码 = 既有回归失败条数 + V 检查失败条数。只做存在性与结构判定，不代替语义复核。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== v1.4 及以前的回归 =="
bash "$DIR/review_final_guard.sh"
prev=$?

echo
echo "== FIX_V1_5 行为事件数据源 =="
python3 - "$DIR" <<'PY'
import re, sys, os

d = sys.argv[1]
read = lambda f: open(os.path.join(d, f), encoding="utf-8").read()
prd, design, plans, tasks = (read(f) for f in ("PRD.md", "DESIGN.md", "PLANS.md", "TASKS.md"))
checklist, fix4, verify = read("REVIEW_R2_CHECKLIST.md"), read("FIX_V1_4.md"), read("verify.sh")
todo = read(os.path.join("..", "..", "docs", "blackbox-spec-rework", "SUBAGENT_TODO.md"))
fails = 0

def check(ok, name, detail=""):
    global fails
    if not ok:
        fails += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or not detail else f" — {detail}"))

def section(text, start_pat, end_pat=r"^#{2,3} "):
    m = re.search(start_pat, text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    e = re.search(end_pat, rest, re.M)
    return rest[: e.start()] if e else rest

def row(text, key):
    return next((l for l in text.splitlines() if l.startswith(f"| {key} |")), "")

# V01：R-21 进入 PRD 需求表与断言点索引，verify.sh 接受 R-21
check("| R-21 | 行为事件数据源 |" in prd and "| R-21 | NC-026 |" in prd and "range(1, 22)" in verify,
      "V01 R-21 已登记且 verify.sh 接受 R-01～R-21")

# V02：DESIGN §11 的关键规则
s11 = section(design, r"^## 11\. 行为事件数据源", r"^## ")
need = ["只追加", "`psn_", "禁止由账号 ID", "已注销用户", "SHA256_hex(E([owner_scope, command_id, event_type]))", "不设 TTL", "原始字节"]
miss = [k for k in need if k not in s11]
check(s11 != "" and not miss, "V02 DESIGN §11 含只追加、随机假名、注销去标识化、事件 ID 派生与永久保留", f"缺 {miss}")

# V03：模型表、前缀表与对象计数
ok03 = ("| BehaviorEvent |" in section(design, r"^## 2\. ", r"^### 2\.1 ")
        and "| PseudonymMapping |" in section(design, r"^## 2\. ", r"^### 2\.1 ")
        and "`bev_<32 hex>`" in design and "`psn_<32 hex>`" in design and "本期新增 17 类对象" in design)
check(ok03, "V03 §2 模型行、§2.1 前缀行与 17 类计数")

# V04：服务端事件与业务同事务
check("隐含命令账本终态写入与行为事件追加" in design and "命令结果、行为事件同事务" in design,
      "V04 §4.3 与 §7.4 声明行为事件与业务同事务")

# V05：NC-026 登记、依赖与 NC-024 覆盖 R-21
r26 = row(tasks, "NC-026")
dep26 = r26.split("|")[3] if r26.count("|") > 4 else ""
r24 = row(tasks, "NC-024")
ok05 = (all(x in dep26 for x in ("NC-002", "NC-003", "NC-005", "NC-009")) and re.search(r"^### NC-026：", tasks, re.M)
        and "NC-026" in r24 and "R-01～R-21" in r24 and "R-01～R-20" not in tasks)
check(bool(ok05), "V05 NC-026 已登记、依赖齐全，NC-024 覆盖 R-01～R-21", f"NC-026 依赖={dep26.strip()}")

# V06：NC-026 的关键验收点
s26 = section(tasks, r"^### NC-026：", r"^#{2,3} ")
need = ["原始字节", "dropped_before", "update 与 delete", "account_id", "注入", "code point"]
miss = [k for k in need if k not in s26]
check(not miss, "V06 NC-026 含原始字节、离线丢弃计数、只追加、注销扫描、故障注入、code point 验收", f"缺 {miss}")

# V07：FIX_V1_4 §4 标记为已决定
check("已决定：维持永久保留" in fix4, "V07 FIX_V1_4 §4 已标记用户决定")

# V08：PRD §9 登记 v1.5 与三项决策
s9 = section(prd, r"^## 9\. ", r"^## ")
need = ["v1.5：新增 R-21", "决策：命令账本维持永久保留", "决策：私人笔记默认上报", "决策：账号注销或彻底删除时删除假名映射"]
miss = [k for k in need if k not in s9]
check(not miss, "V08 PRD §9 登记 v1.5 与三项用户决策", f"缺 {miss}")

# V09：四份文档升版到 1.5
heads = {k: "\n".join(t.splitlines()[:12]) for k, t in (("PRD", prd), ("DESIGN", design), ("PLANS", plans), ("TASKS", tasks))}
bad = [k for k, h in heads.items() if not re.search(r"版本：1\.[5-9]", h)]  # v1.6 起放宽（FIX_V1_6）
check(not bad, "V09 四份文档版本为 1.5", f"未升版={bad}")

# V10：PLANS 阶段、串行顺序、验收入口与复核清单
ok10 = ("| P2 媒体与公开社交 | NC-025, NC-008～012, NC-026 |" in plans and "NC-021 → NC-026" in plans
        and "review_v1_5_guard.sh" in section(plans, r"^## 8\. ", r"^## ")
        and "review_v1_5_guard.sh" in checklist and "v1.5" in checklist)
check(ok10, "V10 PLANS 阶段与串行顺序含 NC-026，验收入口与清单指向 v1.5 守卫")

# V11：唯一监控表登记
check("NC-026：行为事件数据源" in todo and "R-01～R-21 全部在" in todo, "V11 SUBAGENT_TODO 登记 NC-026 且总验收覆盖 R-21")

# V12：注销事件作为外部依赖由 NC-001 登记
check("账号注销" in section(design, r"^## 10\. ", r"^## ") and "上述十项" in tasks and "⑩" in section(tasks, r"^### NC-001"),
      "V12 §10 登记注销事件依赖，NC-001 必填项增至十项")

# V13：§9.1 行为事件规模
check("| 行为事件规模 |" in section(design, r"^### 9\.1 "), "V13 §9.1 含行为事件容量估算")

# V14：PRD §7 划清本期范围
check("行为事件的采集与保存属于本期" in prd, "V14 PRD §7 写明采集保存属本期、分析不属本期")

print(f"\nV 失败条数：{fails}")
sys.exit(fails)
PY
v=$?

total=$((prev + v))
echo
echo "--------------------------------------------"
echo "合计失败条数：$total（既有回归 $prev，V $v）"
exit "$total"
