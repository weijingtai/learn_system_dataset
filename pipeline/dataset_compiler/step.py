"""M8 在 Ledger 上真实编译：run_m8 事务序列（规格 §16、§17、§17.1）。

异常分层照搬 impl-02 ``pipeline/corpus_compiler/step.py``：
参数校验与 ``resolve_m8_inputs`` 产生的异常原样外抛；``create_processing_run`` /
``put_run_artifact`` / ``begin_step_run`` 本身抛出的异常原样外抛；``begin_step_run``
成功之后的任何例外一律 ``_fail("internal", …)`` 封存并返回 failed summary。
检查名闭集 {input_contract, admission, compile, publication_gate, internal}。
"""

import hashlib
import json
import re

import yaml

from pipeline.dataset_compiler import (
    CONSUMPTION_LEVELS,
    M8_TOOL,
    M8_TOOL_VERSION,
    SUB_PACK_SCHEMA_VERSION,
)
from pipeline.dataset_compiler import gate, levels, packs
from pipeline.dataset_compiler.canonical import canonical_bytes
from pipeline.dataset_compiler.errors import DatasetRefused
from pipeline.dataset_compiler.inputs import resolve_m8_inputs
from pipeline.ledger import ids
from pipeline.ledger.errors import SchemaViolation

MIN_APP_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")

_SCHEMA_VERSIONS = {
    "evidence_map_pack": SUB_PACK_SCHEMA_VERSION,
    "release_manifest": SUB_PACK_SCHEMA_VERSION,
    "source_asset_pack": SUB_PACK_SCHEMA_VERSION,
}


def _artifact_ref(revision_id, artifacts_map):
    """构造 artifact_ref dict。"""
    artifact_id, artifact_type = artifacts_map[revision_id]
    return {
        "schema_version": "1.0.0",
        "artifact_kind": "artifact",
        "artifact_id": artifact_id,
        "artifact_revision_id": revision_id,
        "artifact_type": artifact_type,
    }


def _build_artifacts_map(service, revision_ids):
    """构建 {revision_id: (artifact_id, artifact_type)} 映射。"""
    result = {}
    for revision_id in set(revision_ids):
        row = service.store.conn.execute(
            "SELECT a.artifact_id, a.artifact_type FROM artifacts a "
            "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
            "WHERE r.artifact_revision_id=?",
            (revision_id,),
        ).fetchone()
        if row:
            result[revision_id] = (row["artifact_id"], row["artifact_type"])
    return result


def _reconciliation(service, frozen):
    """冻结输入的 {artifact_revision_id, artifact_type, sha256} 对账列表。"""
    result = []
    for revision_id in frozen:
        revision = service.get_revision(revision_id)
        artifact_type = service.store.conn.execute(
            "SELECT a.artifact_type FROM artifacts a "
            "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
            "WHERE r.artifact_revision_id=?",
            (revision_id,),
        ).fetchone()[0]
        result.append(
            {
                "artifact_revision_id": revision_id,
                "artifact_type": artifact_type,
                "sha256": revision["sha256"],
            }
        )
    return result


def _read_and_verify_frozen(service, frozen):
    """一次性读取并校验每个冻结修订的对象字节（sha256 必须与登记值一致）。"""
    frozen_bytes = {}
    for revision_id in frozen:
        revision = service.get_revision(revision_id)
        data = service.objects.get(revision["sha256"])
        if hashlib.sha256(data).hexdigest() != revision["sha256"]:
            raise DatasetRefused(
                "冻结修订 %s 对象内容哈希不一致（SRC_003）" % revision_id, code="SRC_003"
            )
        frozen_bytes[revision_id] = data
    return frozen_bytes


def _validate_input_contract(service, inputs, manifest, spans_doc, m3_package, frozen_bytes):
    """§17 步骤 6：m3 包、spans、清单与页图的一致性校验，返回 asset_records。"""
    if m3_package.get("stage") != "m3":
        raise DatasetRefused("m3 包 stage 非法", code="SCH_002")
    if (m3_package.get("validation") or {}).get("passed") is not True:
        raise DatasetRefused("m3 包 validation.passed 非真", code="SCH_002")
    if m3_package["payload"]["spans_revision_id"] != inputs["spans_revision_id"]:
        raise DatasetRefused("m3 包 spans_revision_id 与解析不一致", code="SCH_002")
    spans_sha256 = hashlib.sha256(frozen_bytes[inputs["spans_revision_id"]]).hexdigest()
    if m3_package["manifest"]["content_sha256"] != spans_sha256:
        raise DatasetRefused("m3 包 content_sha256 与 spans 字节不符", code="SRC_003")

    manifest_refs = []
    page_set_refs = []
    page_refs = []
    for reference in m3_package["manifest"]["input_artifacts"]:
        if reference["artifact_type"] == "source_manifest":
            manifest_refs.append(reference["artifact_revision_id"])
        elif reference["artifact_type"] == "ocr_page_set":
            page_set_refs.append(reference["artifact_revision_id"])
        elif reference["artifact_type"] == "ocr_page":
            page_refs.append(reference["artifact_revision_id"])
    if manifest_refs != [inputs["manifest_revision_id"]]:
        raise DatasetRefused("m3 包 source_manifest 引用与解析不一致", code="REF_001")
    if page_set_refs != [inputs["ocr_page_set_revision_id"]]:
        raise DatasetRefused("m3 包 ocr_page_set 引用与解析不一致", code="REF_001")
    if set(page_refs) != set(inputs["page_revision_ids"].values()):
        raise DatasetRefused("m3 包 ocr_page 引用与解析不一致", code="REF_001")

    manifest_assets = {item["page"]: item for item in manifest["source_assets"]}
    asset_records = {}
    for page, revision_id in inputs["asset_revision_ids"].items():
        revision = service.get_revision(revision_id)
        asset_records[page] = {
            "artifact_revision_id": revision_id,
            "sha256": revision["sha256"],
            "size": revision["size_bytes"],
            "width": manifest_assets[page]["width"],
            "height": manifest_assets[page]["height"],
        }
    return asset_records


def _write_task_checkpoint(service, step_run_id, edition_part_id, task_id, revision_id, remaining):
    """每个 task 落盘一个 m8 Checkpoint（§17.1:843）。"""
    return service.write_checkpoint(
        step_run_id,
        edition_part_id=edition_part_id,
        stage="m8",
        completed_tasks=[
            {
                "task_id": task_id,
                "artifact_revision_id": revision_id,
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=[],
        pending_queue=[{"task_id": name} for name in remaining],
        next_pointer={"task_id": remaining[0]} if remaining else None,
    )


def _fail(service, step_run_id, check, detail):
    """失败封存：put failure_report → seal → fail_step_run → failed summary。"""
    _, failure_revision_id = service.put_artifact(
        step_run_id,
        "failure_report",
        canonical_bytes({"check": check, "detail": detail}),
        producer_module=M8_TOOL,
        producer_version=M8_TOOL_VERSION,
    )
    service.seal_revision(failure_revision_id)
    service.fail_step_run(step_run_id, [failure_revision_id], "M8 %s: %s" % (check, detail))
    return {
        "status": "failed",
        "step_run_id": step_run_id,
        "failed_check": check,
        "failure_revision_id": failure_revision_id,
        "reason": detail,
    }


def run_m8(service, edition_part_id, *, consumption_level, min_app_version=None, release_id=None):
    """在真实 Ledger 上执行 M8 首切片编译的完整事务序列（规格 §16、§17）。"""
    # ---- 1) 参数校验（begin 之前，无任何写入）----
    if consumption_level not in CONSUMPTION_LEVELS:
        raise SchemaViolation(
            "消费级别非法: %r（§16 闭集）" % (consumption_level,), code="SCH_002"
        )
    if min_app_version is not None and MIN_APP_VERSION_RE.match(min_app_version) is None:
        raise SchemaViolation(
            "min_app_version 格式非法: %r" % (min_app_version,), code="SCH_002"
        )
    if release_id is not None:
        ids.validate("release_id", release_id)

    # ---- 2) 解析输入（异常原样外抛）----
    inputs = resolve_m8_inputs(service, edition_part_id)

    # ---- 3) ProcessingRun（异常原样外抛）----
    processing_run_id = service.create_processing_run(
        "release_run", edition_part_id, inputs["technique_id"]
    )

    # ---- 4) 配置修订（异常原样外抛）----
    config_payload = {
        "stage": "m8",
        "tool": M8_TOOL,
        "tool_version": M8_TOOL_VERSION,
        "consumption_level": consumption_level,
        "min_app_version": min_app_version,
        "release_scope": {"edition_part_ids": [edition_part_id]},
    }
    if release_id is not None:
        config_payload["release_id"] = release_id
    _, config_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical_bytes(config_payload),
        producer_module=M8_TOOL,
        producer_version=M8_TOOL_VERSION,
    )

    # ---- 5) 冻结输入（按清单页序）与 begin（异常原样外抛）----
    manifest_revision = service.get_revision(inputs["manifest_revision_id"])
    manifest = yaml.safe_load(
        service.objects.get(manifest_revision["sha256"]).decode("utf-8")
    )
    frozen = [
        inputs["m3_package_revision_id"],
        inputs["spans_revision_id"],
        inputs["manifest_revision_id"],
        inputs["ocr_page_set_revision_id"],
    ]
    for page in manifest["edition_part"]["pages"]:
        frozen.append(inputs["page_revision_ids"][page])
    for page in manifest["edition_part"]["pages"]:
        frozen.append(inputs["asset_revision_ids"][page])

    step_run_id = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": ids.new_id("step_run_id"),
            "input_artifact_ids": frozen,
            "technique_profile_id": inputs["technique_id"],
            "configuration_artifact_id": config_revision_id,
        }
    )

    # ---- begin 之后：任何异常转为 internal 失败封存 ----
    try:
        return _run_after_begin(
            service, edition_part_id, step_run_id, processing_run_id, inputs, frozen,
            config_revision_id, consumption_level, min_app_version, release_id,
        )
    except Exception as exc:
        try:
            return _fail(
                service, step_run_id, "internal", "%s: %s" % (type(exc).__name__, exc)
            )
        except Exception as fail_exc:
            raise exc from fail_exc


def _run_after_begin(
    service, edition_part_id, step_run_id, processing_run_id, inputs, frozen,
    config_revision_id, consumption_level, min_app_version, release_id,
):
    """begin_step_run 成功之后的完整流程（§17 步骤 6–14）。"""
    # ---- 6) 输入契约 ----
    try:
        frozen_bytes = _read_and_verify_frozen(service, frozen)
        manifest = yaml.safe_load(frozen_bytes[inputs["manifest_revision_id"]].decode("utf-8"))
        spans_doc = yaml.safe_load(frozen_bytes[inputs["spans_revision_id"]].decode("utf-8"))
        m3_package = json.loads(frozen_bytes[inputs["m3_package_revision_id"]].decode("utf-8"))
        page_docs = {
            page: json.loads(frozen_bytes[revision_id].decode("utf-8"))
            for page, revision_id in inputs["page_revision_ids"].items()
        }
        asset_records = _validate_input_contract(
            service, inputs, manifest, spans_doc, m3_package, frozen_bytes
        )
    except Exception as exc:
        return _fail(service, step_run_id, "input_contract", str(exc))

    # ---- 7) 准入 ----
    admission = levels.evaluate_admission(
        consumption_level=consumption_level,
        content_statuses={spans_doc["content_status"]},
        evidence_level=spans_doc["evidence_level"],
        release_policy=manifest["release_policy"],
        rights_status=manifest["rights_status"],
        schema_versions=dict(_SCHEMA_VERSIONS),
        min_app_version=min_app_version,
    )
    if admission["admitted"] is not True:
        return _fail(
            service, step_run_id, "admission", "unmet: " + ",".join(admission["unmet"])
        )

    # ---- 8) 子包编译 ----
    checkpoint_revision_ids = []
    try:
        source_asset_pack = packs.build_source_asset_pack(
            manifest=manifest, asset_records=asset_records
        )
        _, source_asset_pack_revision_id = service.put_artifact(
            step_run_id, "source_asset_pack", source_asset_pack["bytes"],
            producer_module=M8_TOOL, producer_version=M8_TOOL_VERSION,
        )
        service.seal_revision(source_asset_pack_revision_id)
        checkpoint_revision_ids.append(
            _write_task_checkpoint(
                service, step_run_id, edition_part_id, "source_asset_pack",
                source_asset_pack_revision_id, packs.TASKS[1:],
            )
        )

        evidence_map_pack = packs.build_evidence_map_pack(
            spans_doc=spans_doc,
            page_docs=page_docs,
            ocr_page_revision_ids=inputs["page_revision_ids"],
            source_asset_pack=source_asset_pack["pack"],
            excluded_pages=inputs["excluded_pages"],
        )
        _, evidence_map_pack_revision_id = service.put_artifact(
            step_run_id, "evidence_map_pack", evidence_map_pack["bytes"],
            producer_module=M8_TOOL, producer_version=M8_TOOL_VERSION,
        )
        service.seal_revision(evidence_map_pack_revision_id)
        checkpoint_revision_ids.append(
            _write_task_checkpoint(
                service, step_run_id, edition_part_id, "evidence_map_pack",
                evidence_map_pack_revision_id, packs.TASKS[2:],
            )
        )
    except Exception as exc:
        return _fail(
            service, step_run_id, "compile", "%s: %s" % (type(exc).__name__, exc)
        )

    effective_release_id = release_id if release_id is not None else ids.new_id("release_id")

    # ---- 9) ReleaseManifest ----
    release_manifest = packs.build_release_manifest(
        release_id=effective_release_id,
        admission=admission,
        release_scope={"edition_part_ids": [edition_part_id]},
        technique_id=inputs["technique_id"],
        packs=[
            {
                "pack_type": "source_asset_pack",
                "artifact_revision_id": source_asset_pack_revision_id,
                "sha256": source_asset_pack["sha256"],
                "size": len(source_asset_pack["bytes"]),
            },
            {
                "pack_type": "evidence_map_pack",
                "artifact_revision_id": evidence_map_pack_revision_id,
                "sha256": evidence_map_pack["sha256"],
                "size": len(evidence_map_pack["bytes"]),
            },
        ],
        input_reconciliation=_reconciliation(service, frozen),
        schema_versions=dict(_SCHEMA_VERSIONS),
        min_app_version=min_app_version,
        known_defects=packs.compute_known_defects(
            evidence_map_pack=evidence_map_pack["pack"],
            m3_gate_profile=inputs["m3_gate_profile"],
            rights_status=manifest["rights_status"],
        ),
        watermark_text=packs.INTERNAL_DEMO_WATERMARK,
    )
    _, release_manifest_revision_id = service.put_artifact(
        step_run_id, "release_manifest", release_manifest["bytes"],
        producer_module=M8_TOOL, producer_version=M8_TOOL_VERSION,
    )
    service.seal_revision(release_manifest_revision_id)
    checkpoint_revision_ids.append(
        _write_task_checkpoint(
            service, step_run_id, edition_part_id, "release_manifest",
            release_manifest_revision_id, packs.TASKS[3:],
        )
    )

    # ---- 10) 独立发布 Gate ----
    gate_report = gate.evaluate_publication(
        manifest=manifest,
        spans_doc=spans_doc,
        page_docs=page_docs,
        ocr_page_revision_ids=inputs["page_revision_ids"],
        asset_records=asset_records,
        excluded_pages=inputs["excluded_pages"],
        m3_gate_profile=inputs["m3_gate_profile"],
        frozen_inputs=_reconciliation(service, frozen),
        source_asset_pack=source_asset_pack["pack"],
        evidence_map_pack=evidence_map_pack["pack"],
        release_manifest=release_manifest["manifest"],
        pack_bytes={
            "source_asset_pack": source_asset_pack["bytes"],
            "evidence_map_pack": evidence_map_pack["bytes"],
        },
        consumption_level=consumption_level,
    )
    validation_data = {
        "gate_profile": "m8_first_slice",
        "consumption_level": consumption_level,
        "admission": admission,
        "passed": gate_report["passed"],
        "checks": gate_report["checks"],
        "failed_checks": gate_report["failed_checks"],
        "knowledge_chain": "not_evaluated",
        "anchor_migration": "not_evaluated",
    }
    _, validation_revision_id = service.put_artifact(
        step_run_id, "validation_report", canonical_bytes(validation_data),
        producer_module=M8_TOOL, producer_version=M8_TOOL_VERSION,
    )
    service.seal_revision(validation_revision_id)
    checkpoint_revision_ids.append(
        _write_task_checkpoint(
            service, step_run_id, edition_part_id, "validation_report",
            validation_revision_id, packs.TASKS[4:],
        )
    )
    if gate_report["passed"] is not True:
        return _fail(
            service, step_run_id, "publication_gate",
            "failed_checks: " + ",".join(gate_report["failed_checks"]),
        )

    # ---- 11) PublicationPackage ----
    publication_data = {
        "release_id": effective_release_id,
        "consumption_level": consumption_level,
        "release_manifest_revision_id": release_manifest_revision_id,
        "validation_report_revision_id": validation_revision_id,
        "packs": {
            "evidence_map_pack": evidence_map_pack_revision_id,
            "source_asset_pack": source_asset_pack_revision_id,
        },
        "canonical_hash": release_manifest["canonical_hash"],
    }
    _, publication_package_revision_id = service.put_artifact(
        step_run_id, "publication_package", canonical_bytes(publication_data),
        producer_module=M8_TOOL, producer_version=M8_TOOL_VERSION,
    )
    service.seal_revision(publication_package_revision_id)

    # ---- 12) Transformation ----
    transformation_id = service.record_transformation(
        step_run_id,
        operation="compile_dataset",
        tool=M8_TOOL,
        tool_version=M8_TOOL_VERSION,
        configuration_revision_id=config_revision_id,
        input_revision_ids=frozen,
        output_revision_ids=[
            source_asset_pack_revision_id,
            evidence_map_pack_revision_id,
            release_manifest_revision_id,
            publication_package_revision_id,
        ],
        validation_report_revision_id=validation_revision_id,
        human_event_revision_ids=[],
    )

    # ---- 13) step_log 与 m8 StagePackage ----
    log_lines = [
        "resolve_m8_inputs",
        "compile source_asset_pack pages=%d" % len(source_asset_pack["pack"]["pages"]),
        "compile evidence_map_pack spans=%d" % len(evidence_map_pack["pack"]["entries"]),
        "evaluate_publication passed=%s" % gate_report["passed"],
    ]
    _, log_revision_id = service.put_artifact(
        step_run_id, "step_log", "\n".join(log_lines).encode("utf-8"),
        producer_module=M8_TOOL, producer_version=M8_TOOL_VERSION,
    )
    service.seal_revision(log_revision_id)

    counts = {
        "spans": len(evidence_map_pack["pack"]["entries"]),
        "pages": len(source_asset_pack["pack"]["pages"]),
        "source_assets": len(source_asset_pack["pack"]["pages"]),
        "glyph_highlights": evidence_map_pack["highlight_counts"]["glyph"],
        "line_bbox_highlights": evidence_map_pack["highlight_counts"]["line_bbox"],
        "packs": 2,
    }

    artifacts_map = _build_artifacts_map(
        service,
        frozen
        + [
            source_asset_pack_revision_id,
            evidence_map_pack_revision_id,
            release_manifest_revision_id,
            validation_revision_id,
            publication_package_revision_id,
            log_revision_id,
        ],
    )
    stage_package_id = ids.new_id("stage_package_id", stage="m8")
    package_revision_id = ids.new_id("artifact_revision_id")
    package = {
        "schema_version": "1.0.0",
        "stage_package_id": stage_package_id,
        "artifact_revision_id": package_revision_id,
        "stage": "m8",
        "status": "sealed",
        "payload": {
            "release_id": effective_release_id,
            "consumption_level": consumption_level,
            "release_manifest_revision_id": release_manifest_revision_id,
            "publication_package_revision_id": publication_package_revision_id,
            "canonical_hash": release_manifest["canonical_hash"],
            "knowledge_chain": "not_compiled",
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "input_artifacts": [_artifact_ref(revision_id, artifacts_map) for revision_id in frozen],
            "output_artifacts": [_artifact_ref(publication_package_revision_id, artifacts_map)],
            "counts": counts,
            "content_sha256": release_manifest["sha256"],
        },
        "validation": {
            "passed": True,
            "report_artifacts": [_artifact_ref(validation_revision_id, artifacts_map)],
        },
        "lineage": {
            "upstream_artifacts": [
                _artifact_ref(inputs["m3_package_revision_id"], artifacts_map),
                _artifact_ref(inputs["manifest_revision_id"], artifacts_map),
            ],
            "transformations": [
                {
                    "operation": "compile_dataset",
                    "step_run_id": step_run_id,
                    "configuration_artifact_revision_id": config_revision_id,
                    "input_artifact_revision_ids": frozen,
                    "output_artifact_revision_ids": [
                        source_asset_pack_revision_id,
                        evidence_map_pack_revision_id,
                        release_manifest_revision_id,
                        publication_package_revision_id,
                    ],
                }
            ],
        },
        "logs": [_artifact_ref(log_revision_id, artifacts_map)],
        "failures": [],
    }
    service.register_stage_package(
        step_run_id,
        package,
        json.dumps(package, sort_keys=True, ensure_ascii=False).encode("utf-8"),
        stage_package_id=stage_package_id,
        artifact_revision_id=package_revision_id,
    )
    service.seal_revision(package_revision_id)

    # ---- 14) finish_step_run ----
    current_version = service.get_step_run(step_run_id)["status_version"]
    step_manifest_revision_id = service.finish_step_run(
        step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "status_version": current_version + 1,
            "status": "succeeded",
            "output_artifact_ids": [
                source_asset_pack_revision_id,
                evidence_map_pack_revision_id,
                release_manifest_revision_id,
                publication_package_revision_id,
                package_revision_id,
            ],
            "validation_report_ids": [validation_revision_id],
            "log_artifact_ids": [log_revision_id],
            "failure_artifact_ids": [],
        },
    )

    return {
        "status": "succeeded",
        "processing_run_id": processing_run_id,
        "step_run_id": step_run_id,
        "configuration_revision_id": config_revision_id,
        "frozen_input_revision_ids": frozen,
        "release_id": effective_release_id,
        "admission": admission,
        "stage_package_id": stage_package_id,
        "package_revision_id": package_revision_id,
        "source_asset_pack_revision_id": source_asset_pack_revision_id,
        "evidence_map_pack_revision_id": evidence_map_pack_revision_id,
        "release_manifest_revision_id": release_manifest_revision_id,
        "validation_report_revision_id": validation_revision_id,
        "publication_package_revision_id": publication_package_revision_id,
        "canonical_hash": release_manifest["canonical_hash"],
        "counts": counts,
        "known_defects": release_manifest["manifest"]["known_defects"],
        "checkpoint_revision_ids": checkpoint_revision_ids,
        "transformation_id": transformation_id,
        "log_revision_id": log_revision_id,
        "step_manifest_revision_id": step_manifest_revision_id,
    }
