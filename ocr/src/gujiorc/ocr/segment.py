"""gujiorc.ocr.segment — 单字切分（PLANS M2）。

对 PaddleOCR 输出的「整行/整列文本块」做单字切分，得到每个字的独立 box。

方法（针对竖排古籍）：
1. 识别一个文本块的「主方向」：宽>高 → 横排；高>宽 → 竖排
2. 沿主方向把块裁成细条，逐条统计暗像素密度（在原始灰度图上）
3. 密度高的条 = 笔画区，密度低的条 = 字间空白 → 投影找字边界
4. 由字边界得到每个单字的 box

依赖：需要原始图像（灰度）来测投影。
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from ..core.models import CharBox, PageResult


def _load_gray(image) -> np.ndarray:
    """加载为灰度 numpy 数组（H,W）。image 可为路径/numpy/PIL。"""
    if isinstance(image, str):
        return np.array(Image.open(image).convert("L"))
    if hasattr(image, "shape"):
        # 已是 numpy（BGR/RGB/灰度）
        arr = np.asarray(image)
        if arr.ndim == 3:
            return np.dot(arr[..., :3], [0.299, 0.587, 0.114]).astype(np.uint8)
        return arr
    return np.array(image.convert("L"))  # PIL


def is_vertical(box: dict) -> bool:
    """判断文本块主方向：高 > 宽 → 竖排。"""
    return box["h"] > box["w"]


def segment_block(
    gray: np.ndarray,
    box: dict,
    pad: int = 2,
    min_gap: int = 3,
    density_thresh: float = 0.02,
) -> list[dict]:
    """把一个文本块切成单字 box（像素坐标，含 pad）。

    返回单字 box 列表 [{x,y,w,h}]，按阅读方向排序（竖排：从上到下）。
    """
    x, y, w, h = int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"])
    img_h, img_w = gray.shape[:2]
    x0, x1 = max(0, x), min(img_w, x + w)
    y0, y1 = max(0, y), min(img_h, y + h)
    if x1 <= x0 or y1 <= y0:
        return []

    region = gray[y0:y1, x0:x1]
    dark = region < 128  # 暗像素 = 笔画

    if is_vertical(box):
        # 竖排：沿 Y 投影，按字间距切
        col_density = dark.mean(axis=1)  # 每行暗像素占比
        gaps = _find_gaps(col_density, min_gap, density_thresh)
        boxes = []
        for g0, g1 in gaps:
            sub = region[g0:g1, :]
            # 子块内找实际文字宽度（水平投影）
            row_density = sub.mean(axis=0)
            col_nonzero = np.where(row_density > density_thresh)[0]
            if len(col_nonzero) == 0:
                continue
            cx0, cx1 = col_nonzero[0], col_nonzero[-1] + 1
            boxes.append({
                "x": float(x0 + cx0),
                "y": float(y0 + g0),
                "w": float(cx1 - cx0),
                "h": float(g1 - g0),
            })
        return _merge_thin_segments(boxes)
    else:
        # 横排：水平投影切
        row_density = dark.mean(axis=0)
        gaps = _find_gaps(row_density, min_gap, density_thresh)
        boxes = []
        for g0, g1 in gaps:
            sub = region[:, g0:g1]
            col_density = sub.mean(axis=0)
            row_nonzero = np.where(col_density > density_thresh)[0]
            if len(row_nonzero) == 0:
                continue
            cy0, cy1 = row_nonzero[0], row_nonzero[-1] + 1
            boxes.append({
                "x": float(x0 + g0),
                "y": float(y0 + cy0),
                "w": float(g1 - g0),
                "h": float(cy1 - cy0),
            })
        return _merge_thin_segments(boxes)


def _merge_thin_segments(boxes: list[dict], min_h_ratio: float = 0.45) -> list[dict]:
    """合并「过细」的字框到相邻框。

    竖排/横排中，个别字笔画稀疏（如「一」「丨」）或切分过度会产生异常细的框
    高度 h 远小于正常字形。取所有高度中位数作为典型字高，把 < 0.45×中位数的
    段合并到上一段（竖排向上，横排向左），减少噪声。
    注意：中位数高度代表「字身」；纯点/竖须可能被合并，但相比保留大量噪声更好。
    """
    if len(boxes) < 2:
        return boxes
    median_h = _median([b["h"] for b in boxes])
    if median_h <= 0:
        return boxes
    merged = []
    for b in boxes:
        if b["h"] < median_h * min_h_ratio and merged:
            # 合并到上一段：扩展其 y 范围（竖排同列 w 相同，取并集高度）
            prev = merged[-1]
            prev["h"] = (max(prev["y"] + prev["h"], b["y"] + b["h"])) - prev["y"]
        else:
            merged.append(dict(b))
    return merged


def _median(vals: list[float]) -> float:
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return 0.0
    return s[n // 2]


def _find_gaps(density: np.ndarray, min_gap: int, thresh: float) -> list[tuple[int, int]]:
    """沿一维投影密度找「内容段」。返回 [(start,end),...]（内容索引，而非空白）。"""
    below = density <= thresh  # 空白位置
    content = ~below
    segments = []
    i = 0
    n = len(density)
    while i < n:
        if content[i]:
            j = i
            while j < n and content[j]:
                j += 1
            segments.append((i, j))
            i = j
        else:
            i += 1
    # 过滤过窄片段（投影噪声），但保留单个字的窄笔画（如「一」）
    # 这里 min_gap 用于底部：若一段内容宽度 < min_gap×0.5 且被夹在空白中，可能是噪声，但保留
    return segments


def segment_page_chars(
    image,
    page: PageResult,
    min_gap: int = 2,
    density_thresh: float = 0.02,
) -> int:
    """对 page 中所有 level=line 块做单字切分，生成 CharBox 列表。

    将原始 line 块的 text 按切出的字符数拆分填充到每个单字 CharBox，
    更新 page.chars 为真正的单字框，page.lines 保留行级。

    返回单字数。
    """
    gray = _load_gray(image)

    new_chars: list[CharBox] = []
    seq = 0
    for line in page.lines:
        seg_boxes = segment_block(gray, line.box, min_gap=min_gap, density_thresh=density_thresh)
        if not seg_boxes:
            continue
        # 原行文本（PaddleOCR 的整行识别文本）
        text = line.text or ""
        # 文字可能比字符多（含标点/空格），按 seg 数尝试对齐；超出的字归并到最后
        n_seg = len(seg_boxes)
        text_chars = _clean_text(text)
        for si, sb in enumerate(seg_boxes):
            char = ""
            if si < len(text_chars):
                char = text_chars[si]
            elif text_chars:
                char = text_chars[-1]  # 超出部分挂最后
            new_chars.append(CharBox(
                id=f"{page.page}c{seq:04d}",
                box=sb,
                char=char,
                conf=line.conf,
                parent=line.id,
                status="pending",
                angle=0.0,
                extra={"band": line.extra.get("band", 0)},
            ))
            seq += 1

    page.chars = new_chars
    return len(new_chars)


def _clean_text(text: str) -> list[str]:
    """从行文本提取汉字+常用标点，去掉首尾空白。"""
    return list(text.strip()) if text else []