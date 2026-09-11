"""ACT impl-01/04：本地进程 ``ledgerd``、``LedgerClient`` 与 CLI（规格 §17）的单元测试。

先写本文件，运行 `.venv/bin/python -m unittest discover -s pipeline/ledger/tests -t .`
因 `pipeline.ledger.ledgerd` / `client` / `cli` 尚不存在而全红。
所有用例只使用 ``tempfile`` 目录，绝不写 ``var/`` 或 fixture。
"""

import base64
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from pipeline.ledger import ids
from pipeline.ledger.client import LedgerClient
from pipeline.ledger.errors import InvalidIdentifier, LedgerError, WriterLocked
from pipeline.ledger.lock import WriterLock
from pipeline.ledger.objects import ObjectStore
from pipeline.ledger.store import MetadataStore, utcnow

REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON = sys.executable


def _subprocess_env():
    """子进程环境：仓库根上 PYTHONPATH，保证 ``-m pipeline.ledger.*`` 可导入。"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["LC_ALL"] = "en_US.UTF-8"
    return env


def _seed_configuration(root, processing_run_id, stage="m1"):
    """低层播种一个已 sealed 的配置修订（内容 JSON 含 ``stage``）。"""
    store = MetadataStore(Path(root) / "ledger.sqlite")
    store.open()
    store.migrate()
    try:
        objects = ObjectStore(root)
        artifact_id = ids.new_id("artifact_id")
        revision_id = ids.new_id("artifact_revision_id")
        data = json.dumps(
            {"stage": stage, "tool": "tests", "tool_version": "1.0"}
        ).encode("utf-8")
        sha256, size = objects.put(data)
        now = utcnow()
        with store.transaction():
            store.insert_artifact(artifact_id, "configuration", now, "local_owner")
            store.insert_revision(
                revision_id,
                artifact_id,
                "sealed",
                1,
                sha256,
                size,
                "objects/%s/%s" % (sha256[:2], sha256),
                "tests",
                "1.0",
                "internal",
                now,
                "local_owner",
                processing_run_id=processing_run_id,
                sealed_at=now,
            )
    finally:
        store.close()
    return revision_id


def _prepare_run(root):
    """建库并播种一个 ProcessingRun + 一个 sealed 配置修订，返回 (prun, config)。"""
    store = MetadataStore(Path(root) / "ledger.sqlite")
    store.open()
    store.migrate()
    processing_run_id = ids.new_id("processing_run_id")
    try:
        with store.transaction():
            store.insert_processing_run(
                processing_run_id,
                "edition_run",
                ids.new_id("artifact_id"),
                "qizheng",
                utcnow(),
                "local_owner",
            )
    finally:
        store.close()
    return processing_run_id, _seed_configuration(root, processing_run_id, "m1")


def _step_request(processing_run_id, step_run_id, configuration_revision_id):
    return {
        "schema_version": "1.0.0",
        "processing_run_id": processing_run_id,
        "step_run_id": step_run_id,
        "input_artifact_ids": [],
        "technique_profile_id": "qizheng",
        "configuration_artifact_id": configuration_revision_id,
    }


class DaemonTestBase(unittest.TestCase):
    """公共脚手架：临时 Ledger 根、进程生命周期与 socket 等待。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "ledger"
        self.root.mkdir(parents=True, exist_ok=True)
        self.socket_path = self.root / "ledger.sock"
        self.client = None

    def close_client(self):
        if self.client is not None:
            self.client.close()
            self.client = None

    def start_daemon(self, root=None, socket_path=None):
        """以子进程启动 ``ledgerd``，返回 Popen（退出清理由 addCleanup 保证）。"""
        proc = subprocess.Popen(
            [
                PYTHON,
                "-m",
                "pipeline.ledger.ledgerd",
                "--root",
                str(root or self.root),
                "--socket",
                str(socket_path or self.socket_path),
            ],
            cwd=str(REPO_ROOT),
            env=_subprocess_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.addCleanup(self._terminate, proc)
        return proc

    def _terminate(self, proc):
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

    def wait_for_socket(self, path=None, timeout=25):
        """等待 socket 文件出现；出现返回 True。"""
        target = Path(path or self.socket_path)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if target.exists():
                return True
            time.sleep(0.05)
        return False

    def make_client(self, socket_path=None):
        self.client = LedgerClient(socket_path or self.socket_path)
        self.addCleanup(self.close_client)
        return self.client


class TestLedgerDaemon(DaemonTestBase):
    """覆盖 §17 进程模型：单写入者、UDS 协议、错误还原、SIGTERM 清理。"""

    def test_daemon_starts_and_client_roundtrip(self):
        self.start_daemon()
        self.assertTrue(self.wait_for_socket(), "ledgerd 未创建 socket 文件")
        client = self.make_client()

        processing_run_id = client.create_processing_run(
            "edition_run", ids.new_id("artifact_id"), "qizheng"
        )
        status = client.run_status(processing_run_id)
        self.assertEqual(status["processing_run_id"], processing_run_id)
        # 同一连接上连续多请求
        second = client.create_processing_run(
            "edition_run", ids.new_id("artifact_id"), "qizheng"
        )
        self.assertNotEqual(second, processing_run_id)
        self.assertEqual(
            client.run_status(second)["processing_run_id"], second
        )

    def test_second_daemon_exits_3_with_LEDGER_WRITER_LOCKED(self):
        self.start_daemon()
        self.assertTrue(self.wait_for_socket(), "ledgerd 未创建 socket 文件")
        second = subprocess.run(
            [
                PYTHON,
                "-m",
                "pipeline.ledger.ledgerd",
                "--root",
                str(self.root),
                "--socket",
                str(self.root / "second.sock"),
            ],
            cwd=str(REPO_ROOT),
            env=_subprocess_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        self.assertEqual(second.returncode, 3)
        self.assertIn(
            "LEDGER_WRITER_LOCKED %s" % self.root, second.stdout.decode("utf-8")
        )
        self.assertFalse((self.root / "second.sock").exists())

    def test_reader_cli_status_works_while_daemon_running(self):
        self.start_daemon()
        self.assertTrue(self.wait_for_socket(), "ledgerd 未创建 socket 文件")
        result = subprocess.run(
            [
                PYTHON,
                "-m",
                "pipeline.ledger.cli",
                "status",
                "--root",
                str(self.root),
            ],
            cwd=str(REPO_ROOT),
            env=_subprocess_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
        first_line = result.stdout.decode("utf-8").strip().split("\n")[0]
        payload = json.loads(first_line)
        self.assertEqual(payload["ledger_schema_version"], "1.0.0")
        self.assertIsInstance(payload["tables"], dict)

    def test_error_propagates_as_same_exception_class(self):
        self.start_daemon()
        self.assertTrue(self.wait_for_socket(), "ledgerd 未创建 socket 文件")
        client = self.make_client()
        with self.assertRaises(InvalidIdentifier) as ctx:
            client.create_processing_run(
                "edition_run",
                ids.new_id("artifact_id"),
                "qizheng",
                processing_run_id="pr_" + "a" * 32,
            )
        self.assertEqual(ctx.exception.code, "ID_001")
        self.assertIsInstance(ctx.exception, LedgerError)

    def test_bytes_roundtrip_via_base64(self):
        processing_run_id, configuration_revision_id = _prepare_run(self.root)
        self.start_daemon()
        self.assertTrue(self.wait_for_socket(), "ledgerd 未创建 socket 文件")
        client = self.make_client()

        step_run_id = client.begin_step_run(
            _step_request(
                processing_run_id, ids.new_id("step_run_id"), configuration_revision_id
            )
        )
        data = bytes(range(256)) * 4  # 1 KiB 确定性字节
        artifact_id, revision_id = client.put_artifact(
            step_run_id,
            "ocr_page",
            data,
            producer_module="tests",
            producer_version="1.0",
        )
        self.assertTrue(artifact_id.startswith("art_"))
        client.seal_revision(revision_id)
        sha256 = client.get_revision(revision_id)["sha256"]
        self.assertEqual(client.read_object(sha256), data)
        # base64 传输本身无损
        self.assertEqual(
            base64.b64decode(base64.b64encode(data)), data
        )

    def test_unknown_op_returns_error(self):
        self.start_daemon()
        self.assertTrue(self.wait_for_socket(), "ledgerd 未创建 socket 文件")
        # 裸协议：直接看 error.type
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(str(self.socket_path))
        try:
            sock.sendall(
                json.dumps({"op": "no_such_op", "args": {}}).encode("utf-8") + b"\n"
            )
            raw_reader = sock.makefile("rb")
            try:
                response = json.loads(raw_reader.readline().decode("utf-8"))
            finally:
                raw_reader.close()
        finally:
            # 服务端串行服务连接，必须先断开裸连接才能让客户端连上
            sock.close()
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["type"], "UnknownOperation")
        # 客户端把未知类型还原为 LedgerError
        client = self.make_client()
        with self.assertRaises(LedgerError):
            client._call("no_such_op", {})

    def test_sigterm_releases_lock_and_removes_socket(self):
        proc = self.start_daemon()
        self.assertTrue(self.wait_for_socket(), "ledgerd 未创建 socket 文件")
        proc.send_signal(signal.SIGTERM)
        self.assertEqual(proc.wait(timeout=30), 0)
        self.assertFalse(self.socket_path.exists(), "退出时未删除 socket 文件")
        lock = WriterLock(self.root)
        self.addCleanup(lock.release)
        lock.acquire()
        self.assertIsNotNone(lock._fd)


if __name__ == "__main__":
    unittest.main()
