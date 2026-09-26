"""M8 纯函数子包编译器（规格 §16:682-723，裁决 D1/D4/D10/D11/D14）。

纯函数：不读文件、不访问 Ledger、不取时间、不用随机数。只 import 标准库、
``pipeline.ledger.ids``、``pipeline.ledger.errors`` 与本包
``__init__``/``errors``/``canonical``/``levels``。

首切片子包：SourceAssetPack、EvidenceMapPack（只闭合尾链四段）、ReleaseManifest。
"""

import re
import struct

from pipeline.ledger import ids
from pipeline.ledger.errors import (
    DuplicateIdentifier,
    HashMismatch,
    InvalidIdentifier,
    MissingReference,
    SchemaViolation,
)

from . import CONSUMPTION_LEVELS, SUB_PACK_SCHEMA_VERSION, SUPPORTED_LEVELS
from .canonical import canonical_bytes, normalized_sha256, quote_sha256, sha256_hex
from .errors import DatasetRefused
from .levels import CONTENT_STATUSES, EVIDENCE_LEVELS

# D10 草案水印文案
INTERNAL_DEMO_WATERMARK = "INTERNAL_DEMO｜机器转录，未经人工校对｜不得作为知识来源或权威依据"

# §16:708-712 的第 4–7 段（SourceSpan→SourceAnchor→OcrPage→SourceAsset）
CHAIN_SEGMENTS = ["SourceSpan", "SourceAnchor", "OcrPage", "SourceAsset"]

# D-W8-14 + README:375：offset 档链段用**显式八段清单**（不采用统一抽象名）。
# 依据：README §11.5:375 已写定的清单逐字采用；统一抽象名会让 Gate 无法从包本身
# 判断该跑 OCR 四项还是 offset 四项，与裁定 107 Q-M8-08 的按档分派冲突。
OFFSET_CHAIN_SEGMENTS = [
    "KnowledgeEntry",
    "Assertion",
    "EvidenceLink",
    "SourceSpan",
    "SourceAnchor",
    "DeterministicPatchSet",
    "RawText",
    "SourceAsset",
]

# 裁定 78 D3：offset 档 SourceAnchor 七键（多一键、少一键都拒收 SCH_002）
OFFSET_ANCHOR_KEYS = (
    "raw_text_revision_id",
    "raw_start",
    "raw_end",
    "cleaned_text_revision_id",
    "start_offset",
    "end_offset",
    "quote_sha256",
)

# ACT 14 三.1：offset 档 SourceAssetPack 条目字段（逐字沿用清单写法，不产页图几何字段）
OFFSET_ASSET_KEYS = (
    "page",
    "path_ref",
    "sha256",
    "normalized_sha256",
    "original_encoding",
    "size",
)

# §17.1:843 四个 task（每个 task 一个 m8 Checkpoint）
TASKS = ("source_asset_pack", "evidence_map_pack", "release_manifest", "validation_report")

# §3.15 GraphProjectionPack 闭集与前缀规范（P3，0.1.0-draft）
GRAPH_PROJECTION_SCHEMA_VERSION = "0.1.0-draft"
GRAPH_NODE_KINDS = ("pattern", "concept", "assertion", "school_view")
GRAPH_RELATIONS = (
    "has_assertion",
    "belongs_to_concept",
    "in_conflict_group",
    "supports",
    "qualifies",
    "opposes",
)
_VALID_NODE_ID_PREFIXES = ("pat_", "co_", "as_", "sv_", "cg_")
_FORBIDDEN_NODE_ID_PREFIXES = ("c_", "e_")


def _validate_node_id(node_id):
    """校验 node_id 符合 ids.py 与 §8.1 闭集，严禁 c_ / e_ 前缀（第 107 条更正）。"""
    if not isinstance(node_id, str):
        raise InvalidIdentifier("node_id 必须为字符串: %r" % (node_id,), code="ID_001")
    for forbidden in _FORBIDDEN_NODE_ID_PREFIXES:
        if node_id.startswith(forbidden):
            raise InvalidIdentifier(
                "node_id 严禁使用未登记的前缀 %r: %r" % (forbidden, node_id), code="ID_001"
            )
    if not any(node_id.startswith(p) for p in _VALID_NODE_ID_PREFIXES):
        raise InvalidIdentifier(
            "node_id 前缀非合法已登记前缀: %r" % (node_id,), code="ID_001"
        )
    if node_id.startswith("pat_"):
        ids.validate("pattern_id", node_id)
    elif node_id.startswith("co_"):
        if node_id.startswith("co_shared_"):
            ids.validate("shared_concept_id", node_id)
        else:
            ids.validate("technique_concept_id", node_id)
    elif node_id.startswith("as_"):
        ids.validate("assertion_id", node_id)
    elif node_id.startswith("sv_"):
        ids.validate("school_view_id", node_id)
    elif node_id.startswith("cg_"):
        ids.validate("conflict_group_id", node_id)


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PAGE_RE = re.compile(r"^page_([0-9]{3,4})$")
_SPAN_TAIL_RE = re.compile(r"_p([0-9]{4})_s([0-9]{2})$")
_OFFSET_SPAN_RE = re.compile(ids.SOURCE_SPAN_ID_OFFSET_PARTS)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def png_size(data):
    """解析 PNG 头的宽高（IHDR 前 8 字节）；非 PNG 或长度不足 → ``SCH_002``。"""
    if (
        not isinstance(data, (bytes, bytearray))
        or len(data) < 24
        or bytes(data[:8]) != _PNG_SIGNATURE
    ):
        raise SchemaViolation("非法 PNG 数据（签名或长度不足）", code="SCH_002")
    return struct.unpack(">II", bytes(data[16:24]))


def page_number(page):
    """解析页名为整数页号；不匹配 → ``SchemaViolation(SCH_002)``。"""
    match = _PAGE_RE.match(page) if isinstance(page, str) else None
    if match is None:
        raise SchemaViolation("非法页名（应匹配 ^page_[0-9]{3,4}$）: %r" % (page,), code="SCH_002")
    return int(match.group(1))


def parse_span_identity(span_id):
    """校验并拆解 ``span_id``。

    经 ``pipeline.ledger.ids`` 校验，不定义自有正则（第 102 条）。
    页码形态返回 ``(页号, 行序)``；offset 形态返回 ``(None, 偏移)``。
    """
    ids.validate("source_span_id", span_id)
    match = _SPAN_TAIL_RE.search(span_id)
    if match is not None:
        return int(match.group(1)), int(match.group(2))
    match_offset = _OFFSET_SPAN_RE.match(span_id)
    if match_offset is not None:
        return None, int(match_offset.group(3))
    raise InvalidIdentifier("span_id 缺少页号/行序或偏移段: %r" % (span_id,), code="ID_001")


def _build_offset_source_asset_pack(*, manifest, raw_text_sha256):
    """编译 offset 档 SourceAssetPack（ACT 14 三；裁定 81、裁定 103 D1）。

    offset 档的资产事实来自 M1 ``source_manifest.source_assets`` 与 ``RawText`` 修订，
    **不是**页图修订（真书无任何 ``source_asset_page``）。逐条取
    ``OFFSET_ASSET_KEYS`` 六字段并校验 ``sha256 == raw_text 修订 sha256``（SRC_003），
    不产出 width/height 一类页图几何字段（不以 0/None 占位）。
    """
    if _SHA256_RE.match(str(raw_text_sha256)) is None:
        raise SchemaViolation(
            "RawText 修订 sha256 格式非法: %r" % (raw_text_sha256,), code="SCH_002"
        )
    assets = manifest.get("source_assets") or []
    if not assets:
        raise MissingReference(
            "清单 source_assets 为空（offset 档底本资产事实缺失）", code="REF_001"
        )
    pages = []
    for item in assets:
        missing = [key for key in OFFSET_ASSET_KEYS if key not in item]
        if missing:
            raise SchemaViolation(
                "offset 档 source_assets 条目缺字段 %r（实际键集 %r）"
                % (missing, sorted(item)),
                code="SCH_002",
            )
        if item["sha256"] != raw_text_sha256:
            raise HashMismatch(
                "页 %s 底本哈希与 RawText 修订不符（SRC_003）" % item["page"],
                code="SRC_003",
            )
        pages.append({key: item[key] for key in OFFSET_ASSET_KEYS})
    pack = {
        "pack_type": "source_asset_pack",
        "schema_version": SUB_PACK_SCHEMA_VERSION,
        "source_id": manifest["source_id"],
        "edition_part_artifact_id": manifest["edition_part"]["artifact_id"],
        "content_level": manifest["release_policy"],
        "rights_status": manifest["rights_status"],
        "pages": pages,
    }
    data = canonical_bytes(pack)
    return {"pack": pack, "bytes": data, "sha256": sha256_hex(data)}


def build_source_asset_pack(*, manifest, asset_records, raw_text_sha256=None):
    """编译 SourceAssetPack（D14、§16:717-723，ACT 10 分派）。

    ``raw_text_sha256``（ACT 14 三）：传入即按 **offset 档**编译——资产事实取自
    ``manifest.source_assets`` 与 RawText 修订，并校验两者 sha256 逐字相等。
    缺省 None 时按 OCR 档编译，行为逐字不变。

    返回 ``{"pack", "bytes", "sha256"}``。
    """
    policy = manifest["release_policy"]
    if policy not in ("derived_page_images_only", "reference_and_hash_only"):
        raise DatasetRefused(
            "发布策略未实现，需 derived_page_images_only 或 reference_and_hash_only: %r"
            % (policy,),
            code="SCH_002",
        )

    if raw_text_sha256 is not None:
        return _build_offset_source_asset_pack(
            manifest=manifest, raw_text_sha256=raw_text_sha256
        )

    page_order = manifest["edition_part"]["pages"]
    manifest_assets = {item["page"]: item for item in manifest["source_assets"]}

    # S2：页序与缺失页校验
    for page in page_order:
        if page not in manifest_assets:
            raise MissingReference("清单 source_assets 缺页: %s" % page, code="REF_001")
        if page not in asset_records:
            raise MissingReference("asset_records 缺页: %s" % page, code="REF_001")
    for page in asset_records:
        if page not in page_order:
            raise SchemaViolation("asset_records 含页序外的页: %s" % page, code="SCH_002")

    # S3：哈希与尺寸校验（reference_and_hash_only 不含宽高/尺寸/正文/图像，bytes_included: false）
    pages = []
    for page in page_order:
        item = manifest_assets[page]
        record = asset_records[page]
        ids.validate("artifact_revision_id", record["artifact_revision_id"])
        if record["sha256"] != item["sha256"]:
            raise HashMismatch("页 %s 资产哈希不符（SRC_003）" % page, code="SRC_003")
        if policy == "reference_and_hash_only":
            pages.append(
                {
                    "page": page,
                    "asset_artifact_revision_id": record["artifact_revision_id"],
                    "sha256": item["sha256"],
                    "bytes_included": False,
                    "rights_note": manifest.get("rights_status") or item.get("rights_note", ""),
                }
            )
        else:
            if (record["width"], record["height"]) != (item["width"], item["height"]):
                raise HashMismatch("页 %s 资产尺寸不符（SRC_003）" % page, code="SRC_003")
            pages.append(
                {
                    "page": page,
                    "asset_artifact_revision_id": record["artifact_revision_id"],
                    "sha256": item["sha256"],
                    "size": record["size"],
                    "width": item["width"],
                    "height": item["height"],
                }
            )

    # S4：组装
    pack = {
        "pack_type": "source_asset_pack",
        "schema_version": SUB_PACK_SCHEMA_VERSION,
        "source_id": manifest["source_id"],
        "edition_part_artifact_id": manifest["edition_part"]["artifact_id"],
        "content_level": policy,
        "rights_status": manifest["rights_status"],
        "pages": pages,
    }
    data = canonical_bytes(pack)
    return {"pack": pack, "bytes": data, "sha256": sha256_hex(data)}


def _check_in_frame(box, frame, span_id):
    """字框/行框是否越出页框；越界 → ``DatasetRefused(SCH_002)``。"""
    if (
        box["x"] < 0
        or box["y"] < 0
        or box["x"] + box["w"] > frame["width"]
        or box["y"] + box["h"] > frame["height"]
    ):
        raise DatasetRefused("框越出页框（越界）: %s" % span_id, code="SCH_002")


def build_evidence_map_pack(
    *,
    spans_doc,
    page_docs,
    ocr_page_revision_ids,
    source_asset_pack,
    excluded_pages,
    snapshot_knowledge=None,
):
    """编译 EvidenceMapPack：完整 ``span_id`` 为键，只闭合尾链四段。

    ``snapshot_knowledge``（ACT 13，D-W8-13b）：有已解析的 M7 Snapshot
    knowledge 时，``knowledge_chain`` 推导为 ``"compiled"``，否则为
    ``"not_compiled"``（README §8 第 3 条：届时 ``knowledge_chain`` 改为
    ``compiled``）。推导在本函数内部完成，不接受调用方直接传字符串字面量。
    本切片 ``chain_segments`` 仍为四段，不改。

    返回 ``{"pack", "bytes", "sha256", "normalized_sha256", "span_keys",
    "highlight_counts", "glyph_count"}``。
    """
    knowledge_chain = "compiled" if snapshot_knowledge is not None else "not_compiled"
    # E1：级别与表头计数
    if spans_doc["evidence_level"] not in EVIDENCE_LEVELS:
        raise SchemaViolation(
            "evidence_level 非法: %r（§11.1 闭集）" % (spans_doc["evidence_level"],),
            code="SCH_002",
        )
    spans = spans_doc["spans"]
    if spans_doc["span_count"] != len(spans):
        raise SchemaViolation(
            "span_count 与实际 spans 长度不符: %r != %d"
            % (spans_doc["span_count"], len(spans)),
            code="SCH_002",
        )

    # E1b（ACT 14 二）：offset 档走独立分支；分派权威 = spans_doc["evidence_level"]
    if spans_doc["evidence_level"] == "offset_level":
        return _build_offset_evidence_map_pack(
            spans_doc=spans_doc,
            spans=spans,
            excluded_pages=excluded_pages,
            knowledge_chain=knowledge_chain,
        )

    # E2：资产页表
    asset_pages = {item["page"]: item for item in source_asset_pack["pages"]}

    entries = {}
    highlight_counts = {"glyph": 0, "line_bbox": 0}
    glyph_count = 0
    content_status = spans_doc["content_status"]

    # E3：逐 span 编译
    for span in spans:
        span_id = span["span_id"]
        page = span["page"]
        pno, seq = parse_span_identity(span_id)
        if pno != page_number(page):
            raise InvalidIdentifier("span_id 页号与 page 不符: %s" % span_id, code="ID_001")
        if seq != span["line_index"] + 1:
            raise InvalidIdentifier(
                "span_id 行序与 line_index+1 不符: %s" % span_id, code="ID_001"
            )
        if span_id in entries:
            raise DuplicateIdentifier("span_id 重复: %s" % span_id, code="ID_002")
        if page in excluded_pages:
            raise DatasetRefused("排除页上出现 Span: %s" % page, code="SCH_002")
        if (
            page not in page_docs
            or page not in ocr_page_revision_ids
            or page not in asset_pages
        ):
            raise MissingReference("Span 引用缺失页: %s" % page, code="REF_001")

        anchor = span["source_anchor"]
        if anchor["page"] != page:
            raise DatasetRefused("锚点页与 span 页不符: %s" % span_id, code="REF_001")

        asset = asset_pages[page]
        if anchor["image_sha256"] != asset["sha256"]:
            raise HashMismatch("锚点图像哈希与资产包不符: %s" % span_id, code="SRC_003")

        page_doc = page_docs[page]
        frame = {"width": page_doc["width"], "height": page_doc["height"]}
        if (frame["width"], frame["height"]) != (asset["width"], asset["height"]):
            raise DatasetRefused("坐标系与资产包不符: %s" % span_id, code="SRC_003")

        _check_in_frame(anchor["bbox"], frame, span_id)
        glyphs = []
        for char in anchor["chars"]:
            _check_in_frame(char["box"], frame, span_id)
            glyphs.append(
                {
                    "char_index": char["char_index"],
                    "glyph_id": char["glyph_id"],
                    "char": char["char"],
                    "box": dict(char["box"]),
                }
            )

        glyph_text_equal = "".join(item["char"] for item in glyphs) == span["text"]
        highlight_level = "glyph" if glyph_text_equal else "line_bbox"
        highlight_counts[highlight_level] += 1
        glyph_count += len(glyphs)

        entries[span_id] = {
            "span_id": span_id,
            "page": page,
            "line_index": span["line_index"],
            "start_offset": span["start_offset"],
            "end_offset": span["end_offset"],
            "text": span["text"],
            "quote_sha256": quote_sha256(span["text"]),
            "content_status": content_status,
            "watermark": content_status.startswith("machine_"),
            "line_id": anchor["line_id"],
            "bbox": dict(anchor["bbox"]),
            "glyphs": glyphs,
            "glyph_text_equal": glyph_text_equal,
            "highlight_level": highlight_level,
            "frame": frame,
            "image_sha256": anchor["image_sha256"],
            "ocr_page_artifact_revision_id": ocr_page_revision_ids[page],
            "source_asset_artifact_revision_id": asset["asset_artifact_revision_id"],
        }

    # E4：反向索引（按资产包页序；排除页值为 []）
    page_index = {}
    for item in source_asset_pack["pages"]:
        page = item["page"]
        page_index[page] = [span["span_id"] for span in spans if span["page"] == page]

    # E5：组装
    pack = {
        "pack_type": "evidence_map_pack",
        "schema_version": SUB_PACK_SCHEMA_VERSION,
        "source_id": spans_doc["source_id"],
        "edition_part_artifact_id": spans_doc["edition_part_artifact_id"],
        "evidence_level": spans_doc["evidence_level"],
        "content_status": content_status,
        "chain_segments": CHAIN_SEGMENTS,
        "knowledge_chain": knowledge_chain,
        "span_count": len(entries),
        "entries": entries,
        "page_index": page_index,
        "excluded_pages": dict(excluded_pages),
    }
    data = canonical_bytes(pack)
    return {
        "pack": pack,
        "bytes": data,
        "sha256": sha256_hex(data),
        "normalized_sha256": normalized_sha256(pack),
        "span_keys": list(entries),
        "highlight_counts": highlight_counts,
        "glyph_count": glyph_count,
    }


def _build_offset_evidence_map_pack(
    *, spans_doc, spans, excluded_pages, knowledge_chain
):
    """编译 offset 档 EvidenceMapPack（ACT 14 二；裁定 78 D3、81、103 D1）。

    与 glyphbox 档的差别：不读 ``span["page"]`` / ``span["line_index"]``，
    不读 ``anchor["chars"]`` / ``anchor["bbox"]``，不读 ``page_docs``、
    不读 ``source_asset_pack["pages"]``；``source_anchor`` 必须恰为裁定 78 D3 七键；
    ``chain_segments`` 取八段清单；``page_index`` 恒为 ``{}``（键必须存在，不许省略）。

    I-11：偏移逐字透传，不加不减。
    """
    if excluded_pages:
        raise SchemaViolation(
            "电子文本路线无页概念，excluded_pages 必须为空: %r" % (sorted(excluded_pages),),
            code="SCH_002",
        )
    entries = {}
    content_status = spans_doc["content_status"]
    for span in spans:
        span_id = span["span_id"]
        ids.validate("source_span_id", span_id)
        if span_id in entries:
            raise DuplicateIdentifier("span_id 重复: %s" % span_id, code="ID_002")
        anchor = span["source_anchor"]
        if set(anchor) != set(OFFSET_ANCHOR_KEYS):
            actual = sorted(anchor)
            missing_keys = [key for key in OFFSET_ANCHOR_KEYS if key not in anchor]
            extra_keys = [key for key in actual if key not in OFFSET_ANCHOR_KEYS]
            raise SchemaViolation(
                "offset 档 SourceAnchor 必须恰为裁定 78 D3 七键: %s 缺 %r 多 %r（实际键集 %r）"
                % (span_id, missing_keys, extra_keys, actual),
                code="SCH_002",
            )
        if anchor["quote_sha256"] != span["quote_sha256"]:
            raise HashMismatch(
                "锚点 quote_sha256 与 span 不符: %s" % span_id, code="SRC_003"
            )
        entries[span_id] = {
            "span_id": span_id,
            "sequence": span["sequence"],
            "start_offset": span["start_offset"],
            "end_offset": span["end_offset"],
            "text": span["text"],
            "quote_sha256": quote_sha256(span["text"]),
            "content_status": content_status,
            "watermark": content_status.startswith("machine_"),
            "evidence_level": "offset_level",
            # 七键逐字透传（I-11），不补造 page/line_index/chars/bbox
            "source_anchor": {key: anchor[key] for key in OFFSET_ANCHOR_KEYS},
        }
    pack = {
        "pack_type": "evidence_map_pack",
        "schema_version": SUB_PACK_SCHEMA_VERSION,
        "source_id": spans_doc["source_id"],
        "edition_part_artifact_id": spans_doc["edition_part_artifact_id"],
        "evidence_level": "offset_level",
        "content_status": content_status,
        "chain_segments": list(OFFSET_CHAIN_SEGMENTS),
        "knowledge_chain": knowledge_chain,
        "span_count": len(entries),
        "entries": entries,
        # offset 档不产出页索引；键必须存在（下游按名取用）
        "page_index": {},
        "excluded_pages": {},
    }
    data = canonical_bytes(pack)
    return {
        "pack": pack,
        "bytes": data,
        "sha256": sha256_hex(data),
        "normalized_sha256": normalized_sha256(pack),
        "span_keys": list(entries),
        # offset 档无 glyph/line_bbox 高亮概念：不计入任何类别
        "highlight_counts": {},
        "glyph_count": 0,
    }


def compute_known_defects(
    *, evidence_map_pack, m3_gate_profile, rights_status, assertion_without_subject=None
):
    """计算已知缺陷（代码闭集，按 code 字典序）。

    ``assertion_without_subject``（T04B）：``build_knowledge_data_pack`` 如实返回的无主体
    断言 ID；非空时按 INTERFACES §3.8 口径披露为 ``assertion_without_subject: N`` 并逐条列 ID。
    """
    defects = []

    if assertion_without_subject:
        orphan_ids = sorted(assertion_without_subject)
        defects.append(
            {
                "code": "assertion_without_subject",
                "detail": "%d: %s" % (len(orphan_ids), ",".join(orphan_ids)),
            }
        )

    excluded_pages = evidence_map_pack.get("excluded_pages") or {}
    if excluded_pages:
        detail = ",".join(
            "%s=%s" % (page, excluded_pages[page]) for page in sorted(excluded_pages)
        )
        defects.append({"code": "excluded_page", "detail": detail})

    evidence_level = evidence_map_pack.get("evidence_level")
    if evidence_level not in EVIDENCE_LEVELS:
        raise SchemaViolation(
            "evidence_map_pack evidence_level 非法: %r（闭集 %r）"
            % (evidence_level, EVIDENCE_LEVELS),
            code="SCH_002",
        )

    if evidence_level == "glyphbox_level":
        line_bbox_ids = [
            span_id
            for span_id, entry in evidence_map_pack["entries"].items()
            if entry["highlight_level"] == "line_bbox"
        ]
        if line_bbox_ids:
            defects.append(
                {"code": "glyph_text_mismatch", "detail": ",".join(line_bbox_ids)}
            )
    elif evidence_level == "offset_level":
        pass

    if evidence_map_pack["knowledge_chain"] != "compiled":
        defects.append(
            {
                "code": "knowledge_chain_not_compiled",
                "detail": "KnowledgeEntry,Assertion,EvidenceLink",
            }
        )

    content_status = evidence_map_pack["content_status"]
    if content_status.startswith("machine_"):
        defects.append({"code": "machine_content", "detail": content_status})

    if isinstance(rights_status, str) and "unconfirmed" in rights_status:
        defects.append({"code": "rights_unconfirmed", "detail": rights_status})

    if m3_gate_profile == "structural_only":
        defects.append(
            {"code": "semantic_not_evaluated", "detail": "m3 gate_profile=structural_only"}
        )

    return sorted(defects, key=lambda item: item["code"])


def build_release_manifest(
    *,
    release_id,
    admission,
    release_scope,
    technique_id,
    packs,
    input_reconciliation,
    schema_versions,
    min_app_version,
    known_defects,
    watermark_text,
):
    """编译 ReleaseManifest（D7、§16:697）。

    返回 ``{"manifest", "bytes", "sha256", "canonical_hash"}``。
    """
    # M1：fail-closed
    ids.validate("release_id", release_id)
    if (
        admission.get("admitted") is not True
        or admission.get("consumption_level") not in SUPPORTED_LEVELS
    ):
        raise DatasetRefused(
            "未准入或消费级别不受支持，fail-closed 拒绝（D12）", code="SCH_002"
        )

    # M2：pack_type 唯一、sha256 合法、按 pack_type 排序
    seen_types = set()
    for item in packs:
        if item["pack_type"] in seen_types:
            raise DuplicateIdentifier(
                "pack_type 重复: %s" % item["pack_type"], code="ID_002"
            )
        seen_types.add(item["pack_type"])
        if _SHA256_RE.match(str(item["sha256"])) is None:
            raise SchemaViolation(
                "pack sha256 格式非法: %r" % (item["sha256"],), code="SCH_002"
            )
    sorted_packs = sorted(packs, key=lambda item: item["pack_type"])

    # M3：canonical_hash
    canonical_hash = sha256_hex(
        canonical_bytes(
            [[item["pack_type"], item["sha256"]] for item in sorted_packs]
        )
    )

    # M4：水印
    if admission["watermark_required"] and not watermark_text:
        raise SchemaViolation("watermark.required 为真但 text 为空", code="SCH_001")
    watermark = {
        "required": admission["watermark_required"],
        "text": watermark_text,
    }

    # M5：组装
    manifest = {
        "manifest_type": "release_manifest",
        "schema_version": SUB_PACK_SCHEMA_VERSION,
        "release_id": release_id,
        "consumption_level": admission["consumption_level"],
        "source_release": admission["source_release"],
        "release_scope": release_scope,
        "technique_id": technique_id,
        "technique_profile_version": None,
        "schema_versions": schema_versions,
        "packs": sorted_packs,
        "canonical_hash": canonical_hash,
        "input_reconciliation": sorted(
            input_reconciliation, key=lambda item: item["artifact_revision_id"]
        ),
        "min_app_version": min_app_version,
        "watermark": watermark,
        "isolation": admission["isolation"],
        "completeness_claim": "partial",
        "authoritative": False,
        "known_defects": known_defects,
        "retired_anchors": [],
    }
    data = canonical_bytes(manifest)
    return {
        "manifest": manifest,
        "bytes": data,
        "sha256": sha256_hex(data),
        "canonical_hash": canonical_hash,
    }


def build_graph_projection_pack(
    *,
    release_id,
    canonical_hash,
    consumption_level,
    nodes=None,
    edges=None,
    knowledge_data=None,
):
    """编译 GraphProjectionPack（规格 §16:725，INTERFACES §3.15，裁决 107 Q-M8-05）。

    纯函数：可从 KnowledgeDataPack 结构同构映射，或由 nodes/edges 显式输入。
    返回 ``{"pack", "bytes", "sha256"}``。
    """
    ids.validate("release_id", release_id)
    if _SHA256_RE.match(str(canonical_hash)) is None:
        raise SchemaViolation(
            "canonical_hash 格式非法（需 64 位十六进制）: %r" % (canonical_hash,),
            code="SCH_002",
        )
    if consumption_level not in CONSUMPTION_LEVELS:
        raise SchemaViolation(
            "consumption_level 非法: %r" % (consumption_level,), code="SCH_002"
        )

    # 实体提取：若传入 knowledge_data，从中同构提取节点与关系边
    extracted_nodes = []
    extracted_edges = []
    if knowledge_data is not None:
        for c in knowledge_data.get("concepts", []):
            extracted_nodes.append({
                "node_id": c["concept_id"],
                "kind": "concept",
                "label": c.get("name") or c.get("canonical_name") or c.get("label", ""),
                "content_status": c.get("content_status", "machine_extracted"),
            })
        for a in knowledge_data.get("assertions", []):
            extracted_nodes.append({
                "node_id": a["assertion_id"],
                "kind": "assertion",
                "label": a.get("proposition") or a.get("label", ""),
                "content_status": a.get("content_status") or a.get("status", "machine_extracted"),
            })
            if a.get("subject_entity_id") and a["subject_entity_id"].startswith("co_"):
                extracted_edges.append({
                    "source": a["assertion_id"],
                    "relation": "belongs_to_concept",
                    "target": a["subject_entity_id"],
                    "content_status": a.get("content_status") or a.get("status", "machine_extracted"),
                })
            for cid in a.get("concept_refs", []):
                extracted_edges.append({
                    "source": a["assertion_id"],
                    "relation": "belongs_to_concept",
                    "target": cid,
                    "content_status": a.get("content_status") or a.get("status", "machine_extracted"),
                })
        for p in knowledge_data.get("patterns", []):
            extracted_nodes.append({
                "node_id": p["pattern_id"],
                "kind": "pattern",
                "label": p.get("name") or p.get("label", ""),
                "content_status": p.get("content_status", "machine_extracted"),
            })
            for aid in p.get("assertion_ids", []):
                extracted_edges.append({
                    "source": p["pattern_id"],
                    "relation": "has_assertion",
                    "target": aid,
                    "content_status": p.get("content_status", "machine_extracted"),
                })
        for sv in knowledge_data.get("school_views", []):
            extracted_nodes.append({
                "node_id": sv["school_view_id"],
                "kind": "school_view",
                "label": sv.get("label") or sv["school_view_id"],
                "content_status": sv.get("content_status", "machine_extracted"),
            })
            if sv.get("conflict_group_id"):
                extracted_edges.append({
                    "source": sv["school_view_id"],
                    "relation": "in_conflict_group",
                    "target": sv["conflict_group_id"],
                    "content_status": sv.get("content_status", "machine_extracted"),
                })

    all_nodes = list(extracted_nodes)
    if nodes is not None:
        all_nodes.extend(nodes)

    all_edges = list(extracted_edges)
    if edges is not None:
        all_edges.extend(edges)

    # 节点校验与去重
    seen_nodes = set()
    validated_nodes = []
    for node in all_nodes:
        if not isinstance(node, dict):
            raise SchemaViolation("node 必须为字典对象", code="SCH_002")
        nid = node.get("node_id")
        _validate_node_id(nid)
        if nid in seen_nodes:
            raise DuplicateIdentifier("node_id 重复: %s" % (nid,), code="ID_002")
        seen_nodes.add(nid)
        kind = node.get("kind")
        if kind not in GRAPH_NODE_KINDS:
            raise SchemaViolation(
                "node kind 非法: %r（闭集 %r）" % (kind, GRAPH_NODE_KINDS), code="SCH_002"
            )
        status = node.get("content_status", "machine_extracted")
        if status not in CONTENT_STATUSES:
            raise SchemaViolation("node content_status 非法: %r" % (status,), code="SCH_002")
        watermark = node.get("watermark")
        if watermark is None:
            watermark = (consumption_level == "INTERNAL_DEMO" and status.startswith("machine_"))
        else:
            watermark = bool(watermark)
        out_node = {
            "node_id": nid,
            "kind": kind,
            "label": node.get("label", ""),
            "content_status": status,
            "watermark": watermark,
        }
        if "properties" in node:
            out_node["properties"] = dict(node["properties"])
        validated_nodes.append(out_node)

    # 边校验与去重（【I-10】/P8/第 107 条 Q-M8-05：无独立 ID，身份为三元组）
    seen_edges = set()
    validated_edges = []
    for edge in all_edges:
        if not isinstance(edge, dict):
            raise SchemaViolation("edge 必须为字典对象", code="SCH_002")
        if "edge_id" in edge or "id" in edge:
            raise SchemaViolation(
                "边禁止包含 edge_id 或 id（【I-10】身份由三元组确定）", code="SCH_002"
            )
        src = edge.get("source")
        rel = edge.get("relation")
        tgt = edge.get("target")
        _validate_node_id(src)
        _validate_node_id(tgt)
        if rel not in GRAPH_RELATIONS:
            raise SchemaViolation(
                "edge relation 非法: %r（闭集 %r）" % (rel, GRAPH_RELATIONS), code="SCH_002"
            )
        triple = (src, rel, tgt)
        if triple in seen_edges:
            raise DuplicateIdentifier("edge 三元组重复: %r" % (triple,), code="ID_002")
        seen_edges.add(triple)
        status = edge.get("content_status", "machine_extracted")
        if status not in CONTENT_STATUSES:
            raise SchemaViolation("edge content_status 非法: %r" % (status,), code="SCH_002")
        watermark = edge.get("watermark")
        if watermark is None:
            watermark = (consumption_level == "INTERNAL_DEMO" and status.startswith("machine_"))
        else:
            watermark = bool(watermark)
        validated_edges.append({
            "source": src,
            "relation": rel,
            "target": tgt,
            "content_status": status,
            "watermark": watermark,
        })

    # 确定性排序：nodes 按 node_id 升序，edges 按 (source, relation, target) 字典序升序
    validated_nodes.sort(key=lambda n: n["node_id"])
    validated_edges.sort(key=lambda e: (e["source"], e["relation"], e["target"]))

    pack = {
        "schema_version": GRAPH_PROJECTION_SCHEMA_VERSION,
        "release_id": release_id,
        "canonical_hash": canonical_hash,
        "consumption_level": consumption_level,
        "nodes": validated_nodes,
        "edges": validated_edges,
        "node_count": len(validated_nodes),
        "edge_count": len(validated_edges),
    }
    data = canonical_bytes(pack)
    return {
        "pack": pack,
        "bytes": data,
        "sha256": sha256_hex(data),
    }


def build_knowledge_data_pack(
    *,
    snapshot_knowledge,
    entry_id_allocation,
    release_id,
    consumption_level,
    technique_id,
):
    """编译 KnowledgeDataPack 与知识链前三段（第 107 条 Q-M8-01/Q-M8-02）。

    主体双轨、**不推断**（Q-M8-01）：
    - Pattern 词条的 ``assertion_ids`` 取 Snapshot 中该 Pattern 已审定的
      ``assertion_ids``（显式引用）；
    - Concept 词条取断言上**显式引用**该 Concept 的 ``concept_refs``
      （Snapshot 中已有的显式字段；无此字段即视为无显式引用，不推断）。

    无主体 assertion 不生成 entry，逐条返回 ``assertion_without_subject``，
    供 ``known_defects`` 按 INTERFACES §3.8 口径写入；每个 entry 的
    ``assertion_ids`` 至少 1 条，否则该主体不生成 entry（返回
    ``subjects_without_entry``）。

    ``entry_id`` 只从传入的 ``entry_id_allocation`` 取（Q-M8-02）：纯函数层
    禁止随机发号（发号见 ``entry_ids`` 模块）；主体缺号抛 ``SchemaViolation(ID_001)``。

    返回 ``{"pack", "bytes", "sha256", "assertion_without_subject",
    "subjects_without_entry", "evidence_chains"}``。
    """
    if consumption_level not in CONSUMPTION_LEVELS:
        raise SchemaViolation(
            "consumption_level 非法: %r" % (consumption_level,), code="SCH_002"
        )
    ids.validate("release_id", release_id)
    if not isinstance(snapshot_knowledge, dict):
        raise SchemaViolation("snapshot_knowledge 必须为字典", code="SCH_002")
    if not isinstance(entry_id_allocation, dict):
        raise SchemaViolation("entry_id_allocation 必须为字典", code="SCH_002")

    # K1：显式引用收集（双轨，不推断）
    # 轨道一：Pattern 的 assertion_ids（Snapshot 显式字段）
    pattern_assertions = {}
    pattern_names = {}
    for pat in snapshot_knowledge.get("patterns", []):
        pat_id = pat.get("pattern_id")
        if pat_id is None:
            continue
        ids.validate("pattern_id", pat_id)
        pattern_names[pat_id] = pat.get("name") or pat_id
        aids = pat.get("assertion_ids") or []
        if not isinstance(aids, list):
            raise SchemaViolation(
                "pattern.assertion_ids 必须为列表: %s" % pat_id, code="SCH_002"
            )
        pattern_assertions.setdefault(pat_id, set()).update(aids)

    # 轨道二：assertion.concept_refs（Snapshot 显式字段；缺字段即无引用）
    concept_assertions = {}
    assertion_ids = set()
    for a in snapshot_knowledge.get("assertions", []):
        aid = a["assertion_id"]
        ids.validate("assertion_id", aid)
        assertion_ids.add(aid)
        for cid in a.get("concept_refs") or []:
            # 引用目标必须真实存在（显式引用悬空属数据缺陷，fail-closed）
            known = any(
                c.get("concept_id") == cid
                for c in snapshot_knowledge.get("concepts", [])
            )
            if not known:
                raise MissingReference(
                    "assertion.concept_refs 悬空: %s -> %s" % (aid, cid),
                    code="REF_001",
                )
            concept_assertions.setdefault(cid, set()).add(aid)

    # K2：主体集合（双轨闭集）与缺号检查（缺号抛错，不得临时生成）。
    # 零断言主体出不了 entry（不占号），只进 subjects_without_entry。
    subjects_without_entry = []
    subjects = {}
    for pat_id in sorted(pattern_assertions):
        if pattern_assertions[pat_id]:
            subjects[pat_id] = sorted(pattern_assertions[pat_id])
    for cid in sorted(concept_assertions):
        if concept_assertions[cid]:
            subjects[cid] = sorted(concept_assertions[cid])
    subjects_without_entry.extend(
        sorted(
            pat_id
            for pat_id, aids in pattern_assertions.items()
            if not aids and pat_id not in subjects
        )
    )

    missing = sorted(
        subject for subject in subjects if subject not in entry_id_allocation
    )
    if missing:
        raise SchemaViolation(
            "entry_id_allocation 缺主体发号（不得临时生成）: %s" % ", ".join(missing),
            code="ID_001",
        )

    # K3：逐主体编词条；无主体 assertion 与零断言主体如实返回
    watermark = (
        INTERNAL_DEMO_WATERMARK if consumption_level == "INTERNAL_DEMO" else None
    )
    entries = []
    assertion_out = []
    school_view_ids = []
    evidence_chains = []
    assertions_by_id = {
        a["assertion_id"]: a for a in snapshot_knowledge.get("assertions", [])
    }
    for a in snapshot_knowledge.get("assertions", []):
        assertion_out.append(
            {
                "assertion_id": a["assertion_id"],
                "proposition": a["proposition"],
                "subject_entity_id": a.get("subject_entity_id"),
                "status": a["content_status"],
            }
        )

    for subject in sorted(subjects):
        entry_id = entry_id_allocation[subject]
        ids.validate("entry_id", entry_id)
        entry_assertion_ids = subjects[subject]
        if not entry_assertion_ids:
            subjects_without_entry.append(subject)
            continue
        for aid in entry_assertion_ids:
            if aid not in assertion_ids:
                raise MissingReference(
                    "主体 %s 引用悬空断言: %s" % (subject, aid), code="REF_001"
                )
        assertion = assertions_by_id[entry_assertion_ids[0]]
        school_ids = sorted(
            {
                sv
                for aid in entry_assertion_ids
                for sv in (assertions_by_id[aid].get("school_view_ids") or [])
            }
        )
        entry = {
            "entry_id": entry_id,
            "subject_entity_id": subject,
            "title": pattern_names.get(subject, subject),
            "assertion_ids": entry_assertion_ids,
            "school_view_ids": school_ids,
            "content_status": assertion["content_status"],
            "mark_binding": None,
        }
        entries.append(entry)
        school_view_ids.extend(sv for sv in school_ids if sv not in school_view_ids)
        for aid in entry_assertion_ids:
            a = assertions_by_id[aid]
            for ev in a.get("evidence") or []:
                # I-11：Snapshot evidence 的偏移为绝对偏移，逐字透传不加减
                evidence_chains.append(
                    {
                        "entry_id": entry_id,
                        "assertion_id": aid,
                        "evidence_link": {
                            "source_span_id": ev["source_span_id"],
                            "start_offset": ev["start_offset"],
                            "end_offset": ev["end_offset"],
                            "quote_sha256": ev["quote_sha256"],
                        },
                    }
                )

    # 无主体断言：显式引用（pattern 归属）与 concept_refs 均没有 → 不生成 entry
    assertion_without_subject = []
    referenced = set()
    for aids in pattern_assertions.values():
        referenced.update(aids)
    for aids in concept_assertions.values():
        referenced.update(aids)
    for aid in sorted(assertion_ids - referenced):
        assertion_without_subject.append(aid)

    pack = {
        "pack_type": "knowledge_data_pack",
        "schema_version": SUB_PACK_SCHEMA_VERSION,
        "release_id": release_id,
        "technique_id": technique_id,
        "consumption_level": consumption_level,
        "watermark": watermark,
        "entries": entries,
        "concepts": [
            {
                "concept_id": c["concept_id"],
                "name": c.get("name") or c.get("canonical_name") or c["concept_id"],
                "basic_imagery": None,
            }
            for c in sorted(
                snapshot_knowledge.get("concepts", []),
                key=lambda c: c["concept_id"],
            )
        ],
        "assertions": assertion_out,
        "school_views": [
            {
                "school_view_id": sv["school_view_id"],
                "school_id": sv["school_id"],
                "subject_entity_id": sv.get("subject_entity_id"),
                "conflict_group_id": sv.get("conflict_group_id"),
                "claim_refs": sv.get("claim_refs") or [],
                "changes_current_judgment": sv["changes_current_judgment"],
                "content_status": sv["content_status"],
            }
            for sv in sorted(
                snapshot_knowledge.get("school_views", []),
                key=lambda sv: sv["school_view_id"],
            )
        ],
        "conflict_groups": [
            {
                "conflict_group_id": cg["conflict_group_id"],
                "school_view_ids": cg.get(
                    "member_school_view_ids", cg.get("school_view_ids", [])
                ),
                "first_layer_display": bool(cg.get("first_layer_display")),
            }
            for cg in sorted(
                snapshot_knowledge.get("conflict_groups", []),
                key=lambda cg: cg["conflict_group_id"],
            )
        ],
    }
    data = canonical_bytes(pack)
    return {
        "pack": pack,
        "bytes": data,
        "sha256": sha256_hex(data),
        "assertion_without_subject": assertion_without_subject,
        "subjects_without_entry": subjects_without_entry,
        "evidence_chains": evidence_chains,
    }


def build_evidence_chain(
    *,
    entry_id,
    assertion_id,
    evidence_link,
    source_span,
    source_anchor,
    evidence_level,
    release_policy="derived_page_images_only",
    ocr_page=None,
    text_mapping=None,
    source_asset=None,
):
    """构建固定七段证据链条目（规格 §16:705-712，INTERFACES §3.10，裁决 107 Q-M8-03/Q-M8-07）。

    每条 chain 必须恰含 7 个键。
    在 reference_and_hash_only 下，evidence_link.quote 与 source_span.text 必须置为 null。
    """
    if evidence_level not in EVIDENCE_LEVELS:
        raise SchemaViolation("evidence_level 非法: %r" % (evidence_level,), code="SCH_002")
    if release_policy not in ("derived_page_images_only", "reference_and_hash_only", "full_scan"):
        raise SchemaViolation("release_policy 非法: %r" % (release_policy,), code="SCH_002")

    ids.validate("entry_id", entry_id)
    ids.validate("assertion_id", assertion_id)

    if not isinstance(evidence_link, dict):
        raise SchemaViolation("evidence_link 必须为字典", code="SCH_002")
    quote_hash = evidence_link.get("quote_sha256")
    if not quote_hash:
        raise SchemaViolation("evidence_link 缺少 quote_sha256", code="SCH_002")
    quote = None if release_policy == "reference_and_hash_only" else evidence_link.get("quote")
    link_out = {
        "assertion_id": assertion_id,
        "source_span_id": evidence_link["source_span_id"],
        "start_offset": evidence_link["start_offset"],
        "end_offset": evidence_link["end_offset"],
        "quote": quote,
        "quote_sha256": quote_hash,
    }

    if not isinstance(source_span, dict):
        raise SchemaViolation("source_span 必须为字典", code="SCH_002")
    text = None if release_policy == "reference_and_hash_only" else source_span.get("text")
    span_out = {
        "source_span_id": source_span["source_span_id"],
        "source_id": source_span["source_id"],
        "page": source_span.get("page"),
        "start_offset": source_span["start_offset"],
        "end_offset": source_span["end_offset"],
        "text": text,
    }

    if not isinstance(source_anchor, dict):
        raise SchemaViolation("source_anchor 必须为字典", code="SCH_002")
    anchor_out = dict(source_anchor)

    chain = {
        "entry_id": entry_id,
        "assertion_id": assertion_id,
        "evidence_link": link_out,
        "source_span": span_out,
        "source_anchor": anchor_out,
    }

    if evidence_level == "glyphbox_level":
        if not isinstance(ocr_page, dict):
            raise SchemaViolation("glyphbox_level 必须提供 ocr_page 字典", code="SCH_002")
        if not isinstance(source_asset, dict):
            raise SchemaViolation("glyphbox_level 必须提供 source_asset 字典", code="SCH_002")
        chain["ocr_page"] = {
            "page": ocr_page["page"],
            "glyph_ids": list(ocr_page["glyph_ids"]),
        }
        chain["source_asset"] = {
            "page": source_asset["page"],
            "image_sha256": source_asset.get("image_sha256") or source_asset.get("sha256"),
        }
    elif evidence_level == "offset_level":
        if not isinstance(text_mapping, dict):
            raise SchemaViolation("offset_level 必须提供 text_mapping 字典", code="SCH_002")
        if not isinstance(source_asset, dict):
            raise SchemaViolation("offset_level 必须提供 source_asset 字典", code="SCH_002")
        required_tm_fields = (
            "raw_text_revision_id",
            "cleaned_text_revision_id",
            "patch_set_revision_id",
            "raw_start",
            "raw_end",
        )
        for f in required_tm_fields:
            if f not in text_mapping:
                raise SchemaViolation("text_mapping 缺少字段: %s" % (f,), code="SCH_002")
        chain["text_mapping"] = {
            "raw_text_revision_id": text_mapping["raw_text_revision_id"],
            "cleaned_text_revision_id": text_mapping["cleaned_text_revision_id"],
            "patch_set_revision_id": text_mapping["patch_set_revision_id"],
            "raw_start": text_mapping["raw_start"],
            "raw_end": text_mapping["raw_end"],
        }
        chain["source_asset"] = {
            "page": source_asset.get("page"),
            "sha256": source_asset.get("sha256") or source_asset.get("image_sha256"),
        }

    return chain
