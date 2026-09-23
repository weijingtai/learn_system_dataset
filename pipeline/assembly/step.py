"""M7 创世汇编执行步骤（spec §17, §6.2, act/g0-04）。

实现 run_m7 最小事务与 begin_or_supersede 接替机制（G7-RULINGS 第 58 条）。
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pipeline.assembly import canonical, incremental, model, orchestrate
from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.gate import evaluate_assembly, evaluate_genesis
from pipeline.assembly.genesis import assemble_genesis, propose_genesis
from pipeline.assembly.inputs import resolve_base_snapshot, resolve_m7_inputs
from pipeline.ledger import ids
from pipeline.ledger.errors import LedgerError

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


def _run_incremental_round(
    service,
    *,
    step_run_id: str,
    scope_key: str,
    technique_id: str,
    base: dict,
    proposal_res: dict,
    pending: List[str],
) -> Dict[str, Any]:
    """增量提案轮（B 波；CHARTER §9.3 收口，BDD 8.1 的形状）。

    只把**已算出**的提案轮落盘 ``assembly_proposal_set`` / ``assembly_report``，
    把待人工决定写进 Checkpoint 的 ``pending_queue``，然后 ``await_human``。

    D 波之后，走到这里只意味着 `orchestrate.assemble` 报了 ``awaiting_human``
    （仍有待决/依赖未决提案）；无待决时由 :func:`_finish_incremental` 完成合并。
    """
    prop_doc = {
        "schema_version": "1.0.0",
        "technique_id": technique_id,
        "base_snapshot_revision_id": base["revision_id"],
        "round": proposal_res["round"],
        "modes": proposal_res["modes"],
        "proposals": proposal_res["proposals"],
        "not_comparable": proposal_res["not_comparable"],
    }
    prop_art_id, prop_rev_id = service.put_artifact(
        step_run_id,
        "assembly_proposal_set",
        json.dumps(prop_doc, sort_keys=True, ensure_ascii=False).encode("utf-8"),
        producer_module=M7_TOOL,
        producer_version=M7_TOOL_VERSION,
    )
    service.seal_revision(prop_rev_id)

    report_doc = {
        "schema_version": "1.0.0",
        "technique_id": technique_id,
        "report": proposal_res["report"],
    }
    rep_art_id, rep_rev_id = service.put_artifact(
        step_run_id,
        "assembly_report",
        json.dumps(report_doc, sort_keys=True, ensure_ascii=False).encode("utf-8"),
        producer_module=M7_TOOL,
        producer_version=M7_TOOL_VERSION,
    )
    service.seal_revision(rep_rev_id)

    service.write_checkpoint(
        step_run_id,
        edition_part_id=scope_key,
        stage="m7",
        completed_tasks=[
            {
                "task_id": "propose_r2",
                "artifact_revision_id": prop_rev_id,
                "status": "succeeded",
            }
        ],
        human_decisions=[],
        pending_queue=pending,
        next_pointer=None,
    )
    service.await_human(step_run_id, [prop_rev_id, rep_rev_id])

    return {
        "status": "awaiting_human",
        "step_run_id": step_run_id,
        "snapshot_revision_id": None,
        "assembly_package_revision_id": None,
        "validation_report_revision_id": None,
        "proposals_revision_id": prop_rev_id,
        "assembly_report_revision_id": rep_rev_id,
        "pending_proposals": pending,
    }


def _finish_incremental(
    service,
    *,
    step_run_id: str,
    scope_key: str,
    technique_id: str,
    base: dict,
    packages: List[dict],
    views: List[dict],
    decisions: List[dict],
    outcome: Dict[str, Any],
    proc_id: str,
    cfg_rev_id: str,
    frozen_revision_ids: List[str],
) -> Dict[str, Any]:
    """增量合并轮收尾：写 Snapshot（prev 指向基底）+ 增量与全量等价自证。

    CHARTER §9.3：写盘前先过名实一致护栏；`meta.base_snapshot_revision_id` 由
    `orchestrate.assemble` 补齐，与 `prev_revision_id` 一致。
    """
    result = outcome["result"]
    knowledge = result["knowledge"]
    base_revision_id = base["revision_id"]

    # 五：增量必须等于全量（本波自证；E 波会独立复验）
    full = orchestrate.assemble(
        base["doc"],
        views,
        decisions,
        incremental=False,
        base_snapshot_revision_id=base_revision_id,
    )
    equivalent = full["status"] == "complete" and orchestrate.knowledge_equivalent(
        knowledge, full["result"]["knowledge"]
    )
    # CHARTER §13.2：`rebuilt == affected` 等式断言已在 D 波删除（闭包一旦真的扩张，
    # 扩张到的对象本轮不会被重建 → 等式不可满足；不扩张时它又是空转）。
    # 此处残留的是同一条等式的副本，同源书返工（闭包经冲突组扩张）第一次跑全栈就撞上它。
    # 按 §13.2 改回「低廉的健全检查」：`rebuilt ⊆ affected`。
    checks = {
        "rebuilt_subset_of_affected": set(result["rebuilt_entity_ids"]).issubset(
            set(outcome["report"]["affected_entity_ids"])
        ),
        "incremental_equals_full_rebuild": bool(equivalent),
    }

    # 三（ACT 25）：增量轮必须有**独立 Gate**，且在写 Snapshot **之前** 跑——
    # 不过即失败封存，不写 Snapshot、不留跑着的 StepRun。
    gate_res = evaluate_assembly(
        base_knowledge=base["doc"],
        views=views,
        decisions=decisions,
        knowledge=knowledge,
        identity_delta=result["identity_delta"],
        collation=result["collation"],
        report=outcome["report"],
    )
    if not gate_res["passed"]:
        failed_checks = sorted(
            name for name, check in gate_res["checks"].items() if not check["passed"]
        )
        fail_doc = {
            "schema_version": "1.0.0",
            "step_run_id": step_run_id,
            "check_name": "incremental_gate",
            "failed_checks": failed_checks,
            "gate": gate_res,
            "checks": checks,
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
        service.fail_step_run(
            step_run_id,
            [fail_rev_id],
            reason="incremental gate failed: %s" % ",".join(failed_checks),
        )
        return {
            "status": "failed",
            "step_run_id": step_run_id,
            "snapshot_revision_id": None,
            "assembly_package_revision_id": None,
            "validation_report_revision_id": None,
            "failed_checks": failed_checks,
            "gate": gate_res,
        }

    incremental.assert_prev_meta_agreement(base_revision_id, knowledge)
    snap_art_id, snap_rev_id = service.put_artifact(
        step_run_id,
        "canonical_snapshot",
        result["knowledge_bytes"],
        prev_revision_id=base_revision_id,
        producer_module=M7_TOOL,
        producer_version=M7_TOOL_VERSION,
    )
    service.seal_revision(snap_rev_id)

    pkg_doc = {
        "schema_version": "0.1.0-draft",
        "technique_id": technique_id,
        "canonical_snapshot_revision_id": snap_rev_id,
        "assembly_report": outcome["report"],
        "identity_delta": result["identity_delta"],
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

    val_doc = {
        "schema_version": "1.0.0",
        "passed": bool(gate_res["passed"] and all(checks.values())),
        "checks": checks,
        "incremental_gate": gate_res,
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

    service.record_transformation(
        step_run_id,
        operation="assemble_incremental",
        tool=M7_TOOL,
        tool_version=M7_TOOL_VERSION,
        configuration_revision_id=cfg_rev_id,
        input_revision_ids=frozen_revision_ids,
        output_revision_ids=[snap_rev_id, pkg_rev_id],
        validation_report_revision_id=val_rev_id,
    )

    if not all(checks.values()):
        fail_doc = {
            "schema_version": "1.0.0",
            "step_run_id": step_run_id,
            "check_name": "incremental_equivalence",
            "checks": checks,
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
        service.fail_step_run(step_run_id, [fail_rev_id], reason="incremental equivalence failed")
        return {
            "status": "failed",
            "step_run_id": step_run_id,
            "snapshot_revision_id": snap_rev_id,
            "assembly_package_revision_id": pkg_rev_id,
            "validation_report_revision_id": val_rev_id,
            "checks": checks,
        }

    stage_package_id = ids.new_id("stage_package_id", stage="m7")
    m7_pkg_rev_id = ids.new_id("artifact_revision_id")
    input_entries = [
        {
            "schema_version": "1.0.0",
            "artifact_kind": "artifact",
            "artifact_id": package["reviewed_package_artifact_id"],
            "artifact_revision_id": package["reviewed_package_revision_id"],
            "artifact_type": "stage_package",
        }
        for package in packages
    ]
    input_entries.append(
        {
            "schema_version": "1.0.0",
            "artifact_kind": "artifact",
            "artifact_id": base["artifact_id"],
            "artifact_revision_id": base_revision_id,
            "artifact_type": base["artifact_type"],
        }
    )
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
            "input_artifacts": list(input_entries),
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
        "lineage": {"upstream_artifacts": list(input_entries), "transformations": []},
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

    service.write_checkpoint(
        step_run_id,
        edition_part_id=scope_key,
        stage="m7",
        completed_tasks=[
            {
                "task_id": "assemble_incremental",
                "artifact_revision_id": snap_rev_id,
                "status": "succeeded",
            }
        ],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )

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
        "base_snapshot_revision_id": base_revision_id,
        "report": outcome["report"],
    }


def run_m7(
    service,
    edition_part_id: str,
    *,
    technique_id: str,
    reviewed_package_revision_ids: List[str],
    base_snapshot_revision_id: Optional[str] = None,
    id_range: Optional[dict] = None,
    decisions: Optional[List[dict]] = None,
    _tamper_fn: Optional[Callable[[dict], None]] = None,
) -> Dict[str, Any]:
    """在真实 Ledger 上执行一次 M7 汇编事务（创世或增量）。

    begin 之前前置校验失败抛出 AssemblyRefused，不写 Ledger；
    begin 之后异常一律失败封存并返回 status="failed"。

    - ``base_snapshot_revision_id is None`` → 创世路径，行为与 g0-04 逐字相同
      （ProcessingRun 的 scope 仍是调用方给的 ``edition_part_id``）。
    - 非 None → 增量路径（ACT 21 contract 二/三）：先**只读**校验并读出基底 Snapshot，
      ReleaseRun 改用本 Run 自己的配置 Artifact 身份作 scope 键（D-02 A），
      新 Snapshot 写成同一 Snapshot Artifact 的新修订并 ``prev`` 指向基底（D-03 A）。
      D 波起，增量路径走 :func:`pipeline.assembly.orchestrate.assemble`：
      有待决 → 只出提案并 ``await_human``；无待决 → 完成合并、写新 Snapshot
      （``prev`` 与 ``meta.base_snapshot_revision_id`` 同时非空，CHARTER §9.3）。
      增量 Gate 属 E 波，本波只自证「增量 == 全量」。
    """
    # ---- 1) begin 之前的拒绝（无写入）----
    # 基底 Snapshot：只读校验（superseded 的基底在这里就拒收，D-15 前半）
    base = None
    if base_snapshot_revision_id is not None:
        base = resolve_base_snapshot(service, base_snapshot_revision_id)

    # 前置解析（异常直接抛出，无写入）
    inputs = resolve_m7_inputs(service, reviewed_package_revision_ids)
    packages = inputs["packages"]
    if len(packages) > 1:
        # 多包 = 多 Edition / 多版次同 Run 编排：D 波只接通了**单包**增量
        # （`resolve_m7_inputs` 已能解析多包，但 apply 的版次合并仍按新 source 追加），
        # 故在此显式拒收，**不静默只取第一个包**。
        if inputs["replaces"]:
            raise AssemblyRefused(
                "多包替换（同一 source_id 与 edition_part_ids 集合出现多次）的继承逻辑属 D 波，"
                "本波只解析与标记: %d 个包" % len(packages),
                code="SCH_002",
            )
        raise AssemblyRefused(
            "多包合并（多 Edition / 多版次）属 B/C 波，本波只解析与标记: %d 个包" % len(packages),
            code="SCH_002",
        )

    # 创世重复检查：该 technique 已有 canonical_snapshot 时拒绝
    # （增量路径的定义就是给同一 technique 追加新 Snapshot 修订，不适用本条）
    if base is not None:
        snap_rows = []
    else:
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

    # ---- 1.5) 增量轮：提案生成（B 波）----
    # 见 _run_incremental_round：本波不做合并，因而不写 canonical_snapshot。

    # ---- 2) 创建 ProcessingRun（release_run）----
    # D-02 A：增量 ReleaseRun 跨多个 Edition，没有单一 EditionPart，
    # 故以「本 Run 自己的配置 Artifact 身份」为 scope 键（也是 Checkpoint 链键）；
    # 创世路径沿用调用方给的 edition_part_id（BDD G0.8、acceptance.check_configuration_and_scope）。
    scope_key = ids.new_id("artifact_id") if base is not None else edition_part_id
    proc_id = service.create_processing_run(
        "release_run",
        scope_key,
        technique_id,
    )

    # ---- 3) 登记配置修订 ----
    cfg_doc = {
        "stage": "m7",
        "task": "assemble",
        "technique_id": technique_id,
        "reviewed_package_revision_ids": reviewed_package_revision_ids,
        "base_snapshot_revision_id": base_snapshot_revision_id,
        "id_range": actual_id_range,
        "tool": M7_TOOL,
        "tool_version": M7_TOOL_VERSION,
    }
    cfg_bytes = json.dumps(cfg_doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
    cfg_id, cfg_rev_id = service.put_run_artifact(
        proc_id,
        "configuration",
        cfg_bytes,
        artifact_id=scope_key if base is not None else None,
        producer_module=M7_TOOL,
        producer_version=M7_TOOL_VERSION,
    )

    # ---- 4) 开启或接替 StepRun ----
    # 上游冻结输入 = 全部 m6 包（本波已拒多包，故实为 1 个）+ 基底 Snapshot（增量时）
    frozen_revision_ids = [p["reviewed_package_revision_id"] for p in packages]
    if base is not None:
        frozen_revision_ids.append(base["revision_id"])
    step_run_id = begin_or_supersede(
        service,
        scope_key,
        "m7",
        cfg_rev_id,
        input_artifact_ids=frozen_revision_ids,
        processing_run_id=proc_id,
        technique_id=technique_id,
    )

    # ---- 4.5) 增量路径：走增量编排（D 波，act/impl-07/24）----
    if base is not None:
        views = [
            {
                "source_id": package["source_id"],
                "candidate_set": package["candidate_set"],
                "reviewed_edition": package["reviewed_edition"],
            }
            for package in packages
        ]
        decisions = list(decisions or [])
        try:
            outcome = orchestrate.assemble(
                base["doc"],
                views,
                decisions,
                incremental=True,
                base_snapshot_revision_id=base["revision_id"],
            )
        except (AssemblyRefused, LedgerError) as exc:
            # begin 之后异常一律失败封存并返回 status="failed"（不得留下跑着的 StepRun）。
            # 含 apply 抛出的 SchemaViolation / DuplicateIdentifier / MissingReference，
            # 例如真书 m6 上 B 波提案重号（C 波回报 §3.4）→ 必须 fail-closed 而不是把异常丢出事务。
            fail_doc = {
                "schema_version": "1.0.0",
                "step_run_id": step_run_id,
                "check_name": "incremental_orchestration",
                "error": str(exc),
                "code": exc.code,
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
            service.fail_step_run(step_run_id, [fail_rev_id], reason="incremental orchestration failed")
            return {
                "status": "failed",
                "step_run_id": step_run_id,
                "snapshot_revision_id": None,
                "assembly_package_revision_id": None,
                "validation_report_revision_id": None,
                "error": str(exc),
            }
        if outcome["status"] == "awaiting_human":
            return _run_incremental_round(
                service,
                step_run_id=step_run_id,
                scope_key=scope_key,
                technique_id=technique_id,
                base=base,
                proposal_res=outcome["rounds"][-1],
                pending=outcome["pending"],
            )
        return _finish_incremental(
            service,
            step_run_id=step_run_id,
            scope_key=scope_key,
            technique_id=technique_id,
            base=base,
            packages=packages,
            views=views,
            decisions=decisions,
            outcome=outcome,
            proc_id=proc_id,
            cfg_rev_id=cfg_rev_id,
            frozen_revision_ids=frozen_revision_ids,
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
    # D-03 A：每 technique 一个 Snapshot Artifact；合并轮（C 波）写同一 Artifact 的新修订，
    # prev 指向基底（传 prev_revision_id 而不传 artifact_id —— put_artifact 会复用 prev 所属
    # Artifact；显式传已存在的 artifact_id 会被 _new_or_explicit 拒为 ID_002）。
    # 写盘前先过名实一致护栏（CHARTER §9.3）：prev 非空 ⟺ meta.base_snapshot_revision_id 非空。
    prev_snapshot_revision_id = base["revision_id"] if base is not None else None
    incremental.assert_prev_meta_agreement(prev_snapshot_revision_id, assembly_res["knowledge"])
    snap_bytes = assembly_res["knowledge_bytes"]
    snap_art_id, snap_rev_id = service.put_artifact(
        step_run_id,
        "canonical_snapshot",
        snap_bytes,
        prev_revision_id=base["revision_id"] if base is not None else None,
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
        input_revision_ids=frozen_revision_ids,
        output_revision_ids=[snap_rev_id, pkg_rev_id],
        validation_report_revision_id=val_rev_id,
    )

    # 7.5 register_stage_package (m7)
    stage_package_id = ids.new_id("stage_package_id", stage="m7")
    m7_pkg_rev_id = ids.new_id("artifact_revision_id")
    # 血缘输入 = 冻结输入（m6 包 + 增量时的基底 Snapshot）
    input_entries = [
        {
            "schema_version": "1.0.0",
            "artifact_kind": "artifact",
            "artifact_id": package["reviewed_package_artifact_id"],
            "artifact_revision_id": package["reviewed_package_revision_id"],
            "artifact_type": "stage_package",
        }
        for package in packages
    ]
    if base is not None:
        input_entries.append(
            {
                "schema_version": "1.0.0",
                "artifact_kind": "artifact",
                "artifact_id": base["artifact_id"],
                "artifact_revision_id": base["revision_id"],
                "artifact_type": base["artifact_type"],
            }
        )

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
            "input_artifacts": list(input_entries),
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
            "upstream_artifacts": list(input_entries),
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
    # D-16 A 前半：非人工 task 各一个 Checkpoint（人工决定即时落盘属 D 波）
    service.write_checkpoint(
        step_run_id,
        edition_part_id=scope_key,
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
        edition_part_id=scope_key,
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
