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

#: 电子文本路线的 M2 四类产物：返回键名 → m3 包 input_artifacts 的 artifact_type。
M2_INPUT_ARTIFACT_TYPES = (
    ("raw_text_revision_id", "raw_text"),
    ("cleaned_text_revision_id", "cleaned_text_revision"),
    ("deterministic_patch_set_revision_id", "deterministic_patch_set"),
    ("sanitization_report_revision_id", "sanitization_report"),
)


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


def _single_input_reference(package, artifact_type):
    """从 m3 包取恰好 1 个该类型的修订引用；数量 != 1 → ``REF_001``（消息含实际数）。"""
    revision_ids = [
        reference["artifact_revision_id"]
        for reference in package["manifest"]["input_artifacts"]
        if reference["artifact_type"] == artifact_type
    ]
    if len(revision_ids) != 1:
        raise DatasetRefused(
            "m3 包 %s 引用数 != 1: %d" % (artifact_type, len(revision_ids)), code="REF_001"
        )
    return revision_ids[0]


def _resolve_electronic_m2_revisions(reader, package):
    """电子文本路线：解析 M2 四类产物修订（各必恰 1 个，均须 sealed 且类型相符）。"""
    resolved = {}
    for key, artifact_type in M2_INPUT_ARTIFACT_TYPES:
        revision_id = _single_input_reference(package, artifact_type)
        _sealed_revision(reader, revision_id, artifact_type)
        if _artifact_type(reader, revision_id) != artifact_type:
            raise DatasetRefused(
                "%s 修订 artifact_type 非 %s: %s" % (key, artifact_type, revision_id),
                code="SCH_002",
            )
        resolved[key] = revision_id
    return resolved


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


def _check_input_references(route, inputs, m3_package):
    """§17 步骤 6 的引用一致性校验（按路线分派）；不一致一律 ``REF_001``。

    ``ocr`` 路线：source_manifest / ocr_page_set / ocr_page 三组与解析逐字一致（逐字不变）。
    ``electronic_text`` 路线：M2 四类产物各恰 1 个且与解析一致；出现
    ``ocr_page_set`` / ``ocr_page`` 引用即 ``REF_001``（说明路线判定与实际不符）。
    """
    if route == "ocr":
        manifest_refs = []
        page_set_refs = []
        page_refs = []
        for reference in m3_package["manifest"]["input_artifacts"]:
            if reference["artifact_type"] == "source_manifest":
                manifest_refs.append(reference["artifact_revision_id"])
            elif reference["artifact_type"] == "ocr_page_set":
                page_set_refs.append(reference["artifact_revision_id"])
            elif reference["artifact_type"] == "ocr_page":
                page_refs.append(reference["artifact_revision_id"])
        if manifest_refs != [inputs["manifest_revision_id"]]:
            raise DatasetRefused("m3 包 source_manifest 引用与解析不一致", code="REF_001")
        if page_set_refs != [inputs["ocr_page_set_revision_id"]]:
            raise DatasetRefused("m3 包 ocr_page_set 引用与解析不一致", code="REF_001")
        if set(page_refs) != set(inputs["page_revision_ids"].values()):
            raise DatasetRefused("m3 包 ocr_page 引用与解析不一致", code="REF_001")
        return

    for key, artifact_type in M2_INPUT_ARTIFACT_TYPES:
        if _single_input_reference(m3_package, artifact_type) != inputs[key]:
            raise DatasetRefused(
                "m3 包 %s 引用与解析不一致" % artifact_type, code="REF_001"
            )
    forbidden = sorted(
        {
            reference["artifact_type"]
            for reference in m3_package["manifest"]["input_artifacts"]
            if reference["artifact_type"] in ("ocr_page_set", "ocr_page")
        }
    )
    if forbidden:
        raise DatasetRefused(
            "电子文本路线 m3 包不得含 %s 引用" % ", ".join(forbidden), code="REF_001"
        )


def _m7_step_run_id(reader, edition_part_id):
    """取最新 succeeded 的 m7 StepRun；无 M7 → ``None``。

    多个 succeeded → 取链序最新一个；若最新两个时间戳相同（无法确定唯一最新）
    → ``REF_001``（不随便取第一个）。
    """
    succeeded = []
    for checkpoint in reader.list_checkpoints(edition_part_id, "m7"):
        step_run_id = (checkpoint.get("content") or {}).get("step_run_id")
        if not step_run_id or step_run_id in succeeded:
            continue
        step_run = reader.get_step_run(step_run_id)
        if step_run is not None and step_run["status"] == "succeeded":
            succeeded.append(step_run_id)
    if not succeeded:
        return None
    if len(succeeded) > 1:
        newest = reader.get_step_run(succeeded[-1]) or {}
        previous = reader.get_step_run(succeeded[-2]) or {}
        if newest.get("created_at") == previous.get("created_at"):
            raise DatasetRefused(
                "多个 succeeded 的 m7 且最新时间戳相同，无法确定唯一最新: %s"
                % ",".join(succeeded),
                code="REF_001",
            )
    return succeeded[-1]


def _resolve_m7(reader, edition_part_id):
    """解析 M7 Snapshot：返回 ``(snapshot_revision_id, snapshot_knowledge)``。

    无 M7 → ``(None, None)``（不报错）。有 M7：取 succeeded StepRun 的 sealed
    StagePackage，经其 ``manifest.output_artifacts`` 声明的 ``canonical_snapshot``
    （或经 ``assembly_package.canonical_snapshot_revision_id``）定位 Snapshot 修订；
    用 ``_sealed_revision`` 校验已封存、用 ``_artifact_type`` 校验类型（不符 → ``SCH_002``）。
    ``snapshot_knowledge`` 即该修订内容（CanonicalSnapshot 的 knowledge 段本身，扁平字典）。
    """
    step_run_id = _m7_step_run_id(reader, edition_part_id)
    if step_run_id is None:
        return None, None
    rows = reader.store.conn.execute(
        "SELECT r.artifact_revision_id FROM artifact_revisions r "
        "JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "WHERE a.artifact_type='stage_package' AND r.step_run_id=? AND r.status='sealed'",
        (step_run_id,),
    ).fetchall()
    if len(rows) != 1:
        raise DatasetRefused(
            "m7 StepRun 名下 sealed StagePackage 数量异常: %d" % len(rows), code="REF_001"
        )
    package = _read_content(reader, _sealed_revision(reader, rows[0][0], "m7 stage_package"))
    output_artifacts = (package.get("manifest") or {}).get("output_artifacts") or []
    snapshot_revision_id = None
    for reference in output_artifacts:
        if reference.get("artifact_type") == "canonical_snapshot":
            snapshot_revision_id = reference.get("artifact_revision_id")
            break
    if snapshot_revision_id is None:
        for reference in output_artifacts:
            if reference.get("artifact_type") == "assembly_package":
                assembly_package = _read_content(
                    reader,
                    _sealed_revision(
                        reader, reference["artifact_revision_id"], "assembly_package"
                    ),
                )
                snapshot_revision_id = assembly_package.get(
                    "canonical_snapshot_revision_id"
                )
                break
    if not snapshot_revision_id:
        raise DatasetRefused("m7 包未声明 canonical_snapshot 修订", code="REF_001")
    snapshot_revision = _sealed_revision(reader, snapshot_revision_id, "canonical_snapshot")
    if _artifact_type(reader, snapshot_revision_id) != "canonical_snapshot":
        raise DatasetRefused(
            "Snapshot 修订 artifact_type 非 canonical_snapshot: %s" % snapshot_revision_id,
            code="SCH_002",
        )
    return snapshot_revision_id, _read_content(reader, snapshot_revision)


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
        m2_revisions = {key: None for key, _ in M2_INPUT_ARTIFACT_TYPES}
    else:
        # 电子文本路线：无 OCR 页、无 SourceAsset；source_manifest 由冻结的 raw_text 反查。
        manifest_revision_id = _resolve_electronic_source_manifest(reader, package)
        ocr_page_set_revision_id = None
        page_revision_ids = {}
        asset_revision_ids = {}
        asset_step_run_id = None
        m2_revisions = _resolve_electronic_m2_revisions(reader, package)

    # R8：M7 Snapshot（无 M7 → (None, None)，不报错）
    m7_snapshot_revision_id, snapshot_knowledge = _resolve_m7(reader, edition_part_id)

    # R7
    manifest_revision = _sealed_revision(reader, manifest_revision_id, "source_manifest")
    manifest = yaml.safe_load(reader.objects.get(manifest_revision["sha256"]).decode("utf-8"))

    resolved = {
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
        "m7_snapshot_revision_id": m7_snapshot_revision_id,
        "snapshot_knowledge": snapshot_knowledge,
    }
    # OCR 路线四键取 None 但键必须存在（下游按名取用，不许省略）
    resolved.update(m2_revisions)
    return resolved
