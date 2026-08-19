"""gujiorc.core.report 质量报告测试（M6_）。"""
import os
import sys

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "src")))

from gujiorc.core.models import PageResult, CharBox, STATUS_CORRECTED, STATUS_UNRECOGNIZED  # noqa: E402
from gujiorc.core.report import page_stats, book_report, render_report_md  # noqa: E402


def make_page(page="page_001"):
    chars = [
        CharBox(id=f"{page}c0", box={"x":0,"y":0,"w":1,"h":1}, char="貴", conf=0.9, status="pending"),
        CharBox(id=f"{page}c1", box={"x":2,"y":0,"w":1,"h":1}, char="凢", conf=0.8,
                is_rare=True, rare_reason="not_in_common_set"),
        CharBox(id=f"{page}c2", box={"x":4,"y":0,"w":1,"h":1}, char="", conf=0.3,
                is_rare=True, rare_reason="low_conf", status=STATUS_UNRECOGNIZED),
        CharBox(id=f"{page}c3", box={"x":6,"y":0,"w":1,"h":1}, char="凡",
                orig_char="凢", status=STATUS_CORRECTED,
                mapping={"from":"凢","target":"凡","source":"manual"}),
    ]
    return PageResult(page=page, image="i.png", width=10, height=10, chars=chars)


def test_page_stats_counts():
    s = page_stats(make_page())
    assert s["total"] == 4
    assert s["rare"] == 2          # 凢(not_common) + 空(low_conf)
    assert s["low_conf"] == 1
    assert s["not_common"] == 1
    assert s["unrecognized"] == 1  # 空字
    assert s["corrected"] == 1     # 凢→凡
    assert s["mapped"] == 1


def test_book_report_aggregates():
    r = book_report([make_page("page_001"), make_page("page_002")])
    s = r["summary"]
    assert s["pages_count"] == 2
    assert s["total"] == 8
    assert s["corrected"] == 2


def test_render_md_contains_key_metrics():
    r = book_report([make_page()])
    md = render_report_md(r, book="测试书")
    assert "测试书" in md
    assert "总字数" in md
    assert "低置信度" in md
    assert "page_001" in md