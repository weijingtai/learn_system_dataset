"""LedgerService（写 API）与 LedgerReader（只读 API）（规格 §7.1、§17、§17.1）。

设计要点：

- 构造 ``LedgerService`` 即 ``migrate()`` 并取 ``WriterLock``；取不到直接
  ``WriterLocked``，不进入半初始化状态；``close()`` 释放锁与连接。
- 每个写方法在**一个** ``store.transaction()`` 内完成；状态变化必定写
  ``revision_status_events`` / ``step_run_events``；每次写 API 调用写
  ``audit_log``（``action`` = 方法名，``target`` = 主标识）。
- 所有 ``*_id`` 参数先经 ``ids.validate``；引用型参数必须是已 ``sealed`` 修订，
  否则 ``MissingReference(REF_001)`` / ``NotConsumable``。
- ``resume_token`` 只存哈希：``resume_token_hash = "v<status_version>:<sha256(token)>"``。
  哈希与签发时的 ``status_version`` 绑定；``recover`` 回到 ``awaiting_human`` 时按新
  版本重新锚定前缀，使 token 在 suspended/recovery 往返后仍可用（§7.1 + BDD 3.3）。
- 实现选定（ACT 未逐字规定，已在交付报告登记）：
  1. ``step_runs.stage`` 由 ``configuration_artifact_id`` 的已封存内容 JSON 的
     ``stage`` 键推导 —— StepRequest Schema 没有 stage 字段，配置修订是该 stage
     的唯一载体（见 act/05.yaml step 2）；
  2. ``StepResult.status_version`` 取「完成该次迁移后的版本」（当前值 + 1），
     因为 ``step_result.schema.json`` 要求 ``minimum: 1``，而新建 StepRun 的
     ``status_version`` 为 0（ACT 03）。
"""

import hashlib
import json
import re
import secrets
from pathlib import Path

import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .actor import ActorProvider, LocalActorProvider
from .errors import (
    DuplicateIdentifier,
    HashMismatch,
    IllegalTransition,
    InvalidIdentifier,
    InvalidResumeToken,
    LedgerError,
    MissingReference,
    NotConsumable,
    SchemaViolation,
)
from .ids import STAGES, new_id, validate
from .lock import WriterLock
from .objects import ObjectStore
from .states import (
    REVIEW_DECISION_TYPES,
    TERMINAL_STEP_RUN,
    check_step_run_transition,
)
from .store import MetadataStore, utcnow

# 默认 Schema 目录：仓库根 openspec/schemas
DEFAULT_SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "openspec" / "schemas"

# artifact_type / operation 的闭集形态（§17 必记字段）
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# suspend 的来源闭集（§17）
SUSPEND_SOURCES = ("operator", "infrastructure")

# put_run_artifact 允许的 artifact_type（ACT 05）
RUN_ARTIFACT_TYPES = ("configuration", "technique_profile")

# Ledger 自己产出的修订的 producer 标记
_LEDGER_PRODUCER = "pipeline.ledger.service"
_LEDGER_PRODUCER_VERSION = "1.0"


def _load_validator(schemas_dir: Path, name: str):
    """加载一个 Draft 2020-12 校验器，并注册 ``artifact_ref.schema.json`` 供 ``$ref`` 解析。"""
    schemas_dir = Path(schemas_dir)
    with open(schemas_dir / name, encoding="utf-8") as handle:
        schema = json.load(handle)
    with open(schemas_dir / "artifact_ref.schema.json", encoding="utf-8") as handle:
        artifact_ref = json.load(handle)
    registry = Registry().with_resource(
        "artifact_ref.schema.json",
        Resource.from_contents(artifact_ref, default_specification=DRAFT202012),
    )
    return jsonschema.Draft202012Validator(schema, registry=registry)


def _validate_instance(validator, instance, label: str):
    """按 Schema 校验；失败抛 ``SchemaViolation``（缺字段 ``SCH_001``、枚举 ``SCH_002``）。"""
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if not errors:
        return instance
    first = errors[0]
    code = "SCH_002" if first.validator in ("enum", "const") else "SCH_001"
    raise SchemaViolation(
        "%s 校验失败（%s）: %s" % (label, first.validator, first.message), code=code
    )


def _token_hash(token: str, status_version: int) -> str:
    """把 ``resume_token`` 与该次 ``awaiting_human`` 的 ``status_version`` 绑定后只存哈希。"""
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return "v%d:%s" % (status_version, digest)


def _token_digest(stored: str) -> str:
    """从存储串 ``v<版本>:<sha256>`` 里取出哈希部分。"""
    _, _, digest = stored.partition(":")
    return digest


class LedgerReadMixin:
    """只读查询面的唯一实现：``LedgerService``（持锁直连）与 ``LedgerReader``（mode=ro）共用。

    两个类暴露同一组同名只读方法（ACT 03 contract），实现只写一份，避免 API 面漂移。
    """

    def get_revision(self, artifact_revision_id):
        """按修订号返回 dict，或 ``None``。"""
        return self.store.get_revision(artifact_revision_id)

    def get_step_run(self, step_run_id):
        """按运行号返回 dict，或 ``None``。"""
        return self.store.get_step_run(step_run_id)

    def list_step_run_events(self, step_run_id):
        """返回某 StepRun 的全部事件（只增不减）。"""
        return self.store.list_step_run_events(step_run_id)

    def list_transformations(self, step_run_id):
        """返回某 StepRun 的全部 Transformation。"""
        return self.store.list_transformations(step_run_id)

    def _checkpoint_with_content(self, row):
        """把 ``stage_checkpoints`` 元数据行补上内容 JSON。"""
        if row is None:
            return None
        result = dict(row)
        revision = self.store.get_revision(result["artifact_revision_id"])
        result["content"] = json.loads(
            self.objects.get(revision["sha256"]).decode("utf-8")
        )
        return result

    def latest_checkpoint(self, edition_part_id, stage):
        """返回某 EditionPart×Stage 链上最新 Checkpoint（含内容 JSON），没有则 ``None``。"""
        return self._checkpoint_with_content(
            self.store.latest_checkpoint(edition_part_id, stage)
        )

    def list_checkpoints(self, edition_part_id, stage):
        """按链序（旧→新）返回该链的全部 Checkpoint（含内容 JSON）。"""
        return [
            self._checkpoint_with_content(row)
            for row in self.store.list_checkpoints(edition_part_id, stage)
        ]

    def read_object(self, sha256):
        """按 SHA-256 读取对象字节（``LedgerService`` 与 ``LedgerReader`` 共用；加工模块不许直接触达 ``.objects``）。"""
        return self.objects.get(sha256)

    # ---- 只读元数据查询（TODO.md T03）：加工模块经 LedgerPort 调用，不许再触达 .store / .objects ----
    def describe_revision(self, artifact_revision_id):
        """修订元数据：artifact_revision_id、artifact_id、artifact_type、sha256、status、step_run_id、
        processing_run_id、created_at、stage_package_id（非 stage_package 为 None）；不存在返回 ``None``。"""
        return self.store.describe_revision(artifact_revision_id)

    def list_step_run_revisions(self, step_run_id, artifact_type=None, status=None):
        """某 StepRun 产出的修订元数据（形状同 ``describe_revision``），可按类型、状态筛选。"""
        return self.store.list_step_run_revisions(step_run_id, artifact_type, status)

    def list_artifact_revisions(self, artifact_id):
        """某 Artifact 的全部修订元数据（形状同 ``describe_revision``），按产生顺序。"""
        return self.store.list_artifact_revisions(artifact_id)

    def list_frozen_inputs(self, step_run_id):
        """某 StepRun 冻结的输入修订号，升序。"""
        return self.store.list_frozen_inputs(step_run_id)

    def get_processing_run(self, processing_run_id):
        """按 ProcessingRun 号返回 dict（含 edition_part_id），或 ``None``。"""
        return self.store.get_processing_run(processing_run_id)

    def list_step_runs(self, edition_part_id, stage=None):
        """某 EditionPart 的 StepRun（可按 stage 筛选），旧→新。"""
        return self.store.list_step_runs(edition_part_id, stage)

    # ---- 只读元数据查询（TODO.md T03c）：M1/M2/M4/M6/M7 原先自写的 SQL 挪到这里 ----
    def latest_processing_run(self, edition_part_id, kind):
        """某 EditionPart 最近创建的指定 kind 的 ProcessingRun 号，没有则 ``None``。"""
        return self.store.latest_processing_run(edition_part_id, kind)

    def latest_checkpoint_step_run(self, edition_part_id, stage, status):
        """某 EditionPart×Stage 检查点所属、StepRun 状态为 ``status`` 的最新 StepRun 号，没有则 ``None``。"""
        return self.store.latest_checkpoint_step_run(edition_part_id, stage, status)

    def list_revisions(
        self,
        artifact_type=None,
        status=None,
        step_run_ids=None,
        processing_run_id=None,
        prev_revision_id=None,
    ):
        """按条件筛修订元数据（形状同 ``describe_revision``，另带 ``prev_revision_id``），按写入顺序。"""
        return self.store.list_revisions(
            artifact_type, status, step_run_ids, processing_run_id, prev_revision_id
        )

    def list_human_events(self, step_run_id=None):
        """人工事件登记行（可按 StepRun 筛），按写入顺序。"""
        return self.store.list_human_events(step_run_id)

    def list_transformation_inputs(self, transformation_id):
        """某 Transformation 的输入修订号（修订号升序）。"""
        return self.store.list_transformation_inputs(transformation_id)

    def list_transformation_outputs(self, transformation_id):
        """某 Transformation 的输出修订号（修订号升序）。"""
        return self.store.list_transformation_outputs(transformation_id)

    def list_transformation_human_events(self, transformation_id):
        """某 Transformation 引用的人工事件修订号（修订号升序）。"""
        return self.store.list_transformation_human_events(transformation_id)

    # —— T03c M6 新增 ——
    def list_step_run_checkpoints(self, step_run_id):
        """某 StepRun 的全部 StageCheckpoint 元数据行（无内容 JSON），按写入顺序（旧→新）。"""
        return self.store.list_step_run_checkpoints(step_run_id)

    def list_stage_packages(self, stage):
        """某 stage 的全部 StagePackage 修订，附 step_run_id 与 step_run_status。"""
        return self.store.list_stage_packages(stage)

    def count_artifacts(self, artifact_type):
        """某类型的 Artifact 数。"""
        return self.store.count_artifacts(artifact_type)

    def run_status(self, processing_run_id):
        """聚合某 ProcessingRun 的运行状态（§17）。"""
        return _run_status(self.store, processing_run_id)

    def stage_progress(self, processing_run_id):
        """按 stage 聚合某 ProcessingRun 的进度（§17.1）。"""
        return _stage_progress(self.store, processing_run_id)


class LedgerService(LedgerReadMixin):
    """Ledger 写 API（规格 §17 步骤事务序列、§7.1 人工恢复、§17.1 Checkpoint）。"""

    def __init__(self, root, actor_provider: ActorProvider = None, schemas_dir=None):
        self.root = Path(root)
        self.actor_provider = actor_provider or LocalActorProvider()
        self.schemas_dir = Path(schemas_dir) if schemas_dir else DEFAULT_SCHEMAS_DIR
        self.store = MetadataStore(self.root / "ledger.sqlite")
        self.store.open()
        try:
            self.store.migrate()
            self.lock = WriterLock(self.root).acquire()
        except BaseException:
            self.store.close()
            raise
        self.objects = ObjectStore(self.root)
        self._validators = {}

    # ------------------------------------------------------------ 基础
    def close(self):
        """释放写锁并关闭连接（幂等）。"""
        if getattr(self, "lock", None) is not None:
            self.lock.release()
            self.lock = None
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def actor(self) -> str:
        """当前操作者引用（写入 ``actor_ref``）。"""
        return self.actor_provider.current_actor()

    def _validator(self, name):
        if name not in self._validators:
            self._validators[name] = _load_validator(self.schemas_dir, name)
        return self._validators[name]

    def _validate(self, schema_name, instance, label):
        return _validate_instance(self._validator(schema_name), instance, label)

    def _audit(self, action, target, payload=None):
        """写审计记录（必须在事务内调用）。"""
        self.store.append_audit(
            action,
            str(target),
            self.actor(),
            json.dumps(payload, sort_keys=True, ensure_ascii=False)
            if payload is not None
            else None,
        )

    def _exists(self, sql, value):
        return self.store.conn.execute(sql, (value,)).fetchone() is not None

    def _new_or_explicit(self, kind, explicit, sql):
        """返回显式 ID（格式非法 ``ID_001``、已占用 ``ID_002``）或新生成的 ID。"""
        if explicit is None:
            return new_id(kind)
        validate(kind, explicit)
        if self._exists(sql, explicit):
            raise DuplicateIdentifier("%s 已被占用: %s" % (kind, explicit))
        return explicit

    def _require_sealed(self, revision_id):
        """要求 ``revision_id`` 存在且为 ``sealed``；否则 ``REF_001`` / ``NotConsumable``。"""
        row = self.store.get_revision(revision_id)
        if row is None:
            raise MissingReference("引用的修订不存在: %s" % revision_id, code="REF_001")
        if row["status"] != "sealed":
            raise NotConsumable(
                "引用的修订不是 sealed（当前 %s）: %s" % (row["status"], revision_id)
            )
        return row

    def _artifact_type(self, revision_id):
        row = self.store.conn.execute(
            "SELECT a.artifact_type FROM artifacts a JOIN artifact_revisions r "
            "ON r.artifact_id = a.artifact_id WHERE r.artifact_revision_id=?",
            (revision_id,),
        ).fetchone()
        return None if row is None else row[0]

    def _live_step_run(self, step_run_id):
        """取一个可继续写入的 StepRun（running / awaiting_human）。"""
        row = self.store.get_step_run(step_run_id)
        if row is None:
            raise MissingReference("StepRun 不存在: %s" % step_run_id, code="REF_001")
        if row["status"] not in ("running", "awaiting_human"):
            raise IllegalTransition(
                "StepRun %s 状态 %s 不接受新的写入" % (step_run_id, row["status"])
            )
        return row

    def _frozen_input_ids(self, step_run_id):
        rows = self.store.conn.execute(
            "SELECT artifact_revision_id FROM frozen_inputs WHERE step_run_id=? "
            "ORDER BY artifact_revision_id",
            (step_run_id,),
        ).fetchall()
        return [row[0] for row in rows]

    def _own_sealed_revisions(self, step_run_id):
        rows = self.store.conn.execute(
            "SELECT artifact_revision_id FROM artifact_revisions "
            "WHERE step_run_id=? AND status='sealed' ORDER BY created_at, rowid",
            (step_run_id,),
        ).fetchall()
        return [row[0] for row in rows]

    def _human_event_ids(self, step_run_id):
        rows = self.store.conn.execute(
            "SELECT event_revision_id FROM human_events WHERE step_run_id=? "
            "ORDER BY created_at, rowid",
            (step_run_id,),
        ).fetchall()
        return [row[0] for row in rows]

    def _edition_part_id(self, processing_run_id):
        row = self.store.conn.execute(
            "SELECT edition_part_id FROM processing_runs WHERE processing_run_id=?",
            (processing_run_id,),
        ).fetchone()
        return None if row is None else row[0]

    def _configuration_stage(self, revision_id):
        """由已封存配置修订的内容 JSON 推导 stage（StepRequest 没有 stage 字段）。"""
        row = self._require_sealed(revision_id)
        try:
            payload = json.loads(self.objects.get(row["sha256"]).decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise SchemaViolation(
                "配置修订内容不是合法 JSON 对象: %s" % exc, code="SCH_001"
            )
        stage = payload.get("stage") if isinstance(payload, dict) else None
        if stage not in STAGES:
            raise SchemaViolation(
                "配置修订缺少合法 stage（§8.1 闭集 m1–m8）: %r" % (stage,),
                code="SCH_002",
            )
        return stage

    def _seal_ledger_revision(self, artifact_revision_id, reason):
        """把 Ledger 自己产出的 draft 修订直接封存（同事务内）。"""
        self.store.update_revision_status(
            artifact_revision_id, "draft", "sealed", reason, self.actor()
        )

    # -------------------------------------------------------- ProcessingRun
    def create_processing_run(
        self, kind, edition_part_id, technique_id, *, processing_run_id=None
    ):
        """建一个 ProcessingRun（``kind`` ∈ edition_run / release_run）。"""
        if kind not in ("edition_run", "release_run"):
            raise SchemaViolation(
                "kind 必须为 edition_run 或 release_run: %r" % (kind,), code="SCH_002"
            )
        validate("artifact_id", edition_part_id)
        if not isinstance(technique_id, str) or not technique_id:
            raise SchemaViolation("technique_id 不能为空", code="SCH_001")
        processing_run_id = self._new_or_explicit(
            "processing_run_id",
            processing_run_id,
            "SELECT 1 FROM processing_runs WHERE processing_run_id=?",
        )
        with self.store.transaction():
            self.store.insert_processing_run(
                processing_run_id,
                kind,
                edition_part_id,
                technique_id,
                utcnow(),
                self.actor(),
            )
            self._audit("create_processing_run", processing_run_id)
        return processing_run_id

    # ------------------------------------------------------------- StepRun
    def _begin_step_run_locked(self, request, step_run_id, supersedes_step_run_id=None):
        """在已开启的事务内建 StepRun（校验 + 冻结输入 + created 事件）。"""
        self._validate("step_request.schema.json", request, "StepRequest")
        request_step_run_id = request["step_run_id"]
        if step_run_id is not None and step_run_id != request_step_run_id:
            raise InvalidIdentifier(
                "step_run_id 参数与 StepRequest 冲突: %r != %r"
                % (step_run_id, request_step_run_id),
                code="ID_001",
            )
        step_run_id = request_step_run_id
        validate("step_run_id", step_run_id)
        processing_run_id = request["processing_run_id"]
        if not self._exists(
            "SELECT 1 FROM processing_runs WHERE processing_run_id=?", processing_run_id
        ):
            raise MissingReference(
                "ProcessingRun 不存在: %s" % processing_run_id, code="REF_001"
            )
        if self.store.get_step_run(step_run_id) is not None:
            raise DuplicateIdentifier("StepRun 已存在: %s" % step_run_id)
        stage = self._configuration_stage(request["configuration_artifact_id"])
        for revision_id in request["input_artifact_ids"]:
            self._require_sealed(revision_id)
        actor = self.actor()
        now = utcnow()
        request_json = json.dumps(request, sort_keys=True, ensure_ascii=False)
        self.store.insert_step_run(
            step_run_id,
            processing_run_id,
            stage,
            "running",
            0,
            request_json,
            now,
            now,
            actor,
            supersedes_step_run_id=supersedes_step_run_id,
        )
        self.store.add_frozen_inputs(step_run_id, request["input_artifact_ids"])
        self.store.append_step_run_event(
            step_run_id,
            "created",
            actor,
            to_status="running",
            payload_json=json.dumps(
                {
                    "stage": stage,
                    "frozen_inputs": self._frozen_input_ids(step_run_id),
                    "supersedes_step_run_id": supersedes_step_run_id,
                },
                sort_keys=True,
                ensure_ascii=False,
            ),
        )
        return step_run_id

    def begin_step_run(self, request, *, step_run_id=None):
        """按 StepRequest 开启一次 StepRun：冻结输入、状态 ``running``、事件 ``created``。"""
        with self.store.transaction():
            new_step_run_id = self._begin_step_run_locked(request, step_run_id)
            self._audit("begin_step_run", new_step_run_id)
        return new_step_run_id

    def supersede_step_run(self, old_step_run_id, new_request, *, step_run_id=None):
        """重跑：新 StepRun 以 ``supersedes_step_run_id`` 指向旧运行。

        旧运行未终结时进入 ``superseded``；已是终态则原终态不变，仅由新运行表达重跑关系。
        """
        old = self.store.get_step_run(old_step_run_id)
        if old is None:
            raise MissingReference(
                "StepRun 不存在: %s" % old_step_run_id, code="REF_001"
            )
        with self.store.transaction():
            new_step_run_id = self._begin_step_run_locked(
                new_request, step_run_id, supersedes_step_run_id=old_step_run_id
            )
            if old["status"] not in TERMINAL_STEP_RUN:
                self.store.update_step_run_status(
                    old_step_run_id, old["status"], "superseded", old["status_version"]
                )
                self.store.append_step_run_event(
                    old_step_run_id,
                    "transition",
                    self.actor(),
                    from_status=old["status"],
                    to_status="superseded",
                    reason="被新 StepRun 取代: %s" % new_step_run_id,
                )
            self._audit("supersede_step_run", new_step_run_id)
        return new_step_run_id

    # ------------------------------------------------------------ Artifact
    def put_artifact(
        self,
        step_run_id,
        artifact_type,
        data,
        *,
        artifact_id=None,
        artifact_revision_id=None,
        prev_revision_id=None,
        schema_id=None,
        schema_version=None,
        producer_module,
        producer_version,
        configuration_revision_id=None,
        rights_scope="internal",
    ):
        """写入一个 draft 修订（内容进 Object Store），返回 ``(artifact_id, revision_id)``。"""
        if not isinstance(artifact_type, str) or not _NAME_RE.match(artifact_type):
            raise SchemaViolation(
                "artifact_type 必须匹配 ^[a-z][a-z0-9_]*$: %r" % (artifact_type,),
                code="SCH_002",
            )
        if not isinstance(data, (bytes, bytearray)):
            raise SchemaViolation("data 必须是 bytes", code="SCH_001")
        data = bytes(data)
        with self.store.transaction():
            step = self._live_step_run(step_run_id)
            if configuration_revision_id is not None:
                self._require_sealed(configuration_revision_id)
            previous = None
            if prev_revision_id is not None:
                previous = self.store.get_revision(prev_revision_id)
                if previous is None:
                    raise MissingReference(
                        "前置修订不存在: %s" % prev_revision_id, code="REF_001"
                    )
            if artifact_id is not None:
                artifact_id = self._new_or_explicit(
                    "artifact_id",
                    artifact_id,
                    "SELECT 1 FROM artifacts WHERE artifact_id=?",
                )
                if previous is not None and previous["artifact_id"] != artifact_id:
                    raise IllegalTransition(
                        "同一 artifact 才能新增修订: %s != %s"
                        % (previous["artifact_id"], artifact_id)
                    )
            elif previous is not None:
                artifact_id = previous["artifact_id"]
            else:
                artifact_id = new_id("artifact_id")
            artifact_revision_id = self._new_or_explicit(
                "artifact_revision_id",
                artifact_revision_id,
                "SELECT 1 FROM artifact_revisions WHERE artifact_revision_id=?",
            )
            sha256, size = self.objects.put(data)
            actor = self.actor()
            now = utcnow()
            if not self._exists(
                "SELECT 1 FROM artifacts WHERE artifact_id=?", artifact_id
            ):
                self.store.insert_artifact(artifact_id, artifact_type, now, actor)
            self.store.insert_revision(
                artifact_revision_id,
                artifact_id,
                "draft",
                0,
                sha256,
                size,
                "objects/%s/%s" % (sha256[:2], sha256),
                producer_module,
                producer_version,
                rights_scope,
                now,
                actor,
                schema_id=schema_id,
                schema_version=schema_version,
                processing_run_id=step["processing_run_id"],
                step_run_id=step_run_id,
                configuration_revision_id=configuration_revision_id,
                prev_revision_id=prev_revision_id,
            )
            self._audit("put_artifact", artifact_id)
        return artifact_id, artifact_revision_id

    def put_run_artifact(
        self,
        processing_run_id,
        artifact_type,
        data,
        *,
        artifact_id=None,
        artifact_revision_id=None,
        producer_module,
        producer_version,
        rights_scope="internal",
        schema_id=None,
        schema_version=None,
    ):
        """受限入口：写入不挂 StepRun 的 ProcessingRun 级修订（配置 / 技法档案），写入即 sealed。

        ``begin_step_run`` 要求 ``configuration_artifact_id`` 已 sealed，而配置修订不属于
        任何 StepRun 的产出，故需要本入口。只允许 ``configuration`` 与
        ``technique_profile``（否则 ``SchemaViolation(SCH_002)``）。
        """
        if artifact_type not in RUN_ARTIFACT_TYPES:
            raise SchemaViolation(
                "put_run_artifact 只允许 %s，收到 %r"
                % ("/".join(RUN_ARTIFACT_TYPES), artifact_type),
                code="SCH_002",
            )
        if not isinstance(data, (bytes, bytearray)):
            raise SchemaViolation("data 必须是 bytes", code="SCH_001")
        data = bytes(data)
        if not self._exists(
            "SELECT 1 FROM processing_runs WHERE processing_run_id=?", processing_run_id
        ):
            raise MissingReference(
                "ProcessingRun 不存在: %s" % processing_run_id, code="REF_001"
            )
        with self.store.transaction():
            artifact_id = self._new_or_explicit(
                "artifact_id",
                artifact_id,
                "SELECT 1 FROM artifacts WHERE artifact_id=?",
            )
            artifact_revision_id = self._new_or_explicit(
                "artifact_revision_id",
                artifact_revision_id,
                "SELECT 1 FROM artifact_revisions WHERE artifact_revision_id=?",
            )
            sha256, size = self.objects.put(data)
            actor = self.actor()
            now = utcnow()
            self.store.insert_artifact(artifact_id, artifact_type, now, actor)
            self.store.insert_revision(
                artifact_revision_id,
                artifact_id,
                "draft",
                0,
                sha256,
                size,
                "objects/%s/%s" % (sha256[:2], sha256),
                producer_module,
                producer_version,
                rights_scope,
                now,
                actor,
                schema_id=schema_id,
                schema_version=schema_version,
                processing_run_id=processing_run_id,
            )
            self._seal_ledger_revision(artifact_revision_id, "运行级修订写入即封存")
            self._audit("put_run_artifact", artifact_id)
        return artifact_id, artifact_revision_id

    def seal_revision(self, artifact_revision_id, *, validation_report_revision_id=None):
        """``draft`` → ``sealed``；Object 哈希校验失败则转 ``quarantined`` 并抛 ``SRC_003``。"""
        validate("artifact_revision_id", artifact_revision_id)
        row = self.store.get_revision(artifact_revision_id)
        if row is None:
            raise MissingReference(
                "修订不存在: %s" % artifact_revision_id, code="REF_001"
            )
        if row["status"] != "draft":
            raise IllegalTransition(
                "seal_revision 只允许 draft 修订: %s 当前为 %s"
                % (artifact_revision_id, row["status"])
            )
        if not self.objects.verify(row["sha256"]):
            with self.store.transaction():
                self.store.update_revision_status(
                    artifact_revision_id,
                    "draft",
                    "quarantined",
                    "封存前 Object 哈希校验失败",
                    self.actor(),
                )
                self._audit("seal_revision", artifact_revision_id)
            raise HashMismatch(
                "Object 哈希校验失败（SRC_003）: %s" % artifact_revision_id,
                code="SRC_003",
            )
        with self.store.transaction():
            if validation_report_revision_id is not None:
                self._require_sealed(validation_report_revision_id)
            self.store.update_revision_status(
                artifact_revision_id, "draft", "sealed", "封存", self.actor()
            )
            if validation_report_revision_id is not None:
                self.store.conn.execute(
                    "UPDATE artifact_revisions SET validation_report_revision_id=? "
                    "WHERE artifact_revision_id=?",
                    (validation_report_revision_id, artifact_revision_id),
                )
            self._audit("seal_revision", artifact_revision_id)

    def quarantine_revision(
        self, artifact_revision_id, reason, *, validation_report_revision_id=None
    ):
        """``draft`` → ``quarantined``（内容与证据保留，但不得被运行消费）。"""
        validate("artifact_revision_id", artifact_revision_id)
        with self.store.transaction():
            row = self.store.get_revision(artifact_revision_id)
            if row is None:
                raise MissingReference(
                    "修订不存在: %s" % artifact_revision_id, code="REF_001"
                )
            if validation_report_revision_id is not None:
                self._require_sealed(validation_report_revision_id)
            self.store.update_revision_status(
                artifact_revision_id,
                "draft",
                "quarantined",
                reason,
                self.actor(),
            )
            self._audit(
                "quarantine_revision", artifact_revision_id, {"reason": reason}
            )

    def invalidate_revision(self, artifact_revision_id, reason):
        """``sealed`` → ``invalidated``（上游变化，历史保留但新运行不得消费）。"""
        validate("artifact_revision_id", artifact_revision_id)
        with self.store.transaction():
            row = self.store.get_revision(artifact_revision_id)
            if row is None:
                raise MissingReference(
                    "修订不存在: %s" % artifact_revision_id, code="REF_001"
                )
            self.store.update_revision_status(
                artifact_revision_id, "sealed", "invalidated", reason, self.actor()
            )
            self._audit("invalidate_revision", artifact_revision_id, {"reason": reason})

    def supersede_revision(self, old_revision_id, new_revision_id):
        """旧修订 → ``superseded``；新修订必须 sealed、同一 Artifact、prev 指向旧修订。"""
        validate("artifact_revision_id", old_revision_id)
        validate("artifact_revision_id", new_revision_id)
        with self.store.transaction():
            old = self.store.get_revision(old_revision_id)
            new = self.store.get_revision(new_revision_id)
            if old is None or new is None:
                raise MissingReference(
                    "修订不存在: %s" % (old_revision_id if old is None else new_revision_id),
                    code="REF_001",
                )
            if new["status"] != "sealed":
                raise IllegalTransition(
                    "新修订必须已 sealed: %s 当前为 %s"
                    % (new_revision_id, new["status"])
                )
            if new["artifact_id"] != old["artifact_id"]:
                raise IllegalTransition(
                    "只有同一 Artifact 的修订才能取代: %s != %s"
                    % (new["artifact_id"], old["artifact_id"])
                )
            if new["prev_revision_id"] != old_revision_id:
                raise IllegalTransition(
                    "新修订的 prev_revision_id 必须指向被取代的修订: %r != %r"
                    % (new["prev_revision_id"], old_revision_id)
                )
            self.store.update_revision_status(
                old_revision_id,
                old["status"],
                "superseded",
                "被 %s 取代" % new_revision_id,
                self.actor(),
            )
            self._audit(
                "supersede_revision",
                old_revision_id,
                {"new_revision_id": new_revision_id},
            )

    def register_stage_package(
        self,
        step_run_id,
        package,
        data,
        *,
        stage_package_id=None,
        artifact_revision_id=None,
    ):
        """登记一个 StagePackage 逻辑身份与其 draft 修订，返回 ``(包号, 修订号)``。"""
        self._validate("stage_package.schema.json", package, "StagePackage")
        if not isinstance(data, (bytes, bytearray)):
            raise SchemaViolation("data 必须是 bytes", code="SCH_001")
        data = bytes(data)
        stage_package_id = stage_package_id or package["stage_package_id"]
        validate("stage_package_id", stage_package_id)
        artifact_revision_id = artifact_revision_id or package["artifact_revision_id"]
        validate("artifact_revision_id", artifact_revision_id)
        stage = package["stage"]
        if stage_package_id.split("_")[1] != stage:
            raise SchemaViolation(
                "stage_package_id 的 <stage> 与 package.stage 不一致: %s vs %s"
                % (stage_package_id, stage),
                code="SCH_002",
            )
        with self.store.transaction():
            step = self._live_step_run(step_run_id)
            if self.store.get_stage_package(stage_package_id) is not None:
                raise DuplicateIdentifier("StagePackage 已存在: %s" % stage_package_id)
            if self.store.get_revision(artifact_revision_id) is not None:
                raise DuplicateIdentifier("修订已存在: %s" % artifact_revision_id)
            sha256, size = self.objects.put(data)
            actor = self.actor()
            now = utcnow()
            artifact_id = new_id("artifact_id")
            self.store.insert_artifact(artifact_id, "stage_package", now, actor)
            self.store.insert_revision(
                artifact_revision_id,
                artifact_id,
                "draft",
                0,
                sha256,
                size,
                "objects/%s/%s" % (sha256[:2], sha256),
                _LEDGER_PRODUCER,
                _LEDGER_PRODUCER_VERSION,
                "internal",
                now,
                actor,
                schema_id="stage_package",
                schema_version=package["schema_version"],
                processing_run_id=step["processing_run_id"],
                step_run_id=step_run_id,
            )
            self.store.insert_stage_package(stage_package_id, artifact_id, stage)
            self._audit("register_stage_package", stage_package_id)
        return stage_package_id, artifact_revision_id

    # -------------------------------------------------------- Transformation
    def record_transformation(
        self,
        step_run_id,
        *,
        operation,
        tool,
        tool_version,
        configuration_revision_id,
        input_revision_ids,
        output_revision_ids,
        model_ref=None,
        validation_report_revision_id=None,
        human_event_revision_ids=(),
    ):
        """记录一条语义转换（§17 必记：输入、输出、工具/模型、配置、校验、人工决定）。"""
        if not isinstance(operation, str) or not _NAME_RE.match(operation):
            raise SchemaViolation(
                "operation 必须匹配 ^[a-z][a-z0-9_]*$: %r" % (operation,),
                code="SCH_002",
            )
        if not tool or not tool_version:
            raise SchemaViolation("tool 与 tool_version 不能为空", code="SCH_001")
        input_revision_ids = list(input_revision_ids)
        output_revision_ids = list(output_revision_ids)
        human_event_revision_ids = list(human_event_revision_ids)
        with self.store.transaction():
            self._live_step_run(step_run_id)
            self._require_sealed(configuration_revision_id)
            if validation_report_revision_id is not None:
                self._require_sealed(validation_report_revision_id)
            allowed_inputs = set(self._frozen_input_ids(step_run_id)) | set(
                self._own_sealed_revisions(step_run_id)
            )
            for revision_id in input_revision_ids:
                if revision_id not in allowed_inputs:
                    raise IllegalTransition(
                        "输入修订不在冻结输入也不属于本 StepRun 的封存产出: %s"
                        % revision_id
                    )
            own_outputs = set(self._own_sealed_revisions(step_run_id))
            for revision_id in output_revision_ids:
                if revision_id not in own_outputs:
                    raise IllegalTransition(
                        "输出修订必须属于本 StepRun 的封存产出: %s" % revision_id
                    )
            for revision_id in human_event_revision_ids:
                self._require_sealed(revision_id)
                if self._artifact_type(revision_id) != "human_event":
                    raise SchemaViolation(
                        "human_event_revision_ids 只能引用 artifact_type=human_event: %s"
                        % revision_id,
                        code="SCH_002",
                    )
            transformation_id = self.store.insert_transformation(
                step_run_id,
                operation,
                tool,
                tool_version,
                configuration_revision_id,
                input_revision_ids=input_revision_ids,
                output_revision_ids=output_revision_ids,
                human_event_revision_ids=human_event_revision_ids,
                model_ref=model_ref,
                validation_report_revision_id=validation_report_revision_id,
            )
            self._audit("record_transformation", transformation_id)
        return transformation_id

    # -------------------------------------------------------- 人工恢复
    def _pending_queue_from_state(self, step_run_id):
        """取最近一次 ``await_human`` 持久化的待处理队列；没有则空。"""
        rows = [
            event
            for event in self.store.list_step_run_events(step_run_id)
            if event["event_type"] == "await_human"
        ]
        if not rows:
            return []
        payload = json.loads(rows[-1]["payload_json"] or "{}")
        return list(payload.get("pending_queue", []))

    def _check_token(self, step, resume_token):
        """校验 ``resume_token``：必须为当前 ``awaiting_human`` 且哈希与版本都匹配。"""
        if step["status"] != "awaiting_human":
            raise InvalidResumeToken(
                "StepRun %s 不处于 awaiting_human（当前 %s）"
                % (step["step_run_id"], step["status"])
            )
        stored = step["resume_token_hash"]
        if not stored:
            raise InvalidResumeToken("StepRun %s 没有待消费的 resume_token" % step["step_run_id"])
        if not isinstance(resume_token, str):
            raise InvalidResumeToken("resume_token 必须是字符串")
        version_part, _, digest = stored.partition(":")
        if not digest:
            raise InvalidResumeToken("resume_token 记录损坏")
        if hashlib.sha256(resume_token.encode("utf-8")).hexdigest() != digest:
            raise InvalidResumeToken("resume_token 不匹配")
        try:
            bound_version = int(version_part.lstrip("v"))
        except ValueError:
            raise InvalidResumeToken("resume_token 记录的 status_version 损坏")
        if bound_version != step["status_version"]:
            raise InvalidResumeToken(
                "resume_token 与当前 status_version 不匹配: %s != %s"
                % (bound_version, step["status_version"])
            )

    def await_human(self, step_run_id, pending_queue_revision_ids):
        """``running`` → ``awaiting_human``，返回单次使用的 ``resume_token``（DB 只存哈希）。"""
        pending_queue_revision_ids = list(pending_queue_revision_ids)
        token = secrets.token_urlsafe(32)
        with self.store.transaction():
            step = self.store.get_step_run(step_run_id)
            if step is None:
                raise MissingReference(
                    "StepRun 不存在: %s" % step_run_id, code="REF_001"
                )
            check_step_run_transition(step["status"], "awaiting_human")
            for revision_id in pending_queue_revision_ids:
                self._require_sealed(revision_id)
            bound_version = step["status_version"] + 1
            self.store.update_step_run_status(
                step_run_id,
                "running",
                "awaiting_human",
                step["status_version"],
                fields={"resume_token_hash": _token_hash(token, bound_version)},
            )
            payload = {
                "frozen_inputs": self._frozen_input_ids(step_run_id),
                "pending_queue": pending_queue_revision_ids,
                "human_events": self._human_event_ids(step_run_id),
            }
            self.store.append_step_run_event(
                step_run_id,
                "await_human",
                self.actor(),
                from_status="running",
                to_status="awaiting_human",
                payload_json=json.dumps(payload, sort_keys=True, ensure_ascii=False),
            )
            self._audit("await_human", step_run_id)
        return token

    def record_human_event(
        self, step_run_id, resume_token, event_artifact_revision_id, *, decision_type=None
    ):
        """把一条不可变人工事件写入 Ledger；**不消费** ``resume_token``。"""
        if decision_type is not None and decision_type not in REVIEW_DECISION_TYPES:
            raise SchemaViolation(
                "decision_type 不在 §8.2 第 2 表: %r" % (decision_type,),
                code="SCH_002",
            )
        validate("artifact_revision_id", event_artifact_revision_id)
        with self.store.transaction():
            step = self.store.get_step_run(step_run_id)
            if step is None:
                raise MissingReference(
                    "StepRun 不存在: %s" % step_run_id, code="REF_001"
                )
            self._check_token(step, resume_token)
            self._require_sealed(event_artifact_revision_id)
            if self._artifact_type(event_artifact_revision_id) != "human_event":
                raise SchemaViolation(
                    "事件修订的 artifact_type 必须为 human_event: %s"
                    % event_artifact_revision_id,
                    code="SCH_002",
                )
            self.store.insert_human_event(
                event_artifact_revision_id, step_run_id, decision_type
            )
            self.store.append_step_run_event(
                step_run_id,
                "human_event",
                self.actor(),
                payload_json=json.dumps(
                    {
                        "event_revision_id": event_artifact_revision_id,
                        "decision_type": decision_type,
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                ),
            )
            self._audit("record_human_event", step_run_id)
        return None

    def resume(self, step_run_id, resume_token):
        """原子消费 ``resume_token``：``awaiting_human`` → ``running``，哈希置 NULL。"""
        with self.store.transaction():
            step = self.store.get_step_run(step_run_id)
            if step is None:
                raise MissingReference(
                    "StepRun 不存在: %s" % step_run_id, code="REF_001"
                )
            self._check_token(step, resume_token)
            self.store.update_step_run_status(
                step_run_id,
                "awaiting_human",
                "running",
                step["status_version"],
                fields={"resume_token_hash": None},
            )
            self.store.append_step_run_event(
                step_run_id,
                "resume",
                self.actor(),
                from_status="awaiting_human",
                to_status="running",
            )
            self._audit("resume", step_run_id)
        return None

    def suspend(self, step_run_id, reason, source):
        """``running``|``awaiting_human`` → ``suspended``，并持久化原因、来源、输入与队列。"""
        if source not in SUSPEND_SOURCES:
            raise SchemaViolation(
                "source 必须为 %s: %r" % ("/".join(SUSPEND_SOURCES), source),
                code="SCH_002",
            )
        with self.store.transaction():
            step = self.store.get_step_run(step_run_id)
            if step is None:
                raise MissingReference(
                    "StepRun 不存在: %s" % step_run_id, code="REF_001"
                )
            check_step_run_transition(step["status"], "suspended")
            pending_queue = (
                self._pending_queue_from_state(step_run_id)
                if step["status"] == "awaiting_human"
                else []
            )
            self.store.update_step_run_status(
                step_run_id, step["status"], "suspended", step["status_version"]
            )
            payload = {
                "reason": reason,
                "source": source,
                "frozen_inputs": self._frozen_input_ids(step_run_id),
                "pending_queue": pending_queue,
                "human_events": self._human_event_ids(step_run_id),
            }
            self.store.append_step_run_event(
                step_run_id,
                "suspended",
                self.actor(),
                from_status=step["status"],
                to_status="suspended",
                reason=reason,
                source=source,
                payload_json=json.dumps(payload, sort_keys=True, ensure_ascii=False),
            )
            self._audit("suspend", step_run_id, {"reason": reason, "source": source})
        return None

    def recover(self, step_run_id, reason):
        """对账后从 ``suspended`` 回到 ``running``（或 ``awaiting_human``，保留 token）。"""
        with self.store.transaction():
            step = self.store.get_step_run(step_run_id)
            if step is None:
                raise MissingReference(
                    "StepRun 不存在: %s" % step_run_id, code="REF_001"
                )
            if step["status"] in TERMINAL_STEP_RUN:
                raise IllegalTransition(
                    "StepRun %s 已是终态 %s，不得改写"
                    % (step_run_id, step["status"])
                )
            if step["status"] != "suspended":
                raise IllegalTransition(
                    "recover 只允许 suspended 状态: %s 当前为 %s"
                    % (step_run_id, step["status"])
                )
            suspended_events = [
                event
                for event in self.store.list_step_run_events(step_run_id)
                if event["event_type"] == "suspended"
            ]
            previous_status = (
                suspended_events[-1]["from_status"] if suspended_events else "running"
            )
            target = "awaiting_human" if previous_status == "awaiting_human" else "running"
            fields = None
            if target == "awaiting_human" and step["resume_token_hash"]:
                # 按新版本重新锚定 token 前缀，使 token 在往返后仍有效（BDD 3.3）
                fields = {
                    "resume_token_hash": "v%d:%s"
                    % (step["status_version"] + 1, _token_digest(step["resume_token_hash"]))
                }
            self.store.update_step_run_status(
                step_run_id, "suspended", target, step["status_version"], fields=fields
            )
            self.store.append_step_run_event(
                step_run_id,
                "recovery",
                self.actor(),
                from_status="suspended",
                to_status=target,
                reason=reason,
            )
            self._audit("recover", step_run_id, {"reason": reason})
            return target

    # ------------------------------------------------- 终态与 StepManifest
    def _seal_step_manifest(self, step_run_id, result):
        """生成并封存 StepManifest 修订，返回其 ``artifact_revision_id``（同事务内）。"""
        step = self.store.get_step_run(step_run_id)
        edition_part_id = self._edition_part_id(step["processing_run_id"])
        latest = (
            self.store.latest_checkpoint(edition_part_id, step["stage"])
            if edition_part_id
            else None
        )
        actor = self.actor()
        now = utcnow()
        content = {
            "step_run_id": step_run_id,
            "request": json.loads(step["request_json"]),
            "result": result,
            "frozen_inputs": self._frozen_input_ids(step_run_id),
            "transformation_ids": [
                row["id"] for row in self.store.list_transformations(step_run_id)
            ],
            "last_checkpoint_revision_id": (
                latest["artifact_revision_id"] if latest else None
            ),
            "sealed_at": now,
        }
        data = json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")
        sha256, size = self.objects.put(data)
        artifact_id = new_id("artifact_id")
        artifact_revision_id = new_id("artifact_revision_id")
        self.store.insert_artifact(artifact_id, "step_manifest", now, actor)
        self.store.insert_revision(
            artifact_revision_id,
            artifact_id,
            "draft",
            0,
            sha256,
            size,
            "objects/%s/%s" % (sha256[:2], sha256),
            _LEDGER_PRODUCER,
            _LEDGER_PRODUCER_VERSION,
            "internal",
            now,
            actor,
            schema_id="step_manifest",
            schema_version=(result or {}).get("schema_version"),
            processing_run_id=step["processing_run_id"],
            step_run_id=step_run_id,
        )
        self._seal_ledger_revision(artifact_revision_id, "封存 StepManifest")
        return artifact_revision_id

    def finish_step_run(self, step_run_id, result):
        """校验 StepResult、``running`` → ``succeeded``、写 result_json 并封存 StepManifest。"""
        self._validate("step_result.schema.json", result, "StepResult")
        if result.get("status") != "succeeded":
            raise IllegalTransition(
                "finish_step_run 只接受 status='succeeded' 的 StepResult: %r"
                % (result.get("status"),)
            )
        with self.store.transaction():
            step = self.store.get_step_run(step_run_id)
            if step is None:
                raise MissingReference(
                    "StepRun 不存在: %s" % step_run_id, code="REF_001"
                )
            if result.get("step_run_id") != step_run_id:
                raise SchemaViolation(
                    "StepResult.step_run_id 与目标 StepRun 不一致: %r"
                    % (result.get("step_run_id"),),
                    code="SCH_001",
                )
            for key in (
                "output_artifact_ids",
                "validation_report_ids",
                "log_artifact_ids",
            ):
                for revision_id in result[key]:
                    row = self._require_sealed(revision_id)
                    if row["step_run_id"] != step_run_id:
                        raise IllegalTransition(
                            "StepResult.%s 引用了不属于本 StepRun 的修订: %s"
                            % (key, revision_id)
                        )
            check_step_run_transition(step["status"], "succeeded")
            self.store.update_step_run_status(
                step_run_id,
                step["status"],
                "succeeded",
                step["status_version"],
                fields={
                    "result_json": json.dumps(
                        result, sort_keys=True, ensure_ascii=False
                    )
                },
            )
            self.store.append_step_run_event(
                step_run_id,
                "transition",
                self.actor(),
                from_status=step["status"],
                to_status="succeeded",
            )
            manifest_revision_id = self._seal_step_manifest(step_run_id, result)
            self._audit("finish_step_run", step_run_id)
        return manifest_revision_id

    def fail_step_run(self, step_run_id, failure_revision_ids, reason):
        """``running``|``awaiting_human``|``suspended`` → ``failed``，失败修订保持封存。"""
        failure_revision_ids = list(failure_revision_ids)
        with self.store.transaction():
            step = self.store.get_step_run(step_run_id)
            if step is None:
                raise MissingReference(
                    "StepRun 不存在: %s" % step_run_id, code="REF_001"
                )
            check_step_run_transition(step["status"], "failed")
            for revision_id in failure_revision_ids:
                self._require_sealed(revision_id)
            self.store.update_step_run_status(
                step_run_id, step["status"], "failed", step["status_version"]
            )
            self.store.append_step_run_event(
                step_run_id,
                "failure",
                self.actor(),
                from_status=step["status"],
                to_status="failed",
                reason=reason,
                payload_json=json.dumps(
                    {"failure_revision_ids": failure_revision_ids},
                    sort_keys=True,
                    ensure_ascii=False,
                ),
            )
            self._seal_step_manifest(step_run_id, None)
            self._audit("fail_step_run", step_run_id, {"reason": reason})
        return None

    # -------------------------------------------------------- Checkpoint
    def _stage_sealed_by_finished_run(self, edition_part_id, stage):
        """返回该 (EditionPart, Stage) 上已 ``succeeded`` 的 StepRun 号列表。"""
        rows = self.store.conn.execute(
            "SELECT DISTINCT c.step_run_id FROM stage_checkpoints c "
            "JOIN step_runs r ON r.step_run_id = c.step_run_id "
            "WHERE c.edition_part_id=? AND c.stage=? AND r.status='succeeded'",
            (edition_part_id, stage),
        ).fetchall()
        return [row[0] for row in rows]

    def _supersedes_chain_reaches(self, step_run_id, target_step_run_id):
        """``step_run_id`` 是否经 ``supersedes_step_run_id`` 链（含自身）指向目标。"""
        seen = set()
        current = step_run_id
        while current is not None and current not in seen:
            if current == target_step_run_id:
                return True
            seen.add(current)
            row = self.store.get_step_run(current)
            current = row["supersedes_step_run_id"] if row else None
        return False

    def _write_checkpoint_locked(
        self,
        step_run_id,
        edition_part_id,
        stage,
        completed_tasks,
        human_decisions,
        pending_queue,
        next_pointer,
        rework_impact_report_revision_id,
        artifact_id,
        artifact_revision_id,
    ):
        """在已开启的事务内落盘一个 StageCheckpoint（内容 JSON 进 Object Store）。"""
        step = self._live_step_run(step_run_id)
        if step["stage"] != stage:
            raise IllegalTransition(
                "Checkpoint 的 stage 与 StepRun 不一致: %s != %s"
                % (stage, step["stage"])
            )
        for item in completed_tasks:
            for key in ("task_id", "artifact_revision_id", "status"):
                if key not in item:
                    raise SchemaViolation(
                        "completed_tasks 缺字段 %s" % key, code="SCH_001"
                    )
            if item["status"] not in ("succeeded", "failed"):
                raise SchemaViolation(
                    "completed_tasks.status 必须为 succeeded/failed: %r"
                    % (item["status"],),
                    code="SCH_002",
                )
            if self.store.get_revision(item["artifact_revision_id"]) is None:
                raise MissingReference(
                    "completed_tasks 引用的修订不存在: %s"
                    % item["artifact_revision_id"],
                    code="REF_001",
                )
        for finished in self._stage_sealed_by_finished_run(edition_part_id, stage):
            if not self._supersedes_chain_reaches(step_run_id, finished):
                raise IllegalTransition(
                    "阶段 %s 已被 succeeded StepRun %s 封存，只有 supersedes 它的新运行可续写"
                    % (stage, finished)
                )
        if rework_impact_report_revision_id is not None:
            self._require_sealed(rework_impact_report_revision_id)
        previous = self.store.latest_checkpoint(edition_part_id, stage)
        previous_revision_id = (
            previous["artifact_revision_id"] if previous else None
        )
        actor = self.actor()
        now = utcnow()
        artifact_id = self._new_or_explicit(
            "artifact_id",
            artifact_id,
            "SELECT 1 FROM artifacts WHERE artifact_id=?",
        )
        artifact_revision_id = self._new_or_explicit(
            "artifact_revision_id",
            artifact_revision_id,
            "SELECT 1 FROM artifact_revisions WHERE artifact_revision_id=?",
        )
        content = {
            "edition_part_id": edition_part_id,
            "stage": stage,
            "step_run_id": step_run_id,
            "completed_tasks": list(completed_tasks),
            "human_decisions": list(human_decisions),
            "pending_queue": list(pending_queue),
            "next_pointer": next_pointer,
            "actor_ref": actor,
            "created_at": now,
            "prev_checkpoint_revision_id": previous_revision_id,
            "rework_impact_report_revision_id": rework_impact_report_revision_id,
        }
        data = json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")
        sha256, size = self.objects.put(data)
        self.store.insert_artifact(artifact_id, "stage_checkpoint", now, actor)
        self.store.insert_revision(
            artifact_revision_id,
            artifact_id,
            "draft",
            0,
            sha256,
            size,
            "objects/%s/%s" % (sha256[:2], sha256),
            _LEDGER_PRODUCER,
            _LEDGER_PRODUCER_VERSION,
            "internal",
            now,
            actor,
            schema_id="stage_checkpoint",
            schema_version="1.0.0",
            processing_run_id=step["processing_run_id"],
            step_run_id=step_run_id,
            prev_revision_id=previous_revision_id,
        )
        # StageCheckpoint 直接 sealed（§17.1：落盘即封存）
        self._seal_ledger_revision(artifact_revision_id, "Checkpoint 落盘")
        self.store.insert_checkpoint(
            artifact_revision_id,
            artifact_id,
            edition_part_id,
            stage,
            step_run_id,
            actor,
            now,
            prev_checkpoint_revision_id=previous_revision_id,
            rework_impact_report_revision_id=rework_impact_report_revision_id,
        )
        self.store.append_step_run_event(
            step_run_id,
            "checkpoint",
            actor,
            payload_json=json.dumps(
                {"checkpoint_revision_id": artifact_revision_id},
                sort_keys=True,
                ensure_ascii=False,
            ),
        )
        return artifact_revision_id

    def write_checkpoint(
        self,
        step_run_id,
        *,
        edition_part_id,
        stage,
        completed_tasks,
        human_decisions,
        pending_queue,
        next_pointer,
        rework_impact_report_revision_id=None,
        artifact_id=None,
        artifact_revision_id=None,
    ):
        """每完成一个 task 落盘一个 StageCheckpoint，返回其 ``artifact_revision_id``。"""
        validate("artifact_id", edition_part_id)
        if stage not in STAGES:
            raise SchemaViolation(
                "stage 必须是 §8.1 闭集 m1–m8: %r" % (stage,), code="SCH_002"
            )
        with self.store.transaction():
            checkpoint_revision_id = self._write_checkpoint_locked(
                step_run_id,
                edition_part_id,
                stage,
                completed_tasks,
                human_decisions,
                pending_queue,
                next_pointer,
                rework_impact_report_revision_id,
                artifact_id,
                artifact_revision_id,
            )
            self._audit("write_checkpoint", checkpoint_revision_id)
        return checkpoint_revision_id

    def _backfill_checkpoint_if_needed(self, checkpoint, edition_part_id, stage):
        """最后人工事件晚于该 Checkpoint 时先补写一个 Checkpoint（§17.1 恢复语义）。"""
        owner_step_run_id = checkpoint["step_run_id"]
        accepted = [
            event
            for event in self.store.list_step_run_events(owner_step_run_id)
            if event["event_type"] == "human_event"
        ]
        if not accepted:
            return checkpoint
        if accepted[-1]["created_at"] <= checkpoint["created_at"]:
            return checkpoint
        content = dict(checkpoint["content"])
        content["human_decisions"] = self._human_event_ids(owner_step_run_id)
        with self.store.transaction():
            backfilled = self._write_checkpoint_locked(
                owner_step_run_id,
                edition_part_id,
                stage,
                content["completed_tasks"],
                content["human_decisions"],
                content["pending_queue"],
                content["next_pointer"],
                content["rework_impact_report_revision_id"],
                None,
                None,
            )
            self._audit("write_checkpoint", backfilled, {"backfill": True})
        return self.latest_checkpoint(edition_part_id, stage)

    def recover_from_checkpoint(
        self, edition_part_id, stage, new_request, *, step_run_id=None
    ):
        """从最近 StageCheckpoint 恢复：建新 StepRun（supersedes 原运行）并返回恢复计划。"""
        validate("artifact_id", edition_part_id)
        if stage not in STAGES:
            raise SchemaViolation(
                "stage 必须是 §8.1 闭集 m1–m8: %r" % (stage,), code="SCH_002"
            )
        checkpoint = self.latest_checkpoint(edition_part_id, stage)
        if checkpoint is None:
            raise MissingReference(
                "没有可恢复的 StageCheckpoint: %s / %s" % (edition_part_id, stage),
                code="REF_001",
            )
        checkpoint = self._backfill_checkpoint_if_needed(
            checkpoint, edition_part_id, stage
        )
        content = checkpoint["content"]
        plan = {
            "checkpoint_revision_id": checkpoint["artifact_revision_id"],
            "completed_task_ids": [
                item["task_id"]
                for item in content["completed_tasks"]
                if item.get("status") == "succeeded"
            ],
            "human_decisions": list(content["human_decisions"]),
            "pending_queue": list(content["pending_queue"]),
            "next_pointer": content["next_pointer"],
        }
        owner_step_run_id = checkpoint["step_run_id"]
        with self.store.transaction():
            new_step_run_id = self._begin_step_run_locked(
                new_request,
                step_run_id,
                supersedes_step_run_id=owner_step_run_id,
            )
            self.store.append_step_run_event(
                new_step_run_id,
                "recovery",
                self.actor(),
                payload_json=json.dumps(
                    {"checkpoint_revision_id": checkpoint["artifact_revision_id"]},
                    sort_keys=True,
                    ensure_ascii=False,
                ),
            )
            self._audit(
                "recover_from_checkpoint",
                new_step_run_id,
                {"checkpoint_revision_id": checkpoint["artifact_revision_id"]},
            )
        return new_step_run_id, plan


# ------------------------------------------------------------------ 只读聚合
def _load_run(store, processing_run_id):
    row = store.conn.execute(
        "SELECT * FROM processing_runs WHERE processing_run_id=?",
        (processing_run_id,),
    ).fetchone()
    if row is None:
        raise MissingReference(
            "ProcessingRun 不存在: %s" % processing_run_id, code="REF_001"
        )
    return dict(row)


def _load_step_runs(store, processing_run_id):
    rows = store.conn.execute(
        "SELECT * FROM step_runs WHERE processing_run_id=? ORDER BY created_at, rowid",
        (processing_run_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _has_successor(store, step_run_id):
    """是否存在以 ``supersedes_step_run_id`` 指向该运行的后续 StepRun。"""
    return (
        store.conn.execute(
            "SELECT 1 FROM step_runs WHERE supersedes_step_run_id=? LIMIT 1",
            (step_run_id,),
        ).fetchone()
        is not None
    )


def _aggregate_status(store, step_runs):
    """按 §17 的语义聚合 ProcessingRun 状态。"""
    if not step_runs:
        return "running"
    if all(step["status"] == "succeeded" for step in step_runs):
        return "succeeded"
    if any(
        step["status"] == "failed" and not _has_successor(store, step["step_run_id"])
        for step in step_runs
    ):
        return "failed"
    pending = [
        step["status"]
        for step in step_runs
        if step["status"] not in TERMINAL_STEP_RUN
    ]
    if pending:
        return pending[-1]
    return "succeeded"


def _run_status(store, processing_run_id):
    run = _load_run(store, processing_run_id)
    step_runs = _load_step_runs(store, processing_run_id)
    finished = [
        step["updated_at"]
        for step in step_runs
        if step["status"] in TERMINAL_STEP_RUN
    ]
    all_terminal = bool(step_runs) and len(finished) == len(step_runs)
    return {
        "processing_run_id": processing_run_id,
        "status": _aggregate_status(store, step_runs),
        "started_at": min(
            [step["created_at"] for step in step_runs] or [run["created_at"]]
        ),
        "finished_at": max(finished) if all_terminal and finished else None,
        "step_runs": step_runs,
    }


def _stage_progress(store, processing_run_id):
    run = _load_run(store, processing_run_id)
    step_runs = _load_step_runs(store, processing_run_id)
    progress = {}
    for step in step_runs:
        entry = progress.setdefault(
            step["stage"],
            {
                "step_runs": 0,
                "succeeded": 0,
                "failed": 0,
                "running": 0,
                "awaiting_human": 0,
                "suspended": 0,
                "superseded": 0,
                "last_checkpoint_revision_id": None,
            },
        )
        entry["step_runs"] += 1
        if step["status"] in entry:
            entry[step["status"]] += 1
    for stage, entry in progress.items():
        latest = store.latest_checkpoint(run["edition_part_id"], stage)
        entry["last_checkpoint_revision_id"] = (
            latest["artifact_revision_id"] if latest else None
        )
    return progress


class LedgerReader(LedgerReadMixin):
    """Ledger 只读 API：``mode=ro`` 打开，不取写锁，可与写入者并发查询（规格 §17）。"""

    def __init__(self, root):
        self.root = Path(root)
        self.store = MetadataStore.open_readonly(self.root / "ledger.sqlite")
        self.objects = ObjectStore(self.root)

    def close(self):
        """关闭只读连接（幂等）。"""
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

