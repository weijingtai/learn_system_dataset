"""M3 电子文本 StagePackage 组装（act/03，rulings 76、78、100 D2、102 Q4⑤）。

组装符合 openspec/schemas/stage_package.schema.json 的 StagePackage。产出的键名与键序
**逐字对齐 OCR 路线**（``pipeline/corpus_compiler/step.py``），下游不得为电子文本另写
读取分支（第 100 条 D2）。

零网络、零 Ledger，纯函数转换：调用方传入已构造好的 artifact_ref 与实算值。
"""

import hashlib


def assemble_m3_text_stage_package(
    *,
    stage_package_id: str,
    artifact_revision_id: str,
    processing_run_id: str,
    step_run_id: str,
    spans_revision_id: str,
    spans_bytes: bytes,
    counts: dict,
    coverage: dict,
    excluded_pages: dict,
    frozen_artifact_refs: list,
    corpus_package_ref: dict,
    validation_report_refs: list,
    log_refs: list,
    transformations: list,
) -> dict:
    """组装 M3 电子文本 StagePackage（键名/键序与 OCR 路线逐一相等）。

    参数：
        stage_package_id / artifact_revision_id：由调用方经 ``ids.new_id`` 生成。
        processing_run_id / step_run_id：本次运行身份。
        spans_revision_id / spans_bytes：本次 ``corpus_spans`` 修订与其字节。
        counts：``{"spans": n, "batches": m}``（与 OCR 路线同键）。
        coverage：``{<M1 page 标识>: <实算覆盖率>}``（第 102 条 Q4①）。
        excluded_pages：``{}``（电子文本无排除页，如实，第 102 条 Q4②）。
        frozen_artifact_refs：本次冻结的 M2 四件产物引用；它同时充当
            ``manifest.input_artifacts`` 与 ``lineage.upstream_artifacts``——电子文本路线
            的真实上游即这四件（第 102 条 Q4④）。
        corpus_package_ref：本次 ``corpus_package`` 修订引用（manifest.output_artifacts）。
        validation_report_refs / log_refs：校验报告与步骤日志引用。
        transformations：``compile_corpus`` 变换条目（键名与 OCR 路线相等）。

    返回：
        符合 stage_package.schema.json 的 m3 StagePackage dict，键序与 OCR 路线一致。
    """
    return {
        "schema_version": "1.0.0",
        "stage_package_id": stage_package_id,
        "artifact_revision_id": artifact_revision_id,
        "stage": "m3",
        "status": "sealed",
        "payload": {
            "spans_revision_id": spans_revision_id,
            "coverage": coverage,
            "excluded_pages": excluded_pages,
            "gate_profile": "structural_only",
            "semantic": "not_evaluated",
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "input_artifacts": list(frozen_artifact_refs),
            "output_artifacts": [corpus_package_ref],
            "counts": {"spans": counts["spans"], "batches": counts["batches"]},
            "content_sha256": hashlib.sha256(spans_bytes).hexdigest(),
        },
        "validation": {
            "passed": True,
            "report_artifacts": list(validation_report_refs),
        },
        "lineage": {
            "upstream_artifacts": list(frozen_artifact_refs),
            "transformations": list(transformations),
        },
        "logs": list(log_refs),
        "failures": [],
    }
