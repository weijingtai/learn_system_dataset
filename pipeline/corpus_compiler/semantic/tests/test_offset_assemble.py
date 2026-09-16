"""act/05 语义层合成（compile_semantic_offset / sem_ 偏移锚点）具名用例。

synthetic_fixture: true —— 全部输入为内联合成数据（含一条水印删除补丁），不读写 fixture 目录。
"""

import hashlib
import unittest

from pipeline.corpus_compiler.offset_anchors import map_cleaned_to_raw
from pipeline.corpus_compiler.semantic.offset_assemble import compile_semantic_offset

WORK = "qianyuan"
EDITION = "ed01"
RAW_REV = "rev_" + "0" * 32
CLEAN_REV = "rev_" + "1" * 32
EDITION_PART = "art_000000000000000000000000000000e1"

SEG1 = "天地玄黄。\n"  # 6 字符 → 规则单片
SEG2 = "宇宙洪荒，日月盈昃，辰宿列张。\n"  # 16 字符 → 窗口 w001
SEG3 = "寒来暑往秋收冬藏闰余成岁。"  # 13 字符 → 窗口 w002

RAW_TEXT = "天地玄黄。\n【广告】\n宇宙洪荒，日月盈昃，辰宿列张。\n寒来暑往秋收冬藏闰余成岁。"
CLEANED_TEXT = SEG1 + SEG2 + SEG3

# 原始文本 6..11 处的「【广告】\n」被删除
PATCHES = [
    {
        "patch_id": "patch_001",
        "raw_start": 6,
        "raw_end": 11,
        "cleaned_start": 6,
        "cleaned_end": 6,
        "action": "deletion",
        "basis": "watermark",
    }
]

TOP_LEVEL_KEYS = [
    "work",
    "source_id",
    "edition_part_artifact_id",
    "raw_spans_sha256",
    "gate_profile",
    "segmentation_profile",
    "content_status",
    "span_count",
    "window_count",
    "dispute_count",
    "evidence_level_counts",
    "spans",
]

SPAN_KEYS = [
    "semantic_span_id",
    "sequence",
    "start_offset",
    "end_offset",
    "text",
    "quote_sha256",
    "boundary_origin",
    "window_id",
    "structural_refs",
    "evidence_level",
    "source_anchor",
]


def make_structural_span(*, sequence, text, cleaned_start, raw_start):
    span_id = "ss_%s_%s_o%07d" % (WORK, EDITION, raw_start)
    quote_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "span_id": span_id,
        "sequence": sequence,
        "start_offset": cleaned_start,
        "end_offset": cleaned_start + len(text),
        "text": text,
        "quote_sha256": quote_sha256,
        "evidence_level": "offset_level",
        "source_anchor": {
            "raw_text_revision_id": RAW_REV,
            "raw_start": raw_start,
            "raw_end": raw_start + len(text),
            "cleaned_text_revision_id": CLEAN_REV,
            "start_offset": cleaned_start,
            "end_offset": cleaned_start + len(text),
            "quote_sha256": quote_sha256,
        },
    }


def make_structural_spans():
    return [
        make_structural_span(sequence=1, text=SEG1, cleaned_start=0, raw_start=0),
        make_structural_span(sequence=2, text=SEG2, cleaned_start=6, raw_start=11),
        make_structural_span(sequence=3, text=SEG3, cleaned_start=22, raw_start=27),
    ]


def make_windows():
    return [
        {
            "window_id": "%s_w001" % WORK,
            "span_id": "ss_%s_%s_o%07d" % (WORK, EDITION, 11),
            "text": SEG2,
            "text_sha256": hashlib.sha256(SEG2.encode("utf-8")).hexdigest(),
            "raw_start": 11,
            "raw_end": 27,
        },
        {
            "window_id": "%s_w002" % WORK,
            "span_id": "ss_%s_%s_o%07d" % (WORK, EDITION, 27),
            "text": SEG3,
            "text_sha256": hashlib.sha256(SEG3.encode("utf-8")).hexdigest(),
            "raw_start": 27,
            "raw_end": 40,
        },
    ]


def make_resolutions():
    return {
        "%s_w001" % WORK: {
            "boundary_origin": "cross_model_agreed",
            "segments": [[0, 9], [9, 16]],
        },
        "%s_w002" % WORK: {
            "boundary_origin": "human_decided",
            "segments": [[0, 7], [7, 13]],
        },
    }


def compile_golden():
    return compile_semantic_offset(
        structural_spans=make_structural_spans(),
        windows=make_windows(),
        resolutions=make_resolutions(),
        raw_text_revision_id=RAW_REV,
        raw_text=RAW_TEXT,
        cleaned_text_revision_id=CLEAN_REV,
        cleaned_text=CLEANED_TEXT,
        patches=PATCHES,
        work=WORK,
        edition=EDITION,
        edition_part_artifact_id=EDITION_PART,
    )


class TestCompileSemanticOffset(unittest.TestCase):
    """语义层合成：结构片段 → sem_ 偏移锚点片段。"""

    def test_compile_semantic_offset_keys_and_order(self):
        """顶层键序与 Span 键序逐字对齐 README §6.2 / act/05 contract。"""
        doc = compile_golden()
        self.assertEqual(list(doc.keys()), TOP_LEVEL_KEYS)
        self.assertEqual(doc["work"], WORK)
        self.assertEqual(doc["source_id"], "src_%s_%s" % (WORK, EDITION))
        self.assertEqual(doc["edition_part_artifact_id"], EDITION_PART)
        self.assertEqual(doc["gate_profile"], "structural_and_semantic")
        self.assertEqual(doc["content_status"], "machine_extracted")
        self.assertEqual(len(doc["raw_spans_sha256"]), 64)
        for span in doc["spans"]:
            self.assertEqual(list(span.keys()), SPAN_KEYS)

    def test_semantic_span_id_prefix_strictly_sem(self):
        """第 88 条护栏：每个 ID 严格以 sem_ 起头并匹配偏移形态，绝无未登记前缀。"""
        import re

        doc = compile_golden()
        pattern = re.compile(r"^sem_[a-z][a-z0-9_]*_ed[0-9]{2}_o[0-9]{7}$")
        ids = [span["semantic_span_id"] for span in doc["spans"]]
        self.assertEqual(len(ids), 5)
        for sem_id in ids:
            self.assertTrue(sem_id.startswith("sem_"), sem_id)
            self.assertRegex(sem_id, pattern)
            self.assertFalse(sem_id.startswith("ss_"))
        # 未登记前缀一律不得出现
        for prefix in ("txt_", "ocr_", "paragraph_", "segment_", "bnd_"):
            for sem_id in ids:
                self.assertFalse(sem_id.startswith(prefix))
        # 已知期望值（raw_start 决定的稳定身份）
        self.assertEqual(
            ids,
            [
                "sem_%s_%s_o%07d" % (WORK, EDITION, 0),
                "sem_%s_%s_o%07d" % (WORK, EDITION, 11),
                "sem_%s_%s_o%07d" % (WORK, EDITION, 20),
                "sem_%s_%s_o%07d" % (WORK, EDITION, 27),
                "sem_%s_%s_o%07d" % (WORK, EDITION, 34),
            ],
        )

    def test_semantic_spans_rule_boundary_origin(self):
        """非窗口片段（长度不足阈值）作为单语义片段，origin=rule、window_id=None。"""
        doc = compile_golden()
        first = doc["spans"][0]
        self.assertEqual(first["boundary_origin"], "rule")
        self.assertIsNone(first["window_id"])
        self.assertEqual(first["text"], SEG1)
        self.assertEqual(first["start_offset"], 0)
        self.assertEqual(first["end_offset"], 6)

    def test_semantic_spans_cross_model_agreed_origin(self):
        """双模型边界一致的窗口，按一致切分产出 origin=cross_model_agreed 的片段。"""
        doc = compile_golden()
        agreed = [s for s in doc["spans"] if s["boundary_origin"] == "cross_model_agreed"]
        self.assertEqual(len(agreed), 2)
        for span in agreed:
            self.assertEqual(span["window_id"], "%s_w001" % WORK)
        self.assertEqual([s["text"] for s in agreed], ["宇宙洪荒，日月盈昃", "，辰宿列张。\n"])
        self.assertEqual([s["start_offset"] for s in agreed], [6, 15])

    def test_semantic_spans_human_decided_origin(self):
        """经人工裁决的窗口，按裁决切分产出 origin=human_decided 的片段。"""
        doc = compile_golden()
        decided = [s for s in doc["spans"] if s["boundary_origin"] == "human_decided"]
        self.assertEqual(len(decided), 2)
        for span in decided:
            self.assertEqual(span["window_id"], "%s_w002" % WORK)
        self.assertEqual([s["text"] for s in decided], ["寒来暑往秋收冬", "藏闰余成岁。"])
        self.assertEqual([s["start_offset"] for s in decided], [22, 29])

    def test_semantic_spans_structural_refs_integrity(self):
        """结构引用完整：局部区间切片等于语义文本，清洗/原始偏移链路一致。"""
        doc = compile_golden()
        structural_by_id = {s["span_id"]: s for s in make_structural_spans()}

        for span in doc["spans"]:
            refs = span["structural_refs"]
            self.assertEqual(len(refs), 1)
            ref = refs[0]
            self.assertIn(ref["span_id"], structural_by_id)
            structural = structural_by_id[ref["span_id"]]
            self.assertEqual(
                structural["text"][ref["start"] : ref["end"]], span["text"]
            )
            self.assertEqual(
                CLEANED_TEXT[span["start_offset"] : span["end_offset"]], span["text"]
            )
            self.assertEqual(
                span["quote_sha256"],
                hashlib.sha256(span["text"].encode("utf-8")).hexdigest(),
            )
            # 全局清洗偏移 = 结构片段起点 + 局部起点
            self.assertEqual(
                span["start_offset"], structural["start_offset"] + ref["start"]
            )
            self.assertEqual(
                span["end_offset"], structural["start_offset"] + ref["end"]
            )
            # 原始偏移由补丁换算得到，且与锚点一致
            anchor = span["source_anchor"]
            self.assertEqual(
                (anchor["raw_start"], anchor["raw_end"]),
                map_cleaned_to_raw(
                    PATCHES, span["start_offset"], span["end_offset"]
                ),
            )
            self.assertEqual(
                list(anchor.keys()),
                [
                    "raw_text_revision_id",
                    "raw_start",
                    "raw_end",
                    "cleaned_text_revision_id",
                    "start_offset",
                    "end_offset",
                    "quote_sha256",
                ],
            )

    def test_semantic_spans_evidence_level_strictly_offset_level(self):
        """顶层证据级别声明与每条片段 evidence_level 严格为 offset_level（不得伪升 glyphbox）。

        注：本文件的顶层证据级别声明形态为 ``evidence_level_counts``（README §6.2 顶层键序
        12 键中无独立 ``evidence_level`` 键），故此处断言 counts 中 glyphbox_level 恒为 0。
        """
        doc = compile_golden()
        self.assertNotIn("evidence_level", doc)
        self.assertEqual(
            doc["evidence_level_counts"],
            {"offset_level": len(doc["spans"]), "glyphbox_level": 0},
        )
        for span in doc["spans"]:
            self.assertEqual(span["evidence_level"], "offset_level")

    def test_compile_semantic_offset_counts_exact(self):
        """span_count / window_count / dispute_count 与实体严格一致。"""
        doc = compile_golden()
        self.assertEqual(doc["span_count"], len(doc["spans"]))
        self.assertEqual(doc["span_count"], 5)
        self.assertEqual(doc["window_count"], len(make_windows()))
        self.assertEqual(doc["window_count"], 2)
        # 裁决窗口数（每窗口一条）
        self.assertEqual(
            doc["dispute_count"],
            len({s["window_id"] for s in doc["spans"] if s["boundary_origin"] == "human_decided"}),
        )
        self.assertEqual(doc["dispute_count"], 1)
        self.assertEqual(
            [s["sequence"] for s in doc["spans"]], [1, 2, 3, 4, 5]
        )
        origins = doc["segmentation_profile"]["boundary_origins"]
        self.assertEqual(origins["rule"], 1)
        self.assertEqual(origins["cross_model_agreed"], 2)
        self.assertEqual(origins["human_decided"], 2)


if __name__ == "__main__":
    unittest.main()
