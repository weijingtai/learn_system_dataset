"""ACT impl-01/01：Artifact / StepRun 状态机与枚举（规格 §8.2）的单元测试。

先写本文件，运行 `python -m unittest discover -s pipeline/ledger/tests -t .`
因 `pipeline.ledger.states` / `pipeline.ledger.errors` 尚不存在而全红。
"""

import unittest

from pipeline.ledger import states
from pipeline.ledger.errors import IllegalTransition, SchemaViolation


class TestStates(unittest.TestCase):
    """覆盖 §8.2：两张迁移表穷举、终态无出边、表外取值 SCH_002、枚举闭集。"""

    def test_artifact_transition_table_exact(self):
        expected = {
            "draft": {"sealed", "quarantined"},
            "sealed": {"invalidated", "superseded"},
            "quarantined": {"superseded"},
            "invalidated": {"superseded"},
            "superseded": set(),
        }
        self.assertEqual(states.ARTIFACT_TRANSITIONS, expected)
        for cur in states.ARTIFACT_STATUS:
            for nxt in states.ARTIFACT_STATUS:
                if nxt in expected[cur]:
                    states.check_artifact_transition(cur, nxt)
                else:
                    with self.assertRaises(IllegalTransition):
                        states.check_artifact_transition(cur, nxt)

    def test_step_run_transition_table_exact(self):
        expected = {
            "running": {"awaiting_human", "suspended", "succeeded", "failed", "superseded"},
            "awaiting_human": {"running", "suspended", "failed", "superseded"},
            "suspended": {"running", "failed", "superseded"},
            "succeeded": set(),
            "failed": set(),
            "superseded": set(),
        }
        self.assertEqual(states.STEP_RUN_TRANSITIONS, expected)
        for cur in states.STEP_RUN_STATUS:
            for nxt in states.STEP_RUN_STATUS:
                if nxt in expected[cur]:
                    states.check_step_run_transition(cur, nxt)
                else:
                    with self.assertRaises(IllegalTransition):
                        states.check_step_run_transition(cur, nxt)

    def test_terminal_states_have_no_exits(self):
        for status in states.TERMINAL_STEP_RUN:
            self.assertEqual(states.STEP_RUN_TRANSITIONS[status], set())
        self.assertEqual(states.ARTIFACT_TRANSITIONS["superseded"], set())

    def test_unknown_status_is_SCH_002(self):
        with self.assertRaises(SchemaViolation) as ctx:
            states.check_artifact_transition("ghost", "sealed")
        self.assertEqual(ctx.exception.code, "SCH_002")
        with self.assertRaises(SchemaViolation) as ctx2:
            states.check_step_run_transition("running", "ghost")
        self.assertEqual(ctx2.exception.code, "SCH_002")

    def test_enum_closed_sets_verbatim(self):
        self.assertEqual(
            states.ARTIFACT_STATUS,
            ("draft", "sealed", "quarantined", "invalidated", "superseded"),
        )
        self.assertEqual(
            states.STEP_RUN_STATUS,
            ("running", "awaiting_human", "suspended", "succeeded", "failed", "superseded"),
        )
        self.assertEqual(
            states.CONTENT_MATURITY,
            (
                "source_verified",
                "machine_extracted",
                "cross_model_reviewed",
                "disputed",
                "needs_expert",
                "expert_verified",
                "deprecated",
            ),
        )
        self.assertEqual(
            states.REVIEW_DECISION_TYPES,
            (
                "review_source_fidelity",
                "review_edition_collation",
                "review_school_attribution",
                "review_explanation_quality",
                "review_case_authenticity",
                "review_practical_validity",
                "review_safety",
                "review_rights",
            ),
        )


if __name__ == "__main__":
    unittest.main()
