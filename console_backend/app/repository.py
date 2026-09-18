"""Sqlite-backed repository for PipelineRun entities."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import List, Optional

from proto.console.v1 import pipeline_pb2


class SqlitePipelineRepository:
    """SQLite 仓储层，负责 PipelineRun 对象的持久化与还原。"""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            with self._conn:
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS pipeline_runs (
                        run_id TEXT PRIMARY KEY,
                        work TEXT,
                        edition TEXT,
                        edition_part_id TEXT,
                        overall_status INTEGER,
                        current_stage INTEGER,
                        created_at TEXT,
                        payload BLOB
                    )
                    """
                )

    def save_run(self, run: pipeline_pb2.PipelineRun) -> None:
        """保存或更新 PipelineRun 记录。"""
        if not run.run_id:
            raise ValueError("PipelineRun must have a valid run_id")

        payload = run.SerializeToString()
        with self._lock:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO pipeline_runs (
                        run_id, work, edition, edition_part_id,
                        overall_status, current_stage, created_at, payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET
                        work = excluded.work,
                        edition = excluded.edition,
                        edition_part_id = excluded.edition_part_id,
                        overall_status = excluded.overall_status,
                        current_stage = excluded.current_stage,
                        created_at = excluded.created_at,
                        payload = excluded.payload
                    """,
                    (
                        run.run_id,
                        run.work,
                        run.edition,
                        run.edition_part_id,
                        int(run.overall_status),
                        int(run.current_stage),
                        run.created_at,
                        payload,
                    ),
                )

    def get_run(self, run_id: str) -> Optional[pipeline_pb2.PipelineRun]:
        """根据 run_id 获取 PipelineRun，若不存在返回 None。"""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT payload FROM pipeline_runs WHERE run_id = ?",
                (run_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            run = pipeline_pb2.PipelineRun()
            run.ParseFromString(row["payload"])
            return run

    def list_runs(self) -> List[pipeline_pb2.PipelineRun]:
        """列出所有 PipelineRun，默认按写入时间逆序排列。"""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT payload FROM pipeline_runs ORDER BY rowid DESC"
            )
            rows = cursor.fetchall()

            runs: List[pipeline_pb2.PipelineRun] = []
            for row in rows:
                run = pipeline_pb2.PipelineRun()
                run.ParseFromString(row["payload"])
                runs.append(run)
            return runs

    def close(self) -> None:
        """关闭 SQLite 连接。"""
        with self._lock:
            self._conn.close()
