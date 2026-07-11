#!/usr/bin/env python3
"""validate_assertion_task.py —— 主张任务包校验器"""

import re
import sys
from pathlib import Path

import yaml

PIPELINE_ROOT = Path(__file__).resolve().parent.parent

errors = []


def err(code, msg):
    errors.append(f"{code} | {msg}")


def main():
    if len(sys.argv) < 2:
        print("用法: python3 validators/validate_assertion_task.py <任务包目录>")
        sys.exit(1)

    task_dir = Path(sys.argv[1]).resolve()
    out_dir = task_dir / "output"
    inp_dir = task_dir / "input"

    # AST_001 双路件
    archive_dirs = sorted(
        [d for d in out_dir.iterdir() if d.is_dir()]
    )
    if len(archive_dirs) < 2:
        err("AST_001", f"output/ 下归档目录不足两个（当前 {len(archive_dirs)} 个）")

    by_names = set()
    for adir in archive_dirs:
        run_file = adir / "run.yaml"
        if run_file.exists():
            try:
                run = yaml.safe_load(run_file.read_text(encoding="utf-8"))
                by_names.add(run.get("model", ""))
            except Exception:
                pass
    if len(by_names) < 2:
        err("AST_001", f"不同 --by 的归档不足两个（当前: {by_names}）")

    review_file = out_dir / "review_compare.yaml"
    merged_file = out_dir / "merged_final.yaml"
    if not review_file.exists():
        err("AST_001", "缺少 review_compare.yaml")
    if not merged_file.exists():
        err("AST_001", "缺少 merged_final.yaml")

    # AST_002 状态越权（方向一）：单路 draft 里禁止出现 cross_model_reviewed 及更高状态
    # （该状态只能由双路比对/签发流程产生；M3 验收负例测试发现首版漏此方向，2026-07-11 补）
    FORBIDDEN_IN_DRAFT = {"cross_model_reviewed", "expert_verified"}
    for draft in sorted(out_dir.glob("draft_*.yaml")):
        try:
            dd = yaml.safe_load(draft.read_text(encoding="utf-8")) or {}
            for a in dd.get("assertions", []):
                if a.get("status") in FORBIDDEN_IN_DRAFT:
                    err("AST_002",
                        f"{draft.name} 中 {a.get('assertion_id')} 的 status 为 "
                        f"{a.get('status')}——单路输出只允许 machine_extracted（状态越权）")
        except Exception as e:
            err("AST_002", f"无法解析 {draft.name}: {e}")

    # AST_002 状态越权（方向二）：merged_final 中每条 status 为 cross_model_reviewed
    merged = {}
    try:
        merged = yaml.safe_load(merged_file.read_text(encoding="utf-8"))
        for a in merged.get("assertions", []):
            if a.get("status") != "cross_model_reviewed":
                err("AST_002",
                    f"merged_final 中 {a.get('assertion_id')} 的 status 为 {a.get('status')}，"
                    "应为 cross_model_reviewed（状态越权）")
    except Exception as e:
        err("AST_002", f"无法解析 merged_final.yaml: {e}")

    # 读输入 segments
    seg_file = inp_dir / "segments.yaml"
    if not seg_file.exists():
        err("AST_003", "input/segments.yaml 不存在")
        if errors:
            for e in errors:
                print(f"      {e}")
            sys.exit(1)

    seg_data = yaml.safe_load(seg_file.read_text(encoding="utf-8"))
    segments = seg_data.get("segments", [])
    all_seg_ids = {s["seg_id"] for s in segments}

    # AST_003 覆盖检查
    referenced_segs = set()
    skipped_raw = merged.get("skipped_segments", []) if isinstance(merged, dict) else []
    skipped_segs = set()
    for s in skipped_raw:
        if isinstance(s, dict):
            skipped_segs.add(s.get("seg_id", ""))
        elif isinstance(s, str):
            skipped_segs.add(s)

    assertions = merged.get("assertions", []) if isinstance(merged, dict) else []
    for a in assertions:
        for ev in a.get("evidence", []):
            span_id = ev.get("source_span_id", "")
            # 解析 seg suffix
            m = re.search(r"_s(\d+)$", span_id)
            if m:
                seg_suffix = f"s{int(m.group(1)):02d}"
                referenced_segs.add(seg_suffix)

    # AST_004 越界引用
    input_seg_range = {s["seg_id"] for s in segments}
    for a in assertions:
        for ev in a.get("evidence", []):
            span_id = ev.get("source_span_id", "")
            m = re.search(r"_s(\d+)$", span_id)
            if m:
                seg_suffix = f"s{int(m.group(1)):02d}"
                if seg_suffix not in input_seg_range:
                    err("AST_004",
                        f"{a.get('assertion_id')} 引用了 {span_id}，"
                        f"其段号 {seg_suffix} 不在输入 segments 范围内")

    # Check coverage
    for sid in sorted(all_seg_ids):
        if sid not in referenced_segs and sid not in skipped_segs:
            err("AST_003",
                f"段 {sid} 未被任何 assertion 引用，也不在 skipped_segments 中（覆盖缺口）")

    # AST_005 括号段处理
    ed_notes_file = inp_dir / "editorial_notes.yaml"
    if ed_notes_file.exists():
        try:
            ed = yaml.safe_load(ed_notes_file.read_text(encoding="utf-8"))
            bracket_segs = set()
            if ed and isinstance(ed, dict):
                for bn in ed.get("bracket_nodes", []):
                    if isinstance(bn, dict):
                        bracket_segs.add(bn.get("seg_id", ""))
                    elif isinstance(bn, str):
                        bracket_segs.add(bn)
            for bs in bracket_segs:
                covered = any(
                    bs in a.get("conditions", [])
                    for a in assertions
                )
                if not covered and bs not in skipped_segs:
                    err("AST_005",
                        f"含编者标记的段 {bs} 未被 assertion conditions 处理，"
                        "也不在 skipped_segments 中")
        except Exception as e:
            err("AST_005", f"无法解析 editorial_notes.yaml: {e}")

    if errors:
        print(f"FAIL  {task_dir.name}  （{len(errors)} 条错误）")
        for e in errors:
            print(f"      {e}")
        sys.exit(1)
    print(f"PASS  {task_dir.name}  （{len(assertions)} 条主张，覆盖 {len(referenced_segs)}/{len(all_seg_ids)} 段）")
    sys.exit(0)


if __name__ == "__main__":
    main()
