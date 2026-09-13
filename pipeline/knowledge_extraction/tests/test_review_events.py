"""ACT 06 审核决定事件契约（review_events）的单测（先红后绿）。

P7：本文件全部为纯函数单测，输入为明确标注的合成事件（测试替身），不写 Ledger、
不建签发 StepRun，不代表任何真实专家决定。
"""

import unittest

from pipeline.knowledge_extraction.review_events import (
    ENTITY_KINDS,
    REVIEW_STAGE,
    build_review_decision,
    derive_content_status,
    required_decision_types,
    validate_review_decision,
)
from pipeline.ledger.errors import InvalidIdentifier, SchemaViolation

REV = "rev_" + "0" * 32
OTHER_REV = "rev_" + "1" * 32
PRUN = "prun_" + "0" * 32
SRUN = "srun_" + "0" * 32
ENTITY = "as_qizheng_000001"


def build(**overrides):
    params = dict(
        decision_type="review_source_fidelity",
        verdict="accept",
        entity_kind="assertion",
        entity_id=ENTITY,
        seen_artifact_revision_id=REV,
        processing_run_id=PRUN,
        step_run_id=SRUN,
        actor_ref="local_owner",
        rationale="逐字核对 page_001 题记与字框",
    )
    params.update(overrides)
    return build_review_decision(**params)


def derive(candidate, decisions):
    return derive_content_status(
        candidate,
        decisions,
        entity_kind="assertion",
        entity_id=ENTITY,
        candidate_revision_id=REV,
    )


class ReviewEventTests(unittest.TestCase):
    def test_build_valid_decision_roundtrip(self):
        doc = build()
        self.assertEqual(validate_review_decision(doc), doc)
        self.assertEqual(doc["event_kind"], "review_decision")
        self.assertEqual(doc["stage"], REVIEW_STAGE)
        self.assertEqual(doc["target"]["artifact_revision_id"], REV)
        self.assertEqual(doc["evidence_refs"], [])
        self.assertEqual(doc["consumption_level"], "INTERNAL_DEMO")

    def test_unknown_decision_type_SCH_002(self):
        with self.assertRaises(SchemaViolation) as ctx:
            build(decision_type="bogus")
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_unknown_verdict_SCH_002(self):
        with self.assertRaises(SchemaViolation) as ctx:
            build(verdict="bogus")
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_entity_prefix_kind_mismatch_ID_001(self):
        with self.assertRaises(InvalidIdentifier):
            build(entity_kind="assertion", entity_id="pat_qizheng_000001")

    def test_bad_seen_revision_ID_001(self):
        with self.assertRaises(InvalidIdentifier):
            build(seen_artifact_revision_id="bad")

    def test_empty_rationale_SCH_001(self):
        with self.assertRaises(SchemaViolation) as ctx:
            build(rationale="   ")
        self.assertEqual(ctx.exception.code, "SCH_001")

    def test_school_dispute_requires_school_attribution_type(self):
        with self.assertRaises(SchemaViolation) as ctx:
            build(verdict="school_dispute")
        self.assertEqual(ctx.exception.code, "SCH_002")
        self.assertEqual(
            build(
                decision_type="review_school_attribution",
                verdict="school_dispute",
            )["verdict"],
            "school_dispute",
        )

    def test_source_fidelity_accept_gives_expert_verified_when_no_school(self):
        candidate = {"content_status": "machine_extracted", "school_ids": []}
        self.assertEqual(derive(candidate, [build()]), "expert_verified")

    def test_school_ids_require_school_attribution(self):
        candidate = {
            "content_status": "machine_extracted",
            "school_ids": ["sch_qizheng_001"],
        }
        self.assertEqual(
            required_decision_types(candidate, entity_kind="assertion"),
            ("review_source_fidelity", "review_school_attribution"),
        )
        self.assertEqual(derive(candidate, [build()]), "machine_extracted")
        both = [build(), build(decision_type="review_school_attribution")]
        self.assertEqual(derive(candidate, both), "expert_verified")

    def test_reject_gives_deprecated_and_latest_wins(self):
        candidate = {"content_status": "machine_extracted", "school_ids": []}
        reject = build(verdict="reject")
        accept = build(verdict="accept")
        self.assertEqual(derive(candidate, [reject, accept]), "expert_verified")
        self.assertEqual(derive(candidate, [accept, reject]), "deprecated")

    def test_modify_or_request_evidence_gives_needs_expert(self):
        candidate = {"content_status": "machine_extracted", "school_ids": []}
        self.assertEqual(derive(candidate, [build(verdict="modify")]), "needs_expert")
        self.assertEqual(
            derive(candidate, [build(verdict="request_evidence")]), "needs_expert"
        )

    def test_decision_on_other_revision_ignored(self):
        candidate = {"content_status": "machine_extracted", "school_ids": []}
        other = build(seen_artifact_revision_id=OTHER_REV)
        self.assertEqual(derive(candidate, [other]), "machine_extracted")


if __name__ == "__main__":
    unittest.main()
