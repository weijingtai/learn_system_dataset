"""ACT impl-04/03：薄 M1 页图登记 register_source_assets 的测试。

合成场景：临时目录合成 PNG + 合成 m1 清单（seed_m1_manifest）。
本机真实页图场景用 ``skipUnless(assets_available())``（K2 起本机 0 skipped）。
"""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.dataset_compiler.errors import DatasetRefused
from pipeline.dataset_compiler.shim.m1_shim_source_assets import (
    SourceAssetMissing,
    register_source_assets,
)
from pipeline.dataset_compiler.tests._ledger_helpers import (
    FIXTURE,
    REPO_ASSET_ROOT,
    REPO_ROOT,
    assets_available,
    make_synthetic_png,
    seed_m1_manifest,
    sha256_hex,
    table_counts,
)
from pipeline.ledger.errors import HashMismatch, SchemaViolation
from pipeline.ledger.fixture_ingest import ingest
from pipeline.ledger.service import LedgerService

PAGES = ("page_001", "page_002", "page_003")


def _build_synthetic(tmp, dimensions=None):
    """在 ``tmp`` 下造合成页图与合成清单，灌入 m1，返回 (root, asset_root, manifest)。"""
    root = Path(tmp) / "ledger"
    asset_root = Path(tmp) / "assets"
    asset_root.mkdir(parents=True, exist_ok=True)
    dimensions = dimensions or {page: (12, 10) for page in PAGES}
    assets = []
    for page in PAGES:
        width, height = dimensions[page]
        data = make_synthetic_png(width, height, payload=page.encode("utf-8"))
        (asset_root / ("%s.png" % page)).write_bytes(data)
        assets.append(
            {
                "page": page,
                "path_ref": "assets/%s.png" % page,
                "sha256": sha256_hex(data),
                "width": width,
                "height": height,
            }
        )
    manifest = {
        "source_id": "src_syn_ed01",
        "technique_id": "qizheng",
        "rights_status": "internal",
        "release_policy": "derived_page_images_only",
        "edition_part": {
            "artifact_id": "art_%032x" % 0xABC,
            "pages": list(PAGES),
        },
        "source_assets": assets,
    }
    service = LedgerService(root)
    try:
        seed_m1_manifest(service, manifest)
    finally:
        service.close()
    return root, asset_root, manifest


class ShimSyntheticBase(unittest.TestCase):
    """合成场景脚手架（不预灌 m1，测试自行 seed）。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m8-shim-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.root = Path(self._tmp) / "ledger"
        self.asset_root = Path(self._tmp) / "assets"
        self.asset_root.mkdir()
        self.service = LedgerService(self.root)
        self.addCleanup(self.service.close)
        self.manifest = self._make_manifest()
        self.edition_part_id = self.manifest["edition_part"]["artifact_id"]

    def _make_manifest(self, dimensions=None):
        dimensions = dimensions or {page: (12, 10) for page in PAGES}
        assets = []
        for page in PAGES:
            width, height = dimensions[page]
            data = make_synthetic_png(width, height, payload=page.encode("utf-8"))
            (self.asset_root / ("%s.png" % page)).write_bytes(data)
            assets.append(
                {
                    "page": page,
                    "path_ref": "assets/%s.png" % page,
                    "sha256": sha256_hex(data),
                    "width": width,
                    "height": height,
                }
            )
        return {
            "source_id": "src_syn_ed01",
            "technique_id": "qizheng",
            "rights_status": "internal",
            "release_policy": "derived_page_images_only",
            "edition_part": {
                "artifact_id": "art_%032x" % 0xABC,
                "pages": list(PAGES),
            },
            "source_assets": assets,
        }

    def seed(self, manifest=None):
        self.manifest = manifest if manifest is not None else self.manifest
        return seed_m1_manifest(self.service, self.manifest)


class ShimSuccessTests(ShimSyntheticBase):
    """成功路径。"""

    def test_register_synthetic_assets_succeeds(self):
        self.seed()
        result = register_source_assets(
            self.service, self.edition_part_id, self.asset_root
        )
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(set(result["asset_revision_ids"]), set(PAGES))
        checkpoints = self.service.list_checkpoints(self.edition_part_id, "m1")
        asset_tasks = [
            task["task_id"]
            for checkpoint in checkpoints
            for task in checkpoint["content"]["completed_tasks"]
            if task["task_id"].startswith("source_asset_")
        ]
        self.assertEqual(
            asset_tasks,
            [
                "source_asset_page_001",
                "source_asset_page_002",
                "source_asset_page_003",
            ],
        )
        for revision_id in result["asset_revision_ids"].values():
            row = self.service.get_revision(revision_id)
            self.assertEqual(row["status"], "sealed")
            self.assertEqual(row["rights_scope"], "internal")
            self.assertEqual(self.service._artifact_type(revision_id), "source_asset_page")
        self.assertEqual(
            self.service.get_step_run(result["step_run_id"])["status"], "succeeded"
        )

    def test_register_writes_transformation_and_register_doc(self):
        manifest_revision_id = self.seed()
        result = register_source_assets(
            self.service, self.edition_part_id, self.asset_root
        )
        rev = self.service.get_revision(result["register_revision_id"])
        doc = json.loads(self.service.objects.get(rev["sha256"]).decode("utf-8"))
        self.assertEqual(set(doc.keys()), set(PAGES))
        for page in PAGES:
            self.assertEqual(
                doc[page]["artifact_revision_id"],
                result["asset_revision_ids"][page],
            )
        transformations = self.service.list_transformations(result["step_run_id"])
        self.assertEqual(len(transformations), 1)
        inputs = self.service.store.list_transformation_inputs(
            transformations[0]["id"]
        )
        outputs = self.service.store.list_transformation_outputs(
            transformations[0]["id"]
        )
        self.assertEqual(inputs, [manifest_revision_id])
        for revision_id in result["asset_revision_ids"].values():
            self.assertIn(revision_id, outputs)
        self.assertIn(result["register_revision_id"], outputs)


class ShimRefusalTests(ShimSyntheticBase):
    """begin 之前的拒绝路径：无写入、异常类型与消息。"""

    def test_missing_asset_raises_blocked_and_no_writes(self):
        self.seed()
        (self.asset_root / "page_003.png").unlink()
        before = table_counts(self.service)
        with self.assertRaises(SourceAssetMissing) as ctx:
            register_source_assets(self.service, self.edition_part_id, self.asset_root)
        self.assertEqual(ctx.exception.code, "SRC_001")
        self.assertTrue(str(ctx.exception).startswith("BLOCKED_SOURCE_ASSET_MISSING "))
        self.assertIn("assets/page_003.png", str(ctx.exception))
        self.assertEqual(table_counts(self.service), before)

    def test_hash_mismatch_SRC_003_no_writes(self):
        self.seed()
        path = self.asset_root / "page_002.png"
        path.write_bytes(path.read_bytes() + b"\x00")
        before = table_counts(self.service)
        with self.assertRaises(HashMismatch) as ctx:
            register_source_assets(self.service, self.edition_part_id, self.asset_root)
        self.assertEqual(ctx.exception.code, "SRC_003")
        self.assertEqual(table_counts(self.service), before)

    def test_png_size_mismatch_SRC_003_no_writes(self):
        manifest = copy.deepcopy(self.manifest)
        for item in manifest["source_assets"]:
            if item["page"] == "page_001":
                item["width"] = item["width"] + 1
        self.seed(manifest)
        before = table_counts(self.service)
        with self.assertRaises(HashMismatch) as ctx:
            register_source_assets(self.service, self.edition_part_id, self.asset_root)
        self.assertEqual(ctx.exception.code, "SRC_003")
        self.assertIn("尺寸", str(ctx.exception))
        self.assertEqual(table_counts(self.service), before)

    def test_non_png_SCH_002_no_writes(self):
        data = b"not a png at all"
        (self.asset_root / "page_001.png").write_bytes(data)
        manifest = copy.deepcopy(self.manifest)
        for item in manifest["source_assets"]:
            if item["page"] == "page_001":
                item["sha256"] = sha256_hex(data)
        self.seed(manifest)
        before = table_counts(self.service)
        with self.assertRaises(SchemaViolation) as ctx:
            register_source_assets(self.service, self.edition_part_id, self.asset_root)
        self.assertEqual(ctx.exception.code, "SCH_002")
        self.assertEqual(table_counts(self.service), before)

    def test_second_registration_refused(self):
        self.seed()
        register_source_assets(self.service, self.edition_part_id, self.asset_root)
        with self.assertRaises(DatasetRefused) as ctx:
            register_source_assets(self.service, self.edition_part_id, self.asset_root)
        self.assertIn("SourceAsset 已登记", str(ctx.exception))

    def test_m1_missing_refused_REF_001(self):
        with self.assertRaises(DatasetRefused) as ctx:
            register_source_assets(self.service, self.edition_part_id, self.asset_root)
        self.assertEqual(ctx.exception.code, "REF_001")


class ShimFailureSealingTests(ShimSyntheticBase):
    """begin 之后的异常封存。"""

    def test_post_begin_exception_seals_failure(self):
        self.seed()
        original = LedgerService.record_transformation

        def boom(self, *args, **kwargs):
            raise RuntimeError("模拟 register_source_assets 写失败")

        LedgerService.record_transformation = boom
        try:
            result = register_source_assets(
                self.service, self.edition_part_id, self.asset_root
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failed_check"], "internal")
            self.assertEqual(
                self.service.get_step_run(result["step_run_id"])["status"], "failed"
            )
            failure = self.service.get_revision(result["failure_revision_id"])
            self.assertEqual(failure["status"], "sealed")
        finally:
            LedgerService.record_transformation = original


class ShimFixtureTests(unittest.TestCase):
    """本机真实页图场景（0 skipped）与 m3 输入解析不受影响。"""

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_fixture_real_assets_when_available(self):
        tmp = tempfile.mkdtemp(prefix="m8-shim-real-")
        try:
            service = LedgerService(Path(tmp) / "ledger")
            try:
                summary = ingest(FIXTURE, service, stages=("m1", "m2"))
                edition_part_id = summary["edition_part_id"]
                result = register_source_assets(
                    service, edition_part_id, REPO_ASSET_ROOT
                )
                self.assertEqual(result["status"], "succeeded")
                manifest = yaml.safe_load((FIXTURE / "manifest.yaml").read_bytes())
                expected = {
                    item["page"]: item["sha256"]
                    for item in manifest["source_assets"]
                }
                for page, revision_id in result["asset_revision_ids"].items():
                    self.assertEqual(
                        service.get_revision(revision_id)["sha256"], expected[page]
                    )
            finally:
                service.close()
        finally:
            shutil.rmtree(tmp, True)

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_register_assets_keeps_m3_input_resolution(self):
        from pipeline.corpus_compiler.inputs import resolve_m3_inputs

        tmp = tempfile.mkdtemp(prefix="m8-shim-m3keep-")
        try:
            service = LedgerService(Path(tmp) / "ledger")
            try:
                summary = ingest(FIXTURE, service, stages=("m1", "m2"))
                edition_part_id = summary["edition_part_id"]
                before = resolve_m3_inputs(service, edition_part_id)[
                    "manifest_revision_id"
                ]
                register_source_assets(service, edition_part_id, REPO_ASSET_ROOT)
                after = resolve_m3_inputs(service, edition_part_id)[
                    "manifest_revision_id"
                ]
                self.assertEqual(before, after)
            finally:
                service.close()
        finally:
            shutil.rmtree(tmp, True)


class ShimCliTests(unittest.TestCase):
    """CLI 退出码：成功 0；空 asset-root 3（BLOCKED_SOURCE_ASSET_MISSING）。"""

    def _run_cli(self, root, asset_root, edition_part_id):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "pipeline.dataset_compiler.shim.m1_shim_source_assets",
                "--root",
                str(root),
                "--edition-part",
                edition_part_id,
                "--asset-root",
                str(asset_root),
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )

    def test_cli_exit_codes(self):
        tmp = tempfile.mkdtemp(prefix="m8-shim-cli-")
        try:
            root, asset_root, manifest = _build_synthetic(tmp)
            edition_part_id = manifest["edition_part"]["artifact_id"]
            proc = self._run_cli(root, asset_root, edition_part_id)
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue(proc.stdout.strip().splitlines()[-1].startswith("ASSETS OK"))

            empty = Path(tmp) / "empty"
            empty.mkdir()
            root2, asset_root2, manifest2 = _build_synthetic(Path(tmp) / "second")
            proc2 = self._run_cli(
                root2, empty, manifest2["edition_part"]["artifact_id"]
            )
            self.assertEqual(proc2.returncode, 3, msg=proc2.stderr)
            self.assertTrue(
                proc2.stdout.strip().splitlines()[0].startswith(
                    "BLOCKED_SOURCE_ASSET_MISSING"
                )
            )
        finally:
            shutil.rmtree(tmp, True)


if __name__ == "__main__":
    unittest.main()
