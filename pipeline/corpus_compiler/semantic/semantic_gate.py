"""M3 独立语义 Gate：``evaluate_semantic_offset``（act/06，规格 §11）。

本模块从清洗文本、结构片段文档、语义片段文档、双路提议与人工裁决事件**独立重算**
语义层的八项判定，不读取 Ledger、零网络、纯函数。

八项检查（名称与顺序固定）：
    (1) semantic_contiguous_coverage：语义片段首尾相连、无缺口、无重叠，拼接后完全等于 cleaned_text
    (2) semantic_strict_offset：cleaned_text[start:end] == span.text 且 quote_sha256 正确、锚点自洽
    (3) structural_refs_consistent：引用的结构 Span 存在，局部偏移与全局偏移换算一致
    (4) window_rule_fidelity：长度 >= model_min_chars 的片段均正确成为窗口，其余片段严格一行一片
    (5) disputes_resolved_zero：独立复算双模型提议；分歧窗口恰有 1 条有效裁决，未决分歧为 0
    (6) evidence_level_honest：每条片段及顶层证据级别声明严格为 offset_level
    (7) semantic_identity：semantic_span_id 形、唯一性与序号连续性
    (8) header_counts：顶层 span_count / window_count / dispute_count 与实体严格一致

独立性（第 88 条）：本模块**不得**引入同包任何编译器实现模块（``offset_assemble``、
``review``、``proposer``、``offset_rules``、``proposals``、``text_compiler``、``step_offset``、
``gate_offset``），以免判定与生产代码“同错同过”。本模块只使用标准库与
``pipeline.ledger.ids``（片段 ID 形态的唯一权威出处，第 85、102 条）。
"""

import hashlib
import json
import re

from pipeline.ledger import ids

# 语义片段 ID：sem_<work>_ed<NN>_o<NNNNNNN>（第 80 条）；正则唯一权威出处为
# pipeline.ledger.ids（第 85、102 条），本模块不自有形态。
_SPAN_ID_RE = re.compile(ids.PATTERNS["semantic_span_id"])

EXPECTED_EVIDENCE_LEVEL = "offset_level"
DECISION_TYPE = "review_source_fidelity"

STATUS_AGREED = "agreed"
STATUS_DISPUTED = "disputed"

BOUNDARY_RULE = "rule"
BOUNDARY_CROSS_MODEL_AGREED = "cross_model_agreed"
BOUNDARY_HUMAN_DECIDED = "human_decided"

# 八项检查名称与固定顺序
CHECK_NAMES = (
    "semantic_contiguous_coverage",
    "semantic_strict_offset",
    "structural_refs_consistent",
    "window_rule_fidelity",
    "disputes_resolved_zero",
    "evidence_level_honest",
    "semantic_identity",
    "header_counts",
)


def evaluate_semantic_offset(
    *,
    cleaned_text: str,
    patches: list,
    structural_spans_doc: dict,
    semantic_spans_doc: dict,
    window_responses: list,
    decisions: list,
    model_min_chars: int = 12,
) -> dict:
    """独立判定语义层是否满足 §11 语义 Gate。

    参数：
        cleaned_text: 清洗文本全文（切片的唯一基准）。
        patches: ``DeterministicPatchSet`` 补丁列表（本 Gate 只做接口形校验；原始偏移链路
            由结构层 Gate 与 M5 证据校验复核，本函数不重复换算）。
        structural_spans_doc: 结构层 spans 文档（含 ``spans`` 列表）。
        semantic_spans_doc: 语义层 spans 文档（README §6.2 的顶层键序）。
        window_responses: 每个模型窗口的双路提议与比较结果（含 ``proposal_a``/``proposal_b``）。
        decisions: 人工裁决事件文档列表。
        model_min_chars: 进入模型窗口的最小字符数（默认 12）。

    返回：
        ``{"semantic": "passed" | "failed", "checks": {name: {"ok": bool, "detail": str}}}``
    """
    spans = _spans_of(semantic_spans_doc)
    structural_spans = _spans_of(structural_spans_doc)
    responses = window_responses or []
    decision_list = decisions or []

    structural_by_id = {
        span.get("span_id"): span for span in structural_spans if isinstance(span, dict)
    }
    by_structural = _group_by_structural(spans)
    by_window = _group_by_window(spans)
    recomputed = _recompute_statuses(responses)

    results = {
        "semantic_contiguous_coverage": _check_contiguous(spans, cleaned_text),
        "semantic_strict_offset": _check_strict_offset(spans, cleaned_text, patches),
        "structural_refs_consistent": _check_structural_refs(
            spans, structural_by_id
        ),
        "window_rule_fidelity": _check_window_rule(
            structural_spans,
            by_structural,
            by_window,
            responses,
            model_min_chars,
            structural_by_id,
        ),
        "disputes_resolved_zero": _check_disputes(
            recomputed, by_window, responses, decision_list, structural_by_id
        ),
        "evidence_level_honest": _check_evidence_level(semantic_spans_doc, spans),
        "semantic_identity": _check_identity(spans),
        "header_counts": _check_header_counts(
            semantic_spans_doc,
            spans,
            responses,
            recomputed,
            structural_spans,
            structural_spans_doc,
        ),
    }

    checks = {
        name: {"ok": ok, "detail": detail} for name, (ok, detail) in results.items()
    }
    return {
        "semantic": "passed" if all(check["ok"] for check in checks.values()) else "failed",
        "checks": checks,
    }


# --------------------------------------------------------------------------
# (1) 连续覆盖
# --------------------------------------------------------------------------


def _check_contiguous(spans, cleaned_text):
    """片段首尾相连、无缺口、无重叠，拼接后完全等于 cleaned_text。"""
    if not spans:
        return False, "语义片段为空，未覆盖任何文本"

    cursor = 0
    pieces = []
    for span in spans:
        start, end, error = _offsets(span)
        if error:
            return False, error
        if start > cursor:
            return False, "存在缺口: [%d, %d)" % (cursor, start)
        if start < cursor:
            return False, "存在重叠: [%d, %d)" % (start, cursor)
        pieces.append(span.get("text") if isinstance(span.get("text"), str) else "")
        cursor = end

    if cursor != len(cleaned_text):
        return False, "未覆盖到 cleaned_text 末尾: 覆盖至 %d，实际 %d" % (
            cursor,
            len(cleaned_text),
        )

    joined = "".join(pieces)
    if joined != cleaned_text:
        return False, "片段拼接结果（%d 字符）与 cleaned_text（%d 字符）不一致" % (
            len(joined),
            len(cleaned_text),
        )
    return True, ""


# --------------------------------------------------------------------------
# (2) 严格 offset
# --------------------------------------------------------------------------


def _check_strict_offset(spans, cleaned_text, patches):
    """cleaned_text[start:end] == span.text，quote_sha256 与锚点自洽。"""
    for span in spans:
        start, end, error = _offsets(span)
        if error:
            return False, error
        if not 0 <= start <= end <= len(cleaned_text):
            return False, "片段 %r 偏移越界: [%d, %d)" % (
                span.get("semantic_span_id"),
                start,
                end,
            )
        text = span.get("text")
        if not isinstance(text, str):
            return False, "片段 %r 的 text 不是字符串" % (span.get("semantic_span_id"),)
        if cleaned_text[start:end] != text:
            return False, "片段 %r: cleaned_text[%d:%d] 与 text 不一致" % (
                span.get("semantic_span_id"),
                start,
                end,
            )
        expected_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if span.get("quote_sha256") != expected_sha256:
            return False, "片段 %r: quote_sha256 与 sha256(text) 不一致" % (
                span.get("semantic_span_id"),
            )
        anchor = span.get("source_anchor")
        if not isinstance(anchor, dict):
            return False, "片段 %r 缺 source_anchor" % (span.get("semantic_span_id"),)
        if anchor.get("start_offset") != start or anchor.get("end_offset") != end:
            return False, "片段 %r: 锚点偏移与片段偏移不一致" % (
                span.get("semantic_span_id"),
            )
        if anchor.get("quote_sha256") != span.get("quote_sha256"):
            return False, "片段 %r: 锚点引文哈希与片段不一致" % (
                span.get("semantic_span_id"),
            )

    for patch in patches or []:
        if not isinstance(patch, dict) or any(
            key not in patch
            for key in ("raw_start", "raw_end", "cleaned_start", "cleaned_end")
        ):
            return False, "补丁形非法（缺偏移键）: %r" % (patch,)
    return True, ""


# --------------------------------------------------------------------------
# (3) 结构引用一致
# --------------------------------------------------------------------------


def _check_structural_refs(spans, structural_by_id):
    """每条语义片段引用存在的结构 Span，且局部偏移与全局偏移换算一致。"""
    for span in spans:
        refs = span.get("structural_refs")
        if not isinstance(refs, list) or not refs:
            return False, "片段 %r 缺结构引用" % (span.get("semantic_span_id"),)

        span_ids = {
            ref.get("span_id") for ref in refs if isinstance(ref, dict)
        }
        if len(span_ids) != 1:
            return False, "片段 %r 的结构引用跨越多个结构片段" % (
                span.get("semantic_span_id"),
            )

        structural = structural_by_id.get(refs[0].get("span_id"))
        if structural is None:
            return False, "片段 %r 引用了不存在的结构片段 %r" % (
                span.get("semantic_span_id"),
                refs[0].get("span_id"),
            )

        structural_text = structural.get("text")
        structural_start = structural.get("start_offset")
        if not isinstance(structural_text, str) or not isinstance(structural_start, int):
            return False, "被引结构片段 %r 形非法" % (refs[0].get("span_id"),)

        pieces = []
        for ref in refs:
            local_start, local_end = ref.get("start"), ref.get("end")
            if (
                isinstance(local_start, bool)
                or isinstance(local_end, bool)
                or not isinstance(local_start, int)
                or not isinstance(local_end, int)
                or local_start < 0
                or local_end > len(structural_text)
                or local_start >= local_end
            ):
                return False, "片段 %r 的局部区间非法: [%r, %r)" % (
                    span.get("semantic_span_id"),
                    local_start,
                    local_end,
                )
            pieces.append(structural_text[local_start:local_end])

        if "".join(pieces) != span.get("text"):
            return False, "片段 %r 的结构引用切片与语义文本不一致" % (
                span.get("semantic_span_id"),
            )

        for previous, current in zip(refs, refs[1:]):
            if previous.get("end") != current.get("start"):
                return False, "片段 %r 的结构引用之间不连续" % (
                    span.get("semantic_span_id"),
                )

        if structural_start + refs[0]["start"] != span.get("start_offset"):
            return False, "片段 %r 局部起点与全局起点换算不一致" % (
                span.get("semantic_span_id"),
            )
        if structural_start + refs[-1]["end"] != span.get("end_offset"):
            return False, "片段 %r 局部终点与全局终点换算不一致" % (
                span.get("semantic_span_id"),
            )
    return True, ""


# --------------------------------------------------------------------------
# (4) 窗口规则保真
# --------------------------------------------------------------------------


def _check_window_rule(
    structural_spans, by_structural, by_window, responses, model_min_chars, structural_by_id
):
    """长度 >= model_min_chars 的片段必须成为窗口；其余片段严格一行一片。"""
    if not structural_spans:
        return False, "结构片段文档为空"

    for structural in structural_spans:
        span_id = structural.get("span_id")
        text = structural.get("text")
        if not isinstance(text, str):
            return False, "结构片段 %r 的 text 非法" % (span_id,)
        group = by_structural.get(span_id) or []

        if not group:
            return False, "结构片段 %r 无语义片段覆盖" % (span_id,)

        if len(text) >= model_min_chars:
            for span in group:
                if span.get("window_id") is None:
                    return False, "窗口片段 %r 缺 window_id" % (
                        span.get("semantic_span_id"),
                    )
                if span.get("boundary_origin") not in (
                    BOUNDARY_CROSS_MODEL_AGREED,
                    BOUNDARY_HUMAN_DECIDED,
                ):
                    return False, "窗口片段 %r 的 boundary_origin 非窗口来源" % (
                        span.get("semantic_span_id"),
                    )
        else:
            if len(group) != 1:
                return False, "非窗口片段 %r（%d 字符）被切成 %d 片，违反一行一片" % (
                    span_id,
                    len(text),
                    len(group),
                )
            only = group[0]
            if only.get("boundary_origin") != BOUNDARY_RULE or only.get("window_id") is not None:
                return False, "非窗口片段 %r 的 boundary_origin 必须为 rule 且 window_id 为 null" % (
                    span_id,
                )

    response_by_window = {
        item.get("window_id"): item for item in responses if isinstance(item, dict)
    }
    if set(by_window) != set(response_by_window):
        return False, "窗口集合不一致: 语义文档 %s vs 提议记录 %s" % (
            sorted(by_window),
            sorted(response_by_window),
        )

    for window_id, items in by_window.items():
        response = response_by_window[window_id]
        structural = _window_structural(response, items, structural_by_id)
        if structural is None:
            return False, "窗口 %r 无法定位其结构片段" % (window_id,)
        window_text = structural.get("text")
        declared = response.get("text")
        if isinstance(declared, str) and declared != window_text:
            return False, "窗口 %r 记录的原文与其结构片段不一致" % (window_id,)

        refs = []
        for span in items:
            span_refs = span.get("structural_refs") or []
            if not span_refs:
                return False, "窗口 %r 的片段缺结构引用" % (window_id,)
            refs.append((span_refs[0].get("start"), span_refs[-1].get("end")))

        for previous, current in zip(refs, refs[1:]):
            if previous[1] != current[0]:
                return False, "窗口 %r 的语义片段在结构片段内不连续" % (window_id,)
        if refs[0][0] != 0:
            return False, "窗口 %r 的语义片段未从窗口起点开始" % (window_id,)
        if refs[-1][1] != len(window_text):
            return False, "窗口 %r 的语义片段未覆盖到窗口末尾（%d != %d）" % (
                window_id,
                refs[-1][1],
                len(window_text),
            )
    return True, ""


# --------------------------------------------------------------------------
# (5) 未决分歧为零
# --------------------------------------------------------------------------


def _check_disputes(recomputed, by_window, responses, decisions, structural_by_id):
    """独立复算双模型提议：分歧窗口恰 1 条有效裁决；一致窗口不得有裁决。"""
    response_by_window = {
        item.get("window_id"): item for item in responses if isinstance(item, dict)
    }

    decisions_by_window = {}
    for decision in decisions:
        if not isinstance(decision, dict):
            return False, "裁决事件不是映射"
        window_id = decision.get("window_id")
        if decision.get("decision_type") != DECISION_TYPE:
            return False, "裁决 %r 的 decision_type 必须为 %r" % (
                window_id,
                DECISION_TYPE,
            )
        if window_id not in recomputed:
            return False, "裁决指向队列外窗口 %r（越权）" % (window_id,)
        decisions_by_window.setdefault(window_id, []).append(decision)

    agreed = {window_id for window_id, status in recomputed.items() if status == STATUS_AGREED}
    disputed = {
        window_id for window_id, status in recomputed.items() if status == STATUS_DISPUTED
    }

    for window_id in agreed:
        if decisions_by_window.get(window_id):
            return False, "双路一致窗口 %r 出现人工裁决（越权）" % (window_id,)

    for window_id in disputed:
        entries = decisions_by_window.get(window_id) or []
        if len(entries) != 1:
            return False, "分歧窗口 %r 的有效裁决数 %d != 1（存在未决分歧）" % (
                window_id,
                len(entries),
            )
        decision = entries[0]
        segments = _as_segments(decision.get("segments"))
        if segments is None:
            return False, "分歧窗口 %r 的裁决切分形非法" % (window_id,)

        window_items = by_window.get(window_id, [])
        window_text = None
        structural = _window_structural(
            response_by_window.get(window_id) or {}, window_items, structural_by_id
        )
        if structural is not None:
            window_text = structural.get("text")
        if not isinstance(window_text, str):
            return False, "分歧窗口 %r 无法定位窗口原文，无法核对裁决" % (window_id,)
        error = _segments_error(segments, window_text)
        if error:
            return False, "分歧窗口 %r 的裁决切分非法: %s" % (window_id, error)

        expected_pieces = [
            [ref.get("start"), ref.get("end")]
            for span in window_items
            for ref in (span.get("structural_refs") or [])
        ]
        if expected_pieces != segments:
            return False, "分歧窗口 %r 的裁决切分与语义片段不一致（裁决被篡改？）" % (
                window_id,
            )

    for window_id, status in recomputed.items():
        expected_origin = (
            BOUNDARY_CROSS_MODEL_AGREED if status == STATUS_AGREED else BOUNDARY_HUMAN_DECIDED
        )
        for span in by_window.get(window_id, []):
            if span.get("boundary_origin") != expected_origin:
                return False, "窗口 %r 的 boundary_origin 为 %r，应为 %r" % (
                    window_id,
                    span.get("boundary_origin"),
                    expected_origin,
                )

    unresolved = [
        window_id for window_id in disputed if not decisions_by_window.get(window_id)
    ]
    if unresolved:
        return False, "未决分歧窗口 %d 个: %s" % (len(unresolved), ", ".join(sorted(unresolved)))
    return True, ""


# --------------------------------------------------------------------------
# (6) 证据级别如实
# --------------------------------------------------------------------------


def _check_evidence_level(semantic_spans_doc, spans):
    """每条片段与顶层证据级别声明严格为 offset_level（不得伪造升格）。"""
    counts = semantic_spans_doc.get("evidence_level_counts")
    if not isinstance(counts, dict):
        return False, "缺顶层 evidence_level_counts 声明"
    if counts.get("offset_level") != len(spans):
        return False, "顶层 evidence_level_counts.offset_level=%r 与片段数 %d 不一致" % (
            counts.get("offset_level"),
            len(spans),
        )
    if counts.get("glyphbox_level", 0) != 0:
        return False, "顶层证据级别出现 glyphbox_level=%r（伪升格）" % (
            counts.get("glyphbox_level"),
        )

    top_level = semantic_spans_doc.get("evidence_level")
    if top_level is not None and top_level != EXPECTED_EVIDENCE_LEVEL:
        return False, "顶层 evidence_level 为 %r，应为 %r" % (
            top_level,
            EXPECTED_EVIDENCE_LEVEL,
        )

    for span in spans:
        level = span.get("evidence_level")
        if level != EXPECTED_EVIDENCE_LEVEL:
            return False, "片段 %r 的 evidence_level 为 %r，应为 %r" % (
                span.get("semantic_span_id"),
                level,
                EXPECTED_EVIDENCE_LEVEL,
            )
    return True, ""


# --------------------------------------------------------------------------
# (7) 标识与序号
# --------------------------------------------------------------------------


def _check_identity(spans):
    """semantic_span_id 形、唯一性、序号连续性、起点偏移段与锚点一致。"""
    seen = set()
    for index, span in enumerate(spans, start=1):
        span_id = span.get("semantic_span_id")
        if not isinstance(span_id, str) or _SPAN_ID_RE.match(span_id) is None:
            return False, "semantic_span_id 形非法: %r" % (span_id,)
        if span_id in seen:
            return False, "semantic_span_id 重复: %s" % span_id
        seen.add(span_id)

        if span.get("sequence") != index:
            return False, "片段 %s 的 sequence=%r 与全文顺序 %d 不符" % (
                span_id,
                span.get("sequence"),
                index,
            )

        anchor = span.get("source_anchor")
        raw_start = anchor.get("raw_start") if isinstance(anchor, dict) else None
        if isinstance(raw_start, int):
            expected_segment = "%07d" % raw_start
            if span_id.rsplit("_o", 1)[-1] != expected_segment:
                return False, "片段 %s 的起点段与 source_anchor.raw_start=%d 不符（身份不稳定）" % (
                    span_id,
                    raw_start,
                )
    return True, ""


# --------------------------------------------------------------------------
# (8) 表头计数
# --------------------------------------------------------------------------


def _check_header_counts(
    semantic_spans_doc, spans, responses, recomputed, structural_spans, structural_spans_doc
):
    """顶层 span_count / window_count / dispute_count 与实体、结构指纹严格一致。"""
    if semantic_spans_doc.get("span_count") != len(spans):
        return False, "顶层 span_count=%r 与语义片段数 %d 不一致" % (
            semantic_spans_doc.get("span_count"),
            len(spans),
        )

    window_count = len({item.get("window_id") for item in responses if isinstance(item, dict)})
    if semantic_spans_doc.get("window_count") != window_count:
        return False, "顶层 window_count=%r 与实际窗口数 %d 不一致" % (
            semantic_spans_doc.get("window_count"),
            window_count,
        )

    dispute_count = sum(1 for status in recomputed.values() if status == STATUS_DISPUTED)
    if semantic_spans_doc.get("dispute_count") != dispute_count:
        return False, "顶层 dispute_count=%r 与实际分歧窗口数 %d 不一致" % (
            semantic_spans_doc.get("dispute_count"),
            dispute_count,
        )

    fingerprint = hashlib.sha256(
        json.dumps(structural_spans, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if semantic_spans_doc.get("raw_spans_sha256") != fingerprint:
        return False, "顶层 raw_spans_sha256 与结构片段文档重算结果不一致"

    if semantic_spans_doc.get("edition_part_artifact_id") != structural_spans_doc.get(
        "edition_part_artifact_id"
    ):
        return False, "顶层 edition_part_artifact_id 与结构片段文档不一致"
    return True, ""


# --------------------------------------------------------------------------
# 内部工具
# --------------------------------------------------------------------------


def _spans_of(document):
    """取文档的 spans 列表（形非法时返回空列表，交由各检查如实判失败）。"""
    if not isinstance(document, dict):
        return []
    spans = document.get("spans")
    if not isinstance(spans, list):
        return []
    return [span for span in spans if isinstance(span, dict)]


def _offsets(span):
    """取片段偏移，返回 (start, end, error)。"""
    start = span.get("start_offset")
    end = span.get("end_offset")
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, int)
        or not isinstance(end, int)
    ):
        return None, None, "片段 %r 的偏移非整数" % (span.get("semantic_span_id"),)
    return start, end, ""


def _window_structural(response, items, structural_by_id):
    """定位窗口所属的结构片段（窗口即一个结构片段）。

    优先按语义片段的结构引用定位；其次按窗口记录里的 ``span_id`` 定位。
    这样 Gate 无需调用方额外提供窗口原文即可独立核对（调用方若提供，则须与结构片段一致）。
    """
    for span in items:
        refs = span.get("structural_refs")
        if isinstance(refs, list) and refs and isinstance(refs[0], dict):
            structural = structural_by_id.get(refs[0].get("span_id"))
            if isinstance(structural, dict):
                return structural
    if isinstance(response, dict):
        structural = structural_by_id.get(response.get("span_id"))
        if isinstance(structural, dict):
            return structural
    return None


def _group_by_structural(spans):
    """按被引结构片段聚合语义片段。"""
    grouped = {}
    for span in spans:
        refs = span.get("structural_refs")
        if not isinstance(refs, list) or not refs or not isinstance(refs[0], dict):
            continue
        grouped.setdefault(refs[0].get("span_id"), []).append(span)
    return grouped


def _group_by_window(spans):
    """按窗口聚合语义片段（非窗口片段不计入）。"""
    grouped = {}
    for span in spans:
        window_id = span.get("window_id")
        if window_id is None:
            continue
        grouped.setdefault(window_id, []).append(span)
    return grouped


def _recompute_statuses(responses):
    """独立复算每个窗口的双路比较结论：{window_id: "agreed" | "disputed"}。"""
    statuses = {}
    for item in responses:
        if not isinstance(item, dict):
            continue
        window_id = item.get("window_id")
        proposal_a = item.get("proposal_a") or {}
        proposal_b = item.get("proposal_b") or {}
        valid = (
            isinstance(proposal_a, dict)
            and isinstance(proposal_b, dict)
            and proposal_a.get("valid") is True
            and proposal_b.get("valid") is True
        )
        same = valid and _boundaries(proposal_a) == _boundaries(proposal_b)
        statuses[window_id] = STATUS_AGREED if same else STATUS_DISPUTED
    return statuses


def _boundaries(parsed):
    """把提议的切分归一化为可比较的边界序列。"""
    segments = parsed.get("segments")
    if not isinstance(segments, list):
        return None
    normalized = []
    for pair in segments:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            return None
        normalized.append((pair[0], pair[1]))
    return normalized


def _as_segments(value):
    """把裁决切分归一化为 [[start, end], ...]，形非法返回 None。"""
    if not isinstance(value, list) or not value:
        return None
    normalized = []
    for pair in value:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            return None
        normalized.append([pair[0], pair[1]])
    return normalized


def _segments_error(segments, text):
    """校验切分是否整数、首尾相连并完整覆盖文本；返回错误说明或空串。"""
    previous_end = 0
    for index, (start, end) in enumerate(segments):
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
            or start < 0
            or end > len(text)
            or start >= end
        ):
            return "区间越界或非法: [%r, %r)" % (start, end)
        if start > previous_end:
            return "存在缺口: [%d, %d)" % (previous_end, start)
        if start < previous_end:
            return "存在重叠: [%d, %d)" % (start, previous_end)
        previous_end = end
    if not segments or previous_end != len(text):
        return "未完整覆盖窗口（覆盖至 %d，窗口长度 %d）" % (previous_end, len(text))
    return ""
