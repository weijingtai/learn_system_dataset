"""gujiorc.ocr.pipeline — 识别流水线：图 → PageResult（层级框）。

流程：识别 → 区块切分 → 行框聚合 → 字框生成 → 生僻字标记。

输出 PageResult（CharBox + LineBox 层级），供存储/索引/生僻字模块消费。
"""
from __future__ import annotations

import numpy as np

from ..core.models import (
    PageResult, CharBox, LineBox, STATUS_PENDING, RARE_LOW_CONF,
)
from .engine import PaddleOcrEngine, split_bands_by_ocr_boxes


def image_to_page(
    image,  # numpy array(BGR) / 路径
    page: str,
    book: str | None = None,
    image_path: str = "",
    gap_thresh: float = 40,
    col_gap_thresh: float = 30,
    conf_thresh: float = 0.6,   # 低置信度 → is_rare (low_conf)
) -> PageResult:
    """识别一张图，产出 PageResult（含区块/行/字的层级框）。

    注意：此阶段生僻字判定（not_in_common_set）由 rare 模块做，
    low_conf 在此标记。
    """
    engine = PaddleOcrEngine()
    raw = engine.recognize(image)
    if not raw or not raw[0]:
        raise ValueError(f"[{page}] 未识别到任何文本")

    res = raw[0]
    texts = res["rec_texts"]
    polys = res["rec_polys"]
    scores = res["rec_scores"]

    # 图像尺寸
    if hasattr(image, "shape"):
        height, width = image.shape[:2]
    else:
        from PIL import Image
        with Image.open(image) as im:
            width, height = im.size

    items, band_ids, _ = split_bands_by_ocr_boxes(res, gap_thresh)

    # 每个识别块 → 一个字框（初始粒度，后续可能聚合成行）
    # 注意：PaddleOCR 是整行/整列输出，这里先存为 line 级块，
    #       单字切分是后续 M2 的事。此处把每个 det 框作 CharBox 的雏形，
    #       但用 level 区分。
    chars: list[CharBox] = []
    for i, (txt, poly, score, band) in enumerate(zip(texts, polys, scores, band_ids)):
        xs, ys = poly[:, 0], poly[:, 1]
        box = {
            "x": float(np.min(xs)),
            "y": float(np.min(ys)),
            "w": float(np.max(xs) - np.min(xs)),
            "h": float(np.max(ys) - np.min(ys)),
        }
        rare = float(score) < conf_thresh
        chars.append(CharBox(
            id=f"{page}c{i:04d}",
            box=box,
            char=txt,          # PaddleOCR 输出的行文本
            conf=float(score),
            status=STATUS_PENDING,
            is_rare=rare,
            rare_reason=RARE_LOW_CONF if rare else None,
            angle=0.0,
            extra={"band": band},
        ))

    # 这里 char 实际是一整行文本——真正的单字切分在 M2。
    # 为忠实保留「最细粒度检测框」，本版本把 det 块作为 line 存储，
    # 字级切分后续实现。先返回 line 级结果，结构对齐 PageResult。
    line_boxes: list[LineBox] = []
    for c in chars:
        line_boxes.append(LineBox(
            id=c.id,
            box=c.box,
            text=c.char,
            conf=c.conf,
            angle=c.angle,
        ))

    return PageResult(
        page=page,
        book=book,
        image=image_path,
        width=width,
        height=height,
        chars=chars,       # line 级块暂存于此（保持向后兼容）
        lines=line_boxes,
        extra={"col_gap_thresh": col_gap_thresh, "count_blocks": len(chars)},
    )