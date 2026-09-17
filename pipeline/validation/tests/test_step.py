"""ACT 05 单元测试：run_m5 事务序列、gate_results / validation_package / m5 StagePackage 与 CLI。

用例名与 act/05.yaml 的 tests 清单逐字一致。
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from pipeline.corpus_compiler.step import run_m3
from pipeline.ledger.fixture_ingest import ingest
from pipeline.ledger.service import LedgerService
from pipeline.validation.context import build_context
from pipeline.validation.errors import ValidationRefused
from pipeline.validation.inputs import resolve_m5_inputs
from pipeline.validation.step import run_m5
from pipeline.validation.tests.helpers import (
    OFFSET_EDITION_PART,
    text_chain,
    write_offset_source,
)

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
SCHEMA = REPO / "openspec" / "schemas" / "stage_package.schema.json"
EDITION_PART = "art_000000000000000000000000000000e1"


def load_stage_package_validator():
    """加载 StagePackage 校验器，并注册 ``artifact_ref.schema.json`` 供 ``$ref`` 解析。"""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    artifact_ref = json.loads(
        (SCHEMA.parent / "artifact_ref.schema.json").read_text(encoding="utf-8")
    )
    registry = Registry().with_resource(
        "artifact_ref.schema.json",
        Resource.from_contents(artifact_ref, default_specification=DRAFT202012),
    )
    return jsonschema.Draft202012Validator(schema, registry=registry)


def _read_revision_doc(service, revision_id):
    row = service.get_revision(revision_id)
    return json.loads(service.objects.get(row["sha256"]).decode("utf-8"))


def _tamper_object(service, revision_id, payload):
    row = service.get_revision(revision_id)
    (service.root / row["object_key"]).write_bytes(payload)


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m5-step-")
        self.service = LedgerService(Path(self._tmp) / "ledger")
        self.addCleanup(self.service.close)
        ingest(FIXTURE, self.service, stages=("m1", "m2"))
        self.m3 = run_m3(self.service, EDITION_PART)


class RunM5Test(_Base):
    def test_run_m5_on_fixture_succeeds(self):
        summary = run_m5(self.service, EDITION_PART)
        self.assertEqual(summary["status"], "succeeded")
        reports = summary["validator_report_revision_ids"]
        self.assertEqual(len(reports), 14)
        checkpoints = self.service.list_checkpoints(EDITION_PART, "m5")
        self.assertEqual(len(checkpoints), 14)
        task_ids = [
            cp["content"]["completed_tasks"][0]["task_id"] for cp in checkpoints
        ]
        self.assertEqual(task_ids, [vid for vid, _g, _f in _validators()])
        self.assertEqual(summary["counts"]["findings"], 7)
        self.assertEqual(summary["gate"]["passed"], True)
        for revision_id in reports:
            row = self.service.get_revision(revision_id)
            self.assertEqual(row["status"], "sealed")

    def test_glyphbox_level_path_unchanged(self):
        """OCR 档护栏（R83）：mini_ed01 的 glyphbox_level 路径结论与计数逐项不变。

        等价既有护栏：``test_run_m5_on_fixture_succeeds``、
        ``test_gate_results_level_verdicts_passed_failed_failed``、
        ``test_frozen_inputs_exactly_seventeen_and_all_sealed``、
        ``test_g2.G2FixtureCleanTest.test_fixture_context_passes_all_g2_validators``、
        ``test_g3.G3FixtureCleanTest.test_fixture_context_g3_clean_except_three_findings``、
        ``test_g1.G1FixtureCleanTest.test_fixture_context_g1_clean_except_four_unresolved_char_findings``。
        """
        inputs = resolve_m5_inputs(self.service, EDITION_PART)
        ctx = build_context(
            self.service, inputs, target_consumption_level="INTERNAL_DEMO"
        )
        self.assertEqual(ctx["evidence_level"], "glyphbox_level")
        for key in (
            "raw_text",
            "cleaned_text",
            "raw_text_revision_id",
            "cleaned_text_revision_id",
            "patch_set_revision_id",
            "sanitization_report_revision_id",
        ):
            self.assertIsNone(ctx[key])
        self.assertEqual(ctx["patches"], [])
        self.assertEqual(ctx["sanitization_report"], {})
        self.assertEqual(
            sorted(ctx["batch_assignments"]),
            ["sanche_b001", "sanche_b002", "sanche_b003", "sanche_b004", "sanche_b005"],
        )

        summary = run_m5(self.service, EDITION_PART)
        self.assertEqual(summary["status"], "succeeded")
        self.assertEqual(summary["counts"]["findings"], 7)
        self.assertTrue(summary["gate"]["passed"])
        gate_results = _read_revision_doc(
            self.service, summary["gate_results_revision_id"]
        )
        self.assertEqual(
            gate_results["gates"],
            {
                "G1": "passed_with_warnings",
                "G2": "passed",
                "G3": "passed_with_warnings",
                "G4": "not_evaluated",
                "G5": "not_evaluated",
                "G6": "not_evaluated",
                "G7": "deferred_to_m8",
            },
        )
        self.assertEqual(
            [finding["check"] for finding in gate_results["warnings"]],
            [
                "unresolved_glyph",
                "unresolved_glyph",
                "quote_hash_not_stored",
                "glyph_text_misaligned",
                "glyph_text_misaligned",
            ],
        )

    def test_gate_results_level_verdicts_passed_failed_failed(self):
        summary = run_m5(self.service, EDITION_PART)
        gate_results = _read_revision_doc(
            self.service, summary["gate_results_revision_id"]
        )
        self.assertEqual(
            gate_results["level_verdicts"],
            {"INTERNAL_DEMO": "passed", "DEV_SEARCH": "failed", "PUBLIC_RELEASE": "failed"},
        )
        self.assertTrue(gate_results["gate"]["passed"])
        self.assertEqual(gate_results["counts"]["findings"], 7)

    def test_stage_package_validates_schema_and_lineage(self):
        summary = run_m5(self.service, EDITION_PART)
        package = _read_revision_doc(self.service, summary["package_revision_id"])
        jsonschema_validator = load_stage_package_validator()
        jsonschema_validator.validate(package)
        self.assertEqual(package["stage"], "m5")
        self.assertTrue(package["validation"]["passed"])
        upstream_types = {ref["artifact_type"] for ref in package["lineage"]["upstream_artifacts"]}
        self.assertIn("stage_package", upstream_types)
        gate_row = self.service.get_revision(summary["gate_results_revision_id"])
        self.assertEqual(package["manifest"]["content_sha256"], gate_row["sha256"])
        self.assertEqual(len(package["manifest"]["input_artifacts"]), 17)

    def test_frozen_inputs_exactly_seventeen_and_all_sealed(self):
        summary = run_m5(self.service, EDITION_PART)
        row = self.service.get_step_run(summary["step_run_id"])
        request = json.loads(row["request_json"])
        self.assertEqual(len(request["input_artifact_ids"]), 17)
        for revision_id in request["input_artifact_ids"]:
            self.assertEqual(self.service.get_revision(revision_id)["status"], "sealed")

    def test_target_public_release_gate_failed(self):
        summary = run_m5(
            self.service, EDITION_PART, target_consumption_level="PUBLIC_RELEASE"
        )
        self.assertEqual(summary["status"], "succeeded")
        self.assertFalse(summary["gate"]["passed"])
        package = _read_revision_doc(self.service, summary["package_revision_id"])
        self.assertFalse(package["validation"]["passed"])
        gate_results = _read_revision_doc(
            self.service, summary["gate_results_revision_id"]
        )
        self.assertTrue(gate_results["rework_tasks"])

    def test_validator_exception_marks_task_errored_and_levels_failed(self):
        with mock.patch(
            "pipeline.validation.g1_source.validate_page_registry",
            side_effect=RuntimeError("boom"),
        ):
            summary = run_m5(self.service, EDITION_PART)
        self.assertEqual(summary["status"], "succeeded")
        gate_results = _read_revision_doc(
            self.service, summary["gate_results_revision_id"]
        )
        errored = [
            item for item in gate_results["validators"]
            if item["validator_id"] == "g1_page_registry"
        ]
        self.assertEqual(errored[0]["task_status"], "errored")
        self.assertEqual(gate_results["level_verdicts"]["INTERNAL_DEMO"], "failed")

    def test_after_begin_exception_seals_failure_and_no_stage_package(self):
        with mock.patch.object(
            self.service, "record_transformation", side_effect=RuntimeError("boom")
        ):
            summary = run_m5(self.service, EDITION_PART)
        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["failed_check"], "internal")
        self.assertNotIn("stage_package_id", summary)
        packages = self.service.store.conn.execute(
            "SELECT COUNT(*) FROM stage_packages WHERE stage='m5'"
        ).fetchone()[0]
        self.assertEqual(packages, 0)

    def test_refuses_when_m3_step_run_failed(self):
        before = tuple(
            self.service.store.conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
            for t in ("artifact_revisions", "step_runs", "audit_log")
        )
        self.service.store.conn.execute(
            "UPDATE step_runs SET status='failed' WHERE step_run_id=?",
            (self.m3["step_run_id"],),
        )
        with self.assertRaises(ValidationRefused):
            run_m5(self.service, EDITION_PART)
        after = tuple(
            self.service.store.conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
            for t in ("artifact_revisions", "step_runs", "audit_log")
        )
        self.assertEqual(after, before)


class RunM5TamperTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m5-tamper-")
        self.service = LedgerService(Path(self._tmp) / "ledger")
        self.addCleanup(self.service.close)
        ingest(FIXTURE, self.service, stages=("m1", "m2"))
        self.m3 = run_m3(self.service, EDITION_PART)
        # 篡改 corpus_spans 对象字节（保持可解析，但哈希不符）
        from pipeline.validation.inputs import resolve_m5_inputs

        inputs = resolve_m5_inputs(self.service, EDITION_PART)
        _tamper_object(
            self.service, inputs["corpus_spans_revision_id"], b"tampered: true\n"
        )

    def test_tampered_corpus_spans_yields_thirteen_skipped_and_all_levels_failed(self):
        summary = run_m5(self.service, EDITION_PART)
        self.assertEqual(summary["status"], "succeeded")
        gate_results = _read_revision_doc(
            self.service, summary["gate_results_revision_id"]
        )
        statuses = [item["task_status"] for item in gate_results["validators"]]
        self.assertEqual(statuses.count("skipped_fail_closed"), 13)
        self.assertEqual(statuses.count("succeeded"), 1)
        self.assertEqual(
            gate_results["level_verdicts"],
            {"INTERNAL_DEMO": "failed", "DEV_SEARCH": "failed", "PUBLIC_RELEASE": "failed"},
        )
        package = _read_revision_doc(self.service, summary["package_revision_id"])
        self.assertFalse(package["validation"]["passed"])


class OffsetLevelStepTest(unittest.TestCase):
    """R83（第 100 条 D5）：电子文本档真实 Ledger 端到端（合成数据，不读真书宿主）。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m5-text-step-")
        self.service = LedgerService(Path(self._tmp) / "ledger")
        self.addCleanup(self.service.close)
        source_dir = write_offset_source(Path(self._tmp) / "src")
        self.chain = text_chain(self.service, source_dir)

    def _frozen_types(self, step_run_id):
        request = json.loads(self.service.get_step_run(step_run_id)["request_json"])
        rows = self.service.store.conn.execute(
            "SELECT a.artifact_type FROM artifacts a "
            "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
            "WHERE r.artifact_revision_id IN (%s)"
            % ",".join("?" * len(request["input_artifact_ids"])),
            tuple(request["input_artifact_ids"]),
        ).fetchall()
        return [row[0] for row in rows]

    def test_offset_level_does_not_read_ocr_page(self):
        self.assertEqual(self.chain["m1"]["raw_text_revision_ids"] is not None, True)
        self.assertEqual(self.chain["m3"]["status"], "succeeded")

        summary = run_m5(self.service, OFFSET_EDITION_PART)
        self.assertEqual(summary["status"], "succeeded")
        frozen_types = self._frozen_types(summary["step_run_id"])
        self.assertNotIn("ocr_page", frozen_types)
        self.assertNotIn("ocr_page_set", frozen_types)
        for required in (
            "source_manifest",
            "raw_text",
            "cleaned_text_revision",
            "deterministic_patch_set",
            "sanitization_report",
        ):
            self.assertIn(required, frozen_types)

        verdicts = summary["level_verdicts"]
        self.assertEqual(
            verdicts,
            {"INTERNAL_DEMO": "passed", "DEV_SEARCH": "passed", "PUBLIC_RELEASE": "failed"},
        )
        self.assertTrue(summary["gate"]["passed"])
        report = {
            item["validator_id"]: item for item in summary["validator_reports"]
        }
        self.assertTrue(report["g1_replay"]["checked"]["replayed"])
        self.assertEqual(report["g1_replay"]["findings"], [])
        self.assertGreater(report["g3_strict_offset_quote"]["checked"]["spans"], 0)
        self.assertEqual(
            [finding["check"] for finding in report["g3_evidence_level"]["findings"]],
            ["evidence_level_insufficient"],
        )


class CliTest(unittest.TestCase):
    def _prepare(self, stages):
        tmp = tempfile.mkdtemp(prefix="m5-cli-")
        root = Path(tmp) / "ledger"
        service = LedgerService(root)
        try:
            ingest(FIXTURE, service, stages=stages)
            if stages == ("m1", "m2"):
                run_m3(service, EDITION_PART)
        finally:
            service.close()
        return root

    def _run(self, root, *extra):
        command = [
            sys.executable, "-m", "pipeline.validation",
            "--root", str(root), "--edition-part", EDITION_PART,
        ] + list(extra)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO)
        return subprocess.run(
            command, cwd=str(REPO), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )

    def test_cli_exit_codes(self):
        root = self._prepare(("m1", "m2"))
        ok = self._run(root)
        self.assertEqual(ok.returncode, 0, ok.stdout.decode("utf-8", "replace"))
        self.assertIn("M5 OK", ok.stdout.decode("utf-8", "replace").splitlines()[-1])

        root2 = self._prepare(("m1", "m2"))
        failed = self._run(root2, "--target-consumption-level", "PUBLIC_RELEASE")
        self.assertEqual(failed.returncode, 1, failed.stdout.decode("utf-8", "replace"))
        self.assertIn(
            "M5 GATE_FAILED",
            failed.stdout.decode("utf-8", "replace").splitlines()[-1],
        )

        root3 = self._prepare(("m1",))
        refused = self._run(root3)
        self.assertEqual(refused.returncode, 2, refused.stdout.decode("utf-8", "replace"))
        self.assertIn(
            "M5 REFUSED",
            refused.stdout.decode("utf-8", "replace").splitlines()[-1],
        )


    def test_cli_failed_after_begin_exit_1(self):
        tmp = tempfile.mkdtemp(prefix="m5-cli-fail-")
        root = Path(tmp) / "ledger"
        service = LedgerService(root)
        try:
            ingest(FIXTURE, service, stages=("m1", "m2"))
            run_m3(service, EDITION_PART)
        finally:
            service.close()

        from pipeline.validation import __main__ as cli

        buffer = io.StringIO()
        with mock.patch(
            "pipeline.ledger.service.LedgerService.record_transformation",
            side_effect=RuntimeError("boom"),
        ):
            with redirect_stdout(buffer):
                code = cli.main(
                    ["--root", str(root), "--edition-part", EDITION_PART]
                )
        self.assertEqual(code, 1, buffer.getvalue())
        self.assertTrue(
            buffer.getvalue().splitlines()[-1].startswith("M5 FAILED"),
            buffer.getvalue().splitlines()[-1],
        )


def _validators():
    from pipeline.validation.registry import VALIDATORS

    return VALIDATORS


if __name__ == "__main__":
    unittest.main()
