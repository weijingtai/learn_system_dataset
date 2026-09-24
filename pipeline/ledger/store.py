"""SQLite Metadata Ledger（规格 §17）。

DDL 表名与列名逐字来自 ACT impl-01/02 contract；本模块只做低层读写，
不做业务校验（业务校验由 ``service.py`` 负责）。连接使用 WAL 允许只读并发，
``PRAGMA foreign_keys=ON`` 与 ``PRAGMA synchronous=FULL`` 保证完整性。
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .errors import IllegalTransition

# 当前 Ledger Schema 版本（写入 schema_meta）
SCHEMA_VERSION = "1.0.0"

# 15/16 张业务表由下方 DDL 逐字枚举；AUTOINCREMENT 会额外产生 SQLite 内部表
# sqlite_sequence（查询 sqlite_master 时需排除）。
DDL = (
    """
    CREATE TABLE IF NOT EXISTS schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS artifacts (
        artifact_id TEXT PRIMARY KEY,
        artifact_type TEXT NOT NULL,
        created_at TEXT NOT NULL,
        actor_ref TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS artifact_revisions (
        artifact_revision_id TEXT PRIMARY KEY,
        artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
        status TEXT NOT NULL,
        status_version INTEGER NOT NULL,
        sha256 TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        object_key TEXT NOT NULL,
        schema_id TEXT,
        schema_version TEXT,
        processing_run_id TEXT,
        step_run_id TEXT,
        producer_module TEXT NOT NULL,
        producer_version TEXT NOT NULL,
        configuration_revision_id TEXT,
        validation_report_revision_id TEXT,
        rights_scope TEXT NOT NULL,
        prev_revision_id TEXT,
        created_at TEXT NOT NULL,
        sealed_at TEXT,
        actor_ref TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS revision_status_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artifact_revision_id TEXT NOT NULL REFERENCES artifact_revisions(artifact_revision_id),
        from_status TEXT NOT NULL,
        to_status TEXT NOT NULL,
        reason TEXT,
        actor_ref TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stage_packages (
        stage_package_id TEXT PRIMARY KEY,
        artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
        stage TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS processing_runs (
        processing_run_id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        edition_part_id TEXT NOT NULL,
        technique_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        actor_ref TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS step_runs (
        step_run_id TEXT PRIMARY KEY,
        processing_run_id TEXT NOT NULL REFERENCES processing_runs(processing_run_id),
        stage TEXT NOT NULL,
        status TEXT NOT NULL,
        status_version INTEGER NOT NULL,
        request_json TEXT NOT NULL,
        result_json TEXT,
        supersedes_step_run_id TEXT,
        resume_token_hash TEXT,
        deadline TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        actor_ref TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS step_run_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        step_run_id TEXT NOT NULL REFERENCES step_runs(step_run_id),
        event_type TEXT NOT NULL,
        from_status TEXT,
        to_status TEXT,
        reason TEXT,
        source TEXT,
        actor_ref TEXT NOT NULL,
        payload_json TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS frozen_inputs (
        step_run_id TEXT NOT NULL REFERENCES step_runs(step_run_id),
        artifact_revision_id TEXT NOT NULL REFERENCES artifact_revisions(artifact_revision_id),
        PRIMARY KEY (step_run_id, artifact_revision_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transformations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        step_run_id TEXT NOT NULL REFERENCES step_runs(step_run_id),
        operation TEXT NOT NULL,
        tool TEXT NOT NULL,
        tool_version TEXT NOT NULL,
        model_ref TEXT,
        configuration_revision_id TEXT NOT NULL REFERENCES artifact_revisions(artifact_revision_id),
        validation_report_revision_id TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transformation_inputs (
        transformation_id INTEGER NOT NULL REFERENCES transformations(id),
        artifact_revision_id TEXT NOT NULL REFERENCES artifact_revisions(artifact_revision_id),
        PRIMARY KEY (transformation_id, artifact_revision_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transformation_outputs (
        transformation_id INTEGER NOT NULL REFERENCES transformations(id),
        artifact_revision_id TEXT NOT NULL REFERENCES artifact_revisions(artifact_revision_id),
        PRIMARY KEY (transformation_id, artifact_revision_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transformation_human_events (
        transformation_id INTEGER NOT NULL REFERENCES transformations(id),
        event_revision_id TEXT NOT NULL REFERENCES artifact_revisions(artifact_revision_id),
        PRIMARY KEY (transformation_id, event_revision_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS human_events (
        event_revision_id TEXT PRIMARY KEY REFERENCES artifact_revisions(artifact_revision_id),
        step_run_id TEXT NOT NULL REFERENCES step_runs(step_run_id),
        decision_type TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stage_checkpoints (
        artifact_revision_id TEXT PRIMARY KEY REFERENCES artifact_revisions(artifact_revision_id),
        artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
        edition_part_id TEXT NOT NULL,
        stage TEXT NOT NULL,
        step_run_id TEXT NOT NULL REFERENCES step_runs(step_run_id),
        prev_checkpoint_revision_id TEXT,
        rework_impact_report_revision_id TEXT,
        actor_ref TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        actor_ref TEXT NOT NULL,
        action TEXT NOT NULL,
        target TEXT NOT NULL,
        payload_json TEXT
    )
    """,
)

# update_step_run_status 允许额外更新的列白名单（防注入）
_STEP_RUN_UPDATABLE = frozenset(
    {"result_json", "supersedes_step_run_id", "resume_token_hash", "deadline", "request_json"}
)


def utcnow() -> str:
    """返回 ISO-8601 UTC 时间字符串（微秒精度，``Z`` 结尾）。"""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _as_dict(row):
    """把 ``sqlite3.Row`` 转为 dict；``None`` 原样返回。"""
    return dict(row) if row is not None else None


class MetadataStore:
    """SQLite Metadata Ledger 的连接与低层 CRUD。

    :param path: ``ledger.sqlite`` 的路径。
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.conn = None

    def open(self):
        """打开（必要时创建）数据库并设置 WAL / FK / synchronous。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.isolation_level = None  # 手动控制事务（transaction()）
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA synchronous=FULL")
        return self

    def close(self):
        """关闭连接（幂等）。"""
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def migrate(self):
        """幂等建表并写入 ``schema_meta``。"""
        if self.conn is None:
            raise RuntimeError("MetadataStore 未打开：请先调用 open()")
        for statement in DDL:
            self.conn.execute(statement)
        self.conn.execute(
            "INSERT OR IGNORE INTO schema_meta(key, value) VALUES ('ledger_schema_version', ?)",
            (SCHEMA_VERSION,),
        )

    @classmethod
    def open_readonly(cls, path):
        """以 ``mode=ro`` 只读打开，不取写锁。"""
        store = cls(path)
        uri = "file:%s?mode=ro" % path
        store.conn = sqlite3.connect(uri, uri=True)
        store.conn.isolation_level = None
        store.conn.row_factory = sqlite3.Row
        return store

    @contextmanager
    def transaction(self):
        """``BEGIN IMMEDIATE`` 事务上下文；异常回滚，正常提交。"""
        if self.conn is None:
            raise RuntimeError("MetadataStore 未打开：请先调用 open()")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
        except BaseException:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()

    # ---- Artifact / Revision ----

    def insert_artifact(self, artifact_id, artifact_type, created_at, actor_ref):
        """插入一个 Artifact 逻辑身份。"""
        self.conn.execute(
            "INSERT INTO artifacts(artifact_id, artifact_type, created_at, actor_ref) "
            "VALUES (?, ?, ?, ?)",
            (artifact_id, artifact_type, created_at, actor_ref),
        )

    def insert_revision(
        self,
        artifact_revision_id,
        artifact_id,
        status,
        status_version,
        sha256,
        size_bytes,
        object_key,
        producer_module,
        producer_version,
        rights_scope,
        created_at,
        actor_ref,
        schema_id=None,
        schema_version=None,
        processing_run_id=None,
        step_run_id=None,
        configuration_revision_id=None,
        validation_report_revision_id=None,
        prev_revision_id=None,
        sealed_at=None,
    ):
        """插入一个不可变 Artifact Revision（低层，不校验状态合法性）。"""
        self.conn.execute(
            "INSERT INTO artifact_revisions("
            "artifact_revision_id, artifact_id, status, status_version, sha256, size_bytes, "
            "object_key, schema_id, schema_version, processing_run_id, step_run_id, "
            "producer_module, producer_version, configuration_revision_id, "
            "validation_report_revision_id, rights_scope, prev_revision_id, created_at, "
            "sealed_at, actor_ref) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                artifact_revision_id,
                artifact_id,
                status,
                status_version,
                sha256,
                size_bytes,
                object_key,
                schema_id,
                schema_version,
                processing_run_id,
                step_run_id,
                producer_module,
                producer_version,
                configuration_revision_id,
                validation_report_revision_id,
                rights_scope,
                prev_revision_id,
                created_at,
                sealed_at,
                actor_ref,
            ),
        )

    def update_revision_status(self, rev, from_status, to_status, reason, actor):
        """按 ``WHERE status=from_status`` 更新 Revision 状态并记事件。

        影响行数不为 1 时抛 ``IllegalTransition``（状态已被并发改写）。
        """
        now = utcnow()
        cursor = self.conn.execute(
            "UPDATE artifact_revisions SET status=?, status_version=status_version+1, "
            "sealed_at=CASE WHEN ?='sealed' THEN ? ELSE sealed_at END "
            "WHERE artifact_revision_id=? AND status=?",
            (to_status, to_status, now, rev, from_status),
        )
        if cursor.rowcount != 1:
            raise IllegalTransition(
                "Revision %s 状态未处于 %s，无法迁移到 %s" % (rev, from_status, to_status)
            )
        self.conn.execute(
            "INSERT INTO revision_status_events("
            "artifact_revision_id, from_status, to_status, reason, actor_ref, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (rev, from_status, to_status, reason, actor, now),
        )

    def get_revision(self, artifact_revision_id):
        """按修订号返回 dict，或 ``None``。"""
        row = self.conn.execute(
            "SELECT * FROM artifact_revisions WHERE artifact_revision_id=?",
            (artifact_revision_id,),
        ).fetchone()
        return _as_dict(row)

    # ---- ProcessingRun / StepRun ----

    def insert_processing_run(
        self, processing_run_id, kind, edition_part_id, technique_id, created_at, actor_ref
    ):
        """插入一个 ProcessingRun。"""
        self.conn.execute(
            "INSERT INTO processing_runs("
            "processing_run_id, kind, edition_part_id, technique_id, created_at, actor_ref) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (processing_run_id, kind, edition_part_id, technique_id, created_at, actor_ref),
        )

    def insert_step_run(
        self,
        step_run_id,
        processing_run_id,
        stage,
        status,
        status_version,
        request_json,
        created_at,
        updated_at,
        actor_ref,
        result_json=None,
        supersedes_step_run_id=None,
        resume_token_hash=None,
        deadline=None,
    ):
        """插入一个 StepRun。"""
        self.conn.execute(
            "INSERT INTO step_runs("
            "step_run_id, processing_run_id, stage, status, status_version, request_json, "
            "result_json, supersedes_step_run_id, resume_token_hash, deadline, created_at, "
            "updated_at, actor_ref) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                step_run_id,
                processing_run_id,
                stage,
                status,
                status_version,
                request_json,
                result_json,
                supersedes_step_run_id,
                resume_token_hash,
                deadline,
                created_at,
                updated_at,
                actor_ref,
            ),
        )

    def update_step_run_status(
        self, step_run_id, from_status, to_status, expected_status_version, fields=None
    ):
        """乐观锁更新 StepRun 状态：``WHERE status=from_status AND status_version=expected``。

        成功时 ``status_version+1``；影响行数不为 1 时抛 ``IllegalTransition``。
        ``fields`` 为额外更新的列（如 ``{"result_json": ...}`` / ``{"resume_token_hash": None}``）。
        """
        now = utcnow()
        assignments = ["status=?", "status_version=status_version+1", "updated_at=?"]
        params = [to_status, now]
        for column, value in (fields or {}).items():
            if column not in _STEP_RUN_UPDATABLE:
                raise ValueError("不允许更新的列: %s" % column)
            assignments.append("%s=?" % column)
            params.append(value)
        params.extend([step_run_id, from_status, expected_status_version])
        cursor = self.conn.execute(
            "UPDATE step_runs SET %s "
            "WHERE step_run_id=? AND status=? AND status_version=?" % ", ".join(assignments),
            params,
        )
        if cursor.rowcount != 1:
            raise IllegalTransition(
                "StepRun %s 乐观锁失败：期望 status=%s, status_version=%s"
                % (step_run_id, from_status, expected_status_version)
            )

    # ---- 只读元数据查询（TODO.md T03：模块经 LedgerPort 调用，不再自己写 SQL） ----

    _DESCRIBE_SELECT = (
        "SELECT r.artifact_revision_id, r.artifact_id, a.artifact_type, r.sha256, r.status, "
        "r.step_run_id, r.processing_run_id, r.created_at, sp.stage_package_id "
        "FROM artifact_revisions r JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "LEFT JOIN stage_packages sp ON sp.artifact_id = r.artifact_id "
    )

    def describe_revision(self, artifact_revision_id):
        """修订的元数据（含 artifact_type；stage_package 另带 stage_package_id），或 ``None``。"""
        row = self.conn.execute(
            self._DESCRIBE_SELECT + "WHERE r.artifact_revision_id=?", (artifact_revision_id,)
        ).fetchone()
        return _as_dict(row)

    def list_step_run_revisions(self, step_run_id, artifact_type=None, status=None):
        """某 StepRun 产出的修订元数据，可按类型、状态筛选；按产生顺序。"""
        sql = self._DESCRIBE_SELECT + "WHERE r.step_run_id=?"
        params = [step_run_id]
        if artifact_type is not None:
            sql += " AND a.artifact_type=?"
            params.append(artifact_type)
        if status is not None:
            sql += " AND r.status=?"
            params.append(status)
        sql += " ORDER BY r.created_at, r.rowid"
        return [dict(row) for row in self.conn.execute(sql, tuple(params)).fetchall()]

    def list_artifact_revisions(self, artifact_id):
        """某 Artifact 的全部修订元数据；按产生顺序。"""
        rows = self.conn.execute(
            self._DESCRIBE_SELECT + "WHERE r.artifact_id=? ORDER BY r.created_at, r.rowid",
            (artifact_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_frozen_inputs(self, step_run_id):
        """某 StepRun 冻结的输入修订号，升序。"""
        rows = self.conn.execute(
            "SELECT artifact_revision_id FROM frozen_inputs WHERE step_run_id=? "
            "ORDER BY artifact_revision_id",
            (step_run_id,),
        ).fetchall()
        return [row[0] for row in rows]

    def get_processing_run(self, processing_run_id):
        """按 ProcessingRun 号返回 dict，或 ``None``。"""
        row = self.conn.execute(
            "SELECT * FROM processing_runs WHERE processing_run_id=?", (processing_run_id,)
        ).fetchone()
        return _as_dict(row)

    def latest_processing_run(self, edition_part_id, kind):
        """某 EditionPart 最近创建的指定 kind 的 ProcessingRun 号，没有则 ``None``。"""
        row = self.conn.execute(
            "SELECT processing_run_id FROM processing_runs WHERE edition_part_id=? AND kind=? "
            "ORDER BY created_at DESC LIMIT 1",
            (edition_part_id, kind),
        ).fetchone()
        return row[0] if row is not None else None

    def latest_checkpoint_step_run(self, edition_part_id, stage, status):
        """某 EditionPart×Stage 检查点所属、StepRun 状态为 ``status`` 的最新 StepRun 号，没有则 ``None``。

        「最新」按检查点 ``created_at DESC, rowid DESC``。
        """
        rows = self.conn.execute(
            "SELECT DISTINCT c.step_run_id, c.created_at, c.rowid FROM stage_checkpoints c "
            "JOIN step_runs r ON r.step_run_id = c.step_run_id "
            "WHERE c.edition_part_id=? AND c.stage=? AND r.status=? "
            "ORDER BY c.created_at DESC, c.rowid DESC",
            (edition_part_id, stage, status),
        ).fetchall()
        return rows[0][0] if rows else None

    def list_revisions(
        self,
        artifact_type=None,
        status=None,
        step_run_ids=None,
        processing_run_id=None,
        prev_revision_id=None,
    ):
        """按条件筛修订元数据（形状同 ``describe_revision``，另带 ``prev_revision_id``）；按写入顺序（rowid）。

        ``step_run_ids`` 为 ``None`` 表示不按 StepRun 筛；为空序列时返回 ``[]``。
        """
        sql = (
            "SELECT r.artifact_revision_id, r.artifact_id, a.artifact_type, r.sha256, r.status, "
            "r.step_run_id, r.processing_run_id, r.created_at, sp.stage_package_id, "
            "r.prev_revision_id "
            "FROM artifact_revisions r JOIN artifacts a ON a.artifact_id = r.artifact_id "
            "LEFT JOIN stage_packages sp ON sp.artifact_id = r.artifact_id WHERE 1=1"
        )
        params = []
        if artifact_type is not None:
            sql += " AND a.artifact_type=?"
            params.append(artifact_type)
        if status is not None:
            sql += " AND r.status=?"
            params.append(status)
        if step_run_ids is not None:
            step_run_ids = list(step_run_ids)
            if not step_run_ids:
                return []
            sql += " AND r.step_run_id IN (%s)" % ",".join("?" * len(step_run_ids))
            params.extend(step_run_ids)
        if processing_run_id is not None:
            sql += " AND r.processing_run_id=?"
            params.append(processing_run_id)
        if prev_revision_id is not None:
            sql += " AND r.prev_revision_id=?"
            params.append(prev_revision_id)
        sql += " ORDER BY r.rowid"
        return [dict(row) for row in self.conn.execute(sql, tuple(params)).fetchall()]

    def list_human_events(self, step_run_id=None):
        """人工事件登记行（event_revision_id、step_run_id、decision_type、created_at），按写入顺序（rowid）。"""
        sql = "SELECT event_revision_id, step_run_id, decision_type, created_at FROM human_events"
        params = ()
        if step_run_id is not None:
            sql += " WHERE step_run_id=?"
            params = (step_run_id,)
        sql += " ORDER BY rowid"
        return [dict(row) for row in self.conn.execute(sql, params).fetchall()]

    # —— T03c M6 新增 ——
    def list_step_run_checkpoints(self, step_run_id):
        """某 StepRun 的全部 StageCheckpoint 元数据行，按写入顺序（rowid）；只读登记列，不读对象内容。"""
        rows = self.conn.execute(
            "SELECT artifact_revision_id, artifact_id, edition_part_id, stage, step_run_id, "
            "prev_checkpoint_revision_id, rework_impact_report_revision_id, actor_ref, created_at "
            "FROM stage_checkpoints WHERE step_run_id=? ORDER BY rowid",
            (step_run_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_step_runs(self, edition_part_id, stage=None):
        """某 EditionPart 的 StepRun（可按 stage 筛选）；按创建顺序（旧→新）。"""
        sql = (
            "SELECT sr.* FROM step_runs sr "
            "JOIN processing_runs pr ON pr.processing_run_id = sr.processing_run_id "
            "WHERE pr.edition_part_id=?"
        )
        params = [edition_part_id]
        if stage is not None:
            sql += " AND sr.stage=?"
            params.append(stage)
        sql += " ORDER BY sr.created_at, sr.rowid"
        return [dict(row) for row in self.conn.execute(sql, tuple(params)).fetchall()]

    def list_stage_packages(self, stage):
        """某 stage 的全部 StagePackage 修订，附归属 StepRun 状态。"""
        rows = self.conn.execute(
            "SELECT sp.stage_package_id, sp.artifact_id, sp.stage, r.artifact_revision_id, "
            "r.step_run_id, sr.status AS step_run_status "
            "FROM stage_packages sp "
            "JOIN artifact_revisions r ON r.artifact_id = sp.artifact_id "
            "JOIN step_runs sr ON sr.step_run_id = r.step_run_id "
            "WHERE sp.stage=? ORDER BY r.created_at, r.rowid",
            (stage,),
        ).fetchall()
        return [dict(row) for row in rows]

    def count_artifacts(self, artifact_type):
        """某类型的 Artifact 数。"""
        row = self.conn.execute(
            "SELECT COUNT(*) FROM artifacts WHERE artifact_type=?", (artifact_type,)
        ).fetchone()
        return int(row[0])

    def get_step_run(self, step_run_id):
        """按运行号返回 dict，或 ``None``。"""
        row = self.conn.execute(
            "SELECT * FROM step_runs WHERE step_run_id=?", (step_run_id,)
        ).fetchone()
        return _as_dict(row)

    def append_step_run_event(
        self,
        step_run_id,
        event_type,
        actor_ref,
        from_status=None,
        to_status=None,
        reason=None,
        source=None,
        payload_json=None,
    ):
        """追加一条 StepRun 事件（只增不减）。"""
        self.conn.execute(
            "INSERT INTO step_run_events("
            "step_run_id, event_type, from_status, to_status, reason, source, actor_ref, "
            "payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                step_run_id,
                event_type,
                from_status,
                to_status,
                reason,
                source,
                actor_ref,
                payload_json,
                utcnow(),
            ),
        )

    def list_step_run_events(self, step_run_id):
        """按写入顺序返回某 StepRun 的全部事件。"""
        rows = self.conn.execute(
            "SELECT * FROM step_run_events WHERE step_run_id=? ORDER BY id ASC",
            (step_run_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def add_frozen_inputs(self, step_run_id, artifact_revision_ids):
        """登记 StepRun 的冻结输入 Revision（重复输入幂等）。"""
        self.conn.executemany(
            "INSERT OR IGNORE INTO frozen_inputs(step_run_id, artifact_revision_id) "
            "VALUES (?, ?)",
            [(step_run_id, revision_id) for revision_id in artifact_revision_ids],
        )

    # ---- Transformation / HumanEvent ----

    def insert_transformation(
        self,
        step_run_id,
        operation,
        tool,
        tool_version,
        configuration_revision_id,
        input_revision_ids=(),
        output_revision_ids=(),
        human_event_revision_ids=(),
        model_ref=None,
        validation_report_revision_id=None,
    ):
        """插入一条 Transformation 及其 inputs/outputs/human_events，返回其整数主键。"""
        cursor = self.conn.execute(
            "INSERT INTO transformations("
            "step_run_id, operation, tool, tool_version, model_ref, configuration_revision_id, "
            "validation_report_revision_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                step_run_id,
                operation,
                tool,
                tool_version,
                model_ref,
                configuration_revision_id,
                validation_report_revision_id,
                utcnow(),
            ),
        )
        transformation_id = cursor.lastrowid
        self.conn.executemany(
            "INSERT INTO transformation_inputs(transformation_id, artifact_revision_id) "
            "VALUES (?, ?)",
            [(transformation_id, rid) for rid in input_revision_ids],
        )
        self.conn.executemany(
            "INSERT INTO transformation_outputs(transformation_id, artifact_revision_id) "
            "VALUES (?, ?)",
            [(transformation_id, rid) for rid in output_revision_ids],
        )
        self.conn.executemany(
            "INSERT INTO transformation_human_events(transformation_id, event_revision_id) "
            "VALUES (?, ?)",
            [(transformation_id, rid) for rid in human_event_revision_ids],
        )
        return transformation_id

    def list_transformations(self, step_run_id):
        """按写入顺序返回某 StepRun 的全部 Transformation。"""
        rows = self.conn.execute(
            "SELECT * FROM transformations WHERE step_run_id=? ORDER BY id ASC",
            (step_run_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_transformation_inputs(self, transformation_id):
        """返回某 Transformation 的输入 Revision 号列表。"""
        rows = self.conn.execute(
            "SELECT artifact_revision_id FROM transformation_inputs WHERE transformation_id=? "
            "ORDER BY artifact_revision_id ASC",
            (transformation_id,),
        ).fetchall()
        return [row[0] for row in rows]

    def list_transformation_outputs(self, transformation_id):
        """返回某 Transformation 的输出 Revision 号列表。"""
        rows = self.conn.execute(
            "SELECT artifact_revision_id FROM transformation_outputs WHERE transformation_id=? "
            "ORDER BY artifact_revision_id ASC",
            (transformation_id,),
        ).fetchall()
        return [row[0] for row in rows]

    def list_transformation_human_events(self, transformation_id):
        """返回某 Transformation 引用的人工事件 Revision 号列表。"""
        rows = self.conn.execute(
            "SELECT event_revision_id FROM transformation_human_events WHERE transformation_id=? "
            "ORDER BY event_revision_id ASC",
            (transformation_id,),
        ).fetchall()
        return [row[0] for row in rows]

    def insert_human_event(self, event_revision_id, step_run_id, decision_type=None):
        """登记一条封存人工事件 Revision。"""
        self.conn.execute(
            "INSERT INTO human_events(event_revision_id, step_run_id, decision_type, created_at) "
            "VALUES (?, ?, ?, ?)",
            (event_revision_id, step_run_id, decision_type, utcnow()),
        )

    # ---- StagePackage / Checkpoint / Audit ----

    def insert_stage_package(self, stage_package_id, artifact_id, stage):
        """登记 StagePackage 逻辑身份与 Artifact 的对应。"""
        self.conn.execute(
            "INSERT INTO stage_packages(stage_package_id, artifact_id, stage) VALUES (?, ?, ?)",
            (stage_package_id, artifact_id, stage),
        )

    def get_stage_package(self, stage_package_id):
        """按包号返回 dict，或 ``None``。"""
        row = self.conn.execute(
            "SELECT * FROM stage_packages WHERE stage_package_id=?", (stage_package_id,)
        ).fetchone()
        return _as_dict(row)

    def insert_checkpoint(
        self,
        artifact_revision_id,
        artifact_id,
        edition_part_id,
        stage,
        step_run_id,
        actor_ref,
        created_at,
        prev_checkpoint_revision_id=None,
        rework_impact_report_revision_id=None,
    ):
        """登记一个 StageCheckpoint 元数据行。"""
        self.conn.execute(
            "INSERT INTO stage_checkpoints("
            "artifact_revision_id, artifact_id, edition_part_id, stage, step_run_id, "
            "prev_checkpoint_revision_id, rework_impact_report_revision_id, actor_ref, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                artifact_revision_id,
                artifact_id,
                edition_part_id,
                stage,
                step_run_id,
                prev_checkpoint_revision_id,
                rework_impact_report_revision_id,
                actor_ref,
                created_at,
            ),
        )

    def latest_checkpoint(self, edition_part_id, stage):
        """返回某 EditionPart×Stage 链上最新的 Checkpoint，没有则 ``None``。"""
        row = self.conn.execute(
            "SELECT * FROM stage_checkpoints WHERE edition_part_id=? AND stage=? "
            "ORDER BY created_at DESC, rowid DESC LIMIT 1",
            (edition_part_id, stage),
        ).fetchone()
        return _as_dict(row)

    def list_checkpoints(self, edition_part_id, stage):
        """按链序（旧→新）返回某 EditionPart×Stage 的全部 Checkpoint。"""
        rows = self.conn.execute(
            "SELECT * FROM stage_checkpoints WHERE edition_part_id=? AND stage=? "
            "ORDER BY created_at ASC, rowid ASC",
            (edition_part_id, stage),
        ).fetchall()
        return [dict(row) for row in rows]

    def append_audit(self, action, target, actor_ref, payload_json=None):
        """追加一条审计记录（只增不减）。"""
        self.conn.execute(
            "INSERT INTO audit_log(created_at, actor_ref, action, target, payload_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (utcnow(), actor_ref, action, target, payload_json),
        )

    def count_audit(self):
        """返回审计记录条数（供测试断言事务无半成品）。"""
        return self.conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
