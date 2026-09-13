"""m4 assemble StepRun（``run_m4``）：冻结输入、每 task 一个 Checkpoint、分歧转人工、Gate、
``candidate_set`` / ``candidate_package`` / m4 StagePackage。

``begin_step_run`` 之前拒绝原样外抛且不得写入；之后分 ``input_contract`` /
``assemble`` / ``candidate_gate`` / ``internal`` 失败封存。同阶段第 2 个及以后的运行
以 ``supersede_step_run`` 接替最近一个 succeeded 运行（G7-RULINGS 第 32/58 条）。
"""

import hashlib
import json

import yaml

from pipeline.ledger import ids
from pipeline.ledger.errors import SchemaViolation

from . import (
    CANDIDATE_SCHEMA_VERSION,
    CATEGORIES,
    M4_TOOL,
    M4_TOOL_VERSION,
)
from . import assemble, gate
from .errors import ExtractionRefused
from .inputs import resolve_m4_inputs
from .serialize import canonical_json
from .submission import validate_submission
from .submit import begin_m4_step_run

# assemble 配置缺省（README §6.7）
DEFAULT_ID_RANGE = {"assertion": [1, 99], "proposition": [1, 99], "pattern": [1, 99]}
DEFAULT_REQUIRED_LANES = {
    "assertion": ["a", "b"],
    "pattern": ["a", "b"],
    "school_view": ["a", "b"],
    "concept_mention": ["a"],
}

GATE_PROFILE = "thin_no_model"
SPAN_LAYER = "structural"
CROSS_MODEL = "not_evaluated"
TERM_LAYERING = "verify_only"

# 类别裁决选择闭集（§6.4(a)）
RULING_CHOICES = ("a", "b", "both", "neither")


class _InputContractError(Exception):
    """begin 之后输入契约不满足（检查名 ``input_contract``）。"""


def _submission_sort_key(key):
    category, lane = key.split("/")
    return (CATEGORIES.index(category), lane)


def _artifact_types(service, revision_ids):
    revision_ids = [rev for rev in revision_ids if rev]
    if not revision_ids:
        return {}
    placeholders = ",".join("?" * len(revision_ids))
    rows = service.store.conn.execute(
        "SELECT r.artifact_revision_id, a.artifact_type FROM artifact_revisions r "
        "JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "WHERE r.artifact_revision_id IN (%s)" % placeholders,
        tuple(revision_ids),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _read_bytes(service, revision_id):
    row = service.get_revision(revision_id)
    if row is None:
        raise _InputContractError("引用的修订不存在: %s" % revision_id)
    read = getattr(service, "read_object", None)
    if read is not None:
        return read(row["sha256"])
    return service.objects.get(row["sha256"])


def _read_doc(service, revision_id):
    try:
        return json.loads(_read_bytes(service, revision_id).decode("utf-8"))
    except ValueError:
        return yaml.safe_load(_read_bytes(service, revision_id).decode("utf-8"))


def _artifact_ref(service, revision_id):
    """构造过 ``artifact_ref.schema.json`` 的引用（stage_package 用包号身份）。"""
    row = service.store.conn.execute(
        "SELECT a.artifact_id, a.artifact_type FROM artifacts a "
        "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
        "WHERE r.artifact_revision_id=?",
        (revision_id,),
    ).fetchone()
    artifact_id, artifact_type = row[0], row[1]
    if artifact_type == "stage_package":
        package_row = service.store.conn.execute(
            "SELECT sp.stage_package_id FROM stage_packages sp "
            "JOIN artifact_revisions r ON r.artifact_id = sp.artifact_id "
            "WHERE r.artifact_revision_id=?",
            (revision_id,),
        ).fetchone()
        return {
            "schema_version": "1.0.0",
            "artifact_kind": "stage_package",
            "stage_package_id": package_row[0],
            "artifact_revision_id": revision_id,
            "artifact_type": artifact_type,
        }
    return {
        "schema_version": "1.0.0",
        "artifact_kind": "artifact",
        "artifact_id": artifact_id,
        "artifact_revision_id": revision_id,
        "artifact_type": artifact_type,
    }


def _build_ctx(service, step_run_id, inputs, config_content):
    """按冻结输入重建装配上下文（只读）；不满足输入契约时抛 ``_InputContractError``。"""
    technique_id = inputs["technique_id"]
    spans_revision_id = inputs["spans_revision_id"]
    spans_bytes = _read_bytes(service, spans_revision_id)
    spans_doc = yaml.safe_load(spans_bytes.decode("utf-8"))
    package = _read_doc(service, inputs["corpus_stage_package_revision_id"])
    if not isinstance(package, dict):
        raise _InputContractError("M3 包不可解析")
    if hashlib.sha256(spans_bytes).hexdigest() != (package.get("manifest") or {}).get(
        "content_sha256"
    ):
        raise _InputContractError("corpus_spans 哈希与 M3 包 manifest.content_sha256 不符")
    if (package.get("payload") or {}).get("spans_revision_id") != spans_revision_id:
        raise _InputContractError("M3 包 payload.spans_revision_id 与冻结输入不符")
    profile = json.loads(
        _read_bytes(service, inputs["technique_profile_revision_id"]).decode("utf-8")
    )
    if profile.get("technique_id") != technique_id:
        raise _InputContractError("technique_profile.technique_id 不符")

    lane_results = {}
    lane_set_bytes = {}
    for key in sorted(inputs["submissions"], key=_submission_sort_key):
        row = inputs["submissions"][key]
        doc = validate_submission(
            json.loads(_read_bytes(service, row["revision_id"]).decode("utf-8")),
            technique_id=technique_id,
        )
        if "%s/%s" % (doc["category"], doc["lane"]) != key:
            raise _InputContractError("提交件 category/lane 与 inputs 键不符: %s" % key)
        lane = assemble.normalize_lane(doc, spans_doc=spans_doc, profile=profile)
        lane_results.setdefault(doc["category"], {})[doc["lane"]] = lane
        lane_set_bytes[key] = canonical_json(lane)

    return {
        "spans_doc": spans_doc,
        "profile": profile,
        "lane_results": lane_results,
        "lane_set_bytes": lane_set_bytes,
        "submission_revision_ids": {
            key: row["revision_id"] for key, row in inputs["submissions"].items()
        },
        "inputs": inputs,
        "processing_run_id": inputs["processing_run_id"],
        "technique_id": technique_id,
    }


def _fail(service, step_run_id, check, detail):
    """失败封存：put failure_report → seal → fail_step_run；返回失败 summary。"""
    _, failure_revision_id = service.put_artifact(
        step_run_id,
        "failure_report",
        canonical_json({"check": check, "detail": detail}),
        producer_module=M4_TOOL,
        producer_version=M4_TOOL_VERSION,
    )
    service.seal_revision(failure_revision_id)
    service.fail_step_run(
        step_run_id, [failure_revision_id], "M4 %s: %s" % (check, detail)
    )
    return {
        "status": "failed",
        "step_run_id": step_run_id,
        "failed_check": check,
        "failure_revision_id": failure_revision_id,
        "reason": detail,
    }


def _complete(service, step_run_id, ctx, rulings=None, human_event_revision_ids=None):
    """装配候选、写 candidate_set/candidate_package 与 m4 StagePackage（ACT 04/05 共用）。"""
    rulings = dict(rulings or {})
    human_event_revision_ids = list(human_event_revision_ids or [])
    try:
        result = assemble.assemble_candidates(
            spans_doc=ctx["spans_doc"],
            profile=ctx["profile"],
            lane_results=ctx["lane_results"],
            required_lanes=ctx["required_lanes"],
            rulings=rulings,
            id_range=ctx["id_range"],
            id_factory=ctx.get("id_factory"),
        )
    except ExtractionRefused as exc:
        return _fail(service, step_run_id, "assemble", str(exc))

    _, candidate_set_revision_id = service.put_artifact(
        step_run_id,
        "candidate_set",
        result["candidate_bytes"],
        producer_module=M4_TOOL,
        producer_version=M4_TOOL_VERSION,
    )
    service.seal_revision(candidate_set_revision_id)
    checkpoint_revision_ids = [
        service.write_checkpoint(
            step_run_id,
            edition_part_id=ctx["edition_part_id"],
            stage="m4",
            completed_tasks=[
                {
                    "task_id": "assemble",
                    "artifact_revision_id": candidate_set_revision_id,
                    "status": "succeeded",
                    "terminal_state": None,
                }
            ],
            human_decisions=human_event_revision_ids,
            pending_queue=[],
            next_pointer=None,
        )
    ]

    gate_report = gate.evaluate_candidates(
        spans_doc=ctx["spans_doc"],
        profile=ctx["profile"],
        candidate_set=result["candidate_set"],
        config=ctx["config"],
    )
    _, validation_report_revision_id = service.put_artifact(
        step_run_id,
        "validation_report",
        canonical_json(gate_report),
        producer_module=M4_TOOL,
        producer_version=M4_TOOL_VERSION,
    )
    service.seal_revision(validation_report_revision_id)
    _, log_revision_id = service.put_artifact(
        step_run_id,
        "step_log",
        (
            "extract_candidates assertions=%d disputes=%d"
            % (
                result["candidate_set"]["counts"]["assertions"],
                result["candidate_set"]["counts"]["disputes"],
            )
        ).encode("utf-8"),
        producer_module=M4_TOOL,
        producer_version=M4_TOOL_VERSION,
    )
    service.seal_revision(log_revision_id)
    if gate_report["structural"] == "failed":
        return _fail(
            service, step_run_id, "candidate_gate", ",".join(gate_report["failed_checks"])
        )

    package_content = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "candidate_set_revision_id": candidate_set_revision_id,
        "candidate_set_sha256": result["candidate_sha256"],
        "lane_set_revision_ids": ctx["lane_set_revision_ids"],
        "submission_revision_ids": ctx["submission_revision_ids"],
        "dispute_queue_revision_id": ctx["dispute_queue_revision_id"],
        "human_event_revision_ids": human_event_revision_ids,
        "corpus_stage_package_revision_id": ctx["inputs"]["corpus_stage_package_revision_id"],
        "spans_revision_id": ctx["inputs"]["spans_revision_id"],
        "technique_profile_revision_id": ctx["inputs"]["technique_profile_revision_id"],
        "gate_profile": GATE_PROFILE,
        "span_layer": SPAN_LAYER,
        "cross_model": CROSS_MODEL,
        "term_layering": TERM_LAYERING,
    }
    _, candidate_package_revision_id = service.put_artifact(
        step_run_id,
        "candidate_package",
        canonical_json(package_content),
        producer_module=M4_TOOL,
        producer_version=M4_TOOL_VERSION,
    )
    service.seal_revision(candidate_package_revision_id)

    transformation_id = service.record_transformation(
        step_run_id,
        operation="extract_candidates",
        tool=M4_TOOL,
        tool_version=M4_TOOL_VERSION,
        configuration_revision_id=ctx["configuration_revision_id"],
        input_revision_ids=ctx["frozen"],
        output_revision_ids=[candidate_package_revision_id, candidate_set_revision_id],
        validation_report_revision_id=validation_report_revision_id,
        human_event_revision_ids=human_event_revision_ids,
        model_ref=None,
    )

    stage_package_id = ids.new_id("stage_package_id", stage="m4")
    package_revision_id = ids.new_id("artifact_revision_id")
    m3_package_revision_id = ctx["inputs"]["corpus_stage_package_revision_id"]
    spans_revision_id = ctx["inputs"]["spans_revision_id"]
    technique_profile_revision_id = ctx["inputs"]["technique_profile_revision_id"]
    package = {
        "schema_version": "1.0.0",
        "stage_package_id": stage_package_id,
        "artifact_revision_id": package_revision_id,
        "stage": "m4",
        "status": "sealed",
        "payload": {
            "candidate_set_revision_id": candidate_set_revision_id,
            "corpus_stage_package_revision_id": m3_package_revision_id,
            "spans_revision_id": spans_revision_id,
            "technique_profile_revision_id": technique_profile_revision_id,
            "gate_profile": GATE_PROFILE,
            "span_layer": SPAN_LAYER,
            "cross_model": CROSS_MODEL,
            "term_layering": TERM_LAYERING,
            "content_status_counts": result["content_status_counts"],
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": ctx["processing_run_id"],
            "step_run_id": step_run_id,
            "input_artifacts": [_artifact_ref(service, rev) for rev in ctx["frozen"]],
            "output_artifacts": [_artifact_ref(service, candidate_package_revision_id)],
            "counts": result["candidate_set"]["counts"],
            "content_sha256": result["candidate_sha256"],
        },
        "validation": {
            "passed": True,
            "report_artifacts": [_artifact_ref(service, validation_report_revision_id)],
        },
        "lineage": {
            "upstream_artifacts": [
                _artifact_ref(service, m3_package_revision_id),
                _artifact_ref(service, spans_revision_id),
                _artifact_ref(service, technique_profile_revision_id),
            ],
            "transformations": [
                {
                    "operation": "extract_candidates",
                    "step_run_id": step_run_id,
                    "configuration_artifact_revision_id": ctx["configuration_revision_id"],
                    "input_artifact_revision_ids": list(ctx["frozen"]),
                    "output_artifact_revision_ids": [
                        candidate_package_revision_id,
                        candidate_set_revision_id,
                    ],
                }
            ],
        },
        "logs": [_artifact_ref(service, log_revision_id)],
        "failures": [],
    }
    service.register_stage_package(
        step_run_id,
        package,
        canonical_json(package),
        stage_package_id=stage_package_id,
        artifact_revision_id=package_revision_id,
    )
    service.seal_revision(package_revision_id)

    version = service.get_step_run(step_run_id)["status_version"]
    step_manifest_revision_id = service.finish_step_run(
        step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": ctx["processing_run_id"],
            "step_run_id": step_run_id,
            "status_version": version + 1,
            "status": "succeeded",
            "output_artifact_ids": [
                package_revision_id,
                candidate_set_revision_id,
                candidate_package_revision_id,
            ],
            "validation_report_ids": [validation_report_revision_id],
            "log_artifact_ids": [log_revision_id],
            "failure_artifact_ids": [],
        },
    )
    return {
        "status": "succeeded",
        "processing_run_id": ctx["processing_run_id"],
        "step_run_id": step_run_id,
        "configuration_revision_id": ctx["configuration_revision_id"],
        "frozen_input_revision_ids": list(ctx["frozen"]),
        "stage_package_id": stage_package_id,
        "package_revision_id": package_revision_id,
        "candidate_package_revision_id": candidate_package_revision_id,
        "candidate_set_revision_id": candidate_set_revision_id,
        "candidate_sha256": result["candidate_sha256"],
        "lane_set_revision_ids": ctx["lane_set_revision_ids"],
        "submission_revision_ids": ctx["submission_revision_ids"],
        "dispute_queue_revision_id": ctx["dispute_queue_revision_id"],
        "validation_report_revision_id": validation_report_revision_id,
        "log_revision_id": log_revision_id,
        "step_manifest_revision_id": step_manifest_revision_id,
        "transformation_id": transformation_id,
        "checkpoint_revision_ids": ctx["checkpoint_revision_ids"]
        + checkpoint_revision_ids,
        "counts": result["candidate_set"]["counts"],
        "gate": gate_report,
    }


def _run_after_begin(
    service,
    edition_part_id,
    step_run_id,
    inputs,
    configuration_revision_id,
    config_content,
    frozen,
    id_range,
    required_lanes,
    id_factory,
):
    try:
        ctx = _build_ctx(service, step_run_id, inputs, config_content)
    except _InputContractError as exc:
        return _fail(service, step_run_id, "input_contract", str(exc))
    ctx["edition_part_id"] = edition_part_id
    ctx["configuration_revision_id"] = configuration_revision_id
    ctx["frozen"] = list(frozen)
    ctx["config"] = {"gate_profile": GATE_PROFILE, "id_range": id_range}
    ctx["required_lanes"] = required_lanes
    ctx["id_range"] = id_range
    ctx["id_factory"] = id_factory

    ordered = sorted(inputs["submissions"], key=_submission_sort_key)
    lane_set_revision_ids = {}
    checkpoint_revision_ids = []
    for index, key in enumerate(ordered):
        category, lane = key.split("/")
        _, lane_revision_id = service.put_artifact(
            step_run_id,
            "candidate_lane_set",
            ctx["lane_set_bytes"][key],
            producer_module=M4_TOOL,
            producer_version=M4_TOOL_VERSION,
        )
        service.seal_revision(lane_revision_id)
        lane_set_revision_ids[key] = lane_revision_id
        pending = [
            {"task_id": "lane_%s" % later.replace("/", "_")} for later in ordered[index + 1 :]
        ] + [{"task_id": "reconcile"}, {"task_id": "assemble"}]
        checkpoint_revision_ids.append(
            service.write_checkpoint(
                step_run_id,
                edition_part_id=edition_part_id,
                stage="m4",
                completed_tasks=[
                    {
                        "task_id": "lane_%s_%s" % (category, lane),
                        "artifact_revision_id": lane_revision_id,
                        "status": "succeeded",
                        "terminal_state": None,
                    }
                ],
                human_decisions=[],
                pending_queue=pending,
                next_pointer=pending[0] if pending else None,
            )
        )
    ctx["lane_set_revision_ids"] = lane_set_revision_ids

    rec = assemble.reconcile_lanes(ctx["lane_results"], required_lanes=required_lanes)
    _, queue_revision_id = service.put_artifact(
        step_run_id,
        "dispute_queue",
        canonical_json({"disputes": rec["disputes"]}),
        producer_module=M4_TOOL,
        producer_version=M4_TOOL_VERSION,
    )
    service.seal_revision(queue_revision_id)
    ctx["dispute_queue_revision_id"] = queue_revision_id
    pending = [{"task_id": row["dispute_id"]} for row in rec["disputes"]] + [
        {"task_id": "assemble"}
    ]
    checkpoint_revision_ids.append(
        service.write_checkpoint(
            step_run_id,
            edition_part_id=edition_part_id,
            stage="m4",
            completed_tasks=[
                {
                    "task_id": "reconcile",
                    "artifact_revision_id": queue_revision_id,
                    "status": "succeeded",
                    "terminal_state": None,
                }
            ],
            human_decisions=[],
            pending_queue=pending,
            next_pointer=pending[0] if pending else None,
        )
    )
    ctx["checkpoint_revision_ids"] = checkpoint_revision_ids

    if rec["disputes"]:
        token = service.await_human(step_run_id, [queue_revision_id])
        return {
            "status": "awaiting_human",
            "processing_run_id": ctx["processing_run_id"],
            "step_run_id": step_run_id,
            "configuration_revision_id": configuration_revision_id,
            "frozen_input_revision_ids": list(frozen),
            "dispute_queue_revision_id": queue_revision_id,
            "dispute_ids": [row["dispute_id"] for row in rec["disputes"]],
            "resume_token": token,
            "lane_set_revision_ids": lane_set_revision_ids,
            "checkpoint_revision_ids": checkpoint_revision_ids,
        }
    return _complete(service, step_run_id, ctx)


def run_m4(
    service,
    edition_part_id,
    *,
    id_range=None,
    required_lanes=None,
    technique_profile_revision_id=None,
    id_factory=None,
):
    """在真实 Ledger 上执行 m4 assemble 的完整事务序列，返回 summary dict。"""
    inputs = resolve_m4_inputs(
        service,
        edition_part_id,
        technique_profile_revision_id=technique_profile_revision_id,
    )
    if not inputs["submissions"]:
        raise ExtractionRefused("没有已登记的提交件", code="REF_001")
    id_range = dict(id_range or DEFAULT_ID_RANGE)
    effective_required_lanes = dict(required_lanes or DEFAULT_REQUIRED_LANES)
    present = sorted({key.split("/")[0] for key in inputs["submissions"]})
    required = {}
    for category in present:
        lanes = list(effective_required_lanes.get(category, []))
        required[category] = lanes
        for lane in lanes:
            if "%s/%s" % (category, lane) not in inputs["submissions"]:
                raise ExtractionRefused(
                    "缺必需路: %s/%s" % (category, lane), code="REF_001"
                )

    processing_run_id = inputs["processing_run_id"]
    technique_id = inputs["technique_id"]
    config_content = {
        "stage": "m4",
        "task": "assemble",
        "tool": M4_TOOL,
        "tool_version": M4_TOOL_VERSION,
        "gate_profile": GATE_PROFILE,
        "id_range": id_range,
        "required_lanes": effective_required_lanes,
        "term_layering": TERM_LAYERING,
    }
    _, configuration_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical_json(config_content),
        producer_module=M4_TOOL,
        producer_version=M4_TOOL_VERSION,
    )
    frozen = [
        inputs["corpus_stage_package_revision_id"],
        inputs["corpus_package_revision_id"],
        inputs["spans_revision_id"],
        inputs["technique_profile_revision_id"],
    ]
    for key in sorted(inputs["submissions"], key=_submission_sort_key):
        frozen.append(inputs["submissions"][key]["revision_id"])

    step_run_id = begin_m4_step_run(
        service,
        edition_part_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": ids.new_id("step_run_id"),
            "input_artifact_ids": frozen,
            "technique_profile_id": technique_id,
            "configuration_artifact_id": configuration_revision_id,
        },
    )
    try:
        return _run_after_begin(
            service,
            edition_part_id,
            step_run_id,
            inputs,
            configuration_revision_id,
            config_content,
            frozen,
            id_range,
            required,
            id_factory,
        )
    except Exception as exc:  # noqa: BLE001 —— begin 之后未预期异常一律内部失败封存
        return _fail(
            service, step_run_id, "internal", "%s: %s" % (type(exc).__name__, exc)
        )


# ------------------------------------------------------------------ 类别裁决 / 恢复
def _edition_part_id(service, processing_run_id):
    row = service.store.conn.execute(
        "SELECT edition_part_id FROM processing_runs WHERE processing_run_id=?",
        (processing_run_id,),
    ).fetchone()
    return row[0] if row else None


def _own_sealed_revisions(service, step_run_id, artifact_type):
    return [
        row[0]
        for row in service.store.conn.execute(
            "SELECT r.artifact_revision_id FROM artifact_revisions r "
            "JOIN artifacts a ON a.artifact_id = r.artifact_id "
            "WHERE r.step_run_id=? AND a.artifact_type=? AND r.status='sealed' "
            "ORDER BY r.created_at, r.rowid",
            (step_run_id, artifact_type),
        ).fetchall()
    ]


def _registered_rulings(service, step_run_id, ordered=False):
    """本 StepRun 已登记的人工裁决事件 ``[(dispute_id, event_revision_id), ...]``。"""
    rows = service.store.conn.execute(
        "SELECT h.event_revision_id FROM human_events h WHERE h.step_run_id=? "
        "ORDER BY h.created_at, h.rowid",
        (step_run_id,),
    ).fetchall()
    pairs = []
    for (revision_id,) in rows:
        content = _read_doc(service, revision_id) or {}
        pairs.append((content.get("dispute_id"), revision_id))
    if ordered:
        return pairs
    return {dispute_id for dispute_id, _revision_id in pairs}


def _inputs_from_frozen(service, step_run_id, frozen):
    """沿 supersedes 链上该运行冻结的修订，按 ``artifact_type`` 重建 inputs（只读）。"""
    step = service.get_step_run(step_run_id)
    request = json.loads(step["request_json"] or "{}")
    types = _artifact_types(service, frozen)
    inputs = {
        "processing_run_id": step["processing_run_id"],
        "technique_id": request["technique_profile_id"],
        "corpus_stage_package_revision_id": None,
        "corpus_package_revision_id": None,
        "spans_revision_id": None,
        "technique_profile_revision_id": None,
        "submissions": {},
    }
    for revision_id in frozen:
        kind = types.get(revision_id)
        if kind == "stage_package":
            inputs["corpus_stage_package_revision_id"] = revision_id
        elif kind == "corpus_package":
            inputs["corpus_package_revision_id"] = revision_id
        elif kind == "corpus_spans":
            inputs["spans_revision_id"] = revision_id
        elif kind == "technique_profile":
            inputs["technique_profile_revision_id"] = revision_id
        elif kind == "candidate_submission":
            doc = _read_doc(service, revision_id)
            key = "%s/%s" % (doc["category"], doc["lane"])
            inputs["submissions"][key] = {
                "revision_id": revision_id,
                "step_run_id": None,
                "channel": doc.get("channel"),
            }
    return inputs


def _required_for(inputs, config):
    effective = dict(config.get("required_lanes") or {})
    present = sorted({key.split("/")[0] for key in inputs["submissions"]})
    return {category: list(effective.get(category, [])) for category in present}


def _verify_lane_integrity(service, step_run_id, ctx):
    """按冻结输入重算 lane 集与 disputes，必须与已封存修订逐字节/逐项相同。"""
    sealed_lane_bytes = {}
    lane_set_revision_ids = {}
    for revision_id in _own_sealed_revisions(service, step_run_id, "candidate_lane_set"):
        data = _read_bytes(service, revision_id)
        doc = json.loads(data.decode("utf-8"))
        key = "%s/%s" % (doc["category"], doc["lane"])
        sealed_lane_bytes[key] = data
        lane_set_revision_ids[key] = revision_id
    if sealed_lane_bytes != ctx["lane_set_bytes"]:
        raise _InputContractError("按冻结输入重算的 lane 集字节与已封存 candidate_lane_set 不一致")
    queue_revisions = _own_sealed_revisions(service, step_run_id, "dispute_queue")
    if len(queue_revisions) != 1:
        raise _InputContractError("本 StepRun 自有 dispute_queue 修订 %d 个" % len(queue_revisions))
    sealed_queue = json.loads(_read_bytes(service, queue_revisions[0]).decode("utf-8"))
    recomputed = assemble.reconcile_lanes(
        ctx["lane_results"], required_lanes=ctx["required_lanes"]
    )["disputes"]
    if sealed_queue.get("disputes") != recomputed:
        raise _InputContractError("重算 disputes 与已封存 dispute_queue 不一致")
    return lane_set_revision_ids


def record_category_ruling(service, step_run_id, resume_token, ruling_doc):
    """登记一条 m4 类别裁决人工事件，并立即写一个 Checkpoint（§17.1）。"""
    step = service.get_step_run(step_run_id)
    if step is None:
        raise ExtractionRefused("StepRun 不存在: %s" % step_run_id, code="REF_001")
    if step["status"] != "awaiting_human":
        raise ExtractionRefused(
            "StepRun 不处于 awaiting_human（当前 %s）" % step["status"]
        )
    if not isinstance(ruling_doc, dict):
        raise SchemaViolation("裁决文档必须是对象", code="SCH_001")
    allowed = {
        "schema_version",
        "dispute_id",
        "choice",
        "rationale",
        "synthetic_fixture",
        "actor_ref",
    }
    required = {"schema_version", "dispute_id", "choice", "rationale"}
    keys = set(ruling_doc)
    if not required <= keys or not keys <= allowed:
        raise ExtractionRefused("ruling_doc 键集合非法: %s" % sorted(keys), code="SCH_002")
    if ruling_doc["schema_version"] != CANDIDATE_SCHEMA_VERSION:
        raise ExtractionRefused("schema_version 不符", code="SCH_002")
    rationale = ruling_doc["rationale"]
    if not isinstance(rationale, str) or not rationale.strip():
        raise ExtractionRefused("rationale 必须为非空字符串", code="SCH_001")
    if ruling_doc["choice"] not in RULING_CHOICES:
        raise ExtractionRefused("choice 非闭集: %r" % (ruling_doc["choice"],), code="SCH_002")
    synthetic = ruling_doc.get("synthetic_fixture", False)
    if not isinstance(synthetic, bool):
        raise ExtractionRefused("synthetic_fixture 必须为 bool", code="SCH_002")

    queues = _own_sealed_revisions(service, step_run_id, "dispute_queue")
    if len(queues) != 1:
        raise ExtractionRefused(
            "本 StepRun 自有 dispute_queue 修订 %d 个" % len(queues), code="REF_001"
        )
    queue_revision_id = queues[0]
    queue = _read_doc(service, queue_revision_id) or {}
    dispute_ids = [row["dispute_id"] for row in queue.get("disputes") or []]
    dispute_id = ruling_doc["dispute_id"]
    if dispute_id not in dispute_ids:
        raise ExtractionRefused("未知 dispute_id: %s" % dispute_id, code="REF_001")
    if dispute_id in _registered_rulings(service, step_run_id):
        raise ExtractionRefused("该 dispute 已有裁决: %s" % dispute_id, code="ID_002")

    event = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "event_kind": "category_ruling",
        "stage": "m4",
        "processing_run_id": step["processing_run_id"],
        "step_run_id": step_run_id,
        "dispute_id": dispute_id,
        "choice": ruling_doc["choice"],
        "rationale": rationale,
        "actor_ref": ruling_doc.get("actor_ref") or service.actor(),
        "synthetic_fixture": synthetic,
        "seen": {"dispute_queue_revision_id": queue_revision_id},
    }
    _, event_revision_id = service.put_artifact(
        step_run_id,
        "human_event",
        canonical_json(event),
        producer_module=M4_TOOL,
        producer_version=M4_TOOL_VERSION,
    )
    service.seal_revision(event_revision_id)
    service.record_human_event(
        step_run_id, resume_token, event_revision_id, decision_type=None
    )
    registered = _registered_rulings(service, step_run_id, ordered=True)
    human_decisions = [revision_id for _dispute_id, revision_id in registered]
    ruled_ids = {row[0] for row in registered}
    remaining = [row for row in dispute_ids if row not in ruled_ids]
    pending = [{"task_id": row} for row in remaining] + [{"task_id": "assemble"}]
    checkpoint_revision_id = service.write_checkpoint(
        step_run_id,
        edition_part_id=_edition_part_id(service, step["processing_run_id"]),
        stage="m4",
        completed_tasks=[
            {
                "task_id": dispute_id,
                "artifact_revision_id": event_revision_id,
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=human_decisions,
        pending_queue=pending,
        next_pointer=pending[0] if pending else None,
    )
    return {
        "event_revision_id": event_revision_id,
        "checkpoint_revision_id": checkpoint_revision_id,
        "remaining_dispute_ids": remaining,
    }


def resume_m4(service, step_run_id, resume_token, *, id_factory=None):
    """消费 ``resume_token`` 并在同一运行内完成装配（以 Ledger 人工暂停恢复语义为准）。"""
    step = service.get_step_run(step_run_id)
    if step is None:
        raise ExtractionRefused("StepRun 不存在: %s" % step_run_id, code="REF_001")
    if step["status"] != "awaiting_human":
        raise ExtractionRefused(
            "StepRun 不处于 awaiting_human（当前 %s）" % step["status"]
        )
    queues = _own_sealed_revisions(service, step_run_id, "dispute_queue")
    if len(queues) != 1:
        raise ExtractionRefused(
            "本 StepRun 自有 dispute_queue 修订 %d 个" % len(queues), code="REF_001"
        )
    queue = _read_doc(service, queues[0]) or {}
    dispute_ids = [row["dispute_id"] for row in queue.get("disputes") or []]
    ruled_pairs = _registered_rulings(service, step_run_id, ordered=True)
    ruled = {dispute_id for dispute_id, _revision_id in ruled_pairs}
    for dispute_id in dispute_ids:
        if dispute_id not in ruled:
            raise ExtractionRefused("仍有未裁决分歧: %s" % dispute_id)

    request = json.loads(step["request_json"] or "{}")
    frozen = service._frozen_input_ids(step_run_id)
    config = _read_doc(service, request.get("configuration_artifact_id")) or {}
    edition_part_id = _edition_part_id(service, step["processing_run_id"])

    service.resume(step_run_id, resume_token)
    try:
        inputs = _inputs_from_frozen(service, step_run_id, frozen)
        try:
            ctx = _build_ctx(service, step_run_id, inputs, config)
        except _InputContractError as exc:
            return _fail(service, step_run_id, "input_contract", str(exc))
        ctx["edition_part_id"] = edition_part_id
        ctx["configuration_revision_id"] = request.get("configuration_artifact_id")
        ctx["frozen"] = list(frozen)
        id_range = dict(config.get("id_range") or DEFAULT_ID_RANGE)
        ctx["id_range"] = id_range
        ctx["config"] = {"gate_profile": config.get("gate_profile", GATE_PROFILE), "id_range": id_range}
        ctx["required_lanes"] = _required_for(inputs, config)
        ctx["id_factory"] = id_factory
        try:
            lane_set_revision_ids = _verify_lane_integrity(service, step_run_id, ctx)
        except _InputContractError as exc:
            return _fail(service, step_run_id, "input_contract", str(exc))
        ctx["lane_set_revision_ids"] = lane_set_revision_ids
        ctx["dispute_queue_revision_id"] = queues[0]
        ctx["checkpoint_revision_ids"] = [
            row["artifact_revision_id"]
            for row in service.list_checkpoints(edition_part_id, "m4")
            if row["content"]["step_run_id"] == step_run_id
        ]
        rulings = {
            dispute_id: (_read_doc(service, revision_id) or {}).get("choice")
            for dispute_id, revision_id in ruled_pairs
        }
        human_event_revision_ids = [revision_id for _dispute_id, revision_id in ruled_pairs]
        return _complete(
            service,
            step_run_id,
            ctx,
            rulings=rulings,
            human_event_revision_ids=human_event_revision_ids,
        )
    except Exception as exc:  # noqa: BLE001 —— resume 之后未预期异常一律内部失败封存
        return _fail(
            service, step_run_id, "internal", "%s: %s" % (type(exc).__name__, exc)
        )
