import json
import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline.ledger.service import LedgerService
from pipeline.review.errors import ReviewRefused
from pipeline.review.rework import (
    open_rework_review,
    request_correction,
    run_rework_propagation,
)
from pipeline.review.step import close_review, open_review, record_decision
from pipeline.review.testing.upstream_stub import (
    load_data,
    seed_corrected_corpus,
    seed_rerun_m4_m5,
    seed_upstream,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"


class TestReworkReview(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m6-rework-review-test-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.ledger_dir = Path(self._tmp) / "ledger"
        self.service = LedgerService(self.ledger_dir)
        self.addCleanup(self.service.close)
        self.seed_result = seed_upstream(self.service, FIXTURE_DIR)
        self.edition_part_id = self.seed_result["edition_part_id"]
        self.corrections = load_data("corrections")
        self.expected = load_data("expected_review")

    # ------------------------------------------------------------ 脚手架
    def _footprint(self):
        conn = self.service.store.conn
        return (
            conn.execute("SELECT count(*) FROM artifact_revisions").fetchone()[0],
            conn.execute("SELECT count(*) FROM human_events").fetchone()[0],
            conn.execute("SELECT count(*) FROM stage_checkpoints").fetchone()[0],
        )

    def _read_doc(self, revision_id):
        row = self.service.get_revision(revision_id)
        return json.loads(self.service.objects.get(row["sha256"]).decode("utf-8"))

    def _run_to_report(self):
        """首审 → CorrectionRequest → 5 决定 → 结审 → 修正语料 → 失效传播。"""
        open_res = open_review(self.service, self.edition_part_id)
        first_step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        cr = request_correction(
            self.service,
            first_step_run_id,
            token,
            source_span_ids=list(
                self.corrections["correction_request"]["source_span_ids"]
            ),
            description=self.corrections["correction_request"]["description"],
        )
        for d in load_data("m6_decisions")["decisions"]:
            record_decision(
                self.service,
                first_step_run_id,
                token,
                queue_item_id=d["queue_item_id"],
                verdict=d["verdict"],
                rationale=d["rationale"],
                modified_content=d.get("modified_content"),
            )
        first_close = close_review(self.service, first_step_run_id, token)

        seeded = seed_corrected_corpus(
            self.service, self.edition_part_id, self.corrections
        )
        propagation = run_rework_propagation(
            self.service,
            self.edition_part_id,
            correction_request_revision_id=cr["correction_request_revision_id"],
            new_corpus_package_revision_id=seeded["new_corpus_package_revision_id"],
        )
        return {
            "first_step_run_id": first_step_run_id,
            "correction_request_revision_id": cr["correction_request_revision_id"],
            "propagation": propagation,
            "report_revision_id": propagation["rework_impact_report_revision_id"],
            "first_reviewed_edition_revision_id": first_close[
                "reviewed_edition_revision_id"
            ],
        }

    def _seed_m4_m5(self, ctx):
        return seed_rerun_m4_m5(
            self.service,
            self.edition_part_id,
            rework_impact_report_revision_id=ctx["report_revision_id"],
        )

    def _open_rerun(self, acknowledge=True):
        ctx = self._run_to_report()
        ctx["seed_res"] = self._seed_m4_m5(ctx)
        ctx["open_res"] = open_rework_review(
            self.service,
            self.edition_part_id,
            rework_impact_report_revision_id=ctx["report_revision_id"],
            acknowledge_rework_warning=acknowledge,
        )
        return ctx

    def _decide_all_and_close(self, ctx):
        res = ctx["open_res"]
        step_run_id = res["step_run_id"]
        token = res["resume_token"]
        for item in res["queue"]:
            record_decision(
                self.service,
                step_run_id,
                token,
                queue_item_id=item["queue_item_id"],
                verdict="accept",
                rationale="复审通过",
            )
        ctx["close_res"] = close_review(self.service, step_run_id, token)
        return ctx["close_res"]

    # ------------------------------------------------------------ 用例
    def test_warning_requires_acknowledgement_zero_writes(self):
        ctx = self._run_to_report()
        self._seed_m4_m5(ctx)
        before = self._footprint()
        with self.assertRaises(ReviewRefused) as err:
            open_rework_review(
                self.service,
                self.edition_part_id,
                rework_impact_report_revision_id=ctx["report_revision_id"],
            )
        self.assertIn("rework_threshold_exceeded", str(err.exception))
        self.assertIn("需操作者确认", str(err.exception))
        self.assertEqual(before, self._footprint())

    def test_acknowledgement_recorded_as_human_event_with_checkpoint(self):
        ctx = self._open_rerun()
        ack_rev = ctx["open_res"]["acknowledgement_revision_id"]
        self.assertIsNotNone(ack_rev)
        rev = self.service.get_revision(ack_rev)
        self.assertEqual(rev["status"], "sealed")
        doc = self._read_doc(ack_rev)
        self.assertEqual(
            set(doc.keys()),
            {
                "schema_version",
                "event_kind",
                "stage",
                "step_run_id",
                "rework_impact_report_revision_id",
                "warnings",
                "actor_ref",
            },
        )
        self.assertEqual(doc["event_kind"], "rework_threshold_ack")
        self.assertEqual(doc["stage"], "m6")
        self.assertEqual(doc["step_run_id"], ctx["open_res"]["step_run_id"])
        self.assertEqual(doc["rework_impact_report_revision_id"], ctx["report_revision_id"])
        self.assertIn("rework_threshold_exceeded", doc["warnings"])
        he_row = self.service.store.conn.execute(
            "SELECT decision_type FROM human_events WHERE event_revision_id=?",
            (ack_rev,),
        ).fetchone()
        self.assertIsNotNone(he_row)
        self.assertIsNone(he_row[0])
        latest = self.service.latest_checkpoint(self.edition_part_id, "m6")
        self.assertIn(ack_rev, latest["content"]["human_decisions"])

    def test_rereview_queue_only_needs_review_items(self):
        ctx = self._open_rerun()
        queue_ids = [it["queue_item_id"] for it in ctx["open_res"]["queue"]]
        self.assertEqual(queue_ids, self.expected["rereview"]["queue"])

    def test_rereview_seen_revision_is_new_candidate_set_revision(self):
        ctx = self._open_rerun()
        new_rev = ctx["seed_res"]["candidate_set_revision_id"]
        for it in ctx["open_res"]["queue"]:
            self.assertEqual(it["seen_artifact_revision_id"], new_rev)

    def test_carried_decisions_not_rerecorded(self):
        ctx = self._open_rerun()
        run_events = {
            r[0]
            for r in self.service.store.conn.execute(
                "SELECT event_revision_id FROM human_events WHERE step_run_id=?",
                (ctx["open_res"]["step_run_id"],),
            ).fetchall()
        }
        report = self._read_doc(ctx["report_revision_id"])
        carried_revs = [
            c["revision_id"]
            for c in report["carried_forward"]
            if c["kind"] == "decision"
        ]
        self.assertEqual(len(carried_revs), 2)
        for rev in carried_revs:
            self.assertNotIn(rev, run_events)

    def test_carried_entry_seen_keeps_first_review_revision(self):
        ctx = self._open_rerun()
        close_res = self._decide_all_and_close(ctx)
        edition = self._read_doc(close_res["reviewed_edition_revision_id"])
        old_rev = self.seed_result["candidate_set_revision_id"]
        carried = [
            d for d in edition["decisions"] if d["standing"] == "carried_forward"
        ]
        self.assertEqual(len(carried), 2)
        for d in carried:
            self.assertEqual(d["seen_artifact_revision_id"], old_rev)

    def test_carried_entry_carried_to_is_new_revision_and_hash_matches(self):
        ctx = self._open_rerun()
        close_res = self._decide_all_and_close(ctx)
        self.assertEqual(close_res["status"], "succeeded")
        # Gate 的 decision_anchoring 逐条校验 carried_content_hash == 当前对象 content_hash
        self.assertTrue(close_res["gate"]["checks"]["decision_anchoring"]["passed"])
        edition = self._read_doc(close_res["reviewed_edition_revision_id"])
        new_rev = ctx["seed_res"]["candidate_set_revision_id"]
        carried = [
            d for d in edition["decisions"] if d["standing"] == "carried_forward"
        ]
        self.assertEqual(len(carried), 2)
        for d in carried:
            self.assertEqual(d["carried_to_revision_id"], new_rev)
            self.assertEqual(d["carried_from_revision_id"], d["decision_revision_id"])

    def test_close_rereview_standings_three_active_two_carried(self):
        ctx = self._open_rerun()
        close_res = self._decide_all_and_close(ctx)
        edition = self._read_doc(close_res["reviewed_edition_revision_id"])
        standings = [d["standing"] for d in edition["decisions"]]
        self.assertEqual(standings.count("active"), 3)
        self.assertEqual(standings.count("carried_forward"), 2)
        self.assertEqual(self.expected["rereview"]["active"], 3)
        self.assertEqual(self.expected["rereview"]["carried_forward"], 2)

    def test_rereview_edition_references_report_and_trigger(self):
        ctx = self._open_rerun()
        close_res = self._decide_all_and_close(ctx)
        edition = self._read_doc(close_res["reviewed_edition_revision_id"])
        self.assertEqual(edition["rework_impact_report_revision_id"], ctx["report_revision_id"])
        package = self._read_doc(close_res["reviewed_edition_package_revision_id"])
        self.assertEqual(package["rework_impact_report_revision_id"], ctx["report_revision_id"])
        carried = [
            d for d in edition["decisions"] if d["standing"] == "carried_forward"
        ]
        for d in carried:
            self.assertEqual(
                d["trigger_correction_request_id"],
                ctx["correction_request_revision_id"],
            )

    def test_rereview_carried_modify_approved_points_to_first_review_reviewed_candidate(self):
        ctx = self._open_rerun()
        close_res = self._decide_all_and_close(ctx)
        edition = self._read_doc(close_res["reviewed_edition_revision_id"])
        first_edition = self._read_doc(ctx["first_reviewed_edition_revision_id"])
        first_approved = {
            a["entity_id"]: a["artifact_revision_id"]
            for a in first_edition["approved"]
        }
        # 首审 as_qizheng_000003 为 modify → 其 approved 指向 reviewed_candidate（非候选集修订）
        self.assertNotEqual(
            first_approved["as_qizheng_000003"],
            self.seed_result["candidate_set_revision_id"],
        )
        modify_carried = [
            d
            for d in edition["decisions"]
            if d["standing"] == "carried_forward" and d["verdict"] == "modify"
        ]
        self.assertEqual(len(modify_carried), 1)
        decision = modify_carried[0]
        self.assertEqual(
            decision["modified_revision_id"],
            first_approved[decision["target_entity_id"]],
        )
        self.assertEqual(
            decision["current_target_revision_id"], decision["modified_revision_id"]
        )
        rework_approved = {
            a["entity_id"]: a["artifact_revision_id"] for a in edition["approved"]
        }
        self.assertEqual(
            rework_approved[decision["target_entity_id"]],
            decision["modified_revision_id"],
        )

    def test_rereview_transformation_includes_carried_and_ack_events(self):
        ctx = self._open_rerun()
        close_res = self._decide_all_and_close(ctx)
        recorded = {
            r[0]
            for r in self.service.store.conn.execute(
                "SELECT event_revision_id FROM transformation_human_events "
                "WHERE transformation_id=?",
                (close_res["transformation_id"],),
            ).fetchall()
        }
        report = self._read_doc(ctx["report_revision_id"])
        carried_revs = {
            c["revision_id"]
            for c in report["carried_forward"]
            if c["kind"] == "decision"
        }
        self.assertTrue(carried_revs.issubset(recorded))
        self.assertIn(ctx["open_res"]["acknowledgement_revision_id"], recorded)
        self.assertEqual(len(recorded), 6)  # 2 carried + 1 ack + 3 复审决定


if __name__ == "__main__":
    unittest.main()
