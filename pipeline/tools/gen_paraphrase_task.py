#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_paraphrase_task.py —— 为工位 6（白话释义）生成任务包（八字）
用法: python3 tools/gen_paraphrase_task.py corpus/bazi/qtbj_ed01 <round> <batch_id...>
产出 TASKS/task_bazi_qtbj_para_<round>/：INSTRUCTIONS / input(segments+glossary) / task.yaml
工位6只做直译，全段翻译，无需 case_candidate 分离。确定性：同输入同输出。"""
import shutil
import sys
from pathlib import Path

import yaml

PIPELINE = Path(__file__).resolve().parent.parent
TEMPLATE = PIPELINE / "task-templates/stage6_paraphrase_bazi/INSTRUCTIONS.md"
GLOSSARY = PIPELINE / "schemas/techniques/bazi/glossary_v0.yaml"


def main():
    corpus = Path(sys.argv[1])
    rnd = sys.argv[2]
    batch_ids = sys.argv[3:]
    spans_all = yaml.safe_load((corpus / "spans.yaml").read_text())["spans"]
    span_by = {(x["batch_id"], x["seg_id"]): x["span_id"] for x in spans_all}

    segs = []
    for bid in batch_ids:
        draft = PIPELINE / f"TASKS/task_bazi_{bid}_seg/output/draft_opencode.yaml"
        data = yaml.safe_load(draft.read_text())
        for s in data["segments"]:
            span_id = span_by[(bid, s["seg_id"])]
            segs.append({"seg_id": span_id.split("_")[-1], "span_id": span_id,
                         "entry_title": s.get("entry_title"), "text": s["text"]})

    td = PIPELINE / f"TASKS/task_bazi_qtbj_para_{rnd}"
    (td / "input").mkdir(parents=True, exist_ok=True)
    yaml.dump({"segments": segs}, open(td / "input/segments.yaml", "w"),
              allow_unicode=True, sort_keys=False)
    shutil.copy(TEMPLATE, td / "INSTRUCTIONS.md")
    shutil.copy(GLOSSARY, td / "input/glossary_v0.yaml")
    yaml.dump({"task_id": f"task_bazi_qtbj_para_{rnd}", "stage": "paraphrase",
               "technique_id": "bazi", "source_id": "src_qtbj_ed01",
               "instruction_version": "paraphrase_bazi_v0.1",
               "covers_batches": batch_ids},
              open(td / "task.yaml", "w"), allow_unicode=True, sort_keys=False)
    print(f"完成：{td.relative_to(PIPELINE)}  （{len(segs)} 段待译）")


if __name__ == "__main__":
    main()
