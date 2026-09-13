"""ACT impl-08/01：LedgerPort 方法闭集与存储 Adapter 的单元测试（规格 §20.10）。

先写本文件，全红后再实现 `pipeline/contract_registry/ports.py`。
所有用例只使用 ``tempfile`` 目录，绝不写 ``var/`` 或 fixture。
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

from pipeline.contract_registry.ports import (  # noqa: E402
    LEDGER_PORT_METHODS,
    DirectLedgerAdapter,
    LedgerdClientAdapter,
    PortGuard,
    missing_port_methods,
    port_surface,
)
from pipeline.ledger import ids  # noqa: E402
from pipeline.ledger.client import LedgerClient  # noqa: E402
from pipeline.ledger.service import LedgerService  # noqa: E402

PYTHON = sys.executable


def _subprocess_env():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["LC_ALL"] = "en_US.UTF-8"
    return env


class PortsTestBase(unittest.TestCase):
    """公共脚手架：临时 Ledger 根与 ledgerd 生命周期。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._daemon = None

    def ledger_root(self, name="ledger"):
        return Path(self._tmp.name) / name

    def start_daemon(self, root, socket_path):
        proc = subprocess.Popen(
            [
                PYTHON,
                "-m",
                "pipeline.ledger.ledgerd",
                "--root",
                str(root),
                "--socket",
                str(socket_path),
            ],
            cwd=str(REPO_ROOT),
            env=_subprocess_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._daemon = proc
        self.addCleanup(self._terminate, proc)
        deadline = time.time() + 25
        while time.time() < deadline:
            if Path(socket_path).exists():
                return proc
            time.sleep(0.05)
        raise AssertionError("ledgerd 未创建 socket 文件")

    @staticmethod
    def _terminate(proc):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=20)
        for stream in (proc.stdout, proc.stderr):
            if stream is not None and not stream.closed:
                stream.close()


class TestLedgerPorts(PortsTestBase):
    """覆盖 BDD §2：闭集、直连/ledgerd Adapter 与 PortGuard。"""

    def test_port_methods_subset_of_ledger_client_public_api(self):
        public = {name for name in dir(LedgerClient) if not name.startswith("_")}
        missing = set(LEDGER_PORT_METHODS) - public
        self.assertEqual(missing, set(), "LedgerClient 缺闭集方法: %s" % sorted(missing))

    def test_direct_adapter_surface_equals_closed_set(self):
        adapter = DirectLedgerAdapter(self.ledger_root())
        self.addCleanup(adapter.close)
        self.assertEqual(port_surface(adapter), sorted(LEDGER_PORT_METHODS))
        self.assertEqual(missing_port_methods(adapter), [])

    def test_direct_adapter_read_object_roundtrip(self):
        adapter = DirectLedgerAdapter(self.ledger_root())
        self.addCleanup(adapter.close)
        processing_run_id = adapter.create_processing_run(
            "edition_run", ids.new_id("artifact_id"), "qizheng"
        )
        data = json.dumps({"stage": "m1"}).encode("utf-8")
        _artifact_id, revision_id = adapter.put_run_artifact(
            processing_run_id,
            "configuration",
            data,
            producer_module="tests",
            producer_version="1.0",
        )
        sha256 = adapter.get_revision(revision_id)["sha256"]
        self.assertEqual(adapter.read_object(sha256), data)

    def test_direct_adapter_unwrap_returns_service(self):
        adapter = DirectLedgerAdapter(self.ledger_root())
        self.addCleanup(adapter.close)
        self.assertIsInstance(adapter.unwrap(), LedgerService)

    def test_ledgerd_adapter_smoke(self):
        root = self.ledger_root()
        socket_path = root / "ledger.sock"
        self.start_daemon(root, socket_path)
        adapter = LedgerdClientAdapter(socket_path)
        self.addCleanup(adapter.close)

        self.assertEqual(port_surface(adapter), sorted(LEDGER_PORT_METHODS))
        self.assertEqual(missing_port_methods(adapter), [])

        processing_run_id = adapter.create_processing_run(
            "edition_run", ids.new_id("artifact_id"), "qizheng"
        )
        data = json.dumps({"stage": "m1"}).encode("utf-8")
        _artifact_id, revision_id = adapter.put_run_artifact(
            processing_run_id,
            "configuration",
            data,
            producer_module="tests",
            producer_version="1.0",
        )
        sha256 = adapter.get_revision(revision_id)["sha256"]
        self.assertEqual(adapter.read_object(sha256), data)

        with self.assertRaises(NotImplementedError):
            adapter.unwrap()

    def test_port_guard_blocks_store_objects_and_unknown(self):
        adapter = DirectLedgerAdapter(self.ledger_root())
        self.addCleanup(adapter.close)
        guard = PortGuard(adapter)
        for name in ("store", "objects", "conn", "definitely_not_a_method"):
            with self.assertRaises(AttributeError):
                getattr(guard, name)
        self.assertTrue(callable(guard.get_revision))
        self.assertIs(guard.unwrap(), adapter.unwrap())


if __name__ == "__main__":
    unittest.main()
