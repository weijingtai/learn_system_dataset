"""gujiorc.core.anomaly 测试。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gujiorc.core.anomaly import register_anomaly, list_anomalies


def test_register_and_list(monkeypatch, tmp_path):
    monkeypatch.setenv("OCR_ROOT", str(tmp_path))
    p1 = register_anomaly(page="page_003", image="star_chart.png", layout_type="star_chart",
                          det_box_count=206, note="圆弧排布，当前识别乱序+低置信")
    assert p1.exists()
    items = list_anomalies()
    assert len(items) == 1
    assert items[0]["layout_type"] == "star_chart"
    assert items[0]["det_box_count"] == 206


def test_filter_page(monkeypatch, tmp_path):
    monkeypatch.setenv("OCR_ROOT", str(tmp_path))
    register_anomaly(page="page_003", image="a.png", layout_type="star_chart")
    register_anomaly(page="page_004", image="b.png", layout_type="circular")
    hits = list_anomalies(page="page_003")
    assert len(hits) == 1
    assert hits[0]["page"] == "page_003"


def test_last(monkeypatch, tmp_path):
    monkeypatch.setenv("OCR_ROOT", str(tmp_path))
    for i in range(5):
        register_anomaly(page=f"p{i}", image=f"{i}.png", layout_type="star_chart")
    items = list_anomalies(last=2)
    assert len(items) == 2
    assert items[0]["page"] == "p3"
    assert items[1]["page"] == "p4"


def test_missing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("OCR_ROOT", str(tmp_path))
    assert list_anomalies() == []

# ── 异常版面判定（星盘/环形等非行列排布页）────────────────────────────────

from gujiorc.core.anomaly import assess_layout  # noqa: E402
from gujiorc.core.models import LineBox, PageResult  # noqa: E402


def _page(specs, page="page_010"):
    """specs: [(text, w, h, conf), ...] → PageResult（只用到 lines）。"""
    lines = [
        LineBox(id=f"{page}c{i:04d}", box={"x": 10.0 + i * 5, "y": 10.0 + i * 5,
                                           "w": float(w), "h": float(h)},
                text=t, conf=c, extra={"band": 0})
        for i, (t, w, h, c) in enumerate(specs)
    ]
    return PageResult(page=page, image=f"{page}.png", width=1203, height=1654, lines=lines)


def test_normal_vertical_page_not_flagged():
    """正常竖排页不得被误判。取《三辰通载》page_004~008 的实测轮廓：
    均置信 0.96、低置信行 0~2%、单字行 0~6%、横排框 0~3%。"""
    specs = [("水星廟旺樂順留伏逆", 40, 226, 0.96)] * 80
    specs += [("十", 36, 19, 0.95)] * 2        # 单字行 2.4%
    specs += [("11", 29, 21, 0.95)]           # 横排框 1.2%
    assert assess_layout(_page(specs, "page_004")) is None


def test_star_chart_page_flagged():
    """星盘/盘面页必须被登记。取 page_010 的实测轮廓：
    均置信 0.63、低置信行 45%、单字行 29%、横排框 13%。"""
    specs = [("水星廟旺", 40, 120, 0.95)] * 60
    specs += [("口", 30, 28, 0.31)] * 34       # 低置信单字
    specs += [("木火", 60, 25, 0.28)] * 15     # 横排框 + 低置信
    hit = assess_layout(_page(specs, "page_010"))
    assert hit is not None, "盘面页未被判为异常版面 → 垃圾识别会静默进入语料"
    assert hit["layout_type"] == "irregular_layout"
    assert len(hit["signals"]) >= 2, f"应有多个信号命中，实得 {hit['signals']}"


def test_empty_page_flagged_as_no_text():
    """一个字都没识别出的页也要登记：可能是空白页，也可能是未处理的纯图页，
    需要人工确认，不能静默跳过。"""
    hit = assess_layout(_page([], "page_002"))
    assert hit is not None and hit["layout_type"] == "no_text"


def test_single_signal_does_not_flag():
    """只有一个信号命中不登记——避免正常页因个别噪声被反复误报。"""
    # 只有横排框偏多，其余全正常
    specs = [("水星廟旺樂順", 40, 180, 0.96)] * 85
    specs += [("木火土金水", 120, 25, 0.95)] * 15   # 横排框 15%
    assert assess_layout(_page(specs, "page_004")) is None


def test_empty_string_page_filter_means_no_filter(monkeypatch, tmp_path):
    """空串必须当「不过滤」：CLI 的 --page 默认值是 ""，若按字面过滤，
    写入侧明明登记了、读取侧却永远显示「暂无异常记录」。"""
    monkeypatch.setenv("OCR_ROOT", str(tmp_path))
    register_anomaly(page="page_010", image="chart.png", layout_type="irregular_layout")
    assert len(list_anomalies(page="")) == 1
    assert len(list_anomalies(layout_type="")) == 1
    assert len(list_anomalies(page="page_010")) == 1
    assert len(list_anomalies(page="page_001")) == 0
