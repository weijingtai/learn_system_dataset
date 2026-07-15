#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_concepts.py —— 工位 4 术语候选清单的确定性校验
（此前工位 4 候选清单无校验器裸奔，本工具补缺；对应 SCHEMA GLO_003 的候选阶段版）

用法：
    python3 validators/check_concepts.py <任务包目录>
    读 <任务包>/output/draft_opencode.yaml 的 candidates，
    对照 <任务包>/input/segments.yaml 的 span_id→text。

检查项（错误码）：
    CON_001  candidates 结构错误 / 缺 surface / kind_guess 非法枚举
    CON_002  surface 在其声称的某个 seg_id(span) 原文中不存在（最要命：下游会去空段找证据）
    CON_003  seg_ids 引用了 segments 里不存在的 span_id
    CON_004  surface 为空 或 seg_ids 为空
    CON_005  同一 surface 出现多条记录（应合并为一条，seg_ids 列全）（警告）

退出码：0 = PASS；1 = FAIL。只报错，不改文件。
"""
import sys
from pathlib import Path

import yaml

KIND_ENUM = {"ten_god", "pattern", "tiaohou", "stem_branch", "phase", "other"}


def main():
    task_dir = Path(sys.argv[1])
    draft = task_dir / "output/draft_opencode.yaml"
    seg_file = task_dir / "input/segments.yaml"
    if not draft.exists():
        print(f"FAIL  找不到 {draft}")
        sys.exit(1)

    data = yaml.safe_load(draft.read_text(encoding="utf-8"))
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        print("FAIL  CON_001 | 无法解析出 candidates 列表")
        sys.exit(1)

    seg_map = {s["span_id"]: s["text"]
               for s in yaml.safe_load(seg_file.read_text(encoding="utf-8"))["segments"]}

    errors, warnings = [], []
    seen_surface = {}
    for i, c in enumerate(candidates, 1):
        surf = str(c.get("surface", "")).strip()
        kind = c.get("kind_guess", "")
        seg_ids = c.get("seg_ids", [])
        if not surf:
            errors.append(f"CON_004 | 第{i}条 | surface 为空")
            continue
        if not seg_ids:
            errors.append(f"CON_004 | {surf} | seg_ids 为空")
        if kind not in KIND_ENUM:
            errors.append(f"CON_001 | {surf} | kind_guess 非法: {kind}（允许 {', '.join(sorted(KIND_ENUM))}）")
        # CON_005 重复 surface
        if surf in seen_surface:
            warnings.append(f"CON_005 | {surf} | 出现多条记录（第{seen_surface[surf]}、{i}条），应合并")
        else:
            seen_surface[surf] = i
        # CON_002 / CON_003 span 存在性 + surface 命中
        for sid in seg_ids:
            if sid not in seg_map:
                errors.append(f"CON_003 | {surf} | 引用的 span 不存在: {sid}")
            elif surf not in seg_map[sid]:
                errors.append(f"CON_002 | {surf} | 在 {sid} 原文中未找到（该 span 不含此词，会误导下游取证）")

    for w in warnings:
        print(f"WARN  {w}")
    if errors:
        print(f"FAIL  {task_dir.name}  （{len(errors)} 条错误，{len(candidates)} 候选）")
        for e in errors:
            print(f"      {e}")
        sys.exit(1)
    print(f"PASS  {task_dir.name}  （{len(candidates)} 候选术语，surface 全部命中原文）")
    sys.exit(0)


if __name__ == "__main__":
    main()
