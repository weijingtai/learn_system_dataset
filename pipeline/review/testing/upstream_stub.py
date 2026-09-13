import hashlib
import json
from pathlib import Path

import yaml

from pipeline.corpus_compiler.step import run_m3
from pipeline.knowledge_extraction.adapters.registry import register_technique_profile
from pipeline.knowledge_extraction.serialize import canonical_json
from pipeline.ledger import ids
from pipeline.ledger.fixture_ingest import ingest
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
