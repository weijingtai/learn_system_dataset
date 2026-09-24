"""M1 事务层单元测试（synthetic_fixture: true）。"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema
import yaml
from referencing import Registry as _RefRegistry, Resource
from referencing.jsonschema import DRAFT202012

from pipeline.intake.errors import IntakeRefused, SourceAssetMissing
from pipeline.intake.step import run_m1
from pipeline.intake.tests.helpers import fixture_source, make_text_file
from pipeline.ledger.service import LedgerService

SCHEMAS_DIR = Path(__file__).resolve().parents[3] / "openspec" / "schemas"


def _validate_schema(schema_name, data):
    """按 L0 Schema 校验对象（注册 ``artifact_ref.schema.json`` 供 ``$ref`` 解析）。"""
    schema = json.loads((SCHEMAS_DIR / (schema_name + ".schema.json")).read_text(encoding="utf-8"))
    artifact_ref = json.loads(
        (SCHEMAS_DIR / "artifact_ref.schema.json").read_text(encoding="utf-8")
    )
    registry = _RefRegistry().with_resource(
        "artifact_ref.schema.json",
        Resource.from_contents(artifact_ref, default_specification=DRAFT202012),
    )
    jsonschema.Draft202012Validator(schema, registry=registry).validate(data)


class TestStep(unittest.TestCase):
    """M1 Ledger 写路径事务测试集。"""

    def setUp(self):
        self.tmp_ledger_dir = tempfile.TemporaryDirectory()
        self.service = LedgerService(self.tmp_ledger_dir.name)
        self.source_info = fixture_source()
        self.edition_part_id = self.source_info["edition_part"]["artifact_id"]
        self.files = [
            {
                "page": "page_001",
                "path_ref": "page_001.txt",
                "data": "太极图说\n天地之初，太极肇判。".encode("utf-8"),
                "sha256": hashlib.sha256("太极图说\n天地之初，太极肇判。".encode("utf-8")).hexdigest(),
                "size": len("太极图说\n天地之初，太极肇判。".encode("utf-8")),
            }
        ]

    def tearDown(self):
        self.service.close()
        self.tmp_ledger_dir.cleanup()

    def test_run_m1_success(self):
        """synthetic_fixture: true，合法输入 → manifest_revision_id, raw_text_revision_ids, step_run_id。"""
        res = run_m1(self.service, self.source_info, self.files, self.edition_part_id)
        self.assertIn("manifest_revision_id", res)
        self.assertIn("raw_text_revision_ids", res)
        self.assertIn("step_run_id", res)
        self.assertTrue(res["manifest_revision_id"].startswith("rev_"))
        self.assertEqual(len(res["raw_text_revision_ids"]), 1)
        self.assertTrue(res["raw_text_revision_ids"][0].startswith("rev_"))
        self.assertTrue(res["step_run_id"].startswith("srun_"))

        # StepRun 终态校验
        step = self.service.get_step_run(res["step_run_id"])
        self.assertIsNotNone(step)
        self.assertEqual(step["status"], "succeeded")

    def test_run_m1_duplicate_refused(self):
        """synthetic_fixture: true，同 edition_part_id 二次运行 → IntakeRefused。"""
        # 第一次运行成功
        res = run_m1(self.service, self.source_info, self.files, self.edition_part_id)
        self.assertIn("step_run_id", res)

        # 第二次运行同一 edition_part_id 被拒
        with self.assertRaises(IntakeRefused) as ctx:
            run_m1(self.service, self.source_info, self.files, self.edition_part_id)
        self.assertIn("M1 已封存", str(ctx.exception))

    def test_run_m1_zero_writes_on_failure(self):
        """synthetic_fixture: true，失败时 Ledger 行数不变。"""
        # 统计失败调用前的各表行数
        table_names = ["artifacts", "artifact_revisions", "step_runs", "processing_runs", "stage_checkpoints"]
        counts_before = {}
        for t in table_names:
            cur = self.service.store.conn.execute(f"SELECT count(*) FROM {t}")
            counts_before[t] = cur.fetchone()[0]

        # 传入非法 source_info 导致校验失败
        bad_source_info = dict(self.source_info)
        del bad_source_info["source_id"]

        with self.assertRaises(IntakeRefused):
            run_m1(self.service, bad_source_info, self.files, self.edition_part_id)

        # 统计失败调用后的各表行数，断言绝对不变（零写入）
        counts_after = {}
        for t in table_names:
            cur = self.service.store.conn.execute(f"SELECT count(*) FROM {t}")
            counts_after[t] = cur.fetchone()[0]

        self.assertEqual(counts_before, counts_after)

    def test_run_m1_raw_text_frozen(self):
        """synthetic_fixture: true，raw_text 修订不可变。"""
        res = run_m1(self.service, self.source_info, self.files, self.edition_part_id)
        raw_revs = res["raw_text_revision_ids"]
        for rev_id in raw_revs:
            rev = self.service.get_revision(rev_id)
            self.assertIsNotNone(rev)
            self.assertEqual(rev["status"], "sealed")
            # 尝试二次封存应被拒绝
            with self.assertRaises(Exception):
                self.service.seal_revision(rev_id)

    def test_run_m1_manifest_sha256(self):
        """synthetic_fixture: true，manifest 内容 sha256 可从 Object Store 取回。"""
        res = run_m1(self.service, self.source_info, self.files, self.edition_part_id)
        manifest_rev_id = res["manifest_revision_id"]
        rev = self.service.get_revision(manifest_rev_id)
        self.assertIsNotNone(rev)

        content_bytes = self.service.objects.get(rev["sha256"])
        self.assertIsNotNone(content_bytes)
        self.assertEqual(hashlib.sha256(content_bytes).hexdigest(), rev["sha256"])

        # 反序列化校验
        manifest_obj = yaml.safe_load(content_bytes.decode("utf-8"))
        self.assertEqual(manifest_obj["source_id"], self.source_info["source_id"])
        self.assertEqual(manifest_obj["content_status"], "machine_extracted")

    def test_run_m1_cli_success(self):
        """synthetic_fixture: true，exit 0，末行 "M1 OK"。"""
        with tempfile.TemporaryDirectory() as tmp_src_dir, tempfile.TemporaryDirectory() as tmp_cli_ledger:
            src_path = Path(tmp_src_dir)
            f_path = make_text_file("page_001.txt", "太极图说\n天地之初，太极肇判。", target_dir=src_path)
            content_bytes = f_path.read_bytes()

            source_dict = fixture_source()
            source_dict["file_sha256"] = hashlib.sha256(content_bytes).hexdigest()
            source_json_path = src_path / "source.json"
            source_json_path.write_text(json.dumps(source_dict, ensure_ascii=False), encoding="utf-8")

            cmd = [
                sys.executable,
                "-m",
                "pipeline.intake",
                "--source-dir",
                str(src_path),
                "--source-json",
                str(source_json_path),
                "--edition-part-id",
                source_dict["edition_part"]["artifact_id"],
                "--ledger-dir",
                tmp_cli_ledger,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"CLI stderr: {proc.stderr}")
            lines = [line.strip() for line in proc.stdout.strip().splitlines() if line.strip()]
            self.assertTrue(lines[-1].startswith("M1 OK"), f"Output: {proc.stdout}")

    def test_run_m1_cli_missing_files(self):
        """synthetic_fixture: true，exit 3，"BLOCKED_SOURCE_ASSET_MISSING"。"""
        with tempfile.TemporaryDirectory() as empty_src_dir, tempfile.TemporaryDirectory() as tmp_cli_ledger:
            src_path = Path(empty_src_dir)
            source_dict = fixture_source()
            source_json_path = src_path / "source.json"
            source_json_path.write_text(json.dumps(source_dict, ensure_ascii=False), encoding="utf-8")

            cmd = [
                sys.executable,
                "-m",
                "pipeline.intake",
                "--source-dir",
                str(src_path),
                "--source-json",
                str(source_json_path),
                "--edition-part-id",
                source_dict["edition_part"]["artifact_id"],
                "--ledger-dir",
                tmp_cli_ledger,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 3)
            combined_output = proc.stdout + proc.stderr
            self.assertIn("BLOCKED_SOURCE_ASSET_MISSING", combined_output)

    def test_run_m1_cli_refused_exit_2(self):
        """synthetic_fixture: true，IntakeRefused 退出码为 2。"""
        with tempfile.TemporaryDirectory() as tmp_src_dir, tempfile.TemporaryDirectory() as tmp_cli_ledger:
            src_path = Path(tmp_src_dir)
            f_path = make_text_file("page_001.txt", "太极图说", target_dir=src_path)
            # 非法 source_dict（缺失必填键 source_id）
            bad_source_dict = fixture_source()
            del bad_source_dict["source_id"]
            source_json_path = src_path / "source.json"
            source_json_path.write_text(json.dumps(bad_source_dict, ensure_ascii=False), encoding="utf-8")

            cmd = [
                sys.executable,
                "-m",
                "pipeline.intake",
                "--source-dir",
                str(src_path),
                "--source-json",
                str(source_json_path),
                "--edition-part-id",
                bad_source_dict["edition_part"]["artifact_id"],
                "--ledger-dir",
                tmp_cli_ledger,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("INTAKE REFUSED", proc.stderr)

    def test_run_m1_registers_stage_package(self):
        """synthetic_fixture: true，M1 自登记恰 1 个 StagePackage（TODO T04A 裁决 1）。"""
        res = run_m1(self.service, self.source_info, self.files, self.edition_part_id)
        step_run_id = res["step_run_id"]
        rows = self.service.list_step_run_revisions(
            step_run_id, artifact_type="stage_package"
        )
        self.assertEqual(len(rows), 1, "M1 必须恰登记 1 个 StagePackage")
        package_revision_id = rows[0]["artifact_revision_id"]
        revision = self.service.get_revision(package_revision_id)
        self.assertEqual(revision["status"], "sealed")
        package = yaml.safe_load(
            self.service.objects.get(revision["sha256"]).decode("utf-8")
        )
        self.assertEqual(package["stage"], "m1")
        self.assertEqual(package["manifest"]["step_run_id"], step_run_id)
        self.assertEqual(package["manifest"]["processing_run_id"], self.service.get_step_run(step_run_id)["processing_run_id"])
        self.assertTrue(package["validation"]["passed"])
        self.assertEqual(package["failures"], [])
        self.assertEqual(
            {
                ref["artifact_revision_id"]
                for ref in package["manifest"]["output_artifacts"]
            },
            {res["manifest_revision_id"], *res["raw_text_revision_ids"]},
        )
        _validate_schema("stage_package", package)
        result = json.loads(self.service.get_step_run(step_run_id)["result_json"])
        self.assertIn(package_revision_id, result["output_artifact_ids"])


if __name__ == "__main__":
    unittest.main()
