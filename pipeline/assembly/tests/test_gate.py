"""M7 创世 Gate 单元测试与篡改矩阵（spec §15, §20.5, act/g0-03）。"""

import ast
import copy
import os
import unittest

from pipeline.assembly.gate import evaluate_genesis
from pipeline.assembly.genesis import assemble_genesis, propose_genesis
from pipeline.assembly.tests.test_genesis import make_genesis_inputs


class TestGate(unittest.TestCase):
    def setUp(self):
        self.cset, self.ed = make_genesis_inputs()
        self.prop = propose_genesis(self.cset, self.ed)
        self.res = assemble_genesis(
            self.cset,
            self.ed,
            self.prop["proposals"],
            id_range={"pattern": [1, 100]},
        )
        self.base_knowledge = copy.deepcopy(self.res["knowledge"])

    def test_genesis_all_checks_pass(self):
        res = evaluate_genesis(
            candidate_set=self.cset,
            reviewed_edition=self.ed,
            knowledge=self.base_knowledge,
        )
        self.assertTrue(res["passed"])
        expected_checks = [
            "schema_and_ids",
            "identity_preserved",
            "allocation_monotonic",
            "provenance_complete",
            "view_objects_unaltered",
            "no_silent_fold",
            "first_layer_display",
            "maturity_not_synthesized",
            "decisions_consistent",
            "genesis_only",
        ]
        self.assertEqual(list(res["checks"].keys()), expected_checks)
        for name, chk in res["checks"].items():
            self.assertTrue(chk["passed"], "Check %s failed: %s" % (name, chk.get("detail")))

    def test_gate_does_not_import_genesis(self):
        gate_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gate.py")
        with open(gate_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename="gate.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn("genesis", alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.assertNotIn("genesis", node.module)
                for alias in node.names:
                    self.assertNotIn("genesis", alias.name)

    def test_tamper_drop_approved_assertion(self):
        k = copy.deepcopy(self.base_knowledge)
        k["assertions"] = []
        res = evaluate_genesis(
            candidate_set=self.cset,
            reviewed_edition=self.ed,
            knowledge=k,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["provenance_complete"]["passed"])

    def test_tamper_duplicate_allocated_id(self):
        k = copy.deepcopy(self.base_knowledge)
        k["allocated_pattern_ids"] = ["pat_qizheng_000010", "pat_qizheng_000010"]
        res = evaluate_genesis(
            candidate_set=self.cset,
            reviewed_edition=self.ed,
            knowledge=k,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["allocation_monotonic"]["passed"])

    def test_tamper_allocated_below_candidate_max(self):
        k = copy.deepcopy(self.base_knowledge)
        k["id_allocation"]["pat_qizheng"] = 0
        res = evaluate_genesis(
            candidate_set=self.cset,
            reviewed_edition=self.ed,
            knowledge=k,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["allocation_monotonic"]["passed"])

    def test_tamper_allocated_outside_id_range(self):
        k = copy.deepcopy(self.base_knowledge)
        k["allocated_pattern_ids"] = ["pat_qizheng_000999"]
        k["id_allocation"]["pat_qizheng"] = 999
        res = evaluate_genesis(
            candidate_set=self.cset,
            reviewed_edition=self.ed,
            knowledge=k,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["allocation_monotonic"]["passed"])

    def test_tamper_revive_retired_id(self):
        k = copy.deepcopy(self.base_knowledge)
        k["retired_entity_ids"] = ["pat_qizheng_000099"]
        res = evaluate_genesis(
            candidate_set=self.cset,
            reviewed_edition=self.ed,
            knowledge=k,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["identity_preserved"]["passed"])

    def test_tamper_relations_nonempty(self):
        k = copy.deepcopy(self.base_knowledge)
        k["relations"] = [
            {
                "relation_key": "rel_01",
                "from_entity_id": "pat_qizheng_000001",
                "to_entity_id": "pat_qizheng_000001",
                "relation_kind": "attached",
            }
        ]
        res = evaluate_genesis(
            candidate_set=self.cset,
            reviewed_edition=self.ed,
            knowledge=k,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["genesis_only"]["passed"])

    def test_tamper_drop_school_view(self):
        k = copy.deepcopy(self.base_knowledge)
        k["school_views"] = []
        k["conflict_groups"] = []
        res = evaluate_genesis(
            candidate_set=self.cset,
            reviewed_edition=self.ed,
            knowledge=k,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["no_silent_fold"]["passed"])

    def test_tamper_first_layer_display_false(self):
        k = copy.deepcopy(self.base_knowledge)
        k["conflict_groups"][0]["first_layer_display"] = False
        res = evaluate_genesis(
            candidate_set=self.cset,
            reviewed_edition=self.ed,
            knowledge=k,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["first_layer_display"]["passed"])

    def test_tamper_synthesized_content_status(self):
        k = copy.deepcopy(self.base_knowledge)
        k["assertions"][0]["content_status"] = "machine_extracted"  # 原本 approved 是 expert_verified
        res = evaluate_genesis(
            candidate_set=self.cset,
            reviewed_edition=self.ed,
            knowledge=k,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["maturity_not_synthesized"]["passed"])

    def test_tamper_proposition_changed(self):
        k = copy.deepcopy(self.base_knowledge)
        k["assertions"][0]["proposition"] = "命宫在丑"  # 原本是 命宫在子
        res = evaluate_genesis(
            candidate_set=self.cset,
            reviewed_edition=self.ed,
            knowledge=k,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["view_objects_unaltered"]["passed"])

    def test_tamper_meta_base_revision_set(self):
        k = copy.deepcopy(self.base_knowledge)
        if "meta" not in k:
            k["meta"] = {}
        k["meta"]["base_snapshot_revision_id"] = "rev_00000000000000000000000000000099"
        res = evaluate_genesis(
            candidate_set=self.cset,
            reviewed_edition=self.ed,
            knowledge=k,
        )
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["genesis_only"]["passed"])


if __name__ == "__main__":
    unittest.main()
