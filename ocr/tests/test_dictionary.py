"""gujiorc.rare.dictionary 生僻字查询/拆解测试。"""
import os
import sys

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "src")))

from gujiorc.rare.dictionary import lookup_char, decompose_char, query_rare  # noqa: E402


def test_lookup_builtin_technique_char():
    """术数生僻字内置字典应返回读音/部首/笔画。"""
    info = lookup_char("孛")
    assert info["reading"] == "bèi"
    assert info["radical"] == "子"
    assert info["strokes"] == 7
    assert "月孛" in info["definition"]


def test_lookup_returns_unicode_always():
    """即使无内置数据，也应给出 Unicode 编码。"""
    info = lookup_char("龘")
    assert info["unicode"] == "U+9F98"
    assert "name" in info


def test_decompose_contains_structure():
    result = decompose_char("炁")
    assert result["radical"] == "火"
    assert result["reading"] == "qì"


def test_query_rare_integration():
    result = query_rare("羅")
    assert result["radical"] == "网"
    assert result["reading"] == "luó"