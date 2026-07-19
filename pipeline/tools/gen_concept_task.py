#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_concept_task.py —— 为工位 4（术语识别）放量批次生成任务包
（把切分产出 + 全局 span 对照 + v0 术语表快照打包，供 OpenCode 直接开跑）

用法：
    python3 tools/gen_concept_task.py corpus/bazi/qtbj_ed01 <round_name> <batch_id...>
    例：python3 tools/gen_concept_task.py corpus/bazi/qtbj_ed01 r1 qtbj_b001 qtbj_b005 qtbj_b006

产出 TASKS/task_bazi_qtbj_concepts_<round_name>/：
    INSTRUCTIONS.md            （八字工位4专用说明）
    input/segments.yaml        （本轮各批段落，seg_id 已换成全局 span_id）
    input/spans.yaml           （span 对照）
    input/glossary_v0.yaml     （已签发术语表快照，供闭集匹配，只提新词）
    task.yaml
确定性：同输入同输出。
"""
import shutil
import sys
from pathlib import Path

import yaml

PIPELINE = Path(__file__).resolve().parent.parent
TEMPLATE = PIPELINE / "task-templates/stage4_concepts_bazi/INSTRUCTIONS.md"
GLOSSARY = PIPELINE / "schemas/techniques/bazi/glossary_v0.yaml"


def main():
    corpus = Path(sys.argv[1])
    round_name = sys.argv[2]
    batch_ids = sys.argv[3:]

    spans_all = yaml.safe_load((corpus / "spans.yaml").read_text())["spans"]
    span_by = {(x["batch_id"], x["seg_id"]): x["span_id"] for x in spans_all}

    segs, sp = [], []
    for bid in batch_ids:
        draft = PIPELINE / f"TASKS/task_bazi_{bid}_seg/output/draft_opencode.yaml"
        data = yaml.safe_load(draft.read_text())
        for s in data["segments"]:
            span_id = span_by[(bid, s["seg_id"])]
            segs.append({"span_id": span_id, "entry_title": s.get("entry_title"),
                         "text": s["text"]})
            sp.append({"span_id": span_id, "batch": bid})

    task_dir = PIPELINE / f"TASKS/task_bazi_qtbj_concepts_{round_name}"
    (task_dir / "input").mkdir(parents=True, exist_ok=True)
    yaml.dump({"segments": segs}, open(task_dir / "input/segments.yaml", "w"),
              allow_unicode=True, sort_keys=False)
    yaml.dump({"spans": sp}, open(task_dir / "input/spans.yaml", "w"),
              allow_unicode=True, sort_keys=False)
    shutil.copy(TEMPLATE, task_dir / "INSTRUCTIONS.md")
    shutil.copy(GLOSSARY, task_dir / "input/glossary_v0.yaml")

    yaml.dump({"task_id": f"task_bazi_qtbj_concepts_{round_name}",
               "stage": "concept_candidates", "technique_id": "bazi",
               "source_id": "src_qtbj_ed01", "instruction_version": "concepts_bazi_v0.1",
               "covers_batches": batch_ids,
               "glossary_ref": "input/glossary_v0.yaml"},
              open(task_dir / "task.yaml", "w"), allow_unicode=True, sort_keys=False)
    print(f"完成：{task_dir.relative_to(PIPELINE)}  （{len(segs)} 段，{len(batch_ids)} 批）")


if __name__ == "__main__":
    main()
