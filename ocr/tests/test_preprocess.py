"""背面透印字抹除（gujiorc.ocr.preprocess）测试。

用真实测得的墨色分布构造样本：真墨灰度 40（实测 32~88），
透印灰度 210（实测 116~240）。
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "src")))

from gujiorc.core.models import LineBox, PageResult  # noqa: E402
from gujiorc.ocr.preprocess import (  # noqa: E402
    DEFAULT_BLEED_THRESH, suppress_bleed_through,
)
from gujiorc.ocr.segment import segment_page_chars  # noqa: E402

REAL_INK = 40    # 真墨：实测 32~88
GHOST_INK = 210  # 背面透印：实测 116~240


def make_page(width=200, height=300):
    """左半列真墨横条，右半列透印横条。"""
    img = np.full((height, width), 250, dtype=np.uint8)
    for y in range(20, 260, 40):
        img[y:y + 20, 30:70] = REAL_INK     # 真墨列
        img[y:y + 20, 130:170] = GHOST_INK  # 透印列
    return img


def test_ghost_ink_erased():
    """透印像素必须被推成纯白。"""
    img = make_page()
    out, _ = suppress_bleed_through(img)
    assert not (out == GHOST_INK).any(), "透印像素仍在图上"
    assert (out[:, 130:170] == 255).all(), "透印列未被抹成纯白"


def test_real_ink_untouched():
    """真墨像素必须一个不动（纸张被推白是预期的，不算改动墨迹）。"""
    img = make_page()
    out, _ = suppress_bleed_through(img)
    ink = img == REAL_INK
    assert ink.any(), "本用例前提：图上有真墨"
    assert (out[ink] == REAL_INK).all(), "真墨像素被改动了"
    assert (out == REAL_INK).sum() == ink.sum(), "真墨像素数变了"


def test_disabled_by_zero_thresh():
    """thresh=0 时原样返回，不做任何修改（供淡印本/褪色本关掉）。"""
    img = make_page()
    out, stats = suppress_bleed_through(img, thresh=0)
    assert (out == img).all()
    assert stats["erased"] == 0.0


def test_erased_ratio_counts_only_ghost_ink_not_paper():
    """报告的抹除比例只统计幽灵墨，不把「纸张变纯白」算成抹墨。

    这个比例是淡印本的告警信号，若把 70% 的纸张算进去就永远看不出异常。
    """
    img = make_page()
    _, stats = suppress_bleed_through(img)
    ghost_frac = (img == GHOST_INK).mean()
    assert stats["erased"] == pytest.approx(ghost_frac, abs=1e-6), (
        f"报告抹除 {stats['erased']:.4f}，实际幽灵墨占 {ghost_frac:.4f}"
    )


def test_faded_book_ink_survives_lower_thresh():
    """淡印本（真墨 150）调低阈值后正文不被抹掉。"""
    img = np.full((100, 100), 250, dtype=np.uint8)
    img[20:40, 20:40] = 150
    erased, _ = suppress_bleed_through(img, thresh=DEFAULT_BLEED_THRESH)
    assert (erased[20:40, 20:40] == 255).all(), "本用例前提：默认阈值会抹掉 150 的墨"
    kept, _ = suppress_bleed_through(img, thresh=180)
    assert (kept[20:40, 20:40] == 150).all(), "调高阈值后淡墨仍被抹掉"


def test_ghost_column_yields_no_char_boxes():
    """抹除后，纯透印的那一列不应再产出任何字框。"""
    img = make_page()
    out, _ = suppress_bleed_through(img)
    line = LineBox(
        id="page_001l0000",
        box={"x": 125.0, "y": 15.0, "w": 50.0, "h": 250.0},
        text="一二三四五六", conf=0.9, extra={"band": 0},
    )
    page = PageResult(page="page_001", image="synthetic.png",
                      width=int(out.shape[1]), height=int(out.shape[0]), lines=[line])
    segment_page_chars(out, page)
    # 抹除后该区域全白，投影无信号 → 只能兜底等分，不该有任何墨迹段
    from gujiorc.ocr.segment import segment_block
    assert not segment_block(out, line.box), "透印列抹除后仍切出墨迹段"


def test_kept_ink_is_the_faded_book_alarm():
    """kept_ink 才是淡印本的告警信号：正常页留下大量真墨，淡印本几乎不留。

    不能用 erased 当告警——真笔画的抗锯齿边缘也落在被抹的灰度带里，
    《三辰通载》正常页实测 erased 就有 3%~14%，做阈值必然全页误报。
    """
    from gujiorc.ocr.preprocess import MIN_KEPT_INK
    normal = make_page()                      # 真墨 40 + 透印 210
    _, s_normal = suppress_bleed_through(normal)
    faded = np.full((300, 200), 250, dtype=np.uint8)
    for y in range(20, 260, 40):
        faded[y:y + 20, 30:70] = 150          # 淡印本：真墨也在被抹的带里
    _, s_faded = suppress_bleed_through(faded)
    assert s_normal["kept_ink"] > MIN_KEPT_INK, "正常页被误判为淡印本"
    assert s_faded["kept_ink"] < MIN_KEPT_INK, "淡印本未被识别出来（会静默抹掉正文）"
