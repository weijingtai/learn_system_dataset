"""gujiorc.ocr.segment 单字切分测试（用合成竖排文字图像）。"""
import os
import sys

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "src")))

from gujiorc.core.models import LineBox, PageResult  # noqa: E402
from gujiorc.ocr.segment import segment_block, segment_page_chars, is_vertical  # noqa: E402


def make_vertical_text_image(width=200, height=400, font_size=30, chars="得孛敬"):
    """画一张竖排文字图（字从上到下排列）。"""
    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", font_size)
    # 竖排：每个字一个位置，从上到下
    x = width // 2
    y = 40
    for ch in chars:
        if ch == "得":
            continue
        draw.text((x, y), ch, fill=0, font=font)
        y += font_size + 20  # 字间距
    return np.array(img)


def test_is_vertical():
    assert is_vertical({"w": 40, "h": 300}) is True
    assert is_vertical({"w": 300, "h": 40}) is False


def test_segment_block_vertical():
    """横排简化为竖排：合成图，框住竖排3字，切出3段。"""
    gray = make_vertical_text_image(chars="得孛敬")
    # 用一个覆盖 3 个字的块
    img = Image.fromarray(gray)
    # 检测文字实际占了哪些行
    dark_rows = np.where((gray < 128).sum(axis=1) > 0)[0]
    y0, y1 = dark_rows[0], dark_rows[-1]
    dark_cols = np.where((gray < 128).sum(axis=0) > 0)[0]
    x0, x1 = dark_cols[0], dark_cols[-1]
    box = {"x": x0 - 5, "y": y0 - 5, "w": (x1 - x0) + 10, "h": (y1 - y0) + 10}
    segs = segment_block(gray, box, min_gap=2)
    # 竖排 3 字应切出 3 段（至少 2，考虑笔画间隙）
    assert len(segs) >= 2, f"应切出多个字，得到 {len(segs)} → {segs}"
    # 每个段应有一定高度（非噪声）
    assert all(s["h"] > 10 for s in segs)


def test_segment_page_chars():
    """整页单字切分：将 1 个 line 切成多个 char。"""
    gray = make_vertical_text_image(chars="得孛敬")
    img = Image.fromarray(gray)
    dark_rows = np.where((gray < 128).sum(axis=1) > 0)[0]
    y0, y1 = dark_rows[0], dark_rows[-1]
    dark_cols = np.where((gray < 128).sum(axis=0) > 0)[0]
    x0, x1 = dark_cols[0], dark_cols[-1]
    line = LineBox(
        id="page_001l0000",
        box={"x": x0 - 5, "y": y0 - 5, "w": (x1 - x0) + 10, "h": (y1 - y0) + 10},
        text="得孛敬",
        conf=0.9,
        extra={"band": 0},
    )
    page = PageResult(page="page_001", image="img.png", width=img.size[0], height=img.size[1],
                      lines=[line])
    n = segment_page_chars(img, page)
    assert n >= 2, f"应切出多个单字，得到 {n}"
    # 生成的 CharBox 应有独立坐标
    assert all(c.level == "char" for c in page.chars)
    assert page.chars[0].parent == "page_001l0000"