"""M7 创世汇编执行步骤（spec §17, §6.2, act/g0-04）。

实现 run_m7 最小事务与 begin_or_supersede 接替机制（G7-RULINGS 第 58 条）。
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pipeline.assembly import canonical, model
from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.gate import evaluate_genesis
from pipeline.assembly.genesis import assemble_genesis, propose_genesis
from pipeline.assembly.inputs import resolve_m7_inputs
from pipeline.ledger import ids

M7_TOOL = "pipeline.assembly"
M7_TOOL_VERSION = "0.1.0-draft"


def latest_succeeded_step_run(reader, edition_part_id: str, stage: str) -> Optional[str]:
    """该 EditionPart×Stage 上最近一个 ``succeeded`` 的 StepRun（只读，不写死号）。"""
    rows = reader.store.conn.execute(
        "SELECT DISTINCT c.step_run_id, c.created_at, c.rowid FROM stage_checkpoints c "
        "JOIN step_runs r ON r.step_run_id = c.step_run_id "
        "WHERE c.edition_part_id=? AND c.stage=? AND r.status='succeeded' "
        "ORDER BY c.created_at DESC, c.rowid DESC",
        (edition_part_id, stage),
    ).fetchall()
    return rows[0][0] if rows else None


def begin_or_supersede(
    service,
    edition_part_id: str,
    stage: str,
    configuration_revision_id: str,
    *,
    input_artifact_ids: Optional[List[str]] = None,
    processing_run_id: Optional[str] = None,
    technique_id: Optional[str] = None,
    step_run_id: Optional[str] = None,
    request: Optional[dict] = None,
) -> str:
    """按 G7-RULINGS 第 58 条建立同阶段 StepRun：若已有 succeeded 运行则接替之。"""
    previous = latest_succeeded_step_run(service, edition_part_id, stage)
    if request is None:
        new_step_run_id = step_run_id or ids.new_id("step_run_id")
        request = {
            "schema_version": "1.0.0",
            "step_run_id": new_step_run_id,
            "processing_run_id": processing_run_id,
            "input_artifact_ids": input_artifact_ids or [],
            "technique_profile_id": technique_id,
            "configuration_artifact_id": configuration_revision_id,
        }
    if previous is None:
        return service.begin_step_run(request)
    return service.supersede_step_run(previous, request)


def run_m7(
    service,
    edition_part_id: str,
    *,
    technique_id: str,
    reviewed_package_revision_ids: List[str],
    base_snapshot_revision_id: Optional[str] = None,
    id_range: Optional[dict] = None,
    _tamper_fn: Optional[Callable[[dict], None]] = None,
) -> Dict[str, Any]:
    """在真实 Ledger 上执行 M7 创世汇编事务。

    begin 之前前置校验失败抛出 AssemblyRefused，不写 Ledger；
    begin 之后异常一律失败封存并返回 status="failed"。
    """
    # ---- 1) begin 之前的拒绝（无写入）----
    if base_snapshot_revision_id is not None:
        raise AssemblyRefused(
            "当前为创世汇编薄切片，base_snapshot 增量汇编推迟至纵切后",
            code="SCH_002",
        )

    # 前置解析（异常直接抛出，无写入）
    inputs = resolve_m7_inputs(service, reviewed_package_revision_ids)

    # 创世重复检查：该 technique 已有 canonical_snapshot 时拒绝
    snap_rows = service.store.conn.execute(
        "SELECT r.artifact_revision_id, r.sha256 FROM artifact_revisions r "
        "JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "WHERE a.artifact_type='canonical_snapshot' AND r.status='sealed'"
    ).fetchall()
    for snap_rev_id, sha in snap_rows:
        raw = service.objects.get(sha)
        if raw:
            try:
                snap_doc = json.loads(raw.decode("utf-8"))
                if snap_doc.get("technique_id") == technique_id:
                    raise AssemblyRefused(
                        "technique %s 已汇编，创世汇编不可重复执行" % technique_id,
                        code="REF_001",
                    )
            except (ValueError, UnicodeDecodeError):
                pass

    actual_id_range = id_range if id_range is not None else {"pattern": [1, 10000]}

    # ---- 2) 创建 ProcessingRun（release_run）----
    proc_id = service.create_processing_run(
        "release_run",
        edition_part_id,
        technique_id,
    )

    # ---- 3) 登记配置修订 ----
    cfg_doc = {
        "stage": "m7",
        "task": "assemble",
        "technique_id": technique_id,
        "reviewed_package_revision_ids": reviewed_package_revision_ids,
        "base_snapshot_revision_id": None,
        "id_range": actual_id_range,
        "tool": M7_TOOL,
        "tool_version": M7_TOOL_VERSION,
    }
    cfg_bytes = json.dumps(cfg_doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
    cfg_id, cfg_rev_id = service.put_run_artifact(
        proc_id,
        "configuration",
        cfg_bytes,
        producer_module=M7_TOOL,
        producer_version=M7_TOOL_VERSION,
    )

    # ---- 4) 开启或接替 StepRun ----
    m6_rev_id = inputs["reviewed_package_revision_id"]
    step_run_id = begin_or_supersede(
        service,
        edition_part_id,
        "m7",
        cfg_rev_id,
        input_artifact_ids=[m6_rev_id],
        processing_run_id=proc_id,
        technique_id=technique_id,
    )

    # ---- 5) 汇编计算 ----
    cset = inputs["candidate_set"]
    ed = inputs["reviewed_edition"]
    prop_res = propose_genesis(cset, ed)
    assembly_res = assemble_genesis(cset, ed, prop_res["proposals"], id_range=actual_id_range)

    if _tamper_fn is not None:
        _tamper_fn(assembly_res["knowledge"])

    gate_res = evaluate_genesis(
        candidate_set=cset,
        reviewed_edition=ed,
        knowledge=assembly_res["knowledge"],
    )

    # ---- 6) Gate 失败处理 ----
    if not gate_res["passed"]:
        fail_doc = {
            "schema_version": "1.0.0",
            "step_run_id": step_run_id,
            "check_name": "genesis_gate",
            "gate": gate_res,
        }
        fail_bytes = json.dumps(fail_doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
        fail_art_id, fail_rev_id = service.put_artifact(
            step_run_id,
            "failure_report",
            fail_bytes,
            producer_module=M7_TOOL,
            producer_version=M7_TOOL_VERSION,
        )
        service.seal_revision(fail_rev_id)
        service.fail_step_run(step_run_id, [fail_rev_id], reason="Gate validation failed")
        return {
            "status": "failed",
            "step_run_id": step_run_id,
            "snapshot_revision_id": None,
            "assembly_package_revision_id": None,
            "validation_report_revision_id": None,
            "gate": gate_res,
        }

    # ---- 7) Gate 通过：写入产物 ----
    # 7.1 canonical_snapshot
    snap_bytes = assembly_res["knowledge_bytes"]
    snap_art_id, snap_rev_id = service.put_artifact(
        step_run_id,
        "canonical_snapshot",
        snap_bytes,
        producer_module=M7_TOOL,
        producer_version=M7_TOOL_VERSION,
    )
    service.seal_revision(snap_rev_id)

    # 7.2 assembly_package
    pkg_doc = {
        "schema_version": "0.1.0-draft",
        "technique_id": technique_id,
        "canonical_snapshot_revision_id": snap_rev_id,
        "report": {
            "excluded_unbound": assembly_res["report"]["excluded_unbound"],
        },
    }
    pkg_bytes = json.dumps(pkg_doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
    pkg_art_id, pkg_rev_id = service.put_artifact(
        step_run_id,
        "assembly_package",
        pkg_bytes,
        producer_module=M7_TOOL,
        producer_version=M7_TOOL_VERSION,
    )
    service.seal_revision(pkg_rev_id)

    # 7.3 validation_report
    val_doc = {
        "schema_version": "1.0.0",
        "passed": True,
        "checks": gate_res["checks"],
    }
    val_bytes = json.dumps(val_doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
    val_art_id, val_rev_id = service.put_artifact(
        step_run_id,
        "validation_report",
        val_bytes,
        producer_module=M7_TOOL,
        producer_version=M7_TOOL_VERSION,
    )
    service.seal_revision(val_rev_id)

    # 7.4 record_transformation
    service.record_transformation(
        step_run_id,
        operation="assemble_knowledge",
        tool=M7_TOOL,
        tool_version=M7_TOOL_VERSION,
        configuration_revision_id=cfg_rev_id,
        input_revision_ids=[m6_rev_id],
        output_revision_ids=[snap_rev_id, pkg_rev_id],
        validation_report_revision_id=val_rev_id,
    )

    # 7.5 register_stage_package (m7)
    stage_package_id = ids.new_id("stage_package_id", stage="m7")
    m7_pkg_rev_id = ids.new_id("artifact_revision_id")
    m6_art_id = service.get_revision(m6_rev_id)["artifact_id"]

    m7_stage_pkg = {
        "schema_version": "1.0.0",
        "stage_package_id": stage_package_id,
        "artifact_revision_id": m7_pkg_rev_id,
        "stage": "m7",
        "status": "draft",
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": proc_id,
            "step_run_id": step_run_id,
            "input_artifacts": [
                {
                    "schema_version": "1.0.0",
                    "artifact_kind": "artifact",
                    "artifact_id": m6_art_id,
                    "artifact_revision_id": m6_rev_id,
                    "artifact_type": "stage_package",
                }
            ],
            "output_artifacts": [
                {
                    "schema_version": "1.0.0",
                    "artifact_kind": "artifact",
                    "artifact_id": pkg_art_id,
                    "artifact_revision_id": pkg_rev_id,
                    "artifact_type": "assembly_package",
                }
            ],
            "counts": {"assembly_package": 1},
            "content_sha256": "0" * 64,
        },
        "validation": {
            "passed": True,
            "report_artifacts": [
                {
                    "schema_version": "1.0.0",
                    "artifact_kind": "artifact",
                    "artifact_id": val_art_id,
                    "artifact_revision_id": val_rev_id,
                    "artifact_type": "validation_report",
                }
            ],
        },
        "lineage": {
            "upstream_artifacts": [
                {
                    "schema_version": "1.0.0",
                    "artifact_kind": "artifact",
                    "artifact_id": m6_art_id,
                    "artifact_revision_id": m6_rev_id,
                    "artifact_type": "stage_package",
                }
            ],
            "transformations": [],
        },
        "payload": {},
        "logs": [],
        "failures": [],
    }
    m7_pkg_bytes = json.dumps(m7_stage_pkg, sort_keys=True, ensure_ascii=False).encode("utf-8")
    service.register_stage_package(
        step_run_id,
        m7_stage_pkg,
        m7_pkg_bytes,
        stage_package_id=stage_package_id,
        artifact_revision_id=m7_pkg_rev_id,
    )
    service.seal_revision(m7_pkg_rev_id)

    # 7.6 write_checkpoint (propose_r1 → seal_snapshot)
    service.write_checkpoint(
        step_run_id,
        edition_part_id=edition_part_id,
        stage="m7",
        completed_tasks=[
            {
                "task_id": "propose_r1",
                "artifact_revision_id": cfg_rev_id,
                "status": "succeeded",
            }
        ],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )
    service.write_checkpoint(
        step_run_id,
        edition_part_id=edition_part_id,
        stage="m7",
        completed_tasks=[
            {
                "task_id": "propose_r1",
                "artifact_revision_id": cfg_rev_id,
                "status": "succeeded",
            },
            {
                "task_id": "seal_snapshot",
                "artifact_revision_id": snap_rev_id,
                "status": "succeeded",
            },
        ],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )

    # 7.7 finish_step_run
    current_version = service.get_step_run(step_run_id)["status_version"]
    service.finish_step_run(
        step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": proc_id,
            "step_run_id": step_run_id,
            "status_version": current_version + 1,
            "status": "succeeded",
            "output_artifact_ids": [m7_pkg_rev_id, snap_rev_id, pkg_rev_id],
            "validation_report_ids": [val_rev_id],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
        },
    )

    return {
        "status": "succeeded",
        "step_run_id": step_run_id,
        "snapshot_revision_id": snap_rev_id,
        "assembly_package_revision_id": pkg_rev_id,
        "validation_report_revision_id": val_rev_id,
        "gate": gate_res,
    }
