"""提交件契约 ``validate_submission``（纯函数，整件拒收）。

提交件是 M4 唯一的外部候选入口（§12.2:572）：一件一类、一个 lane、一个 channel。
本函数只做形状与闭集校验并补齐缺省值；渠道是否被首切片接受由 ``run_m4_submit``
在 ``begin_step_run`` 之前判定（D-01）。形状失败一律抛
``pipeline.ledger.errors.SchemaViolation``（缺字段 SCH_001、枚举/越界 SCH_002）。
"""

import copy

from pipeline.ledger.errors import SchemaViolation

from . import (
    CANDIDATE_SCHEMA_VERSION,
    CATEGORIES,
    CHANNELS,
    ITEM_KEYS,
    LANES,
    LAYERS,
    PRODUCER_KINDS,
    RELATIONS,
    SUPPORT_TYPES,
)

_TOP_REQUIRED = (
    "schema_version",
    "category",
    "lane",
    "channel",
    "technique_id",
    "producer",
    "items",
)
_TOP_OPTIONAL = ("source_task", "skipped", "adapter_notes")
_PRODUCER_REQUIRED = ("kind", "name")
_PRODUCER_OPTIONAL = ("model_id", "prompt_sha256", "response_sha256")
_EVIDENCE_REQUIRED = ("source_span_id", "support_type")
_EVIDENCE_OPTIONAL = ("span_char_start", "span_char_end", "quote")
_ALLOWED_STATUS = (None, "machine_extracted")
_SUBJECT_KINDS = ("assertion", "pattern")


def _require(condition, message, code):
    """条件不成立即抛 ``SchemaViolation``（整件拒收）。"""
    if not condition:
        raise SchemaViolation(message, code=code)


def _is_int(value):
    """排除 ``bool`` 的整型判定。"""
    return isinstance(value, int) and not isinstance(value, bool)


def _text(value, label):
    """要求非空字符串。"""
    _require(isinstance(value, str) and bool(value.strip()), "%s 必须为非空字符串" % label, "SCH_001")
    return value


def _normalize_status(item):
    """status 缺省补 ``None``；高于 ``machine_extracted`` 一律 SCH_002。"""
    status = item.get("status")
    _require(
        status in _ALLOWED_STATUS,
        "status 越权: %r（M4 上限 machine_extracted）" % (status,),
        "SCH_002",
    )
    return status


def _normalize_evidence(evidence, label):
    """校验 evidence 列表并规范化每条证据键（只保留契约允许的键）。"""
    _require(isinstance(evidence, list), "%s.evidence 必须是 list" % label, "SCH_001")
    normalized = []
    for index, entry in enumerate(evidence):
        where = "%s.evidence[%d]" % (label, index)
        _require(isinstance(entry, dict), "%s 必须是对象" % where, "SCH_001")
        extra = set(entry) - set(_EVIDENCE_REQUIRED) - set(_EVIDENCE_OPTIONAL)
        _require(not extra, "%s 含未知键: %s" % (where, sorted(extra)), "SCH_002")
        missing = [key for key in _EVIDENCE_REQUIRED if key not in entry]
        _require(not missing, "%s 缺必填键: %s" % (where, missing), "SCH_001")
        _text(entry["source_span_id"], "%s.source_span_id" % where)
        _require(
            entry["support_type"] in SUPPORT_TYPES,
            "%s.support_type 非闭集: %r" % (where, entry["support_type"]),
            "SCH_002",
        )
        has_start = "span_char_start" in entry
        has_end = "span_char_end" in entry
        _require(has_start == has_end, "%s 的 span_char_start/span_char_end 必须成对出现" % where, "SCH_001")
        if has_start:
            _require(
                _is_int(entry["span_char_start"]) and entry["span_char_start"] >= 0,
                "%s.span_char_start 必须为非负整数" % where,
                "SCH_001",
            )
            _require(
                _is_int(entry["span_char_end"]) and entry["span_char_end"] >= 0,
                "%s.span_char_end 必须为非负整数" % where,
                "SCH_001",
            )
        if "quote" in entry:
            _text(entry["quote"], "%s.quote" % where)
        row = {
            "source_span_id": entry["source_span_id"],
            "support_type": entry["support_type"],
        }
        if has_start:
            row["span_char_start"] = entry["span_char_start"]
            row["span_char_end"] = entry["span_char_end"]
        if "quote" in entry:
            row["quote"] = entry["quote"]
        normalized.append(row)
    return normalized


def _normalize_producer(producer):
    """校验并规范化 producer（缺省补 None）。"""
    _require(isinstance(producer, dict), "producer 必须是对象", "SCH_001")
    extra = set(producer) - set(_PRODUCER_REQUIRED) - set(_PRODUCER_OPTIONAL)
    _require(not extra, "producer 含未知键: %s" % sorted(extra), "SCH_002")
    missing = [key for key in _PRODUCER_REQUIRED if key not in producer]
    _require(not missing, "producer 缺必填键: %s" % missing, "SCH_001")
    _require(
        producer["kind"] in PRODUCER_KINDS,
        "producer.kind 非闭集: %r" % (producer["kind"],),
        "SCH_002",
    )
    _text(producer["name"], "producer.name")
    return {
        "kind": producer["kind"],
        "name": producer["name"],
        "model_id": producer.get("model_id"),
        "prompt_sha256": producer.get("prompt_sha256"),
        "response_sha256": producer.get("response_sha256"),
    }


def _assertion_item(item, evidence):
    """assertion item 规范化（S7–S8）。"""
    _require(item["relation"] in RELATIONS, "relation 非闭集: %r" % (item["relation"],), "SCH_002")
    layer = item.get("layer", "general")
    _require(layer in LAYERS, "layer 非闭集: %r" % (layer,), "SCH_002")
    for key in ("conditions", "exceptions", "concept_refs", "school_ids"):
        value = item.get(key, [])
        _require(isinstance(value, list), "%s 必须是 list" % key, "SCH_001")
    return {
        "proposition": _text(item["proposition"], "proposition"),
        "relation": item["relation"],
        "evidence": evidence,
        "conditions": list(item.get("conditions", [])),
        "exceptions": list(item.get("exceptions", [])),
        "concept_refs": list(item.get("concept_refs", [])),
        "school_ids": list(item.get("school_ids", [])),
        "layer": layer,
        "status": _normalize_status(item),
    }


def _pattern_item(item, evidence):
    """pattern item 规范化（S9）。"""
    propositions = item["assertion_propositions"]
    _require(isinstance(propositions, list) and propositions, "assertion_propositions 必须为非空 list", "SCH_001")
    for value in propositions:
        _require(isinstance(value, str) and value.strip(), "assertion_propositions 每项必须为非空字符串", "SCH_001")
    interpretation = item.get("interpretation")
    _require(interpretation is None or isinstance(interpretation, str), "interpretation 必须为字符串或 null", "SCH_001")
    return {
        "name": _text(item["name"], "name"),
        "assertion_propositions": list(propositions),
        "evidence": evidence,
        "interpretation": interpretation,
        "status": _normalize_status(item),
    }


def _school_view_item(item, evidence):
    """school_view item 规范化（S10）。"""
    _text(item["school_id"], "school_id")
    subject = item["subject"]
    _require(isinstance(subject, dict), "subject 必须是对象", "SCH_001")
    extra = set(subject) - {"kind", "key"}
    _require(not extra, "subject 含未知键: %s" % sorted(extra), "SCH_002")
    _require(subject.get("kind") in _SUBJECT_KINDS, "subject.kind 非闭集: %r" % (subject.get("kind"),), "SCH_002")
    _text(subject.get("key"), "subject.key")
    claims = item["claim_propositions"]
    _require(isinstance(claims, list), "claim_propositions 必须是 list", "SCH_001")
    for value in claims:
        _require(isinstance(value, str) and value.strip(), "claim_propositions 每项必须为非空字符串", "SCH_001")
    _require(isinstance(item["changes_current_judgment"], bool), "changes_current_judgment 必须为 bool", "SCH_001")
    conflict_key = item.get("conflict_key")
    _require(conflict_key is None or isinstance(conflict_key, str), "conflict_key 必须为字符串或 null", "SCH_001")
    return {
        "school_id": item["school_id"],
        "subject": {"kind": subject["kind"], "key": subject["key"]},
        "claim_propositions": list(claims),
        "changes_current_judgment": item["changes_current_judgment"],
        "conflict_key": conflict_key,
        "evidence": evidence,
        "status": _normalize_status(item),
    }


def _concept_mention_item(item, evidence):
    """concept_mention item 规范化（S11）。"""
    concept_ref = item.get("concept_ref")
    _require(concept_ref is None or isinstance(concept_ref, str), "concept_ref 必须为字符串或 null", "SCH_001")
    return {
        "surface": _text(item["surface"], "surface"),
        "evidence": evidence,
        "concept_ref": concept_ref,
        "status": _normalize_status(item),
    }


_ITEM_NORMALIZERS = {
    "assertion": _assertion_item,
    "pattern": _pattern_item,
    "school_view": _school_view_item,
    "concept_mention": _concept_mention_item,
}


def _normalize_item(category, item, label):
    """按类别键表校验单个 item 并规范化。"""
    _require(isinstance(item, dict), "%s 必须是对象" % label, "SCH_001")
    spec = ITEM_KEYS[category]
    required = set(spec["required"])
    optional = set(spec["optional"])
    extra = set(item) - required - optional
    _require(not extra, "%s 含类别外键（类别混合）: %s" % (label, sorted(extra)), "SCH_002")
    missing = [key for key in spec["required"] if key not in item]
    _require(not missing, "%s 缺必填键: %s" % (label, missing), "SCH_001")
    evidence = _normalize_evidence(item["evidence"], label)
    return _ITEM_NORMALIZERS[category](item, evidence)


def validate_submission(doc, *, technique_id):
    """校验并规范化一份提交件，返回深拷贝；任何形状/闭集失败整件拒收。"""
    _require(isinstance(doc, dict), "提交件必须是对象", "SCH_001")
    extra = set(doc) - set(_TOP_REQUIRED) - set(_TOP_OPTIONAL)
    _require(not extra, "提交件含未知顶层键: %s" % sorted(extra), "SCH_002")
    missing = [key for key in _TOP_REQUIRED if key not in doc]
    _require(not missing, "提交件缺必填键: %s" % missing, "SCH_001")
    _require(
        doc["schema_version"] == CANDIDATE_SCHEMA_VERSION,
        "schema_version 不符: %r" % (doc["schema_version"],),
        "SCH_002",
    )
    _require(
        doc["technique_id"] == technique_id,
        "technique_id 不符: %r" % (doc["technique_id"],),
        "SCH_002",
    )
    category = doc["category"]
    _require(category in CATEGORIES, "category 非闭集: %r" % (category,), "SCH_002")
    _require(doc["lane"] in LANES, "lane 非闭集: %r" % (doc["lane"],), "SCH_002")
    _require(doc["channel"] in CHANNELS, "channel 非闭集: %r" % (doc["channel"],), "SCH_002")
    producer = _normalize_producer(doc["producer"])
    _require(isinstance(doc["items"], list), "items 必须是 list", "SCH_001")
    items = [
        _normalize_item(category, item, "items[%d]" % index)
        for index, item in enumerate(doc["items"])
    ]
    skipped = doc.get("skipped", [])
    adapter_notes = doc.get("adapter_notes", [])
    _require(isinstance(skipped, list), "skipped 必须是 list", "SCH_001")
    _require(isinstance(adapter_notes, list), "adapter_notes 必须是 list", "SCH_001")
    return {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "category": category,
        "lane": doc["lane"],
        "channel": doc["channel"],
        "technique_id": doc["technique_id"],
        "producer": producer,
        "source_task": copy.deepcopy(doc.get("source_task")),
        "skipped": list(skipped),
        "adapter_notes": list(adapter_notes),
        "items": items,
    }
