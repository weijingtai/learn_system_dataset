"""M3 输入解析：从 Ledger 冻结修订中解析编译所需输入（规格 §7、§10.1、§11）。

本模块只调用 ``LedgerReadMixin`` 公开方法，不做任何写入。
"""

import json

import yaml

from pipeline.corpus_compiler.errors import CompileRefused


def resolve_m3_inputs(reader, edition_part_id):
    """从 Ledger 读接口解析 M3 编译所需的冻结输入。

    参数：
        reader：``LedgerReadMixin`` 实例（``LedgerService`` 或 ``LedgerReader``）。
        edition_part_id：版本部件标识。

    返回 dict，键：``processing_run_id``、``technique_id``、``m1_step_run_id``、
    ``m2_step_run_id``、``manifest_revision_id``、``ocr_page_set_revision_id``、
    ``page_revision_ids``（{页: 修订}）、``terminal_states``（{页: 终态}）、
    ``human_event_revision_ids``（[...]）。
    """
    # ---- M1 解析 ----
    m1_checkpoints = reader.list_checkpoints(edition_part_id, "m1")
    if not m1_checkpoints:
        raise CompileRefused("M1 未灌入：没有 m1 Checkpoint", code="REF_001")

    m1_step_run_id = None
    manifest_revision_id = None
    for cp in m1_checkpoints:
        for task in cp["content"].get("completed_tasks", []):
            if (
                task["task_id"] == "ingest_source"
                and task["status"] == "succeeded"
            ):
                m1_step_run_id = cp["content"]["step_run_id"]
                manifest_revision_id = task["artifact_revision_id"]
                break
        if m1_step_run_id is not None:
            break

    if m1_step_run_id is None or manifest_revision_id is None:
        raise CompileRefused(
            "M1 未完成：没有 task_id=ingest_source 且 status=succeeded 的记录",
            code="REF_001",
        )

    # manifest 修订必须 sealed
    manifest_rev = reader.get_revision(manifest_revision_id)
    if manifest_rev is None or manifest_rev["status"] != "sealed":
        raise CompileRefused(
            "manifest 修订未封存: %s" % manifest_revision_id, code="REF_001"
        )

    # ---- M2 解析 ----
    m2_checkpoints = reader.list_checkpoints(edition_part_id, "m2")
    if not m2_checkpoints:
        raise CompileRefused("M2 未灌入：没有 m2 Checkpoint", code="REF_001")

    m2_step_run_id = None
    for cp in m2_checkpoints:
        m2_step_run_id = cp["content"]["step_run_id"]
    if m2_step_run_id is None:
        raise CompileRefused("M2 Checkpoint 缺少 step_run_id", code="REF_001")

    m2_step_run = reader.get_step_run(m2_step_run_id)
    if m2_step_run is None or m2_step_run["status"] != "succeeded":
        raise CompileRefused(
            "M2 未通过：StepRun %s 状态 %s"
            % (m2_step_run_id, m2_step_run["status"] if m2_step_run else "不存在"),
            code="REF_001",
        )

    processing_run_id = m2_step_run["processing_run_id"]

    # 从 M2 Checkpoint 链中解析 page_revision_ids、terminal_states、human_event_revision_ids
    page_revision_ids = {}
    terminal_states = {}
    human_event_revision_ids = []

    for cp in m2_checkpoints:
        for task in cp["content"].get("completed_tasks", []):
            page = task["task_id"]
            if page.startswith("page_"):
                page_revision_ids[page] = task["artifact_revision_id"]
                ts = task.get("terminal_state")
                if ts is not None:
                    terminal_states[page] = ts
        # 最新 Checkpoint 的 human_decisions
        if cp == m2_checkpoints[-1]:
            human_event_revision_ids = list(
                cp["content"].get("human_decisions", [])
            )

    # ---- ocr_page_set_revision_id ----
    # 原实现遍历 M2 transformation 的输出再按 artifact_type 过滤；端口方法
    # ``list_step_run_revisions`` 直接回答同一问题（该 StepRun 产出的指定类型修订，按产生顺序）。
    ocr_page_set_revisions = reader.list_step_run_revisions(
        m2_step_run_id, artifact_type="ocr_page_set"
    )
    ocr_page_set_revision_id = (
        ocr_page_set_revisions[0]["artifact_revision_id"]
        if ocr_page_set_revisions
        else None
    )

    if ocr_page_set_revision_id is None:
        raise CompileRefused(
            "M2 未产出 ocr_page_set 修订", code="REF_001"
        )

    # ---- technique_id（从 manifest 内容中读取）----
    manifest_data = yaml.safe_load(
        reader.read_object(manifest_rev["sha256"]).decode("utf-8")
    )
    technique_id = manifest_data.get("technique_id", "")

    return {
        "processing_run_id": processing_run_id,
        "technique_id": technique_id,
        "m1_step_run_id": m1_step_run_id,
        "m2_step_run_id": m2_step_run_id,
        "manifest_revision_id": manifest_revision_id,
        "ocr_page_set_revision_id": ocr_page_set_revision_id,
        "page_revision_ids": page_revision_ids,
        "terminal_states": terminal_states,
        "human_event_revision_ids": human_event_revision_ids,
    }
