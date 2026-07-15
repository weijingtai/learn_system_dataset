#!/usr/bin/env python3
"""validate_paraphrase_task.py —— 白话释义任务包校验器（工位 6）

程序层只兜结构底：覆盖率、status 越权、span_id 有效、original 与输入原文逐字一致。
吉凶强化、补背景知识、语气篡改等语义红线无法纯程序判定，留给人工复核。
用完整 span_id 比对，绝不用 _sNN 尾号（工位5栽过的跨页碰撞坑）。
"""

import sys
from pathlib import Path

import yaml

errors = []


def err(code, msg):
    errors.append(f"{code} | {msg}")


def main():
    if len(sys.argv) < 2:
        print("用法: python3 validators/validate_paraphrase_task.py <任务包目录>")
        sys.exit(1)

    task_dir = Path(sys.argv[1]).resolve()
    out_dir = task_dir / "output"
    inp_dir = task_dir / "input"

    # PAR_001 双路件：至少两个不同 --by 的归档 + merged
    archive_dirs = [d for d in out_dir.iterdir() if d.is_dir()] if out_dir.exists() else []
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
        err("PAR_001", f"不同 --by 的归档不足两个（当前: {by_names or '无'}）")
    merged_file = out_dir / "merged_final.yaml"
    if not merged_file.exists():
        err("PAR_001", "缺少 merged_final.yaml")

    # PAR_002 状态越权：draft 只许 machine_translated；merged 每条须 cross_model_reviewed
    ALLOWED_DRAFT = {"machine_translated", "needs_escalation"}
    for draft in sorted(out_dir.glob("draft_*.yaml")) if out_dir.exists() else []:
        try:
            dd = yaml.safe_load(draft.read_text(encoding="utf-8")) or {}
            for p in dd.get("paraphrases", []):
                if p.get("status") not in ALLOWED_DRAFT:
                    err("PAR_002",
                        f"{draft.name} 中 {p.get('span_id')} 的 status={p.get('status')}，"
                        "单路草稿只允许 machine_translated（状态越权）")
        except Exception as e:
            err("PAR_002", f"无法解析 {draft.name}: {e}")

    merged = {}
    if merged_file.exists():
        try:
            merged = yaml.safe_load(merged_file.read_text(encoding="utf-8")) or {}
            for p in merged.get("paraphrases", []):
                if p.get("status") != "cross_model_reviewed":
                    err("PAR_002",
                        f"merged_final 中 {p.get('span_id')} 的 status={p.get('status')}，"
                        "应为 cross_model_reviewed（状态越权）")
        except Exception as e:
            err("PAR_002", f"无法解析 merged_final.yaml: {e}")

    # 读输入 segments（span_id 为唯一键）
    seg_file = inp_dir / "segments.yaml"
    if not seg_file.exists():
        err("PAR_003", "input/segments.yaml 不存在")
        _report(task_dir, 0)
        return
    segments = yaml.safe_load(seg_file.read_text(encoding="utf-8")).get("segments", [])
    orig_by_span = {s["span_id"]: s["text"] for s in segments}
    all_spans = set(orig_by_span)

    paraphrases = merged.get("paraphrases", []) if isinstance(merged, dict) else []
    seen_spans = set()
    for p in paraphrases:
        sp = p.get("span_id", "")
        # PAR_004 越界引用
        if sp not in all_spans:
            err("PAR_004", f"释义引用了 {sp}，不在输入 segments 范围内")
            continue
        seen_spans.add(sp)
        # PAR_005 原文篡改：original 字段必须与输入原文逐字一致
        if p.get("original", "") != orig_by_span[sp]:
            err("PAR_005",
                f"{sp} 的 original 字段与输入原文不一致（疑似改字/漏字，须逐字照抄原文）")
        # PAR_006 空译
        if not (p.get("vernacular") or "").strip():
            err("PAR_006", f"{sp} 的 vernacular 为空（每段必须有白话释义）")

    # PAR_003 覆盖缺口：每个 span 都要有释义
    for sp in sorted(all_spans):
        if sp not in seen_spans:
            err("PAR_003", f"段 {sp} 没有白话释义（覆盖缺口）")

    _report(task_dir, len(paraphrases))


def _report(task_dir, n):
    if errors:
        print(f"FAIL  {task_dir.name}  （{len(errors)} 条错误）")
        for e in errors:
            print(f"      {e}")
        sys.exit(1)
    print(f"PASS  {task_dir.name}  （{n} 条白话释义）")
    sys.exit(0)


if __name__ == "__main__":
    main()
