#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_concept_task.py —— 为工位 4（术语识别）放量批次生成任务包
（把切分产出 + 全局 span 对照 + v0 术语表快照打包，供 OpenCode 直接开跑）

用法：
    python3 tools/gen_concept_task.py corpus/bazi/qtbj_ed01 <round_name> <batch_id...>
    例：python3 tools/gen_concept_task.py corpus/bazi/qtbj_ed01 r1 qtbj_b001 qtbj_b005 qtbj_b006

产出 TASKS/task_<technique>_<book>_concepts_<round_name>/：
    INSTRUCTIONS.md            （工位4专用说明）
    input/segments.yaml        （本轮各批段落，seg_id 已换成全局 span_id）
    input/spans.yaml           （span 对照）
    input/glossary_v0.yaml     （已签发术语表快照，供闭集匹配，只提新词）
    task.yaml
确定性：同输入同输出。骨架见 tools/lib/taskgen.py。
"""
import sys
from pathlib import Path

from lib.taskgen import PIPELINE, DownstreamTaskSpec, build


def _seg(bid, span_id, seg_local, s):
    seg = {"span_id": span_id, "entry_title": s.get("entry_title"), "text": s["text"]}
    sp = {"span_id": span_id, "batch": bid}
    return seg, sp


def main():
    corpus = Path(sys.argv[1])
    build(DownstreamTaskSpec(
        corpus=corpus,
        round_name=sys.argv[2],
        batch_ids=sys.argv[3:],
        stage="concept_candidates",
        task_suffix="concepts",
        template=PIPELINE / "task-templates/stage4_concepts_bazi/INSTRUCTIONS.md",
        glossary=PIPELINE / "schemas/techniques/bazi/glossary_v0.yaml",
        instruction_version="concepts_bazi_v0.1",
        seg_builder=_seg,
        emit_spans=True,
        extra_task_meta={"glossary_ref": "input/glossary_v0.yaml"},
    ))


if __name__ == "__main__":
    main()
