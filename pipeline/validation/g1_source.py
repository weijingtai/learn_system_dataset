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
# 第 103 条 D1：已知不可解决但如实披露的字符（INTERNAL_DEMO 必须披露）
_WARN_WARN_ERR = {
    "INTERNAL_DEMO": "warning",
    "DEV_SEARCH": "warning",
    "PUBLIC_RELEASE": "error",
}

# M2 清洗报告的「已知不可解决」终态（第 103 条 D1、impl-09 README 权威表）
_KNOWN_UNRESOLVABLE = "known_unresolvable"

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


def _kind_for_forbidden_char(char):
    """禁止字符 → 清洗报告 ``kind``（第 103 条 D1）。

    仅三种字符类别有对应 kind：PUA → ``private_use_area``；U+FFFD →
    ``replacement_char``；C0/C1 控制符（含 DEL）→ ``control_char``。
    ``□``（U+25A1）与 ``〓``（U+3013）在裁决枚举之外，返回 ``None``
    （即无记录可比 → 仍判 ``forbidden_char_in_text``）。

    kind 名与终态名逐字取自第 103 条 D1 与 ``pipeline.digitization``
    常量；``tests/test_g1.py`` 用一条用例把它们钉在
    ``FINDING_KINDS``/``TERMINAL_STATES`` 上，防静默漂移（第 85 条）。
    """
    code = ord(char)
    if 0xE000 <= code <= 0xF8FF:
        return "private_use_area"
    if code == 0xFFFD:
        return "replacement_char"
    if code < 0x20 or code == 0x7F:
        return "control_char"
    return None


def _map_cleaned_offset(ordered_patches, position, is_end):
    """把 CleanedText 偏移逆向换算为 RawText 偏移（本模块独立实现，不 import M3）。

    与 ``g3_evidence._map_raw_offset`` 同一直属纪律（第 88 条）：语义与
    ``DeterministicPatchSet`` 一致，代码独立书写，判定不与生产代码同错同过。
    """
    if not ordered_patches:
        return position
    by_cleaned = sorted(ordered_patches, key=lambda patch: patch["cleaned_start"])
    if position < by_cleaned[0]["cleaned_start"]:
        return position

    for index, patch in enumerate(by_cleaned):
        raw_start = patch["raw_start"]
        raw_end = patch["raw_end"]
        cleaned_start = patch["cleaned_start"]
        cleaned_end = patch["cleaned_end"]

        if position < cleaned_start:
            previous = by_cleaned[index - 1]
            return previous["raw_end"] + (position - previous["cleaned_end"])
        if cleaned_start <= position <= cleaned_end:
            if cleaned_start == cleaned_end:  # 删除：cleaned 侧长度为零
                return raw_start if is_end else raw_end
            if position == cleaned_start:
                return raw_start
            if position == cleaned_end:
                return raw_end
            raw_len = raw_end - raw_start
            cleaned_len = cleaned_end - cleaned_start
            if raw_len == 0:
                return raw_start
            if raw_len == cleaned_len:
                return raw_start + (position - cleaned_start)
            return raw_start + round(
                (position - cleaned_start) * raw_len / cleaned_len
            )

    last = by_cleaned[-1]
    return last["raw_end"] + (position - last["cleaned_end"])


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


def _validate_text_unresolved_chars(ctx):
    """offset 档逐个禁止字符与清洗报告对账（第 103 条 D1）。

    逐字符（不是按 Span 去重）判定，因为证据链要求逐码位对齐原始偏移：
    片段 → 清洗偏移 → patch 映射 → 原始偏移 → ``sanitization_report`` 记录。
    """
    spans = (ctx.get("spans_doc") or {}).get("spans") or []
    cleaned_text = ctx.get("cleaned_text")
    patches = ctx.get("patches") or []
    report = ctx.get("sanitization_report") or {}
    report_findings = report.get("findings") or []
    spans_rev = ctx.get("corpus_spans_revision_id")
    ordered_patches = sorted(patches, key=lambda patch: patch.get("cleaned_start", 0))
    findings = []
    total = 0
    disclosed = 0

    for span in spans:
        text = span.get("text") or ""
        start_offset = span.get("start_offset")
        subject = _subject(span.get("span_id"), spans_rev)
        for match in _FORBIDDEN_RE.finditer(text):
            total += 1
            char = match.group()
            kind = _kind_for_forbidden_char(char)
            cleaned_pos = (
                start_offset + match.start() if isinstance(start_offset, int) else None
            )
            raw_pos = (
                _map_cleaned_offset(ordered_patches, cleaned_pos, is_end=False)
                if cleaned_pos is not None and isinstance(cleaned_text, str)
                else None
            )
            matched = [
                entry
                for entry in report_findings
                if kind is not None
                and isinstance(entry, dict)
                and entry.get("kind") == kind
                and entry.get("terminal_state") == _KNOWN_UNRESOLVABLE
                and isinstance(entry.get("raw_start"), int)
                and isinstance(entry.get("raw_end"), int)
                and raw_pos is not None
                and entry["raw_start"] <= raw_pos < entry["raw_end"]
            ]
            if len(matched) == 1:
                disclosed += 1
                findings.append(
                    make_finding(
                        "g1_unresolved_chars", "G1",
                        "known_unresolvable_char_disclosed", None,
                        _WARN_WARN_ERR, subject,
                        detail="字符 U+%04X（清洗偏移 %r → 原始偏移 %r）已由清洗报告"
                        "如实登记为 known_unresolvable: %s"
                        % (
                            ord(char),
                            cleaned_pos,
                            raw_pos,
                            matched[0].get("finding_id"),
                        ),
                    )
                )
            else:
                findings.append(
                    make_finding(
                        "g1_unresolved_chars", "G1", "forbidden_char_in_text",
                        "TXT_001", _ERROR, subject,
                        detail="字符 U+%04X（清洗偏移 %r → 原始偏移 %r）无合法"
                        " known_unresolvable 登记（kind=%s，匹配 %d 条）"
                        % (ord(char), cleaned_pos, raw_pos, kind, len(matched)),
                    )
                )

    return {
        "findings": findings,
        "checked": {
            "spans": len(spans),
            "forbidden_chars": total,
            "disclosed": disclosed,
        },
    }


def validate_unresolved_chars(ctx):
    """检查未决字符：占位/控制符、未识别字框与未人工校对字框。

    OCR 档（``glyphbox_level``）：
    - span 文本含 PUA/U+FFFD/``□``/``〓``/控制符 → ``forbidden_char_in_text``
      （TXT_001，三级 ``error``）；
    - 字框 ``status == "unrecognized"`` 或 ``char`` 为空 → ``unresolved_glyph``
      （SRC_001，``{warning, error, error}``），按所属 Span 聚合；
    - 字框 ``status == "pending"`` → ``unproofread_glyphs``（``code=None``，
      ``{info, warning, error}``），按页聚合。

    offset 档（第 103 条 D1）：M2 依第 79 条 D4 **有意保留**无法映射的码位，
    故每个禁止字符经 patch 映射换算为原始偏移后，须在冻结
    ``sanitization_report`` 中找到**恰好一条**覆盖该偏移、``kind`` 与字符类别
    相符、``terminal_state == known_unresolvable`` 的发现：
    对上 → ``known_unresolvable_char_disclosed``（``{warning, warning, error}``，
    detail 带 ``finding_id``）；对不上（无记录 / 多条 / kind 不符 / 终态不符）
    → 仍判 ``forbidden_char_in_text`` 三级 ``error``。OCR 档逐字不变。
    """
    if _is_offset(ctx):
        return _validate_text_unresolved_chars(ctx)

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
