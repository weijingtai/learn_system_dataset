"""ACT impl-02/02：独立结构 Gate evaluate_structural 的测试。

输入取自 fixture（manifest.yaml、pages/*.json、anomalies.yaml、spans.yaml）；
evidence_pages 默认 ``{"page_002"}``；batch_size 默认 10。每个篡改用例断言
``structural == "failed"`` 且指定检查的 ``ok`` 为 ``False``。
"""

import ast
import copy
import json
import os
import unittest

import yaml

from pipeline.corpus_compiler.gate import evaluate_structural

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_TESTS_DIR, os.pardir, os.pardir, os.pardir))
_FIXTURE_DIR = os.path.join(_REPO_ROOT, "pipeline", "corpus", "_fixture", "mini_ed01")

_EIGHT_CHECK_NAMES = (
    "page_accounting",
    "contiguous_coverage",
    "strict_offset",
    "concat_equals_block",
    "glyphbox_anchors",
    "span_identity",
    "batch_rules",
    "header_counts",
)


def _load_yaml(name):
    with open(os.path.join(_FIXTURE_DIR, name), encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_json(name):
    with open(os.path.join(_FIXTURE_DIR, name), encoding="utf-8") as handle:
        return json.load(handle)


def _base_gate_inputs():
    """返回 (manifest, page_docs, terminal_states, evidence_pages, spans_doc, batch_size)。"""
    manifest = _load_yaml("manifest.yaml")
    page_docs = {
        "page_001": _load_json("pages/page_001.json"),
        "page_002": _load_json("pages/page_002.json"),
        "page_003": _load_json("pages/page_003.json"),
    }
    anomalies = _load_yaml("anomalies.yaml")
    terminal_states = {
        entry["page"]: entry["terminal_state"] for entry in anomalies["entries"]
    }
    spans_doc = _load_yaml("spans.yaml")
    evidence_pages = {"page_002"}
    batch_size = 10
    return manifest, page_docs, terminal_states, evidence_pages, spans_doc, batch_size


def _find_span_index(spans_doc, page, line_index):
    for i, span in enumerate(spans_doc["spans"]):
        if span["page"] == page and span["line_index"] == line_index:
            return i
    raise AssertionError("未在 spans_doc 中找到 page=%s line_index=%d 的 span" % (page, line_index))


class GateGoldenTests(unittest.TestCase):
    """金标 Span 应通过全部 8 项检查，语义层恒为 not_evaluated。"""

    def test_fixture_spans_pass_all_eight_checks(self):
        manifest, page_docs, terminal_states, evidence_pages, spans_doc, batch_size = _base_gate_inputs()
        report = evaluate_structural(
            manifest=manifest,
            page_docs=page_docs,
            terminal_states=terminal_states,
            evidence_pages=evidence_pages,
            spans_doc=spans_doc,
            batch_size=batch_size,
        )
        self.assertEqual(report["structural"], "passed")
        for name in _EIGHT_CHECK_NAMES:
            check = report["checks"][name]
            self.assertTrue(check["ok"], msg="%s 未通过: %s" % (name, check["failures"]))

    def test_semantic_always_not_evaluated_and_profile_structural_only(self):
        manifest, page_docs, terminal_states, evidence_pages, spans_doc, batch_size = _base_gate_inputs()
        report = evaluate_structural(
            manifest=manifest,
            page_docs=page_docs,
            terminal_states=terminal_states,
            evidence_pages=evidence_pages,
            spans_doc=spans_doc,
            batch_size=batch_size,
        )
        self.assertEqual(report["semantic"], "not_evaluated")
        self.assertEqual(report["gate_profile"], "structural_only")

    def test_pages_report_coverage_one_and_excluded_page_002(self):
        manifest, page_docs, terminal_states, evidence_pages, spans_doc, batch_size = _base_gate_inputs()
        report = evaluate_structural(
            manifest=manifest,
            page_docs=page_docs,
            terminal_states=terminal_states,
            evidence_pages=evidence_pages,
            spans_doc=spans_doc,
            batch_size=batch_size,
        )
        self.assertEqual(report["pages"]["page_001"]["coverage"], 1.0)
        self.assertEqual(report["pages"]["page_003"]["coverage"], 1.0)
        self.assertEqual(report["pages"]["page_002"]["status"], "excluded")


class GateTamperedSpansTests(unittest.TestCase):
    """篡改 spans_doc 后指定检查必须失败，Gate 整体为 failed。"""

    def _evaluate(self, spans_doc=None, terminal_states=None, evidence_pages=None, batch_size=None):
        manifest, page_docs, base_terminal_states, base_evidence_pages, base_spans_doc, base_batch_size = (
            _base_gate_inputs()
        )
        return evaluate_structural(
            manifest=manifest,
            page_docs=page_docs,
            terminal_states=terminal_states if terminal_states is not None else base_terminal_states,
            evidence_pages=evidence_pages if evidence_pages is not None else base_evidence_pages,
            spans_doc=spans_doc if spans_doc is not None else base_spans_doc,
            batch_size=batch_size if batch_size is not None else base_batch_size,
        )

    def test_drop_span_fails_contiguous_coverage(self):
        _, _, _, _, spans_doc, _ = _base_gate_inputs()
        spans_doc = copy.deepcopy(spans_doc)
        idx = _find_span_index(spans_doc, "page_003", 7)
        del spans_doc["spans"][idx]
        report = self._evaluate(spans_doc=spans_doc)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["contiguous_coverage"]["ok"])

    def test_overlap_fails_contiguous_coverage(self):
        _, _, _, _, spans_doc, _ = _base_gate_inputs()
        spans_doc = copy.deepcopy(spans_doc)
        spans_doc["spans"][1]["start_offset"] = spans_doc["spans"][0]["end_offset"]
        report = self._evaluate(spans_doc=spans_doc)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["contiguous_coverage"]["ok"])

    def test_shift_end_offset_fails_strict_offset(self):
        _, _, _, _, spans_doc, _ = _base_gate_inputs()
        spans_doc = copy.deepcopy(spans_doc)
        spans_doc["spans"][0]["end_offset"] += 1
        report = self._evaluate(spans_doc=spans_doc)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["strict_offset"]["ok"])

    def test_changed_text_fails_strict_offset(self):
        _, _, _, _, spans_doc, _ = _base_gate_inputs()
        spans_doc = copy.deepcopy(spans_doc)
        spans_doc["spans"][0]["text"] = "改动文本"
        report = self._evaluate(spans_doc=spans_doc)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["strict_offset"]["ok"])

    def test_bbox_change_fails_glyphbox_anchors(self):
        _, _, _, _, spans_doc, _ = _base_gate_inputs()
        spans_doc = copy.deepcopy(spans_doc)
        spans_doc["spans"][0]["source_anchor"]["bbox"]["x"] += 1.0
        report = self._evaluate(spans_doc=spans_doc)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["glyphbox_anchors"]["ok"])

    def test_glyph_id_change_fails_glyphbox_anchors(self):
        _, _, _, _, spans_doc, _ = _base_gate_inputs()
        spans_doc = copy.deepcopy(spans_doc)
        spans_doc["spans"][0]["source_anchor"]["chars"][0]["glyph_id"] = "bogus_glyph_id"
        report = self._evaluate(spans_doc=spans_doc)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["glyphbox_anchors"]["ok"])

    def test_image_sha_change_fails_glyphbox_anchors(self):
        _, _, _, _, spans_doc, _ = _base_gate_inputs()
        spans_doc = copy.deepcopy(spans_doc)
        spans_doc["spans"][0]["source_anchor"]["image_sha256"] = "0" * 64
        report = self._evaluate(spans_doc=spans_doc)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["glyphbox_anchors"]["ok"])

    def test_line_index_mismatch_fails_glyphbox_anchors(self):
        _, _, _, _, spans_doc, _ = _base_gate_inputs()
        spans_doc = copy.deepcopy(spans_doc)
        idx = _find_span_index(spans_doc, "page_001", 0)
        spans_doc["spans"][idx]["line_index"] = 1
        report = self._evaluate(spans_doc=spans_doc)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["glyphbox_anchors"]["ok"])

    def test_span_id_page_mismatch_fails_span_identity(self):
        _, _, _, _, spans_doc, _ = _base_gate_inputs()
        spans_doc = copy.deepcopy(spans_doc)
        idx = _find_span_index(spans_doc, "page_001", 0)
        spans_doc["spans"][idx]["span_id"] = "ss_sanche_ed01_p0099_s01"
        report = self._evaluate(spans_doc=spans_doc)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["span_identity"]["ok"])

    def test_duplicate_span_id_fails_span_identity(self):
        _, _, _, _, spans_doc, _ = _base_gate_inputs()
        spans_doc = copy.deepcopy(spans_doc)
        spans_doc["spans"][1]["span_id"] = spans_doc["spans"][0]["span_id"]
        report = self._evaluate(spans_doc=spans_doc)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["span_identity"]["ok"])

    def test_batch_over_size_fails_batch_rules(self):
        report = self._evaluate(batch_size=3)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["batch_rules"]["ok"])

    def test_batch_cross_page_fails_batch_rules(self):
        _, _, _, _, spans_doc, _ = _base_gate_inputs()
        spans_doc = copy.deepcopy(spans_doc)
        idx = _find_span_index(spans_doc, "page_001", 0)
        spans_doc["spans"][idx]["batch_id"] = "sanche_b002"
        report = self._evaluate(spans_doc=spans_doc)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["batch_rules"]["ok"])

    def test_header_span_count_fails_header_counts(self):
        _, _, _, _, spans_doc, _ = _base_gate_inputs()
        spans_doc = copy.deepcopy(spans_doc)
        spans_doc["span_count"] = spans_doc["span_count"] + 1
        report = self._evaluate(spans_doc=spans_doc)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["header_counts"]["ok"])

    def test_remove_all_page_003_spans_fails_page_accounting(self):
        _, _, _, _, spans_doc, _ = _base_gate_inputs()
        spans_doc = copy.deepcopy(spans_doc)
        spans_doc["spans"] = [s for s in spans_doc["spans"] if s["page"] != "page_003"]
        report = self._evaluate(spans_doc=spans_doc)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["page_accounting"]["ok"])

    def test_unlabeled_empty_page_fails_page_accounting(self):
        report = self._evaluate(terminal_states={})
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["page_accounting"]["ok"])

    def test_known_unrecognizable_without_evidence_fails_page_accounting(self):
        report = self._evaluate(evidence_pages=set())
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["page_accounting"]["ok"])
        details = " ".join(
            failure["detail"] for failure in report["checks"]["page_accounting"]["failures"]
        )
        self.assertIn("裸标", details)

    def test_deferred_page_fails_page_accounting(self):
        _, _, terminal_states, _, _, _ = _base_gate_inputs()
        terminal_states = dict(terminal_states)
        terminal_states["page_003"] = "deferred"
        report = self._evaluate(terminal_states=terminal_states)
        self.assertEqual(report["structural"], "failed")
        self.assertFalse(report["checks"]["page_accounting"]["ok"])


class GateIndependenceTests(unittest.TestCase):
    """Gate 不得 import 编译器或序列化模块（防止同错同过）。"""

    def test_gate_does_not_import_compiler(self):
        gate_path = os.path.join(_REPO_ROOT, "pipeline", "corpus_compiler", "gate.py")
        with open(gate_path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=gate_path)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.append(node.module)
                for alias in node.names:
                    imported.append(
                        "%s.%s" % (node.module, alias.name) if node.module else alias.name
                    )
        for name in imported:
            self.assertNotIn("compiler", name)
            self.assertNotIn("serialize", name)


if __name__ == "__main__":
    unittest.main()
