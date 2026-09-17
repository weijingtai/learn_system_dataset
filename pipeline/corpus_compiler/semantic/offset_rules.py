"""M3 语义层：模型切分窗口选择（act/04，G7-RULINGS 第 80 条）。

规则优先切分之后（结构 Span 已定），长度 ``>= model_min_chars``（默认 12）的片
段进入双模型边界提议；长度不足阈值的片段直接作为单语义片段，不送模型。

本模块为纯函数：零网络、零 Ledger、不写文件；只使用标准库 hashlib 与 re。
"""

import hashlib
import re

from pipeline.ledger import ids

# 结构片段 ID：ss_<work>_ed<NN>_o<NNNNNNN>；正则唯一权威出处为 pipeline.ledger.ids
# （第 85、102 条），本模块不自有形态。
_RE_SOURCE_SPAN_ID = re.compile(ids.SOURCE_SPAN_ID_OFFSET_PARTS)

# README §4.3 默认阈值
DEFAULT_MODEL_MIN_CHARS = 12


def select_text_windows(
    spans: list[dict],
    *,
    model_min_chars: int = DEFAULT_MODEL_MIN_CHARS,
) -> list[dict]:
    """按原顺序挑选需要模型切分的窗口（长度 >= ``model_min_chars`` 的片段）。

    参数：
        spans: 结构层 spans 列表（每条含 ``span_id``、``text``、``source_anchor``）。
        model_min_chars: 进入模型窗口的最小字符数（默认 12）。

    返回：
        窗口列表，每项键序固定为
        ``window_id, span_id, text, text_sha256, raw_start, raw_end``；
        ``window_id`` 形如 ``<work>_w%03d``，编号在**入选序列上**从 1 连续递增。

    异常：
        ValueError("SCH_002: ...")：``span_id`` 形非法，无法推导 ``work`` 段。
    """
    windows: list[dict] = []

    for span in spans or []:
        text = span.get("text") or ""
        if len(text) < model_min_chars:
            continue

        anchor = span.get("source_anchor") or {}
        work = _work_from_span_id(span.get("span_id"))
        windows.append(
            {
                "window_id": "%s_w%03d" % (work, len(windows) + 1),
                "span_id": span.get("span_id"),
                "text": text,
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "raw_start": anchor.get("raw_start"),
                "raw_end": anchor.get("raw_end"),
            }
        )

    return windows


def _work_from_span_id(span_id) -> str:
    """从结构片段 ID 的 ``work`` 段推导作品标识（窗口 ID 前缀）。"""
    match = _RE_SOURCE_SPAN_ID.match(span_id) if isinstance(span_id, str) else None
    if match is None:
        raise ValueError("SCH_002: span_id 形非法，无法推导 work 段: %r" % (span_id,))
    return match.group(1)
