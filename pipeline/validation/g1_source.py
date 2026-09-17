"""G1 来源与可重放性 Validator（规格 §13.1 G1）。

本模块**严禁 import M3 编译包**（防止与 M3 同错同过）；重放一致性由
``replay.py`` 独占实现。四项 Validator 只读冻结上下文，不做任何写入，
返回统一结构 ``{"findings": [...], "checked": {...}}``。
"""

import re

from .findings import make_finding

# 三级严重度常量
_ERROR = {"INTERNAL_DEMO": "error", "DEV_SEARCH": "error", "PUBLIC_RELEASE": "error"}
_WARN_ERR_ERR = {
    "INTERNAL_DEMO": "warning",
    "DEV_SEARCH": "error",
    "PUBLIC_RELEASE": "error",
}
_INFO_WARN_ERR = {
    "INTERNAL_DEMO": "info",
    "DEV_SEARCH": "warning",
    "PUBLIC_RELEASE": "error",
}

# 明文中的占位/控制字符：PUA、U+FFFD、□、〓、C0/C1 控制符（不含 \t \n）
_FORBIDDEN_RE = re.compile(
    "[\ue000-\uf8ff\ufffd\u25a1\u3013\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"
)


def _subject(entity_id, revision_id=None, page=None):
    return {
        "entity_id": entity_id,
        "artifact_revision_id": revision_id,
        "page": page,
    }


def _is_offset(ctx):
    """证据级别是否为电子文本档 ``offset_level``（R83，第 100 条 D5）。"""
    return (ctx.get("spans_doc") or {}).get("evidence_level") == "offset_level"


def _frozen(ctx):
    return (ctx.get("raw") or {}).get("frozen") or {}


def validate_frozen_bytes(ctx):
    """校验每个冻结对象的 raw 字节 sha256 与元数据登记 sha256 吻合。

    对象缺失（``actual_sha256``/``doc`` 为 ``None``）判 ``object_missing``
    （SRC_001）；哈希不符判 ``hash_mismatch``（SRC_003）：三级均 ``error``。
    返回额外含 ``fail_closed`` 标志（任一 error 发现即真）。
    """
    frozen = _frozen(ctx)
    findings = []
    for rev in sorted(frozen):
        entry = frozen[rev]
        subject = _subject(rev, rev)
        actual = entry.get("actual_sha256")
        if actual is None or entry.get("doc") is None:
            findings.append(
                make_finding(
                    "g1_frozen_bytes", "G1", "object_missing", "SRC_001",
                    _ERROR, subject,
                    detail="冻结修订 %s 的对象缺失" % rev,
                )
            )
        elif actual != entry.get("sha256"):
            findings.append(
                make_finding(
                    "g1_frozen_bytes", "G1", "hash_mismatch", "SRC_003",
                    _ERROR, subject,
                    detail="冻结修订 %s 对象哈希不符：登记 %s，实得 %s"
                    % (rev, entry.get("sha256"), actual),
                )
            )
    return {
        "findings": findings,
        "checked": {"frozen": len(frozen), "mismatched": len(findings)},
        "fail_closed": bool(findings),
    }


def validate_page_registry(ctx):
    """核对来源登记：页集合、页修订哈希与终态一致性。

    OCR 档（``glyphbox_level``）：
    - 页集合与 manifest 页序不符 → ``page_set_mismatch``（REF_001）；
    - 页修订登记 sha256 与 ``ocr_page_set`` 登记不符 → ``page_hash_mismatch``
      （SRC_003）；
    - ``terminal_states`` 与冻结 ``ocr_page_set.terminal_states`` 不符 →
      ``terminal_state_mismatch``（REF_001）。

    offset 档（``offset_level``，R83）：无 ``ocr_page``，登记单位是 M1
    ``source_manifest`` 的 SourceAsset——
    - ``source_assets[].page`` 集合与 manifest 页序不符 → ``page_set_mismatch``；
    - SourceAsset 声明的 ``normalized_sha256``（M1 契约中指向冻结 RawText 的
      归一化字节哈希，第 94 条 D4）与冻结 ``raw_text`` 修订对象字节实得哈希
      不符（或 ``normalized_sha256`` 缺失时退到 ``sha256``）→
      ``source_asset_mismatch``（SRC_003）。
    """
    if _is_offset(ctx):
        return _validate_text_source_registry(ctx)

    manifest = ctx.get("manifest") or {}
    pages = (manifest.get("edition_part") or {}).get("pages") or []
    ocr_page_set = ctx.get("ocr_page_set") or {}
    ocr_pages = ocr_page_set.get("ocr_pages") or []
    ocr_map = {
        entry.get("page"): entry.get("sha256")
        for entry in ocr_pages
        if isinstance(entry, dict)
    }
    page_revs = ctx.get("page_revision_ids") or {}
    frozen = _frozen(ctx)
    findings = []

    manifest_set = set(pages)
    ocr_set = set(ocr_map)
    for page in pages:
        if page not in ocr_set:
            findings.append(
                make_finding(
                    "g1_page_registry", "G1", "page_set_mismatch", "REF_001",
                    _ERROR, _subject(page, page_revs.get(page), page),
                    detail="manifest 页序中的页未登记进 ocr_page_set: %s" % page,
                )
            )
    for page in sorted(ocr_set - manifest_set):
        findings.append(
            make_finding(
                "g1_page_registry", "G1", "page_set_mismatch", "REF_001",
                _ERROR, _subject(page, page_revs.get(page), page),
                detail="ocr_page_set 出现 manifest 页序外的页: %s" % page,
            )
        )

    for page in pages:
        if page not in ocr_map:
            continue
        rev = page_revs.get(page)
        registered = (frozen.get(rev) or {}).get("sha256")
        if registered is not None and registered != ocr_map[page]:
            findings.append(
                make_finding(
                    "g1_page_registry", "G1", "page_hash_mismatch", "SRC_003",
                    _ERROR, _subject(page, rev, page),
                    detail="页 %s 修订登记哈希 %s != ocr_page_set 登记 %s"
                    % (page, registered, ocr_map[page]),
                )
            )

    terminal_states = ctx.get("terminal_states") or {}
    frozen_terminals = ocr_page_set.get("terminal_states") or {}
    for page in sorted(set(terminal_states) | set(frozen_terminals)):
        if terminal_states.get(page) != frozen_terminals.get(page):
            findings.append(
                make_finding(
                    "g1_page_registry", "G1", "terminal_state_mismatch", "REF_001",
                    _ERROR, _subject(page, page_revs.get(page), page),
                    detail="页 %s 终态 %r 与冻结登记 %r 不符"
                    % (page, terminal_states.get(page), frozen_terminals.get(page)),
                )
            )

    return {
        "findings": findings,
        "checked": {"pages": len(pages), "ocr_pages": len(ocr_map)},
    }


def _validate_text_source_registry(ctx):
    """offset 档来源登记：SourceAsset 集合与哈希到冻结 ``raw_text`` 字节。

    证据链（§4.7）：片段 → 清洗文本偏移 → patch 映射 → 原始文本偏移 →
    **SourceAsset SHA-256**。末端一环即此处复算：M1 冻结的 ``raw_text`` 修订
    对象字节实得哈希，必须等于 ``source_manifest.source_assets`` 声明的归一化
    哈希（``normalized_sha256``；缺失时退到 ``sha256``）。
    """
    manifest = ctx.get("manifest") or {}
    pages = (manifest.get("edition_part") or {}).get("pages") or []
    assets = [item for item in (manifest.get("source_assets") or []) if isinstance(item, dict)]
    raw_text_revision_id = ctx.get("raw_text_revision_id")
    entry = _frozen(ctx).get(raw_text_revision_id) or {}
    actual_sha256 = entry.get("actual_sha256")
    findings = []

    asset_pages = {asset.get("page") for asset in assets}
    for page in pages:
        if page not in asset_pages:
            findings.append(
                make_finding(
                    "g1_page_registry", "G1", "page_set_mismatch", "REF_001",
                    _ERROR, _subject(page, manifest.get("artifact_revision_id")),
                    detail="manifest 页序中的页未登记 SourceAsset: %s" % page,
                )
            )
    for page in sorted(asset_pages - set(pages), key=str):
        findings.append(
            make_finding(
                "g1_page_registry", "G1", "page_set_mismatch", "REF_001",
                _ERROR, _subject(page, manifest.get("artifact_revision_id")),
                detail="SourceAsset 出现 manifest 页序外的页: %s" % page,
            )
        )

    for asset in assets:
        declared = asset.get("normalized_sha256") or asset.get("sha256")
        if declared is not None and declared == actual_sha256:
            continue
        findings.append(
            make_finding(
                "g1_page_registry", "G1", "source_asset_mismatch", "SRC_003",
                _ERROR, _subject(asset.get("page"), raw_text_revision_id),
                detail="SourceAsset %s 声明哈希 %r != 冻结 raw_text 修订字节 %r"
                % (asset.get("page"), declared, actual_sha256),
            )
        )

    return {
        "findings": findings,
        "checked": {
            "pages": len(pages),
            "source_assets": len(assets),
            "raw_text_revision": raw_text_revision_id,
        },
    }


def validate_content_hashes(ctx):
    """核对内容哈希与 spans 修订指向。

    - m3 StagePackage ``manifest.content_sha256`` 与当前 ``corpus_spans`` 修订
      登记 sha256 不符 → ``content_sha256_mismatch``（SRC_003）；
    - ``corpus_package.spans_revision_id`` 未指向当前 spans 修订 →
      ``spans_revision_mismatch``（REF_001）。
    """
    m3_package = ctx.get("m3_package") or {}
    corpus_package = ctx.get("corpus_package") or {}
    spans_rev = ctx.get("corpus_spans_revision_id")
    frozen = _frozen(ctx)
    findings = []

    registered = (frozen.get(spans_rev) or {}).get("sha256")
    declared = (m3_package.get("manifest") or {}).get("content_sha256")
    m3_rev = m3_package.get("artifact_revision_id")
    if registered is not None and declared != registered:
        findings.append(
            make_finding(
                "g1_content_hashes", "G1", "content_sha256_mismatch", "SRC_003",
                _ERROR, _subject(m3_rev or "m3_package", m3_rev),
                detail="m3 包 content_sha256 %r != corpus_spans 登记 %r"
                % (declared, registered),
            )
        )

    if corpus_package.get("spans_revision_id") != spans_rev:
        cp_rev = ctx.get("corpus_package_revision_id")
        findings.append(
            make_finding(
                "g1_content_hashes", "G1", "spans_revision_mismatch", "REF_001",
                _ERROR, _subject(cp_rev or "corpus_package", cp_rev),
                detail="corpus_package.spans_revision_id %r != 当前 spans 修订 %r"
                % (corpus_package.get("spans_revision_id"), spans_rev),
            )
        )

    return {
        "findings": findings,
        "checked": {"spans_revision": spans_rev},
    }


def validate_unresolved_chars(ctx):
    """检查未决字符：占位/控制符、未识别字框与未人工校对字框。

    - span 文本含 PUA/U+FFFD/``□``/``〓``/控制符 → ``forbidden_char_in_text``
      （TXT_001，三级 ``error``）；
    - 字框 ``status == "unrecognized"`` 或 ``char`` 为空 → ``unresolved_glyph``
      （SRC_001，``{warning, error, error}``），按所属 Span 聚合；
    - 字框 ``status == "pending"`` → ``unproofread_glyphs``（``code=None``，
      ``{info, warning, error}``），按页聚合。
    """
    spans_doc = ctx.get("spans_doc") or {}
    spans = spans_doc.get("spans") or []
    page_docs = ctx.get("page_docs") or {}
    page_revs = ctx.get("page_revision_ids") or {}
    findings = []

    for span in spans:
        text = span.get("text") or ""
        bad = sorted({match.group() for match in _FORBIDDEN_RE.finditer(text)})
        if bad:
            findings.append(
                make_finding(
                    "g1_unresolved_chars", "G1", "forbidden_char_in_text", "TXT_001",
                    _ERROR,
                    _subject(span.get("span_id"), page_revs.get(span.get("page")), span.get("page")),
                    detail="span 文本含占位/控制字符: %s"
                    % ",".join("U+%04X" % ord(ch) for ch in bad),
                )
            )

    line_to_span = {}
    for span in spans:
        anchor = span.get("source_anchor") or {}
        line_to_span[(span.get("page"), anchor.get("line_id"))] = span

    unresolved = {}
    pending = {}
    chars_total = 0
    for page, doc in page_docs.items():
        for char in doc.get("chars") or []:
            chars_total += 1
            status = char.get("status")
            if status == "unrecognized" or char.get("char") in (None, ""):
                span = line_to_span.get((page, char.get("parent")))
                key = span.get("span_id") if span else page
                group = unresolved.setdefault(
                    key, {"page": page, "glyphs": [], "span": span}
                )
                group["glyphs"].append(char.get("id"))
            elif status == "pending":
                pending[page] = pending.get(page, 0) + 1

    unresolved_count = 0
    for key, group in unresolved.items():
        unresolved_count += len(group["glyphs"])
        span = group["span"]
        findings.append(
            make_finding(
                "g1_unresolved_chars", "G1", "unresolved_glyph", "SRC_001",
                _WARN_ERR_ERR,
                _subject(key, page_revs.get(group["page"]), group["page"]),
                detail="字框未识别或字符为空: %s" % ",".join(
                    sorted(str(g) for g in group["glyphs"])
                ),
            )
        )

    pending_total = 0
    for page in sorted(pending):
        count = pending[page]
        pending_total += count
        rev = page_revs.get(page)
        findings.append(
            make_finding(
                "g1_unresolved_chars", "G1", "unproofread_glyphs", None,
                _INFO_WARN_ERR,
                _subject(rev, rev, page),
                detail="页 %s 有 %d 个字框未人工校对" % (page, count),
            )
        )

    return {
        "findings": findings,
        "checked": {
            "spans": len(spans),
            "chars": chars_total,
            "unresolved": unresolved_count,
            "pending": pending_total,
        },
    }
