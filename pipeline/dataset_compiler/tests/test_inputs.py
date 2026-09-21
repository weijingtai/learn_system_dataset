"""ACT impl-04/04：M8 输入解析 resolve_m8_inputs 的测试。

脚手架用 ``_ledger_helpers.prepare_m3`` / ``prepare_m8_ready``；只读用例断言
解析前后 Ledger 行数不变。
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline.corpus_compiler.step_offset import run_m3_text
from pipeline.corpus_compiler.tests.test_step_offset import _setup_m2_ledger
from pipeline.dataset_compiler.errors import DatasetRefused
from pipeline.dataset_compiler.inputs import _detect_route, resolve_m8_inputs
from pipeline.dataset_compiler.tests._ledger_helpers import (
    FIXTURE,
    assets_available,
    prepare_m3,
    prepare_m8_ready,
    seed_succeeded_m8_checkpoint,
    table_counts,
)
from pipeline.ledger import ids
from pipeline.ledger.fixture_ingest import ingest
from pipeline.ledger.service import LedgerService


def _artifact_id_of(service, revision_id):
    """按修订号取 artifact_id。"""
    return service.store.conn.execute(
        "SELECT artifact_id FROM artifact_revisions WHERE artifact_revision_id=?",
        (revision_id,),
    ).fetchone()[0]


def seed_m7_snapshot(
    service,
    edition_part_id,
    *,
    knowledge=None,
    snapshot_artifact_type="canonical_snapshot",
):
    """在临时 Ledger 上登记一个 succeeded 的 m7 StepRun + Snapshot + 包 + Checkpoint。

    供 ACT 13 的 M7 Snapshot 解析测试使用。``snapshot_artifact_type`` 可改成非
    ``canonical_snapshot`` 以验证类型不符 → ``SCH_002``。
    """
    if knowledge is None:
        knowledge = {
            "technique_id": "qizheng",
            "patterns": [],
            "concepts": [],
            "assertions": [],
            "school_views": [],
            "conflict_groups": [],
        }
    processing_run_id = service.create_processing_run(
        "release_run", edition_part_id, "qizheng"
    )
    _, config_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        json.dumps({"stage": "m7"}, sort_keys=True).encode("utf-8"),
        producer_module="test.seed",
        producer_version="0",
    )
    step_run_id = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": ids.new_id("step_run_id"),
            "input_artifact_ids": [],
            "technique_profile_id": "qizheng",
            "configuration_artifact_id": config_revision_id,
        }
    )
    _, snapshot_revision_id = service.put_artifact(
        step_run_id,
        snapshot_artifact_type,
        json.dumps(knowledge, sort_keys=True, ensure_ascii=False).encode("utf-8"),
        producer_module="test.seed",
        producer_version="0",
    )
    service.seal_revision(snapshot_revision_id)
    snapshot_artifact_id = _artifact_id_of(service, snapshot_revision_id)

    _, assembly_revision_id = service.put_artifact(
        step_run_id,
        "assembly_package",
        json.dumps(
            {
                "schema_version": "0.1.0-draft",
                "technique_id": "qizheng",
                "canonical_snapshot_revision_id": snapshot_revision_id,
                "report": {},
            },
            sort_keys=True,
        ).encode("utf-8"),
        producer_module="test.seed",
        producer_version="0",
    )
    service.seal_revision(assembly_revision_id)
    assembly_artifact_id = _artifact_id_of(service, assembly_revision_id)

    def _ref(artifact_id, revision_id, artifact_type):
        return {
            "schema_version": "1.0.0",
            "artifact_kind": "artifact",
            "artifact_id": artifact_id,
            "artifact_revision_id": revision_id,
            "artifact_type": artifact_type,
        }

    stage_package_id = ids.new_id("stage_package_id", stage="m7")
    package_revision_id = ids.new_id("artifact_revision_id")
    package = {
        "schema_version": "1.0.0",
        "stage_package_id": stage_package_id,
        "artifact_revision_id": package_revision_id,
        "stage": "m7",
        "status": "draft",
        "payload": {},
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "input_artifacts": [],
            "output_artifacts": [
                _ref(assembly_artifact_id, assembly_revision_id, "assembly_package"),
            ],
            "counts": {"assembly_package": 1},
            "content_sha256": "0" * 64,
        },
        "validation": {"passed": True, "report_artifacts": []},
        "lineage": {"upstream_artifacts": [], "transformations": []},
        "logs": [],
        "failures": [],
    }
    service.register_stage_package(
        step_run_id,
        package,
        json.dumps(package, sort_keys=True).encode("utf-8"),
        stage_package_id=stage_package_id,
        artifact_revision_id=package_revision_id,
    )
    service.seal_revision(package_revision_id)
    service.write_checkpoint(
        step_run_id,
        edition_part_id=edition_part_id,
        stage="m7",
        completed_tasks=[
            {
                "task_id": "seal_snapshot",
                "artifact_revision_id": package_revision_id,
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )
    current_version = service.get_step_run(step_run_id)["status_version"]
    service.finish_step_run(
        step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "status_version": current_version + 1,
            "status": "succeeded",
            "output_artifact_ids": [
                package_revision_id,
                snapshot_revision_id,
                assembly_revision_id,
            ],
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
        },
    )
    return {
        "step_run_id": step_run_id,
        "snapshot_revision_id": snapshot_revision_id,
        "package_revision_id": package_revision_id,
        "knowledge": knowledge,
    }


class ResolveM8InputsBase(unittest.TestCase):
    """临时 Ledger 脚手架。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m8-inputs-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.service = LedgerService(Path(self._tmp) / "ledger")
        self.addCleanup(self.service.close)

    def new_service(self):
        """另起一个干净 Ledger（用于只读断言等）。"""
        return self.service


class ResolveFixtureTests(ResolveM8InputsBase):
    """真实页图齐备时的完整解析。"""

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_resolve_fixture_inputs(self):
        prepared = prepare_m8_ready(self.service)
        edition_part_id = prepared["edition_part_id"]
        result = resolve_m8_inputs(self.service, edition_part_id)
        self.assertEqual(
            set(result["page_revision_ids"]),
            {"page_001", "page_002", "page_003"},
        )
        self.assertEqual(
            set(result["asset_revision_ids"]),
            {"page_001", "page_002", "page_003"},
        )
        self.assertEqual(result["m3_gate_profile"], "structural_only")
        self.assertEqual(
            result["excluded_pages"], {"page_002": "known_unrecognizable"}
        )
        self.assertEqual(result["technique_id"], "qizheng")
        self.assertEqual(result["source_id"], "src_sanche_ed01")
        self.assertEqual(result["m3_step_run_id"], prepared["m3"]["step_run_id"])
        self.assertEqual(
            result["asset_step_run_id"], prepared["assets"]["step_run_id"]
        )
        self.assertIsNotNone(result["spans_revision_id"])
        self.assertIsNotNone(result["manifest_revision_id"])
        self.assertIsNotNone(result["ocr_page_set_revision_id"])


class ResolveRefusalTests(ResolveM8InputsBase):
    """拒绝路径。"""

    def test_refuses_without_m3_REF_001(self):
        summary = ingest(FIXTURE, self.service, stages=("m1", "m2"))
        with self.assertRaises(DatasetRefused) as ctx:
            resolve_m8_inputs(self.service, summary["edition_part_id"])
        self.assertIn("M3 未编译", str(ctx.exception))

    def test_refuses_fixture_ingested_m3_package(self):
        summary = ingest(FIXTURE, self.service, stages=("m1", "m2", "m3"))
        with self.assertRaises(DatasetRefused) as ctx:
            resolve_m8_inputs(self.service, summary["edition_part_id"])
        self.assertIn("spans_revision_id", str(ctx.exception))

    def test_refuses_without_assets_REF_001(self):
        prepared = prepare_m3(self.service)
        with self.assertRaises(DatasetRefused) as ctx:
            resolve_m8_inputs(self.service, prepared["edition_part_id"])
        self.assertIn("SourceAsset 未登记", str(ctx.exception))
        self.assertEqual(ctx.exception.code, "REF_001")

    def test_refuses_when_m8_sealed(self):
        prepared = prepare_m3(self.service)
        seed_succeeded_m8_checkpoint(self.service, prepared["edition_part_id"])
        with self.assertRaises(DatasetRefused) as ctx:
            resolve_m8_inputs(self.service, prepared["edition_part_id"])
        self.assertIn("M8 已封存", str(ctx.exception))


class DetectRouteTests(unittest.TestCase):
    """ACT 13a：路线判定唯一权威 = m3 包 manifest.input_artifacts 的构成。"""

    @staticmethod
    def _package(*artifact_types):
        return {
            "manifest": {
                "input_artifacts": [
                    {"artifact_type": artifact_type} for artifact_type in artifact_types
                ]
            }
        }

    def test_detect_route_electronic_text_from_raw_text_reference(self):
        package = self._package(
            "raw_text",
            "cleaned_text_revision",
            "deterministic_patch_set",
            "sanitization_report",
        )
        self.assertEqual(_detect_route(package), "electronic_text")
        self.assertEqual(
            _detect_route(self._package("source_manifest", "ocr_page_set", "ocr_page")),
            "ocr",
        )

    def test_detect_route_refuses_ambiguous_input_artifacts(self):
        with self.assertRaises(DatasetRefused) as ctx:
            _detect_route(self._package("raw_text", "ocr_page_set"))
        self.assertEqual(ctx.exception.code, "REF_001")
        self.assertIn("ocr_page_set", str(ctx.exception))
        self.assertIn("raw_text", str(ctx.exception))

        with self.assertRaises(DatasetRefused) as ctx2:
            _detect_route(self._package("cleaned_text_revision"))
        self.assertEqual(ctx2.exception.code, "REF_001")


class ElectronicTextRouteTests(unittest.TestCase):
    """ACT 13a：电子文本路线在无 OCR 页、无 SourceAsset 的账本上仍须跑通。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m8-etext-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.edition_part_id = "art_000000000000000000000000000000e1"
        self.service, self.meta = _setup_m2_ledger(
            self._tmp, edition_part_id=self.edition_part_id
        )
        self.addCleanup(self.service.close)
        summary = run_m3_text(self.service, self.edition_part_id)
        self.assertEqual(summary["status"], "succeeded")

    def test_electronic_text_route_yields_no_pages_and_no_assets(self):
        result = resolve_m8_inputs(self.service, self.edition_part_id)
        self.assertEqual(result["route"], "electronic_text")
        self.assertIsNone(result["ocr_page_set_revision_id"])
        self.assertEqual(result["page_revision_ids"], {})
        self.assertEqual(result["asset_revision_ids"], {})
        self.assertIsNone(result["asset_step_run_id"])
        self.assertIsNotNone(result["manifest_revision_id"])
        self.assertEqual(result["technique_id"], "qizheng")
        self.assertEqual(result["source_id"], "src_qianyuan_ed01")
        # source_manifest 必须与冻结的 raw_text 同属一个 M1 StepRun（唯一权威上游路径）
        producer_step_run_id = self.service.store.conn.execute(
            "SELECT step_run_id FROM artifact_revisions WHERE artifact_revision_id=?",
            (self.meta["raw_rev"],),
        ).fetchone()[0]
        expected_manifest_revision_id = self.service.store.conn.execute(
            "SELECT r.artifact_revision_id FROM artifact_revisions r "
            "JOIN artifacts a ON a.artifact_id = r.artifact_id "
            "WHERE a.artifact_type='source_manifest' AND r.step_run_id=? AND r.status='sealed'",
            (producer_step_run_id,),
        ).fetchone()[0]
        self.assertEqual(
            result["manifest_revision_id"], expected_manifest_revision_id
        )


class ResolveM7SnapshotTests(unittest.TestCase):
    """ACT 13：M7 Snapshot 解析（无 M7 → None，不报错）。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m8-m7-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.edition_part_id = "art_000000000000000000000000000000e1"
        self.service, _ = _setup_m2_ledger(
            self._tmp, edition_part_id=self.edition_part_id
        )
        self.addCleanup(self.service.close)
        summary = run_m3_text(self.service, self.edition_part_id)
        self.assertEqual(summary["status"], "succeeded")

    def test_resolve_m8_inputs_reads_sealed_m7_snapshot_knowledge(self):
        knowledge = {
            "technique_id": "qizheng",
            "patterns": [],
            "concepts": [],
            "assertions": [],
            "school_views": [],
            "conflict_groups": [],
        }
        seeded = seed_m7_snapshot(self.service, self.edition_part_id, knowledge=knowledge)
        result = resolve_m8_inputs(self.service, self.edition_part_id)
        self.assertEqual(
            result["m7_snapshot_revision_id"], seeded["snapshot_revision_id"]
        )
        self.assertEqual(result["snapshot_knowledge"], knowledge)

    def test_resolve_m8_inputs_yields_none_when_no_m7_checkpoint(self):
        result = resolve_m8_inputs(self.service, self.edition_part_id)
        self.assertIsNone(result["m7_snapshot_revision_id"])
        self.assertIsNone(result["snapshot_knowledge"])

    def test_resolve_m8_inputs_refuses_wrong_snapshot_artifact_type(self):
        seed_m7_snapshot(
            self.service,
            self.edition_part_id,
            snapshot_artifact_type="validation_report",
        )
        with self.assertRaises(DatasetRefused) as ctx:
            resolve_m8_inputs(self.service, self.edition_part_id)
        self.assertEqual(ctx.exception.code, "SCH_002")


class OcrRouteRegressionTests(ResolveM8InputsBase):
    """ACT 13a：OCR 路线既有拒收行为逐字不变。"""

    def test_ocr_route_unchanged_still_requires_pages_and_assets(self):
        prepared = prepare_m3(self.service)
        with self.assertRaises(DatasetRefused) as ctx:
            resolve_m8_inputs(self.service, prepared["edition_part_id"])
        self.assertIn("SourceAsset 未登记", str(ctx.exception))
        self.assertEqual(ctx.exception.code, "REF_001")


class ResolvePurityTests(ResolveM8InputsBase):
    """resolve_m8_inputs 只读，不写 Ledger。"""

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_resolve_does_not_write(self):
        prepared = prepare_m8_ready(self.service)
        before = table_counts(self.service)
        resolve_m8_inputs(self.service, prepared["edition_part_id"])
        self.assertEqual(table_counts(self.service), before)


if __name__ == "__main__":
    unittest.main()
