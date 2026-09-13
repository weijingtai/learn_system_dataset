"""M7 创世汇编纯函数单元测试（spec §15, §6.2）。"""

import unittest

from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.genesis import assemble_genesis, propose_genesis
from pipeline.assembly.model import (
    validate_candidate_set,
    validate_reviewed_edition,
    validate_snapshot_knowledge,
)
from pipeline.assembly.tests.test_model import (
    make_valid_candidate_set,
    make_valid_reviewed_edition,
)


def make_genesis_inputs():
    cset = make_valid_candidate_set()
    ed = make_valid_reviewed_edition()
    v_cset = validate_candidate_set(cset)
    v_ed = validate_reviewed_edition(ed)
    return v_cset, v_ed


class TestGenesis(unittest.TestCase):
    def test_genesis_single_view_bytes_deterministic(self):
        cset, ed = make_genesis_inputs()
        p1 = propose_genesis(cset, ed)
        r1 = assemble_genesis(cset, ed, p1["proposals"], id_range={"pattern": [1, 100]})
        p2 = propose_genesis(cset, ed)
        r2 = assemble_genesis(cset, ed, p2["proposals"], id_range={"pattern": [1, 100]})
        self.assertEqual(r1["knowledge_bytes"], r2["knowledge_bytes"])
        self.assertEqual(r1["knowledge_sha256"], r2["knowledge_sha256"])
        self.assertEqual(r1["canonical_hash"], r2["canonical_hash"])

    def test_genesis_all_proposals_auto(self):
        cset, ed = make_genesis_inputs()
        prop = propose_genesis(cset, ed)
        self.assertGreater(len(prop["proposals"]), 0)
        for p in prop["proposals"]:
            self.assertEqual(p["resolution"], "auto")
            self.assertIsNone(p["decision_type"])
            self.assertEqual(p["depends_on"], [])
            self.assertEqual(p["options"], ["admit_new"])
            self.assertEqual(p["auto_choice"], "admit_new")

    def test_genesis_preserves_m4_pattern_id(self):
        cset, ed = make_genesis_inputs()
        p = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, p["proposals"], id_range={"pattern": [1, 100]})
        pat_ids = [pt["pattern_id"] for pt in res["knowledge"]["patterns"]]
        self.assertIn("pat_qizheng_000001", pat_ids)
        self.assertEqual(res["knowledge"]["allocated_pattern_ids"], [])

    def test_genesis_defensive_allocates_when_pattern_id_null(self):
        cset_raw = make_valid_candidate_set()
        cset_raw["patterns"][0]["pattern_id"] = None
        cset_raw["patterns"][0]["candidate_key"] = "ck_pat_01"

        cset, ed = validate_candidate_set(cset_raw), make_genesis_inputs()[1]
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [10, 20]})

        self.assertEqual(res["knowledge"]["allocated_pattern_ids"], ["pat_qizheng_000010"])
        self.assertEqual(res["knowledge"]["patterns"][0]["pattern_id"], "pat_qizheng_000010")

    def test_genesis_concepts_from_bound_mentions(self):
        cset, ed = make_genesis_inputs()
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [1, 100]})
        concepts = res["knowledge"]["concepts"]
        self.assertEqual(len(concepts), 1)
        self.assertEqual(concepts[0]["concept_id"], "co_qizheng_000001")
        self.assertEqual(concepts[0]["name"], "命宫")

    def test_genesis_excludes_unbound_new_concepts(self):
        cset_raw = make_valid_candidate_set()
        cset_raw["new_concept_candidates"].append({
            "surface": "未绑定概念",
            "technique_id": "qizheng",
            "evidence": [],
            "content_status": "machine_extracted",
            "origin": {"lane": "main", "item_index": 1},
        })
        cset_raw["counts"]["new_concept_candidates"] = 1
        ed = make_valid_reviewed_edition()

        v_cset = validate_candidate_set(cset_raw)
        v_ed = validate_reviewed_edition(ed)
        prop = propose_genesis(v_cset, v_ed)
        res = assemble_genesis(v_cset, v_ed, prop["proposals"], id_range={"pattern": [1, 100]})

        concept_ids = [c["concept_id"] for c in res["knowledge"]["concepts"]]
        self.assertNotIn("未绑定概念", concept_ids)
        self.assertEqual(len(res["report"]["excluded_unbound"]), 1)
        self.assertEqual(res["report"]["excluded_unbound"][0]["surface"], "未绑定概念")

    def test_genesis_assertion_subject_from_pattern_assertion_ids(self):
        cset, ed = make_genesis_inputs()
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [1, 100]})
        assertions = res["knowledge"]["assertions"]
        self.assertEqual(len(assertions), 1)
        self.assertEqual(assertions[0]["subject_entity_id"], "pat_qizheng_000001")

    def test_genesis_assertion_subject_resolved_to_snapshot_id(self):
        cset_raw = make_valid_candidate_set()
        cset_raw["patterns"][0]["pattern_id"] = None
        cset_raw["patterns"][0]["candidate_key"] = "ck_pat_sub"

        cset, ed = validate_candidate_set(cset_raw), make_genesis_inputs()[1]
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [5, 10]})

        self.assertEqual(res["knowledge"]["assertions"][0]["subject_entity_id"], "pat_qizheng_000005")

    def test_genesis_assertion_evidence_from_reviewed_edition(self):
        cset, ed = make_genesis_inputs()
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [1, 100]})
        ev = res["knowledge"]["assertions"][0]["evidence"][0]
        self.assertEqual(ev["source_span_id"], "ss_qizheng_ed01_p0001_s01")
        self.assertEqual(ev["start_offset"], 10)
        self.assertEqual(ev["end_offset"], 20)

    def test_genesis_assertion_school_view_ids_reverse_derived(self):
        cset, ed = make_genesis_inputs()
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [1, 100]})
        self.assertEqual(
            res["knowledge"]["assertions"][0]["school_view_ids"],
            ["sv_00000000000000000000000000000001"],
        )

    def test_genesis_pattern_school_view_ids_from_school_views(self):
        cset_raw = make_valid_candidate_set()
        ed_raw = make_valid_reviewed_edition()
        # 将 school_view 的 subject_entity_id 指向 pattern
        cset_raw["school_views"][0]["subject_entity_id"] = "pat_qizheng_000001"
        ed_raw["school_views"][0]["subject_entity_id"] = "pat_qizheng_000001"

        v_cset = validate_candidate_set(cset_raw)
        v_ed = validate_reviewed_edition(ed_raw)
        prop = propose_genesis(v_cset, v_ed)
        res = assemble_genesis(v_cset, v_ed, prop["proposals"], id_range={"pattern": [1, 100]})

        self.assertEqual(
            res["knowledge"]["patterns"][0]["school_view_ids"],
            ["sv_00000000000000000000000000000001"],
        )

    def test_genesis_conflict_group_preserved_and_first_layer_display(self):
        cset, ed = make_genesis_inputs()
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [1, 100]})
        cgs = res["knowledge"]["conflict_groups"]
        self.assertEqual(len(cgs), 1)
        self.assertEqual(cgs[0]["conflict_group_id"], "cg_00000000000000000000000000000001")
        self.assertTrue(cgs[0]["first_layer_display"])

    def test_genesis_no_content_status_synthesis(self):
        cset, ed = make_genesis_inputs()
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [1, 100]})
        # Pattern 顶层无 content_status
        self.assertNotIn("content_status", res["knowledge"]["patterns"][0])
        # Assertion content_status 为 approved 原值
        self.assertEqual(res["knowledge"]["assertions"][0]["content_status"], "expert_verified")

    def test_genesis_relations_empty_and_retired_empty(self):
        cset, ed = make_genesis_inputs()
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [1, 100]})
        self.assertEqual(res["knowledge"]["relations"], [])
        self.assertEqual(res["knowledge"]["retired_entity_ids"], [])

    def test_genesis_id_allocation_monotonic(self):
        cset, ed = make_genesis_inputs()
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [1, 100]})
        self.assertEqual(res["knowledge"]["id_allocation"]["pat_qizheng"], 1)

    def test_genesis_result_self_validates(self):
        cset, ed = make_genesis_inputs()
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [1, 100]})
        # 不抛异常即为自检通过
        validate_snapshot_knowledge(res["knowledge"])

    def test_genesis_allocates_from_config_id_range(self):
        cset_raw = make_valid_candidate_set()
        cset_raw["patterns"][0]["pattern_id"] = None
        cset_raw["patterns"][0]["candidate_key"] = "ck_alloc"

        cset, ed = validate_candidate_set(cset_raw), make_genesis_inputs()[1]
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [50, 60]})

        allocated_id = res["knowledge"]["allocated_pattern_ids"][0]
        self.assertEqual(allocated_id, "pat_qizheng_000050")

    def test_genesis_skips_ids_already_used_by_m4(self):
        cset_raw = make_valid_candidate_set()
        cset_raw["patterns"][0]["pattern_id"] = "pat_qizheng_000010"
        cset_raw["patterns"].append({
            "pattern_id": None,
            "candidate_key": "ck_defensive",
            "name": "待发号格局",
            "assertion_ids": ["as_qizheng_000001"],
            "evidence": [],
            "interpretation": None,
            "interpretation_status": "not_captured",
            "recognition_rule_status": "not_captured",
            "content_status": "machine_extracted",
            "origin": {"lane": "main", "item_index": 1},
        })
        cset_raw["counts"]["patterns"] = 2
        ed_raw = make_valid_reviewed_edition()
        ed_raw["approved"][0]["entity_id"] = "pat_qizheng_000010"

        v_cset = validate_candidate_set(cset_raw)
        v_ed = validate_reviewed_edition(ed_raw)
        prop = propose_genesis(v_cset, v_ed)
        # 区间从 10 开始，10 已被 M4 占用，应跳过 10 分配 11
        res = assemble_genesis(v_cset, v_ed, prop["proposals"], id_range={"pattern": [10, 20]})
        self.assertEqual(res["knowledge"]["allocated_pattern_ids"], ["pat_qizheng_000011"])

    def test_genesis_preserves_m4_id_outside_range(self):
        cset_raw = make_valid_candidate_set()
        ed_raw = make_valid_reviewed_edition()
        # M4 已发 pat_qizheng_000999 在 [1, 50] 之外
        cset_raw["patterns"][0]["pattern_id"] = "pat_qizheng_000999"
        ed_raw["approved"][0]["entity_id"] = "pat_qizheng_000999"

        v_cset = validate_candidate_set(cset_raw)
        v_ed = validate_reviewed_edition(ed_raw)
        prop = propose_genesis(v_cset, v_ed)
        res = assemble_genesis(v_cset, v_ed, prop["proposals"], id_range={"pattern": [1, 50]})

        self.assertEqual(res["knowledge"]["patterns"][0]["pattern_id"], "pat_qizheng_000999")

    def test_genesis_id_range_exhausted_refused(self):
        cset, ed = make_genesis_inputs()
        prop = propose_genesis(cset, ed)
        # start > end -> SCH_002
        with self.assertRaises(AssemblyRefused) as ctx:
            assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [10, 9]})
        self.assertEqual(ctx.exception.code, "SCH_002")

        # 真正号段不足
        cset_raw = make_valid_candidate_set()
        cset_raw["patterns"][0]["pattern_id"] = "pat_qizheng_000005"
        cset_raw["patterns"].append({
            "pattern_id": None,
            "candidate_key": "ck_exhaust2",
            "name": "格局2",
            "assertion_ids": ["as_qizheng_000001"],
            "evidence": [],
            "interpretation": None,
            "interpretation_status": "not_captured",
            "recognition_rule_status": "not_captured",
            "content_status": "machine_extracted",
            "origin": {"lane": "main", "item_index": 1},
        })
        cset_raw["counts"]["patterns"] = 2
        ed_raw = make_valid_reviewed_edition()
        ed_raw["approved"][0]["entity_id"] = "pat_qizheng_000005"
        v_cset2 = validate_candidate_set(cset_raw)
        v_ed2 = validate_reviewed_edition(ed_raw)
        prop2 = propose_genesis(v_cset2, v_ed2)
        # 号段 [5, 5]，但 5 已被占用
        with self.assertRaises(AssemblyRefused) as ctx:
            assemble_genesis(v_cset2, v_ed2, prop2["proposals"], id_range={"pattern": [5, 5]})
        self.assertEqual(ctx.exception.code, "SCH_002")
        self.assertIn("号段不足", str(ctx.exception))

    def test_genesis_knowledge_carries_id_range_and_allocation_list(self):
        cset, ed = make_genesis_inputs()
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [1, 100]})
        # 第 70 条：输入为 pattern，存储层按命名空间改键为 pat_qizheng
        self.assertEqual(res["knowledge"]["id_range"], {"pat_qizheng": [1, 100]})
        self.assertIsInstance(res["knowledge"]["allocated_pattern_ids"], list)


if __name__ == "__main__":
    unittest.main()
