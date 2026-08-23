"""单字切分「不丢字 + 不错位」契约测试（bug 复现 → 疫苗）。

复现的两个真实缺陷（《三辰通载》前10页，727 行中 360 行失配、493 字整行丢失）：

缺陷 A（切过头 → 错位）
    `segment_page_chars` 把投影切出的第 si 段直接配给行文本的第 si 个字
    （`text_chars[si]`）。而「一二三」这类横笔画字、「宫」「主」这类内部
    有横向空隙的字，沿 Y 投影会被切成多段，段数 > 字数，于是从该字起
    整列文字全部后移：前一个字被后一个字顶掉、末尾若干框拿不到字。
    这是交接文档里「字错位」「琅玕重叠」「八一合框」的同一个根因。

缺陷 B（淡字整行丢失）
    `segment_block` 用硬编码绝对阈值 `region < 128` 做二值化。古籍扫描的
    背面透印字、浅印字灰度在 176~229 之间，区域内没有任何像素 < 128 →
    投影全空 → 返回 0 段 → 调用方 `continue` 跳过 → 该行文字被静默丢弃。

本文件的断言是这两个缺陷的疫苗，永久保留：切分结果必须与行文本逐字对齐，
且任何情况下都不得静默丢字。
"""
import os
import sys

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "src")))

from gujiorc.core.models import LineBox, PageResult  # noqa: E402
from gujiorc.ocr.segment import segment_block, segment_page_chars  # noqa: E402

FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"
pytestmark = pytest.mark.skipif(
    not os.path.exists(FONT_PATH), reason="需要系统中文字体渲染合成竖排图"
)


def render_vertical(chars: str, fill: int = 0, font_size: int = 36, gap: int = 14):
    """渲染一张竖排文字图，返回 (灰度数组, 覆盖全部字的 line box, 每字真值行程)。

    fill 控制墨色深浅：0 为正常黑字，210 模拟背面透印的淡字。
    line box 由绘制位置直接推出（而不是靠 <128 找暗像素），这样淡字也能拿到框——
    对应真实链路里 PaddleOCR 检测器给出的框。
    truth 是每个字实际占据的 y 区间 [(y0,y1),...]，用于校验「框↔字」几何对应：
    只断言内容顺序不足以发现错位（段数多于字数时，前几段内容看着是对的，
    但框已经贴到了上一个字的某一笔上）。
    """
    pad_x, pad_y = 30, 20
    width = pad_x * 2 + font_size
    height = pad_y * 2 + len(chars) * (font_size + gap)
    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, font_size)
    truth = []
    y = pad_y
    for ch in chars:
        draw.text((pad_x, y), ch, fill=fill, font=font)
        truth.append((float(y), float(y + font_size)))
        y += font_size + gap
    box = {
        "x": float(pad_x - 6),
        "y": float(pad_y - 6),
        "w": float(font_size + 12),
        "h": float(len(chars) * (font_size + gap) + 12),
    }
    return np.array(img), box, truth


def segment_one_line(chars: str, fill: int = 0):
    """按真实链路跑一遍单字切分，返回 (page, 每字真值 y 区间)。"""
    gray, box, truth = render_vertical(chars, fill=fill)
    line = LineBox(id="page_001l0000", box=box, text=chars, conf=0.9, extra={"band": 0})
    page = PageResult(
        page="page_001",
        image="synthetic.png",
        width=int(gray.shape[1]),
        height=int(gray.shape[0]),
        lines=[line],
    )
    segment_page_chars(Image.fromarray(gray), page)
    return page, truth


def content_chars(page: PageResult) -> str:
    """按阅读顺序（竖排从上到下）拼出有内容的字框文本。"""
    ordered = sorted((c for c in page.chars if c.char), key=lambda c: c.box["y"])
    return "".join(c.char for c in ordered)


# ── 缺陷 A：切过头导致错位 ──────────────────────────────────────────────

@pytest.mark.parametrize("chars", ["一二三", "三口", "身宫主星", "四百八十一", "四八二", "八二", "二"])
def test_segment_count_matches_text_length(chars):
    """横笔画字不得被切成多个字框：有内容的字框数必须等于行文本字数。"""
    page, _ = segment_one_line(chars)
    filled = [c for c in page.chars if c.char]
    assert len(filled) == len(chars), (
        f"{chars!r}: 期望 {len(chars)} 个有字的框，实得 {len(filled)} 个"
        f"（切分段数与行文本长度失配 → 整列文字错位）"
    )


@pytest.mark.parametrize("chars", ["一二三", "三口", "身宫主星", "四百八十一", "四八二", "八二", "二"])
def test_chars_align_with_text_in_reading_order(chars):
    """字框内容必须与行文本逐字对齐，不得后移、重复或顶掉前字。"""
    page, _ = segment_one_line(chars)
    assert content_chars(page) == chars, (
        f"{chars!r}: 按 y 序读出 {content_chars(page)!r}，与行文本不一致（错位）"
    )


@pytest.mark.parametrize("chars", ["一二三", "三口", "身宫主星", "四百八十一", "四八二", "八二", "二"])
def test_char_box_geometrically_matches_its_own_glyph(chars):
    """框↔字几何对应：第 i 个字的框必须落在第 i 个字实际占据的 y 区间内。

    这是错位的真正判据。只看内容顺序会漏——「一二三」被切成 6 段时，
    前 3 段内容读出来仍是「一二三」，但「三」的框已经贴到「二」的下半横上。

    判据用「框中心落在该字 em 区间内」而不是「重叠面积过半」：「一」这类字的
    墨迹只占 em 区间的一小截（36px 的字高里只有 4px 实墨），紧贴笔画的窄框是
    正确结果，不是错位。同时限制框高不超过一个字距，防止两个字并进一个框。
    """
    page, truth = segment_one_line(chars)
    filled = sorted((c for c in page.chars if c.char), key=lambda c: c.box["y"])
    assert len(filled) == len(truth), (
        f"{chars!r}: 框数 {len(filled)} ≠ 字数 {len(truth)}，无法逐字比对几何位置"
    )
    pitch = truth[1][0] - truth[0][0] if len(truth) > 1 else (truth[0][1] - truth[0][0])
    for i, (c, (ty0, ty1)) in enumerate(zip(filled, truth)):
        by0, by1 = c.box["y"], c.box["y"] + c.box["h"]
        center = (by0 + by1) / 2
        assert ty0 <= center <= ty1, (
            f"{chars!r} 第{i}字 {c.char!r}: 框中心 y={center:.0f} 不在该字真实区间 "
            f"[{ty0:.0f},{ty1:.0f}] 内 —— 框贴到了别的字上（错位）"
        )
        assert c.box["h"] <= pitch, (
            f"{chars!r} 第{i}字 {c.char!r}: 框高 {c.box['h']:.0f} 超过一个字距 "
            f"{pitch:.0f} —— 多个字被并进一个框"
        )


def test_each_char_box_is_disjoint_and_ordered():
    """相邻字框不得互相包含：一个字一个框，且 y 单调递增。"""
    page, _ = segment_one_line("一二三")
    boxes = sorted((c.box for c in page.chars if c.char), key=lambda b: b["y"])
    for prev, cur in zip(boxes, boxes[1:]):
        assert cur["y"] >= prev["y"], "字框未按竖排顺序排列"
        assert cur["y"] + cur["h"] > prev["y"] + prev["h"], "后一个字框被前一个包含"


# ── 缺陷 B：淡字（背面透印/浅印）整行丢失 ────────────────────────────────

def test_faint_text_region_still_segments():
    """淡字区域（灰度 210，无任何像素 < 128）仍须切出段，不得返回空。"""
    gray, box, _ = render_vertical("身宫主星", fill=210)
    assert gray.min() >= 128, "本用例前提：区域内不存在 <128 的像素"
    segs = segment_block(gray, box)
    assert segs, "淡字区域返回 0 段 → 硬编码 <128 阈值失效，整行文字将被丢弃"


def test_faint_text_not_silently_dropped():
    """淡字行的文字不得被静默丢弃：必须逐字落到字框里。"""
    page, _ = segment_one_line("身宫主星", fill=210)
    assert content_chars(page) == "身宫主星", (
        f"淡字行读出 {content_chars(page)!r}，期望 '身宫主星'（静默丢字）"
    )


# ── 全局不丢字契约 ──────────────────────────────────────────────────────

def test_no_char_lost_across_mixed_lines():
    """多行混排（含淡字行）时，全页有内容的字框数必须等于各行文本字数之和。"""
    specs = [("一二三", 0), ("身宫主星", 210), ("四百八十一", 0)]
    lines, arrays, y_off, expected = [], [], 0, ""
    for i, (chars, fill) in enumerate(specs):
        gray, box, _ = render_vertical(chars, fill=fill)
        arrays.append(gray)
        lines.append(LineBox(
            id=f"page_001l{i:04d}",
            box={**box, "y": box["y"] + y_off},
            text=chars, conf=0.9, extra={"band": 0},
        ))
        y_off += gray.shape[0]
        expected += chars
    # 纵向拼接成一张图（各行等宽）
    canvas = np.vstack(arrays)
    page = PageResult(page="page_001", image="synthetic.png",
                      width=int(canvas.shape[1]), height=int(canvas.shape[0]), lines=lines)
    segment_page_chars(Image.fromarray(canvas), page)
    filled = [c for c in page.chars if c.char]
    assert len(filled) == len(expected), (
        f"全页期望 {len(expected)} 字，实得 {len(filled)} 字（净丢失 "
        f"{len(expected) - len(filled)} 字）"
    )


# ── 缺陷 C：细横笔画被并进上一个字（page_006 页码「四八二」）─────────────

def build_bars(bars: list[tuple[int, int]], width: int = 44, pad: int = 10):
    """按给定的 (y起, 高) 列表画横条，返回 (灰度图, 覆盖全部条的 line box)。

    不用字体渲染而是直接画条：真实缺陷依赖「二」两横一个 3px 一个 4px 的不对称
    （`_merge_thin_segments` 的 4.0 绝对下限使 3px 被并、4px 不被并，于是段数刚好
    等于字数，对齐层无从察觉），字体渲染出的笔画高度不可控，复现不出来。
    """
    top = bars[0][0] - pad
    bot = bars[-1][0] + bars[-1][1] + pad
    img = np.full((bot + pad, width + 2 * pad), 255, dtype=np.uint8)
    for y, h in bars:
        img[y:y + h, pad:pad + width] = 30
    box = {"x": float(pad - 2), "y": float(top), "w": float(width + 4), "h": float(bot - top)}
    return img, box


def test_thin_stroke_not_merged_into_previous_char():
    """细横笔画不得被并进上一个字：page_006 页码「四八二」的真实几何。

    投影正确切出 4 段（四16px / 八15px / 二上横3px / 二下横4px），但
    `_merge_thin_segments` 把 3px 的「二上横」无条件并进**上一段**（八），
    于是「八」的框涨到 h=32 吞掉二的上横，「二」只剩下横 h=4，看上去像「一」。
    段数被并成 3 恰好等于字数，对齐层察觉不到，必须在切分层修。
    """
    #            四            八            二上          二下
    bars = [(1251, 16), (1280, 15), (1309, 3), (1320, 4)]
    gray, box = build_bars(bars)
    line = LineBox(id="page_006l0075", box=box, text="四八二", conf=0.9, extra={"band": 0})
    page = PageResult(page="page_006", image="synthetic.png",
                      width=int(gray.shape[1]), height=int(gray.shape[0]), lines=[line])
    segment_page_chars(Image.fromarray(gray), page)
    got = sorted(page.chars, key=lambda c: c.box["y"])
    assert len(got) == 3, f"应得 3 个字框，实得 {len(got)}"
    # 每个字的实际墨迹范围：二 = 上下两横合起来
    ink = {"四": (1251, 1267), "八": (1280, 1295), "二": (1309, 1324)}
    for c in got:
        i0, i1 = ink[c.char]
        b0, b1 = c.box["y"], c.box["y"] + c.box["h"]
        assert i0 - 3 <= b0 and b1 <= i1 + 3, (
            f"{c.char!r} 的框 y=[{b0:.0f},{b1:.0f}] 超出该字墨迹范围 [{i0},{i1}]"
            f" —— 吞掉了相邻字的笔画"
        )
    assert got[2].box["h"] >= 10, (
        f"「二」的框高只有 {got[2].box['h']:.0f}px，只框到了一横（另一横被上一个字吞了）"
    )
