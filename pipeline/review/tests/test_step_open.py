import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline.ledger.errors import InvalidIdentifier, MissingReference
from pipeline.ledger.service import LedgerService
import pipeline.review.inputs
from pipeline.review.errors import ReviewRefused
from pipeline.review.step import open_review, record_decision, recover_review
from pipeline.review.testing.upstream_stub import seed_upstream, load_data

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"


class TestStepOpen(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m6-step-open-test-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.ledger_dir = Path(self._tmp) / "ledger"
        self.service = LedgerService(self.ledger_dir)
        self.addCleanup(self.service.close)
        self.seed_result = seed_upstream(self.service, FIXTURE_DIR)
        self.edition_part_id = self.seed_result["edition_part_id"]

    def test_open_review_awaiting_human_with_token(self):
        res = open_review(self.service, self.edition_part_id)
        self.assertEqual(res["status"], "awaiting_human")
        self.assertTrue(res["resume_token"])
        step = self.service.get_step_run(res["step_run_id"])
        self.assertEqual(step["status"], "awaiting_human")

    def test_open_frozen_inputs_exact_seven(self):
        res = open_review(self.service, self.edition_part_id)
        self.assertEqual(len(res["frozen_input_revision_ids"]), 7)

    def test_open_queue_five_items_from_required_decision_types(self):
        res = open_review(self.service, self.edition_part_id)
        self.assertEqual(len(res["queue"]), 5)
        item_ids = [item["queue_item_id"] for item in res["queue"]]
        self.assertIn("as_qizheng_000001#review_source_fidelity", item_ids)
        self.assertIn("as_qizheng_000002#review_source_fidelity", item_ids)
        self.assertIn("as_qizheng_000003#review_source_fidelity", item_ids)
        self.assertIn("sv_00000000000000000000000000000001#review_source_fidelity", item_ids)
        self.assertIn("sv_00000000000000000000000000000001#review_school_attribution", item_ids)

    def test_open_queue_sealed_and_first_checkpoint(self):
        res = open_review(self.service, self.edition_part_id)
        queue_rev = res["queue_revision_id"]
        rev_row = self.service.get_revision(queue_rev)
        self.assertEqual(rev_row["status"], "sealed")
        cp = self.service.latest_checkpoint(self.edition_part_id, "m6")
        self.assertIsNotNone(cp)
        self.assertEqual(cp["artifact_revision_id"], res["checkpoint_revision_id"])
        self.assertEqual(len(cp["content"]["human_decisions"]), 0)
        self.assertEqual(len(cp["content"]["pending_queue"]), 5)

    def test_open_refuses_without_upstream_zero_writes(self):
        tmp = tempfile.mkdtemp(prefix="m6-empty-ledger-")
        self.addCleanup(shutil.rmtree, tmp, True)
        empty_service = LedgerService(Path(tmp) / "ledger")
        self.addCleanup(empty_service.close)
        with self.assertRaises(Exception):
            open_review(empty_service, self.edition_part_id)

    def test_open_input_contract_failure_fails_step_run(self):
        # Patch input reading to simulate quote_sha256 mismatch
        orig_read = pipeline.review.inputs._read_doc

        def fake_read(reader, rev_id):
            doc = orig_read(reader, rev_id)
            if doc and "assertions" in doc:
                doc = dict(doc)
                assertions = [dict(a) for a in doc["assertions"]]
                assertions[0]["evidence"] = [dict(e) for e in assertions[0]["evidence"]]
                assertions[0]["evidence"][0]["quote_sha256"] = "bad_hash_111111111111111111111111"
                doc["assertions"] = assertions
            return doc

        with mock.patch("pipeline.review.inputs._read_doc", side_effect=fake_read):
            res = open_review(self.service, self.edition_part_id)
            self.assertEqual(res["status"], "failed")
            self.assertEqual(res["failed_check"], "input_contract")

    def test_five_decisions_five_human_events_with_decision_type(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        decisions_data = load_data("m6_decisions")["decisions"]
        for d in decisions_data:
            rec_res = record_decision(
                self.service,
                step_run_id,
                token,
                queue_item_id=d["queue_item_id"],
                verdict=d["verdict"],
                rationale=d["rationale"],
                modified_content=d.get("modified_content"),
            )
            self.assertIsNotNone(rec_res["decision_revision_id"])

        events = self.service.store.conn.execute(
            "SELECT event_revision_id, decision_type FROM human_events WHERE step_run_id=?",
            (step_run_id,),
        ).fetchall()
        self.assertEqual(len(events), 5)
        decision_types = {e[1] for e in events}
        self.assertIn("review_source_fidelity", decision_types)
        self.assertIn("review_school_attribution", decision_types)

    def test_decision_event_matches_review_events_contract(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        rec_res = record_decision(
            self.service,
            step_run_id,
            token,
            queue_item_id="as_qizheng_000001#review_source_fidelity",
            verdict="accept",
            rationale="来源忠实",
        )
        ev_row = self.service.get_revision(rec_res["decision_revision_id"])
        ev_data = json.loads(self.service.objects.get(ev_row["sha256"]).decode("utf-8"))
        self.assertEqual(ev_data["event_kind"], "review_decision")
        self.assertEqual(ev_data["stage"], "m6")
        self.assertEqual(ev_data["decision_type"], "review_source_fidelity")
        self.assertEqual(ev_data["target"]["entity_id"], "as_qizheng_000001")
        self.assertNotIn("standing", ev_data)

    def test_checkpoint_per_decision_chain_and_cumulative_lists(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        decisions_data = load_data("m6_decisions")["decisions"]

        # Initial checkpoint has 0 human decisions
        cps = self.service.list_checkpoints(self.edition_part_id, "m6")
        self.assertEqual(len(cps), 1)

        for i, d in enumerate(decisions_data, 1):
            rec_res = record_decision(
                self.service,
                step_run_id,
                token,
                queue_item_id=d["queue_item_id"],
                verdict=d["verdict"],
                rationale=d["rationale"],
                modified_content=d.get("modified_content"),
            )
            cp = self.service.latest_checkpoint(self.edition_part_id, "m6")
            self.assertEqual(len(cp["content"]["human_decisions"]), i)
            self.assertEqual(len(cp["content"]["pending_queue"]), 5 - i)

        cps = self.service.list_checkpoints(self.edition_part_id, "m6")
        self.assertEqual(len(cps), 6)

    def test_modify_seals_reviewed_candidate_and_entry_carries_modified_revision(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        rec_res = record_decision(
            self.service,
            step_run_id,
            token,
            queue_item_id="as_qizheng_000003#review_source_fidelity",
            verdict="modify",
            rationale="修正文字",
            modified_content={"text": "（宋）錢如璧撰"},
        )
        self.assertIsNotNone(rec_res["modified_revision_id"])
        mod_row = self.service.get_revision(rec_res["modified_revision_id"])
        self.assertEqual(mod_row["status"], "sealed")

    def test_redecide_request_evidence_then_accept_keeps_history(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        # First request evidence
        r1 = record_decision(
            self.service,
            step_run_id,
            token,
            queue_item_id="as_qizheng_000001#review_source_fidelity",
            verdict="request_evidence",
            rationale="需要更多证据",
        )
        self.assertEqual(r1["remaining"], 5)
        # Then accept
        r2 = record_decision(
            self.service,
            step_run_id,
            token,
            queue_item_id="as_qizheng_000001#review_source_fidelity",
            verdict="accept",
            rationale="已补充证据",
        )
        self.assertEqual(r2["remaining"], 4)
        cp = self.service.latest_checkpoint(self.edition_part_id, "m6")
        self.assertEqual(len(cp["content"]["human_decisions"]), 2)

    def test_wrong_token_zero_writes(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        conn = self.service.store.conn
        rev_count_before = conn.execute("SELECT count(*) FROM artifact_revisions").fetchone()[0]
        with self.assertRaises(Exception):
            record_decision(
                self.service,
                step_run_id,
                "wrong_token",
                queue_item_id="as_qizheng_000001#review_source_fidelity",
                verdict="accept",
                rationale="ok",
            )
        rev_count_after = conn.execute("SELECT count(*) FROM artifact_revisions").fetchone()[0]
        self.assertEqual(rev_count_before, rev_count_after)

    def test_unknown_item_zero_writes(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        conn = self.service.store.conn
        rev_count_before = conn.execute("SELECT count(*) FROM artifact_revisions").fetchone()[0]
        with self.assertRaises(ReviewRefused):
            record_decision(
                self.service,
                step_run_id,
                token,
                queue_item_id="unknown_entity#review_source_fidelity",
                verdict="accept",
                rationale="ok",
            )
        rev_count_after = conn.execute("SELECT count(*) FROM artifact_revisions").fetchone()[0]
        self.assertEqual(rev_count_before, rev_count_after)

    def test_recover_after_checkpoint_write_crash(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]

        # Record 1st decision
        record_decision(
            self.service,
            step_run_id,
            token,
            queue_item_id="as_qizheng_000001#review_source_fidelity",
            verdict="accept",
            rationale="ok",
        )

        # Record 2nd decision, but simulate crash during write_checkpoint
        orig_wc = self.service.write_checkpoint

        def crash_wc(*args, **kwargs):
            raise RuntimeError("simulated crash during write_checkpoint")

        with mock.patch.object(self.service, "write_checkpoint", side_effect=crash_wc):
            with self.assertRaises(RuntimeError):
                record_decision(
                    self.service,
                    step_run_id,
                    token,
                    queue_item_id="as_qizheng_000002#review_source_fidelity",
                    verdict="reject",
                    rationale="no",
                )

        # Now recover
        rec_res = recover_review(self.service, self.edition_part_id, reason="crash_recovery")
        self.assertEqual(rec_res["supersedes_step_run_id"], step_run_id)
        self.assertEqual(len(rec_res["carried_decision_revision_ids"]), 2)
        self.assertEqual(len(rec_res["replayed_pending"]), 3)

    def test_recover_old_run_still_awaiting_human(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        recover_review(self.service, self.edition_part_id, reason="test_status")
        old_step = self.service.get_step_run(step_run_id)
        self.assertEqual(old_step["status"], "awaiting_human")


if __name__ == "__main__":
    unittest.main()
