"""M7 增量汇编：独立配对层（act/impl-07/22 contract 二；CHARTER §3.1）。

**本文件是 M7 里唯一允许判断「哪些单元是同一件事」的地方。**
`incremental.py` 及其它任何代码都不许自己比对，只能调用 :func:`propose_pairs`。

本波（B）只允许**确定性**实现，三条可用依据：

1. 精确键相等（两侧声明的 ``collation_key`` 逐字相同）
2. 共享证据片段（两侧证据链含同一个 ``source_span_id``）
3. 同一已正式对象（两侧 ``entity_ref`` 非空且相同）

**禁止**：模糊文本相似度、编辑距离、任何阈值可调的打分；不得调用任何模型 API。
（文本「相等」比对只在 ``incremental.py`` 的 R07/R08 里做**逐字相等**判断，
那是规则表明确要求的一步，不是相似度。）

将来接模型建议：**只换这一个文件**，且模型结论只能落在
:attr:`PairCandidate.suggestion` 旁路字段——不得进入 Gate 判定、不得影响 ID 发号、
不得改变自动裁定结果。本波 ``suggestion`` 恒为 ``None``。
"""

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pipeline.assembly.canonical import nfc_key, sha256_hex
from pipeline.assembly.model import PairCandidate

#: ``collation_key`` 为 null / 缺失时的「无法配对」原因（CHARTER §8.2：如实返回，不许猜）
NOT_COMPARABLE_MISSING_COLLATION_KEY = "missing_collation_key"

_STRATEGY_RANK = {
    "exact_collation_key": 0,
    "same_formal_object": 1,
    "shared_evidence_span": 2,
}


def unit_key(unit: Dict[str, Any]) -> str:
    """单元的稳定标识（只由声明字段构成，不含输入下标）。"""
    return "%s|%s|%s" % (
        unit.get("source_id") or "-",
        unit.get("entity_ref") or "-",
        unit.get("collation_key") or "-",
    )


def make_unit(
    source_id: str,
    *,
    collation_key: Optional[str] = None,
    entity_ref: Optional[str] = None,
    present: bool = True,
    text: Optional[str] = None,
    text_sha256: Optional[str] = None,
    evidence_span_ids: Iterable[str] = (),
) -> Dict[str, Any]:
    """构造一个可比单元（只填声明字段；不做任何判断）。

    ``text_sha256`` = ``sha256(NFC 文本)``：视图一侧由 ``text`` 现算，基底一侧取 Snapshot
    断言里存的 ``text_sha256``，两者口径相同才能做**逐字相等**比对（不是相似度）。
    """
    digest = text_sha256
    if digest is None and text is not None:
        digest = sha256_hex(nfc_key(text).encode("utf-8"))
    return {
        "source_id": source_id,
        "collation_key": collation_key,
        "entity_ref": entity_ref,
        "present": bool(present),
        "text_sha256": digest,
        "evidence_span_ids": tuple(sorted(set(evidence_span_ids))),
    }


def units_of_view(candidate_set: dict, reviewed_edition: dict) -> List[Dict[str, Any]]:
    """从一份视图抽出可比单元（只抽取声明字段，不判断）。

    单元来源：``candidate_set.collation_units[]``（声明了哪些可比单元）
    与 ``candidate_set.assertions[]``（哪条断言落在该单元上、其证据片段与文本键）。
    """
    source_id = candidate_set.get("source_id")
    by_key: Dict[Any, Dict[str, Any]] = {}
    for index, entry in enumerate(candidate_set.get("collation_units") or []):
        key = entry.get("collation_key")
        by_key[_unit_group(key, index)] = make_unit(
            source_id,
            collation_key=key,
            present=bool(entry.get("present", True)),
        )
    for assertion in candidate_set.get("assertions") or []:
        key = assertion.get("collation_key")
        # 缺 collation_key 时**按断言各自成单元**：26 条无键断言就是 26 个「无法配对」的单元，
        # 不得因为键都是 None 而被折成一个（否则 not_comparable 计数会被静默压低）。
        group = _unit_group(key, None, entity_ref=assertion.get("assertion_id"))
        unit = by_key.get(group)
        if unit is None:
            unit = make_unit(source_id, collation_key=key)
            by_key[group] = unit
        unit["entity_ref"] = assertion.get("assertion_id")
        proposition = assertion.get("proposition")
        if proposition is not None:
            unit["text_sha256"] = sha256_hex(nfc_key(proposition).encode("utf-8"))
        spans = [
            ev.get("source_span_id")
            for ev in assertion.get("evidence") or []
            if ev.get("source_span_id")
        ]
        unit["evidence_span_ids"] = tuple(sorted(set(unit["evidence_span_ids"]) | set(spans)))
    return [by_key[key] for key in sorted(by_key, key=repr)]


def _unit_group(collation_key: Any, index: Optional[int], entity_ref: Optional[str] = None) -> tuple:
    """单元分组键：有声明键就按声明键合并，否则各自成组（不因键为 None 而合并）。"""
    if collation_key:
        return ("declared", collation_key)
    if entity_ref:
        return ("entity", entity_ref)
    return ("declared_unnamed", index)


def unpairable_units(units: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """如实列出**无法确定性配对**的单元（本波只可能因为缺 ``collation_key``）。

    CHARTER §8.2：真书路径上 ``collation_key`` 全为 null、``collation_units`` 键不存在，
    此时必须返回「无法配对」，**不许猜、不许回退到文本比对**，且要计数（不得静默跳过）。
    """
    return [
        {
            "source_id": unit.get("source_id"),
            "entity_ref": unit.get("entity_ref"),
            "collation_key": unit.get("collation_key"),
            "reason": NOT_COMPARABLE_MISSING_COLLATION_KEY,
        }
        for unit in units
        if not unit.get("collation_key")
    ]


def propose_pairs(
    left_units: Sequence[Dict[str, Any]],
    right_units: Sequence[Dict[str, Any]],
) -> List[PairCandidate]:
    """两个视图之间的配对候选（**确定性**；无模型、无相似度、无阈值）。

    只为三种依据成对；同一对命中多条依据时取最强的一条记录 ``strategy``，
    其余命中写进 ``shared``。输出按 ``(strategy, left_key, right_key)`` 升序，
    因此同一输入两次调用逐字节相同。
    """
    candidates: List[PairCandidate] = []
    for left in left_units:
        for right in right_units:
            strategies = []
            if left.get("collation_key") and left["collation_key"] == right.get("collation_key"):
                strategies.append("exact_collation_key")
            if left.get("entity_ref") and left["entity_ref"] == right.get("entity_ref"):
                strategies.append("same_formal_object")
            shared_spans = sorted(
                set(left.get("evidence_span_ids") or ()) & set(right.get("evidence_span_ids") or ())
            )
            if shared_spans:
                strategies.append("shared_evidence_span")
            if not strategies:
                continue
            strategies.sort(key=lambda s: _STRATEGY_RANK[s])
            candidates.append(
                PairCandidate(
                    left_key=unit_key(left),
                    right_key=unit_key(right),
                    strategy=strategies[0],
                    shared=tuple(strategies[1:] + shared_spans),
                    suggestion=None,
                )
            )
    candidates.sort(key=lambda c: (_STRATEGY_RANK[c.strategy], c.left_key, c.right_key))
    return candidates


def pair_index(pairs: Sequence[PairCandidate]) -> Dict[Tuple[str, str], PairCandidate]:
    """把候选列表转成 ``{(left_key, right_key): candidate}``（便于规则层查表）。"""
    return {(pair.left_key, pair.right_key): pair for pair in pairs}
