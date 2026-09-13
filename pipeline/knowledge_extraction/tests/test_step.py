"""ACT 04 m4 assemble StepRun（run_m4）与 CLI 的集成测试（先红后绿）。

统一脚手架：tempfile → LedgerService → ingest(m1,m2) → run_m3 → register_technique_profile → 提交件。
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jsonschema
import yaml
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from pipeline.corpus_compiler.step import run_m3
from pipeline.knowledge_extraction import serialize
from pipeline.knowledge_extraction.adapters.registry import register_technique_profile
from pipeline.knowledge_extraction.errors import ExtractionRefused
from pipeline.knowledge_extraction.step import (
    DEFAULT_ID_RANGE,
    DEFAULT_REQUIRED_LANES,
    run_m4,
)
from pipeline.knowledge_extraction.submit import run_m4_submit
from pipeline.ledger.fixture_ingest import ingest
from pipeline.ledger.service import LedgerService

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
CANON_DIR = ROOT / "pipeline" / "schemas" / "shared" / "canon"
SCHEMA_DIR = ROOT / "openspec" / "schemas"
DATA = Path(__file__).resolve().parent / "data" / "appendix_a"

PRODUCER_MODULE = "fixture:mini_ed01"
PRODUCER_VERSION = "mini_ed01"


def _load_yaml(name):
    with open(DATA / name, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _validate_stage_package(package):
    schema = json.loads((SCHEMA_DIR / "stage_package.schema.json").read_text(encoding="utf-8"))
    ref = json.loads((SCHEMA_DIR / "artifact_ref.schema.json").read_text(encoding="utf-8"))
    registry = Registry().with_resource(
        "artifact_ref.schema.json",
        Resource.from_contents(ref, default_specification=DRAFT202012),
    )
    jsonschema.Draft202012Validator(schema, registry=registry).validate(package)


class RunM4TestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m4-step-test-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.root = Path(self._tmp) / "ledger"
        self.service = LedgerService(self.root)
        self.addCleanup(self.service.close)
        self.edition_part_id, self.m3 = self._ingest(self.service)
        self.profile_revision_id = register_technique_profile(
            self.service,
            self.m3["processing_run_id"],
            technique_id="qizheng",
            canon_dir=CANON_DIR,
        )

    def _ingest(self, service):
        summary = ingest(FIXTURE_DIR, service, stages=("m1", "m2"))
        edition_part_id = summary["edition_part_id"]
        return edition_part_id, run_m3(service, edition_part_id)

    def _new_ledger(self, register_profile=True):
        tmp = tempfile.mkdtemp(prefix="m4-step-aux-")
        self.addCleanup(shutil.rmtree, tmp, True)
        service = LedgerService(Path(tmp) / "ledger")
        self.addCleanup(service.close)
        edition_part_id, m3 = self._ingest(service)
        if register_profile:
            register_technique_profile(
                service, m3["processing_run_id"], technique_id="qizheng", canon_dir=CANON_DIR
            )
        return service, edition_part_id, m3, Path(tmp) / "ledger"

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

    def submit(self, service, edition_part_id, name):
        return run_m4_submit(
            service,
            edition_part_id,
            (DATA / name).read_bytes(),
            producer_module=PRODUCER_MODULE,
            producer_version=PRODUCER_VERSION,
        )

    def submit_doc(self, service, edition_part_id, doc):
        data = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False).encode("utf-8")
        return run_m4_submit(
            service,
            edition_part_id,
            data,
            producer_module=PRODUCER_MODULE,
            producer_version=PRODUCER_VERSION,
        )

    def no_dispute_submissions(self, service=None, edition_part_id=None):
        service = service or self.service
        edition_part_id = edition_part_id or self.edition_part_id
        self.submit(service, edition_part_id, "submission_assertion_a.yaml")
        twin = _load_yaml("submission_assertion_a.yaml")
        twin["lane"] = "b"
        self.submit_doc(service, edition_part_id, twin)
        self.submit(service, edition_part_id, "submission_concept_mention_a.yaml")

    def gold_dispute_submissions(self, service=None, edition_part_id=None):
        service = service or self.service
        edition_part_id = edition_part_id or self.edition_part_id
        self.submit(service, edition_part_id, "submission_assertion_a.yaml")
        self.submit(service, edition_part_id, "submission_assertion_b.yaml")
        self.submit(service, edition_part_id, "submission_concept_mention_a.yaml")

    def read_json(self, revision_id):
        row = self.service.get_revision(revision_id)
        return json.loads(self.service.objects.get(row["sha256"]).decode("utf-8"))

    def _closed_ledger(self, kind):
        """建一个已完成准备并已释放写锁的 Ledger（供 CLI 子进程使用）。"""
        tmp = tempfile.mkdtemp(prefix="m4-step-cli-")
        self.addCleanup(shutil.rmtree, tmp, True)
        root = Path(tmp) / "ledger"
        service = LedgerService(root)
        edition_part_id, _m3 = self._ingest(service)
        register_technique_profile(
            service, _m3["processing_run_id"], technique_id="qizheng", canon_dir=CANON_DIR
        )
        if kind == "no_dispute":
            self.no_dispute_submissions(service, edition_part_id)
        elif kind == "dispute":
            self.gold_dispute_submissions(service, edition_part_id)
        service.close()
        return root, edition_part_id

    def _cli(self, root, edition_part_id):
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pipeline.knowledge_extraction",
                "assemble",
                "--root",
                str(root),
                "--edition-part",
                edition_part_id,
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        lines = [line for line in proc.stdout.strip().splitlines() if line]
        return proc.returncode, lines


class RunM4Tests(RunM4TestBase):
    def test_run_m4_no_dispute_succeeds(self):
        self.no_dispute_submissions()
        summary = run_m4(self.service, self.edition_part_id)
        self.assertEqual(summary["status"], "succeeded")
        self.assertEqual(summary["counts"]["assertions"], 2)
        self.assertEqual(summary["counts"]["disputes"], 0)
        self.assertEqual(summary["counts"]["rejected"], 0)
        step = self.service.get_step_run(summary["step_run_id"])
        self.assertEqual(step["status"], "succeeded")

    def test_candidate_set_bytes_identical_across_two_ledgers(self):
        self.no_dispute_submissions()
        first = run_m4(self.service, self.edition_part_id)
        service2, edition_part_id2, _m3, _root = self._new_ledger()
        self.no_dispute_submissions(service2, edition_part_id2)
        second = run_m4(service2, edition_part_id2)
        self.assertEqual(first["candidate_sha256"], second["candidate_sha256"])

    def test_frozen_inputs_exact(self):
        self.no_dispute_submissions()
        summary = run_m4(self.service, self.edition_part_id)
        frozen = set(self.service._frozen_input_ids(summary["step_run_id"]))
        expected = {
            self.m3["package_revision_id"],
            self.m3["corpus_package_revision_id"],
            self.m3["spans_revision_id"],
            self.profile_revision_id,
        }
        for row in summary["submission_revision_ids"].values():
            expected.add(row)
        self.assertEqual(frozen, expected)
        self.assertEqual(len(frozen), 7)

    def test_five_checkpoints_lanes_reconcile_assemble_chained(self):
        self.no_dispute_submissions()
        summary = run_m4(self.service, self.edition_part_id)
        chain = self.service.list_checkpoints(self.edition_part_id, "m4")
        self.assertIsNone(chain[0]["prev_checkpoint_revision_id"])
        for previous, current in zip(chain, chain[1:]):
            self.assertEqual(
                current["prev_checkpoint_revision_id"], previous["artifact_revision_id"]
            )
        own = [
            row["content"]["completed_tasks"][0]["task_id"]
            for row in chain
            if row["content"]["step_run_id"] == summary["step_run_id"]
        ]
        self.assertEqual(
            own,
            [
                "lane_assertion_a",
                "lane_assertion_b",
                "lane_concept_mention_a",
                "reconcile",
                "assemble",
            ],
        )

    def test_stage_package_schema_lineage_counts(self):
        self.no_dispute_submissions()
        summary = run_m4(self.service, self.edition_part_id)
        package = self.read_json(summary["package_revision_id"])
        _validate_stage_package(package)
        m3_refs = [
            ref
            for ref in package["manifest"]["input_artifacts"]
            if ref["artifact_kind"] == "stage_package"
        ]
        self.assertEqual(len(m3_refs), 1)
        candidate_bytes = self.service.objects.get(
            self.service.get_revision(summary["candidate_set_revision_id"])["sha256"]
        )
        self.assertEqual(
            package["manifest"]["content_sha256"],
            serialize.sha256_hex(candidate_bytes),
        )
        candidate_set = self.read_json(summary["candidate_set_revision_id"])
        self.assertEqual(package["manifest"]["counts"], candidate_set["counts"])

    def test_config_records_gate_profile_id_range_required_lanes(self):
        self.no_dispute_submissions()
        summary = run_m4(self.service, self.edition_part_id)
        config = self.read_json(summary["configuration_revision_id"])
        self.assertEqual(config["gate_profile"], "thin_no_model")
        self.assertEqual(config["id_range"], DEFAULT_ID_RANGE)
        self.assertEqual(config["required_lanes"], DEFAULT_REQUIRED_LANES)
        self.assertEqual(config["term_layering"], "verify_only")
        self.assertEqual(config["task"], "assemble")

    def test_gold_dispute_returns_awaiting_human(self):
        self.gold_dispute_submissions()
        summary = run_m4(self.service, self.edition_part_id)
        self.assertEqual(summary["status"], "awaiting_human")
        self.assertEqual(summary["dispute_ids"], ["m4_d001"])
        self.assertTrue(summary["resume_token"])
        step = self.service.get_step_run(summary["step_run_id"])
        self.assertEqual(step["status"], "awaiting_human")
        queue = self.read_json(summary["dispute_queue_revision_id"])
        self.assertEqual([row["dispute_id"] for row in queue["disputes"]], ["m4_d001"])
        kinds = {
            row[0]
            for row in self.service.store.conn.execute(
                "SELECT a.artifact_type FROM artifact_revisions r "
                "JOIN artifacts a ON a.artifact_id = r.artifact_id "
                "WHERE r.step_run_id=?",
                (summary["step_run_id"],),
            ).fetchall()
        }
        self.assertNotIn("candidate_set", kinds)
        self.assertNotIn("stage_package", kinds)

    def test_missing_required_lane_refused_no_writes(self):
        self.submit(self.service, self.edition_part_id, "submission_assertion_a.yaml")
        before = self.counts()
        with self.assertRaises(ExtractionRefused) as ctx:
            run_m4(self.service, self.edition_part_id)
        self.assertIn("缺必需路", ctx.exception.message)
        self.assertEqual(self.counts(), before)

    def test_missing_profile_refused_no_writes(self):
        service, edition_part_id, _m3, _root = self._new_ledger(register_profile=False)
        self.submit(service, edition_part_id, "submission_assertion_a.yaml")
        before = (
            self.service.store.conn.execute("SELECT COUNT(*) FROM artifact_revisions").fetchone()[0],
            self.service.store.conn.execute("SELECT COUNT(*) FROM step_runs").fetchone()[0],
        )
        with self.assertRaises(ExtractionRefused):
            run_m4(service, edition_part_id)
        after = (
            self.service.store.conn.execute("SELECT COUNT(*) FROM artifact_revisions").fetchone()[0],
            self.service.store.conn.execute("SELECT COUNT(*) FROM step_runs").fetchone()[0],
        )
        self.assertEqual(before, after)

    def test_second_assemble_refused_after_sealed(self):
        self.no_dispute_submissions()
        run_m4(self.service, self.edition_part_id)
        before = self.counts()
        with self.assertRaises(ExtractionRefused) as ctx:
            run_m4(self.service, self.edition_part_id)
        self.assertIn("M4 已封存", ctx.exception.message)
        self.assertEqual(self.counts(), before)

    def test_spans_hash_mismatch_fails_input_contract(self):
        self.no_dispute_submissions()
        from pipeline.knowledge_extraction import step as step_module

        real = step_module.resolve_m4_inputs

        def swapped(reader, edition_part_id, **kwargs):
            inputs = real(reader, edition_part_id, **kwargs)
            inputs["spans_revision_id"], inputs["corpus_package_revision_id"] = (
                inputs["corpus_package_revision_id"],
                inputs["spans_revision_id"],
            )
            return inputs

        with mock.patch(
            "pipeline.knowledge_extraction.step.resolve_m4_inputs", side_effect=swapped
        ):
            summary = run_m4(self.service, self.edition_part_id)
        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["failed_check"], "input_contract")

    def test_gate_failure_fails_step_run(self):
        from pipeline.knowledge_extraction import assemble as assemble_module

        self.no_dispute_submissions()
        real = assemble_module.assemble_candidates

        def tampered(**kwargs):
            result = real(**kwargs)
            result["candidate_set"]["assertions"][0]["content_status"] = "expert_verified"
            result["candidate_bytes"] = serialize.canonical_json(result["candidate_set"])
            return result

        with mock.patch(
            "pipeline.knowledge_extraction.assemble.assemble_candidates", side_effect=tampered
        ):
            summary = run_m4(self.service, self.edition_part_id)
        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["failed_check"], "candidate_gate")

    def test_unexpected_exception_after_begin_is_internal(self):
        self.no_dispute_submissions()
        with mock.patch(
            "pipeline.knowledge_extraction.gate.evaluate_candidates",
            side_effect=RuntimeError("boom"),
        ):
            summary = run_m4(self.service, self.edition_part_id)
        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["failed_check"], "internal")

    def test_cli_exit_codes(self):
        root_ok, edition_part_id = self._closed_ledger("no_dispute")
        code, lines = self._cli(root_ok, edition_part_id)
        self.assertEqual(code, 0)
        self.assertTrue(lines[-1].startswith("M4 OK"))

        root_empty, edition_part_id2 = self._closed_ledger("empty")
        code2, lines2 = self._cli(root_empty, edition_part_id2)
        self.assertEqual(code2, 2)
        self.assertTrue(lines2[-1].startswith("M4 REFUSED"))

        root_dispute, edition_part_id3 = self._closed_ledger("dispute")
        code3, lines3 = self._cli(root_dispute, edition_part_id3)
        self.assertEqual(code3, 4)
        self.assertTrue(lines3[-1].startswith("M4 AWAITING_HUMAN"))


if __name__ == "__main__":
    unittest.main()
