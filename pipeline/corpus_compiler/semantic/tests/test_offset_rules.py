"""act/04 语义窗口选择（select_text_windows）具名用例。

synthetic_fixture: true —— 输入全部为内联合成数据，不读取、不写入任何 fixture 目录（P4）。
"""

import hashlib
import unittest

from pipeline.corpus_compiler.semantic.offset_rules import select_text_windows

WORK = "qianyuan"
EDITION = "ed01"
RAW_REV = "rev_" + "0" * 32
CLEAN_REV = "rev_" + "1" * 32

# 阈值（默认 model_min_chars=12）两侧的合成片段
SHORT_TEXT = "短句。"  # 3 字符，不足阈值
LONG_TEXT_A = "天地玄黄宇宙洪荒日月盈昃"  # 12 字符，恰好达阈值
LONG_TEXT_B = "寒来暑往秋收冬藏闰余成岁"  # 12 字符


def make_structural_span(*, sequence, text, cleaned_start, raw_start):
    """构造一条结构 Span（键序与 corpus_spans 契约一致）。"""
    cleaned_end = cleaned_start + len(text)
    raw_end = raw_start + len(text)
    quote_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "span_id": "ss_%s_%s_o%07d" % (WORK, EDITION, raw_start),
        "sequence": sequence,
        "start_offset": cleaned_start,
        "end_offset": cleaned_end,
        "text": text,
        "quote_sha256": quote_sha256,
        "evidence_level": "offset_level",
        "source_anchor": {
            "raw_text_revision_id": RAW_REV,
            "raw_start": raw_start,
            "raw_end": raw_end,
            "cleaned_text_revision_id": CLEAN_REV,
            "start_offset": cleaned_start,
            "end_offset": cleaned_end,
            "quote_sha256": quote_sha256,
        },
    }


def make_three_spans():
    """长-短-长三条结构 Span（清洗文本偏移首尾相连）。"""
    span_a = make_structural_span(
        sequence=1, text=LONG_TEXT_A, cleaned_start=0, raw_start=0
    )
    span_short = make_structural_span(
        sequence=2,
        text=SHORT_TEXT,
        cleaned_start=len(LONG_TEXT_A),
        raw_start=len(LONG_TEXT_A),
    )
    span_b = make_structural_span(
        sequence=3,
        text=LONG_TEXT_B,
        cleaned_start=len(LONG_TEXT_A) + len(SHORT_TEXT),
        raw_start=len(LONG_TEXT_A) + len(SHORT_TEXT),
    )
    return [span_a, span_short, span_b]


class TestSelectTextWindows(unittest.TestCase):
    """窗口筛选：长度 >= model_min_chars 的片段成为模型窗口，编号从 1 递增。"""

    def test_select_text_windows_threshold_filtering(self):
        """短片段不入选、长片段入选，且编号在入选序列上从 w001 连续递增。"""
        windows = select_text_windows(make_three_spans())
        self.assertEqual([w["text"] for w in windows], [LONG_TEXT_A, LONG_TEXT_B])
        self.assertEqual(
            [w["window_id"] for w in windows],
            ["%s_w001" % WORK, "%s_w002" % WORK],
        )

        # 阈值抬高到 13 后，两条 12 字符片段均不入选
        self.assertEqual(select_text_windows(make_three_spans(), model_min_chars=13), [])

        # 阈值降到 12 时短片段仍不入选（3 < 12）
        strict = select_text_windows(make_three_spans(), model_min_chars=12)
        self.assertNotIn(SHORT_TEXT, [w["text"] for w in strict])

    def test_select_text_windows_empty_input(self):
        """空 spans 列表返回空窗口列表（不抛异常）。"""
        self.assertEqual(select_text_windows([]), [])

    def test_select_text_windows_keys_and_order(self):
        """每项键序严格为 window_id, span_id, text, text_sha256, raw_start, raw_end。"""
        spans = make_three_spans()
        windows = select_text_windows(spans)
        self.assertEqual(len(windows), 2)

        first = windows[0]
        self.assertEqual(
            list(first.keys()),
            [
                "window_id",
                "span_id",
                "text",
                "text_sha256",
                "raw_start",
                "raw_end",
            ],
        )
        self.assertEqual(first["span_id"], spans[0]["span_id"])
        self.assertEqual(first["text"], LONG_TEXT_A)
        self.assertEqual(
            first["text_sha256"],
            hashlib.sha256(LONG_TEXT_A.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(first["raw_start"], spans[0]["source_anchor"]["raw_start"])
        self.assertEqual(first["raw_end"], spans[0]["source_anchor"]["raw_end"])

        second = windows[1]
        self.assertEqual(second["span_id"], spans[2]["span_id"])
        self.assertEqual(
            second["text_sha256"],
            hashlib.sha256(LONG_TEXT_B.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(second["raw_start"], spans[2]["source_anchor"]["raw_start"])
        self.assertEqual(second["raw_end"], spans[2]["source_anchor"]["raw_end"])


if __name__ == "__main__":
    unittest.main()
