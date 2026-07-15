#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_canon.py —— 生成 L1 共享源数据 canon（天干/地支/五行/阴阳/八卦/十二长生/地支藏干）
（CROSS_TECHNIQUE_ONTOLOGY.md L1 层的确定性实现）

设计要点（配合 GOVERNANCE.md）：
- concept_id 永久稳定：co_shared_<domain>_NN，按标准顺序编号，不复用不删除；
- 每概念带 rev=1、status=active、可变字段（aliases/note 等），支持事后修订；
- 闭集：天干恰好 10、地支恰好 12、五行 5、阴阳 2、八卦 8、长生 12；
- 地支藏干是映射数据，同样进 canon（各技法共享同一藏干表）。

用法：
    python3 tools/gen_canon.py         # 生成到 schemas/shared/canon/
确定性：纯静态数据，同版本永远同输出。修改数据请改本脚本并升对应概念 rev（见 GOVERNANCE）。
"""
from pathlib import Path
import yaml

CANON = Path(__file__).resolve().parent.parent / "schemas/shared/canon"

# —— 标准闭集静态数据（改这里＝改标准，须走 GOVERNANCE 决议并升 rev）——
STEMS = [  # 天干：字, 阴阳, 五行
    ("甲", "阳", "木"), ("乙", "阴", "木"), ("丙", "阳", "火"), ("丁", "阴", "火"),
    ("戊", "阳", "土"), ("己", "阴", "土"), ("庚", "阳", "金"), ("辛", "阴", "金"),
    ("壬", "阳", "水"), ("癸", "阴", "水"),
]
BRANCHES = [  # 地支：字, 阴阳, 五行, 生肖, 藏干(本气/中气/余气)
    ("子", "阳", "水", "鼠", ["癸"]),
    ("丑", "阴", "土", "牛", ["己", "癸", "辛"]),
    ("寅", "阳", "木", "虎", ["甲", "丙", "戊"]),
    ("卯", "阴", "木", "兔", ["乙"]),
    ("辰", "阳", "土", "龙", ["戊", "乙", "癸"]),
    ("巳", "阴", "火", "蛇", ["丙", "庚", "戊"]),
    ("午", "阳", "火", "马", ["丁", "己"]),
    ("未", "阴", "土", "羊", ["己", "丁", "乙"]),
    ("申", "阳", "金", "猴", ["庚", "壬", "戊"]),
    ("酉", "阴", "金", "鸡", ["辛"]),
    ("戌", "阳", "土", "狗", ["戊", "辛", "丁"]),
    ("亥", "阴", "水", "猪", ["壬", "甲"]),
]
WUXING = ["木", "火", "土", "金", "水"]
YINYANG = ["阴", "阳"]
BAGUA = [  # 八卦：卦名, 五行, 后天方位
    ("乾", "金", "西北"), ("坤", "土", "西南"), ("震", "木", "东"), ("巽", "木", "东南"),
    ("坎", "水", "北"), ("离", "火", "南"), ("艮", "土", "东北"), ("兑", "金", "西"),
]
CHANGSHENG = ["长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养"]


def concept(cid, surface, domain, **extra):
    """统一概念结构：稳定 id + rev + status + 可变字段。"""
    base = {"concept_id": cid, "surface": surface, "domain": domain,
            "rev": 1, "status": "active", "aliases": [], "note": ""}
    base.update(extra)
    return base


def dump(name, concepts, closed_count):
    doc = {
        "canon_domain": name,
        "schema_version": "canon_v0.1",
        "closed_set_size": closed_count,   # 闭集应有成员数，check_canon 强校验
        "id_prefix": f"co_shared_{name}_",
        "concepts": concepts,
        "revisions": [{"date": "2026-07-11", "change": "初版生成", "rev_scope": "all@1"}],
    }
    (CANON / f"{name}.yaml").write_text(
        yaml.dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"  {name}.yaml: {len(concepts)} 条（闭集 {closed_count}）")


def main():
    CANON.mkdir(parents=True, exist_ok=True)
    print("生成 L1 共享 canon：")

    dump("stem", [
        concept(f"co_shared_stem_{i:02d}", s, "stem", yinyang=yy, wuxing=wx)
        for i, (s, yy, wx) in enumerate(STEMS, 1)], 10)

    dump("branch", [
        concept(f"co_shared_branch_{i:02d}", s, "branch",
                yinyang=yy, wuxing=wx, zodiac=zo, hidden_stems=hs)
        for i, (s, yy, wx, zo, hs) in enumerate(BRANCHES, 1)], 12)

    dump("wuxing", [
        concept(f"co_shared_wuxing_{i:02d}", s, "wuxing")
        for i, s in enumerate(WUXING, 1)], 5)

    dump("yinyang", [
        concept(f"co_shared_yinyang_{i:02d}", s, "yinyang")
        for i, s in enumerate(YINYANG, 1)], 2)

    dump("bagua", [
        concept(f"co_shared_bagua_{i:02d}", s, "bagua", wuxing=wx, direction=d)
        for i, (s, wx, d) in enumerate(BAGUA, 1)], 8)

    dump("changsheng", [
        concept(f"co_shared_changsheng_{i:02d}", s, "changsheng", order=i)
        for i, s in enumerate(CHANGSHENG, 1)], 12)

    print("完成。修改数据请改本脚本静态表并按 GOVERNANCE 升 rev。")


if __name__ == "__main__":
    main()
