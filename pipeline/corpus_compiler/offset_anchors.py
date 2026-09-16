"""M3 纯函数：偏移锚点计算与 DeterministicPatchSet 双向换算（G7-RULINGS 第 78 条、act/00）。

本模块仅使用标准库 hashlib 与 re，不依赖外部库、不访问 Ledger、不写文件。
严格遵守 P6（零网络调用）、P8（前缀严格限定为 ss_ 与 sem_）。
"""

import hashlib
import re

_RE_WORK = re.compile(r"^[a-z][a-z0-9_]*$")
_RE_EDITION = re.compile(r"^ed[0-9]{2}$")
_RE_SOURCE_SPAN_ID = re.compile(r"^ss_[a-z][a-z0-9_]*_ed[0-9]{2}_o[0-9]{7}$")
_RE_SEMANTIC_SPAN_ID = re.compile(r"^sem_[a-z][a-z0-9_]*_ed[0-9]{2}_o[0-9]{7}$")


def format_source_span_id(work: str, edition: str, raw_start: int) -> str:
    """格式化 SourceSpan ID，格式 ss_<work>_<edition>_o<NNNNNNN>。

    参数：
        work: 作品标识（匹配 ^[a-z][a-z0-9_]*$）
        edition: 版本标识（匹配 ^ed[0-9]{2}$）
        raw_start: 冻结 RawText 中的起始字符偏移（>= 0，7 位零填充）

    返回：
        严格符合 ^ss_[a-z][a-z0-9_]*_ed[0-9]{2}_o[0-9]{7}$ 的 ID 字符串

    异常：
        ValueError("SCH_002: 无效的 SourceSpan ID 参数")
    """
    if not (
        isinstance(work, str)
        and _RE_WORK.match(work)
        and isinstance(edition, str)
        and _RE_EDITION.match(edition)
        and isinstance(raw_start, int)
        and raw_start >= 0
    ):
        raise ValueError("SCH_002: 无效的 SourceSpan ID 参数")

    span_id = f"ss_{work}_{edition}_o{raw_start:07d}"
    if not _RE_SOURCE_SPAN_ID.match(span_id):
        raise ValueError("SCH_002: 无效的 SourceSpan ID 参数")
    return span_id


def format_semantic_span_id(work: str, edition: str, raw_start: int) -> str:
    """格式化 SemanticSpan ID，格式 sem_<work>_<edition>_o<NNNNNNN>。

    严格遵守 P8 铁律：除 ss_ 与 sem_ 外严禁引入任何新前缀。

    参数：
        work: 作品标识（匹配 ^[a-z][a-z0-9_]*$）
        edition: 版本标识（匹配 ^ed[0-9]{2}$）
        raw_start: 冻结 RawText 中的起始字符偏移（>= 0，7 位零填充）

    返回：
        严格符合 ^sem_[a-z][a-z0-9_]*_ed[0-9]{2}_o[0-9]{7}$ 的 ID 字符串

    异常：
        ValueError("SCH_002: 无效的 SemanticSpan ID 参数")
    """
    if not (
        isinstance(work, str)
        and _RE_WORK.match(work)
        and isinstance(edition, str)
        and _RE_EDITION.match(edition)
        and isinstance(raw_start, int)
        and raw_start >= 0
    ):
        raise ValueError("SCH_002: 无效的 SemanticSpan ID 参数")

    sem_id = f"sem_{work}_{edition}_o{raw_start:07d}"
    if not _RE_SEMANTIC_SPAN_ID.match(sem_id):
        raise ValueError("SCH_002: 无效的 SemanticSpan ID 参数")
    return sem_id


def _map_raw_point(sorted_patches: list[dict], pos: int, is_end: bool) -> int:
    """将 RawText 中的单个偏移点映射至 CleanedText。"""
    if not sorted_patches:
        return pos
    if pos < sorted_patches[0]["raw_start"]:
        return pos

    for i, p in enumerate(sorted_patches):
        p_r_start = p["raw_start"]
        p_r_end = p["raw_end"]
        p_c_start = p["cleaned_start"]
        p_c_end = p["cleaned_end"]

        # 落在当前补丁与前一补丁之间的未修改空白区
        if pos < p_r_start:
            prev = sorted_patches[i - 1]
            return prev["cleaned_end"] + (pos - prev["raw_end"])

        # 落在当前补丁区间内或边界上
        if p_r_start <= pos <= p_r_end:
            # 插入动作：在 raw 长度为 0
            if p_r_start == p_r_end:
                return p_c_start if is_end else p_c_end

            if pos == p_r_start:
                return p_c_start
            if pos == p_r_end:
                return p_c_end

            # 落在补丁内部
            raw_len = p_r_end - p_r_start
            cleaned_len = p_c_end - p_c_start
            if cleaned_len == 0:
                return p_c_start
            if raw_len == cleaned_len:
                return p_c_start + (pos - p_r_start)
            return p_c_start + round((pos - p_r_start) * cleaned_len / raw_len)

    # 落在最后一个补丁之后
    last = sorted_patches[-1]
    return last["cleaned_end"] + (pos - last["raw_end"])


def _map_cleaned_point(sorted_patches: list[dict], pos: int, is_end: bool) -> int:
    """将 CleanedText 中的单个偏移点逆向映射至 RawText。"""
    if not sorted_patches:
        return pos

    c_sorted = sorted(sorted_patches, key=lambda p: p["cleaned_start"])
    if pos < c_sorted[0]["cleaned_start"]:
        return pos

    for i, p in enumerate(c_sorted):
        p_r_start = p["raw_start"]
        p_r_end = p["raw_end"]
        p_c_start = p["cleaned_start"]
        p_c_end = p["cleaned_end"]

        # 落在当前补丁与前一补丁之间的未修改空白区
        if pos < p_c_start:
            prev = c_sorted[i - 1]
            return prev["raw_end"] + (pos - prev["cleaned_end"])

        # 落在当前补丁区间内或边界上
        if p_c_start <= pos <= p_c_end:
            # 删除动作：在 cleaned 长度为 0
            if p_c_start == p_c_end:
                return p_r_start if is_end else p_r_end

            if pos == p_c_start:
                return p_r_start
            if pos == p_c_end:
                return p_r_end

            # 落在补丁内部
            raw_len = p_r_end - p_r_start
            cleaned_len = p_c_end - p_c_start
            if raw_len == 0:
                return p_r_start
            if raw_len == cleaned_len:
                return p_r_start + (pos - p_c_start)
            return p_r_start + round((pos - p_c_start) * raw_len / cleaned_len)

    # 落在最后一个补丁之后
    last = c_sorted[-1]
    return last["raw_end"] + (pos - last["cleaned_end"])


def map_raw_to_cleaned(patches: list[dict], raw_start: int, raw_end: int) -> tuple[int, int]:
    """依据 patches 将原始文本区间映射为清洗文本区间（纯函数）。

    参数：
        patches: 确定性修补列表，每项含 raw_start, raw_end, cleaned_start, cleaned_end 等
        raw_start: 原始文本起始偏移
        raw_end: 原始文本结束偏移

    返回：
        tuple[int, int]: (cleaned_start, cleaned_end)

    异常：
        ValueError("SCH_002: 原始偏移区间非法"): 当 raw_start > raw_end 或 raw_start < 0
    """
    if not isinstance(raw_start, int) or not isinstance(raw_end, int):
        raise ValueError("SCH_002: 原始偏移区间非法")
    if raw_start < 0 or raw_start > raw_end:
        raise ValueError("SCH_002: 原始偏移区间非法")

    sorted_patches = sorted(patches, key=lambda p: p["raw_start"])
    if raw_start == raw_end:
        pt = _map_raw_point(sorted_patches, raw_start, is_end=False)
        return (pt, pt)

    c_start = _map_raw_point(sorted_patches, raw_start, is_end=False)
    c_end = _map_raw_point(sorted_patches, raw_end, is_end=True)
    return (c_start, c_end)


def map_cleaned_to_raw(patches: list[dict], cleaned_start: int, cleaned_end: int) -> tuple[int, int]:
    """逆向映射清洗文本区间至原始文本区间（纯函数，与 map_raw_to_cleaned 互逆）。

    参数：
        patches: 确定性修补列表
        cleaned_start: 清洗文本起始偏移
        cleaned_end: 清洗文本结束偏移

    返回：
        tuple[int, int]: (raw_start, raw_end)

    异常：
        ValueError("SCH_002: 清洗偏移区间非法"): 当 cleaned_start > cleaned_end 或 cleaned_start < 0
    """
    if not isinstance(cleaned_start, int) or not isinstance(cleaned_end, int):
        raise ValueError("SCH_002: 清洗偏移区间非法")
    if cleaned_start < 0 or cleaned_start > cleaned_end:
        raise ValueError("SCH_002: 清洗偏移区间非法")

    sorted_patches = sorted(patches, key=lambda p: p["cleaned_start"])
    if cleaned_start == cleaned_end:
        pt = _map_cleaned_point(sorted_patches, cleaned_start, is_end=False)
        return (pt, pt)

    r_start = _map_cleaned_point(sorted_patches, cleaned_start, is_end=False)
    r_end = _map_cleaned_point(sorted_patches, cleaned_end, is_end=True)
    return (r_start, r_end)


def make_offset_anchor(
    *,
    raw_text_revision_id: str,
    raw_start: int,
    raw_end: int,
    cleaned_text_revision_id: str,
    start_offset: int,
    end_offset: int,
    quote: str,
) -> dict:
    """构造标准 7 键有序偏移锚点字典。

    键序严格对齐：
        1. raw_text_revision_id
        2. raw_start
        3. raw_end
        4. cleaned_text_revision_id
        5. start_offset
        6. end_offset
        7. quote_sha256

    约束：
        len(quote) == end_offset - start_offset > 0
        raw_end > raw_start >= 0
        不满足抛出 ValueError("SCH_002: 锚点引文或区间非法")
    """
    if (
        not isinstance(raw_text_revision_id, str)
        or not raw_text_revision_id
        or not isinstance(cleaned_text_revision_id, str)
        or not cleaned_text_revision_id
        or not isinstance(quote, str)
        or not isinstance(raw_start, int)
        or not isinstance(raw_end, int)
        or not isinstance(start_offset, int)
        or not isinstance(end_offset, int)
        or raw_start < 0
        or raw_end <= raw_start
        or start_offset < 0
        or end_offset <= start_offset
        or len(quote) != (end_offset - start_offset)
    ):
        raise ValueError("SCH_002: 锚点引文或区间非法")

    quote_sha256 = hashlib.sha256(quote.encode("utf-8")).hexdigest()

    anchor = {
        "raw_text_revision_id": raw_text_revision_id,
        "raw_start": raw_start,
        "raw_end": raw_end,
        "cleaned_text_revision_id": cleaned_text_revision_id,
        "start_offset": start_offset,
        "end_offset": end_offset,
        "quote_sha256": quote_sha256,
    }
    return anchor


def verify_anchor(
    *,
    raw_text: str,
    cleaned_text: str,
    patches: list[dict],
    anchor: dict,
) -> tuple[bool, str]:
    """验证锚点内部一致性。

    检查：
        (a) quote_sha256 == sha256(cleaned_text[start_offset:end_offset])
        (b) map_raw_to_cleaned(patches, raw_start, raw_end) == (start_offset, end_offset)
        (c) map_cleaned_to_raw(patches, start_offset, end_offset) == (raw_start, raw_end)

    返回：
        (True, "") 或 (False, <原因说明>)
    """
    required_keys = [
        "raw_text_revision_id",
        "raw_start",
        "raw_end",
        "cleaned_text_revision_id",
        "start_offset",
        "end_offset",
        "quote_sha256",
    ]
    for k in required_keys:
        if k not in anchor:
            return False, f"缺少锚点键: {k}"

    start_offset = anchor["start_offset"]
    end_offset = anchor["end_offset"]
    raw_start = anchor["raw_start"]
    raw_end = anchor["raw_end"]
    expected_hash = anchor["quote_sha256"]

    if start_offset < 0 or end_offset > len(cleaned_text) or start_offset >= end_offset:
        return False, f"清洗偏移超出范围: [{start_offset}, {end_offset})"

    cleaned_slice = cleaned_text[start_offset:end_offset]
    actual_hash = hashlib.sha256(cleaned_slice.encode("utf-8")).hexdigest()
    if actual_hash != expected_hash:
        return False, f"引文哈希不符: 期望 {expected_hash}, 实际 {actual_hash}"

    try:
        mapped_cleaned = map_raw_to_cleaned(patches, raw_start, raw_end)
        if mapped_cleaned != (start_offset, end_offset):
            return (
                False,
                f"原始到清洗偏移映射不符: 换算结果 {mapped_cleaned}, 锚点记录 {(start_offset, end_offset)}",
            )
    except Exception as e:
        return False, f"原始到清洗偏移换算异常: {e}"

    try:
        mapped_raw = map_cleaned_to_raw(patches, start_offset, end_offset)
        if mapped_raw != (raw_start, raw_end):
            return (
                False,
                f"清洗到原始偏移逆向映射不符: 换算结果 {mapped_raw}, 锚点记录 {(raw_start, raw_end)}",
            )
    except Exception as e:
        return False, f"清洗到原始偏移逆向换算异常: {e}"

    return True, ""
