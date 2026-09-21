"""M8 输入解析 resolve_m8_inputs（规格 §16:661-668，裁决 D1/D13）。

沿 M3 StagePackage 的 ``manifest.input_artifacts`` 反查 M1 清单与 M2 页修订，
页图来自薄 M1 登记进 Ledger 的 ``source_asset_page`` 修订（裁定 §9.2-32：以接替后
的 m1 运行为准）。只调用 ``LedgerReadMixin`` 公开方法；查 artifact_type 与
stage_package 修订允许经 ``reader.store.conn`` 只读 SELECT（先例 impl-02
``act/03.yaml:17``）。本函数不做任何写入。
"""

import json

import yaml

from pipeline.dataset_compiler.errors import DatasetRefused
from pipeline.ledger.errors import NotConsumable

_SOURCE_ASSET_PREFIX = "source_asset_"


def _artifact_type(reader, artifact_revision_id):
    """经只读 SELECT 取修订的 artifact_type。"""
    row = reader.store.conn.execute(
        "SELECT a.artifact_type FROM artifacts a "
        "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
        "WHERE r.artifact_revision_id=?",
        (artifact_revision_id,),
    ).fetchone()
    return None if row is None else row[0]


def _sealed_revision(reader, artifact_revision_id, label):
    """取一个必须存在的 sealed 修订；缺失 ``REF_001``，未封存 ``NotConsumable``。"""
    revision = reader.get_revision(artifact_revision_id)
    if revision is None:
        raise DatasetRefused("%s 修订不存在: %s" % (label, artifact_revision_id), code="REF_001")
    if revision["status"] != "sealed":
        raise NotConsumable(
            "%s 修订未封存（%s）: %s" % (label, revision["status"], artifact_revision_id)
        )
    return revision


def _read_content(reader, revision):
    """读取修订内容对象：优先 JSON，回退 YAML（fixture_ingest 灌入的包为 YAML）。"""
    raw = reader.objects.get(revision["sha256"]).decode("utf-8")
    try:
        return json.loads(raw)
    except ValueError:
        return yaml.safe_load(raw)


def _resolve_m3(reader, edition_part_id):
    """R2/R3/R4：定位唯一 succeeded 的 m3 StepRun 与其 StagePackage。"""
    checkpoints = reader.list_checkpoints(edition_part_id, "m3")
    if not checkpoints:
        raise DatasetRefused("M3 未编译：没有 m3 Checkpoint", code="REF_001")
    step_run_ids = []
    for checkpoint in checkpoints:
        step_run_id = checkpoint["content"]["step_run_id"]
        if step_run_id not in step_run_ids:
            step_run_ids.append(step_run_id)
    succeeded = [
        step_run_id
        for step_run_id in step_run_ids
        if (reader.get_step_run(step_run_id) or {}).get("status") == "succeeded"
    ]
    if not succeeded:
        raise DatasetRefused("M3 未通过：没有 succeeded 的 m3 StepRun", code="REF_001")
    if len(succeeded) > 1:
        raise DatasetRefused("多个 M3 成功运行: %s" % ",".join(succeeded))
    m3_step_run_id = succeeded[0]

    rows = reader.store.conn.execute(
        "SELECT r.artifact_revision_id FROM artifact_revisions r "
        "JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "WHERE a.artifact_type='stage_package' AND r.step_run_id=? AND r.status='sealed'",
        (m3_step_run_id,),
    ).fetchall()
    if len(rows) != 1:
        raise DatasetRefused(
            "m3 StepRun 名下 sealed StagePackage 数量异常: %d" % len(rows), code="REF_001"
        )
    m3_package_revision_id = rows[0][0]
    revision = _sealed_revision(reader, m3_package_revision_id, "m3 stage_package")
    package = _read_content(reader, revision)
    if package.get("stage") != "m3" or (package.get("validation") or {}).get("passed") is not True:
        raise DatasetRefused("m3 包的 stage/validation 非法", code="SCH_002")
    payload = package.get("payload") or {}
    if "spans_revision_id" not in payload:
        raise DatasetRefused(
            "m3 包 payload 缺少 spans_revision_id（fixture_ingest 灌入的包属此类）",
            code="REF_001",
        )
    return m3_step_run_id, m3_package_revision_id, package


def _detect_route(package):
    """按 m3 包 ``manifest.input_artifacts`` 的构成判定证据路线（唯一权威）。

    有 ``ocr_page_set`` 且无 ``raw_text`` → ``"ocr"``；
    有 ``raw_text`` 且无 ``ocr_page_set`` → ``"electronic_text"``；
    其余（两者皆有 / 两者皆无）→ ``REF_001``，消息含实际类型的排序列表。
    """
    artifact_types = {
        reference["artifact_type"] for reference in package["manifest"]["input_artifacts"]
    }
    has_ocr_page_set = "ocr_page_set" in artifact_types
    has_raw_text = "raw_text" in artifact_types
    if has_ocr_page_set and not has_raw_text:
        return "ocr"
    if has_raw_text and not has_ocr_page_set:
        return "electronic_text"
    raise DatasetRefused(
        "M3 包 input_artifacts 无法判定路线: [%s]" % ", ".join(sorted(artifact_types)),
        code="REF_001",
    )


def _resolve_electronic_source_manifest(reader, package):
    """电子文本路线：从冻结的 ``raw_text`` 修订反查同属一个 M1 StepRun 的 ``source_manifest``。

    唯一权威路径：m3 包已冻结 ``raw_text``（上游事实），其 producer StepRun 即 M1，
    该 StepRun 名下恰有一个 sealed ``source_manifest``。不遍历全表取第一个。
    """
    raw_text_revision_ids = [
        reference["artifact_revision_id"]
        for reference in package["manifest"]["input_artifacts"]
        if reference["artifact_type"] == "raw_text"
    ]
    if len(raw_text_revision_ids) != 1:
        raise DatasetRefused(
            "电子文本路线 m3 包 raw_text 引用数 != 1: %d" % len(raw_text_revision_ids),
            code="REF_001",
        )
    raw_text_revision_id = raw_text_revision_ids[0]
    row = reader.store.conn.execute(
        "SELECT step_run_id FROM artifact_revisions WHERE artifact_revision_id=?",
        (raw_text_revision_id,),
    ).fetchone()
    if row is None or not row[0]:
        raise DatasetRefused(
            "raw_text 修订无 producer StepRun: %s" % raw_text_revision_id, code="REF_001"
        )
    rows = reader.store.conn.execute(
        "SELECT r.artifact_revision_id FROM artifact_revisions r "
        "JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "WHERE a.artifact_type='source_manifest' AND r.step_run_id=? AND r.status='sealed'",
        (row[0],),
    ).fetchall()
    if len(rows) != 1:
        raise DatasetRefused(
            "raw_text producer StepRun 名下 sealed source_manifest 数量异常: %d" % len(rows),
            code="REF_001",
        )
    return rows[0][0]


def _resolve_pages(reader, package):
    """R5：从 m3 包 manifest.input_artifacts 反查清单、页集与各页修订。"""
    manifest_revision_ids = []
    ocr_page_set_revision_ids = []
    ocr_page_revision_ids = []
    for reference in package["manifest"]["input_artifacts"]:
        artifact_type = reference["artifact_type"]
        revision_id = reference["artifact_revision_id"]
        if artifact_type == "source_manifest":
            manifest_revision_ids.append(revision_id)
        elif artifact_type == "ocr_page_set":
            ocr_page_set_revision_ids.append(revision_id)
        elif artifact_type == "ocr_page":
            ocr_page_revision_ids.append(revision_id)

    if len(manifest_revision_ids) != 1:
        raise DatasetRefused(
            "m3 包 source_manifest 引用数 != 1: %d" % len(manifest_revision_ids),
            code="REF_001",
        )
    if len(ocr_page_set_revision_ids) != 1:
        raise DatasetRefused(
            "m3 包 ocr_page_set 引用数 != 1: %d" % len(ocr_page_set_revision_ids),
            code="REF_001",
        )
    if not ocr_page_revision_ids:
        raise DatasetRefused("m3 包缺少 ocr_page 引用", code="REF_001")

    page_revision_ids = {}
    for revision_id in ocr_page_revision_ids:
        revision = _sealed_revision(reader, revision_id, "ocr_page")
        page = _read_content(reader, revision)["page"]
        if page in page_revision_ids:
            raise DatasetRefused("ocr_page 页重复: %s" % page, code="ID_002")
        page_revision_ids[page] = revision_id

    _sealed_revision(reader, ocr_page_set_revision_ids[0], "ocr_page_set")
    return (
        manifest_revision_ids[0],
        ocr_page_set_revision_ids[0],
        page_revision_ids,
    )


def _resolve_assets(reader, edition_part_id):
    """R6：从 m1 Checkpoint 的 ``source_asset_`` 任务收集页图修订。"""
    asset_revision_ids = {}
    asset_step_run_id = None
    for checkpoint in reader.list_checkpoints(edition_part_id, "m1"):
        step_run_id = checkpoint["content"]["step_run_id"]
        step_run = reader.get_step_run(step_run_id)
        if step_run is None or step_run["status"] != "succeeded":
            continue
        for task in checkpoint["content"].get("completed_tasks", []):
            if task["task_id"].startswith(_SOURCE_ASSET_PREFIX) and task["status"] == "succeeded":
                page = task["task_id"][len(_SOURCE_ASSET_PREFIX):]
                asset_revision_ids[page] = task["artifact_revision_id"]
                asset_step_run_id = step_run_id
    if not asset_revision_ids:
        raise DatasetRefused("SourceAsset 未登记", code="REF_001")
    for revision_id in asset_revision_ids.values():
        _sealed_revision(reader, revision_id, "source_asset_page")
        if _artifact_type(reader, revision_id) != "source_asset_page":
            raise DatasetRefused(
                "页图修订 artifact_type 非 source_asset_page: %s" % revision_id,
                code="SCH_002",
            )
    return asset_revision_ids, asset_step_run_id


def resolve_m8_inputs(reader, edition_part_id):
    """解析 M8 首切片所需的全部冻结输入（只读）。

    返回键逐字见 ACT impl-04/04 contract。
    """
    # R1：M8 已封存（D13：首切片不支持重跑）
    for checkpoint in reader.list_checkpoints(edition_part_id, "m8"):
        step_run = reader.get_step_run(checkpoint["content"]["step_run_id"])
        if step_run is not None and step_run["status"] == "succeeded":
            raise DatasetRefused(
                "M8 已封存：StepRun %s 已 succeeded" % checkpoint["content"]["step_run_id"]
            )

    m3_step_run_id, m3_package_revision_id, package = _resolve_m3(reader, edition_part_id)
    payload = package["payload"]
    spans_revision_id = payload["spans_revision_id"]

    # R4
    _sealed_revision(reader, spans_revision_id, "corpus_spans")
    if _artifact_type(reader, spans_revision_id) != "corpus_spans":
        raise DatasetRefused("spans 修订类型非 corpus_spans", code="SCH_002")
    m3_stage_package_id = package["stage_package_id"]
    m3_gate_profile = payload["gate_profile"]
    excluded_pages = payload["excluded_pages"]

    route = _detect_route(package)
    if route == "ocr":
        manifest_revision_id, ocr_page_set_revision_id, page_revision_ids = _resolve_pages(
            reader, package
        )
        asset_revision_ids, asset_step_run_id = _resolve_assets(reader, edition_part_id)
    else:
        # 电子文本路线：无 OCR 页、无 SourceAsset；source_manifest 由冻结的 raw_text 反查。
        manifest_revision_id = _resolve_electronic_source_manifest(reader, package)
        ocr_page_set_revision_id = None
        page_revision_ids = {}
        asset_revision_ids = {}
        asset_step_run_id = None

    # R7
    manifest_revision = _sealed_revision(reader, manifest_revision_id, "source_manifest")
    manifest = yaml.safe_load(reader.objects.get(manifest_revision["sha256"]).decode("utf-8"))

    return {
        "route": route,
        "m3_step_run_id": m3_step_run_id,
        "m3_package_revision_id": m3_package_revision_id,
        "m3_stage_package_id": m3_stage_package_id,
        "spans_revision_id": spans_revision_id,
        "manifest_revision_id": manifest_revision_id,
        "ocr_page_set_revision_id": ocr_page_set_revision_id,
        "page_revision_ids": page_revision_ids,
        "asset_revision_ids": asset_revision_ids,
        "asset_step_run_id": asset_step_run_id,
        "technique_id": manifest["technique_id"],
        "source_id": manifest["source_id"],
        "m3_gate_profile": m3_gate_profile,
        "excluded_pages": excluded_pages,
    }
