#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_paraphrase_task.py —— 为工位 6（白话释义）生成任务包
用法: python3 tools/gen_paraphrase_task.py corpus/bazi/qtbj_ed01 <round> <batch_id...>
产出 TASKS/task_<technique>_<book>_para_<round>/：INSTRUCTIONS / input(segments+glossary) / task.yaml
工位6只做直译，全段翻译，无需 case_candidate 分离。确定性：同输入同输出。
骨架见 tools/lib/taskgen.py。"""
import sys
from pathlib import Path

from lib.taskgen import DownstreamTaskSpec, build


def _seg(bid, span_id, seg_local, s):
    seg = {"seg_id": seg_local, "span_id": span_id,
           "entry_title": s.get("entry_title"), "text": s["text"]}
    return seg, None


def _done(n_segs, n_batches, td_rel):
    return f"完成：{td_rel}  （{n_segs} 段待译）"


def make_spec(corpus, round_name, batch_ids):
    return DownstreamTaskSpec(
        corpus=Path(corpus),
        round_name=round_name,
        batch_ids=batch_ids,
        stage="paraphrase",
        task_suffix="para",
        template_stage_dir="stage6_paraphrase",
        instruction_version="paraphrase_bazi_v0.1",
        seg_builder=_seg,
        emit_spans=False,
        done_note=_done,
    )


def main():
    build(make_spec(sys.argv[1], sys.argv[2], sys.argv[3:]))


if __name__ == "__main__":
    main()
