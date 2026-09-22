"""M7 D 波返工（act/impl-07/24b）：闭包健全性检查 + R04 按概念分组。

本文件只读 fixture 与已验收模块；**不读 var/**（真书重跑见 `probe_real_m6_orchestrate.py`）。
"""

import copy
import json
import unittest
from pathlib import Path
from unittest import mock

import yaml

from pipeline.assembly import apply as apply_module
from pipeline.assembly import fixture_seed, incremental, orchestrate
from pipeline.assembly.canonical import content_sha256
from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.model import empty_snapshot_knowledge
from pipeline.assembly.orchestrate import (
    affected_closure,
    assemble,
    closure_soundness_violations,
    knowledge_equivalent,
)
from pipeline.ledger.errors import DuplicateIdentifier

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"


def load_manifest():
    return yaml.safe_load((FIXTURE / "manifest.yaml").read_text(encoding="utf-8"))


def fixture_views(manifest):
    views = []
    for edition in manifest["editions"]:
        view_dir = edition["views_dir"]
        views.append(
            {
                "source_id": edition["source_id"],
                "candidate_set": json.loads((FIXTURE / view_dir / "candidate_set.json").read_text(encoding="utf-8")),
                "reviewed_edition": json.loads((FIXTURE / view_dir / "reviewed_edition.json").read_text(encoding="utf-8")),
            }
        )
    return views


def round1_knowledge(manifest):
    return json.loads((FIXTURE / manifest["expected"]["round1"]).read_text(encoding="utf-8"))


def _relation(kind, left, right, index):
    return {
        "relation_key": "x:%s" % ("%032d" % index),
        "from_entity_id": left,
        "to_entity_id": right,
        "relation_kind": kind,
        "detail": {},
        "resolution": {"mode": "auto", "proposal_key": "auto:0"},
    }


def expanded_base(manifest):
    """r1 金标 + 一条 alias_of + 一个冲突组：让闭包**必须扩张**才覆盖得住。

    扩张到的对象（pat_qizheng_900060 / sv_900060）本轮不会被改动 → 交给 apply 原样拷贝。
    """
    base = round1_knowledge(manifest)
    base["patterns"] = sorted(
        base["patterns"]
        + [
            {
                "pattern_id": "pat_qizheng_900060", "concept_id": None, "name": "無關格局",
                "aliases": [], "rules": [], "assertion_ids": [],
                # 与基底自洽：school_view_ids 必须已按 _link_school_views 口径连好
                "school_view_ids": ["sv_%032d" % 900060],
                "recognition_rule_status": "not_captured", "provenance": [],
            }
        ],
        key=lambda item: item["pattern_id"],
    )
    base["school_views"] = sorted(
        base["school_views"]
        + [
            {
                "school_view_id": "sv_%032d" % 900060,
                "school_id": "sch_qizheng_003",
                "subject_entity_id": "pat_qizheng_900060",
                "conflict_group_id": "cg_%032d" % 900060,
                "source_conflict_group_id": "cg_%032d" % 900060,
                "claim_refs": [],
                "changes_current_judgment": True,
                "content_status": "machine_extracted",
            }
        ],
        key=lambda item: item["school_view_id"],
    )
    base["conflict_groups"] = sorted(
        [
            dict(
                group,
                member_school_view_ids=sorted(
                    group["member_school_view_ids"] + ["sv_%032d" % 900060]
                ),
            )
            for group in base["conflict_groups"]
        ]
        + [
            {
                "conflict_group_id": "cg_%032d" % 900060,
                "member_school_view_ids": ["sv_%032d" % 900060],
                "first_layer_display": True,
                "resolutions": [],
            }
        ],
        key=lambda item: item["conflict_group_id"],
    )
    base["relations"] = sorted(
        base["relations"] + [_relation("alias_of", "pat_qizheng_900001", "pat_qizheng_900060", 1)],
        key=lambda item: item["relation_key"],
    )
    return base


class ClosureSoundnessTest(unittest.TestCase):
    """§13.2：删等式断言、加健全性检查、扩张对象原样拷贝。"""

    def setUp(self):
        self.manifest = load_manifest()
        self.base = expanded_base(self.manifest)
        self.views = [fixture_views(self.manifest)[1]]

    # ---------------------- 具名用例 1（扩张后 assemble 必须成功）
    def test_closure_expansion_via_alias_assembles_successfully(self):
        closure = affected_closure(
            self.base,
            self.views,
            incremental.propose_incremental(self.base, self.views, round_no=2)["proposals"],
            [],
        )
        self.assertIn(
            "pat_qizheng_900060",
            closure["affected"],
            "alias_of 对端必须被闭包拉到（证明这条链路真的扩张了）",
        )

        result = assemble(
            self.base, self.views, [], incremental=True,
            base_snapshot_revision_id="rev_000000000000000000000000000000f1",
        )
        self.assertEqual(result["status"], "complete", "扩张到「不被改动」的对象不得让增量轮拒收")
        self.assertGreater(
            len(result["report"]["affected_entity_ids"]),
            len(result["result"]["rebuilt_entity_ids"]),
            "本用例必须真的出现「扩张到但未被改动」的对象（affected ⊋ rebuilt）",
        )

    # ---------------------- 具名用例 2（闭包漏对象 → 「闭包不完整」）
    def test_closure_missing_touched_object_refuses_incomplete(self):
        real_closure = affected_closure(self.base, self.views, [], [])

        def blind_closure(*args, **kwargs):
            return {"affected": [], "created": [], "untouched": sorted(real_closure["untouched"])}

        with mock.patch.object(orchestrate, "affected_closure", blind_closure):
            with self.assertRaises(AssemblyRefused) as ctx:
                assemble(
                    self.base, self.views, [], incremental=True,
                    base_snapshot_revision_id="rev_000000000000000000000000000000f1",
                )
        message = str(ctx.exception)
        self.assertIn("闭包不完整", message)
        self.assertIn("pat_qizheng_900001", message, "必须列出漏掉的对象 id: %s" % message)

    # ---------------------- 具名用例 3（扩张对象原样拷贝）
    def test_expanded_untouched_objects_copied_verbatim(self):
        result = assemble(
            self.base, self.views, [], incremental=True,
            base_snapshot_revision_id="rev_000000000000000000000000000000f1",
        )
        knowledge = result["result"]["knowledge"]
        affected = set(result["report"]["affected_entity_ids"])
        rebuilt = set(result["result"]["rebuilt_entity_ids"])
        expanded = affected - rebuilt
        self.assertIn("pat_qizheng_900060", expanded)

        by_id = {item["pattern_id"]: item for item in knowledge["patterns"]}
        base_by_id = {item["pattern_id"]: item for item in self.base["patterns"]}
        for entity_id in sorted(expanded):
            if entity_id in by_id:
                self.assertEqual(
                    by_id[entity_id], base_by_id[entity_id], "扩张对象必须原样拷贝: %s" % entity_id
                )
        sv_by_id = {item["school_view_id"]: item for item in knowledge["school_views"]}
        base_sv = {item["school_view_id"]: item for item in self.base["school_views"]}
        for entity_id in sorted(expanded):
            if entity_id in sv_by_id:
                self.assertEqual(sv_by_id[entity_id], base_sv[entity_id])

        # 监视护栏（ACT 24）仍须成立：交给 apply 的 affected 恰是闭包集合
        with mock.patch.object(
            apply_module, "_restore_untouched", wraps=apply_module._restore_untouched
        ) as spy:
            assemble(
                self.base, self.views, [], incremental=True,
                base_snapshot_revision_id="rev_000000000000000000000000000000f1",
            )
        self.assertTrue(spy.called)
        self.assertNotEqual(spy.call_args[0][3], None)
        self.assertEqual(spy.call_args[0][3], affected)

    # ---------------------- 具名用例 4（有扩张时增量仍 ≡ 全量）
    def test_incremental_equals_full_rebuild_with_expansion(self):
        inc = assemble(
            self.base, self.views, [], incremental=True,
            base_snapshot_revision_id="rev_000000000000000000000000000000f1",
        )
        full = assemble(
            self.base, self.views, [], incremental=False,
            base_snapshot_revision_id="rev_000000000000000000000000000000f1",
        )
        self.assertEqual(inc["status"], "complete")
        self.assertEqual(full["status"], "complete")
        self.assertTrue(
            knowledge_equivalent(inc["result"]["knowledge"], full["result"]["knowledge"]),
            "存在闭包扩张时，增量仍必须与全量逐字节相同",
        )

    # ---------------------- 健全性推导本身（不经过 apply）
    def test_closure_soundness_derivation_covers_attach_and_alias(self):
        proposals = [
            {
                "proposal_key": "merge:x", "kind": "merge", "rule_id": "R01", "resolution": "auto",
                "subject": ["pattern", "src_sanche_ed99", "pat_qizheng_900001"],
                "targets": ["pat_qizheng_900001"], "options": [], "auto_choice": "attach:pat_qizheng_900001",
                "decision_type": None, "basis_sha256": None, "depends_on": [],
            },
            {
                "proposal_key": "alias:y", "kind": "alias", "rule_id": "R04", "resolution": "human",
                "subject": ["concept", "src_sanche_ed99", "co_qizheng_900001"],
                "targets": ["co_qizheng_900001"], "options": ["accept_alias", "reject_alias"],
                "auto_choice": None, "decision_type": None, "basis_sha256": None, "depends_on": [],
            },
            {
                "proposal_key": "conflict:z", "kind": "conflict", "rule_id": "R11", "resolution": "auto",
                "subject": ["provenance_lost", "as_qizheng_900002"], "targets": [], "options": [],
                "auto_choice": "retire", "decision_type": None, "basis_sha256": None, "depends_on": [],
            },
        ]
        decisions = [
            {
                "proposal_set_revision_id": "rev_0", "proposal_key": "alias:y", "choice": "accept_alias",
                "target_entity_ids": ["co_qizheng_900001"], "seen_revision_id": "rev_0", "decision_type": None,
            }
        ]
        will_modify = orchestrate.will_modify_entity_ids(self.base, proposals, decisions)
        self.assertEqual(
            will_modify,
            sorted({"pat_qizheng_900001", "co_qizheng_900001", "as_qizheng_900002"}),
        )
        # 未决的人工提案不交给 apply → 不得计入
        self.assertEqual(orchestrate.will_modify_entity_ids(self.base, proposals, []),
                         sorted({"pat_qizheng_900001", "as_qizheng_900002"}))
        violations = closure_soundness_violations(
            self.base, proposals, decisions, affected={"pat_qizheng_900001"}
        )
        self.assertEqual(sorted(violations), ["as_qizheng_900002", "co_qizheng_900001"])


class R04GroupingTest(unittest.TestCase):
    """§13.3：R04 先按主体键分组，每组一条。"""

    def setUp(self):
        self.manifest = load_manifest()
        self.base = round1_knowledge(self.manifest)

    def _base(self):
        return empty_snapshot_knowledge("qizheng", {"pat_qizheng": [1, 10000]})

    def _view(self, candidates, approved):
        return {
            "source_id": "src_sanche_ed99",
            "candidate_set": {
                "schema_version": "1.0.0", "technique_id": "qizheng", "source_id": "src_sanche_ed99",
                "edition_part_artifact_id": "art_00000000000000000000000000000099",
                "patterns": [], "assertions": [], "collation_units": [],
                "concept_mentions": [], "new_concept_candidates": candidates,
                "school_views": [],
            },
            "reviewed_edition": {"approved": approved, "rejected": [], "decisions": []},
        }

    # ---------------------- 具名用例 5（同概念多次提及 → 一条）
    def test_r04_one_proposal_per_concept_across_mentions(self):
        candidates = [
            {"surface": "三辰", "concept_id": "co_qizheng_000007", "aliases": ["辰"], "rules": []},
            {"surface": "三辰", "concept_id": "co_qizheng_000007", "aliases": [], "rules": []},
            {"surface": "三辰", "concept_id": "co_qizheng_000007", "aliases": [], "rules": []},
        ]
        view = self._view(candidates, [{"kind": "concept", "entity_id": "co_qizheng_000007"}])
        out = incremental.propose_incremental(self._base(), [view], round_no=2)
        r04 = [p for p in out["proposals"] if p["rule_id"] == "R04"]
        self.assertEqual(len(r04), 1, "同一概念的三次提及必须合并成一条提案: %r" % (r04,))
        keys = [p["proposal_key"] for p in out["proposals"]]
        self.assertEqual(len(keys), len(set(keys)), "提案不得重号")

        # 真书路径的 ID_002 判据不得因分组而失效（分组只限 R04）
        again = incremental.propose_incremental(self._base(), [view], round_no=2)["proposals"]
        self.assertEqual(
            json.dumps(again, sort_keys=True, ensure_ascii=False),
            json.dumps(out["proposals"], sort_keys=True, ensure_ascii=False),
        )

    # ---------------------- 具名用例 6（别名/规则哈希取并集）
    def test_r04_aggregates_aliases_and_rule_hashes(self):
        candidates = [
            {"surface": "三辰", "concept_id": "co_qizheng_000007", "aliases": ["甲"], "rules": [{"ast_sha256": "h1"}]},
            {"surface": "三辰", "concept_id": "co_qizheng_000007", "aliases": ["乙"], "rules": [{"ast_sha256": "h2"}]},
        ]
        view = self._view(candidates, [{"kind": "concept", "entity_id": "co_qizheng_000007"}])
        proposal = [
            p for p in incremental.propose_incremental(self._base(), [view], round_no=2)["proposals"]
            if p["rule_id"] == "R04"
        ][0]
        expected = content_sha256(
            {
                "name": "三辰",
                "aliases": ["乙", "甲"],
                "rule_hashes": ["h1", "h2"],
                "concept_id": "co_qizheng_000007",
            }
        )
        self.assertEqual(
            proposal["basis_sha256"], expected,
            "basis 必须按组聚合后的别名与规则哈希计算（并集、排序）",
        )
        # 并集必须真的进了匹配：两个别名都命中基底同名概念 → 两条 target
        base = self._base()
        base["concepts"] = [
            {"concept_id": "co_qizheng_000011", "name": "別名甲", "aliases": ["甲"], "provenance": []},
            {"concept_id": "co_qizheng_000012", "name": "別名乙", "aliases": ["乙"], "provenance": []},
        ]
        alias_proposal = [
            p for p in incremental.propose_incremental(base, [view], round_no=2)["proposals"]
            if p["rule_id"] == "R04" and p["kind"] == "alias"
        ][0]
        self.assertEqual(alias_proposal["targets"], ["co_qizheng_000011", "co_qizheng_000012"])

    # ---------------------- 具名用例 7（同 concept_id 名称不一致 → 拒收）
    def test_r04_conflicting_names_same_concept_id_refuses(self):
        candidates = [
            {"surface": "三辰", "concept_id": "co_qizheng_000007", "aliases": [], "rules": []},
            {"surface": "通載", "concept_id": "co_qizheng_000007", "aliases": [], "rules": []},
        ]
        view = self._view(candidates, [{"kind": "concept", "entity_id": "co_qizheng_000007"}])
        with self.assertRaises(AssemblyRefused) as ctx:
            incremental.propose_incremental(self._base(), [view], round_no=2)
        message = str(ctx.exception)
        self.assertIn("概念名称冲突", message)
        self.assertIn("co_qizheng_000007", message)
        self.assertIn("三辰", message)
        self.assertIn("通載", message)

    # ---------------------- 具名用例 8（其余规则的 ID_002 原样保留）
    def test_id_002_still_refuses_duplicate_keys_from_other_rules(self):
        base = self._base()
        base["patterns"] = [
            {"pattern_id": "pat_qizheng_000009", "name": "同名格局", "aliases": [], "rules": [], "provenance": []}
        ]
        candidate = {
            "pattern_id": "pat_qizheng_000009", "name": "同名格局", "assertion_ids": [],
            "interpretation_status": "not_captured", "recognition_rule_status": "not_captured",
            "content_status": "machine_extracted",
        }
        cset = {
            "schema_version": "1.0.0", "technique_id": "qizheng", "source_id": "src_sanche_ed99",
            "edition_part_artifact_id": "art_00000000000000000000000000000099",
            "evidence_level": "glyphbox_level", "span_layer": "structural", "source_channels": {},
            "patterns": [candidate, copy.deepcopy(candidate)],
            "assertions": [], "collation_units": [], "concept_mentions": [],
            "new_concept_candidates": [], "school_views": [], "rejected": [], "disputes": [],
        }
        cset["counts"] = {
            key: len(cset[key])
            for key in (
                "assertions", "patterns", "school_views", "concept_mentions",
                "new_concept_candidates", "rejected", "disputes",
            )
        }
        view = {
            "source_id": "src_sanche_ed99",
            "candidate_set": cset,
            "reviewed_edition": {
                "schema_version": "1.0.0",
                "edition_part_artifact_id": cset["edition_part_artifact_id"],
                "candidate_set_revision_id": "rev_%032d" % 90,
                "candidate_package_revision_id": "rev_%032d" % 91,
                "validation_package_revision_id": "rev_%032d" % 92,
                "approved": [
                    {
                        "kind": "pattern", "entity_id": "pat_qizheng_000009",
                        "artifact_revision_id": "rev_%032d" % 90,
                        "content_status": "machine_extracted", "decision_revision_ids": [],
                    }
                ],
                "rejected": [], "decisions": [], "evidence_links": [], "school_views": [],
                "correction_request_revision_ids": [], "rework_impact_report_revision_id": None,
                "unresolved_count": 0,
            },
        }
        proposals = incremental.propose_incremental(base, [view], round_no=2)["proposals"]
        r01 = [p for p in proposals if p["rule_id"] == "R01"]
        keys = [p["proposal_key"] for p in r01]
        self.assertEqual(len(r01), 2, "R01 对重复候选仍应各出一条（不得被通用去重吞掉）")
        self.assertEqual(keys[0], keys[1], "这两条的键本就相同（同 subject）")

        # 唯一性检查必须原样保留：apply 拒收，且 orchestrate 不得替它去重
        with self.assertRaises(DuplicateIdentifier) as ctx:
            apply_module.apply_resolutions(base, [view], proposals, [])
        self.assertEqual(ctx.exception.code, "ID_002")
        with self.assertRaises(DuplicateIdentifier):
            assemble(base, [view], [], incremental=True,
                     base_snapshot_revision_id="rev_000000000000000000000000000000f1")


if __name__ == "__main__":
    unittest.main()
