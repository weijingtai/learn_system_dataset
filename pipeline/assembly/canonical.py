"""M7 规范化与确定性哈希/提案键生成（spec §15, §8.1）。"""

import hashlib
import json
import re
import unicodedata

from pipeline.ledger.errors import InvalidIdentifier, SchemaViolation

# 提案类型闭集
PROPOSAL_KINDS = ("merge", "alias", "conflict", "evidence")

# 关系类型闭集
RELATION_KINDS = (
    "attached",
    "alias_of",
    "distinct_from",
    "merged_into",
    "alignment",
    "variant_reading",
    "addition",
    "omission",
)

_VALID_KINDS = frozenset(PROPOSAL_KINDS + RELATION_KINDS)
_WORK_KEY_RE = re.compile(r"^src_([a-z][a-z0-9]*)_ed([0-9]{2})$")


def canonical_json(obj) -> bytes:
    """按规范格式序列化 JSON 字节（含尾部换行，UTF-8）。"""
    dumped = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return (dumped + "\n").encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """计算字节数据的 SHA256 十六进制摘要。"""
    return hashlib.sha256(data).hexdigest()


def content_sha256(obj) -> str:
    """计算 Python 对象的规范 JSON SHA256 十六进制摘要。"""
    return sha256_hex(canonical_json(obj))


def nfc_key(text: str) -> str:
    """将文本规范化为 NFC 形式并去除首尾空白字符。非字符串抛 SchemaViolation(SCH_002)。"""
    if not isinstance(text, str):
        raise SchemaViolation(
            "nfc_key 要求输入必须为字符串，收到: %r" % (type(text),),
            code="SCH_002",
        )
    return unicodedata.normalize("NFC", text).strip()


def make_key(kind: str, subject_tuple) -> str:
    """生成形如 ``<kind>:<hash[:32]>`` 的提案或关系稳定键。kind 越界抛 SchemaViolation(SCH_002)。"""
    if kind not in _VALID_KINDS:
        raise SchemaViolation("非法提案/关系 kind: %r" % (kind,), code="SCH_002")
    return "%s:%s" % (kind, content_sha256(list(subject_tuple))[:32])


def work_key(source_id: str) -> str:
    """从 source_id 提取作品键（正则第 1 组）。不匹配抛 InvalidIdentifier(ID_001)。"""
    if not isinstance(source_id, str):
        raise InvalidIdentifier(
            "source_id 必须为字符串，收到: %r" % (type(source_id),), code="ID_001"
        )
    match = _WORK_KEY_RE.match(source_id)
    if match is None:
        raise InvalidIdentifier(
            "source_id 不符合 ^src_([a-z][a-z0-9]*)_ed([0-9]{2})$: %r"
            % (source_id,),
            code="ID_001",
        )
    return match.group(1)
