"""TODO.md T03：LedgerPort 新增的只读元数据查询。

M3 / M5 / M8 原先在模块里自己写 SQL（``.store.conn.execute``）、直接读对象存储（``.objects.get``），
共 63 处绕过端口。这里验证替代它们的端口方法：结果正确、服务端与只读端同名同义。
"""

import unittest

from pipeline.ledger import ids
from pipeline.ledger.service import LedgerReader
from pipeline.ledger.tests.test_service import ServiceTestBase


class ReadQueriesTest(ServiceTestBase):
    def setUp(self):
        super().setUp()
        self.pr = self.new_processing_run()
        self.step, self.config = self.begin(self.pr, stage="m1", inputs=())
        self.manifest_artifact, self.manifest_rev = self.put_sealed(self.step, "source_manifest", b"m")
        _, self.page_rev = self.put_sealed(self.step, "ocr_page", b"p")

    def test_describe_revision_reports_type_and_ownership(self):
        info = self.service.describe_revision(self.manifest_rev)
        self.assertEqual(info["artifact_type"], "source_manifest")
        self.assertEqual(info["artifact_id"], self.manifest_artifact)
        self.assertEqual(info["status"], "sealed")
        self.assertEqual(info["step_run_id"], self.step)
        self.assertIsNone(info["stage_package_id"])
        self.assertIsNone(self.service.describe_revision(ids.new_id("artifact_revision_id")))

    def test_list_step_run_revisions_filters_by_type_and_status(self):
        all_revs = [row["artifact_revision_id"] for row in self.service.list_step_run_revisions(self.step)]
        self.assertIn(self.manifest_rev, all_revs)
        self.assertIn(self.page_rev, all_revs)
        pages = self.service.list_step_run_revisions(self.step, artifact_type="ocr_page")
        self.assertEqual([row["artifact_revision_id"] for row in pages], [self.page_rev])
        self.assertEqual(self.service.list_step_run_revisions(self.step, status="draft"), [])

    def test_list_artifact_revisions(self):
        rows = self.service.list_artifact_revisions(self.manifest_artifact)
        self.assertEqual([row["artifact_revision_id"] for row in rows], [self.manifest_rev])

    def test_frozen_inputs_and_processing_run(self):
        step2, _ = self.begin(self.pr, stage="m2", inputs=[self.manifest_rev])
        self.assertEqual(self.service.list_frozen_inputs(step2), [self.manifest_rev])
        run = self.service.get_processing_run(self.pr)
        self.assertEqual(run["processing_run_id"], self.pr)
        self.assertIn("edition_part_id", run)

    def test_list_step_runs_filters_by_stage(self):
        step2, _ = self.begin(self.pr, stage="m2", inputs=[self.manifest_rev])
        edition_part_id = self.service.get_processing_run(self.pr)["edition_part_id"]
        all_ids = [row["step_run_id"] for row in self.service.list_step_runs(edition_part_id)]
        self.assertEqual(all_ids, [self.step, step2])
        m2 = self.service.list_step_runs(edition_part_id, stage="m2")
        self.assertEqual([row["step_run_id"] for row in m2], [step2])

    def test_count_artifacts(self):
        self.assertEqual(self.service.count_artifacts("ocr_page"), 1)
        self.assertEqual(self.service.count_artifacts("no_such_type"), 0)

    def test_read_object_on_service(self):
        info = self.service.describe_revision(self.page_rev)
        self.assertEqual(self.service.read_object(info["sha256"]), b"p")

    def test_reader_exposes_same_methods(self):
        reader = LedgerReader(self.root)
        self.addCleanup(reader.close)
        self.assertEqual(
            reader.describe_revision(self.manifest_rev), self.service.describe_revision(self.manifest_rev)
        )
        self.assertEqual(reader.list_frozen_inputs(self.step), self.service.list_frozen_inputs(self.step))
        self.assertEqual(reader.count_artifacts("ocr_page"), 1)


class PortMethodSetTest(unittest.TestCase):
    def test_new_queries_are_in_the_port_closed_set_and_on_both_backends(self):
        from pipeline.contract_registry.ports import LEDGER_PORT_METHODS
        from pipeline.ledger.client import LedgerClient
        from pipeline.ledger.service import LedgerService

        for name in (
            "describe_revision", "list_step_run_revisions", "list_artifact_revisions",
            "list_frozen_inputs", "get_processing_run", "list_step_runs",
            "list_stage_packages", "count_artifacts", "read_object",
        ):
            with self.subTest(name=name):
                self.assertIn(name, LEDGER_PORT_METHODS)
                self.assertTrue(callable(getattr(LedgerService, name, None)))
                self.assertTrue(callable(getattr(LedgerClient, name, None)))


if __name__ == "__main__":
    unittest.main()
