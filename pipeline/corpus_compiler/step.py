"""M3 在 Ledger 上真实编译：run_m3 事务序列（规格 §17、§17.1）。

本模块实现从冻结输入解析到 StagePackage 封存的完整写路径。
"""

import hashlib
import json
import re

import yaml

from pipeline.ledger import ids
from pipeline.ledger.errors import HashMismatch

from . import M3_TOOL, M3_TOOL_VERSION
from .compiler import compile_structural
from .errors import CompileRefused
from .gate import evaluate_structural
from .inputs import resolve_m3_inputs
from .serialize import dump_yaml


def _artifact_ref(rev, artifacts_map):
    """构造 artifact_ref dict。"""
    art_id, art_type = artifacts_map[rev]
    return {
        "schema_version": "1.0.0",
        "artifact_kind": "artifact",
        "artifact_id": art_id,
        "artifact_revision_id": rev,
        "artifact_type": art_type,
    }


def run_m3(service, edition_part_id, *, batch_size=10):
    """在真实 Ledger 上执行 M3 编译的完整事务序列。

    参数：
        service：``LedgerService`` 实例。
        edition_part_id：版本部件标识。
        batch_size：每批最大行数。

    返回 summary dict。

    异常分层（J3 返工 C5）：
        - ``resolve_m3_inputs`` 与本函数「M3 已封存」检查产生的异常原样抛出（不改类型）；
        - ``put_run_artifact``/``begin_step_run`` 本身抛出的异常原样抛出（此时尚无 StepRun）；
        - ``begin_step_run`` 成功之后的任何异常一律转为失败封存（检查名 ``internal``），
          返回 status ``failed`` 的 summary，不再向外抛出。
    """
    # ---- 1) 解析输入（异常原样抛出）----
    inputs = resolve_m3_inputs(service, edition_part_id)
    processing_run_id = inputs["processing_run_id"]

    # 检查 M3 是否已封存（异常原样抛出）
    m3_checkpoints = service.list_checkpoints(edition_part_id, "m3")
    for cp in m3_checkpoints:
        step_run = service.get_step_run(cp["content"]["step_run_id"])
        if step_run is not None and step_run["status"] == "succeeded":
            raise CompileRefused(
                "M3 已封存：StepRun %s 已 succeeded" % cp["content"]["step_run_id"]
            )

    return _run_m3_inner(service, edition_part_id, inputs, batch_size)


def _run_m3_inner(service, edition_part_id, inputs, batch_size):
    """begin_step_run 之前：解析/写入异常原样抛出；之后：任何异常转为失败封存。"""
    processing_run_id = inputs["processing_run_id"]
    technique_id = inputs["technique_id"]
    manifest_revision_id = inputs["manifest_revision_id"]
    ocr_page_set_revision_id = inputs["ocr_page_set_revision_id"]
    page_revision_ids = inputs["page_revision_ids"]
    terminal_states = inputs["terminal_states"]
    human_event_revision_ids = inputs["human_event_revision_ids"]

    # ---- 2) 配置修订（begin 之前，异常原样抛出）----
    config_data = json.dumps(
        {
            "stage": "m3",
            "tool": M3_TOOL,
            "tool_version": M3_TOOL_VERSION,
            "batch_size": batch_size,
            "gate_profile": "structural_only",
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    config_id, config_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        config_data,
        producer_module=M3_TOOL,
        producer_version=M3_TOOL_VERSION,
    )

    # ---- 3) 冻结输入（begin 之前，异常原样抛出）----
    # ocr_page_set + manifest + 各页修订 + 人工事件修订
    frozen = [ocr_page_set_revision_id, manifest_revision_id]
    pages_manifest = _read_manifest_content(service, manifest_revision_id)
    for page in pages_manifest["edition_part"]["pages"]:
        if page in page_revision_ids:
            frozen.append(page_revision_ids[page])
    frozen.extend(human_event_revision_ids)

    step_run_id = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": ids.new_id("step_run_id"),
            "input_artifact_ids": frozen,
            "technique_profile_id": technique_id,
            "configuration_artifact_id": config_revision_id,
        }
    )

    # ---- begin 之后：任何异常一律转为失败封存（检查名 "internal"）----
    try:
        return _run_m3_after_begin(
            service, edition_part_id, step_run_id, processing_run_id,
            manifest_revision_id, ocr_page_set_revision_id, page_revision_ids,
            terminal_states, human_event_revision_ids, frozen,
            config_revision_id, batch_size,
        )
    except Exception as exc:
        try:
            return _fail(
                service, step_run_id, "internal",
                "%s: %s" % (type(exc).__name__, exc),
            )
        except Exception as fail_exc:
            # _fail 自身失败：抛出原始异常，链上保留 _fail 的异常信息。
            raise exc from fail_exc


def _run_m3_after_begin(
    service, edition_part_id, step_run_id, processing_run_id,
    manifest_revision_id, ocr_page_set_revision_id, page_revision_ids,
    terminal_states, human_event_revision_ids, frozen,
    config_revision_id, batch_size,
):
    """begin_step_run 成功之后的完整流程（§17 步骤 4–14）。

    ``input_contract``/``compile``/``structural_gate`` 三个检查名下的失败在此就地
    封存并直接返回失败 summary（不向外抛出）；其余未预期异常向外传播，交由
    调用方 ``_run_m3_inner`` 统一转为 ``internal`` 失败封存。
    """
    # ---- 4) 输入契约校验 ----
    # C1：begin 之后、读取任何冻结输入内容之前，对每个冻结修订一次性读取对象
    #     字节并校验 sha256；之后所有内容解析只使用这份已校验字节，不得再次
    #     从 Object Store 读取未校验字节。
    # C2/C3/C4：ocr_page_set 页登记、终态、人工事件的语义校验。
    try:
        frozen_bytes = _read_and_verify_frozen(service, frozen)
        manifest = yaml.safe_load(frozen_bytes[manifest_revision_id].decode("utf-8"))
        ocr_page_set = json.loads(
            frozen_bytes[ocr_page_set_revision_id].decode("utf-8")
        )
        evidence_pages = _validate_input_contract(
            service, manifest, ocr_page_set, page_revision_ids, terminal_states,
            human_event_revision_ids, frozen_bytes,
        )
    except Exception as exc:
        return _fail(service, step_run_id, "input_contract", str(exc))

    # ---- 5) 编译（只使用 C1 已校验的冻结字节，不再读 Object Store）----
    page_docs = {}
    for page in manifest["edition_part"]["pages"]:
        if page in page_revision_ids:
            page_docs[page] = json.loads(
                frozen_bytes[page_revision_ids[page]].decode("utf-8")
            )

    try:
        result = compile_structural(
            manifest=manifest,
            page_docs=page_docs,
            terminal_states=terminal_states,
            batch_size=batch_size,
        )
    except Exception as exc:
        return _fail(service, step_run_id, "compile", str(exc))

    # ---- 6) 批次写入 ----
    checkpoint_revision_ids = []
    spans_by_batch = {}
    for span in result["spans"]:
        spans_by_batch.setdefault(span["batch_id"], []).append(span)

    for idx, batch_id in enumerate(result["batches"]):
        batch_spans = spans_by_batch[batch_id]
        batch_bytes = json.dumps(
            batch_spans, sort_keys=True, ensure_ascii=False
        ).encode("utf-8")
        _, batch_rev = service.put_artifact(
            step_run_id, "corpus_batch", batch_bytes,
            producer_module=M3_TOOL, producer_version=M3_TOOL_VERSION,
        )
        service.seal_revision(batch_rev)
        remaining = [{"task_id": b} for b in result["batches"][idx + 1:]]
        cp_rev = service.write_checkpoint(
            step_run_id,
            edition_part_id=edition_part_id,
            stage="m3",
            completed_tasks=[{
                "task_id": batch_id,
                "artifact_revision_id": batch_rev,
                "status": "succeeded",
                "terminal_state": None,
            }],
            human_decisions=[],
            pending_queue=remaining,
            next_pointer=remaining[0] if remaining else None,
        )
        checkpoint_revision_ids.append(cp_rev)

    # ---- 7) spans 修订 ----
    _, spans_revision_id = service.put_artifact(
        step_run_id, "corpus_spans", result["spans_bytes"],
        producer_module=M3_TOOL, producer_version=M3_TOOL_VERSION,
    )
    service.seal_revision(spans_revision_id)

    # ---- 8) Gate 判定 ----
    gate = evaluate_structural(
        manifest=manifest,
        page_docs=page_docs,
        terminal_states=terminal_states,
        evidence_pages=evidence_pages,
        spans_doc=result["spans_doc"],
        batch_size=batch_size,
    )

    # ---- 9) coverage_report / validation_report / step_log ----
    coverage_bytes = json.dumps(gate, sort_keys=True, ensure_ascii=False).encode("utf-8")
    _, coverage_rev = service.put_artifact(
        step_run_id, "coverage_report", coverage_bytes,
        producer_module=M3_TOOL, producer_version=M3_TOOL_VERSION,
    )
    service.seal_revision(coverage_rev)

    failed_checks = [
        name for name, check in gate["checks"].items() if not check["ok"]
    ]
    validation_data = {
        "gate_profile": "structural_only",
        "structural": gate["structural"],
        "semantic": "not_evaluated",
        "failed_checks": failed_checks,
    }
    _, validation_rev = service.put_artifact(
        step_run_id, "validation_report",
        json.dumps(validation_data, sort_keys=True, ensure_ascii=False).encode("utf-8"),
        producer_module=M3_TOOL, producer_version=M3_TOOL_VERSION,
    )
    service.seal_revision(validation_rev)

    log_lines = [
        "resolve_m3_inputs",
        "compile_structural spans=%d batches=%d" % (len(result["spans"]), len(result["batches"])),
        "evaluate_structural structural=%s" % gate["structural"],
    ]
    _, log_rev = service.put_artifact(
        step_run_id, "step_log", "\n".join(log_lines).encode("utf-8"),
        producer_module=M3_TOOL, producer_version=M3_TOOL_VERSION,
    )
    service.seal_revision(log_rev)

    # ---- 10) Gate 失败 → 失败封存 ----
    if gate["structural"] == "failed":
        return _fail(service, step_run_id, "structural_gate",
                     "Gate 判定 failed: %s" % "; ".join(failed_checks))

    # ---- 11) corpus_package ----
    corpus_data = json.dumps({
        "spans_revision_id": spans_revision_id,
        "coverage_report_revision_id": coverage_rev,
        "coverage": result["coverage"],
        "excluded_pages": result["excluded_pages"],
        "gate_profile": "structural_only",
        "semantic": "not_evaluated",
    }, sort_keys=True, ensure_ascii=False).encode("utf-8")
    _, corpus_rev = service.put_artifact(
        step_run_id, "corpus_package", corpus_data,
        producer_module=M3_TOOL, producer_version=M3_TOOL_VERSION,
    )
    service.seal_revision(corpus_rev)

    # ---- 12) Transformation ----
    transformation_id = service.record_transformation(
        step_run_id,
        operation="compile_corpus",
        tool=M3_TOOL,
        tool_version=M3_TOOL_VERSION,
        configuration_revision_id=config_revision_id,
        input_revision_ids=frozen,
        output_revision_ids=[corpus_rev, spans_revision_id, coverage_rev],
        validation_report_revision_id=validation_rev,
        human_event_revision_ids=human_event_revision_ids,
    )

    # ---- 13) StagePackage ----
    stage_package_id = ids.new_id("stage_package_id", stage="m3")
    package_revision_id = ids.new_id("artifact_revision_id")

    artifacts_map = _build_artifacts_map(
        service, step_run_id, frozen,
        [corpus_rev, spans_revision_id, coverage_rev, validation_rev, log_rev]
    )

    package = {
        "schema_version": "1.0.0",
        "stage_package_id": stage_package_id,
        "artifact_revision_id": package_revision_id,
        "stage": "m3",
        "status": "sealed",
        "payload": {
            "spans_revision_id": spans_revision_id,
            "coverage": result["coverage"],
            "excluded_pages": result["excluded_pages"],
            "gate_profile": "structural_only",
            "semantic": "not_evaluated",
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "input_artifacts": [_artifact_ref(rev, artifacts_map) for rev in frozen],
            "output_artifacts": [_artifact_ref(corpus_rev, artifacts_map)],
            "counts": {"spans": len(result["spans"]), "batches": len(result["batches"])},
            "content_sha256": result["spans_sha256"],
        },
        "validation": {
            "passed": True,
            "report_artifacts": [_artifact_ref(validation_rev, artifacts_map)],
        },
        "lineage": {
            "upstream_artifacts": [
                _artifact_ref(ocr_page_set_revision_id, artifacts_map),
                _artifact_ref(manifest_revision_id, artifacts_map),
            ],
            "transformations": [{
                "operation": "compile_corpus",
                "step_run_id": step_run_id,
                "configuration_artifact_revision_id": config_revision_id,
                "input_artifact_revision_ids": frozen,
                "output_artifact_revision_ids": [corpus_rev, spans_revision_id, coverage_rev],
            }],
        },
        "logs": [_artifact_ref(log_rev, artifacts_map)],
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
            "output_artifact_ids": [corpus_rev, spans_revision_id, coverage_rev, package_revision_id],
            "validation_report_ids": [validation_rev],
            "log_artifact_ids": [log_rev],
            "failure_artifact_ids": [],
        },
    )

    return {
        "status": "succeeded",
        "processing_run_id": processing_run_id,
        "step_run_id": step_run_id,
        "configuration_revision_id": config_revision_id,
        "frozen_input_revision_ids": frozen,
        "stage_package_id": stage_package_id,
        "package_revision_id": package_revision_id,
        "corpus_package_revision_id": corpus_rev,
        "spans_revision_id": spans_revision_id,
        "spans_sha256": result["spans_sha256"],
        "coverage_report_revision_id": coverage_rev,
        "validation_report_revision_id": validation_rev,
        "log_revision_id": log_rev,
        "step_manifest_revision_id": step_manifest_revision_id,
        "transformation_id": transformation_id,
        "checkpoint_revision_ids": checkpoint_revision_ids,
        "batches": result["batches"],
        "counts": {"spans": len(result["spans"]), "batches": len(result["batches"])},
        "coverage": result["coverage"],
        "excluded_pages": result["excluded_pages"],
        "gate": gate,
    }


def _fail(service, step_run_id, check, detail):
    """失败封存：put failure_report → seal → fail_step_run。"""
    failure_data = json.dumps(
        {"check": check, "detail": detail}, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    _, failure_rev = service.put_artifact(
        step_run_id, "failure_report", failure_data,
        producer_module=M3_TOOL, producer_version=M3_TOOL_VERSION,
    )
    service.seal_revision(failure_rev)
    service.fail_step_run(step_run_id, [failure_rev], "M3 %s: %s" % (check, detail))
    return {
        "status": "failed",
        "step_run_id": step_run_id,
        "failed_check": check,
        "failure_revision_id": failure_rev,
        "reason": detail,
    }


def _read_manifest_content(service, manifest_revision_id):
    """读取 manifest 修订的内容（YAML 格式）。

    仅用于 begin_step_run 之前构造冻结列表（此时尚未冻结，无法先行校验）；
    begin 之后一律改用 ``_read_and_verify_frozen`` 产出的已校验字节。
    """
    rev = service.get_revision(manifest_revision_id)
    return yaml.safe_load(service.objects.get(rev["sha256"]).decode("utf-8"))


def _read_and_verify_frozen(service, frozen):
    """一次性读取并校验每个冻结修订的对象字节（C1）。

    对 ``frozen`` 中每个修订：读取其登记 ``sha256`` 对应的对象字节，重算
    ``sha256`` 并与登记值比对；不一致说明 Object Store 中的物理内容已被
    篡改（内容与 Ledger 记录的 Revision 元数据不符），抛出 ``HashMismatch``
    （``SRC_003``）。返回 ``{artifact_revision_id: 已校验字节}``；调用方之后
    所有对冻结输入内容的解析必须复用这份字典，不得再次访问 Object Store。
    """
    frozen_bytes = {}
    for revision_id in frozen:
        rev = service.get_revision(revision_id)
        data = service.objects.get(rev["sha256"])
        actual_sha256 = hashlib.sha256(data).hexdigest()
        if actual_sha256 != rev["sha256"]:
            raise HashMismatch(
                "冻结修订 %s 对象内容哈希不一致（SRC_003）：登记 %s，实得 %s"
                % (revision_id, rev["sha256"], actual_sha256),
                code="SRC_003",
            )
        frozen_bytes[revision_id] = data
    return frozen_bytes


def _validate_input_contract(
    service, manifest, ocr_page_set, page_revision_ids, terminal_states,
    human_event_revision_ids, frozen_bytes,
):
    """输入契约校验（§17 步骤 4，C2/C3/C4）。

    只使用 C1 已校验的冻结字节（``frozen_bytes``）与 Ledger 元数据（修订的
    登记 ``sha256``），不得再次访问 Object Store。返回 ``evidence_pages``
    （人工事件顶层 ``page`` 字段集合），供 Gate 判定复用。
    """
    # C2：ocr_page_set["ocr_pages"] 必须是非空列表，每项含 page 与 sha256；
    # 页集合与 page_revision_ids 键集合严格相等；每页修订登记 sha256 == 该项
    # sha256（否则 HashMismatch SRC_003）。删除按 manifest.files 比对的逻辑
    # 与所有「缺失即跳过」分支。
    ocr_pages_raw = ocr_page_set.get("ocr_pages")
    if not isinstance(ocr_pages_raw, list) or not ocr_pages_raw:
        raise CompileRefused("ocr_page_set.ocr_pages 缺失或为空")

    entries = {}
    for item in ocr_pages_raw:
        if not isinstance(item, dict) or "page" not in item or "sha256" not in item:
            raise CompileRefused(
                "ocr_page_set.ocr_pages 条目缺少 page 或 sha256: %r" % (item,)
            )
        entries[item["page"]] = item["sha256"]

    prid_pages = set(page_revision_ids.keys())
    if set(entries.keys()) != prid_pages:
        raise CompileRefused(
            "ocr_page_set 页集合 %r != page_revision_ids 键集合 %r"
            % (set(entries.keys()), prid_pages)
        )

    for page, rev_id in page_revision_ids.items():
        rev = service.get_revision(rev_id)
        if rev["sha256"] != entries[page]:
            raise HashMismatch(
                "页 %s 修订登记哈希 %s != ocr_page_set 登记 %s（SRC_003）"
                % (page, rev["sha256"], entries[page]),
                code="SRC_003",
            )

    # C3：终态必须与 m2 Checkpoint 解析结果严格相等。
    ocr_terminal = ocr_page_set.get("terminal_states")
    if not isinstance(ocr_terminal, dict) or ocr_terminal != terminal_states:
        raise CompileRefused(
            "ocr_page_set.terminal_states %r != terminal_states %r"
            % (ocr_terminal, terminal_states)
        )

    # C4：每个人工事件内容必须是含顶层 "page" 的 dict；evidence_pages 取该字段。
    evidence_pages = set()
    for event_id in human_event_revision_ids:
        event_data = json.loads(frozen_bytes[event_id].decode("utf-8"))
        if not isinstance(event_data, dict) or "page" not in event_data:
            raise CompileRefused("人工事件 %s 缺少顶层 page 字段" % event_id)
        evidence_pages.add(event_data["page"])

    # manifest 页序中每个页名必须匹配 ^page_[0-9]{3,4}$
    for page in manifest["edition_part"]["pages"]:
        if not re.match(r"^page_[0-9]{3,4}$", page):
            raise CompileRefused(
                "页名 %s 格式非法（应匹配 ^page_[0-9]{3,4}$）" % page
            )

    return evidence_pages


def _build_artifacts_map(service, step_run_id, frozen_ids, own_ids):
    """构建 {revision_id: (artifact_id, artifact_type)} 映射。"""
    all_ids = set(frozen_ids) | set(own_ids)
    artifacts_map = {}
    for rev_id in all_ids:
        rev = service.get_revision(rev_id)
        if rev is None:
            continue
        row = service.store.conn.execute(
            "SELECT a.artifact_id, a.artifact_type FROM artifacts a "
            "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
            "WHERE r.artifact_revision_id=?",
            (rev_id,),
        ).fetchone()
        if row:
            artifacts_map[rev_id] = (row["artifact_id"], row["artifact_type"])
    return artifacts_map
