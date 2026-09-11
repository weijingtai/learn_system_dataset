#!/usr/bin/env python3
"""nchash/v2 参考编码器（规格侧预言机）。

依据：openspec/annotation-community/DESIGN.md §7.2。
用途：生成 fixtures/community/content_hash_cases.json 的 expected_canonical_hex 与 expected_hash；
      主 Agent 验收时用它复算执行者实现的输出。它不是 SERVER/CLIENT 的生产实现，
      两端实现必须各自独立编写，测试只比对 fixture 中的字面量。

只用标准库。任何违反 §7.2 的输入都抛 ValueError（不静默修正）。
"""
from __future__ import annotations

import hashlib
import json
import sys
from typing import Any

DOMAIN = b"nchash/v2\n"
INT_MAX = 2**53 - 1

# ---------------------------------------------------------------- E 编码 ---

def _utf8(s: str) -> bytes:
    try:
        return s.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:  # 孤立 surrogate
        raise ValueError(f"孤立 surrogate 不允许: {exc}") from exc


def encode(value: Any) -> bytes:
    """E(value)：长度前缀递归字节编码。"""
    if value is None:
        return b"n;"
    if value is True:
        return b"b1;"
    if value is False:
        return b"b0;"
    if isinstance(value, int):
        if value > INT_MAX or value < -INT_MAX:
            raise ValueError(f"整数超出 ±(2^53-1): {value}")
        return b"i" + str(value).encode("ascii") + b";"
    if isinstance(value, float):
        raise ValueError(f"拒绝浮点/NaN/Infinity: {value!r}")
    if isinstance(value, str):
        raw = _utf8(value)
        return b"s" + str(len(raw)).encode("ascii") + b":" + raw
    if isinstance(value, list):
        out = b"a" + str(len(value)).encode("ascii") + b":"
        for item in value:
            out += encode(item)
        return out
    if isinstance(value, dict):
        keys = list(value.keys())
        for k in keys:
            if not isinstance(k, str):
                raise ValueError(f"对象键必须是字符串: {k!r}")
        if len(set(keys)) != len(keys):
            raise ValueError("重复键")
        out = b"o" + str(len(keys)).encode("ascii") + b":"
        for k in sorted(keys, key=_utf8):
            out += encode(k) + encode(value[k])
        return out
    raise ValueError(f"不支持的类型: {type(value).__name__}")


# ------------------------------------------------------- snapshot 规范化 ---

SNAPSHOT_FIELDS = ("title", "markdown", "attachment_refs", "mentions", "bindings", "change_summary")
ATTACHMENT_FIELDS = ("attachment_id", "object_version", "content_digest", "alt", "caption")
MENTION_FIELDS = ("user_id", "display_name", "start_offset", "length")
BINDING_FIELDS = ("relation", "target_kind", "target_ref", "anchor")
ANCHOR_FIELDS = ("anchor_id", "target_type", "entity_id", "artifact_revision_id", "release_id", "context", "selector")


def _require_exact_keys(obj: dict, fields: tuple, what: str) -> None:
    extra = set(obj) - set(fields)
    missing = set(fields) - set(obj)
    if extra:
        raise ValueError(f"{what} 含未知字段: {sorted(extra)}")
    if missing:
        raise ValueError(f"{what} 缺字段（Schema 应已补默认值）: {sorted(missing)}")


def _reject_duplicates(items: list, what: str) -> None:
    seen = set()
    for it in items:
        e = encode(it)
        if e in seen:
            raise ValueError(f"{what} 含完全相同的重复项（应在保存前被 Schema 拒绝）")
        seen.add(e)


def normalize_snapshot(snapshot: dict) -> dict:
    """按 §7.2 规范化：补默认值、校验字段全集、三类顶层数组按规范顺序排序、拒绝重复。"""
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot 必须是对象")
    s = dict(snapshot)
    s.setdefault("title", "")
    s.setdefault("markdown", "")
    s.setdefault("change_summary", "")
    s.setdefault("attachment_refs", [])
    s.setdefault("mentions", [])
    s.setdefault("bindings", [])
    _require_exact_keys(s, SNAPSHOT_FIELDS, "snapshot")
    for f in ("title", "markdown", "change_summary"):
        if not isinstance(s[f], str):
            raise ValueError(f"{f} 必须是字符串")

    atts = []
    for a in s["attachment_refs"]:
        a = dict(a)
        a.setdefault("alt", "")
        a.setdefault("caption", "")
        _require_exact_keys(a, ATTACHMENT_FIELDS, "attachment")
        atts.append(a)
    _reject_duplicates(atts, "attachment_refs")
    atts.sort(key=lambda a: (_utf8(a["attachment_id"]), encode(a)))

    mens = []
    for m in s["mentions"]:
        m = dict(m)
        _require_exact_keys(m, MENTION_FIELDS, "mention")
        if not isinstance(m["start_offset"], int) or not isinstance(m["length"], int) or isinstance(m["start_offset"], bool):
            raise ValueError("mention 的 start_offset/length 必须是整数")
        mens.append(m)
    _reject_duplicates(mens, "mentions")
    mens.sort(key=lambda m: (m["start_offset"], m["length"], _utf8(m["user_id"]), encode(m)))

    binds = []
    for b in s["bindings"]:
        b = dict(b)
        b.setdefault("anchor", None)
        _require_exact_keys(b, BINDING_FIELDS, "binding")
        if b["anchor"] is not None:
            anc = dict(b["anchor"])
            _require_exact_keys(anc, ANCHOR_FIELDS, "anchor")
            b["anchor"] = anc  # selector.ranges 等嵌套有序数组保持原顺序，不递归排序
        binds.append(b)
    _reject_duplicates(binds, "bindings")
    binds.sort(key=lambda b: encode(b))

    return {
        "title": s["title"],
        "markdown": s["markdown"],
        "attachment_refs": atts,
        "mentions": mens,
        "bindings": binds,
        "change_summary": s["change_summary"],
    }


def canonical_bytes(snapshot: dict) -> bytes:
    return encode(normalize_snapshot(snapshot))


def content_hash(snapshot: dict) -> str:
    return hashlib.sha256(DOMAIN + canonical_bytes(snapshot)).hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write("usage: nchash_reference.py <snapshot.json>\n")
        return 2
    snap = json.loads(open(argv[1], encoding="utf-8").read())
    print(canonical_bytes(snap).hex())
    print(content_hash(snap))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
