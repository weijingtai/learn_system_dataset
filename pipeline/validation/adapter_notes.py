"""M5 Gate 的门禁级检查：扫描 M4 提交件 ``adapter_notes`` 的截断自述（W8 ACT 19 Q3）。

``adapter_notes`` 由 M4 Adapter 写入（``pipeline.knowledge_extraction.submission``），
抽取员在里面写「我略去了什么」。此前**没有任何下游消费者**——抽取员说「为控总数略去」
「受 20 条上限所限未逐一登记」，而 M4 照常封存、M5 照常通过，截断就这样静默消失了
（真书实测：5 个 concept_mention 词条因此永久缺失，见 ACT 19 Q2）。本模块给 M5 Gate
接上第一条消费者。

设计口径（为什么是「门禁级检查」而不是第 15 个 Validator）
----------------------------------------------------------
1. ``registry.VALIDATORS`` 是 **恰 14 项、顺序固定、禁止增删**的注册表（impl-03
   ``act/00.yaml`` contract），且被 ``tests/test_registry.py`` 与 ``tests/test_step.py``
   各硬断言一次；加第 15 项会让既有 M5 用例转红。本检查因此挂在 14 项套件**之外**，
   由 ``step.run_m5`` 在套件跑完后执行：``validators`` / Checkpoint / 冻结输入数与
   验收行数一概不变。
2. 本检查**只在账本里确有 M4 提交件时**产出发现：夹具与 OCR 档没有提交件，
   于是产出恒为空、检查前后 M5 行为逐字节一致。
3. 门禁取 ``G3``：``package._NOT_EVALUATED`` 里那条 M4 依赖项 ``candidate_evidence``
   本就归 G3（理由「M4 Knowledge Extraction」），候选证据的**完整性**属同一门禁。
4. 命中即产出 ``severity[级别] == "error"``、``rework_stage`` 非空的发现——
   于是它进入 ``gate_results.rework_tasks``、``pending_rework_count`` 非零、
   ``gate.passed`` 转假，且 M5 StagePackage 的 ``validation.passed`` 随之为假：
   **不得静默通过**，也不冒充 ``ok`` / ``not_evaluated``。
5. 返工阶段取 ``m3``：``findings._REWORK_STAGES`` 是 ``("m2", "m3", None)`` 闭集
   （D-11：无新前缀，只区分 m2/m3），M4 来源的返工项只能落在 m3。
6. 词表**集中定义**在本模块的 ``TRUNCATION_MARKERS``，可整体覆盖（调用方参数或
   ``M5_ADAPTER_NOTES_MARKERS`` 环境变量），不在别处硬编码。

本模块**只读**：账本只经 LedgerPort 的只读方法（``get_revision`` / ``describe_revision`` / ``read_object``）取用，
不写账本、不写提交件、不签发任何东西（人工裁决与 Concept 引用仍只由用户做，P7）。
"""

import json
import os

from . import CONSUMPTION_LEVELS
from .findings import make_finding

# 检查名（已登记进 ``registry.CHECK_CODES``，取 ``None``：§5.5 缺口同类的「如实披露项」，
# §8.2 九码里没有语义吻合的码，不得伪挂一个）
CHECK_NAME = "adapter_notes_truncation"
# 门禁代号（G1–G7 闭集；见模块 docstring 第 3 条）
GATE = "G3"
# 产出者标识：门禁级检查，不在 14 项 Validator 注册表内
PRODUCER_ID = "m5_adapter_notes"
# 返工阶段（D-11 闭集 m2/m3，见 docstring 第 5 条）
REWORK_STAGE = "m3"

# 截断自述词表（集中定义；ACT 19 Q3 给定的四个词）
TRUNCATION_MARKERS = ("控总数", "上限", "略去", "未逐一登记")

# 机械转换注记不是抽取员自述，其中的词不作数
_TRANSFORM_MARKER = "机械转换"

# 词表覆盖用的环境变量名
MARKERS_ENV = "M5_ADAPTER_NOTES_MARKERS"

# M4 提交件的冻结输入类型
SUBMISSION_TYPE = "candidate_submission"


def markers_from_env(env=None):
    """从环境变量读词表覆盖；未设置或全为空白时返回默认词表。"""
    source = os.environ if env is None else env
    raw = source.get(MARKERS_ENV)
    if raw is None:
        return tuple(TRUNCATION_MARKERS)
    markers = tuple(part.strip() for part in raw.split(",") if part.strip())
    return markers or tuple(TRUNCATION_MARKERS)


def scan_documents(documents, *, markers=None):
    """扫描 ``[(revision_id, submission_doc), ...]``，返回命中清单（确定性顺序）。

    命中项形如::

        {"artifact_revision_id": ..., "lane": ..., "category": ...,
         "note_index": ..., "note": ..., "markers": [命中的词表项, ...]}

    条目按 ``(revision_id, note_index)`` 升序；机械转换注记整条跳过。
    """
    active = tuple(markers if markers is not None else TRUNCATION_MARKERS)
    hits = []
    for revision_id, doc in sorted(documents, key=lambda item: item[0]):
        if not isinstance(doc, dict):
            continue
        notes = doc.get("adapter_notes") or []
        if not isinstance(notes, list):
            continue
        for index, note in enumerate(notes):
            if not isinstance(note, str) or _TRANSFORM_MARKER in note:
                continue
            matched = sorted({marker for marker in active if marker in note})
            if not matched:
                continue
            hits.append(
                {
                    "artifact_revision_id": revision_id,
                    "lane": doc.get("lane"),
                    "category": doc.get("category"),
                    "note_index": index,
                    "note": note,
                    "markers": matched,
                }
            )
    return hits


def findings_from_hits(hits):
    """把命中清单转成 M5 发现（每命中一条一个 error 发现）。"""
    findings = []
    for hit in hits:
        revision_id = hit["artifact_revision_id"]
        detail = (
            "adapter_notes 截断自述（命中 %s）：%s"
            % ("/".join(hit["markers"]), hit["note"][:120])
        )
        findings.append(
            make_finding(
                PRODUCER_ID,
                GATE,
                CHECK_NAME,
                None,
                {level: "error" for level in CONSUMPTION_LEVELS},
                {"entity_id": revision_id, "artifact_revision_id": revision_id},
                relation=None,
                rework_stage=REWORK_STAGE,
                detail=detail,
            )
        )
    return findings


def _artifact_types(reader, revision_ids):
    """经 LedgerPort ``describe_revision`` 取 ``artifact_type``；不存在的修订不出现在结果里。"""
    types = {}
    for revision_id in revision_ids:
        info = reader.describe_revision(revision_id) if revision_id else None
        if info is not None:
            types[revision_id] = info["artifact_type"]
    return types


def _read_bytes(reader, sha256):
    # LedgerService 与 LedgerReader 都经 LedgerReadMixin 提供 read_object（TODO.md T03），不再直读对象存储
    return reader.read_object(sha256)


def _read_doc(reader, revision_id):
    """读某个修订的内容并解析为 dict（先 JSON 后 YAML）；失败返回 ``None``。"""
    import yaml

    row = reader.get_revision(revision_id)
    if row is None:
        return None
    try:
        data = _read_bytes(reader, row["sha256"])
    except Exception:  # noqa: BLE001 —— 对象缺失不抛，交由调用方如实跳过
        return None
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


def submission_documents(reader, edition_part_id):
    """只读定位该 edition_part 的 M4 提交件，返回 ``[(revision_id, doc), ...]``。

    来源：``stage == "m4"`` 的 Checkpoint 链里**状态为 succeeded** 的 StepRun，
    取其 ``request_json.input_artifact_ids`` 中 ``artifact_type ==
    "candidate_submission"`` 的冻结输入（M4 把六份提交件作为冻结输入登记）。
    非 succeeded 的 M4 StepRun 一律不看（与上游「只接受 succeeded 的包」同口径）。
    """
    documents = []
    for checkpoint in reader.list_checkpoints(edition_part_id, "m4"):
        step_run_id = (checkpoint.get("content") or {}).get("step_run_id")
        if not step_run_id:
            continue
        step = reader.get_step_run(step_run_id)
        if step is None or step["status"] != "succeeded":
            continue
        request = json.loads(step["request_json"] or "{}")
        revision_ids = list(request.get("input_artifact_ids") or [])
        types = _artifact_types(reader, revision_ids)
        for revision_id in revision_ids:
            if types.get(revision_id) != SUBMISSION_TYPE:
                continue
            documents.append((revision_id, _read_doc(reader, revision_id)))
    return documents


def scan(reader, edition_part_id, *, markers=None):
    """``run_m5`` 用的入口：定位提交件→扫描→产出发现（无提交件即返回空表）。"""
    documents = submission_documents(reader, edition_part_id)
    if not documents:
        return []
    active = markers if markers is not None else markers_from_env()
    return findings_from_hits(scan_documents(documents, markers=active))
