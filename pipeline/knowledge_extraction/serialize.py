"""规范化序列化（README §5.3 固化默认）。

只依赖标准库；不读写文件、不访问 Ledger。
"""

import hashlib
import json


def canonical_json(obj) -> bytes:
    """按固化默认序列化为字节：键排序、保留 Unicode、紧凑分隔、拒绝 NaN。"""
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """返回 ``data`` 的 SHA-256 十六进制摘要。"""
    return hashlib.sha256(data).hexdigest()
