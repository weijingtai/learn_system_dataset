"""M5 只读上下文：把冻结修订的字节读入并复算 sha256。

``build_context`` 经 ``reader.read_object``（若不可用则退化到
``reader.objects.get``，以同时支持 ``LedgerReader`` 与 ``LedgerService``）
读取每个冻结修订的字节并逐个复算 sha256；哈希不符或对象缺失**不抛异常**，
只把 ``actual_sha256`` / ``doc`` 置为 ``None``，交由 ``g1_frozen_bytes`` 判
fail-closed。输出键集与 K1 ``fixture_context()`` 完全一致。
"""

import hashlib
import json

import yaml


def _read_bytes(reader, sha256):
    reader_read = getattr(reader, "read_object", None)
    if reader_read is not None:
        return reader_read(sha256)
    return reader.objects.get(sha256)


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
    row = reader.store.conn.execute(
        "SELECT r.status, a.artifact_type, a.artifact_id FROM artifact_revisions r "
        "JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "WHERE r.artifact_revision_id=?",
        (revision_id,),
    ).fetchone()
    return dict(row) if row is not None else {}


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

    manifest = doc_of(inputs["manifest_revision_id"]) or {}
    ocr_page_set = doc_of(inputs["ocr_page_set_revision_id"]) or {}
    page_docs = {
        page: doc_of(revision_id) or {}
        for page, revision_id in inputs["page_revision_ids"].items()
    }
    human_events = [
        doc_of(revision_id) or {}
        for revision_id in inputs["human_event_revision_ids"]
    ]
    spans_doc = doc_of(inputs["corpus_spans_revision_id"]) or {}

    revision_roles = {
        "m3_package": inputs["m3_package_revision_id"],
        "corpus_package": inputs["corpus_package_revision_id"],
        "corpus_spans": inputs["corpus_spans_revision_id"],
        "coverage_report": inputs["coverage_report_revision_id"],
        "validation_report": inputs["validation_report_revision_id"],
        "configuration": inputs["configuration_revision_id"],
        "source_manifest": inputs["manifest_revision_id"],
        "ocr_page_set": inputs["ocr_page_set_revision_id"],
    }
    batch_names = []
    for span in spans_doc.get("spans") or []:
        if span.get("batch_id") not in batch_names:
            batch_names.append(span.get("batch_id"))
    for name, revision_id in zip(batch_names, inputs["batch_revision_ids"]):
        revision_roles[name] = revision_id
    for page, revision_id in inputs["page_revision_ids"].items():
        revision_roles[page] = revision_id
    for revision_id in inputs["human_event_revision_ids"]:
        revision_roles["human_event"] = revision_id

    return {
        "manifest": manifest,
        "ocr_page_set": ocr_page_set,
        "page_docs": page_docs,
        "terminal_states": ocr_page_set.get("terminal_states") or {},
        "human_events": human_events,
        "spans_doc": spans_doc,
        "corpus_package": doc_of(inputs["corpus_package_revision_id"]) or {},
        "m3_package": doc_of(inputs["m3_package_revision_id"]) or {},
        "configuration": doc_of(inputs["configuration_revision_id"]) or {},
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
