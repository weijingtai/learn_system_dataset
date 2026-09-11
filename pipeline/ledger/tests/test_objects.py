"""ACT impl-01/02：content-addressed Object Store（规格 §17）的单元测试。

先写本文件，运行 `python -m unittest discover -s pipeline/ledger/tests -t .`
因 `pipeline.ledger.objects` 尚不存在而全红。所有用例只使用 ``tempfile`` 目录。
"""

import hashlib
import tempfile
import unittest
from pathlib import Path

from pipeline.ledger.errors import MissingReference
from pipeline.ledger.objects import ObjectStore


class TestObjectStore(unittest.TestCase):
    """覆盖 §17：SHA-256 内容寻址、物理去重、tmp 清理、篡改可检出。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_put_returns_sha256_and_size_and_is_content_addressed(self):
        store = ObjectStore(self.root)
        data = b"hello ledger"
        digest, size = store.put(data)
        self.assertEqual(digest, hashlib.sha256(data).hexdigest())
        self.assertEqual(size, len(data))
        self.assertEqual(
            store.path_for(digest), self.root / "objects" / digest[:2] / digest
        )
        self.assertTrue(store.path_for(digest).is_file())
        self.assertTrue(store.exists(digest))
        self.assertEqual(store.get(digest), data)

    def test_put_dedups_identical_bytes(self):
        store = ObjectStore(self.root)
        data = b"same bytes"
        first = store.put(data)
        second = store.put(data)
        self.assertEqual(first, second)
        files = [p for p in (self.root / "objects").rglob("*") if p.is_file()]
        self.assertEqual(len(files), 1)

    def test_get_missing_raises_REF_001(self):
        store = ObjectStore(self.root)
        with self.assertRaises(MissingReference) as ctx:
            store.get("0" * 64)
        self.assertEqual(ctx.exception.code, "REF_001")

    def test_tmp_file_not_left_behind_on_success(self):
        store = ObjectStore(self.root)
        store.put(b"payload")
        tmp_dir = self.root / "objects" / "tmp"
        leftovers = (
            [p for p in tmp_dir.rglob("*") if p.is_file()] if tmp_dir.exists() else []
        )
        self.assertEqual(leftovers, [])

    def test_verify_detects_tampered_object(self):
        store = ObjectStore(self.root)
        digest, _ = store.put(b"original")
        self.assertTrue(store.verify(digest))
        path = store.path_for(digest)
        raw = bytearray(path.read_bytes())
        raw[0] ^= 0x01
        path.write_bytes(bytes(raw))
        self.assertFalse(store.verify(digest))


if __name__ == "__main__":
    unittest.main()
