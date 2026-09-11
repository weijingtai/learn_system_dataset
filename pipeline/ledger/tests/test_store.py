"""ACT impl-01/02：SQLite Metadata Ledger 与写入者锁（规格 §17）的单元测试。

先写本文件，运行 `python -m unittest discover -s pipeline/ledger/tests -t .`
因 `pipeline.ledger.store` / `pipeline.ledger.lock` 尚不存在而全红。
所有用例只使用 ``tempfile`` 目录，绝不写 ``var/``。
"""

import multiprocessing
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pipeline.ledger import ids
from pipeline.ledger.errors import IllegalTransition, WriterLocked
from pipeline.ledger.lock import WriterLock
from pipeline.ledger.store import MetadataStore

NOW = "2026-09-11T00:00:00.000000Z"

# DDL 逐字枚举的表名（不含 SQLite 内部 sqlite_sequence；见交付报告对 15/16 计数差异的说明）
EXPECTED_TABLES = {
    "schema_meta",
    "artifacts",
    "artifact_revisions",
    "revision_status_events",
    "stage_packages",
    "processing_runs",
    "step_runs",
    "step_run_events",
    "frozen_inputs",
    "transformations",
    "transformation_inputs",
    "transformation_outputs",
    "transformation_human_events",
    "human_events",
    "stage_checkpoints",
    "audit_log",
}


def _try_acquire(root, queue):
    """子进程工作函数：尝试取写锁并把结果放回队列（spawn 需要顶层函数）。"""
    from pipeline.ledger.errors import WriterLocked
    from pipeline.ledger.lock import WriterLock

    try:
        WriterLock(root).acquire()
    except WriterLocked:
        queue.put("locked")
    else:
        queue.put("acquired")


def _insert_artifact_and_revision(store, status="sealed"):
    """插入一条 Artifact 与其 Revision，返回 (artifact_id, artifact_revision_id)。"""
    artifact_id = ids.new_id("artifact_id")
    revision_id = ids.new_id("artifact_revision_id")
    store.insert_artifact(artifact_id, "test", NOW, "local_owner")
    store.insert_revision(
        revision_id,
        artifact_id,
        status,
        0,
        "0" * 64,
        1,
        "objects/00/" + "0" * 64,
        "test_module",
        "1.0",
        "internal",
        NOW,
        "local_owner",
    )
    return artifact_id, revision_id


class TestMetadataStore(unittest.TestCase):
    """覆盖 §17：DDL 建表、WAL/FK、乐观锁、事务回滚、只读打开。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.db = self.root / "ledger.sqlite"

    def _open(self):
        store = MetadataStore(self.db)
        store.open()
        store.migrate()
        self.addCleanup(store.close)
        return store

    def test_migrate_creates_all_tables(self):
        store = self._open()
        rows = store.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {row[0] for row in rows} - {"sqlite_sequence"}
        self.assertEqual(names, EXPECTED_TABLES)

    def test_wal_and_foreign_keys_enabled(self):
        store = self._open()
        self.assertEqual(
            store.conn.execute("PRAGMA journal_mode").fetchone()[0], "wal"
        )
        self.assertEqual(
            store.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1
        )

    def test_update_revision_status_rejects_stale_from_status(self):
        store = self._open()
        _, revision_id = _insert_artifact_and_revision(store, status="sealed")
        with self.assertRaises(IllegalTransition):
            store.update_revision_status(
                revision_id, "draft", "sealed", "stale", "local_owner"
            )

    def test_step_run_optimistic_lock(self):
        store = self._open()
        processing_run_id = ids.new_id("processing_run_id")
        step_run_id = ids.new_id("step_run_id")
        with store.transaction():
            store.insert_processing_run(
                processing_run_id, "edition_run", "art_part", "qizheng", NOW, "local_owner"
            )
            store.insert_step_run(
                step_run_id,
                processing_run_id,
                "m1",
                "running",
                0,
                "{}",
                NOW,
                NOW,
                "local_owner",
            )
        # 第一次更新成功：running v0 → awaiting_human v1
        with store.transaction():
            store.update_step_run_status(step_run_id, "running", "awaiting_human", 0)
        # 第二次以同一 expected_status_version=0 更新，乐观锁拒绝
        with self.assertRaises(IllegalTransition):
            store.update_step_run_status(step_run_id, "running", "failed", 0)

    def test_transaction_rolls_back_on_exception(self):
        store = self._open()
        with self.assertRaises(RuntimeError):
            with store.transaction():
                store.insert_artifact(
                    ids.new_id("artifact_id"), "test", NOW, "local_owner"
                )
                raise RuntimeError("boom")
        count = store.conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
        self.assertEqual(count, 0)

    def test_readonly_open_cannot_write(self):
        store = self._open()
        store.close()
        readonly = MetadataStore.open_readonly(self.db)
        self.addCleanup(readonly.close)
        with self.assertRaises(sqlite3.OperationalError):
            readonly.conn.execute(
                "INSERT INTO schema_meta(key, value) VALUES ('x', 'y')"
            )

    def test_writer_lock_exclusive(self):
        lock = WriterLock(self.root)
        lock.acquire()
        self.addCleanup(lock.release)
        ctx = multiprocessing.get_context("spawn")
        queue = ctx.Queue()
        proc = ctx.Process(target=_try_acquire, args=(str(self.root), queue))
        proc.start()
        proc.join(timeout=60)
        self.assertEqual(proc.exitcode, 0)
        self.assertEqual(queue.get(timeout=10), "locked")

    def test_gitignore_has_var(self):
        repo_root = Path(__file__).resolve().parents[3]
        lines = (repo_root / ".gitignore").read_text(encoding="utf-8").split("\n")
        self.assertEqual(lines.count("var/"), 1)


if __name__ == "__main__":
    unittest.main()
