"""标识生成与校验（规格 §8.1）。

前缀与正则逐字来自 §8.1；UUIDv4 家族统一使用 ``uuid.uuid4().hex``（32 位全小写
十六进制）；人工闭集家族沿用既定位数。本模块不新增任何前缀。

第 78、80、100、102 条在本模块登记两处补充：片段 ID 的偏移形态
``ss_<work>_ed<NN>_o<NNNNNNN>`` 与 ``sem_`` 家族（本次只登记偏移形态）。
本模块是 ``<work>`` / ``<edition>`` 段与全部片段 ID 形态的**唯一权威出处**，
其他模块一律从此导入，不得自有正则（第 85、102 条）。
"""

import re
import uuid

from .errors import InvalidIdentifier

# 命名空间段（第 102 条 Q1）：片段 ID 的 ``<work>`` 取自 ``source_id``
# （``src_<work>_ed<NN>``）；允许下划线会使 ``_ed`` 分段产生歧义，故一律禁止。
WORK = r"[a-z][a-z0-9]*"
EDITION = r"ed[0-9]{2}"

# 20 个前缀家族：键为家族名，值为完整正则（^…$），逐字按 §8.1（含第 78、80 条形态）
PATTERNS = {
    "artifact_id": r"^art_[0-9a-f]{32}$",
    "artifact_revision_id": r"^rev_[0-9a-f]{32}$",
    "processing_run_id": r"^prun_[0-9a-f]{32}$",
    "step_run_id": r"^srun_[0-9a-f]{32}$",
    "stage_package_id": r"^pkg_m[1-8]_[0-9a-f]{32}$",
    "release_id": r"^rel_[0-9a-f]{32}$",
    "school_id": r"^sch_[a-z][a-z0-9]*_[0-9]{3}$",
    "school_view_id": r"^sv_[0-9a-f]{32}$",
    "conflict_group_id": r"^cg_[0-9a-f]{32}$",
    "pattern_id": r"^pat_[a-z][a-z0-9]*_[0-9]{6}$",
    "entry_id": r"^ent_[0-9a-f]{32}$",
    "source_id": r"^src_%s_%s$" % (WORK, EDITION),
    # 第 78 条：无页码来源的片段 ID 为 ss_<work>_ed<NN>_o<NNNNNNN>，与页码形态共存
    # （第 100 条 D3）；页码形态逐字保持不变。
    "source_span_id": r"^ss_%s_%s_(?:p[0-9]{4}_s[0-9]{2}|o[0-9]{7})$" % (WORK, EDITION),
    # 第 80 条 + 第 102 条 Q2：sem_ 本次只登记偏移形态；页码形态的序号位数
    # （第 80 条为 3 位、登记册 §3.6 为 2 位）留待第二版扫描本启用时另行裁定。
    "semantic_span_id": r"^sem_%s_%s_o[0-9]{7}$" % (WORK, EDITION),
    "knowledge_unit_id": r"^ku_[a-z][a-z0-9]*_[0-9]{6}$",
    "assertion_id": r"^as_[a-z][a-z0-9]*_[0-9]{6}$",
    "proposition_id": r"^pr_[a-z][a-z0-9]*_[0-9]{6}$",
    "shared_concept_id": r"^co_shared_[a-z][a-z0-9]*_[0-9]{2}$",
    "technique_concept_id": r"^co_[a-z][a-z0-9]*_[0-9]{6}$",
    "homograph_anchor_id": r"^hg_[0-9]{4}$",
}

# 需要分段捕获的调用方（独立结构 Gate、语义窗口选择）从此取正则，保证与 PATTERNS
# 同源（第 85、102 条）；三段依次为 work、edition、7 位偏移。
SOURCE_SPAN_ID_OFFSET_PARTS = r"^ss_(%s)_(%s)_o([0-9]{7})$" % (WORK, EDITION)

# Stage 闭集（§8.1 第 3b 节：m1–m8，其他值非法）
STAGES = ("m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8")

# UUIDv4 家族的固定前缀
_UUID_PREFIXES = {
    "artifact_id": "art_",
    "artifact_revision_id": "rev_",
    "processing_run_id": "prun_",
    "step_run_id": "srun_",
    "release_id": "rel_",
    "school_view_id": "sv_",
    "conflict_group_id": "cg_",
    "entry_id": "ent_",
}

# 家族前缀（用于 kind_of 最长匹配）
_PREFIX_BY_KIND = {
    "artifact_id": "art_",
    "artifact_revision_id": "rev_",
    "processing_run_id": "prun_",
    "step_run_id": "srun_",
    "stage_package_id": "pkg_",
    "release_id": "rel_",
    "school_id": "sch_",
    "school_view_id": "sv_",
    "conflict_group_id": "cg_",
    "pattern_id": "pat_",
    "entry_id": "ent_",
    "source_id": "src_",
    "source_span_id": "ss_",
    "semantic_span_id": "sem_",
    "knowledge_unit_id": "ku_",
    "assertion_id": "as_",
    "proposition_id": "pr_",
    "shared_concept_id": "co_shared_",
    "technique_concept_id": "co_",
    "homograph_anchor_id": "hg_",
}

# 按前缀长度从长到短排序，保证 co_shared_ 先于 co_、prun_ 先于 pr_
_PREFIXES_BY_LENGTH = tuple(
    sorted(
        ((prefix, kind) for kind, prefix in _PREFIX_BY_KIND.items()),
        key=lambda item: len(item[0]),
        reverse=True,
    )
)

_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_WORK_RE = re.compile(r"^%s$" % WORK)
_EDITION_RE = re.compile(r"^%s$" % EDITION)


def is_hex32(s) -> bool:
    """判断 ``s`` 是否为 32 位全小写十六进制字符串。"""
    return isinstance(s, str) and _HEX32.match(s) is not None


def is_work(s) -> bool:
    """判断 ``s`` 是否为合法的 ``<work>`` 段（第 102 条 Q1：禁止下划线）。"""
    return isinstance(s, str) and _WORK_RE.match(s) is not None


def is_edition(s) -> bool:
    """判断 ``s`` 是否为合法的 ``<edition>`` 段（形如 ``ed01``）。"""
    return isinstance(s, str) and _EDITION_RE.match(s) is not None


def new_id(kind: str, stage: str | None = None) -> str:
    """按 ``kind`` 生成一个新标识（UUIDv4 家族用 ``uuid.uuid4().hex``）。

    ``stage_package_id`` 必须给定 ``stage`` 且属于 ``STAGES`` 闭集，否则
    ``InvalidIdentifier``（``ID_001``）。
    """
    if kind == "stage_package_id":
        if stage not in STAGES:
            raise InvalidIdentifier(
                "stage_package_id 需要合法 stage（m1–m8），收到: %r" % (stage,),
                code="ID_001",
            )
        return "pkg_%s_%s" % (stage, uuid.uuid4().hex)
    prefix = _UUID_PREFIXES.get(kind)
    if prefix is None:
        raise InvalidIdentifier(
            "new_id 不支持的 kind: %r" % (kind,), code="ID_001"
        )
    return prefix + uuid.uuid4().hex


def validate(kind: str, value: str) -> str:
    """校验 ``value`` 是否匹配 ``kind`` 家族的完整正则；不匹配抛 ``InvalidIdentifier``。"""
    pattern = PATTERNS.get(kind)
    if pattern is None or not isinstance(value, str) or re.match(pattern, value) is None:
        raise InvalidIdentifier(
            "标识非法（kind=%s, value=%r）" % (kind, value), code="ID_001"
        )
    return value


def kind_of(value: str) -> str | None:
    """按前缀最长匹配返回家族名；无匹配返回 ``None``。"""
    if not isinstance(value, str):
        return None
    for prefix, kind in _PREFIXES_BY_LENGTH:
        if value.startswith(prefix):
            return kind
    return None
