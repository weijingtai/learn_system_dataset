"""M7 增量汇编 B 波：配对层 + 提案规则 + 号位 + 名实一致护栏（act/impl-07/22）。

本文件只读 fixture 与已验收模块；**不读 var/**。真书证据见回报文件。
"""

import ast
import hashlib
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.assembly import fixture_seed, incremental, matcher
from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.incremental import (
    PROPOSAL_FIELDS,
    RULE_IDS,
    allocate_ids,
    assert_prev_meta_agreement,
    propose_incremental,
    snapshot_revision_pairs,
)
from pipeline.assembly.matcher import (
    NOT_COMPARABLE_MISSING_COLLATION_KEY,
    propose_pairs,
    units_of_view,
    unpairable_units,
)
from pipeline.assembly.model import MERGE_RELATIONS, PROPOSAL_KINDS, PairCandidate
from pipeline.assembly.step import run_m7
from pipeline.ledger.service import LedgerService

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"
ASSEMBLY_DIR = ROOT / "pipeline" / "assembly"

#: act/03.yaml:26-49 的规则名，逐字（与 ACT 22 contract 一「逐字」要求对照）
RULE_TABLE_IDS = (
    "R01", "R01b", "R02", "R03a", "R03b", "R03c", "R03d", "R03e", "R03f", "R03g",
    "R04", "R06", "R07", "R07b", "R08", "R09", "R10", "R11", "R11b",
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


def real_book_shaped_view():
    """真书形态（CHARTER §8.2）：无 `collation_units` 键、断言 `collation_key` 全 null。"""
    return {
        "source_id": "src_qianyuan_ed01",
        "candidate_set": {
            "schema_version": "1.0.0",
            "technique_id": "qizheng",
            "source_id": "src_qianyuan_ed01",
            "edition_part_artifact_id": "art_00000000000000000000000000000001",
            "patterns": [
                {"pattern_id": "pat_qizheng_000001", "name": "奇儀格局", "assertion_ids": []},
                {"pattern_id": "pat_qizheng_000002", "name": "三奇得使", "assertion_ids": []},
            ],
            "assertions": [
                {
                    "assertion_id": "as_qizheng_000001",
                    "collation_key": None,
                    "proposition": "命宮在子",
                    "evidence": [{"source_span_id": "ss_qianyuan_p1_s1"}],
                }
            ],
            "concept_mentions": [],
            "new_concept_candidates": [],
            "school_views": [],
            "rejected": [],
            "disputes": [],
        },
        "reviewed_edition": {
            "approved": [{"kind": "assertion", "entity_id": "as_qizheng_000001"}],
            "rejected": [],
            "decisions": [],
        },
    }


def empty_base(technique_id="qizheng"):
    return {
        "technique_id": technique_id,
        "id_range": {"pat_%s" % technique_id: [1, 10000]},
        "id_allocation": {"pat_%s" % technique_id: 0},
        "allocated_pattern_ids": [],
        "retired_entity_ids": [],
        "editions": [],
        "concepts": [],
        "patterns": [],
        "assertions": [],
        "school_views": [],
        "conflict_groups": [],
        "relations": [],
    }


class PairingLayerTest(unittest.TestCase):
    # ------------------------------------------------ 具名用例 1（结构护栏）
    def test_propose_pairs_is_the_only_matching_site(self):
        """三.3：配对判断只允许出现在 matcher.py。"""
        matcher_src = (ASSEMBLY_DIR / "matcher.py").read_text(encoding="utf-8")
        incremental_src = (ASSEMBLY_DIR / "incremental.py").read_text(encoding="utf-8")

        self.assertIn("def propose_pairs(", matcher_src, "配对层签名必须固定")
        self.assertIn("propose_pairs", incremental_src, "incremental.py 必须经 propose_pairs 配对")

        # incremental.py 里不得出现「另一侧 collation_key 的比对」
        pattern = re.compile(r"collation_key\"\]\s*==|==\s*\w*\[\"collation_key\"\]")
        offenders = [
            (i + 1, line.strip())
            for i, line in enumerate(incremental_src.splitlines())
            if pattern.search(line)
        ]
        self.assertEqual(offenders, [], "incremental.py 不得自行比对 collation_key: %r" % (offenders,))

        # 两个文件都不许引入相似度/编辑距离/网络库
        for source, name in ((matcher_src, "matcher.py"), (incremental_src, "incremental.py")):
            tree = ast.parse(source)
            imported = {
                alias.name.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in (node.names if isinstance(node, ast.Import) else [node.module and ast.alias(node.module)])
                or []
                if alias is not None and alias.name
            }
            forbidden = imported & {"difflib", "requests", "httpx", "openai"}
            self.assertEqual(forbidden, set(), "%s 引入了禁止模块: %r" % (name, forbidden))
            for token in ("SequenceMatcher", "levenshtein", "similarity"):
                self.assertNotIn(token, source, "%s 不得出现 %s" % (name, token))

        # 除 matcher.py 外，仓库内不得有第二个文件持有配对实现
        holders = [
            path.name
            for path in sorted(ASSEMBLY_DIR.glob("*.py"))
            if "def propose_pairs(" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(holders, ["matcher.py"], "配对实现只能有一个落点: %r" % (holders,))

    # ------------------------------------------------ 具名用例 2（确定性）
    def test_propose_pairs_deterministic_same_input_same_output(self):
        manifest = load_manifest()
        views = fixture_views(manifest)
        left = units_of_view(views[0]["candidate_set"], views[0]["reviewed_edition"])
        right = units_of_view(views[1]["candidate_set"], views[1]["reviewed_edition"])

        first = propose_pairs(left, right)
        second = propose_pairs(left, right)
        self.assertEqual(first, second)
        self.assertEqual(
            [pair.as_dict() for pair in first], [pair.as_dict() for pair in second]
        )
        self.assertGreater(len(first), 0, "fixture 两版次本就有共享 collation_key 与共享 span")

        # 全量提案层同样逐字节可复现
        base = json.loads((FIXTURE / manifest["expected"]["round1"]).read_text(encoding="utf-8"))
        out1 = propose_incremental(base, [views[1]], round_no=2)
        out2 = propose_incremental(base, [views[1]], round_no=2)
        self.assertEqual(
            json.dumps(out1, sort_keys=True, ensure_ascii=False),
            json.dumps(out2, sort_keys=True, ensure_ascii=False),
        )

    # ------------------------------------------------ 具名用例 3（§8.2 如实返回）
    def test_propose_pairs_returns_not_comparable_when_collation_key_null(self):
        view = real_book_shaped_view()
        other = dict(real_book_shaped_view(), source_id="src_qianyuan_ed02")
        other["candidate_set"] = dict(
            other["candidate_set"],
            source_id="src_qianyuan_ed02",
            assertions=[
                {
                    "assertion_id": "as_qizheng_000002",
                    "collation_key": None,
                    "proposition": "命宮在丑",
                    "evidence": [{"source_span_id": "ss_qianyuan_p9_s9"}],
                }
            ],
        )
        # 第三个视图：文本与 left **逐字相同**但同样没有 collation_key。
        # 这一条是「不许回退到文本比对」的非空转判据（P2 探针正打在它上面）。
        same_text = dict(real_book_shaped_view(), source_id="src_qianyuan_ed03")
        same_text["candidate_set"] = dict(
            same_text["candidate_set"],
            source_id="src_qianyuan_ed03",
            assertions=[
                {
                    "assertion_id": "as_qizheng_000003",
                    "collation_key": None,
                    "proposition": "命宮在子",
                    "evidence": [{"source_span_id": "ss_qianyuan_p7_s7"}],
                }
            ],
        )

        left = units_of_view(view["candidate_set"], view["reviewed_edition"])
        right_units = units_of_view(other["candidate_set"], other["reviewed_edition"])
        same_text_units = units_of_view(same_text["candidate_set"], same_text["reviewed_edition"])

        self.assertEqual(propose_pairs(left, right_units), [], "缺 collation_key 时不许猜、不许回退文本比对")
        self.assertEqual(
            propose_pairs(left, same_text_units),
            [],
            "文本逐字相同但双方都没声明 collation_key —— 不得就此配成对（§8.2）",
        )
        reasons = unpairable_units(left)
        self.assertGreaterEqual(len(reasons), 1)
        for reason in reasons:
            self.assertEqual(reason["reason"], NOT_COMPARABLE_MISSING_COLLATION_KEY)

        base = empty_base()
        out = propose_incremental(base, [view], round_no=2)
        self.assertEqual(
            out["report"]["not_comparable_missing_collation_key"],
            len(reasons),
            "无法配对必须计数，不得静默跳过",
        )
        collation_rules = {"R07", "R07b", "R08", "R09"}
        self.assertEqual(
            [p for p in out["proposals"] if p["rule_id"] in collation_rules],
            [],
            "对勘规则在缺 collation_key 的输入下不产生提案，这是正确行为",
        )

    # ------------------------------------------------ 具名用例 4（suggestion 恒 None）
    def test_pair_candidate_suggestion_is_none_in_this_wave(self):
        manifest = load_manifest()
        views = fixture_views(manifest)
        left = units_of_view(views[0]["candidate_set"], views[0]["reviewed_edition"])
        right = units_of_view(views[1]["candidate_set"], views[1]["reviewed_edition"])
        pairs = propose_pairs(left, right)

        field_names = [f.name for f in PairCandidate.__dataclass_fields__.values()]
        self.assertIn("suggestion", field_names, "PairCandidate 必须预留 suggestion 旁路字段")
        for pair in pairs:
            self.assertIsNone(pair.suggestion, "本波 suggestion 恒为 None")
            self.assertIn(pair.strategy, ("exact_collation_key", "shared_evidence_span", "same_formal_object"))


class ProposalRulesTest(unittest.TestCase):
    # ------------------------------------------------ 具名用例 5（rule_id 逐字）
    def test_proposal_rule_ids_match_the_rule_table_verbatim(self):
        self.assertEqual(RULE_IDS, RULE_TABLE_IDS, "rule_id 必须逐字等于 act/03.yaml:26-49 的规则表")
        self.assertGreaterEqual(len(RULE_IDS), 19)

        manifest = load_manifest()
        views = fixture_views(manifest)
        base = json.loads((FIXTURE / manifest["expected"]["round1"]).read_text(encoding="utf-8"))
        out = propose_incremental(base, [views[1]], round_no=2)

        self.assertGreater(len(out["proposals"]), 0, "ed99 轮必须产出提案")
        for proposal in out["proposals"]:
            self.assertIn(proposal["rule_id"], RULE_IDS)
            self.assertEqual(
                sorted(proposal.keys()), sorted(PROPOSAL_FIELDS), "提案键序/键集必须逐字"
            )
            self.assertIn(proposal["kind"], PROPOSAL_KINDS)
            self.assertTrue(proposal["proposal_key"].startswith(proposal["kind"] + ":"))
        keys = [p["proposal_key"] for p in out["proposals"]]
        self.assertEqual(keys, sorted(keys), "提案须按 proposal_key 升序")
        self.assertEqual(len(keys), len(set(keys)), "proposal_key 不得重复")

    # ------------------------------------------------ 具名用例 6（D-05 闭集）
    def test_merge_relation_is_closed_set(self):
        self.assertEqual(set(MERGE_RELATIONS), {"attach", "admit_new", "merge_entities"})
        manifest = load_manifest()
        base = json.loads((FIXTURE / manifest["expected"]["round1"]).read_text(encoding="utf-8"))
        out = propose_incremental(base, [fixture_views(manifest)[1]], round_no=2)
        merges = [p for p in out["proposals"] if p["kind"] == "merge"]
        self.assertGreater(len(merges), 0)
        for proposal in merges:
            if proposal["auto_choice"] is not None:
                head = proposal["auto_choice"].split(":", 1)[0]
                self.assertIn(head, MERGE_RELATIONS, "并入语义必须在闭集内: %r" % proposal["auto_choice"])
        # 越界的 relation 必须被拒（不是静默通过）
        with self.assertRaises(AssemblyRefused) as ctx:
            incremental._proposal("merge", "R02", ["pattern", "s", "p"], resolution="auto", auto_choice="silent_merge")
        self.assertEqual(ctx.exception.code, "SCH_002")

    # ------------------------------------------------ 具名用例 7（D-06 名称相等不自动 attach）
    def test_name_equality_does_not_auto_attach(self):
        view = {
            "source_id": "src_a_ed02",
            "candidate_set": {
                "schema_version": "1.0.0",
                "technique_id": "qizheng",
                "source_id": "src_a_ed02",
                "patterns": [{"pattern_id": None, "candidate_key": "a1", "name": "三奇得使", "assertion_ids": []}],
                "assertions": [],
                "collation_units": [],
                "concept_mentions": [],
                "new_concept_candidates": [],
                "school_views": [],
            },
            "reviewed_edition": {"approved": [{"kind": "pattern", "entity_id": "a1"}], "rejected": [], "decisions": []},
        }
        base = empty_base()
        base["patterns"] = [{"pattern_id": "pat_qizheng_000009", "name": "三奇得使", "aliases": [], "rules": []}]

        out = propose_incremental(base, [view], round_no=2)
        proposals = [p for p in out["proposals"] if p["subject"][0] == "pattern"]
        self.assertEqual(len(proposals), 1)
        proposal = proposals[0]
        self.assertEqual(proposal["rule_id"], "R03b", "仅名称命中不得自动 attach")
        self.assertEqual(proposal["resolution"], "human")
        self.assertIn("attach:pat_qizheng_000009", proposal["options"])
        self.assertIn("admit_new", proposal["options"])
        self.assertIsNone(proposal["auto_choice"])


class IdAllocationTest(unittest.TestCase):
    def _real_book_view_with_unapproved_ids(self):
        view = real_book_shaped_view()
        view["candidate_set"]["patterns"].append(
            {"pattern_id": "pat_qizheng_000003", "name": "乙奇得使", "assertion_ids": []}
        )
        return view

    # ------------------------------------------------ 具名用例 8（§8.1 只按已获批取号）
    def test_id_allocation_counts_only_approved(self):
        view = self._real_book_view_with_unapproved_ids()
        base = empty_base()
        base["patterns"] = [{"pattern_id": "pat_qizheng_000004", "name": "已正式格局", "aliases": [], "rules": []}]

        plan = allocate_ids(base, [view])
        self.assertEqual(
            plan["id_allocation"],
            {"pat_qizheng": 4},
            "未获批的 pat_qizheng_00000X 不得抬高号位（CHARTER §8.1）",
        )
        self.assertEqual(plan["allocated_pattern_ids"], [])

    # ------------------------------------------------ 具名用例 9（§8.1 不得静默丢弃）
    def test_unapproved_self_issued_id_is_reported_not_dropped(self):
        view = self._real_book_view_with_unapproved_ids()
        base = empty_base()
        report = allocate_ids(base, [view])["unapproved_with_self_issued_id"]
        self.assertEqual(
            sorted(item["pattern_id"] for item in report),
            ["pat_qizheng_000001", "pat_qizheng_000002", "pat_qizheng_000003"],
        )
        for item in report:
            self.assertEqual(item["source_id"], "src_qianyuan_ed01")
            self.assertEqual(item["reason"], "unapproved_with_self_issued_id")

        # 同一份报告必须出现在提案层的 assembly_report 里
        out = propose_incremental(base, [view], round_no=2)
        self.assertEqual(out["report"]["unapproved_with_self_issued_id"], report)
        # 未获批候选不得产生任何提案（也不许被当成已正式对象）
        self.assertEqual(
            [p for p in out["proposals"] if p["kind"] in ("merge", "alias")], [],
            "未获批候选不得自动并入",
        )


class PrevMetaAgreementTest(unittest.TestCase):
    # ------------------------------------------------ 具名用例 10（§9.3 **最重要**）
    def test_prev_revision_and_meta_base_agree(self):
        """``prev_revision_id`` 非空 ⟺ ``meta.base_snapshot_revision_id`` 非空。"""
        base_rev = "rev_000000000000000000000000000000f1"
        # 两侧都空 / 两侧都非空 → 通过
        assert_prev_meta_agreement(None, {"meta": None})
        assert_prev_meta_agreement(None, {})
        assert_prev_meta_agreement(base_rev, {"meta": {"base_snapshot_revision_id": base_rev}})
        # 任一侧单边非空 → 拒收（A 波那处名实不符正是这一形状）
        for prev, knowledge in (
            (base_rev, {"meta": None}),
            (base_rev, {"meta": {"base_snapshot_revision_id": None}}),
            (None, {"meta": {"base_snapshot_revision_id": base_rev}}),
        ):
            with self.assertRaises(AssemblyRefused) as ctx:
                assert_prev_meta_agreement(prev, knowledge)
            self.assertEqual(ctx.exception.code, "SCH_002")
            self.assertIn("名实不符", str(ctx.exception))

        # 真实 Ledger 上跑一遍：创世与增量轮后，全部 Snapshot 修订都必须两侧一致
        manifest = load_manifest()
        tmp = tempfile.mkdtemp(prefix="m7_b_guard_")
        self.addCleanup(shutil.rmtree, tmp, True)
        service = LedgerService(Path(tmp) / "ledger")
        self.addCleanup(service.close)
        seeded = fixture_seed.seed_release_package(service, FIXTURE)["editions"]

        ed01 = manifest["editions"][0]
        ed99 = manifest["editions"][1]
        first = run_m7(
            service,
            ed01["edition_part_artifact_id"],
            technique_id=manifest["technique_id"],
            reviewed_package_revision_ids=[seeded[ed01["edition_key"]]["m6_package_revision_id"]],
            id_range=manifest["id_range"],
        )
        self.assertEqual(first["status"], "succeeded")
        second = run_m7(
            service,
            ed99["edition_part_artifact_id"],
            technique_id=manifest["technique_id"],
            reviewed_package_revision_ids=[seeded[ed99["edition_key"]]["m6_package_revision_id"]],
            base_snapshot_revision_id=first["snapshot_revision_id"],
            id_range=manifest["id_range"],
        )
        self.assertEqual(second["status"], "awaiting_human", "增量轮先出提案，等人工决定")

        pairs = snapshot_revision_pairs(service)
        self.assertGreaterEqual(len(pairs), 1, "至少应有创世那一份 Snapshot")
        for pair in pairs:
            with self.subTest(revision=pair["snapshot_revision_id"]):
                assert_prev_meta_agreement(
                    pair["prev_revision_id"],
                    {"meta": {"base_snapshot_revision_id": pair["meta_base_snapshot_revision_id"]}},
                )


if __name__ == "__main__":
    unittest.main()
