"""M7 视图与快照模型校验单元测试（spec §15, §6.2, §8.1）。"""

import copy
import unittest

from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.model import (
    empty_snapshot_knowledge,
    validate_candidate_set,
    validate_reviewed_edition,
    validate_reviewed_package,
    validate_snapshot_knowledge,
)
from pipeline.ledger.errors import (
    DuplicateIdentifier,
    InvalidIdentifier,
    MissingReference,
    SchemaViolation,
)


def make_valid_reviewed_package():
    return {
        "schema_version": "0.1.0-draft",
        "reviewed_edition_revision_id": "rev_00000000000000000000000000000001",
        "decision_revision_ids": ["rev_00000000000000000000000000000002"],
        "decision_count": 1,
        "approved_count": 1,
        "rejected_count": 0,
        "unresolved_count": 0,
        "correction_request_revision_ids": [],
        "rework_impact_report_revision_id": None,
    }


def make_valid_reviewed_edition():
    return {
        "schema_version": "0.1.0-draft",
        "edition_part_artifact_id": "art_00000000000000000000000000000001",
        "candidate_set_revision_id": "rev_00000000000000000000000000000002",
        "candidate_package_revision_id": "rev_00000000000000000000000000000003",
        "validation_package_revision_id": "rev_00000000000000000000000000000004",
        "approved": [
            {
                "entity_id": "pat_qizheng_000001",
                "kind": "pattern",
                "artifact_revision_id": "rev_00000000000000000000000000000005",
                "content_status": "expert_verified",
                "decision_revision_ids": ["rev_00000000000000000000000000000006"],
            },
            {
                "entity_id": "as_qizheng_000001",
                "kind": "assertion",
                "artifact_revision_id": "rev_00000000000000000000000000000005",
                "content_status": "expert_verified",
                "decision_revision_ids": ["rev_00000000000000000000000000000006"],
            },
            {
                "entity_id": "sv_00000000000000000000000000000001",
                "kind": "school_view",
                "artifact_revision_id": "rev_00000000000000000000000000000005",
                "content_status": "expert_verified",
                "decision_revision_ids": ["rev_00000000000000000000000000000006"],
            },
        ],
        "rejected": [],
        "decisions": [
            {
                "decision_revision_id": "rev_00000000000000000000000000000006",
                "target_entity_id": "pat_qizheng_000001",
                "verdict": "accept",
            }
        ],
        "evidence_links": [
            {
                "entity_id": "as_qizheng_000001",
                "source_span_id": "ss_qizheng_ed01_p0001_s01",
                "corpus_spans_revision_id": "rev_00000000000000000000000000000007",
                "start_offset": 10,
                "end_offset": 20,
                "quote_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            }
        ],
        "school_views": [
            {
                "school_view_id": "sv_00000000000000000000000000000001",
                "school_id": "sch_qizheng_001",
                "subject_entity_id": "as_qizheng_000001",
                "conflict_group_id": "cg_00000000000000000000000000000001",
                "changes_current_judgment": True,
            }
        ],
        "correction_request_revision_ids": [],
        "rework_impact_report_revision_id": None,
        "unresolved_count": 0,
    }


def make_valid_candidate_set():
    return {
        "schema_version": "0.1.0-draft",
        "technique_id": "qizheng",
        "source_id": "src_qizheng_ed01",
        "edition_part_artifact_id": "art_00000000000000000000000000000001",
        "evidence_level": "offset_level",
        "span_layer": "structural",
        "source_channels": {"default": {"main": "text"}},
        "assertions": [
            {
                "assertion_id": "as_qizheng_000001",
                "proposition_id": "pr_qizheng_000001",
                "proposition": "命宫在子",
                "relation": "supports",
                "evidence": [
                    {
                        "source_span_id": "ss_qizheng_ed01_p0001_s01",
                        "start_offset": 10,
                        "end_offset": 20,
                        "quote": "命宫在子",
                        "quote_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                    }
                ],
                "conditions": [],
                "exceptions": [],
                "concept_refs": ["co_qizheng_000001"],
                "school_ids": ["sch_qizheng_001"],
                "layer": "general",
                "content_status": "machine_extracted",
                "origin": {"lane": "main", "item_index": 0},
            }
        ],
        "patterns": [
            {
                "pattern_id": "pat_qizheng_000001",
                "name": "子宫命格",
                "assertion_ids": ["as_qizheng_000001"],
                "evidence": [],
                "interpretation": "基本格局",
                "interpretation_status": "captured",
                "recognition_rule_status": "not_captured",
                "content_status": "machine_extracted",
                "origin": {"lane": "main", "item_index": 0},
            }
        ],
        "school_views": [
            {
                "school_view_id": "sv_00000000000000000000000000000001",
                "school_id": "sch_qizheng_001",
                "subject_entity_id": "as_qizheng_000001",
                "claim_refs": ["as_qizheng_000001"],
                "conflict_group_id": "cg_00000000000000000000000000000001",
                "changes_current_judgment": True,
                "source_refs": [
                    {
                        "source_id": "src_qizheng_ed01",
                        "source_span_id": "ss_qizheng_ed01_p0001_s01",
                    }
                ],
                "evidence": [],
                "content_status": "machine_extracted",
                "origin": {"lane": "main", "item_index": 0},
            }
        ],
        "concept_mentions": [
            {
                "surface": "命宫",
                "concept_ref": "co_qizheng_000001",
                "evidence": [],
                "content_status": "machine_extracted",
                "origin": {"lane": "main", "item_index": 0},
            }
        ],
        "new_concept_candidates": [],
        "rejected": [],
        "disputes": [],
        "counts": {
            "assertions": 1,
            "patterns": 1,
            "school_views": 1,
            "concept_mentions": 1,
            "new_concept_candidates": 0,
            "rejected": 0,
            "disputes": 0,
        },
    }


def make_valid_snapshot_knowledge():
    k = empty_snapshot_knowledge("qizheng", {"pat_qizheng": [1, 100]})
    k["patterns"].append({
        "pattern_id": "pat_qizheng_000001",
        "name": "子宫命格",
        "aliases": [],
        "concept_id": None,
        "rules": [],
        "assertion_ids": ["as_qizheng_000001"],
        "school_view_ids": ["sv_00000000000000000000000000000001"],
        "recognition_rule_status": "not_captured",
        "provenance": [],
    })
    k["assertions"].append({
        "assertion_id": "as_qizheng_000001",
        "subject_entity_id": "pat_qizheng_000001",
        "source_id": "src_qizheng_ed01",
        "proposition": "命宫在子",
        "collation_key": None,
        "text_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "source_span_ids": ["ss_qizheng_ed01_p0001_s01"],
        "evidence": [
            {
                "source_span_id": "ss_qizheng_ed01_p0001_s01",
                "start_offset": 10,
                "end_offset": 20,
                "quote_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            }
        ],
        "school_view_ids": ["sv_00000000000000000000000000000001"],
        "content_status": "expert_verified",
    })
    k["school_views"].append({
        "school_view_id": "sv_00000000000000000000000000000001",
        "school_id": "sch_qizheng_001",
        "subject_entity_id": "as_qizheng_000001",
        "conflict_group_id": "cg_00000000000000000000000000000001",
        "source_conflict_group_id": "cg_00000000000000000000000000000001",
        "claim_refs": ["as_qizheng_000001"],
        "changes_current_judgment": True,
        "content_status": "expert_verified",
    })
    k["conflict_groups"].append({
        "conflict_group_id": "cg_00000000000000000000000000000001",
        "member_school_view_ids": ["sv_00000000000000000000000000000001"],
        "first_layer_display": True,
        "resolutions": [],
    })
    k["id_allocation"] = {"pat_qizheng": 1}
    return k


class TestModel(unittest.TestCase):
    def test_valid_reviewed_package_passes(self):
        pkg = make_valid_reviewed_package()
        res = validate_reviewed_package(pkg)
        self.assertIn("doc", res)
        self.assertEqual(res["reviewed_edition_revision_id"], pkg["reviewed_edition_revision_id"])

    def test_reviewed_package_unresolved_nonzero_refused(self):
        pkg = make_valid_reviewed_package()
        pkg["unresolved_count"] = 2
        with self.assertRaises(AssemblyRefused) as ctx:
            validate_reviewed_package(pkg)
        self.assertEqual(ctx.exception.code, "SCH_001")
        self.assertIn("未解决", str(ctx.exception))

    def test_valid_reviewed_edition_passes(self):
        ed = make_valid_reviewed_edition()
        res = validate_reviewed_edition(ed)
        self.assertEqual(res["edition_part_artifact_id"], ed["edition_part_artifact_id"])
        self.assertEqual(res["candidate_package_revision_id"], ed["candidate_package_revision_id"])
        self.assertIn("as_qizheng_000001", res["approved_index"])
        self.assertIn("as_qizheng_000001", res["hashes"])

    def test_reviewed_edition_missing_top_level_key_SCH_001(self):
        ed = make_valid_reviewed_edition()
        del ed["candidate_set_revision_id"]
        with self.assertRaises(SchemaViolation) as ctx:
            validate_reviewed_edition(ed)
        self.assertEqual(ctx.exception.code, "SCH_001")

    def test_reviewed_edition_bad_entity_id_ID_001(self):
        ed = make_valid_reviewed_edition()
        ed["approved"][0]["entity_id"] = "bad_pat_id"
        with self.assertRaises(InvalidIdentifier) as ctx:
            validate_reviewed_edition(ed)
        self.assertEqual(ctx.exception.code, "ID_001")

    def test_reviewed_edition_duplicate_entity_across_approved_rejected_ID_002(self):
        ed = make_valid_reviewed_edition()
        ed["rejected"].append(copy.deepcopy(ed["approved"][0]))
        with self.assertRaises(DuplicateIdentifier) as ctx:
            validate_reviewed_edition(ed)
        self.assertEqual(ctx.exception.code, "ID_002")

    def test_evidence_link_entity_not_approved_or_rejected_REF_001(self):
        ed = make_valid_reviewed_edition()
        ed["evidence_links"][0]["entity_id"] = "as_qizheng_999999"
        with self.assertRaises(MissingReference) as ctx:
            validate_reviewed_edition(ed)
        self.assertEqual(ctx.exception.code, "REF_001")

    def test_school_view_subject_dangling_REF_001(self):
        ed = make_valid_reviewed_edition()
        ed["school_views"][0]["subject_entity_id"] = "as_qizheng_999999"
        with self.assertRaises(MissingReference) as ctx:
            validate_reviewed_edition(ed)
        self.assertEqual(ctx.exception.code, "REF_001")

    def test_valid_candidate_set_passes(self):
        cset = make_valid_candidate_set()
        res = validate_candidate_set(cset)
        self.assertEqual(res["technique_id"], "qizheng")
        self.assertEqual(res["work_key"], "qizheng")
        self.assertEqual(res["pattern_ids"], ["pat_qizheng_000001"])
        self.assertEqual(res["assertion_ids"], ["as_qizheng_000001"])
        self.assertEqual(res["assertion_to_patterns"]["as_qizheng_000001"], ["pat_qizheng_000001"])

    def test_candidate_set_dangling_pattern_assertion_ref_REF_001(self):
        cset = make_valid_candidate_set()
        cset["patterns"][0]["assertion_ids"] = ["as_qizheng_999999"]
        with self.assertRaises(MissingReference) as ctx:
            validate_candidate_set(cset)
        self.assertEqual(ctx.exception.code, "REF_001")

    def test_candidate_set_bad_content_status_SCH_002(self):
        cset = make_valid_candidate_set()
        cset["assertions"][0]["content_status"] = "unknown_status"
        with self.assertRaises(SchemaViolation) as ctx:
            validate_candidate_set(cset)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_candidate_set_pattern_id_always_issued_SCH_002(self):
        cset = make_valid_candidate_set()
        cset["patterns"][0]["pattern_id"] = None
        # 无 candidate_key 时拒绝 SCH_002
        with self.assertRaises(SchemaViolation) as ctx:
            validate_candidate_set(cset)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_candidate_set_school_view_dangling_subject_REF_001(self):
        cset = make_valid_candidate_set()
        cset["school_views"][0]["subject_entity_id"] = "as_qizheng_999999"
        with self.assertRaises(MissingReference) as ctx:
            validate_candidate_set(cset)
        self.assertEqual(ctx.exception.code, "REF_001")

    def test_candidate_set_school_view_claim_refs_dangling_REF_001(self):
        cset = make_valid_candidate_set()
        cset["school_views"][0]["claim_refs"] = ["as_qizheng_999999"]
        with self.assertRaises(MissingReference) as ctx:
            validate_candidate_set(cset)
        self.assertEqual(ctx.exception.code, "REF_001")

    def test_empty_snapshot_knowledge_shape(self):
        k = empty_snapshot_knowledge("qizheng", {"pat_qizheng": [1, 100]})
        self.assertEqual(k["technique_id"], "qizheng")
        self.assertEqual(k["id_range"], {"pat_qizheng": [1, 100]})
        self.assertEqual(k["allocated_pattern_ids"], [])
        self.assertEqual(k["retired_entity_ids"], [])
        self.assertEqual(k["relations"], [])
        # 自检应通过
        validate_snapshot_knowledge(k)

    def test_snapshot_unsorted_list_SCH_002(self):
        k = make_valid_snapshot_knowledge()
        k["patterns"].append({
            "pattern_id": "pat_qizheng_000000",
            "name": "前置命格",
            "aliases": [],
            "concept_id": None,
            "rules": [],
            "assertion_ids": [],
            "school_view_ids": [],
            "recognition_rule_status": "not_captured",
            "provenance": [],
        })
        # patterns 乱序（000001 在 000000 前面）
        with self.assertRaises(SchemaViolation) as ctx:
            validate_snapshot_knowledge(k)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_snapshot_retired_alive_ID_002(self):
        k = make_valid_snapshot_knowledge()
        k["retired_entity_ids"] = ["pat_qizheng_000001"]
        with self.assertRaises(DuplicateIdentifier) as ctx:
            validate_snapshot_knowledge(k)
        self.assertEqual(ctx.exception.code, "ID_002")

    def test_snapshot_allocation_below_max_SCH_002(self):
        k = make_valid_snapshot_knowledge()
        k["id_allocation"] = {"pat_qizheng": 0}  # 小于活对象最大号 1
        with self.assertRaises(SchemaViolation) as ctx:
            validate_snapshot_knowledge(k)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_snapshot_dangling_relation_REF_001(self):
        k = make_valid_snapshot_knowledge()
        k["relations"].append({
            "relation_key": "rel_01",
            "from_entity_id": "pat_qizheng_000001",
            "to_entity_id": "pat_qizheng_999999",
            "relation_kind": "attached",
        })
        with self.assertRaises(MissingReference) as ctx:
            validate_snapshot_knowledge(k)
        self.assertEqual(ctx.exception.code, "REF_001")

    def test_snapshot_pattern_with_content_status_SCH_002(self):
        k = make_valid_snapshot_knowledge()
        k["patterns"][0]["content_status"] = "expert_verified"
        with self.assertRaises(SchemaViolation) as ctx:
            validate_snapshot_knowledge(k)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_snapshot_id_range_and_allocation_list_shape_SCH_002(self):
        k = make_valid_snapshot_knowledge()
        k["id_range"] = {"pat_qizheng": [100, 50]}  # start > end
        with self.assertRaises(SchemaViolation) as ctx:
            validate_snapshot_knowledge(k)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_snapshot_allocated_id_outside_range_SCH_002(self):
        k = make_valid_snapshot_knowledge()
        k["allocated_pattern_ids"] = ["pat_qizheng_000999"]
        k["id_allocation"] = {"pat_qizheng": 999}
        # 999 超出 [1, 100]
        with self.assertRaises(SchemaViolation) as ctx:
            validate_snapshot_knowledge(k)
        self.assertEqual(ctx.exception.code, "SCH_002")


if __name__ == "__main__":
    unittest.main()
