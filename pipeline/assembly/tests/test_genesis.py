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



# ──────────────────────────────────────────────────────────────────────────────
# W8 8.5 / ACT impl-07/11 新增用例（D1 editions 补字段，D2 证据偏移统一 I-11）
# ──────────────────────────────────────────────────────────────────────────────


class TestGenesisEditionsEvidenceFields(unittest.TestCase):
    """D1: editions[] 补 evidence_level / corpus_spans_revision_id。"""

    def _make_inputs_with_csrid(self, csrid="rev_00000000000000000000000000000007"):
        """构造包含 corpus_spans_revision_id 的标准输入（两路偏移一致）。"""
        from pipeline.assembly.tests.test_model import make_valid_candidate_set, make_valid_reviewed_edition
        cset_raw = make_valid_candidate_set()
        ed_raw = make_valid_reviewed_edition()
        ed_raw["evidence_links"][0]["corpus_spans_revision_id"] = csrid
        v_cset = validate_candidate_set(cset_raw)
        v_ed = validate_reviewed_edition(ed_raw)
        return v_cset, v_ed

    def test_editions_carry_evidence_level_from_candidate_set(self):
        """evidence_level 取自 candidate_set，非硬编码。"""
        from pipeline.assembly.tests.test_model import make_valid_candidate_set, make_valid_reviewed_edition
        cset_raw = make_valid_candidate_set()
        cset_raw["evidence_level"] = "glyphbox_level"
        ed_raw = make_valid_reviewed_edition()
        v_cset = validate_candidate_set(cset_raw)
        v_ed = validate_reviewed_edition(ed_raw)
        prop = propose_genesis(v_cset, v_ed)
        res = assemble_genesis(v_cset, v_ed, prop["proposals"], id_range={"pattern": [1, 100]})
        editions = res["knowledge"]["editions"]
        self.assertEqual(len(editions), 1)
        self.assertEqual(editions[0]["evidence_level"], "glyphbox_level")

    def test_editions_reject_candidate_set_without_evidence_level(self):
        """缺字段抛 SchemaViolation SCH_001，非法值抛 SCH_002，不填默认。"""
        from pipeline.assembly.tests.test_model import make_valid_candidate_set
        from pipeline.ledger.errors import SchemaViolation
        # 1. 缺字段 -> SCH_001
        cset_raw = make_valid_candidate_set()
        del cset_raw["evidence_level"]
        with self.assertRaises(SchemaViolation) as ctx:
            validate_candidate_set(cset_raw)
        self.assertEqual(ctx.exception.code, "SCH_001")

        # 2. 取值不在闭集内 -> SCH_002
        cset_bad_val = make_valid_candidate_set()
        cset_bad_val["evidence_level"] = "invalid_level"
        with self.assertRaises(SchemaViolation) as ctx:
            validate_candidate_set(cset_bad_val)
        self.assertEqual(ctx.exception.code, "SCH_002")

        # 3. assemble_genesis 遇缺字段 candidate_set 同样抛 SCH_001（不静默填默认）
        ed_raw = make_valid_reviewed_edition()
        v_ed = validate_reviewed_edition(ed_raw)
        with self.assertRaises(AssemblyRefused) as ctx:
            assemble_genesis({"doc": cset_raw}, v_ed, [], id_range={"pattern": [1, 100]})
        self.assertEqual(ctx.exception.code, "SCH_001")

    def test_editions_carry_corpus_spans_revision_id_when_links_agree(self):
        """各链一致时取该值。"""
        v_cset, v_ed = self._make_inputs_with_csrid("rev_00000000000000000000000000000007")
        prop = propose_genesis(v_cset, v_ed)
        res = assemble_genesis(v_cset, v_ed, prop["proposals"], id_range={"pattern": [1, 100]})
        editions = res["knowledge"]["editions"]
        self.assertEqual(editions[0]["corpus_spans_revision_id"], "rev_00000000000000000000000000000007")

    def test_editions_corpus_spans_revision_id_none_when_links_have_none(self):
        """全为 None 时置 None，不编造。"""
        from pipeline.assembly.tests.test_model import make_valid_candidate_set, make_valid_reviewed_edition
        cset_raw = make_valid_candidate_set()
        ed_raw = make_valid_reviewed_edition()
        ed_raw["evidence_links"][0].pop("corpus_spans_revision_id", None)
        v_cset = validate_candidate_set(cset_raw)
        v_ed = validate_reviewed_edition(ed_raw)
        prop = propose_genesis(v_cset, v_ed)
        res = assemble_genesis(v_cset, v_ed, prop["proposals"], id_range={"pattern": [1, 100]})
        editions = res["knowledge"]["editions"]
        self.assertIsNone(editions[0]["corpus_spans_revision_id"])

    def test_editions_raise_on_conflicting_corpus_spans_revision_id(self):
        """出现两个不同值时抛错停手。"""
        from pipeline.assembly.tests.test_model import make_valid_candidate_set, make_valid_reviewed_edition
        cset_raw = make_valid_candidate_set()
        cset_raw["assertions"].append({
            "assertion_id": "as_qizheng_000002",
            "proposition_id": "pr_qizheng_000002",
            "proposition": "命宫在丑",
            "relation": "supports",
            "evidence": [
                {
                    "source_span_id": "ss_qizheng_ed01_o0000100",
                    "start_offset": 100,
                    "end_offset": 110,
                    "quote": "命宫在丑",
                    "quote_sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
                }
            ],
            "conditions": [], "exceptions": [], "concept_refs": [], "school_ids": [],
            "layer": "general", "content_status": "machine_extracted",
            "origin": {"lane": "main", "item_index": 1},
        })
        cset_raw["counts"]["assertions"] = 2
        ed_raw = make_valid_reviewed_edition()
        ed_raw["approved"].append({
            "entity_id": "as_qizheng_000002",
            "kind": "assertion",
            "artifact_revision_id": "rev_00000000000000000000000000000005",
            "content_status": "expert_verified",
            "decision_revision_ids": ["rev_00000000000000000000000000000006"],
        })
        ed_raw["evidence_links"][0]["corpus_spans_revision_id"] = "rev_00000000000000000000000000000007"
        ed_raw["evidence_links"].append({
            "entity_id": "as_qizheng_000002",
            "source_span_id": "ss_qizheng_ed01_o0000100",
            "corpus_spans_revision_id": "rev_00000000000000000000000000000099",
            "start_offset": 100,
            "end_offset": 110,
            "quote_sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        })
        v_cset = validate_candidate_set(cset_raw)
        v_ed = validate_reviewed_edition(ed_raw)
        prop = propose_genesis(v_cset, v_ed)
        with self.assertRaises(Exception) as ctx:
            assemble_genesis(v_cset, v_ed, prop["proposals"], id_range={"pattern": [1, 100]})
        self.assertIn("corpus_spans_revision_id", str(ctx.exception))


class TestGenesisEvidenceOffsets(unittest.TestCase):
    """D2: 证据偏移统一 I-11 绝对偏移。"""

    def test_evidence_offsets_are_absolute_i11(self):
        """M6 链与 M4 候选两路都在时，区间逐字段相等。"""
        cset, ed = make_genesis_inputs()
        prop = propose_genesis(cset, ed)
        res = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [1, 100]})
        ev = res["knowledge"]["assertions"][0]["evidence"][0]
        self.assertEqual(ev["start_offset"], 10)
        self.assertEqual(ev["end_offset"], 20)

    def test_evidence_offsets_reject_local_offset_masquerading(self):
        """注入局部偏移冒充绝对偏移 → 拒绝（护栏用例，必须能转红）。"""
        from pipeline.assembly.tests.test_model import make_valid_candidate_set, make_valid_reviewed_edition
        cset_raw = make_valid_candidate_set()
        ed_raw = make_valid_reviewed_edition()
        # M4 候选 start_offset=10, end_offset=20；M6 链注入不同值（模拟局部偏移）
        ed_raw["evidence_links"][0]["start_offset"] = 5
        ed_raw["evidence_links"][0]["end_offset"] = 15
        v_cset = validate_candidate_set(cset_raw)
        v_ed = validate_reviewed_edition(ed_raw)
        prop = propose_genesis(v_cset, v_ed)
        with self.assertRaises(Exception) as ctx:
            assemble_genesis(v_cset, v_ed, prop["proposals"], id_range={"pattern": [1, 100]})
        self.assertIn("offset", str(ctx.exception).lower())

    def test_no_local_offset_guessing_branch(self):
        """AST 断言 genesis.py 未出现「猜局部/回退整片段」分支的标志性写法。"""
        import pathlib
        genesis_path = pathlib.Path(__file__).parent.parent / "genesis.py"
        source = genesis_path.read_text(encoding="utf-8")
        forbidden_patterns = [
            "span.start_offset",
            "局部偏移猜测",
            "越界回退整片段",
        ]
        for pat in forbidden_patterns:
            self.assertNotIn(pat, source,
                msg="genesis.py 中出现了被禁止的局部偏移猜测模式: %r" % pat)


if __name__ == "__main__":
    unittest.main()
