#!/usr/bin/env python
"""G1（act/impl-07/26）实跑探针：把本波停手的五项阻塞逐项复现（只读，不写任何文件）。

用法（仓库根目录）：

    .venv/bin/python pipeline/assembly/tests/probe_g_blockers.py

命名沿用既有 `tests/probe_real_m6_*.py` 惯例（不叫 `test_*`，`unittest discover` 不会收集）。
退出码 0 = 探针跑完（"这些路径接不上"是结论不是失败）；1 = 探针自身出错。

判定口径：每一项都用**当前 HEAD 的真实运行结果**说话，命令与输出一并留在 M7 G1 回报里
（`/Users/jingtaiwei/tmux-agents/runs/fb-m7-g1.report.md`）。本文件不 import 任何被改动的
模块之外的私货，只用 fixture 视图 + 已验收引擎。
"""

import copy
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:  # 允许直接 `python pipeline/assembly/tests/probe_g_blockers.py`
    sys.path.insert(0, str(ROOT))

from pipeline.assembly import apply as m7_apply  # noqa: E402
from pipeline.assembly import gate, incremental, orchestrate  # noqa: E402

FIXTURE = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"
R1_REV = "rev_000000000000000000000000000000f1"  # expected/snapshot_revisions.yaml 的 r1 修订号

FINDINGS = []


def record(tag, ok, detail):
    FINDINGS.append((tag, ok))
    print("%s %s\n    %s" % ("REPRODUCED" if ok else "NOT REPRODUCED", tag, detail))


def load_manifest():
    return yaml.safe_load((FIXTURE / "manifest.yaml").read_text(encoding="utf-8"))


def load_view(edition):
    view_dir = FIXTURE / edition["views_dir"]
    return {
        "source_id": edition["source_id"],
        "candidate_set": json.loads((view_dir / "candidate_set.json").read_text(encoding="utf-8")),
        "reviewed_edition": json.loads((view_dir / "reviewed_edition.json").read_text(encoding="utf-8")),
    }


def load_r1():
    return json.loads((FIXTURE / "expected" / "snapshot_r1.json").read_text(encoding="utf-8"))


def r2_knowledge(ed99_view):
    """r1 → ed99 增量实跑（ACT 26 一.1 那一次实跑），返回 r2 的 knowledge。"""
    res = orchestrate.assemble(
        load_r1(), [ed99_view], [], incremental=True, base_snapshot_revision_id=R1_REV
    )
    assert res["status"] == "complete", res
    return res["result"]["knowledge"]


def rework_view(edition, *, drop="as_qizheng_900002", units=None):
    """同书返工视图：同一 (source_id, edition_part_ids)，删一条 Assertion。"""
    view = copy.deepcopy(load_view(edition))
    cset = view["candidate_set"]
    if drop:
        cset["assertions"] = [a for a in cset["assertions"] if a["assertion_id"] != drop]
    cset["counts"]["assertions"] = len(cset["assertions"])
    if units is not None:
        cset["collation_units"] = units
    reviewed = view["reviewed_edition"]
    if drop:
        reviewed["approved"] = [i for i in reviewed["approved"] if i["entity_id"] != drop]
        reviewed["decisions"] = [d for d in reviewed["decisions"] if d["target_entity_id"] != drop]
        reviewed["evidence_links"] = [l for l in reviewed["evidence_links"] if l["entity_id"] != drop]
    return view


def expect_raise(callable_, tag, needle, note):
    try:
        callable_()
    except Exception as exc:  # noqa: BLE001 - 探针要连异常类型一起打印
        detail = "%s: %s\n    断言片段命中=%s\n    %s" % (
            type(exc).__name__,
            exc,
            needle in str(exc),
            note,
        )
        record(tag, needle in str(exc), detail)
        return str(exc)
    record(tag, False, "预期抛出含 %r 的异常，实际未抛（%s）" % (needle, note))
    return ""


def main():
    manifest = load_manifest()
    ed01, ed99 = manifest["editions"]
    ed01_view, ed99_view = load_view(ed01), load_view(ed99)
    r1 = load_r1()

    print("== F1 同书返工（replacement/extension）在 apply 层被写死拒收")
    expect_raise(
        lambda: m7_apply.apply_resolutions(r1, [ed01_view], [], []),
        "F1_rework_refused_by_apply",
        "已在基底里",
        "ACT 26 一.3 的 ed01r2（同 source_id）走不到 apply：C 波留下的 fail-closed 护栏"
        "（apply.py:469，commit 564717f）从未被 D/E 波拆除；替换继承只在 incremental 侧实现。",
    )

    print("\n== F2 缺文（Omission）在 apply 层无对可配")
    omit_view = copy.deepcopy(ed99_view)
    omit_view["candidate_set"]["collation_units"].append(
        {"collation_key": "sanche-0002", "present": False}
    )
    expect_raise(
        lambda: orchestrate.assemble(
            r1, [omit_view], [], incremental=True, base_snapshot_revision_id=R1_REV
        ),
        "F2_omission_refused_by_apply",
        "对勘配对不唯一",
        "incremental R09 会照常产出 evidence/omission 提案，但 apply._collation_pair 要求"
        "两侧各恰有 1 条同 collation_key 的**断言**；真缺项一侧没有断言 → 候选 0 条 → 拒收。",
    )

    print("\n== F3 增文（Addition）口径：同 source 或缺项都被判成 addition")
    r2 = r2_knowledge(ed99_view)
    rework_absent = rework_view(
        ed01,
        units=[
            {"collation_key": "sanche-0001", "present": True},
            {"collation_key": "sanche-0002", "present": False},
            {"collation_key": "sanche-0003", "present": True},
        ],
    )
    props = incremental.propose_incremental(r2, [rework_absent], round_no=3)["proposals"]
    r09 = [p for p in props if p["rule_id"] == "R09"]
    ok = bool(r09) and {p["auto_choice"] for p in r09} == {"addition"}
    record(
        "F3_same_source_absent_unit_labelled_addition",
        ok,
        "R09 提案 auto_choice=%s（同 source 时 incremental.py:441 的 sorted(source) 比较退化，"
        "省文被判成 addition）；README §6 R09 要求「新版 present、旧版 present:false → addition」，"
        "但 Snapshot 没有承载「旧版 present:false」的字段，故跨 source 的 addition 在原理上不可达。"
        % sorted({p["auto_choice"] for p in r09}),
    )

    print("\n== F4 异文（VariantReading）：同 as_ 号 + 异文被撞号护栏拒收")
    variant_view = copy.deepcopy(ed99_view)
    variant_view["candidate_set"]["assertions"][0]["proposition"] = "三辰通載（異文）"
    expect_raise(
        lambda: orchestrate.assemble(
            r1, [variant_view], [], incremental=True, base_snapshot_revision_id=R1_REV
        ),
        "F4_variant_reading_refused_by_apply",
        "撞号 fail-closed",
        "R08（incremental.py:456-459）要求两侧 entity_ref（= as_ 号）相同且文本不同，"
        "而 apply.py:798 要求同号必须同命题。"
        "test_apply.py:451 自己写明了这一点：同号情形 incremental 只会产出 R07b（人工），"
        "variant_reading 只能靠**构造提案 + 显式 targets** 驱动。",
    )

    print("\n== F5 退役（retired）写死 proposal_key='retire'，identity_delta_contract 恒红")
    retire_proposal = {
        "proposal_key": incremental.proposal_key("conflict", ["provenance_lost", "as_qizheng_900002"]),
        "kind": "conflict",
        "rule_id": "R11",
        "resolution": "auto",
        "subject": ["provenance_lost", "as_qizheng_900002"],
        "targets": [],
        "options": [],
        "auto_choice": "retire",
        "decision_type": None,
        "basis_sha256": None,
        "depends_on": [],
    }
    # 只留一条退役提案：视图用空载荷的新 source（避免「禁止静默并入」等无关拒收）
    empty_payload_view = copy.deepcopy(ed99_view)
    for collection in ("assertions", "patterns", "school_views", "concept_mentions", "new_concept_candidates"):
        empty_payload_view["candidate_set"][collection] = []
        empty_payload_view["candidate_set"]["counts"][collection] = 0
    empty_payload_view["reviewed_edition"]["approved"] = []
    empty_payload_view["reviewed_edition"]["decisions"] = []
    empty_payload_view["reviewed_edition"]["evidence_links"] = []
    empty_payload_view["reviewed_edition"]["school_views"] = []

    out = m7_apply.apply_resolutions(r1, [empty_payload_view], [retire_proposal], [])
    entries = out["identity_delta"]["entries"]
    keys = sorted({entry["reason_ref"]["proposal_key"] for entry in entries})
    check = gate.evaluate_assembly(
        base_knowledge=r1,
        views=[empty_payload_view],
        decisions=[],
        knowledge=out["knowledge"],
        identity_delta=out["identity_delta"],
        collation=out["collation"],
        report={},
    )["checks"]["identity_delta_contract"]
    ok = keys == ["retire"] and not check["passed"]
    record(
        "F5_retired_entry_uses_literal_proposal_key",
        ok,
        "identity_delta[0]=%s\n    delta 里的键=%s / R11 提案键=%s\n"
        "    gate.identity_delta_contract: passed=%s detail=%s\n"
        "    apply.py:1131 把 proposal_key 写死成字面量 'retire'，既不等于 R11 的提案键，"
        "也不在任何提案集里 → ACT 26 二/三 落地后**任何**带退役的轮次都会 FAIL。"
        % (
            json.dumps(entries[0], ensure_ascii=False),
            keys,
            retire_proposal["proposal_key"],
            check["passed"],
            check["detail"],
        ),
    )

    print("\n== F6 合并（merged）：CHANGE_TYPES 里有，代码里没有任何产出路径")
    merged_paths = [
        "apply._apply_split → 'split'",
        "apply._apply_retire → 'retired'",
        "merge_entities → AssemblyRefused（apply.py:307-314）",
    ]
    ok = "merged" in m7_apply.CHANGE_TYPES and len(m7_apply.CHANGE_TYPES) == 3
    record(
        "F6_merged_change_type_has_no_producer",
        ok,
        "CHANGE_TYPES=%s；三条可能的产出路径：%s；"
        "accept_alias 只追加 aliases/provenance，不写 identity_delta 条目。"
        "ACT 26 一.3 要求 ed01r2 造出「两个 Concept 被裁定合并 → merged」在本波范围内无法实现。"
        % (list(m7_apply.CHANGE_TYPES), "; ".join(merged_paths)),
    )

    bad = [tag for tag, ok in FINDINGS if not ok]
    print("\nSUMMARY reproduced=%d/%d" % (len(FINDINGS) - len(bad), len(FINDINGS)))
    if bad:
        print("NOT REPRODUCED: %s" % bad)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
