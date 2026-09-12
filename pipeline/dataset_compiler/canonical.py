"""规范化 JSON 与内容哈希（规格 §16 哈希无环、D10）。

纯函数：不读文件、不访问 Ledger、不取时间、不用随机数。

- ``canonical_bytes``：``sort_keys=True, ensure_ascii=False, separators=(",", ":"),
  allow_nan=False``，UTF-8 编码；NaN/Infinity 触发 ``ValueError``。
- ``normalized_sha256``：先递归剥离所有以 ``artifact_revision_id`` 结尾的键，
  使两个独立 Ledger 的编译结果可在忽略修订号后比对。
"""

import hashlib
import json

from pipeline.ledger.errors import SchemaViolation

# 需要剥离的修订号键后缀（"artifact_revision_id" 本身即以此结尾）
_REVISION_KEY_SUFFIX = "artifact_revision_id"


def canonical_bytes(obj):
    """把 ``obj`` 序列化为规范化 JSON 字节（UTF-8，键序稳定）。"""
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data):
    """返回 ``data`` 的十六进制 SHA-256；非 bytes → ``SchemaViolation(SCH_001)``。"""
    if not isinstance(data, (bytes, bytearray)):
        raise SchemaViolation("sha256_hex 需要 bytes", code="SCH_001")
    return hashlib.sha256(bytes(data)).hexdigest()


def quote_sha256(text):
    """返回 ``text``（UTF-8）的十六进制 SHA-256。"""
    return sha256_hex(text.encode("utf-8"))


def strip_revision_ids(obj):
    """递归深拷贝并删除所有以 ``artifact_revision_id`` 结尾的键；不修改入参。"""
    if isinstance(obj, dict):
        return {
            key: strip_revision_ids(value)
            for key, value in obj.items()
            if not (isinstance(key, str) and key.endswith(_REVISION_KEY_SUFFIX))
        }
    if isinstance(obj, list):
        return [strip_revision_ids(item) for item in obj]
    return obj


def normalized_sha256(obj):
    """剥离修订号后的规范化 JSON 的 SHA-256。"""
    return sha256_hex(canonical_bytes(strip_revision_ids(obj)))
