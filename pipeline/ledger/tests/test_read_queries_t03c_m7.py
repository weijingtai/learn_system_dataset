"""TODO.md T03c M7：LedgerPort 为 M7 (assembly) 新增的只读查询。

验证替代原 SQL (inputs.py:48) 的端口方法：
- get_stage_package(stage_package_id=None, artifact_id=None)
"""

import unittest

from pipeline.ledger import ids
from pipeline.ledger.service import LedgerReader
from pipeline.ledger.tests.test_service import ServiceTestBase

T03C_M7_METHODS = (
    "get_stage_package",
)


class GetStagePackageTest(ServiceTestBase):
    def test_get_stage_package_by_id_and_by_artifact_id(self):
        sp_id = ids.new_id("stage_package_id", stage="m6")
        art_id = ids.new_id("artifact_id")
        from pipeline.ledger.store import utcnow
        self.service.store.insert_artifact(art_id, "stage_package", utcnow(), "actor_test")
        self.service.store.insert_stage_package(sp_id, art_id, "m6")

        # 直连服务查询
        by_id = self.service.get_stage_package(stage_package_id=sp_id)
        self.assertIsNotNone(by_id)
        self.assertEqual(by_id["stage_package_id"], sp_id)
        self.assertEqual(by_id["artifact_id"], art_id)
        self.assertEqual(by_id["stage"], "m6")

        by_art = self.service.get_stage_package(artifact_id=art_id)
        self.assertEqual(by_art, by_id)

        # 只读 reader 查询
        reader = LedgerReader(self.service.root)
        self.addCleanup(reader.close)
        self.assertEqual(reader.get_stage_package(stage_package_id=sp_id), by_id)
        self.assertEqual(reader.get_stage_package(artifact_id=art_id), by_id)

        # 不存在时返回 None
        missing_id = ids.new_id("stage_package_id", stage="m6")
        self.assertIsNone(self.service.get_stage_package(stage_package_id=missing_id))
        self.assertIsNone(reader.get_stage_package(stage_package_id=missing_id))

        # 未提供任何参数报错
        with self.assertRaises(ValueError):
            self.service.get_stage_package()


class PortMethodSetTest(unittest.TestCase):
    def test_new_queries_are_in_the_port_closed_set_and_on_all_backends(self):
        from pipeline.contract_registry.ports import LEDGER_PORT_METHODS
        from pipeline.ledger.client import LedgerClient
        from pipeline.ledger.service import LedgerService

        for name in T03C_M7_METHODS:
            with self.subTest(name=name):
                self.assertIn(name, LEDGER_PORT_METHODS)
                self.assertTrue(callable(getattr(LedgerService, name, None)))
                self.assertTrue(callable(getattr(LedgerReader, name, None)))
                self.assertTrue(callable(getattr(LedgerClient, name, None)))


if __name__ == "__main__":
    unittest.main()
