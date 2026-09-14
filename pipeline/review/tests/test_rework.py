import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline.ledger.service import LedgerService
from pipeline.review.errors import ReviewRefused
from pipeline.review.rework import request_correction, run_rework_propagation
from pipeline.review.step import close_review, open_review, record_decision
from pipeline.review.testing.upstream_stub import (
    load_data,
    seed_corrected_corpus,
    seed_upstream,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"


class TestRework(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m6-rework-test-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.ledger_dir = Path(self._tmp) / "ledger"
        self.service = LedgerService(self.ledger_dir)
        self.addCleanup(self.service.close)
        self.seed_result = seed_upstream(self.service, FIXTURE_DIR)
        self.edition_part_id = self.seed_result["edition_part_id"]
        self.corrections = load_data("corrections")

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

    def _first_review(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        cr = request_correction(
            self.service,
            step_run_id,
            token,
            source_span_ids=list(self.corrections["correction_request"]["source_span_ids"]),
            description=self.corrections["correction_request"]["description"],
        )
        for d in load_data("m6_decisions")["decisions"]:
            record_decision(
                self.service,
                step_run_id,
                token,
                queue_item_id=d["queue_item_id"],
                verdict=d["verdict"],
                rationale=d["rationale"],
                modified_content=d.get("modified_content"),
            )
        close_review(self.service, step_run_id, token)
        return step_run_id, cr["correction_request_revision_id"]

    def _run_rework(self, corrections=None):
        first_step_run_id, cr_rev = self._first_review()
        seed_res = seed_corrected_corpus(
            self.service, self.edition_part_id, corrections or self.corrections
        )
        res = run_rework_propagation(
            self.service,
            self.edition_part_id,
            correction_request_revision_id=cr_rev,
            new_corpus_package_revision_id=seed_res["new_corpus_package_revision_id"],
        )
        return res, first_step_run_id, cr_rev, seed_res

    def _run_cli(self, *args):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        cmd = [
            sys.executable,
            "-m",
            "pipeline.review",
            "--root",
            str(self.ledger_dir),
            *args,
        ]
        return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(ROOT))

    # ------------------------------------------------------------ 用例
    def test_request_correction_is_human_event_with_checkpoint(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        cps_before = len(self.service.list_checkpoints(self.edition_part_id, "m6"))
        he_before = self.service.store.conn.execute(
            "SELECT count(*) FROM human_events"
        ).fetchone()[0]

        cr = request_correction(
            self.service,
            step_run_id,
            token,
            source_span_ids=["ss_sanche_ed01_p0003_s08"],
            description="修正宮為官",
        )

        self.assertEqual(
            set(cr.keys()), {"correction_request_revision_id", "checkpoint_revision_id"}
        )
        rev = self.service.get_revision(cr["correction_request_revision_id"])
        self.assertEqual(rev["status"], "sealed")
        art_row = self.service.store.conn.execute(
            "SELECT a.artifact_type FROM artifacts a "
            "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
            "WHERE r.artifact_revision_id = ?",
            (cr["correction_request_revision_id"],),
        ).fetchone()
        self.assertEqual(art_row[0], "human_event")

        doc = self._read_doc(cr["correction_request_revision_id"])
        self.assertEqual(
            set(doc.keys()),
            {
                "schema_version",
                "event_kind",
                "stage",
                "step_run_id",
                "source_span_ids",
                "description",
                "target_stage",
                "actor_ref",
            },
        )
        self.assertEqual(doc["schema_version"], "0.1.0-draft")
        self.assertEqual(doc["event_kind"], "correction_request")
        self.assertEqual(doc["stage"], "m6")
        self.assertEqual(doc["step_run_id"], step_run_id)
        self.assertEqual(doc["source_span_ids"], ["ss_sanche_ed01_p0003_s08"])
        self.assertEqual(doc["description"], "修正宮為官")
        self.assertEqual(doc["target_stage"], "m2")
        self.assertTrue(doc["actor_ref"])

        he_rows = self.service.store.conn.execute(
            "SELECT decision_type FROM human_events WHERE event_revision_id = ?",
            (cr["correction_request_revision_id"],),
        ).fetchall()
        self.assertEqual(len(he_rows), 1)
        self.assertIsNone(he_rows[0][0])
        he_after = self.service.store.conn.execute(
            "SELECT count(*) FROM human_events"
        ).fetchone()[0]
        self.assertEqual(he_after, he_before + 1)

        cps = self.service.list_checkpoints(self.edition_part_id, "m6")
        self.assertEqual(len(cps), cps_before + 1)
        self.assertEqual(cps[-1]["artifact_revision_id"], cr["checkpoint_revision_id"])
        self.assertEqual(
            cps[-1]["content"]["human_decisions"],
            [cr["correction_request_revision_id"]],
        )
        self.assertEqual(len(cps[-1]["content"]["pending_queue"]), 5)

    def test_request_correction_unknown_span_zero_writes(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        before = self._footprint()
        with self.assertRaises(ReviewRefused):
            request_correction(
                self.service,
                step_run_id,
                token,
                source_span_ids=["ss_sanche_ed01_p0099_s99"],
                description="未知 span",
            )
        self.assertEqual(before, self._footprint())

    def test_rework_counts_match_expected_review(self):
        res, _, _, _ = self._run_rework()
        self.assertEqual(res["status"], "succeeded")
        self.assertEqual(
            res["counts"], {"invalidated": 3, "carried_forward": 3, "needs_review": 3}
        )
        report = self._read_doc(res["rework_impact_report_revision_id"])
        exp = load_data("expected_review")["rework"]
        self.assertEqual(report["invalidated_count"], exp["invalidated_count"])
        self.assertEqual(report["carried_forward_count"], exp["carried_forward_count"])
        self.assertEqual(report["needs_review_count"], exp["needs_review_count"])
        self.assertEqual(report["valid_object_count"], exp["valid_object_count"])
        self.assertEqual(report["invalidated_ratio"], exp["invalidated_ratio"])
        self.assertEqual(report["changed_span_ids"], exp["changed_span_ids"])
        self.assertEqual(report["reachable_entity_ids"], exp["reachable_entity_ids"])
        self.assertEqual(report["warnings"], exp["warnings"])
        self.assertEqual(report["rework_round"], exp["rework_round"])

    def test_rework_report_lists_reachable_invalidated_objects(self):
        res, _, _, _ = self._run_rework()
        report = self._read_doc(res["rework_impact_report_revision_id"])
        invalidated = [x for x in report["invalidated"] if x["kind"] == "candidate"]
        self.assertEqual(len(invalidated), 3)
        self.assertEqual(
            sorted(x["entity_id"] for x in invalidated),
            report["reachable_entity_ids"],
        )
        self.assertEqual(len(res["invalidated"]), 3)
        self.assertEqual(len(res["carried_forward"]), 3)
        self.assertEqual(len(res["needs_review"]), 3)

    def test_rework_does_not_change_any_revision_status(self):
        self._run_rework()
        conn = self.service.store.conn
        n = conn.execute(
            "SELECT count(*) FROM artifact_revisions WHERE status = 'invalidated'"
        ).fetchone()[0]
        self.assertEqual(n, 0)
        statuses = {r[0] for r in conn.execute("SELECT DISTINCT status FROM artifact_revisions").fetchall()}
        self.assertNotIn("invalidated", statuses)

    def test_rework_report_sealed_and_checkpoint_references_it(self):
        res, _, _, _ = self._run_rework()
        rev = self.service.get_revision(res["rework_impact_report_revision_id"])
        self.assertEqual(rev["status"], "sealed")
        cp_row = self.service.store.conn.execute(
            "SELECT rework_impact_report_revision_id FROM stage_checkpoints "
            "WHERE step_run_id = ? ORDER BY rowid DESC LIMIT 1",
            (res["step_run_id"],),
        ).fetchone()
        self.assertEqual(cp_row[0], res["rework_impact_report_revision_id"])
        latest = self.service.latest_checkpoint(self.edition_part_id, "m6")
        self.assertEqual(latest["artifact_revision_id"], res["checkpoint_revision_id"])
        self.assertEqual(
            latest["content"]["rework_impact_report_revision_id"],
            res["rework_impact_report_revision_id"],
        )

    def test_rework_transformation_human_events_include_correction_request(self):
        res, _, cr_rev, _ = self._run_rework()
        rows = self.service.store.conn.execute(
            "SELECT event_revision_id FROM transformation_human_events "
            "WHERE transformation_id = ?",
            (res["transformation_id"],),
        ).fetchall()
        self.assertEqual([r[0] for r in rows], [cr_rev])

    def test_rework_supersedes_first_review_chain(self):
        res, first_step_run_id, _, _ = self._run_rework()
        self.assertEqual(res["supersedes_step_run_id"], first_step_run_id)
        self.assertEqual(
            self.service.get_step_run(first_step_run_id)["status"], "succeeded"
        )
        new_step = self.service.get_step_run(res["step_run_id"])
        self.assertEqual(new_step["supersedes_step_run_id"], first_step_run_id)
        self.assertEqual(new_step["status"], "succeeded")

    def test_correction_scope_unchanged_span_fails(self):
        first_step_run_id, cr_rev = self._first_review()
        only_s05 = {
            "span_patches": [
                p for p in self.corrections["span_patches"] if p["span_id"].endswith("s05")
            ]
        }
        seed_res = seed_corrected_corpus(self.service, self.edition_part_id, only_s05)
        conn = self.service.store.conn
        before = conn.execute(
            "SELECT count(*) FROM artifacts WHERE artifact_type = 'rework_impact_report'"
        ).fetchone()[0]
        res = run_rework_propagation(
            self.service,
            self.edition_part_id,
            correction_request_revision_id=cr_rev,
            new_corpus_package_revision_id=seed_res["new_corpus_package_revision_id"],
        )
        self.assertEqual(res["status"], "failed")
        self.assertEqual(res["failed_check"], "correction_scope")
        after = conn.execute(
            "SELECT count(*) FROM artifacts WHERE artifact_type = 'rework_impact_report'"
        ).fetchone()[0]
        self.assertEqual(before, after)

    def test_rework_module_does_not_reference_invalidate_revision(self):
        source = (Path(__file__).resolve().parents[1] / "rework.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("invalidate_revision", source)

    def test_rework_refuses_without_succeeded_review_zero_writes(self):
        before = self._footprint()
        with self.assertRaises(ReviewRefused):
            run_rework_propagation(
                self.service,
                self.edition_part_id,
                correction_request_revision_id="rev_" + "0" * 32,
                new_corpus_package_revision_id="rev_" + "1" * 32,
            )
        self.assertEqual(before, self._footprint())

    def test_console_rework_line(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        self.service.close()

        res_correct = self._run_cli(
            "correct",
            "--step-run",
            step_run_id,
            "--resume-token",
            token,
            "--span",
            "ss_sanche_ed01_p0003_s08",
            "--description",
            "修正宮為官",
        )
        self.assertEqual(
            res_correct.returncode, 0, res_correct.stderr + res_correct.stdout
        )
        correction_lines = [
            l for l in res_correct.stdout.splitlines() if l.startswith("M6 CORRECTION")
        ]
        self.assertEqual(len(correction_lines), 1)
        cr_rev = correction_lines[0].split()[-1]

        service = LedgerService(self.ledger_dir)
        try:
            for d in load_data("m6_decisions")["decisions"]:
                record_decision(
                    service,
                    step_run_id,
                    token,
                    queue_item_id=d["queue_item_id"],
                    verdict=d["verdict"],
                    rationale=d["rationale"],
                    modified_content=d.get("modified_content"),
                )
            close_review(service, step_run_id, token)
            seed_res = seed_corrected_corpus(
                service, self.edition_part_id, self.corrections
            )
        finally:
            service.close()

        res_rework = self._run_cli(
            "rework",
            "--edition-part",
            self.edition_part_id,
            "--correction-request",
            cr_rev,
            "--new-corpus-package",
            seed_res["new_corpus_package_revision_id"],
        )
        self.assertEqual(
            res_rework.returncode, 0, res_rework.stderr + res_rework.stdout
        )
        lines = [
            l for l in res_rework.stdout.splitlines() if l.startswith("M6 REWORK")
        ]
        self.assertEqual(len(lines), 1)
        self.assertIn("invalidated=3 carried_forward=3 needs_review=3", lines[0])
        self.assertIn("warnings=rework_threshold_exceeded", lines[0])


if __name__ == "__main__":
    unittest.main()
