#!/usr/bin/env python3
"""validate_glossary.py —— 术语表校验器"""

import re
import sys
from pathlib import Path

import yaml

PIPELINE_ROOT = Path(__file__).resolve().parent.parent

ID_GLOSSARY = re.compile(r"^co_[a-z]+_\d{6}$")
# L1 共享 canon 引用：co_shared_<domain>_NN（技法表可引用共享概念，见 CROSS_TECHNIQUE_ONTOLOGY）
ID_SHARED = re.compile(r"^co_shared_[a-z]+_\d{2,}$")
STATUS_ENUM = {"confirmed_v0", "candidate", "rejected", "rejected_suggested"}

errors = []


def err(code, msg):
    errors.append(f"{code} | {msg}")


def main():
    if len(sys.argv) < 2:
        print("用法: python3 validators/validate_glossary.py <glossary.yaml> [segments.yaml]")
        sys.exit(1)

    glossary_path = Path(sys.argv[1])
    segments_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    try:
        data = yaml.safe_load(glossary_path.read_text(encoding="utf-8"))
        concepts = data.get("concepts", [])
    except Exception as e:
        err("GLO_001", f"无法解析 glossary: {e}")
        print(f"FAIL  {len(errors)} 条错误")
        for e in errors:
            print(f"      {e}")
        sys.exit(1)

    # 预加载 segments
    seg_map = {}
    if segments_path and segments_path.exists():
        seg_data = yaml.safe_load(segments_path.read_text(encoding="utf-8"))
        for s in seg_data.get("segments", []):
            seg_map[s["seg_id"]] = s["text"]

    seen_ids = set()
    for c in concepts:
        cid = c.get("concept_id", "")
        # GLO_001 编号
        if not cid:
            err("GLO_001", "concept_id 缺失")
        elif not (ID_GLOSSARY.match(cid) or ID_SHARED.match(cid)):
            err("GLO_001", f"concept_id 格式错误: {cid}（应符合 co_[a-z]+_\\d{{6}} 或 co_shared_<domain>_NN）")
        else:
            if cid in seen_ids:
                err("GLO_001", f"concept_id 重复: {cid}")
            seen_ids.add(cid)

        # GLO_002 状态
        status = c.get("status", "")
        if status not in STATUS_ENUM:
            err("GLO_002", f"status 非法: {status}（{cid}）允许: {', '.join(sorted(STATUS_ENUM))}")

        # GLO_003 surface 非空 且 在对应的 segment 中存在
        surface = c.get("surface", "")
        if not surface or not surface.strip():
            err("GLO_003", f"surface 为空（{cid}）")
        else:
            seg_ids = c.get("seg_ids", [])
            for sid in seg_ids:
                if sid not in seg_map:
                    err("GLO_003", f"seg_id '{sid}' 在 segments 文件中不存在（{cid}）")
                elif surface not in seg_map[sid]:
                    err("GLO_003", f"surface '{surface}' 在 {sid} 原文中未找到（{cid}）")

        # GLO_004 rejected 条目需有 note
        if status == "rejected" and not c.get("note", "").strip():
            err("GLO_004", f"rejected 条目缺少 note（{cid}）")

    if errors:
        print(f"FAIL  {glossary_path.name}  （{len(errors)} 条错误）")
        for e in errors:
            print(f"      {e}")
        sys.exit(1)
    print(f"PASS  {glossary_path.name}  （{len(concepts)} 条术语）")
    sys.exit(0)


if __name__ == "__main__":
    main()
