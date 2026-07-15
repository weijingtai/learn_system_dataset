#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_canon.py —— L1 共享 canon 的完整性与修订合规校验
（GOVERNANCE.md 铁律的程序执行；canon 每次修改后必须 PASS）

检查项（错误码）：
    CAN_001  concept_id 格式错 / 不符 co_shared_<domain>_NN / 与文件 domain 不符
    CAN_002  concept_id 重复（全 canon 范围内唯一）
    CAN_003  闭集数量不符：concepts 数 ≠ closed_set_size（天干必须恰好10、地支12…）
    CAN_004  缺 rev / status / surface 必填字段，或 status 非法
    CAN_005  地支 hidden_stems 引用了不存在的天干字（藏干映射完整性）
    CAN_006  surface 在同一 domain 内重复（闭集成员不许同名）

退出码：0 = PASS；1 = FAIL。
用法：python3 validators/check_canon.py schemas/shared/canon/
"""
import re
import sys
from pathlib import Path

import yaml

ID_RE = re.compile(r"^co_shared_([a-z]+)_(\d{2,})$")
STATUS_ENUM = {"active", "deprecated"}
STEMS = set("甲乙丙丁戊己庚辛壬癸")


def main():
    canon_dir = Path(sys.argv[1])
    errors = []
    all_ids = {}

    files = sorted(canon_dir.glob("*.yaml"))
    if not files:
        print(f"FAIL  {canon_dir} 下无 canon 文件")
        sys.exit(1)

    for f in files:
        doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        domain = doc.get("canon_domain", "")
        concepts = doc.get("concepts", [])
        closed = doc.get("closed_set_size")

        # CAN_003 闭集数量
        if closed is not None and len(concepts) != closed:
            errors.append(f"CAN_003 | {f.name} | concepts {len(concepts)} ≠ closed_set_size {closed}")

        seen_surface = set()
        for c in concepts:
            cid = c.get("concept_id", "")
            m = ID_RE.match(cid)
            # CAN_001
            if not m:
                errors.append(f"CAN_001 | {f.name} | id 格式错: {cid}")
            elif m.group(1) != domain:
                errors.append(f"CAN_001 | {f.name} | id domain『{m.group(1)}』≠ 文件 domain『{domain}』: {cid}")
            # CAN_002 全局唯一
            if cid in all_ids:
                errors.append(f"CAN_002 | {cid} | 重复（另见 {all_ids[cid]}）")
            else:
                all_ids[cid] = f.name
            # CAN_004 必填
            if not c.get("surface", "").strip():
                errors.append(f"CAN_004 | {cid} | surface 空")
            if "rev" not in c:
                errors.append(f"CAN_004 | {cid} | 缺 rev")
            if c.get("status") not in STATUS_ENUM:
                errors.append(f"CAN_004 | {cid} | status 非法: {c.get('status')}")
            # CAN_006 域内 surface 唯一
            surf = c.get("surface", "")
            if surf in seen_surface:
                errors.append(f"CAN_006 | {f.name} | surface 域内重复: {surf}")
            seen_surface.add(surf)
            # CAN_005 藏干映射完整性
            for hs in c.get("hidden_stems", []) or []:
                if hs not in STEMS:
                    errors.append(f"CAN_005 | {cid} | hidden_stems『{hs}』不是合法天干")

    if errors:
        print(f"FAIL  canon  （{len(errors)} 条错误，{len(all_ids)} 概念）")
        for e in errors:
            print(f"      {e}")
        sys.exit(1)
    print(f"PASS  canon  （{len(files)} 域，{len(all_ids)} 概念，闭集完整、ID 唯一）")
    sys.exit(0)


if __name__ == "__main__":
    main()
