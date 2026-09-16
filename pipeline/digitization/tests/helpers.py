"""M2 清洗测试辅助工具（synthetic_fixture: true）。"""


def sample_dirty_text() -> str:
    r"""返回包含多种清洗发现的合成测试文本（synthetic_fixture: true）。

    包含：
    - replacement_char: '?' 或 '□'
    - private_use_area: '\ue000'
    - escape_residue: r'\-' 或 r'\['
    - control_char: '\u200b' (零宽字符)
    - variant_mixed: 繁体与简体混用
    - suspected_error: 常见形近误字（如 '日' 与 '曰'）
    """
    return (
        "太极图说\n"
        "天地之初，太极肇判。?\n"  # replacement_char
        "此字为私用区\ue000测试。\n"  # private_use_area
        "转义残留验证：\\- 以及 \\[。\n"  # escape_residue
        "零宽空白\u200b测试。\n"  # control_char
        "繁簡混杂测试：繁體字与简体字混用。\n"  # variant_mixed
        "形近误字：子曰与子日。\n"  # suspected_error
    )


def sample_clean_text() -> str:
    """返回无任何清洗问题的纯净合成文本（synthetic_fixture: true）。"""
    return "太极图说\n天地之初，太极肇判。阴阳运行，万物化生。"
