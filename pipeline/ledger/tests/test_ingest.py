"""ACT impl-01/05：mini_ed01 经真实 Ledger 写路径灌入（规格 §17、§22.1）的单元测试。

先写本文件，运行 `.venv/bin/python -m unittest discover -s pipeline/ledger/tests -t .`
因 `pipeline.ledger.fixture_ingest` 尚不存在而全红。
所有用例只使用 ``tempfile`` 目录；fixture 只读，绝不写入 fixture。
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline.ledger.errors import DuplicateIdentifier, SchemaViolation
from pipeline.ledger.fixture_ingest import Fixture, ingest
from pipeline.ledger.service import LedgerService

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"


class IngestTestBase(unittest.TestCase):
    """公共脚手架：临时 Ledger 根 + 一次真实灌入。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "ledger"
        self.service = LedgerService(self.root)
        self.addCleanup(self.service.close)
        self.fixture = Fixture(FIXTURE_DIR)

    def count(self, sql, params=()):
        return self.service.store.conn.execute(sql, params).fetchone()[0]


class TestFixtureIngest(IngestTestBase):
    """覆盖 ACT 05：三 StepRun / 九 Checkpoint / 三 Transformation 与 fixture 常量。"""

    def test_ingest_creates_3_step_runs_9_checkpoints_3_transformations(self):
        summary = ingest(FIXTURE_DIR, self.service)
        self.assertEqual(self.count("SELECT COUNT(*) FROM step_runs"), 3)
        self.assertEqual(self.count("SELECT COUNT(*) FROM stage_checkpoints"), 9)
        self.assertEqual(self.count("SELECT COUNT(*) FROM transformations"), 3)
        self.assertEqual(self.count("SELECT COUNT(*) FROM stage_packages"), 3)
        self.assertEqual(self.count("SELECT COUNT(*) FROM processing_runs"), 1)
        self.assertEqual(
            summary["processing_run_id"],
            self.fixture.stage_constants("m1")["processing_run_id"],
        )
        for stage, expected_length in (("m1", 1), ("m2", 3), ("m3", 5)):
            self.assertEqual(
                len(
                    self.service.list_checkpoints(
                        summary["edition_part_id"], stage
                    )
                ),
                expected_length,
            )

    def test_ingest_uses_fixture_constant_ids(self):
        summary = ingest(FIXTURE_DIR, self.service)
        for stage in ("m1", "m2", "m3"):
            constants = self.fixture.stage_constants(stage)
            recorded = summary["stage_packages"][stage]
            self.assertEqual(recorded["stage_package_id"], constants["stage_package_id"])
            self.assertEqual(
                recorded["artifact_revision_id"], constants["package_revision_id"]
            )
            self.assertEqual(recorded["step_run_id"], constants["step_run_id"])
            self.assertEqual(
                recorded["output_revision_id"], constants["output_revision_id"]
            )
            self.assertEqual(
                recorded["output_artifact_id"], constants["output_artifact_id"]
            )
            self.assertEqual(
                recorded["configuration_revision_id"],
                constants["configuration_revision_id"],
            )
            # Ledger 内确实存在这些标识
            self.assertIsNotNone(
                self.service.store.get_stage_package(constants["stage_package_id"])
            )
            self.assertEqual(
                self.service.get_revision(constants["output_revision_id"])["status"],
                "sealed",
            )
            self.assertEqual(
                self.service.get_step_run(constants["step_run_id"])["status"],
                "succeeded",
            )
            # 阶段包修订已封存，且 artifact_type 与 fixture expected 包声明一致
            package_revision = self.service.get_revision(
                constants["package_revision_id"]
            )
            self.assertEqual(package_revision["status"], "sealed")
            self.assertEqual(
                self.service._artifact_type(constants["package_revision_id"]),
                "stage_package",
            )
            self.assertEqual(
                self.service._artifact_type(constants["output_revision_id"]),
                constants["artifact_type"],
            )
        # 三个阶段各一条 Transformation，operation 逐字取自 expected 包
        for stage in ("m1", "m2", "m3"):
            transformation = self.service.store.conn.execute(
                "SELECT operation, tool, tool_version FROM transformations t "
                "JOIN step_runs s ON s.step_run_id = t.step_run_id WHERE s.stage=?",
                (stage,),
            ).fetchone()
            constants = self.fixture.stage_constants(stage)
            self.assertEqual(transformation["operation"], constants["operation"])
            self.assertEqual(transformation["tool"], "tools/build_fixture.py")
            self.assertEqual(transformation["tool_version"], "mini_ed01")

    def test_ingest_twice_raises_ID_002_and_leaves_no_partial_state(self):
        ingest(FIXTURE_DIR, self.service)
        before = {
            table: self.count("SELECT COUNT(*) FROM %s" % table)
            for table in (
                "processing_runs",
                "step_runs",
                "stage_checkpoints",
                "transformations",
                "artifact_revisions",
                "audit_log",
            )
        }
        with self.assertRaises(DuplicateIdentifier) as ctx:
            ingest(FIXTURE_DIR, self.service)
        self.assertEqual(ctx.exception.code, "ID_002")
        after = {
            table: self.count("SELECT COUNT(*) FROM %s" % table)
            for table in before
        }
        self.assertEqual(before, after)

    def test_ingest_page_002_records_human_event_with_terminal_state(self):
        summary = ingest(FIXTURE_DIR, self.service)
        m2_step_run = summary["stage_packages"]["m2"]["step_run_id"]
        events = self.service.store.conn.execute(
            "SELECT r.artifact_revision_id, r.status, r.sha256 "
            "FROM artifact_revisions r JOIN artifacts a "
            "ON a.artifact_id = r.artifact_id "
            "WHERE r.step_run_id=? AND a.artifact_type='human_event'",
            (m2_step_run,),
        ).fetchall()
        self.assertEqual(len(events), 1)
        event_revision_id = events[0]["artifact_revision_id"]
        self.assertEqual(events[0]["status"], "sealed")
        payload = json.loads(
            self.service.objects.get(events[0]["sha256"]).decode("utf-8")
        )
        # 事件内容就是 anomalies.yaml 中 page_002 的那一条
        self.assertEqual(payload["page"], "page_002")
        self.assertEqual(payload["terminal_state"], "known_unrecognizable")
        # page_002 的 terminal_state 写进 completed_tasks
        chain = self.service.list_checkpoints(summary["edition_part_id"], "m2")
        page2_items = [
            item
            for row in chain
            for item in row["content"]["completed_tasks"]
            if item["task_id"] == "page_002"
        ]
        self.assertEqual(len(page2_items), 1)
        self.assertEqual(page2_items[0]["terminal_state"], "known_unrecognizable")
        self.assertEqual(page2_items[0]["status"], "succeeded")
        # 已封存人工决定写入 Checkpoint，并作为 Transformation 的人工决定
        page2_checkpoint = [
            row
            for row in chain
            if any(
                item["task_id"] == "page_002"
                for item in row["content"]["completed_tasks"]
            )
        ][0]
        self.assertIn(
            event_revision_id, page2_checkpoint["content"]["human_decisions"]
        )
        m2_transformation = self.service.store.conn.execute(
            "SELECT t.id FROM transformations t WHERE t.step_run_id=?",
            (m2_step_run,),
        ).fetchone()[0]
        self.assertEqual(
            [
                row[0]
                for row in self.service.store.conn.execute(
                    "SELECT event_revision_id FROM transformation_human_events "
                    "WHERE transformation_id=?",
                    (m2_transformation,),
                ).fetchall()
            ],
            [event_revision_id],
        )

    def test_put_run_artifact_only_configuration_types(self):
        summary = ingest(FIXTURE_DIR, self.service)
        processing_run_id = summary["processing_run_id"]
        with self.assertRaises(SchemaViolation) as ctx:
            self.service.put_run_artifact(
                processing_run_id,
                "ocr_page",
                b"not a run artifact",
                producer_module="tests",
                producer_version="1.0",
            )
        self.assertEqual(ctx.exception.code, "SCH_002")
        # 允许的两类写入即 sealed
        for artifact_type in ("configuration", "technique_profile"):
            _, revision_id = self.service.put_run_artifact(
                processing_run_id,
                artifact_type,
                b'{"stage": "m3"}',
                producer_module="tests",
                producer_version="1.0",
            )
            self.assertEqual(
                self.service.get_revision(revision_id)["status"], "sealed"
            )


if __name__ == "__main__":
    unittest.main()
