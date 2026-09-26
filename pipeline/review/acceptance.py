"""M6 m6-data-fields 验收（规格 §19.0:910 判据）：十六项判定（12 PASS + 2 BLOCKED）。

判定只读 Ledger 与 ``testing/data/expected_review.yaml``（或 ``--expected``）；**不**直接
import ``gate`` / ``model`` / ``propagation`` / ``step`` / ``rework`` 的判定函数，也不信任
``close_review`` 返回的 Gate 报告，一律自行重算。驱动准备步骤的函数经 ``importlib`` 取用
（属运行入口，不属判定）。

依赖真实 ``expert_verified`` 签发的判定恒 BLOCKED（P7 / 第 80 条签发决定表）。
"""

import argparse
import hashlib
import importlib
import json
import re
import shutil
import tempfile
from pathlib import Path

from pipeline.ledger.service import LedgerService

try:
    import jsonschema
    import yaml
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except ImportError:  # pragma: no cover —— 宿主匮乏由 main 统一转 exit 3
    jsonschema = None
    yaml = None

from pipeline.review.testing.upstream_stub import (
    load_data,
    seed_corrected_corpus,
    seed_rerun_m4_m5,
    seed_upstream,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "openspec" / "schemas"
DEFAULT_EXPECTED = Path(__file__).resolve().parent / "testing" / "data" / "expected_review.yaml"

_step = importlib.import_module("pipeline.review.step")
_rework = importlib.import_module("pipeline.review.rework")

REV32 = re.compile(r"^rev_[0-9a-f]{32}$")
# review_decision 事件顶层键（§8.2 / review_events._TOP_KEYS），独立重写
REVIEW_TOP_KEYS = {
    "schema_version",
    "event_kind",
    "stage",
    "decision_type",
    "verdict",
    "target",
    "processing_run_id",
    "step_run_id",
    "actor_ref",
    "rationale",
    "evidence_refs",
    "consumption_level",
}
REVIEW_TARGET_KEYS = {"entity_kind", "entity_id", "artifact_revision_id"}

BLOCKED_CHECKS = (
    (
        "legacy_workbench_seed",
        "前置缺失: M6 Review Workbench；pattern_knowledge_workbench 旧数据体未迁入（准入判定见 run_all 20.7）",
    ),
    (
        "upstream_real",
        "前置缺失: 真实 expert_verified 签发决定表由用户撰写（第 80 条签发决定表）；旧工作台数据迁入；M5 候选级校验未实现",
    ),
)


# ------------------------------------------------------------------ 只读工具
def _revision_bytes(service, revision_id):
    row = service.get_revision(revision_id)
    if row is None:
        raise KeyError("修订不存在: %s" % revision_id)
    return service.read_object(row["sha256"])


def _doc(service, revision_id):
    text = _revision_bytes(service, revision_id).decode("utf-8")
    try:
        return json.loads(text)
    except ValueError:
        return yaml.safe_load(text)


def _artifact_type(service, revision_id):
    info = service.describe_revision(revision_id)
    return None if info is None else info["artifact_type"]


def _frozen_inputs(service, step_run_id):
    return service.list_frozen_inputs(step_run_id)


def _m6_step_runs(service):
    return service.list_stage_checkpoint_step_runs("m6")


def _own_checkpoints(service, edition_part_id, step_run_id):
    return [
        row
        for row in service.list_checkpoints(edition_part_id, "m6")
        if row["content"]["step_run_id"] == step_run_id
    ]


def _human_event_revs(service, step_run_id):
    return [
        row["event_revision_id"] for row in service.list_human_events(step_run_id)
    ]


def _all_review_queues(service):
    """所有 ``review_queue`` 修订的内容列表。"""
    rows = service.list_revisions(artifact_type="review_queue")
    return [_doc(service, row["artifact_revision_id"]) or [] for row in rows]


def _stage_package_validator():
    schema = json.loads((SCHEMA_DIR / "stage_package.schema.json").read_text(encoding="utf-8"))
    ref = json.loads((SCHEMA_DIR / "artifact_ref.schema.json").read_text(encoding="utf-8"))
    registry = Registry().with_resource(
        "artifact_ref.schema.json",
        Resource.from_contents(ref, default_specification=DRAFT202012),
    )
    return jsonschema.Draft202012Validator(schema, registry=registry)


def _spans_map(service, revision_id):
    doc = _doc(service, revision_id) or {}
    raw = doc.get("spans")
    if isinstance(raw, list):
        return {s["span_id"]: s for s in raw if isinstance(s, dict) and "span_id" in s}
    if isinstance(raw, dict):
        return raw
    return {}


def _changed_and_reachable(old_spans, new_spans, candidate_set):
    """独立重算「变更 Span」与「可达对象」（D-07 键：text + source_anchor；引用闭包）。"""
    changed, removed = [], []
    for span_id, old in old_spans.items():
        if span_id not in new_spans:
            removed.append(span_id)
            continue
        new = new_spans[span_id]
        old_key = json.dumps(
            {k: old.get(k) for k in ("text", "source_anchor") if k in old},
            sort_keys=True,
            ensure_ascii=False,
        )
        new_key = json.dumps(
            {k: new.get(k) for k in ("text", "source_anchor") if k in new},
            sort_keys=True,
            ensure_ascii=False,
        )
        if old_key != new_key:
            changed.append(span_id)
    affected = set(changed) | set(removed)

    objects = (
        list(candidate_set.get("assertions") or [])
        + list(candidate_set.get("school_views") or [])
        + list(candidate_set.get("patterns") or [])
    )
    reachable = set()
    for obj in objects:
        eid = obj.get("assertion_id") or obj.get("school_view_id") or obj.get("pattern_id")
        for ev in obj.get("evidence") or []:
            if ev.get("source_span_id") in affected:
                reachable.add(eid)
        for ref in obj.get("source_refs") or []:
            if ref.get("source_span_id") in affected:
                reachable.add(eid)
    changed_flag = True
    while changed_flag:
        changed_flag = False
        for obj in objects:
            eid = obj.get("assertion_id") or obj.get("school_view_id") or obj.get("pattern_id")
            if eid in reachable:
                continue
            if obj.get("subject_entity_id") in reachable:
                reachable.add(eid)
                changed_flag = True
            for claim in obj.get("claim_refs") or []:
                if claim.get("entity_id") in reachable:
                    reachable.add(eid)
                    changed_flag = True
            for aid in obj.get("assertion_ids") or []:
                if aid in reachable:
                    reachable.add(eid)
                    changed_flag = True
    return sorted(changed), sorted(removed), sorted(reachable)


# ------------------------------------------------------------------ 十四项判定
def _check_inputs_frozen(world):
    service = world["service"]
    seed = world["seed"]
    step_run_id = world["first_open"]["step_run_id"]
    m3_outputs = list(
        json.loads(service.get_step_run(seed["m3_step_run_id"])["result_json"] or "{}").get(
            "output_artifact_ids"
        )
        or []
    )
    corpus_package_rev = next(
        (rev for rev in m3_outputs if _artifact_type(service, rev) == "corpus_package"),
        None,
    )
    expected = {
        seed["corpus_stage_package_revision_id"],
        corpus_package_rev,
        seed["spans_revision_id"],
        seed["candidate_package_revision_id"],
        seed["candidate_set_revision_id"],
        seed["validation_package_revision_id"],
        seed["gate_results_revision_id"],
    }
    errors = []
    frozen = set(_frozen_inputs(service, step_run_id))
    if frozen != expected:
        errors.append("首审 frozen_inputs 不符: %s" % sorted(frozen ^ expected))
    step_created_at = service.get_step_run(step_run_id)["created_at"]
    for revision_id in expected:
        if revision_id is None:
            errors.append("期望冻结修订缺失")
            continue
        row = service.first_sealed_event_created_at(revision_id)
        if row is None:
            errors.append("冻结修订无 sealed 事件: %s" % revision_id)
        elif row > step_created_at:
            errors.append("冻结修订在其后封存: %s" % revision_id)
    return errors


def _check_queue_from_upstream(world):
    service = world["service"]
    errors = []
    config = _doc(service, world["first_open"]["configuration_revision_id"]) or {}
    required = config.get("required_decision_types") or {}
    candidate_set = _doc(service, world["seed"]["candidate_set_revision_id"]) or {}
    expected = set()
    for assertion in candidate_set.get("assertions") or []:
        for decision_type in required.get(assertion["assertion_id"], []):
            expected.add("%s#%s" % (assertion["assertion_id"], decision_type))
    for pattern in candidate_set.get("patterns") or []:  # T19：pattern 同样进审核队列
        for decision_type in required.get(pattern["pattern_id"], []):
            expected.add("%s#%s" % (pattern["pattern_id"], decision_type))
    for school_view in candidate_set.get("school_views") or []:
        for decision_type in required.get(school_view["school_view_id"], []):
            expected.add("%s#%s" % (school_view["school_view_id"], decision_type))
    actual = {
        item["queue_item_id"]
        for item in (_doc(service, world["first_open"]["queue_revision_id"]) or [])
    }
    if expected != actual:
        errors.append("队列项集合与独立推导不符: %s" % sorted(expected ^ actual))
    return errors


def _check_decisions_as_human_events(world):
    service = world["service"]
    errors = []
    queue_types = {}
    for queue in _all_review_queues(service):
        for item in queue:
            queue_types[item["queue_item_id"]] = item["decision_type"]
    m6_runs = set(_m6_step_runs(service))

    rows = [
        (row["event_revision_id"], row["step_run_id"], row["decision_type"])
        for row in service.list_human_events()
    ]
    for event_revision_id, step_run_id, decision_type in rows:
        doc = _doc(service, event_revision_id) or {}
        if doc.get("event_kind") != "review_decision":
            continue
        revision = service.get_revision(event_revision_id)
        if revision is None or revision["status"] != "sealed":
            errors.append("决定非 sealed: %s" % event_revision_id)
        if set(doc) != REVIEW_TOP_KEYS:
            errors.append("决定事件键集不符: %s" % sorted(set(doc) ^ REVIEW_TOP_KEYS))
        if set(doc.get("target") or {}) != REVIEW_TARGET_KEYS:
            errors.append("target 键集不符: %s" % event_revision_id)
        if _artifact_type(service, event_revision_id) != "human_event":
            errors.append("决定非 human_event: %s" % event_revision_id)
        if step_run_id not in m6_runs:
            errors.append("决定不属 m6 运行: %s" % event_revision_id)
        queue_item_id = "%s#%s" % (
            doc["target"]["entity_id"],
            doc["decision_type"],
        )
        if queue_types.get(queue_item_id) != decision_type:
            errors.append("human_events.decision_type 与队列项不符: %s" % event_revision_id)
        if not (doc.get("rationale") or "").strip():
            errors.append("rationale 为空: %s" % event_revision_id)
        if not (doc.get("actor_ref") or "").strip():
            errors.append("actor_ref 为空: %s" % event_revision_id)
    return errors


def _check_checkpoint_per_decision(world):
    service = world["service"]
    edition_part_id = world["edition_part_id"]
    errors = []
    chain = service.list_checkpoints(edition_part_id, "m6")
    for previous, current in zip(chain, chain[1:]):
        if current.get("prev_checkpoint_revision_id") != previous["artifact_revision_id"]:
            errors.append("Checkpoint 链 prev 不连续")
            break
    for step_run_id in _m6_step_runs(service):
        own = _own_checkpoints(service, edition_part_id, step_run_id)
        events = _human_event_revs(service, step_run_id)
        if len(own) != 1 + len(events):
            errors.append(
                "运行 %s Checkpoint 数 %d != 1 + human_event %d"
                % (step_run_id, len(own), len(events))
            )
        listed = set()
        for checkpoint in own:
            decisions = checkpoint["content"].get("human_decisions") or []
            if len(decisions) != len(set(decisions)):
                errors.append("human_decisions 含重复: %s" % checkpoint["artifact_revision_id"])
            listed.update(decisions)
        for event_revision_id in events:
            if event_revision_id not in listed:
                errors.append("人工事件未落入任何 Checkpoint: %s" % event_revision_id)
    return errors


def _check_decision_anchor_fields(world):
    service = world["service"]
    errors = []
    candidate_revs = {
        world["seed"]["candidate_set_revision_id"],
        world["seed_rerun"]["candidate_set_revision_id"],
    }
    for label, revision_id in (
        ("首审", world["first_close"]["reviewed_edition_revision_id"]),
        ("复审", world["rework_close"]["reviewed_edition_revision_id"]),
    ):
        edition = _doc(service, revision_id) or {}
        for decision in edition.get("decisions") or []:
            entity_id = decision.get("target_entity_id")
            queue_item_id = decision.get("queue_item_id") or ""
            if not entity_id or queue_item_id.split("#")[0] != entity_id:
                errors.append("%s 决定的 target_entity_id 与前缀不符" % label)
            for key in ("seen_artifact_revision_id", "current_target_revision_id"):
                value = decision.get(key)
                if not (isinstance(value, str) and REV32.match(value)):
                    errors.append("%s 决定的 %s 非法: %r" % (label, key, value))
            if decision.get("seen_artifact_revision_id") not in candidate_revs:
                errors.append("%s 决定的 seen 修订非候选修订" % label)
    return errors


def _check_reviewed_edition_contract(world):
    service = world["service"]
    expected = world["expected"]["first_review"]
    errors = []
    validator = _stage_package_validator()
    packages = service.list_stage_packages("m6")
    if len(packages) != 2:
        errors.append("m6 StagePackage 数不为 2: %d" % len(packages))
    for package_row in packages:
        revision_id = package_row["artifact_revision_id"]
        package = _doc(service, revision_id) or {}
        try:
            validator.validate(package)
        except jsonschema.ValidationError as exc:
            errors.append("m6 StagePackage 未过 Schema: %s" % exc.message)
            continue
        edition_revision_id = package["payload"]["reviewed_edition_revision_id"]
        edition_bytes = _revision_bytes(service, edition_revision_id)
        if package["manifest"]["content_sha256"] != hashlib.sha256(edition_bytes).hexdigest():
            errors.append("manifest.content_sha256 != sha256(reviewed_edition)")
        edition = json.loads(edition_bytes.decode("utf-8"))
        if edition.get("unresolved_count") != 0:
            errors.append("unresolved_count != 0")

    first_edition = _doc(service, world["first_close"]["reviewed_edition_revision_id"]) or {}
    if sorted(a["entity_id"] for a in first_edition.get("approved") or []) != sorted(
        expected["approved"]
    ):
        errors.append("首审 approved 与 expected 不符")
    if sorted(a["entity_id"] for a in first_edition.get("rejected") or []) != sorted(
        expected["rejected"]
    ):
        errors.append("首审 rejected 与 expected 不符")

    for label, revision_id in (
        ("首审", world["first_close"]["reviewed_edition_revision_id"]),
        ("复审", world["rework_close"]["reviewed_edition_revision_id"]),
    ):
        edition = _doc(service, revision_id) or {}
        for link in edition.get("evidence_links") or []:
            spans = _spans_map(service, link.get("corpus_spans_revision_id"))
            span = spans.get(link.get("source_span_id"))
            if span is None:
                errors.append("%s 证据引文 Span 不存在" % label)
                continue
            quote = span.get("text", "")[link.get("start", 0) : link.get("end", 0)]
            if hashlib.sha256(quote.encode("utf-8")).hexdigest() != link.get("quote_sha256"):
                errors.append("%s 证据引文哈希不符" % label)
    return errors


def _check_transformation_record(world):
    service = world["service"]
    errors = []
    for response in (world["first_close"], world["rework_close"], world["propagation"]):
        step_run_id = response["step_run_id"]
        step = service.get_step_run(step_run_id)
        if step["status"] != "succeeded":
            errors.append("运行非 succeeded: %s" % step_run_id)
        manifest = service.list_step_run_revisions(
            step_run_id, artifact_type="step_manifest"
        )
        if not manifest:
            errors.append("运行无 StepManifest: %s" % step_run_id)
        frozen = set(_frozen_inputs(service, step_run_id))
        for transformation in service.list_transformations(step_run_id):
            if transformation["operation"] not in (
                "review_candidates",
                "propagate_invalidation",
            ):
                continue
            transformation_id = transformation["id"]
            if not transformation.get("tool") or not transformation.get("tool_version"):
                errors.append("Transformation tool/version 为空")
            if _artifact_type(service, transformation["configuration_revision_id"]) != "configuration":
                errors.append("Transformation 配置非 configuration")
            report = transformation.get("validation_report_revision_id")
            if not report or _artifact_type(service, report) != "validation_report":
                errors.append("Transformation 校验报告缺失或类型不符")
            inputs = service.list_transformation_inputs(transformation_id)
            if not inputs:
                errors.append("Transformation 输入为空")
            own_sealed = {
                row["artifact_revision_id"]
                for row in service.list_revisions(
                    status="sealed", step_run_ids=[step_run_id]
                )
            }
            extra = set(inputs) - (frozen | own_sealed)
            if extra:
                errors.append("Transformation 输入既非冻结输入也非本运行产出: %s" % sorted(extra))
            outputs = service.list_transformation_outputs(transformation_id)
            for revision_id in outputs:
                row = service.get_revision(revision_id)
                if row is None or row["status"] != "sealed":
                    errors.append("Transformation 输出未 sealed: %s" % revision_id)
            human_events = set(
                service.list_transformation_human_events(transformation_id)
            )
            for revision_id in human_events:
                if _artifact_type(service, revision_id) != "human_event":
                    errors.append("Transformation 人工事件类型不符: %s" % revision_id)
            own = set(_human_event_revs(service, step_run_id))
            if not own.issubset(human_events):
                errors.append("Transformation 漏记本运行人工事件: %s" % sorted(own - human_events))
    return errors


def _check_recovery_replays_pending_only(world):
    service = world["service"]
    errors = []
    recovery = world["recovery"]
    old_step_run_id = world["first_open"]["step_run_id"]
    if recovery["supersedes_step_run_id"] != old_step_run_id:
        errors.append("恢复运行未 supersede 首审运行")
    inherited = set(recovery["carried_decision_revision_ids"])
    replayed = set(_human_event_revs(service, recovery["step_run_id"]))
    if inherited & replayed:
        errors.append("继承决定在恢复运行重录: %s" % sorted(inherited & replayed))

    old_pending = _old_pending_queue(world)
    recovery_checkpoints = _own_checkpoints(
        service, world["edition_part_id"], recovery["step_run_id"]
    )
    if not recovery_checkpoints:
        errors.append("恢复运行无 Checkpoint")
        return errors
    first_pending = {
        item["task_id"]
        for item in (recovery_checkpoints[0]["content"].get("pending_queue") or [])
    }
    if first_pending != old_pending:
        errors.append("恢复运行首个 Checkpoint pending 与旧运行未决项不符")
    return errors


def _old_pending_queue(world):
    """旧（首审）运行尚未决定的队列项。"""
    service = world["service"]
    queue = _doc(service, world["first_open"]["queue_revision_id"]) or []
    decided_entities = set()
    for revision_id, decision_type in [
        (row["event_revision_id"], row["decision_type"])
        for row in service.list_human_events(world["first_open"]["step_run_id"])
    ]:
        if decision_type is None:
            continue
        doc = _doc(service, revision_id) or {}
        if doc.get("event_kind") == "review_decision":
            decided_entities.add(doc["target"]["entity_id"])
    return {
        item["queue_item_id"]
        for item in queue
        if item["target_entity_id"] not in decided_entities
    }


def _check_precise_invalidation(world):
    service = world["service"]
    expected = world["expected"]["rework"]
    errors = []
    report_revision_id = world["propagation"]["rework_impact_report_revision_id"]
    report = _doc(service, report_revision_id) or {}
    for key in (
        "invalidated_count",
        "carried_forward_count",
        "needs_review_count",
        "valid_object_count",
        "invalidated_ratio",
        "warnings",
        "rework_round",
    ):
        if report.get(key) != expected.get(key):
            errors.append("报告 %s != expected: %r != %r" % (key, report.get(key), expected.get(key)))
    if sorted(report.get("changed_span_ids") or []) != sorted(expected.get("changed_span_ids") or []):
        errors.append("报告 changed_span_ids != expected")
    if sorted(report.get("reachable_entity_ids") or []) != sorted(
        expected.get("reachable_entity_ids") or []
    ):
        errors.append("报告 reachable_entity_ids != expected")

    old_spans = _spans_map(service, world["seed"]["spans_revision_id"])
    new_spans = _spans_map(service, world["seed_corrected"]["new_corpus_spans_revision_id"])
    candidate_set = _doc(service, world["seed"]["candidate_set_revision_id"]) or {}
    changed, _removed, reachable = _changed_and_reachable(old_spans, new_spans, candidate_set)
    if changed != sorted(report.get("changed_span_ids") or []):
        errors.append("独立重算变更 Span 不一致")
    if reachable != sorted(report.get("reachable_entity_ids") or []):
        errors.append("独立重算可达对象不一致")

    referenced = service.count_checkpoints_by_rework_report(report_revision_id)
    if referenced < 1:
        errors.append("无 Checkpoint 引用该报告")
    return errors


def _check_no_cross_module_status_change(world):
    service = world["service"]
    errors = []
    invalidated = service.list_revisions(status="invalidated")
    if invalidated:
        errors.append(
            "存在被置为 invalidated 的修订: %s"
            % [row["artifact_revision_id"] for row in invalidated]
        )
    old_candidate_set = world["seed"]["candidate_set_revision_id"]
    row = service.get_revision(old_candidate_set)
    if row["status"] != "superseded":
        errors.append("旧 candidate_set 未被 supersede: %s" % row["status"])
    successor = service.list_revisions(prev_revision_id=old_candidate_set)
    if not successor:
        errors.append("旧 candidate_set 无后继修订")
    return errors


def _check_rework_rereview_scope(world):
    service = world["service"]
    expected = world["expected"]["rereview"]
    errors = []
    queue = _doc(service, world["rework_open"]["queue_revision_id"]) or []
    if [item["queue_item_id"] for item in queue] != list(expected["queue"]):
        errors.append("复审队列 != expected.rereview.queue")
    edition = _doc(service, world["rework_close"]["reviewed_edition_revision_id"]) or {}
    standings = [decision["standing"] for decision in edition.get("decisions") or []]
    if standings.count("active") != expected["active"]:
        errors.append("复审 active 数 != expected")
    if standings.count("carried_forward") != expected["carried_forward"]:
        errors.append("复审 carried_forward 数 != expected")
    old_candidate_set = world["seed"]["candidate_set_revision_id"]
    for decision in edition.get("decisions") or []:
        if decision.get("standing") != "carried_forward":
            continue
        if decision.get("seen_artifact_revision_id") != old_candidate_set:
            errors.append("carried 条目 seen 未保持首审旧修订")
        if decision.get("carried_from_revision_id") != decision.get("decision_revision_id"):
            errors.append("carried_from 与决定修订不符")
        if decision.get("carried_to_revision_id") != world["seed_rerun"]["candidate_set_revision_id"]:
            errors.append("carried_to 非复审当前候选修订")
        if decision.get("trigger_correction_request_id") != world["correction_request_revision_id"]:
            errors.append("carried 条目缺 trigger_correction_request_id")
    ack = world["rework_open"].get("acknowledgement_revision_id")
    ack_doc = _doc(service, ack) if ack else {}
    if (ack_doc or {}).get("event_kind") != "rework_threshold_ack":
        errors.append("阈值确认事件缺失或类型不符")
    return errors


def _check_snapshot_projection(world) -> list[str]:
    """真实 M6 产出驱动 M7 产出 Snapshot，独立核对投影（第 83 条）。"""
    from pipeline.assembly.model import validate_snapshot_knowledge
    from pipeline.assembly.step import run_m7 as _run_m7

    errors = []
    service = world["service"]
    edition_part_id = world["edition_part_id"]

    # 1. 查找 m6 StagePackage 与 reviewed_edition
    if "rework_close" in world and world["rework_close"]:
        m6_pkg_rev_id = world["rework_close"]["package_revision_id"]
        re_rev_id = world["rework_close"]["reviewed_edition_revision_id"]
    elif "first_close" in world and world["first_close"]:
        m6_pkg_rev_id = world["first_close"]["package_revision_id"]
        re_rev_id = world["first_close"]["reviewed_edition_revision_id"]
    else:
        # list_stage_packages 按 r.created_at, r.rowid 升序（写入顺序），末行即最近写入的 m6 包
        packages = service.list_stage_packages("m6")
        if not packages:
            return ["未找到 m6 StagePackage"]
        m6_pkg_rev_id = packages[-1]["artifact_revision_id"]
        pkg_doc = _doc(service, m6_pkg_rev_id) or {}
        re_rev_id = pkg_doc.get("payload", {}).get("reviewed_edition_revision_id")
        if not re_rev_id:
            return ["m6 StagePackage payload 缺少 reviewed_edition_revision_id"]

    re_doc = _doc(service, re_rev_id)
    if not re_doc:
        return ["未找到 reviewed_edition: %s" % re_rev_id]

    # 2. 运行或获取 Snapshot 修订
    snap_rev_id = world.get("snapshot_revision_id")
    if not snap_rev_id:
        try:
            res = _run_m7(
                service, edition_part_id, technique_id="qizheng",
                reviewed_package_revision_ids=[m6_pkg_rev_id],
                base_snapshot_revision_id=None,
            )
            if res.get("status") != "succeeded":
                return ["run_m7 未成功: %r" % res.get("failed_check")]
            snap_rev_id = res["snapshot_revision_id"]
            world["snapshot_revision_id"] = snap_rev_id
        except Exception as exc:
            return ["run_m7 异常: %s" % exc]

    snap_rev = service.get_revision(snap_rev_id)
    if not snap_rev:
        return ["未找到 Snapshot 修订: %s" % snap_rev_id]
    snap_doc = json.loads(service.read_object(snap_rev["sha256"]).decode("utf-8"))
    k = snap_doc.get("knowledge", snap_doc)

    # 独立核对四项（不复用 run_m7 返回的 gate/report）：
    # 1. reviewed_edition.approved 的 entity_id 集合，与 Snapshot knowledge 中对应对象的 ID 集合按 kind 分别比对
    approved_by_kind = {"assertion": set(), "pattern": set(), "school_view": set(), "concept": set()}
    for a in re_doc.get("approved", []):
        kind = a.get("kind")
        if kind in approved_by_kind:
            approved_by_kind[kind].add(a["entity_id"])
        else:
            errors.append("approved 包含未知 kind: %s" % kind)

    snap_assertion_ids = {a["assertion_id"] for a in k.get("assertions", [])}
    snap_pattern_ids = {p["pattern_id"] for p in k.get("patterns", [])}
    snap_sv_ids = {sv["school_view_id"] for sv in k.get("school_views", [])}
    snap_concept_ids = {c["concept_id"] for c in k.get("concepts", [])}

    if approved_by_kind["assertion"] != snap_assertion_ids:
        errors.append(
            "approved assertions 与 Snapshot assertions 不符: approved=%s vs snap=%s"
            % (sorted(approved_by_kind["assertion"]), sorted(snap_assertion_ids))
        )
    if approved_by_kind["pattern"] != snap_pattern_ids:
        errors.append(
            "approved patterns 与 Snapshot patterns 不符: approved=%s vs snap=%s"
            % (sorted(approved_by_kind["pattern"]), sorted(snap_pattern_ids))
        )
    if approved_by_kind["school_view"] != snap_sv_ids:
        errors.append(
            "approved school_views 与 Snapshot school_views 不符: approved=%s vs snap=%s"
            % (sorted(approved_by_kind["school_view"]), sorted(snap_sv_ids))
        )
    if approved_by_kind["concept"] != snap_concept_ids:
        errors.append(
            "approved concepts 与 Snapshot concepts 不符: approved=%s vs snap=%s"
            % (sorted(approved_by_kind["concept"]), sorted(snap_concept_ids))
        )

    # 2. Snapshot 修订中 evidence_links 的 source_span_id 与 reviewed_edition.evidence_links 一致
    re_evidence = {e["source_span_id"] for e in re_doc.get("evidence_links", [])}
    snap_evidence = set()
    for item in (k.get("assertions", []) + k.get("patterns", []) + k.get("school_views", []) + k.get("concepts", [])):
        for ev in item.get("evidence", []):
            span_id = ev.get("source_span_id")
            if span_id:
                snap_evidence.add(span_id)
    if re_evidence != snap_evidence:
        errors.append(
            "evidence_links 不一致: reviewed_edition=%s vs Snapshot=%s"
            % (sorted(re_evidence), sorted(snap_evidence))
        )

    # 3. Snapshot 修订中 content_status 在 approved 对象上投影为 expert_verified
    for a in k.get("assertions", []):
        if a["assertion_id"] in approved_by_kind["assertion"]:
            if a.get("content_status") != "expert_verified":
                errors.append(
                    "approved assertion %s content_status 非 expert_verified: %s"
                    % (a["assertion_id"], a.get("content_status"))
                )
    for p in k.get("patterns", []):
        if p["pattern_id"] in approved_by_kind["pattern"]:
            if p.get("content_status") != "expert_verified":
                errors.append(
                    "approved pattern %s content_status 非 expert_verified: %s"
                    % (p["pattern_id"], p.get("content_status"))
                )
    for sv in k.get("school_views", []):
        if sv["school_view_id"] in approved_by_kind["school_view"]:
            if sv.get("content_status") != "expert_verified":
                errors.append(
                    "approved school_view %s content_status 非 expert_verified: %s"
                    % (sv["school_view_id"], sv.get("content_status"))
                )
    for c in k.get("concepts", []):
        if c["concept_id"] in approved_by_kind["concept"]:
            if c.get("content_status") != "expert_verified":
                errors.append(
                    "approved concept %s content_status 非 expert_verified: %s"
                    % (c["concept_id"], c.get("content_status"))
                )

    # 4. reviewed_edition.rejected 的 entity_id 不得出现在 Snapshot knowledge 的任何对象 ID 中
    rejected_ids = {r["entity_id"] for r in re_doc.get("rejected", [])}
    all_snap_ids = snap_assertion_ids | snap_pattern_ids | snap_sv_ids | snap_concept_ids
    leaked = rejected_ids & all_snap_ids
    if leaked:
        errors.append("rejected entity_id 出现在 Snapshot 中: %s" % sorted(leaked))

    # 5. Schema 校验
    try:
        validate_snapshot_knowledge(k)
    except Exception as exc:
        errors.append("validate_snapshot_knowledge 失败: %s" % exc)

    return errors


def _check_first_review_counts(world) -> list[str]:
    """比对金标 expected.first_review.decisions 计数与实际 m6 运行的 Checkpoint 中 human_decisions 计数。"""
    errors = []
    service = world["service"]
    expected = world.get("expected", {})
    first_review = expected.get("first_review", {})
    exp_decisions = first_review.get("decisions")
    if exp_decisions is None:
        return errors

    if isinstance(exp_decisions, list):
        expected_count = len(exp_decisions)
    elif isinstance(exp_decisions, int):
        expected_count = exp_decisions
    else:
        errors.append("expected.first_review.decisions 类型未知: %r" % type(exp_decisions))
        return errors

    # 统计首审关联 step runs 的 Checkpoints 中 human_decisions（review_decision 计数）
    first_steps = set()
    if "first_open" in world and world["first_open"]:
        first_steps.add(world["first_open"]["step_run_id"])

    if "recovery" in world and world["recovery"]:
        first_steps.add(world["recovery"]["step_run_id"])
    if "first_close" in world and world["first_close"]:
        first_steps.add(world["first_close"]["step_run_id"])

    cps = service.list_checkpoints(world["edition_part_id"], "m6")
    first_cps = [cp for cp in cps if cp.get("step_run_id") in first_steps]
    human_decisions = set()
    for cp in first_cps:
        for rev in cp.get("content", {}).get("human_decisions") or []:
            doc = _doc(service, rev)
            if doc and doc.get("event_kind") == "review_decision":
                human_decisions.add(rev)
    human_count = len(human_decisions)

    if expected_count != human_count:
        errors.append(
            "first_review.decisions 计数 %d != human_decisions 计数 %d"
            % (expected_count, human_count)
        )
    return errors


COMPUTED_CHECKS = (
    ("inputs_frozen", _check_inputs_frozen),
    ("queue_from_upstream", _check_queue_from_upstream),
    ("decisions_as_human_events", _check_decisions_as_human_events),
    ("checkpoint_per_decision", _check_checkpoint_per_decision),
    ("decision_anchor_fields", _check_decision_anchor_fields),
    ("reviewed_edition_contract", _check_reviewed_edition_contract),
    ("transformation_record", _check_transformation_record),
    ("recovery_replays_pending_only", _check_recovery_replays_pending_only),
    ("precise_invalidation", _check_precise_invalidation),
    ("no_cross_module_status_change", _check_no_cross_module_status_change),
    ("rework_rereview_scope", _check_rework_rereview_scope),
    ("snapshot_projection", _check_snapshot_projection),
    ("first_review_counts", _check_first_review_counts),
)


# ------------------------------------------------------------------ 准备
def _prepare(fixture_dir, expected_path):
    tmp = tempfile.mkdtemp(prefix="m6-acceptance-")
    service = LedgerService(Path(tmp) / "ledger")
    seed = seed_upstream(service, fixture_dir)
    edition_part_id = seed["edition_part_id"]
    corrections = load_data("corrections")
    decisions = load_data("m6_decisions")["decisions"]

    def _record(step_run_id, token, decision):
        return _step.record_decision(
            service,
            step_run_id,
            token,
            queue_item_id=decision["queue_item_id"],
            verdict=decision["verdict"],
            rationale=decision["rationale"],
            modified_content=decision.get("modified_content"),
        )

    # 1) open_review → 2) request_correction
    first_open = _step.open_review(service, edition_part_id)
    first_step_run_id = first_open["step_run_id"]
    first_token = first_open["resume_token"]
    correction = _rework.request_correction(
        service,
        first_step_run_id,
        first_token,
        source_span_ids=list(corrections["correction_request"]["source_span_ids"]),
        description=corrections["correction_request"]["description"],
    )

    # 3) 前 2 条决定；第 2 条之后注入 write_checkpoint 异常并恢复
    _record(first_step_run_id, first_token, decisions[0])
    original_write_checkpoint = service.write_checkpoint

    def _crash(*args, **kwargs):
        raise RuntimeError("acceptance 注入：write_checkpoint 失败")

    service.write_checkpoint = _crash
    try:
        _record(first_step_run_id, first_token, decisions[1])
    except RuntimeError:
        pass
    finally:
        service.write_checkpoint = original_write_checkpoint
    recovery = _step.recover_review(
        service, edition_part_id, reason="acceptance_injected_crash"
    )

    # 4) 恢复运行上完成其余决定 → close_review
    for decision in decisions[2:]:
        _record(recovery["step_run_id"], recovery["resume_token"], decision)
    first_close = _step.close_review(
        service, recovery["step_run_id"], recovery["resume_token"]
    )
    if first_close.get("status") != "succeeded":
        raise RuntimeError("首审 close_review 未成功: %r" % first_close.get("failed_check"))

    # 5) 修正语料 → 失效传播
    seed_corrected = seed_corrected_corpus(service, edition_part_id, corrections)
    propagation = _rework.run_rework_propagation(
        service,
        edition_part_id,
        correction_request_revision_id=correction["correction_request_revision_id"],
        new_corpus_package_revision_id=seed_corrected["new_corpus_package_revision_id"],
    )
    if propagation.get("status") != "succeeded":
        raise RuntimeError("失效传播未成功: %r" % propagation.get("failed_check"))

    # 6) M4'/M5' 重跑 → 复审 → 重放 needs_review 项 → 结审
    seed_rerun = seed_rerun_m4_m5(
        service,
        edition_part_id,
        rework_impact_report_revision_id=propagation[
            "rework_impact_report_revision_id"
        ],
    )
    rework_open = _rework.open_rework_review(
        service,
        edition_part_id,
        rework_impact_report_revision_id=propagation[
            "rework_impact_report_revision_id"
        ],
        acknowledge_rework_warning=True,
    )
    for item in rework_open["queue"]:
        _step.record_decision(
            service,
            rework_open["step_run_id"],
            rework_open["resume_token"],
            queue_item_id=item["queue_item_id"],
            verdict="accept",
            rationale="复审通过",
        )
    rework_close = _step.close_review(
        service, rework_open["step_run_id"], rework_open["resume_token"]
    )
    if rework_close.get("status") != "succeeded":
        raise RuntimeError("复审 close_review 未成功: %r" % rework_close.get("failed_check"))

    expected = yaml.safe_load(Path(expected_path).read_text(encoding="utf-8"))
    world = {
        "service": service,
        "edition_part_id": edition_part_id,
        "fixture_dir": Path(fixture_dir),
        "seed": seed,
        "corrections": corrections,
        "first_open": first_open,
        "correction_request_revision_id": correction["correction_request_revision_id"],
        "recovery": recovery,
        "first_close": first_close,
        "seed_corrected": seed_corrected,
        "propagation": propagation,
        "seed_rerun": seed_rerun,
        "rework_open": rework_open,
        "rework_close": rework_close,
        "expected": expected,
    }
    return tmp, service, world


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pipeline.review.acceptance")
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--expected", default=None)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args(argv)

    if yaml is None or jsonschema is None:
        print("BLOCKED m6_acceptance 前置缺失: 测试宿主匮乏；yaml/jsonschema 不可导入")
        print("SUMMARY pass=0 fail=0 blocked=1")
        return 3

    fixture_dir = Path(args.fixture)
    if not (fixture_dir / "manifest.yaml").exists():
        print("BLOCKED m6_acceptance 前置缺失: fixture manifest %s" % (fixture_dir / "manifest.yaml"))
        print("SUMMARY pass=0 fail=0 blocked=1")
        return 3
    expected_path = Path(args.expected) if args.expected else DEFAULT_EXPECTED

    try:
        tmp, service, world = _prepare(fixture_dir, expected_path)
    except Exception as exc:  # noqa: BLE001 —— 宿主准备失败统一 exit 1
        print("FAIL m6_acceptance 宿主准备失败: %s: %s" % (type(exc).__name__, exc))
        return 1

    passed = 0
    failed = 0
    blocked = 0
    try:
        for name, func in COMPUTED_CHECKS:
            try:
                errors = func(world)
            except Exception as exc:  # noqa: BLE001 —— 判定自身异常转该项 FAIL
                errors = ["%s: %s" % (type(exc).__name__, exc)]
            if errors:
                failed += 1
                print("FAIL %s %s" % (name, "; ".join(str(err) for err in errors[:3])))
            else:
                passed += 1
                print("PASS %s" % name)
        for name, text in BLOCKED_CHECKS:
            blocked += 1
            print("BLOCKED %s %s" % (name, text))
    finally:
        service.close()
        if not args.keep:
            shutil.rmtree(tmp, True)

    print("SUMMARY pass=%d fail=%d blocked=%d" % (passed, failed, blocked))
    if failed:
        return 1
    if blocked:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
