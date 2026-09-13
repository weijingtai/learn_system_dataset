"""ACT 05 类别裁决（record_category_ruling）与恢复（resume_m4）的集成测试（先红后绿）。"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from pipeline.corpus_compiler.step import run_m3
from pipeline.knowledge_extraction import assemble as assemble_module
from pipeline.knowledge_extraction.adapters.registry import register_technique_profile
from pipeline.knowledge_extraction.errors import ExtractionRefused
from pipeline.knowledge_extraction.step import (
    RULING_CHOICES,
    record_category_ruling,
    resume_m4,
    run_m4,
)
from pipeline.knowledge_extraction.submit import run_m4_submit
from pipeline.ledger.errors import InvalidResumeToken
from pipeline.ledger.fixture_ingest import ingest
from pipeline.ledger.service import LedgerService

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
CANON_DIR = ROOT / "pipeline" / "schemas" / "shared" / "canon"
DATA = Path(__file__).resolve().parent / "data" / "appendix_a"

PRODUCER_MODULE = "fixture:mini_ed01"
PRODUCER_VERSION = "mini_ed01"


class RulingTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m4-ruling-test-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.service = LedgerService(Path(self._tmp) / "ledger")
        self.addCleanup(self.service.close)
        self._prepare(self.service)

    def _ingest(self, service):
        summary = ingest(FIXTURE_DIR, service, stages=("m1", "m2"))
        edition_part_id = summary["edition_part_id"]
        return edition_part_id, run_m3(service, edition_part_id)

    def _submit(self, service, edition_part_id, name):
        return run_m4_submit(
            service,
            edition_part_id,
            (DATA / name).read_bytes(),
            producer_module=PRODUCER_MODULE,
            producer_version=PRODUCER_VERSION,
        )

    def _prepare(self, service):
        self.edition_part_id, self.m3 = self._ingest(service)
        register_technique_profile(
            service,
            self.m3["processing_run_id"],
            technique_id="qizheng",
            canon_dir=CANON_DIR,
        )
        self._submit(service, self.edition_part_id, "submission_assertion_a.yaml")
        self._submit(service, self.edition_part_id, "submission_assertion_b.yaml")
        self._submit(service, self.edition_part_id, "submission_concept_mention_a.yaml")

    def awaiting(self):
        summary = run_m4(self.service, self.edition_part_id)
        self.assertEqual(summary["status"], "awaiting_human")
        return summary

    def gold_ruling(self):
        return yaml.safe_load((DATA / "ruling_m4_d001.yaml").read_text(encoding="utf-8"))

    def count(self, table):
        return self.service.store.conn.execute(
            "SELECT COUNT(*) FROM %s" % table
        ).fetchone()[0]

    def counts(self):
        return (
            self.count("artifact_revisions"),
            self.count("step_runs"),
            self.count("audit_log"),
        )

    def read_json(self, revision_id):
        row = self.service.get_revision(revision_id)
        return json.loads(self.service.objects.get(row["sha256"]).decode("utf-8"))

    def own_revisions(self, step_run_id):
        return self.service.store.conn.execute(
            "SELECT r.artifact_revision_id, a.artifact_type FROM artifact_revisions r "
            "JOIN artifacts a ON a.artifact_id = r.artifact_id WHERE r.step_run_id=?",
            (step_run_id,),
        ).fetchall()


class RulingTests(RulingTestBase):
    def test_gold_full_path_succeeds(self):
        awaiting = self.awaiting()
        ruling = self.gold_ruling()
        result = record_category_ruling(
            self.service, awaiting["step_run_id"], awaiting["resume_token"], ruling
        )
        self.assertEqual(result["remaining_dispute_ids"], [])
        final = resume_m4(
            self.service, awaiting["step_run_id"], awaiting["resume_token"]
        )
        self.assertEqual(final["status"], "succeeded")
        candidate_set = self.read_json(final["candidate_set_revision_id"])
        self.assertEqual(
            [(row["assertion_id"], row["proposition"]) for row in candidate_set["assertions"]],
            [
                ("as_qizheng_000001", "宋錢如璧撰"),
                ("as_qizheng_000002", "三辰通載三十卷"),
            ],
        )
        ruled_out = [
            row
            for row in candidate_set["rejected"]
            if row["lane"] == "b" and row["item_index"] == 2 and row["reason_code"] == "TXT_001"
        ]
        self.assertEqual(len(ruled_out), 1)
        self.assertEqual(len(candidate_set["new_concept_candidates"]), 2)
        self.assertEqual(
            candidate_set["counts"],
            {
                "assertions": 2,
                "patterns": 0,
                "school_views": 0,
                "concept_mentions": 0,
                "new_concept_candidates": 2,
                "rejected": 1,
                "disputes": 1,
                "human_decisions": 1,
            },
        )

    def test_ruling_checkpoint_written_immediately(self):
        awaiting = self.awaiting()
        result = record_category_ruling(
            self.service, awaiting["step_run_id"], awaiting["resume_token"], self.gold_ruling()
        )
        chain = [
            row
            for row in self.service.list_checkpoints(self.edition_part_id, "m4")
            if row["content"]["step_run_id"] == awaiting["step_run_id"]
        ]
        latest = chain[-1]
        self.assertEqual(latest["content"]["completed_tasks"][0]["task_id"], "m4_d001")
        self.assertIn(result["event_revision_id"], latest["content"]["human_decisions"])

    def test_human_event_registered_with_null_decision_type(self):
        awaiting = self.awaiting()
        record_category_ruling(
            self.service, awaiting["step_run_id"], awaiting["resume_token"], self.gold_ruling()
        )
        rows = self.service.store.conn.execute(
            "SELECT decision_type FROM human_events WHERE step_run_id=?",
            (awaiting["step_run_id"],),
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0][0])

    def test_synthetic_ruling_event_retains_marker_not_expert_verified(self):
        awaiting = self.awaiting()
        result = record_category_ruling(
            self.service, awaiting["step_run_id"], awaiting["resume_token"], self.gold_ruling()
        )
        event = self.read_json(result["event_revision_id"])
        self.assertTrue(event["synthetic_fixture"])
        self.assertEqual(event["actor_ref"], "fixture:mini_ed01")
        final = resume_m4(
            self.service, awaiting["step_run_id"], awaiting["resume_token"]
        )
        for revision_id, _kind in self.own_revisions(awaiting["step_run_id"]):
            row = self.service.get_revision(revision_id)
            data = self.service.objects.get(row["sha256"])
            self.assertNotIn(b"expert_verified", data)
        self.assertEqual(final["status"], "succeeded")

    def test_transformation_carries_ruling_event_ids(self):
        awaiting = self.awaiting()
        result = record_category_ruling(
            self.service, awaiting["step_run_id"], awaiting["resume_token"], self.gold_ruling()
        )
        resume_m4(self.service, awaiting["step_run_id"], awaiting["resume_token"])
        rows = self.service.store.conn.execute(
            "SELECT t.id FROM transformations t WHERE t.step_run_id=? AND t.operation='extract_candidates'",
            (awaiting["step_run_id"],),
        ).fetchall()
        self.assertEqual(len(rows), 1)
        event_ids = [
            row[0]
            for row in self.service.store.conn.execute(
                "SELECT event_revision_id FROM transformation_human_events WHERE transformation_id=?",
                (rows[0][0],),
            ).fetchall()
        ]
        self.assertEqual(event_ids, [result["event_revision_id"]])

    def test_six_assemble_checkpoints_in_order(self):
        awaiting = self.awaiting()
        record_category_ruling(
            self.service, awaiting["step_run_id"], awaiting["resume_token"], self.gold_ruling()
        )
        resume_m4(self.service, awaiting["step_run_id"], awaiting["resume_token"])
        chain = [
            row
            for row in self.service.list_checkpoints(self.edition_part_id, "m4")
            if row["content"]["step_run_id"] == awaiting["step_run_id"]
        ]
        self.assertEqual(
            [row["content"]["completed_tasks"][0]["task_id"] for row in chain],
            [
                "lane_assertion_a",
                "lane_assertion_b",
                "lane_concept_mention_a",
                "reconcile",
                "m4_d001",
                "assemble",
            ],
        )

    def test_resume_refused_when_unruled_token_not_consumed(self):
        awaiting = self.awaiting()
        with self.assertRaises(ExtractionRefused):
            resume_m4(self.service, awaiting["step_run_id"], awaiting["resume_token"])
        self.assertEqual(
            self.service.get_step_run(awaiting["step_run_id"])["status"], "awaiting_human"
        )
        record_category_ruling(
            self.service, awaiting["step_run_id"], awaiting["resume_token"], self.gold_ruling()
        )
        final = resume_m4(self.service, awaiting["step_run_id"], awaiting["resume_token"])
        self.assertEqual(final["status"], "succeeded")

    def test_duplicate_ruling_refused_no_new_revisions(self):
        awaiting = self.awaiting()
        record_category_ruling(
            self.service, awaiting["step_run_id"], awaiting["resume_token"], self.gold_ruling()
        )
        before = self.counts()
        with self.assertRaises(ExtractionRefused):
            record_category_ruling(
                self.service, awaiting["step_run_id"], awaiting["resume_token"], self.gold_ruling()
            )
        self.assertEqual(self.counts(), before)

    def test_unknown_dispute_id_refused_no_new_revisions(self):
        awaiting = self.awaiting()
        ruling = self.gold_ruling()
        ruling["dispute_id"] = "m4_d999"
        before = self.counts()
        with self.assertRaises(ExtractionRefused):
            record_category_ruling(
                self.service, awaiting["step_run_id"], awaiting["resume_token"], ruling
            )
        self.assertEqual(self.counts(), before)

    def test_invalid_choice_refused(self):
        awaiting = self.awaiting()
        ruling = self.gold_ruling()
        ruling["choice"] = "z"
        with self.assertRaises(ExtractionRefused) as ctx:
            record_category_ruling(
                self.service, awaiting["step_run_id"], awaiting["resume_token"], ruling
            )
        self.assertEqual(ctx.exception.code, "SCH_002")
        self.assertEqual(
            self.service.get_step_run(awaiting["step_run_id"])["status"], "awaiting_human"
        )

    def test_resume_with_consumed_token_rejected_by_ledger(self):
        awaiting = self.awaiting()
        record_category_ruling(
            self.service, awaiting["step_run_id"], awaiting["resume_token"], self.gold_ruling()
        )
        resume_m4(self.service, awaiting["step_run_id"], awaiting["resume_token"])
        with self.assertRaises((ExtractionRefused, InvalidResumeToken)):
            resume_m4(self.service, awaiting["step_run_id"], awaiting["resume_token"])
        with self.assertRaises(InvalidResumeToken):
            self.service.resume(awaiting["step_run_id"], awaiting["resume_token"])

    def test_tampered_lane_set_fails_input_contract(self):
        awaiting = self.awaiting()
        record_category_ruling(
            self.service, awaiting["step_run_id"], awaiting["resume_token"], self.gold_ruling()
        )
        real = assemble_module.normalize_lane

        def tampered(submission, *, spans_doc, profile):
            lane = real(submission, spans_doc=spans_doc, profile=profile)
            lane["channel"] = "tampered"
            return lane

        with mock.patch(
            "pipeline.knowledge_extraction.assemble.normalize_lane", side_effect=tampered
        ):
            final = resume_m4(
                self.service, awaiting["step_run_id"], awaiting["resume_token"]
            )
        self.assertEqual(final["status"], "failed")
        self.assertEqual(final["failed_check"], "input_contract")

    def test_cli_rule_and_resume(self):
        tmp = tempfile.mkdtemp(prefix="m4-ruling-cli-")
        self.addCleanup(shutil.rmtree, tmp, True)
        root = Path(tmp) / "ledger"
        service = LedgerService(root)
        self._prepare(service)
        awaiting = run_m4(service, self.edition_part_id)
        self.assertEqual(awaiting["status"], "awaiting_human")
        step_run_id = awaiting["step_run_id"]
        token = awaiting["resume_token"]
        service.close()

        ruled = subprocess.run(
            [
                sys.executable,
                "-m",
                "pipeline.knowledge_extraction",
                "rule",
                "--root",
                str(root),
                "--step-run",
                step_run_id,
                "--token",
                token,
                "--from",
                str(DATA / "ruling_m4_d001.yaml"),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(ruled.returncode, 0)
        self.assertTrue(
            ruled.stdout.strip().splitlines()[-1].startswith("M4 RULED m4_d001")
        )

        resumed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pipeline.knowledge_extraction",
                "resume",
                "--root",
                str(root),
                "--step-run",
                step_run_id,
                "--token",
                token,
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(resumed.returncode, 0)
        self.assertTrue(resumed.stdout.strip().splitlines()[-1].startswith("M4 OK"))


if __name__ == "__main__":
    unittest.main()
