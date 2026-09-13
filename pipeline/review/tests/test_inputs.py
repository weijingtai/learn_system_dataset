import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline.ledger.errors import NotConsumable
from pipeline.ledger.service import LedgerService
from pipeline.review.errors import ReviewRefused
import pipeline.review.inputs
from pipeline.review.inputs import resolve_m6_inputs
from pipeline.review.testing.upstream_stub import seed_upstream, load_data

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"


class TestReviewInputs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m6-inputs-test-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.ledger_dir = Path(self._tmp) / "ledger"
        self.service = LedgerService(self.ledger_dir)
        self.addCleanup(self.service.close)
        self.seed_result = seed_upstream(self.service, FIXTURE_DIR)
        self.edition_part_id = self.seed_result["edition_part_id"]

    def test_seed_upstream_all_stages_succeeded(self):
        reader = self.service
        # Check m3, m4, m5 step runs all succeeded
        m3_run = reader.get_step_run(self.seed_result["m3_step_run_id"])
        self.assertEqual(m3_run["status"], "succeeded")
        m4_run = reader.get_step_run(self.seed_result["m4_step_run_id"])
        self.assertEqual(m4_run["status"], "succeeded")
        m5_run = reader.get_step_run(self.seed_result["m5_step_run_id"])
        self.assertEqual(m5_run["status"], "succeeded")

    def test_seed_candidates_four_objects_include_school_view(self):
        cands_data = load_data("m4_candidates")
        self.assertIn("assertions", cands_data)
        self.assertIn("school_views", cands_data)
        self.assertEqual(len(cands_data["assertions"]), 3)
        self.assertEqual(len(cands_data["school_views"]), 1)

    def test_resolve_returns_exact_revisions_and_objects(self):
        resolved = resolve_m6_inputs(self.service, self.edition_part_id)
        expected_keys = {
            "processing_run_id",
            "technique_id",
            "edition_part_id",
            "corpus_package_revision_id",
            "spans_revision_id",
            "corpus_stage_package_revision_id",
            "candidate_package_revision_id",
            "candidate_set_revision_id",
            "candidate_objects",
            "validation_package_revision_id",
            "gate_results_revision_id",
            "validation_package",
            "m3_step_run_id",
            "m4_step_run_id",
            "m5_step_run_id",
        }
        self.assertEqual(set(resolved.keys()), expected_keys)
        self.assertEqual(resolved["candidate_package_revision_id"], self.seed_result["candidate_package_revision_id"])
        self.assertEqual(resolved["candidate_set_revision_id"], self.seed_result["candidate_set_revision_id"])
        self.assertEqual(resolved["validation_package_revision_id"], self.seed_result["validation_package_revision_id"])
        self.assertEqual(len(resolved["candidate_objects"]), 4)
        kinds = [c["kind"] for c in resolved["candidate_objects"]]
        self.assertEqual(kinds.count("assertion"), 3)
        self.assertEqual(kinds.count("school_view"), 1)

    def test_resolve_writes_nothing(self):
        conn = self.service.store.conn
        rev_count_before = conn.execute("SELECT count(*) FROM artifact_revisions").fetchone()[0]
        step_count_before = conn.execute("SELECT count(*) FROM step_runs").fetchone()[0]
        audit_count_before = conn.execute("SELECT count(*) FROM audit_log").fetchone()[0]

        resolve_m6_inputs(self.service, self.edition_part_id)

        rev_count_after = conn.execute("SELECT count(*) FROM artifact_revisions").fetchone()[0]
        step_count_after = conn.execute("SELECT count(*) FROM step_runs").fetchone()[0]
        audit_count_after = conn.execute("SELECT count(*) FROM audit_log").fetchone()[0]

        self.assertEqual(rev_count_before, rev_count_after)
        self.assertEqual(step_count_before, step_count_after)
        self.assertEqual(audit_count_before, audit_count_after)

    def test_refuses_when_m5_missing(self):
        orig_latest = pipeline.review.inputs.latest_succeeded_step_run

        def fake_latest(reader, ep, stage):
            if stage == "m5":
                return None
            return orig_latest(reader, ep, stage)

        with mock.patch("pipeline.review.inputs.latest_succeeded_step_run", side_effect=fake_latest):
            with self.assertRaises(ReviewRefused):
                resolve_m6_inputs(self.service, self.edition_part_id)

    def test_refuses_when_m5_gate_not_passed(self):
        # Patch _read_doc to simulate validation_package gate.passed == False
        orig_read_doc = pipeline.review.inputs._read_doc

        def fake_read_doc(reader, rev_id):
            doc = orig_read_doc(reader, rev_id)
            if rev_id == self.seed_result["validation_package_revision_id"]:
                doc = dict(doc)
                doc["gate"] = {"passed": False}
            return doc

        with mock.patch("pipeline.review.inputs._read_doc", side_effect=fake_read_doc):
            with self.assertRaises(ReviewRefused):
                resolve_m6_inputs(self.service, self.edition_part_id)

    def test_refuses_when_candidate_package_not_bound_to_m3(self):
        orig_read_doc = pipeline.review.inputs._read_doc

        def fake_read_doc(reader, rev_id):
            doc = orig_read_doc(reader, rev_id)
            if rev_id == self.seed_result["candidate_package_revision_id"]:
                doc = dict(doc)
                doc["corpus_stage_package_revision_id"] = "rev_mismatch111111111111111111111111"
            return doc

        with mock.patch("pipeline.review.inputs._read_doc", side_effect=fake_read_doc):
            with self.assertRaises(ReviewRefused):
                resolve_m6_inputs(self.service, self.edition_part_id)

    def test_refuses_when_candidate_revision_not_sealed(self):
        cand_set_rev = self.seed_result["candidate_set_revision_id"]
        self.service.store.conn.execute(
            "UPDATE artifact_revisions SET status='invalidated' WHERE artifact_revision_id=?",
            (cand_set_rev,),
        )
        self.service.store.conn.commit()
        with self.assertRaises(NotConsumable):
            resolve_m6_inputs(self.service, self.edition_part_id)


if __name__ == "__main__":
    unittest.main()
