"""M7 增量汇编：应用裁定（act/impl-07/23 contract 二；规格 act/04.yaml:20-40）。

本模块是**纯函数层**：不写 Ledger、不改任何既有对象、不发登记 ID 前缀（除 M7 自己的
`pat_` 号位与 split 顺延的 `as_` 号）。

三处读法必须记录在案（见回报 §3）：

1. **§11 的 difflib 例外**：`difflib.SequenceMatcher.get_opcodes()` 只许用于
   **记录已确立配对的差异细节**（`variant_reading.detail.opcodes`），
   **不得参与任何配对/裁定判断**。配对结果只能来自提案（`targets`/`subject`）与视图声明。
   本文件是全仓库**唯一**允许导入 `difflib` 的汇编模块（`matcher.py` / `incremental.py` 禁止）。
2. **发号口径按 CHARTER §8.1**：号位只从「已获批、进入 Snapshot 的对象」取最大号 + 1；
   未获批却携带 M4 自发 `pat_` 号的候选**不计入号位**，并逐条写进
   ``report["unapproved_with_self_issued_id"]``。号位计算复用
   :func:`pipeline.assembly.incremental.allocate_ids`，与提案层**同源单一口径**。
3. **配对判断一律经 matcher**：本模块只调用 :func:`matcher.unpairable_units` 做
   「无法配对」计数，不自己做任何配对比对。

`merge_entities` 的口径（CHARTER §19.2、§21 ④）：旧号进 `retired_entity_ids`，身份变化只记在
IdentityDelta（`change_type="merged"`），**不写** `merged_into` 关系——
`model.validate_snapshot_knowledge` 要求 `relations` 端点必须是**活对象**，而已退役的旧号不该出现在关系表里。
两号合并时**较小的号存活**（`to`），较大的号退役（`from`）；退役号被任何活对象引用即 fail-closed（与 split 同口径）。
"""

import copy
import difflib
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from pipeline.assembly import matcher
from pipeline.assembly.canonical import (
    canonical_json,
    content_sha256,
    make_key,
    nfc_key,
    sha256_hex,
    work_key,
)
from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.incremental import allocate_ids
from pipeline.assembly.model import (
    empty_snapshot_knowledge,
    validate_candidate_set,
    validate_reviewed_edition,
    validate_snapshot_knowledge,
)
from pipeline.ledger import ids
from pipeline.ledger.errors import (
    DuplicateIdentifier,
    MissingReference,
    SchemaViolation,
)

#: 返回键逐字（act/04.yaml:39；`report` 为 §8.1 追加项，见回报 §3.3）
RESULT_KEYS = (
    "knowledge",
    "knowledge_bytes",
    "knowledge_sha256",
    "collation",
    "identity_delta",
    "created_entity_ids",
    "rebuilt_entity_ids",
    "resolution_log",
    "report",
)

#: IdentityDelta entry 键序逐字
IDENTITY_DELTA_ENTRY_FIELDS = (
    "from_entity_id",
    "to_entity_ids",
    "change_type",
    "entity_kind",
    "reason_ref",
)

#: IdentityDelta 变更类型闭集
CHANGE_TYPES = ("merged", "split", "retired")

#: 对勘四类（act/04.yaml:38）
COLLATION_KINDS = ("alignment", "variant_reading", "addition", "omission")

#: 需要人工决定的提案状态（human/blocked；blocked 未决即拒收，待依赖解除后重出）
NEEDS_DECISION = ("human", "blocked")

#: 可接受人工决定的提案状态：`decided` 是回流轮次按规格（act/03.yaml:26）记下的
#: 「已有合法决定」态，必须与 `human`/`blocked` 同样落地（CHARTER §21 ②）。
DECIDABLE = ("human", "blocked", "decided")

#: 决定必填键逐字
DECISION_REQUIRED_FIELDS = (
    "proposal_set_revision_id",
    "proposal_key",
    "choice",
    "target_entity_ids",
    "seen_revision_id",
    "decision_type",
)

#: 决定可选键
DECISION_OPTIONAL_FIELDS = ("span_allocation", "note")

_COLLECTIONS = ("patterns", "concepts", "assertions", "school_views")
_ID_KEYS = {
    "patterns": "pattern_id",
    "concepts": "concept_id",
    "assertions": "assertion_id",
    "school_views": "school_view_id",
}
_ENTITY_KINDS = {
    "patterns": "pattern",
    "concepts": "concept",
    "assertions": "assertion",
    "school_views": "school_view",
}

_PLACEHOLDER_PKG_REV = "rev_00000000000000000000000000000000"
_PLACEHOLDER_ED_REV = "rev_00000000000000000000000000000001"
_PLACEHOLDER_STAGE_PKG = "pkg_m6_00000000000000000000000000000000"


# --------------------------------------------------------------------------- 裁定校验
def validate_decision(proposal: dict, decision: dict) -> None:
    """校验一条人工决定（act/04.yaml:22-27）。

    - `proposal.resolution` 不是「待人工决定」态 → ``AssemblyRefused(SCH_002)``
    - 缺必填键 / 出现未知键 → ``SchemaViolation(SCH_001/SCH_002)``
    - `choice ∉ options`（`attach` 以 `"attach:<id>"` 比较）→ ``SchemaViolation(SCH_002)``
    - `decision_type` 非 ``None`` 时必须等于 `proposal.decision_type` → ``SchemaViolation(SCH_002)``
    - `split` 的 `span_allocation` 结构（键=新对象占位名、值=Span 号列表、两两不相交）
      → 违反即 ``SchemaViolation(SCH_002)``；「并集等于旧对象全部 source_span_ids」
      需要旧对象在座，由 :func:`apply_resolutions` 在基座上下文里补验。
    """
    if not isinstance(proposal, dict) or not proposal.get("proposal_key"):
        raise SchemaViolation("proposal 必须是含 proposal_key 的字典", code="SCH_001")
    if proposal.get("resolution") not in DECIDABLE:
        raise AssemblyRefused(
            "提案 %s 的 resolution=%r 不接受人工决定（只接受 %s）"
            % (proposal.get("proposal_key"), proposal.get("resolution"), list(DECIDABLE)),
            code="SCH_002",
        )
    if not isinstance(decision, dict):
        raise SchemaViolation("decision 必须为字典", code="SCH_001")

    missing = [key for key in DECISION_REQUIRED_FIELDS if key not in decision]
    if missing:
        raise SchemaViolation("决定缺必填键: %s" % sorted(missing), code="SCH_001")
    unknown = [
        key
        for key in decision
        if key not in DECISION_REQUIRED_FIELDS and key not in DECISION_OPTIONAL_FIELDS
    ]
    if unknown:
        raise SchemaViolation("决定含未知键: %s" % sorted(unknown), code="SCH_002")

    if decision["proposal_key"] != proposal["proposal_key"]:
        raise SchemaViolation(
            "决定 proposal_key=%r 与提案 %r 不一致"
            % (decision["proposal_key"], proposal["proposal_key"]),
            code="SCH_002",
        )
    if not isinstance(decision["target_entity_ids"], list):
        raise SchemaViolation("target_entity_ids 必须为列表", code="SCH_002")
    if not isinstance(decision["choice"], str) or not decision["choice"]:
        raise SchemaViolation("choice 必须为非空字符串", code="SCH_002")

    choice = decision["choice"]
    options = list(proposal.get("options") or [])
    if choice not in options:
        raise SchemaViolation(
            "choice=%r 不在提案 options=%r 内" % (choice, options), code="SCH_002"
        )

    decision_type = decision.get("decision_type")
    if decision_type is not None and decision_type != proposal.get("decision_type"):
        raise SchemaViolation(
            "decision_type=%r 与提案 %r 不一致" % (decision_type, proposal.get("decision_type")),
            code="SCH_002",
        )

    if choice == "split":
        _validate_span_allocation(decision.get("span_allocation"))


def _validate_span_allocation(allocation: Any) -> None:
    if not isinstance(allocation, dict) or not allocation:
        raise SchemaViolation(
            "split 决定必须带 span_allocation（键=新对象占位名，值=Span 号列表）", code="SCH_002"
        )
    seen: Set[str] = set()
    for placeholder, spans in allocation.items():
        if not isinstance(placeholder, str) or not placeholder:
            raise SchemaViolation("span_allocation 的键必须为非空占位名", code="SCH_002")
        if not isinstance(spans, list) or not spans:
            raise SchemaViolation(
                "span_allocation[%r] 必须为非空 Span 号列表" % (placeholder,), code="SCH_002"
            )
        for span_id in spans:
            if not isinstance(span_id, str):
                raise SchemaViolation("span_allocation 里出现非字符串 Span 号", code="SCH_002")
            if span_id in seen:
                raise SchemaViolation(
                    "span_allocation 的 Span 号在多个新对象间重复: %s" % span_id, code="SCH_002"
                )
            seen.add(span_id)


# --------------------------------------------------------------------------- 主体
def apply_resolutions(
    base_knowledge: dict,
    views: Sequence[dict],
    proposals: Sequence[dict],
    decisions: Sequence[dict],
    *,
    affected: Optional[Iterable[str]] = None,
) -> dict:
    """把裁定应用到基座知识上，产出新的 CanonicalKnowledgeSnapshot knowledge。

    - `affected=None` → 全部重建；`affected=集合` → 只重建集合内基底对象，
      集合外基底对象的规范 JSON **原样拷贝**（从 `base_knowledge` 取对象，不重新构造）
    - 结果经 :func:`pipeline.assembly.model.validate_snapshot_knowledge` 自检
    - 纯函数、确定性：同一输入两次调用 `knowledge_bytes` 逐字节相同
    """
    base = copy.deepcopy(base_knowledge or {})
    view_docs = [_resolve_view(view) for view in views]
    if not view_docs:
        raise AssemblyRefused("views 不得为空", code="SCH_001")

    technique_id = base.get("technique_id") or view_docs[0]["candidate_set"]["technique_id"]
    range_key = "pat_%s" % technique_id
    id_range = base.get("id_range")
    if not isinstance(id_range, dict) or range_key not in id_range:
        raise AssemblyRefused(
            "基座缺 id_range[%r]（创世轮须传入空基底号段）" % range_key, code="SCH_002"
        )
    range_start = int(id_range[range_key][0])

    proposal_index = _index_proposals(proposals, decisions, view_docs)
    affected_set = None if affected is None else {str(item) for item in affected}
    base_state = _index_base(base)
    touched: Set[str] = set()
    retired: Set[str] = set()
    new_relations: List[Dict[str, Any]] = []
    identity_entries: List[Dict[str, Any]] = []
    pruned: List[Dict[str, Any]] = []
    #: 本轮要删的基底关系及其理由（CHARTER §22.2：**静默删除一律不许**）
    dropped_relations: List[Dict[str, Any]] = []
    #: 基底关系（供 merge/split 的「基底 ∪ 本轮」引用检查；见 _referencing_relations）
    base_relations: List[dict] = list(base.get("relations") or [])

    # §8.1 号位与「未获批自发号」由 incremental.allocate_ids 统一口径计算；
    # 传**已规约**的视图（candidate_set / reviewed_edition 都是有效文档），
    # 避免 `{"doc": …}` 形状的输入在那里被当成「没有候选」而静默低估。
    allocation = allocate_ids(
        base,
        [
            {
                "source_id": view["source_id"],
                "candidate_set": view["candidate_set"],
                "reviewed_edition": view["reviewed_edition"],
            }
            for view in view_docs
        ],
    )
    watermark = int(allocation["id_allocation"].get(range_key, 0) or 0)

    editions = _merge_editions(base_state, view_docs)
    concepts, materialized_concepts = _build_concepts(base_state, view_docs, touched)
    patterns, allocated_new, distinct_pairs, materialized_patterns = _build_patterns(
        base_state, view_docs, proposal_index, watermark, range_start, range_key, touched
    )
    assertions, materialized_assertions = _build_assertions(
        base_state, view_docs, proposal_index, touched
    )
    materialized = {
        "pattern": materialized_patterns,
        "concept": materialized_concepts,
        "assertion": materialized_assertions,
    }
    school_views = _build_school_views(base_state, view_docs, touched)
    _link_subjects(patterns, assertions)
    _link_school_views(patterns, assertions, school_views)
    conflict_groups = _build_conflict_groups(base_state, school_views)

    knowledge = _template(base, technique_id, id_range)
    knowledge["editions"] = editions
    knowledge["concepts"] = concepts
    knowledge["patterns"] = patterns
    knowledge["assertions"] = assertions
    knowledge["school_views"] = school_views
    knowledge["conflict_groups"] = conflict_groups
    knowledge["allocated_pattern_ids"] = sorted(
        set(base.get("allocated_pattern_ids") or []) | set(allocated_new)
    )

    live = _live_index(knowledge)

    # ---------------------------------------------------------------- 逐提案落地
    for pair in distinct_pairs:
        new_relations.append(
            _relation_for("distinct_from", pair[0], pair[1], {}, pair[2], mode="human")
        )

    for proposal in proposal_index["ordered"]:
        decision = proposal_index["by_decision"].get(proposal["proposal_key"])
        if decision is not None:
            validate_decision(proposal, decision)
            choice, mode = decision["choice"], "human"
        elif proposal.get("resolution") == "auto":
            choice, mode = proposal.get("auto_choice"), "auto"
        elif proposal.get("resolution") == "decided":
            raise AssemblyRefused(
                "提案 %s 的 resolution='decided' 却找不到对应决定：decided 必须真有一条合法决定"
                % proposal.get("proposal_key"),
                code="SCH_002",
            )
        else:
            continue
        if not choice:
            continue

        if choice == "merge_entities":
            _apply_merge(
                proposal,
                decision,
                live,
                knowledge,
                identity_entries,
                touched,
                retired,
                extra_relations=base_relations,
            )
            continue
        if choice == "split":
            _apply_split(
                proposal,
                decision,
                live,
                knowledge,
                identity_entries,
                touched,
                retired,
                extra_relations=base_relations,
            )
            continue
        if choice == "retire":
            target = proposal["subject"][-1] if proposal.get("subject") else None
            _apply_retire(
                target,
                live,
                knowledge,
                identity_entries,
                touched,
                retired,
                pruned,
                proposal_key=proposal["proposal_key"],
            )
            continue
        if choice == "accept_alias":
            new_relations.append(_apply_accept_alias(proposal, view_docs, live))
            continue
        if choice in COLLATION_KINDS or choice == "accept_alignment":
            relation = _apply_evidence(proposal, choice, base_state, view_docs, live)
            if relation is not None:
                new_relations.append(relation)
            continue
        if choice in ("unify", "keep_separate"):
            _record_group_resolution(choice, proposal, knowledge)
            continue

    # attached：auto 或人工 attach 且目标在基底已存在（创世与 R02 不写）
    new_relations.extend(
        _attached_relations(base_state, view_docs, knowledge, proposal_index["attach_choices"])
    )

    _remove_retired(knowledge, retired)
    _restore_untouched(base, knowledge, base_state, affected_set, touched)
    # §22.2：删除两种随身份变化作废的基底关系，且必须如实记账（静默删除一律不许）：
    #   ① 合并双方彼此之间的关系（merge_internal）
    #   ② 指向已退役号的关系（endpoint_retired，含 R11 退役断言）
    merge_pairs = [
        (entry["from_entity_id"], entry["to_entity_ids"][0])
        for entry in identity_entries
        if entry["change_type"] == "merged" and entry.get("to_entity_ids")
    ]
    for relation in base.get("relations", []):
        if not _relation_touches(relation, retired):
            continue
        dropped_relations.append(
            {
                "relation_key": relation["relation_key"],
                "reason": "merge_internal"
                if any(_is_merge_internal(relation, pair) for pair in merge_pairs)
                else "endpoint_retired",
            }
        )
    knowledge["relations"] = sorted(
        [rel for rel in copy.deepcopy(base.get("relations", [])) if not _relation_touches(rel, retired)]
        + new_relations,
        key=lambda rel: rel["relation_key"],
    )
    knowledge["retired_entity_ids"] = sorted(set(base.get("retired_entity_ids") or []) | retired)
    knowledge["id_allocation"] = _id_allocation(base, knowledge, technique_id, range_key)
    _sort_knowledge(knowledge)

    collation_relations = [
        rel for rel in knowledge["relations"] if rel["relation_kind"] in COLLATION_KINDS
    ]
    collation = {
        "relations": collation_relations,
        "not_comparable": _not_comparable(view_docs),
    }
    identity_delta = {
        "base_knowledge_sha256": sha256_hex(canonical_json(base)),
        "entries": sorted(
            identity_entries,
            key=lambda entry: (entry["change_type"], entry["from_entity_id"]),
        ),
    }

    # admit_new 却没产出对象（例如无正式 co_ 号的 concept 候选）：必须如实报告，不得静默丢弃
    without_object = _admit_new_without_object(proposal_index, materialized)

    validate_snapshot_knowledge(knowledge)

    knowledge_bytes = canonical_json(knowledge)
    return {
        "knowledge": knowledge,
        "knowledge_bytes": knowledge_bytes,
        "knowledge_sha256": sha256_hex(knowledge_bytes),
        "collation": collation,
        "identity_delta": identity_delta,
        "created_entity_ids": sorted(_created_ids(base_state, knowledge)),
        "rebuilt_entity_ids": _rebuilt_ids(base_state, touched, affected_set),
        "resolution_log": _resolution_log(proposal_index),
        "report": {
            "id_allocation": copy.deepcopy(knowledge.get("id_allocation") or {}),
            "allocated_pattern_ids": list(knowledge["allocated_pattern_ids"]),
            "unapproved_with_self_issued_id": copy.deepcopy(
                allocation["unapproved_with_self_issued_id"]
            ),
            "pruned_relations_for_retired": pruned,
            "admit_new_without_object": without_object,
            # ACT 28 / CHARTER §22.2：随退役或合并删除的基底关系及其理由，按 relation_key 升序
            "dropped_relations": sorted(
                dropped_relations, key=lambda item: item["relation_key"]
            ),
        },
    }


# --------------------------------------------------------------------------- 视图/基座
def _resolve_view(view: dict) -> Dict[str, Any]:
    """规约一份视图（支持已校验结果与原始文档两种形状）。"""
    candidate_set_doc = view.get("candidate_set")
    reviewed_doc = view.get("reviewed_edition")
    if "doc" in candidate_set_doc:
        cset_doc = candidate_set_doc["doc"]
        source_id = candidate_set_doc.get("source_id") or cset_doc["source_id"]
    else:
        checked = validate_candidate_set(candidate_set_doc)
        cset_doc = checked["doc"]
        source_id = checked["source_id"]
    if "doc" in reviewed_doc:
        reviewed = reviewed_doc["doc"]
        approved_index = reviewed_doc.get("approved_index") or {
            item["entity_id"]: item for item in reviewed.get("approved", [])
        }
    else:
        checked = validate_reviewed_edition(reviewed_doc)
        reviewed = checked["doc"]
        approved_index = checked["approved_index"]
    return {
        "source_id": source_id,
        "candidate_set": cset_doc,
        "reviewed_edition": reviewed,
        "approved_index": approved_index,
    }


def _index_base(base: dict) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        collection: {item[_ID_KEYS[collection]]: item for item in base.get(collection, [])}
        for collection in _COLLECTIONS
    }
    state["conflict_groups"] = {
        item["conflict_group_id"]: item for item in base.get("conflict_groups", [])
    }
    state["editions"] = {item["source_id"]: item for item in base.get("editions", [])}
    state["retired"] = set(base.get("retired_entity_ids") or [])
    state["relations"] = list(base.get("relations") or [])
    state["alive"] = set().union(*(set(state[collection]) for collection in _COLLECTIONS))
    return state


def _template(base: dict, technique_id: str, id_range: dict) -> dict:
    """knowledge 顶层模板：空基底用创世同形；有基底则保留其元数据（id_range/meta/…）。"""
    if base.get("technique_id"):
        knowledge = copy.deepcopy(base)
        for collection in _COLLECTIONS:
            knowledge[collection] = []
        knowledge["conflict_groups"] = []
        knowledge["relations"] = []
        knowledge.setdefault("retired_entity_ids", [])
        knowledge.setdefault("allocated_pattern_ids", [])
        return knowledge
    knowledge = empty_snapshot_knowledge(technique_id, copy.deepcopy(id_range))
    return knowledge


def _live_index(knowledge: dict) -> Dict[str, Dict[str, dict]]:
    return {
        collection: {
            item[_ID_KEYS[collection]]: item for item in knowledge.get(collection, [])
        }
        for collection in _COLLECTIONS
    }


# --------------------------------------------------------------------------- 版次
def _merge_editions(base_state: Dict[str, Any], view_docs: Sequence[Dict[str, Any]]) -> List[dict]:
    """版次合并（D-14 / ACT 28 一）：新 source 追加；同 `(source_id, edition_part_ids)` 视为**替换**。

    - **替换**：`editions[]` 里原条目被替换，**不新增条目**；并按规格继承基底该版次的
      `reviewed_edition_*` 身份字段（识别口径是 part 集合，不是 `stage_package_id`）
    - **扩展**（同 source、part 集合不相交）：本波不做，遇则拒收并写明
    - part 集合**部分重叠**：无法判定，拒收（与 `incremental._classify_modes` 同口径）
    """
    editions = sorted(
        copy.deepcopy(list(base_state["editions"].values())), key=lambda ed: ed["source_id"]
    )
    for view in view_docs:
        source_id = view["source_id"]
        entry = {
            "source_id": source_id,
            "work_key": work_key(source_id),
            "reviewed_edition_package_revision_id": (
                view["reviewed_edition"].get("reviewed_edition_package_revision_id")
                or _PLACEHOLDER_PKG_REV
            ),
            "reviewed_edition_revision_id": (
                view["reviewed_edition"].get("reviewed_edition_revision_id")
                or _PLACEHOLDER_ED_REV
            ),
            "stage_package_id": (
                view["reviewed_edition"].get("stage_package_id") or _PLACEHOLDER_STAGE_PKG
            ),
            "edition_part_artifact_ids": [view["candidate_set"]["edition_part_artifact_id"]],
            "edition_complete": False,
            "evidence_level": view["candidate_set"]["evidence_level"],
            "corpus_spans_revision_id": _corpus_spans_revision_id(view),
        }
        previous = base_state["editions"].get(source_id)
        if previous is None:
            editions.append(entry)
            continue

        declared = {view["candidate_set"]["edition_part_artifact_id"]}
        existing = set(previous.get("edition_part_artifact_ids") or [])
        if declared != existing and not (declared & existing):
            raise AssemblyRefused(
                "同 source 不同 edition_part_ids 的扩展属后续波次（本波不做）: %s 基底 %s / 视图 %s"
                % (source_id, sorted(existing), sorted(declared)),
                code="SCH_002",
            )
        if declared != existing:
            raise AssemblyRefused(
                "版次 %s 的 edition_part_ids 与基底部分重叠，无法判定替换或扩展: %s vs %s"
                % (source_id, sorted(declared), sorted(existing)),
                code="SCH_002",
            )
        # 替换：继承基底该版次的 reviewed_edition_* 身份字段（不新增条目）
        for key in ("reviewed_edition_package_revision_id", "reviewed_edition_revision_id"):
            entry[key] = previous.get(key) or entry[key]
        editions = [ed for ed in editions if ed["source_id"] != source_id]
        editions.append(entry)
    editions.sort(key=lambda ed: ed["source_id"])
    return editions


def _corpus_spans_revision_id(view: Dict[str, Any]) -> Optional[str]:
    """取本版次 evidence_links 里唯一的 corpus_spans 修订；两个及以上不同值即停手。"""
    values = {
        link.get("corpus_spans_revision_id")
        for link in view["reviewed_edition"].get("evidence_links", [])
        if link.get("corpus_spans_revision_id") is not None
    }
    if len(values) > 1:
        raise AssemblyRefused(
            "evidence_links 中出现多个不同的 corpus_spans_revision_id，须停手上报: %s"
            % sorted(values),
            code="SCH_002",
        )
    return values.pop() if values else None


# --------------------------------------------------------------------------- 概念
def _surfaces_of_concept(concept: dict) -> Set[str]:
    surfaces = {nfc_key(concept["name"])}
    surfaces.update(nfc_key(alias) for alias in concept.get("aliases") or [])
    return surfaces


def _build_concepts(
    base_state: Dict[str, Any], view_docs: Sequence[Dict[str, Any]], touched: Set[str]
) -> Tuple[List[dict], Set[str]]:
    concepts = copy.deepcopy(list(base_state["concepts"].values()))
    by_id = {item["concept_id"]: item for item in concepts}
    materialized: Set[str] = set()

    for view in view_docs:
        source_id = view["source_id"]
        technique_id = view["candidate_set"]["technique_id"]
        mentions: Dict[str, List[dict]] = {}
        for mention in view["candidate_set"].get("concept_mentions", []):
            ref = mention.get("concept_ref")
            if ref:
                mentions.setdefault(ref, []).append(mention)

        for ref, items in mentions.items():
            if ids.kind_of(ref) != "technique_concept_id":
                raise DuplicateIdentifier(
                    "concept_ref 不属于 co_ 家族，碰撞即 fail-closed: %s" % ref, code="ID_002"
                )
            if ref[len("co_"):].split("_", 1)[0] != technique_id:
                raise DuplicateIdentifier(
                    "co_ 号 %s 的技法段与 Snapshot 技法 %s 不一致（撞号 fail-closed）"
                    % (ref, technique_id),
                    code="ID_002",
                )
            surfaces = sorted({nfc_key(item["surface"]) for item in items})
            materialized.add(ref)
            materialized.update(surfaces)
            existing = by_id.get(ref)
            if existing is None:
                by_id[ref] = {
                    "concept_id": ref,
                    "name": surfaces[0],
                    "aliases": surfaces[1:],
                    "provenance": [_concept_provenance(source_id, surfaces[0], surfaces[1:], items)],
                }
                continue

            touched.add(ref)
            declared_sources = {
                entry.get("source_id") for entry in existing.get("provenance") or []
            }
            if source_id in declared_sources and not (_surfaces_of_concept(existing) & set(surfaces)):
                raise DuplicateIdentifier(
                    "co_ 号 %s 已由同一版次 %s 声明为 %s，候选却声明 %s 且无别名交集"
                    % (ref, source_id, sorted(_surfaces_of_concept(existing)), surfaces),
                    code="ID_002",
                )
            existing["aliases"] = sorted(
                set(existing.get("aliases") or [])
                | set(surfaces[1:])
                | ({surfaces[0]} - {nfc_key(existing["name"])})
            )
            existing.setdefault("provenance", [])
            if source_id not in declared_sources:
                existing["provenance"].append(
                    _concept_provenance(source_id, surfaces[0], surfaces[1:], items)
                )

    return sorted(by_id.values(), key=lambda item: item["concept_id"]), materialized


def _concept_provenance(
    source_id: str, name: str, aliases: Sequence[str], items: Sequence[dict]
) -> dict:
    return {
        "source_id": source_id,
        "content_sha256": content_sha256({"name": name, "aliases": list(aliases)}),
        "content_status": items[0].get("content_status", "machine_extracted"),
    }


# --------------------------------------------------------------------------- 格局
def _build_patterns(
    base_state: Dict[str, Any],
    view_docs: Sequence[Dict[str, Any]],
    proposal_index: Dict[str, Any],
    watermark: int,
    range_start: int,
    range_key: str,
    touched: Set[str],
) -> Tuple[List[dict], List[str], List[Tuple[str, str, str]], Set[str]]:
    """装配 patterns（返回值含「实际发成对象」的候选键集，用于防静默丢弃）。

    - 已获批、无号的候选（`candidate_key`）按 **(source_id, candidate_key) 升序**发新号
    - 已获批、带正式号的候选：默认并入（attach）；若决定要求 `admit_new`/`reject_alias`
      则**另发新号**并留 `distinct_from(较小号, 较大号)`
    """
    technique_id = range_key[len("pat_"):]
    patterns = copy.deepcopy(list(base_state["patterns"].values()))
    by_id = {item["pattern_id"]: item for item in patterns}
    allocated: List[str] = []
    distinct_pairs: List[Tuple[str, str, str]] = []

    pending: List[Tuple[str, str, dict, Dict[str, Any]]] = []
    for view in view_docs:
        for candidate in view["candidate_set"].get("patterns", []):
            if candidate.get("pattern_id"):
                continue
            if not _is_approved(view["approved_index"], candidate):
                continue
            pending.append(
                (view["source_id"], candidate.get("candidate_key") or "", candidate, view)
            )
    pending.sort(key=lambda item: (item[0], item[1]))

    used = _used_pattern_numbers(base_state, technique_id)
    number = max(watermark + 1, range_start)
    for source_id, _key, candidate, view in pending:
        while number in used:
            number += 1
        new_id = "pat_%s_%06d" % (technique_id, number)
        by_id[new_id] = _new_pattern(new_id, source_id, candidate, view)
        used.add(number)
        allocated.append(new_id)
        number += 1

    for view in view_docs:
        source_id = view["source_id"]
        for candidate in view["candidate_set"].get("patterns", []):
            pattern_id = candidate.get("pattern_id")
            if not pattern_id or not _is_approved(view["approved_index"], candidate):
                continue
            choice, proposal_key = _effective_choice(proposal_index, pattern_id, source_id, candidate)
            existing = by_id.get(pattern_id)
            if existing is None:
                # 携带正式号且基底无此号 → 以该号入账（admit_new 的「另立」语义由
                # `distinct_from` 记录，不另发号）
                by_id[pattern_id] = _new_pattern(pattern_id, source_id, candidate, view)
                if choice in ("admit_new", "reject_alias"):
                    for target in proposal_index["targets_of"].get((source_id, pattern_id), []):
                        if target == pattern_id or target not in by_id:
                            continue
                        distinct_pairs.append(
                            (
                                min(target, pattern_id),
                                max(target, pattern_id),
                                proposal_key or "unknown",
                            )
                        )
                continue
            if choice in ("admit_new", "reject_alias"):
                raise DuplicateIdentifier(
                    "候选 %s（source=%s）已被裁定 %s，但它携带的 pat_ 号 %s 已被基底对象占用："
                    "一个正式号只能指一个对象，号已占用即碰撞 fail-closed"
                    % (pattern_id, source_id, choice, pattern_id),
                    code="ID_002",
                )
            if pattern_id in base_state["retired"]:
                raise DuplicateIdentifier(
                    "候选携带的 pat_ 号已退役，禁止复活: %s" % pattern_id, code="ID_002"
                )
            touched.add(pattern_id)
            # D-14 替换继承（CHARTER §21 ①）：provenance 未变的对象本轮不再产生 merge 提案
            # （沿用 Snapshot 结果），也就没有内容并入 → 不要求留痕；内容变了才必须留痕。
            if _pattern_provenance_changed(existing, source_id, candidate):
                _require_trace(
                    proposal_index, source_id, pattern_id, candidate.get("collation_key")
                )
            existing["assertion_ids"] = sorted(
                set(existing.get("assertion_ids") or [])
                | set(_approved_assertion_ids(candidate, view))
            )
            existing.setdefault("provenance", [])
            if source_id not in {entry.get("source_id") for entry in existing["provenance"]}:
                existing["provenance"].append(
                    {
                        "source_id": source_id,
                        "content_sha256": content_sha256(candidate),
                        "content_status": candidate.get("content_status", "machine_extracted"),
                    }
                )

    patterns = sorted(by_id.values(), key=lambda item: item["pattern_id"])
    materialized: Set[str] = set()
    for view in view_docs:
        for candidate in view["candidate_set"].get("patterns", []):
            if not _is_approved(view["approved_index"], candidate):
                continue
            key = candidate.get("pattern_id") or candidate.get("candidate_key")
            if key:
                materialized.add(key)
    return patterns, allocated, distinct_pairs, materialized


def _pattern_provenance_changed(existing: dict, source_id: str, candidate: dict) -> bool:
    """候选内容是否与基底该 source 的 provenance 哈希不同（与 D-14 同一口径）。"""
    expected = content_sha256(candidate)
    return not any(
        row.get("source_id") == source_id and row.get("content_sha256") == expected
        for row in existing.get("provenance") or []
    )


def _new_pattern(pattern_id: str, source_id: str, candidate: dict, view: Dict[str, Any]) -> dict:
    return {
        "pattern_id": pattern_id,
        "concept_id": None,
        "name": candidate["name"],
        "aliases": [],
        "rules": [],
        "assertion_ids": _approved_assertion_ids(candidate, view),
        "school_view_ids": [],
        "recognition_rule_status": candidate.get("recognition_rule_status", "not_captured"),
        "provenance": [
            {
                "source_id": source_id,
                "content_sha256": content_sha256(candidate),
                "content_status": candidate.get("content_status", "machine_extracted"),
            }
        ],
    }


def _used_pattern_numbers(base_state: Dict[str, Any], technique_id: str) -> Set[int]:
    used: Set[int] = set()
    for pattern_id in list(base_state["patterns"]) + list(base_state["retired"]):
        number = _number_of(pattern_id, technique_id)
        if number is not None:
            used.add(number)
    return used


def _number_of(pattern_id: Any, technique_id: str) -> Optional[int]:
    prefix = "pat_%s_" % technique_id
    if not isinstance(pattern_id, str) or not pattern_id.startswith(prefix):
        return None
    digits = pattern_id[len(prefix):]
    return int(digits) if re.match(r"^[0-9]{6}$", digits) else None


def _approved_assertion_ids(candidate: dict, view: Dict[str, Any]) -> List[str]:
    """候选声明的断言里**已获批**的那些（approved_index 按 entity_id 索引）。"""
    approved = view["approved_index"]
    return sorted(
        aid
        for aid in candidate.get("assertion_ids", [])
        if aid in approved and approved[aid].get("kind") == "assertion"
    )


def _is_approved(approved: Dict[str, dict], candidate: dict) -> bool:
    for key in (candidate.get("pattern_id"), candidate.get("candidate_key")):
        if key and key in approved:
            return True
    return False


# --------------------------------------------------------------------------- 断言
def _build_assertions(
    base_state: Dict[str, Any],
    view_docs: Sequence[Dict[str, Any]],
    proposal_index: Dict[str, Any],
    touched: Set[str],
) -> Tuple[List[dict], Set[str]]:
    assertions = copy.deepcopy(list(base_state["assertions"].values()))
    by_id = {item["assertion_id"]: item for item in assertions}
    materialized: Set[str] = set()

    for view in view_docs:
        source_id = view["source_id"]
        technique_id = view["candidate_set"]["technique_id"]
        links_by_entity = _links_by_entity(view["reviewed_edition"])
        for candidate in view["candidate_set"].get("assertions", []):
            aid = candidate["assertion_id"]
            if aid not in view["approved_index"]:
                continue
            materialized.add(aid)
            prop_nfc = nfc_key(candidate["proposition"])
            evidence = _evidence_of(candidate, links_by_entity)
            existing = by_id.get(aid)
            if existing is None:
                by_id[aid] = {
                    "assertion_id": aid,
                    "subject_entity_id": None,
                    "source_id": source_id,
                    "proposition": prop_nfc,
                    "collation_key": candidate.get("collation_key"),
                    "text_sha256": sha256_hex(prop_nfc.encode("utf-8")),
                    "source_span_ids": sorted({item["source_span_id"] for item in evidence}),
                    "evidence": evidence,
                    "school_view_ids": [],
                    "content_status": view["approved_index"][aid]["content_status"],
                }
                continue

            # as_ 号碰撞检测：同号必须同命题（M4 一个号一个命题）；否则 fail-closed
            if _as_number_of(aid, technique_id) is not None and nfc_key(
                existing["proposition"]
            ) != prop_nfc:
                raise DuplicateIdentifier(
                    "as_ 号 %s 已指向命题 %r，候选却声称 %r（撞号 fail-closed）"
                    % (aid, existing["proposition"], prop_nfc),
                    code="ID_002",
                )
            if aid in base_state["retired"]:
                raise DuplicateIdentifier(
                    "候选携带的 as_ 号已退役，禁止复活: %s" % aid, code="ID_002"
                )
            touched.add(aid)
            _require_trace(proposal_index, source_id, aid, candidate.get("collation_key"))
            merged = {_evidence_key(item): item for item in existing.get("evidence") or []}
            for item in evidence:
                merged.setdefault(_evidence_key(item), item)
            existing["evidence"] = [merged[key] for key in sorted(merged)]
            existing["source_span_ids"] = sorted(
                {item["source_span_id"] for item in existing["evidence"]}
            )

    return sorted(by_id.values(), key=lambda item: item["assertion_id"]), materialized


def _as_number_of(assertion_id: Any, technique_id: str) -> Optional[int]:
    prefix = "as_%s_" % technique_id
    if not isinstance(assertion_id, str) or not assertion_id.startswith(prefix):
        return None
    digits = assertion_id[len(prefix):]
    return int(digits) if re.match(r"^[0-9]{6}$", digits) else None


def _evidence_key(item: dict) -> Tuple[str, Any, Any]:
    return (item["source_span_id"], item.get("start_offset"), item.get("end_offset"))


def _evidence_of(candidate: dict, links_by_entity: Dict[str, List[dict]]) -> List[dict]:
    links = links_by_entity.get(candidate["assertion_id"])
    if links:
        m4_evidence = {item["source_span_id"]: item for item in candidate.get("evidence") or []}
        for link in links:
            span_id = link["source_span_id"]
            if span_id in m4_evidence:
                original = m4_evidence[span_id]
                if (
                    link["start_offset"] != original["start_offset"]
                    or link["end_offset"] != original["end_offset"]
                ):
                    raise AssemblyRefused(
                        "M6 链与 M4 候选在 source_span_id=%r 上的偏移不一致" % span_id,
                        code="SCH_002",
                    )
        source = links
    else:
        source = candidate.get("evidence") or []
    evidence = [
        {
            "source_span_id": item["source_span_id"],
            "start_offset": item["start_offset"],
            "end_offset": item["end_offset"],
            "quote_sha256": item["quote_sha256"],
        }
        for item in source
    ]
    evidence.sort(
        key=lambda item: (item["source_span_id"], item["start_offset"], item["end_offset"])
    )
    return evidence


def _links_by_entity(reviewed: dict) -> Dict[str, List[dict]]:
    links: Dict[str, List[dict]] = {}
    for link in reviewed.get("evidence_links", []):
        links.setdefault(link["entity_id"], []).append(link)
    return links


# --------------------------------------------------------------------------- 学校观/冲突组
def _build_school_views(
    base_state: Dict[str, Any], view_docs: Sequence[Dict[str, Any]], touched: Set[str]
) -> List[dict]:
    school_views = copy.deepcopy(list(base_state["school_views"].values()))
    by_id = {item["school_view_id"]: item for item in school_views}

    for view in view_docs:
        for candidate in view["candidate_set"].get("school_views", []):
            svid = candidate["school_view_id"]
            if svid not in view["approved_index"]:
                continue
            declared_cg = candidate.get("conflict_group_id")
            existing = by_id.get(svid)
            if existing is None:
                by_id[svid] = {
                    "school_view_id": svid,
                    "school_id": candidate["school_id"],
                    "subject_entity_id": candidate["subject_entity_id"],
                    "conflict_group_id": _resolve_conflict_group_id(declared_cg, base_state),
                    "source_conflict_group_id": declared_cg,
                    "claim_refs": sorted(set(candidate.get("claim_refs") or [])),
                    "changes_current_judgment": candidate["changes_current_judgment"],
                    "content_status": view["approved_index"][svid]["content_status"],
                }
                continue
            touched.add(svid)
            existing["claim_refs"] = sorted(
                set(existing.get("claim_refs") or []) | set(candidate.get("claim_refs") or [])
            )
            existing["changes_current_judgment"] = bool(
                existing["changes_current_judgment"] or candidate["changes_current_judgment"]
            )

    return sorted(by_id.values(), key=lambda item: item["school_view_id"])


def _link_subjects(patterns: Sequence[dict], assertions: Sequence[dict]) -> None:
    """断言的主体指回格局（口径同创世引擎：命中多个取最小号，无命中为 null）。"""
    claims: Dict[str, List[str]] = {}
    for pattern in patterns:
        for assertion_id in pattern.get("assertion_ids") or []:
            claims.setdefault(assertion_id, []).append(pattern["pattern_id"])
    for assertion in assertions:
        matched = sorted(claims.get(assertion["assertion_id"], []))
        assertion["subject_entity_id"] = matched[0] if matched else None


def _link_school_views(
    patterns: Sequence[dict], assertions: Sequence[dict], school_views: Sequence[dict]
) -> None:
    """把学校观回填到断言/格局（口径同创世引擎：断言记 subject ∪ claim_refs，格局只记 subject）。"""
    by_claim: Dict[str, Set[str]] = {}
    by_subject: Dict[str, Set[str]] = {}
    for sv in school_views:
        svid = sv["school_view_id"]
        subject = sv.get("subject_entity_id")
        if subject:
            by_subject.setdefault(subject, set()).add(svid)
            by_claim.setdefault(subject, set()).add(svid)
        for claim in sv.get("claim_refs") or []:
            by_claim.setdefault(claim, set()).add(svid)
    for assertion in assertions:
        assertion["school_view_ids"] = sorted(by_claim.get(assertion["assertion_id"], set()))
    for pattern in patterns:
        pattern["school_view_ids"] = sorted(by_subject.get(pattern["pattern_id"], set()))


def _resolve_conflict_group_id(declared: Optional[str], base_state: Dict[str, Any]) -> Optional[str]:
    """unify：视图声明的组正是某基底组的来源组时，落到基底组号（保号）。"""
    if not declared:
        return None
    for group in base_state["conflict_groups"].values():
        if group.get("source_conflict_group_id") == declared:
            return group["conflict_group_id"]
    return declared


def _build_conflict_groups(
    base_state: Dict[str, Any], school_views: Sequence[dict]
) -> List[dict]:
    groups: Dict[str, Dict[str, Any]] = {
        group["conflict_group_id"]: copy.deepcopy(group)
        for group in base_state["conflict_groups"].values()
    }
    members: Dict[str, List[dict]] = {}
    for sv in school_views:
        cg_id = sv.get("conflict_group_id")
        if cg_id:
            members.setdefault(cg_id, []).append(sv)

    for cg_id, rows in members.items():
        member_ids = sorted(row["school_view_id"] for row in rows)
        first_layer = any(row["changes_current_judgment"] for row in rows)
        existing = groups.get(cg_id)
        if existing is None:
            groups[cg_id] = {
                "conflict_group_id": cg_id,
                "member_school_view_ids": member_ids,
                "first_layer_display": first_layer,
                "resolutions": [],
            }
        else:
            existing["member_school_view_ids"] = member_ids
            existing["first_layer_display"] = first_layer
            existing.setdefault("resolutions", [])
            existing["resolutions"].sort(
                key=lambda row: (row.get("mode") or "", row.get("proposal_key") or "")
            )
    return sorted(groups.values(), key=lambda item: item["conflict_group_id"])


def _record_group_resolution(choice: str, proposal: dict, knowledge: dict) -> None:
    """unify → 落到基底组号；keep_separate → 以视图 cg_ 号独立登记，并记一条 resolution。"""
    targets = list(proposal.get("targets") or [])
    wanted = set(targets)
    for group in knowledge["conflict_groups"]:
        if wanted and group["conflict_group_id"] not in wanted:
            continue
        group.setdefault("resolutions", [])
        group["resolutions"] = [
            row for row in group["resolutions"] if row.get("proposal_key") != proposal["proposal_key"]
        ]
        group["resolutions"].append(
            {
                "mode": "human",
                "proposal_key": proposal["proposal_key"],
                "basis_sha256": proposal.get("basis_sha256"),
            }
        )
        group["resolutions"].sort(
            key=lambda row: (row.get("mode") or "", row.get("proposal_key") or "")
        )


# --------------------------------------------------------------------------- 决定落地
def _apply_split(
    proposal: dict,
    decision: dict,
    live: Dict[str, Any],
    knowledge: dict,
    identity_entries: List[Dict[str, Any]],
    touched: Set[str],
    retired: Set[str],
    *,
    extra_relations: Sequence[dict] = (),
) -> None:
    """split：占位名升序发新号、旧号退役、IdentityDelta 一条 split 携带 span_allocation。"""
    targets = list(decision.get("target_entity_ids") or [])
    if len(targets) != 1:
        raise SchemaViolation("split 决定的 target_entity_ids 必须恰含一个旧对象号", code="SCH_002")
    old_id = targets[0]
    location = _locate(live, old_id)
    if location is None:
        raise MissingReference("split 目标不在 Snapshot 活对象里: %s" % old_id, code="REF_001")
    collection, item = location
    if collection != "assertions":
        raise AssemblyRefused(
            "split 当前只支持断言（%s 的 split 需要 pattern/概念的发号口径裁定）" % collection,
            code="SCH_002",
        )
    allocation_input = decision["span_allocation"]
    declared_spans = sorted({span for spans in allocation_input.values() for span in spans})
    if declared_spans != sorted(item.get("source_span_ids") or []):
        raise SchemaViolation(
            "split 的 span_allocation 并集必须等于旧对象的全部 source_span_ids：%s != %s"
            % (declared_spans, sorted(item.get("source_span_ids") or [])),
            code="SCH_002",
        )

    referencing = _referenced_by(knowledge, old_id, extra_relations)
    if referencing:
        raise AssemblyRefused(
            "split 目标 %s 被 %s 引用；act/04 未规定引用改指规则，停手上报（回报 §3.2）"
            % (old_id, sorted(referencing)),
            code="SCH_002",
        )

    technique_id = knowledge["technique_id"]
    allocation: Dict[str, List[str]] = {}
    for placeholder in sorted(allocation_input):
        new_id = _next_assertion_id(live, technique_id)
        # 占位名替换为新号（act/04.yaml:33）
        allocation[new_id] = sorted(allocation_input[placeholder])
        clone = copy.deepcopy(item)
        clone["assertion_id"] = new_id
        clone["source_span_ids"] = sorted(allocation_input[placeholder])
        clone["evidence"] = [
            entry
            for entry in clone.get("evidence", [])
            if entry["source_span_id"] in clone["source_span_ids"]
        ]
        knowledge["assertions"].append(clone)
        live["assertions"][new_id] = clone

    _retire(old_id, live, knowledge, retired)
    identity_entries.append(
        _identity_entry(
            old_id,
            sorted(allocation),
            "split",
            _ENTITY_KINDS[collection],
            proposal["proposal_key"],
            span_allocation=allocation,
        )
    )
    touched.add(old_id)


def _apply_merge(
    proposal: dict,
    decision: dict,
    live: Dict[str, Any],
    knowledge: dict,
    identity_entries: List[Dict[str, Any]],
    touched: Set[str],
    retired: Set[str],
    *,
    extra_relations: Sequence[dict] = (),
) -> None:
    """merge_entities（CHARTER §19.2、§21 ④、§22.2）：两号合并，身份变化只记在 IdentityDelta。

    - 决定的 `target_entity_ids` 必须恰含**两个互异的活号**，且同类
    - **较小的号存活**（`to`），较大的号退役（`from`）——不依赖决定里的列表顺序
    - **第三方**活对象/关系指向退役号（基底 ∪ 本轮）→ ``AssemblyRefused``（不自动改指，§22.2 第 2 种）
    - 合并**双方彼此之间**的关系随合并作废，由调用方在重建关系表时删除并记进
      `report.dropped_relations`（reason=`merge_internal`，§22.2 第 1 种）
    - **不写** `merged_into` 关系：关系两端必须存活，已退役的旧号不该进关系表
    """
    targets = [str(item) for item in (decision.get("target_entity_ids") or [])]
    if len(set(targets)) != 2:
        raise SchemaViolation(
            "merge_entities 决定的 target_entity_ids 必须恰含两个互异的号: %r" % (targets,),
            code="SCH_002",
        )
    located: Dict[str, Tuple[str, dict]] = {}
    for target_id in targets:
        location = _locate(live, target_id)
        if location is None:
            raise MissingReference(
                "merge_entities 目标不在 Snapshot 活对象里: %s" % target_id, code="REF_001"
            )
        located[target_id] = location
    collections = {collection for collection, _item in located.values()}
    if len(collections) != 1:
        raise AssemblyRefused(
            "merge_entities 的两个目标必须同类，实为 %s" % sorted(collections), code="SCH_002"
        )
    collection = collections.pop()
    survivor_id, retired_id = sorted(targets)
    pair = (retired_id, survivor_id)

    third_party = sorted(_non_relation_referenced_by(knowledge, retired_id))
    if third_party:
        raise AssemblyRefused(
            "merge_entities 的退役号 %s 被第三方活对象 %s 引用；act/04 未规定引用改指规则，"
            "与 split 同口径停手上报（§21 ④、§22.2）" % (retired_id, third_party),
            code="SCH_002",
        )
    outsiders = [
        relation
        for relation in _referencing_relations(knowledge, retired_id, extra_relations)
        if not _is_merge_internal(relation, pair)
    ]
    if outsiders:
        counterparts = sorted(
            {
                endpoint
                for relation in outsiders
                for endpoint in (relation.get("from_entity_id"), relation.get("to_entity_id"))
                if endpoint and endpoint != retired_id
            }
        )
        raise AssemblyRefused(
            "merge_entities 的退役号 %s 被第三方关系 %s（对端 %s）引用；act/04 未规定引用改指规则，"
            "与 split 同口径停手上报（§21 ④、§22.2）"
            % (
                retired_id,
                sorted(relation["relation_key"] for relation in outsiders),
                counterparts,
            ),
            code="SCH_002",
        )

    _retire(retired_id, live, knowledge, retired)
    identity_entries.append(
        _identity_entry(
            retired_id, [survivor_id], "merged", _ENTITY_KINDS[collection], proposal["proposal_key"]
        )
    )
    touched.add(retired_id)


def _non_relation_referenced_by(knowledge: dict, entity_id: str) -> Set[str]:
    """列出以**非关系**方式引用 `entity_id` 的活对象号（school_view / pattern 的成员表）。"""
    referencing: Set[str] = set()
    for sv in knowledge.get("school_views", []):
        if sv.get("subject_entity_id") == entity_id or entity_id in (sv.get("claim_refs") or []):
            referencing.add(sv["school_view_id"])
    for pattern in knowledge.get("patterns", []):
        if entity_id in (pattern.get("assertion_ids") or []):
            referencing.add(pattern["pattern_id"])
        if entity_id in (pattern.get("school_view_ids") or []):
            referencing.add(pattern["pattern_id"])
    return referencing


def _referencing_relations(
    knowledge: dict, entity_id: str, extra_relations: Sequence[dict] = ()
) -> List[dict]:
    """列出引用 `entity_id` 的关系，按 `relation_key` 升序去重（CHARTER §22.2 第 2 条）。

    `extra_relations` 是调用方给的「基底 ∪ 本轮已写」的关系。原来只看
    `knowledge["relations"]`，而增量轮那份列表在逐提案落地期间恒为空
    （`_template` 把它清空、本轮关系先进 `new_relations`）—— 于是基底关系根本看不见，
    “退役号被引用即 fail-closed”这道护栏实际上从未生效过。
    """
    indexed: Dict[str, dict] = {}
    for relation in list(extra_relations or []) + list(knowledge.get("relations") or []):
        if entity_id in (relation.get("from_entity_id"), relation.get("to_entity_id")):
            indexed[relation["relation_key"]] = relation
    return [indexed[key] for key in sorted(indexed)]


def _referenced_by(
    knowledge: dict, entity_id: str, extra_relations: Sequence[dict] = ()
) -> Set[str]:
    """列出引用了 `entity_id` 的活对象号与关系键（split 的引用改指未在规格里规定，须停手）。"""
    referencing = _non_relation_referenced_by(knowledge, entity_id)
    referencing.update(
        relation["relation_key"]
        for relation in _referencing_relations(knowledge, entity_id, extra_relations)
    )
    return referencing


def _is_merge_internal(relation: dict, pair: Tuple[str, str]) -> bool:
    """关系两端是否都落在**被合并的两个号**内（CHARTER §22.2 第 1 种：随合并作废）。"""
    endpoints = {relation.get("from_entity_id"), relation.get("to_entity_id")} - {None}
    return bool(endpoints) and endpoints <= set(pair)


def _apply_retire(
    target_id: Optional[str],
    live: Dict[str, Any],
    knowledge: dict,
    identity_entries: List[Dict[str, Any]],
    touched: Set[str],
    retired: Set[str],
    pruned: List[Dict[str, Any]],
    *,
    proposal_key: str,
) -> None:
    """R11 auto / R11b human：对象移除、号进 retired、IdentityDelta 一条 retired。

    `proposal_key` 必须是**触发这次退役的那条提案**的键（F5，ACT 28 contract 二）：
    写死字面量会让 IdentityDelta 的理由引用落在任何提案集之外，
    而 `gate.identity_delta_contract` 按草稿口径只认本轮提案键。
    """
    if not target_id:
        raise SchemaViolation("retire 提案缺目标号", code="SCH_002")
    location = _locate(live, target_id)
    if location is None:
        raise MissingReference("retire 目标不在 Snapshot 活对象里: %s" % target_id, code="REF_001")
    collection, _item = location
    # CHARTER §22.2 第 3 种：指向被退役断言的关系随退役作废 —— 删除并记进 report，**不停手**
    # （删掉的断言带着关系是返工的常态，停手等于返工永远跑不通；规格 §16:732 对 retired
    # 本来就是「转为孤儿并记录」）。删除与记账在关系表重建处统一做，见 apply_resolutions。
    _retire(target_id, live, knowledge, retired)
    identity_entries.append(
        _identity_entry(target_id, [], "retired", _ENTITY_KINDS[collection], proposal_key)
    )
    touched.add(target_id)


def _apply_accept_alias(
    proposal: dict, view_docs: Sequence[Dict[str, Any]], live: Dict[str, Any]
) -> Optional[dict]:
    """accept_alias：目标 aliases 追加候选名（NFC 去重、升序），候选并入目标。"""
    targets = list(proposal.get("targets") or [])
    if len(targets) != 1:
        raise SchemaViolation("accept_alias 必须恰有一个目标号", code="SCH_002")
    target_id = targets[0]
    location = _locate(live, target_id)
    if location is None:
        raise MissingReference("accept_alias 目标不在活对象里: %s" % target_id, code="REF_001")
    source_id = proposal["subject"][1] if len(proposal.get("subject") or []) > 1 else None
    candidate = _candidate_for(proposal, view_docs, source_id, ("concept_mentions", "new_concept_candidates"))
    if candidate is None:
        raise MissingReference(
            "accept_alias 找不到候选（source=%s subject=%r）" % (source_id, proposal.get("subject")),
            code="REF_001",
        )
    _collection, item = location
    surface = nfc_key(candidate.get("name") or candidate.get("surface") or "")
    aliases = set(item.get("aliases") or [])
    if surface and surface != nfc_key(item.get("name") or ""):
        aliases.add(surface)
    item["aliases"] = sorted(aliases)
    item.setdefault("provenance", [])
    if source_id not in {entry.get("source_id") for entry in item["provenance"]}:
        item["provenance"].append(
            {
                "source_id": source_id,
                "content_sha256": content_sha256({"name": surface, "aliases": []}),
                "content_status": candidate.get("content_status", "machine_extracted"),
            }
        )
    return _relation_for(
        "alias_of",
        target_id,
        None,
        {
            "source_id": source_id,
            "candidate_key": candidate.get("candidate_key"),
            "name": surface,
        },
        proposal["proposal_key"],
        mode="human",
        key_subject=[target_id, source_id, surface],
    )


# --------------------------------------------------------------------------- 对勘
def _apply_evidence(
    proposal: dict,
    choice: str,
    base_state: Dict[str, Any],
    view_docs: Sequence[Dict[str, Any]],
    live: Dict[str, Any],
) -> Optional[dict]:
    """对勘四类写入 relations（subject 为较小 source 一侧断言号；缺失侧为 null）。"""
    relation_kind = "alignment" if choice == "accept_alignment" else choice
    left, right = _collation_pair(proposal, base_state, view_docs)
    if relation_kind in ("addition", "omission"):
        if left is None or right is None:
            present, absent = (right, left) if left is None else (left, right)
        else:
            present = _smaller_source(left, right)
            absent = right if present is left else left
        subject_id = present["assertion_id"] if present else None
        object_id = None
    else:
        smaller = _smaller_source(left, right)
        subject_id = smaller["assertion_id"]
        target = right if smaller is left else left
        object_id = target["assertion_id"] if target else None
    detail: Dict[str, Any] = {}
    if relation_kind == "variant_reading":
        detail = {
            "opcodes": [
                list(opcode)
                for opcode in difflib.SequenceMatcher(
                    None,
                    nfc_key((left or {}).get("proposition") or ""),
                    nfc_key((right or {}).get("proposition") or ""),
                    autojunk=False,
                ).get_opcodes()
            ]
        }
    return _relation_for(relation_kind, subject_id, object_id, detail, proposal["proposal_key"], mode="auto")


def _collation_pair(
    proposal: dict, base_state: Dict[str, Any], view_docs: Sequence[Dict[str, Any]]
) -> Tuple[Optional[dict], Optional[dict]]:
    """定位对勘两侧。

    **配对由提案确立**：优先用 `targets` 里的两个号（基底侧优先取基座对象）；
    `targets` 不足时按 `subject` 声明的 `collation_key` 取唯一一对，不唯一即停手上报（不许猜）。
    """
    targets = [target for target in proposal.get("targets") or []]
    if len(targets) == 2:
        resolved = []
        for target in targets:
            item = base_state["assertions"].get(target)
            if item is not None:
                resolved.append(item)
                continue
            found = None
            for view in view_docs:
                for candidate in view["candidate_set"].get("assertions", []):
                    if candidate["assertion_id"] == target:
                        found = candidate
                        break
                if found is not None:
                    break
            if found is None:
                raise MissingReference("对勘目标不在基座也不在视图里: %s" % target, code="REF_001")
            resolved.append(found)
        return resolved[0], resolved[1]

    subject = proposal.get("subject") or []
    collation_key = subject[2] if len(subject) > 2 else None
    candidates = [
        item
        for view in view_docs
        for item in view["candidate_set"].get("assertions", [])
        if item.get("collation_key") == collation_key
    ]
    base_items = [
        item
        for item in base_state["assertions"].values()
        if item.get("collation_key") == collation_key
    ]
    pairs = [(left, right) for left in candidates for right in base_items]
    if len(pairs) != 1:
        raise AssemblyRefused(
            "对勘配对不唯一（subject=%r，候选 %d 条 × 基座 %d 条），须停手上报而不是猜"
            % (subject, len(candidates), len(base_items)),
            code="SCH_002",
        )
    return pairs[0]


def _smaller_source(left: Optional[dict], right: Optional[dict]) -> Optional[dict]:
    if left is None:
        return right
    if right is None:
        return left
    return left if left.get("source_id", "") <= right.get("source_id", "") else right


# --------------------------------------------------------------------------- 关系
def _relation_for(
    kind: str,
    from_entity_id: Optional[str],
    to_entity_id: Optional[str],
    detail: Optional[dict],
    proposal_key: str,
    *,
    mode: str,
    key_subject: Optional[Sequence[Any]] = None,
) -> dict:
    """构造一条关系。

    `relation_key` 只由**稳定声明**构成（默认 `[from, to]`，必要时加 source_id 等），
    **不得**包含 `detail` 里的差异细节：否则 difflib 录的 opcodes 会反推改变键，
    违反 §11「difflib 只记录、不裁定」。
    """
    subject = list(key_subject) if key_subject is not None else [from_entity_id, to_entity_id]
    return {
        "relation_key": make_key(kind, subject),
        "from_entity_id": from_entity_id,
        "to_entity_id": to_entity_id,
        "relation_kind": kind,
        "detail": detail or {},
        "resolution": {"mode": mode, "proposal_key": proposal_key},
    }


def _relation_touches(relation: dict, ids_: Set[str]) -> bool:
    return bool(
        ids_ & {relation.get("from_entity_id"), relation.get("to_entity_id")} - {None}
    )


def _attached_relations(
    base_state: Dict[str, Any],
    view_docs: Sequence[Dict[str, Any]],
    knowledge: dict,
    attach_choices: Dict[Tuple[str, str], str],
) -> List[dict]:
    """attach 关系：仅限目标在**基底已存在**的并入（创世与 R02 不写 attached）。"""
    relations = []
    for view in view_docs:
        for candidate in view["candidate_set"].get("patterns", []):
            pattern_id = candidate.get("pattern_id")
            if not pattern_id or pattern_id not in base_state["patterns"]:
                continue
            proposal_key = attach_choices.get((view["source_id"], pattern_id))
            if not proposal_key:
                continue
            relations.append(
                _relation_for(
                    "attached",
                    pattern_id,
                    None,
                    {
                        "source_id": view["source_id"],
                        "candidate_key": candidate.get("candidate_key") or pattern_id,
                    },
                    proposal_key,
                    mode="auto",
                    key_subject=[pattern_id, view["source_id"]],
                )
            )
    return relations


def _not_comparable(view_docs: Sequence[Dict[str, Any]]) -> List[dict]:
    rows: List[dict] = []
    for view in view_docs:
        units = matcher.units_of_view(view["candidate_set"], view["reviewed_edition"])
        for unit in matcher.unpairable_units(units):
            rows.append(dict(unit, source_id=view["source_id"]))
    rows.sort(
        key=lambda row: (row["source_id"], row.get("entity_ref") or "", row.get("reason") or "")
    )
    return rows


# --------------------------------------------------------------------------- 索引/登记
def _require_trace(
    proposal_index: Dict[str, Any], source_id: str, key: str, collation_key: Optional[str]
) -> None:
    """D-05：任何并入都必须有一条提案留痕，禁止静默并入。"""
    for proposal in proposal_index["ordered"]:
        subject = proposal.get("subject") or []
        if key in subject or key in (proposal.get("targets") or []):
            return
        if (
            collation_key
            and len(subject) > 2
            and subject[0] == "collation"
            and subject[1] == source_id
            and subject[2] == collation_key
        ):
            return
    raise AssemblyRefused(
        "禁止静默并入：候选 %s（source=%s）没有对应提案留痕" % (key, source_id), code="SCH_002"
    )


def _effective_choice(
    proposal_index: Dict[str, Any], key: str, source_id: str, candidate: dict
) -> Tuple[Optional[str], Optional[str]]:
    """候选的最终裁定（决定优先于自动选择）；可空。"""
    for proposal in proposal_index["ordered"]:
        subject = proposal.get("subject") or []
        if key not in subject and key not in (proposal.get("targets") or []):
            continue
        decision = proposal_index["by_decision"].get(proposal["proposal_key"])
        if decision is not None:
            return decision["choice"], proposal["proposal_key"]
        if proposal.get("resolution") == "auto":
            return proposal.get("auto_choice"), proposal["proposal_key"]
    return None, None


def _index_proposals(
    proposals: Sequence[dict], decisions: Sequence[dict], view_docs: Sequence[Dict[str, Any]]
) -> Dict[str, Any]:
    """提案/决定索引；未决、重复决定、悬空决定在此 fail-closed。"""
    by_key: Dict[str, dict] = {}
    for proposal in proposals:
        key = proposal.get("proposal_key")
        if not key:
            raise SchemaViolation("提案缺 proposal_key", code="SCH_001")
        if key in by_key:
            raise DuplicateIdentifier("提案 proposal_key 重复: %s" % key, code="ID_002")
        by_key[key] = proposal

    by_decision: Dict[str, dict] = {}
    for decision in decisions:
        key = decision.get("proposal_key")
        if key not in by_key:
            raise MissingReference("决定引用了不存在的 proposal_key: %s" % key, code="REF_001")
        if key in by_decision:
            raise DuplicateIdentifier("同一提案出现多条决定: %s" % key, code="ID_002")
        by_decision[key] = decision

    for proposal in proposals:
        if proposal.get("resolution") in NEEDS_DECISION and (
            proposal["proposal_key"] not in by_decision
        ):
            raise AssemblyRefused(
                "存在未决提案（resolution=%s）：%s 尚无人工决定"
                % (proposal.get("resolution"), proposal["proposal_key"]),
                code="SCH_001",
            )

    attach_choices: Dict[Tuple[str, str], str] = {}
    targets_of: Dict[Tuple[str, str], List[str]] = {}
    for proposal in proposals:
        subject = proposal.get("subject") or []
        if len(subject) < 3:
            continue
        decision = by_decision.get(proposal["proposal_key"])
        choice = decision["choice"] if decision else (
            proposal.get("auto_choice") if proposal.get("resolution") == "auto" else None
        )
        if subject[0] == "pattern":
            # 创世与 R02 不写 attached（act/04.yaml:37）
            if choice and str(choice).startswith("attach:") and proposal.get("rule_id") != "R02":
                attach_choices[(subject[1], subject[2])] = proposal["proposal_key"]
            targets_of[(subject[1], subject[2])] = list(proposal.get("targets") or [])

    return {
        "by_key": by_key,
        "by_decision": by_decision,
        "ordered": sorted(proposals, key=lambda item: item["proposal_key"]),
        "attach_choices": attach_choices,
        "targets_of": targets_of,
    }


def _id_allocation(base: dict, knowledge: dict, technique_id: str, range_key: str) -> Dict[str, int]:
    """§8.1：`id_allocation[pat_<tech>]` 取「活对象与补发」的最大号（不得低于基座口径）。

    ⚠ 冻结校验器 `model.validate_snapshot_knowledge` 同时要求
    `id_allocation == max(活对象 ∪ 补发)` **且** `>= max(活对象 ∪ 已退役 ∪ 补发)`；
    两者在「命名空间最大号的那个 pattern 被退役」时不可同时成立。
    本函数按前一条（活对象与补发）取值；后者靠调用方不把最大号退役来满足，
    属 model.py 冻结口径下的已知约束（见 H 波回报「新发现」节）。
    """
    numbers = []
    for item in knowledge.get("patterns", []):
        number = _number_of(item.get("pattern_id"), technique_id)
        if number is not None:
            numbers.append(number)
    for pattern_id in knowledge.get("allocated_pattern_ids", []):
        number = _number_of(pattern_id, technique_id)
        if number is not None:
            numbers.append(number)
    if not numbers:
        return copy.deepcopy(base.get("id_allocation") or {})
    return {range_key: max(numbers)}


def _admit_new_without_object(
    proposal_index: Dict[str, Any], materialized: Dict[str, Set[str]]
) -> List[dict]:
    """`admit_new` 却没产出对象的提案（如无正式 `co_` 号的 concept 候选）：如实报告。"""
    rows = []
    for proposal in proposal_index["ordered"]:
        if proposal.get("kind") != "merge":
            continue
        decision = proposal_index["by_decision"].get(proposal["proposal_key"])
        choice = decision["choice"] if decision else (
            proposal.get("auto_choice") if proposal.get("resolution") == "auto" else None
        )
        if choice != "admit_new":
            continue
        subject = list(proposal.get("subject") or [])
        if len(subject) < 3:
            continue
        kind, source_id, key = subject[0], subject[1], subject[-1]
        if key in materialized.get(kind, set()):
            continue
        rows.append(
            {
                "proposal_key": proposal["proposal_key"],
                "rule_id": proposal.get("rule_id"),
                "kind": kind,
                "source_id": source_id,
                "subject_key": key,
                "reason": "candidate_not_materialized",
            }
        )
    rows.sort(key=lambda row: (row["proposal_key"], row["subject_key"]))
    return rows


def _resolution_log(proposal_index: Dict[str, Any]) -> List[dict]:
    """裁定日志：`[{proposal_key, mode, choice}]` 按 proposal_key 升序。"""
    rows = []
    for proposal in proposal_index["ordered"]:
        decision = proposal_index["by_decision"].get(proposal["proposal_key"])
        if decision is not None:
            rows.append(
                {
                    "proposal_key": proposal["proposal_key"],
                    "mode": "human",
                    "choice": decision["choice"],
                }
            )
        elif proposal.get("resolution") == "auto":
            rows.append(
                {
                    "proposal_key": proposal["proposal_key"],
                    "mode": "auto",
                    "choice": proposal.get("auto_choice"),
                }
            )
    rows.sort(key=lambda row: row["proposal_key"])
    return rows


def _locate(live: Dict[str, Any], entity_id: str) -> Optional[Tuple[str, dict]]:
    for collection in _COLLECTIONS:
        item = live[collection].get(entity_id)
        if item is not None:
            return collection, item
    return None


def _next_assertion_id(live: Dict[str, Any], technique_id: str) -> str:
    numbers = [
        number
        for number in (
            _as_number_of(entity_id, technique_id) for entity_id in live["assertions"]
        )
        if number is not None
    ]
    return "as_%s_%06d" % (technique_id, (max(numbers) + 1) if numbers else 1)


def _retire(entity_id: str, live: Dict[str, Any], knowledge: dict, retired: Set[str]) -> None:
    """退役：从活对象集合里移除，并把号记入本轮 retired 集合。"""
    for collection in _COLLECTIONS:
        live[collection].pop(entity_id, None)
    retired.add(entity_id)


def _remove_retired(knowledge: dict, retired: Set[str]) -> None:
    if not retired:
        return
    for collection in _COLLECTIONS:
        knowledge[collection] = [
            item for item in knowledge[collection] if item[_ID_KEYS[collection]] not in retired
        ]


def _identity_entry(
    from_entity_id: str,
    to_entity_ids: Sequence[str],
    change_type: str,
    entity_kind: str,
    proposal_key: str,
    *,
    span_allocation: Optional[Dict[str, Any]] = None,
) -> dict:
    entry = {
        "from_entity_id": from_entity_id,
        "to_entity_ids": list(to_entity_ids),
        "change_type": change_type,
        "entity_kind": entity_kind,
        "reason_ref": {"kind": "proposal", "proposal_key": proposal_key},
    }
    if span_allocation is not None:
        entry["span_allocation"] = span_allocation
    return entry


def _restore_untouched(
    base: dict,
    knowledge: dict,
    base_state: Dict[str, Any],
    affected_set: Optional[Set[str]],
    touched: Set[str],
) -> None:
    """`affected` 集合外（或本轮未触及）的基底对象，从基座**原样拷贝**（不重新构造）。"""
    if affected_set is None:
        return
    for collection in _COLLECTIONS:
        verbatim = {
            entity_id: copy.deepcopy(item)
            for entity_id, item in base_state[collection].items()
            if entity_id not in affected_set or entity_id not in touched
        }
        for entity_id, item in sorted(verbatim.items()):
            knowledge[collection] = [
                row for row in knowledge[collection] if row[_ID_KEYS[collection]] != entity_id
            ]
            knowledge[collection].append(item)


def _candidate_for(
    proposal: dict,
    view_docs: Sequence[Dict[str, Any]],
    source_id: Optional[str],
    extra_collections: Sequence[str] = (),
) -> Optional[dict]:
    """按提案 subject / targets 在视图里定位候选（不做任何相似度判断）。"""
    keys = list(proposal.get("targets") or [])
    if proposal.get("subject"):
        keys.append(proposal["subject"][-1])
    for view in view_docs:
        if source_id and view["source_id"] != source_id:
            continue
        for candidate in view["candidate_set"].get("patterns", []):
            for key in (candidate.get("pattern_id"), candidate.get("candidate_key")):
                if key and key in keys:
                    return candidate
        for collection in extra_collections:
            for candidate in view["candidate_set"].get(collection, []):
                for key in (candidate.get("concept_ref"), candidate.get("surface"), candidate.get("candidate_key")):
                    if key and key in keys:
                        return candidate
    return None


def _created_ids(base_state: Dict[str, Any], knowledge: dict) -> List[str]:
    created: Set[str] = set()
    for collection in _COLLECTIONS:
        for item in knowledge.get(collection, []):
            entity_id = item[_ID_KEYS[collection]]
            if entity_id not in base_state[collection]:
                created.add(entity_id)
    return sorted(created)


def _rebuilt_ids(
    base_state: Dict[str, Any], touched: Set[str], affected_set: Optional[Set[str]]
) -> List[str]:
    if affected_set is None:
        return sorted(base_state["alive"] & touched)
    return sorted(affected_set & touched)


def _sort_knowledge(knowledge: dict) -> None:
    knowledge["editions"].sort(key=lambda item: item["source_id"])
    knowledge["concepts"].sort(key=lambda item: item["concept_id"])
    knowledge["patterns"].sort(key=lambda item: item["pattern_id"])
    knowledge["assertions"].sort(key=lambda item: item["assertion_id"])
    knowledge["school_views"].sort(key=lambda item: item["school_view_id"])
    knowledge["conflict_groups"].sort(key=lambda item: item["conflict_group_id"])
    knowledge["relations"].sort(key=lambda item: item["relation_key"])
    knowledge["retired_entity_ids"] = sorted(set(knowledge.get("retired_entity_ids") or []))
    knowledge["allocated_pattern_ids"] = sorted(set(knowledge.get("allocated_pattern_ids") or []))
