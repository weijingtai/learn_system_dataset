"""TODO T04B：M7 登记为发布段生产模块的薄适配入口 ``pipeline.assembly.entry:run_m7``。

调度器按 ``legacy_self_driving`` 约定调用 ``(service, edition_part_id, **entry_kwargs)``；
适配层只从 Ledger 事实找出该 EditionPart 最新 succeeded 的 M6 StagePackage，
再原样调用 ``pipeline.assembly.step.run_m7``（创世路径），并补上 ``processing_run_id``。
"""

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.fixture_seed import seed_release_package
from pipeline.ledger.service import LedgerService

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"


class M7EntryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp(prefix="m7_entry_")
        self.addCleanup(shutil.rmtree, tmp, True)
        self.service = LedgerService(Path(tmp) / "ledger")
        self.addCleanup(self.service.close)
        self.manifest = yaml.safe_load((FIXTURE / "manifest.yaml").read_text(encoding="utf-8"))

    def test_entry_runs_genesis_on_latest_m6_package_of_the_edition_part(self):
        from pipeline.assembly.entry import run_m7

        seeded = seed_release_package(self.service, FIXTURE)
        ed01 = self.manifest["editions"][0]
        first = seeded["editions"][ed01["edition_key"]]

        summary = run_m7(
            self.service,
            ed01["edition_part_artifact_id"],
            id_range=self.manifest["id_range"],
        )
        self.assertEqual(summary["status"], "succeeded")
        # owns_processing_run：适配层补齐 processing_run_id（取自 StepRun 事实）
        step = self.service.get_step_run(summary["step_run_id"])
        self.assertEqual(summary["processing_run_id"], step["processing_run_id"])
        # 冻结输入 = 该 EditionPart 的 M6 包（不是别的版次的包）
        self.assertEqual(
            self.service.list_frozen_inputs(summary["step_run_id"]),
            [first["m6_package_revision_id"]],
        )
        # 与直接调用 run_m7 同一产出：Snapshot 逐字节等于 r1 金标
        snapshot = self.service.get_revision(summary["snapshot_revision_id"])
        self.assertEqual(snapshot["status"], "sealed")
        self.assertEqual(
            self.service.read_object(snapshot["sha256"]),
            (FIXTURE / self.manifest["expected"]["round1"]).read_bytes(),
        )

    def test_entry_refuses_without_m6_package_and_writes_nothing(self):
        from pipeline.assembly.entry import run_m7

        before = self.service.count_artifacts("configuration")
        with self.assertRaises(AssemblyRefused) as caught:
            run_m7(self.service, self.manifest["editions"][0]["edition_part_artifact_id"])
        self.assertEqual(caught.exception.code, "REF_001")
        self.assertEqual(self.service.count_artifacts("configuration"), before)
        self.assertEqual(self.service.count_artifacts("canonical_snapshot"), 0)

    def test_entry_passes_base_snapshot_revision_id_for_incremental(self):
        from pipeline.assembly.entry import run_m7

        seed_release_package(self.service, FIXTURE)
        ed01 = self.manifest["editions"][0]
        ed99 = self.manifest["editions"][1]

        r1 = run_m7(
            self.service,
            ed01["edition_part_artifact_id"],
            id_range=self.manifest["id_range"],
        )
        self.assertEqual(r1["status"], "succeeded")

        r2 = run_m7(
            self.service,
            ed99["edition_part_artifact_id"],
            base_snapshot_revision_id=r1["snapshot_revision_id"],
            id_range=self.manifest["id_range"],
        )
        self.assertEqual(r2["status"], "awaiting_human")
        self.assertIsNotNone(r2.get("resume_token"))
        step = self.service.get_step_run(r2["step_run_id"])
        self.assertEqual(r2["processing_run_id"], step["processing_run_id"])


if __name__ == "__main__":
    unittest.main()

