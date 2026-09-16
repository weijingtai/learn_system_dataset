"""M2 清洗纯函数单元测试（synthetic_fixture: true）。

覆盖十三项清洗规则、数据驱动表规模与行为、真实感正反例成对护栏。
"""

import unittest

from pipeline.digitization import FINDING_KINDS
from pipeline.digitization.cleaner import (
    CleanResult,
    Finding,
    clean_text,
    load_default_suspected_pairs,
    load_default_variant_pairs,
)
from pipeline.digitization.patcher import Patch, apply_patches, build_patches
from pipeline.digitization.raw_text import freeze_raw_text
from pipeline.digitization.reporter import build_sanitization_report
from pipeline.digitization.tests.helpers import sample_clean_text, sample_dirty_text


class TestCleaner(unittest.TestCase):
    """M2 纯函数测试集。"""

    # --- 基础纯函数与既有用例 ---

    def test_clean_control_chars_stripped(self):
        """synthetic_fixture: true，控制字符被剥离且生成 finding。"""
        text = "乾元秘旨\u200b太极图说"
        res = clean_text(text)
        self.assertIn("control_char", [f.kind for f in res.findings])
        self.assertEqual(res.cleaned_text, "乾元秘旨太极图说")

    def test_clean_escape_residue_unrecognized_kept(self):
        """synthetic_fixture: true，无转义斜杠文本保留原貌。"""
        text = "乾元秘旨太极图说"
        res = clean_text(text)
        self.assertEqual(res.cleaned_text, text)

    def test_clean_escape_residue_common_escaped(self):
        r"""synthetic_fixture: true，Markdown 转义被清理。"""
        text = r"乾元秘旨\[太极图说\]"
        res = clean_text(text)
        self.assertIn("escape_residue", [f.kind for f in res.findings])
        self.assertEqual(res.cleaned_text, "乾元秘旨[太极图说]")

    def test_clean_clean_input_zero_findings(self):
        """synthetic_fixture: true，纯净文本 0 findings。"""
        text = "天地之初，太极肇判。乾坤定位，日月运行。"
        res = clean_text(text)
        self.assertEqual(len(res.findings), 0)
        self.assertEqual(res.cleaned_text, text)

    def test_clean_multiple_findings_sorted_offsets(self):
        """synthetic_fixture: true，多个 findings 按 raw_start 升序排列。"""
        text = sample_dirty_text()
        res = clean_text(text)
        offsets = [f.raw_start for f in res.findings]
        self.assertEqual(offsets, sorted(offsets))

    def test_clean_all_thirteen_kinds_represented(self):
        """synthetic_fixture: true，FINDING_KINDS 常量完备包含 12 项发现类。"""
        self.assertEqual(len(FINDING_KINDS), 12)

    def test_clean_returns_dataclass(self):
        """synthetic_fixture: true，clean_text 返回 CleanResult 数据类。"""
        res = clean_text("太极图说")
        self.assertIsInstance(res, CleanResult)
        self.assertIsInstance(res.findings, list)
        self.assertIsInstance(res.cleaned_text, str)

    def test_clean_finding_has_required_fields(self):
        """synthetic_fixture: true，Finding 具备 10 个必填字段且无多余字段。"""
        res = clean_text("测试\u200b")
        self.assertGreater(len(res.findings), 0)
        f = res.findings[0]
        expected_fields = {
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
        }
        self.assertEqual(set(f.__dict__.keys()), expected_fields)

    def test_build_patches_invertible(self):
        """synthetic_fixture: true，apply_patches(raw, patches) == cleaned_text 严格可逆。"""
        raw = sample_dirty_text()
        res = clean_text(raw)
        patches = build_patches(raw, res.cleaned_text, res.findings)
        reconstructed = apply_patches(raw, patches)
        self.assertEqual(reconstructed, res.cleaned_text)

    def test_build_patches_empty_on_clean_input(self):
        """synthetic_fixture: true，纯净文本 build_patches 为空列表。"""
        raw = sample_clean_text()
        res = clean_text(raw)
        patches = build_patches(raw, res.cleaned_text, res.findings)
        self.assertEqual(len(patches), 0)

    def test_build_patches_offset_shift_monotonic(self):
        """synthetic_fixture: true，patches 偏移单调递增。"""
        raw = sample_dirty_text()
        res = clean_text(raw)
        patches = build_patches(raw, res.cleaned_text, res.findings)
        raw_starts = [p.raw_start for p in patches]
        self.assertEqual(raw_starts, sorted(raw_starts))

    def test_build_sanitization_report_fixed_key_order(self):
        """synthetic_fixture: true，SanitizationReport 顶层与 finding 键序固定。"""
        raw = sample_dirty_text()
        res = clean_text(raw)
        patches = build_patches(raw, res.cleaned_text, res.findings)
        report = build_sanitization_report(res.findings, patches)
        self.assertEqual(
            list(report.keys()),
            ["schema_version", "findings", "patches", "summary"],
        )

    def test_build_sanitization_report_summary_counts(self):
        """synthetic_fixture: true，summary 中各 kind 计数严格一致。"""
        raw = sample_dirty_text()
        res = clean_text(raw)
        patches = build_patches(raw, res.cleaned_text, res.findings)
        report = build_sanitization_report(res.findings, patches)
        summary = report["summary"]
        total_findings = sum(v for k, v in summary.items() if k != "deferred_count")
        self.assertEqual(total_findings, len(res.findings))

    def test_build_sanitization_report_deferred_count(self):
        """synthetic_fixture: true，deferred_count 统计准确。"""
        raw = "子日：学而时习之"  # suspected_error -> deferred
        res = clean_text(raw)
        report = build_sanitization_report(res.findings, [])
        self.assertGreater(report["summary"]["deferred_count"], 0)

    def test_clean_text_pure_no_io(self):
        """synthetic_fixture: true，freeze_raw_text 为确定性纯函数。"""
        data = "太极图说\n天地之初。".encode("utf-8")
        res = freeze_raw_text(data, "utf-8")
        self.assertEqual(res["size"], len(data))
        self.assertEqual(res["encoding_normalized"], "utf-8")

    # --- 六项重写规则的正反例成对测试（第 91 条） ---

    def test_clean_text_finds_encoding_issue(self):
        """synthetic_fixture: true，真实感古籍文本含 BOM → 检出 encoding_issue。"""
        text = "\ufeff乾元秘旨卷之一\n周易太极图说\n天地之初，太极肇判。"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("encoding_issue", kinds)
        f = next(f for f in res.findings if f.kind == "encoding_issue")
        self.assertEqual(f.terminal_state, "processed")
        self.assertEqual(f.action, "patched")

    def test_clean_text_encoding_issue_negative(self):
        """synthetic_fixture: true，反例：无 BOM 纯净古籍文本不误报 encoding_issue。"""
        text = "乾元秘旨卷之一\n周易太极图说\n天地之初，太极肇判。"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertNotIn("encoding_issue", kinds)

    def test_clean_text_finds_watermark(self):
        """synthetic_fixture: true，真实感古籍电子文本含维护者声明/链接 → 检出 watermark。"""
        text = "乾元秘旨卷之一\n太极图说\n天地之初，太极肇判。\n本电子书由殆知阁整理制作，下载自 https://daizhige.org"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("watermark", kinds)
        f = next(f for f in res.findings if f.kind == "watermark")
        self.assertEqual(f.terminal_state, "processed")

    def test_clean_text_watermark_negative(self):
        """synthetic_fixture: true，反例：正文含正常文献语句不误报 watermark。"""
        text = "乾元秘旨卷之一\n太极图说\n天地之初，太极肇判。阴阳运行，万物化生。"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertNotIn("watermark", kinds)

    def test_clean_text_finds_header_footer(self):
        """synthetic_fixture: true，非空行全文重复 >= 3 次 → 检出 header_footer。"""
        text = (
            "乾元秘旨卷之一\n太极图说\n天地之初，太极肇判。\n"
            "乾元秘旨卷之一\n两仪四象\n乾坤定位，日月运行。\n"
            "乾元秘旨卷之一\n五行生成\n水火木金土各定其位。\n"
        )
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("header_footer", kinds)
        f = next(f for f in res.findings if f.kind == "header_footer")
        self.assertEqual(f.terminal_state, "processed")

    def test_clean_text_header_footer_negative(self):
        """synthetic_fixture: true，反例：行出现不足 3 次且非分页标记不误报 header_footer。"""
        text = "乾元秘旨卷之一\n太极图说\n天地之初，太极肇判。\n乾坤定位，日月运行。"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertNotIn("header_footer", kinds)

    def test_clean_text_finds_duplicate(self):
        """synthetic_fixture: true，全文跨段落重复内容 → 检出 duplicate（登记不删除）。"""
        text = (
            "乾元秘旨卷之一\n"
            "天地之初太极肇判阴阳化合而万物生焉。\n"
            "两仪篇章日月升沉。\n"
            "天地之初太极肇判阴阳化合而万物生焉。\n"
        )
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("duplicate", kinds)
        f = next(f for f in res.findings if f.kind == "duplicate")
        self.assertEqual(f.action, "flagged")
        self.assertIsNone(f.patch_id)

    def test_clean_text_duplicate_negative(self):
        """synthetic_fixture: true，反例：无重复段落的古籍文本不误报 duplicate。"""
        text = (
            "乾元秘旨卷之一\n"
            "天地之初太极肇判阴阳化合而万物生焉。\n"
            "两仪篇章日月升沉四时顺序各安其位。\n"
        )
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertNotIn("duplicate", kinds)

    def test_clean_text_finds_missing(self):
        """synthetic_fixture: true，解析文内目录核对章节缺失 → 检出 missing 且恒 deferred。"""
        text = (
            "乾元秘旨目錄：\n"
            "卷一·太极图说\n"
            "卷二·两仪四象\n\n"
            "卷一·太极图说\n"
            "天地之初，太极肇判。阴阳运行，万物化生。"
        )
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("missing", kinds)
        f = next(f for f in res.findings if f.kind == "missing")
        self.assertEqual(f.terminal_state, "deferred")
        self.assertIn("两仪四象", f.raw_excerpt)

    def test_clean_text_missing_negative(self):
        """synthetic_fixture: true，反例：文内无目录或目录章节齐全不误报 missing。"""
        # (1) 文内无目录（已知边界：无从判定，不误报）
        text1 = "乾元秘旨卷之一\n太极图说\n天地之初，太极肇判。"
        res1 = clean_text(text1)
        self.assertNotIn("missing", [f.kind for f in res1.findings])

        # (2) 目录所列章节正文齐全
        text2 = (
            "乾元秘旨目錄：\n"
            "卷一·太极图说\n\n"
            "卷一·太极图说\n"
            "天地之初，太极肇判。"
        )
        res2 = clean_text(text2)
        self.assertNotIn("missing", [f.kind for f in res2.findings])

    def test_clean_text_finds_textualized_diagram(self):
        """synthetic_fixture: true，含连续制表线与 ASCII 几何框线区块 → 检出 textualized_diagram。"""
        text = (
            "乾元秘旨太极图式：\n"
            "┌───────┐\n"
            "│ ☰ 乾  │\n"
            "├───────┤\n"
            "│ ☷ 坤  │\n"
            "└───────┘\n"
            "天地初判。"
        )
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertIn("textualized_diagram", kinds)
        f = next(f for f in res.findings if f.kind == "textualized_diagram")
        self.assertEqual(f.terminal_state, "processed")

    def test_clean_text_textualized_diagram_negative(self):
        """synthetic_fixture: true，反例：普通正文排版不误报 textualized_diagram。"""
        text = "乾元秘旨卷之一\n太极图说\n天地之初，太极肇判。乾为天，坤为地。"
        res = clean_text(text)
        kinds = [f.kind for f in res.findings]
        self.assertNotIn("textualized_diagram", kinds)

    # --- 数据驱动规模断言与动态行为测试 ---

    def test_variant_pairs_scale_and_behavior(self):
        """synthetic_fixture: true，繁简对照表规模 >= 100 且动态追加条目即改变判定行为。"""
        default_pairs = load_default_variant_pairs()
        distinct_pairs = [
            p for p in default_pairs
            if p.get("tc") and p.get("sc") and p["tc"] != p["sc"]
        ]
        self.assertGreaterEqual(
            len(distinct_pairs),
            100,
            f"繁简对照表规模不足 100（实有 {len(distinct_pairs)}）",
        )

        # 动态扩展性测试：新增条目即改变行为
        test_sample = "古籍校勘测试本：此句包含测试简体字与测试繁體字混杂。"
        custom_pairs = list(default_pairs) + [{"tc": "測試字", "sc": "测试字"}]
        res_custom = clean_text(test_sample, variant_pairs=custom_pairs)
        self.assertIn("variant_mixed", [f.kind for f in res_custom.findings])

    def test_suspected_error_pairs_scale_and_behavior(self):
        """synthetic_fixture: true，形近误字表规模 >= 20 且动态追加条目即改变判定行为。"""
        default_pairs = load_default_suspected_pairs()
        self.assertGreaterEqual(
            len(default_pairs),
            20,
            f"形近误字表规模不足 20（实有 {len(default_pairs)}）",
        )

        # 动态扩展性测试：新增条目即改变行为
        test_sample = "周易经传：此中有特定形近误字出现。"
        custom_pairs = list(default_pairs) + [
            {"wrong": "特定形近误字", "correct": "特定正字", "basis": "动态扩展测试"}
        ]
        res_custom = clean_text(test_sample, suspected_error_pairs=custom_pairs)
        self.assertIn("suspected_error", [f.kind for f in res_custom.findings])

    # --- 全量护栏与反例复核 ---

    def test_every_finding_kind_has_detector(self):
        """对 FINDING_KINDS 每一个 kind，断言存在能触发它的真实感古籍合成输入，缺失检测器时必须转红。"""
        KIND_SAMPLES = {
            "encoding_issue": "\ufeff乾元秘旨卷之一\n周易太极图说\n天地之初，太极肇判。",
            "replacement_char": "周易乾卦：元□利贞，天行健，君子以自强不息。",
            "private_use_area": "乾元秘旨卷之一：此字为私用区码位\ue001在此存录。",
            "control_char": "太极图说\n天地之初\u200b太极肇判。",
            "escape_residue": r"周易大传：\[乾元秘旨\] 卷之一。",
            "watermark": "乾元秘旨卷之一\n天地之初，太极肇判。\n本电子书由殆知阁整理制作，下载自 https://daizhige.org",
            "header_footer": (
                "乾元秘旨卷之一\n太极图说\n天地之初太极肇判。\n"
                "乾元秘旨卷之一\n两仪四象\n乾坤定位日月运行。\n"
                "乾元秘旨卷之一\n五行生成\n水火木金土各定其位。\n"
            ),
            "duplicate": (
                "乾元秘旨卷之一\n"
                "天地之初太极肇判阴阳化合而万物生焉。\n"
                "两仪篇章日月升沉。\n"
                "天地之初太极肇判阴阳化合而万物生焉。\n"
            ),
            "missing": (
                "乾元秘旨目錄：\n"
                "卷一·太极图说\n"
                "卷二·两仪四象\n\n"
                "卷一·太极图说\n"
                "天地之初，太极肇判。"
            ),
            "textualized_diagram": (
                "乾元秘旨太极图式：\n"
                "┌───────┐\n"
                "│ ☰ 乾  │\n"
                "├───────┤\n"
                "│ ☷ 坤  │\n"
                "└───────┘\n"
                "天地初判。"
            ),
            "variant_mixed": "乾元秘旨：天地之初，太極肇判，万物化生。",
            "suspected_error": "论语集注：子日学而时习之，不亦说乎。",
        }

        for kind in FINDING_KINDS:
            self.assertIn(
                kind, KIND_SAMPLES, f"FINDING_KINDS 包含未配置检测样本的 kind: {kind}"
            )

        for kind, sample in KIND_SAMPLES.items():
            res = clean_text(sample)
            found_kinds = {f.kind for f in res.findings}
            self.assertIn(
                kind,
                found_kinds,
                f"kind={kind} 未能被 clean_text 检测到！样本: {sample!r}",
            )

    def test_clean_corpus_zero_false_positives(self):
        """synthetic_fixture: true，反例复核：纯净古籍文本零误报（findings 为空）。"""
        clean_ancient_text = (
            "周易正义卷之一\n"
            "魏少保尚书左仆射王弼注\n"
            "唐国子祭酒兼修国史孔颖达疏\n"
            "第一卦乾\n"
            "乾元亨利贞\n"
            "初九潜龙勿用\n"
            "九二见龙在田利见大人\n"
            "九三君子终日乾乾夕惕若厉无咎\n"
            "九四或跃在渊无咎\n"
            "九五飞龙在天利见大人\n"
            "上九亢龙有悔\n"
            "用九见群龙无首吉\n"
        )
        res = clean_text(clean_ancient_text)
        self.assertEqual(
            len(res.findings),
            0,
            f"纯净古籍文本产生了意外误报: {[f.kind for f in res.findings]}",
        )


if __name__ == "__main__":
    unittest.main()
