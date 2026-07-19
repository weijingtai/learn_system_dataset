#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_task.py —— 从 batches.yaml 为指定 batch 生成切分任务包
（HANDBOOK 4.2 分批规则的确定性实现，供 OpenCode 直接开跑）

用法：
    python3 tools/gen_task.py corpus/bazi/qtbj_ed01 qtbj_b002

产出 TASKS/task_bazi_qtbj_b002_seg/：
    INSTRUCTIONS.md              （软链/复制自 task-templates/stage3c_segmentation_C）
    input/text.md                （本 batch 叶子节点的正文，逐字取自 transcript）
    input/path.txt               （卷章路径）
    input/context_before.md      （上一伪页末约 200 字，仅供理解指代）
    task.yaml                    （审计元数据）
确定性：同输入同输出，无时间戳。
"""
import re
import shutil
import sys
from pathlib import Path

import yaml

PIPELINE = Path(__file__).resolve().parent.parent
TEMPLATE = PIPELINE / "task-templates/stage3c_segmentation_C/INSTRUCTIONS.md"


def page_body(txt, page):
    parts = re.split(r"<!-- p(\d{4}) -->", txt)
    for i in range(1, len(parts), 2):
        if int(parts[i]) == page:
            return parts[i + 1].strip()
    return ""


def main():
    corpus = Path(sys.argv[1])
    batch_id = sys.argv[2]
    batches = yaml.safe_load((corpus / "batches.yaml").read_text())["batches"]
    b = next(x for x in batches if x["batch_id"] == batch_id)

    txt = (corpus / "source/transcript_v1.md").read_text()
    outline = yaml.safe_load((corpus / "outline.yaml").read_text())["outline"]
    node = next(o for o in outline if o["node_id"] == b["node_id"])
    page = node["page"]

    body = page_body(txt, page)
    # 上一伪页末 200 字作为 context_before
    prev = page_body(txt, page - 1) if page > 1 else ""
    context_before = prev[-200:] if prev else "（本批为全书起始，无前文）"

    task_dir = PIPELINE / b["task_dir"]
    (task_dir / "input").mkdir(parents=True, exist_ok=True)
    (task_dir / "input/text.md").write_text(body + "\n", encoding="utf-8")
    (task_dir / "input/path.txt").write_text(node["path"] + "\n", encoding="utf-8")
    (task_dir / "input/context_before.md").write_text(
        context_before + "\n", encoding="utf-8")
    shutil.copy(TEMPLATE, task_dir / "INSTRUCTIONS.md")

    task_meta = {
        "task_id": f"task_bazi_{batch_id}_seg",
        "stage": "segmentation",
        "text_type": "C",
        "source_snapshot": str(corpus / "source/transcript_v1.md"),
        "source_id": "src_qtbj_ed01",
        "batch_id": batch_id,
        "node_id": b["node_id"],
        "path": node["path"],
        "id_range": b["id_range"],
        "instruction_version": "seg_C_v0.1",
    }
    (task_dir / "task.yaml").write_text(
        yaml.dump(task_meta, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"完成：{task_dir.relative_to(PIPELINE)}  （{len(body)} 字，path={node['path']}）")


if __name__ == "__main__":
    main()
