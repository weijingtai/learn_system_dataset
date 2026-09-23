"""M7 增量编排（act/impl-07/24；规格逐字沿用 `act/05.yaml:18-40`）。

三个函数 + 一条等价判据：

- :func:`affected_closure` —— 触点 + 沿 `alias_of` / `distinct_from` / `merged_into`
  两端与 `conflict_groups` 同组成员**迭代到不动点**
- :func:`carry_forward` —— 基底里 `mode == "human"` 的裁定在本轮如何沿用
- :func:`assemble` —— 回流轮次 + 应用裁定 + 增量正确性断言（`rebuilt == affected`）
- :func:`knowledge_equivalent` —— `content_sha256` 相等

外加 D-14 的替换继承（:func:`view_modes` / :func:`carry_forward_proposals`）。

边界纪律：

- 本模块**不自己判断「哪些单元是同一件事」**（CHARTER §3.1）：一律读提案已声明的
  `targets` / `options` / `subject`，配对仍只经 :mod:`pipeline.assembly.matcher`。
- 本模块**不改** `matcher.py` / `incremental.py` / `apply.py` / `genesis.py` /
  `canonical.py` / `gate.py` / `inputs.py`，只调用。
- `incremental.py` 的 `_classify_modes` 是 D-14 替换识别的**单一口径**，这里直接复用，
  避免两套规则漂移（见回报「三处读法」）。
"""

import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from pipeline.assembly import apply as apply_module
from pipeline.assembly import incremental as incremental_module
from pipeline.assembly.canonical import canonical_json, content_sha256, sha256_hex, work_key
from pipeline.assembly.errors import AssemblyRefused

#: `report` 键序**逐字**（act/05.yaml:36；`round_proposal_keys` 为 ACT 26 二新增，只许追加在末尾）
REPORT_KEYS = (
    "affected_entity_ids",
    "rebuilt_entity_ids",
    "created_entity_ids",
    "untouched_count",
    "proposals_by_resolution",
    "rounds",
    "carried",
    "needs_review",
    "not_comparable_count",
    "round_proposal_keys",
    "dropped_proposal_keys",
    "dropped_relations",  # ACT 28（CHARTER §22.2）：随退役/合并删除的基底关系，只许追加在末尾
)

#: 闭包要沿其两端的三种关系（act/05.yaml:31）
CLOSURE_RELATION_KINDS = ("alias_of", "distinct_from", "merged_into")

#: 需要人工决定的提案状态
NEEDS_DECISION = ("human", "blocked")

#: 替换继承要过滤的提案类型（contract 三：provenance 未变的不再产生 merge/alias/conflict）
PROVENANCE_FILTERED_KINDS = ("merge", "alias", "conflict")

_COLLECTIONS = ("patterns", "concepts", "assertions", "school_views")


# --------------------------------------------------------------------------- 基础
def knowledge_equivalent(a_knowledge: dict, b_knowledge: dict) -> bool:
    """增量正确性的根本判据：两份知识快照的规范哈希相等。"""
    return content_sha256(a_knowledge) == content_sha256(b_knowledge)


def _view_parts(view: Dict[str, Any]) -> Tuple[Optional[str], dict, dict]:
    cset = view.get("candidate_set") or {}
    reviewed = view.get("reviewed_edition") or {}
    source_id = view.get("source_id") or cset.get("source_id")
    return source_id, cset, reviewed


def view_modes(base_knowledge: dict, views: Sequence[dict]) -> Dict[str, str]:
    """D-14：以 `(source_id, edition_part_ids 集合)` 识别 new / replacement / extension。

    直接复用 :func:`incremental_module._classify_modes`（单一口径，**不以 `stage_package_id` 识别**）。
    """
    return incremental_module._classify_modes(base_knowledge or {}, views)


def _concept_provenance_hash(candidate: dict) -> str:
    """与 `apply._concept_provenance` 同一口径的 concept provenance 哈希。

    口径：`content_sha256({"name": name_or_surface, "aliases": [...]})`。
    """
    return content_sha256(
        {
            "name": candidate.get("name") or candidate.get("surface"),
            "aliases": list(candidate.get("aliases") or []),
        }
    )


def _index_base(base: dict) -> Dict[str, Any]:
    index: Dict[str, Any] = {
        collection: {item[collection_key]: item for item in base.get(collection) or []}
        for collection, collection_key in (
            ("patterns", "pattern_id"),
            ("concepts", "concept_id"),
            ("assertions", "assertion_id"),
            ("school_views", "school_view_id"),
        )
    }
    index["conflict_groups"] = {
        item["conflict_group_id"]: item for item in base.get("conflict_groups") or []
    }
    return index


def _all_ids(index: Dict[str, Any]) -> Set[str]:
    return set().union(*(set(index[collection]) for collection in _COLLECTIONS))


def _work_key_or_none(source_id: Optional[str]) -> Optional[str]:
    try:
        return work_key(source_id) if source_id else None
    except Exception:
        return None


def _collation_contacts(index: Dict[str, Any], collation_key: Optional[str], wk: Optional[str]) -> Set[str]:
    """基底中同 `(work_key, collation_key)` 的 Assertion（精确键相等，不做配对判断）。"""
    if not collation_key:
        return set()
    out = set()
    for assertion_id, assertion in index["assertions"].items():
        if assertion.get("collation_key") != collation_key:
            continue
        if wk is not None:
            assertion_wk = _work_key_or_none(assertion.get("source_id"))
            if assertion_wk is not None and assertion_wk != wk:
                continue
        out.add(assertion_id)
    return out


def _candidate_index(views: Sequence[dict]) -> Dict[Tuple[str, str], dict]:
    """按**声明键**查视图候选（只查表，不做任何比对）。"""
    out: Dict[Tuple[str, str], dict] = {}
    for view in views:
        source_id, cset, _ = _view_parts(view)
        for pattern in cset.get("patterns") or []:
            for key in (pattern.get("pattern_id"), pattern.get("candidate_key")):
                if key and source_id:
                    out.setdefault((source_id, key), pattern)
        for candidate in list(cset.get("concept_mentions") or []) + list(
            cset.get("new_concept_candidates") or []
        ):
            for key in (
                candidate.get("concept_ref"),
                candidate.get("concept_id"),
                candidate.get("surface"),
                candidate.get("candidate_key"),
            ):
                if key and source_id:
                    out.setdefault((source_id, key), candidate)
    return out


def _declared_collation_keys(views: Sequence[dict]) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for view in views:
        source_id, cset, _ = _view_parts(view)
        keys = {
            unit.get("collation_key")
            for unit in cset.get("collation_units") or []
            if unit.get("present")
        }
        out[source_id] = {key for key in keys if key}
    return out


# --------------------------------------------------------------------------- 触点/闭包
def affected_closure(
    base_knowledge: dict,
    views: Sequence[dict],
    proposals: Sequence[dict],
    decisions: Sequence[dict],
) -> Dict[str, Any]:
    """触点 + 闭包（act/05.yaml:20-31）。

    返回 `{"affected": 升序, "created": [], "untouched": 升序}`。
    `created` 是调用方在**应用裁定之前**传入的空表（新建号由 `apply` 结果给出）。
    """
    base = base_knowledge or {}
    index = _index_base(base)
    all_ids = _all_ids(index)
    candidates = _candidate_index(views)
    declared = _declared_collation_keys(views)
    contacts: Set[str] = set()

    # ---- 提案触点
    for proposal in proposals:
        for target in proposal.get("targets") or []:
            if target in all_ids:
                contacts.add(target)
        subject = list(proposal.get("subject") or [])
        head = subject[0] if subject else None
        if head == "pattern":
            source_id = subject[1] if len(subject) > 1 else None
            key = subject[-1]
            if key in all_ids:
                contacts.add(key)
            for option in proposal.get("options") or []:
                if isinstance(option, str) and option.startswith("attach:"):
                    target_id = option.split(":", 1)[1]
                    if target_id in all_ids:
                        contacts.add(target_id)
            candidate = candidates.get((source_id, key))
            if candidate:
                concept_ref = candidate.get("concept_ref") or candidate.get("concept_id")
                if concept_ref in all_ids:
                    contacts.add(concept_ref)
        elif head == "concept":
            source_id = subject[1] if len(subject) > 1 else None
            key = subject[-1]
            if key in all_ids:
                contacts.add(key)
            candidate = candidates.get((source_id, key))
            if candidate:
                concept_id = candidate.get("concept_ref") or candidate.get("concept_id")
                if concept_id in all_ids:
                    contacts.add(concept_id)
        elif head == "collation" and len(subject) > 2:
            contacts |= _collation_contacts(
                index, subject[2], _work_key_or_none(subject[1])
            )
        elif head == "provenance_lost":
            entity_id = subject[-1]
            if entity_id in all_ids:
                contacts.add(entity_id)
                assertion = index["assertions"].get(entity_id)
                if assertion is not None:
                    contacts |= _collation_contacts(
                        index,
                        assertion.get("collation_key"),
                        _work_key_or_none(assertion.get("source_id")),
                    )
        elif head == "conflict_group":
            subject_entity = subject[1] if len(subject) > 1 else None
            if subject_entity in all_ids:
                contacts.add(subject_entity)
            for group in index["conflict_groups"].values():
                members = [m for m in group.get("member_school_view_ids") or []]
                if any(
                    index["school_views"].get(m, {}).get("subject_entity_id") == subject_entity
                    for m in members
                ):
                    contacts |= {m for m in members if m in all_ids}
                    # 同 (主体, school_id) 的基底 SchoolView 一并计入触点
                    pairs = {
                        (
                            index["school_views"][m].get("subject_entity_id"),
                            index["school_views"][m].get("school_id"),
                        )
                        for m in members
                        if m in index["school_views"]
                    }
                    for sv_id, sv in index["school_views"].items():
                        if (sv.get("subject_entity_id"), sv.get("school_id")) in pairs:
                            contacts.add(sv_id)

    # ---- 决定触点
    by_key = {proposal["proposal_key"]: proposal for proposal in proposals}
    for decision in decisions:
        proposal = by_key.get(decision.get("proposal_key"))
        for target in decision.get("target_entity_ids") or []:
            if target in all_ids:
                contacts.add(target)
        if proposal is not None and proposal.get("rule_id") == "R06":
            for group_id in decision.get("target_entity_ids") or []:
                group = index["conflict_groups"].get(group_id)
                if group is None:
                    continue
                contacts |= {
                    m for m in group.get("member_school_view_ids") or [] if m in all_ids
                }

    # ---- collation_units[present == false] 触点
    for view in views:
        source_id, cset, _ = _view_parts(view)
        for unit in cset.get("collation_units") or []:
            if unit.get("present"):
                continue
            contacts |= _collation_contacts(
                index, unit.get("collation_key"), _work_key_or_none(source_id)
            )

    # ---- 替换：provenance 哈希变化 / 被删除的对象自身
    try:
        modes = view_modes(base, views)
    except AssemblyRefused:
        modes = {}
    for view in views:
        source_id, cset, _ = _view_parts(view)
        if modes.get(source_id) != "replacement":
            continue
        for pattern_id, pattern in index["patterns"].items():
            provenance = [
                row for row in pattern.get("provenance") or [] if row.get("source_id") == source_id
            ]
            if not provenance:
                continue
            candidate = candidates.get((source_id, pattern_id))
            if candidate is None or content_sha256(candidate) != provenance[0].get("content_sha256"):
                contacts.add(pattern_id)
        for concept_id, concept in index["concepts"].items():
            provenance = [
                row for row in concept.get("provenance") or [] if row.get("source_id") == source_id
            ]
            if not provenance:
                continue
            candidate = candidates.get((source_id, concept_id))
            if candidate is None or _concept_provenance_hash(candidate) != provenance[0].get(
                "content_sha256"
            ):
                contacts.add(concept_id)
        for assertion_id, assertion in index["assertions"].items():
            if assertion.get("source_id") != source_id:
                continue
            collation_key = assertion.get("collation_key")
            if collation_key and collation_key not in declared.get(source_id, set()):
                contacts.add(assertion_id)

    # ---- 闭包（不动点）
    adjacency: Dict[str, Set[str]] = {}
    for rel in base.get("relations") or []:
        if rel.get("relation_kind") not in CLOSURE_RELATION_KINDS:
            continue
        left, right = rel.get("from_entity_id"), rel.get("to_entity_id")
        if left and right:
            adjacency.setdefault(left, set()).add(right)
            adjacency.setdefault(right, set()).add(left)
    for group in base.get("conflict_groups") or []:
        members = list(group.get("member_school_view_ids") or [])
        for member in members:
            adjacency.setdefault(member, set()).update(other for other in members if other != member)

    affected = {entity_id for entity_id in contacts if entity_id in all_ids}
    frontier = list(affected)
    while frontier:
        current = frontier.pop()
        for neighbour in adjacency.get(current, ()):
            if neighbour in all_ids and neighbour not in affected:
                affected.add(neighbour)
                frontier.append(neighbour)

    return {
        "affected": sorted(affected),
        "created": [],
        "untouched": sorted(all_ids - affected),
    }


# --------------------------------------------------------------------------- 裁定沿用
def carry_forward(base_knowledge: dict, views: Sequence[dict], proposals: Sequence[dict]) -> Dict[str, Any]:
    """基底 `mode == "human"` 的裁定在本轮的走向（act/05.yaml:32-35）。

    基底 human 裁定来自 `relations[].resolution` 与 `conflict_groups[].resolutions`；
    本轮**同键**提案仍为 `human` 且 `basis` 不同 → `needs_review`，否则 `carried`。
    基底未记录 basis（`relations[].resolution` 只记 mode/proposal_key）时无法证明未变，
    按保守口径判为 `needs_review`（见回报「三处读法」）。
    """
    base = base_knowledge or {}
    base_basis: Dict[str, Optional[str]] = {}
    for rel in base.get("relations") or []:
        resolution = rel.get("resolution") or {}
        if resolution.get("mode") == "human" and resolution.get("proposal_key"):
            base_basis.setdefault(resolution["proposal_key"], resolution.get("basis_sha256"))
    for group in base.get("conflict_groups") or []:
        for resolution in group.get("resolutions") or []:
            if resolution.get("mode") == "human" and resolution.get("proposal_key"):
                base_basis.setdefault(resolution["proposal_key"], resolution.get("basis_sha256"))

    current = {proposal["proposal_key"]: proposal for proposal in proposals}
    carried: List[str] = []
    needs_review: List[str] = []
    for proposal_key in sorted(base_basis):
        proposal = current.get(proposal_key)
        if proposal is None or proposal.get("resolution") != "human":
            carried.append(proposal_key)
            continue
        if proposal.get("basis_sha256") == base_basis[proposal_key]:
            carried.append(proposal_key)
        else:
            needs_review.append(proposal_key)
    return {"carried": sorted(carried), "needs_review": sorted(needs_review)}


# --------------------------------------------------------------------------- 替换继承
def carry_forward_proposals(
    base_knowledge: dict,
    views: Sequence[dict],
    proposals: Sequence[dict],
    *,
    modes: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """D-14 替换继承：provenance 未变的对象本轮不再产生 merge/alias/conflict 提案。

    「未变」的判据（只用已声明字段与哈希，不做配对判断）：

    - Pattern：基底 provenance 的 `content_sha256` 与视图候选的规范哈希逐字相同
    - Concept：按 `apply._concept_provenance` 同一口径重算后相同
    - Assertion：其 `collation_key` 在本轮视图的 `collation_units` 里仍声明 present

    返回 `{"dropped": 升序, "kept": 升序}`。
    """
    base = base_knowledge or {}
    views = list(views)
    modes = view_modes(base, views) if modes is None else modes
    index = _index_base(base)
    candidates = _candidate_index(views)
    declared = _declared_collation_keys(views)

    unchanged: Set[str] = set()
    for view in views:
        source_id, _, _ = _view_parts(view)
        if modes.get(source_id) != "replacement":
            continue
        for pattern_id, pattern in index["patterns"].items():
            provenance = [
                row for row in pattern.get("provenance") or [] if row.get("source_id") == source_id
            ]
            if not provenance:
                continue
            candidate = candidates.get((source_id, pattern_id))
            if candidate is not None and content_sha256(candidate) == provenance[0].get(
                "content_sha256"
            ):
                unchanged.add(pattern_id)
        for concept_id, concept in index["concepts"].items():
            provenance = [
                row for row in concept.get("provenance") or [] if row.get("source_id") == source_id
            ]
            if not provenance:
                continue
            candidate = candidates.get((source_id, concept_id))
            if candidate is not None and _concept_provenance_hash(candidate) == provenance[0].get(
                "content_sha256"
            ):
                unchanged.add(concept_id)
        for assertion_id, assertion in index["assertions"].items():
            if assertion.get("source_id") != source_id:
                continue
            collation_key = assertion.get("collation_key")
            if collation_key and collation_key in declared.get(source_id, set()):
                unchanged.add(assertion_id)

    dropped: List[str] = []
    kept: List[str] = []
    for proposal in proposals:
        subject = list(proposal.get("subject") or [])
        head = subject[0] if subject else None
        object_id = subject[-1] if head in ("pattern", "concept", "provenance_lost") else None
        if (
            object_id is not None
            and object_id in unchanged
            and proposal.get("kind") in PROVENANCE_FILTERED_KINDS
        ):
            dropped.append(proposal["proposal_key"])
        else:
            kept.append(proposal["proposal_key"])
    return {"dropped": sorted(dropped), "kept": sorted(kept)}


# --------------------------------------------------------------------------- 闭包健全性
def will_modify_entity_ids(
    base_knowledge: dict,
    proposals: Sequence[dict],
    decisions: Sequence[dict],
) -> List[str]:
    """从本轮交给 `apply` 的**裁定本身**独立推出「将要改动的基底对象集」（CHARTER §13.2）。

    只读裁定：`subject` / `targets` / `auto_choice` / 人工决定的 `choice` 与
    `target_entity_ids`；**不调用也不复刻 `apply` 的私有函数**。

    只覆盖四类实体（`patterns` / `concepts` / `assertions` / `school_views`）——
    因为只有它们会落在 `apply._restore_untouched` 的「原样拷贝」回滚面里
    （`relations` 与 `conflict_groups` 会被重算/合并，不存在静默覆盖的洞）。

    未决（`human` / `blocked` 且无决定）的提案不交给 `apply`，因此不计入。
    返回升序的基底对象号。
    """
    base = base_knowledge or {}
    all_ids = _all_ids(_index_base(base))
    by_decision = {
        decision["proposal_key"]: decision
        for decision in decisions
        if decision.get("proposal_key")
    }
    touched: Set[str] = set()
    for proposal in proposals:
        decision = by_decision.get(proposal.get("proposal_key"))
        if decision is not None:
            choice = decision.get("choice")
            targets = list(decision.get("target_entity_ids") or proposal.get("targets") or [])
        elif proposal.get("resolution") == "auto":
            choice = proposal.get("auto_choice")
            targets = list(proposal.get("targets") or [])
        else:
            continue
        if not choice:
            continue
        if isinstance(choice, str) and choice.startswith("attach:"):
            touched.add(choice.split(":", 1)[1])
        elif choice == "accept_alias":
            touched.update(targets)
        elif choice == "retire":
            subject = list(proposal.get("subject") or [])
            if subject:
                touched.add(subject[-1])
        elif choice == "split":
            touched.update(targets)
        elif choice in apply_module.COLLATION_KINDS or choice == "accept_alignment":
            touched.update(targets)
        # unify / keep_separate 等改的是 conflict_groups：不在回滚面内，故不计入
    return sorted(entity_id for entity_id in touched if entity_id in all_ids)


def closure_soundness_violations(
    base_knowledge: dict,
    proposals: Sequence[dict],
    decisions: Sequence[dict],
    affected: Iterable[str],
) -> List[str]:
    """将要改动的对象里、不在 `affected` 内的那些（升序）。空列表 = 健全。"""
    affected_set = {str(entity_id) for entity_id in affected}
    return sorted(
        set(will_modify_entity_ids(base_knowledge, proposals, decisions)) - affected_set
    )


# --------------------------------------------------------------------------- 编排主体
def assemble(
    base_knowledge: dict,
    views: Sequence[dict],
    decisions: Sequence[dict],
    *,
    max_rounds: int = 10,
    incremental: bool = True,
    base_snapshot_revision_id: Optional[str] = None,
) -> Dict[str, Any]:
    """回流轮次 + 应用裁定（act/05.yaml:36-40）。

    `base_snapshot_revision_id` 是**追加**的关键字参数（原件没有）：合并轮产物必须同时
    补 `meta.base_snapshot_revision_id` / `assembly_seq` / `decision_refs`（CHARTER §9.3），
    而修订 id 只存在于 Ledger 行上，不在 knowledge 文档里。见回报「偏差 3」。
    """
    decisions = list(decisions or [])
    base = base_knowledge or {}
    first_round = int((base.get("meta") or {}).get("assembly_seq") or 1) + 1
    decided_keys = {
        decision.get("proposal_key") for decision in decisions if decision.get("proposal_key")
    }

    rounds: List[Dict[str, Any]] = []
    final: Optional[Dict[str, Any]] = None
    previous_fingerprint: Optional[str] = None
    for offset in range(max_rounds):
        proposals_res = incremental_module.propose_incremental(
            base, views, decisions=decisions, round_no=first_round + offset
        )
        rounds.append(proposals_res)
        final = proposals_res

        pending = [
            proposal
            for proposal in proposals_res["proposals"]
            if proposal["resolution"] in NEEDS_DECISION
            and proposal["proposal_key"] not in decided_keys
        ]
        if not pending:
            break
        if any(proposal["resolution"] == "human" for proposal in pending):
            return {
                "status": "awaiting_human",
                "rounds": rounds,
                "pending": sorted(proposal["proposal_key"] for proposal in pending),
            }
        ready = [
            proposal
            for proposal in pending
            if all(dep in decided_keys for dep in proposal.get("depends_on") or [])
        ]
        if not ready:
            return {
                "status": "awaiting_human",
                "rounds": rounds,
                "pending": sorted(proposal["proposal_key"] for proposal in pending),
            }
        fingerprint = json.dumps(
            [proposal["proposal_key"] for proposal in proposals_res["proposals"]], sort_keys=True
        )
        if fingerprint == previous_fingerprint:
            raise AssemblyRefused(
                "回流未收敛：blocked 提案在依赖已决后重出且无变化", code="SCH_001"
            )
        previous_fingerprint = fingerprint
    else:
        raise AssemblyRefused("回流未收敛：超过 max_rounds=%d" % max_rounds, code="SCH_001")

    proposals = final["proposals"]

    # D-14 替换继承接线（CHARTER §21 ①）：视图里 provenance 未变 / 仍声明着的对象
    # 本轮**不再产生** merge/alias/conflict 提案（沿用 Snapshot 结果）。不接这一步，
    # 同书返工时 R11 会把仍在视图里的断言一并退役（`carry_forward_proposals` 是本函数之前
    # 唯一没被 `assemble` 调用的 D 波产物）。被剔除的键如实进 `report.dropped_proposal_keys`，
    # 不许静默丢弃。
    inherited = carry_forward_proposals(base, views, proposals)
    dropped_keys = set(inherited["dropped"])
    effective_proposals = [
        proposal for proposal in proposals if proposal["proposal_key"] not in dropped_keys
    ]

    # 闭包仍按**本轮生成过的全部提案**算（它描述「这一轮触及了基底的哪些对象」，
    # 与 `report.round_proposal_keys` 同一口径），交经 `apply` 的只有过滤后的那批。
    closure = affected_closure(base, views, proposals, decisions)
    affected = closure["affected"] if incremental else None

    # CHARTER §13.2 闭包健全性：apply 之前先独立推出「将要改动的对象集」，必须 ⊆ affected。
    # 闭包漏掉一个其实会被改动的对象时，`apply._restore_untouched` 会拿基底旧版把它静默覆盖——
    # 这条检查正是那个洞的守卫（等式断言 `rebuilt == affected` 已按 §13.2 删除）。
    # 按 §21 ①，检查的输入是**过滤之后**交给 apply 的那批裁定。
    if incremental:
        missing = closure_soundness_violations(
            base, effective_proposals, decisions, closure["affected"]
        )
        if missing:
            raise AssemblyRefused(
                "闭包不完整：本轮将要改动的对象不在 affected 内: %s" % missing, code="SCH_002"
            )

    result = apply_module.apply_resolutions(
        base, views, effective_proposals, decisions, affected=affected
    )
    # 廉价健全检查（不是证明）：重建范围不得超出闭包
    if incremental and not set(result["rebuilt_entity_ids"]) <= set(closure["affected"]):
        raise AssemblyRefused(
            "重建范围超出闭包：rebuilt=%r affected=%r"
            % (result["rebuilt_entity_ids"], closure["affected"]),
            code="SCH_002",
        )

    # CHARTER §9.3 名实一致收口：合并轮必须补 meta 三键
    knowledge = result["knowledge"]
    meta = dict(knowledge.get("meta") or {})
    meta["base_snapshot_revision_id"] = base_snapshot_revision_id
    meta["assembly_seq"] = first_round
    meta["decision_refs"] = sorted(decided_keys)
    knowledge["meta"] = meta
    knowledge_bytes = canonical_json(knowledge)
    result["knowledge_bytes"] = knowledge_bytes
    result["knowledge_sha256"] = sha256_hex(knowledge_bytes)
    incremental_module.assert_prev_meta_agreement(base_snapshot_revision_id, knowledge)

    proposal_counts = {"auto": 0, "human": 0, "blocked_then_resolved": 0}
    for proposal in proposals:
        if proposal["resolution"] == "auto":
            proposal_counts["auto"] += 1
        elif proposal["resolution"] == "human":
            proposal_counts["human"] += 1
        elif proposal["resolution"] == "decided":
            proposal_counts["blocked_then_resolved"] += 1
    carried = carry_forward(base, views, proposals)

    # ACT 26 二：本轮（含回流各轮）全部提案键，升序去重。
    # 这是 `gate.identity_delta_contract` 回到草稿口径的唯一依据（CHARTER §16.1 第 2 条）。
    round_proposal_keys = sorted(
        {
            proposal["proposal_key"]
            for proposals_res in rounds
            for proposal in proposals_res["proposals"]
        }
    )

    report = {
        "affected_entity_ids": closure["affected"] if incremental else None,
        "rebuilt_entity_ids": result["rebuilt_entity_ids"],
        "created_entity_ids": result["created_entity_ids"],
        "untouched_count": len(closure["untouched"]),
        "proposals_by_resolution": proposal_counts,
        "rounds": [proposals_res["round"] for proposals_res in rounds],
        "carried": carried["carried"],
        "needs_review": carried["needs_review"],
        "not_comparable_count": len(final["not_comparable"]),
        "round_proposal_keys": round_proposal_keys,
        "dropped_proposal_keys": sorted(dropped_keys),
        # CHARTER §22.2：随退役/合并删除的基底关系（含理由），由 apply 产出后原样透传
        "dropped_relations": result["report"]["dropped_relations"],
    }
    return {"status": "complete", "rounds": rounds, "pending": [], "result": result, "report": report}
