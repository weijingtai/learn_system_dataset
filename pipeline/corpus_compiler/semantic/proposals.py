"""M3 语义层：模型提议解析与比较（act/04）。

铁律：**绝不信任模型返回的文本**。``parse_proposal`` 只采信偏移，片段原文一律由程序从
``window_text[start:end]`` 切取；模型自带的 ``text`` 字段一律丢弃。

错误码（``error`` 字段）闭集与语义：
    ``None``      合法；
    ``json``      响应不是合法 UTF-8 JSON；
    ``shape``     结构不符（非映射、缺 ``segments`` 列表、项缺偏移键）；
    ``type``      偏移不是整数；
    ``range``     偏移越界或 ``start >= end``；
    ``empty``     ``segments`` 为空列表；
    ``gap``       内部缺口（前段终点与后段起点之间的文本未被覆盖）；
    ``overlap``   内部重叠；
    ``coverage``  未覆盖整个窗口（首端或尾端缺失）。

本模块为纯函数：零网络、零 Ledger、不写文件。
"""

import json

# 合法结果与非法结果的键序（契约固定）
_RESULT_KEYS = ("valid", "segments", "reasons", "error")

# 错误码闭集
ERROR_JSON = "json"
ERROR_SHAPE = "shape"
ERROR_TYPE = "type"
ERROR_RANGE = "range"
ERROR_EMPTY = "empty"
ERROR_GAP = "gap"
ERROR_OVERLAP = "overlap"
ERROR_COVERAGE = "coverage"

ERROR_CODES = (
    ERROR_JSON,
    ERROR_SHAPE,
    ERROR_TYPE,
    ERROR_RANGE,
    ERROR_EMPTY,
    ERROR_GAP,
    ERROR_OVERLAP,
    ERROR_COVERAGE,
)


def parse_proposal(response_bytes: bytes, window_text: str) -> dict:
    """解析一侧模型的切分响应。

    参数：
        response_bytes: 模型响应的原始字节（须为 UTF-8 JSON）。
        window_text: 本窗口原文，仅用于**程序侧**切取与覆盖校验。

    返回：
        ``{"valid": bool, "segments": [[start, end], ...], "reasons": [str], "error": ...}``
    """
    if not isinstance(window_text, str):
        return _invalid(ERROR_SHAPE, ["window_text 必须是字符串"])

    if isinstance(response_bytes, str):
        raw = response_bytes
    else:
        try:
            raw = bytes(response_bytes).decode("utf-8")
        except Exception:
            return _invalid(ERROR_JSON, ["响应不是 UTF-8 字节"])

    try:
        doc = json.loads(raw)
    except Exception:
        return _invalid(ERROR_JSON, ["响应不是合法 JSON"])

    if not isinstance(doc, dict) or not isinstance(doc.get("segments"), list):
        return _invalid(ERROR_SHAPE, ["响应必须是含 segments 列表的映射"])

    items = doc["segments"]
    if not items:
        return _invalid(ERROR_EMPTY, ["segments 为空，未切分任何片段"])

    segments: list[list[int]] = []
    reasons: list[str] = []

    for item in items:
        if not isinstance(item, dict):
            return _invalid(ERROR_SHAPE, ["segments 项必须是映射"])
        if "start_offset" not in item or "end_offset" not in item:
            return _invalid(ERROR_SHAPE, ["segments 项缺 start_offset/end_offset"])

        start = item["start_offset"]
        end = item["end_offset"]
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
        ):
            return _invalid(ERROR_TYPE, ["偏移必须是整数: %r, %r" % (start, end)])
        if start < 0 or end > len(window_text) or start >= end:
            return _invalid(
                ERROR_RANGE, ["偏移越界或区间非法: [%r, %r) 窗口长度 %d" % (start, end, len(window_text))]
            )

        segments.append([start, end])
        # 只取 reason 作说明，模型自带的 text 一律丢弃（绝不采信）
        reason = item.get("reason")
        reasons.append(reason if isinstance(reason, str) else "")

    if segments[0][0] != 0:
        return _invalid(
            ERROR_COVERAGE, ["窗口首端未被覆盖: 首段起点 %d" % segments[0][0]]
        )

    previous_end = segments[0][0]
    for start, end in segments:
        if start > previous_end:
            return _invalid(ERROR_GAP, ["内部缺口: [%d, %d)" % (previous_end, start)])
        if start < previous_end:
            return _invalid(ERROR_OVERLAP, ["内部重叠: [%d, %d)" % (start, previous_end)])
        previous_end = end

    if previous_end != len(window_text):
        return _invalid(
            ERROR_COVERAGE,
            ["窗口尾端未被覆盖: 覆盖至 %d，窗口长度 %d" % (previous_end, len(window_text))],
        )

    return {"valid": True, "segments": segments, "reasons": reasons, "error": None}


def compare_proposals(parsed_a: dict, parsed_b: dict) -> dict:
    """比较两侧提议：边界完全一致方可 ``agreed``，否则 ``disputed``。

    返回键序固定为 ``status, reason, segments``：
        - 两侧均有效且切分边界完全一致 → ``{"status": "agreed", "reason": None,
          "segments": parsed_a["segments"]}``；
        - 任一侧无效 → ``reason = "proposal_invalid"``，``segments = None``；
        - 边界不一致 → ``reason = "boundary_mismatch"``，``segments = None``。
    """
    if not (_is_valid(parsed_a) and _is_valid(parsed_b)):
        return {"status": "disputed", "reason": "proposal_invalid", "segments": None}

    if _boundaries(parsed_a) != _boundaries(parsed_b):
        return {"status": "disputed", "reason": "boundary_mismatch", "segments": None}

    return {"status": "agreed", "reason": None, "segments": parsed_a["segments"]}


def _is_valid(parsed) -> bool:
    """一侧提议是否有效（须为 parse_proposal 的合法结果）。"""
    return (
        isinstance(parsed, dict)
        and parsed.get("valid") is True
        and isinstance(parsed.get("segments"), list)
        and len(parsed["segments"]) > 0
    )


def _boundaries(parsed) -> list[tuple[int, int]]:
    """归一化切分边界，用于两侧比较。"""
    return [(int(start), int(end)) for start, end in parsed["segments"]]


def _invalid(error_code: str, reasons: list[str]) -> dict:
    """构造非法结果（键序与合法结果一致）。"""
    return {"valid": False, "segments": [], "reasons": reasons, "error": error_code}
