"""M3 电子文本 StagePackage 组装（act/03，rulings 76, 78）。

组装符合 openspec/schemas/stage_package.schema.json 的 StagePackage。
零网络、零 Ledger，纯函数转换。
"""

import hashlib
import uuid


def assemble_m3_text_stage_package(
    *,
    edition_part_id: str,
    spans_revision_id: str,
    spans_bytes: bytes,
    spans_doc: dict,
    validation_report_revision_id: str,
    coverage_report_revision_id: str,
    step_run_id: str,
    transformations: list,
) -> dict:
    """组装 M3 电子文本 StagePackage。

    返回的 dict 包含符合 schema 中 m3 stage required properties 的键：
        - schema_version: "1.0.0"
        - stage_package_id: pkg_m3_<32hex>
        - artifact_revision_id: rev_<32hex>
        - stage: "m3"
        - status: "sealed"
        - payload：包含 spans_revision_id, coverage_report_revision_id, coverage, gate_profile, evidence_level
        - manifest：包含 schema_version, processing_run_id, step_run_id,
                     input_artifacts, output_artifacts, counts, content_sha256
        - validation：passed(True), report_artifacts([validation_report_revision_id])
        - lineage：包含 transformations 列表
        - logs: []
        - failures: []
    """
    # 生成32位十六进制ID
    hex_id = uuid.uuid4().hex[:32]
    processing_run_id = f"prun_{hex_id}"

    # 解析 spans_doc 以获取 spans 列表和 counts
    spans = spans_doc.get("spans", []) or []
    span_count = len(spans)

    # 计算 manifest content_sha256
    content_sha256 = hashlib.sha256(spans_bytes).hexdigest()

    # 构造 artifact ref 对象
    def _artifact_ref(revision_id, kind="artifact"):
        # 提取32位hex部分用于模式匹配
        if "_" in revision_id:
            hex_part = revision_id.rsplit("_", 1)[1]
        else:
            hex_part = revision_id[:32] if len(revision_id) >= 32 else revision_id
        if kind == "stage_package":
            return {
                "schema_version": "1.0.0",
                "artifact_kind": kind,
                "stage_package_id": f"pkg_m3_{hex_part}",
                "artifact_revision_id": f"rev_{hex_part}",
                "artifact_type": revision_id,
            }
        else:
            return {
                "schema_version": "1.0.0",
                "artifact_kind": kind,
                "artifact_id": f"art_{hex_part}",
                "artifact_revision_id": f"rev_{hex_part}",
                "artifact_type": revision_id,
            }

    # payload
    payload = {
        "spans_revision_id": spans_revision_id,
        "coverage_report_revision_id": coverage_report_revision_id,
        "coverage": span_count,
        "gate_profile": "structural_only",
        "evidence_level": "offset_level",
    }

    # manifest - 必须包含 schema required: schema_version, processing_run_id,
    # step_run_id, input_artifacts, output_artifacts, counts, content_sha256
    manifest = {
        "schema_version": "1.0.0",
        "processing_run_id": processing_run_id,
        "step_run_id": step_run_id,
        "input_artifacts": [
            _artifact_ref(spans_revision_id, kind="stage_package"),
            _artifact_ref(coverage_report_revision_id, kind="stage_package"),
        ],
        "output_artifacts": [
            _artifact_ref(spans_revision_id, kind="stage_package"),
            _artifact_ref(coverage_report_revision_id),
        ],
        "counts": {"spans": span_count},
        "content_sha256": content_sha256,
    }

    # validation
    validation = {
        "passed": True,
        "report_artifacts": [_artifact_ref(validation_report_revision_id, kind="stage_package")],
    }

    # lineage
    lineage = {
        "upstream_artifacts": [],
        "transformations": transformations,
    }

    # complete StagePackage
    pkg = {
        "schema_version": "1.0.0",
        "stage_package_id": f"pkg_m3_{hex_id}",
        "artifact_revision_id": f"rev_{hex_id}",
        "stage": "m3",
        "status": "sealed",
        "payload": payload,
        "manifest": manifest,
        "validation": validation,
        "lineage": lineage,
        "logs": [],
        "failures": [],
    }

    return pkg