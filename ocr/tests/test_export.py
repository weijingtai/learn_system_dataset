"""gujiorc.core.export 导出测试（PLANS §6）。"""
import os
import sys
import tempfile

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "src")))

from gujiorc.core.models import PageResult, CharBox  # noqa: E402
from gujiorc.core.export import (  # noqa: E402
    page_to_text, gen_all_pages_text, gen_transcript_md, gen_tsv, export_common,
)


def make_page(page="page_001"):
    # 有序字框（已按阅读序排列）
    chars = [
        CharBox(id=f"{page}c0", box={"x":100,"y":0,"w":1,"h":1}, char="貴", orig_char="貴"),
        CharBox(id=f"{page}c1", box={"x":80,"y":0,"w":1,"h":1}, char="人", orig_char="人"),
        CharBox(id=f"{page}c2", box={"x":60,"y":0,"w":1,"h":1}, char="凢", orig_char="凢", is_rare=True),
        CharBox(id=f"{page}c3", box={"x":40,"y":0,"w":1,"h":1}, char="", orig_char=""),
    ]
    return PageResult(page=page, image="i.png", width=120, height=10, chars=chars)


def test_page_to_text_uses_char_and_square_for_unknown():
    p = make_page()
    txt = page_to_text(p)
    assert txt == "貴人凢□"   # 未识别 → □


def test_gen_all_pages_text():
    res = gen_all_pages_text([make_page("page_001"), make_page("page_002")])
    # 纯文本拼接，不含页标记，每页一行
    lines = res.splitlines()
    assert len(lines) == 2
    assert all("貴" in l and "凢" in l and "□" in l for l in lines)


def test_gen_transcript_md_format():
    res = gen_transcript_md([make_page()], pageno_start=1)
    assert "<!-- p0001 -->" in res
    assert "貴人凢□" in res


def test_gen_tsv_columns():
    res = gen_tsv([make_page()])
    lines = res.splitlines()
    assert lines[0].startswith("page\tchar_id")
    assert "page_001c0" in res
    assert "貴" in res


def test_export_common_writes_files():
    with tempfile.TemporaryDirectory() as tmp:
        outs = export_common([make_page()], tmp, prefix="book")
        for fmt in ("json", "txt", "tsv", "transcript"):
            assert fmt in outs, f"缺少导出 {fmt}"
            assert outs[fmt].exists()
        txt = outs["txt"].read_text(encoding="utf-8")
        assert "貴" in txt


def test_gen_transcript_no_simplification():
    """繁体保持原字形（transcript 不允许简繁转换）。"""
    p = make_page()
    res = gen_transcript_md([p])
    assert "貴" in res
    assert "贵" not in res.split("<!--")[0][:20]  # 首页正文不应出现简体"贵"