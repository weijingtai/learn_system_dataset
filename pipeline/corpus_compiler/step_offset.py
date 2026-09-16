"""M3 电子文本事务：输入解析与 StepRun 写路径（G7-RULINGS 第 76、78 条，act/02）。

本模块实现：
1. resolve_m3_text_inputs：从 Ledger 解析 M2 四类产物（P5 门禁、deferred 门禁、零写入）；
2. run_m3_text：执行 M3 电子文本编译事务序列（Checkpoint 批次链、corpus_spans 封存、血缘记录）。

严格遵守 P6（零网络调用）、第 88 条（SafeDumper 零污染）、P5（上游只认 succeeded）。
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

import yaml

from pipeline.ledger import ids
from pipeline.ledger.service import LedgerService

from .errors import CompileRefused
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
        # 尝试从 processing_runs 寻找最近的 step_run
        row = service.store.conn.execute(
            "SELECT sr.step_run_id FROM step_runs sr "
            "JOIN processing_runs pr ON pr.processing_run_id = sr.processing_run_id "
            "WHERE pr.edition_part_id=? ORDER BY sr.created_at DESC LIMIT 1",
            (edition_part_id,),
        ).fetchone()
        if row:
            m2_step_run_id = row[0]

    if not m2_step_run_id:
        raise CompileRefused("P5: M2 阶段未成功完成 (未找到 M2 StepRun)")

    m2_step_run = service.get_step_run(m2_step_run_id)
    if m2_step_run is None or m2_step_run.get("status") != "succeeded":
        status_str = m2_step_run.get("status") if m2_step_run else "不存在"
        raise CompileRefused(f"P5: M2 阶段未成功完成 (状态: {status_str})")

    processing_run_id = m2_step_run.get("processing_run_id", "")
    technique_id = "qizheng"

    # ---- 2. 收集四类产物修订 ----
    produced_rows = service.store.conn.execute(
        "SELECT a.artifact_type, r.artifact_revision_id, r.sha256 FROM artifacts a "
        "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
        "WHERE r.step_run_id=?",
        (m2_step_run_id,),
    ).fetchall()

    artifacts_by_type: dict[str, tuple[str, str]] = {}
    for art_type, rev_id, sha256 in produced_rows:
        artifacts_by_type[art_type] = (rev_id, sha256)

    # 查找 raw_text 修订：严格限定在 M2 StepRun 的 input_artifact_ids 中
    req_json = json.loads(m2_step_run["request_json"]) if "request_json" in m2_step_run else {}
    input_rev_ids = req_json.get("input_artifact_ids", [])
    technique_id = req_json.get("technique_profile_id", technique_id)

    raw_text_rev_id = None
    raw_text_sha256 = None
    for in_id in input_rev_ids:
        in_row = service.store.conn.execute(
            "SELECT a.artifact_type, r.sha256 FROM artifacts a "
            "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
            "WHERE r.artifact_revision_id=?",
            (in_id,),
        ).fetchone()
        if in_row and in_row[0] == "raw_text":
            raw_text_rev_id = in_id
            raw_text_sha256 = in_row[1]
            break
        elif in_row and raw_text_rev_id is None:
            raw_text_rev_id = in_id
            raw_text_sha256 = in_row[1]

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
    raw_bytes = service.objects.get(raw_text_sha256)
    if raw_bytes is None:
        raise CompileRefused(f"SCH_001: 无法读取 raw_text 数据: {raw_text_sha256}")
    raw_text = raw_bytes.decode("utf-8")

    cleaned_bytes = service.objects.get(cleaned_sha256)
    if cleaned_bytes is None:
        raise CompileRefused(f"SCH_001: 无法读取 cleaned_text 数据: {cleaned_sha256}")
    cleaned_text = cleaned_bytes.decode("utf-8")

    patch_bytes = service.objects.get(patch_sha256)
    if patch_bytes is None:
        raise CompileRefused(f"SCH_001: 无法读取 deterministic_patch_set 数据: {patch_sha256}")
    try:
        patches = json.loads(patch_bytes.decode("utf-8"))
    except Exception:
        patches = yaml.safe_load(patch_bytes.decode("utf-8"))

    report_bytes = service.objects.get(report_sha256)
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
                data = service.objects.get(rev["sha256"])
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

        # 5. 记录 compile_corpus 变换
        output_artifacts = [spans_rev_id] + batch_rev_ids
        service.record_transformation(
            step_run_id,
            operation="compile_corpus",
            tool=M3_TEXT_TOOL,
            tool_version=M3_TEXT_TOOL_VERSION,
            configuration_revision_id=config_rev_id,
            input_revision_ids=frozen,
            output_revision_ids=output_artifacts,
        )

        # 6. 完成 StepRun
        service.finish_step_run(
            step_run_id,
            {
                "schema_version": "1.0.0",
                "processing_run_id": processing_run_id,
                "step_run_id": step_run_id,
                "status_version": 1,
                "status": "succeeded",
                "output_artifact_ids": output_artifacts,
                "validation_report_ids": [],
                "log_artifact_ids": [],
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
        }

    except Exception as exc:
        return _fail(service, step_run_id, "internal", f"{type(exc).__name__}: {exc}")
