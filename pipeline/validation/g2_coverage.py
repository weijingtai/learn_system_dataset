"""G2 全书覆盖 Validator（规格 §13.1 G2）。

本模块**严禁 import M3 编译包**，必须独立重算页块、覆盖与批次；只读冻结
上下文，不做任何写入，返回统一结构 ``{"findings": [...], "checked": {...}}``。
"""

from .findings import make_finding

_ERROR = {"INTERNAL_DEMO": "error", "DEV_SEARCH": "error", "PUBLIC_RELEASE": "error"}
_WARN_ERR_ERR = {
    "INTERNAL_DEMO": "warning",
    "DEV_SEARCH": "error",
    "PUBLIC_RELEASE": "error",
}

# §10.1 异常页终态枚举 + 未标注（None，等同 manually_transcribed）
_KNOWN_TERMINAL = (None, "manually_transcribed", "known_unrecognizable")


def _subject(entity_id, revision_id=None, page=None):
    return {
        "entity_id": entity_id,
        "artifact_revision_id": revision_id,
        "page": page,
    }


def _page_block(doc):
    """页块 = 该页 OCR 各行文本以 ``"\\n"`` 连接。"""
    return "\n".join(line["text"] for line in doc.get("lines") or [])


def _is_offset(ctx):
    """证据级别是否为电子文本档 ``offset_level``（R83，第 100 条 D5）。"""
    return (ctx.get("spans_doc") or {}).get("evidence_level") == "offset_level"


def _covered_chars(spans):
    total = 0
    for span in spans:
        start = span.get("start_offset")
        end = span.get("end_offset")
        if isinstance(start, int) and isinstance(end, int) and end > start:
            total += end - start
    return total


def _gaps_and_overlaps(spans):
    """按 ``start_offset`` 顺序独立实算页级缺口与重叠区间（与 M3 同键）。"""
    gaps = []
    overlaps = []
    previous_end = 0
    for span in sorted(spans, key=lambda item: item.get("start_offset", 0)):
        start = span.get("start_offset")
        end = span.get("end_offset")
        if not (isinstance(start, int) and isinstance(end, int)):
            continue
        if start > previous_end:
            gaps.append([previous_end, start])
        elif start < previous_end:
            overlaps.append([start, previous_end])
        previous_end = max(previous_end, end)
    return gaps, overlaps


def _spans_by_page(spans):
    grouped = {}
    for span in spans:
        grouped.setdefault(span.get("page"), []).append(span)
    return grouped


def _manifest_pages(ctx):
    return ((ctx.get("manifest") or {}).get("edition_part") or {}).get("pages") or []


def validate_page_accounting(ctx):
    """覆盖页 ∪ 排除页 == manifest 页序；排除页须有终端状态与人工事件证据。

    - manifest 页序中的页缺页文档 → ``page_missing``（REF_001）；
    - 覆盖页（终态 ``None``/``manually_transcribed``）没有 Span →
      ``page_without_span``（SRC_001）；
    - 排除页（``known_unrecognizable``）无人工事件证据 →
      ``excluded_page_no_evidence``（SEM_001）；
    - ``deferred`` 或表外终态 → ``page_deferred``（REF_001）；
    - Span 引用 manifest 页序外的页 → ``page_unregistered``（REF_001）。

    offset 档（R83）改按 M1 页单位与 m3 ``coverage_report``（OCR 外形）判：
    ``coverage_report.pages`` 的键集必须与 manifest 页序逐一相等，不自造页。
    """
    if _is_offset(ctx):
        return _validate_text_page_accounting(ctx)

    pages = _manifest_pages(ctx)
    page_docs = ctx.get("page_docs") or {}
    terminal = ctx.get("terminal_states") or {}
    page_revs = ctx.get("page_revision_ids") or {}
    spans = (ctx.get("spans_doc") or {}).get("spans") or []
    evidence_pages = {
        event.get("page")
        for event in (ctx.get("human_events") or [])
        if isinstance(event, dict)
    }
    by_page = _spans_by_page(spans)
    findings = []

    for page in pages:
        if page not in page_docs:
            findings.append(
                make_finding(
                    "g2_page_accounting", "G2", "page_missing", "REF_001",
                    _ERROR, _subject(page, page_revs.get(page), page),
                    detail="manifest 页序中的页缺少页文档: %s" % page,
                )
            )
            continue
        state = terminal.get(page)
        if state == "deferred":
            findings.append(
                make_finding(
                    "g2_page_accounting", "G2", "page_deferred", "REF_001",
                    _ERROR, _subject(page, page_revs.get(page), page),
                    detail="页终态为 deferred，依据 §10.1 严格阻断: %s" % page,
                )
            )
            continue
        if state == "known_unrecognizable":
            if page not in evidence_pages:
                findings.append(
                    make_finding(
                        "g2_page_accounting", "G2", "excluded_page_no_evidence",
                        "SEM_001", _ERROR, _subject(page, page_revs.get(page), page),
                        detail="排除页裸标：无人工事件证据: %s" % page,
                    )
                )
            continue
        if state is not None and state not in _KNOWN_TERMINAL:
            findings.append(
                make_finding(
                    "g2_page_accounting", "G2", "page_deferred", "REF_001",
                    _ERROR, _subject(page, page_revs.get(page), page),
                    detail="页终态为表外枚举 %r，不得进入覆盖: %s" % (state, page),
                )
            )
            continue
        if not by_page.get(page):
            findings.append(
                make_finding(
                    "g2_page_accounting", "G2", "page_without_span", "SRC_001",
                    _ERROR, _subject(page, page_revs.get(page), page),
                    detail="覆盖页有行却无 Span（疑似漏编）: %s" % page,
                )
            )

    page_set = set(pages)
    for page in by_page:
        if page not in page_set:
            findings.append(
                make_finding(
                    "g2_page_accounting", "G2", "page_unregistered", "REF_001",
                    _ERROR, _subject(page, page_revs.get(page), page),
                    detail="Span 引用 manifest 页序外的页: %s" % page,
                )
            )

    return {
        "findings": findings,
        "checked": {"pages": len(pages), "covered": len(by_page)},
    }


def _validate_text_page_accounting(ctx):
    """offset 档页登记：只能有 manifest 页序里的页，且 m3 报告逐页登记。

    - manifest 页序中的页未进 ``coverage_report.pages`` → ``page_missing``；
    - ``coverage_report.pages`` 出现 manifest 页序外的页 → ``page_unregistered``。
    """
    pages = _manifest_pages(ctx)
    report_pages = (ctx.get("coverage_report") or {}).get("pages") or {}
    spans_rev = ctx.get("corpus_spans_revision_id")
    findings = []

    for page in pages:
        if page not in report_pages:
            findings.append(
                make_finding(
                    "g2_page_accounting", "G2", "page_missing", "REF_001",
                    _ERROR, _subject(page, spans_rev),
                    detail="manifest 页序中的页未登记进 coverage_report: %s" % page,
                )
            )
    for page in report_pages:
        if page not in set(pages):
            findings.append(
                make_finding(
                    "g2_page_accounting", "G2", "page_unregistered", "REF_001",
                    _ERROR, _subject(page, spans_rev),
                    detail="coverage_report 出现 manifest 页序外的页: %s" % page,
                )
            )

    return {
        "findings": findings,
        "checked": {"pages": len(pages), "reported": len(report_pages)},
    }


def validate_contiguous_coverage(ctx):
    """逐页重算页块，核对 Span 首尾相接、无缺口/重叠/越界、拼接等于页块。

    - 缺口 / 首条未从 0 起 → ``coverage_gap``（TXT_001）；
    - 重叠 → ``coverage_overlap``（TXT_001）；
    - 相邻间隔非换行、offset 非法、末条未覆盖块尾 →
      ``span_boundary_mismatch``（TXT_001）；
    - 拼接文本 ≠ 页块 → ``span_text_mismatch``（TXT_001）。

    offset 档（R83）以冻结 ``cleaned_text`` 为全文，独立重算片段连续性与覆盖，
    再与 m3 ``coverage_report`` 的实算值逐项对账（对账不符 → ``count_mismatch``）。
    """
    if _is_offset(ctx):
        return _validate_text_contiguous_coverage(ctx)

    page_docs = ctx.get("page_docs") or {}
    terminal = ctx.get("terminal_states") or {}
    page_revs = ctx.get("page_revision_ids") or {}
    spans = (ctx.get("spans_doc") or {}).get("spans") or []
    by_page = _spans_by_page(spans)
    findings = []

    for page in _manifest_pages(ctx):
        state = terminal.get(page)
        if state not in _KNOWN_TERMINAL:
            continue
        doc = page_docs.get(page)
        if doc is None:
            continue
        block = _page_block(doc)
        page_spans = sorted(
            by_page.get(page, []), key=lambda span: span.get("start_offset", 0)
        )
        if not page_spans:
            if block:
                findings.append(
                    make_finding(
                        "g2_contiguous_coverage", "G2", "coverage_gap", "TXT_001",
                        _ERROR, _subject(None, page_revs.get(page), page),
                        detail="页有文本却无 Span 覆盖: %s" % page,
                    )
                )
            continue

        previous = None
        for span in page_spans:
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
                        "g2_contiguous_coverage", "G2", "span_boundary_mismatch",
                        "TXT_001", _ERROR,
                        _subject(span.get("span_id"), page_revs.get(page), page),
                        detail="offset 越界或非法: start=%r end=%r" % (start, end),
                    )
                )
                previous = span
                continue
            if previous is None:
                if start != 0:
                    findings.append(
                        make_finding(
                            "g2_contiguous_coverage", "G2", "coverage_gap", "TXT_001",
                            _ERROR,
                            _subject(span.get("span_id"), page_revs.get(page), page),
                            detail="首条 Span 未从 0 开始: %s" % span.get("span_id"),
                        )
                    )
            else:
                previous_end = previous.get("end_offset")
                if isinstance(previous_end, int):
                    if start > previous_end + 1:
                        findings.append(
                            make_finding(
                                "g2_contiguous_coverage", "G2", "coverage_gap",
                                "TXT_001", _ERROR,
                                _subject(span.get("span_id"), page_revs.get(page), page),
                                detail="存在缺口: [%d, %d]" % (previous_end, start),
                            )
                        )
                    elif start <= previous_end:
                        findings.append(
                            make_finding(
                                "g2_contiguous_coverage", "G2", "coverage_overlap",
                                "TXT_001", _ERROR,
                                _subject(span.get("span_id"), page_revs.get(page), page),
                                detail="存在重叠: [%d, %d]" % (start, previous_end),
                            )
                        )
                    elif previous_end >= len(block) or block[previous_end] != "\n":
                        findings.append(
                            make_finding(
                                "g2_contiguous_coverage", "G2",
                                "span_boundary_mismatch", "TXT_001", _ERROR,
                                _subject(span.get("span_id"), page_revs.get(page), page),
                                detail="相邻 Span 之间不是换行符",
                            )
                        )
            previous = span

        last_end = page_spans[-1].get("end_offset")
        if isinstance(last_end, int) and last_end != len(block):
            findings.append(
                make_finding(
                    "g2_contiguous_coverage", "G2", "span_boundary_mismatch",
                    "TXT_001", _ERROR,
                    _subject(page_spans[-1].get("span_id"), page_revs.get(page), page),
                    detail="末条 Span 未覆盖到页块尾部",
                )
            )

        joined = "\n".join(span.get("text", "") for span in page_spans)
        if joined != block:
            findings.append(
                make_finding(
                    "g2_contiguous_coverage", "G2", "span_text_mismatch", "TXT_001",
                    _ERROR, _subject(None, page_revs.get(page), page),
                    detail="Span 拼接结果与页块不一致: %s" % page,
                )
            )

    return {"findings": findings, "checked": {"pages": len(by_page)}}


def _validate_text_contiguous_coverage(ctx):
    """offset 档覆盖：片段连续 + 拼接等于 ``cleaned_text`` + 与报告实算值对账。"""
    spans = (ctx.get("spans_doc") or {}).get("spans") or []
    cleaned_text = ctx.get("cleaned_text")
    spans_rev = ctx.get("corpus_spans_revision_id")
    findings = []

    if not isinstance(cleaned_text, str):
        findings.append(
            make_finding(
                "g2_contiguous_coverage", "G2", "coverage_gap", "TXT_001",
                _ERROR, _subject(spans_rev, spans_rev),
                detail="冻结 cleaned_text 对象不可读，无法复算覆盖",
            )
        )
        return {"findings": findings, "checked": {"spans": len(spans)}}

    ordered = sorted(spans, key=lambda span: span.get("start_offset", 0))
    position = 0
    for span in ordered:
        start = span.get("start_offset")
        end = span.get("end_offset")
        text = span.get("text") or ""
        subject = _subject(span.get("span_id"), spans_rev)
        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or start < 0
            or end > len(cleaned_text)
            or start > end
        ):
            findings.append(
                make_finding(
                    "g2_contiguous_coverage", "G2", "span_boundary_mismatch", "TXT_001",
                    _ERROR, subject,
                    detail="offset 越界或非法: start=%r end=%r len=%d"
                    % (start, end, len(cleaned_text)),
                )
            )
            continue
        if start > position:
            findings.append(
                make_finding(
                    "g2_contiguous_coverage", "G2", "coverage_gap", "TXT_001",
                    _ERROR, subject, detail="存在缺口: [%d, %d)" % (position, start),
                )
            )
        elif start < position:
            findings.append(
                make_finding(
                    "g2_contiguous_coverage", "G2", "coverage_overlap", "TXT_001",
                    _ERROR, subject, detail="存在重叠: [%d, %d)" % (start, position),
                )
            )
        if cleaned_text[start:end] != text:
            findings.append(
                make_finding(
                    "g2_contiguous_coverage", "G2", "span_text_mismatch", "TXT_001",
                    _ERROR, subject,
                    detail="cleaned_text[start:end] 与 span.text 不一致",
                )
            )
        position = max(position, end)

    if position != len(cleaned_text):
        findings.append(
            make_finding(
                "g2_contiguous_coverage", "G2", "coverage_gap", "TXT_001",
                _ERROR, _subject(spans_rev, spans_rev),
                detail="片段未覆盖到 cleaned_text 末尾: 覆盖至 %d，实际长度 %d"
                % (position, len(cleaned_text)),
            )
        )

    # ---- 与 m3 coverage_report 的实算值对账（不自造页）----
    report = ctx.get("coverage_report") or {}
    gaps, overlaps = _gaps_and_overlaps(spans)
    covered = _covered_chars(spans)
    coverage_value = (covered / len(cleaned_text)) if cleaned_text else 0.0
    line_count = len((ctx.get("raw_text") or "").splitlines())

    def reconcile(page, key, expected, actual):
        if expected != actual:
            findings.append(
                make_finding(
                    "g2_contiguous_coverage", "G2", "count_mismatch", None,
                    _ERROR, _subject(page, spans_rev),
                    detail="coverage_report.%s 实算 %r != 报告 %r" % (key, expected, actual),
                )
            )

    for page in _manifest_pages(ctx):
        entry = (report.get("pages") or {}).get(page)
        if not isinstance(entry, dict):
            continue
        reconcile(page, "span_count", len(spans), entry.get("span_count"))
        reconcile(page, "coverage", coverage_value, entry.get("coverage"))
        reconcile(page, "line_count", line_count, entry.get("line_count"))
        reconcile(page, "gaps", gaps, entry.get("gaps"))
        reconcile(page, "overlaps", overlaps, entry.get("overlaps"))

    return {
        "findings": findings,
        "checked": {"spans": len(spans), "pages": len(_manifest_pages(ctx))},
    }


def validate_batch_partition(ctx):
    """验证批次划分：Span 与批次严格双射、不跨页、不超 ``batch_size``。

    - Span 无批次归属或批次含语料外 Span → ``batch_span_leak``（REF_001）；
    - 同一 Span 出现在多个批次 → ``batch_span_duplicate``（ID_002）；
    - 批次跨页 → ``batch_cross_page``（ID_002）；
    - 批次超过 ``batch_size`` → ``batch_oversize``（SCH_002）。

    offset 档（R83）的片段本身不带 ``batch_id``，批次划分落在冻结 ``corpus_batch``
    修订里：此处按 ``batch_assignments``（``{task_id: [span_id, ...]}``）独立复算
    「片段与批次严格双射、不超 ``batch_size``」。
    """
    if _is_offset(ctx):
        return _validate_text_batch_partition(ctx)

    spans = (ctx.get("spans_doc") or {}).get("spans") or []
    config = ctx.get("configuration") or {}
    batch_size = config.get("batch_size", 10)
    spans_rev = ctx.get("corpus_spans_revision_id")
    findings = []

    by_batch = {}
    span_batches = {}
    for span in spans:
        batch_id = span.get("batch_id")
        if not batch_id:
            findings.append(
                make_finding(
                    "g2_batch_partition", "G2", "batch_span_leak", "REF_001",
                    _ERROR, _subject(span.get("span_id"), spans_rev, span.get("page")),
                    detail="Span 无批次归属: %s" % span.get("span_id"),
                )
            )
            continue
        by_batch.setdefault(batch_id, []).append(span)
        span_batches.setdefault(span.get("span_id"), set()).add(batch_id)

    for span_id, batch_ids in span_batches.items():
        if len(batch_ids) > 1:
            findings.append(
                make_finding(
                    "g2_batch_partition", "G2", "batch_span_duplicate", "ID_002",
                    _ERROR, _subject(span_id, spans_rev),
                    detail="同一 Span 出现在多个批次: %s -> %s"
                    % (span_id, sorted(batch_ids)),
                )
            )

    for batch_id, members in sorted(by_batch.items()):
        if isinstance(batch_size, int) and len(members) > batch_size:
            findings.append(
                make_finding(
                    "g2_batch_partition", "G2", "batch_oversize", "SCH_002",
                    _ERROR, _subject(batch_id, spans_rev),
                    detail="批次 %s 超过 batch_size=%s" % (batch_id, batch_size),
                )
            )
        if len({member.get("page") for member in members}) > 1:
            findings.append(
                make_finding(
                    "g2_batch_partition", "G2", "batch_cross_page", "ID_002",
                    _ERROR, _subject(batch_id, spans_rev),
                    detail="批次 %s 跨页" % batch_id,
                )
            )

    expected = ctx.get("batches")
    if isinstance(expected, dict):
        for batch_id, expected_ids in expected.items():
            actual_ids = {member.get("span_id") for member in by_batch.get(batch_id, [])}
            for span_id in expected_ids:
                if span_id not in actual_ids:
                    findings.append(
                        make_finding(
                            "g2_batch_partition", "G2", "batch_span_leak", "REF_001",
                            _ERROR, _subject(span_id, spans_rev),
                            detail="批次 %s 漏 Span: %s" % (batch_id, span_id),
                        )
                    )
        for batch_id in by_batch:
            if batch_id not in expected:
                findings.append(
                    make_finding(
                        "g2_batch_partition", "G2", "batch_span_leak", "REF_001",
                        _ERROR, _subject(batch_id, spans_rev),
                        detail="批次含语料外 Span: %s" % batch_id,
                    )
                )

    return {
        "findings": findings,
        "checked": {"batches": len(by_batch), "spans": len(spans)},
    }


def _validate_text_batch_partition(ctx):
    """offset 档批次：冻结 ``corpus_batch`` 与片段严格双射、不超 ``batch_size``。"""
    spans = (ctx.get("spans_doc") or {}).get("spans") or []
    assignments = ctx.get("batch_assignments") or {}
    config = ctx.get("configuration") or {}
    batch_size = config.get("batch_size", 10)
    spans_rev = ctx.get("corpus_spans_revision_id")
    findings = []

    span_ids = [span.get("span_id") for span in spans]
    known = set(span_ids)
    if spans and not assignments:
        findings.append(
            make_finding(
                "g2_batch_partition", "G2", "batch_span_leak", "REF_001",
                _ERROR, _subject(spans_rev, spans_rev),
                detail="无任何冻结 corpus_batch 批次可对账",
            )
        )

    assigned = {}
    for batch_id in sorted(assignments, key=str):
        members = assignments[batch_id] or []
        if isinstance(batch_size, int) and len(members) > batch_size:
            findings.append(
                make_finding(
                    "g2_batch_partition", "G2", "batch_oversize", "SCH_002",
                    _ERROR, _subject(batch_id, spans_rev),
                    detail="批次 %s 超过 batch_size=%s" % (batch_id, batch_size),
                )
            )
        for span_id in members:
            if span_id not in known:
                findings.append(
                    make_finding(
                        "g2_batch_partition", "G2", "batch_span_leak", "REF_001",
                        _ERROR, _subject(span_id, spans_rev),
                        detail="批次 %s 含语料外 Span: %s" % (batch_id, span_id),
                    )
                )
            assigned.setdefault(span_id, []).append(batch_id)

    for span_id, batch_ids in assigned.items():
        if len(batch_ids) > 1:
            findings.append(
                make_finding(
                    "g2_batch_partition", "G2", "batch_span_duplicate", "ID_002",
                    _ERROR, _subject(span_id, spans_rev),
                    detail="同一 Span 出现在多个批次: %s -> %s" % (span_id, sorted(batch_ids)),
                )
            )
    for span_id in span_ids:
        if span_id not in assigned:
            findings.append(
                make_finding(
                    "g2_batch_partition", "G2", "batch_span_leak", "REF_001",
                    _ERROR, _subject(span_id, spans_rev),
                    detail="Span 无批次归属: %s" % span_id,
                )
            )

    return {
        "findings": findings,
        "checked": {"batches": len(assignments), "spans": len(spans)},
    }


def _validate_text_count_reconciliation(ctx):
    """offset 档计数对账：表头、m3 包与片段偏移合计 vs ``cleaned_text`` 长度。"""
    spans_doc = ctx.get("spans_doc") or {}
    spans = spans_doc.get("spans") or []
    m3_package = ctx.get("m3_package") or {}
    assignments = ctx.get("batch_assignments") or {}
    cleaned_text = ctx.get("cleaned_text")
    spans_rev = ctx.get("corpus_spans_revision_id")
    findings = []

    def add(detail):
        findings.append(
            make_finding(
                "g2_count_reconciliation", "G2", "count_mismatch", None, _ERROR,
                _subject(spans_rev, spans_rev), detail=detail,
            )
        )

    batches = len(assignments)
    if spans_doc.get("span_count") != len(spans):
        add("表头 span_count %r != 实际 %d" % (spans_doc.get("span_count"), len(spans)))
    if "batch_count" in spans_doc and spans_doc.get("batch_count") != batches:
        add("表头 batch_count %r != 实际 %d" % (spans_doc.get("batch_count"), batches))

    counts = (m3_package.get("manifest") or {}).get("counts") or {}
    if counts.get("spans") != len(spans):
        add("m3 包 counts.spans %r != 实际 %d" % (counts.get("spans"), len(spans)))
    if counts.get("batches") != batches:
        add("m3 包 counts.batches %r != 实际 %d" % (counts.get("batches"), batches))

    if isinstance(cleaned_text, str):
        covered = _covered_chars(spans)
        if covered != len(cleaned_text):
            add("片段偏移合计 %d != cleaned_text 长度 %d" % (covered, len(cleaned_text)))

    return {
        "findings": findings,
        "checked": {
            "spans": len(spans),
            "batches": batches,
            "cleaned_chars": len(cleaned_text) if isinstance(cleaned_text, str) else 0,
        },
    }


def validate_count_reconciliation(ctx):
    """核对 counts：表头、m3 包、页行数合计与锚点字框合计。

    任一处不符 → ``count_mismatch``（``code=None``）。

    offset 档（R83）无页文档与字框，改为对账表头计数、m3 包计数，以及片段偏移
    合计与冻结 ``cleaned_text`` 长度。
    """
    if _is_offset(ctx):
        return _validate_text_count_reconciliation(ctx)

    spans_doc = ctx.get("spans_doc") or {}
    spans = spans_doc.get("spans") or []
    page_docs = ctx.get("page_docs") or {}
    m3_package = ctx.get("m3_package") or {}
    spans_rev = ctx.get("corpus_spans_revision_id")
    findings = []

    def add(detail):
        findings.append(
            make_finding(
                "g2_count_reconciliation", "G2", "count_mismatch", None, _ERROR,
                _subject(spans_rev, spans_rev), detail=detail,
            )
        )

    distinct_batches = len({span.get("batch_id") for span in spans})
    if spans_doc.get("span_count") != len(spans):
        add("表头 span_count %r != 实际 %d" % (spans_doc.get("span_count"), len(spans)))
    if spans_doc.get("batch_count") != distinct_batches:
        add("表头 batch_count %r != 实际 %d"
            % (spans_doc.get("batch_count"), distinct_batches))

    counts = (m3_package.get("manifest") or {}).get("counts") or {}
    if counts.get("spans") != len(spans):
        add("m3 包 counts.spans %r != 实际 %d" % (counts.get("spans"), len(spans)))
    if counts.get("batches") != distinct_batches:
        add("m3 包 counts.batches %r != 实际 %d"
            % (counts.get("batches"), distinct_batches))

    lines_total = sum(len(doc.get("lines") or []) for doc in page_docs.values())
    if lines_total != len(spans):
        add("页行数合计 %d != Span 数 %d" % (lines_total, len(spans)))

    chars_total = sum(len(doc.get("chars") or []) for doc in page_docs.values())
    anchor_chars = sum(
        len((span.get("source_anchor") or {}).get("chars") or []) for span in spans
    )
    if chars_total != anchor_chars:
        add("页字框合计 %d != 锚点字框数 %d" % (chars_total, anchor_chars))

    return {
        "findings": findings,
        "checked": {
            "spans": len(spans),
            "batches": distinct_batches,
            "lines": lines_total,
            "chars": chars_total,
        },
    }
