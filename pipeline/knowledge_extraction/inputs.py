"""M4 输入解析：从 Artifact Ledger 冻结修订只读解析 M3 输出与 M4 输入。

只经 LedgerPort 只读方法读账本（TODO T03c），不做任何写入。
上游只认「``succeeded`` 且 Transformation ``operation == compile_corpus``」的 m3 运行
（P5），输出定位经 ``result_json["output_artifact_ids"]`` + ``artifacts.artifact_type``，
**不依赖** ``list_transformations`` 返回输出（它只返回 ``transformations`` 表行）。
"""

import json
import re

import yaml

from pipeline.ledger.errors import NotConsumable

from . import CATEGORIES
from .errors import ExtractionRefused

_M3_CONTENT_TYPES = ("corpus_package", "corpus_spans", "coverage_report")
_SUBMIT_TASK_RE = re.compile(r"^submit_(%s)_([abc])$" % "|".join(CATEGORIES))


# ---------------------------------------------------------------- 只读工具
def _read_bytes(reader, sha256):
    return reader.read_object(sha256)


def _read_doc(reader, revision_id):
    """读一个修订的对象内容并解析为 dict（先 JSON 后 YAML）；不存在返回 ``None``。"""
    row = reader.get_revision(revision_id)
    if row is None:
        return None
    text = _read_bytes(reader, row["sha256"]).decode("utf-8")
    try:
        return json.loads(text)
    except ValueError:
        return yaml.safe_load(text)


def _artifact_types(reader, revision_ids):
    """经 LedgerPort ``describe_revision`` 取 ``artifact_type``；不存在的修订不出现在结果里。"""
    types = {}
    for revision_id in revision_ids:
        info = reader.describe_revision(revision_id) if revision_id else None
        if info is not None:
            types[revision_id] = info["artifact_type"]
    return types


def latest_succeeded_step_run(reader, edition_part_id, stage):
    """该 EditionPart×Stage 上最近一个 ``succeeded`` 的 StepRun（只读，不写死号）。

    后续 StepRun 以 ``supersede_step_run`` 接替它（G7-RULINGS 第 32/58 条）。
    """
    return reader.latest_checkpoint_step_run(edition_part_id, stage, "succeeded")


def _processing_run_technique_id(reader, processing_run_id):
    run = reader.get_processing_run(processing_run_id)
    if run is None:
        raise ExtractionRefused(
            "ProcessingRun 不存在: %s" % processing_run_id, code="REF_001"
        )
    return run["technique_id"]


def _m3_candidates(reader, edition_part_id):
    """m3 链上 succeeded 且含 ``compile_corpus`` 的 StepRun（去重保序）。"""
    candidates = []
    for checkpoint in reader.list_checkpoints(edition_part_id, "m3"):
        step_run_id = checkpoint["content"]["step_run_id"]
        if step_run_id in candidates:
            continue
        step = reader.get_step_run(step_run_id)
        if step is None or step["status"] != "succeeded":
            continue
        operations = [
            row.get("operation") for row in reader.list_transformations(step_run_id)
        ]
        if "compile_corpus" not in operations:
            continue
        candidates.append(step_run_id)
    return candidates


def _m3_stage_package(reader, stage="m3"):
    return [
        {
            "stage_package_id": row["stage_package_id"],
            "artifact_revision_id": row["artifact_revision_id"],
            "step_run_id": row["step_run_id"],
        }
        for row in reader.list_stage_packages(stage)
    ]


def resolve_m3_outputs(reader, edition_part_id):
    """解析唯一 succeeded 的 m3 运行及其输出修订（只读，不写入）。"""
    candidates = _m3_candidates(reader, edition_part_id)
    if not candidates:
        raise ExtractionRefused(
            "M3 未通过：没有 succeeded 的 compile_corpus 运行", code="REF_001"
        )
    if len(candidates) > 1:
        raise ExtractionRefused("多个 M3 结果: %r" % candidates)
    m3_step_run_id = candidates[0]
    step = reader.get_step_run(m3_step_run_id)
    result = json.loads(step["result_json"] or "{}")
    processing_run_id = step["processing_run_id"]
    output_ids = list(result.get("output_artifact_ids") or [])
    types = _artifact_types(reader, output_ids)

    def pick(kind):
        revisions = [rev for rev in output_ids if types.get(rev) == kind]
        return revisions[0] if len(revisions) == 1 else None

    content_revision_ids = {kind: pick(kind) for kind in _M3_CONTENT_TYPES}
    if any(value is None for value in content_revision_ids.values()):
        raise ExtractionRefused(
            "M3 未通过：输出形状不符（corpus_package/corpus_spans/coverage_report 非各 1 个）: %r"
            % (content_revision_ids,),
            code="REF_001",
        )

    technique_id = _processing_run_technique_id(reader, processing_run_id)

    packages = _m3_stage_package(reader, "m3")
    if len(packages) != 1:
        raise ExtractionRefused(
            "M3 未通过：stage_packages 中 m3 记录 %d 条" % len(packages), code="REF_001"
        )
    package = packages[0]
    content = _read_doc(reader, package["artifact_revision_id"]) or {}
    payload = content.get("payload") or {}
    if (
        payload.get("spans_revision_id") != content_revision_ids["corpus_spans"]
        or payload.get("gate_profile") != "structural_only"
    ):
        raise ExtractionRefused(
            "M3 未通过：m3 包 payload.spans_revision_id/gate_profile 与输出不符", code="REF_001"
        )

    for revision_id in (
        content_revision_ids["corpus_package"],
        content_revision_ids["corpus_spans"],
        content_revision_ids["coverage_report"],
        package["artifact_revision_id"],
    ):
        row = reader.get_revision(revision_id)
        if row is None:
            raise ExtractionRefused("引用修订不存在: %s" % revision_id, code="REF_001")
        if row["status"] != "sealed":
            raise NotConsumable(
                "引用修订未 sealed: %s（当前 %s）" % (revision_id, row["status"])
            )

    return {
        "processing_run_id": processing_run_id,
        "technique_id": technique_id,
        "m3_step_run_id": m3_step_run_id,
        "corpus_stage_package_id": package["stage_package_id"],
        "corpus_stage_package_revision_id": package["artifact_revision_id"],
        "corpus_package_revision_id": content_revision_ids["corpus_package"],
        "spans_revision_id": content_revision_ids["corpus_spans"],
    }


def m4_is_sealed(reader, edition_part_id):
    """该 EditionPart 的 m4 链上是否已有 succeeded 的 assemble 运行。"""
    for checkpoint in reader.list_checkpoints(edition_part_id, "m4"):
        step = reader.get_step_run(checkpoint["content"]["step_run_id"])
        if step is None or step["status"] != "succeeded":
            continue
        request = json.loads(step["request_json"] or "{}")
        config = _read_doc(reader, request.get("configuration_artifact_id"))
        if isinstance(config, dict) and config.get("task") == "assemble":
            return True
    return False


def collect_submissions(reader, edition_part_id):
    """收集 m4 已登记的提交件：``{"<category>/<lane>": {...}}``；同类同路多于一件 → ID_002。"""
    submissions = {}
    for checkpoint in reader.list_checkpoints(edition_part_id, "m4"):
        content = checkpoint["content"]
        step_run_id = content["step_run_id"]
        step = reader.get_step_run(step_run_id)
        if step is None or step["status"] != "succeeded":
            continue
        for task in content.get("completed_tasks") or []:
            if task.get("status") != "succeeded":
                continue
            match = _SUBMIT_TASK_RE.match(task.get("task_id") or "")
            if match is None:
                continue
            revision_id = task.get("artifact_revision_id")
            if _artifact_types(reader, [revision_id]).get(revision_id) != "candidate_submission":
                continue
            key = "%s/%s" % (match.group(1), match.group(2))
            if key in submissions:
                raise ExtractionRefused("同类同路提交件多于一件: %s" % key, code="ID_002")
            doc = _read_doc(reader, revision_id) or {}
            submissions[key] = {
                "revision_id": revision_id,
                "step_run_id": step_run_id,
                "channel": doc.get("channel"),
            }
    return submissions


def _profile_revisions(reader, processing_run_id, technique_id):
    # 端口按写入顺序返回；稳定排序后即原 SQL 的 ORDER BY created_at, rowid
    rows = sorted(
        reader.list_revisions(artifact_type="technique_profile", processing_run_id=processing_run_id),
        key=lambda row: row["created_at"],
    )
    matches = []
    for row in rows:
        content = _read_doc(reader, row["artifact_revision_id"]) or {}
        if content.get("technique_id") == technique_id:
            matches.append(row["artifact_revision_id"])
    return matches


def resolve_m4_inputs(reader, edition_part_id, *, technique_profile_revision_id=None):
    """解析 M4 输入：m3 输出 + ``technique_profile`` + 全部已登记提交件（只读）。"""
    if m4_is_sealed(reader, edition_part_id):
        raise ExtractionRefused("M4 已封存：存在 succeeded 的 assemble 运行")
    base = resolve_m3_outputs(reader, edition_part_id)
    processing_run_id = base["processing_run_id"]
    technique_id = base["technique_id"]

    if technique_profile_revision_id is not None:
        row = reader.get_revision(technique_profile_revision_id)
        if row is None:
            raise ExtractionRefused(
                "technique_profile 修订不存在: %s" % technique_profile_revision_id,
                code="REF_001",
            )
        if (
            _artifact_types(reader, [technique_profile_revision_id]).get(
                technique_profile_revision_id
            )
            != "technique_profile"
        ):
            raise ExtractionRefused("指定修订不是 technique_profile", code="SCH_002")
        if row["status"] != "sealed":
            raise NotConsumable(
                "technique_profile 未 sealed: %s" % technique_profile_revision_id
            )
        content = _read_doc(reader, technique_profile_revision_id) or {}
        if content.get("technique_id") != technique_id:
            raise ExtractionRefused(
                "technique_profile.technique_id 与上游不符", code="REF_001"
            )
    else:
        matches = _profile_revisions(reader, processing_run_id, technique_id)
        if not matches:
            raise ExtractionRefused("缺少 technique_profile", code="REF_001")
        if len(matches) > 1:
            raise ExtractionRefused("存在多个 technique_profile，需显式指定")
        technique_profile_revision_id = matches[0]

    result = dict(base)
    result["technique_profile_revision_id"] = technique_profile_revision_id
    result["submissions"] = collect_submissions(reader, edition_part_id)
    return result
