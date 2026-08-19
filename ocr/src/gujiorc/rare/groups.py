"""gujiorc.rare.groups — 生僻字分组归并（M12_ ★核心）。

- 展板页数据：字形样本 + 未分组状态
- 分组：把字形样本归入同一组（认为同一个字）
- 组级统一定义：定义组代表 char/font 后，组内所有字框映射为该字

底层字框原始识别结果永不销毁；分组定义仅用于展示/导出映射。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..core.models import GlyphGroup
from ..core.paths import get_root


def groups_path() -> Path:
    return Path(get_root()) / "rare" / "glyph_groups.json"


def load_groups() -> list[GlyphGroup]:
    p = groups_path()
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return [GlyphGroup.from_dict(g) for g in data.get("groups", [])]


def save_groups(groups: list[GlyphGroup]):
    p = groups_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"groups": [g.to_dict() for g in groups]}
    tmp = p.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(p)


def _ts() -> str:
    return datetime.now().isoformat(timespec="minutes")


def create_group(groups: list[GlyphGroup], name: str, samples: list[str], note: str = "") -> GlyphGroup:
    """新建一个组，归入给定字形样本 ID。"""
    gid = f"grp_{len(groups) + 1:02d}"
    # 避免撞号
    used = {g.id for g in groups}
    n = len(groups) + 1
    while f"grp_{n:02d}" in used:
        n += 1
    gid = f"grp_{n:02d}"
    group = GlyphGroup(
        id=gid,
        name=name,
        samples=samples,
        note=note,
        created=_ts(),
    )
    groups.append(group)
    return group


def add_samples(groups: list[GlyphGroup], gid: str, samples: list[str]):
    """向组内添加样本（去重；样本已在其他组则先剔除）。"""
    g = next((x for x in groups if x.id == gid), None)
    if g is None:
        raise ValueError(f"找不到组 {gid}")
    for s in samples:
        if s in g.samples:
            continue
        # 从其他组移除该样本（同一样本只能在一组）
        for other in groups:
            if other.id != gid and s in other.samples:
                other.samples.remove(s)
        g.samples.append(s)
    g.updated = _ts()


def remove_samples(groups: list[GlyphGroup], gid: str, samples: list[str]):
    g = next((x for x in groups if x.id == gid), None)
    if g is None:
        return
    for s in samples:
        if s in g.samples:
            g.samples.remove(s)
    g.updated = _ts()


def define_group(groups: list[GlyphGroup], gid: str, char: str | None = None, font: str | None = None):
    """组级统一定义：给组填代表字 / 字体。定义后组内所有字框按此映射。"""
    g = next((x for x in groups if x.id == gid), None)
    if g is None:
        raise ValueError(f"找不到组 {gid}")
    if char is not None:
        g.char = char
    if font is not None:
        g.font = font
    g.status = "defined" if g.char else "unresolved"
    g.updated = _ts()


def resolve_char(groups: list[GlyphGroup], char_id: str) -> str | None:
    """查出某字框若在某个已定义组，返回映射字。"""
    for g in groups:
        if g.status == "defined" and g.char and char_id in g.samples:
            return g.char
    return None