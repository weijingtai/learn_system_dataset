"""M4 m4-stage-gate 验收（规格 §19.0 判据）：十六项判定（13 PASS + 3 BLOCKED）。

本模块**不** import ``assemble`` / ``gate`` / ``submission``；判定只读 Ledger 与
fixture/金标，不信任 ``run_m4`` / ``resume_m4`` 返回的 Gate 报告。依赖真实
``expert_verified`` 签发的判定一律 BLOCKED（P7）；金标中的合成人工事件不计入
真实 ``expert_verified``。
"""

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

import jsonschema
import yaml
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from pipeline.corpus_compiler.step import run_m3
from pipeline.ledger.fixture_ingest import ingest
from pipeline.ledger.service import LedgerService

from .adapters.registry import register_technique_profile
from .step import record_category_ruling, resume_m4, run_m4
from .submit import run_m4_submit

FIVE = (
    "assertions",
    "patterns",
    "school_views",
    "concept_mentions",
    "new_concept_candidates",
)
M4_STATUS_CEILING = ("machine_extracted", "disputed", "needs_expert")
GATE_PROFILE = "thin_no_model"

# 独立维护的类别键表（逐字等于 act/00 ITEM_KEYS）
ITEM_KEYS = {
    "assertion": {
        "required": ("proposition", "relation", "evidence"),
        "optional": ("conditions", "exceptions", "concept_refs", "school_ids", "layer", "status"),
    },
    "pattern": {
        "required": ("name", "assertion_propositions", "evidence"),
        "optional": ("interpretation", "status"),
    },
    "school_view": {
        "required": (
            "school_id",
            "subject",
            "claim_propositions",
            "changes_current_judgment",
            "evidence",
        ),
        "optional": ("conflict_key", "status"),
    },
    "concept_mention": {
        "required": ("surface", "evidence"),
        "optional": ("concept_ref", "status"),
    },
}

# 自行正则（不 import gate）
ID_PATTERNS = {
    "assertion_id": re.compile(r"^as_[a-z][a-z0-9]*_[0-9]{6}$"),
    "proposition_id": re.compile(r"^pr_[a-z][a-z0-9]*_[0-9]{6}$"),
    "pattern_id": re.compile(r"^pat_[a-z][a-z0-9]*_[0-9]{6}$"),
    "school_view_id": re.compile(r"^sv_[0-9a-f]{32}$"),
    "conflict_group_id": re.compile(r"^cg_[0-9a-f]{32}$"),
}

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CANON_DIR = REPO_ROOT / "pipeline" / "schemas" / "shared" / "canon"
SCHEMA_DIR = REPO_ROOT / "openspec" / "schemas"

EXPECTED_ASSERTIONS = [
    ("as_qizheng_000001", "宋錢如璧撰"),
    ("as_qizheng_000002", "三辰通載三十卷"),
]
CHECK_ORDER = (
    "lane_assertion_a",
    "lane_assertion_b",
    "lane_concept_mention_a",
    "reconcile",
    "m4_d001",
    "assemble",
)

BLOCKED_CHECKS = (
    (
        "cross_model_extraction",
        "前置缺失: M4 Knowledge Extraction；生产模型 A/B 独立抽取与复核模型 C（§12.2）未接入 Model Adapter，本批为无模型薄接入",
    ),
    (
        "semantic_span_input",
        "前置缺失: M3 Corpus Compilation；SemanticSpan 未实现，M4 以 StructuralSpan 薄接入（span_layer=structural）",
    ),
    (
        "term_layering_scan",
        "前置缺失: Contract Registry；schemas/shared/homographs 与 qizheng 术语表不存在，L1/L2/L3 自动判层未实现（本批只校验提交件自带 concept_ref）",
    ),
)


# ------------------------------------------------------------------ 只读工具
def _revision_bytes(service, revision_id):
    row = service.get_revision(revision_id)
    return service.objects.get(row["sha256"])


def _doc(service, revision_id):
    text = _revision_bytes(service, revision_id).decode("utf-8")
    try:
        return json.loads(text)
    except ValueError:
        return yaml.safe_load(text)


def _iter_evidence(candidate_set):
    for key in FIVE:
        for obj in candidate_set.get(key) or []:
            for evidence in obj.get("evidence") or []:
                yield "%s/%s" % (key, obj.get("origin", {}).get("item_index")), evidence


def _page_blocks(spans_doc):
    order = []
    grouped = {}
    for span in spans_doc["spans"]:
        page = span["page"]
        if page not in grouped:
            grouped[page] = []
            order.append(page)
        grouped[page].append(span["text"])
    return {page: "\n".join(grouped[page]) for page in order}


def _m4_step_runs(world):
    return {row["step_run_id"] for row in world["submits"]} | {world["final"]["step_run_id"]}


def _own_checkpoints(service, world, step_run_id):
    return [
        row
        for row in service.list_checkpoints(world["edition_part_id"], "m4")
        if row["content"]["step_run_id"] == step_run_id
    ]


# ------------------------------------------------------------------ 十六项
def _check_inputs_frozen(world):
    service = world["service"]
    final = world["final"]
    errors = []
    if final.get("status") != "succeeded":
        errors.append("assemble resume status != succeeded: %r" % (final.get("status"),))
    step = final["step_run_id"]
    frozen = set(service._frozen_input_ids(step))
    m3 = world["m3"]
    expected = {
        m3["package_revision_id"],
        m3["corpus_package_revision_id"],
        m3["spans_revision_id"],
        world["profile_revision_id"],
    }
    expected |= {row["submission_revision_id"] for row in world["submits"]}
    if frozen != expected:
        errors.append("frozen_inputs 不符: %s" % sorted(frozen ^ expected))
    for revision_id in frozen:
        row = service.get_revision(revision_id)
        if row is None or row["status"] != "sealed":
            errors.append("冻结修订未 sealed: %s" % revision_id)
    return errors


def _check_lane_isolation(world):
    service = world["service"]
    m3 = world["m3"]
    errors = []
    for submit in world["submits"]:
        frozen = set(service._frozen_input_ids(submit["step_run_id"]))
        if frozen != {m3["package_revision_id"], m3["spans_revision_id"]}:
            errors.append("submit %s 冻结输入不符: %s" % (submit["step_run_id"], sorted(frozen)))
        for revision_id in frozen:
            artifact_type = service.store.conn.execute(
                "SELECT a.artifact_type FROM artifact_revisions r "
                "JOIN artifacts a ON a.artifact_id = r.artifact_id "
                "WHERE r.artifact_revision_id=?",
                (revision_id,),
            ).fetchone()[0]
            if artifact_type == "candidate_submission":
                errors.append("submit 冻结输入含 candidate_submission: %s" % revision_id)
    if world["submits"][0]["step_run_id"] == world["submits"][1]["step_run_id"]:
        errors.append("assertion a/b 属同一 StepRun")
    return errors


def _check_evidence_resolvable(world):
    service = world["service"]
    spans_doc = _doc(service, world["m3"]["spans_revision_id"])
    span_map = {span["span_id"]: span for span in spans_doc["spans"]}
    errors = []
    for label, evidence in _iter_evidence(world["candidate_set"]):
        span = span_map.get(evidence.get("source_span_id"))
        if span is None:
            errors.append("%s 未知 Span: %r" % (label, evidence.get("source_span_id")))
            continue
        start = evidence.get("start_offset")
        end = evidence.get("end_offset")
        if not isinstance(start, int) or not isinstance(end, int) or not (
            span["start_offset"] <= start < end <= span["end_offset"]
        ):
            errors.append("%s offset 越出 Span" % label)
    return errors


def _check_quote_fidelity(world):
    service = world["service"]
    spans_doc = _doc(service, world["m3"]["spans_revision_id"])
    span_map = {span["span_id"]: span for span in spans_doc["spans"]}
    blocks = _page_blocks(spans_doc)
    errors = []
    for label, evidence in _iter_evidence(world["candidate_set"]):
        quote = evidence.get("quote")
        if not isinstance(quote, str):
            errors.append("%s quote 非字符串" % label)
            continue
        if hashlib.sha256(quote.encode("utf-8")).hexdigest() != evidence.get("quote_sha256"):
            errors.append("%s quote_sha256 不一致" % label)
        span = span_map.get(evidence.get("source_span_id"))
        start = evidence.get("start_offset")
        end = evidence.get("end_offset")
        if span is None or not isinstance(start, int) or not isinstance(end, int):
            continue
        if blocks.get(span["page"], "")[start:end] != quote:
            errors.append("%s 页块切片 != quote" % label)
    return errors


def _check_evidence_required(world):
    errors = []
    for key in FIVE:
        for index, obj in enumerate(world["candidate_set"].get(key) or []):
            if not obj.get("evidence"):
                errors.append("%s[%d] evidence 为空" % (key, index))
    return errors


def _check_identity(world):
    service = world["service"]
    candidate_set = world["candidate_set"]
    config = _doc(service, world["final"]["configuration_revision_id"])
    id_range = (config or {}).get("id_range") or {}
    technique_id = candidate_set.get("technique_id")
    errors = []

    def matches(kind, value):
        pattern = ID_PATTERNS.get(kind)
        return bool(pattern and isinstance(value, str) and pattern.match(value))

    seen = set()
    for index, row in enumerate(candidate_set.get("assertions") or []):
        assertion_id = row.get("assertion_id")
        proposition_id = row.get("proposition_id")
        if not matches("assertion_id", assertion_id):
            errors.append("assertions[%d] assertion_id 非法" % index)
        if not matches("proposition_id", proposition_id):
            errors.append("assertions[%d] proposition_id 非法" % index)
        if isinstance(assertion_id, str) and isinstance(proposition_id, str):
            if assertion_id.rsplit("_", 1)[-1] != proposition_id.rsplit("_", 1)[-1]:
                errors.append("assertions[%d] as/pr 号不一致" % index)
        if isinstance(assertion_id, str):
            if assertion_id in seen:
                errors.append("assertions[%d] as_ 重复" % index)
            seen.add(assertion_id)
            number = int(assertion_id.rsplit("_", 1)[-1])
            bounds = id_range.get("assertion")
            if bounds and not (bounds[0] <= number <= bounds[1]):
                errors.append("assertions[%d] as_ 越出 id_range" % index)
            parts = assertion_id.split("_")
            if len(parts) >= 3 and parts[1] != technique_id:
                errors.append("assertions[%d] 技法段不符" % index)
    pattern_seen = set()
    for index, row in enumerate(candidate_set.get("patterns") or []):
        pattern_id = row.get("pattern_id")
        if not matches("pattern_id", pattern_id):
            errors.append("patterns[%d] pattern_id 非法" % index)
        if isinstance(pattern_id, str):
            if pattern_id in pattern_seen:
                errors.append("patterns[%d] pat_ 重复" % index)
            pattern_seen.add(pattern_id)
            number = int(pattern_id.rsplit("_", 1)[-1])
            bounds = id_range.get("pattern")
            if bounds and not (bounds[0] <= number <= bounds[1]):
                errors.append("patterns[%d] pat_ 越出 id_range" % index)
    sv_seen = set()
    for index, row in enumerate(candidate_set.get("school_views") or []):
        school_view_id = row.get("school_view_id")
        if not matches("school_view_id", school_view_id):
            errors.append("school_views[%d] school_view_id 非法" % index)
        if isinstance(school_view_id, str):
            if school_view_id in sv_seen:
                errors.append("school_views[%d] sv_ 重复" % index)
            sv_seen.add(school_view_id)
        conflict_group_id = row.get("conflict_group_id")
        if conflict_group_id is not None and not matches("conflict_group_id", conflict_group_id):
            errors.append("school_views[%d] conflict_group_id 非法" % index)
    return errors


def _check_status_ceiling(world):
    service = world["service"]
    candidate_set = world["candidate_set"]
    errors = []
    for key in FIVE:
        for index, obj in enumerate(candidate_set.get(key) or []):
            if obj.get("content_status") not in M4_STATUS_CEILING:
                errors.append("%s[%d] content_status 越权" % (key, index))
    placeholders = ",".join("?" * len(_m4_step_runs(world)))
    rows = service.store.conn.execute(
        "SELECT r.artifact_revision_id FROM artifact_revisions r WHERE r.step_run_id IN (%s)"
        % placeholders,
        tuple(_m4_step_runs(world)),
    ).fetchall()
    for (revision_id,) in rows:
        data = _revision_bytes(service, revision_id)
        if b"expert_verified" in data or b"cross_model_reviewed" in data:
            errors.append("m4 修订含越权状态字节: %s" % revision_id)
    return errors


def _check_category_separation(world):
    service = world["service"]
    errors = []
    for submit in world["submits"]:
        doc = _doc(service, submit["submission_revision_id"])
        category = doc.get("category")
        if category not in ITEM_KEYS:
            errors.append("提交件类别非法: %r" % (category,))
            continue
        allowed = set(ITEM_KEYS[category]["required"]) | set(ITEM_KEYS[category]["optional"])
        for index, item in enumerate(doc.get("items") or []):
            extra = set(item) - allowed
            if extra:
                errors.append("提交件 %s items[%d] 含类别外键: %s" % (category, index, sorted(extra)))
    return errors


def _check_references(world):
    service = world["service"]
    profile = _doc(service, world["profile_revision_id"]) or {}
    concepts = {row["concept_id"] for row in (profile.get("canon") or {}).get("concepts") or []}
    concepts |= {row["concept_id"] for row in profile.get("glossary") or []}
    schools = {row["school_id"] for row in profile.get("schools") or []}
    candidate_set = world["candidate_set"]
    assertion_ids = {row.get("assertion_id") for row in candidate_set.get("assertions") or []}
    pattern_ids = {row.get("pattern_id") for row in candidate_set.get("patterns") or []}
    errors = []
    for index, row in enumerate(candidate_set.get("assertions") or []):
        for ref in row.get("concept_refs") or []:
            if ref not in concepts:
                errors.append("assertions[%d] concept_refs 未登记: %s" % (index, ref))
        for ref in row.get("school_ids") or []:
            if ref not in schools:
                errors.append("assertions[%d] school_ids 未登记: %s" % (index, ref))
    for index, row in enumerate(candidate_set.get("concept_mentions") or []):
        ref = row.get("concept_ref")
        if ref is not None and ref not in concepts:
            errors.append("concept_mentions[%d] concept_ref 未登记: %s" % (index, ref))
    for index, row in enumerate(candidate_set.get("patterns") or []):
        for ref in row.get("assertion_ids") or []:
            if ref not in assertion_ids:
                errors.append("patterns[%d] assertion_ids 悬空: %s" % (index, ref))
    for index, row in enumerate(candidate_set.get("school_views") or []):
        if row.get("subject_entity_id") not in assertion_ids | pattern_ids:
            errors.append("school_views[%d] subject_entity_id 悬空" % index)
        for ref in row.get("claim_refs") or []:
            if ref not in assertion_ids:
                errors.append("school_views[%d] claim_refs 悬空: %s" % (index, ref))
        if row.get("school_id") not in schools:
            errors.append("school_views[%d] school_id 未登记" % index)
    return errors


def _check_dispute_ruling(world):
    service = world["service"]
    step = world["final"]["step_run_id"]
    errors = []
    events = service.list_step_run_events(step)
    event_types = [event["event_type"] for event in events]
    disputes = world["candidate_set"].get("disputes") or []
    await_idx = [i for i, kind in enumerate(event_types) if kind == "await_human"]
    human_idx = [i for i, kind in enumerate(event_types) if kind == "human_event"]
    resume_idx = [i for i, kind in enumerate(event_types) if kind == "resume"]
    if len(await_idx) != 1:
        errors.append("await_human 事件数不为 1: %d" % len(await_idx))
    if len(resume_idx) != 1:
        errors.append("resume 事件数不为 1: %d" % len(resume_idx))
    if len(human_idx) != len(disputes):
        errors.append("human_event 数 %d != disputes 数 %d" % (len(human_idx), len(disputes)))
    if await_idx and human_idx and resume_idx and not (
        await_idx[-1] < human_idx[0] and human_idx[-1] < resume_idx[-1]
    ):
        errors.append("事件顺序非 await_human → human_event → resume")
    rows = service.store.conn.execute(
        "SELECT decision_type FROM human_events WHERE step_run_id=?", (step,)
    ).fetchall()
    if any(row[0] is not None for row in rows):
        errors.append("human_events.decision_type 非 NULL")
    events_registered = service.store.conn.execute(
        "SELECT event_revision_id FROM human_events WHERE step_run_id=? ORDER BY created_at, rowid",
        (step,),
    ).fetchall()
    own = _own_checkpoints(service, world, step)
    for (revision_id,) in events_registered:
        content = _doc(service, revision_id) or {}
        dispute_id = content.get("dispute_id")
        matched = [
            row
            for row in own
            if row["content"]["completed_tasks"]
            and row["content"]["completed_tasks"][0]["task_id"] == dispute_id
            and revision_id in row["content"]["human_decisions"]
        ]
        if not matched:
            errors.append("裁决 %s 后无对应 Checkpoint" % dispute_id)
    if [row.get("choice") for row in disputes] != [world["ruling"]["choice"]]:
        errors.append("candidate_set.disputes choice 与金标裁决不符")
    return errors


def _check_task_checkpoints(world):
    service = world["service"]
    errors = []
    chain = service.list_checkpoints(world["edition_part_id"], "m4")
    for previous, current in zip(chain, chain[1:]):
        if current.get("prev_checkpoint_revision_id") != previous["artifact_revision_id"]:
            errors.append("Checkpoint 链 prev 不连续")
            break
    own = _own_checkpoints(service, world, world["final"]["step_run_id"])
    order = [row["content"]["completed_tasks"][0]["task_id"] for row in own]
    if order != list(CHECK_ORDER):
        errors.append("assemble Checkpoint 顺序不符: %s" % order)
    manifest = _doc(service, world["final"]["step_manifest_revision_id"])
    if chain and manifest.get("last_checkpoint_revision_id") != chain[-1]["artifact_revision_id"]:
        errors.append("StepManifest.last_checkpoint_revision_id 非末个")
    for submit in world["submits"]:
        cps = _own_checkpoints(service, world, submit["step_run_id"])
        task = "submit_%s_%s" % (submit["category"], submit["lane"])
        if len(cps) != 1 or cps[0]["content"]["completed_tasks"][0]["task_id"] != task:
            errors.append("submit StepRun %s 的 Checkpoint 不符" % submit["step_run_id"])
    return errors


def _check_package_lineage(world):
    service = world["service"]
    errors = []
    package = _doc(service, world["final"]["package_revision_id"])
    try:
        _stage_package_validator().validate(package)
    except jsonschema.ValidationError as exc:
        errors.append("m4 StagePackage 未过 Schema: %s" % exc.message)
    if package.get("stage") != "m4":
        errors.append("StagePackage.stage != m4")
    candidate_bytes = _revision_bytes(service, world["final"]["candidate_set_revision_id"])
    if package.get("manifest", {}).get("content_sha256") != hashlib.sha256(candidate_bytes).hexdigest():
        errors.append("manifest.content_sha256 != sha256(candidate_set)")
    m3_refs = [
        ref
        for ref in package.get("manifest", {}).get("input_artifacts") or []
        if ref.get("artifact_kind") == "stage_package"
    ]
    if len(m3_refs) != 1:
        errors.append("M3 包输入 ArtifactRef 数不为 1")
    step = world["final"]["step_run_id"]
    lineage_inputs = set(
        package.get("lineage", {}).get("transformations", [{}])[0].get(
            "input_artifact_revision_ids"
        )
        or []
    )
    if lineage_inputs != set(service._frozen_input_ids(step)):
        errors.append("lineage 输入集合 != frozen_inputs")
    transformations = [
        row for row in service.list_transformations(step) if row["operation"] == "extract_candidates"
    ]
    if len(transformations) != 1:
        errors.append("extract_candidates Transformation 数不为 1")
    else:
        transformation_id = transformations[0]["id"]
        outputs = [
            row[0]
            for row in service.store.conn.execute(
                "SELECT artifact_revision_id FROM transformation_outputs WHERE transformation_id=?",
                (transformation_id,),
            ).fetchall()
        ]
        for revision_id in outputs:
            row = service.get_revision(revision_id)
            if row is None or row["status"] != "sealed":
                errors.append("Transformation 输出未 sealed: %s" % revision_id)
        events = [
            row[0]
            for row in service.store.conn.execute(
                "SELECT event_revision_id FROM transformation_human_events WHERE transformation_id=?",
                (transformation_id,),
            ).fetchall()
        ]
        registered = [
            row[0]
            for row in service.store.conn.execute(
                "SELECT event_revision_id FROM human_events WHERE step_run_id=? ORDER BY created_at, rowid",
                (step,),
            ).fetchall()
        ]
        if events != registered:
            errors.append("Transformation human_event_revision_ids 与裁决事件不符")
    config = _doc(service, world["final"]["configuration_revision_id"])
    if config.get("gate_profile") != GATE_PROFILE:
        errors.append("配置 gate_profile != thin_no_model")
    return errors


def _check_golden_match(world):
    service = world["service"]
    fixture_dir = world["fixture_dir"]
    errors = []
    expected = yaml.safe_load(
        (fixture_dir / "expected" / "m4.stage_package.yaml").read_text(encoding="utf-8")
    )
    candidate_set = world["candidate_set"]
    candidate_bytes = _revision_bytes(service, world["final"]["candidate_set_revision_id"])
    if candidate_set.get("counts") != expected["manifest"]["counts"]:
        errors.append("counts != expected manifest.counts")
    if hashlib.sha256(candidate_bytes).hexdigest() != expected["manifest"]["content_sha256"]:
        errors.append("sha256(candidate_set) != expected manifest.content_sha256")
    package = _doc(service, world["final"]["package_revision_id"])
    for key in ("gate_profile", "span_layer", "cross_model", "term_layering"):
        if package.get("payload", {}).get(key) != expected["payload"].get(key):
            errors.append("payload.%s != expected" % key)
    got_assertions = [
        (row["assertion_id"], row["proposition"]) for row in candidate_set.get("assertions") or []
    ]
    if got_assertions != EXPECTED_ASSERTIONS:
        errors.append("assertions 列表 != 金标")
    return errors


def _stage_package_validator():
    schema = json.loads((SCHEMA_DIR / "stage_package.schema.json").read_text(encoding="utf-8"))
    ref = json.loads((SCHEMA_DIR / "artifact_ref.schema.json").read_text(encoding="utf-8"))
    registry = Registry().with_resource(
        "artifact_ref.schema.json",
        Resource.from_contents(ref, default_specification=DRAFT202012),
    )
    return jsonschema.Draft202012Validator(schema, registry=registry)


COMPUTED_CHECKS = (
    ("inputs_frozen", _check_inputs_frozen),
    ("lane_isolation", _check_lane_isolation),
    ("evidence_resolvable", _check_evidence_resolvable),
    ("quote_fidelity", _check_quote_fidelity),
    ("evidence_required", _check_evidence_required),
    ("identity", _check_identity),
    ("status_ceiling", _check_status_ceiling),
    ("category_separation", _check_category_separation),
    ("references", _check_references),
    ("dispute_ruling", _check_dispute_ruling),
    ("task_checkpoints", _check_task_checkpoints),
    ("package_lineage", _check_package_lineage),
    ("golden_match", _check_golden_match),
)


def _prepare(fixture_dir, gold_dir, canon_dir):
    tmp = tempfile.mkdtemp(prefix="m4-acceptance-")
    service = LedgerService(Path(tmp) / "ledger")
    summary = ingest(fixture_dir, service, stages=("m1", "m2"))
    edition_part_id = summary["edition_part_id"]
    m3 = run_m3(service, edition_part_id)
    profile_revision_id = register_technique_profile(
        service,
        m3["processing_run_id"],
        technique_id="qizheng",
        canon_dir=canon_dir,
    )
    submits = []
    for name in (
        "submission_assertion_a.yaml",
        "submission_assertion_b.yaml",
        "submission_concept_mention_a.yaml",
    ):
        submits.append(
            run_m4_submit(
                service,
                edition_part_id,
                (Path(gold_dir) / name).read_bytes(),
                producer_module="fixture:mini_ed01",
                producer_version="mini_ed01",
            )
        )
    awaiting = run_m4(service, edition_part_id)
    ruling = yaml.safe_load(
        (Path(gold_dir) / "ruling_m4_d001.yaml").read_text(encoding="utf-8")
    )
    record_category_ruling(service, awaiting["step_run_id"], awaiting["resume_token"], ruling)
    final = resume_m4(service, awaiting["step_run_id"], awaiting["resume_token"])
    world = {
        "service": service,
        "edition_part_id": edition_part_id,
        "m3": m3,
        "submits": submits,
        "awaiting": awaiting,
        "final": final,
        "profile_revision_id": profile_revision_id,
        "ruling": ruling,
        "fixture_dir": Path(fixture_dir),
        "gold_dir": Path(gold_dir),
    }
    if final.get("status") == "succeeded":
        world["candidate_set"] = _doc(service, final["candidate_set_revision_id"])
    return tmp, service, world


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pipeline.knowledge_extraction.acceptance")
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--gold-dir", default=None)
    parser.add_argument("--canon-dir", default=None)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args(argv)

    fixture_dir = Path(args.fixture)
    gold_dir = Path(args.gold_dir) if args.gold_dir else fixture_dir / "m4"
    canon_dir = Path(args.canon_dir) if args.canon_dir else DEFAULT_CANON_DIR
    for label, path in (
        ("fixture manifest", fixture_dir / "manifest.yaml"),
        ("gold-dir", gold_dir),
        ("canon-dir", canon_dir),
    ):
        if not path.exists():
            print("BLOCKED m4_acceptance 前置缺失: %s %s" % (label, path))
            print("SUMMARY pass=0 fail=0 blocked=1")
            return 3

    try:
        tmp, service, world = _prepare(fixture_dir, gold_dir, canon_dir)
    except Exception as exc:  # noqa: BLE001 —— 宿主准备失败统一退出 1
        print("FAIL m4_acceptance 宿主准备失败: %s: %s" % (type(exc).__name__, exc))
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
