#!/usr/bin/env bash
# 本线文档层总守卫：先回归 review_r3_guard.sh（其内含 R2 回归），再逐条检查 FIX_V1_4.md 的 18 项修复。
# 用法：bash openspec/annotation-community/review_final_guard.sh
# 退出码 = R2+R3 回归失败条数 + FIX 检查失败条数。只做存在性与结构判定。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== R2 + R3 回归 =="
bash "$DIR/review_r3_guard.sh"
prev=$?

echo
echo "== FIX_V1_4 十八项 =="
python3 - "$DIR" <<'PY'
import re, sys, os

d = sys.argv[1]
read = lambda f: open(os.path.join(d, f), encoding="utf-8").read()
prd, design, plans, tasks = (read(f) for f in ("PRD.md", "DESIGN.md", "PLANS.md", "TASKS.md"))
r1, checklist = read("REVIEW_R1.md"), read("REVIEW_R2_CHECKLIST.md")
four = {"PRD": prd, "DESIGN": design, "PLANS": plans, "TASKS": tasks}
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

def absent(texts, needles):
    return [f"{n}@{k}" for k, t in texts.items() for n in needles if n in t]

# FIX-01：DESIGN 禁止 Dart 直接 substring；NC-012 引用 code point
check("String.substring" in design and "markdown.substring(start" not in design
      and "code point" in section(tasks, r"^### NC-012"),
      "FIX-01 mention 偏移按 code point，旧 substring 写法已移除")

# FIX-02：summary_touched 规则与 NC-004 三条用例
nc004 = section(tasks, r"^### NC-004")
check("summary_touched" in design and "summary_touched" in nc004 and "不继承 X" in nc004,
      "FIX-02 修改说明会话初值与 summary_touched 用例")

# FIX-03：唯一命令队列所有权与依赖
nc010, nc011, nc012 = (section(tasks, rf"^### NC-01{i}") for i in (0, 1, 2))
dep011 = row(tasks, "NC-011").split("|")[3] if row(tasks, "NC-011") else ""
ok03 = ("command_queue.dart" in nc010 and "command_queue.dart" in nc011 and "command_queue.dart" in nc012
        and "NC-010" in dep011 and "report.create" in nc012
        and "| R-16 | NC-010, NC-011, NC-012, NC-014 |" in prd)
check(ok03, "FIX-03 客户端命令队列唯一且 NC-010/011/012 所有权明确", f"NC-011 依赖={dep011.strip()}")

# FIX-04：applied_version 空操作取值
check("不能以 0 冒充" not in design and "applied_version=0" in design, "FIX-04 applied_version 空操作取值已定义")

# FIX-05：重复项拒绝而非去重
check("完全相同项去重" not in design and "规范排序/去重" not in tasks and "重复项视为非法输入" in design,
      "FIX-05 重复项改为 Schema 拒绝")

# FIX-06：桥接文档 ID 为 SHA-256 hex
check("键为原始 notifier_delivery_id" not in design and "SHA256_hex(UTF8(notifier_delivery_id))" in design,
      "FIX-06 桥接记录文档 ID 为原值的 SHA-256 hex")

# FIX-07：dlv_ 前缀全部改为 ntf_
hits = absent({**four, "CHECKLIST": checklist}, ["dlv_"])
check(not hits and "`ntf_<32 hex>`" in design, "FIX-07 业务通知前缀改为 ntf_", "; ".join(hits))

# FIX-08：错误码命名
hits = absent({"DESIGN": design}, ["command.result_expired", "command.status_unavailable"])
check(not hits and "gone.command_result" in design and "unavailable.command_status" in design,
      "FIX-08 命令错误码符合 <类别>.<细节>", "; ".join(hits))

# FIX-09：§9.1 命令账本规模
check("| 命令账本规模 |" in section(design, r"^### 9\.1 "), "FIX-09 §9.1 含命令账本容量估算")

# FIX-10：R1 取代注记位于文件头部
check("不是现行规范" in "\n".join(r1.splitlines()[:12]), "FIX-10 REVIEW_R1 头部含取代注记")

# FIX-11：删除与 §6.2 矛盾的旧句
check("HTTP→Outcome" not in design, "FIX-11 ReceiptRejected 旧句已删除")

# FIX-12：REST 表补齐 purge 与 share.revoke
check(row(design, "content publish/update/withdraw/trash/restore/purge") != ""
      and "| share create/revoke/resolve" in design, "FIX-12 REST 表含 purge 与 share revoke")

# FIX-13：唯一键统一
hits = absent({"DESIGN": design, "TASKS": tasks}, ["操作域", "?operation="])
check(not hits and "(owner_scope, command_id) 唯一" in design, "FIX-13 命令唯一键为 (owner_scope, command_id)", "; ".join(hits))

# FIX-14：客户端待办与清理任务状态拆分
hits = absent(four, ["withdraw_pending", "trash_pending", "purge_failed", "pending_op=purge_pending"])
ok14 = (not hits and "purge_requested" in design and "queued / running / failed / succeeded" in design
        and "六台状态机" not in design and "九台状态机" in design and "九台状态机" in tasks
        and "PurgeTask.state=failed" in prd)
check(ok14, "FIX-14 pending_op 改 _requested 并新增清理任务状态机", "; ".join(hits))

# FIX-15：thread_closed
check("forbidden.thread_closed" in design and "forbidden.thread_closed" in nc011,
      "FIX-15 新增 forbidden.thread_closed 并进入 NC-011 用例")

# FIX-16：PLANS §8 指向总守卫
check("review_final_guard.sh" in section(plans, r"^## 8\. "), "FIX-16 PLANS §8 验收顺序指向总守卫")

# FIX-17：复核入口改指 v1.4 与总守卫
check("review_final_guard.sh" in checklist and "v1.3" not in checklist, "FIX-17 复核入口指向 v1.4 与总守卫")

# FIX-18：版本号与变更记录
heads = {k: "\n".join(t.splitlines()[:12]) for k, t in four.items()}
bad = [k for k, h in heads.items() if not re.search(r"版本：1\.[4-9]", h)]
check(not bad and "v1.4：落实 FIX_V1_4" in section(prd, r"^## 9\. "), "FIX-18 四份文档为 1.4 且 PRD §9 有记录", f"未升版={bad}")

print(f"\nFIX 失败条数：{fails}")
sys.exit(fails)
PY
fix=$?

total=$((prev + fix))
echo
echo "--------------------------------------------"
echo "合计失败条数：$total（R2+R3 回归 $prev，FIX $fix）"
exit "$total"
