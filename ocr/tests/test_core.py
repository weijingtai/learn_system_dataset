"""gujiorc 核心逻辑测试（不依赖 PaddleOCR）。

覆盖：数据模型序列化、生僻字判定、全字索引查询/去重、分组归并、进度汇报、路径。
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "src")))

from gujiorc.core.models import (  # noqa: E402
    CharBox, LineBox, PageResult, RareChar, GlyphGroup,
    RARE_NOT_IN_COMMON, RARE_LOW_CONF,
)
from gujiorc.rare.detector import (  # noqa: E402
    build_common_set, detect_rare_chars, build_rare_list, parse_char,
)
from gujiorc.index.fulltext import CharIndex  # noqa: E402
from gujiorc.core.progress import ProgressReporter  # noqa: E402


def make_page(page="page_001", book="book_qt01") -> PageResult:
    """构造测试页（含常见字、生僻字、低置信度字）。"""
    chars = [
        CharBox(id="page_001c0000", box={"x": 0, "y": 0, "w": 10, "h": 10},
                char="得", conf=0.98, status="pending", extra={"band": 0}),
        CharBox(id="page_001c0001", box={"x": 20, "y": 0, "w": 10, "h": 10},
                char="孛", conf=0.95, status="pending", extra={"band": 0}),
        CharBox(id="page_001c0002", box={"x": 40, "y": 0, "w": 10, "h": 10},
                char="敬", conf=0.30, status="pending", extra={"band": 0}),
    ]
    return PageResult(page=page, book=book, image="img.png", width=100, height=100, chars=chars)


# ---------------- 字节模型序列化 ----------------

def test_char_box_roundtrip():
    c = CharBox(id="x", box={"x": 1, "y": 2, "w": 3, "h": 4}, char="孛")
    d = c.to_dict()
    c2 = CharBox.from_dict(d)
    assert c2.box == {"x": 1.0, "y": 2.0, "w": 3.0, "h": 4.0}
    assert c2.char == "孛"


def test_page_roundtrip():
    p = make_page()
    d = p.to_dict()
    p2 = PageResult.from_dict(d)
    assert len(p2.chars) == 3
    assert p2.chars[1].char == "孛"
    assert p2.chars[1].box["w"] == 10.0


# ---------------- 生僻字判定 ----------------

def test_parse_char_filters_non_hanzi():
    assert parse_char("得孛敬。") == "得孛敬"
    assert parse_char("1234") == ""


def test_detect_rare_chars():
    p = make_page()
    common = build_common_set()
    detect_rare_chars(p, common)
    chars = {c.char: c for c in p.chars}
    # "得" 在常用集 → 非生僻
    assert not chars["得"].is_rare
    # "孛" 在术数白名单 → 非生僻（白名单免除误判）
    assert not chars["孛"].is_rare, "孛应在白名单中"
    # 编译一个字不在常用集也不在白名单
    p2 = make_page()
    p2.chars[1].char = "龘"  # 生僻字
    detect_rare_chars(p2, common)
    assert p2.chars[1].is_rare
    assert p2.chars[1].rare_reason == RARE_NOT_IN_COMMON


def test_low_conf_kept():
    p = make_page()
    common = build_common_set()
    detect_rare_chars(p, common)
    # 低置信度字已有标记，保留
    assert p.chars[2].is_rare
    assert p.chars[2].rare_reason == RARE_LOW_CONF


# ---------------- 生僻字清单汇总 ----------------

def test_build_rare_list():
    p = make_page()
    # 造两个生僻字出现
    p.chars[1].char = "龘"
    detect_rare_chars(p, build_common_set())
    rare_list = build_rare_list([p])
    assert any(r.char == "龘" for r in rare_list)


# ---------------- 全字索引 ----------------

def test_char_index_query_and_dups():
    with tempfile.TemporaryDirectory() as tmp:
        idx = CharIndex(db_path=os.path.join(tmp, "index.db"))
        p1 = make_page("page_001")
        # 让 "得" 在 page_001 和 page_002 都出现
        p2 = make_page("page_002")
        idx.rebuild_from_page(p1)
        idx.rebuild_from_page(p2)

        rows = idx.query_char("得")
        assert len(rows) == 2
        assert {r["page"] for r in rows} == {"page_001", "page_002"}

        dups = idx.duplicates(min_count=2)
        assert any(d["char"] == "得" and d["cnt"] == 2 for d in dups)
        idx.close()


# ---------------- 分组归并 ----------------

def test_groups_create_define():
    groups = []
    g = create_group_names(groups, "生僻字A", ["p1c1", "p1c2"])
    assert g.id in {x.id for x in groups}
    define_group_names(groups, g.id, char="孛")
    assert resolve_char_names(groups, "p1c1") == "孛"


def create_group_names(groups, name, samples):
    from gujiorc.rare.groups import create_group
    return create_group(groups, name, samples)


def define_group_names(groups, gid, char):
    from gujiorc.rare.groups import define_group
    define_group(groups, gid, char=char)


def resolve_char_names(groups, cid):
    from gujiorc.rare.groups import resolve_char
    return resolve_char(groups, cid)


# ---------------- 进度汇报 ----------------

def test_progress_reports_every_5(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["OCR_ROOT"] = tmp
        rep = ProgressReporter(total=100, report_every=5.0,
                               progress_path=os.path.join(tmp, "progress.json"))
        for i in range(100):
            rep.tick(f"page_{i}")
        rep.finish()
        out = capsys.readouterr().out
        # 应包含 5%,10%,...100% 多处进度输出
        assert "识别进度" in out
        assert "100.0%" in out
        # progress.json 应存在且 status=done
        import json
        with open(os.path.join(tmp, "progress.json"), encoding="utf-8") as f:
            data = json.load(f)
        assert data["status"] == "done"
        assert data["done"] == 100
        del os.environ["OCR_ROOT"]


# ---------------- 数据模型 extra ----------------

def test_charbox_extra():
    c = CharBox(id="x", box={"x": 0, "y": 0, "w": 1, "h": 1}, char="字")
    c.extra["band"] = 2
    assert c.to_dict()["extra"]["band"] == 2
    c2 = CharBox.from_dict(c.to_dict())
    assert c2.extra["band"] == 2