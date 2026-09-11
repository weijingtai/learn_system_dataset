#!/usr/bin/env bash
# v1.6 守卫：先回归 review_v1_5_guard.sh（其内含 final/R2/R3 回归），再检查 FIX_V1_6 的 S6 模型修订。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LC_ALL=C bash "$DIR/review_v1_5_guard.sh" >/dev/null 2>&1; g=$?
python3 - "$DIR" "$g" <<'PY'
import re, sys
from pathlib import Path
d=Path(sys.argv[1]); g=int(sys.argv[2]); fails=0
def check(ok,name,detail=""):
    global fails
    if not ok: fails+=1
    print(("PASS  " if ok else "FAIL  ")+name+("" if ok or not detail else f" — {detail}"))
def read(p): return (d/p).read_text(encoding="utf-8")
def section(t,a,b):
    m=re.search(a,t,re.M); 
    if not m: return ""
    rest=t[m.end():]; n=re.search(b,rest,re.M); return rest[:n.start()] if n else rest
check(g==0,"V16-00 回归：review_v1_5_guard.sh 为 0",str(g))
prd,design,plans,tasks=read("PRD.md"),read("DESIGN.md"),read("PLANS.md"),read("TASKS.md")
heads={k:"\n".join(t.splitlines()[:12]) for k,t in (("PRD",prd),("DESIGN",design),("PLANS",plans),("TASKS",tasks))}
check(all("版本：1.6" in h for h in heads.values()),"V16-01 四份文档版本为 1.6",str([k for k,h in heads.items() if "版本：1.6" not in h]))
check("| R-13 | 手动导出与导入 |" in prd and "S6 D13" in prd,"V16-02 PRD R-13 改为手动导出与导入并明示 D13")
body=prd.split("## 9. ")[0]
body=body.replace("无恢复材料","").replace("不存在恢复材料","").replace("恢复材料重建证据","")
check("恢复材料" not in body and "云备份" not in body,"V16-03 PRD 正文（§9 以外）不再出现恢复材料/云备份",f"恢复材料={body.count('恢复材料')} 云备份={body.count('云备份')}")
check("| 导出备份 | 未导出 / 导出中(x%) / 已导出至 <时间> / 有 N 处新修订未导出 / 导出失败 |" in prd,"V16-04 PRD §6.1 第三维度为导出备份五值")
check("7. 首次导出备份" in prd and "8. 在另一台设备导入" in prd,"V16-05 旅程 7/8 重写")
d5=section(design,r"^## 5\. ",r"^## ")
check("一次一密" in d5 and "X25519" in d5 and "D13" in d5 and "云备份" not in d5,"V16-06 DESIGN §5 为 S6 模型且无云备份")
check("v1.6 保留为枚举值" in design and "保留为枚举值不实现" in design,"V16-07 DESIGN backup.* 保留枚举值")
n15=section(tasks,r"^### NC-015",r"^### "); n17=section(tasks,r"^### NC-017",r"^### "); n18=section(tasks,r"^### NC-018",r"^### ")
check("2026-08-02-s6-p2p-sync-third-party-design.md" in n15 and "X25519" in n15 and "不重写密码学" in n15,"V16-08 TASKS NC-015 为接入型并引用 S6 设计稿")
check("| NC-017 | 口令加密导出文件格式与本机写入 | NC-004, NC-015 |" in tasks and "口令" in n17 and "原始字节" in n17,"V16-09 TASKS NC-017 为导出文件格式")
check("| NC-018 | 导出/导入 UI 与验证 | NC-016, NC-017 |" in tasks and "CloudBackupStatus" in n18,"V16-10 TASKS NC-018 为导出/导入 UI 且迁移 CloudBackupStatus")
check("NC-003 → NC-013 → NC-021 → NC-026" in plans and "NC-013 → NC-017" not in plans,"V16-11 PLANS 串行链已去掉 NC-017")
check("v1.6：backup.* 三个值保留为枚举值" in read("contracts/community-models.md") and "v1.6（2026-09-11）" in read("contracts/editor.md"),"V16-12 契约备注（community-models、editor.md）")
check("| 2026-09-11 | v1.6：" in prd and (d/"FIX_V1_6.md").is_file() and "V16-07" in read("FIX_V1_6.md"),"V16-13 PRD §9 登记 v1.6 且 FIX_V1_6 存在")
print(f"\nv1.6 失败条数：{fails}"); sys.exit(fails)
PY
