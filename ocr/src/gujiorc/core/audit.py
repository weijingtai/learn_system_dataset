"""gujiorc.core.audit — 全局审计日志（append-only，跨页可追溯）。

每行一个 JSON 事件，写 {OCR_ROOT}/logs/audit.jsonl。
铁律：只追加、永不修改/删除已有行。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .paths import get_root, ensure_struct

ACTIONS = {"fix", "segment_new", "rotate", "verify",
           "group_create", "group_add", "group_define", "group_remove", "export"}


def log_event(action: str, *, actor: str, page: str = "",
              char_id: str = "", **fields) -> Path:
    """追加一条审计事件，返回 audit.jsonl 路径。

    actor: "cli" | "web" | "colab"
    fields: 任意附加键值（from/to/source/note 等，值必须是可 json 序列化的简单类型）
    action 不在 ACTIONS 里 → raise ValueError
    """
    if action not in ACTIONS:
        raise ValueError(f"action {action!r} 不在允许列表中")
    event = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "actor": actor,
        "action": action,
        "page": page,
        "char_id": char_id,
        **fields,
    }
    path = ensure_struct()["logs"] / "audit.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return path


def read_events(*, page: str | None = None, action: str | None = None,
                last: int = 0) -> list[dict]:
    """读审计事件。page/action 过滤；last=N 只返回最近 N 条（保持时间正序）。
    文件不存在返回 []。坏行（非 JSON）跳过，不抛异常。
    """
    path = ensure_struct()["logs"] / "audit.jsonl"
    if not path.exists():
        return []
    out: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if page is not None and item.get("page") != page:
            continue
        if action is not None and item.get("action") != action:
            continue
        out.append(item)
    if last and last > 0:
        out = out[-last:]
    return out