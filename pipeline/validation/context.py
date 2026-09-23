"""M5 只读上下文：把冻结修订的字节读入并复算 sha256。

``build_context`` 经 LedgerPort 的 ``reader.read_object``（``LedgerReader`` 与 ``LedgerService`` 同名同义）
读取每个冻结修订的字节并逐个复算 sha256；哈希不符或对象缺失**不抛异常**，
只把 ``actual_sha256`` / ``doc`` 置为 ``None``，交由 ``g1_frozen_bytes`` 判
fail-closed。输出键集与 K1 ``fixture_context()`` 完全一致。

**按证据级别分派（R83，第 100 条 D5）**：``evidence_level == "offset_level"``
时额外装载电子文本档所需的 M1/M2 文本对象——``raw_text`` 与
``cleaned_text_revision`` 是**裸文本字节**，不走 ``json``/``yaml`` 解析（原文
含 YAML front matter，按文档结构解析会失真），一律直接按 UTF-8 解码；
``patches`` 与 ``sanitization_report`` 是 JSON 对象；``batch_assignments`` 为
冻结 ``corpus_batch`` 修订的 ``{task_id: [span_id, ...]}``。OCR 档下这些键
如实为空值，键集不变。
"""

import hashlib
import json

import yaml


def _read_bytes(reader, sha256):
    # LedgerService 与 LedgerReader 都经 LedgerReadMixin 提供 read_object（TODO.md T03），不再直读对象存储
    return reader.read_object(sha256)


def _parse(data):
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


def _revision_meta(reader, revision_id):
    info = reader.describe_revision(revision_id)
    if info is None:
        return {}
    return {key: info[key] for key in ("status", "artifact_type", "artifact_id")}


def build_context(reader, inputs, *, target_consumption_level):
    """读取全部冻结修订的字节并构造纯函数上下文（键集同 ``fixture_context()``）。"""
    frozen_revision_ids = list(inputs["frozen_revision_ids"])
    raw_frozen = {}
    for revision_id in frozen_revision_ids:
        row = reader.get_revision(revision_id)
        registered = row["sha256"] if row is not None else None
        data = None
        if registered is not None:
            try:
                data = _read_bytes(reader, registered)
            except Exception:  # noqa: BLE001 —— 对象缺失不抛，判 fail-closed
                data = None
        actual = hashlib.sha256(data).hexdigest() if data is not None else None
        meta = _revision_meta(reader, revision_id)
        raw_frozen[revision_id] = {
            "sha256": registered,
            "actual_sha256": actual,
            "doc": _parse(data) if data is not None else None,
            "status": meta.get("status"),
            "artifact_type": meta.get("artifact_type"),
            "artifact_id": meta.get("artifact_id"),
        }

    def doc_of(revision_id):
        return (raw_frozen.get(revision_id) or {}).get("doc")

    def raw_text_of(revision_id):
        """按修订登记 sha256 读裸文本字节并 UTF-8 解码。"""
        entry = raw_frozen.get(revision_id) or {}
        sha256 = entry.get("sha256")
        if sha256 is None:
            return None
        try:
            data = _read_bytes(reader, sha256)
        except Exception:  # noqa: BLE001 —— 对象缺失不抛
            return None
        if data is None:
            return None
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return None

    manifest = doc_of(inputs["manifest_revision_id"]) or {}
    ocr_page_set = (
        doc_of(inputs["ocr_page_set_revision_id"])
        if inputs.get("ocr_page_set_revision_id")
        else {}
    ) or {}
    page_docs = {
        page: doc_of(revision_id) or {}
        for page, revision_id in inputs["page_revision_ids"].items()
    }
    human_events = [
        doc_of(revision_id) or {}
        for revision_id in inputs["human_event_revision_ids"]
    ]
    spans_doc = doc_of(inputs["corpus_spans_revision_id"]) or {}

    evidence_level = spans_doc.get("evidence_level")
    raw_text_revision_id = inputs.get("raw_text_revision_id")
    cleaned_text_revision_id = inputs.get("cleaned_text_revision_id")
    patch_set_revision_id = inputs.get("patch_set_revision_id")
    sanitization_report_revision_id = inputs.get("sanitization_report_revision_id")

    raw_text = raw_text_of(raw_text_revision_id) if raw_text_revision_id else None
    cleaned_text = (
        raw_text_of(cleaned_text_revision_id) if cleaned_text_revision_id else None
    )
    # 裸文本修订的内容**就是**文本：其 ``doc`` 取 UTF-8 解码结果，不以
    # JSON/YAML 是否可解析论「对象缺失」（原文含 YAML front matter，按文档
    # 结构解析会失败，那不是缺对象）。OCR 档下这两者恒为 None，不受影响。
    for revision_id, text in (
        (raw_text_revision_id, raw_text),
        (cleaned_text_revision_id, cleaned_text),
    ):
        if revision_id and text is not None:
            (raw_frozen.get(revision_id) or {})["doc"] = text
    patches = doc_of(patch_set_revision_id) if patch_set_revision_id else None
    if not isinstance(patches, list):
        patches = []
    sanitization_report = (
        doc_of(sanitization_report_revision_id) if sanitization_report_revision_id else None
    )
    if not isinstance(sanitization_report, dict):
        sanitization_report = {}

    # 冻结 corpus_batch 修订 → {task_id: [span_id, ...]}（offset 档批次复算用）
    batch_assignments = {}
    batch_names = list(inputs.get("batch_names") or [])
    for name, revision_id in zip(batch_names, inputs["batch_revision_ids"]):
        members = doc_of(revision_id)
        if not isinstance(members, list):
            continue
        batch_assignments[name] = [
            member.get("span_id") for member in members if isinstance(member, dict)
        ]

    revision_roles = {
        "m3_package": inputs["m3_package_revision_id"],
        "corpus_package": inputs["corpus_package_revision_id"],
        "corpus_spans": inputs["corpus_spans_revision_id"],
        "coverage_report": inputs["coverage_report_revision_id"],
        "validation_report": inputs["validation_report_revision_id"],
        "configuration": inputs["configuration_revision_id"],
        "source_manifest": inputs["manifest_revision_id"],
    }
    if inputs.get("ocr_page_set_revision_id"):
        revision_roles["ocr_page_set"] = inputs["ocr_page_set_revision_id"]
    for name, revision_id in zip(batch_names, inputs["batch_revision_ids"]):
        revision_roles[name] = revision_id
    for page, revision_id in inputs["page_revision_ids"].items():
        revision_roles[page] = revision_id
    for revision_id in inputs["human_event_revision_ids"]:
        revision_roles["human_event"] = revision_id
    for kind in (
        "raw_text",
        "cleaned_text_revision",
        "deterministic_patch_set",
        "sanitization_report",
    ):
        revision_id = inputs.get(
            {
                "raw_text": "raw_text_revision_id",
                "cleaned_text_revision": "cleaned_text_revision_id",
                "deterministic_patch_set": "patch_set_revision_id",
                "sanitization_report": "sanitization_report_revision_id",
            }[kind]
        )
        if revision_id:
            revision_roles[kind] = revision_id

    return {
        "manifest": manifest,
        "ocr_page_set": ocr_page_set,
        "page_docs": page_docs,
        "terminal_states": ocr_page_set.get("terminal_states") or {},
        "human_events": human_events,
        "spans_doc": spans_doc,
        "corpus_package": doc_of(inputs["corpus_package_revision_id"]) or {},
        "coverage_report": doc_of(inputs["coverage_report_revision_id"]) or {},
        "m3_package": doc_of(inputs["m3_package_revision_id"]) or {},
        "configuration": doc_of(inputs["configuration_revision_id"]) or {},
        "evidence_level": evidence_level,
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "patches": patches,
        "sanitization_report": sanitization_report,
        "batch_assignments": batch_assignments,
        "raw_text_revision_id": raw_text_revision_id,
        "cleaned_text_revision_id": cleaned_text_revision_id,
        "patch_set_revision_id": patch_set_revision_id,
        "sanitization_report_revision_id": sanitization_report_revision_id,
        "technique_id": manifest.get("technique_id"),
        "target_consumption_level": target_consumption_level,
        "page_revision_ids": dict(inputs["page_revision_ids"]),
        "batch_revision_ids": list(inputs["batch_revision_ids"]),
        "corpus_spans_revision_id": inputs["corpus_spans_revision_id"],
        "corpus_package_revision_id": inputs["corpus_package_revision_id"],
        "m3_package_revision_id": inputs["m3_package_revision_id"],
        "frozen_revision_ids": frozen_revision_ids,
        "revision_roles": revision_roles,
        "raw": {"frozen": raw_frozen},
    }
