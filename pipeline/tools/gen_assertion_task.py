#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_assertion_task.py —— 为工位 5（主张提取）生成任务包
用法: python3 tools/gen_assertion_task.py corpus/bazi/qtbj_ed01 <round> <batch_id...>
产出 TASKS/task_<technique>_<book>_assert_<round>/：INSTRUCTIONS / input(segments+spans+glossary) / task.yaml
segments 带 case_candidate 标记（工位5据此排除命例）。确定性：同输入同输出。
骨架见 tools/lib/taskgen.py。
"""
import sys
from pathlib import Path

from lib.taskgen import DownstreamTaskSpec, build


def _seg(bid, span_id, seg_local, s):
    seg = {"seg_id": seg_local, "span_id": span_id,
           "entry_title": s.get("entry_title"),
           "case_candidate": bool(s.get("case_candidate")),
           "text": s["text"]}
    sp = {"seg_id": seg_local, "span_id": span_id, "batch": bid}
    return seg, sp


def main():
    corpus = Path(sys.argv[1])
    rnd = sys.argv[2]
    # 统计命例数用于完成语：包一层 seg_builder 累加
    ncase = {"n": 0}

    def seg(bid, span_id, seg_local, s):
        d, sp = _seg(bid, span_id, seg_local, s)
        if d["case_candidate"]:
            ncase["n"] += 1
        return d, sp

    def done(n_segs, n_batches, td_rel):
        return f"完成：{td_rel}  （{n_segs} 段，其中命例 {ncase['n']} 段待排除）"

    build(DownstreamTaskSpec(
        corpus=corpus,
        round_name=rnd,
        batch_ids=sys.argv[3:],
        stage="assertions",
        task_suffix="assert",
        template_stage_dir="stage5_assertions",
        instruction_version="assertions_bazi_v0.1",
        seg_builder=seg,
        emit_spans=True,
        extra_task_meta={"id_range": {"assertion": f"as_bazi (round {rnd})",
                                      "proposition": f"pr_bazi (round {rnd})"}},
        done_note=done,
    ))


if __name__ == "__main__":
    main()
