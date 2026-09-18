"""Sqlite-backed repository for PipelineRun entities."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import List, Optional

from proto.console.v1 import pipeline_pb2, workbench_m1_m2_pb2, workbench_review_pb2


class SqlitePipelineRepository:
    """SQLite 仓储层，负责 PipelineRun 与工作台各阶段实体对象的持久化与还原。"""

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
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS m1_page_scans (
                        run_id TEXT,
                        page_index INTEGER,
                        payload BLOB,
                        PRIMARY KEY (run_id, page_index)
                    )
                    """
                )
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS m2_sanitizations (
                        run_id TEXT PRIMARY KEY,
                        payload BLOB
                    )
                    """
                )
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS review_items (
                        run_id TEXT,
                        queue_item_id TEXT,
                        payload BLOB,
                        PRIMARY KEY (run_id, queue_item_id)
                    )
                    """
                )
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS review_decisions (
                        run_id TEXT,
                        queue_item_id TEXT,
                        payload BLOB,
                        PRIMARY KEY (run_id, queue_item_id)
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

    def save_m1_page_scan(self, run_id: str, scan: workbench_m1_m2_pb2.PageScan) -> None:
        """保存或更新 M1 PageScan 数据。"""
        payload = scan.SerializeToString()
        with self._lock:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO m1_page_scans (run_id, page_index, payload)
                    VALUES (?, ?, ?)
                    ON CONFLICT(run_id, page_index) DO UPDATE SET
                        payload = excluded.payload
                    """,
                    (run_id, scan.page_index, payload),
                )

    def get_m1_page_scan(self, run_id: str, page_index: int = 1) -> Optional[workbench_m1_m2_pb2.PageScan]:
        """获取指定 run_id 和 page_index 的 M1 PageScan。"""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT payload FROM m1_page_scans WHERE run_id = ? AND page_index = ?",
                (run_id, page_index),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            scan = workbench_m1_m2_pb2.PageScan()
            scan.ParseFromString(row["payload"])
            return scan

    def save_m2_data(self, run_id: str, data: workbench_m1_m2_pb2.SanitizationWorkbenchData) -> None:
        """保存或更新 M2 SanitizationWorkbenchData 数据。"""
        payload = data.SerializeToString()
        with self._lock:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO m2_sanitizations (run_id, payload)
                    VALUES (?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET
                        payload = excluded.payload
                    """,
                    (run_id, payload),
                )

    def get_m2_data(self, run_id: str) -> Optional[workbench_m1_m2_pb2.SanitizationWorkbenchData]:
        """获取指定 run_id 的 M2 SanitizationWorkbenchData。"""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT payload FROM m2_sanitizations WHERE run_id = ?",
                (run_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            data = workbench_m1_m2_pb2.SanitizationWorkbenchData()
            data.ParseFromString(row["payload"])
            return data

    def save_review_items(self, run_id: str, items: List[workbench_review_pb2.ReviewQueueItem]) -> None:
        """保存 M3/M6 审核队列条目。"""
        with self._lock:
            with self._conn:
                for item in items:
                    self._conn.execute(
                        """
                        INSERT INTO review_items (run_id, queue_item_id, payload)
                        VALUES (?, ?, ?)
                        ON CONFLICT(run_id, queue_item_id) DO UPDATE SET
                            payload = excluded.payload
                        """,
                        (run_id, item.queue_item_id, item.SerializeToString()),
                    )

    def get_review_items(self, run_id: str) -> List[workbench_review_pb2.ReviewQueueItem]:
        """获取指定 run_id 的 M3/M6 审核队列。"""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT payload FROM review_items WHERE run_id = ? ORDER BY rowid ASC",
                (run_id,),
            )
            rows = cursor.fetchall()
            items: List[workbench_review_pb2.ReviewQueueItem] = []
            for row in rows:
                item = workbench_review_pb2.ReviewQueueItem()
                item.ParseFromString(row["payload"])
                items.append(item)
            return items

    def save_review_decisions(self, run_id: str, decisions: List[workbench_review_pb2.DecisionSubmission]) -> None:
        """记录审核决策。"""
        with self._lock:
            with self._conn:
                for d in decisions:
                    self._conn.execute(
                        """
                        INSERT INTO review_decisions (run_id, queue_item_id, payload)
                        VALUES (?, ?, ?)
                        ON CONFLICT(run_id, queue_item_id) DO UPDATE SET
                            payload = excluded.payload
                        """,
                        (run_id, d.queue_item_id, d.SerializeToString()),
                    )

    def get_review_decisions(self, run_id: str) -> List[workbench_review_pb2.DecisionSubmission]:
        """获取指定 run_id 已提交的所有审核决策。"""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT payload FROM review_decisions WHERE run_id = ? ORDER BY rowid ASC",
                (run_id,),
            )
            rows = cursor.fetchall()
            decisions: List[workbench_review_pb2.DecisionSubmission] = []
            for row in rows:
                d = workbench_review_pb2.DecisionSubmission()
                d.ParseFromString(row["payload"])
                decisions.append(d)
            return decisions

    def close(self) -> None:
        """关闭 SQLite 连接。"""
        with self._lock:
            self._conn.close()
