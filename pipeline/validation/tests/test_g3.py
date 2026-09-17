"""ACT 03 单元测试：G3 身份、引用与证据锚点五项 Validator。

用例名与 act/03.yaml 的 tests 清单逐字一致；全部基于 ``fixture_context()``，
对上下文副本施加篡改（不写 fixture 目录）。
"""

import copy
import hashlib
import unittest
from pathlib import Path

from pipeline.validation.g3_evidence import (
    validate_evidence_level,
    validate_glyphbox_anchor,
    validate_references,
    validate_span_identity,
    validate_strict_offset_quote,
)
from pipeline.validation.tests.helpers import fixture_context, offset_fixture_context


def _by_check(result, check):
    return [f for f in result["findings"] if f["check"] == check]


class G3FixtureCleanTest(unittest.TestCase):
    def test_fixture_context_g3_clean_except_three_findings(self):
        ctx = fixture_context()
        self.assertEqual(validate_span_identity(ctx)["findings"], [])
        self.assertEqual(validate_references(ctx)["findings"], [])
        self.assertEqual(validate_evidence_level(ctx)["findings"], [])

        strict = validate_strict_offset_quote(ctx)
        self.assertEqual(len(_by_check(strict, "quote_hash_not_stored")), 1)
        self.assertEqual(len(strict["findings"]), 1)

        anchor = validate_glyphbox_anchor(ctx)
        self.assertEqual(len(_by_check(anchor, "glyph_text_misaligned")), 2)
        self.assertEqual(
            {f["subject"]["entity_id"] for f in _by_check(anchor, "glyph_text_misaligned")},
            {"ss_sanche_ed01_p0001_s03", "ss_sanche_ed01_p0001_s04"},
        )

    def test_quote_hash_not_stored_is_single_with_warning_error_error(self):
        ctx = fixture_context()
        findings = _by_check(validate_strict_offset_quote(ctx), "quote_hash_not_stored")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "SCH_001")
        self.assertEqual(
            findings[0]["severity"],
            {"INTERNAL_DEMO": "warning", "DEV_SEARCH": "error", "PUBLIC_RELEASE": "error"},
        )


class G3SpanIdentityTest(unittest.TestCase):
    def test_span_identity_flags_illegal_format(self):
        ctx = fixture_context()
        ctx["spans_doc"]["spans"][0]["span_id"] = "bogus"
        findings = _by_check(validate_span_identity(ctx), "span_id_format")
        self.assertTrue(findings)
        self.assertEqual(findings[0]["code"], "ID_001")

    def test_span_identity_flags_duplicate_span_id(self):
        ctx = fixture_context()
        ctx["spans_doc"]["spans"][1]["span_id"] = ctx["spans_doc"]["spans"][0]["span_id"]
        findings = _by_check(validate_span_identity(ctx), "span_id_duplicate")
        self.assertTrue(findings)
        self.assertEqual(findings[0]["code"], "ID_002")

    def test_span_identity_flags_page_line_mismatch(self):
        ctx = fixture_context()
        ctx["spans_doc"]["spans"][0]["line_index"] = 5
        findings = _by_check(validate_span_identity(ctx), "page_line_mismatch")
        self.assertTrue(findings)
        self.assertEqual(findings[0]["code"], "REF_001")

    def test_span_identity_flags_source_id_mismatch(self):
        ctx = fixture_context()
        ctx["spans_doc"]["source_id"] = "src_other_ed01"
        findings = _by_check(validate_span_identity(ctx), "source_id_mismatch")
        self.assertTrue(findings)

    def test_span_identity_flags_illegal_content_status(self):
        ctx = fixture_context()
        ctx["spans_doc"]["content_status"] = "not_a_status"
        findings = _by_check(validate_span_identity(ctx), "content_status_invalid")
        self.assertTrue(findings)
        self.assertEqual(findings[0]["code"], "SCH_002")


class G3ReferencesTest(unittest.TestCase):
    def _add_dangling(self, ctx):
        ctx["m3_package"]["manifest"]["input_artifacts"].append(
            {
                "schema_version": "1.0.0",
                "artifact_kind": "artifact",
                "artifact_id": "art_" + "0" * 32,
                "artifact_revision_id": "rev_" + "0" * 32,
                "artifact_type": "ocr_page",
            }
        )

    def test_references_flags_dangling_revision(self):
        ctx = fixture_context()
        self._add_dangling(ctx)
        findings = _by_check(validate_references(ctx), "dangling_ref")
        self.assertTrue(findings)
        self.assertEqual(findings[0]["code"], "REF_001")

    def test_references_flags_unsealed_revision(self):
        ctx = fixture_context()
        rev = ctx["revision_roles"]["ocr_page_set"]
        ctx["raw"]["frozen"][rev]["status"] = "draft"
        findings = _by_check(validate_references(ctx), "not_consumable")
        self.assertTrue(findings)

    def test_references_flags_artifact_type_mismatch(self):
        ctx = fixture_context()
        rev = ctx["revision_roles"]["ocr_page_set"]
        for ref in ctx["m3_package"]["manifest"]["input_artifacts"]:
            if ref["artifact_revision_id"] == rev:
                ref["artifact_type"] = "corpus_spans"
        findings = _by_check(validate_references(ctx), "ref_type_mismatch")
        self.assertTrue(findings)

    def test_references_carry_artifact_ref_relation_for_broken_relations(self):
        ctx = fixture_context()
        self._add_dangling(ctx)
        findings = _by_check(validate_references(ctx), "dangling_ref")
        self.assertTrue(findings)
        self.assertEqual(findings[0]["relation"], "artifact_ref")
        self.assertTrue(findings[0]["subject"]["entity_id"])


class G3StrictOffsetQuoteTest(unittest.TestCase):
    def test_strict_offset_flags_shifted_offset(self):
        ctx = fixture_context()
        ctx["spans_doc"]["spans"][0]["start_offset"] = 1
        findings = _by_check(validate_strict_offset_quote(ctx), "offset_mismatch")
        self.assertTrue(findings)
        self.assertEqual(findings[0]["code"], "TXT_001")

    def test_strict_offset_flags_out_of_range(self):
        ctx = fixture_context()
        ctx["spans_doc"]["spans"][0]["end_offset"] = 99999
        findings = _by_check(validate_strict_offset_quote(ctx), "offset_out_of_range")
        self.assertTrue(findings)
        self.assertEqual(findings[0]["code"], "TXT_001")

    def test_quote_hash_mismatch_when_span_carries_quote_sha256(self):
        ctx = fixture_context()
        ctx["spans_doc"]["spans"][0]["quote_sha256"] = "0" * 64
        result = validate_strict_offset_quote(ctx)
        self.assertTrue(_by_check(result, "quote_hash_mismatch"))
        # 至少一条 span 自带 quote_sha256，则不得再有 quote_hash_not_stored
        self.assertEqual(_by_check(result, "quote_hash_not_stored"), [])


class G3GlyphboxAnchorTest(unittest.TestCase):
    def test_glyphbox_anchor_flags_page_image_hash_mismatch(self):
        ctx = fixture_context()
        ctx["spans_doc"]["spans"][0]["source_anchor"]["image_sha256"] = "0" * 64
        findings = _by_check(validate_glyphbox_anchor(ctx), "page_image_hash_mismatch")
        self.assertTrue(findings)
        self.assertEqual(findings[0]["code"], "SRC_003")

    def test_glyphbox_anchor_flags_line_and_glyph_box_mismatch(self):
        ctx = fixture_context()
        ctx["spans_doc"]["spans"][0]["source_anchor"]["bbox"]["x"] = -1.0
        self.assertTrue(
            _by_check(validate_glyphbox_anchor(ctx), "line_box_mismatch")
        )

        ctx2 = fixture_context()
        ctx2["spans_doc"]["spans"][0]["source_anchor"]["chars"][0]["box"]["w"] = 0.5
        self.assertTrue(
            _by_check(validate_glyphbox_anchor(ctx2), "glyph_box_mismatch")
        )

    def test_glyphbox_anchor_flags_out_of_page_box(self):
        ctx = fixture_context()
        box = ctx["spans_doc"]["spans"][0]["source_anchor"]["chars"][0]["box"]
        box["x"] = 2000.0
        box["w"] = 100.0
        self.assertTrue(
            _by_check(validate_glyphbox_anchor(ctx), "anchor_out_of_page")
        )

    def test_glyphbox_anchor_accepts_axis_aligned_as_four_point_equivalent(self):
        ctx = fixture_context()
        result = validate_glyphbox_anchor(ctx)
        self.assertEqual(_by_check(result, "anchor_field_missing"), [])
        self.assertEqual(_by_check(result, "anchor_out_of_page"), [])

    def test_glyphbox_anchor_flags_missing_anchor_field(self):
        ctx = fixture_context()
        line_id = ctx["spans_doc"]["spans"][0]["source_anchor"]["line_id"]
        page = ctx["spans_doc"]["spans"][0]["page"]
        for line in ctx["page_docs"][page]["lines"]:
            if line["id"] == line_id:
                line["angle"] = 1.0
        self.assertTrue(
            _by_check(validate_glyphbox_anchor(ctx), "anchor_field_missing")
        )

    def test_glyph_text_misaligned_lists_subject_and_difference(self):
        ctx = fixture_context()
        findings = _by_check(validate_glyphbox_anchor(ctx), "glyph_text_misaligned")
        self.assertEqual(len(findings), 2)
        for finding in findings:
            self.assertTrue(finding["detail"])
            self.assertEqual(
                finding["severity"],
                {"INTERNAL_DEMO": "warning", "DEV_SEARCH": "error", "PUBLIC_RELEASE": "error"},
            )
            self.assertTrue(finding["subject"]["entity_id"])


class G3EvidenceLevelTest(unittest.TestCase):
    def test_evidence_level_insufficient_on_offset_level(self):
        ctx = fixture_context()
        ctx["spans_doc"]["evidence_level"] = "offset_level"
        findings = _by_check(
            validate_evidence_level(ctx), "evidence_level_insufficient"
        )
        self.assertTrue(findings)
        self.assertEqual(
            findings[0]["severity"],
            {"INTERNAL_DEMO": "info", "DEV_SEARCH": "info", "PUBLIC_RELEASE": "error"},
        )

    def test_evidence_level_glyphbox_incomplete_when_chars_empty(self):
        ctx = fixture_context()
        ctx["spans_doc"]["spans"][0]["source_anchor"]["chars"] = []
        findings = _by_check(validate_evidence_level(ctx), "glyphbox_incomplete")
        self.assertTrue(findings)
        self.assertEqual(findings[0]["code"], "SCH_001")
        self.assertEqual(set(findings[0]["severity"].values()), {"error"})

    def test_evidence_level_invalid_on_unknown_value(self):
        ctx = fixture_context()
        ctx["spans_doc"]["evidence_level"] = "unknown_level"
        findings = _by_check(validate_evidence_level(ctx), "evidence_level_invalid")
        self.assertTrue(findings)
        self.assertEqual(findings[0]["code"], "SCH_002")


class G3OffsetLevelTest(unittest.TestCase):
    """R83（第 100 条 D5）：offset 档 G3 逐片段独立复算（合成数据）。"""

    def test_g3_offset_level_recomputes_quote_sha256_per_span(self):
        ctx = offset_fixture_context()
        result = validate_strict_offset_quote(ctx)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["checked"]["spans"], 3)
        for span in ctx["spans_doc"]["spans"]:
            expected = hashlib.sha256(span["text"].encode("utf-8")).hexdigest()
            self.assertEqual(span["quote_sha256"], expected)
            self.assertEqual(
                ctx["cleaned_text"][span["start_offset"]:span["end_offset"]],
                span["text"],
            )

        self.assertEqual(validate_span_identity(ctx)["findings"], [])
        self.assertEqual(validate_glyphbox_anchor(ctx)["findings"], [])

    def test_g3_offset_level_rejects_tampered_quote_sha256(self):
        ctx = offset_fixture_context()
        ctx["spans_doc"]["spans"][0]["quote_sha256"] = "0" * 64
        result = validate_strict_offset_quote(ctx)
        findings = _by_check(result, "quote_hash_mismatch")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "TXT_001")
        self.assertEqual(findings[0]["relation"], "content_hash")
        self.assertEqual(_by_check(result, "quote_hash_not_stored"), [])

    def test_g3_offset_level_rejects_offset_out_of_cleaned_range(self):
        ctx = offset_fixture_context()
        ctx["spans_doc"]["spans"][0]["end_offset"] = 99999
        findings = _by_check(
            validate_strict_offset_quote(ctx), "offset_out_of_range"
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "TXT_001")

        ctx2 = offset_fixture_context()
        ctx2["spans_doc"]["spans"][0]["text"] = "篡改"
        self.assertTrue(_by_check(validate_strict_offset_quote(ctx2), "offset_mismatch"))

    def test_g3_offset_level_rejects_raw_anchor_mapping_break(self):
        ctx = offset_fixture_context()
        anchor = ctx["spans_doc"]["spans"][1]["source_anchor"]
        anchor["raw_start"] += 1
        anchor["raw_end"] += 1
        findings = _by_check(
            validate_strict_offset_quote(ctx), "raw_anchor_mismatch"
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "TXT_001")

    def test_g3_offset_level_rejects_span_id_not_from_ids_registry(self):
        ctx = offset_fixture_context()
        ctx["spans_doc"]["spans"][0]["span_id"] = "ss_qianyuan_ed01_p0001_s01"
        findings = _by_check(validate_span_identity(ctx), "span_id_format")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "ID_001")

    def test_g3_offset_level_rejects_glyphbox_anchor_key(self):
        ctx = offset_fixture_context()
        ctx["spans_doc"]["spans"][0]["source_anchor"]["image_sha256"] = "0" * 64
        findings = _by_check(validate_glyphbox_anchor(ctx), "anchor_field_missing")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "SCH_001")


class G3IndependenceTest(unittest.TestCase):
    def test_g3_module_has_no_corpus_compiler_import(self):
        source = (Path(__file__).resolve().parents[1] / "g3_evidence.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("corpus_compiler", source)


if __name__ == "__main__":
    unittest.main()
