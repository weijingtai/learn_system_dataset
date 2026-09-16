"""Unit tests for offset anchor computation and deterministic patch mapping (Ruling 78, act/00).

synthetic_fixture: true
"""

import copy
import hashlib
import re
import unittest

from pipeline.corpus_compiler.offset_anchors import (
    format_semantic_span_id,
    format_source_span_id,
    make_offset_anchor,
    map_cleaned_to_raw,
    map_raw_to_cleaned,
    verify_anchor,
)


class TestOffsetAnchors(unittest.TestCase):
    """测试偏移锚点纯函数与补丁双向换算（act/00）。"""

    def test_format_source_span_id_valid(self):
        """测试合法的 SourceSpan ID 格式生成与正则匹配。"""
        span_id = format_source_span_id("qianyuan", "ed01", 128)
        self.assertEqual(span_id, "ss_qianyuan_ed01_o0000128")
        self.assertRegex(span_id, r"^ss_[a-z][a-z0-9_]*_ed[0-9]{2}_o[0-9]{7}$")

    def test_format_source_span_id_zero_padded_7_digits(self):
        """测试 SourceSpan ID 偏移量固定 7 位零填充。"""
        span_id_zero = format_source_span_id("work_a", "ed02", 0)
        self.assertEqual(span_id_zero, "ss_work_a_ed02_o0000000")
        span_id_large = format_source_span_id("work_a", "ed02", 1234567)
        self.assertEqual(span_id_large, "ss_work_a_ed02_o1234567")

    def test_format_source_span_id_rejects_negative_offset_SCH_002(self):
        """测试负数偏移抛出 ValueError('SCH_002: ...')。"""
        with self.assertRaises(ValueError) as ctx:
            format_source_span_id("qianyuan", "ed01", -1)
        self.assertIn("SCH_002", str(ctx.exception))

    def test_format_source_span_id_rejects_invalid_edition_SCH_002(self):
        """测试非法 edition 或 work 格式抛出 ValueError('SCH_002: ...')。"""
        with self.assertRaises(ValueError) as ctx:
            format_source_span_id("qianyuan", "v1", 10)
        self.assertIn("SCH_002", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx2:
            format_source_span_id("Invalid-Work", "ed01", 10)
        self.assertIn("SCH_002", str(ctx2.exception))

    def test_format_semantic_span_id_valid(self):
        """测试合法的 SemanticSpan ID 格式生成。"""
        sem_id = format_semantic_span_id("qianyuan", "ed01", 256)
        self.assertEqual(sem_id, "sem_qianyuan_ed01_o0000256")
        self.assertRegex(sem_id, r"^sem_[a-z][a-z0-9_]*_ed[0-9]{2}_o[0-9]{7}$")

    def test_format_semantic_span_id_prefix_strictly_sem(self):
        """断言前缀恒以 sem_ 起头，绝无第三方前缀（P8 护栏）。"""
        sem_id = format_semantic_span_id("zhouyi", "ed99", 1024)
        self.assertTrue(sem_id.startswith("sem_"))
        self.assertFalse(sem_id.startswith("ss_"))
        self.assertFalse(sem_id.startswith("span_"))
        self.assertFalse(sem_id.startswith("frag_"))

    def test_map_raw_to_cleaned_without_patches(self):
        """无补丁时偏移严格恒等。"""
        patches = []
        c_start, c_end = map_raw_to_cleaned(patches, 10, 30)
        self.assertEqual((c_start, c_end), (10, 30))

    def test_map_raw_to_cleaned_with_single_replacement_patch(self):
        """单个替换补丁下前后及内部偏移换算。"""
        # 原始文本在 [10, 15) 被替换为清洗文本 [10, 13)（减少 2 字符）
        patches = [
            {
                "patch_id": "patch_001",
                "raw_start": 10,
                "raw_end": 15,
                "cleaned_start": 10,
                "cleaned_end": 13,
                "action": "patched",
                "basis": "CTP",
            }
        ]
        # 补丁前的区间不变
        self.assertEqual(map_raw_to_cleaned(patches, 0, 5), (0, 5))
        # 补丁自身的区间换算
        self.assertEqual(map_raw_to_cleaned(patches, 10, 15), (10, 13))
        # 补丁后的区间整体左移 2
        self.assertEqual(map_raw_to_cleaned(patches, 20, 30), (18, 28))

    def test_map_raw_to_cleaned_with_insertion_and_deletion_patches(self):
        """包含插入（raw_len < cleaned_len）与删除（raw_len > cleaned_len）的多补丁映射。"""
        patches = [
            # 删除 5 字符（raw [10, 15) -> cleaned [10, 10)）
            {
                "patch_id": "patch_001",
                "raw_start": 10,
                "raw_end": 15,
                "cleaned_start": 10,
                "cleaned_end": 10,
                "action": "deletion",
                "basis": "watermark",
            },
            # 插入 3 字符（raw [25, 25) -> cleaned [20, 23)）
            {
                "patch_id": "patch_002",
                "raw_start": 25,
                "raw_end": 25,
                "cleaned_start": 20,
                "cleaned_end": 23,
                "action": "insertion",
                "basis": "CTP",
            },
        ]
        # 跨越两个补丁的区间测试
        # raw 0..5 -> cleaned 0..5 (before all)
        self.assertEqual(map_raw_to_cleaned(patches, 0, 5), (0, 5))
        # raw 15..20 (between patches) -> cleaned 10..15 (shifted by -5)
        self.assertEqual(map_raw_to_cleaned(patches, 15, 20), (10, 15))
        # raw 30..40 (after all patches) -> cumulative delta: -5 + 3 = -2 -> cleaned 28..38
        self.assertEqual(map_raw_to_cleaned(patches, 30, 40), (28, 38))

    def test_map_cleaned_to_raw_roundtrip_reversibility(self):
        """正反向映射往返恒等（可逆性验证）。"""
        patches = [
            {
                "patch_id": "patch_001",
                "raw_start": 12,
                "raw_end": 14,
                "cleaned_start": 12,
                "cleaned_end": 18,
                "action": "patched",
                "basis": "CTP",
            },
            {
                "patch_id": "patch_002",
                "raw_start": 40,
                "raw_end": 50,
                "cleaned_start": 44,
                "cleaned_end": 44,
                "action": "deletion",
                "basis": "header_footer",
            },
        ]
        test_ranges = [
            (0, 10),
            (12, 18),  # 补丁 1 在 cleaned 上的区间
            (20, 30),
            (44, 60),  # 补丁 2 之后的区间
        ]
        for c_start, c_end in test_ranges:
            r_start, r_end = map_cleaned_to_raw(patches, c_start, c_end)
            c_start_rev, c_end_rev = map_raw_to_cleaned(patches, r_start, r_end)
            self.assertEqual((c_start_rev, c_end_rev), (c_start, c_end))

    def test_map_raw_to_cleaned_rejects_inverted_range_SCH_002(self):
        """倒置区间或负数偏移抛出 ValueError('SCH_002: ...')。"""
        with self.assertRaises(ValueError) as ctx:
            map_raw_to_cleaned([], 20, 10)
        self.assertIn("SCH_002", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx2:
            map_raw_to_cleaned([], -5, 10)
        self.assertIn("SCH_002", str(ctx2.exception))

        with self.assertRaises(ValueError) as ctx3:
            map_cleaned_to_raw([], 30, 15)
        self.assertIn("SCH_002", str(ctx3.exception))

    def test_make_offset_anchor_keys_and_order(self):
        """7 键键序严格逐字对齐。"""
        anchor = make_offset_anchor(
            raw_text_revision_id="raw_rev_001",
            raw_start=0,
            raw_end=6,
            cleaned_text_revision_id="cleaned_rev_001",
            start_offset=0,
            end_offset=6,
            quote="天地玄黄宇宙",
        )
        expected_keys = [
            "raw_text_revision_id",
            "raw_start",
            "raw_end",
            "cleaned_text_revision_id",
            "start_offset",
            "end_offset",
            "quote_sha256",
        ]
        self.assertEqual(list(anchor.keys()), expected_keys)

    def test_make_offset_anchor_computes_exact_quote_sha256(self):
        """精确计算引文 SHA-256。"""
        quote = "洪荒日月盈昃"
        anchor = make_offset_anchor(
            raw_text_revision_id="raw_rev_001",
            raw_start=6,
            raw_end=12,
            cleaned_text_revision_id="cleaned_rev_001",
            start_offset=6,
            end_offset=12,
            quote=quote,
        )
        expected_sha = hashlib.sha256(quote.encode("utf-8")).hexdigest()
        self.assertEqual(anchor["quote_sha256"], expected_sha)

    def test_make_offset_anchor_rejects_quote_len_mismatch_SCH_002(self):
        """引文长度与清洗偏移区间不符时抛出 ValueError('SCH_002: ...')。"""
        with self.assertRaises(ValueError) as ctx:
            make_offset_anchor(
                raw_text_revision_id="raw_rev_001",
                raw_start=0,
                raw_end=10,
                cleaned_text_revision_id="cleaned_rev_001",
                start_offset=0,
                end_offset=10,
                quote="短文本",  # 长度 3 != 10
            )
        self.assertIn("SCH_002", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx2:
            make_offset_anchor(
                raw_text_revision_id="raw_rev_001",
                raw_start=10,
                raw_end=5,  # 倒置
                cleaned_text_revision_id="cleaned_rev_001",
                start_offset=0,
                end_offset=3,
                quote="abc",
            )
        self.assertIn("SCH_002", str(ctx2.exception))

    def test_verify_anchor_success_on_valid_inputs(self):
        """有效输入下校验通过返回 (True, '')。"""
        raw_text = "天地玄黄【注释】宇宙洪荒"
        cleaned_text = "天地玄黄宇宙洪荒"
        patches = [
            {
                "patch_id": "patch_001",
                "raw_start": 4,
                "raw_end": 8,
                "cleaned_start": 4,
                "cleaned_end": 4,
                "action": "deletion",
                "basis": "commentary",
            }
        ]
        # 引文 "宇宙洪荒"，cleaned 偏移 [4, 8)，raw 对应 [8, 12)
        anchor = make_offset_anchor(
            raw_text_revision_id="raw_rev_001",
            raw_start=8,
            raw_end=12,
            cleaned_text_revision_id="cleaned_rev_001",
            start_offset=4,
            end_offset=8,
            quote="宇宙洪荒",
        )
        ok, reason = verify_anchor(
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            patches=patches,
            anchor=anchor,
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_verify_anchor_detects_tampered_quote_hash(self):
        """篡改引文哈希时检出失败并说明原因。"""
        raw_text = "天地玄黄宇宙洪荒"
        cleaned_text = "天地玄黄宇宙洪荒"
        patches = []
        anchor = make_offset_anchor(
            raw_text_revision_id="raw_rev_001",
            raw_start=0,
            raw_end=4,
            cleaned_text_revision_id="cleaned_rev_001",
            start_offset=0,
            end_offset=4,
            quote="天地玄黄",
        )
        anchor["quote_sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"
        ok, reason = verify_anchor(
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            patches=patches,
            anchor=anchor,
        )
        self.assertFalse(ok)
        self.assertIn("引文哈希不符", reason)

    def test_verify_anchor_detects_patch_offset_drift(self):
        """偏移与 patch 换算不符时检出失败并说明原因。"""
        raw_text = "天地玄黄【注释】宇宙洪荒"
        cleaned_text = "天地玄黄宇宙洪荒"
        patches = [
            {
                "patch_id": "patch_001",
                "raw_start": 4,
                "raw_end": 8,
                "cleaned_start": 4,
                "cleaned_end": 4,
                "action": "deletion",
                "basis": "commentary",
            }
        ]
        # 故意将 raw_start 标为 4（实际应为 8）
        anchor = make_offset_anchor(
            raw_text_revision_id="raw_rev_001",
            raw_start=4,
            raw_end=12,
            cleaned_text_revision_id="cleaned_rev_001",
            start_offset=4,
            end_offset=8,
            quote="宇宙洪荒",
        )
        ok, reason = verify_anchor(
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            patches=patches,
            anchor=anchor,
        )
        self.assertFalse(ok)
        self.assertTrue("映射不符" in reason or "换算结果" in reason)

    def test_anchors_pure_does_not_mutate_inputs(self):
        """护栏用例：断言入参 patches 深度比对在调用前后完全一致，检出意外修改。"""
        patches = [
            {
                "patch_id": "patch_001",
                "raw_start": 10,
                "raw_end": 15,
                "cleaned_start": 10,
                "cleaned_end": 12,
                "action": "patched",
                "basis": "CTP",
            },
            {
                "patch_id": "patch_002",
                "raw_start": 30,
                "raw_end": 35,
                "cleaned_start": 27,
                "cleaned_end": 27,
                "action": "deletion",
                "basis": "watermark",
            },
        ]
        patches_copy = copy.deepcopy(patches)

        # 执行各函数调用
        map_raw_to_cleaned(patches, 0, 5)
        map_raw_to_cleaned(patches, 10, 15)
        map_raw_to_cleaned(patches, 20, 30)
        map_cleaned_to_raw(patches, 0, 5)
        map_cleaned_to_raw(patches, 10, 12)
        map_cleaned_to_raw(patches, 15, 25)

        anchor = make_offset_anchor(
            raw_text_revision_id="raw_01",
            raw_start=0,
            raw_end=5,
            cleaned_text_revision_id="clean_01",
            start_offset=0,
            end_offset=5,
            quote="测试原文本",
        )
        verify_anchor(
            raw_text="测试原文本",
            cleaned_text="测试原文本",
            patches=patches,
            anchor=anchor,
        )

        # 深度比对输入无任何修改
        self.assertEqual(patches, patches_copy)


if __name__ == "__main__":
    unittest.main()
