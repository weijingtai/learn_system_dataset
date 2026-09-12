"""M5 输入解析：从 Artifact Ledger 冻结修订中解析 M5 所需输入。

上游约束（impl-02 ACCEPTANCE §5.3、§9 第 23 条）：解析上游 StagePackage 时
只接受所属 StepRun 状态为 ``succeeded`` 的包；非 ``succeeded`` 一律拒绝并抛
``ValidationRefused``。本模块只调用 ``LedgerReadMixin`` 公开方法，不做任何
写入；三类元数据缺口经 ``reader.store.conn`` 只读 SELECT，集中在
``_m3_step_run`` / ``_artifact_types`` / ``_stage_package_for_stage``。
"""

import json

import yaml

from pipeline.ledger.errors import NotConsumable

from .errors import ValidationRefused

# M3 的三个内容输出类型（各恰 1 个）
_M3_CONTENT_TYPES = ("corpus_package", "corpus_spans", "coverage_report")

# M1/M2 经 M3 冻结的输入类型
_INPUT_TYPES = ("source_manifest", "ocr_page_set", "ocr_page", "human_event")


# ---------------------------------------------------------------- 只读 SELECT
def _m3_step_run(reader, step_run_id):
    """只读 SELECT：某 StepRun 在 ``frozen_inputs`` 中登记的冻结修订集合。"""
    rows = reader.store.conn.execute(
        "SELECT artifact_revision_id FROM frozen_inputs WHERE step_run_id=?",
        (step_run_id,),
    ).fetchall()
    return {row[0] for row in rows}


def _artifact_types(reader, revision_ids):
    """只读 SELECT：``artifacts.artifact_type``（经 ``artifact_revisions`` join）。"""
    revision_ids = [rev for rev in revision_ids if rev]
    if not revision_ids:
        return {}
    placeholders = ",".join("?" * len(revision_ids))
    rows = reader.store.conn.execute(
        "SELECT r.artifact_revision_id, a.artifact_type FROM artifact_revisions r "
        "JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "WHERE r.artifact_revision_id IN (%s)" % placeholders,
        tuple(revision_ids),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _stage_package_for_stage(reader, stage):
    """只读 SELECT：某 stage 的全部 StagePackage 及其归属 StepRun 状态。"""
    rows = reader.store.conn.execute(
        "SELECT sp.stage_package_id, sp.artifact_id, sp.stage, r.step_run_id, sr.status "
        "FROM stage_packages sp "
        "JOIN artifact_revisions r ON r.artifact_id = sp.artifact_id "
        "JOIN step_runs sr ON sr.step_run_id = r.step_run_id "
        "WHERE sp.stage=?",
        (stage,),
    ).fetchall()
    return [dict(row) for row in rows]


def _read_bytes(reader, sha256):
    reader_read = getattr(reader, "read_object", None)
    if reader_read is not None:
        return reader_read(sha256)
    return reader.objects.get(sha256)


def _parse(data):
    """把对象字节解析为 dict（先 JSON，后 YAML）；失败返回 ``None``。"""
    if data is None:
        return None
    text = data.decode("utf-8")
    try:
        return json.loads(text)
    except ValueError:
        try:
            return yaml.safe_load(text)
        except yaml.YAMLError:
            return None


def _read_doc(reader, revision_id):
    row = reader.get_revision(revision_id)
    if row is None:
        return None
    try:
        return _parse(_read_bytes(reader, row["sha256"]))
    except Exception:  # noqa: BLE001 —— 对象缺失时不抛，交由调用方判定
        return None


def resolve_m5_inputs(reader, edition_part_id):
    """从 Ledger 读取 M5 的 17 个冻结修订并返回角色映射（只读，不写入）。"""
    m3_checkpoints = reader.list_checkpoints(edition_part_id, "m3")
    if not m3_checkpoints:
        raise ValidationRefused("M3 未提交：没有 m3 Checkpoint")

    m3_step_run_id = m3_checkpoints[-1]["content"]["step_run_id"]
    m3_step = reader.get_step_run(m3_step_run_id)
    if m3_step is None or m3_step["status"] != "succeeded":
        raise ValidationRefused(
            "M3 未通过：StepRun %s 状态 %s"
            % (m3_step_run_id, m3_step["status"] if m3_step else "不存在")
        )

    for checkpoint in reader.list_checkpoints(edition_part_id, "m5"):
        step = reader.get_step_run(checkpoint["content"]["step_run_id"])
        if step is not None and step["status"] == "succeeded":
            raise ValidationRefused("M5 已封存：StepRun %s 已 succeeded" % step["step_run_id"])

    request = json.loads(m3_step["request_json"] or "{}")
    result = json.loads(m3_step["result_json"] or "{}")
    processing_run_id = m3_step["processing_run_id"]

    # ---- 配置：stage 必须 m3、gate_profile 必须 structural_only ----
    configuration_revision_id = request.get("configuration_artifact_id")
    config = _read_doc(reader, configuration_revision_id) if configuration_revision_id else None
    if (
        not isinstance(config, dict)
        or config.get("stage") != "m3"
        or config.get("gate_profile") != "structural_only"
    ):
        raise ValidationRefused(
            "input_contract：m3 配置 stage/gate_profile 不符: %r" % (config,)
        )

    # ---- M3 内容输出（各恰 1 个）----
    output_ids = list(result.get("output_artifact_ids") or [])
    output_types = _artifact_types(reader, output_ids)

    def pick(kind):
        revision_ids = [rev for rev in output_ids if output_types.get(rev) == kind]
        return revision_ids[0] if len(revision_ids) == 1 else None

    content_revision_ids = {kind: pick(kind) for kind in _M3_CONTENT_TYPES}
    if any(value is None for value in content_revision_ids.values()):
        raise ValidationRefused(
            "REF_001：m3 输出缺少唯一的 corpus_package/corpus_spans/coverage_report: %r"
            % (content_revision_ids,)
        )

    # ---- D-15：StagePackage 归属 succeeded StepRun ----
    candidates = _stage_package_for_stage(reader, "m3")
    succeeded = [item for item in candidates if item["status"] == "succeeded"]
    if candidates and not succeeded:
        raise ValidationRefused(
            "上游包归属失败 StepRun：%r" % ([item["stage_package_id"] for item in candidates],)
        )
    own = [item for item in succeeded if item["step_run_id"] == m3_step_run_id]
    chosen = (own or succeeded or [None])[0]

    package_revisions = [rev for rev in output_ids if output_types.get(rev) == "stage_package"]
    if package_revisions:
        m3_package_revision_id = package_revisions[0]
    elif chosen is not None:
        rows = reader.store.conn.execute(
            "SELECT artifact_revision_id FROM artifact_revisions WHERE artifact_id=?",
            (chosen["artifact_id"],),
        ).fetchall()
        m3_package_revision_id = rows[0][0] if rows else None
    else:
        m3_package_revision_id = None
    if m3_package_revision_id is None:
        raise ValidationRefused("上游包归属失败 StepRun：未找到 m3 StagePackage")
    m3_stage_package_id = chosen["stage_package_id"] if chosen else None

    # ---- M3 自检报告（恰 1 个，只冻结不解析）----
    validation_report_ids = list(result.get("validation_report_ids") or [])
    if len(validation_report_ids) != 1:
        raise ValidationRefused(
            "REF_001：validation_report_ids 不是恰 1 个: %r" % (validation_report_ids,)
        )

    # ---- 批次：m3 Checkpoint 链中 succeeded 的 corpus_batch 任务 ----
    batch_revision_ids = []
    for checkpoint in m3_checkpoints:
        for task in checkpoint["content"].get("completed_tasks", []):
            if task.get("status") != "succeeded":
                continue
            rev = task.get("artifact_revision_id")
            if rev and _artifact_types(reader, [rev]).get(rev) == "corpus_batch":
                batch_revision_ids.append(rev)

    # ---- M1/M2：沿 M3 request 的冻结输入顺序解析 ----
    input_ids = list(request.get("input_artifact_ids") or [])
    input_types = _artifact_types(reader, input_ids)
    frozen_rows = _m3_step_run(reader, m3_step_run_id)
    manifest_revision_id = None
    ocr_page_set_revision_id = None
    human_event_revision_ids = []
    page_revision_ids = {}
    for rev in input_ids:
        if frozen_rows and rev not in frozen_rows:
            continue
        kind = input_types.get(rev)
        if kind == "source_manifest":
            manifest_revision_id = manifest_revision_id or rev
        elif kind == "ocr_page_set":
            ocr_page_set_revision_id = ocr_page_set_revision_id or rev
        elif kind == "ocr_page":
            page = (_read_doc(reader, rev) or {}).get("page")
            if page:
                page_revision_ids[page] = rev
        elif kind == "human_event":
            human_event_revision_ids.append(rev)
    if manifest_revision_id is None or ocr_page_set_revision_id is None:
        raise ValidationRefused("REF_001：M3 未冻结 source_manifest / ocr_page_set")

    manifest = _read_doc(reader, manifest_revision_id) or {}
    pages = (manifest.get("edition_part") or {}).get("pages") or []
    if set(page_revision_ids) != set(pages):
        raise ValidationRefused(
            "REF_001：冻结页集合 %r 与 manifest 页序 %r 不符"
            % (sorted(page_revision_ids), sorted(pages))
        )
    page_revision_ids = {page: page_revision_ids[page] for page in pages}

    frozen_revision_ids = (
        [
            m3_package_revision_id,
            content_revision_ids["corpus_package"],
            content_revision_ids["corpus_spans"],
            content_revision_ids["coverage_report"],
            validation_report_ids[0],
            configuration_revision_id,
        ]
        + batch_revision_ids
        + [manifest_revision_id, ocr_page_set_revision_id]
        + [page_revision_ids[page] for page in pages]
        + human_event_revision_ids
    )

    for revision_id in frozen_revision_ids:
        row = reader.get_revision(revision_id)
        if row is None:
            raise ValidationRefused("REF_001：引用修订不存在: %s" % revision_id)
        if row["status"] != "sealed":
            raise NotConsumable(
                "引用修订未 sealed: %s（当前 %s）" % (revision_id, row["status"])
            )

    revision_roles = {
        "m3_package": m3_package_revision_id,
        "corpus_package": content_revision_ids["corpus_package"],
        "corpus_spans": content_revision_ids["corpus_spans"],
        "coverage_report": content_revision_ids["coverage_report"],
        "validation_report": validation_report_ids[0],
        "configuration": configuration_revision_id,
        "source_manifest": manifest_revision_id,
        "ocr_page_set": ocr_page_set_revision_id,
    }
    spans_doc = _read_doc(reader, content_revision_ids["corpus_spans"]) or {}
    batch_names = []
    for span in spans_doc.get("spans") or []:
        if span.get("batch_id") not in batch_names:
            batch_names.append(span.get("batch_id"))
    for name, rev in zip(batch_names, batch_revision_ids):
        revision_roles[name] = rev
    for page, rev in page_revision_ids.items():
        revision_roles[page] = rev
    for rev in human_event_revision_ids:
        revision_roles["human_event"] = rev

    return {
        "processing_run_id": processing_run_id,
        "technique_id": manifest.get("technique_id"),
        "m3_step_run_id": m3_step_run_id,
        "m3_stage_package_id": m3_stage_package_id,
        "m3_package_revision_id": m3_package_revision_id,
        "configuration_revision_id": configuration_revision_id,
        "corpus_package_revision_id": content_revision_ids["corpus_package"],
        "corpus_spans_revision_id": content_revision_ids["corpus_spans"],
        "coverage_report_revision_id": content_revision_ids["coverage_report"],
        "validation_report_revision_id": validation_report_ids[0],
        "batch_revision_ids": batch_revision_ids,
        "manifest_revision_id": manifest_revision_id,
        "ocr_page_set_revision_id": ocr_page_set_revision_id,
        "page_revision_ids": page_revision_ids,
        "human_event_revision_ids": human_event_revision_ids,
        "frozen_revision_ids": frozen_revision_ids,
        "revision_roles": revision_roles,
    }
