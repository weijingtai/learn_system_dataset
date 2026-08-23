"""gujiorc.core.anomaly — 异常版面登记（星盘/环形图画式版面）。

传统古籍除了行列排布的正文，还有星盘、环形图、表格这类**非行列版面**。
这类页面的字沿弧线或放射方向排布，PaddleOCR 的矩形检测框贴合不了，识别结果
基本是垃圾。这种页必须登记下来交人工处理，不能让垃圾识别静默进入语料。

本模块两件事：
- ``assess_layout()`` 判定一页是否为异常版面（写入侧的触发判据）
- ``register_anomaly()`` / ``list_anomalies()`` 登记与查询（logs/anomalies.jsonl）
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import get_root, ensure_struct

# 异常版面判据阈值。取自《三辰通载》前10页实测（已抹除背面透印后）：
# 正常竖排页 page_001/003~009 —— 均置信 0.95~0.97、低置信行 0~2.0%、
#                              单字行 0~6.1%、横排框 0~3.0%
# 盘面页     page_010        —— 均置信 0.63、低置信行 45.4%、
#                              单字行 28.6%、横排框 12.6%
# 阈值取两者之间，每项都留了数倍余量。
LOW_CONF = 0.6                  # 单行置信度低于此值算「低置信行」
MAX_LOW_CONF_RATIO = 0.20       # 低置信行占比上限
MAX_SINGLE_CHAR_RATIO = 0.15    # 单字行占比上限（盘面上多是孤立标注）
MAX_HORIZONTAL_RATIO = 0.07     # 横排框占比上限（竖排书里几乎不该有宽>高的框）
MIN_MEAN_CONF = 0.80            # 全页平均置信度下限
MIN_SIGNALS = 2                 # 至少几个信号同时命中才登记


def assess_layout(page) -> dict[str, Any] | None:
    """判定一页是否为需要人工处理的异常版面。

    返回 None 表示版面正常；否则返回 {layout_type, signals, metrics}。

    判据是「多信号投票」而非单一指标：任何单项都可能被个别噪声触发
    （正常页偶尔也有一两个横排框或低置信行），要求至少 ``MIN_SIGNALS`` 项
    同时命中，才判为异常版面。命中了哪几项一并记下，人工能看出为什么。
    """
    lines = list(getattr(page, "lines", None) or [])
    if not lines:
        # 一个字都没识别出来：可能是空白页，也可能是未处理的纯图页（星盘整页）。
        # 两者都需要人工确认一眼，不能静默跳过。
        return {
            "layout_type": "no_text",
            "signals": ["no_text"],
            "metrics": {"lines": 0},
        }

    n = len(lines)
    confs = [float(getattr(x, "conf", 0.0) or 0.0) for x in lines]
    mean_conf = sum(confs) / n
    low_conf_ratio = sum(1 for c in confs if c < LOW_CONF) / n
    single_ratio = sum(1 for x in lines if len((x.text or "").strip()) <= 1) / n
    horiz_ratio = sum(1 for x in lines if x.box["w"] >= x.box["h"]) / n

    signals = []
    if low_conf_ratio > MAX_LOW_CONF_RATIO:
        signals.append("low_conf_lines")
    if single_ratio > MAX_SINGLE_CHAR_RATIO:
        signals.append("many_single_char_boxes")
    if horiz_ratio > MAX_HORIZONTAL_RATIO:
        signals.append("mixed_orientation")
    if mean_conf < MIN_MEAN_CONF:
        signals.append("low_mean_conf")

    metrics = {
        "lines": n,
        "mean_conf": round(mean_conf, 3),
        "low_conf_ratio": round(low_conf_ratio, 3),
        "single_char_ratio": round(single_ratio, 3),
        "horizontal_ratio": round(horiz_ratio, 3),
    }
    if len(signals) < MIN_SIGNALS:
        return None
    return {"layout_type": "irregular_layout", "signals": signals, "metrics": metrics}


def register_anomaly(
    *,
    page: str,
    image: str,
    layout_type: str = "unknown_anomaly",
    det_box_count: int = 0,
    rec_texts_sample: list[str] | None = None,
    note: str = "",
    extra: dict[str, Any] | None = None,
) -> Path:
    event = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "page": page,
        "image": image,
        "layout_type": layout_type,
        "det_box_count": det_box_count,
        "rec_texts_sample": rec_texts_sample or [],
        "note": note,
        "extra": extra or {},
    }
    path = ensure_struct()["logs"] / "anomalies.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return path


def list_anomalies(
    page: str | None = None,
    layout_type: str | None = None,
    last: int = 0,
) -> list[dict[str, Any]]:
    """列出登记的异常版面。page/layout_type 为空（None 或空串）都表示不过滤。

    空串必须当作「不过滤」：CLI 的 `--page` 默认值是 `""`，若按字面过滤就永远
    匹配不到任何一页，于是写入侧明明登记了、读取侧却一直显示「暂无异常记录」。
    """
    path = ensure_struct()["logs"] / "anomalies.jsonl"
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if page and item.get("page") != page:
            continue
        if layout_type and item.get("layout_type") != layout_type:
            continue
        out.append(item)
    if last and last > 0:
        out = out[-last:]
    return out