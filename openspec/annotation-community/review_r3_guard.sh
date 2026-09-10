#!/usr/bin/env bash
# R3 复核守卫：先回归 review_r2_guard.sh，再检查 REVIEW_R3_RESULT.md §4 的 RW3-1～RW3-3。
# 用法：bash openspec/annotation-community/review_r3_guard.sh
# 退出码 = R2 回归失败条数 + R3 失败条数。只做存在性与结构判定，不代替语义复核。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== R2 回归 =="
bash "$DIR/review_r2_guard.sh"
r2=$?

echo
echo "== R3 返工项 =="
python3 - "$DIR" <<'PY'
import re, sys, os

d = sys.argv[1]
read = lambda f: open(os.path.join(d, f), encoding="utf-8").read()
design, tasks = read("DESIGN.md"), read("TASKS.md")
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

def same_sentence(text, a, b):
    """a 与 b 出现在同一句（不跨句号与换行）。"""
    return re.search(rf"{a}[^。\n]*{b}|{b}[^。\n]*{a}", text) is not None

# RW3-1：mention 偏移单位定义为 code point，NC-002 有补充平面字符用例
unit = same_sentence(design, "start_offset", r"(code point|码点)")
nc002 = section(tasks, r"^### NC-002")
fixture = any(re.search(r"mention", l) and re.search(r"(补充平面|4 字节)", l) for l in nc002.splitlines())
check(unit and fixture, "RW3-1 mention 偏移单位与补充平面字符 fixture", f"单位定义={unit}，NC-002 用例={fixture}")

# RW3-2：change_summary 会话初值已定义，且有「改回原文」去重用例
init = same_sentence(design, "change_summary", r"(初值|会话开始)")
revert = "改回" in nc002 or "改回" in section(tasks, r"^### NC-004")
check(init and revert, "RW3-2 change_summary 会话初值与改回原文用例", f"初值规则={init}，改回用例={revert}")

# RW3-3：客户端 comment.create 恢复验收有具名所有者
owner = "comment.create" in section(tasks, r"^### NC-010") or "comment.create" in section(tasks, r"^### NC-011")
check(owner, "RW3-3 客户端 comment.create 命令恢复有具名所有者")

print(f"\nR3 失败条数：{fails}")
sys.exit(fails)
PY
r3=$?

total=$((r2 + r3))
echo
echo "--------------------------------------------"
echo "合计失败条数：$total（R2 回归 $r2，R3 $r3）"
exit "$total"
