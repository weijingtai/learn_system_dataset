"""ACT impl-04/06：run_m8 失败路径与检查名闭集的测试。

脚手架同 test_step（``_ledger_helpers.prepare_m8_ready``）。
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline.dataset_compiler import packs
from pipeline.dataset_compiler.errors import DatasetRefused
from pipeline.dataset_compiler.step import run_m8
from pipeline.dataset_compiler.tests._ledger_helpers import (
    FIXTURE,
    assets_available,
    prepare_m8_ready,
    table_counts,
)
from pipeline.ledger.fixture_ingest import ingest
from pipeline.ledger.service import LedgerService

_SUBPACK_TYPES = (
    "source_asset_pack",
    "evidence_map_pack",
    "release_manifest",
    "publication_package",
)


class FailureSealingBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m8-fail-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.service = LedgerService(Path(self._tmp) / "ledger")
        self.addCleanup(self.service.close)

    def ready(self):
        prepared = prepare_m8_ready(self.service)
        self.edition_part_id = prepared["edition_part_id"]

    def _artifact_count(self, artifact_type):
        return self.service.store.conn.execute(
            "SELECT COUNT(*) FROM artifacts WHERE artifact_type=?",
            (artifact_type,),
        ).fetchone()[0]

    def _m8_step_run_count(self):
        return self.service.store.conn.execute(
            "SELECT COUNT(*) FROM step_runs WHERE stage='m8'"
        ).fetchone()[0]


class AdmissionFailureTests(FailureSealingBase):
    """准入失败在 begin 之后封存，不留任何子包修订或第二个 m8 StepRun。"""

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_dev_search_sealed_admission_failure(self):
        self.ready()
        result = run_m8(self.service, self.edition_part_id, consumption_level="DEV_SEARCH")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_check"], "admission")
        self.assertEqual(result["reason"], "unmet: dev_search_gates_not_implemented")
        self.assertEqual(
            self.service.get_step_run(result["step_run_id"])["status"], "failed"
        )
        for artifact_type in _SUBPACK_TYPES:
            self.assertEqual(self._artifact_count(artifact_type), 0)
        self.assertEqual(self._m8_step_run_count(), 1)

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_public_release_unmet_six_codes(self):
        self.ready()
        result = run_m8(self.service, self.edition_part_id, consumption_level="PUBLIC_RELEASE")
        self.assertEqual(result["failed_check"], "admission")
        for code in (
            "content_not_expert_verified",
            "draft_schema",
            "min_app_version_unset",
            "public_release_gates_not_implemented",
            "rights_unconfirmed",
            "source_release_dev",
        ):
            self.assertIn(code, result["reason"])

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_public_release_with_min_app_version_still_fails_without_that_code(self):
        self.ready()
        result = run_m8(
            self.service,
            self.edition_part_id,
            consumption_level="PUBLIC_RELEASE",
            min_app_version="1.0.0",
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_check"], "admission")
        self.assertNotIn("min_app_version_unset", result["reason"])


class CheckNameTests(FailureSealingBase):
    """检查名闭集：compile / internal / 预处理拒绝。"""

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_compile_failure_check_name(self):
        self.ready()
        original = packs.build_evidence_map_pack

        def boom(*args, **kwargs):
            raise RuntimeError("模拟子包编译失败")

        packs.build_evidence_map_pack = boom
        try:
            result = run_m8(
                self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO"
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failed_check"], "compile")
            failure = self.service.get_revision(result["failure_revision_id"])
            self.assertEqual(failure["status"], "sealed")
        finally:
            packs.build_evidence_map_pack = original

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_internal_failure_check_name(self):
        self.ready()
        original = LedgerService.record_transformation

        def boom(self, *args, **kwargs):
            raise RuntimeError("模拟 Ledger 写失败")

        LedgerService.record_transformation = boom
        try:
            result = run_m8(
                self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO"
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failed_check"], "internal")
            self.assertEqual(
                self.service.get_step_run(result["step_run_id"])["status"], "failed"
            )
            failure = self.service.get_revision(result["failure_revision_id"])
            self.assertEqual(failure["status"], "sealed")
        finally:
            LedgerService.record_transformation = original

    def test_pre_begin_refusal_type_preserved(self):
        summary = ingest(FIXTURE, self.service, stages=("m1", "m2"))
        before = table_counts(self.service)
        with self.assertRaises(DatasetRefused) as ctx:
            run_m8(
                self.service,
                summary["edition_part_id"],
                consumption_level="INTERNAL_DEMO",
            )
        self.assertFalse(str(ctx.exception).startswith("M8 编译异常"))
        self.assertEqual(table_counts(self.service), before)


if __name__ == "__main__":
    unittest.main()
