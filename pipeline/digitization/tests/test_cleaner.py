"""M2 清洗纯函数单元测试（synthetic_fixture: true）。"""

import unittest

from pipeline.digitization.cleaner import CleanResult, Finding, clean_text
from pipeline.digitization.patcher import Patch, apply_patches, build_patches
from pipeline.digitization.raw_text import freeze_raw_text
from pipeline.digitization.reporter import build_sanitization_report
from pipeline.digitization.tests.helpers import sample_clean_text, sample_dirty_text


class TestCleaner(unittest.TestCase):
    """M2 纯函数测试集。"""

    def test_clean_text_finds_replacement_chars(self):
        """synthetic_fixture: true，含 ? 的合成文本 → replacement_char finding。"""
        text = "测试文本带有替换字符?"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("replacement_char", kinds)
        f = next(f for f in res.findings if f.kind == "replacement_char")
        self.assertEqual(text[f.raw_start : f.raw_end], "?")

    def test_clean_text_finds_pua(self):
        """synthetic_fixture: true，含 PUA 字符 → private_use_area finding。"""
        text = "私用区字符\ue001在此。"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("private_use_area", kinds)
        f = next(f for f in res.findings if f.kind == "private_use_area")
        self.assertEqual(text[f.raw_start : f.raw_end], "\ue001")

    def test_clean_text_finds_escape_residue(self):
        r"""synthetic_fixture: true，含 \- 的文本 → escape_residue finding。"""
        text = r"转义残留验证：\- 以及 \["
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("escape_residue", kinds)

    def test_clean_text_finds_control_chars(self):
        """synthetic_fixture: true，含零宽字符 → control_char finding。"""
        text = "零宽控制字符\u200b测试"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("control_char", kinds)

    def test_clean_text_finds_variant_mixed(self):
        """synthetic_fixture: true，含繁简混杂 → variant_mixed finding。"""
        text = "简体中文与繁體字混用"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("variant_mixed", kinds)

    def test_clean_text_finds_suspected_error(self):
        """synthetic_fixture: true，含疑似形近误字 → suspected_error finding。"""
        text = "子日：学而时习之"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("suspected_error", kinds)

    def test_clean_text_no_findings_clean_input(self):
        """synthetic_fixture: true，无问题文本 → 0 findings。"""
        clean_input = sample_clean_text()
        res = clean_text(clean_input)
        self.assertEqual(len(res.findings), 0)
        self.assertEqual(res.cleaned_text, clean_input)

    def test_clean_text_deferred_blocks_gate(self):
        """synthetic_fixture: true，deferred finding → deferred_count > 0。"""
        # 构造包含形近误字（suspected_error 属于 deferred 终态）的文本
        text = "子日：温故而知新"
        res = clean_text(text)
        deferred = [f for f in res.findings if f.terminal_state == "deferred"]
        self.assertGreater(len(deferred), 0)

        report = build_sanitization_report(res.findings, [])
        self.assertGreater(report["summary"]["deferred_count"], 0)

    def test_build_patches_deterministic(self):
        """synthetic_fixture: true，两次调用字节相同。"""
        raw = "测试文本带有替换字符?以及转义\\-"
        res = clean_text(raw)
        p1 = build_patches(raw, res.cleaned_text, res.findings)
        p2 = build_patches(raw, res.cleaned_text, res.findings)
        self.assertEqual(len(p1), len(p2))
        for a, b in zip(p1, p2):
            self.assertEqual(a.__dict__, b.__dict__)

    def test_apply_patches_reversible(self):
        """synthetic_fixture: true，apply_patches(raw, patches) == cleaned。"""
        raw = "原始字串带零宽\u200b和转义\\-。"
        res = clean_text(raw)
        patches = build_patches(raw, res.cleaned_text, res.findings)
        reproduced_cleaned = apply_patches(raw, patches)
        self.assertEqual(reproduced_cleaned, res.cleaned_text)

    def test_build_sanitization_report_key_order(self):
        """synthetic_fixture: true，finding 键序与 report 顶层结构。"""
        raw = sample_dirty_text()
        res = clean_text(raw)
        patches = build_patches(raw, res.cleaned_text, res.findings)
        report = build_sanitization_report(res.findings, patches)

        self.assertEqual(report["schema_version"], "0.1.0-draft")
        self.assertIn("findings", report)
        self.assertIn("patches", report)
        self.assertIn("summary", report)

        expected_finding_keys = [
            "finding_id",
            "kind",
            "raw_start",
            "raw_end",
            "raw_excerpt",
            "context",
            "action",
            "patch_id",
            "basis",
            "terminal_state",
        ]
        for finding in report["findings"]:
            self.assertEqual(list(finding.keys()), expected_finding_keys)

    def test_build_sanitization_report_summary_counts(self):
        """synthetic_fixture: true，各 kind 计数与 deferred_count 正确。"""
        raw = sample_dirty_text()
        res = clean_text(raw)
        patches = build_patches(raw, res.cleaned_text, res.findings)
        report = build_sanitization_report(res.findings, patches)

        summary = report["summary"]
        total_findings = sum(v for k, v in summary.items() if k != "deferred_count")
        self.assertEqual(total_findings, len(res.findings))

        actual_deferred = sum(1 for f in res.findings if f.terminal_state == "deferred")
        self.assertEqual(summary["deferred_count"], actual_deferred)

    def test_findings_have_unique_ids(self):
        """synthetic_fixture: true，finding_id 格式 <kind>@<raw_start>-<raw_end>。"""
        raw = sample_dirty_text()
        res = clean_text(raw)
        ids = [f.finding_id for f in res.findings]
        self.assertEqual(len(ids), len(set(ids)))
        for f in res.findings:
            expected_id = f"{f.kind}@{f.raw_start}-{f.raw_end}"
            self.assertEqual(f.finding_id, expected_id)

    def test_findings_raw_offsets_consistent(self):
        """synthetic_fixture: true，raw_start < raw_end。"""
        raw = sample_dirty_text()
        res = clean_text(raw)
        for f in res.findings:
            self.assertLess(f.raw_start, f.raw_end)
            self.assertEqual(raw[f.raw_start : f.raw_end], f.raw_excerpt)

    def test_deferred_finding_in_report(self):
        """synthetic_fixture: true，测试 deferred 发现登记进 report。"""
        raw = "子日学而时习之"  # suspected_error -> deferred
        res = clean_text(raw)
        report = build_sanitization_report(res.findings, [])
        deferred_findings = [f for f in report["findings"] if f["terminal_state"] == "deferred"]
        self.assertGreater(len(deferred_findings), 0)
        self.assertEqual(report["summary"]["deferred_count"], len(deferred_findings))


    def test_clean_text_finds_encoding_issue(self):
        """synthetic_fixture: true，含 BOM 或编码声明 → encoding_issue finding。"""
        text = "\ufeff太极图说\n天地之初"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("encoding_issue", kinds)
        f = next(f for f in res.findings if f.kind == "encoding_issue")
        self.assertEqual(f.terminal_state, "processed")

    def test_clean_text_finds_watermark(self):
        """synthetic_fixture: true，含非文献水印内容 → watermark finding。"""
        text = "太极图说\nhttps://daizhige.org 殆知阁整理\n天地之初"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("watermark", kinds)
        f = next(f for f in res.findings if f.kind == "watermark")
        self.assertEqual(f.terminal_state, "processed")

    def test_clean_text_finds_header_footer(self):
        """synthetic_fixture: true，含重复页眉页脚行 → header_footer finding。"""
        text = "--- 第 1 页 ---\n太极图说\n天地之初"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("header_footer", kinds)
        f = next(f for f in res.findings if f.kind == "header_footer")
        self.assertEqual(f.terminal_state, "processed")

    def test_clean_text_finds_duplicate(self):
        """synthetic_fixture: true，含连续重复内容 → duplicate finding，登记位置不静默删除。"""
        text = "太极图说太极图说\n天地之初"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("duplicate", kinds)
        f = next(f for f in res.findings if f.kind == "duplicate")
        self.assertEqual(f.action, "flagged")
        self.assertIsNone(f.patch_id)

    def test_clean_text_finds_missing(self):
        """synthetic_fixture: true，含缺失缺口标记 → missing finding，终态恒 deferred。"""
        text = "太极图说【缺字】天地之初"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("missing", kinds)
        f = next(f for f in res.findings if f.kind == "missing")
        self.assertEqual(f.terminal_state, "deferred")

    def test_clean_text_finds_textualized_diagram(self):
        """synthetic_fixture: true，含文本化图表区块 → textualized_diagram finding。"""
        text = "太极图说\n【图表：太极阴阳总图】\n天地之初"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("textualized_diagram", kinds)
        f = next(f for f in res.findings if f.kind == "textualized_diagram")
        self.assertEqual(f.terminal_state, "processed")

    def test_every_finding_kind_has_detector(self):
        """对 FINDING_KINDS 每一个 kind，断言存在能触发它的合成输入，缺失检测器时必须转红。"""
        from pipeline.digitization import FINDING_KINDS

        KIND_SAMPLES = {
            "encoding_issue": "\ufeff太极图说",
            "replacement_char": "太极□说",
            "private_use_area": "天地\ue001之初",
            "control_char": "太极\u200b图说",
            "escape_residue": r"\[太极图说\]",
            "watermark": "太极图说 https://daizhige.org 殆知阁整理",
            "header_footer": "--- 第 1 页 ---\n太极图说",
            "duplicate": "太极图说太极图说",
            "missing": "太极图说【缺字】",
            "textualized_diagram": "太极图说【图表：太极阴阳图】",
            "variant_mixed": "繁體与简体",
            "suspected_error": "子日天地",
        }

        for kind in FINDING_KINDS:
            self.assertIn(kind, KIND_SAMPLES, f"FINDING_KINDS 包含未配置检测样本的 kind: {kind}")

        for kind, sample in KIND_SAMPLES.items():
            res = clean_text(sample)
            found_kinds = {f.kind for f in res.findings}
            self.assertIn(kind, found_kinds, f"kind={kind} 未能被 clean_text 检测到！样本: {sample!r}")


if __name__ == "__main__":
    unittest.main()
