"""T19（T04 阶段 4 Q6）：M6 审核队列纳入 pattern。

M4 的 candidate_set 里有 patterns，M7 创世只收 M6 已审的 pattern；M6 过去只把 assertions 与
school_views 排进审核队列，pattern 永远到不了 reviewed_edition，真书因此编不出 entry。
本文件用审核台公开入口（open_review / record_decision / close_review）走一遍含 pattern 的 M6。
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline.ledger.service import LedgerService
from pipeline.review.step import close_review, open_review, record_decision
from pipeline.review.testing import upstream_stub

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
PATTERN_ID = "pat_qizheng_000001"
PATTERN_ITEM = "%s#review_source_fidelity" % PATTERN_ID


def _pattern(assertion_ids):
    """形状同 M4 candidate_set 的 pattern（证据经 assertion_ids 引到断言，自身无 evidence）。"""
    return {
        "pattern_id": PATTERN_ID,
        "name": "去官留煞",
        "assertion_ids": list(assertion_ids),
        "evidence": [],
        "interpretation": "测试宿主：引论断的格局",
        "interpretation_status": "captured",
        "recognition_rule_status": "not_captured",
        "content_status": "machine_extracted",
        "origin": {"lane": "a", "item_index": 0},
    }


class PatternReviewTests(unittest.TestCase):
    def _seed(self, assertion_ids=("as_qizheng_000001",)):
        tmp = tempfile.mkdtemp(prefix="m6-pattern-")
        self.addCleanup(shutil.rmtree, tmp, True)
        self.service = LedgerService(Path(tmp) / "ledger")
        self.addCleanup(self.service.close)
        original = upstream_stub.load_data

        def with_pattern(name):
            data = original(name)
            if name == "m4_candidates":
                data = dict(data, patterns=[_pattern(assertion_ids)])
            return data

        with mock.patch.object(upstream_stub, "load_data", side_effect=with_pattern):
            self.seeded = upstream_stub.seed_upstream(self.service, FIXTURE_DIR)
        self.edition_part_id = self.seeded["edition_part_id"]

    def _queue_item_ids(self, step_run_id):
        rows = self.service.list_step_run_revisions(step_run_id, artifact_type="review_queue")
        self.assertEqual(len(rows), 1)
        queue = json.loads(self.service.read_object(rows[0]["sha256"]).decode("utf-8"))
        return [item["queue_item_id"] for item in queue]

    def _review(self, pattern_verdict):
        """按夹具决定表审完原有队列项，pattern 项给 ``pattern_verdict``，然后 close。"""
        opened = open_review(self.service, self.edition_part_id)
        step_run_id, token = opened["step_run_id"], opened["resume_token"]
        for decision in upstream_stub.load_data("m6_decisions")["decisions"]:
            record_decision(
                self.service,
                step_run_id,
                token,
                queue_item_id=decision["queue_item_id"],
                verdict=decision["verdict"],
                rationale=decision["rationale"],
                modified_content=decision.get("modified_content"),
            )
        record_decision(
            self.service,
            step_run_id,
            token,
            queue_item_id=PATTERN_ITEM,
            verdict=pattern_verdict,
            rationale="测试宿主：pattern 审核",
        )
        return step_run_id, close_review(self.service, step_run_id, token)

    def _reviewed_edition(self, step_run_id):
        rows = self.service.list_step_run_revisions(
            step_run_id, artifact_type="reviewed_edition", status="sealed"
        )
        self.assertEqual(len(rows), 1)
        return json.loads(self.service.read_object(rows[0]["sha256"]).decode("utf-8"))

    def test_pattern_is_queued_for_source_fidelity(self):
        self._seed()
        opened = open_review(self.service, self.edition_part_id)
        self.assertIn(PATTERN_ITEM, self._queue_item_ids(opened["step_run_id"]))

    def test_accepted_pattern_reaches_reviewed_edition(self):
        self._seed()
        step_run_id, result = self._review("accept")
        self.assertEqual(result["status"], "succeeded", result)
        self.assertIn(PATTERN_ID, result["approved"])
        edition = self._reviewed_edition(step_run_id)
        approved = {item["entity_id"]: item for item in edition["approved"]}
        self.assertEqual(approved[PATTERN_ID]["kind"], "pattern")
        self.assertEqual(approved[PATTERN_ID]["content_status"], "expert_verified")
        self.assertIn(PATTERN_ITEM, {entry["queue_item_id"] for entry in edition["decisions"]})

    def test_rejected_pattern_is_listed_as_rejected(self):
        self._seed()
        step_run_id, result = self._review("reject")
        self.assertEqual(result["status"], "succeeded", result)
        self.assertIn(PATTERN_ID, result["rejected"])
        self.assertNotIn(PATTERN_ID, {item["entity_id"] for item in self._reviewed_edition(step_run_id)["approved"]})

    def test_m6_acceptance_independently_derives_the_pattern_queue_item(self):
        """M6 验收的「队列来自上游」独立推导也须含 pattern，否则把正确的队列判成不符。"""
        from pipeline.review import acceptance

        self._seed()
        opened = open_review(self.service, self.edition_part_id)
        errors = acceptance._check_queue_from_upstream(
            {"service": self.service, "first_open": opened, "seed": self.seeded}
        )
        self.assertEqual(errors, [])

    def test_approved_pattern_needs_an_approved_assertion(self):
        """evidence_closure 覆盖 pattern：已审 pattern 的证据经其 assertion_ids 闭合，至少一条须已审通过。"""
        self._seed(assertion_ids=("as_qizheng_000002",))  # 夹具决定表里该断言被 reject
        _step_run_id, result = self._review("accept")
        self.assertEqual(result["status"], "failed", result)
        self.assertIn("evidence_closure", json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
