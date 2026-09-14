import hashlib
import json
from pathlib import Path

import yaml

from pipeline.corpus_compiler.step import run_m3
from pipeline.knowledge_extraction.adapters.registry import register_technique_profile
from pipeline.knowledge_extraction.serialize import canonical_json
from pipeline.ledger import ids
from pipeline.ledger.fixture_ingest import ingest
from pipeline.review.inputs import _artifact_types, _read_doc, latest_succeeded_step_run
from pipeline.validation.step import run_m5

STUB_TOOL = "pipeline.review.testing.upstream_stub"
STUB_TOOL_VERSION = "0.1.0"

_DATA_DIR = Path(__file__).resolve().parent / "data"
_CANON_DIR = Path(__file__).resolve().parents[3] / "pipeline" / "schemas" / "shared" / "canon"


def load_data(name: str) -> dict:
    path = _DATA_DIR / f"{name}.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _artifact_ref(service, revision_id):
    row = service.store.conn.execute(
        "SELECT a.artifact_id, a.artifact_type FROM artifacts a "
        "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
        "WHERE r.artifact_revision_id=?",
        (revision_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Revision {revision_id} not found")
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


def seed_upstream(service, fixture_dir) -> dict:
    summary = ingest(fixture_dir, service, stages=("m1", "m2"))
    edition_part_id = summary["edition_part_id"]
    m3_res = run_m3(service, edition_part_id)
    if m3_res.get("status") != "succeeded":
        raise RuntimeError("run_m3 failed")

    processing_run_id = m3_res["processing_run_id"]
    technique_profile_revision_id = register_technique_profile(
        service,
        processing_run_id,
        technique_id="qizheng",
        canon_dir=_CANON_DIR,
    )

    corpus_stage_package_revision_id = m3_res["package_revision_id"]
    spans_revision_id = m3_res["spans_revision_id"]
    m3_step_run_id = m3_res["step_run_id"]

    # 3. 合成 M4 输入
    m4_step_run_id = ids.new_id("step_run_id")
    config = {
        "stage": "m4",
        "task": "assemble",
        "tool": STUB_TOOL,
        "tool_version": STUB_TOOL_VERSION,
    }
    _, configuration_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical_json(config),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )

    frozen_inputs = [
        corpus_stage_package_revision_id,
        spans_revision_id,
        technique_profile_revision_id,
    ]

    service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m4_step_run_id,
            "input_artifact_ids": frozen_inputs,
            "technique_profile_id": "qizheng",
            "configuration_artifact_id": configuration_revision_id,
        }
    )

    cands_data = load_data("m4_candidates")
    assertions = cands_data.get("assertions", [])
    school_views = cands_data.get("school_views", [])

    candidate_set = {
        "schema_version": "0.1.0-draft",
        "source_id": "src_sanche_ed01",
        "edition_part_artifact_id": "art_000000000000000000000000000000e1",
        "technique_id": "qizheng",
        "span_layer": "structural",
        "evidence_level": "glyphbox_level",
        "counts": {
            "assertions": len(assertions),
            "school_views": len(school_views),
            "disputes": 0,
            "human_decisions": 0,
            "patterns": 0,
            "new_concept_candidates": 0,
            "rejected": 0,
        },
        "assertions": assertions,
        "school_views": school_views,
        "concept_mentions": [],
        "disputes": [],
        "new_concept_candidates": [],
        "patterns": [],
        "rejected": [],
        "source_channels": {},
    }
    candidate_bytes = canonical_json(candidate_set)
    _, candidate_set_revision_id = service.put_artifact(
        m4_step_run_id,
        "candidate_set",
        candidate_bytes,
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(candidate_set_revision_id)

    candidate_package = {
        "schema_version": "0.1.0-draft",
        "candidate_set_revision_id": candidate_set_revision_id,
        "candidate_set_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        "lane_set_revision_ids": [],
        "submission_revision_ids": [],
        "dispute_queue_revision_id": None,
        "human_event_revision_ids": [],
        "corpus_stage_package_revision_id": corpus_stage_package_revision_id,
        "spans_revision_id": spans_revision_id,
        "technique_profile_revision_id": technique_profile_revision_id,
        "gate_profile": "strict",
        "span_layer": "structural",
        "cross_model": "dual_independent",
        "term_layering": "hierarchical",
    }
    _, candidate_package_revision_id = service.put_artifact(
        m4_step_run_id,
        "candidate_package",
        canonical_json(candidate_package),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(candidate_package_revision_id)

    service.write_checkpoint(
        m4_step_run_id,
        edition_part_id=edition_part_id,
        stage="m4",
        completed_tasks=[
            {
                "task_id": "assemble",
                "artifact_revision_id": candidate_set_revision_id,
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )

    service.record_transformation(
        m4_step_run_id,
        operation="extract_candidates_stub",
        tool=STUB_TOOL,
        tool_version=STUB_TOOL_VERSION,
        configuration_revision_id=configuration_revision_id,
        input_revision_ids=frozen_inputs,
        output_revision_ids=[candidate_package_revision_id, candidate_set_revision_id],
    )

    _, log_revision_id = service.put_artifact(
        m4_step_run_id,
        "step_log",
        b"extract_candidates_stub",
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(log_revision_id)

    stage_package_id = ids.new_id("stage_package_id", stage="m4")
    package_revision_id = ids.new_id("artifact_revision_id")
    m4_stage_package = {
        "schema_version": "1.0.0",
        "stage_package_id": stage_package_id,
        "artifact_revision_id": package_revision_id,
        "stage": "m4",
        "status": "sealed",
        "payload": {
            "candidate_set_revision_id": candidate_set_revision_id,
            "corpus_stage_package_revision_id": corpus_stage_package_revision_id,
            "spans_revision_id": spans_revision_id,
            "technique_profile_revision_id": technique_profile_revision_id,
            "gate_profile": "strict",
            "span_layer": "structural",
            "cross_model": "dual_independent",
            "term_layering": "hierarchical",
            "content_status_counts": {"machine_extracted": len(assertions) + len(school_views)},
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m4_step_run_id,
            "input_artifacts": [_artifact_ref(service, rev) for rev in frozen_inputs],
            "output_artifacts": [_artifact_ref(service, candidate_package_revision_id)],
            "counts": candidate_set["counts"],
            "content_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        },
        "validation": {
            "passed": True,
            "report_artifacts": [],
        },
        "lineage": {
            "upstream_artifacts": [
                _artifact_ref(service, corpus_stage_package_revision_id),
                _artifact_ref(service, spans_revision_id),
                _artifact_ref(service, technique_profile_revision_id),
            ],
            "transformations": [
                {
                    "operation": "extract_candidates_stub",
                    "step_run_id": m4_step_run_id,
                    "configuration_artifact_revision_id": configuration_revision_id,
                    "input_artifact_revision_ids": frozen_inputs,
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
        m4_step_run_id,
        m4_stage_package,
        canonical_json(m4_stage_package),
        stage_package_id=stage_package_id,
        artifact_revision_id=package_revision_id,
    )
    service.seal_revision(package_revision_id)

    version = service.get_step_run(m4_step_run_id)["status_version"]
    service.finish_step_run(
        m4_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m4_step_run_id,
            "status_version": version + 1,
            "status": "succeeded",
            "output_artifact_ids": [
                package_revision_id,
                candidate_package_revision_id,
                candidate_set_revision_id,
            ],
            "validation_report_ids": [],
            "log_artifact_ids": [log_revision_id],
            "failure_artifact_ids": [],
        },
    )

    # 4. run_m5
    m5_res = run_m5(service, edition_part_id, target_consumption_level="INTERNAL_DEMO")
    if m5_res.get("status") != "succeeded":
        raise RuntimeError(f"run_m5 failed: {m5_res}")

    return {
        "edition_part_id": edition_part_id,
        "processing_run_id": processing_run_id,
        "corpus_stage_package_revision_id": corpus_stage_package_revision_id,
        "spans_revision_id": spans_revision_id,
        "candidate_package_revision_id": candidate_package_revision_id,
        "candidate_set_revision_id": candidate_set_revision_id,
        "validation_package_revision_id": m5_res["validation_package_revision_id"],
        "gate_results_revision_id": m5_res["gate_results_revision_id"],
        "m3_step_run_id": m3_step_run_id,
        "m4_step_run_id": m4_step_run_id,
        "m5_step_run_id": m5_res["step_run_id"],
    }


def seed_corrected_corpus(service, edition_part_id, corrections) -> dict:
    """非生产桩：把「修正后」的 m3 语料经真实 Ledger 写路径注入为新 succeeded 运行。

    按 ``corrections["span_patches"]`` 修改旧 ``corpus_spans``（改字同步改 ``chars[].char``；
    ``bbox_dx`` 加到 ``source_anchor.bbox.x``），写出**新** ``corpus_spans``/``corpus_package``
    修订；不调用 ``supersede_revision``，旧修订保持 sealed 供失效传播冻结（D-14）。
    """
    old_m3_step_run_id = latest_succeeded_step_run(service, edition_part_id, "m3")
    if old_m3_step_run_id is None:
        raise RuntimeError("无 succeeded 的 m3 StepRun，无法注入修正语料")
    old_m3_step = service.get_step_run(old_m3_step_run_id)
    old_request = json.loads(old_m3_step["request_json"] or "{}")
    old_frozen = list(old_request.get("input_artifact_ids") or [])
    old_result = json.loads(old_m3_step["result_json"] or "{}")
    old_outputs = list(old_result.get("output_artifact_ids") or [])
    old_output_types = _artifact_types(service, old_outputs)
    corpus_package_revs = [
        r for r in old_outputs if old_output_types.get(r) == "corpus_package"
    ]
    if len(corpus_package_revs) != 1:
        raise RuntimeError("旧 m3 运行的 corpus_package 输出数不为 1")
    old_corpus_package_rev = corpus_package_revs[0]
    corpus_package_doc = _read_doc(service, old_corpus_package_rev) or {}
    old_spans_rev = corpus_package_doc.get("spans_revision_id")
    spans_doc = _read_doc(service, old_spans_rev) or {}

    spans_list = spans_doc.get("spans")
    spans_by_id = {s["span_id"]: s for s in spans_list}
    for patch in corrections.get("span_patches", []) or []:
        span = spans_by_id[patch["span_id"]]
        if "char_index" in patch:
            idx = patch["char_index"]
            text = span["text"]
            span["text"] = text[:idx] + patch["char"] + text[idx + 1 :]
            chars = (span.get("source_anchor") or {}).get("chars") or []
            if 0 <= idx < len(chars):
                chars[idx]["char"] = patch["char"]
        if "bbox_dx" in patch:
            span["source_anchor"]["bbox"]["x"] += patch["bbox_dx"]

    new_spans_bytes = yaml.safe_dump(
        spans_doc, allow_unicode=True, default_flow_style=False, sort_keys=False
    ).encode("utf-8")

    processing_run_id = old_m3_step["processing_run_id"]
    _, configuration_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical_json(
            {
                "stage": "m3",
                "tool": STUB_TOOL,
                "tool_version": STUB_TOOL_VERSION,
                "task": "corrected_corpus",
            }
        ),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )

    new_step_run_id = ids.new_id("step_run_id")
    service.supersede_step_run(
        old_m3_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": new_step_run_id,
            "input_artifact_ids": old_frozen,
            "technique_profile_id": old_request.get("technique_profile_id"),
            "configuration_artifact_id": configuration_revision_id,
        },
    )

    _, new_spans_revision_id = service.put_artifact(
        new_step_run_id,
        "corpus_spans",
        new_spans_bytes,
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(new_spans_revision_id)

    new_corpus_package_doc = dict(corpus_package_doc)
    new_corpus_package_doc["spans_revision_id"] = new_spans_revision_id
    new_corpus_package_bytes = canonical_json(new_corpus_package_doc)
    _, new_corpus_package_revision_id = service.put_artifact(
        new_step_run_id,
        "corpus_package",
        new_corpus_package_bytes,
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(new_corpus_package_revision_id)

    service.write_checkpoint(
        new_step_run_id,
        edition_part_id=edition_part_id,
        stage="m3",
        completed_tasks=[
            {
                "task_id": "corrected_corpus",
                "artifact_revision_id": new_corpus_package_revision_id,
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )

    service.record_transformation(
        new_step_run_id,
        operation="correct_corpus_stub",
        tool=STUB_TOOL,
        tool_version=STUB_TOOL_VERSION,
        configuration_revision_id=configuration_revision_id,
        input_revision_ids=old_frozen,
        output_revision_ids=[new_corpus_package_revision_id, new_spans_revision_id],
    )

    _, log_revision_id = service.put_artifact(
        new_step_run_id,
        "step_log",
        b"correct_corpus_stub",
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(log_revision_id)

    stage_package_id = ids.new_id("stage_package_id", stage="m3")
    package_revision_id = ids.new_id("artifact_revision_id")
    m3_stage_package = {
        "schema_version": "1.0.0",
        "stage_package_id": stage_package_id,
        "artifact_revision_id": package_revision_id,
        "stage": "m3",
        "status": "sealed",
        "payload": {
            "corpus_package_revision_id": new_corpus_package_revision_id,
            "spans_revision_id": new_spans_revision_id,
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": new_step_run_id,
            "input_artifacts": [_artifact_ref(service, rev) for rev in old_frozen],
            "output_artifacts": [
                _artifact_ref(service, new_corpus_package_revision_id)
            ],
            "counts": {},
            "content_sha256": hashlib.sha256(new_corpus_package_bytes).hexdigest(),
        },
        "validation": {"passed": True, "report_artifacts": []},
        "lineage": {
            "upstream_artifacts": [_artifact_ref(service, rev) for rev in old_frozen],
            "transformations": [
                {
                    "operation": "correct_corpus_stub",
                    "step_run_id": new_step_run_id,
                    "configuration_artifact_revision_id": configuration_revision_id,
                    "input_artifact_revision_ids": old_frozen,
                    "output_artifact_revision_ids": [
                        new_corpus_package_revision_id,
                        new_spans_revision_id,
                    ],
                }
            ],
        },
        "logs": [_artifact_ref(service, log_revision_id)],
        "failures": [],
    }
    service.register_stage_package(
        new_step_run_id,
        m3_stage_package,
        canonical_json(m3_stage_package),
        stage_package_id=stage_package_id,
        artifact_revision_id=package_revision_id,
    )
    service.seal_revision(package_revision_id)

    version = service.get_step_run(new_step_run_id)["status_version"]
    service.finish_step_run(
        new_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": new_step_run_id,
            "status_version": version + 1,
            "status": "succeeded",
            "output_artifact_ids": [
                package_revision_id,
                new_corpus_package_revision_id,
                new_spans_revision_id,
            ],
            "validation_report_ids": [],
            "log_artifact_ids": [log_revision_id],
            "failure_artifact_ids": [],
        },
    )

    return {
        "new_corpus_package_revision_id": new_corpus_package_revision_id,
        "new_corpus_spans_revision_id": new_spans_revision_id,
        "m3_step_run_id": new_step_run_id,
    }
