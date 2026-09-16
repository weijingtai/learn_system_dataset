"""act/06 独立语义 Gate（evaluate_semantic_offset）具名用例。

synthetic_fixture: true —— 全部输入为内联合成数据；Golden 由 act/05 的 compile_semantic_offset
产出后交给 Gate 独立判定（Gate 自身不 import 任何编译器实现模块）。
"""

import ast
import copy
import hashlib
import json
import unittest
from pathlib import Path

from pipeline.corpus_compiler.offset_anchors import map_cleaned_to_raw
from pipeline.corpus_compiler.semantic.offset_assemble import compile_semantic_offset
from pipeline.corpus_compiler.semantic.semantic_gate import evaluate_semantic_offset

WORK = "qianyuan"
EDITION = "ed01"
RAW_REV = "rev_" + "0" * 32
CLEAN_REV = "rev_" + "1" * 32
EDITION_PART = "art_000000000000000000000000000000e1"

SEG1 = "天地玄黄。\n"  # 6 字符 → 规则单片
SEG2 = "宇宙洪荒，日月盈昃，辰宿列张。\n"  # 16 字符 → 窗口 w001（双路一致）
SEG3 = "寒来暑往秋收冬藏闰余成岁。"  # 13 字符 → 窗口 w002（分歧 → 人工裁决）

RAW_TEXT = "天地玄黄。\n【广告】\n" + SEG2 + SEG3
CLEANED_TEXT = SEG1 + SEG2 + SEG3
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

W001_SEGMENTS = [[0, 9], [9, 16]]
W002_A_SEGMENTS = [[0, 7], [7, 13]]
W002_B_SEGMENTS = [[0, 6], [6, 13]]

CHECK_NAMES = [
    "semantic_contiguous_coverage",
    "semantic_strict_offset",
    "structural_refs_consistent",
    "window_rule_fidelity",
    "disputes_resolved_zero",
    "evidence_level_honest",
    "semantic_identity",
    "header_counts",
]


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_structural_span(*, sequence, text, cleaned_start, raw_start):
    span_id = "ss_%s_%s_o%07d" % (WORK, EDITION, raw_start)
    return {
        "span_id": span_id,
        "sequence": sequence,
        "start_offset": cleaned_start,
        "end_offset": cleaned_start + len(text),
        "text": text,
        "quote_sha256": _sha256(text),
        "evidence_level": "offset_level",
        "source_anchor": {
            "raw_text_revision_id": RAW_REV,
            "raw_start": raw_start,
            "raw_end": raw_start + len(text),
            "cleaned_text_revision_id": CLEAN_REV,
            "start_offset": cleaned_start,
            "end_offset": cleaned_start + len(text),
            "quote_sha256": _sha256(text),
        },
    }


def make_structural_spans():
    return [
        make_structural_span(sequence=1, text=SEG1, cleaned_start=0, raw_start=0),
        make_structural_span(sequence=2, text=SEG2, cleaned_start=6, raw_start=11),
        make_structural_span(sequence=3, text=SEG3, cleaned_start=22, raw_start=27),
    ]


def make_structural_doc(spans=None):
    spans = make_structural_spans() if spans is None else spans
    return {
        "work": WORK,
        "source_id": "src_%s_%s" % (WORK, EDITION),
        "edition_part_artifact_id": EDITION_PART,
        "evidence_level": "offset_level",
        "content_status": "machine_extracted",
        "span_count": len(spans),
        "spans": spans,
    }


def make_windows(include_short_span=False):
    windows = [
        {
            "window_id": "%s_w001" % WORK,
            "span_id": "ss_%s_%s_o%07d" % (WORK, EDITION, 11),
            "text": SEG2,
            "text_sha256": _sha256(SEG2),
            "raw_start": 11,
            "raw_end": 27,
        },
        {
            "window_id": "%s_w002" % WORK,
            "span_id": "ss_%s_%s_o%07d" % (WORK, EDITION, 27),
            "text": SEG3,
            "text_sha256": _sha256(SEG3),
            "raw_start": 27,
            "raw_end": 40,
        },
    ]
    if include_short_span:
        windows.append(
            {
                "window_id": "%s_w003" % WORK,
                "span_id": "ss_%s_%s_o%07d" % (WORK, EDITION, 0),
                "text": SEG1,
                "text_sha256": _sha256(SEG1),
                "raw_start": 0,
                "raw_end": 6,
            }
        )
    return windows


def make_resolutions(include_short_span=False):
    resolutions = {
        "%s_w001" % WORK: {
            "boundary_origin": "cross_model_agreed",
            "segments": W001_SEGMENTS,
        },
        "%s_w002" % WORK: {
            "boundary_origin": "human_decided",
            "segments": W002_A_SEGMENTS,
        },
    }
    if include_short_span:
        resolutions["%s_w003" % WORK] = {
            "boundary_origin": "cross_model_agreed",
            "segments": [[0, 3], [3, 6]],
        }
    return resolutions


def make_window_responses(disputed=True, include_short_span=False):
    def parsed(segments):
        return {
            "valid": True,
            "segments": [list(pair) for pair in segments],
            "reasons": ["r%d" % i for i in range(len(segments))],
            "error": None,
        }

    responses = [
        {
            "window_id": "%s_w001" % WORK,
            "status": "agreed",
            "reason": None,
            "segments": W001_SEGMENTS,
            "proposal_a": parsed(W001_SEGMENTS),
            "proposal_b": parsed(W001_SEGMENTS),
        },
        {
            "window_id": "%s_w002" % WORK,
            "status": "disputed",
            "reason": "boundary_mismatch",
            "segments": None,
            "proposal_a": parsed(W002_A_SEGMENTS),
            "proposal_b": parsed(W002_B_SEGMENTS),
        },
    ]
    if include_short_span:
        responses.append(
            {
                "window_id": "%s_w003" % WORK,
                "status": "agreed",
                "reason": None,
                "segments": [[0, 3], [3, 6]],
                "proposal_a": parsed([[0, 3], [3, 6]]),
                "proposal_b": parsed([[0, 3], [3, 6]]),
            }
        )
    return responses


def make_decisions():
    return [
        {
            "schema": "m3_boundary_decision/1",
            "window_id": "%s_w002" % WORK,
            "decision_type": "review_source_fidelity",
            "choice": "a",
            "segments": [list(pair) for pair in W002_A_SEGMENTS],
            "rationale": "合成裁决（synthetic_fixture）",
            "synthetic_fixture": True,
            "actor_ref": "fixture_reviewer",
        }
    ]


def build_semantic_doc(*, include_short_span=False):
    return compile_semantic_offset(
        structural_spans=make_structural_spans(),
        windows=make_windows(include_short_span=include_short_span),
        resolutions=make_resolutions(include_short_span=include_short_span),
        raw_text_revision_id=RAW_REV,
        raw_text=RAW_TEXT,
        cleaned_text_revision_id=CLEAN_REV,
        cleaned_text=CLEANED_TEXT,
        patches=PATCHES,
        work=WORK,
        edition=EDITION,
        edition_part_artifact_id=EDITION_PART,
    )


def golden_inputs(*, include_short_span=False):
    """Golden 输入（Gate 的全部关键字参数）。"""
    return {
        "cleaned_text": CLEANED_TEXT,
        "patches": PATCHES,
        "structural_spans_doc": make_structural_doc(),
        "semantic_spans_doc": build_semantic_doc(include_short_span=include_short_span),
        "window_responses": make_window_responses(include_short_span=include_short_span),
        "decisions": make_decisions(),
        "model_min_chars": 12,
    }


def evaluate(**overrides):
    kwargs = golden_inputs()
    kwargs.update(overrides)
    return evaluate_semantic_offset(**kwargs)


class TestSemanticGate(unittest.TestCase):
    """八项独立语义检查（名称与顺序固定）。"""

    def test_evaluate_semantic_offset_golden_all_pass(self):
        """Golden 全绿：八项检查按固定顺序全 ok，semantic == passed。"""
        result = evaluate()
        self.assertEqual(result["semantic"], "passed")
        self.assertEqual(list(result["checks"].keys()), CHECK_NAMES)
        for name, check in result["checks"].items():
            self.assertTrue(check["ok"], "%s 意外失败: %s" % (name, check["detail"]))

    def test_semantic_gate_ast_forbids_compiler_imports(self):
        """第 88 条护栏：AST 断言未 import 任何编译器实现模块（含 from . import X 写法）。"""
        source = (
            Path(__file__).resolve().parents[1] / "semantic_gate.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)

        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.append(node.module)
                for alias in node.names:
                    imported.append(alias.name)

        forbidden = [
            "offset_assemble",
            "review",
            "proposer",
            "offset_rules",
            "proposals",
            "text_compiler",
            "step_offset",
            "gate_offset",
        ]
        for module in imported:
            for banned in forbidden:
                self.assertNotIn(
                    banned, module, "semantic_gate.py 违规引入编译模块 %r" % module
                )

    def test_semantic_gate_catches_gap_and_overlap(self):
        """篡改片段造成缺口或重叠时，semantic_contiguous_coverage 判失败。"""
        gapped = golden_inputs()
        gapped["semantic_spans_doc"]["spans"][1]["start_offset"] += 2
        result = evaluate_semantic_offset(**gapped)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["semantic_contiguous_coverage"]["ok"])

        overlapped = golden_inputs()
        overlapped["semantic_spans_doc"]["spans"][1]["start_offset"] -= 2
        result = evaluate_semantic_offset(**overlapped)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["semantic_contiguous_coverage"]["ok"])

    def test_tampered_semantic_text_fails_strict_offset(self):
        """语义片段文本被篡改时，semantic_strict_offset 判失败。"""
        tampered = golden_inputs()
        tampered["semantic_spans_doc"]["spans"][0]["text"] = "篡改文本。\n"
        result = evaluate_semantic_offset(**tampered)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["semantic_strict_offset"]["ok"])

    def test_tampered_semantic_quote_hash_fails_strict_offset(self):
        """语义片段引文哈希不符时，semantic_strict_offset 判失败。"""
        tampered = golden_inputs()
        tampered["semantic_spans_doc"]["spans"][0]["quote_sha256"] = "0" * 64
        result = evaluate_semantic_offset(**tampered)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["semantic_strict_offset"]["ok"])

    def test_broken_structural_ref_fails_structural_refs_consistent(self):
        """结构引用指向不存在的结构 Span 时，structural_refs_consistent 判失败。"""
        tampered = golden_inputs()
        tampered["semantic_spans_doc"]["spans"][1]["structural_refs"][0][
            "span_id"
        ] = "ss_%s_%s_o%07d" % (WORK, EDITION, 9999)
        result = evaluate_semantic_offset(**tampered)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["structural_refs_consistent"]["ok"])

    def test_offset_mismatch_with_structural_ref_fails(self):
        """局部起点与全局起点换算不一致时，structural_refs_consistent 判失败。"""
        tampered = golden_inputs()
        tampered["semantic_spans_doc"]["spans"][1]["structural_refs"][0]["start"] = 2
        result = evaluate_semantic_offset(**tampered)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["structural_refs_consistent"]["ok"])

    def test_non_window_split_fails_window_rule_fidelity(self):
        """长度不足阈值的片段被切成多片时，window_rule_fidelity 判失败。"""
        inputs = golden_inputs(include_short_span=True)
        result = evaluate_semantic_offset(**inputs)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["window_rule_fidelity"]["ok"])

    def test_window_threshold_discrepancy_fails_window_rule_fidelity(self):
        """model_min_chars 与该文档实际切分不符时，window_rule_fidelity 判失败。"""
        result = evaluate(model_min_chars=14)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["window_rule_fidelity"]["ok"])

        # 阈值 <= 12 时窗口集合不变，不应误报
        self.assertEqual(evaluate(model_min_chars=12)["checks"]["window_rule_fidelity"]["ok"], True)

    def test_unresolved_dispute_fails_semantic_gate(self):
        """第 88 条护栏：遗留未决分歧窗口时，disputes_resolved_zero 判 ok: False。"""
        result = evaluate(decisions=[])
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["disputes_resolved_zero"]["ok"])

        mismatched = golden_inputs()
        mismatched["decisions"][0]["window_id"] = "%s_w001" % WORK
        result = evaluate_semantic_offset(**mismatched)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["disputes_resolved_zero"]["ok"])

    def test_decision_on_agreed_window_fails(self):
        """对双路一致窗口提交裁决属越权，disputes_resolved_zero 判失败。"""
        tampered = golden_inputs()
        extra = dict(tampered["decisions"][0])
        extra["window_id"] = "%s_w001" % WORK
        extra["segments"] = [list(pair) for pair in W001_SEGMENTS]
        extra["choice"] = "custom"
        tampered["decisions"] = tampered["decisions"] + [extra]
        result = evaluate_semantic_offset(**tampered)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["disputes_resolved_zero"]["ok"])

    def test_tampered_decision_segments_fails(self):
        """裁决切分与语义片段不一致（篡改裁决）时，disputes_resolved_zero 判失败。"""
        tampered = golden_inputs()
        tampered["decisions"][0]["segments"] = [[0, 5], [5, 13]]
        result = evaluate_semantic_offset(**tampered)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["disputes_resolved_zero"]["ok"])

    def test_upgraded_glyphbox_fails_evidence_level_honest(self):
        """伪造升格为 glyphbox_level 时，evidence_level_honest 必判失败。"""
        span_tampered = golden_inputs()
        span_tampered["semantic_spans_doc"]["spans"][0]["evidence_level"] = "glyphbox_level"
        result = evaluate_semantic_offset(**span_tampered)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["evidence_level_honest"]["ok"])

        top_tampered = golden_inputs()
        top_tampered["semantic_spans_doc"]["evidence_level_counts"] = {
            "offset_level": 4,
            "glyphbox_level": 1,
        }
        result = evaluate_semantic_offset(**top_tampered)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["evidence_level_honest"]["ok"])

    def test_duplicate_semantic_span_id_fails_identity(self):
        """语义片段 ID 重复时，semantic_identity 判失败。"""
        tampered = golden_inputs()
        spans = tampered["semantic_spans_doc"]["spans"]
        spans[1]["semantic_span_id"] = spans[0]["semantic_span_id"]
        result = evaluate_semantic_offset(**tampered)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["semantic_identity"]["ok"])

    def test_invalid_semantic_span_id_regex_fails_identity(self):
        """语义片段 ID 形不符（含自创前缀）时，semantic_identity 判失败。"""
        for bad_id in ("sem_qianyuan_o0000000", "bnd_qianyuan_ed01_o0000000", "invalid"):
            tampered = golden_inputs()
            tampered["semantic_spans_doc"]["spans"][0]["semantic_span_id"] = bad_id
            result = evaluate_semantic_offset(**tampered)
            self.assertEqual(result["semantic"], "failed", bad_id)
            self.assertFalse(result["checks"]["semantic_identity"]["ok"], bad_id)

    def test_semantic_span_count_mismatch_fails_header_counts(self):
        """顶层 span_count 与实体不符时，header_counts 判失败。"""
        tampered = golden_inputs()
        tampered["semantic_spans_doc"]["span_count"] = 99
        result = evaluate_semantic_offset(**tampered)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["header_counts"]["ok"])

    def test_window_count_mismatch_fails_header_counts(self):
        """顶层 window_count 与实际窗口数不符时，header_counts 判失败。"""
        tampered = golden_inputs()
        tampered["semantic_spans_doc"]["window_count"] = 99
        result = evaluate_semantic_offset(**tampered)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["header_counts"]["ok"])

    def test_dispute_count_mismatch_fails_header_counts(self):
        """顶层 dispute_count 与实际分歧数不符时，header_counts 判失败。"""
        tampered = golden_inputs()
        tampered["semantic_spans_doc"]["dispute_count"] = 0
        result = evaluate_semantic_offset(**tampered)
        self.assertEqual(result["semantic"], "failed")
        self.assertFalse(result["checks"]["header_counts"]["ok"])


if __name__ == "__main__":
    unittest.main()
