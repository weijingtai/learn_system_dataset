"""TODO.md T02：M8 验收的 mentions / knowledge_chain / graph_projection / identity_migration 判据必须看实际产出。

此前这些判据无条件输出 BLOCKED（acceptance.py 原 638、660、692、728 行），理由是写死的常量，
将来即使 M8 真的产出了子包，判据也不会变。本文件用构造的「产出事实」证明结论随事实变化：
- 没产出 → BLOCKED，理由里写出实测到的子包清单
- 产出了但内容校验尚未实现 → FAIL（不许悄悄判 PASS）
- 声称 compiled 却没有子包 → FAIL
"""

import unittest

from pipeline.dataset_compiler import acceptance

BASE_PACKS = {"evidence_map_pack": "rev_e", "source_asset_pack": "rev_s"}


def facts(**overrides):
    base = {
        "packs": dict(BASE_PACKS),
        "knowledge_chain": "not_compiled",
        "input_types": ["corpus_spans", "stage_package"],
        "mentions": None,
    }
    base.update(overrides)
    return base


class MentionsMappingTest(unittest.TestCase):
    def test_absent_is_blocked_with_observed_packs(self):
        name, status, detail = acceptance._check_mentions_mapping(facts())
        self.assertEqual((name, status), ("mentions_mapping", "BLOCKED"))
        self.assertIn("evidence_map_pack", detail)
        self.assertIn("实测", detail)

    def test_mentions_present_is_not_silently_passed(self):
        _, status, detail = acceptance._check_mentions_mapping(
            facts(mentions=[{"concept_id": "co_x", "span_id": "sp_1"}])
        )
        self.assertEqual(status, "FAIL")
        self.assertIn("尚未实现", detail)

    def test_search_index_pack_present_is_not_silently_passed(self):
        packs = dict(BASE_PACKS, search_index_pack="rev_i")
        _, status, _ = acceptance._check_mentions_mapping(facts(packs=packs))
        self.assertEqual(status, "FAIL")


class KnowledgeChainTest(unittest.TestCase):
    def test_not_compiled_without_snapshot_is_blocked_and_says_so(self):
        _, status, detail = acceptance._check_knowledge_chain(facts())
        self.assertEqual(status, "BLOCKED")
        self.assertIn("not_compiled", detail)
        self.assertIn("不含 M7 Snapshot", detail)

    def test_snapshot_input_is_reported_as_present(self):
        _, status, detail = acceptance._check_knowledge_chain(
            facts(input_types=["canonical_snapshot", "corpus_spans"])
        )
        self.assertEqual(status, "BLOCKED")
        self.assertIn("含 M7 Snapshot", detail)
        self.assertNotIn("不含 M7 Snapshot", detail)

    def test_compiled_without_pack_fails(self):
        _, status, detail = acceptance._check_knowledge_chain(facts(knowledge_chain="compiled"))
        self.assertEqual(status, "FAIL")
        self.assertIn("没有 knowledge_data_pack", detail)

    def test_pack_present_is_not_silently_passed(self):
        packs = dict(BASE_PACKS, knowledge_data_pack="rev_k")
        _, status, detail = acceptance._check_knowledge_chain(facts(knowledge_chain="compiled", packs=packs))
        self.assertEqual(status, "FAIL")
        self.assertIn("尚未实现", detail)


class SubpackProducedTest(unittest.TestCase):
    CASES = (
        ("graph_projection", "graph_projection_pack", "T05d"),
        ("identity_migration", "identity_migration_map", "T05e"),
    )

    def test_absent_is_blocked_with_observed_packs(self):
        for name, key, todo in self.CASES:
            with self.subTest(name=name):
                got_name, status, detail = acceptance._check_subpack_produced(name, facts(), key, todo, "原因")
                self.assertEqual((got_name, status), (name, "BLOCKED"))
                self.assertIn("实测发布包无 %s" % key, detail)
                self.assertIn(todo, detail)

    def test_present_is_not_silently_passed(self):
        for name, key, todo in self.CASES:
            with self.subTest(name=name):
                packs = dict(BASE_PACKS, **{key: "rev_x"})
                _, status, detail = acceptance._check_subpack_produced(name, facts(packs=packs), key, todo, "原因")
                self.assertEqual(status, "FAIL")
                self.assertIn("尚未实现", detail)


class NoHardcodedVerdictTest(unittest.TestCase):
    def test_old_unconditional_constants_are_gone(self):
        self.assertFalse(hasattr(acceptance, "MENTIONS_BLOCKED"))
        self.assertFalse(hasattr(acceptance, "KNOWLEDGE_CHAIN_BLOCKED"))


if __name__ == "__main__":
    unittest.main()
