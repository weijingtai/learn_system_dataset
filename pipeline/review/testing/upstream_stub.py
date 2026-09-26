import copy
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
from pipeline.review.step import _artifact_ref
from pipeline.validation.step import run_m5

STUB_TOOL = "pipeline.review.testing.upstream_stub"
STUB_TOOL_VERSION = "0.1.0"

_DATA_DIR = Path(__file__).resolve().parent / "data"
_CANON_DIR = Path(__file__).resolve().parents[3] / "pipeline" / "schemas" / "shared" / "canon"


def load_data(name: str) -> dict:
    path = _DATA_DIR / f"{name}.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


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
    patterns = cands_data.get("patterns", [])
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
            "concept_mentions": 0,
            "disputes": 0,
            "human_decisions": 0,
            "patterns": len(patterns),
            "new_concept_candidates": 0,
            "rejected": 0,
        },
        "assertions": assertions,
        "school_views": school_views,
        "concept_mentions": [],
        "disputes": [],
        "new_concept_candidates": [],
        "patterns": patterns,
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


def _spans_by_id(spans_doc):
    raw = (spans_doc or {}).get("spans")
    if isinstance(raw, list):
        return {s["span_id"]: s for s in raw if isinstance(s, dict) and "span_id" in s}
    if isinstance(raw, dict):
        return raw
    return {}


def _quote_offsets(ev, span):
    text_len = len(span.get("text", ""))
    span_start = span.get("start_offset", 0)
    s_off = ev.get("start_offset", 0)
    e_off = ev.get("end_offset", s_off)
    if 0 <= s_off < e_off <= text_len:
        return s_off, e_off
    if span_start > 0 and 0 <= (s_off - span_start) < (e_off - span_start) <= text_len:
        return s_off - span_start, e_off - span_start
    return 0, text_len


def _refresh_evidence_quotes(obj, spans_by_id):
    """按新 spans 重算该对象证据的 quote/quote_sha256（M4' 的代表行为）。"""
    for ev in obj.get("evidence", []) or []:
        span = spans_by_id.get(ev.get("source_span_id"), {})
        start, end = _quote_offsets(ev, span)
        quote = span.get("text", "")[start:end]
        ev["quote"] = quote
        ev["quote_sha256"] = hashlib.sha256(quote.encode("utf-8")).hexdigest()


def _latest_m3_outputs(service, edition_part_id):
    """取最近 succeeded 的 m3 运行输出（修正后语料会取代旧运行）。

    不走 ``resolve_m3_outputs``：该函数要求 m3 StagePackage 恰 1 条，而修正运行会再登记
    一条（D-14 单线链）；本桩按「最近 succeeded 运行」解析新 corpus。
    """
    m3_step_run_id = latest_succeeded_step_run(service, edition_part_id, "m3")
    if m3_step_run_id is None:
        raise RuntimeError("无 succeeded 的 m3 StepRun")
    step = service.get_step_run(m3_step_run_id)
    outputs = list(
        json.loads(step["result_json"] or "{}").get("output_artifact_ids") or []
    )
    types = _artifact_types(service, outputs)

    def pick(kind):
        revs = [r for r in outputs if types.get(r) == kind]
        if len(revs) != 1:
            raise RuntimeError("m3 输出 %s 数量不为 1" % kind)
        return revs[0]

    request = json.loads(step["request_json"] or "{}")
    return {
        "m3_step_run_id": m3_step_run_id,
        "processing_run_id": step["processing_run_id"],
        "technique_id": request.get("technique_profile_id"),
        "corpus_stage_package_revision_id": pick("stage_package"),
        "corpus_package_revision_id": pick("corpus_package"),
        "spans_revision_id": pick("corpus_spans"),
    }


def seed_rerun_m4_m5(
    service, edition_part_id, *, rework_impact_report_revision_id
) -> dict:
    """非生产桩：注入 M4'/M5' 重跑。

    M4'：新 ``candidate_set`` 修订（同 artifact、``prev_revision_id`` 指旧修订，经
    ``supersede_revision`` 替换）；可达对象按新 spans 重算证据引文，不可达对象沿用旧内容。
    M5'：新 ``validation_package`` 绑定新 corpus（仍 ``scope=corpus_only``）。
    """
    report = _read_doc(service, rework_impact_report_revision_id) or {}
    invalidated_ids = {
        c["entity_id"]
        for c in report.get("invalidated", []) or []
        if c.get("kind") == "candidate"
    }

    m3 = _latest_m3_outputs(service, edition_part_id)
    new_corpus_stage_package_revision_id = m3["corpus_stage_package_revision_id"]
    new_corpus_package_revision_id = m3["corpus_package_revision_id"]
    new_spans_revision_id = m3["spans_revision_id"]
    processing_run_id = m3["processing_run_id"]
    technique_id = m3["technique_id"]
    spans_by_id = _spans_by_id(_read_doc(service, new_spans_revision_id))

    # ---------------- M4' ----------------
    old_m4_step_run_id = latest_succeeded_step_run(service, edition_part_id, "m4")
    old_m4_step = service.get_step_run(old_m4_step_run_id)
    old_m4_outputs = list(
        json.loads(old_m4_step["result_json"] or "{}").get("output_artifact_ids") or []
    )
    old_m4_types = _artifact_types(service, old_m4_outputs)
    old_candidate_package_rev = next(
        r for r in old_m4_outputs if old_m4_types.get(r) == "candidate_package"
    )
    old_candidate_set_rev = next(
        r for r in old_m4_outputs if old_m4_types.get(r) == "candidate_set"
    )
    old_candidate_pkg_doc = _read_doc(service, old_candidate_package_rev) or {}
    old_candidate_set_doc = _read_doc(service, old_candidate_set_rev) or {}
    technique_profile_revision_id = old_candidate_pkg_doc.get(
        "technique_profile_revision_id"
    )

    _, m4_config_rev = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical_json(
            {
                "stage": "m4",
                "tool": STUB_TOOL,
                "tool_version": STUB_TOOL_VERSION,
                "task": "assemble_rerun",
            }
        ),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    m4_frozen = [
        new_corpus_stage_package_revision_id,
        new_spans_revision_id,
        technique_profile_revision_id,
    ]
    m4_step_run_id = ids.new_id("step_run_id")
    service.supersede_step_run(
        old_m4_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m4_step_run_id,
            "input_artifact_ids": m4_frozen,
            "technique_profile_id": technique_id,
            "configuration_artifact_id": m4_config_rev,
        },
    )

    new_candidate_set = copy.deepcopy(old_candidate_set_doc)
    for a in new_candidate_set.get("assertions", []) or []:
        if a["assertion_id"] in invalidated_ids:
            _refresh_evidence_quotes(a, spans_by_id)
    new_candidate_set_bytes = canonical_json(new_candidate_set)
    _, new_candidate_set_rev = service.put_artifact(
        m4_step_run_id,
        "candidate_set",
        new_candidate_set_bytes,
        prev_revision_id=old_candidate_set_rev,
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(new_candidate_set_rev)
    service.supersede_revision(old_candidate_set_rev, new_candidate_set_rev)

    new_candidate_package = copy.deepcopy(old_candidate_pkg_doc)
    new_candidate_package["candidate_set_revision_id"] = new_candidate_set_rev
    new_candidate_package["candidate_set_sha256"] = hashlib.sha256(
        new_candidate_set_bytes
    ).hexdigest()
    new_candidate_package["corpus_stage_package_revision_id"] = (
        new_corpus_stage_package_revision_id
    )
    new_candidate_package["spans_revision_id"] = new_spans_revision_id
    _, new_candidate_package_rev = service.put_artifact(
        m4_step_run_id,
        "candidate_package",
        canonical_json(new_candidate_package),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(new_candidate_package_rev)

    service.write_checkpoint(
        m4_step_run_id,
        edition_part_id=edition_part_id,
        stage="m4",
        completed_tasks=[
            {
                "task_id": "assemble_rerun",
                "artifact_revision_id": new_candidate_set_rev,
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
        operation="extract_candidates_rerun_stub",
        tool=STUB_TOOL,
        tool_version=STUB_TOOL_VERSION,
        configuration_revision_id=m4_config_rev,
        input_revision_ids=m4_frozen,
        output_revision_ids=[new_candidate_package_rev, new_candidate_set_rev],
    )
    _, m4_log_rev = service.put_artifact(
        m4_step_run_id,
        "step_log",
        b"extract_candidates_rerun_stub",
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(m4_log_rev)

    m4_stage_package_id = ids.new_id("stage_package_id", stage="m4")
    m4_package_revision_id = ids.new_id("artifact_revision_id")
    m4_stage_package = {
        "schema_version": "1.0.0",
        "stage_package_id": m4_stage_package_id,
        "artifact_revision_id": m4_package_revision_id,
        "stage": "m4",
        "status": "sealed",
        "payload": {
            "candidate_set_revision_id": new_candidate_set_rev,
            "corpus_stage_package_revision_id": new_corpus_stage_package_revision_id,
            "spans_revision_id": new_spans_revision_id,
            "technique_profile_revision_id": technique_profile_revision_id,
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m4_step_run_id,
            "input_artifacts": [_artifact_ref(service, r) for r in m4_frozen],
            "output_artifacts": [_artifact_ref(service, new_candidate_package_rev)],
            "counts": {
                "assertions": len(new_candidate_set.get("assertions", []) or []),
                "school_views": len(new_candidate_set.get("school_views", []) or []),
            },
            "content_sha256": hashlib.sha256(new_candidate_set_bytes).hexdigest(),
        },
        "validation": {"passed": True, "report_artifacts": []},
        "lineage": {
            "upstream_artifacts": [_artifact_ref(service, r) for r in m4_frozen],
            "transformations": [
                {
                    "operation": "extract_candidates_rerun_stub",
                    "step_run_id": m4_step_run_id,
                    "configuration_artifact_revision_id": m4_config_rev,
                    "input_artifact_revision_ids": m4_frozen,
                    "output_artifact_revision_ids": [
                        new_candidate_package_rev,
                        new_candidate_set_rev,
                    ],
                }
            ],
        },
        "logs": [_artifact_ref(service, m4_log_rev)],
        "failures": [],
    }
    service.register_stage_package(
        m4_step_run_id,
        m4_stage_package,
        canonical_json(m4_stage_package),
        stage_package_id=m4_stage_package_id,
        artifact_revision_id=m4_package_revision_id,
    )
    service.seal_revision(m4_package_revision_id)

    m4_version = service.get_step_run(m4_step_run_id)["status_version"]
    service.finish_step_run(
        m4_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m4_step_run_id,
            "status_version": m4_version + 1,
            "status": "succeeded",
            "output_artifact_ids": [
                m4_package_revision_id,
                new_candidate_package_rev,
                new_candidate_set_rev,
            ],
            "validation_report_ids": [],
            "log_artifact_ids": [m4_log_rev],
            "failure_artifact_ids": [],
        },
    )

    # ---------------- M5' ----------------
    old_m5_step_run_id = latest_succeeded_step_run(service, edition_part_id, "m5")
    old_m5_step = service.get_step_run(old_m5_step_run_id)
    old_m5_outputs = list(
        json.loads(old_m5_step["result_json"] or "{}").get("output_artifact_ids") or []
    )
    old_m5_types = _artifact_types(service, old_m5_outputs)
    old_validation_package_rev = next(
        r for r in old_m5_outputs if old_m5_types.get(r) == "validation_package"
    )
    old_gate_results_rev = next(
        r for r in old_m5_outputs if old_m5_types.get(r) == "gate_results"
    )
    old_validation_package_doc = _read_doc(service, old_validation_package_rev) or {}
    old_gate_results_doc = _read_doc(service, old_gate_results_rev) or {}

    _, m5_config_rev = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical_json(
            {
                "stage": "m5",
                "tool": STUB_TOOL,
                "tool_version": STUB_TOOL_VERSION,
                "task": "validate_corpus_rerun",
            }
        ),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    m5_frozen = [
        new_corpus_stage_package_revision_id,
        new_corpus_package_revision_id,
        new_spans_revision_id,
    ]
    m5_step_run_id = ids.new_id("step_run_id")
    service.supersede_step_run(
        old_m5_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m5_step_run_id,
            "input_artifact_ids": m5_frozen,
            "technique_profile_id": technique_id,
            "configuration_artifact_id": m5_config_rev,
        },
    )

    _, new_gate_results_rev = service.put_artifact(
        m5_step_run_id,
        "gate_results",
        canonical_json(old_gate_results_doc),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(new_gate_results_rev)

    new_validation_package_doc = copy.deepcopy(old_validation_package_doc)
    new_validation_package_doc["gate_results_revision_id"] = new_gate_results_rev
    new_validation_package_doc["corpus_package_revision_id"] = (
        new_corpus_package_revision_id
    )
    new_validation_package_doc["corpus_spans_revision_id"] = new_spans_revision_id
    new_validation_package_doc["m3_package_revision_id"] = (
        new_corpus_stage_package_revision_id
    )
    sp_info = service.describe_revision(new_corpus_stage_package_revision_id)
    if sp_info is not None and sp_info["stage_package_id"] is not None:
        new_validation_package_doc["m3_stage_package_id"] = sp_info["stage_package_id"]
    _, new_validation_package_rev = service.put_artifact(
        m5_step_run_id,
        "validation_package",
        canonical_json(new_validation_package_doc),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(new_validation_package_rev)

    service.write_checkpoint(
        m5_step_run_id,
        edition_part_id=edition_part_id,
        stage="m5",
        completed_tasks=[
            {
                "task_id": "validate_corpus_rerun",
                "artifact_revision_id": new_validation_package_rev,
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )
    service.record_transformation(
        m5_step_run_id,
        operation="validate_corpus_rerun_stub",
        tool=STUB_TOOL,
        tool_version=STUB_TOOL_VERSION,
        configuration_revision_id=m5_config_rev,
        input_revision_ids=m5_frozen,
        output_revision_ids=[new_gate_results_rev, new_validation_package_rev],
    )
    _, m5_log_rev = service.put_artifact(
        m5_step_run_id,
        "step_log",
        b"validate_corpus_rerun_stub",
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(m5_log_rev)

    m5_stage_package_id = ids.new_id("stage_package_id", stage="m5")
    m5_package_revision_id = ids.new_id("artifact_revision_id")
    old_counts = old_gate_results_doc.get("counts", {}) or {}
    m5_stage_package = {
        "schema_version": "1.0.0",
        "stage_package_id": m5_stage_package_id,
        "artifact_revision_id": m5_package_revision_id,
        "stage": "m5",
        "status": "sealed",
        "payload": {
            "validation_package_revision_id": new_validation_package_rev,
            "gate_results_revision_id": new_gate_results_rev,
            "scope": "corpus_only",
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m5_step_run_id,
            "input_artifacts": [_artifact_ref(service, r) for r in m5_frozen],
            "output_artifacts": [_artifact_ref(service, new_validation_package_rev)],
            "counts": {
                key: int(old_counts.get(key, 0))
                for key in (
                    "validators",
                    "findings",
                    "failures",
                    "warnings",
                    "rework_tasks",
                )
            },
            "content_sha256": hashlib.sha256(
                canonical_json(old_gate_results_doc)
            ).hexdigest(),
        },
        "validation": {"passed": True, "report_artifacts": []},
        "lineage": {
            "upstream_artifacts": [_artifact_ref(service, r) for r in m5_frozen],
            "transformations": [
                {
                    "operation": "validate_corpus_rerun_stub",
                    "step_run_id": m5_step_run_id,
                    "configuration_artifact_revision_id": m5_config_rev,
                    "input_artifact_revision_ids": m5_frozen,
                    "output_artifact_revision_ids": [
                        new_gate_results_rev,
                        new_validation_package_rev,
                    ],
                }
            ],
        },
        "logs": [_artifact_ref(service, m5_log_rev)],
        "failures": [],
    }
    service.register_stage_package(
        m5_step_run_id,
        m5_stage_package,
        canonical_json(m5_stage_package),
        stage_package_id=m5_stage_package_id,
        artifact_revision_id=m5_package_revision_id,
    )
    service.seal_revision(m5_package_revision_id)

    m5_version = service.get_step_run(m5_step_run_id)["status_version"]
    service.finish_step_run(
        m5_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m5_step_run_id,
            "status_version": m5_version + 1,
            "status": "succeeded",
            "output_artifact_ids": [
                new_gate_results_rev,
                new_validation_package_rev,
                m5_package_revision_id,
            ],
            "validation_report_ids": [],
            "log_artifact_ids": [m5_log_rev],
            "failure_artifact_ids": [],
        },
    )

    return {
        "candidate_package_revision_id": new_candidate_package_rev,
        "candidate_set_revision_id": new_candidate_set_rev,
        "validation_package_revision_id": new_validation_package_rev,
        "gate_results_revision_id": new_gate_results_rev,
    }


def seed_offset_upstream(service, edition_part_id="ep_qianyuan_ed01_001") -> dict:
    """R84b (裁决 106 D3)：在真实 Ledger 上注入 offset_level 上游桩。

    复用 M4 ``test_gate.py:_offset_spans_doc`` 与 M5 ``helpers.offset_fixture_context`` 的形态：
    - 登记 offset_level 语料 spans（evidence_level: "offset_level"）
    - M4 candidates 引用 offset spans 并严格满足 I-11 绝对偏移
    - M5 gate results 与 validation_package
    """
    if not (isinstance(edition_part_id, str) and edition_part_id.startswith("art_") and len(edition_part_id) == 36):
        edition_part_id = "art_" + hashlib.md5(edition_part_id.encode("utf-8")).hexdigest()

    processing_run_id = service.create_processing_run(
        "edition_run", edition_part_id, "qizheng"
    )
    technique_profile_revision_id = register_technique_profile(
        service,
        processing_run_id,
        technique_id="qizheng",
        canon_dir=_CANON_DIR,
    )

    # 1. M3 阶段（电子文本 offset_level）
    m3_step_run_id = ids.new_id("step_run_id")
    m3_config = {
        "stage": "m3",
        "task": "compile_corpus",
        "tool": STUB_TOOL,
        "tool_version": STUB_TOOL_VERSION,
        "evidence_level": "offset_level",
        "gate_profile": "structural_only",
    }
    _, m3_config_rev = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical_json(m3_config),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m3_step_run_id,
            "input_artifact_ids": [],
            "technique_profile_id": "qizheng",
            "configuration_artifact_id": m3_config_rev,
        }
    )

    raw_text_rev = ids.new_id("artifact_revision_id")
    cleaned_text_rev = ids.new_id("artifact_revision_id")

    span_rows = [
        ("ss_qianyuan_ed01_o0008663", 8663, "天官者，天干之官也。"),
        ("ss_qianyuan_ed01_o0008673", 8673, "余俱从天干取用。"),
    ]
    spans = []
    for idx, (span_id, s_off, s_text) in enumerate(span_rows):
        e_off = s_off + len(s_text)
        q_sha = hashlib.sha256(s_text.encode("utf-8")).hexdigest()
        spans.append({
            "span_id": span_id,
            "sequence": idx + 1,
            "start_offset": s_off,
            "end_offset": e_off,
            "text": s_text,
            "quote_sha256": q_sha,
            "evidence_level": "offset_level",
            "source_anchor": {
                "raw_text_revision_id": raw_text_rev,
                "raw_start": s_off,
                "raw_end": e_off,
                "cleaned_text_revision_id": cleaned_text_rev,
                "start_offset": s_off,
                "end_offset": e_off,
                "quote_sha256": q_sha,
            },
        })

    spans_doc = {
        "schema_version": "0.1.0-draft",
        "work": "qianyuan",
        "source_id": "src_qianyuan_ed01",
        "edition_part_artifact_id": edition_part_id,
        "evidence_level": "offset_level",
        "content_status": "machine_extracted",
        "span_count": len(spans),
        "spans": spans,
    }
    spans_bytes = canonical_json(spans_doc)
    _, spans_revision_id = service.put_artifact(
        m3_step_run_id,
        "corpus_spans",
        spans_bytes,
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(spans_revision_id)

    coverage_report = {
        "schema_version": "0.1.0-draft",
        "gate_profile": "structural_only",
        "structural": "passed",
        "semantic": "not_evaluated",
        "checks": {
            "text_contiguous_coverage": {"ok": True, "failures": []},
            "text_strict_offset": {"ok": True, "failures": []},
            "raw_anchor_fidelity": {"ok": True, "failures": []},
            "identity_and_stability": {"ok": True, "failures": []},
            "evidence_level_honest": {"ok": True, "failures": []},
            "header_counts": {"ok": True, "failures": []},
        },
        "pages": {},
    }
    _, coverage_report_rev_id = service.put_artifact(
        m3_step_run_id,
        "coverage_report",
        canonical_json(coverage_report),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(coverage_report_rev_id)

    corpus_package = {
        "schema_version": "0.1.0-draft",
        "spans_revision_id": spans_revision_id,
        "coverage_report_revision_id": coverage_report_rev_id,
        "coverage": {"qianyuan_ed01_text": 1.0},
        "excluded_pages": {},
        "gate_profile": "structural_only",
        "semantic": "not_evaluated",
    }
    _, corpus_package_rev_id = service.put_artifact(
        m3_step_run_id,
        "corpus_package",
        canonical_json(corpus_package),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(corpus_package_rev_id)

    m3_stage_package_id = ids.new_id("stage_package_id", stage="m3")
    m3_package_rev_id = ids.new_id("artifact_revision_id")
    m3_stage_package = {
        "schema_version": "1.0.0",
        "stage_package_id": m3_stage_package_id,
        "artifact_revision_id": m3_package_rev_id,
        "stage": "m3",
        "status": "sealed",
        "payload": {
            "spans_revision_id": spans_revision_id,
            "corpus_package_revision_id": corpus_package_rev_id,
            "coverage": {"qianyuan_ed01_text": 1.0},
            "excluded_pages": {},
            "gate_profile": "structural_only",
            "semantic": "not_evaluated",
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m3_step_run_id,
            "input_artifacts": [],
            "output_artifacts": [_artifact_ref(service, corpus_package_rev_id)],
            "counts": {"spans": len(spans)},
            "content_sha256": hashlib.sha256(spans_bytes).hexdigest(),
        },
        "validation": {"passed": True, "report_artifacts": []},
        "lineage": {"upstream_artifacts": [], "transformations": []},
        "logs": [],
        "failures": [],
    }
    service.register_stage_package(
        m3_step_run_id,
        m3_stage_package,
        canonical_json(m3_stage_package),
        stage_package_id=m3_stage_package_id,
        artifact_revision_id=m3_package_rev_id,
    )
    service.seal_revision(m3_package_rev_id)

    service.write_checkpoint(
        m3_step_run_id,
        edition_part_id=edition_part_id,
        stage="m3",
        completed_tasks=[{
            "task_id": "compile_corpus",
            "artifact_revision_id": corpus_package_rev_id,
            "status": "succeeded",
            "terminal_state": None,
        }],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )
    service.record_transformation(
        m3_step_run_id,
        operation="compile_corpus",
        tool=STUB_TOOL,
        tool_version=STUB_TOOL_VERSION,
        configuration_revision_id=m3_config_rev,
        input_revision_ids=[],
        output_revision_ids=[corpus_package_rev_id, spans_revision_id],
    )
    service.finish_step_run(
        m3_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m3_step_run_id,
            "status_version": 1,
            "status": "succeeded",
            "output_artifact_ids": [
                m3_package_rev_id,
                corpus_package_rev_id,
                spans_revision_id,
                coverage_report_rev_id,
            ],
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
        },
    )

    # 2. M4 阶段（offset 候选）
    m4_step_run_id = ids.new_id("step_run_id")
    m4_config = {
        "stage": "m4",
        "task": "assemble",
        "tool": STUB_TOOL,
        "tool_version": STUB_TOOL_VERSION,
    }
    _, m4_configuration_rev_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical_json(m4_config),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    m4_frozen_inputs = [
        m3_package_rev_id,
        spans_revision_id,
        technique_profile_revision_id,
    ]
    service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m4_step_run_id,
            "input_artifact_ids": m4_frozen_inputs,
            "technique_profile_id": "qizheng",
            "configuration_artifact_id": m4_configuration_rev_id,
        }
    )

    ev1_quote = "天官者，天干之官"
    ev2_quote = "余俱从天干取用"
    ev3_quote = "天官"
    assertions = [
        {
            "assertion_id": "as_qizheng_000001",
            "proposition": "天官即天干之官",
            "relation": "supports",
            "status": "machine_extracted",
            "confidence": 0.95,
            "evidence": [{
                "source_span_id": "ss_qianyuan_ed01_o0008663",
                "start_offset": 8663,
                "end_offset": 8663 + len(ev1_quote),
                "quote": ev1_quote,
                "quote_sha256": hashlib.sha256(ev1_quote.encode("utf-8")).hexdigest(),
                "support_type": "direct",
            }],
        },
        {
            "assertion_id": "as_qizheng_000002",
            "proposition": "余俱从天干取用",
            "relation": "supports",
            "status": "machine_extracted",
            "confidence": 0.92,
            "evidence": [{
                "source_span_id": "ss_qianyuan_ed01_o0008673",
                "start_offset": 8673,
                "end_offset": 8673 + len(ev2_quote),
                "quote": ev2_quote,
                "quote_sha256": hashlib.sha256(ev2_quote.encode("utf-8")).hexdigest(),
                "support_type": "direct",
            }],
        },
        {
            "assertion_id": "as_qizheng_000003",
            "proposition": "天官从干",
            "relation": "supports",
            "status": "machine_extracted",
            "confidence": 0.88,
            "evidence": [{
                "source_span_id": "ss_qianyuan_ed01_o0008663",
                "start_offset": 8663,
                "end_offset": 8663 + len(ev3_quote),
                "quote": ev3_quote,
                "quote_sha256": hashlib.sha256(ev3_quote.encode("utf-8")).hexdigest(),
                "support_type": "direct",
            }],
        },
    ]
    school_views = [
        {
            "school_view_id": "sv_00000000000000000000000000000001",
            "school_id": "sch_qizheng_001",
            "school_name": "果老星宗",
            "view_type": "interpretation",
            "status": "machine_extracted",
            "claim_refs": ["as_qizheng_000001"],
            "changes_current_judgment": False,
            "evidence": [{
                "source_span_id": "ss_qianyuan_ed01_o0008663",
                "start_offset": 8663,
                "end_offset": 8663 + len(ev3_quote),
                "quote": ev3_quote,
                "quote_sha256": hashlib.sha256(ev3_quote.encode("utf-8")).hexdigest(),
                "support_type": "direct",
            }],
        },
    ]

    candidate_set = {
        "schema_version": "0.1.0-draft",
        "source_id": "src_qianyuan_ed01",
        "edition_part_artifact_id": edition_part_id,
        "technique_id": "qizheng",
        "span_layer": "structural",
        "evidence_level": "offset_level",
        "counts": {
            "assertions": len(assertions),
            "school_views": len(school_views),
            "concept_mentions": 0,
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
        "corpus_stage_package_revision_id": m3_package_rev_id,
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
        completed_tasks=[{
            "task_id": "assemble",
            "artifact_revision_id": candidate_set_revision_id,
            "status": "succeeded",
            "terminal_state": None,
        }],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )
    service.record_transformation(
        m4_step_run_id,
        operation="extract_candidates_stub",
        tool=STUB_TOOL,
        tool_version=STUB_TOOL_VERSION,
        configuration_revision_id=m4_configuration_rev_id,
        input_revision_ids=m4_frozen_inputs,
        output_revision_ids=[candidate_package_revision_id, candidate_set_revision_id],
    )

    _, log_revision_id = service.put_artifact(
        m4_step_run_id,
        "step_log",
        b"extract_candidates_offset_stub",
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(log_revision_id)

    m4_stage_package_id = ids.new_id("stage_package_id", stage="m4")
    m4_package_rev_id = ids.new_id("artifact_revision_id")
    m4_stage_package = {
        "schema_version": "1.0.0",
        "stage_package_id": m4_stage_package_id,
        "artifact_revision_id": m4_package_rev_id,
        "stage": "m4",
        "status": "sealed",
        "payload": {
            "candidate_set_revision_id": candidate_set_revision_id,
            "corpus_stage_package_revision_id": m3_package_rev_id,
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
            "input_artifacts": [_artifact_ref(service, rev) for rev in m4_frozen_inputs],
            "output_artifacts": [_artifact_ref(service, candidate_package_revision_id)],
            "counts": candidate_set["counts"],
            "content_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        },
        "validation": {"passed": True, "report_artifacts": []},
        "lineage": {
            "upstream_artifacts": [_artifact_ref(service, rev) for rev in m4_frozen_inputs],
            "transformations": [{
                "operation": "extract_candidates_stub",
                "step_run_id": m4_step_run_id,
                "configuration_artifact_revision_id": m4_configuration_rev_id,
                "input_artifact_revision_ids": m4_frozen_inputs,
                "output_artifact_revision_ids": [
                    candidate_package_revision_id,
                    candidate_set_revision_id,
                ],
            }],
        },
        "logs": [_artifact_ref(service, log_revision_id)],
        "failures": [],
    }
    service.register_stage_package(
        m4_step_run_id,
        m4_stage_package,
        canonical_json(m4_stage_package),
        stage_package_id=m4_stage_package_id,
        artifact_revision_id=m4_package_rev_id,
    )
    service.seal_revision(m4_package_rev_id)

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
                m4_package_rev_id,
                candidate_package_revision_id,
                candidate_set_revision_id,
            ],
            "validation_report_ids": [],
            "log_artifact_ids": [log_revision_id],
            "failure_artifact_ids": [],
        },
    )

    # 3. M5 阶段（offset 验证）
    m5_step_run_id = ids.new_id("step_run_id")
    m5_config = {
        "stage": "m5",
        "task": "validate_corpus",
        "tool": STUB_TOOL,
        "tool_version": STUB_TOOL_VERSION,
    }
    _, m5_configuration_rev_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical_json(m5_config),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    m5_frozen = [m3_package_rev_id, corpus_package_rev_id, spans_revision_id]
    service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m5_step_run_id,
            "input_artifact_ids": m5_frozen,
            "technique_profile_id": "qizheng",
            "configuration_artifact_id": m5_configuration_rev_id,
        }
    )

    gate_results = {
        "schema_version": "0.1.0-draft",
        "passed": True,
        "checks": {
            "findings_valid": {"passed": True},
            "source_fidelity": {"passed": True},
            "evidence_fidelity": {"passed": True},
        },
        "counts": {
            "validators": 3,
            "findings": 0,
            "failures": 0,
            "warnings": 0,
            "rework_tasks": 0,
        },
        "failures": [],
        "warnings": [],
    }
    _, gate_results_rev_id = service.put_artifact(
        m5_step_run_id,
        "gate_results",
        canonical_json(gate_results),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(gate_results_rev_id)

    validation_package = {
        "schema_version": "0.1.0-draft",
        "gate": {"passed": True},
        "scope": "corpus_only",
        "gate_results_revision_id": gate_results_rev_id,
        "corpus_package_revision_id": corpus_package_rev_id,
        "corpus_spans_revision_id": spans_revision_id,
        "m3_package_revision_id": m3_package_rev_id,
        "m3_stage_package_id": m3_stage_package_id,
    }
    _, val_package_rev_id = service.put_artifact(
        m5_step_run_id,
        "validation_package",
        canonical_json(validation_package),
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(val_package_rev_id)

    service.write_checkpoint(
        m5_step_run_id,
        edition_part_id=edition_part_id,
        stage="m5",
        completed_tasks=[{
            "task_id": "validate_corpus",
            "artifact_revision_id": val_package_rev_id,
            "status": "succeeded",
            "terminal_state": None,
        }],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )
    service.record_transformation(
        m5_step_run_id,
        operation="validate_corpus_stub",
        tool=STUB_TOOL,
        tool_version=STUB_TOOL_VERSION,
        configuration_revision_id=m5_configuration_rev_id,
        input_revision_ids=m5_frozen,
        output_revision_ids=[gate_results_rev_id, val_package_rev_id],
    )
    _, m5_log_rev = service.put_artifact(
        m5_step_run_id,
        "step_log",
        b"validate_corpus_offset_stub",
        producer_module=STUB_TOOL,
        producer_version=STUB_TOOL_VERSION,
    )
    service.seal_revision(m5_log_rev)

    m5_stage_package_id = ids.new_id("stage_package_id", stage="m5")
    m5_package_rev_id = ids.new_id("artifact_revision_id")
    m5_stage_package = {
        "schema_version": "1.0.0",
        "stage_package_id": m5_stage_package_id,
        "artifact_revision_id": m5_package_rev_id,
        "stage": "m5",
        "status": "sealed",
        "payload": {
            "validation_package_revision_id": val_package_rev_id,
            "gate_results_revision_id": gate_results_rev_id,
            "scope": "corpus_only",
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m5_step_run_id,
            "input_artifacts": [_artifact_ref(service, r) for r in m5_frozen],
            "output_artifacts": [_artifact_ref(service, val_package_rev_id)],
            "counts": gate_results["counts"],
            "content_sha256": hashlib.sha256(canonical_json(gate_results)).hexdigest(),
        },
        "validation": {"passed": True, "report_artifacts": []},
        "lineage": {
            "upstream_artifacts": [_artifact_ref(service, r) for r in m5_frozen],
            "transformations": [{
                "operation": "validate_corpus_stub",
                "step_run_id": m5_step_run_id,
                "configuration_artifact_revision_id": m5_configuration_rev_id,
                "input_artifact_revision_ids": m5_frozen,
                "output_artifact_revision_ids": [gate_results_rev_id, val_package_rev_id],
            }],
        },
        "logs": [_artifact_ref(service, m5_log_rev)],
        "failures": [],
    }
    service.register_stage_package(
        m5_step_run_id,
        m5_stage_package,
        canonical_json(m5_stage_package),
        stage_package_id=m5_stage_package_id,
        artifact_revision_id=m5_package_rev_id,
    )
    service.seal_revision(m5_package_rev_id)

    m5_version = service.get_step_run(m5_step_run_id)["status_version"]
    service.finish_step_run(
        m5_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": m5_step_run_id,
            "status_version": m5_version + 1,
            "status": "succeeded",
            "output_artifact_ids": [
                gate_results_rev_id,
                val_package_rev_id,
                m5_package_rev_id,
            ],
            "validation_report_ids": [],
            "log_artifact_ids": [m5_log_rev],
            "failure_artifact_ids": [],
        },
    )

    return {
        "edition_part_id": edition_part_id,
        "processing_run_id": processing_run_id,
        "corpus_stage_package_revision_id": m3_package_rev_id,
        "spans_revision_id": spans_revision_id,
        "candidate_package_revision_id": candidate_package_revision_id,
        "candidate_set_revision_id": candidate_set_revision_id,
        "validation_package_revision_id": val_package_rev_id,
        "gate_results_revision_id": gate_results_rev_id,
        "m3_step_run_id": m3_step_run_id,
        "m4_step_run_id": m4_step_run_id,
        "m5_step_run_id": m5_step_run_id,
    }
