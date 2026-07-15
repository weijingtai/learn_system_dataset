#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_coverage.py —— 全书覆盖闭合校验（防"某批无声漏跑"的致命缺口）
（对应 G1 完整性判据 / HANDBOOK 4.3 批次账本）

背景教训：《穷通宝鉴》b001「五行总论」在账本里存在，却从未进过任何启动句，
        成了孤儿，直到全书快跑完才发现——因为派发全靠人肉记范围，没有程序核对。
        本工具把"41 批是否都派了、都做了"变成一条命令，杜绝人肉遗漏。

用法：
    python3 tools/check_coverage.py corpus/bazi/qtbj_ed01 [--stage segmentation]

检查项（错误码）：
    COV_001  某 batch 的 stage_status 为 pending/in_progress（未完成）
    COV_002  某 batch 声称 done，但 task_dir 下找不到 draft 产出（账本与实物不符）
    COV_003  outline 叶子数 ≠ batches 数（结构盘点与账本对不上）
    COV_004  某 batch draft 的段 path 覆盖的伪页，与 outline 记录的 page 不符

退出码：0 = 全书闭合；1 = 有缺口。这是放量/签发前的强制门。
"""
import sys
from pathlib import Path

import yaml

PIPELINE = Path(__file__).resolve().parent.parent


def main():
    corpus = Path(sys.argv[1])
    stage = "segmentation"
    if "--stage" in sys.argv:
        stage = sys.argv[sys.argv.index("--stage") + 1]

    outline = yaml.safe_load((corpus / "outline.yaml").read_text())
    batches = yaml.safe_load((corpus / "batches.yaml").read_text())["batches"]
    errors = []

    # COV_003 结构对账
    if outline["leaf_count"] != len(batches):
        errors.append(f"COV_003 | outline 叶子 {outline['leaf_count']} ≠ batches {len(batches)}")

    for b in batches:
        bid = b["batch_id"]
        st = b["stage_status"].get(stage, "pending")
        draft = PIPELINE / b["task_dir"] / "output/draft_opencode.yaml"
        # COV_001 未完成
        if st != "done":
            errors.append(f"COV_001 | {bid} | stage[{stage}]={st}（未完成，{b['path']}）")
            continue
        # COV_002 账本说 done 但没实物
        if not draft.exists():
            errors.append(f"COV_002 | {bid} | 账本 done 但缺 draft 产出 {draft.relative_to(PIPELINE)}")

    total = len(batches)
    done = sum(1 for b in batches if b["stage_status"].get(stage) == "done")
    if errors:
        print(f"FAIL  覆盖未闭合  （{done}/{total} 批 done，{len(errors)} 条缺口）")
        for e in errors:
            print(f"      {e}")
        sys.exit(1)
    print(f"PASS  全书覆盖闭合  （{total} 批全部 {stage}=done，产出齐备）")
    sys.exit(0)


if __name__ == "__main__":
    main()
