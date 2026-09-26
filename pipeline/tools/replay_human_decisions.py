"""Human decisions replayer for M4 rulings and M6 decisions.

从旧账本只读提取历史人工裁决与决定，按对位规则严格校验，并通过公开 API 回放至新账本。
严格纪律：
- 只读旧账本经 LedgerPort / 服务公开方法（不触达私有存储与内部对象，无 SQL）；
- 对位规则任一不满足即停手抛出 ReplayMismatchError，不造决定；
- 回放只走公开入口（record_category_ruling / record_decision）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from pipeline.knowledge_extraction import CANDIDATE_SCHEMA_VERSION
from pipeline.knowledge_extraction.step import record_category_ruling
from pipeline.ledger.service import LedgerReader
from pipeline.review.step import record_decision


class ReplayMismatchError(Exception):
    """回放对位规则校验失败，不满足要求，立即停手。"""


def _read_json_object(reader: Any, revision_id: str) -> Any:
    """经公开端口读取某修订封存的 JSON 文档。"""
    rev_row = reader.get_revision(revision_id)
    if rev_row is None:
        raise ReplayMismatchError(f"修订不存在: {revision_id}")
    raw_bytes = reader.read_object(rev_row["sha256"])
    return json.loads(raw_bytes.decode("utf-8"))


# ---------------------------------------------------------------------------
# M4 对位与回放
# ---------------------------------------------------------------------------

def verify_m4_disputes(new_disputes: list[dict], old_disputes: list[dict]) -> None:
    """比对 M4 分歧队列：数量、ID 集合、每条的两路候选内容必须完全相等。"""
    if len(new_disputes) != len(old_disputes):
        raise ReplayMismatchError(
            f"M4 分歧数量不等: 新 {len(new_disputes)} != 旧 {len(old_disputes)}"
        )

    new_ids = {d["dispute_id"] for d in new_disputes}
    old_ids = {d["dispute_id"] for d in old_disputes}
    if new_ids != old_ids:
        raise ReplayMismatchError(
            f"M4 分歧 ID 集合不等: 新 {sorted(new_ids)} != 旧 {sorted(old_ids)}"
        )

    new_by_id = {d["dispute_id"]: d for d in new_disputes}
    for old_d in old_disputes:
        did = old_d["dispute_id"]
        new_d = new_by_id[did]
        # 逐项对比两路候选内容 a 与 b
        if new_d.get("a") != old_d.get("a") or new_d.get("b") != old_d.get("b"):
            raise ReplayMismatchError(
                f"M4 候选内容不等: 分歧 {did} 两路候选内容 (a/b) 与旧账本不一致"
            )


def load_m4_rulings_from_ledger(
    reader: Any, step_run_id: str | None = None
) -> tuple[list[dict], dict[str, dict]]:
    """从旧账本中读取 M4 分歧队列及对应的类别裁决事件。

    :return: (old_disputes, old_rulings_by_dispute_id)
    """
    human_events = reader.list_human_events(step_run_id)
    m4_events = []
    for ev in human_events:
        rev_id = ev["event_revision_id"]
        doc = _read_json_object(reader, rev_id)
        if doc.get("event_kind") == "category_ruling" or "dispute_id" in doc:
            doc["_event_revision_id"] = rev_id
            m4_events.append(doc)

    if not m4_events:
        raise ReplayMismatchError("旧账本中未找到 M4 人工类别裁决事件")

    # 从第一条裁决的 seen.dispute_queue_revision_id 取得当时的分歧队列
    first_seen = m4_events[0].get("seen") or {}
    dq_rev_id = first_seen.get("dispute_queue_revision_id")
    if not dq_rev_id:
        # 尝试通过 step_run 查找 dispute_queue
        target_srun = m4_events[0].get("step_run_id")
        revisions = reader.list_step_run_revisions(
            target_srun, artifact_type="dispute_queue"
        )
        if revisions:
            dq_rev_id = revisions[0]["artifact_revision_id"]

    if not dq_rev_id:
        raise ReplayMismatchError("旧账本中无法定位 M4 dispute_queue 修订")

    dq_doc = _read_json_object(reader, dq_rev_id)
    old_disputes = dq_doc.get("disputes", [])

    old_rulings = {ev["dispute_id"]: ev for ev in m4_events}
    return old_disputes, old_rulings


def replay_m4_rulings(
    service: Any,
    step_run_id: str,
    resume_token: str,
    *,
    old_disputes: list[dict],
    old_rulings: dict[str, dict],
) -> list[dict]:
    """在新运行的 M4 暂停节点回放裁决。"""
    queues = service.list_step_run_revisions(step_run_id, artifact_type="dispute_queue")
    if not queues:
        raise ReplayMismatchError(f"新运行 {step_run_id} 未找到 dispute_queue 修订")

    new_dq_rev_id = queues[0]["artifact_revision_id"]
    new_dq_doc = _read_json_object(service, new_dq_rev_id)
    new_disputes = new_dq_doc.get("disputes", [])

    # 执行对位比对
    verify_m4_disputes(new_disputes, old_disputes)

    applied = []
    for d in new_disputes:
        did = d["dispute_id"]
        old_r = old_rulings[did]
        ruling_doc = {
            "schema_version": CANDIDATE_SCHEMA_VERSION,
            "dispute_id": did,
            "choice": old_r["choice"],
            "rationale": old_r["rationale"],
            "actor_ref": old_r.get("actor_ref", "user:wjt"),
        }
        record_category_ruling(service, step_run_id, resume_token, ruling_doc)
        applied.append(
            {
                "dispute_id": did,
                "old_event_revision_id": old_r.get("_event_revision_id"),
                "choice": ruling_doc["choice"],
            }
        )

    return applied


# ---------------------------------------------------------------------------
# M6 对位与回放
# ---------------------------------------------------------------------------

def verify_m6_targets(new_queue_items: list[dict], old_decisions: list[dict]) -> None:
    """比对 M6 审核队列目标集合必须与旧决定的 target 集合恰好相等（不多不少）。"""
    new_targets = {
        (
            item["target_entity_id"],
            item.get("kind") or item.get("entity_kind"),
            item["decision_type"],
        )
        for item in new_queue_items
    }
    old_targets = {
        (
            d["target_entity_id"],
            d["entity_kind"],
            d["decision_type"],
        )
        for d in old_decisions
    }

    if new_targets != old_targets:
        diff = new_targets ^ old_targets
        raise ReplayMismatchError(
            f"M6 审核目标集合不等: 新有旧无 {sorted(new_targets - old_targets)}, "
            f"旧有新无 {sorted(old_targets - new_targets)}, 差异集合: {sorted(diff)}"
        )


def load_m6_decisions_from_ledger(
    reader: Any, step_run_id: str | None = None
) -> list[dict]:
    """从旧账本中读取 succeeded 的 M6 StepRun 上的 26 条 review_decision。"""
    human_events = reader.list_human_events(step_run_id)

    # 按 step_run_id 分组
    by_srun: dict[str, list[dict]] = {}
    for ev in human_events:
        rev_id = ev["event_revision_id"]
        doc = _read_json_object(reader, rev_id)
        if doc.get("event_kind") == "review_decision":
            doc["_event_revision_id"] = rev_id
            srun = doc["step_run_id"]
            by_srun.setdefault(srun, []).append(doc)

    if not by_srun:
        raise ReplayMismatchError("旧账本中未找到 M6 review_decision 事件")

    target_srun = step_run_id
    if target_srun is None:
        # 只选取 succeeded 状态的 step_run（如 STAGE4-brief 规定）
        for srun_id, docs in by_srun.items():
            srun_row = reader.get_step_run(srun_id)
            if srun_row and srun_row["status"] == "succeeded":
                target_srun = srun_id
                break

    if target_srun is None or target_srun not in by_srun:
        raise ReplayMismatchError("旧账本中未找到处于 succeeded 状态的 M6 StepRun 决定")

    m6_events = by_srun[target_srun]

    # 读取该 step_run 中的 reviewed_candidate（针对 modify 决定提取 modified_content）
    rev_cands = reader.list_step_run_revisions(
        target_srun, artifact_type="reviewed_candidate"
    )
    rev_cands_by_eid = {}
    for rc in rev_cands:
        rc_doc = _read_json_object(reader, rc["artifact_revision_id"])
        eid = rc_doc.get("assertion_id") or rc_doc.get("school_view_id")
        if eid:
            rev_cands_by_eid[eid] = rc_doc

    decisions = []
    for ev in m6_events:
        target = ev.get("target") or {}
        eid = target.get("entity_id")
        ekind = target.get("entity_kind")
        dtype = ev.get("decision_type")
        verdict = ev.get("verdict")
        rationale = ev.get("rationale")
        evidence_refs = ev.get("evidence_refs", [])
        actor_ref = ev.get("actor_ref", "local_owner")

        modified_content = None
        if verdict == "modify":
            # 提取原候选与 reviewed_candidate 之间的字段差异作为 modified_content
            rev_cand = rev_cands_by_eid.get(eid)
            if rev_cand is None:
                raise ReplayMismatchError(
                    f"旧账本中 M6 modify 决定未找到对应的 reviewed_candidate: {eid}"
                )
            target_rev_id = target.get("artifact_revision_id")
            if target_rev_id:
                cand_set_doc = _read_json_object(reader, target_rev_id)
                cand_list = cand_set_doc.get("assertions", []) + cand_set_doc.get(
                    "school_views", []
                )
                orig_obj = next(
                    (
                        c
                        for c in cand_list
                        if c.get("assertion_id") == eid or c.get("school_view_id") == eid
                    ),
                    None,
                )
                if orig_obj:
                    modified_content = {
                        k: v for k, v in rev_cand.items() if orig_obj.get(k) != v
                    }
            if modified_content is None:
                # 备用方案：以 reviewed_candidate 中非元数据核心键构建
                modified_content = {
                    k: v
                    for k, v in rev_cand.items()
                    if k not in ("assertion_id", "school_view_id", "origin")
                }

        decisions.append(
            {
                "target_entity_id": eid,
                "entity_kind": ekind,
                "decision_type": dtype,
                "verdict": verdict,
                "rationale": rationale,
                "evidence_refs": evidence_refs,
                "actor_ref": actor_ref,
                "modified_content": modified_content,
                "_event_revision_id": ev.get("_event_revision_id"),
            }
        )

    return decisions


def load_m6_supplement_decisions(path: Path | str) -> list[dict]:
    """从外部 YAML 文件（如 U07-decisions_supplement.yaml）加载人工审核决定。"""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"缺少 M6 补充决定文件: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    actor_ref = data.get("actor_ref", "user:wjt")
    items = []
    for d in data.get("decisions", []):
        eid = d.get("entity_id") or d.get("target_entity_id")
        ekind = d.get("entity_kind")
        if not ekind:
            if eid.startswith("pat_"):
                ekind = "pattern"
            elif eid.startswith("as_"):
                ekind = "assertion"
            elif eid.startswith("sv_"):
                ekind = "school_view"
            else:
                ekind = "pattern"
        items.append(
            {
                "target_entity_id": eid,
                "entity_kind": ekind,
                "decision_type": d["decision_type"],
                "verdict": d["verdict"],
                "rationale": d["rationale"],
                "evidence_refs": d.get("evidence_refs", []),
                "actor_ref": d.get("actor_ref", actor_ref),
                "modified_content": d.get("modified_content"),
                "_event_revision_id": None,
            }
        )
    return items


def replay_m6_decisions(
    service: Any,
    step_run_id: str,
    resume_token: str,
    *,
    old_decisions: list[dict],
    supplement_decisions: list[dict] | None = None,
) -> list[dict]:
    """在新运行的 M6 暂停节点回放审核决定。"""
    queues = service.list_step_run_revisions(step_run_id, artifact_type="review_queue")
    if not queues:
        raise ReplayMismatchError(f"新运行 {step_run_id} 未找到 review_queue 修订")

    new_rq_rev_id = queues[0]["artifact_revision_id"]
    new_queue_items = _read_json_object(service, new_rq_rev_id)

    all_decisions = list(old_decisions)
    if supplement_decisions:
        all_decisions.extend(supplement_decisions)

    # 对位校验
    verify_m6_targets(new_queue_items, all_decisions)

    old_by_key = {
        (
            d["target_entity_id"],
            d["entity_kind"],
            d["decision_type"],
        ): d
        for d in all_decisions
    }

    applied = []
    for item in new_queue_items:
        key = (
            item["target_entity_id"],
            item.get("kind") or item.get("entity_kind"),
            item["decision_type"],
        )
        old_d = old_by_key[key]

        record_decision(
            service,
            step_run_id,
            resume_token,
            queue_item_id=item["queue_item_id"],
            verdict=old_d["verdict"],
            rationale=old_d["rationale"],
            modified_content=old_d.get("modified_content"),
            evidence_refs=old_d.get("evidence_refs", ()),
        )

        applied.append(
            {
                "target_entity_id": item["target_entity_id"],
                "queue_item_id": item["queue_item_id"],
                "verdict": old_d["verdict"],
                "old_event_revision_id": old_d.get("_event_revision_id"),
            }
        )

    return applied


# ---------------------------------------------------------------------------
# 顶层便利入口
# ---------------------------------------------------------------------------

def replay_from_reference_ledger(
    ref_ledger_dir: Path | str,
    target_service: Any,
    stage: str,
    step_run_id: str,
    resume_token: str,
) -> list[dict]:
    """从只读参考账本副本回放指定 stage (m4 或 m6) 的决定到 target_service。"""
    with LedgerReader(Path(ref_ledger_dir)) as reader:
        if stage == "m4":
            old_disputes, old_rulings = load_m4_rulings_from_ledger(reader)
            return replay_m4_rulings(
                target_service,
                step_run_id,
                resume_token,
                old_disputes=old_disputes,
                old_rulings=old_rulings,
            )
        elif stage == "m6":
            old_decisions = load_m6_decisions_from_ledger(reader)
            return replay_m6_decisions(
                target_service,
                step_run_id,
                resume_token,
                old_decisions=old_decisions,
            )
        else:
            raise ValueError(f"不支持回放的 stage: {stage}")
