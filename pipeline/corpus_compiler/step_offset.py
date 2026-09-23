"""M3 电子文本事务：输入解析与 StepRun 写路径（G7-RULINGS 第 76、78、100、102 条，act/02）。

本模块实现：
1. resolve_m3_text_inputs：从 Ledger 解析 M2 四类产物（P5 门禁、deferred 门禁、零写入）；
2. run_m3_text：执行 M3 电子文本编译事务序列（Checkpoint 批次链、corpus_spans、
   coverage_report、corpus_package 与 m3 阶段包封存、血缘记录）。

三件产物（``corpus_spans``/``coverage_report``/``corpus_package``）与 m3 阶段包的键名、键序
与 OCR 路线（``pipeline/corpus_compiler/step.py``）逐一相等，下游不得为电子文本另写读取分支
（第 100 条 D2）。Gate 用电子文本路线自己的 ``gate_offset`` 判定（已验收）；Gate 不过即封存
失败，不登记阶段包。

严格遵守 P6（零网络调用）、第 88 条（SafeDumper 零污染）、P5（上游只认 succeeded）。
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

import yaml

from pipeline.intake import MANIFEST_TASK_ID
from pipeline.ledger import ids
from pipeline.ledger.service import LedgerService

from .assemble_offset import assemble_m3_text_stage_package
from .errors import CompileRefused
from .gate_offset import evaluate_text_coverage
from .text_compiler import compile_offset_spans

# 失败检查名闭集（act/02 contract §2）
FAILED_CHECKS = (
    "input_contract",
    "compile",
    "deferred_findings",
    "structural_gate",
    "internal",
)

M3_TEXT_TOOL = "pipeline.corpus_compiler.step_offset"
M3_TEXT_TOOL_VERSION = "0.1.0"


@dataclass
class M3TextInputs:
    """M3 电子文本阶段输入数据类（act/02 contract §1）。"""

    raw_text_revision_id: str
    raw_text: str
    cleaned_text_revision_id: str
    cleaned_text: str
    patch_set_revision_id: str
    patches: list[dict]
    report_revision_id: str
    sanitization_report: dict
    edition_part_id: str
    m2_step_run_id: str
    work: str = "qianyuan"
    edition: str = "ed01"
    processing_run_id: str = ""
    technique_id: str = "qizheng"


def _fail(service: LedgerService, step_run_id: str, check: str, detail: str) -> dict[str, Any]:
    """begin 之后的失败封存。"""
    if check not in FAILED_CHECKS:
        check = "internal"
    failure_data = json.dumps(
        {"check": check, "detail": detail}, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    _, failure_rev = service.put_artifact(
        step_run_id,
        "failure_report",
        failure_data,
        producer_module=M3_TEXT_TOOL,
        producer_version=M3_TEXT_TOOL_VERSION,
    )
    service.seal_revision(failure_rev)
    service.fail_step_run(step_run_id, [failure_rev], f"M3 {check}: {detail}")
    return {
        "status": "failed",
        "step_run_id": step_run_id,
        "failed_check": check,
        "failure_revision_id": failure_rev,
        "reason": detail,
    }


def _artifact_ref(service: LedgerService, revision_id: str) -> dict:
    """构造 artifact_ref（形态与 OCR 路线 ``step._artifact_ref`` 逐字一致，第 100 条 D2）。"""
    info = service.describe_revision(revision_id)
    if info is None:
        raise CompileRefused("SCH_001: 制品修订不存在: %s" % revision_id)
    return {
        "schema_version": "1.0.0",
        "artifact_kind": "artifact",
        "artifact_id": info["artifact_id"],
        "artifact_revision_id": revision_id,
        "artifact_type": info["artifact_type"],
    }


def _resolve_m1_page_ids(service: LedgerService, edition_part_id: str) -> list:
    """解析 M1 ``source_manifest`` 的页单位标识（第 102 条 Q4①）。

    电子文本在 M1 中的 page 标识即它的页单位（如 ``qianyuan_ed01_text``）。
    """
    for checkpoint in service.list_checkpoints(edition_part_id, "m1"):
        for task in checkpoint["content"].get("completed_tasks", []):
            if task.get("task_id") != MANIFEST_TASK_ID or task.get("status") != "succeeded":
                continue
            revision = service.get_revision(task["artifact_revision_id"])
            if revision is None:
                continue
            manifest = yaml.safe_load(service.read_object(revision["sha256"]).decode("utf-8"))
            pages = (manifest.get("edition_part") or {}).get("pages") or []
            if len(pages) != 1:
                raise CompileRefused(
                    "SCH_001: 电子文本路线要求 M1 恰 1 个 page 单位（第 102 条 Q4①），实际 %d 个"
                    % len(pages)
                )
            return list(pages)
    raise CompileRefused("SCH_001: 缺失 M1 source_manifest 产物（无法确定页单位）")


def _page_gaps_and_overlaps(spans: list) -> tuple:
    """按 ``start_offset`` 顺序实算页级缺口与重叠区间（OCR ``pages`` 同键）。"""
    gaps = []
    overlaps = []
    previous_end = 0
    for span in sorted(spans, key=lambda item: item.get("start_offset", 0)):
        start = span.get("start_offset")
        end = span.get("end_offset")
        if not (isinstance(start, int) and isinstance(end, int)):
            continue
        if start > previous_end:
            gaps.append([previous_end, start])
        elif start < previous_end:
            overlaps.append([start, previous_end])
        previous_end = max(previous_end, end)
    return gaps, overlaps


def _coverage_report(
    *,
    gate: dict,
    page_ids: list,
    span_count: int,
    coverage_value: float,
    line_count: int,
    spans: list,
) -> dict:
    """把已验收的电子文本 Gate 结果转换为 OCR 外形的 coverage_report（第 102 条 Q4③）。

    - ``checks.<名>.failures``：失败时 ``[detail]``，通过时 ``[]``（与 OCR 同键）；
    - ``pages``：``{<M1 page 标识>: <与 OCR 同键的实算值>}``；``line_count`` 取该页单位
      冻结 RawText 的物理行数，``span_count``/``coverage`` 为实算值，``gaps``/``overlaps``
      由 Span 偏移实算；
    - ``structural``/``semantic``/``gate_profile`` 与 OCR 同类取值；
    - **不改变** ``gate_offset`` 的判定逻辑。
    """
    gaps, overlaps = _page_gaps_and_overlaps(spans)
    checks = {
        name: {"ok": check["ok"], "failures": [] if check["ok"] else [check["detail"]]}
        for name, check in gate["checks"].items()
    }
    pages = {
        page: {
            "status": "covered",
            "terminal_state": None,
            "line_count": line_count,
            "span_count": span_count,
            "coverage": coverage_value,
            "gaps": gaps,
            "overlaps": overlaps,
        }
        for page in page_ids
    }
    return {
        "gate_profile": "structural_only",
        "structural": "passed" if gate["passed"] else "failed",
        "semantic": "not_evaluated",
        "checks": checks,
        "pages": pages,
    }


def resolve_m3_text_inputs(service: LedgerService, edition_part_id: str) -> M3TextInputs:
    """从 Ledger 解析对应 EditionPart 的 M2 产物并执行准入门禁（纯读，零写入）。

    异常分层与门禁：
        1. 必须找到已成功完成的 M2 StepRun，否则抛 CompileRefused("P5: M2 阶段未成功完成")；
        2. sanitization_report 中的 deferred_count 必须 == 0，否则抛 CompileRefused("§10.1: 存在暂缓处理项 deferred，阻断 M3 编译")；
        3. 缺失任一必要产物抛 CompileRefused("SCH_001: ...")。
    """
    # ---- 1. 定位 M2 StepRun ----
    m2_checkpoints = service.list_checkpoints(edition_part_id, "m2")
    m2_step_run_id = None
    if m2_checkpoints:
        for cp in reversed(m2_checkpoints):
            s_id = cp["content"].get("step_run_id")
            if s_id:
                m2_step_run_id = s_id
                break

    if not m2_step_run_id:
        # 退路：该 EditionPart 最近一次 **m2** StepRun（旧实现取的是最近一次任意阶段，
        # 会把 M3 自己或别的阶段的运行当成 M2；见 TODO T03 修正）。
        m2_runs = service.list_step_runs(edition_part_id, stage="m2")
        if m2_runs:
            m2_step_run_id = m2_runs[-1]["step_run_id"]

    if not m2_step_run_id:
        raise CompileRefused("P5: M2 阶段未成功完成 (未找到 M2 StepRun)")

    m2_step_run = service.get_step_run(m2_step_run_id)
    if m2_step_run is None or m2_step_run.get("status") != "succeeded":
        status_str = m2_step_run.get("status") if m2_step_run else "不存在"
        raise CompileRefused(f"P5: M2 阶段未成功完成 (状态: {status_str})")

    processing_run_id = m2_step_run.get("processing_run_id", "")
    technique_id = "qizheng"

    # ---- 2. 收集四类产物修订 ----
    # 端口按产生顺序返回该 StepRun 的产出修订（原 SQL 无 ORDER BY；同一类型多条时
    # 现在确定取最后产生的那条）。
    artifacts_by_type: dict[str, tuple[str, str]] = {}
    for produced in service.list_step_run_revisions(m2_step_run_id):
        artifacts_by_type[produced["artifact_type"]] = (
            produced["artifact_revision_id"],
            produced["sha256"],
        )

    # 查找 raw_text 修订：严格限定在 M2 StepRun 的 input_artifact_ids 中
    req_json = json.loads(m2_step_run["request_json"]) if "request_json" in m2_step_run else {}
    input_rev_ids = req_json.get("input_artifact_ids", [])
    technique_id = req_json.get("technique_profile_id", technique_id)

    raw_text_rev_id = None
    raw_text_sha256 = None
    for in_id in input_rev_ids:
        in_info = service.describe_revision(in_id)
        if in_info is None:
            continue
        if in_info["artifact_type"] == "raw_text":
            raw_text_rev_id = in_id
            raw_text_sha256 = in_info["sha256"]
            break
        elif raw_text_rev_id is None:
            raw_text_rev_id = in_id
            raw_text_sha256 = in_info["sha256"]

    if not raw_text_rev_id or not raw_text_sha256:
        raise CompileRefused("SCH_001: 缺失 raw_text 产物")

    if "cleaned_text_revision" not in artifacts_by_type:
        raise CompileRefused("SCH_001: 缺失 cleaned_text_revision 产物")
    cleaned_rev_id, cleaned_sha256 = artifacts_by_type["cleaned_text_revision"]

    if "deterministic_patch_set" not in artifacts_by_type:
        raise CompileRefused("SCH_001: 缺失 deterministic_patch_set 产物")
    patch_rev_id, patch_sha256 = artifacts_by_type["deterministic_patch_set"]

    if "sanitization_report" not in artifacts_by_type:
        raise CompileRefused("SCH_001: 缺失 sanitization_report 产物")
    report_rev_id, report_sha256 = artifacts_by_type["sanitization_report"]

    # ---- 3. 读取并反序列化内容 ----
    raw_bytes = service.read_object(raw_text_sha256)
    if raw_bytes is None:
        raise CompileRefused(f"SCH_001: 无法读取 raw_text 数据: {raw_text_sha256}")
    raw_text = raw_bytes.decode("utf-8")

    cleaned_bytes = service.read_object(cleaned_sha256)
    if cleaned_bytes is None:
        raise CompileRefused(f"SCH_001: 无法读取 cleaned_text 数据: {cleaned_sha256}")
    cleaned_text = cleaned_bytes.decode("utf-8")

    patch_bytes = service.read_object(patch_sha256)
    if patch_bytes is None:
        raise CompileRefused(f"SCH_001: 无法读取 deterministic_patch_set 数据: {patch_sha256}")
    try:
        patches = json.loads(patch_bytes.decode("utf-8"))
    except Exception:
        patches = yaml.safe_load(patch_bytes.decode("utf-8"))

    report_bytes = service.read_object(report_sha256)
    if report_bytes is None:
        raise CompileRefused(f"SCH_001: 无法读取 sanitization_report 数据: {report_sha256}")
    try:
        report = json.loads(report_bytes.decode("utf-8"))
    except Exception:
        report = yaml.safe_load(report_bytes.decode("utf-8"))

    # ---- 4. 校验清洗报告 deferred_count（第 88 条、§10.1 阻断门禁）----
    deferred_count = report.get("deferred_count")
    if deferred_count is None:
        deferred_count = report.get("summary", {}).get("deferred_count", 0)
    if deferred_count > 0:
        raise CompileRefused(f"§10.1: 存在暂缓处理项 deferred (count={deferred_count})，阻断 M3 编译")

    findings = report.get("findings", [])
    if any(f.get("terminal_state") == "deferred" for f in findings):
        raise CompileRefused("§10.1: 存在暂缓处理项 deferred，阻断 M3 编译")

    # 推导 work 与 edition
    work = "qianyuan"
    edition = "ed01"

    return M3TextInputs(
        raw_text_revision_id=raw_text_rev_id,
        raw_text=raw_text,
        cleaned_text_revision_id=cleaned_rev_id,
        cleaned_text=cleaned_text,
        patch_set_revision_id=patch_rev_id,
        patches=patches,
        report_revision_id=report_rev_id,
        sanitization_report=report,
        edition_part_id=edition_part_id,
        m2_step_run_id=m2_step_run_id,
        work=work,
        edition=edition,
        processing_run_id=processing_run_id,
        technique_id=technique_id,
    )


def run_m3_text(
    service: LedgerService,
    edition_part_id: str,
    *,
    batch_size: int = 10,
) -> dict[str, Any]:
    """在真实 Ledger 上执行 M3 电子文本结构编译 StepRun 事务。

    参数：
        service: LedgerService 实例
        edition_part_id: 版本部件标识
        batch_size: 批次切分大小（默认 10）

    返回：
        成功：{"status": "succeeded", "step_run_id": str, "spans_revision_id": str, ...}
        失败：{"status": "failed", "step_run_id": str, "failed_check": str, ...}
    """
    # ---- P1. 输入解析（begin 之前，校验失败直接抛出，零写入）----
    inputs = resolve_m3_text_inputs(service, edition_part_id)

    # 页单位（M1 page 标识）取自 M1 source_manifest（第 102 条 Q4①）；解析失败零写入。
    page_ids = _resolve_m1_page_ids(service, edition_part_id)

    # 原始文本内容检查
    if not inputs.raw_text:
        raise CompileRefused("SCH_002: raw_text 不能为空")

    # ---- P2. 阶段守卫（同阶段已存在 succeeded StepRun 则拒绝）----
    m3_checkpoints = service.list_checkpoints(edition_part_id, "m3")
    for cp in m3_checkpoints:
        s_id = cp["content"].get("step_run_id")
        if s_id:
            s_run = service.get_step_run(s_id)
            if s_run and s_run.get("status") == "succeeded":
                raise CompileRefused(f"M3 已封存：StepRun {s_id} 已 succeeded")

    # ---- P3. 配置与启动 begin_step_run ----
    processing_run_id = inputs.processing_run_id
    if not processing_run_id:
        processing_run_id = service.create_processing_run(
            "edition_run", edition_part_id, inputs.technique_id
        )

    config_dict = {
        "stage": "m3",
        "tool": M3_TEXT_TOOL,
        "tool_version": M3_TEXT_TOOL_VERSION,
        "evidence_level": "offset_level",
        "batch_size": batch_size,
        "gate_profile": "structural_only",
    }
    config_bytes = json.dumps(config_dict, sort_keys=True, ensure_ascii=False).encode("utf-8")
    _, config_rev_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        config_bytes,
        producer_module=M3_TEXT_TOOL,
        producer_version=M3_TEXT_TOOL_VERSION,
    )

    frozen = [
        inputs.raw_text_revision_id,
        inputs.cleaned_text_revision_id,
        inputs.patch_set_revision_id,
        inputs.report_revision_id,
    ]

    step_run_id = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": ids.new_id("step_run_id"),
            "input_artifact_ids": frozen,
            "technique_profile_id": inputs.technique_id,
            "configuration_artifact_id": config_rev_id,
        }
    )

    # ---- begin 之后：任何异常走 _fail 封存 ----
    try:
        # 1. 校验输入完整性与对象哈希
        for rev_id in frozen:
            rev = service.get_revision(rev_id)
            if not rev:
                return _fail(service, step_run_id, "input_contract", f"修订不存在: {rev_id}")
            try:
                data = service.read_object(rev["sha256"])
            except Exception as e:
                return _fail(service, step_run_id, "input_contract", f"对象内容读取失败: {e}")
            if data is None:
                return _fail(service, step_run_id, "input_contract", f"对象内容缺失: {rev['sha256']}")
            if hashlib.sha256(data).hexdigest() != rev["sha256"]:
                return _fail(service, step_run_id, "input_contract", f"对象哈希篡改: {rev_id}")

        # 2. 编译生成结构 Spans
        try:
            result = compile_offset_spans(
                work=inputs.work,
                edition=inputs.edition,
                edition_part_artifact_id=edition_part_id,
                raw_text_revision_id=inputs.raw_text_revision_id,
                raw_text=inputs.raw_text,
                cleaned_text_revision_id=inputs.cleaned_text_revision_id,
                cleaned_text=inputs.cleaned_text,
                patches=inputs.patches,
            )
        except Exception as exc:
            return _fail(service, step_run_id, "compile", str(exc))

        spans = result["spans"]

        # 3. 按 batch_size 切分子批次并写入 Checkpoint 链
        if not spans:
            batches = [[]]
        else:
            batches = [spans[i : i + batch_size] for i in range(0, len(spans), batch_size)]

        batch_rev_ids = []
        checkpoint_ids = []

        for idx, batch_spans in enumerate(batches):
            batch_id = f"batch_{idx + 1:03d}"
            batch_bytes = json.dumps(batch_spans, sort_keys=True, ensure_ascii=False).encode("utf-8")
            _, batch_rev = service.put_artifact(
                step_run_id,
                "corpus_batch",
                batch_bytes,
                producer_module=M3_TEXT_TOOL,
                producer_version=M3_TEXT_TOOL_VERSION,
            )
            service.seal_revision(batch_rev)
            batch_rev_ids.append(batch_rev)

            remaining = [{"task_id": f"batch_{j + 1:03d}"} for j in range(idx + 1, len(batches))]
            cp_rev = service.write_checkpoint(
                step_run_id,
                edition_part_id=edition_part_id,
                stage="m3",
                completed_tasks=[
                    {
                        "task_id": batch_id,
                        "artifact_revision_id": batch_rev,
                        "status": "succeeded",
                        "terminal_state": None,
                    }
                ],
                human_decisions=[],
                pending_queue=remaining,
                next_pointer=remaining[0] if remaining else None,
            )
            checkpoint_ids.append(cp_rev)

        # 4. 封存 corpus_spans 制品
        _, spans_rev_id = service.put_artifact(
            step_run_id,
            "corpus_spans",
            result["spans_bytes"],
            producer_module=M3_TEXT_TOOL,
            producer_version=M3_TEXT_TOOL_VERSION,
        )
        service.seal_revision(spans_rev_id)

        # 5. Gate 判定与实算覆盖率（电子文本路线自己的 Gate，act/03）
        covered_chars = sum(span["end_offset"] - span["start_offset"] for span in spans)
        total_chars = len(inputs.cleaned_text)
        coverage_value = (covered_chars / total_chars) if total_chars else 0.0
        coverage = {page: coverage_value for page in page_ids}
        excluded_pages = {}
        line_count = len(inputs.raw_text.splitlines())

        gate = evaluate_text_coverage(
            raw_text=inputs.raw_text,
            cleaned_text=inputs.cleaned_text,
            patches=inputs.patches,
            spans_doc=result["spans_doc"],
        )
        failed_checks = [name for name, check in gate["checks"].items() if not check["ok"]]

        # 6. coverage_report / validation_report / step_log（写序与 OCR 路线一致：先写后判）
        coverage_doc = _coverage_report(
            gate=gate,
            page_ids=page_ids,
            span_count=len(spans),
            coverage_value=coverage_value,
            line_count=line_count,
            spans=spans,
        )
        _, coverage_rev = service.put_artifact(
            step_run_id,
            "coverage_report",
            json.dumps(coverage_doc, sort_keys=True, ensure_ascii=False).encode("utf-8"),
            producer_module=M3_TEXT_TOOL,
            producer_version=M3_TEXT_TOOL_VERSION,
        )
        service.seal_revision(coverage_rev)

        validation_data = {
            "gate_profile": "structural_only",
            "structural": coverage_doc["structural"],
            "semantic": "not_evaluated",
            "failed_checks": failed_checks,
        }
        _, validation_rev = service.put_artifact(
            step_run_id,
            "validation_report",
            json.dumps(validation_data, sort_keys=True, ensure_ascii=False).encode("utf-8"),
            producer_module=M3_TEXT_TOOL,
            producer_version=M3_TEXT_TOOL_VERSION,
        )
        service.seal_revision(validation_rev)

        log_lines = [
            "resolve_m3_text_inputs",
            "compile_offset_spans spans=%d batches=%d" % (len(spans), len(batches)),
            "evaluate_text_coverage structural=%s" % coverage_doc["structural"],
        ]
        _, log_rev = service.put_artifact(
            step_run_id,
            "step_log",
            "\n".join(log_lines).encode("utf-8"),
            producer_module=M3_TEXT_TOOL,
            producer_version=M3_TEXT_TOOL_VERSION,
        )
        service.seal_revision(log_rev)

        # 7. Gate 失败 → 失败封存，不产出 corpus_package、不登记阶段包（与 OCR 路线一致）
        if not gate["passed"]:
            return _fail(
                service,
                step_run_id,
                "structural_gate",
                "Gate 判定 failed: %s" % "; ".join(failed_checks),
            )

        # 8. corpus_package
        corpus_data = json.dumps(
            {
                "spans_revision_id": spans_rev_id,
                "coverage_report_revision_id": coverage_rev,
                "coverage": coverage,
                "excluded_pages": excluded_pages,
                "gate_profile": "structural_only",
                "semantic": "not_evaluated",
            },
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
        _, corpus_rev = service.put_artifact(
            step_run_id,
            "corpus_package",
            corpus_data,
            producer_module=M3_TEXT_TOOL,
            producer_version=M3_TEXT_TOOL_VERSION,
        )
        service.seal_revision(corpus_rev)

        # 9. 记录 compile_corpus 变换（输出与 OCR 路线同形）
        compiled_outputs = [corpus_rev, spans_rev_id, coverage_rev]
        service.record_transformation(
            step_run_id,
            operation="compile_corpus",
            tool=M3_TEXT_TOOL,
            tool_version=M3_TEXT_TOOL_VERSION,
            configuration_revision_id=config_rev_id,
            input_revision_ids=frozen,
            output_revision_ids=compiled_outputs,
            validation_report_revision_id=validation_rev,
        )

        # 10. StagePackage（键名/键序与 OCR 路线逐一相等，第 100 条 D2）
        stage_package_id = ids.new_id("stage_package_id", stage="m3")
        package_revision_id = ids.new_id("artifact_revision_id")
        package = assemble_m3_text_stage_package(
            stage_package_id=stage_package_id,
            artifact_revision_id=package_revision_id,
            processing_run_id=processing_run_id,
            step_run_id=step_run_id,
            spans_revision_id=spans_rev_id,
            spans_bytes=result["spans_bytes"],
            counts={"spans": len(spans), "batches": len(batches)},
            coverage=coverage,
            excluded_pages=excluded_pages,
            frozen_artifact_refs=[_artifact_ref(service, rev_id) for rev_id in frozen],
            corpus_package_ref=_artifact_ref(service, corpus_rev),
            validation_report_refs=[_artifact_ref(service, validation_rev)],
            log_refs=[_artifact_ref(service, log_rev)],
            transformations=[
                {
                    "operation": "compile_corpus",
                    "step_run_id": step_run_id,
                    "configuration_artifact_revision_id": config_rev_id,
                    "input_artifact_revision_ids": frozen,
                    "output_artifact_revision_ids": compiled_outputs,
                }
            ],
        )
        service.register_stage_package(
            step_run_id,
            package,
            json.dumps(package, sort_keys=True, ensure_ascii=False).encode("utf-8"),
            stage_package_id=stage_package_id,
            artifact_revision_id=package_revision_id,
        )
        service.seal_revision(package_revision_id)

        # 11. 完成 StepRun
        output_artifacts = compiled_outputs + [package_revision_id]
        service.finish_step_run(
            step_run_id,
            {
                "schema_version": "1.0.0",
                "processing_run_id": processing_run_id,
                "step_run_id": step_run_id,
                "status_version": 1,
                "status": "succeeded",
                "output_artifact_ids": output_artifacts,
                "validation_report_ids": [validation_rev],
                "log_artifact_ids": [log_rev],
                "failure_artifact_ids": [],
            },
        )

        return {
            "status": "succeeded",
            "step_run_id": step_run_id,
            "spans_revision_id": spans_rev_id,
            "spans_sha256": result["spans_sha256"],
            "counts": result["counts"],
            "batches": len(batches),
            "batch_checkpoint_ids": checkpoint_ids,
            "coverage_report_revision_id": coverage_rev,
            "corpus_package_revision_id": corpus_rev,
            "validation_report_revision_id": validation_rev,
            "log_revision_id": log_rev,
            "stage_package_id": stage_package_id,
            "package_revision_id": package_revision_id,
            "coverage": coverage,
            "excluded_pages": excluded_pages,
            "gate": gate,
        }

    except Exception as exc:
        return _fail(service, step_run_id, "internal", f"{type(exc).__name__}: {exc}")
