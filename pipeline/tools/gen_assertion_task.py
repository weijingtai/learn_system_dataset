#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_assertion_task.py —— 为工位 5（主张提取）生成任务包（八字）
用法: python3 tools/gen_assertion_task.py corpus/bazi/qtbj_ed01 <round> <batch_id...>
产出 TASKS/task_bazi_qtbj_assert_<round>/：INSTRUCTIONS / input(segments+spans+glossary) / task.yaml
segments 带 case_candidate 标记（工位5据此排除命例）。确定性：同输入同输出。
"""
import shutil
import sys
from pathlib import Path

import yaml

PIPELINE = Path(__file__).resolve().parent.parent
TEMPLATE = PIPELINE / "task-templates/stage5_assertions_bazi/INSTRUCTIONS.md"
GLOSSARY = PIPELINE / "schemas/techniques/bazi/glossary_v0.yaml"


def main():
    corpus = Path(sys.argv[1])
    rnd = sys.argv[2]
    batch_ids = sys.argv[3:]
    spans_all = yaml.safe_load((corpus / "spans.yaml").read_text())["spans"]
    span_by = {(x["batch_id"], x["seg_id"]): x["span_id"] for x in spans_all}

    segs, sp = [], []
    for bid in batch_ids:
        draft = PIPELINE / f"TASKS/task_bazi_{bid}_seg/output/draft_opencode.yaml"
        data = yaml.safe_load(draft.read_text())
        for s in data["segments"]:
            span_id = span_by[(bid, s["seg_id"])]
            # seg_id 用全局 span 的尾段号，保持与校验器 _sNN 解析一致
            seg_local = span_id.split("_")[-1]
            segs.append({"seg_id": seg_local, "span_id": span_id,
                         "entry_title": s.get("entry_title"),
                         "case_candidate": bool(s.get("case_candidate")),
                         "text": s["text"]})
            sp.append({"seg_id": seg_local, "span_id": span_id, "batch": bid})

    td = PIPELINE / f"TASKS/task_bazi_qtbj_assert_{rnd}"
    (td / "input").mkdir(parents=True, exist_ok=True)
    yaml.dump({"segments": segs}, open(td / "input/segments.yaml", "w"),
              allow_unicode=True, sort_keys=False)
    yaml.dump({"spans": sp}, open(td / "input/spans.yaml", "w"),
              allow_unicode=True, sort_keys=False)
    shutil.copy(TEMPLATE, td / "INSTRUCTIONS.md")
    shutil.copy(GLOSSARY, td / "input/glossary_v0.yaml")
    ncase = sum(1 for s in segs if s["case_candidate"])
    yaml.dump({"task_id": f"task_bazi_qtbj_assert_{rnd}", "stage": "assertions",
               "technique_id": "bazi", "source_id": "src_qtbj_ed01",
               "instruction_version": "assertions_bazi_v0.1",
               "covers_batches": batch_ids,
               "id_range": {"assertion": f"as_bazi (round {rnd})",
                            "proposition": f"pr_bazi (round {rnd})"}},
              open(td / "task.yaml", "w"), allow_unicode=True, sort_keys=False)
    print(f"完成：{td.relative_to(PIPELINE)}  （{len(segs)} 段，其中命例 {ncase} 段待排除）")


if __name__ == "__main__":
    main()
