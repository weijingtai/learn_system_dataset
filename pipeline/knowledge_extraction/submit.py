"""m4 submit StepRun：每路（category × lane）登记一份提交件为 Ledger 已封存修订（D-04）。

``begin_step_run`` 之前的任何拒绝都不得写入 Ledger；之后任何异常一律转为
``internal`` 失败封存。渠道是否被首切片接受在 begin 之前判定（D-01）。
"""

import json

import yaml

from pipeline.ledger import ids
from pipeline.ledger.errors import SchemaViolation

from . import ACCEPTED_CHANNELS, M4_TOOL, M4_TOOL_VERSION
from .errors import ExtractionRefused
from .inputs import (
    collect_submissions,
    latest_succeeded_step_run,
    m4_is_sealed,
    resolve_m3_outputs,
)
from .serialize import canonical_json
from .submission import validate_submission


def begin_m4_step_run(service, edition_part_id, request):
    """建立 m4 阶段的新 StepRun：若已有 succeeded 的同阶段运行则接替之。

    同阶段第 2 个及以后的运行一律 ``supersede_step_run``（G7-RULINGS 第 32 条推广为
    第 58 条），表示续写而非替换；首个运行仍用 ``begin_step_run``。返回 ``step_run_id``。
    """
    previous = latest_succeeded_step_run(service, edition_part_id, "m4")
    if previous is None:
        return service.begin_step_run(request)
    return service.supersede_step_run(previous, request)


def _parse_submission(submission_bytes):
    """解析提交件字节（先 JSON 后 YAML）；非对象 → SchemaViolation(SCH_001)。"""
    text = submission_bytes.decode("utf-8")
    try:
        doc = json.loads(text)
    except ValueError:
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError:
            raise SchemaViolation("提交件不是合法 JSON/YAML", code="SCH_001")
    if not isinstance(doc, dict):
        raise SchemaViolation("提交件必须是对象", code="SCH_001")
    return doc


def _fail(service, step_run_id, check, detail):
    """失败封存：put failure_report → seal → fail_step_run。"""
    _, failure_revision_id = service.put_artifact(
        step_run_id,
        "failure_report",
        canonical_json({"check": check, "detail": detail}),
        producer_module=M4_TOOL,
        producer_version=M4_TOOL_VERSION,
    )
    service.seal_revision(failure_revision_id)
    service.fail_step_run(
        step_run_id, [failure_revision_id], "M4 submit %s: %s" % (check, detail)
    )
    return failure_revision_id


def run_m4_submit(
    service,
    edition_part_id,
    submission_bytes,
    *,
    producer_module,
    producer_version,
    model_ref=None,
):
    """登记一路提交件为 m4 submit StepRun；返回 summary dict。"""
    # ---- begin 之前：任何拒绝都不得写入 Ledger ----
    m3 = resolve_m3_outputs(service, edition_part_id)
    doc = validate_submission(
        _parse_submission(submission_bytes), technique_id=m3["technique_id"]
    )
    if doc["channel"] not in ACCEPTED_CHANNELS or doc["lane"] == "c":
        raise ExtractionRefused(
            "首切片不收 channel=%s lane=%s" % (doc["channel"], doc["lane"]), code="SCH_002"
        )
    if m4_is_sealed(service, edition_part_id):
        raise ExtractionRefused("M4 已封存：存在 succeeded 的 assemble 运行")
    key = "%s/%s" % (doc["category"], doc["lane"])
    if key in collect_submissions(service, edition_part_id):
        raise ExtractionRefused("同类同路提交件已存在: %s" % key, code="ID_002")

    processing_run_id = m3["processing_run_id"]
    technique_id = m3["technique_id"]
    category = doc["category"]
    lane = doc["lane"]
    channel = doc["channel"]

    # ---- 写入 ----
    _, configuration_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical_json(
            {
                "stage": "m4",
                "task": "submit",
                "category": category,
                "lane": lane,
                "channel": channel,
                "tool": M4_TOOL,
                "tool_version": M4_TOOL_VERSION,
            }
        ),
        producer_module=M4_TOOL,
        producer_version=M4_TOOL_VERSION,
    )
    frozen = [m3["corpus_stage_package_revision_id"], m3["spans_revision_id"]]
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
        _, submission_revision_id = service.put_artifact(
            step_run_id,
            "candidate_submission",
            canonical_json(doc),
            producer_module=producer_module,
            producer_version=producer_version,
        )
        service.seal_revision(submission_revision_id)
        checkpoint_revision_id = service.write_checkpoint(
            step_run_id,
            edition_part_id=edition_part_id,
            stage="m4",
            completed_tasks=[
                {
                    "task_id": "submit_%s_%s" % (category, lane),
                    "artifact_revision_id": submission_revision_id,
                    "status": "succeeded",
                    "terminal_state": None,
                }
            ],
            human_decisions=[],
            pending_queue=[],
            next_pointer=None,
        )
        _, log_revision_id = service.put_artifact(
            step_run_id,
            "step_log",
            (
                "register_submission %s/%s\nchannel=%s"
                % (category, lane, channel)
            ).encode("utf-8"),
            producer_module=M4_TOOL,
            producer_version=M4_TOOL_VERSION,
        )
        service.seal_revision(log_revision_id)
        service.record_transformation(
            step_run_id,
            operation="register_submission",
            tool=producer_module,
            tool_version=producer_version,
            configuration_revision_id=configuration_revision_id,
            input_revision_ids=frozen,
            output_revision_ids=[submission_revision_id],
            model_ref=model_ref,
            validation_report_revision_id=None,
            human_event_revision_ids=[],
        )
        version = service.get_step_run(step_run_id)["status_version"]
        service.finish_step_run(
            step_run_id,
            {
                "schema_version": "1.0.0",
                "processing_run_id": processing_run_id,
                "step_run_id": step_run_id,
                "status_version": version + 1,
                "status": "succeeded",
                "output_artifact_ids": [submission_revision_id],
                "validation_report_ids": [],
                "log_artifact_ids": [log_revision_id],
                "failure_artifact_ids": [],
            },
        )
    except Exception as exc:  # noqa: BLE001 —— begin 之后一律内部失败封存
        return {
            "status": "failed",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "configuration_revision_id": configuration_revision_id,
            "frozen_input_revision_ids": frozen,
            "category": category,
            "lane": lane,
            "channel": channel,
            "failed_check": "internal",
            "failure_revision_id": _fail(
                service, step_run_id, "internal", "%s: %s" % (type(exc).__name__, exc)
            ),
            "reason": "%s: %s" % (type(exc).__name__, exc),
        }
    return {
        "status": "succeeded",
        "processing_run_id": processing_run_id,
        "step_run_id": step_run_id,
        "configuration_revision_id": configuration_revision_id,
        "frozen_input_revision_ids": frozen,
        "category": category,
        "lane": lane,
        "channel": channel,
        "submission_revision_id": submission_revision_id,
        "checkpoint_revision_id": checkpoint_revision_id,
        "log_revision_id": log_revision_id,
    }
