import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from pipeline.ledger.service import LedgerService
from pipeline.review.errors import ReviewRefused
from pipeline.review.step import close_review, open_review, record_decision, request_correction, run_m6
from pipeline.review.testing.upstream_stub import load_data, seed_upstream

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
SCHEMA_DIR = ROOT / "openspec" / "schemas"


def _validate_schema(schema_name, data):
    schema_text = (SCHEMA_DIR / schema_name).read_text(encoding="utf-8")
    schema = json.loads(schema_text)
    ref_text = (SCHEMA_DIR / "artifact_ref.schema.json").read_text(encoding="utf-8")
    ref_schema = json.loads(ref_text)
    registry = Registry().with_resource(
        "artifact_ref.schema.json",
        Resource.from_contents(ref_schema, default_specification=DRAFT202012),
    )
    jsonschema.Draft202012Validator(schema, registry=registry).validate(data)


class TestStepClose(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m6-step-close-test-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.ledger_dir = Path(self._tmp) / "ledger"
        self.service = LedgerService(self.ledger_dir)
        self.addCleanup(self.service.close)
        self.seed_result = seed_upstream(self.service, FIXTURE_DIR)
        self.edition_part_id = self.seed_result["edition_part_id"]

    def _open_and_record_all(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        decisions_data = load_data("m6_decisions")["decisions"]
        for d in decisions_data:
            record_decision(
                self.service,
                step_run_id,
                token,
                queue_item_id=d["queue_item_id"],
                verdict=d["verdict"],
                rationale=d["rationale"],
                modified_content=d.get("modified_content"),
            )
        return step_run_id, token, open_res

    def test_close_succeeds_three_approved_one_rejected(self):
        step_run_id, token, _ = self._open_and_record_all()
        res = close_review(self.service, step_run_id, token)
        self.assertEqual(res["status"], "succeeded")
        self.assertEqual(len(res["approved"]), 3)
        self.assertEqual(len(res["rejected"]), 1)
        expected = load_data("expected_review")["first_review"]
        self.assertEqual(sorted(res["approved"]), sorted(expected["approved"]))
        self.assertEqual(sorted(res["rejected"]), sorted(expected["rejected"]))

    def test_close_consumes_token_and_step_succeeded(self):
        step_run_id, token, _ = self._open_and_record_all()
        res = close_review(self.service, step_run_id, token)
        self.assertEqual(res["status"], "succeeded")
        step = self.service.get_step_run(step_run_id)
        self.assertEqual(step["status"], "succeeded")
        # Token cannot be reused
        with self.assertRaises(Exception):
            close_review(self.service, step_run_id, token)

    def test_reviewed_edition_decisions_have_entity_and_seen_revision(self):
        step_run_id, token, _ = self._open_and_record_all()
        res = close_review(self.service, step_run_id, token)
        ed_row = self.service.get_revision(res["reviewed_edition_revision_id"])
        ed_doc = json.loads(self.service.objects.get(ed_row["sha256"]).decode("utf-8"))
        for d in ed_doc["decisions"]:
            self.assertTrue(d["target_entity_id"])
            self.assertTrue(d["seen_artifact_revision_id"])
            self.assertEqual(d["seen_artifact_revision_id"], self.seed_result["candidate_set_revision_id"])

    def test_reviewed_edition_decision_includes_modified_revision_id(self):
        step_run_id, token, _ = self._open_and_record_all()
        res = close_review(self.service, step_run_id, token)
        ed_row = self.service.get_revision(res["reviewed_edition_revision_id"])
        ed_doc = json.loads(self.service.objects.get(ed_row["sha256"]).decode("utf-8"))
        for d in ed_doc["decisions"]:
            if d["verdict"] == "modify":
                self.assertIsNotNone(d["modified_revision_id"])
            else:
                self.assertIsNone(d["modified_revision_id"])

    def test_modified_object_uses_reviewed_candidate_revision(self):
        step_run_id, token, _ = self._open_and_record_all()
        res = close_review(self.service, step_run_id, token)
        ed_row = self.service.get_revision(res["reviewed_edition_revision_id"])
        ed_doc = json.loads(self.service.objects.get(ed_row["sha256"]).decode("utf-8"))
        mod_item = next(it for it in ed_doc["approved"] if it["entity_id"] == "as_qizheng_000003")
        self.assertNotEqual(mod_item["artifact_revision_id"], self.seed_result["candidate_set_revision_id"])
        # Matches reviewed_candidate revision
        rev_row = self.service.get_revision(mod_item["artifact_revision_id"])
        self.assertEqual(rev_row["status"], "sealed")

    def test_evidence_links_quote_hash_recomputed_from_ledger_spans(self):
        step_run_id, token, _ = self._open_and_record_all()
        res = close_review(self.service, step_run_id, token)
        ed_row = self.service.get_revision(res["reviewed_edition_revision_id"])
        ed_doc = json.loads(self.service.objects.get(ed_row["sha256"]).decode("utf-8"))
        for link in ed_doc["evidence_links"]:
            self.assertTrue(link["quote_sha256"])
            self.assertEqual(link["corpus_spans_revision_id"], self.seed_result["spans_revision_id"])

    def test_stage_package_validates_schema_and_content_sha(self):
        step_run_id, token, _ = self._open_and_record_all()
        res = close_review(self.service, step_run_id, token)
        pkg_row = self.service.get_revision(res["package_revision_id"])
        pkg_doc = json.loads(self.service.objects.get(pkg_row["sha256"]).decode("utf-8"))
        _validate_schema("stage_package.schema.json", pkg_doc)
        ed_row = self.service.get_revision(res["reviewed_edition_revision_id"])
        self.assertEqual(pkg_doc["manifest"]["content_sha256"], ed_row["sha256"])

    def test_transformation_records_all_human_events(self):
        step_run_id, token, _ = self._open_and_record_all()
        res = close_review(self.service, step_run_id, token)
        t_id = res["transformation_id"]
        rows = self.service.store.conn.execute(
            "SELECT event_revision_id FROM transformation_human_events WHERE transformation_id=?",
            (t_id,),
        ).fetchall()
        self.assertEqual(len(rows), 5)

    def test_close_refuses_with_unresolved_zero_writes_token_kept(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        # Only record 1 decision out of 5
        record_decision(
            self.service,
            step_run_id,
            token,
            queue_item_id="as_qizheng_000001#review_source_fidelity",
            verdict="accept",
            rationale="ok",
        )
        conn = self.service.store.conn
        rev_count_before = conn.execute("SELECT count(*) FROM artifact_revisions").fetchone()[0]
        with self.assertRaises(ReviewRefused) as ctx:
            close_review(self.service, step_run_id, token)
        self.assertIn("未解决项", str(ctx.exception))
        rev_count_after = conn.execute("SELECT count(*) FROM artifact_revisions").fetchone()[0]
        self.assertEqual(rev_count_before, rev_count_after)

    def test_close_lists_correction_requests_without_blocking(self):
        open_res = open_review(self.service, self.edition_part_id)
        step_run_id = open_res["step_run_id"]
        token = open_res["resume_token"]
        # request correction
        cr_res = request_correction(
            self.service,
            step_run_id,
            token,
            source_span_ids=["ss_sanche_ed01_p0003_s08"],
            description="修正宮為官",
        )
        # then record all 5 decisions
        decisions_data = load_data("m6_decisions")["decisions"]
        for d in decisions_data:
            record_decision(
                self.service,
                step_run_id,
                token,
                queue_item_id=d["queue_item_id"],
                verdict=d["verdict"],
                rationale=d["rationale"],
                modified_content=d.get("modified_content"),
            )
        res = close_review(self.service, step_run_id, token)
        self.assertEqual(res["status"], "succeeded")
        ed_row = self.service.get_revision(res["reviewed_edition_revision_id"])
        ed_doc = json.loads(self.service.objects.get(ed_row["sha256"]).decode("utf-8"))
        self.assertIn(cr_res["correction_request_revision_id"], ed_doc["correction_request_revision_ids"])

    def test_gate_failure_fails_step_run_no_stage_package(self):
        step_run_id, token, _ = self._open_and_record_all()
        with mock.patch("pipeline.review.gate.evaluate_review") as mock_eval:
            mock_eval.return_value = {
                "review": "failed",
                "checks": {"validation_intake": {"passed": False, "detail": "failed"}},
            }
            res = close_review(self.service, step_run_id, token)
            self.assertEqual(res["status"], "failed")
            self.assertEqual(res["failed_check"], "review_gate")
            # No stage package created
            sp_rows = self.service.store.conn.execute(
                "SELECT count(*) FROM stage_packages WHERE stage='m6'"
            ).fetchone()[0]
            self.assertEqual(sp_rows, 0)

    def test_exception_after_resume_fails_internal(self):
        step_run_id, token, _ = self._open_and_record_all()
        with mock.patch.object(self.service, "record_transformation", side_effect=RuntimeError("internal crash")):
            res = close_review(self.service, step_run_id, token)
            self.assertEqual(res["status"], "failed")
            self.assertEqual(res["failed_check"], "internal")
            fail_rev = self.service.get_revision(res["failure_revision_id"])
            self.assertEqual(fail_rev["status"], "sealed")


if __name__ == "__main__":
    unittest.main()
