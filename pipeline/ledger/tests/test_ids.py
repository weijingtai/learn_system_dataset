"""ACT impl-01/01：标识生成与校验（规格 §8.1）的单元测试。

先写本文件，运行 `python -m unittest discover -s pipeline/ledger/tests -t .`
因 `pipeline.ledger.ids` / `pipeline.ledger.errors` 尚不存在而全红。
"""

import ast
import unittest
from pathlib import Path

from pipeline.ledger import ids
from pipeline.ledger.errors import InvalidIdentifier, LedgerError

REPO_ROOT = Path(__file__).resolve().parents[3]

# 第 102 条 Q1：``<work>`` 段的唯一权威出处是 ids.py，其字符集禁止下划线。
_SPAN_ID_FAMILIES = ("source_span_id", "semantic_span_id")


class TestIds(unittest.TestCase):
    """覆盖 §8.1：20 个前缀家族、UUIDv4 发号、最长前缀判定与既有格式沿用。"""

    def test_new_id_matches_pattern_for_each_kind(self):
        # 20 个前缀家族逐字登记（第 100 条 D3、第 102 条 Q3 新增 semantic_span_id）
        self.assertEqual(len(ids.PATTERNS), 20)
        # new_id 支持的 9 个 kind 全部能被 validate 接受
        for kind in (
            "artifact_id",
            "artifact_revision_id",
            "processing_run_id",
            "step_run_id",
            "release_id",
            "school_view_id",
            "conflict_group_id",
            "entry_id",
        ):
            value = ids.new_id(kind)
            self.assertEqual(ids.validate(kind, value), value)
        for stage in ids.STAGES:
            value = ids.new_id("stage_package_id", stage=stage)
            self.assertEqual(ids.validate("stage_package_id", value), value)

    def test_stage_package_requires_valid_stage(self):
        for bad in ("m9", "ledger"):
            with self.assertRaises(InvalidIdentifier):
                ids.new_id("stage_package_id", stage=bad)

    def test_validate_rejects_uppercase_hex(self):
        with self.assertRaises(InvalidIdentifier) as ctx:
            ids.validate("artifact_id", "art_" + "A" * 32)
        self.assertEqual(ctx.exception.code, "ID_001")

    def test_validate_rejects_wrong_length(self):
        for length in (31, 33):
            with self.assertRaises(InvalidIdentifier):
                ids.validate("artifact_id", "art_" + "a" * length)

    def test_validate_rejects_pr_for_processing_run(self):
        with self.assertRaises(InvalidIdentifier) as ctx:
            ids.validate("processing_run_id", "pr_" + "a" * 32)
        self.assertEqual(ctx.exception.code, "ID_001")

    def test_kind_of_prefers_longest_prefix(self):
        # co_shared_ 必须先于 co_ 匹配
        self.assertEqual(ids.kind_of("co_shared_x_01"), "shared_concept_id")
        self.assertEqual(ids.kind_of("co_qizheng_000042"), "technique_concept_id")
        # prun_ 必须先于 pr_ 匹配
        self.assertEqual(ids.kind_of("prun_" + "a" * 32), "processing_run_id")
        self.assertEqual(ids.kind_of("pr_bazi_000101"), "proposition_id")

    def test_legacy_formats_verbatim(self):
        for kind, value in (
            ("source_id", "src_sanche_ed01"),
            ("source_span_id", "ss_sanche_ed01_p0001_s01"),
            ("knowledge_unit_id", "ku_qizheng_000001"),
            ("homograph_anchor_id", "hg_0001"),
        ):
            self.assertEqual(ids.validate(kind, value), value)
        # 三位页码非法（必须 4 位）
        with self.assertRaises(InvalidIdentifier):
            ids.validate("source_span_id", "ss_sanche_ed01_p001_s01")

    def test_error_has_code_ID_001(self):
        with self.assertRaises(InvalidIdentifier) as ctx:
            ids.validate("artifact_id", "nope")
        self.assertIsInstance(ctx.exception, LedgerError)
        self.assertEqual(ctx.exception.code, "ID_001")

    # ------------------------------------------------ 偏移形态（第 78、100、102 条）

    def test_offset_form_source_span_id_accepted(self):
        """偏移形态 ss_<work>_ed<NN>_o<NNNNNNN> 正例（7 位零填充）。"""
        for value in (
            "ss_qianyuan_ed01_o0000018",
            "ss_sanche_ed01_o0000000",
            "ss_worka_ed02_o1234567",
        ):
            self.assertEqual(ids.validate("source_span_id", value), value)

    def test_offset_form_semantic_span_id_accepted(self):
        """sem_ 只登记偏移形态 sem_<work>_ed<NN>_o<NNNNNNN>（第 80 条 + 第 102 条 Q2）。"""
        for value in ("sem_qianyuan_ed01_o0000018", "sem_worka_ed02_o0000000"):
            self.assertEqual(ids.validate("semantic_span_id", value), value)

    def test_offset_form_rejects_wrong_width_offset(self):
        """反例：6 位与 8 位偏移均非法（必须恰 7 位零填充）。"""
        for value in ("ss_qianyuan_ed01_o000123", "ss_qianyuan_ed01_o00000123"):
            with self.assertRaises(InvalidIdentifier) as ctx:
                ids.validate("source_span_id", value)
            self.assertEqual(ctx.exception.code, "ID_001")

    def test_span_id_rejects_mixed_page_and_offset_segments(self):
        """反例：同一 ID 不得同时带页码段与偏移段（两种形态互斥）。"""
        for value in (
            "ss_qianyuan_ed01_p0001_s01_o0000018",
            "ss_qianyuan_ed01_o0000018_p0001_s01",
        ):
            with self.assertRaises(InvalidIdentifier):
                ids.validate("source_span_id", value)

    def test_span_id_work_segment_rejects_underscore(self):
        """反例：第 102 条 Q1——``<work>`` 禁止下划线，与 source_id 同口径。"""
        for kind, value in (
            ("source_span_id", "ss_work_a_ed01_o0000000"),
            ("source_span_id", "ss_work_a_ed01_p0001_s01"),
            ("semantic_span_id", "sem_work_a_ed01_o0000000"),
        ):
            with self.assertRaises(InvalidIdentifier):
                ids.validate(kind, value)

    def test_semantic_span_id_requires_edition_and_rejects_page_form(self):
        """反例：sem_ 缺 ``ed`` 段非法；页码形态本次未登记（第 102 条 Q2）。"""
        for value in (
            "sem_qianyuan_o0000018",
            "sem_qianyuan_ed01_p0001_s003",
            "sem_qianyuan_ed01_p0001_s01",
        ):
            with self.assertRaises(InvalidIdentifier):
                ids.validate("semantic_span_id", value)

    def test_kind_of_recognizes_span_id_families(self):
        """kind_of 按前缀最长匹配识别两个片段 ID 家族。"""
        self.assertEqual(ids.kind_of("ss_qianyuan_ed01_o0000018"), "source_span_id")
        self.assertEqual(ids.kind_of("ss_qianyuan_ed01_p0001_s01"), "source_span_id")
        self.assertEqual(ids.kind_of("sem_qianyuan_ed01_o0000018"), "semantic_span_id")

    def test_work_and_edition_segments_have_single_authority(self):
        """第 102 条 Q1：``<work>``/``<edition>`` 段的判定只由 ids 提供。"""
        self.assertTrue(ids.is_work("worka"))
        self.assertFalse(ids.is_work("work_a"))
        self.assertFalse(ids.is_work("Worka"))
        self.assertTrue(ids.is_edition("ed01"))
        self.assertFalse(ids.is_edition("ed1"))

    def test_offset_anchors_uses_ledger_id_patterns(self):
        """第 85、102 条：offset_anchors 不再自有正则，校验结果与 ids 一致。"""
        from pipeline.corpus_compiler import offset_anchors

        for name in ("_RE_WORK", "_RE_EDITION", "_RE_SOURCE_SPAN_ID", "_RE_SEMANTIC_SPAN_ID"):
            self.assertFalse(
                hasattr(offset_anchors, name),
                "offset_anchors 仍自带正则对象 %s，应改为从 pipeline.ledger.ids 导入" % name,
            )
        # 正例与反例逐一对齐 ids 的判定
        for work, accepted in (("worka", True), ("work_a", False)):
            if accepted:
                span_id = offset_anchors.format_source_span_id(work, "ed02", 7)
                self.assertEqual(ids.validate("source_span_id", span_id), span_id)
            else:
                with self.assertRaises(ValueError):
                    offset_anchors.format_source_span_id(work, "ed02", 7)

    def test_no_private_span_id_patterns_outside_ledger_ids(self):
        """第 85、102 条：corpus_compiler 非测试代码不得再自有 ss_/sem_ 形态正则字面量。

        守护范围：偏移形态 ``ss_…_o<NNNNNNN>``（第 78 条）与 ``sem_`` 家族（第 80 条）。
        页码形态 ``ss_…_p<NNNN>_s<NN>`` 的 parts 正则不在本条守护范围——它不在第 102 条
        授权的改动文件清单内，且字符集与 ids 页码形态逐字相同，未构成分叉（已在 8.1 回报中列出）。
        """
        package_dir = REPO_ROOT / "pipeline" / "corpus_compiler"
        offenders = []
        for path in sorted(package_dir.rglob("*.py")):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)):
                    continue
                if func.value.id != "re" or func.attr not in ("compile", "match", "fullmatch", "search"):
                    continue
                if not node.args or not isinstance(node.args[0], ast.Constant):
                    continue
                pattern = node.args[0].value
                if not isinstance(pattern, str):
                    continue
                if "sem_" in pattern or ("ss_" in pattern and "_o" in pattern):
                    offenders.append("%s:%d" % (path.relative_to(REPO_ROOT), node.lineno))
        self.assertEqual(
            offenders,
            [],
            "以下位置仍自有 ss_/sem_ 形态正则字面量，应改为从 pipeline.ledger.ids 导入: %r" % offenders,
        )


if __name__ == "__main__":
    unittest.main()
