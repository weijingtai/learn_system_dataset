"""TODO.md T03c：LedgerPort 为 M1/M2/M4/M6/M7 新增的只读查询。

这 5 个包原先在模块里自己写 SQL（``.store.conn.execute``）、直接读对象存储（``.objects.get``），
共 111 处绕过端口。这里验证替代它们的端口方法：结果与原 SQL 一致、服务端与只读端同名同义、
进了端口闭集且 socket 客户端也有。
"""

import unittest

from pipeline.ledger import ids
from pipeline.ledger.service import LedgerReader
from pipeline.ledger.tests.test_service import ServiceTestBase

# 本任务新增的端口方法（随各包清零逐步追加）
T03C_METHODS = (
    "latest_processing_run",
)


class LatestProcessingRunTest(ServiceTestBase):
    def test_returns_newest_run_of_kind_for_edition_part(self):
        edition_part_id = ids.new_id("artifact_id")
        self.assertIsNone(self.service.latest_processing_run(edition_part_id, "edition_run"))
        first = self.service.create_processing_run("edition_run", edition_part_id, "qizheng")
        second = self.service.create_processing_run("edition_run", edition_part_id, "qizheng")
        self.service.create_processing_run("release_run", edition_part_id, "qizheng")
        self.service.create_processing_run("edition_run", ids.new_id("artifact_id"), "qizheng")
        self.assertNotEqual(first, second)
        self.assertEqual(self.service.latest_processing_run(edition_part_id, "edition_run"), second)
        reader = LedgerReader(self.root)
        self.addCleanup(reader.close)
        self.assertEqual(reader.latest_processing_run(edition_part_id, "edition_run"), second)


class PortMethodSetTest(unittest.TestCase):
    def test_new_queries_are_in_the_port_closed_set_and_on_all_backends(self):
        from pipeline.contract_registry.ports import LEDGER_PORT_METHODS
        from pipeline.ledger.client import LedgerClient
        from pipeline.ledger.service import LedgerService

        for name in T03C_METHODS:
            with self.subTest(name=name):
                self.assertIn(name, LEDGER_PORT_METHODS)
                self.assertTrue(callable(getattr(LedgerService, name, None)))
                self.assertTrue(callable(getattr(LedgerReader, name, None)))
                self.assertTrue(callable(getattr(LedgerClient, name, None)))


if __name__ == "__main__":
    unittest.main()
