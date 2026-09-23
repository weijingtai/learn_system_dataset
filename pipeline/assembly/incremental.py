"""M7 增量汇编：提案生成（act/impl-07/22 contract 一/三/四）。

规则表**逐字沿用** `act/03.yaml:26-49`（`rule_id` 与 `options` 名逐字，见 :data:`RULE_IDS`）；
该草稿的其余部分按 CHARTER §5 校准后作废，本模块**不照抄**它的前置拒绝段。

本模块是**纯函数层**：不写 Ledger、不发号、不改任何既有对象。
所有「哪些单元是同一件事」的判断一律经 :mod:`pipeline.assembly.matcher`
（CHARTER §3.1：matcher.py 之外任何代码不得直接做配对判断）。
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

from pipeline.assembly.canonical import canonical_json, content_sha256, nfc_key, sha256_hex, work_key
from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.matcher import (
    NOT_COMPARABLE_MISSING_COLLATION_KEY,
    propose_pairs,
    units_of_view,
)
from pipeline.assembly.model import MERGE_RELATIONS, PROPOSAL_KINDS

#: ``not_comparable`` 的理由闭集（CHARTER §25.5、§28 Q5/假设一、§28b；
#: `missing_collation_key` 见 :mod:`matcher`）
NOT_COMPARABLE_BASE_UNDECLARED = "base_undeclared"
NOT_COMPARABLE_DECLARED_WITHOUT_ASSERTION = "declared_without_assertion"
NOT_COMPARABLE_VIEW_UNDECLARED = "view_undeclared"
NOT_COMPARABLE_SAME_SOURCE = "same_source"
NOT_COMPARABLE_MULTIPLE = "multiple_assertions_per_unit"

#: 有键单元的理由优先级（CHARTER §29 Q11 第 3 条，逐字：先命中者胜）
NOT_COMPARABLE_PRIORITY = (
    NOT_COMPARABLE_VIEW_UNDECLARED,
    NOT_COMPARABLE_SAME_SOURCE,
    NOT_COMPARABLE_BASE_UNDECLARED,
    NOT_COMPARABLE_MULTIPLE,
    NOT_COMPARABLE_DECLARED_WITHOUT_ASSERTION,
)

#: act/03.yaml:26-49 的规则名，**逐字**
RULE_IDS = (
    "R01", "R01b", "R02", "R03a", "R03b", "R03c", "R03d", "R03e", "R03f", "R03g",
    "R04", "R06", "R07", "R07b", "R08", "R09", "R10", "R11", "R11b",
)

#: 提案键序（act/03.yaml:11-14 逐字）
PROPOSAL_FIELDS = (
    "proposal_key", "kind", "rule_id", "resolution", "subject", "targets",
    "options", "auto_choice", "decision_type", "basis_sha256", "depends_on",
)

_PAT_PREFIX = "pat_%s_"


# --------------------------------------------------------------------------- 基础
def proposal_key(kind: str, subject: Sequence[Any]) -> str:
    """D-12：``"<kind>:" + sha256(规范 JSON(主体元组))[:32]``；**不发登记 ID 前缀**。"""
    if kind not in PROPOSAL_KINDS:
        raise AssemblyRefused("未知提案 kind: %r" % (kind,), code="SCH_002")
    digest = sha256_hex(canonical_json(list(subject)))
    return "%s:%s" % (kind, digest[:32])


def _proposal(
    kind: str,
    rule_id: str,
    subject: Sequence[Any],
    *,
    resolution: str,
    options: Sequence[str] = (),
    auto_choice: Optional[str] = None,
    targets: Sequence[str] = (),
    decision_type: Optional[str] = None,
    basis_sha256: Optional[str] = None,
    depends_on: Sequence[str] = (),
) -> Dict[str, Any]:
    if rule_id not in RULE_IDS:
        raise AssemblyRefused("rule_id 不在规则表内: %r" % (rule_id,), code="SCH_002")
    if kind == "merge" and auto_choice is not None:
        # D-05：并入语义闭集 {attach, admit_new, merge_entities}；`attach:<id>` 取冒号前一段
        head = auto_choice.split(":", 1)[0]
        if head not in MERGE_RELATIONS:
            raise AssemblyRefused(
                "merge 关系必须在闭集 %s 内: %r" % (list(MERGE_RELATIONS), auto_choice), code="SCH_002"
            )
    return {
        "proposal_key": proposal_key(kind, subject),
        "kind": kind,
        "rule_id": rule_id,
        "resolution": resolution,
        "subject": list(subject),
        "targets": list(targets),
        "options": list(options),
        "auto_choice": auto_choice,
        "decision_type": decision_type,
        "basis_sha256": basis_sha256,
        "depends_on": list(depends_on),
    }


def _view_parts(view: Dict[str, Any]) -> Tuple[str, dict, dict]:
    """把一份视图规约成 ``(source_id, candidate_set, reviewed_edition)``。"""
    cset = view.get("candidate_set") or {}
    reviewed = view.get("reviewed_edition") or {}
    source_id = view.get("source_id") or cset.get("source_id")
    if not source_id:
        raise AssemblyRefused("视图缺少 source_id", code="SCH_002")
    return source_id, cset, reviewed


def _approved_index(reviewed: dict) -> set:
    return {
        (item.get("kind"), item.get("entity_id"))
        for item in reviewed.get("approved") or []
    }


def _name_keys(item: dict) -> set:
    values = [item.get("name"), item.get("surface")]
    values.extend(item.get("aliases") or [])
    return {nfc_key(v) for v in values if v}


def _rule_keys(item: dict) -> set:
    return {
        rule.get("ast_sha256")
        for rule in item.get("rules") or []
        if rule.get("ast_sha256")
    }


def _formal_payload(item: dict) -> dict:
    """``basis_sha256`` 用到的对象字段（act/03.yaml:50 逐字）。"""
    return {
        "name": item.get("name"),
        "aliases": sorted(item.get("aliases") or []),
        "rule_hashes": sorted(_rule_keys(item)),
        "concept_id": item.get("concept_id"),
    }


def _pattern_basis(target: Optional[dict], candidate: dict) -> str:
    return content_sha256(
        {
            "target": _formal_payload(target) if target is not None else None,
            "candidate": _formal_payload(candidate),
        }
    )


def _number_of(pattern_id: Optional[str], technique_id: str) -> Optional[int]:
    if not pattern_id or not pattern_id.startswith(_PAT_PREFIX % technique_id):
        return None
    digits = pattern_id[len(_PAT_PREFIX % technique_id):]
    return int(digits) if digits.isdigit() and len(digits) == 6 else None


# --------------------------------------------------------------------------- §8.1
def allocate_ids(base_knowledge: dict, views: Sequence[dict]) -> Dict[str, Any]:
    """按 CHARTER §8.1 计算号位（**只按已获批、进入 Snapshot 的对象取号**）。

    返回 ``{"id_allocation": {...}, "allocated_pattern_ids": [...], "unapproved_with_self_issued_id": [...]}``。
    携带 M4 自发 ``pat_`` 号但**未获批**的候选：不进号位、也不许静默——逐条进
    ``unapproved_with_self_issued_id``。
    """
    technique_id = base_knowledge.get("technique_id")
    used: List[int] = []
    unapproved: List[Dict[str, Any]] = []

    for pattern in base_knowledge.get("patterns") or []:
        number = _number_of(pattern.get("pattern_id"), technique_id)
        if number is not None:
            used.append(number)
    for entity_id in base_knowledge.get("retired_entity_ids") or []:
        number = _number_of(entity_id, technique_id)
        if number is not None:
            used.append(number)
    for pattern_id in base_knowledge.get("allocated_pattern_ids") or []:
        number = _number_of(pattern_id, technique_id)
        if number is not None:
            used.append(number)

    for view in views:
        source_id, cset, reviewed = _view_parts(view)
        approved = _approved_index(reviewed)
        for candidate in cset.get("patterns") or []:
            pattern_id = candidate.get("pattern_id")
            if ("pattern", pattern_id) in approved:
                number = _number_of(pattern_id, technique_id)
                if number is not None:
                    used.append(number)
            elif pattern_id:
                unapproved.append(
                    {
                        "source_id": source_id,
                        "pattern_id": pattern_id,
                        "reason": "unapproved_with_self_issued_id",
                    }
                )

    unapproved.sort(key=lambda item: (item["source_id"], item["pattern_id"]))
    return {
        "id_allocation": {"pat_%s" % technique_id: max(used) if used else 0},
        "allocated_pattern_ids": [],
        "unapproved_with_self_issued_id": unapproved,
    }


# --------------------------------------------------------------------------- 名实一致
def assert_prev_meta_agreement(prev_revision_id: Optional[str], knowledge: dict) -> None:
    """CHARTER §9.3 的名实一致收口：``prev`` 非空 **⟺** ``meta.base_snapshot_revision_id`` 非空。

    A 波留下的中间态（``prev`` 有基底而 ``meta`` 说没有）在这里被直接拒收。
    """
    meta = knowledge.get("meta") or {}
    meta_base = meta.get("base_snapshot_revision_id") if isinstance(meta, dict) else None
    if (prev_revision_id is None) != (meta_base is None):
        raise AssemblyRefused(
            "名实不符：prev_revision_id=%r 而 meta.base_snapshot_revision_id=%r"
            % (prev_revision_id, meta_base),
            code="SCH_002",
        )


def snapshot_revision_pairs(service) -> List[Dict[str, Any]]:
    """扫描 Ledger 里全部 sealed ``canonical_snapshot`` 修订，返回 ``(prev, meta_base)`` 对。"""
    rows = service.store.conn.execute(
        "SELECT r.artifact_revision_id, r.prev_revision_id, r.sha256 FROM artifact_revisions r "
        "JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "WHERE a.artifact_type='canonical_snapshot' AND r.status='sealed' "
        "ORDER BY r.artifact_revision_id"
    ).fetchall()
    pairs = []
    for revision_id, prev_revision_id, sha256 in rows:
        raw = service.objects.get(sha256)
        knowledge = {}
        if raw:
            try:
                import json as _json

                knowledge = _json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                knowledge = {}
        meta = knowledge.get("meta") or {}
        pairs.append(
            {
                "snapshot_revision_id": revision_id,
                "prev_revision_id": prev_revision_id,
                "meta_base_snapshot_revision_id": (
                    meta.get("base_snapshot_revision_id") if isinstance(meta, dict) else None
                ),
            }
        )
    return pairs


# --------------------------------------------------------------------------- 规则表
def propose_incremental(
    base_knowledge: dict,
    views: Sequence[dict],
    *,
    decisions: Sequence[dict] = (),
    round_no: int = 1,
) -> Dict[str, Any]:
    """按 R01–R11b 生成四类提案（merge / alias / conflict / evidence）。

    ``views`` 每项为 ``{"source_id":…, "candidate_set":…, "reviewed_edition":…}``。
    返回 ``{"round", "modes", "proposals"(按 proposal_key 升序), "not_comparable", "report"}``。
    """
    if round_no < 1:
        raise AssemblyRefused("round_no 必须 ≥ 1", code="SCH_001")
    if not views:
        raise AssemblyRefused("views 不得为空", code="SCH_001")
    source_ids = [_view_parts(view)[0] for view in views]
    if len(set(source_ids)) != len(source_ids):
        raise AssemblyRefused("views 的 source_id 必须互异", code="SCH_002")

    technique_id = base_knowledge.get("technique_id")
    base_editions = {ed.get("source_id"): ed for ed in base_knowledge.get("editions") or []}
    modes = _classify_modes(base_knowledge, views)

    live_patterns = list(base_knowledge.get("patterns") or [])
    base_by_id = {p["pattern_id"]: p for p in live_patterns}
    base_by_name: Dict[str, List[dict]] = {}
    for pattern in live_patterns:
        for key in _name_keys(pattern):
            base_by_name.setdefault(key, []).append(pattern)
    base_by_rule: Dict[str, List[dict]] = {}
    for pattern in live_patterns:
        for key in _rule_keys(pattern):
            base_by_rule.setdefault(key, []).append(pattern)

    distinct_pairs = {
        frozenset((rel.get("from_entity_id"), rel.get("to_entity_id")))
        for rel in base_knowledge.get("relations") or []
        if rel.get("relation_key", "").startswith("distinct_from") or rel.get("kind") == "distinct_from"
    }

    proposals: List[Dict[str, Any]] = []
    not_comparable: List[Dict[str, Any]] = []
    missing_collation = 0
    base_undeclared = 0
    declared_without_assertion = 0
    base_entity_ids = _base_entity_ids(base_knowledge)

    # 本批候选（用于 R03f/R03g 的批内交集判断）
    batch = _batch_candidates(views)

    for view in views:
        source_id, cset, reviewed = _view_parts(view)
        approved = _approved_index(reviewed)
        mode = modes[source_id]

        # ---------------------------------------------------------- R01/R01b/R02/R03*/R10
        for candidate in cset.get("patterns") or []:
            pattern_id = candidate.get("pattern_id")
            candidate_key = candidate.get("candidate_key")
            # 已获批的判定：正式号（`pat_`）或候选键（`candidate_key`）二者之一被批准即可
            approved_keys = {
                key for key in (("pattern", pattern_id), ("pattern", candidate_key)) if key[1]
            }
            if not (approved_keys & approved):
                continue  # 未获批不进 Snapshot，也不产生提案（§8.1 由 allocate_ids 报告）
            subject = ["pattern", source_id, pattern_id or candidate.get("candidate_key")]
            target = base_by_id.get(pattern_id) if pattern_id else None
            if target is not None:
                if _concept_consistent(candidate, target):
                    proposals.append(
                        _proposal(
                            "merge", "R01", subject, resolution="auto",
                            auto_choice="attach:%s" % pattern_id, targets=[pattern_id],
                            basis_sha256=_pattern_basis(target, candidate),
                        )
                    )
                else:
                    proposals.append(
                        _proposal(
                            "conflict", "R01b", ["concept_binding", source_id, candidate.get("candidate_key")],
                            resolution="human",
                            options=["keep_binding_of_canonical", "rebind_candidate"],
                            basis_sha256=_pattern_basis(target, candidate),
                        )
                    )
                continue
            name_hits, rule_hits = _hits(
                candidate, base_by_name, base_by_rule, distinct_pairs, target=None
            )
            if pattern_id and not name_hits and not rule_hits:
                proposals.append(
                    _proposal(
                        "merge", "R02", subject, resolution="auto",
                        auto_choice="admit_new", targets=[pattern_id],
                        basis_sha256=_pattern_basis(None, candidate),
                    )
                )
                continue
            proposals.extend(
                _r03_proposals(
                    candidate, subject, name_hits, rule_hits, batch, source_id, proposals,
                )
            )

        # ---------------------------------------------------------- R04 Concept
        # CHARTER §13.3：先按**主体键**分组，每组只出一条提案。
        # （同一概念被提及多次时，逐条出提案会产生同键多条，apply 以 ID_002 拒收。）
        concept_groups: Dict[Tuple[Any, ...], List[dict]] = {}
        for candidate in list(cset.get("new_concept_candidates") or []) + list(
            cset.get("concept_mentions") or []
        ):
            concept_ref = candidate.get("concept_ref") or candidate.get("concept_id")
            if concept_ref and ("concept", concept_ref) not in approved and (
                "concept_mention", concept_ref
            ) not in approved:
                continue
            group_key = ("concept", source_id, concept_ref or candidate.get("surface"))
            concept_groups.setdefault(group_key, []).append(candidate)

        base_concepts = list(base_knowledge.get("concepts") or [])
        base_concept_ids = {item["concept_id"] for item in base_concepts}
        for group_key in sorted(concept_groups, key=lambda item: str(item[2])):
            members = concept_groups[group_key]
            merged = _merge_concept_group(group_key, members)
            concept_id = merged["concept_ref"]
            label = _r04_branch_label(group_key, merged, members, base_concepts, base_concept_ids)
            if label == "attach":
                proposals.append(
                    _proposal(
                        "merge", "R04", list(group_key), resolution="auto",
                        auto_choice="attach:%s" % concept_id, targets=[concept_id],
                        basis_sha256=_concept_basis(merged),
                    )
                )
            elif label == "alias":
                name_keys = _name_keys(merged)
                same_name = [
                    item["concept_id"]
                    for item in base_concepts
                    if name_keys & _name_keys(item)
                ]
                proposals.append(
                    _proposal(
                        "alias", "R04", list(group_key),
                        resolution="human", options=["accept_alias", "reject_alias"],
                        targets=sorted(same_name), basis_sha256=_concept_basis(merged),
                    )
                )
            else:
                proposals.append(
                    _proposal(
                        "merge", "R04", list(group_key), resolution="auto",
                        auto_choice="admit_new", basis_sha256=_concept_basis(merged),
                    )
                )

        # ---------------------------------------------------------- R06 SchoolView
        for school_view in cset.get("school_views") or []:
            subject_entity = school_view.get("subject_entity_id")
            conflict_group = school_view.get("conflict_group_id")
            if not conflict_group or subject_entity not in _base_entity_ids(base_knowledge):
                continue
            existing = [
                cg["conflict_group_id"]
                for cg in base_knowledge.get("conflict_groups") or []
                if subject_entity in _conflict_members(base_knowledge, cg["conflict_group_id"])
            ]
            pending = sorted(
                sv.get("school_view_id")
                for sv in base_knowledge.get("school_views") or []
                if sv.get("subject_entity_id") == subject_entity
            )
            proposals.append(
                _proposal(
                    "conflict", "R06", ["conflict_group", subject_entity, pending],
                    resolution="human", options=["unify", "keep_separate"],
                    decision_type="review_school_attribution",
                    targets=sorted(existing),
                    basis_sha256=_school_view_basis(cset, subject_entity),
                )
            )

        # ---------------------------------------------------------- R07/R07b/R08/R09
        # CHARTER §25.2–§25.7、§28 Q3/Q5/假设一、§29 Q8/Q11：对勘在**本轮视图**与基底里
        # **其他**版次之间做（同 source 不比，§25.3），按**主体**（`subject_entity_id`）判可比，
        # 方向按角色（新版 = 本轮视图、旧版 = 基底，§25.4），提案一律带 `targets = [from, to]`。
        #
        # 同书返工轮（mode == "replacement"）**也要**算：§29 Q8 要求「涉及视图 source 的对勘
        # 关系全部删掉、按本轮角色重算」，故这里照常算，只是**同 source 的版次不参与**。
        if mode in ("new", "replacement"):
            outcomes, rows, counts = _collation_analysis(
                base_knowledge, cset, reviewed, source_id, approved
            )
            not_comparable.extend(rows)
            missing_collation += counts.get(NOT_COMPARABLE_MISSING_COLLATION_KEY, 0)
            base_undeclared += counts.get(NOT_COMPARABLE_BASE_UNDECLARED, 0)
            declared_without_assertion += counts.get(
                NOT_COMPARABLE_DECLARED_WITHOUT_ASSERTION, 0
            )
            view_subjects = _view_subjects(cset)
            # §25.1：视图沿用基底号时（同书返工保号携带），该断言的主体早已在基底裁定，
            # 以基底主体为准；否则同书返工里保号携带的断言会被错判成「主体不同 → R07b」。
            carried_subjects = {
                assertion.get("assertion_id"): assertion.get("subject_entity_id")
                for assertion in base_knowledge.get("assertions") or []
            }
            for outcome in outcomes:
                key = outcome["collation_key"]
                view_side, base_side = outcome["view"], outcome["base"]
                subject = ["collation", source_id, key, base_side["source_id"]]
                if not view_side["present"] or not base_side["present"]:
                    # §25.4：增文 = 新版 present、旧版声明 present:false；缺文反之
                    present_side = view_side if view_side["present"] else base_side
                    present_assertion = present_side["assertion"]
                    if present_assertion is None:
                        # 声明了 present 却没有断言：已进 not_comparable，不出关系
                        continue
                    proposals.append(
                        _proposal(
                            "evidence", "R09", subject, resolution="auto",
                            auto_choice="addition" if view_side["present"] else "omission",
                            targets=[present_assertion["assertion_id"], None],
                        )
                    )
                    continue
                view_assertion = view_side["assertion"]
                base_assertion = base_side["assertion"]
                if view_assertion is None or base_assertion is None:
                    continue
                targets = [view_assertion["assertion_id"], base_assertion["assertion_id"]]
                view_subject = carried_subjects.get(
                    view_assertion["assertion_id"],
                    view_subjects.get(view_assertion["assertion_id"]),
                )
                base_subject = base_assertion.get("subject_entity_id")
                if not view_subject or not base_subject:
                    # §28 Q3：任一主体为 null → 不算同一正式对象 → R07b 人工
                    proposals.append(_collation_conflict(subject, targets))
                    continue
                if view_subject != base_subject:
                    if view_subject in base_entity_ids:
                        # §25.2：主体裁决到**不同**正式对象 → R07b 人工
                        proposals.append(_collation_conflict(subject, targets))
                        continue
                    # 主体本身还在等人工裁决 → 对勘提案 depends_on 那条提案，不许猜
                    dependency = proposal_key("merge", ["pattern", source_id, view_subject])
                    pending = any(
                        item["proposal_key"] == dependency
                        and item["resolution"] in ("human", "blocked")
                        for item in proposals
                    )
                    if not pending:
                        raise AssemblyRefused(
                            "对勘单元 %s 的主体 %r 尚待裁决且推不出确定对应（无对应人工提案），"
                            "须停手上报" % (key, view_subject),
                            code="SCH_002",
                        )
                    proposals.append(
                        _proposal(
                            "evidence", "R07", subject, resolution="blocked",
                            targets=targets, depends_on=[dependency],
                        )
                    )
                    continue
                same_text = _assertion_text_sha(view_assertion) == base_assertion.get(
                    "text_sha256"
                )
                proposals.append(
                    _proposal(
                        "evidence", "R07" if same_text else "R08", subject,
                        resolution="auto",
                        auto_choice="alignment" if same_text else "variant_reading",
                        targets=targets,
                    )
                )

        # ---------------------------------------------------------- R11/R11b（替换模式）
        if mode == "replacement":
            proposals.extend(_replacement_proposals(base_knowledge, source_id, technique_id))

    proposals = _apply_decisions(proposals, decisions, base_by_id, base_by_name, base_by_rule, distinct_pairs)
    proposals.sort(key=lambda item: item["proposal_key"])

    allocation = allocate_ids(base_knowledge, views)
    report = {
        "round": round_no,
        "modes": modes,
        "not_comparable_missing_collation_key": missing_collation,
        "not_comparable_base_undeclared": base_undeclared,
        "not_comparable_declared_without_assertion": declared_without_assertion,
        "base_editions_without_views": sorted(set(base_editions) - set(source_ids)),
        **allocation,
    }
    # CHARTER §28b：清单排序键固定为 `(source_id, collation_key or "", assertion_id or "")`
    not_comparable.sort(key=_not_comparable_sort_key)
    return {
        "round": round_no,
        "modes": modes,
        "proposals": proposals,
        "not_comparable": not_comparable,
        "report": report,
    }


# --------------------------------------------------------------------------- 内部
def _classify_modes(base_knowledge: dict, views: Sequence[dict]) -> Dict[str, str]:
    """D-14：``(source_id, edition_part_ids 集合)`` 相等 → replacement；不相交 → extension；
    部分重叠 → 拒绝（README:394）。``new`` 表示基底里没有该 source。"""
    base_editions = {
        ed.get("source_id"): set(ed.get("edition_part_artifact_ids") or [])
        for ed in base_knowledge.get("editions") or []
    }
    modes = {}
    for view in views:
        source_id, cset, _ = _view_parts(view)
        parts = {cset.get("edition_part_artifact_id")} if cset.get("edition_part_artifact_id") else set()
        if source_id not in base_editions:
            modes[source_id] = "new"
            continue
        existing = base_editions[source_id]
        if parts and existing and parts == existing:
            modes[source_id] = "replacement"
        elif not (parts & existing):
            modes[source_id] = "extension"
        else:
            raise AssemblyRefused(
                "视图 %s 的 edition_part 集合与基底部分重叠，无法判定替换或扩展: %s vs %s"
                % (source_id, sorted(parts), sorted(existing)),
                code="SCH_002",
            )
    return modes


def _batch_candidates(views: Sequence[dict]) -> Dict[str, dict]:
    batch = {}
    for view in views:
        source_id, cset, _ = _view_parts(view)
        for candidate in cset.get("patterns") or []:
            key = candidate.get("pattern_id") or candidate.get("candidate_key")
            if key:
                batch["%s|%s" % (source_id, key)] = candidate
    return batch


def _hits(
    candidate: dict,
    base_by_name: Dict[str, List[dict]],
    base_by_rule: Dict[str, List[dict]],
    distinct_pairs: set,
    *,
    target: Optional[dict],
) -> Tuple[set, set]:
    """名称命中集与规则命中集；R10 在此排除已被声明 ``distinct_from`` 的命中。"""
    name_hits = {
        pattern["pattern_id"]
        for key in _name_keys(candidate)
        for pattern in base_by_name.get(key, [])
    }
    rule_hits = {
        pattern["pattern_id"]
        for key in _rule_keys(candidate)
        for pattern in base_by_rule.get(key, [])
    }
    if target is not None and distinct_pairs:
        excluded = {
            endpoint
            for pair in distinct_pairs
            if target["pattern_id"] in pair
            for endpoint in pair
            if endpoint != target["pattern_id"]
        }
        name_hits -= excluded
        rule_hits -= excluded
    return name_hits, rule_hits


def _r03_proposals(
    candidate: dict,
    subject: list,
    name_hits: set,
    rule_hits: set,
    batch: Dict[str, dict],
    source_id: str,
    existing_proposals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """act/03.yaml:29-35（R03a–R03g）。"""
    has_id = bool(candidate.get("pattern_id"))
    if len(name_hits) >= 2 or len(rule_hits) >= 2:
        options = ["attach:%s" % p for p in sorted(name_hits | rule_hits)]
        return [
            _proposal(
                "merge", "R03d", subject, resolution="human",
                options=options + ["admit_new", "merge_entities"],
                basis_sha256=_pattern_basis(None, candidate),
            )
        ]
    if has_id:
        if name_hits:
            only = sorted(name_hits)[0]
            return [
                _proposal(
                    "merge", "R03b", subject, resolution="human",
                    options=["attach:%s" % only, "admit_new"], targets=[only],
                    basis_sha256=_pattern_basis(None, candidate),
                )
            ]
        only = sorted(rule_hits)[0]
        return [
            _proposal(
                "alias", "R03c", subject, resolution="human",
                options=["accept_alias", "reject_alias"], targets=[only],
                basis_sha256=_pattern_basis(None, candidate),
            )
        ]
    if name_hits and rule_hits and name_hits == rule_hits:
        only = sorted(name_hits)[0]
        return [
            _proposal(
                "merge", "R03a", subject, resolution="auto",
                auto_choice="attach:%s" % only, targets=[only],
                basis_sha256=_pattern_basis(None, candidate),
            )
        ]
    if name_hits and not rule_hits:
        only = sorted(name_hits)[0]
        return [
            _proposal(
                "merge", "R03b", subject, resolution="human",
                options=["attach:%s" % only, "admit_new"], targets=[only],
                basis_sha256=_pattern_basis(None, candidate),
            )
        ]
    if rule_hits and not name_hits:
        only = sorted(rule_hits)[0]
        return [
            _proposal(
                "alias", "R03c", subject, resolution="human",
                options=["accept_alias", "reject_alias"], targets=[only],
                basis_sha256=_pattern_basis(None, candidate),
            )
        ]
    # 对 S 无命中：与批内其他候选比对（R03f / R03g / R03e）
    my_keys = _name_keys(candidate) | _rule_keys(candidate)
    dependencies: List[str] = []
    for other_key, other in sorted(batch.items()):
        if other_key.endswith("|%s" % (candidate.get("pattern_id") or candidate.get("candidate_key"))):
            continue
        if not (my_keys & (_name_keys(other) | _rule_keys(other))):
            continue
        other_subject = [
            "pattern",
            other_key.split("|", 1)[0],
            other.get("pattern_id") or other.get("candidate_key"),
        ]
        other_proposal = proposal_key("merge", other_subject)
        if any(
            item["proposal_key"] == other_proposal and item["resolution"] == "human"
            for item in existing_proposals
        ):
            dependencies.append(other_proposal)
        else:
            dependencies.append(other_proposal)
    if dependencies:
        if any(
            item["proposal_key"] == dep and item["rule_id"].startswith("R03b")
            for item in existing_proposals
            for dep in dependencies
        ):
            return [
                _proposal(
                    "merge", "R03f", subject, resolution="blocked",
                    depends_on=sorted(set(dependencies)),
                    basis_sha256=_pattern_basis(None, candidate),
                )
            ]
        return [
            _proposal(
                "merge", "R03g", subject, resolution="human",
                options=["admit_new_each", "admit_new_one_attach_other"],
                depends_on=sorted(set(dependencies)),
                basis_sha256=_pattern_basis(None, candidate),
            )
        ]
    return [
        _proposal(
            "merge", "R03e", subject, resolution="auto", auto_choice="admit_new",
            basis_sha256=_pattern_basis(None, candidate),
        )
    ]


def _concept_consistent(candidate: dict, target: dict) -> bool:
    declared = candidate.get("concept_refs") or candidate.get("concept_id")
    if not declared:
        return True
    if isinstance(declared, str):
        return declared == target.get("concept_id")
    return target.get("concept_id") in set(declared)


def _merge_concept_group(group_key: Tuple[Any, ...], members: List[dict]) -> dict:
    """CHARTER §13.3：把同一主体键下的多个概念候选聚合成一条提案的输入。

    - 名称必须一致（同一概念号下出现不同名称 → ``AssemblyRefused``，message 含「概念名称冲突」）
    - `aliases` 与规则哈希取并集（排序）
    - 输出字段与 :func:`_concept_basis` 的口径逐字对齐（单成员时与原实现等价）
    """
    identifier = group_key[2]
    raw_names = [member.get("name") or member.get("surface") for member in members]
    distinct = sorted({nfc_key(name) for name in raw_names if name})
    if len(distinct) > 1:
        raise AssemblyRefused(
            "概念名称冲突：同一概念 %r 下出现多个名称 %s"
            % (identifier, sorted({name for name in raw_names if name})),
            code="SCH_002",
        )
    name = distinct[0] if distinct else None
    return {
        "concept_ref": identifier,
        "concept_id": identifier,
        "name": name,
        "surface": name,
        "aliases": sorted({alias for member in members for alias in (member.get("aliases") or [])}),
        "rules": [
            {"ast_sha256": digest}
            for digest in sorted({digest for member in members for digest in _rule_keys(member)})
        ],
    }


def _r04_branch_label(
    group_key: Tuple[Any, ...],
    merged: dict,
    members: List[dict],
    base_concepts: List[dict],
    base_concept_ids: set,
) -> str:
    """组内三种分支（已存在于基底 / 同名歧义 / 全新）必须一致，否则停手上报。

    组内各成员单独判定；不一致即 ``AssemblyRefused``（CHARTER §13.3 第 4 条）。
    """
    def label_of(candidate: dict) -> str:
        concept_id = candidate.get("concept_ref") or candidate.get("concept_id")
        if concept_id and concept_id in base_concept_ids:
            return "attach"
        name_keys = _name_keys(candidate)
        if any(name_keys & _name_keys(item) for item in base_concepts):
            return "alias"
        return "admit_new"

    labels = {label_of(member) for member in members}
    if len(labels) > 1:
        raise AssemblyRefused(
            "R04 组内分支判定不一致：概念 %r 的候选分别被判为 %s，须停手上报"
            % (group_key[2], sorted(labels)),
            code="SCH_002",
        )
    return sorted(labels)[0]


def _concept_basis(candidate: dict) -> str:
    return content_sha256(
        {
            "name": candidate.get("name") or candidate.get("surface"),
            "aliases": sorted(candidate.get("aliases") or []),
            "rule_hashes": sorted(_rule_keys(candidate)),
            "concept_id": candidate.get("concept_ref") or candidate.get("concept_id"),
        }
    )


def _school_view_basis(cset: dict, subject_entity: str) -> str:
    rows = [
        {
            "school_view_id": sv.get("school_view_id"),
            "school_id": sv.get("school_id"),
            "subject": sv.get("subject_entity_id"),
            "claim_refs": sv.get("claim_refs") or [],
            "conflict_group_id": sv.get("conflict_group_id"),
            "changes_current_judgment": sv.get("changes_current_judgment"),
        }
        for sv in cset.get("school_views") or []
        if sv.get("subject_entity_id") == subject_entity
    ]
    rows.sort(key=lambda row: row["school_view_id"])
    return content_sha256(rows)


def _base_entity_ids(base_knowledge: dict) -> set:
    ids = set()
    for collection, key in (
        ("patterns", "pattern_id"), ("concepts", "concept_id"),
        ("assertions", "assertion_id"), ("school_views", "school_view_id"),
    ):
        ids.update(item.get(key) for item in base_knowledge.get(collection) or [])
    return ids


def _conflict_members(base_knowledge: dict, conflict_group_id: str) -> set:
    for cg in base_knowledge.get("conflict_groups") or []:
        if cg.get("conflict_group_id") == conflict_group_id:
            return set(cg.get("member_school_view_ids") or [])
    return set()


def _work_key_or_none(source_id: Optional[str]) -> Optional[str]:
    try:
        return work_key(source_id) if source_id else None
    except Exception:  # noqa: BLE001 - 算不出 work_key 就不拿它当前提
        return None


def _view_subjects(cset: dict) -> Dict[str, str]:
    """视图里每条断言声明的**主体**（`assertion_id → 主体引用`）。

    口径与 `apply._link_subjects` 一致：主体来自 `patterns[].assertion_ids` 指向的格局
    （正式 `pat_` 号或未发号的 `candidate_key`）；同一断言落在多个格局下时取**较小**的引用。
    视图不声明的断言不在表内（主体推不出 → 对勘层停手上报，见 §25.2）。
    """
    collected: Dict[str, List[str]] = {}
    for pattern in cset.get("patterns") or []:
        ref = pattern.get("pattern_id") or pattern.get("candidate_key")
        if not ref:
            continue
        for assertion_id in pattern.get("assertion_ids") or []:
            if assertion_id:
                collected.setdefault(assertion_id, []).append(ref)
    return {assertion_id: min(refs) for assertion_id, refs in collected.items()}


def _assertion_text_sha(assertion: dict) -> Optional[str]:
    """断言命题的 NFC 文本哈希（与 `matcher.make_unit` 同一口径：逐字相等，不是相似度）。"""
    proposition = assertion.get("proposition")
    if proposition is None:
        return None
    return sha256_hex(nfc_key(proposition).encode("utf-8"))


def _collation_conflict(subject: Sequence[Any], targets: Sequence[str]) -> dict:
    """R07b：主体裁决不到同一正式对象 → 人工裁定（§25.2）。

    选项沿用现有闭集（`apply` 按 CHARTER §28 Q2 把裁定落成关系：
    `accept_alignment` → alignment / variant_reading；`reject_alignment` → distinct_from）。
    """
    return _proposal(
        "conflict", "R07b", list(subject), resolution="human",
        options=["accept_alignment", "reject_alignment"],
        decision_type="review_edition_collation",
        targets=list(targets),
    )


def _base_units(base_knowledge: dict, view_source_id: Optional[str]) -> List[dict]:
    """基底一侧的可比单元（CHARTER §25.5、§28 假设一）。

    **声明只从 `editions[].collation_units` 读**，不再从断言推（旧写法把每条有键的断言都
    当成 present:true，这正是增文永远出不来的根源 F3）。
    同 `source_id` 的版次不参与（§25.3），不同 `work_key` 的版次不参与（§25.2 的可比前提）。

    声明了 present 却没有获批断言的单元也要返回（`entity_ref` 为 None），由规则层如实记进
    `not_comparable`（理由 `declared_without_assertion`）。同键多条断言**不再拒收**，
    而是标记 `ambiguous`（§28 假设一：推不出确定配对 → `multiple_assertions_per_unit`）。
    """
    from pipeline.assembly.matcher import make_unit

    wk = _work_key_or_none(view_source_id)
    by_source: Dict[Any, Dict[Any, List[dict]]] = {}
    for assertion in base_knowledge.get("assertions") or []:
        by_source.setdefault(assertion.get("source_id"), {}).setdefault(
            assertion.get("collation_key"), []
        ).append(assertion)

    units: List[dict] = []
    for edition in base_knowledge.get("editions") or []:
        source_id = edition.get("source_id")
        if source_id == view_source_id:
            continue
        other_wk = _work_key_or_none(source_id)
        if wk is not None and other_wk is not None and other_wk != wk:
            continue
        for declared in edition.get("collation_units") or []:
            key = declared.get("collation_key")
            if not key:
                continue
            present = bool(declared.get("present", True))
            rows = by_source.get(source_id, {}).get(key) or []
            unique = rows[0] if len(rows) == 1 else None
            unit = make_unit(
                source_id,
                collation_key=key,
                present=present,
                entity_ref=unique.get("assertion_id") if unique else None,
                text_sha256=unique.get("text_sha256") if unique else None,
                evidence_span_ids=[
                    ev.get("source_span_id") for ev in (unique or {}).get("evidence") or []
                ],
            )
            # `make_unit`（matcher，只读）不带主体字段，这里按已声明字段补上
            unit["subject_entity_id"] = unique.get("subject_entity_id") if unique else None
            unit["ambiguous"] = len(rows) > 1
            units.append(unit)
    return units


def _not_comparable_sort_key(row: dict) -> tuple:
    """CHARTER §28b：`(source_id, collation_key or "", assertion_id or "")`。"""
    return (
        row.get("source_id") or "",
        row.get("collation_key") or "",
        row.get("assertion_id") or "",
    )


def _pick_not_comparable_reason(reasons: set) -> str:
    """CHARTER §29 Q11 第 3 条：按固定优先级取第一个命中的理由。"""
    for reason in NOT_COMPARABLE_PRIORITY:
        if reason in reasons:
            return reason
    return NOT_COMPARABLE_BASE_UNDECLARED


def _collation_analysis(
    base_knowledge: dict,
    cset: dict,
    reviewed: dict,
    view_source_id: str,
    approved: dict,
) -> Tuple[List[dict], List[dict], Dict[str, int]]:
    """一个视图的对勘分析（CHARTER §25.2–§25.7、§28 Q3/Q5/假设一、§29 Q11）。

    返回 ``(outcomes, not_comparable_rows, counts)``：

    - `outcomes`：**可比**单元的配对（每个「视图键 × 基底版次」一项），供规则层造提案；
    - `not_comparable_rows`：不可比清单，形状**恰为**
      ``{source_id, collation_key, assertion_id, reason}``（§28b / §29 Q11）；
    - `counts`：按理由计数（供 `report` 的三个既有键）。

    可比性判断只经 `matcher.propose_pairs`（CHARTER §3.1：配对判断的唯一落点）；
    本函数只**读声明、算理由**，不自己比对 `collation_key`。
    """
    from pipeline.assembly.matcher import propose_pairs, unit_key

    declared: Dict[str, bool] = {}
    null_declarations = 0
    for entry in cset.get("collation_units") or []:
        key = entry.get("collation_key")
        if key:
            declared[key] = bool(entry.get("present", True))
        else:
            null_declarations += 1

    view_assertions: Dict[str, List[dict]] = {}
    keyless_ids: List[str] = []
    approved_assertions: List[dict] = []
    for assertion in cset.get("assertions") or []:
        aid = assertion.get("assertion_id")
        # CHARTER §30.1：只数 `reviewed_edition.approved` 里 `kind=assertion` 的；
        # 未获批断言不参与单元判定，也不进 not_comparable。
        if ("assertion", aid) not in approved:
            continue
        approved_assertions.append(assertion)
        key = assertion.get("collation_key")
        if key:
            view_assertions.setdefault(key, []).append(assertion)
        else:
            keyless_ids.append(aid)

    editions: List[dict] = []
    for edition in base_knowledge.get("editions") or []:
        declarations: Dict[str, bool] = {}
        for entry in edition.get("collation_units") or []:
            key = entry.get("collation_key")
            if key:
                declarations[key] = bool(entry.get("present", True))
        editions.append(
            {"source_id": edition.get("source_id"), "declared": declarations, "by_key": {}}
        )
    by_source = {edition["source_id"]: edition for edition in editions}
    for assertion in base_knowledge.get("assertions") or []:
        edition = by_source.get(assertion.get("source_id"))
        if edition is None:
            continue
        key = assertion.get("collation_key")
        if key:
            edition["by_key"].setdefault(key, []).append(assertion)

    wk = _work_key_or_none(view_source_id)
    peers: List[dict] = []
    own: List[dict] = []
    for edition in editions:
        if edition["source_id"] == view_source_id:
            own.append(edition)
            continue
        other_wk = _work_key_or_none(edition["source_id"])
        if wk is not None and other_wk is not None and other_wk != wk:
            continue
        peers.append(edition)

    outcomes: List[dict] = []
    rows: List[dict] = []
    counts: Dict[str, int] = {}

    def add_row(key: Optional[str], reason: str) -> None:
        rows.append(
            {
                "source_id": view_source_id,
                "collation_key": key,
                "assertion_id": None,
                "reason": reason,
            }
        )
        counts[reason] = counts.get(reason, 0) + 1

    view_only = dict(cset)
    view_only["assertions"] = approved_assertions
    left_units = units_of_view(view_only, reviewed)
    base_units = _base_units(base_knowledge, view_source_id)
    base_by_unit_key = {unit_key(unit): unit for unit in base_units}
    # 只取「按声明键配对」（`exact_collation_key`）的候选；同键自比一律不算（§25.3）。
    paired: Dict[str, List[dict]] = {}
    for pair in propose_pairs(left_units, base_units):
        if pair.strategy != "exact_collation_key":
            continue
        right = base_by_unit_key.get(pair.right_key)
        if right is None:
            continue
        paired.setdefault(pair.left_key, []).append(right)

    for unit in left_units:
        key = unit.get("collation_key")
        if not key:
            continue
        # 配对判断只经 matcher（CHARTER §3.1）：这里只消费它给出的候选，不自己比对键。
        paired_sources = {
            right.get("source_id") for right in paired.get(unit_key(unit)) or []
        }
        reasons = set()
        # §28 Q5：视图有键但**自己没声明**该单元 → view_undeclared（最高优先级）
        if key not in declared:
            reasons.add(NOT_COMPARABLE_VIEW_UNDECLARED)
        if len(view_assertions.get(key) or []) > 1:
            # §28 假设一：同侧同键 >1 条获批断言 → 推不出确定配对
            reasons.add(NOT_COMPARABLE_MULTIPLE)
        if declared.get(key) and not view_assertions.get(key):
            reasons.add(NOT_COMPARABLE_DECLARED_WITHOUT_ASSERTION)
        own_declares = any(key in edition["declared"] for edition in own)
        peer_declaring = [edition for edition in peers if key in edition["declared"]]
        if own_declares and not peer_declaring:
            # §25.3：唯一能对上的是**自己这个版次** → 不比自己
            reasons.add(NOT_COMPARABLE_SAME_SOURCE)
        if peers and any(key not in edition["declared"] for edition in peers):
            reasons.add(NOT_COMPARABLE_BASE_UNDECLARED)
        if editions and not own_declares and not peer_declaring:
            reasons.add(NOT_COMPARABLE_BASE_UNDECLARED)

        comparable: List[dict] = []
        if NOT_COMPARABLE_VIEW_UNDECLARED not in reasons and NOT_COMPARABLE_MULTIPLE not in reasons:
            if key in declared:
                view_present = declared[key]
                view_assertion = (view_assertions.get(key) or [None])[0]
                if view_present and view_assertion is None:
                    reasons.add(NOT_COMPARABLE_DECLARED_WITHOUT_ASSERTION)
                else:
                    for edition in peer_declaring:
                        if edition["source_id"] not in paired_sources:
                            reasons.add(NOT_COMPARABLE_BASE_UNDECLARED)
                            continue
                        assertions = edition["by_key"].get(key) or []
                        if len(assertions) > 1:
                            # §28 假设一：基底侧同键多条
                            reasons.add(NOT_COMPARABLE_MULTIPLE)
                            continue
                        base_present = edition["declared"][key]
                        base_assertion = assertions[0] if assertions else None
                        if base_present and base_assertion is None:
                            # §25.5：声明了 present 却没有获批断言
                            reasons.add(NOT_COMPARABLE_DECLARED_WITHOUT_ASSERTION)
                            continue
                        comparable.append(
                            {
                                "collation_key": key,
                                "view": {
                                    "source_id": view_source_id,
                                    "present": view_present,
                                    "assertion": view_assertion,
                                },
                                "base": {
                                    "source_id": edition["source_id"],
                                    "present": base_present,
                                    "assertion": base_assertion,
                                },
                            }
                        )
        if comparable:
            outcomes.extend(comparable)
        else:
            # §29 Q11 第 5 条：对所有基底版次都不可比 → 列一项，取优先级最高的理由。
            # 一个版次都没有时按 Gate 独立算法的同一口径落到 `base_undeclared`。
            add_row(
                key,
                _pick_not_comparable_reason(reasons)
                if reasons
                else NOT_COMPARABLE_BASE_UNDECLARED,
            )

    # §29 Q11 第 1 条：无键的两种都计，理由都是 missing_collation_key
    for aid in keyless_ids:
        rows.append(
            {
                "source_id": view_source_id,
                "collation_key": None,
                "assertion_id": aid,
                "reason": NOT_COMPARABLE_MISSING_COLLATION_KEY,
            }
        )
        counts[NOT_COMPARABLE_MISSING_COLLATION_KEY] = (
            counts.get(NOT_COMPARABLE_MISSING_COLLATION_KEY, 0) + 1
        )
    for _ in range(null_declarations):
        rows.append(
            {
                "source_id": view_source_id,
                "collation_key": None,
                "assertion_id": None,
                "reason": NOT_COMPARABLE_MISSING_COLLATION_KEY,
            }
        )
        counts[NOT_COMPARABLE_MISSING_COLLATION_KEY] = (
            counts.get(NOT_COMPARABLE_MISSING_COLLATION_KEY, 0) + 1
        )

    rows.sort(key=_not_comparable_sort_key)
    outcomes.sort(key=lambda item: (item["base"]["source_id"], item["collation_key"]))
    return outcomes, rows, counts


def collation_not_comparable(base_knowledge: dict, views: Sequence[dict]) -> List[dict]:
    """`not_comparable` 清单（CHARTER §28b / §29 Q11）——视图侧独立算，形状固定。

    `incremental.propose_incremental` 与本模块外（`apply` 的 `collation` 契约字段）共用
    这一个口径，避免两套写法漂移。"""
    rows: List[dict] = []
    for view in views:
        source_id, cset, reviewed = _view_parts(view)
        _, view_rows, _ = _collation_analysis(
            base_knowledge, cset, reviewed, source_id, _approved_index(reviewed)
        )
        rows.extend(view_rows)
    rows.sort(key=_not_comparable_sort_key)
    return rows


def _replacement_proposals(base_knowledge: dict, source_id: str, technique_id: str) -> List[Dict[str, Any]]:
    """act/03.yaml:46-49（替换模式：R11 删除断言 → retire；R11b 失去全部 provenance）。"""
    proposals = []
    for assertion in base_knowledge.get("assertions") or []:
        if assertion.get("source_id") != source_id:
            continue
        if not (assertion.get("evidence") or []):
            continue
        proposals.append(
            _proposal(
                "conflict", "R11", ["provenance_lost", assertion["assertion_id"]],
                resolution="auto", auto_choice="retire",
            )
        )
    for pattern in base_knowledge.get("patterns") or []:
        provenance = [p for p in pattern.get("provenance") or [] if p.get("source_id") == source_id]
        if provenance and all(p.get("content_sha256") is None for p in provenance):
            proposals.append(
                _proposal(
                    "conflict", "R11b", ["provenance_lost", pattern["pattern_id"]],
                    resolution="human", options=["retire", "keep"],
                )
            )
    return proposals


def _apply_decisions(
    proposals: List[Dict[str, Any]],
    decisions: Sequence[dict],
    base_by_id: Dict[str, dict],
    base_by_name: Dict[str, List[dict]],
    base_by_rule: Dict[str, List[dict]],
    distinct_pairs: set,
) -> List[Dict[str, Any]]:
    """回流：合法决定使提案 ``resolution = decided``；R10 按已裁决目标收紧命中集。"""
    decided = {
        decision.get("proposal_key"): decision
        for decision in decisions
        if decision.get("proposal_key")
    }
    if not decided:
        return proposals
    result = []
    for proposal in proposals:
        decision = decided.get(proposal["proposal_key"])
        if decision is None:
            result.append(proposal)
            continue
        choice = decision.get("choice")
        updated = dict(proposal)
        updated["resolution"] = "decided"
        if choice:
            updated["auto_choice"] = choice
        if choice and choice.startswith("attach:"):
            target_id = choice.split(":", 1)[1]
            target = base_by_id.get(target_id)
            if target is not None and distinct_pairs:
                excluded = {
                    endpoint
                    for pair in distinct_pairs
                    if target_id in pair
                    for endpoint in pair
                    if endpoint != target_id
                }
                if excluded:
                    updated["rule_id"] = "R10"
                    updated["targets"] = [target_id]
        result.append(updated)
    return result
