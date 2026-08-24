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
    """单字框（最细粒度）。

    数据铁律：原始 OCR 识别结果永不覆盖销毁。
    - orig_char       识别/录入的原始文本（OCR 或 manual 录入，只增不改）
    - char            当前规范字符（展示/导出用）＝ orig_char 或其映射结果
    - mapping         若 char 由 orig_char 转化而来，记录来源与目标
                       {target, from, source: opencc_simp|glyph_group|manual, ts}
    除人工显式「改正」外，所有自动转化（繁简归一/分组映射）都不改 orig_char，
    只写 char + mapping，保证可回退。
    """
    id: str                       # {book}_{page}_{seq}
    box: dict[str, float]         # {x,y,w,h}
    level: str = "char"
    parent: str | None = None     # 父框(行/列) ID
    angle: float = 0.0            # 旋转角(度)，0=正直，逆时针为正
    char: str = ""                # 当前规范字（展示/导出用）
    orig_char: str = ""           # 原始 OCR 识别文本（永不覆盖）
    conf: float = 0.0             # OCR 置信度
    source: str = "ocr"           # ocr | manual
    status: str = STATUS_PENDING
    is_rare: bool = False         # 是否生僻字
    rare_reason: str | None = None  # RARE_* 之一
    glyph: dict[str, Any] | None = None  # 拆解结果 {"radical","parts","note"}
    sample_img: str | None = None  # 生僻字截图路径（M10_）
    mapping: dict[str, Any] | None = None  # 转化记录 {target, from, source, ts}
    extra: dict[str, Any] = field(default_factory=dict)  # 任意扩展

    def set_char(self, new_char: str, mapping_source: str = "manual"):
        """设置当前规范字，同时保留原始字并记录映射。

        - 若当前 char 等于原始 orig_char（第一次改动），则先填 orig_char
        - 记录 mapping: 从旧char → 新char，来源 manual/opencc_simp/glyph_group
        """
        if not self.orig_char and self.char:
            self.orig_char = self.char
        old = self.char
        self.char = new_char
        self.mapping = {
            "target": new_char,
            "from": old,
            "source": mapping_source,
            "ts": _now_iso(),
        }
        # 前缀匹配而非全等：人工编辑有多种细分来源（manual:merge / manual:reflow
        # 等，见 core/edit.py），它们同样是人工改正，都该标 corrected。
        if mapping_source.startswith("manual"):
            self.status = STATUS_CORRECTED

    def normalize_from_orig(self, mapping_source: str = "opencc_simp"):
        """由 orig_char 派生当前 char（如繁简归一）；不改 orig_char。"""
        if not self.orig_char:
            return
        old = self.char
        if old == self.orig_char:
            return  # 尚无映射
        self.mapping = {
            "target": self.char,
            "from": self.orig_char,
            "source": mapping_source,
            "ts": _now_iso(),
        }

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CharBox":
        d = dict(d)
        d["box"] = parse_box(d["box"])
        # 向后兼容：旧数据**根本没有** orig_char 这个键 → 用 char 兜底。
        # 必须判「键缺失」而非「值为空」：`to_dict()` 走 asdict，新数据一定带这个键，
        # 所以空字符串是**故意**的——那是 split 拆出来、OCR 确实什么都没认出来的框
        # （见 core/edit.py）。若对空值也兜底，这类框一旦被人工填字，存盘再读就变成
        # 「OCR 原本就认得这个字」，审计链上再也分不清机器认的和人填的。
        if "orig_char" not in d and d.get("char"):
            d["orig_char"] = d["char"]
        return cls(**d)


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


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
    extra: dict[str, Any] = field(default_factory=dict)

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