"""ACT impl-01/01：标识生成与校验（规格 §8.1）的单元测试。

先写本文件，运行 `python -m unittest discover -s pipeline/ledger/tests -t .`
因 `pipeline.ledger.ids` / `pipeline.ledger.errors` 尚不存在而全红。
"""

import unittest

from pipeline.ledger import ids
from pipeline.ledger.errors import InvalidIdentifier, LedgerError


class TestIds(unittest.TestCase):
    """覆盖 §8.1：19 个前缀家族、UUIDv4 发号、最长前缀判定与既有格式沿用。"""

    def test_new_id_matches_pattern_for_each_kind(self):
        # 19 个前缀家族逐字登记
        self.assertEqual(len(ids.PATTERNS), 19)
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


if __name__ == "__main__":
    unittest.main()
