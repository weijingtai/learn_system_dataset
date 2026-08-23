"""gujiorc.core.anomaly — 异常版面登记（星盘/环形图画式版面）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import get_root, ensure_struct


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
        if page is not None and item.get("page") != page:
            continue
        if layout_type is not None and item.get("layout_type") != layout_type:
            continue
        out.append(item)
    if last and last > 0:
        out = out[-last:]
    return out