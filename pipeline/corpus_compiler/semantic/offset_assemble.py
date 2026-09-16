"""M3 语义层合成：``sem_`` 偏移锚点 SemanticSpan 与语义文档（act/05，G7-RULINGS 第 80 条）。

在结构片段之上按「规则优先 + 双模型窗口 + 人工裁决」合成语义片段：

    - 非窗口片段（长度 < ``model_min_chars``）→ ``boundary_origin: rule`` 单片；
    - 双模型边界一致的窗口 → ``boundary_origin: cross_model_agreed``，按一致切分；
    - 经人工裁决的窗口 → ``boundary_origin: human_decided``，按裁决切分。

片段 ID 严格限定为 ``sem_<work>_ed<NN>_o<NNNNNNN>``（P8），起点偏移取**冻结 RawText** 中的
位置，故不随清洗修订漂移（第 78、80 条）。

本模块为纯函数：零网络、零 Ledger、不写文件。
"""

import hashlib
import json
import re

from ..offset_anchors import (
    format_semantic_span_id,
    make_offset_anchor,
    map_cleaned_to_raw,
)

_RE_WORK = re.compile(r"^[a-z][a-z0-9_]*$")
_RE_EDITION = re.compile(r"^ed[0-9]{2}$")

GATE_PROFILE = "structural_and_semantic"
SEGMENTATION_PROFILE = "offset_semantic_v1"
CONTENT_STATUS = "machine_extracted"
EVIDENCE_LEVEL = "offset_level"

BOUNDARY_RULE = "rule"
BOUNDARY_CROSS_MODEL_AGREED = "cross_model_agreed"
BOUNDARY_HUMAN_DECIDED = "human_decided"
BOUNDARY_ORIGINS = (BOUNDARY_RULE, BOUNDARY_CROSS_MODEL_AGREED, BOUNDARY_HUMAN_DECIDED)

# 语义片段键序（README §6.2）
SPAN_KEYS = (
    "semantic_span_id",
    "sequence",
    "start_offset",
    "end_offset",
    "text",
    "quote_sha256",
    "boundary_origin",
    "window_id",
    "structural_refs",
    "evidence_level",
    "source_anchor",
)


def spans_sha256(spans: list[dict]) -> str:
    """结构片段列表的确定性内容指纹（Gate 侧按同一算法独立重算）。"""
    payload = json.dumps(spans or [], sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compile_semantic_offset(
    *,
    structural_spans: list[dict],
    windows: list[dict],
    resolutions: dict,
    raw_text_revision_id: str,
    raw_text: str,
    cleaned_text_revision_id: str,
    cleaned_text: str,
    patches: list[dict],
    work: str,
    edition: str,
    edition_part_artifact_id: str = None,
) -> dict:
    """合成语义层文档（顶层键序与 README §6.2 逐字一致）。

    参数：
        structural_spans: 结构层 spans 列表（含 ``span_id``、``text``、``start_offset``）。
        windows: ``offset_rules.select_text_windows`` 产出的窗口列表。
        resolutions: ``{window_id: {"boundary_origin": ..., "segments": [[start, end], ...]}}``，
            覆盖**每一个**窗口（一致窗口来自双模型比较，分歧窗口来自人工裁决）。
        raw_text_revision_id / raw_text: 冻结原始文本及其修订。
        cleaned_text_revision_id / cleaned_text: 清洗文本及其修订。
        patches: ``DeterministicPatchSet`` 补丁列表（用于清洗偏移 → 原始偏移换算）。
        work / edition: 作品与版本标识（决定 ``sem_`` 前缀内的两段）。
        edition_part_artifact_id: 版本部件标识（顶层键所需；contract 未列该参数，为**追加的
            关键字参数**，缺省 None 即拒绝——见回报中的偏差说明）。

    返回：
        语义层文档字典，顶层键序 ``work, source_id, edition_part_artifact_id,
        raw_spans_sha256, gate_profile, segmentation_profile, content_status, span_count,
        window_count, dispute_count, evidence_level_counts, spans``。

    异常：
        ValueError("SCH_002: ...")：参数形不符、窗口缺裁决结果、边界形非法或原始偏移越界。
    """
    if not (isinstance(work, str) and _RE_WORK.match(work)):
        raise ValueError("SCH_002: 非法的 work 标识: %r" % (work,))
    if not (isinstance(edition, str) and _RE_EDITION.match(edition)):
        raise ValueError("SCH_002: 非法的 edition 标识: %r" % (edition,))
    if not isinstance(edition_part_artifact_id, str) or not edition_part_artifact_id:
        raise ValueError("SCH_002: 缺少 edition_part_artifact_id（顶层键必需）")
    if not isinstance(raw_text, str) or not raw_text:
        raise ValueError("SCH_002: raw_text 不能为空")
    if not isinstance(cleaned_text, str):
        raise ValueError("SCH_002: cleaned_text 必须为字符串")
    if not isinstance(resolutions, dict):
        raise ValueError("SCH_002: resolutions 必须为映射")

    window_by_span = {
        window.get("span_id"): window for window in (windows or [])
    }

    semantic_spans: list[dict] = []
    origin_counts = {origin: 0 for origin in BOUNDARY_ORIGINS}

    for structural in structural_spans or []:
        span_id = structural.get("span_id")
        span_text = structural.get("text")
        if not isinstance(span_text, str):
            raise ValueError("SCH_002: 结构片段 %r 的 text 不是字符串" % (span_id,))
        base_cleaned = structural.get("start_offset")
        if not isinstance(base_cleaned, int):
            raise ValueError("SCH_002: 结构片段 %r 缺 start_offset" % (span_id,))

        window = window_by_span.get(span_id)
        if window is None:
            pieces = [(0, len(span_text), BOUNDARY_RULE, None)]
        else:
            window_id = window.get("window_id")
            resolution = resolutions.get(window_id)
            if resolution is None:
                raise ValueError(
                    "SCH_002: 窗口 %s 缺少一致/裁决结果，拒绝合成" % (window_id,)
                )
            origin = resolution.get("boundary_origin")
            if origin not in (BOUNDARY_CROSS_MODEL_AGREED, BOUNDARY_HUMAN_DECIDED):
                raise ValueError(
                    "SCH_002: 窗口 %s 的 boundary_origin 非法: %r" % (window_id, origin)
                )
            segments = resolution.get("segments")
            if not isinstance(segments, list) or not segments:
                raise ValueError("SCH_002: 窗口 %s 缺少切分区间" % (window_id,))
            pieces = [
                (
                    _as_int(pair[0], window_id),
                    _as_int(pair[1], window_id),
                    origin,
                    window_id,
                )
                for pair in segments
            ]

        for local_start, local_end, origin, window_id in pieces:
            if local_start < 0 or local_end > len(span_text) or local_start >= local_end:
                raise ValueError(
                    "SCH_002: 窗口 %r 局部区间越界: [%d, %d) 文本长度 %d"
                    % (window_id, local_start, local_end, len(span_text))
                )

            text = span_text[local_start:local_end]
            cleaned_start = base_cleaned + local_start
            cleaned_end = base_cleaned + local_end
            if cleaned_text and (
                cleaned_end > len(cleaned_text)
                or cleaned_text[cleaned_start:cleaned_end] != text
            ):
                raise ValueError(
                    "SCH_002: 片段与 cleaned_text 不一致: [%d, %d)" % (cleaned_start, cleaned_end)
                )

            raw_start, raw_end = map_cleaned_to_raw(patches, cleaned_start, cleaned_end)
            if raw_end > len(raw_text):
                raise ValueError(
                    "SCH_002: 换算后的原始偏移越界: [%d, %d) raw 长度 %d"
                    % (raw_start, raw_end, len(raw_text))
                )

            source_anchor = make_offset_anchor(
                raw_text_revision_id=raw_text_revision_id,
                raw_start=raw_start,
                raw_end=raw_end,
                cleaned_text_revision_id=cleaned_text_revision_id,
                start_offset=cleaned_start,
                end_offset=cleaned_end,
                quote=text,
            )

            origin_counts[origin] += 1
            semantic_spans.append(
                {
                    "semantic_span_id": format_semantic_span_id(work, edition, raw_start),
                    "sequence": len(semantic_spans) + 1,
                    "start_offset": cleaned_start,
                    "end_offset": cleaned_end,
                    "text": text,
                    "quote_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "boundary_origin": origin,
                    "window_id": window_id,
                    "structural_refs": [
                        {"span_id": span_id, "start": local_start, "end": local_end}
                    ],
                    "evidence_level": EVIDENCE_LEVEL,
                    "source_anchor": source_anchor,
                }
            )

    # 分歧窗口数 = 经人工裁决的窗口数（每个裁决窗口一条决议）
    dispute_count = sum(
        1
        for resolution in (resolutions or {}).values()
        if isinstance(resolution, dict)
        and resolution.get("boundary_origin") == BOUNDARY_HUMAN_DECIDED
    )

    semantic_spans_doc = {
        "work": work,
        "source_id": "src_%s_%s" % (work, edition),
        "edition_part_artifact_id": edition_part_artifact_id,
        "raw_spans_sha256": spans_sha256(structural_spans),
        "gate_profile": GATE_PROFILE,
        "segmentation_profile": {
            "profile": SEGMENTATION_PROFILE,
            "boundary_origins": origin_counts,
        },
        "content_status": CONTENT_STATUS,
        "span_count": len(semantic_spans),
        "window_count": len(windows or []),
        "dispute_count": dispute_count,
        "evidence_level_counts": {
            EVIDENCE_LEVEL: len(semantic_spans),
            "glyphbox_level": 0,
        },
        "spans": semantic_spans,
    }
    return semantic_spans_doc


def _as_int(value, window_id) -> int:
    """把窗口切分区间端点转为整数，非法即拒绝。"""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("SCH_002: 窗口 %r 区间端点非整数: %r" % (window_id, value))
    return value
