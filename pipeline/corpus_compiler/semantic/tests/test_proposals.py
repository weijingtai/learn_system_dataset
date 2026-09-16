"""act/04 提议解析与比较（parse_proposal / compare_proposals）具名用例。

synthetic_fixture: true —— 输入全部为内联合成数据（含故意伪造的模型 text 字段）。
"""

import json
import unittest

from pipeline.corpus_compiler.semantic.proposals import (
    compare_proposals,
    parse_proposal,
)

WINDOW_TEXT = "天地玄黄宇宙洪荒日月盈昃"  # 12 字符
MODEL_LIE = "模型伪造的原文不得采信"


def make_response(segments, *, reason_prefix="r", with_model_text=False):
    """把 [(start, end), ...] 序列化为模型响应字节。"""
    items = []
    for index, (start, end) in enumerate(segments):
        item = {
            "start_offset": start,
            "end_offset": end,
            "reason": "%s%d" % (reason_prefix, index),
        }
        if with_model_text:
            item["text"] = MODEL_LIE
        items.append(item)
    return json.dumps({"segments": items}, ensure_ascii=False).encode("utf-8")


class TestParseProposal(unittest.TestCase):
    """提议解析：只采信偏移，片段原文一律由程序从 window_text 切取。"""

    def test_parse_proposal_valid_single_segment(self):
        """单片段、完整覆盖窗口时 valid=True 且 segments 为该区间。"""
        parsed = parse_proposal(make_response([(0, 12)]), WINDOW_TEXT)
        self.assertTrue(parsed["valid"])
        self.assertIsNone(parsed["error"])
        self.assertEqual(parsed["segments"], [[0, 12]])
        self.assertEqual(parsed["reasons"], ["r0"])

    def test_parse_proposal_valid_multi_segment(self):
        """多片段、首尾相连且完整覆盖时 valid=True。"""
        parsed = parse_proposal(
            make_response([(0, 4), (4, 8), (8, 12)]), WINDOW_TEXT
        )
        self.assertTrue(parsed["valid"])
        self.assertIsNone(parsed["error"])
        self.assertEqual(parsed["segments"], [[0, 4], [4, 8], [8, 12]])
        self.assertEqual(parsed["reasons"], ["r0", "r1", "r2"])
        self.assertEqual(WINDOW_TEXT[0:4], "天地玄黄")
        self.assertEqual(WINDOW_TEXT[8:12], "日月盈昃")

    def test_parse_proposal_ignores_model_text_field(self):
        """模型自带的 text 字段一律丢弃，返回结果只含偏移。"""
        parsed = parse_proposal(
            make_response([(0, 4), (4, 12)], with_model_text=True), WINDOW_TEXT
        )
        self.assertTrue(parsed["valid"])
        self.assertEqual(parsed["segments"], [[0, 4], [4, 12]])
        self.assertEqual(
            list(parsed.keys()), ["valid", "segments", "reasons", "error"]
        )
        self.assertNotIn(MODEL_LIE, json.dumps(parsed, ensure_ascii=False))
        self.assertNotIn("text", parsed)
        self.assertNotIn(MODEL_LIE, parsed["reasons"])

    def test_parse_proposal_detects_gap_and_overlap(self):
        """缺口、重叠、越界、覆盖不全、空列表、非 JSON 等各自给出对应 error。"""
        gap = parse_proposal(make_response([(0, 4), (6, 12)]), WINDOW_TEXT)
        self.assertFalse(gap["valid"])
        self.assertEqual(gap["error"], "gap")

        overlap = parse_proposal(make_response([(0, 6), (4, 12)]), WINDOW_TEXT)
        self.assertFalse(overlap["valid"])
        self.assertEqual(overlap["error"], "overlap")

        coverage = parse_proposal(make_response([(0, 4)]), WINDOW_TEXT)
        self.assertFalse(coverage["valid"])
        self.assertEqual(coverage["error"], "coverage")

        out_of_range = parse_proposal(make_response([(0, 99)]), WINDOW_TEXT)
        self.assertFalse(out_of_range["valid"])
        self.assertEqual(out_of_range["error"], "range")

        empty = parse_proposal(make_response([]), WINDOW_TEXT)
        self.assertFalse(empty["valid"])
        self.assertEqual(empty["error"], "empty")

        bad_type = parse_proposal(
            json.dumps(
                {"segments": [{"start_offset": 0, "end_offset": "12"}]}
            ).encode("utf-8"),
            WINDOW_TEXT,
        )
        self.assertFalse(bad_type["valid"])
        self.assertEqual(bad_type["error"], "type")

        bad_shape = parse_proposal(b'{"foo": 1}', WINDOW_TEXT)
        self.assertFalse(bad_shape["valid"])
        self.assertEqual(bad_shape["error"], "shape")

        bad_json = parse_proposal(b"{not json", WINDOW_TEXT)
        self.assertFalse(bad_json["valid"])
        self.assertEqual(bad_json["error"], "json")


class TestCompareProposals(unittest.TestCase):
    """提议比较：边界完全一致方可 cross_model_agreed，否则 disputed。"""

    def test_compare_proposals_agreed(self):
        """A、B 均有效且边界完全一致 → agreed，segments 取 A 的切分。"""
        parsed_a = parse_proposal(
            make_response([(0, 4), (4, 12)], reason_prefix="a"), WINDOW_TEXT
        )
        parsed_b = parse_proposal(
            make_response([(0, 4), (4, 12)], reason_prefix="b"), WINDOW_TEXT
        )
        compared = compare_proposals(parsed_a, parsed_b)
        self.assertEqual(
            list(compared.keys()), ["status", "reason", "segments"]
        )
        self.assertEqual(compared["status"], "agreed")
        self.assertIsNone(compared["reason"])
        self.assertEqual(compared["segments"], [[0, 4], [4, 12]])

    def test_compare_proposals_disputed_on_mismatch(self):
        """边界不一致 → boundary_mismatch；任一提议非法 → proposal_invalid。"""
        parsed_a = parse_proposal(make_response([(0, 4), (4, 12)]), WINDOW_TEXT)
        parsed_b = parse_proposal(make_response([(0, 6), (6, 12)]), WINDOW_TEXT)
        mismatch = compare_proposals(parsed_a, parsed_b)
        self.assertEqual(mismatch["status"], "disputed")
        self.assertEqual(mismatch["reason"], "boundary_mismatch")
        self.assertIsNone(mismatch["segments"])

        parsed_invalid = parse_proposal(make_response([(0, 99)]), WINDOW_TEXT)
        invalid = compare_proposals(parsed_a, parsed_invalid)
        self.assertEqual(invalid["status"], "disputed")
        self.assertEqual(invalid["reason"], "proposal_invalid")
        self.assertIsNone(invalid["segments"])


if __name__ == "__main__":
    unittest.main()
