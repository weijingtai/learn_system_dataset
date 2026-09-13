"""ACT 03 输入解析与 submit StepRun 的集成测试（先红后绿）。

统一脚手架：tempfile → LedgerService → ingest(m1,m2) → run_m3 → register_technique_profile。
"""

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.corpus_compiler.step import run_m3
from pipeline.knowledge_extraction import serialize
from pipeline.knowledge_extraction.adapters.registry import register_technique_profile
from pipeline.knowledge_extraction.errors import ExtractionRefused
from pipeline.knowledge_extraction.inputs import resolve_m3_outputs, resolve_m4_inputs
from pipeline.knowledge_extraction.submit import begin_m4_step_run, run_m4_submit
from pipeline.knowledge_extraction.submission import validate_submission
from pipeline.ledger import ids
from pipeline.ledger.errors import IllegalTransition, SchemaViolation
from pipeline.ledger.fixture_ingest import Fixture, ingest
from pipeline.ledger.service import LedgerService

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
CANON_DIR = ROOT / "pipeline" / "schemas" / "shared" / "canon"
DATA = Path(__file__).resolve().parent / "data" / "appendix_a"
FIXTURE_EDITION_PART = "art_000000000000000000000000000000e1"

PRODUCER_MODULE = "fixture:mini_ed01"
PRODUCER_VERSION = "mini_ed01"


def _load_yaml(name):
    with open(DATA / name, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


class SubmitTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m4-submit-test-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.service = LedgerService(Path(self._tmp) / "ledger")
        self.addCleanup(self.service.close)
        self.fixture = Fixture(FIXTURE_DIR)
        summary = ingest(FIXTURE_DIR, self.service, stages=("m1", "m2"))
        self.edition_part_id = summary["edition_part_id"]
        self.m3 = run_m3(self.service, self.edition_part_id)
        self.profile_revision_id = register_technique_profile(
            self.service,
            self.m3["processing_run_id"],
            technique_id="qizheng",
            canon_dir=CANON_DIR,
        )

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

    def submit(self, name, **overrides):
        params = {
            "producer_module": PRODUCER_MODULE,
            "producer_version": PRODUCER_VERSION,
        }
        params.update(overrides)
        return run_m4_submit(
            self.service, self.edition_part_id, (DATA / name).read_bytes(), **params
        )

    def submit_doc(self, doc, **overrides):
        data = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False).encode("utf-8")
        params = {
            "producer_module": PRODUCER_MODULE,
            "producer_version": PRODUCER_VERSION,
        }
        params.update(overrides)
        return run_m4_submit(self.service, self.edition_part_id, data, **params)

    def seal_m4(self):
        """测试替身：直接造一个 succeeded 的 m4 assemble StepRun（ACT 04 前用它验封存卫）。"""
        _, config = self.service.put_run_artifact(
            self.m3["processing_run_id"],
            "configuration",
            serialize.canonical_json(
                {
                    "stage": "m4",
                    "task": "assemble",
                    "tool": "pipeline.knowledge_extraction",
                    "tool_version": "0.1.0",
                }
            ),
            producer_module="pipeline.knowledge_extraction",
            producer_version="0.1.0",
        )
        step = begin_m4_step_run(
            self.service,
            self.edition_part_id,
            {
                "schema_version": "1.0.0",
                "processing_run_id": self.m3["processing_run_id"],
                "step_run_id": ids.new_id("step_run_id"),
                "input_artifact_ids": [],
                "technique_profile_id": "qizheng",
                "configuration_artifact_id": config,
            },
        )
        self.service.write_checkpoint(
            step,
            edition_part_id=self.edition_part_id,
            stage="m4",
            completed_tasks=[],
            human_decisions=[],
            pending_queue=[],
            next_pointer=None,
        )
        version = self.service.get_step_run(step)["status_version"]
        self.service.finish_step_run(
            step,
            {
                "schema_version": "1.0.0",
                "processing_run_id": self.m3["processing_run_id"],
                "step_run_id": step,
                "status_version": version + 1,
                "status": "succeeded",
                "output_artifact_ids": [],
                "validation_report_ids": [],
                "log_artifact_ids": [],
                "failure_artifact_ids": [],
            },
        )
        return step


class ResolveM3Tests(SubmitTestBase):
    def test_resolve_m3_outputs_after_run_m3(self):
        inputs = resolve_m3_outputs(self.service, self.edition_part_id)
        self.assertEqual(inputs["processing_run_id"], self.m3["processing_run_id"])
        self.assertEqual(inputs["m3_step_run_id"], self.m3["step_run_id"])
        self.assertEqual(inputs["spans_revision_id"], self.m3["spans_revision_id"])
        self.assertEqual(
            inputs["corpus_package_revision_id"], self.m3["corpus_package_revision_id"]
        )
        self.assertEqual(
            inputs["corpus_stage_package_revision_id"], self.m3["package_revision_id"]
        )
        self.assertEqual(inputs["technique_id"], "qizheng")

    def test_resolve_refuses_fixture_only_m3(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = LedgerService(Path(tmp) / "ledger")
            self.addCleanup(service.close)
            ingest(FIXTURE_DIR, service, stages=("m1", "m2", "m3"))
            with self.assertRaises(ExtractionRefused) as ctx:
                resolve_m3_outputs(service, FIXTURE_EDITION_PART)
            self.assertEqual(ctx.exception.code, "REF_001")
            self.assertIn("M3 未通过", ctx.exception.message)

    def test_resolve_refuses_without_m3(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = LedgerService(Path(tmp) / "ledger")
            self.addCleanup(service.close)
            ingest(FIXTURE_DIR, service, stages=("m1", "m2"))
            with self.assertRaises(ExtractionRefused) as ctx:
                resolve_m3_outputs(service, FIXTURE_EDITION_PART)
            self.assertIn("M3 未通过", ctx.exception.message)


class SubmitTests(SubmitTestBase):
    def test_submit_gold_assertion_a_succeeds(self):
        summary = self.submit("submission_assertion_a.yaml")
        self.assertEqual(summary["status"], "succeeded")
        self.assertEqual(summary["category"], "assertion")
        self.assertEqual(summary["lane"], "a")
        self.assertEqual(summary["channel"], "fixture_gold")
        frozen = self.service._frozen_input_ids(summary["step_run_id"])
        self.assertEqual(
            set(frozen),
            {self.m3["package_revision_id"], self.m3["spans_revision_id"]},
        )
        checkpoints = self.service.list_checkpoints(self.edition_part_id, "m4")
        self.assertEqual(len(checkpoints), 1)
        self.assertEqual(
            checkpoints[0]["content"]["completed_tasks"][0]["task_id"],
            "submit_assertion_a",
        )
        stored = self.service.get_revision(summary["submission_revision_id"])
        self.assertEqual(stored["status"], "sealed")
        self.assertEqual(
            self.service._artifact_type(summary["submission_revision_id"]),
            "candidate_submission",
        )
        expected = validate_submission(
            _load_yaml("submission_assertion_a.yaml"), technique_id="qizheng"
        )
        self.assertEqual(
            self.service.objects.get(stored["sha256"]), serialize.canonical_json(expected)
        )
        transforms = self.service.list_transformations(summary["step_run_id"])
        self.assertEqual([row["operation"] for row in transforms], ["register_submission"])

    def test_submit_lane_isolation(self):
        first = self.submit("submission_assertion_a.yaml")
        second = self.submit("submission_assertion_b.yaml")
        self.assertNotEqual(first["step_run_id"], second["step_run_id"])
        frozen = self.service._frozen_input_ids(second["step_run_id"])
        self.assertEqual(
            set(frozen),
            {self.m3["package_revision_id"], self.m3["spans_revision_id"]},
        )
        types = {self.service._artifact_type(rev) for rev in frozen}
        self.assertNotIn("candidate_submission", types)

    def test_duplicate_lane_refused_no_writes(self):
        self.submit("submission_assertion_a.yaml")
        before = self.counts()
        with self.assertRaises(ExtractionRefused):
            self.submit("submission_assertion_a.yaml")
        self.assertEqual(self.counts(), before)

    def test_model_adapter_channel_refused_no_writes(self):
        doc = _load_yaml("submission_assertion_a.yaml")
        doc["channel"] = "model_adapter"
        before = self.counts()
        with self.assertRaises(ExtractionRefused) as ctx:
            self.submit_doc(doc)
        self.assertIn("首切片不收", ctx.exception.message)
        self.assertEqual(self.counts(), before)

    def test_lane_c_refused_no_writes(self):
        doc = _load_yaml("submission_assertion_a.yaml")
        doc["lane"] = "c"
        before = self.counts()
        with self.assertRaises(ExtractionRefused) as ctx:
            self.submit_doc(doc)
        self.assertIn("首切片不收", ctx.exception.message)
        self.assertEqual(self.counts(), before)

    def test_shape_error_refused_before_begin(self):
        before = self.counts()
        with self.assertRaises(SchemaViolation):
            run_m4_submit(
                self.service,
                self.edition_part_id,
                b"[1, 2, 3]",
                producer_module=PRODUCER_MODULE,
                producer_version=PRODUCER_VERSION,
            )
        self.assertEqual(self.counts(), before)

    def test_submit_refused_after_m4_sealed(self):
        self.seal_m4()
        before = self.counts()
        with self.assertRaises(ExtractionRefused) as ctx:
            self.submit("submission_assertion_a.yaml")
        self.assertIn("M4 已封存", ctx.exception.message)
        self.assertEqual(self.counts(), before)

    def test_resolve_m4_inputs_lists_three_gold_submissions(self):
        self.submit("submission_assertion_a.yaml")
        self.submit("submission_assertion_b.yaml")
        self.submit("submission_concept_mention_a.yaml")
        inputs = resolve_m4_inputs(self.service, self.edition_part_id)
        self.assertEqual(
            set(inputs["submissions"]),
            {"assertion/a", "assertion/b", "concept_mention/a"},
        )
        for row in inputs["submissions"].values():
            self.assertEqual(row["channel"], "fixture_gold")
            self.assertTrue(row["revision_id"].startswith("rev_"))
            self.assertTrue(row["step_run_id"].startswith("srun_"))
        self.assertEqual(
            inputs["technique_profile_revision_id"], self.profile_revision_id
        )

    def test_resolve_m4_inputs_multiple_profiles_refused(self):
        register_technique_profile(
            self.service,
            self.m3["processing_run_id"],
            technique_id="qizheng",
            canon_dir=CANON_DIR,
        )
        with self.assertRaises(ExtractionRefused) as ctx:
            resolve_m4_inputs(self.service, self.edition_part_id)
        self.assertIn("需显式指定", ctx.exception.message)

    def test_submissions_chain_via_supersede_all_resolved(self):
        first = self.submit("submission_assertion_a.yaml")
        second = self.submit("submission_assertion_b.yaml")
        third = self.submit("submission_concept_mention_a.yaml")
        self.assertEqual(
            self.service.get_step_run(second["step_run_id"])["supersedes_step_run_id"],
            first["step_run_id"],
        )
        self.assertEqual(
            self.service.get_step_run(third["step_run_id"])["supersedes_step_run_id"],
            second["step_run_id"],
        )
        inputs = resolve_m4_inputs(self.service, self.edition_part_id)
        self.assertEqual(
            set(inputs["submissions"]),
            {"assertion/a", "assertion/b", "concept_mention/a"},
        )

    def test_later_m4_run_without_supersede_refused(self):
        self.submit("submission_assertion_a.yaml")
        _, config = self.service.put_run_artifact(
            self.m3["processing_run_id"],
            "configuration",
            serialize.canonical_json(
                {
                    "stage": "m4",
                    "task": "submit",
                    "category": "assertion",
                    "lane": "b",
                    "channel": "fixture_gold",
                    "tool": "pipeline.knowledge_extraction",
                    "tool_version": "0.1.0",
                }
            ),
            producer_module="pipeline.knowledge_extraction",
            producer_version="0.1.0",
        )
        later = self.service.begin_step_run(
            {
                "schema_version": "1.0.0",
                "processing_run_id": self.m3["processing_run_id"],
                "step_run_id": ids.new_id("step_run_id"),
                "input_artifact_ids": [],
                "technique_profile_id": "qizheng",
                "configuration_artifact_id": config,
            }
        )
        with self.assertRaises(IllegalTransition):
            self.service.write_checkpoint(
                later,
                edition_part_id=self.edition_part_id,
                stage="m4",
                completed_tasks=[],
                human_decisions=[],
                pending_queue=[],
                next_pointer=None,
            )


if __name__ == "__main__":
    unittest.main()
