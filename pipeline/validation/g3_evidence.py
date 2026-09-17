"""G3 身份、引用与证据锚点 Validator（规格 §13.1 G3）。

本模块**严禁 import M3 编译包**，一律独立重算；只读冻结上下文，不做任何
写入。五项 Validator 统一返回 ``{"findings": [...], "checked": {...}}``；
引用类发现的 ``relation`` 取 ``artifact_ref``（含 from_id/to_id 语义），
供 ``gate_results.broken_relations`` 汇总。
"""

import hashlib
import re

from pipeline.ledger import ids

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

# offset 档 source_anchor 的 7 个键（第 78 条；键序与 make_offset_anchor 一致）
_OFFSET_ANCHOR_KEYS = (
    "raw_text_revision_id",
    "raw_start",
    "raw_end",
    "cleaned_text_revision_id",
    "start_offset",
    "end_offset",
    "quote_sha256",
)

# offset 档片段 ID 的起点偏移段（唯一权威出处为 pipeline.ledger.ids，第 102 条）
_SPAN_ID_OFFSET_PARTS = re.compile(ids.SOURCE_SPAN_ID_OFFSET_PARTS)

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


def _is_offset(ctx):
    """证据级别是否为电子文本档 ``offset_level``（R83，第 100 条 D5）。"""
    return (ctx.get("spans_doc") or {}).get("evidence_level") == "offset_level"


def _map_raw_offset(ordered_patches, position, is_end):
    """把 RawText 偏移换算为 CleanedText 偏移（本模块独立实现，不 import M3）。

    语义与 ``DeterministicPatchSet`` 的确定性换算一致：补丁内按长度比例取整，
    补丁之间的未改动区段按原始长度平移。此处**独立书写**（与 ``gate_offset``
    同一纪律），保证判定不与生产代码同错同过（第 88 条）。
    """
    if not ordered_patches:
        return position
    if position < ordered_patches[0]["raw_start"]:
        return position

    for index, patch in enumerate(ordered_patches):
        raw_start = patch["raw_start"]
        raw_end = patch["raw_end"]
        cleaned_start = patch["cleaned_start"]
        cleaned_end = patch["cleaned_end"]

        if position < raw_start:
            previous = ordered_patches[index - 1]
            return previous["cleaned_end"] + (position - previous["raw_end"])
        if raw_start <= position <= raw_end:
            if raw_start == raw_end:
                return cleaned_start if is_end else cleaned_end
            if position == raw_start:
                return cleaned_start
            if position == raw_end:
                return cleaned_end
            raw_len = raw_end - raw_start
            cleaned_len = cleaned_end - cleaned_start
            if cleaned_len == 0:
                return cleaned_start
            if raw_len == cleaned_len:
                return cleaned_start + (position - raw_start)
            return cleaned_start + round(
                (position - raw_start) * cleaned_len / raw_len
            )

    last = ordered_patches[-1]
    return last["cleaned_end"] + (position - last["raw_end"])


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

    offset 档（R83）改用 ``pipeline.ledger.ids`` 校验片段 ID 的偏移形态（第 102
    条：不许自带正则），并核对 ID 起点偏移段与锚点 ``raw_start`` 一致
    （``anchor_offset_mismatch``，REF_001）。
    """
    if _is_offset(ctx):
        return _validate_text_span_identity(ctx)

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


def _validate_text_span_identity(ctx):
    """offset 档片段身份：ids 权威正则、全局唯一、work 段与锚点起点偏移。"""
    spans_doc = ctx.get("spans_doc") or {}
    spans = spans_doc.get("spans") or []
    manifest = ctx.get("manifest") or {}
    spans_rev = ctx.get("corpus_spans_revision_id")
    declared_work = spans_doc.get("work")
    findings = []
    seen = set()

    for span in spans:
        span_id = span.get("span_id")
        subject = _subject(span_id, spans_rev)
        match = (
            _SPAN_ID_OFFSET_PARTS.match(span_id)
            if isinstance(span_id, str)
            else None
        )
        if match is None:
            findings.append(
                make_finding(
                    "g3_span_identity", "G3", "span_id_format", "ID_001",
                    _ERROR, subject,
                    detail="offset 档 span_id 格式非法: %r" % (span_id,),
                )
            )
            continue
        if span_id in seen:
            findings.append(
                make_finding(
                    "g3_span_identity", "G3", "span_id_duplicate", "ID_002",
                    _ERROR, subject, detail="span_id 重复: %s" % span_id,
                )
            )
        else:
            seen.add(span_id)

        work_seg, _edition, offset_seg = match.groups()
        if declared_work and work_seg != declared_work:
            findings.append(
                make_finding(
                    "g3_span_identity", "G3", "source_id_mismatch", "REF_001",
                    _ERROR, subject,
                    detail="span_id 的 work 段 %r 与文档 work %r 不符"
                    % (work_seg, declared_work),
                )
            )
        anchor = span.get("source_anchor") or {}
        anchor_raw_start = anchor.get("raw_start") if isinstance(anchor, dict) else None
        if isinstance(anchor_raw_start, int) and anchor_raw_start != int(offset_seg):
            findings.append(
                make_finding(
                    "g3_span_identity", "G3", "anchor_offset_mismatch", "REF_001",
                    _ERROR, subject,
                    detail="span_id 起点偏移段 %s 与 source_anchor.raw_start %d 不符"
                    % (offset_seg, anchor_raw_start),
                )
            )

    declared_source = spans_doc.get("source_id")
    manifest_source = manifest.get("source_id")
    if declared_source != manifest_source:
        findings.append(
            make_finding(
                "g3_span_identity", "G3", "source_id_mismatch", "REF_001",
                _ERROR, _subject(spans_rev, spans_rev),
                detail="spans source_id %r != manifest.source_id %r"
                % (declared_source, manifest_source),
            )
        )

    content_status = spans_doc.get("content_status")
    if content_status not in _CONTENT_STATUSES:
        findings.append(
            make_finding(
                "g3_span_identity", "G3", "content_status_invalid", "SCH_002",
                _ERROR, _subject(spans_rev, spans_rev),
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

    offset 档（R83）以冻结 ``cleaned_text`` 为全文逐片段独立复算，并按
    ``deterministic_patch_set`` 把锚点的原始偏移映射回清洗偏移核对
    （``raw_anchor_mismatch``，TXT_001）；锚点修订号必须指向本次冻结的
    ``raw_text``/``cleaned_text_revision``（``anchor_revision_mismatch``，REF_001）。
    """
    if _is_offset(ctx):
        return _validate_text_strict_offset_quote(ctx)

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


def _validate_text_strict_offset_quote(ctx):
    """offset 档逐片段复算：cleaned 偏移、quote sha256、patch 映射与锚点修订号。"""
    spans = (ctx.get("spans_doc") or {}).get("spans") or []
    cleaned_text = ctx.get("cleaned_text")
    raw_text = ctx.get("raw_text")
    patches = ctx.get("patches") or []
    m3_rev = (ctx.get("m3_package") or {}).get("artifact_revision_id")
    raw_text_revision_id = ctx.get("raw_text_revision_id")
    cleaned_text_revision_id = ctx.get("cleaned_text_revision_id")
    findings = []
    any_quote = False

    if not isinstance(cleaned_text, str):
        findings.append(
            make_finding(
                "g3_strict_offset_quote", "G3", "offset_out_of_range", "TXT_001",
                _ERROR, _subject(m3_rev or "corpus_spans", m3_rev),
                detail="冻结 cleaned_text 对象不可读，无法复算片段偏移",
            )
        )
        return {"findings": findings, "checked": {"spans": len(spans)}}

    ordered_patches = sorted(patches, key=lambda patch: patch.get("raw_start", 0))

    for span in spans:
        start = span.get("start_offset")
        end = span.get("end_offset")
        subject = _subject(span.get("span_id"), cleaned_text_revision_id)
        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or start < 0
            or end > len(cleaned_text)
            or start > end
        ):
            findings.append(
                make_finding(
                    "g3_strict_offset_quote", "G3", "offset_out_of_range", "TXT_001",
                    _ERROR, subject,
                    detail="offset 越界或非法: start=%r end=%r len=%d"
                    % (start, end, len(cleaned_text)),
                )
            )
            continue

        quote = cleaned_text[start:end]
        if quote != span.get("text"):
            findings.append(
                make_finding(
                    "g3_strict_offset_quote", "G3", "offset_mismatch", "TXT_001",
                    _ERROR, subject,
                    detail="cleaned_text[start:end] 与 text 不一致: %r != %r"
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
                        "TXT_001", _ERROR, subject, relation="content_hash",
                        detail="quote_sha256 %r != 复算 %s"
                        % (span.get("quote_sha256"), expected),
                    )
                )

        anchor = span.get("source_anchor") or {}
        if (
            anchor.get("raw_text_revision_id") != raw_text_revision_id
            or anchor.get("cleaned_text_revision_id") != cleaned_text_revision_id
        ):
            findings.append(
                make_finding(
                    "g3_strict_offset_quote", "G3", "anchor_revision_mismatch",
                    "REF_001", _ERROR, subject,
                    detail="锚点修订号 %r/%r != 本次冻结 %r/%r"
                    % (
                        anchor.get("raw_text_revision_id"),
                        anchor.get("cleaned_text_revision_id"),
                        raw_text_revision_id,
                        cleaned_text_revision_id,
                    ),
                )
            )

        raw_start = anchor.get("raw_start")
        raw_end = anchor.get("raw_end")
        if (
            not isinstance(raw_start, int)
            or not isinstance(raw_end, int)
            or not isinstance(raw_text, str)
            or raw_start < 0
            or raw_end < raw_start
            or raw_end > len(raw_text)
        ):
            findings.append(
                make_finding(
                    "g3_strict_offset_quote", "G3", "raw_anchor_mismatch", "TXT_001",
                    _ERROR, subject,
                    detail="原始偏移越界或非法: raw_start=%r raw_end=%r len=%r"
                    % (raw_start, raw_end, len(raw_text) if isinstance(raw_text, str) else None),
                )
            )
            continue

        mapped = (
            _map_raw_offset(ordered_patches, raw_start, is_end=False),
            _map_raw_offset(ordered_patches, raw_end, is_end=True),
        )
        if mapped != (start, end):
            findings.append(
                make_finding(
                    "g3_strict_offset_quote", "G3", "raw_anchor_mismatch", "TXT_001",
                    _ERROR, subject,
                    detail="patches 换算 (%d, %d) 与片段偏移 (%r, %r) 不符"
                    % (mapped[0], mapped[1], start, end),
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

    offset 档（R83）没有扫描页与字框：此处的职责转为**锚点键集诚实性**——每条
    片段的 ``source_anchor`` 必须恰为 7 个偏移键，不得混入字框/图像键（那会是
    对 ``glyphbox_level`` 的虚假声明）。多键与缺键同判 ``anchor_field_missing``。
    """
    if _is_offset(ctx):
        return _validate_text_anchor_keys(ctx)

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


def _validate_text_anchor_keys(ctx):
    """offset 档锚点键集：每条片段的 ``source_anchor`` 恰为 7 个偏移键。"""
    spans = (ctx.get("spans_doc") or {}).get("spans") or []
    spans_rev = ctx.get("corpus_spans_revision_id")
    findings = []

    for span in spans:
        anchor = span.get("source_anchor")
        subject = _subject(span.get("span_id"), spans_rev)
        if not isinstance(anchor, dict):
            findings.append(
                make_finding(
                    "g3_glyphbox_anchor", "G3", "anchor_field_missing", "SCH_001",
                    _ERROR, subject, detail="source_anchor 不是映射",
                )
            )
            continue
        missing = [key for key in _OFFSET_ANCHOR_KEYS if key not in anchor]
        extra = [key for key in anchor if key not in _OFFSET_ANCHOR_KEYS]
        if missing:
            findings.append(
                make_finding(
                    "g3_glyphbox_anchor", "G3", "anchor_field_missing", "SCH_001",
                    _ERROR, subject,
                    detail="offset 档锚点缺键: %s" % ", ".join(missing),
                )
            )
        if extra:
            findings.append(
                make_finding(
                    "g3_glyphbox_anchor", "G3", "anchor_field_missing", "SCH_001",
                    _ERROR, subject,
                    detail="offset 档锚点含非偏移档键（字框/图像）: %s" % ", ".join(sorted(extra)),
                )
            )

    return {
        "findings": findings,
        "checked": {"spans": len(spans), "level": "offset_level"},
    }


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
