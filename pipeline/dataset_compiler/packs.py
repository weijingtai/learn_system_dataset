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

from . import SUB_PACK_SCHEMA_VERSION
from . import SUPPORTED_LEVELS
from .canonical import canonical_bytes, normalized_sha256, quote_sha256, sha256_hex
from .errors import DatasetRefused
from .levels import EVIDENCE_LEVELS

# D10 草案水印文案
INTERNAL_DEMO_WATERMARK = "INTERNAL_DEMO｜机器转录，未经人工校对｜不得作为知识来源或权威依据"

# §16:708-712 的第 4–7 段（SourceSpan→SourceAnchor→OcrPage→SourceAsset）
CHAIN_SEGMENTS = ["SourceSpan", "SourceAnchor", "OcrPage", "SourceAsset"]

# §17.1:843 四个 task（每个 task 一个 m8 Checkpoint）
TASKS = ("source_asset_pack", "evidence_map_pack", "release_manifest", "validation_report")

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PAGE_RE = re.compile(r"^page_([0-9]{3,4})$")
_SPAN_TAIL_RE = re.compile(r"_p([0-9]{4})_s([0-9]{2})$")
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
    """校验并拆解 ``span_id``，返回 ``(页号, 行序)``（§19:882）。"""
    ids.validate("source_span_id", span_id)
    match = _SPAN_TAIL_RE.search(span_id)
    if match is None:
        raise InvalidIdentifier("span_id 缺少页号/行序段: %r" % (span_id,), code="ID_001")
    return int(match.group(1)), int(match.group(2))


def build_source_asset_pack(*, manifest, asset_records):
    """编译 SourceAssetPack（D14、§16:717-723）。

    返回 ``{"pack", "bytes", "sha256"}``。
    """
    # S1：只支持 derived_page_images_only
    if manifest["release_policy"] != "derived_page_images_only":
        raise DatasetRefused(
            "发布策略未实现，需 derived_page_images_only: %r"
            % (manifest["release_policy"],),
            code="SCH_002",
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

    # S3：哈希与尺寸校验
    pages = []
    for page in page_order:
        item = manifest_assets[page]
        record = asset_records[page]
        ids.validate("artifact_revision_id", record["artifact_revision_id"])
        if record["sha256"] != item["sha256"]:
            raise HashMismatch("页 %s 资产哈希不符（SRC_003）" % page, code="SRC_003")
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
        "content_level": manifest["release_policy"],
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
    *, spans_doc, page_docs, ocr_page_revision_ids, source_asset_pack, excluded_pages
):
    """编译 EvidenceMapPack：完整 ``span_id`` 为键，只闭合尾链四段。

    返回 ``{"pack", "bytes", "sha256", "normalized_sha256", "span_keys",
    "highlight_counts", "glyph_count"}``。
    """
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
        "knowledge_chain": "not_compiled",
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


def compute_known_defects(*, evidence_map_pack, m3_gate_profile, rights_status):
    """计算已知缺陷（代码闭集，按 code 字典序）。"""
    defects = []

    excluded_pages = evidence_map_pack.get("excluded_pages") or {}
    if excluded_pages:
        detail = ",".join(
            "%s=%s" % (page, excluded_pages[page]) for page in sorted(excluded_pages)
        )
        defects.append({"code": "excluded_page", "detail": detail})

    line_bbox_ids = [
        span_id
        for span_id, entry in evidence_map_pack["entries"].items()
        if entry["highlight_level"] == "line_bbox"
    ]
    if line_bbox_ids:
        defects.append(
            {"code": "glyph_text_mismatch", "detail": ",".join(line_bbox_ids)}
        )

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
