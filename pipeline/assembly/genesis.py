"""M7 创世汇编纯函数实现（spec §15, §6.2）。

本模块只走空基底自动汇编分支，实现 propose_genesis 与 assemble_genesis。
"""

import copy
import re

from pipeline.ledger import ids
from .canonical import (
    canonical_json,
    content_sha256,
    make_key,
    nfc_key,
    sha256_hex,
    work_key,
)
from .errors import AssemblyRefused
from .model import (
    declared_collation_units,
    empty_snapshot_knowledge,
    validate_candidate_set,
    validate_reviewed_edition,
    validate_snapshot_knowledge,
)


def propose_genesis(candidate_set: dict, reviewed_edition: dict) -> dict:
    """对空基底与单 Edition 视图生成自动汇编提案集合（纯函数）。"""
    if "doc" in candidate_set:
        cset_doc = candidate_set["doc"]
        source_id = candidate_set.get("source_id") or cset_doc["source_id"]
    else:
        v = validate_candidate_set(candidate_set)
        cset_doc = v["doc"]
        source_id = v["source_id"]

    if "approved_index" in reviewed_edition:
        approved_index = reviewed_edition["approved_index"]
    else:
        v = validate_reviewed_edition(reviewed_edition)
        approved_index = v["approved_index"]

    approved_entities = set(approved_index.keys())

    proposals = []
    resolved_subjects = {}

    # R02 / R03e: Pattern 提案
    for p in cset_doc.get("patterns", []):
        pat_id = p.get("pattern_id")
        cand_key = p.get("candidate_key")

        if pat_id is not None:
            if pat_id in approved_entities:
                subject = ["pattern", source_id, pat_id]
                kind = "merge"
                rule_id = "R02"
                basis_sha256 = content_sha256({
                    "candidate": {
                        "name": nfc_key(p["name"]),
                        "recognition_rule_status": p.get("recognition_rule_status", "not_captured"),
                    },
                    "target": None,
                })
                proposal_key = make_key(kind, subject)
                proposals.append({
                    "proposal_key": proposal_key,
                    "kind": kind,
                    "rule_id": rule_id,
                    "resolution": "auto",
                    "subject": subject,
                    "targets": [],
                    "options": ["admit_new"],
                    "auto_choice": "admit_new",
                    "decision_type": None,
                    "basis_sha256": basis_sha256,
                    "depends_on": [],
                })
                resolved_subjects[pat_id] = pat_id
        elif cand_key is not None:
            subject = ["pattern", source_id, cand_key]
            kind = "merge"
            rule_id = "R03e"
            basis_sha256 = content_sha256({
                "candidate": {
                    "name": nfc_key(p["name"]),
                    "recognition_rule_status": p.get("recognition_rule_status", "not_captured"),
                },
                "target": None,
            })
            proposal_key = make_key(kind, subject)
            proposals.append({
                "proposal_key": proposal_key,
                "kind": kind,
                "rule_id": rule_id,
                "resolution": "auto",
                "subject": subject,
                "targets": [],
                "options": ["admit_new"],
                "auto_choice": "admit_new",
                "decision_type": None,
                "basis_sha256": basis_sha256,
                "depends_on": [],
            })
            resolved_subjects[cand_key] = cand_key

    # R04: Concept 提案（已绑定 concept_ref）
    seen_concept_refs = set()
    for cm in cset_doc.get("concept_mentions", []):
        ref = cm.get("concept_ref")
        if ref and ref not in seen_concept_refs:
            seen_concept_refs.add(ref)
            subject = ["concept", source_id, ref]
            kind = "merge"
            rule_id = "R04"
            basis_sha256 = content_sha256({
                "candidate": {"concept_ref": ref},
                "target": None,
            })
            proposal_key = make_key(kind, subject)
            proposals.append({
                "proposal_key": proposal_key,
                "kind": kind,
                "rule_id": rule_id,
                "resolution": "auto",
                "subject": subject,
                "targets": [],
                "options": ["admit_new"],
                "auto_choice": "admit_new",
                "decision_type": None,
                "basis_sha256": basis_sha256,
                "depends_on": [],
            })

    proposals.sort(key=lambda prop: prop["proposal_key"])

    excluded_unbound = sorted(
        copy.deepcopy(cset_doc.get("new_concept_candidates", [])),
        key=lambda ncc: ncc["surface"],
    )

    return {
        "round": 1,
        "proposals": proposals,
        "excluded_unbound": excluded_unbound,
        "resolved_subjects": resolved_subjects,
    }


def assemble_genesis(
    candidate_set: dict,
    reviewed_edition: dict,
    proposals: list,
    *,
    id_range: dict,
    id_factory=None,
    reviewed_edition_package_revision_id: str | None = None,
    reviewed_edition_revision_id: str | None = None,
    stage_package_id: str | None = None,
) -> dict:
    """根据提案和配置号段执行创世汇编，产出 CanonicalKnowledgeSnapshot knowledge 及报告。"""
    # 校验配置 id_range（第 70 条）
    if not isinstance(id_range, dict) or "pattern" not in id_range:
        raise AssemblyRefused(
            "id_range 必须为字典且包含 'pattern' 键: %r" % (id_range,),
            code="SCH_002",
        )
    rng = id_range["pattern"]
    if (
        not isinstance(rng, (list, tuple))
        or len(rng) != 2
        or not isinstance(rng[0], int)
        or not isinstance(rng[1], int)
        or rng[0] < 0
        or rng[1] < 0
        or rng[0] > rng[1]
    ):
        raise AssemblyRefused(
            "id_range['pattern'] 必须为 [start, end] 两个非负整数且 start <= end: %r" % (rng,),
            code="SCH_002",
        )
    start, end = rng[0], rng[1]

    if "doc" in candidate_set:
        cset_doc = candidate_set["doc"]
        technique_id = candidate_set.get("technique_id") or cset_doc["technique_id"]
        source_id = candidate_set.get("source_id") or cset_doc["source_id"]
        wk = candidate_set.get("work_key") or work_key(source_id)
    else:
        v = validate_candidate_set(candidate_set)
        cset_doc = v["doc"]
        technique_id = v["technique_id"]
        source_id = v["source_id"]
        wk = v["work_key"]

    if "doc" in reviewed_edition:
        reviewed_doc = reviewed_edition["doc"]
        approved_index = reviewed_edition.get("approved_index") or {
            item["entity_id"]: item for item in reviewed_doc.get("approved", [])
        }
    else:
        v = validate_reviewed_edition(reviewed_edition)
        reviewed_doc = v["doc"]
        approved_index = v["approved_index"]

    approved_entities = set(approved_index.keys())

    # 收集候选 pattern 既有合法 pat_ 号
    pat_prefix = "pat_%s_" % technique_id
    used_numbers = set()
    for p in cset_doc.get("patterns", []):
        pid = p.get("pattern_id")
        if pid and pid.startswith(pat_prefix):
            num_part = pid[len(pat_prefix):]
            if re.match(r"^[0-9]{6}$", num_part):
                used_numbers.add(int(num_part))

    # 防御分支（pattern_id 为 null 且带 candidate_key）确定性发号
    defensive_candidates = [
        p for p in cset_doc.get("patterns", [])
        if p.get("pattern_id") is None and p.get("candidate_key")
    ]
    defensive_candidates.sort(key=lambda p: (source_id, p["candidate_key"]))

    allocated_pattern_ids = []
    resolved_defensive = {}
    current_alloc_num = start

    for p in defensive_candidates:
        while current_alloc_num in used_numbers and current_alloc_num <= end:
            current_alloc_num += 1
        if current_alloc_num > end:
            raise AssemblyRefused(
                "号段不足，无法为候选 pattern 补发号: range=[%d, %d]" % (start, end),
                code="SCH_002",
            )
        allocated_id = "pat_%s_%06d" % (technique_id, current_alloc_num)
        used_numbers.add(current_alloc_num)
        allocated_pattern_ids.append(allocated_id)
        resolved_defensive[p["candidate_key"]] = allocated_id
        current_alloc_num += 1

    allocated_pattern_ids.sort()

    # 初始化 Snapshot knowledge（存储层改键为 pat_<technique>，第 70 条）
    storage_id_range = {"pat_%s" % technique_id: [start, end]}
    knowledge = empty_snapshot_knowledge(technique_id, storage_id_range)
    knowledge["allocated_pattern_ids"] = list(allocated_pattern_ids)

    max_pat_number = max(used_numbers) if used_numbers else 0
    if max_pat_number > 0 or allocated_pattern_ids:
        knowledge["id_allocation"] = {"pat_%s" % technique_id: max_pat_number}
    else:
        knowledge["id_allocation"] = {}

    # 1. editions
    # D1：取 evidence_level 自 candidate_set（禁止硬编码、禁止默认值兜底）
    if "evidence_level" not in cset_doc:
        raise AssemblyRefused(
            "candidate_set 缺必填字段 evidence_level",
            code="SCH_001",
        )
    ev_level = cset_doc["evidence_level"]

    # D1：corpus_spans_revision_id 来自本 edition 下各 evidence_links
    # 全部一致 → 取该值；全部为 None → 置 None；出现两个及以上不同值 → 抛错停手
    link_csrids = [
        link.get("corpus_spans_revision_id")
        for link in reviewed_doc.get("evidence_links", [])
    ]
    distinct_csrids = set(r for r in link_csrids if r is not None)
    if len(distinct_csrids) > 1:
        raise AssemblyRefused(
            "evidence_links 中出现多个不同的 corpus_spans_revision_id，须停手上报: %s"
            % sorted(distinct_csrids),
            code="SCH_002",
        )
    corpus_spans_revision_id = distinct_csrids.pop() if distinct_csrids else None

    pkg_rev_id = (
        reviewed_edition_package_revision_id
        or reviewed_edition.get("reviewed_edition_package_revision_id")
        or reviewed_doc.get("reviewed_edition_package_revision_id")
        or "rev_00000000000000000000000000000000"
    )
    ed_rev_id = (
        reviewed_edition_revision_id
        or reviewed_edition.get("reviewed_edition_revision_id")
        or reviewed_doc.get("reviewed_edition_revision_id")
        or "rev_00000000000000000000000000000001"
    )
    stg_pkg_id = (
        stage_package_id
        or reviewed_edition.get("stage_package_id")
        or reviewed_doc.get("stage_package_id")
        or "pkg_m6_00000000000000000000000000000000"
    )
    knowledge["editions"] = [
        {
            "source_id": source_id,
            "work_key": wk,
            "reviewed_edition_package_revision_id": pkg_rev_id,
            "reviewed_edition_revision_id": ed_rev_id,
            "stage_package_id": stg_pkg_id,
            "edition_part_artifact_ids": [cset_doc["edition_part_artifact_id"]],
            "edition_complete": False,
            "evidence_level": ev_level,
            "corpus_spans_revision_id": corpus_spans_revision_id,
            # CHARTER §25.5：创世时也要记下**本版次声明过哪些可比单元**
            # （基底一侧的「声明」只从这个字段读，不再从断言推）
            "collation_units": declared_collation_units(cset_doc),
        }
    ]

    # 2. concepts
    mentions_by_ref = {}
    for cm in cset_doc.get("concept_mentions", []):
        ref = cm.get("concept_ref")
        if ref:
            mentions_by_ref.setdefault(ref, []).append(cm)

    concepts = []
    for ref, m_list in mentions_by_ref.items():
        surfaces = sorted(set(nfc_key(m["surface"]) for m in m_list))
        cname = surfaces[0]
        aliases = surfaces[1:]
        cstatus = approved_index.get(ref, {}).get("content_status", m_list[0]["content_status"])
        provenance = [
            {
                "source_id": source_id,
                "content_sha256": content_sha256({"name": cname, "aliases": aliases}),
                "content_status": cstatus,
            }
        ]
        concepts.append({
            "concept_id": ref,
            "name": cname,
            "aliases": aliases,
            "provenance": provenance,
        })
    concepts.sort(key=lambda c: c["concept_id"])
    knowledge["concepts"] = concepts

    # 3. patterns
    patterns = []
    for p in cset_doc.get("patterns", []):
        pid = p.get("pattern_id")
        ck = p.get("candidate_key")
        pat_id = None
        cstatus = "machine_extracted"
        if pid and pid in approved_entities:
            pat_id = pid
            cstatus = approved_index[pid]["content_status"]
        elif ck:
            pat_id = resolved_defensive.get(ck)
            if ck in approved_index:
                cstatus = approved_index[ck]["content_status"]
            else:
                cstatus = p.get("content_status", "machine_extracted")

        if pat_id is None:
            continue

        cand_assertion_ids = p.get("assertion_ids", [])
        approved_aids = sorted(aid for aid in cand_assertion_ids if aid in approved_entities)

        # school_views where subject_entity_id == pat_id
        sv_ids = []
        for sv in cset_doc.get("school_views", []):
            if sv["school_view_id"] in approved_entities:
                sub_entity = sv.get("subject_entity_id")
                if sub_entity == pat_id or sub_entity == pid or (ck and sub_entity == ck):
                    sv_ids.append(sv["school_view_id"])
        sv_ids.sort()

        provenance = [
            {
                "source_id": source_id,
                "content_sha256": content_sha256(p),
                "content_status": cstatus,
            }
        ]
        patterns.append({
            "pattern_id": pat_id,
            "concept_id": None,
            "name": p["name"],
            "aliases": [],
            "rules": [],
            "assertion_ids": approved_aids,
            "school_view_ids": sv_ids,
            "recognition_rule_status": "not_captured",
            "provenance": provenance,
        })
    patterns.sort(key=lambda pt: pt["pattern_id"])
    knowledge["patterns"] = patterns

    # 4. assertions
    pattern_assertion_map = {}
    for pat in knowledge["patterns"]:
        for aid in pat["assertion_ids"]:
            pattern_assertion_map.setdefault(aid, []).append(pat["pattern_id"])
    for aid in pattern_assertion_map:
        pattern_assertion_map[aid].sort()

    school_view_map = {}
    for sv in cset_doc.get("school_views", []):
        sv_id = sv["school_view_id"]
        if sv_id in approved_entities:
            sub = sv.get("subject_entity_id")
            if sub:
                school_view_map.setdefault(sub, set()).add(sv_id)
            for claim in sv.get("claim_refs", []):
                school_view_map.setdefault(claim, set()).add(sv_id)

    links_by_entity = {}
    for link in reviewed_doc.get("evidence_links", []):
        links_by_entity.setdefault(link["entity_id"], []).append(link)

    assertions = []
    for a in cset_doc.get("assertions", []):
        aid = a["assertion_id"]
        if aid not in approved_entities:
            continue

        prop_nfc = nfc_key(a["proposition"])
        text_hash = sha256_hex(prop_nfc.encode("utf-8"))

        # D2（ACT impl-07/11）：两路来源都存在时，同一 source_span_id 上区间必须逐字段相等
        # 严格执行 I-11：第 106 条 D1 已删除的两条静默分支不得复活
        if aid in links_by_entity:
            links_for_aid = links_by_entity[aid]
            # 若 M4 候选也有证据，逐条比对同一 source_span_id 的偏移
            m4_ev_by_span = {ev["source_span_id"]: ev for ev in a.get("evidence", [])}
            for link in links_for_aid:
                span_id = link["source_span_id"]
                if span_id in m4_ev_by_span:
                    m4_ev = m4_ev_by_span[span_id]
                    if (link["start_offset"] != m4_ev["start_offset"]
                            or link["end_offset"] != m4_ev["end_offset"]):
                        raise AssemblyRefused(
                            "M6 链与 M4 候选在 source_span_id=%r 上的偏移不一致，"
                            "M6 链: start_offset=%r end_offset=%r，"
                            "M4 候选: start_offset=%r end_offset=%r。"
                            "请确认 I-11 修复是否覆盖所有路径。"
                            % (
                                span_id,
                                link["start_offset"], link["end_offset"],
                                m4_ev["start_offset"], m4_ev["end_offset"],
                            ),
                            code="SCH_002",
                        )
            ev_list = [
                {
                    "source_span_id": l["source_span_id"],
                    "start_offset": l["start_offset"],
                    "end_offset": l["end_offset"],
                    "quote_sha256": l["quote_sha256"],
                }
                for l in links_for_aid
            ]
        else:
            ev_list = [
                {
                    "source_span_id": ev["source_span_id"],
                    "start_offset": ev["start_offset"],
                    "end_offset": ev["end_offset"],
                    "quote_sha256": ev["quote_sha256"],
                }
                for ev in a.get("evidence", [])
            ]
        ev_list.sort(key=lambda x: (x["source_span_id"], x["start_offset"], x["end_offset"]))
        source_span_ids = sorted(list(set(ev["source_span_id"] for ev in ev_list)))

        matched_pats = pattern_assertion_map.get(aid, [])
        if len(matched_pats) == 1:
            sub_entity_id = matched_pats[0]
        elif len(matched_pats) > 1:
            sub_entity_id = min(matched_pats)
        else:
            sub_entity_id = None

        sv_ids = sorted(list(school_view_map.get(aid, set())))

        assertions.append({
            "assertion_id": aid,
            "subject_entity_id": sub_entity_id,
            "source_id": source_id,
            "proposition": prop_nfc,
            "collation_key": a.get("collation_key"),
            "text_sha256": text_hash,
            "source_span_ids": source_span_ids,
            "evidence": ev_list,
            "school_view_ids": sv_ids,
            "content_status": approved_index[aid]["content_status"],
        })
    assertions.sort(key=lambda asrt: asrt["assertion_id"])
    knowledge["assertions"] = assertions

    # 5. school_views
    school_views = []
    for sv in cset_doc.get("school_views", []):
        sv_id = sv["school_view_id"]
        if sv_id not in approved_entities:
            continue

        sub = sv.get("subject_entity_id")
        if sub in resolved_defensive:
            sub = resolved_defensive[sub]

        claim_refs = sorted(list(set(sv.get("claim_refs", []))))
        cg_id = sv.get("conflict_group_id")

        school_views.append({
            "school_view_id": sv_id,
            "school_id": sv["school_id"],
            "subject_entity_id": sub,
            "conflict_group_id": cg_id,
            "source_conflict_group_id": cg_id,
            "claim_refs": claim_refs,
            "changes_current_judgment": sv["changes_current_judgment"],
            "content_status": approved_index[sv_id]["content_status"],
        })
    school_views.sort(key=lambda s: s["school_view_id"])
    knowledge["school_views"] = school_views

    # 6. conflict_groups
    cgs_by_id = {}
    for sv in knowledge["school_views"]:
        cg_id = sv.get("conflict_group_id")
        if cg_id:
            cgs_by_id.setdefault(cg_id, []).append(sv)

    conflict_groups = []
    for cg_id, sv_list in cgs_by_id.items():
        m_ids = sorted(s["school_view_id"] for s in sv_list)
        first_layer = any(s["changes_current_judgment"] for s in sv_list)
        conflict_groups.append({
            "conflict_group_id": cg_id,
            "member_school_view_ids": m_ids,
            "first_layer_display": first_layer,
            "resolutions": [],
        })
    conflict_groups.sort(key=lambda cg: cg["conflict_group_id"])
    knowledge["conflict_groups"] = conflict_groups

    # 7. relations & retired
    knowledge["relations"] = []
    knowledge["retired_entity_ids"] = []

    # 自检通过
    validate_snapshot_knowledge(knowledge)

    k_bytes = canonical_json(knowledge)
    k_sha = sha256_hex(k_bytes)
    canon_hash = sha256_hex(
        canonical_json({
            "concepts": knowledge["concepts"],
            "patterns": knowledge["patterns"],
            "assertions": knowledge["assertions"],
            "school_views": knowledge["school_views"],
            "conflict_groups": knowledge["conflict_groups"],
        })
    )

    excluded_unbound = sorted(
        copy.deepcopy(cset_doc.get("new_concept_candidates", [])),
        key=lambda ncc: ncc["surface"],
    )

    report = {
        "proposals_count": len(proposals),
        "proposals_auto": len(proposals),
        "excluded_unbound": excluded_unbound,
        "editions": len(knowledge["editions"]),
        "concepts": len(knowledge["concepts"]),
        "patterns": len(knowledge["patterns"]),
        "assertions": len(knowledge["assertions"]),
        "school_views": len(knowledge["school_views"]),
        "conflict_groups": len(knowledge["conflict_groups"]),
        "allocated_pattern_ids": list(knowledge["allocated_pattern_ids"]),
    }

    return {
        "knowledge": knowledge,
        "knowledge_bytes": k_bytes,
        "knowledge_sha256": k_sha,
        "canonical_hash": canon_hash,
        "report": report,
    }
