#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_outline.py —— 从 sections.yaml + transcript 自动生成 outline.yaml 与 batches.yaml
（HANDBOOK 4.1 结构盘点 / 4.3 批次账本的确定性实现）

用法：
    python3 tools/gen_outline.py corpus/bazi/qtbj_ed01

规则：
- 叶子节点 = level3 季节条目（三春甲木…）；无 level3 的 level1（五行总论/十干分论总述）也作叶子；
- 每叶子一个 batch，id_range 按顺序切 100 号一段；
- 字数由伪页正文块统计；全书页码连续即无缺口。
- 成本字段（token/人工分钟/返工轮）留空占位，跑完由账本回填（章程 G6）。
确定性：无时间戳、无随机，同输入同输出。
"""
import re
import sys
from pathlib import Path

import yaml


def main():
    corpus = Path(sys.argv[1])
    secs = yaml.safe_load((corpus / "source/sections.yaml").read_text())["sections"]
    txt = (corpus / "source/transcript_v1.md").read_text()
    parts = re.split(r"<!-- p(\d{4}) -->", txt)
    body_by_page = {}
    for i in range(1, len(parts), 2):
        body_by_page[int(parts[i])] = parts[i + 1]

    def chars(page):
        b = body_by_page.get(page, "")
        return len(re.sub(r"\s|#|[（）()]", "", b))

    sec_by_page = {s["page"]: s for s in secs}
    pages_with_l3_child = set()
    for s in secs:
        if s["level"] == 3:
            # 找它的父 level2、祖 level1 —— 标记祖先"有更深子节点"
            pages_with_l3_child.add(s["path"].split(" / ")[0])

    outline, batches = [], []
    n = 0
    for s in secs:
        is_leaf = s["level"] == 3 or (
            s["level"] == 1 and s["title"] not in
            {p.split(" / ")[0] for p in (x["path"] for x in secs) if " / " in p})
        if not is_leaf:
            continue
        n += 1
        nid = f"n{n:03d}"
        lo = 200 + (n - 1) * 100          # 号段从 ku_bazi_000200 起，每叶 100 号
        # 类型自动判定：路径含"总论"或无天干月令的总述节 = B 类论说散文；
        # 干×季条目（论X木/三春X木…）= C 类条目。防止总论被误当条目切成一大段。
        title_last = s["path"].split(" / ")[-1]
        is_prose = ("总论" in s["path"] or "总" in title_last
                    or not re.search(r"[甲乙丙丁戊己庚辛壬癸](?:木|火|土|金|水)", s["path"]))
        text_type = "B" if is_prose else "C"
        outline.append({
            "node_id": nid,
            "path": s["path"],
            "page": s["page"],
            "text_type": text_type,
            "est_chars": chars(s["page"]),
            "status": "pending",
        })
        batches.append({
            "batch_id": f"qtbj_b{n:03d}",
            "node_id": nid,
            "path": s["path"],
            "text_type": text_type,
            "task_dir": f"tasks/task_bazi_qtbj_b{n:03d}_seg",
            "id_range": [f"ku_bazi_{lo:06d}", f"ku_bazi_{lo + 99:06d}"],
            "stage_status": {"segmentation": "pending",
                             "concepts": "pending",
                             "assertions": "pending"},
            "cost": {"tokens_in": None, "tokens_out": None,
                     "human_minutes": None, "rework_rounds": None},
        })

    (corpus / "outline.yaml").write_text(
        yaml.dump({"work": "窮通寶鑑", "source_id": "src_qtbj_ed01",
                   "leaf_count": n, "total_chars": sum(o["est_chars"] for o in outline),
                   "outline": outline}, allow_unicode=True, sort_keys=False))
    (corpus / "batches.yaml").write_text(
        yaml.dump({"work": "窮通寶鑑", "source_id": "src_qtbj_ed01",
                   "batch_count": n, "batches": batches},
                  allow_unicode=True, sort_keys=False))
    print(f"完成：{n} 个叶子节点（batch），总 {sum(o['est_chars'] for o in outline)} 字")
    print(f"输出：{corpus}/outline.yaml ＋ batches.yaml")


if __name__ == "__main__":
    main()
