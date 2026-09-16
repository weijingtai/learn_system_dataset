"""M3 电子文本结构 Gate——偏移层覆盖与锚点评定（act/03，G7-RULINGS 第 76、78 条）。

本模块从冻结的 ``RawText``、``CleanedText``、``DeterministicPatchSet`` 与 spans
文档独立重算覆盖、偏移、锚点换算、标识与表头计数，判定电子文本路线（证据级别
``offset_level``）的片段集合是否满足结构层 Gate。本模块只做纯计算，不读文件、
不访问 Ledger、零网络；且**不得**引用同包模块 ``text_compiler``、``step_offset`` 与
``assemble_offset``——它们与编译生成器共享同一处逻辑，引用它们会让判定与生产代码
“同错同过”（G7-RULINGS 第 88 条）。

六项检查（名称与顺序固定）：
    (1) text_contiguous_coverage：片段首尾相连、无缺口、无重叠，拼接后 100% 等于 cleaned_text
    (2) text_strict_offset：cleaned_text[start:end] == span.text，且 quote_sha256 == sha256(span.text)
    (3) raw_anchor_fidelity：经 patches 换算 (raw_start, raw_end) 后等于 (start_offset, end_offset)
    (4) identity_and_stability：span_id 严格符合 ss_<work>_ed<NN>_o<NNNNNNN>，序号单调递增，ID 全局唯一
    (5) evidence_level_honest：每条 Span 及顶层 evidence_level 严格为 "offset_level"
    (6) header_counts：文档顶层 span_count 与 spans 列表长度严格一致

六项全部 ok，``passed`` 才为 ``True``。
"""

import hashlib
import re

# G7-RULINGS 第 78 条：无页码文本的片段 ID 为 ss_<work>_ed<NN>_o<NNNNNNN>，
# o 后为片段起点在冻结 RawText 中的字符偏移（7 位零填充，RawText 冻结不变故 ID 稳定）。
_SPAN_ID_RE = re.compile(r"^ss_([a-z][a-z0-9]*)_ed([0-9]{2})_o([0-9]{7})$")

# 电子文本第一版发布级别的证据级别（G7-RULINGS 第 76 条）。
_EXPECTED_EVIDENCE_LEVEL = "offset_level"


def evaluate_text_coverage(
    *,
    raw_text: str,
    cleaned_text: str,
    patches: list,
    spans_doc: dict,
) -> dict:
    """独立判定电子文本片段集合是否满足结构层 Gate（act/03 contract）。

    参数：
        raw_text：冻结的 RawText 全文。
        cleaned_text：清洗后的 CleanedText 全文。
        patches：DeterministicPatchSet 的补丁列表，每条含
            ``raw_start``/``raw_end``/``cleaned_start``/``cleaned_end``。
        spans_doc：待判定的 spans 文档（含顶层 ``work``、``evidence_level``、
            ``span_count`` 与 ``spans`` 列表）。

    返回 ``{"passed": bool, "checks": {name: {"ok": bool, "detail": str}}}``，
    ``checks`` 的键序固定为六项检查名。
    """
    spans = spans_doc.get("spans", []) or []
    work = spans_doc.get("work", "")
    evidence_level = spans_doc.get("evidence_level", "")

    results = {
        "text_contiguous_coverage": _check_contiguous_coverage(spans, cleaned_text),
        "text_strict_offset": _check_strict_offset(spans, cleaned_text),
        "raw_anchor_fidelity": _check_raw_anchor_fidelity(
            spans, patches, raw_text, cleaned_text
        ),
        "identity_and_stability": _check_identity_and_stability(spans, work),
        "evidence_level_honest": _check_evidence_level_honest(spans, evidence_level),
        "header_counts": _check_header_counts(spans, spans_doc),
    }

    checks = {
        name: {"ok": ok, "detail": detail} for name, (ok, detail) in results.items()
    }
    return {"passed": all(check["ok"] for check in checks.values()), "checks": checks}


def _check_contiguous_coverage(spans, cleaned_text):
    """片段首尾相连、无缺口、无重叠，且各片段文本拼接后 100% 等于 cleaned_text。"""
    ordered = sorted(spans, key=lambda s: s.get("start_offset", 0))

    assembled = []
    prev_end = 0
    for span in ordered:
        start = span.get("start_offset")
        end = span.get("end_offset")
        if not (isinstance(start, int) and isinstance(end, int)) or start < 0 or end < start:
            return False, "Span %s: offset 非法: start=%r end=%r" % (
                span.get("span_id"),
                start,
                end,
            )
        if start > prev_end:
            return False, "存在缺口: [%d, %d)" % (prev_end, start)
        if start < prev_end:
            return False, "存在重叠: [%d, %d)" % (start, prev_end)
        assembled.append(span.get("text", "") or "")
        prev_end = end

    if prev_end != len(cleaned_text):
        return False, "片段未覆盖到 cleaned_text 末尾: 覆盖至 %d，实际长度 %d" % (
            prev_end,
            len(cleaned_text),
        )

    joined = "".join(assembled)
    if joined != cleaned_text:
        return False, "片段拼接结果（%d 字符）与 cleaned_text（%d 字符）不一致" % (
            len(joined),
            len(cleaned_text),
        )
    return True, ""


def _check_strict_offset(spans, cleaned_text):
    """每条 Span 的 cleaned_text[start:end] == span.text，且 quote_sha256 == sha256(text)。"""
    for span in spans:
        start = span.get("start_offset")
        end = span.get("end_offset")
        text = span.get("text", "")
        if not (
            isinstance(start, int)
            and isinstance(end, int)
            and 0 <= start <= end <= len(cleaned_text)
        ):
            return False, "Span %s: offset 越界或非法: start=%r end=%r" % (
                span.get("span_id"),
                start,
                end,
            )
        if cleaned_text[start:end] != text:
            return False, "Span %s: cleaned_text[%d:%d] 与 text 不一致" % (
                span.get("span_id"),
                start,
                end,
            )
        expected_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if span.get("quote_sha256") != expected_sha256:
            return False, "Span %s: quote_sha256 与 sha256(text) 不一致" % span.get("span_id")
    return True, ""


def _check_raw_anchor_fidelity(spans, patches, raw_text, cleaned_text):
    """经 patches 校验：raw 侧 (raw_start, raw_end) 换算到 cleaned 侧应等于 Span 的偏移。"""
    ordered = (
        sorted(patches, key=lambda p: p.get("raw_start", 0)) if patches else []
    )

    for span in spans:
        anchor = span.get("source_anchor") or {}
        if not isinstance(anchor, dict):
            return False, "Span %s: source_anchor 不是映射" % span.get("span_id")
        raw_start = anchor.get("raw_start")
        raw_end = anchor.get("raw_end")
        if not (isinstance(raw_start, int) and isinstance(raw_end, int)):
            return False, "Span %s: source_anchor 缺 raw_start/raw_end" % span.get("span_id")
        if not (0 <= raw_start <= raw_end <= len(raw_text)):
            return False, "Span %s: raw 锚点越界或非法: raw_start=%r raw_end=%r" % (
                span.get("span_id"),
                raw_start,
                raw_end,
            )

        mapped_start = _map_raw_offset(ordered, raw_start, is_end=False)
        mapped_end = _map_raw_offset(ordered, raw_end, is_end=True)
        start_offset = span.get("start_offset")
        end_offset = span.get("end_offset")
        if (mapped_start, mapped_end) != (start_offset, end_offset):
            return False, (
                "Span %s: patches 换算 (%r, %r) 与记录 (%r, %r) 不符"
                % (span.get("span_id"), mapped_start, mapped_end, start_offset, end_offset)
            )
    return True, ""


def _map_raw_offset(ordered_patches, position, is_end):
    """把 RawText 中的单个偏移点换算为 CleanedText 中的偏移（本文件内独立实现）。"""
    if not ordered_patches:
        return position

    if position < ordered_patches[0]["raw_start"]:
        return position

    for index, patch in enumerate(ordered_patches):
        patch_raw_start = patch["raw_start"]
        patch_raw_end = patch["raw_end"]
        patch_cleaned_start = patch["cleaned_start"]
        patch_cleaned_end = patch["cleaned_end"]

        # 落在当前补丁之前、上一补丁之后的未修改区段
        if position < patch_raw_start:
            if index == 0:
                return position
            previous = ordered_patches[index - 1]
            return previous["cleaned_end"] + (position - previous["raw_end"])

        if patch_raw_start <= position <= patch_raw_end:
            if patch_raw_start == patch_raw_end:  # 插入：raw 侧长度为零
                return patch_cleaned_start if is_end else patch_cleaned_end
            if position == patch_raw_start:
                return patch_cleaned_start
            if position == patch_raw_end:
                return patch_cleaned_end
            raw_len = patch_raw_end - patch_raw_start
            cleaned_len = patch_cleaned_end - patch_cleaned_start
            if cleaned_len == 0:
                return patch_cleaned_start
            if raw_len == cleaned_len:
                return patch_cleaned_start + (position - patch_raw_start)
            return patch_cleaned_start + round(
                (position - patch_raw_start) * cleaned_len / raw_len
            )

    last = ordered_patches[-1]
    return last["cleaned_end"] + (position - last["raw_end"])


def _check_identity_and_stability(spans, work):
    """span_id 严格符合 ss_<work>_ed<NN>_o<NNNNNNN>，起点偏移单调递增且 ID 全局唯一。"""
    seen = set()
    previous_offset = None

    for span in spans:
        span_id = span.get("span_id")
        if not isinstance(span_id, str):
            return False, "span_id 非字符串: %r" % (span_id,)
        match = _SPAN_ID_RE.match(span_id)
        if match is None:
            return False, "span_id 格式非法: %r" % (span_id,)
        if span_id in seen:
            return False, "span_id 重复: %s" % span_id
        seen.add(span_id)

        span_work, _edition, offset_segment = match.groups()
        if work and span_work != work:
            return False, "span_id 的 work 段 %r 与文档 work %r 不符" % (span_work, work)

        offset = int(offset_segment)
        if previous_offset is not None and offset <= previous_offset:
            return False, "span_id 起点偏移未单调递增: %d -> %d" % (previous_offset, offset)
        previous_offset = offset

        anchor = span.get("source_anchor") or {}
        anchor_raw_start = anchor.get("raw_start") if isinstance(anchor, dict) else None
        if isinstance(anchor_raw_start, int) and anchor_raw_start != offset:
            return False, "span_id 起点偏移 %d 与 source_anchor.raw_start %d 不符" % (
                offset,
                anchor_raw_start,
            )
    return True, ""


def _check_evidence_level_honest(spans, evidence_level):
    """每条 Span 及顶层 evidence_level 严格为 "offset_level"（不得伪造升格）。"""
    if evidence_level != _EXPECTED_EVIDENCE_LEVEL:
        return False, "顶层 evidence_level 为 %r，应为 %r" % (
            evidence_level,
            _EXPECTED_EVIDENCE_LEVEL,
        )
    for span in spans:
        span_evidence_level = span.get("evidence_level")
        if span_evidence_level != _EXPECTED_EVIDENCE_LEVEL:
            return False, "Span %s: evidence_level 为 %r，应为 %r" % (
                span.get("span_id"),
                span_evidence_level,
                _EXPECTED_EVIDENCE_LEVEL,
            )
    return True, ""


def _check_header_counts(spans, spans_doc):
    """文档顶层 span_count 与 spans 列表长度严格一致。"""
    span_count = spans_doc.get("span_count")
    actual_count = len(spans)
    if span_count != actual_count:
        return False, "顶层 span_count=%r 与 spans 列表长度 %d 不一致" % (
            span_count,
            actual_count,
        )
    return True, ""
