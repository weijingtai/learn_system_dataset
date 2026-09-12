"""ACT 04 单元测试：resolve_m5_inputs 与 build_context。

用例名与 act/04.yaml 的 tests 清单逐字一致（另含主 Agent 裁定的
``test_build_context_keys_match_fixture_context``）。测试只用 tempfile 目录。
"""

import copy
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.corpus_compiler.step import run_m3
from pipeline.ledger import ids
from pipeline.ledger.fixture_ingest import ingest
from pipeline.ledger.service import LedgerService
from pipeline.validation.context import build_context
from pipeline.validation.errors import ValidationRefused
from pipeline.validation.inputs import resolve_m5_inputs
from pipeline.validation.tests.helpers import fixture_context

FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "pipeline"
    / "corpus"
    / "_fixture"
    / "mini_ed01"
)
EDITION_PART = "art_000000000000000000000000000000e1"


def _chain(service):
    """真实链路：ingest(m1,m2) → run_m3，返回 m3 summary。"""
    ingest(FIXTURE, service, stages=("m1", "m2"))
    return run_m3(service, EDITION_PART)


def _processing_run_id(service):
    return service.store.conn.execute(
        "SELECT processing_run_id FROM processing_runs LIMIT 1"
    ).fetchone()[0]


def _fake_stage_run(service, stage, *, gate_profile="structural_only", succeed=True,
                    package=False):
    """构造一个 stage 的 StepRun（含 Checkpoint、可选 StagePackage），可成功或失败。"""
    prun = _processing_run_id(service)
    config = json.dumps(
        {
            "stage": stage,
            "tool": "pipeline.corpus_compiler",
            "tool_version": "0.1.0",
            "batch_size": 10,
            "gate_profile": gate_profile,
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    _, config_rev = service.put_run_artifact(
        prun, "configuration", config,
        producer_module="test", producer_version="test",
    )
    run = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": prun,
            "step_run_id": ids.new_id("step_run_id"),
            "input_artifact_ids": [],
            "technique_profile_id": "qizheng",
            "configuration_artifact_id": config_rev,
        }
    )
    _, dummy = service.put_artifact(
        run, "step_log", b"fake", producer_module="test", producer_version="test"
    )
    service.seal_revision(dummy)
    service.write_checkpoint(
        run,
        edition_part_id=EDITION_PART,
        stage=stage,
        completed_tasks=[
            {
                "task_id": "noop",
                "artifact_revision_id": dummy,
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )
    if package:
        pkg = copy.deepcopy(
            yaml.safe_load(
                (FIXTURE / "expected" / "m3.stage_package.yaml").read_text(
                    encoding="utf-8"
                )
            )
        )
        pkg["stage_package_id"] = ids.new_id("stage_package_id", stage="m3")
        pkg["artifact_revision_id"] = ids.new_id("artifact_revision_id")
        pkg["manifest"]["step_run_id"] = run
        service.register_stage_package(
            run,
            pkg,
            json.dumps(pkg, sort_keys=True, ensure_ascii=False).encode("utf-8"),
            stage_package_id=pkg["stage_package_id"],
            artifact_revision_id=pkg["artifact_revision_id"],
        )
        service.seal_revision(pkg["artifact_revision_id"])
    if succeed:
        version = service.get_step_run(run)["status_version"]
        service.finish_step_run(
            run,
            {
                "schema_version": "1.0.0",
                "processing_run_id": prun,
                "step_run_id": run,
                "status_version": version + 1,
                "status": "succeeded",
                "output_artifact_ids": [dummy],
                "validation_report_ids": [dummy],
                "log_artifact_ids": [dummy],
                "failure_artifact_ids": [],
            },
        )
    else:
        service.fail_step_run(run, [], "fake failure")
    return run


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m5-inputs-")
        self.service = LedgerService(Path(self._tmp) / "ledger")
        self.addCleanup(self.service.close)


class ResolveInputsTest(_Base):
    def test_resolve_returns_seventeen_sealed_revisions_with_roles(self):
        _chain(self.service)
        inputs = resolve_m5_inputs(self.service, EDITION_PART)
        frozen = inputs["frozen_revision_ids"]
        self.assertEqual(len(frozen), 17)
        self.assertEqual(len(set(frozen)), 17)
        for rev in frozen:
            self.assertEqual(self.service.get_revision(rev)["status"], "sealed")
        roles = inputs["revision_roles"]
        for role in (
            "m3_package", "corpus_package", "corpus_spans", "coverage_report",
            "validation_report", "configuration", "source_manifest",
            "ocr_page_set", "human_event",
        ):
            self.assertIn(role, roles)
        self.assertEqual(len(inputs["batch_revision_ids"]), 5)
        self.assertEqual(len(inputs["page_revision_ids"]), 3)

    def test_resolve_frozen_order_and_page_keys_match_manifest(self):
        _chain(self.service)
        inputs = resolve_m5_inputs(self.service, EDITION_PART)
        manifest = yaml.safe_load(
            (FIXTURE / "manifest.yaml").read_text(encoding="utf-8")
        )
        pages = manifest["edition_part"]["pages"]
        expected = [
            inputs["m3_package_revision_id"],
            inputs["corpus_package_revision_id"],
            inputs["corpus_spans_revision_id"],
            inputs["coverage_report_revision_id"],
            inputs["validation_report_revision_id"],
            inputs["configuration_revision_id"],
        ] + list(inputs["batch_revision_ids"]) + [
            inputs["manifest_revision_id"],
            inputs["ocr_page_set_revision_id"],
        ] + [inputs["page_revision_ids"][page] for page in pages] + list(
            inputs["human_event_revision_ids"]
        )
        self.assertEqual(list(inputs["frozen_revision_ids"]), expected)
        self.assertEqual(list(inputs["page_revision_ids"]), pages)

    def test_resolve_refuses_when_m3_checkpoint_missing(self):
        ingest(FIXTURE, self.service, stages=("m1", "m2"))
        with self.assertRaises(ValidationRefused):
            resolve_m5_inputs(self.service, EDITION_PART)

    def test_resolve_refuses_when_m3_step_run_failed(self):
        ingest(FIXTURE, self.service, stages=("m1", "m2"))
        _fake_stage_run(self.service, "m3", succeed=False)
        with self.assertRaises(ValidationRefused) as ctx:
            resolve_m5_inputs(self.service, EDITION_PART)
        self.assertIn("M3 未通过", str(ctx.exception))

    def test_resolve_refuses_when_package_owned_by_failed_step_run(self):
        ingest(FIXTURE, self.service, stages=("m1", "m2"))
        _fake_stage_run(self.service, "m3", succeed=False, package=True)
        with self.assertRaises(ValidationRefused):
            resolve_m5_inputs(self.service, EDITION_PART)

    def test_resolve_refuses_when_gate_profile_not_structural_only(self):
        ingest(FIXTURE, self.service, stages=("m1", "m2"))
        _fake_stage_run(self.service, "m3", gate_profile="semantic_only")
        with self.assertRaises(ValidationRefused) as ctx:
            resolve_m5_inputs(self.service, EDITION_PART)
        self.assertIn("input_contract", str(ctx.exception))

    def test_resolve_refuses_when_m5_already_sealed(self):
        _chain(self.service)
        _fake_stage_run(self.service, "m5", succeed=True)
        with self.assertRaises(ValidationRefused) as ctx:
            resolve_m5_inputs(self.service, EDITION_PART)
        self.assertIn("M5 已封存", str(ctx.exception))

    def test_resolve_refuses_when_unsealed_revision_referenced(self):
        _chain(self.service)
        inputs = resolve_m5_inputs(self.service, EDITION_PART)
        rev = inputs["coverage_report_revision_id"]
        self.service.store.conn.execute(
            "UPDATE artifact_revisions SET status='invalidated' "
            "WHERE artifact_revision_id=?",
            (rev,),
        )
        with self.assertRaises(Exception):
            resolve_m5_inputs(self.service, EDITION_PART)

    def test_resolve_performs_no_writes(self):
        _chain(self.service)

        def counts():
            conn = self.service.store.conn
            return tuple(
                conn.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
                for table in ("artifact_revisions", "step_runs", "audit_log")
            )

        before = counts()
        resolve_m5_inputs(self.service, EDITION_PART)
        self.assertEqual(counts(), before)


class BuildContextTest(_Base):
    def _inputs(self):
        return resolve_m5_inputs(self.service, EDITION_PART)

    def test_build_context_loads_all_frozen_docs(self):
        _chain(self.service)
        ctx = build_context(
            self.service, self._inputs(), target_consumption_level="INTERNAL_DEMO"
        )
        self.assertEqual(len(ctx["raw"]["frozen"]), 17)
        for entry in ctx["raw"]["frozen"].values():
            self.assertEqual(entry["actual_sha256"], entry["sha256"])
        self.assertEqual(set(ctx["page_docs"]), {"page_001", "page_002", "page_003"})
        self.assertEqual(len(ctx["spans_doc"]["spans"]), 43)
        self.assertEqual(ctx["terminal_states"], {"page_002": "known_unrecognizable"})

    def test_build_context_records_hash_mismatch_without_raising(self):
        _chain(self.service)
        inputs = self._inputs()
        rev = inputs["coverage_report_revision_id"]
        row = self.service.get_revision(rev)
        object_path = self.service.root / row["object_key"]
        object_path.write_bytes(b'{"tampered": true}')
        ctx = build_context(
            self.service, inputs, target_consumption_level="INTERNAL_DEMO"
        )
        entry = ctx["raw"]["frozen"][rev]
        self.assertNotEqual(entry["actual_sha256"], entry["sha256"])
        self.assertEqual(entry["doc"], {"tampered": True})

    def test_build_context_missing_object_doc_is_none(self):
        _chain(self.service)
        inputs = self._inputs()
        rev = inputs["coverage_report_revision_id"]
        row = self.service.get_revision(rev)
        (self.service.root / row["object_key"]).unlink()
        ctx = build_context(
            self.service, inputs, target_consumption_level="INTERNAL_DEMO"
        )
        entry = ctx["raw"]["frozen"][rev]
        self.assertIsNone(entry["actual_sha256"])
        self.assertIsNone(entry["doc"])

    def test_build_context_keys_match_fixture_context(self):
        _chain(self.service)
        ctx = build_context(
            self.service, self._inputs(), target_consumption_level="INTERNAL_DEMO"
        )
        self.assertEqual(set(ctx), set(fixture_context()))


if __name__ == "__main__":
    unittest.main()
