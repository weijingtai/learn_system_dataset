"""Unit tests for electronic text segmentation and offset SourceSpan assembly (Ruling 78, act/01).

synthetic_fixture: true
"""

import copy
import hashlib
import importlib
import re
import unittest
import yaml

from pipeline.corpus_compiler.text_compiler import (
    compile_offset_spans,
    dump_yaml_bytes,
    segment_cleaned_text,
)


class TestTextCompiler(unittest.TestCase):
    """测试电子文本切分与 SourceSpan 产出纯函数（act/01）。"""

    def test_segment_cleaned_text_empty_string(self):
        """测试空文本切分返回空列表。"""
        self.assertEqual(segment_cleaned_text(""), [])

    def test_segment_cleaned_text_single_line(self):
        """测试单行文本切分。"""
        text = "乾元亨利贞。"
        segments = segment_cleaned_text(text)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0], (0, 6))
        self.assertEqual(text[segments[0][0] : segments[0][1]], text)

    def test_segment_cleaned_text_multi_line(self):
        """测试多行与多标点文本切分。"""
        text = "乾元亨利贞。\n坤元亨利牝马之贞。\n大哉乾元！"
        segments = segment_cleaned_text(text)
        self.assertGreaterEqual(len(segments), 3)
        # 拼接验证
        reconstructed = "".join(text[s:e] for s, e in segments)
        self.assertEqual(reconstructed, text)

    def test_segmentation_no_gap_no_overlap(self):
        """护栏用例：验证所有片段首尾相接、无缺口、无重叠，拼接后完全等于原文本。"""
        test_samples = [
            "单行无标点纯文本",
            "天地玄黄。宇宙洪荒。日月盈昃，辰宿列张。\n寒来暑往，秋收冬藏。",
            "第一段\n\n第二段\n第三段\n",
            "   前导空格与缩进\t\n后随文本。\n",
        ]
        for sample in test_samples:
            segments = segment_cleaned_text(sample)
            self.assertTrue(len(segments) > 0)
            # 首尾相接无缺口、无重叠校验
            self.assertEqual(segments[0][0], 0, f"起点必须为 0: {sample!r}")
            for i in range(len(segments) - 1):
                cur_end = segments[i][1]
                next_start = segments[i + 1][0]
                self.assertEqual(
                    cur_end,
                    next_start,
                    f"片段 [{i}] 与 [{i+1}] 存在缺口或重叠: {cur_end} != {next_start}",
                )
            self.assertEqual(
                segments[-1][1],
                len(sample),
                f"终点必须为文本长度: {segments[-1][1]} != {len(sample)}",
            )
            # 逐字符拼接恒等
            reconstructed = "".join(sample[s:e] for s, e in segments)
            self.assertEqual(reconstructed, sample)

    def test_compile_offset_spans_doc_top_level_keys_and_order(self):
        """7 个顶层键序严格逐字对齐。"""
        raw_text = "天地玄黄宇宙洪荒"
        cleaned_text = "天地玄黄宇宙洪荒"
        res = compile_offset_spans(
            work="qianyuan",
            edition="ed01",
            edition_part_artifact_id="epa_001",
            raw_text_revision_id="raw_rev_001",
            raw_text=raw_text,
            cleaned_text_revision_id="clean_rev_001",
            cleaned_text=cleaned_text,
            patches=[],
        )
        spans_doc = res["spans_doc"]
        expected_keys = [
            "work",
            "source_id",
            "edition_part_artifact_id",
            "evidence_level",
            "content_status",
            "span_count",
            "spans",
        ]
        self.assertEqual(list(spans_doc.keys()), expected_keys)
        self.assertEqual(spans_doc["source_id"], "src_qianyuan_ed01")

    def test_compile_offset_spans_span_keys_and_order(self):
        """8 个 Span 键序严格逐字对齐。"""
        raw_text = "天地玄黄\n宇宙洪荒"
        cleaned_text = "天地玄黄\n宇宙洪荒"
        res = compile_offset_spans(
            work="zhouyi",
            edition="ed02",
            edition_part_artifact_id="epa_002",
            raw_text_revision_id="raw_rev_001",
            raw_text=raw_text,
            cleaned_text_revision_id="clean_rev_001",
            cleaned_text=cleaned_text,
            patches=[],
        )
        spans = res["spans"]
        self.assertGreater(len(spans), 0)
        expected_span_keys = [
            "span_id",
            "sequence",
            "start_offset",
            "end_offset",
            "text",
            "quote_sha256",
            "evidence_level",
            "source_anchor",
        ]
        for span in spans:
            self.assertEqual(list(span.keys()), expected_span_keys)

    def test_compile_offset_spans_source_span_id_stability_across_patches(self):
        """补丁增删导致 cleaned 偏移漂移时，RawText 偏移不变使得 ID 严格恒定（Ruling 78）。"""
        # 冻结的原始文本
        raw_text = "天地玄黄。\n【旧广告】\n宇宙洪荒。"
        # 版本 1：仅删除【旧广告】（raw 6..12 -> cleaned 6..6）
        # "宇宙洪荒。" 在 raw_text 中的起始字符为 12
        patches_v1 = [
            {
                "patch_id": "patch_001",
                "raw_start": 6,
                "raw_end": 12,
                "cleaned_start": 6,
                "cleaned_end": 6,
                "action": "deletion",
                "basis": "watermark",
            }
        ]
        cleaned_v1 = "天地玄黄。\n宇宙洪荒。"
        res_v1 = compile_offset_spans(
            work="qianyuan",
            edition="ed01",
            edition_part_artifact_id="epa_001",
            raw_text_revision_id="raw_rev_01",
            raw_text=raw_text,
            cleaned_text_revision_id="clean_rev_01",
            cleaned_text=cleaned_v1,
            patches=patches_v1,
        )
        target_span_v1 = [s for s in res_v1["spans"] if "宇宙洪荒" in s["text"]][0]
        # start_offset 为 6，但 raw_start 为 12，ID 锚定 12
        self.assertEqual(target_span_v1["start_offset"], 6)
        self.assertEqual(target_span_v1["span_id"], "ss_qianyuan_ed01_o0000012")

        # 版本 2：底层的 raw_text 严格冻结！但在 0..2 之间新增了清洗补丁（导致其后 cleaned 偏移发生漂移）
        patches_v2 = [
            {
                "patch_id": "patch_000",
                "raw_start": 0,
                "raw_end": 2,
                "cleaned_start": 0,
                "cleaned_end": 4,
                "action": "patched",
                "basis": "CTP",
            },
            {
                "patch_id": "patch_001",
                "raw_start": 6,
                "raw_end": 12,
                "cleaned_start": 8,
                "cleaned_end": 8,
                "action": "deletion",
                "basis": "watermark",
            },
        ]
        cleaned_v2 = "乾坤天地玄黄。\n宇宙洪荒。"
        res_v2 = compile_offset_spans(
            work="qianyuan",
            edition="ed01",
            edition_part_artifact_id="epa_001",
            raw_text_revision_id="raw_rev_01",
            raw_text=raw_text,
            cleaned_text_revision_id="clean_rev_02",
            cleaned_text=cleaned_v2,
            patches=patches_v2,
        )
        target_span_v2 = [s for s in res_v2["spans"] if "宇宙洪荒" in s["text"]][0]
        # 在 cleaned_text 中的起始偏移已从 6 漂移到 8
        self.assertEqual(target_span_v2["start_offset"], 8)
        # 但 ID 依然稳定保持为 ss_qianyuan_ed01_o0000012，与 v1 完全相同！
        self.assertEqual(target_span_v2["span_id"], target_span_v1["span_id"])
        self.assertEqual(target_span_v2["span_id"], "ss_qianyuan_ed01_o0000012")

    def test_compile_offset_spans_quote_and_hash_integrity(self):
        """引文切片与哈希校验完整性。"""
        raw_text = "乾道变化，各正性命。"
        cleaned_text = "乾道变化，各正性命。"
        res = compile_offset_spans(
            work="zhouyi",
            edition="ed01",
            edition_part_artifact_id="epa_001",
            raw_text_revision_id="raw_01",
            raw_text=raw_text,
            cleaned_text_revision_id="clean_01",
            cleaned_text=cleaned_text,
            patches=[],
        )
        for span in res["spans"]:
            start = span["start_offset"]
            end = span["end_offset"]
            expected_text = cleaned_text[start:end]
            self.assertEqual(span["text"], expected_text)
            expected_hash = hashlib.sha256(expected_text.encode("utf-8")).hexdigest()
            self.assertEqual(span["quote_sha256"], expected_hash)
            self.assertEqual(span["source_anchor"]["quote_sha256"], expected_hash)

    def test_compile_offset_spans_sequence_continuous_from_one(self):
        """sequence 顺序号从 1 严格连续递增。"""
        raw_text = "第一句。\n第二句。\n第三句。"
        cleaned_text = "第一句。\n第二句。\n第三句。"
        res = compile_offset_spans(
            work="zhouyi",
            edition="ed01",
            edition_part_artifact_id="epa_001",
            raw_text_revision_id="raw_01",
            raw_text=raw_text,
            cleaned_text_revision_id="clean_01",
            cleaned_text=cleaned_text,
            patches=[],
        )
        spans = res["spans"]
        self.assertEqual([s["sequence"] for s in spans], list(range(1, len(spans) + 1)))

    def test_compile_offset_spans_counts_and_sha256_exact(self):
        """统计计数值与文档 sha256 精确计算。"""
        raw_text = "大哉乾元，万物资始。"
        cleaned_text = "大哉乾元，万物资始。"
        res = compile_offset_spans(
            work="zhouyi",
            edition="ed01",
            edition_part_artifact_id="epa_001",
            raw_text_revision_id="raw_01",
            raw_text=raw_text,
            cleaned_text_revision_id="clean_01",
            cleaned_text=cleaned_text,
            patches=[],
        )
        num_spans = len(res["spans"])
        self.assertEqual(res["counts"]["spans"], num_spans)
        self.assertEqual(res["counts"]["evidence_level_counts"]["offset_level"], num_spans)
        self.assertEqual(res["counts"]["evidence_level_counts"]["glyphbox_level"], 0)
        self.assertEqual(res["spans_doc"]["span_count"], num_spans)
        # sha256 校验
        expected_sha = hashlib.sha256(res["spans_bytes"]).hexdigest()
        self.assertEqual(res["spans_sha256"], expected_sha)

    def test_evidence_level_strictly_offset_level(self):
        """护栏用例：断言顶层及每条 Span 的 evidence_level 恒等于 offset_level。"""
        raw_text = "天行健，君子以自强不息。"
        cleaned_text = "天行健，君子以自强不息。"
        res = compile_offset_spans(
            work="zhouyi",
            edition="ed01",
            edition_part_artifact_id="epa_001",
            raw_text_revision_id="raw_01",
            raw_text=raw_text,
            cleaned_text_revision_id="clean_01",
            cleaned_text=cleaned_text,
            patches=[],
        )
        self.assertEqual(res["spans_doc"]["evidence_level"], "offset_level")
        for s in res["spans"]:
            self.assertEqual(s["evidence_level"], "offset_level")
            self.assertNotEqual(s["evidence_level"], "glyphbox_level")

    def test_dump_yaml_bytes_deterministic(self):
        """YAML 序列化确定性验证（两次序列化字节完全一致）。"""
        data = {
            "work": "zhouyi",
            "source_id": "src_zhouyi_ed01",
            "evidence_level": "offset_level",
            "spans": [{"id": 1, "text": "测试文本"}],
        }
        b1 = dump_yaml_bytes(data)
        b2 = dump_yaml_bytes(data)
        self.assertEqual(b1, b2)
        # 反序列化保持一致
        loaded = yaml.safe_load(b1.decode("utf-8"))
        self.assertEqual(loaded["work"], "zhouyi")

    def test_global_safedumper_not_polluted_on_import_and_runtime(self):
        """第 88 条护栏用例：断言 SafeDumper.yaml_representers 未被污染，reload 无副作用。"""
        clean_rep_keys = set(yaml.SafeDumper.yaml_representers.keys())

        # 重新 reload 模块
        import pipeline.corpus_compiler.text_compiler as tc_module

        importlib.reload(tc_module)

        post_import_keys = set(yaml.SafeDumper.yaml_representers.keys())
        self.assertEqual(clean_rep_keys, post_import_keys, "SafeDumper 在 import 期被污染！")

        # 运行一次编译与 dump
        res = tc_module.compile_offset_spans(
            work="zhouyi",
            edition="ed01",
            edition_part_artifact_id="epa_001",
            raw_text_revision_id="raw_01",
            raw_text="测试内容",
            cleaned_text_revision_id="clean_01",
            cleaned_text="测试内容",
            patches=[],
        )
        tc_module.dump_yaml_bytes(res["spans_doc"])

        post_runtime_keys = set(yaml.SafeDumper.yaml_representers.keys())
        self.assertEqual(clean_rep_keys, post_runtime_keys, "SafeDumper 在运行期被污染！")

    def test_compile_offset_spans_rejects_empty_raw_text_SCH_002(self):
        """原始文本为空时抛出 ValueError('SCH_002: ...')。"""
        with self.assertRaises(ValueError) as ctx:
            compile_offset_spans(
                work="zhouyi",
                edition="ed01",
                edition_part_artifact_id="epa_001",
                raw_text_revision_id="raw_01",
                raw_text="",
                cleaned_text_revision_id="clean_01",
                cleaned_text="",
                patches=[],
            )
        self.assertIn("SCH_002", str(ctx.exception))

    def test_compile_offset_spans_rejects_invalid_edition_SCH_002(self):
        """非法 edition 格式抛出 ValueError('SCH_002: ...')。"""
        with self.assertRaises(ValueError) as ctx:
            compile_offset_spans(
                work="zhouyi",
                edition="v1_invalid",
                edition_part_artifact_id="epa_001",
                raw_text_revision_id="raw_01",
                raw_text="测试文本",
                cleaned_text_revision_id="clean_01",
                cleaned_text="测试文本",
                patches=[],
            )
        self.assertIn("SCH_002", str(ctx.exception))

    def test_compile_offset_spans_rejects_patch_out_of_bounds_SCH_002(self):
        """补丁偏移超出文本边界时抛出 ValueError('SCH_002: ...')。"""
        patches = [
            {
                "patch_id": "patch_001",
                "raw_start": 0,
                "raw_end": 100,  # 远超 raw_text 长度 (4)
                "cleaned_start": 0,
                "cleaned_end": 4,
                "action": "patched",
                "basis": "CTP",
            }
        ]
        with self.assertRaises(ValueError) as ctx:
            compile_offset_spans(
                work="zhouyi",
                edition="ed01",
                edition_part_artifact_id="epa_001",
                raw_text_revision_id="raw_01",
                raw_text="四个字",
                cleaned_text_revision_id="clean_01",
                cleaned_text="四个字",
                patches=patches,
            )
        self.assertIn("SCH_002", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
