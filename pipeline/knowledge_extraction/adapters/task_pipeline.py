"""任务管线 Adapter：把工位 4/5 产出规范化为提交件，并导出任务输入。

Adapter 只负责把外部形态转成提交件；产物必须先登记进 Ledger 才能被 M4 核心消费。
本模块不读 Ledger、不调用模型。
"""

from pathlib import Path

import yaml

from pipeline.ledger.errors import SchemaViolation

from .. import CANDIDATE_SCHEMA_VERSION
from ..errors import ExtractionRefused
from ..submission import validate_submission

# 工位 5 产出中 M4 会丢弃（重新分配或首切片不收）的键
_DROP_KEYS = ("assertion_id", "proposition_id", "canon_refs")
_DROP_NOTE = "丢弃 %s（M4 重新分配或首切片不收）"

_STAGE_BY_CATEGORY = {"assertion": "assertions", "concept_mention": "concepts"}

_TASK_NOTE = "segments 取自 Ledger corpus_spans；产出经 normalize_task_output 登记"


def _evidence_row(entry):
    """把工位 5 证据条目转成提交件证据键（保留已有 quote / span_char_*）。"""
    row = {
        "source_span_id": entry["source_span_id"],
        "support_type": entry["support_type"],
    }
    for key in ("quote", "span_char_start", "span_char_end"):
        if key in entry:
            row[key] = entry[key]
    return row


def _assertion_items(doc):
    """从工位 5 ``assertions`` 产出条 目与 adapter_notes。"""
    if "assertions" not in doc:
        raise SchemaViolation("工位 5 产出缺 assertions", code="SCH_001")
    entries = doc["assertions"]
    if not isinstance(entries, list):
        raise SchemaViolation("assertions 必须是 list", code="SCH_001")
    items = []
    notes = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise SchemaViolation("assertions[%d] 必须是对象" % index, code="SCH_001")
        for key in ("proposition", "relation"):
            if key not in entry:
                raise SchemaViolation("assertions[%d] 缺 %s" % (index, key), code="SCH_001")
        evidence = [_evidence_row(row) for row in entry.get("evidence", []) or []]
        items.append(
            {
                "proposition": entry["proposition"],
                "relation": entry["relation"],
                "evidence": evidence,
                "conditions": list(entry.get("conditions", []) or []),
                "exceptions": list(entry.get("exceptions", []) or []),
                "concept_refs": list(entry.get("concept_ids", []) or []),
                "school_ids": list(entry.get("school_ids", []) or []),
                "layer": entry.get("layer", "general"),
                "status": entry.get("status"),
            }
        )
        for key in _DROP_KEYS:
            if key in entry:
                notes.add(_DROP_NOTE % key)
    return items, sorted(notes)


def _concept_mention_items(doc, seg_span_map):
    """从工位 4 ``new_concept_candidates`` / ``concept_mentions`` 生成 item。"""
    if "new_concept_candidates" not in doc and "concept_mentions" not in doc:
        raise SchemaViolation(
            "工位 4 产出缺 new_concept_candidates / concept_mentions", code="SCH_001"
        )
    entries = list(doc.get("new_concept_candidates") or []) + list(
        doc.get("concept_mentions") or []
    )
    items = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise SchemaViolation("concept 条目 %d 必须是对象" % index, code="SCH_001")
        surface = entry.get("surface")
        if not isinstance(surface, str) or not surface.strip():
            raise SchemaViolation("concept 条目 %d 缺 surface" % index, code="SCH_001")
        span_id = entry.get("source_span_id") or entry.get("span_id")
        if not span_id:
            seg_id = entry.get("seg_id")
            if seg_id is None or not seg_span_map or seg_id not in seg_span_map:
                raise SchemaViolation(
                    "concept 条目 %d 缺 source_span_id/span_id 且无可用 seg_span_map" % index,
                    code="SCH_001",
                )
            span_id = seg_span_map[seg_id]
        items.append(
            {
                "surface": surface,
                "evidence": [
                    {"source_span_id": span_id, "support_type": "direct", "quote": surface}
                ],
                "concept_ref": entry.get("concept_id"),
                "status": entry.get("status"),
            }
        )
    return items, []


def normalize_task_output(
    doc,
    *,
    category,
    lane,
    channel,
    technique_id,
    producer,
    source_task=None,
    seg_span_map=None,
):
    """把工位 4/5 产出规范化成提交件并通过 ``validate_submission`` 校验后返回。"""
    if not isinstance(doc, dict):
        raise SchemaViolation("任务产出必须是对象", code="SCH_001")
    if category == "assertion":
        items, notes = _assertion_items(doc)
    elif category == "concept_mention":
        items, notes = _concept_mention_items(doc, seg_span_map)
    else:
        raise SchemaViolation(
            "首切片 Adapter 只支持工位 4/5 形态（assertion / concept_mention），收到: %r"
            % (category,),
            code="SCH_002",
        )
    submission = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "category": category,
        "lane": lane,
        "channel": channel,
        "technique_id": technique_id,
        "producer": producer,
        "source_task": source_task,
        "skipped": list(doc.get("skipped_segments", []) or []),
        "adapter_notes": notes,
        "items": items,
    }
    return validate_submission(submission, technique_id=technique_id)


def _write_yaml(path, obj):
    """按固化默认写出 YAML（Unicode 保留、键序不排序）。"""
    path.write_bytes(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False).encode("utf-8"))


def export_task_inputs(
    spans_doc,
    *,
    out_dir,
    task_id,
    category,
    lane,
    technique_id,
    template_path,
    id_range,
    instruction_version,
    spans_revision_id=None,
):
    """导出任务输入到 ``out_dir``，返回写出的相对路径列表（顺序固定）。"""
    out = Path(out_dir)
    if out.exists() and any(out.iterdir()):
        raise ExtractionRefused("导出目录已存在且非空: %s" % out, code="SCH_002")
    (out / "input").mkdir(parents=True, exist_ok=True)
    (out / "INSTRUCTIONS.md").write_bytes(Path(template_path).read_bytes())
    spans = spans_doc["spans"]
    segments = [
        {
            "seg_id": "s%03d" % (index + 1),
            "span_id": span["span_id"],
            "page": span["page"],
            "text": span["text"],
        }
        for index, span in enumerate(spans)
    ]
    _write_yaml(out / "input" / "segments.yaml", {"segments": segments})
    _write_yaml(
        out / "input" / "spans.yaml",
        {"spans": [{"seg_id": row["seg_id"], "span_id": row["span_id"]} for row in segments]},
    )
    _write_yaml(
        out / "task.yaml",
        {
            "task_id": task_id,
            "stage": _STAGE_BY_CATEGORY[category],
            "technique_id": technique_id,
            "source_id": spans_doc["source_id"],
            "lane": lane,
            "instruction_version": instruction_version,
            "id_range": id_range,
            "spans_revision_id": spans_revision_id,
            "note": _TASK_NOTE,
        },
    )
    return ["INSTRUCTIONS.md", "input/segments.yaml", "input/spans.yaml", "task.yaml"]
