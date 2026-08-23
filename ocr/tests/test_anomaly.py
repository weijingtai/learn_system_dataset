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