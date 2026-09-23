"""M7 增量汇编 D 波：增量编排（act/impl-07/24）。

本文件只读 fixture 与已验收模块；**不读 var/**（真书实跑证据见回报文件与
`tests/probe_real_m6_orchestrate.py`）。
"""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from pipeline.assembly import apply as apply_module
from pipeline.assembly import fixture_seed, incremental, orchestrate
from pipeline.assembly.canonical import content_sha256
from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.incremental import assert_prev_meta_agreement, snapshot_revision_pairs
from pipeline.assembly.model import empty_snapshot_knowledge
from pipeline.assembly.orchestrate import (
    REPORT_KEYS,
    affected_closure,
    assemble,
    carry_forward,
    carry_forward_proposals,
    knowledge_equivalent,
    view_modes,
)
from pipeline.assembly.step import run_m7
from pipeline.assembly.tests.fixture_decisions import decisions_for_round
from pipeline.ledger import ids
from pipeline.ledger.errors import MissingReference
from pipeline.ledger.service import LedgerService

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"

#: report 键序逐字（act/05.yaml:36 + ACT 26 二：新字段只许追加在末尾）
EXPECTED_REPORT_KEYS = (
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
    "dropped_proposal_keys",  # ACT 28（CHARTER §21 ①）：D-14 剔除的提案键
    "dropped_relations",  # ACT 28（CHARTER §22.2）：随退役/合并删除的基底关系，追加在末尾
)


def load_manifest():
    return yaml.safe_load((FIXTURE / "manifest.yaml").read_text(encoding="utf-8"))


def load_view(view_dir, name):
    return json.loads((FIXTURE / view_dir / name).read_text(encoding="utf-8"))


def fixture_views(manifest):
    views = []
    for edition in manifest["editions"]:
        view_dir = edition["views_dir"]
        views.append(
            {
                "source_id": edition["source_id"],
                "candidate_set": load_view(view_dir, "candidate_set.json"),
                "reviewed_edition": load_view(view_dir, "reviewed_edition.json"),
            }
        )
    return views


def round1_knowledge(manifest):
    return json.loads((FIXTURE / manifest["expected"]["round1"]).read_text(encoding="utf-8"))


def proposal(kind, rule_id, subject, *, targets=(), options=(), resolution="auto", auto_choice=None):
    """手工构造一条形态完整的提案（只为闭包/搬运判定，不参与生成）。"""
    return {
        "proposal_key": incremental.proposal_key(kind, subject),
        "kind": kind,
        "rule_id": rule_id,
        "resolution": resolution,
        "subject": list(subject),
        "targets": list(targets),
        "options": list(options),
        "auto_choice": auto_choice,
        "decision_type": None,
        "basis_sha256": None,
        "depends_on": [],
    }


#: 「同名歧义」版次的合成保留号（只进临时 Ledger；不是新 ID 前缀）
AMBIGUOUS_LEDGER_CONSTANTS = {
    "processing_run_id": "prun_%032d" % 31,
    "m4_step_run_id": "srun_%032d" % 31,
    "candidate_set_artifact_id": "art_%032d" % 31,
    "candidate_set_revision_id": "rev_%032d" % 31,
    "candidate_package_artifact_id": "art_%032d" % 32,
    "candidate_package_revision_id": "rev_%032d" % 32,
    "reviewed_edition_artifact_id": "art_%032d" % 33,
    "reviewed_edition_revision_id": "rev_%032d" % 33,
    "reviewed_edition_package_artifact_id": "art_%032d" % 34,
    "reviewed_edition_package_revision_id": "rev_%032d" % 34,
    "m6_stage_package_id": "pkg_m6_%032d" % 35,
    "m6_package_revision_id": "rev_%032d" % 35,
    "m6_step_run_id": "srun_%032d" % 36,
}


def make_snapshot_revision(service, technique_id, payload):
    """在临时 Ledger 上造一条已 sealed 的 canonical_snapshot 修订（只当基底用）。"""
    prun = service.create_processing_run("release_run", ids.new_id("artifact_id"), technique_id)
    _, cfg_rev = service.put_run_artifact(
        prun,
        "configuration",
        json.dumps({"stage": "m7", "synthetic_base": True}, sort_keys=True).encode("utf-8"),
        producer_module="pipeline.assembly.tests",
        producer_version="0.1.0-draft",
    )
    step_run = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "step_run_id": ids.new_id("step_run_id"),
            "processing_run_id": prun,
            "input_artifact_ids": [],
            "technique_profile_id": technique_id,
            "configuration_artifact_id": cfg_rev,
        }
    )
    data = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    art_id, rev_id = service.put_artifact(
        step_run,
        "canonical_snapshot",
        data,
        producer_module="pipeline.assembly.tests",
        producer_version="0.1.0-draft",
    )
    service.seal_revision(rev_id)
    return art_id, rev_id


#: 夹具第二版次的人工决定集（同名歧义 R03b → admit_new）：用例不得手写决定
FIXTURE_DECISIONS_R2 = decisions_for_round(2)


def retired_assertion_scope(base, views) -> set:
    """被 D-14 剔除的 R11 提案指向的断言号（反证用例用，不依赖 assemble 的 report）。"""
    proposals = incremental.propose_incremental(base, views, round_no=2)["proposals"]
    dropped = set(carry_forward_proposals(base, views, proposals)["dropped"])
    return {
        proposal["subject"][-1]
        for proposal in proposals
        if proposal["proposal_key"] in dropped and proposal["rule_id"] == "R11"
    }


def relation(kind, left, right):
    return {
        "relation_key": "x:%s" % abs(hash((kind, left, right))),
        "from_entity_id": left,
        "to_entity_id": right,
        "relation_kind": kind,
        "detail": {},
        "resolution": {"mode": "auto", "proposal_key": "auto:0"},
    }


class AffectedClosureTest(unittest.TestCase):
    # ------------------------------------------------- 具名用例（不动点到不动点）
    def test_affected_closure_reaches_fixpoint(self):
        """二.2：沿 alias_of / distinct_from / merged_into 与冲突组同组迭代到不动点。"""
        p = lambda i: "pat_qizheng_%06d" % i
        sv = lambda i: "sv_%032d" % i
        base = empty_snapshot_knowledge("qizheng", {"pat_qizheng": [1, 10000]})
        base["patterns"] = [
            {"pattern_id": p(i), "name": "N%d" % i, "aliases": [], "rules": [], "provenance": []}
            for i in (1, 2, 3, 4)
        ]
        base["school_views"] = [
            {"school_view_id": sv(i), "school_id": "sch_qizheng_001", "subject_entity_id": p(1),
             "conflict_group_id": "cg_%032d" % 1, "claim_refs": [], "changes_current_judgment": True,
             "content_status": "machine_extracted"}
            for i in (1, 2)
        ]
        base["conflict_groups"] = [
            {"conflict_group_id": "cg_%032d" % 1, "member_school_view_ids": [sv(1), sv(2)],
             "first_layer_display": True, "resolutions": []}
        ]
        base["relations"] = [
            relation("distinct_from", p(1), p(2)),
            relation("alias_of", p(2), p(3)),
            relation("merged_into", p(3), sv(1)),
        ]

        # 只碰一个端点 p1：闭包必须把 p2、p3、sv1（经冲突组）与 sv2 全拉进来，且不得多拉 p4
        proposals = [proposal("merge", "R01", ["pattern", "src_sanche_ed99", p(1)], targets=[p(1)])]
        closure = affected_closure(base, [{"source_id": "src_sanche_ed99", "candidate_set": {}, "reviewed_edition": {}}], proposals, [])
        self.assertEqual(closure["affected"], sorted([p(1), p(2), p(3), sv(1), sv(2)]))
        self.assertNotIn(p(4), closure["affected"])
        self.assertIn(p(4), closure["untouched"])
        self.assertEqual(closure["created"], [], "apply 之前 created 为空表")

    # ------------------------------------- 具名用例（affected 之外原样拷贝）
    def test_untouched_objects_are_not_rebuilt(self):
        manifest = load_manifest()
        base = round1_knowledge(manifest)
        views = [fixture_views(manifest)[1]]
        final = incremental.propose_incremental(base, views, round_no=2)["proposals"]
        closure = affected_closure(base, views, final, FIXTURE_DECISIONS_R2)

        # 行为事实（不是读源码文本）：「原样拷贝」路径必须真的拿到闭包集合。
        # 否则「增量」可能悄悄退化成全量重建：apply 的 rebuilt = affected ∩ touched
        # 在 touched ⊆ affected 时对 affected 参数不敏感，光看 rebuilt 看不出来（见回报 §6）。
        with mock.patch.object(
            apply_module, "_restore_untouched", wraps=apply_module._restore_untouched
        ) as restore_spy:
            result = assemble(
                base, views, FIXTURE_DECISIONS_R2, incremental=True,
                base_snapshot_revision_id="rev_000000000000000000000000000000f1",
            )
        self.assertTrue(restore_spy.called, "必须走到「原样拷贝」路径")
        self.assertEqual(
            restore_spy.call_args[0][3],
            set(closure["affected"]),
            "传给 apply 的 affected 必须恰是闭包集合（不得为 None）",
        )

        # CHARTER §25.6：A2 是本轮**缺文**关系（`from=as_qizheng_900002`）的旧版端点，
        # 必须落在闭包内（否则关系端点悬空）；它本身没有断言级改动（不在 touched 里），
        # 所以仍然走「原样拷贝」而不是重建。
        self.assertIn("as_qizheng_900002", closure["affected"])
        self.assertNotIn("as_qizheng_900002", result["result"]["rebuilt_entity_ids"])
        self.assertTrue(closure["untouched"], "构造样本必须仍有闭包外的基底对象")
        by_id = {a["assertion_id"]: a for a in result["result"]["knowledge"]["assertions"]}
        self.assertEqual(
            by_id["as_qizheng_900002"],
            {a["assertion_id"]: a for a in base["assertions"]}["as_qizheng_900002"],
            "affected 之外的基底对象必须从基座原样拷贝",
        )
        # §13.2：等式断言 `rebuilt == affected` 已删，留存的不变量是 rebuilt ⊆ affected
        self.assertTrue(set(result["result"]["rebuilt_entity_ids"]) <= set(closure["affected"]))
        self.assertTrue(
            result["result"]["rebuilt_entity_ids"], "受影响对象里必须真的有被重建的（判据非空转）"
        )
        self.assertEqual(result["report"]["untouched_count"], len(closure["untouched"]))


class AssembleTest(unittest.TestCase):
    # ------------------------------------- 具名用例（本波最重要：增量 == 全量）
    def test_incremental_equals_full_rebuild(self):
        manifest = load_manifest()
        base = round1_knowledge(manifest)
        views = [fixture_views(manifest)[1]]

        inc = assemble(base, views, FIXTURE_DECISIONS_R2, incremental=True, base_snapshot_revision_id="rev_1")
        full = assemble(base, views, FIXTURE_DECISIONS_R2, incremental=False, base_snapshot_revision_id="rev_1")

        self.assertEqual(inc["status"], "complete")
        self.assertEqual(full["status"], "complete")
        self.assertTrue(
            knowledge_equivalent(inc["result"]["knowledge"], full["result"]["knowledge"]),
            "增量汇编结果必须与全量重算逐字节相同",
        )
        self.assertEqual(inc["result"]["knowledge_sha256"], full["result"]["knowledge_sha256"])
        # 增量侧不得超范围重建（本夹具上 rebuilt 恰等于闭包；等式本身已按 §13.2 不再是判据）
        self.assertLessEqual(
            set(inc["result"]["rebuilt_entity_ids"]),
            set(inc["report"]["affected_entity_ids"]),
        )
        self.assertGreater(inc["report"]["untouched_count"], 0, "增量轮必须有未被重建的对象")

    # ------------------- 具名用例（rebuilt ⊆ affected；闭包不完整即拒收）
    # 原名 `test_rebuilt_equals_affected_or_refuses`。§13.2 删掉了等式断言，
    # 判据改为「闭包健全性」（推导见 `test_incremental_rework.py`），用例名随行为改名。
    def test_rebuilt_is_subset_of_affected_or_refuses(self):
        manifest = load_manifest()
        base = round1_knowledge(manifest)
        views = [fixture_views(manifest)[1]]

        ok = assemble(base, views, FIXTURE_DECISIONS_R2, incremental=True, base_snapshot_revision_id="rev_1")
        self.assertLessEqual(
            set(ok["result"]["rebuilt_entity_ids"]),
            set(ok["report"]["affected_entity_ids"]),
        )

        # 闭包漏掉「将会被改动的对象」→ 必须拒收（这正是 §13.2 要防的静默覆盖）
        def blind_closure(*args, **kwargs):
            return {"affected": [], "created": [], "untouched": []}

        with mock.patch.object(orchestrate, "affected_closure", blind_closure):
            with self.assertRaises(AssemblyRefused) as ctx:
                assemble(base, views, FIXTURE_DECISIONS_R2, incremental=True, base_snapshot_revision_id="rev_1")
        self.assertIn("闭包不完整", str(ctx.exception))
        self.assertIn("pat_qizheng_900001", str(ctx.exception))

        # 闭包过宽（多报一个不会被改动的号）→ §13.2 裁定 (b)：不得拒收
        def wide_closure(*args, **kwargs):
            return {
                "affected": sorted(set(ok["report"]["affected_entity_ids"]) | {"as_qizheng_900002"}),
                "created": [],
                "untouched": ["as_qizheng_900003"],
            }

        with mock.patch.object(orchestrate, "affected_closure", wide_closure):
            wide = assemble(base, views, FIXTURE_DECISIONS_R2, incremental=True, base_snapshot_revision_id="rev_1")
        self.assertEqual(wide["status"], "complete", "扩张到的对象按原样拷贝，不得拒收")
        self.assertNotIn("as_qizheng_900002", wide["result"]["rebuilt_entity_ids"])

    # ------------------------------------- 具名用例（report 键序逐字）
    def test_report_key_order_is_verbatim(self):
        self.assertEqual(REPORT_KEYS, EXPECTED_REPORT_KEYS)
        manifest = load_manifest()
        base = round1_knowledge(manifest)
        result = assemble(
            base, [fixture_views(manifest)[1]], FIXTURE_DECISIONS_R2, incremental=True,
            base_snapshot_revision_id="rev_1",
        )
        self.assertEqual(tuple(result["report"].keys()), EXPECTED_REPORT_KEYS)
        # 同名歧义（R03b）由夹具决定集裁定 → 该提案计入 blocked_then_resolved
        self.assertEqual(
            result["report"]["proposals_by_resolution"],
            {"auto": 7, "human": 0, "blocked_then_resolved": 1},
        )
        self.assertEqual(result["report"]["rounds"], [2])
        # not_comparable 必须如实入册（不得静默压成 0），本夹具恰有两个：
        #   ① ed99 声明了一个**无 collation_key** 的可比单元（真书 26 条断言全无键的形状）；
        #   ② `sanche-0004`——ed99 有断言，而 ed01 **未声明**该单元（CHARTER §25.5/§25.9）。
        self.assertEqual(result["report"]["not_comparable_count"], 2)

    # ------------------------------------- 具名用例（ACT 26 二：report 记本轮提案键）
    def test_report_records_round_proposal_keys(self):
        """`report.round_proposal_keys` = 本次 ReleaseRun **各轮**全部提案键，升序去重。

        该字段是 `gate.identity_delta_contract` 回到草稿口径的依据（ACT 26 二/三），
        因此必须真的覆盖每一轮的提案（含回流后重出的轮次），不能只记最后一轮。
        """
        manifest = load_manifest()
        base = round1_knowledge(manifest)
        views = [fixture_views(manifest)[1]]
        result = assemble(
            base, views, FIXTURE_DECISIONS_R2, incremental=True, base_snapshot_revision_id="rev_1"
        )
        report = result["report"]

        self.assertEqual(tuple(report.keys()), EXPECTED_REPORT_KEYS, "新字段必须追加在末尾")
        keys = report["round_proposal_keys"]
        self.assertEqual(keys, sorted(set(keys)), "必须升序去重")
        self.assertTrue(keys, "本轮不得为空（夹具上至少有 R07/R01/R04 三条）")

        every = sorted(
            {
                proposal["proposal_key"]
                for proposals_res in result["rounds"]
                for proposal in proposals_res["proposals"]
            }
        )
        self.assertEqual(keys, every, "各轮全部提案键都要在册（不得只记最后一轮）")
        for proposal_key in keys:
            self.assertIn(proposal_key, every)

        # 与既有字段自洽：本轮全部提案的裁定计数之和等于提案键数
        self.assertGreaterEqual(len(keys), sum(report["proposals_by_resolution"].values()))

    # ------------------------------------- 具名用例（有待决 → awaiting_human）
    def test_awaiting_human_lists_pending_keys_sorted(self):
        p = ["pat_qizheng_000001", "pat_qizheng_000002"]
        base = empty_snapshot_knowledge("qizheng", {"pat_qizheng": [1, 10000]})
        base["patterns"] = [
            {"pattern_id": pid, "name": "三奇得使", "aliases": [], "rules": [], "provenance": []}
            for pid in p
        ]
        view = {
            "source_id": "src_sanche_ed99",
            "candidate_set": {
                "schema_version": "1.0.0", "technique_id": "qizheng", "source_id": "src_sanche_ed99",
                "edition_part_artifact_id": "art_00000000000000000000000000000099",
                "patterns": [{"pattern_id": None, "candidate_key": "c1", "name": "三奇得使", "assertion_ids": []}],
                "assertions": [], "collation_units": [], "concept_mentions": [],
                "new_concept_candidates": [], "school_views": [],
            },
            "reviewed_edition": {"approved": [{"kind": "pattern", "entity_id": "c1"}], "rejected": [], "decisions": []},
        }
        res = assemble(base, [view], [], incremental=True, base_snapshot_revision_id="rev_1")

        self.assertEqual(res["status"], "awaiting_human")
        self.assertNotIn("result", res, "有待决时不得给出 result")
        self.assertEqual(res["pending"], sorted(res["pending"]))
        self.assertGreaterEqual(len(res["pending"]), 1)
        for key in res["pending"]:
            self.assertIn(":", key)

    # ------------------------------------- 具名用例（超 max_rounds → 拒收）
    def test_rounds_exceeding_max_refuses_with_message(self):
        base = empty_snapshot_knowledge("qizheng", {"pat_qizheng": [1, 10000]})
        base["patterns"] = [
            {"pattern_id": "pat_qizheng_000001", "name": "三奇得使", "aliases": [], "rules": [],
             "provenance": []}
        ]
        view = {
            "source_id": "src_sanche_ed99",
            "candidate_set": {
                "schema_version": "1.0.0", "technique_id": "qizheng", "source_id": "src_sanche_ed99",
                "edition_part_artifact_id": "art_00000000000000000000000000000099",
                "patterns": [
                    {"pattern_id": None, "candidate_key": "cA", "name": "三奇得使", "assertion_ids": [],
                     "rules": [{"ast_sha256": "h1"}]},
                    {"pattern_id": None, "candidate_key": "cB", "name": "另一格局", "assertion_ids": [],
                     "rules": [{"ast_sha256": "h1"}]},
                ],
                "assertions": [], "collation_units": [], "concept_mentions": [],
                "new_concept_candidates": [], "school_views": [],
            },
            "reviewed_edition": {
                "approved": [{"kind": "pattern", "entity_id": "cA"}, {"kind": "pattern", "entity_id": "cB"}],
                "rejected": [], "decisions": [],
            },
        }
        # cA 命中基底名称 → R03b（人工）；cB 与 cA 共享规则哈希 → R03f（blocked，依赖 cA）
        decisions = [
            {
                "proposal_set_revision_id": "rev_0",
                "proposal_key": incremental.proposal_key("merge", ["pattern", "src_sanche_ed99", "cA"]),
                "choice": "admit_new",
                "target_entity_ids": [],
                "seen_revision_id": "rev_0",
                "decision_type": None,
            }
        ]
        with self.assertRaises(AssemblyRefused) as ctx:
            assemble(base, [view], decisions, max_rounds=1, incremental=True,
                     base_snapshot_revision_id="rev_1")
        self.assertIn("回流未收敛", str(ctx.exception))


class CarryForwardTest(unittest.TestCase):
    # ------------------------------------- 具名用例（basis 变 → needs_review）
    def test_carry_forward_marks_needs_review_on_basis_change(self):
        base = empty_snapshot_knowledge("qizheng", {"pat_qizheng": [1, 10000]})
        key = "conflict:abc"
        base["conflict_groups"] = [
            {
                "conflict_group_id": "cg_%032d" % 1,
                "member_school_view_ids": [],
                "first_layer_display": True,
                "resolutions": [{"mode": "human", "proposal_key": key, "basis_sha256": "old"}],
            }
        ]

        changed = [dict(proposal("conflict", "R06", ["conflict_group", "x", []]),
                        proposal_key=key, resolution="human", basis_sha256="new")]
        out = carry_forward(base, [], changed)
        self.assertEqual(out, {"carried": [], "needs_review": [key]})

        same = [dict(proposal("conflict", "R06", ["conflict_group", "x", []]),
                     proposal_key=key, resolution="human", basis_sha256="old")]
        self.assertEqual(carry_forward(base, [], same), {"carried": [key], "needs_review": []})

        # 本轮不再是人工待决（例如已转 auto）→ 沿用上一轮结论
        auto = [dict(proposal("conflict", "R06", ["conflict_group", "x", []]),
                     proposal_key=key, resolution="auto", auto_choice="unify")]
        self.assertEqual(carry_forward(base, [], auto), {"carried": [key], "needs_review": []})
        # 本轮根本没有这条键 → 沿用
        self.assertEqual(carry_forward(base, [], []), {"carried": [key], "needs_review": []})


class ReplacementInheritanceTest(unittest.TestCase):
    # ------------------------------------- 具名用例（D-14 识别口径）
    def test_replacement_identified_by_source_and_parts_not_package_id(self):
        manifest = load_manifest()
        base = round1_knowledge(manifest)
        ed01, ed99 = fixture_views(manifest)

        # 同一 (source_id, edition_part_ids) → replacement，且与包身份无关
        reworked = copy.deepcopy(ed01)
        reworked["reviewed_edition"]["stage_package_id"] = "pkg_m6_%032d" % 77
        reworked["candidate_set"]["candidate_set_revision_id"] = "rev_%032d" % 77
        reworked["reviewed_edition"]["reviewed_edition_revision_id"] = "rev_%032d" % 77
        self.assertEqual(view_modes(base, [reworked]), {"src_sanche_ed01": "replacement"})

        # 基底没有该 source → new
        self.assertEqual(view_modes(base, [ed99]), {"src_sanche_ed99": "new"})

        # 同一 source、版次部件不相交 → extension
        extended = copy.deepcopy(ed01)
        extended["candidate_set"]["edition_part_artifact_id"] = "art_%032d" % 88
        self.assertEqual(view_modes(base, [extended]), {"src_sanche_ed01": "extension"})

    # ------------------------------------- 具名用例（未变 provenance 不产提案）
    def test_unchanged_provenance_yields_no_new_proposal(self):
        manifest = load_manifest()
        base = round1_knowledge(manifest)
        ed01 = fixture_views(manifest)[0]
        modes = view_modes(base, [ed01])
        self.assertEqual(modes, {"src_sanche_ed01": "replacement"})

        proposals = incremental.propose_incremental(base, [ed01], round_no=2)["proposals"]
        filter_res = carry_forward_proposals(base, [ed01], proposals, modes=modes)
        dropped_rules = {
            p["rule_id"] for p in proposals if p["proposal_key"] in set(filter_res["dropped"])
        }
        # 未变的 Pattern（provenance 哈希逐字相同）与其仍有声明的断言：不得再产提案
        self.assertIn("R01", dropped_rules, "provenance 未变的 pattern 不得再出 merge 提案")
        self.assertIn("R11", dropped_rules, "声明仍在的 assertion 不得被判为删除（R11）")
        self.assertNotIn("R11", {p["rule_id"] for p in proposals if p["proposal_key"] in set(filter_res["kept"])})
        self.assertEqual(filter_res["dropped"], sorted(filter_res["dropped"]))

        # 候选内容变了（哈希不同）→ 提案必须保留
        changed = copy.deepcopy(ed01)
        changed["candidate_set"]["patterns"][0]["name"] = "三辰通載貴格（改）"
        proposals2 = incremental.propose_incremental(base, [changed], round_no=2)["proposals"]
        kept2 = carry_forward_proposals(base, [changed], proposals2, modes=modes)["kept"]
        kept_rules2 = {p["rule_id"] for p in proposals2 if p["proposal_key"] in set(kept2)}
        self.assertIn("R01", kept_rules2, "provenance 变化的 pattern 必须照常出提案")
    # ------------------------------------- 具名用例（CHARTER §21 ①）：接线是真的
    def test_carry_forward_wired_into_assemble(self):
        """`assemble` 必须真的调用 D-14 的 `carry_forward_proposals`，而不是只把它摆在那里。

        判据（全部只看 `assemble` 的可见输出）：

        1. 替换版次上未变的 provenance 必须有提案被剔除，键升序进 `report.dropped_proposal_keys`；
        2. `round_proposal_keys` 仍记**全部生成过**的键（剔除前），但 `apply` 实际收到的
           是剔除后的那批——用 spy 直接抓 `apply_resolutions` 的入参；
        3. 被剔除的 R11 键不得在 `identity_delta` 里留下任何痕迹；
        4. 反证（护栏有效）：把过滤关掉，同一输入立刻把仍在视图里的断言退役。
        """
        manifest = load_manifest()
        base = round1_knowledge(manifest)
        views = [fixture_views(manifest)[0]]  # ed01 重跑 → replacement
        self.assertEqual(view_modes(base, views), {"src_sanche_ed01": "replacement"})

        # 本轮天生带一条 R06（冲突组）人工提案：先给出决定，才走得到 apply
        proposals = incremental.propose_incremental(base, views, round_no=2)["proposals"]
        human = [item for item in proposals if item["resolution"] == "human"]
        self.assertTrue(human, "替换版次必须带人工提案（R06）")
        decisions = [
            {
                "proposal_set_revision_id": "rev_0",
                "proposal_key": item["proposal_key"],
                "choice": item["options"][0],
                "target_entity_ids": [],
                "seen_revision_id": "rev_0",
                "decision_type": item["decision_type"],
            }
            for item in human
        ]

        captured = {}
        real_apply = apply_module.apply_resolutions

        def spy(base_knowledge, view_docs, proposals, decisions, **kwargs):
            captured["keys"] = sorted(p["proposal_key"] for p in proposals)
            return real_apply(base_knowledge, view_docs, proposals, decisions, **kwargs)

        with mock.patch.object(apply_module, "apply_resolutions", spy):
            result = assemble(base, views, decisions, incremental=True, base_snapshot_revision_id="rev_1")

        self.assertEqual(result["status"], "complete")
        report = result["report"]
        dropped = report["dropped_proposal_keys"]
        self.assertTrue(dropped, "替换版次上未变的 provenance / 仍有声明的断言必须被剔除")
        self.assertEqual(dropped, sorted(dropped), "dropped_proposal_keys 必须升序")
        self.assertLessEqual(set(dropped), set(report["round_proposal_keys"]))

        # 2. 交给 apply 的正是「全部生成过的」−「被剔除的」
        self.assertEqual(
            captured["keys"],
            sorted(set(report["round_proposal_keys"]) - set(dropped)),
            "apply 必须收到过滤之后的那批裁定",
        )

        # 3. 剔除的键不得在身份变更（含 R11 退役）里留下痕迹
        delta_keys = {
            entry["reason_ref"]["proposal_key"]
            for entry in result["result"]["identity_delta"]["entries"]
        }
        self.assertFalse(
            delta_keys & set(dropped), "被剔除的提案不得出现在 identity_delta 的 reason_ref 里"
        )
        retired = {
            entry["from_entity_id"]
            for entry in result["result"]["identity_delta"]["entries"]
            if entry["change_type"] == "retire"
        }
        self.assertFalse(retired, "替换版次不得把仍在视图里的对象退役")

        # 4. 反证：拆掉过滤 → 同一输入立刻把仍在视图里声明的断言退役（静默折叠）。
        #    旧口径下这还会让「同 source 自配」的对勘关系端点悬空而 fail-closed（MissingReference）；
        #    CHARTER §25.3 之后同 source 不再配对，故本波的可观察破坏是「仍在视图里的断言被退役」
        #    ——判据仍然不许是空的。
        dangling = sorted(retired_assertion_scope(base, views))
        self.assertTrue(dangling, "替换版次上必须真的存在「被 R11 误判为删除」的断言")
        kept_live = {a["assertion_id"] for a in result["result"]["knowledge"]["assertions"]}
        self.assertTrue(
            set(dangling) <= kept_live,
            "接上 D-14 过滤后，仍在视图里声明的断言必须存活：%s" % dangling,
        )

        def bypass(*args, **kwargs):
            return {"dropped": [], "kept": []}

        with mock.patch.object(orchestrate, "carry_forward_proposals", bypass):
            broken = assemble(
                base, views, decisions, incremental=True, base_snapshot_revision_id="rev_1"
            )
        self.assertEqual(broken["status"], "complete")
        broken_knowledge = broken["result"]["knowledge"]
        broken_live = {a["assertion_id"] for a in broken_knowledge["assertions"]}
        self.assertFalse(
            broken_live & set(dangling),
            "拆掉护栏后，仍在视图里声明的断言必须真的被退役——否则第 1/3 条判据在空转：%s"
            % dangling,
        )
        for assertion_id in dangling:
            self.assertIn(assertion_id, broken_knowledge["retired_entity_ids"])


class AwaitingHumanLedgerTest(unittest.TestCase):
    """人工回流：``awaiting_human`` 在真 Ledger 上仍要落提案集与 ``pending_queue``。

    这条覆盖不因 D 波接通合并而丢掉（A 波原用例已改为「完成合并」，见回报「测试改动」节）。
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="m7_inc_dh_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.service = LedgerService(Path(self.tmp) / "ledger")
        self.addCleanup(self.service.close)
        self.manifest = load_manifest()
        self.technique_id = self.manifest["technique_id"]
        self.seeded = fixture_seed.seed_release_package(self.service, FIXTURE)["editions"]

    def _ambiguous_base(self):
        """r1 金标 + 同名第二条 pattern：制造名称歧义 → R03d（人工）。"""
        base = round1_knowledge(self.manifest)
        twin = copy.deepcopy(base["patterns"][0])
        twin["pattern_id"] = "pat_qizheng_900002"
        base["patterns"] = sorted(base["patterns"] + [twin], key=lambda p: p["pattern_id"])
        return base

    def _seed_ambiguous_view(self):
        ed99 = self.manifest["editions"][1]
        lc = dict(ed99["ledger_constants"])
        lc.update(AMBIGUOUS_LEDGER_CONSTANTS)
        view_dir = ed99["views_dir"]
        cset = load_view(view_dir, "candidate_set.json")
        pattern = cset["patterns"][0]
        pattern.pop("pattern_id", None)
        pattern["candidate_key"] = "ed99x"
        pattern["name"] = self._ambiguous_base()["patterns"][0]["name"]
        reviewed = load_view(view_dir, "reviewed_edition.json")
        reviewed["candidate_set_revision_id"] = lc["candidate_set_revision_id"]
        reviewed["candidate_package_revision_id"] = lc["candidate_package_revision_id"]
        for item in reviewed["approved"]:
            if item["kind"] == "pattern":
                item["entity_id"] = "ed99x"
        self.service.create_processing_run(
            "release_run", ed99["edition_part_artifact_id"], self.technique_id,
            processing_run_id=lc["processing_run_id"],
        )
        return fixture_seed._seed_one_edition(
            self.service,
            self.technique_id,
            ed99["edition_part_artifact_id"],
            lc["processing_run_id"],
            lc,
            cset,
            reviewed,
            dict(
                load_view(view_dir, "reviewed_edition_package.json"),
                reviewed_edition_revision_id=lc["reviewed_edition_revision_id"],
            ),
        )

    # ------------------------------------- 具名用例（待决 → 提案落盘 + 等人工）
    def test_awaiting_human_writes_proposal_artifacts_and_pending_queue(self):
        _, base_rev_id = make_snapshot_revision(
            self.service, self.technique_id, self._ambiguous_base()
        )
        seeded = self._seed_ambiguous_view()
        res = run_m7(
            self.service,
            self.manifest["editions"][1]["edition_part_artifact_id"],
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[seeded["m6_package_revision_id"]],
            base_snapshot_revision_id=base_rev_id,
            id_range=self.manifest["id_range"],
        )

        self.assertEqual(res["status"], "awaiting_human")
        self.assertIsNone(res["snapshot_revision_id"], "有待决时不得写 Snapshot")
        self.assertIsNotNone(res["proposals_revision_id"])
        self.assertEqual(res["pending_proposals"], sorted(res["pending_proposals"]))
        self.assertGreaterEqual(len(res["pending_proposals"]), 1)

        prop_rev = self.service.get_revision(res["proposals_revision_id"])
        self.assertEqual(prop_rev["status"], "sealed")
        prop_doc = json.loads(self.service.objects.get(prop_rev["sha256"]).decode("utf-8"))
        self.assertEqual(prop_doc["base_snapshot_revision_id"], base_rev_id)
        self.assertGreater(len(prop_doc["proposals"]), 0)

        step = self.service.get_step_run(res["step_run_id"])
        scope_row = self.service.store.conn.execute(
            "SELECT edition_part_id FROM processing_runs WHERE processing_run_id=?",
            (step["processing_run_id"],),
        ).fetchone()
        chain = self.service.list_checkpoints(scope_row[0], "m7")
        self.assertEqual(chain[-1]["content"]["pending_queue"], res["pending_proposals"])

        # 待决时不得留下任何 canonical_snapshot 新修订（除基底）
        snapshots = [
            row[0]
            for row in self.service.store.conn.execute(
                "SELECT r.artifact_revision_id FROM artifact_revisions r "
                "JOIN artifacts a ON a.artifact_id = r.artifact_id "
                "WHERE a.artifact_type='canonical_snapshot' AND r.status='sealed'"
            ).fetchall()
        ]
        self.assertEqual(snapshots, [base_rev_id])


class LedgerAgreementTest(unittest.TestCase):
    """§9.3 名实一致护栏在真 Ledger 上仍然成立（既有护栏不许改、不许跳过）。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="m7_inc_d_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.service = LedgerService(Path(self.tmp) / "ledger")
        self.addCleanup(self.service.close)
        self.manifest = load_manifest()
        self.seeded = fixture_seed.seed_release_package(self.service, FIXTURE)["editions"]

    # ------------------------------------- 具名用例（prev 非空 ⟺ meta.base 非空）
    def test_prev_revision_and_meta_base_agree_still_holds(self):
        ed01 = self.manifest["editions"][0]
        ed99 = self.manifest["editions"][1]
        first = run_m7(
            self.service,
            ed01["edition_part_artifact_id"],
            technique_id=self.manifest["technique_id"],
            reviewed_package_revision_ids=[self.seeded[ed01["edition_key"]]["m6_package_revision_id"]],
            id_range=self.manifest["id_range"],
        )
        self.assertEqual(first["status"], "succeeded")

        second = run_m7(
            self.service,
            ed99["edition_part_artifact_id"],
            technique_id=self.manifest["technique_id"],
            reviewed_package_revision_ids=[self.seeded[ed99["edition_key"]]["m6_package_revision_id"]],
            base_snapshot_revision_id=first["snapshot_revision_id"],
            id_range=self.manifest["id_range"],
            decisions=FIXTURE_DECISIONS_R2,
        )
        self.assertEqual(second["status"], "succeeded", "待决提案已由夹具决定集裁定，增量轮必须完成合并")

        pairs = snapshot_revision_pairs(self.service)
        self.assertEqual(len(pairs), 2)
        for pair in pairs:
            with self.subTest(revision=pair["snapshot_revision_id"]):
                assert_prev_meta_agreement(
                    pair["prev_revision_id"],
                    {"meta": {"base_snapshot_revision_id": pair["meta_base_snapshot_revision_id"]}},
                )
        delta = [p for p in pairs if p["snapshot_revision_id"] == second["snapshot_revision_id"]][0]
        self.assertEqual(delta["prev_revision_id"], first["snapshot_revision_id"])
        self.assertEqual(delta["meta_base_snapshot_revision_id"], first["snapshot_revision_id"])

        # 新 Snapshot 写在同一 Artifact 下（D-03 A），且带 assembly_seq
        rev = self.service.get_revision(second["snapshot_revision_id"])
        base_rev = self.service.get_revision(first["snapshot_revision_id"])
        self.assertEqual(rev["artifact_id"], base_rev["artifact_id"])
        knowledge = json.loads(self.service.objects.get(rev["sha256"]).decode("utf-8"))
        self.assertEqual(knowledge["meta"]["base_snapshot_revision_id"], first["snapshot_revision_id"])
        self.assertEqual(knowledge["meta"]["assembly_seq"], 2)
        self.assertIn("decision_refs", knowledge["meta"])


if __name__ == "__main__":
    unittest.main()
