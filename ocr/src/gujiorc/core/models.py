"""gujiorc.core.models — 数据模型（层级框 / 生僻字标记 / 分组归并）。

对应 PLANS.md §4.1/§4.2：
- CharBox   单字框（最细粒度，含 box/angle/char/conf/status/is_rare）
- LineBox   行/列框（父框，children 指向字框）
- PageResult 一页识别结果（含 all 层级框 + 元数据）
- RareChar  生僻字清单条目
- GlyphGroup 生僻字分组归并组
- BookMeta  书目元数据
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


# 状态枚举（与 PLANS schema 一致）
STATUS_PENDING = "pending"          # 待校对
STATUS_VERIFIED = "verified"        # 已确认
STATUS_CORRECTED = "corrected"      # 已改正
STATUS_UNRECOGNIZED = "unrecognized"  # 未识别
STATUSES = {STATUS_PENDING, STATUS_VERIFIED, STATUS_CORRECTED, STATUS_UNRECOGNIZED}

# 生僻字判定原因
RARE_NOT_IN_COMMON = "not_in_common_set"   # 不在常用字表
RARE_LOW_CONF = "low_conf"                 # 低置信度（形变字）
RARE_METHODS = {RARE_NOT_IN_COMMON, RARE_LOW_CONF}


def parse_box(box: dict[str, float] | tuple | list) -> dict[str, float]:
    """统一 box 格式为 {x, y, w, h}。接受 dict 或 [x,y,w,h] / (x,y,w,h)。"""
    if isinstance(box, dict):
        return {"x": float(box["x"]), "y": float(box["y"]), "w": float(box["w"]), "h": float(box["h"])}
    seq = list(box)
    if len(seq) != 4:
        raise ValueError(f"box 必须为 [x,y,w,h]，得到 {box}")
    return {"x": float(seq[0]), "y": float(seq[1]), "w": float(seq[2]), "h": float(seq[3])}


@dataclass
class CharBox:
    """单字框（最细粒度）。"""
    id: str                       # {book}_{page}_{seq}
    box: dict[str, float]         # {x,y,w,h}
    level: str = "char"
    parent: str | None = None     # 父框(行/列) ID
    angle: float = 0.0            # 旋转角(度)，0=正直，逆时针为正
    char: str = ""                # 识别字；未识别为空
    conf: float = 0.0             # OCR 置信度
    source: str = "ocr"           # ocr | manual
    status: str = STATUS_PENDING
    is_rare: bool = False         # 是否生僻字
    rare_reason: str | None = None  # RARE_* 之一
    glyph: dict[str, Any] | None = None  # 拆解结果 {"radical","parts","note"}
    sample_img: str | None = None  # 生僻字截图路径（M10_）
    extra: dict[str, Any] = field(default_factory=dict)  # 任意扩展

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CharBox":
        d = dict(d)
        d["box"] = parse_box(d["box"])
        return cls(**d)


@dataclass
class LineBox:
    """行/列框（父框，包含若干字）。"""
    id: str
    box: dict[str, float]
    level: str = "line"
    parent: str | None = None     # 可能的列框
    text: str = ""                # 该行识别文本（子框拼接）
    children: list[str] = field(default_factory=list)
    conf: float = 0.0
    angle: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LineBox":
        d = dict(d)
        d["box"] = parse_box(d["box"])
        return cls(**d)


@dataclass
class PageResult:
    """一页识别结果。"""
    page: str                            # 页码 e.g. "page_001"
    image: str                           # 底图相对路径
    width: int
    height: int
    chars: list[CharBox] = field(default_factory=list)
    lines: list[LineBox] = field(default_factory=list)
    book: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)  # 扩展（列/区块分组等）

    def to_dict(self) -> dict:
        return {
            "page": self.page,
            "book": self.book,
            "image": self.image,
            "width": self.width,
            "height": self.height,
            "lines": [l.to_dict() for l in self.lines],
            "chars": [c.to_dict() for c in self.chars],
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PageResult":
        return cls(
            page=d["page"],
            book=d.get("book"),
            image=d.get("image", ""),
            width=d.get("width", 0),
            height=d.get("height", 0),
            chars=[CharBox.from_dict(c) for c in d.get("chars", [])],
            lines=[LineBox.from_dict(l) for l in d.get("lines", [])],
            extra=d.get("extra", {}),
        )


@dataclass
class RareChar:
    """生僻字清单条目。"""
    char: str
    count: int = 0
    positions: list[dict] = field(default_factory=list)  # [{page, id, box, reason}]
    note: str = ""
    group_id: str | None = None   # 归属分组（M12_）

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GlyphGroup:
    """生僻字分组归并组（M12_）。"""
    id: str
    name: str
    char: str | None = None       # 定义后填目标字
    font: str | None = None       # TTF 字体名
    note: str = ""
    samples: list[str] = field(default_factory=list)  # 组内字框 ID 列表
    status: str = "unresolved"    # unresolved | defined
    created: str = ""
    updated: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "GlyphGroup":
        return cls(**d)