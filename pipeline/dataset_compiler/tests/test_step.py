"""ACT impl-04/05：run_m8 在真实 Ledger 上的集成测试（规格 §16、§17、§17.1）。

统一脚手架：tempfile → LedgerService → ingest(m1,m2) → run_m3 → register_source_assets
（即 ``_ledger_helpers.prepare_m8_ready``）。
"""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline.dataset_compiler import packs
from pipeline.dataset_compiler.canonical import normalized_sha256
from pipeline.dataset_compiler.errors import DatasetRefused
from pipeline.dataset_compiler.inputs import resolve_m8_inputs
from pipeline.dataset_compiler.step import run_m8
from pipeline.dataset_compiler.tests._ledger_helpers import (
    REPO_ROOT,
    assets_available,
    prepare_m8_ready,
    table_counts,
)
from pipeline.dataset_compiler.tests.test_inputs import seed_m7_snapshot
from pipeline.ledger.errors import SchemaViolation
from pipeline.ledger.service import LedgerService

SCHEMA_DIR = REPO_ROOT / "openspec" / "schemas"
FIXTURE_EDITION_PART = "art_000000000000000000000000000000e1"


def _load_pack(service, revision_id):
    revision = service.get_revision(revision_id)
    return json.loads(service.objects.get(revision["sha256"]).decode("utf-8"))


def _validate_stage_package(package):
    import jsonschema
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    with open(SCHEMA_DIR / "stage_package.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open(SCHEMA_DIR / "artifact_ref.schema.json", encoding="utf-8") as handle:
        artifact_ref = json.load(handle)
    registry = Registry().with_resource(
        "artifact_ref.schema.json",
        Resource.from_contents(artifact_ref, default_specification=DRAFT202012),
    )
    jsonschema.Draft202012Validator(schema, registry=registry).validate(package)


def _validation_report_for(service, step_run_id):
    """取某 StepRun 名下唯一的 validation_report 修订内容。"""
    row = service.store.conn.execute(
        "SELECT r.artifact_revision_id FROM artifact_revisions r "
        "JOIN artifacts a ON a.artifact_id = r.artifact_id "
        "WHERE a.artifact_type='validation_report' AND r.step_run_id=?",
        (step_run_id,),
    ).fetchone()
    return _load_pack(service, row[0])


class StepTestBase(unittest.TestCase):
    """公共脚手架：临时 Ledger；需真实页图的用例自行调用 ``ready()``。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m8-step-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.service = LedgerService(Path(self._tmp) / "ledger")
        self.addCleanup(self.service.close)

    def ready(self):
        prepared = prepare_m8_ready(self.service)
        self.edition_part_id = prepared["edition_part_id"]
        return prepared

    def _tamper_object(self, revision_id):
        """翻转对象字节首位，制造「对象内容与登记 sha256 不符」。"""
        revision = self.service.get_revision(revision_id)
        path = self.service.objects.path_for(revision["sha256"])
        data = bytearray(path.read_bytes())
        data[0] = data[0] ^ 0x01
        path.write_bytes(bytes(data))

    def _m8_package_count(self):
        return self.service.store.conn.execute(
            "SELECT COUNT(*) FROM stage_packages WHERE stage='m8'"
        ).fetchone()[0]

    def _artifact_count(self, artifact_type):
        return self.service.store.conn.execute(
            "SELECT COUNT(*) FROM artifacts WHERE artifact_type=?",
            (artifact_type,),
        ).fetchone()[0]


class StepSuccessTests(StepTestBase):
    """成功路径。"""

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_run_m8_on_fixture_succeeds(self):
        self.ready()
        result = run_m8(self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO")
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(
            result["counts"],
            {
                "spans": 43,
                "pages": 3,
                "source_assets": 3,
                "glyph_highlights": 41,
                "line_bbox_highlights": 2,
                "packs": 2,
            },
        )
        self.assertEqual(
            self.service.get_step_run(result["step_run_id"])["status"], "succeeded"
        )

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_frozen_inputs_exactly_ten(self):
        self.ready()
        inputs = resolve_m8_inputs(self.service, self.edition_part_id)
        result = run_m8(self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO")
        frozen = set(self.service._frozen_input_ids(result["step_run_id"]))
        expected = {
            inputs["m3_package_revision_id"],
            inputs["spans_revision_id"],
            inputs["manifest_revision_id"],
            inputs["ocr_page_set_revision_id"],
        }
        expected.update(inputs["page_revision_ids"].values())
        expected.update(inputs["asset_revision_ids"].values())
        self.assertEqual(len(expected), 10)
        self.assertEqual(frozen, expected)

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_four_checkpoints_chained(self):
        self.ready()
        result = run_m8(self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO")
        chain = self.service.list_checkpoints(self.edition_part_id, "m8")
        self.assertEqual(len(chain), 4)
        task_ids = [
            task["task_id"]
            for checkpoint in chain
            for task in checkpoint["content"]["completed_tasks"]
        ]
        self.assertEqual(
            task_ids,
            [
                "source_asset_pack",
                "evidence_map_pack",
                "release_manifest",
                "validation_report",
            ],
        )
        self.assertIsNone(chain[0]["prev_checkpoint_revision_id"])
        for previous, current in zip(chain, chain[1:]):
            self.assertEqual(
                current["prev_checkpoint_revision_id"],
                previous["artifact_revision_id"],
            )
        self.assertEqual(
            result["checkpoint_revision_ids"],
            [checkpoint["artifact_revision_id"] for checkpoint in chain],
        )

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_subpacks_are_independent_sealed_artifacts(self):
        self.ready()
        result = run_m8(self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO")
        mapping = {
            "source_asset_pack": result["source_asset_pack_revision_id"],
            "evidence_map_pack": result["evidence_map_pack_revision_id"],
            "release_manifest": result["release_manifest_revision_id"],
            "validation_report": result["validation_report_revision_id"],
            "publication_package": result["publication_package_revision_id"],
        }
        artifact_ids = set()
        for artifact_type, revision_id in mapping.items():
            row = self.service.get_revision(revision_id)
            self.assertEqual(row["status"], "sealed")
            self.assertEqual(self.service._artifact_type(revision_id), artifact_type)
            artifact_ids.add(row["artifact_id"])
        self.assertEqual(len(artifact_ids), len(mapping))

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_release_manifest_hashes_match_ledger_bytes(self):
        self.ready()
        result = run_m8(self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO")
        manifest = _load_pack(self.service, result["release_manifest_revision_id"])
        by_type = {item["pack_type"]: item for item in manifest["packs"]}
        for artifact_type, revision_id in (
            ("source_asset_pack", result["source_asset_pack_revision_id"]),
            ("evidence_map_pack", result["evidence_map_pack_revision_id"]),
        ):
            revision = self.service.get_revision(revision_id)
            self.assertEqual(by_type[artifact_type]["sha256"], revision["sha256"])
            self.assertEqual(by_type[artifact_type]["size"], revision["size_bytes"])

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_m8_stage_package_validates_schema_and_lineage(self):
        self.ready()
        inputs = resolve_m8_inputs(self.service, self.edition_part_id)
        result = run_m8(self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO")
        package = _load_pack(self.service, result["package_revision_id"])
        _validate_stage_package(package)
        self.assertEqual(package["stage"], "m8")
        self.assertEqual(
            set(package["payload"].keys()),
            {
                "release_id",
                "consumption_level",
                "release_manifest_revision_id",
                "publication_package_revision_id",
                "canonical_hash",
                "knowledge_chain",
            },
        )
        self.assertEqual(package["payload"]["knowledge_chain"], "not_compiled")
        upstream = {
            reference["artifact_revision_id"]
            for reference in package["lineage"]["upstream_artifacts"]
        }
        self.assertIn(inputs["m3_package_revision_id"], upstream)
        self.assertIn(inputs["manifest_revision_id"], upstream)
        release_revision = self.service.get_revision(
            result["release_manifest_revision_id"]
        )
        self.assertEqual(
            package["manifest"]["content_sha256"], release_revision["sha256"]
        )

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_two_ledgers_normalized_sha_equal(self):
        self.ready()
        first = run_m8(self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO")
        first_pack = _load_pack(self.service, first["evidence_map_pack_revision_id"])

        tmp2 = tempfile.mkdtemp(prefix="m8-step-second-")
        try:
            service2 = LedgerService(Path(tmp2) / "ledger")
            try:
                prepared2 = prepare_m8_ready(service2)
                second = run_m8(
                    service2,
                    prepared2["edition_part_id"],
                    consumption_level="INTERNAL_DEMO",
                )
                second_pack = _load_pack(
                    service2, second["evidence_map_pack_revision_id"]
                )
            finally:
                service2.close()
        finally:
            shutil.rmtree(tmp2, True)

        self.assertNotEqual(first["evidence_map_pack_revision_id"],
                            second["evidence_map_pack_revision_id"])
        self.assertEqual(
            normalized_sha256(first_pack), normalized_sha256(second_pack)
        )


class StepRefusalTests(StepTestBase):
    """拒绝路径。"""

    def test_illegal_level_SCH_002_no_writes(self):
        before = table_counts(self.service)
        with self.assertRaises(SchemaViolation) as ctx:
            run_m8(
                self.service,
                FIXTURE_EDITION_PART,
                consumption_level="internal_demo",
            )
        self.assertEqual(ctx.exception.code, "SCH_002")
        self.assertEqual(table_counts(self.service), before)

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_second_run_m8_refused(self):
        self.ready()
        run_m8(self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO")
        with self.assertRaises(DatasetRefused) as ctx:
            run_m8(self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO")
        self.assertIn("M8 已封存", str(ctx.exception))


class StepFailureSealingTests(StepTestBase):
    """begin 之后的失败封存。"""

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_tampered_spans_object_fails_input_contract(self):
        self.ready()
        inputs = resolve_m8_inputs(self.service, self.edition_part_id)
        self._tamper_object(inputs["spans_revision_id"])
        result = run_m8(self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_check"], "input_contract")
        self.assertEqual(self._m8_package_count(), 0)

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_tampered_asset_object_fails_input_contract(self):
        self.ready()
        inputs = resolve_m8_inputs(self.service, self.edition_part_id)
        self._tamper_object(inputs["asset_revision_ids"]["page_001"])
        result = run_m8(self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_check"], "input_contract")
        self.assertEqual(self._m8_package_count(), 0)

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_gate_failure_fails_publication_gate(self):
        self.ready()
        original = packs.build_evidence_map_pack

        def tampered(*args, **kwargs):
            result = original(*args, **kwargs)
            pack = copy.deepcopy(result["pack"])
            pack["entries"].pop(next(iter(pack["entries"])))
            result["pack"] = pack
            return result

        packs.build_evidence_map_pack = tampered
        try:
            result = run_m8(
                self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO"
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failed_check"], "publication_gate")
            self.assertEqual(self._artifact_count("publication_package"), 0)
            self.assertEqual(self._m8_package_count(), 0)
        finally:
            packs.build_evidence_map_pack = original


class StepKnowledgeChainTests(StepTestBase):
    """ACT 13：knowledge_chain 由 Snapshot 事实推出，不再硬编码字面量（D-W8-13b）。"""

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_knowledge_chain_not_compiled_without_snapshot(self):
        self.ready()
        result = run_m8(
            self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO"
        )
        self.assertEqual(result["status"], "succeeded")
        report = _validation_report_for(self.service, result["step_run_id"])
        self.assertEqual(report["knowledge_chain"], "not_compiled")
        self.assertEqual(
            report["checks"]["knowledge_chain"]["status"], "not_evaluated"
        )

    def _validation_report_with_knowledge(self, knowledge):
        """在独立 Ledger 上跑一次带 M7 Snapshot 的 M8，返回其 validation_report。"""
        tmp = tempfile.mkdtemp(prefix="m8-kc-")
        try:
            service = LedgerService(Path(tmp) / "ledger")
            try:
                prepared = prepare_m8_ready(service)
                seed_m7_snapshot(
                    service, prepared["edition_part_id"], knowledge=knowledge
                )
                result = run_m8(
                    service,
                    prepared["edition_part_id"],
                    consumption_level="INTERNAL_DEMO",
                )
                return _validation_report_for(service, result["step_run_id"])
            finally:
                service.close()
        finally:
            shutil.rmtree(tmp, True)

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_knowledge_chain_reflects_gate_result_with_snapshot(self):
        self.ready()
        seed_m7_snapshot(
            self.service, self.edition_part_id,
            knowledge={"patterns": [], "assertions": [], "concepts": []},
        )
        result = run_m8(
            self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO"
        )
        # 有 Snapshot → 链转实评；本切片未接 GraphProjectionPack，gate 如实失败
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_check"], "publication_gate")
        report = _validation_report_for(self.service, result["step_run_id"])
        # 两处 knowledge_chain 取 gate 实评结果，而非 not_evaluated/not_compiled 字面量
        self.assertEqual(report["knowledge_chain"], "evaluated")
        self.assertEqual(report["checks"]["knowledge_chain"]["status"], "evaluated")
        self.assertEqual(report["checks"]["chain_closure"]["status"], "evaluated")

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_knowledge_chain_verdict_tracks_snapshot_content(self):
        """改动 Snapshot 内容必须改变 gate 对知识链的实评（驳回「写死」）。"""
        empty = self._validation_report_with_knowledge(
            {"patterns": [], "assertions": [], "concepts": []}
        )
        populated = self._validation_report_with_knowledge(
            {
                "patterns": [
                    {
                        "pattern_id": "pat_qizheng_000001",
                        "assertion_ids": ["as_qizheng_000001"],
                    }
                ],
                "concepts": [],
                "assertions": [{"assertion_id": "as_qizheng_000001"}],
                "school_views": [],
                "conflict_groups": [],
            }
        )
        self.assertIs(empty["checks"]["chain_closure"]["ok"], False)
        self.assertIs(populated["checks"]["chain_closure"]["ok"], True)


if __name__ == "__main__":
    unittest.main()
