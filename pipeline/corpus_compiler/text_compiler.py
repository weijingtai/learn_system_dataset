"""M3 纯函数：电子文本切分与 SourceSpan 产出（G7-RULINGS 第 78 条、act/01）。

本模块仅包含纯函数：
- 零外部网络调用（P6）
- 不访问 Ledger、不写入文件
- 绝不污染全局 yaml.SafeDumper（第 88 条）
- evidence_level 恒为 offset_level
"""

import hashlib
import re
import yaml

from .offset_anchors import (
    format_source_span_id,
    make_offset_anchor,
    map_cleaned_to_raw,
)

_RE_WORK = re.compile(r"^[a-z][a-z0-9_]*$")
_RE_EDITION = re.compile(r"^ed[0-9]{2}$")

# 切分规则：以句末标点（含后随空白/换行）或换行符为界切分
_SEGMENT_PATTERN = re.compile(
    r"[^。！？；\r\n]+(?:[。！？；]+[ \t\r\n]*|[\r\n]+)?|[。！？；]+[ \t\r\n]*|[\r\n]+"
)


def segment_cleaned_text(cleaned_text: str) -> list[tuple[int, int]]:
    """依据换行符与标点规则将清洗后文本切分为结构行/片段。

    约束：
        - 100% 覆盖全文，无缺口、无重叠，拼接后严格等于 cleaned_text
        - 若 cleaned_text 为空串，返回 []

    返回：
        list[tuple[int, int]]: 各片段在 cleaned_text 中的起始与结束偏移 [start, end)
    """
    if not cleaned_text:
        return []

    segments: list[tuple[int, int]] = []
    last_end = 0
    for m in _SEGMENT_PATTERN.finditer(cleaned_text):
        start, end = m.span()
        if start > last_end:
            segments.append((last_end, start))
        segments.append((start, end))
        last_end = end

    if last_end < len(cleaned_text):
        segments.append((last_end, len(cleaned_text)))

    return segments


def dump_yaml_bytes(doc: dict) -> bytes:
    """确定性序列化字典为 YAML UTF-8 字节。

    第 88 条护栏铁律：
        绝不向全局 SafeDumper 注册自定义 representer，绝不污染全局 yaml.SafeDumper。
        通过专用子类与私有 representers 字典保证完全隔离。
    """
    class _IsolatedDumper(yaml.SafeDumper):
        pass

    _IsolatedDumper.yaml_representers = dict(yaml.SafeDumper.yaml_representers)

    yaml_str = yaml.dump(
        doc,
        Dumper=_IsolatedDumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    return yaml_str.encode("utf-8")


def compile_offset_spans(
    *,
    work: str,
    edition: str,
    edition_part_artifact_id: str,
    raw_text_revision_id: str,
    raw_text: str,
    cleaned_text_revision_id: str,
    cleaned_text: str,
    patches: list[dict],
) -> dict:
    """切分 cleaned_text 并为每片构造偏移锚点与 SourceSpan（纯函数）。

    参数：
        work: 作品标识（匹配 ^[a-z][a-z0-9_]*$）
        edition: 版本标识（匹配 ^ed[0-9]{2}$）
        edition_part_artifact_id: 关联的 EditionPart artifact ID
        raw_text_revision_id: 原始文本修订 ID
        raw_text: 原始文本全文（不可为空）
        cleaned_text_revision_id: 清洗文本修订 ID
        cleaned_text: 清洗后文本全文
        patches: 确定性修补集列表

    返回：
        {
            "spans": spans,
            "spans_doc": spans_doc,
            "spans_bytes": spans_bytes,
            "spans_sha256": spans_sha256,
            "counts": counts,
        }

    异常：
        ValueError("SCH_002: ..."): 参数格式不符、raw_text 为空、补丁越界等
    """
    if not (isinstance(work, str) and _RE_WORK.match(work)):
        raise ValueError(f"SCH_002: 非法的 work 标识: {work!r}")
    if not (isinstance(edition, str) and _RE_EDITION.match(edition)):
        raise ValueError(f"SCH_002: 非法的 edition 标识: {edition!r}")
    if not isinstance(raw_text, str) or not raw_text:
        raise ValueError("SCH_002: raw_text 不能为空")
    if not isinstance(cleaned_text, str):
        raise ValueError("SCH_002: cleaned_text 必须为字符串")
    if not isinstance(edition_part_artifact_id, str) or not edition_part_artifact_id:
        raise ValueError("SCH_002: edition_part_artifact_id 不能为空")
    if not isinstance(raw_text_revision_id, str) or not raw_text_revision_id:
        raise ValueError("SCH_002: raw_text_revision_id 不能为空")
    if not isinstance(cleaned_text_revision_id, str) or not cleaned_text_revision_id:
        raise ValueError("SCH_002: cleaned_text_revision_id 不能为空")

    # 校验 patches 边界
    raw_len = len(raw_text)
    clean_len = len(cleaned_text)
    for p in patches:
        r_start = p.get("raw_start", -1)
        r_end = p.get("raw_end", -1)
        c_start = p.get("cleaned_start", -1)
        c_end = p.get("cleaned_end", -1)
        if r_start < 0 or r_end < r_start or r_end > raw_len:
            raise ValueError(f"SCH_002: 补丁原始偏移超出边界: [{r_start}, {r_end}) vs len={raw_len}")
        if c_start < 0 or c_end < c_start or c_end > clean_len:
            raise ValueError(f"SCH_002: 补丁清洗偏移超出边界: [{c_start}, {c_end}) vs len={clean_len}")

    segments = segment_cleaned_text(cleaned_text)
    spans: list[dict] = []

    for seq, (c_start, c_end) in enumerate(segments, start=1):
        span_text = cleaned_text[c_start:c_end]
        quote_sha256 = hashlib.sha256(span_text.encode("utf-8")).hexdigest()

        # 映射回 RawText 偏移区间
        raw_start, raw_end = map_cleaned_to_raw(patches, c_start, c_end)

        # 格式化稳定 SourceSpan ID（锚定冻结 RawText）
        span_id = format_source_span_id(work, edition, raw_start)

        # 构造标准 7 键锚点字典
        source_anchor = make_offset_anchor(
            raw_text_revision_id=raw_text_revision_id,
            raw_start=raw_start,
            raw_end=raw_end,
            cleaned_text_revision_id=cleaned_text_revision_id,
            start_offset=c_start,
            end_offset=c_end,
            quote=span_text,
        )

        # 8 个 Span 键严格有序
        span = {
            "span_id": span_id,
            "sequence": seq,
            "start_offset": c_start,
            "end_offset": c_end,
            "text": span_text,
            "quote_sha256": quote_sha256,
            "evidence_level": "offset_level",
            "source_anchor": source_anchor,
        }
        spans.append(span)

    # 7 个顶层键严格有序
    spans_doc = {
        "work": work,
        "source_id": f"src_{work}_{edition}",
        "edition_part_artifact_id": edition_part_artifact_id,
        "evidence_level": "offset_level",
        "content_status": "machine_extracted",
        "span_count": len(spans),
        "spans": spans,
    }

    spans_bytes = dump_yaml_bytes(spans_doc)
    spans_sha256 = hashlib.sha256(spans_bytes).hexdigest()

    counts = {
        "spans": len(spans),
        "evidence_level_counts": {
            "offset_level": len(spans),
            "glyphbox_level": 0,
        },
    }

    return {
        "spans": spans,
        "spans_doc": spans_doc,
        "spans_bytes": spans_bytes,
        "spans_sha256": spans_sha256,
        "counts": counts,
    }
