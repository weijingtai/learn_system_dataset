"""EditionRun 运行输入校验（TODO T04A 第 2 项：M4 技法画像走运行输入）。

``technique_profile``（``{technique_id, canon_dir}``）是电子文本路线必备的运行输入：
M4 薄适配据此登记运行级 ``technique_profile`` 修订。本模块只断言调度器侧的形状校验，
不读盘、不 import 任何加工 Module。
"""

import copy
import sqlite3
import unittest

from pipeline.ledger import ids
from pipeline.orchestrator.edition_run import start_edition_run
from pipeline.orchestrator.errors import OrchestratorRefused
from pipeline.orchestrator.run_inputs import validate_run_inputs
from pipeline.orchestrator.tests.scaffold import LedgerTestCase

# 形状合法的运行输入（校验只看形状，不读盘，故路径无需存在）
VALID = {
    "route": "text",
    "source_dir": "host/source",
    "source_info": {"pages": [{"page": 1}]},
    "technique_profile": {"technique_id": "qizheng", "canon_dir": "host/canon"},
}


def _with(mutate):
    run_inputs = copy.deepcopy(VALID)
    mutate(run_inputs)
    return run_inputs


class TestRunInputsTechniqueProfile(unittest.TestCase):
    """``technique_profile`` 必备、闭集两键、非空字符串、技法号与 EditionRun 一致。"""

    def test_valid_inputs_pass_unchanged(self):
        run_inputs = copy.deepcopy(VALID)
        self.assertIs(validate_run_inputs(run_inputs, technique_id="qizheng"), run_inputs)
        self.assertEqual(run_inputs, VALID)

    def test_technique_profile_required(self):
        run_inputs = _with(lambda doc: doc.pop("technique_profile"))
        with self.assertRaises(OrchestratorRefused) as ctx:
            validate_run_inputs(run_inputs, technique_id="qizheng")
        self.assertIn("technique_profile", str(ctx.exception))

    def test_technique_profile_shape_is_closed(self):
        cases = {
            "not_dict": lambda doc: doc.__setitem__("technique_profile", "qizheng"),
            "missing_technique_id": lambda doc: doc["technique_profile"].pop("technique_id"),
            "missing_canon_dir": lambda doc: doc["technique_profile"].pop("canon_dir"),
            "empty_technique_id": lambda doc: doc["technique_profile"].__setitem__("technique_id", ""),
            "empty_canon_dir": lambda doc: doc["technique_profile"].__setitem__("canon_dir", ""),
            "non_str_canon_dir": lambda doc: doc["technique_profile"].__setitem__("canon_dir", ["a"]),
            "extra_key": lambda doc: doc["technique_profile"].__setitem__("profile_revision_id", "x"),
        }
        for label, mutate in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(OrchestratorRefused) as ctx:
                    validate_run_inputs(_with(mutate), technique_id="qizheng")
                self.assertIn("technique_profile", str(ctx.exception))

    def test_technique_id_must_match_edition_run(self):
        with self.assertRaises(OrchestratorRefused) as ctx:
            validate_run_inputs(copy.deepcopy(VALID), technique_id="other")
        self.assertIn("technique_profile.technique_id", str(ctx.exception))


class TestStartRefusesBadTechniqueProfile(LedgerTestCase):
    """``start_edition_run`` 在建 ProcessingRun 之前拒收，零写入。"""

    def _counts(self):
        connection = sqlite3.connect(
            "file:%s?mode=ro" % (self.root / "ledger.sqlite"), uri=True
        )
        try:
            return tuple(
                connection.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
                for table in ("processing_runs", "artifact_revisions", "audit_log")
            )
        finally:
            connection.close()

    def test_start_refuses_mismatched_technique_before_write(self):
        before = self._counts()
        with self.assertRaises(OrchestratorRefused):
            start_edition_run(
                self.adapter,
                edition_part_id=ids.new_id("artifact_id"),
                technique_id="other",
                run_inputs=copy.deepcopy(VALID),
            )
        self.assertEqual(before, self._counts())

    def test_start_refuses_missing_technique_profile_before_write(self):
        before = self._counts()
        with self.assertRaises(OrchestratorRefused):
            start_edition_run(
                self.adapter,
                edition_part_id=ids.new_id("artifact_id"),
                technique_id="qizheng",
                run_inputs=_with(lambda doc: doc.pop("technique_profile")),
            )
        self.assertEqual(before, self._counts())


if __name__ == "__main__":
    unittest.main()
