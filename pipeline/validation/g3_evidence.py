"""G3 身份、引用与证据锚点 Validator（规格 §13.1 G3）。

本模块**严禁 import M3 编译包**，一律独立重算；只读冻结上下文，不做任何
写入。五项 Validator 统一返回 ``{"findings": [...], "checked": {...}}``；
引用类发现的 ``relation`` 取 ``artifact_ref``（含 from_id/to_id 语义），
供 ``gate_results.broken_relations`` 汇总。
"""

import hashlib
import re

from .findings import make_finding

_ERROR = {"INTERNAL_DEMO": "error", "DEV_SEARCH": "error", "PUBLIC_RELEASE": "error"}
_WARN_ERR_ERR = {
    "INTERNAL_DEMO": "warning",
    "DEV_SEARCH": "error",
    "PUBLIC_RELEASE": "error",
}
_INFO_INFO_ERR = {
    "INTERNAL_DEMO": "info",
    "DEV_SEARCH": "info",
    "PUBLIC_RELEASE": "error",
}

# source_id 与 span_id 各段（独立书写，与 ids.PATTERNS 同一格式）
_SOURCE_ID_RE = re.compile(r"^src_([a-z][a-z0-9]*)_ed([0-9]{2})$")
_SPAN_ID_RE = re.compile(r"^ss_([a-z][a-z0-9]*)_ed([0-9]{2})_p([0-9]{4})_s([0-9]{2})$")
_PAGE_RE = re.compile(r"^page_([0-9]{3,4})$")

# §8.2 内容成熟度状态闭集（7 值）
_CONTENT_STATUSES = (
    "source_verified",
    "machine_extracted",
    "cross_model_reviewed",
    "disputed",
    "needs_expert",
    "expert_verified",
    "deprecated",
)

# §11.1 证据级别闭集
_EVIDENCE_LEVELS = ("offset_level", "glyphbox_level")

# corpus_package 中 *_revision_id 的期望 artifact_type
_CORPUS_PACKAGE_REF_TYPES = {
    "spans_revision_id": "corpus_spans",
    "coverage_report_revision_id": "coverage_report",
}


def _subject(entity_id, revision_id=None, page=None):
    return {
        "entity_id": entity_id,
        "artifact_revision_id": revision_id,
        "page": page,
    }


def _page_block(doc):
    return "\n".join(line["text"] for line in doc.get("lines") or [])


def _page_number(page):
    match = _PAGE_RE.match(page) if isinstance(page, str) else None
    return int(match.group(1)) if match else None


def _box_in_page(box, width, height):
    if not isinstance(box, dict):
        return True
    x = box.get("x")
    y = box.get("y")
    w = box.get("w")
    h = box.get("h")
    if not all(isinstance(value, (int, float)) for value in (x, y, w, h)):
        return True
    if w <= 0 or h <= 0 or x < 0 or y < 0:
        return False
    if width is not None and x + w > width:
        return False
    if height is not None and y + h > height:
        return False
    return True


def validate_span_identity(ctx):
    """Span 身份：格式、全局唯一、页号/行序一致、source_id 与内容成熟度。

    - ``span_id_format``（ID_001）、``span_id_duplicate``（ID_002）、
      ``page_line_mismatch``（REF_001）、``source_id_mismatch``（REF_001）、
      ``content_status_invalid``（SCH_002）。
    """
    spans_doc = ctx.get("spans_doc") or {}
    spans = spans_doc.get("spans") or []
    manifest = ctx.get("manifest") or {}
    page_revs = ctx.get("page_revision_ids") or {}
    findings = []
    seen = set()

    for span in spans:
        span_id = span.get("span_id")
        page = span.get("page")
        subject = _subject(span_id, page_revs.get(page), page)
        match = _SPAN_ID_RE.match(span_id) if isinstance(span_id, str) else None
        if match is None:
            findings.append(
                make_finding(
                    "g3_span_identity", "G3", "span_id_format", "ID_001",
                    _ERROR, subject,
                    detail="span_id 格式非法: %r" % (span_id,),
                )
            )
            continue
        if span_id in seen:
            findings.append(
                make_finding(
                    "g3_span_identity", "G3", "span_id_duplicate", "ID_002",
                    _ERROR, subject,
                    detail="span_id 重复: %s" % span_id,
                )
            )
        else:
            seen.add(span_id)
        _work, _edition, page_str, seq_str = match.groups()
        pnum = _page_number(page)
        if pnum is None or int(page_str) != pnum:
            findings.append(
                make_finding(
                    "g3_span_identity", "G3", "page_line_mismatch", "REF_001",
                    _ERROR, subject,
                    detail="span_id 页号段 %s 与 page %r 不符" % (page_str, page),
                )
            )
        line_index = span.get("line_index")
        if not isinstance(line_index, int) or int(seq_str) != line_index + 1:
            findings.append(
                make_finding(
                    "g3_span_identity", "G3", "page_line_mismatch", "REF_001",
                    _ERROR, subject,
                    detail="span_id 行序段 %s 与 line_index %r 不符"
                    % (seq_str, line_index),
                )
            )

    declared_source = spans_doc.get("source_id")
    manifest_source = manifest.get("source_id")
    if declared_source != manifest_source:
        findings.append(
            make_finding(
                "g3_span_identity", "G3", "source_id_mismatch", "REF_001",
                _ERROR, _subject(ctx.get("corpus_spans_revision_id"),
                                 ctx.get("corpus_spans_revision_id")),
                detail="spans source_id %r != manifest.source_id %r"
                % (declared_source, manifest_source),
            )
        )

    content_status = spans_doc.get("content_status")
    if content_status not in _CONTENT_STATUSES:
        findings.append(
            make_finding(
                "g3_span_identity", "G3", "content_status_invalid", "SCH_002",
                _ERROR, _subject(ctx.get("corpus_spans_revision_id"),
                                 ctx.get("corpus_spans_revision_id")),
                detail="content_status 表外取值: %r" % (content_status,),
            )
        )

    return {
        "findings": findings,
        "checked": {"spans": len(spans), "unique_ids": len(seen)},
    }


def validate_references(ctx):
    """引用闭合：dangling_ref / not_consumable / ref_type_mismatch（均 REF_001）。

    收集 m3 包 ``manifest.input_artifacts``/``output_artifacts`` 与
    ``corpus_package`` 的全部 ``*_revision_id`` 值：修订不存在 → 悬空；存在但
    未 ``sealed`` → 不可消费；引用点期望类型与登记类型不符 → 类型不符。
    """
    m3_package = ctx.get("m3_package") or {}
    corpus_package = ctx.get("corpus_package") or {}
    frozen = (ctx.get("raw") or {}).get("frozen") or {}
    m3_rev = m3_package.get("artifact_revision_id")
    cp_rev = ctx.get("corpus_package_revision_id")
    findings = []

    refs = []
    manifest = m3_package.get("manifest") or {}
    for collection in (
        manifest.get("input_artifacts") or [],
        manifest.get("output_artifacts") or [],
    ):
        for ref in collection:
            refs.append(
                (m3_rev, ref.get("artifact_revision_id"), ref.get("artifact_type"))
            )
    for key, value in corpus_package.items():
        if key.endswith("_revision_id") and isinstance(value, str):
            refs.append((cp_rev, value, _CORPUS_PACKAGE_REF_TYPES.get(key)))

    for from_id, rev, expected_type in refs:
        if not isinstance(rev, str):
            continue
        subject = _subject(from_id, rev)
        if rev not in frozen:
            findings.append(
                make_finding(
                    "g3_references", "G3", "dangling_ref", "REF_001", _ERROR, subject,
                    relation="artifact_ref",
                    detail="引用修订不存在: %s -> %s" % (from_id, rev),
                )
            )
        elif frozen[rev].get("status") != "sealed":
            findings.append(
                make_finding(
                    "g3_references", "G3", "not_consumable", "REF_001", _ERROR, subject,
                    relation="artifact_ref",
                    detail="引用修订未 sealed（%s）: %s -> %s"
                    % (frozen[rev].get("status"), from_id, rev),
                )
            )
        elif expected_type is not None and frozen[rev].get("artifact_type") != expected_type:
            findings.append(
                make_finding(
                    "g3_references", "G3", "ref_type_mismatch", "REF_001", _ERROR,
                    subject, relation="artifact_ref",
                    detail="引用期望类型 %s != 登记 %s: %s -> %s"
                    % (expected_type, frozen[rev].get("artifact_type"), from_id, rev),
                )
            )

    return {"findings": findings, "checked": {"references": len(refs)}}


def validate_strict_offset_quote(ctx):
    """严格 offset 与 quote hash 对账（TXT_001 / SCH_001）。

    逐条 Span：越界 → ``offset_out_of_range``；``block[start:end] != text`` →
    ``offset_mismatch``；Span 自带 ``quote_sha256`` 与复算不符 →
    ``quote_hash_mismatch``；整份未存储任何 quote hash → 恰 1 条
    ``quote_hash_not_stored``（SCH_001，``{warning, error, error}``）。
    """
    spans = (ctx.get("spans_doc") or {}).get("spans") or []
    page_docs = ctx.get("page_docs") or {}
    page_revs = ctx.get("page_revision_ids") or {}
    m3_rev = (ctx.get("m3_package") or {}).get("artifact_revision_id")
    findings = []
    any_quote = False

    for span in spans:
        page = span.get("page")
        block = _page_block(page_docs.get(page) or {"lines": []})
        subject = _subject(span.get("span_id"), page_revs.get(page), page)
        start = span.get("start_offset")
        end = span.get("end_offset")
        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or start < 0
            or end > len(block)
            or start > end
        ):
            findings.append(
                make_finding(
                    "g3_strict_offset_quote", "G3", "offset_out_of_range", "TXT_001",
                    _ERROR, subject,
                    detail="offset 越界或非法: start=%r end=%r len=%d"
                    % (start, end, len(block)),
                )
            )
            continue
        quote = block[start:end]
        if quote != span.get("text"):
            findings.append(
                make_finding(
                    "g3_strict_offset_quote", "G3", "offset_mismatch", "TXT_001",
                    _ERROR, subject,
                    detail="block[start:end] 与 text 不一致: %r != %r"
                    % (quote, span.get("text")),
                )
            )
        if span.get("quote_sha256") is not None:
            any_quote = True
            expected = hashlib.sha256(quote.encode("utf-8")).hexdigest()
            if span.get("quote_sha256") != expected:
                findings.append(
                    make_finding(
                        "g3_strict_offset_quote", "G3", "quote_hash_mismatch",
                        "TXT_001", _ERROR, subject,
                        relation="content_hash",
                        detail="quote_sha256 %r != 复算 %s"
                        % (span.get("quote_sha256"), expected),
                    )
                )

    if not any_quote:
        findings.append(
            make_finding(
                "g3_strict_offset_quote", "G3", "quote_hash_not_stored", "SCH_001",
                _WARN_ERR_ERR, _subject(m3_rev or "m3_package", m3_rev),
                relation="content_hash",
                detail="整份 corpus_spans 未存储任何 quote hash（§11.1）",
            )
        )

    return {"findings": findings, "checked": {"spans": len(spans)}}


def validate_glyphbox_anchor(ctx):
    """字框锚点：页图哈希、行框/字框逐项一致、页内边界与字框文本对齐。

    - ``page_image_hash_mismatch``（SRC_003）、``line_box_mismatch`` /
      ``glyph_box_mismatch`` / ``anchor_out_of_page`` / ``glyph_text_misaligned``
      （TXT_001）、``anchor_field_missing``（SCH_001）。
    """
    spans = (ctx.get("spans_doc") or {}).get("spans") or []
    page_docs = ctx.get("page_docs") or {}
    page_revs = ctx.get("page_revision_ids") or {}
    manifest = ctx.get("manifest") or {}
    assets = {
        item.get("page"): item for item in (manifest.get("source_assets") or [])
    }
    findings = []

    for span in spans:
        page = span.get("page")
        anchor = span.get("source_anchor") or {}
        subject = _subject(span.get("span_id"), page_revs.get(page), page)
        asset = assets.get(page) or {}
        width = asset.get("width")
        height = asset.get("height")

        if anchor.get("image_sha256") != asset.get("sha256"):
            findings.append(
                make_finding(
                    "g3_glyphbox_anchor", "G3", "page_image_hash_mismatch", "SRC_003",
                    _ERROR, subject, relation="anchor_image",
                    detail="source_anchor.image_sha256 与 manifest 资产不符: %s" % page,
                )
            )

        doc = page_docs.get(page) or {}
        lines = doc.get("lines") or []
        line = None
        for candidate in lines:
            if candidate.get("id") == anchor.get("line_id"):
                line = candidate
                break
        if line is None:
            findings.append(
                make_finding(
                    "g3_glyphbox_anchor", "G3", "line_box_mismatch", "TXT_001",
                    _ERROR, subject, relation="anchor_image",
                    detail="line_id %r 不在该页 lines 中" % anchor.get("line_id"),
                )
            )
        else:
            if anchor.get("bbox") != line.get("box"):
                findings.append(
                    make_finding(
                        "g3_glyphbox_anchor", "G3", "line_box_mismatch", "TXT_001",
                        _ERROR, subject, relation="anchor_image",
                        detail="行框与页 JSON line.box 不一致",
                    )
                )
            angle = line.get("angle")
            if angle not in (0, 0.0, None) and not anchor.get("points"):
                findings.append(
                    make_finding(
                        "g3_glyphbox_anchor", "G3", "anchor_field_missing", "SCH_001",
                        _ERROR, subject, relation="anchor_image",
                        detail="行框 angle=%r 且锚点无四点字段" % (angle,),
                    )
                )

        expected_chars = [
            (index, char)
            for index, char in enumerate(doc.get("chars") or [])
            if char.get("parent") == anchor.get("line_id")
        ]
        got_chars = anchor.get("chars") or []
        if len(got_chars) != len(expected_chars):
            findings.append(
                make_finding(
                    "g3_glyphbox_anchor", "G3", "glyph_box_mismatch", "TXT_001",
                    _ERROR, subject, relation="anchor_image",
                    detail="字框数量 %d != 页 JSON %d" % (len(got_chars), len(expected_chars)),
                )
            )
        else:
            for got, (index, expect) in zip(got_chars, expected_chars):
                if (
                    got.get("char_index"),
                    got.get("glyph_id"),
                    got.get("char"),
                    got.get("box"),
                ) != (
                    index,
                    expect.get("id"),
                    expect.get("char"),
                    expect.get("box"),
                ):
                    findings.append(
                        make_finding(
                            "g3_glyphbox_anchor", "G3", "glyph_box_mismatch", "TXT_001",
                            _ERROR, subject, relation="anchor_image",
                            detail="字框锚点与页 JSON chars 不一致: %r" % (got.get("glyph_id"),),
                        )
                    )
                    break

        boxes = [anchor.get("bbox")] + [
            char.get("box") for char in got_chars
        ]
        for box in boxes:
            if not _box_in_page(box, width, height):
                findings.append(
                    make_finding(
                        "g3_glyphbox_anchor", "G3", "anchor_out_of_page", "TXT_001",
                        _ERROR, subject, relation="anchor_image",
                        detail="框越出页宽高: %r（%sx%s）" % (box, width, height),
                    )
                )
                break

        joined = "".join(
            char.get("char") for char in got_chars if char.get("char")
        )
        if joined != (span.get("text") or ""):
            findings.append(
                make_finding(
                    "g3_glyphbox_anchor", "G3", "glyph_text_misaligned", "TXT_001",
                    _WARN_ERR_ERR, subject, relation="anchor_image",
                    detail="字框拼接 %r != Span 文本 %r" % (joined, span.get("text")),
                )
            )

    return {"findings": findings, "checked": {"spans": len(spans)}}


def validate_evidence_level(ctx):
    """证据级别判定（规格 §11.1）。

    - ``offset_level`` → ``evidence_level_insufficient``（``{info, info, error}``）；
    - ``glyphbox_level`` 但某 Span ``source_anchor.chars`` 缺失或为空 →
      ``glyphbox_incomplete``（SCH_001，三级 ``error``）；
    - 表外取值 → ``evidence_level_invalid``（SCH_002）。
    """
    spans_doc = ctx.get("spans_doc") or {}
    spans = spans_doc.get("spans") or []
    level = spans_doc.get("evidence_level")
    page_revs = ctx.get("page_revision_ids") or {}
    spans_rev = ctx.get("corpus_spans_revision_id")
    findings = []

    if level not in _EVIDENCE_LEVELS:
        findings.append(
            make_finding(
                "g3_evidence_level", "G3", "evidence_level_invalid", "SCH_002",
                _ERROR, _subject(spans_rev, spans_rev),
                detail="evidence_level 表外取值: %r" % (level,),
            )
        )
        return {"findings": findings, "checked": {"spans": len(spans), "level": level}}

    if level == "offset_level":
        findings.append(
            make_finding(
                "g3_evidence_level", "G3", "evidence_level_insufficient", "SEM_001",
                _INFO_INFO_ERR, _subject(spans_rev, spans_rev),
                detail="evidence_level=offset_level，PUBLIC_RELEASE 必须 glyphbox_level",
            )
        )
        return {"findings": findings, "checked": {"spans": len(spans), "level": level}}

    for span in spans:
        chars = (span.get("source_anchor") or {}).get("chars")
        if not chars:
            page = span.get("page")
            findings.append(
                make_finding(
                    "g3_evidence_level", "G3", "glyphbox_incomplete", "SCH_001",
                    _ERROR, _subject(span.get("span_id"), page_revs.get(page), page),
                    detail="声明 glyphbox_level 但 source_anchor.chars 为空",
                )
            )

    return {"findings": findings, "checked": {"spans": len(spans), "level": level}}
