"""M3 独立结构 Gate（规格 §11）。

本模块从页 JSON 与 manifest 独立重新计算页块、字框锚点与批次规则，
判定 StructuralSpan 集合是否满足：全页覆盖 100%、无缺口、无重叠、
严格 offset、拼接等于原文、glyphbox 锚点一致、标识唯一合规、批次规则
合规、表头计数一致；语义层未做，恒为 ``not_evaluated``。

本模块只做纯计算，不读文件、不访问 Ledger；且**不得** import
``pipeline.corpus_compiler.compiler`` 或 ``pipeline.corpus_compiler.serialize``，
以防编译器与判定共享同一处错误而“同错同过”，可以 import
``pipeline.ledger.ids`` 复用已冻结的标识正则闭集。
"""

import re

from pipeline.ledger import ids

# §8.1：来源标识 src_<work>_ed<NN>
_SOURCE_ID_RE = re.compile(r"^src_([a-z][a-z0-9]*)_ed([0-9]{2})$")
# 页名 page_NNN 或 page_NNNN
_PAGE_NUMBER_RE = re.compile(r"^page_([0-9]{3,4})$")
# source_span_id 各段拆解（与 ids.PATTERNS["source_span_id"] 同一格式，独立书写）
_SPAN_ID_PARTS_RE = re.compile(r"^ss_([a-z][a-z0-9]*)_ed([0-9]{2})_p([0-9]{4})_s([0-9]{2})$")
_SPAN_ID_FULL_RE = re.compile(ids.PATTERNS["source_span_id"])

# 8 项检查名称与固定顺序（规格 §11 Gate）
_CHECK_NAMES = (
    "page_accounting",
    "contiguous_coverage",
    "strict_offset",
    "concat_equals_block",
    "glyphbox_anchors",
    "span_identity",
    "batch_rules",
    "header_counts",
)

# §10.1 异常页终态枚举 + 未标注（None，等同 manually_transcribed 一样要求有文字）
_KNOWN_TERMINAL_STATES = (None, "manually_transcribed", "known_unrecognizable")


def _page_block(page_doc):
    """页块 = 该页 OCR 各行文本以 "\\n" 连接（本文件内自行实现，不依赖编译器）。"""
    return "\n".join(line["text"] for line in page_doc["lines"])


def _page_number(page):
    """解析页名为整数页号；不匹配返回 ``None``（Gate 内部不因此抛异常，交由检查记失败）。"""
    match = _PAGE_NUMBER_RE.match(page) if isinstance(page, str) else None
    return int(match.group(1)) if match else None


def _parse_source_id(source_id):
    """解析 source_id 为 (work, edition)；不匹配返回 (None, None)。"""
    match = _SOURCE_ID_RE.match(source_id) if isinstance(source_id, str) else None
    if match is None:
        return None, None
    return match.group(1), match.group(2)


def _coverage_for_page(page, block, page_spans):
    """计算单页覆盖情况，返回 (ok, failures, coverage, gaps, overlaps)。"""
    failures = []
    gaps = []
    overlaps = []

    if not page_spans:
        if len(block) > 0:
            gaps.append([0, len(block)])
        failures.append({"page": page, "span_id": None, "detail": "页 %s 无 Span 覆盖" % page})
        return False, failures, 0.0, gaps, overlaps

    ordered = sorted(page_spans, key=lambda s: s.get("start_offset", 0))

    if ordered[0].get("start_offset") != 0:
        failures.append(
            {
                "page": page,
                "span_id": ordered[0].get("span_id"),
                "detail": "首条 span 未从 0 开始",
            }
        )

    covered_ranges = []
    prev = None
    for span in ordered:
        start = span.get("start_offset")
        end = span.get("end_offset")
        if prev is not None:
            prev_end = prev.get("end_offset")
            if start > prev_end + 1:
                gaps.append([prev_end, start])
                failures.append(
                    {
                        "page": page,
                        "span_id": span.get("span_id"),
                        "detail": "存在缺口: [%s, %s]" % (prev_end, start),
                    }
                )
            elif start <= prev_end:
                overlaps.append([start, prev_end])
                failures.append(
                    {
                        "page": page,
                        "span_id": span.get("span_id"),
                        "detail": "存在重叠: [%s, %s]" % (start, prev_end),
                    }
                )
            else:
                sep_index = prev_end
                if sep_index >= len(block) or block[sep_index] != "\n":
                    failures.append(
                        {
                            "page": page,
                            "span_id": span.get("span_id"),
                            "detail": "相邻 Span 之间不是换行符",
                        }
                    )
        covered_ranges.append((start, end))
        prev = span

    if ordered[-1].get("end_offset") != len(block):
        failures.append(
            {
                "page": page,
                "span_id": ordered[-1].get("span_id"),
                "detail": "末条 span 未覆盖到页块尾部",
            }
        )

    total_non_newline = sum(1 for ch in block if ch != "\n")
    covered_positions = set()
    for start, end in covered_ranges:
        if start is None or end is None:
            continue
        for pos in range(max(0, start), min(end, len(block))):
            if block[pos] != "\n":
                covered_positions.add(pos)
    coverage = (len(covered_positions) / total_non_newline) if total_non_newline else 1.0

    ok = coverage == 1.0 and not gaps and not overlaps and not failures
    return ok, failures, coverage, gaps, overlaps


def evaluate_structural(
    *, manifest, page_docs, terminal_states, evidence_pages, spans_doc, batch_size
):
    """独立判定 StructuralSpan 集合是否满足结构层 Gate（规格 §11）。

    参数：
        manifest：M1 manifest.yaml 解析后的 dict。
        page_docs：``{page: OCR 页 JSON dict}``。
        terminal_states：``{page: 终态字符串}``。
        evidence_pages：有人工事件证据的页名集合。
        spans_doc：待判定的 spans 文档（含 ``spans`` 列表与表头字段）。
        batch_size：批次规则校验用的每批最大行数。

    返回 dict，键：``gate_profile``、``structural``、``semantic``、
    ``checks``、``pages``。
    """
    pages_seq = manifest["edition_part"]["pages"]
    page_set = set(pages_seq)
    spans = spans_doc.get("spans", []) or []

    # ---- 初始化每页基础报告 ----
    pages_report = {}
    for page in pages_seq:
        doc = page_docs.get(page)
        line_count = len(doc["lines"]) if doc is not None else 0
        pages_report[page] = {
            "status": "invalid",
            "terminal_state": terminal_states.get(page),
            "line_count": line_count,
            "span_count": 0,
            "coverage": 0.0,
            "gaps": [],
            "overlaps": [],
        }

    spans_by_page = {}
    extra_page_spans = []
    for span in spans:
        page = span.get("page")
        if page in pages_report:
            pages_report[page]["span_count"] += 1
            spans_by_page.setdefault(page, []).append(span)
        else:
            extra_page_spans.append(span)

    checks = {}

    # ---- 1. page_accounting ----
    pa_failures = []
    for page in pages_seq:
        state = terminal_states.get(page)
        line_count = pages_report[page]["line_count"]
        span_count = pages_report[page]["span_count"]
        if state == "known_unrecognizable":
            ok_page = True
            if line_count != 0:
                pa_failures.append(
                    {"page": page, "span_id": None, "detail": "known_unrecognizable 页行数非 0"}
                )
                ok_page = False
            if span_count != 0:
                pa_failures.append(
                    {"page": page, "span_id": None, "detail": "known_unrecognizable 页含 Span"}
                )
                ok_page = False
            if page not in evidence_pages:
                pa_failures.append(
                    {
                        "page": page,
                        "span_id": None,
                        "detail": "known_unrecognizable 页裸标：无人工事件证据",
                    }
                )
                ok_page = False
            pages_report[page]["status"] = "excluded" if ok_page else "invalid"
        elif state == "deferred":
            pa_failures.append({"page": page, "span_id": None, "detail": "页终态为 deferred"})
            pages_report[page]["status"] = "invalid"
        elif state not in _KNOWN_TERMINAL_STATES:
            pa_failures.append(
                {"page": page, "span_id": None, "detail": "页终态非法枚举: %r" % (state,)}
            )
            pages_report[page]["status"] = "invalid"
        else:
            ok_page = True
            if line_count == 0:
                pa_failures.append(
                    {"page": page, "span_id": None, "detail": "裸空页：0 行且无终态覆盖"}
                )
                ok_page = False
            if span_count == 0:
                pa_failures.append(
                    {"page": page, "span_id": None, "detail": "漏编：页有行却无 Span"}
                )
                ok_page = False
            pages_report[page]["status"] = "covered" if ok_page else "invalid"

    for span in extra_page_spans:
        pa_failures.append(
            {
                "page": span.get("page"),
                "span_id": span.get("span_id"),
                "detail": "Span 引用页序外的页",
            }
        )
    checks["page_accounting"] = {"ok": len(pa_failures) == 0, "failures": pa_failures}

    # ---- 2. contiguous_coverage ----
    cc_failures = []
    for page in pages_seq:
        state = terminal_states.get(page)
        if state not in (None, "manually_transcribed"):
            continue
        doc = page_docs.get(page)
        if doc is None:
            cc_failures.append(
                {"page": page, "span_id": None, "detail": "页文档不存在，无法计算页块"}
            )
            continue
        block = _page_block(doc)
        page_spans = spans_by_page.get(page, [])
        _ok, page_failures, coverage_val, gaps, overlaps = _coverage_for_page(
            page, block, page_spans
        )
        cc_failures.extend(page_failures)
        pages_report[page]["coverage"] = coverage_val
        pages_report[page]["gaps"] = gaps
        pages_report[page]["overlaps"] = overlaps
    checks["contiguous_coverage"] = {"ok": len(cc_failures) == 0, "failures": cc_failures}

    # ---- 3. strict_offset ----
    so_failures = []
    block_cache = {}

    def _get_block(page):
        if page not in block_cache:
            doc = page_docs.get(page)
            block_cache[page] = _page_block(doc) if doc is not None else None
        return block_cache[page]

    for span in spans:
        page = span.get("page")
        span_id = span.get("span_id")
        block = _get_block(page)
        if block is None:
            so_failures.append({"page": page, "span_id": span_id, "detail": "页块不存在，无法校验 offset"})
            continue
        start = span.get("start_offset")
        end = span.get("end_offset")
        if not (isinstance(start, int) and isinstance(end, int) and 0 <= start <= end <= len(block)):
            so_failures.append(
                {
                    "page": page,
                    "span_id": span_id,
                    "detail": "offset 越界或非法: start=%r end=%r" % (start, end),
                }
            )
            continue
        if block[start:end] != span.get("text"):
            so_failures.append(
                {"page": page, "span_id": span_id, "detail": "block[start:end] 与 text 不一致"}
            )
    checks["strict_offset"] = {"ok": len(so_failures) == 0, "failures": so_failures}

    # ---- 4. concat_equals_block ----
    ce_failures = []
    for page, plist in spans_by_page.items():
        block = _get_block(page)
        if block is None:
            continue
        ordered = sorted(plist, key=lambda s: s.get("start_offset", 0))
        joined = "\n".join(s.get("text", "") for s in ordered)
        if joined != block:
            ce_failures.append({"page": page, "span_id": None, "detail": "拼接结果与页块不一致"})
    checks["concat_equals_block"] = {"ok": len(ce_failures) == 0, "failures": ce_failures}

    # ---- 5. glyphbox_anchors ----
    ga_failures = []
    asset_sha = {item["page"]: item["sha256"] for item in manifest.get("source_assets", [])}
    for span in spans:
        page = span.get("page")
        span_id = span.get("span_id")
        anchor = span.get("source_anchor") or {}
        if anchor.get("page") != page:
            ga_failures.append(
                {"page": page, "span_id": span_id, "detail": "source_anchor.page 与 span.page 不一致"}
            )
            continue
        doc = page_docs.get(page)
        if doc is None:
            ga_failures.append({"page": page, "span_id": span_id, "detail": "页文档不存在"})
            continue
        if anchor.get("image_sha256") != asset_sha.get(page):
            ga_failures.append(
                {"page": page, "span_id": span_id, "detail": "image_sha256 与 manifest 资产不符"}
            )
            continue
        lines = doc["lines"]
        line = None
        line_idx = None
        for i, candidate in enumerate(lines):
            if candidate["id"] == anchor.get("line_id"):
                line = candidate
                line_idx = i
                break
        if line is None:
            ga_failures.append(
                {"page": page, "span_id": span_id, "detail": "line_id 不在该页 lines 中"}
            )
            continue
        if span.get("line_index") != line_idx:
            ga_failures.append(
                {"page": page, "span_id": span_id, "detail": "line_index 与实际下标不符"}
            )
        if span.get("text") != line.get("text"):
            ga_failures.append({"page": page, "span_id": span_id, "detail": "text 与该行文本不符"})
        if anchor.get("bbox") != line.get("box"):
            ga_failures.append({"page": page, "span_id": span_id, "detail": "bbox 与 line.box 不符"})
        expect_chars = [
            (ci, ch["id"], ch["char"], ch["box"])
            for ci, ch in enumerate(doc.get("chars", []))
            if ch["parent"] == anchor.get("line_id")
        ]
        got_chars = anchor.get("chars") or []
        if len(got_chars) != len(expect_chars):
            ga_failures.append(
                {"page": page, "span_id": span_id, "detail": "chars 数量与页 JSON 不符"}
            )
        else:
            for got, expect in zip(got_chars, expect_chars):
                ci, glyph_id, char, box = expect
                if (
                    got.get("char_index"),
                    got.get("glyph_id"),
                    got.get("char"),
                    got.get("box"),
                ) != (ci, glyph_id, char, box):
                    ga_failures.append(
                        {
                            "page": page,
                            "span_id": span_id,
                            "detail": "字框锚点与页 JSON chars 不一致",
                        }
                    )
                    break
    checks["glyphbox_anchors"] = {"ok": len(ga_failures) == 0, "failures": ga_failures}

    # ---- 6. span_identity ----
    si_failures = []
    seen_span_ids = set()
    work_expected, edition_expected = _parse_source_id(manifest.get("source_id"))
    for span in spans:
        page = span.get("page")
        span_id = span.get("span_id")
        if not isinstance(span_id, str) or _SPAN_ID_FULL_RE.match(span_id) is None:
            si_failures.append({"page": page, "span_id": span_id, "detail": "span_id 格式非法"})
            continue
        if span_id in seen_span_ids:
            si_failures.append({"page": page, "span_id": span_id, "detail": "span_id 重复"})
        else:
            seen_span_ids.add(span_id)
        parts = _SPAN_ID_PARTS_RE.match(span_id)
        if parts is None:
            si_failures.append({"page": page, "span_id": span_id, "detail": "span_id 无法解析各段"})
            continue
        work, edition, page_str, seq_str = parts.groups()
        expected_pnum = _page_number(page)
        if expected_pnum is None or int(page_str) != expected_pnum:
            si_failures.append(
                {"page": page, "span_id": span_id, "detail": "span_id 页号段与 page 不符"}
            )
        if int(seq_str) != (span.get("line_index", -999) + 1):
            si_failures.append(
                {"page": page, "span_id": span_id, "detail": "span_id 行序段与 line_index+1 不符"}
            )
        if work_expected is not None and (work != work_expected or edition != edition_expected):
            si_failures.append(
                {
                    "page": page,
                    "span_id": span_id,
                    "detail": "span_id 的 work/ed 段与 manifest.source_id 不符",
                }
            )
    checks["span_identity"] = {"ok": len(si_failures) == 0, "failures": si_failures}

    # ---- 7. batch_rules ----
    br_failures = []
    batch_pattern = (
        re.compile(r"^%s_b[0-9]{3}$" % re.escape(work_expected)) if work_expected else None
    )
    batch_order = []
    batch_members = {}
    for span in spans:
        batch_id = span.get("batch_id")
        if batch_pattern is None or not isinstance(batch_id, str) or batch_pattern.match(batch_id) is None:
            br_failures.append(
                {"page": span.get("page"), "span_id": span.get("span_id"), "detail": "batch_id 格式非法: %r" % (batch_id,)}
            )
            continue
        if batch_id not in batch_members:
            batch_members[batch_id] = []
            batch_order.append(batch_id)
        batch_members[batch_id].append(span)

    for position, batch_id in enumerate(batch_order, start=1):
        expected_suffix = "_b%03d" % position
        if not batch_id.endswith(expected_suffix):
            br_failures.append(
                {
                    "page": None,
                    "span_id": None,
                    "detail": "批号未按首次出现顺序从 001 递增: %s（应为第 %d 个批次）"
                    % (batch_id, position),
                }
            )
        members = batch_members[batch_id]
        if len(members) > batch_size:
            br_failures.append(
                {"page": None, "span_id": None, "detail": "批次 %s 超过 batch_size=%d" % (batch_id, batch_size)}
            )
        pages_in_batch = {m.get("page") for m in members}
        if len(pages_in_batch) > 1:
            br_failures.append({"page": None, "span_id": None, "detail": "批次 %s 跨页" % batch_id})
        else:
            ordered_members = sorted(members, key=lambda s: s.get("line_index", 0))
            expected_idx = ordered_members[0].get("line_index")
            for member in ordered_members:
                if member.get("line_index") != expected_idx:
                    br_failures.append(
                        {
                            "page": member.get("page"),
                            "span_id": member.get("span_id"),
                            "detail": "批次 %s 内 line_index 不连续" % batch_id,
                        }
                    )
                expected_idx = member.get("line_index", expected_idx) + 1
    checks["batch_rules"] = {"ok": len(br_failures) == 0, "failures": br_failures}

    # ---- 8. header_counts ----
    hc_failures = []
    if spans_doc.get("span_count") != len(spans):
        hc_failures.append({"page": None, "span_id": None, "detail": "span_count 与实际 spans 长度不符"})
    distinct_batches = len({span.get("batch_id") for span in spans})
    if spans_doc.get("batch_count") != distinct_batches:
        hc_failures.append({"page": None, "span_id": None, "detail": "batch_count 与实际不同批号数不符"})
    if spans_doc.get("work") != manifest.get("work_title"):
        hc_failures.append({"page": None, "span_id": None, "detail": "work 与 manifest.work_title 不符"})
    if spans_doc.get("source_id") != manifest.get("source_id"):
        hc_failures.append({"page": None, "span_id": None, "detail": "source_id 与 manifest.source_id 不符"})
    if spans_doc.get("edition_part_artifact_id") != manifest.get("edition_part", {}).get("artifact_id"):
        hc_failures.append(
            {"page": None, "span_id": None, "detail": "edition_part_artifact_id 与 manifest 不符"}
        )
    if spans_doc.get("evidence_level") != "glyphbox_level":
        hc_failures.append(
            {"page": None, "span_id": None, "detail": "evidence_level 不是 glyphbox_level"}
        )
    checks["header_counts"] = {"ok": len(hc_failures) == 0, "failures": hc_failures}

    structural = "passed" if all(checks[name]["ok"] for name in _CHECK_NAMES) else "failed"

    return {
        "gate_profile": "structural_only",
        "structural": structural,
        "semantic": "not_evaluated",
        "checks": checks,
        "pages": pages_report,
    }
