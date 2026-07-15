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

    # --single <draft文件名>：单路模式（2026-07-14 决策后默认流程）。
    # 以该 draft 为提取源，跳过双路专属检查（两路件/merged 状态）。
    # 不加则走双路模式（保留，供抽检背书批次用）。
    args = sys.argv[1:]
    single_draft = None
    if "--single" in args:
        i = args.index("--single")
        single_draft = args[i + 1] if i + 1 < len(args) else "authoritative.yaml"
        args = args[:i] + args[i + 2:]
    task_dir = Path(args[0]).resolve()
    out_dir = task_dir / "output"
    inp_dir = task_dir / "input"

    if single_draft:
        # 单路：提取源 = 指定 draft；不要求两路件/merged_final
        src_file = out_dir / single_draft
        if not src_file.exists():
            err("AST_001", f"单路模式指定的 {single_draft} 不存在")
            merged = {}
        else:
            merged = yaml.safe_load(src_file.read_text(encoding="utf-8")) or {}
            # 单路 draft 只允许 machine_extracted
            for a in merged.get("assertions", []):
                if a.get("status") in {"cross_model_reviewed", "expert_verified"}:
                    err("AST_002",
                        f"{single_draft} 中 {a.get('assertion_id')} 的 status 为 "
                        f"{a.get('status')}——单路输出只允许 machine_extracted（状态越权）")
    else:
        # AST_001 双路件
        archive_dirs = sorted([d for d in out_dir.iterdir() if d.is_dir()])
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

        # AST_002 状态越权（方向一）：单路 draft 里禁止 cross_model_reviewed 及更高
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
    # 以完整 span_id 为唯一键（seg_id 尾号跨页碰撞，不可用作比对键；2026-07-14 修）
    all_span_ids = {s["span_id"] for s in segments}
    # seg_id -> span_id（skipped_segments 可能用任一种，两头都收）
    segid_to_span = {}
    for s in segments:
        segid_to_span.setdefault(s["seg_id"], set()).add(s["span_id"])

    def norm_skip(val):
        """把 skipped 项归一到 span_id 集合（接受 span_id 或唯一的 seg_id）"""
        if val in all_span_ids:
            return {val}
        return segid_to_span.get(val, set())

    # AST_003 覆盖检查（按 span_id）
    referenced_spans = set()
    skipped_raw = merged.get("skipped_segments", []) if isinstance(merged, dict) else []
    skipped_spans = set()
    for s in skipped_raw:
        if isinstance(s, dict):
            # 各写法都收：seg_span_id / span_id 是完整 span，seg_id 是局部键，
            # 取所有能解析出 span 的键（字段名历史上不统一，2026-07-14 补 seg_span_id）
            for k in (s.get("seg_span_id"), s.get("span_id"), s.get("seg_id")):
                if k:
                    skipped_spans |= norm_skip(k)
        else:
            skipped_spans |= norm_skip(s)

    assertions = merged.get("assertions", []) if isinstance(merged, dict) else []
    for a in assertions:
        for ev in a.get("evidence", []):
            span_id = ev.get("source_span_id", "")
            if span_id:
                referenced_spans.add(span_id)

    # AST_004 越界引用（按完整 span_id）
    for a in assertions:
        for ev in a.get("evidence", []):
            span_id = ev.get("source_span_id", "")
            if span_id and span_id not in all_span_ids:
                err("AST_004",
                    f"{a.get('assertion_id')} 引用了 {span_id}，不在输入 segments 范围内")

    # Check coverage（按 span_id）
    for sid in sorted(all_span_ids):
        if sid not in referenced_spans and sid not in skipped_spans:
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
                bspans = norm_skip(bs)
                covered = any(
                    (set(a.get("conditions", [])) & bspans)
                    for a in assertions
                )
                if not covered and not (bspans & skipped_spans):
                    err("AST_005",
                        f"含编者标记的段 {bs} 未被 assertion conditions 处理，"
                        "也不在 skipped_segments 中")
        except Exception as e:
            err("AST_005", f"无法解析 editorial_notes.yaml: {e}")

    # AST_006 命例分离（工位5头号风控，2026-07-14 重写）：
    # case_candidate: true 只表示"段内含命造举例"，语义是"段内通则与命造分离，
    # 命造不提为主张、通则照常提取"（见 stage3c 切分模板）——不是整段丢弃。
    # 旧逻辑把"case段被提主张"判 FAIL，反而逼着整段丢，静默丢失整本书的调候总纲。
    # 新逻辑翻转为防误丢：case_candidate 段若被【整段 skip】(有 skip、无任何主张引用)，
    # 而该段又检测不到四柱命造特征(≥2 组连续干支)，则告警——极可能是把通则误当命例丢了。
    import re as _re
    _GZ = _re.compile(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]")
    text_by_span = {s["span_id"]: s.get("text", "") for s in segments}
    case_spans = {s["span_id"] for s in segments if s.get("case_candidate")}
    for cs in case_spans:
        skipped_here = cs in skipped_spans
        referenced_here = cs in referenced_spans
        # 只在"整段丢、无任何主张"时才怀疑误丢通则
        if skipped_here and not referenced_here:
            gz_pairs = len(_GZ.findall(text_by_span.get(cs, "")))
            if gz_pairs < 2:
                err("AST_006",
                    f"命例段 {cs}（case_candidate）被整段 skip 且无任何主张，"
                    f"但段内检测不到四柱命造（连续干支仅 {gz_pairs} 组）——"
                    "极可能把通则误当命例丢了。case_candidate 是'段内分离'不是'整段弃'，"
                    "请提取该段的通则部分（取用/调候总纲），只排除真正的命造举例。")

    if errors:
        print(f"FAIL  {task_dir.name}  （{len(errors)} 条错误）")
        for e in errors:
            print(f"      {e}")
        sys.exit(1)
    print(f"PASS  {task_dir.name}  （{len(assertions)} 条主张，覆盖 {len(referenced_spans)}/{len(all_span_ids)} 段，命例 {len(case_spans)} 段已排除）")
    sys.exit(0)


if __name__ == "__main__":
    main()
