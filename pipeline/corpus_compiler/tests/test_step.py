"""ACT impl-02/03：run_m3 在真实 Ledger 上的集成测试（规格 §17、§17.1）。

统一脚手架：tempfile 目录 → LedgerService(root/"ledger") →
ingest(FIXTURE, service, stages=("m1","m2")) → run_m3。

所有用例只使用 tempfile 目录；fixture 只读，绝不写入 fixture。
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.corpus_compiler.compiler import compile_structural
from pipeline.corpus_compiler.errors import CompileRefused
from pipeline.corpus_compiler.inputs import resolve_m3_inputs
from pipeline.ledger.errors import (
    NotConsumable,
    SchemaViolation,
)
from pipeline.ledger.fixture_ingest import Fixture, ingest
from pipeline.ledger.service import LedgerService

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
SCHEMA_DIR = REPO_ROOT / "openspec" / "schemas"


def _load_fixture_yaml(name):
    with open(FIXTURE_DIR / name, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_fixture_bytes(name):
    return (FIXTURE_DIR / name).read_bytes()


class StepTestBase(unittest.TestCase):
    """公共脚手架：临时 Ledger + 灌入 m1/m2 + 运行 run_m3。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m3-step-test-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.root = Path(self._tmp) / "ledger"
        self.service = LedgerService(self.root)
        self.addCleanup(self.service.close)
        self.fixture = Fixture(FIXTURE_DIR)
        self.summary = ingest(FIXTURE_DIR, self.service, stages=("m1", "m2"))
        self.edition_part_id = self.summary["edition_part_id"]

    def count(self, sql, params=()):
        return self.service.store.conn.execute(sql, params).fetchone()[0]

    def _tamper_object(self, revision_id):
        """篡改某修订对应的对象字节：翻转其中一个十六进制字符（保持文本可解析）。

        用于模拟「Object Store 中的物理内容与 Ledger 登记的 sha256 不符」——
        即 J2 独立验收发现的冻结输入被篡改场景（J3 返工 C1/C2/C4）。
        """
        rev = self.service.get_revision(revision_id)
        path = self.service.objects.path_for(rev["sha256"])
        text = path.read_text(encoding="utf-8")
        for i, ch in enumerate(text):
            if ch in "0123456789abcdef":
                new_ch = "1" if ch == "0" else "0"
                text = text[:i] + new_ch + text[i + 1:]
                break
        else:
            text += " "
        path.write_text(text, encoding="utf-8")


class TestRunM3Succeeds(StepTestBase):
    """run_m3 成功路径：status succeeded、counts、spans_sha256、StepRun succeeded。"""

    def test_run_m3_on_fixture_succeeds(self):
        from pipeline.corpus_compiler.step import run_m3

        result = run_m3(self.service, self.edition_part_id)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["counts"], {"spans": 43, "batches": 5})
        golden_sha = "ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef"
        self.assertEqual(result["spans_sha256"], golden_sha)
        step_run = self.service.get_step_run(result["step_run_id"])
        self.assertEqual(step_run["status"], "succeeded")

    def test_spans_revision_bytes_equal_fixture_spans_yaml(self):
        from pipeline.corpus_compiler.step import run_m3

        result = run_m3(self.service, self.edition_part_id)
        revision = self.service.get_revision(result["spans_revision_id"])
        got = self.service.objects.get(revision["sha256"])
        golden = _load_fixture_bytes("spans.yaml")
        self.assertEqual(got, golden)

    def test_frozen_inputs_exactly_resolved(self):
        from pipeline.corpus_compiler.step import run_m3

        result = run_m3(self.service, self.edition_part_id)
        frozen = set(self.service._frozen_input_ids(result["step_run_id"]))
        # 应包含：ocr_page_set + manifest + 三页 OCR + page_002 人工事件 = 6 个
        self.assertEqual(len(frozen), 6)

    def test_five_checkpoints_one_per_batch_chained(self):
        from pipeline.corpus_compiler.step import run_m3

        result = run_m3(self.service, self.edition_part_id)
        chain = self.service.list_checkpoints(self.edition_part_id, "m3")
        self.assertEqual(len(chain), 5)
        # prev 指针成链
        self.assertIsNone(chain[0]["prev_checkpoint_revision_id"])
        for prev, cur in zip(chain, chain[1:]):
            self.assertEqual(
                cur["prev_checkpoint_revision_id"], prev["artifact_revision_id"]
            )
        # task_id 等于批号
        for cp in chain:
            task_ids = [t["task_id"] for t in cp["content"]["completed_tasks"]]
            self.assertEqual(len(task_ids), 1)
            self.assertTrue(task_ids[0].startswith("sanche_b"))

    def test_stage_package_validates_schema_and_lineage(self):
        from pipeline.corpus_compiler.step import run_m3

        result = run_m3(self.service, self.edition_part_id)
        # 读取 StagePackage 内容
        pkg_rev = self.service.get_revision(result["package_revision_id"])
        pkg_bytes = self.service.objects.get(pkg_rev["sha256"])
        pkg = json.loads(pkg_bytes)

        # 过 Schema 校验
        import jsonschema
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT202012

        with open(SCHEMA_DIR / "stage_package.schema.json", encoding="utf-8") as fh:
            schema = json.load(fh)
        with open(SCHEMA_DIR / "artifact_ref.schema.json", encoding="utf-8") as fh:
            artifact_ref = json.load(fh)
        registry = Registry().with_resource(
            "artifact_ref.schema.json",
            Resource.from_contents(artifact_ref, default_specification=DRAFT202012),
        )
        validator = jsonschema.Draft202012Validator(schema, registry=registry)
        validator.validate(pkg)

        # lineage 输入集合 == frozen_inputs
        lineage_inputs = {
            ref["artifact_revision_id"]
            for ref in pkg["manifest"]["input_artifacts"]
        }
        frozen = set(self.service._frozen_input_ids(result["step_run_id"]))
        self.assertEqual(lineage_inputs, frozen)

        # content_sha256 == spans 哈希
        golden_sha = "ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef"
        self.assertEqual(pkg["manifest"]["content_sha256"], golden_sha)

    def test_config_records_gate_profile_and_batch_size(self):
        from pipeline.corpus_compiler.step import run_m3

        result = run_m3(self.service, self.edition_part_id)
        config_rev = self.service.get_revision(result["configuration_revision_id"])
        config = json.loads(self.service.objects.get(config_rev["sha256"]))
        self.assertEqual(config["gate_profile"], "structural_only")
        self.assertEqual(config["batch_size"], 10)


class TestRunM3Refusal(StepTestBase):
    """run_m3 拒绝路径：M2 缺失、M3 已封存。"""

    def test_refuses_when_m2_missing(self):
        from pipeline.corpus_compiler.step import run_m3
        from pipeline.ledger.fixture_ingest import ingest as do_ingest

        # 只灌 m1
        tmp2 = tempfile.mkdtemp(prefix="m3-refuse-")
        self.addCleanup(shutil.rmtree, tmp2, True)
        svc2 = LedgerService(Path(tmp2) / "ledger")
        self.addCleanup(svc2.close)
        sum2 = do_ingest(FIXTURE_DIR, svc2, stages=("m1",))
        with self.assertRaises(CompileRefused) as ctx:
            run_m3(svc2, sum2["edition_part_id"])
        self.assertIn("M2", str(ctx.exception))
        # Ledger 中无 m3 StepRun、无新配置修订
        m3_steps = svc2.store.conn.execute(
            "SELECT COUNT(*) FROM step_runs WHERE stage='m3'"
        ).fetchone()[0]
        self.assertEqual(m3_steps, 0)

    def test_refuses_second_run_when_m3_sealed(self):
        from pipeline.corpus_compiler.step import run_m3

        run_m3(self.service, self.edition_part_id)
        with self.assertRaises(CompileRefused) as ctx:
            run_m3(self.service, self.edition_part_id)
        self.assertIn("M3", str(ctx.exception))


class TestRunM3Failure(StepTestBase):
    """run_m3 失败封存路径：输入哈希不匹配、Gate 失败、畸形页名、deferred 终态。"""

    def test_page_hash_mismatch_fails_step_run(self):
        from pipeline.corpus_compiler import step as step_mod

        original_resolve = step_mod.resolve_m3_inputs

        def tampered_resolve(reader, edition_part_id):
            result = original_resolve(reader, edition_part_id)
            # 交换 page_001 和 page_003 的修订 ID
            prids = result["page_revision_ids"]
            prids["page_001"], prids["page_003"] = prids["page_003"], prids["page_001"]
            return result

        step_mod.resolve_m3_inputs = tampered_resolve
        try:
            result = step_mod.run_m3(self.service, self.edition_part_id)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failed_check"], "input_contract")
            # 失败修订已 sealed
            self.assertIsNotNone(
                self.service.get_revision(result["failure_revision_id"])
            )
            # 无 m3 StagePackage
            self.assertNotIn("stage_package_id", result)
        finally:
            step_mod.resolve_m3_inputs = original_resolve

    def test_gate_failure_fails_step_run(self):
        from pipeline.corpus_compiler import step as step_mod

        original_compile = step_mod.compile_structural

        def tampered_compile(**kwargs):
            result = original_compile(**kwargs)
            result["spans"] = result["spans"][:-1]
            result["spans_doc"]["spans"] = result["spans"]
            result["spans_doc"]["span_count"] = len(result["spans"])
            from pipeline.corpus_compiler.serialize import dump_yaml
            import hashlib
            result["spans_bytes"] = dump_yaml(result["spans_doc"])
            result["spans_sha256"] = hashlib.sha256(result["spans_bytes"]).hexdigest()
            return result

        step_mod.compile_structural = tampered_compile
        try:
            result = step_mod.run_m3(self.service, self.edition_part_id)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failed_check"], "structural_gate")
            self.assertNotIn("stage_package_id", result)
        finally:
            step_mod.compile_structural = original_compile

    def test_malformed_page_name_fails_input_contract(self):
        from pipeline.corpus_compiler import step as step_mod

        original_resolve = step_mod.resolve_m3_inputs

        def tampered_resolve(reader, edition_part_id):
            result = original_resolve(reader, edition_part_id)
            # 把 page_002 改名为 page_2（格式非法）
            prids = result["page_revision_ids"]
            if "page_002" in prids:
                prids["page_2"] = prids.pop("page_002")
            return result

        step_mod.resolve_m3_inputs = tampered_resolve
        try:
            result = step_mod.run_m3(self.service, self.edition_part_id)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failed_check"], "input_contract")
        finally:
            step_mod.resolve_m3_inputs = original_resolve

    def test_deferred_terminal_state_fails_step_run(self):
        from pipeline.corpus_compiler import step as step_mod

        original_resolve = step_mod.resolve_m3_inputs

        def tampered_resolve(reader, edition_part_id):
            result = original_resolve(reader, edition_part_id)
            result["terminal_states"]["page_002"] = "deferred"
            return result

        step_mod.resolve_m3_inputs = tampered_resolve
        try:
            result = step_mod.run_m3(self.service, self.edition_part_id)
            self.assertEqual(result["status"], "failed")
            self.assertIn(result["failed_check"], ("compile", "input_contract"))
        finally:
            step_mod.resolve_m3_inputs = original_resolve


class TestRunM3J3Rework(StepTestBase):
    """J3 返工（act/05）：冻结输入完整性、终态严格比对、begin 后异常封存。"""

    def test_manifest_object_tamper_fails_input_contract(self):
        from pipeline.corpus_compiler.step import run_m3

        inputs = resolve_m3_inputs(self.service, self.edition_part_id)
        self._tamper_object(inputs["manifest_revision_id"])
        result = run_m3(self.service, self.edition_part_id)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_check"], "input_contract")
        failure_rev = self.service.get_revision(result["failure_revision_id"])
        self.assertEqual(failure_rev["status"], "sealed")
        self.assertNotIn("stage_package_id", result)
        count = self.service.store.conn.execute("select count(*) from stage_packages where stage='m3'").fetchone()[0]
        self.assertEqual(count, 0)

    def test_page_set_object_tamper_fails_input_contract(self):
        from pipeline.corpus_compiler.step import run_m3

        inputs = resolve_m3_inputs(self.service, self.edition_part_id)
        self._tamper_object(inputs["ocr_page_set_revision_id"])
        result = run_m3(self.service, self.edition_part_id)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_check"], "input_contract")
        failure_rev = self.service.get_revision(result["failure_revision_id"])
        self.assertEqual(failure_rev["status"], "sealed")
        self.assertNotIn("stage_package_id", result)
        count = self.service.store.conn.execute("select count(*) from stage_packages where stage='m3'").fetchone()[0]
        self.assertEqual(count, 0)

    def test_human_event_object_tamper_fails_input_contract(self):
        from pipeline.corpus_compiler.step import run_m3

        inputs = resolve_m3_inputs(self.service, self.edition_part_id)
        self.assertTrue(inputs["human_event_revision_ids"])
        self._tamper_object(inputs["human_event_revision_ids"][0])
        result = run_m3(self.service, self.edition_part_id)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_check"], "input_contract")
        failure_rev = self.service.get_revision(result["failure_revision_id"])
        self.assertEqual(failure_rev["status"], "sealed")
        self.assertNotIn("stage_package_id", result)
        count = self.service.store.conn.execute("select count(*) from stage_packages where stage='m3'").fetchone()[0]
        self.assertEqual(count, 0)

    def test_terminal_states_mismatch_fails_input_contract(self):
        from pipeline.corpus_compiler import step as step_mod

        original_resolve = step_mod.resolve_m3_inputs

        def tampered_resolve(reader, edition_part_id):
            result = original_resolve(reader, edition_part_id)
            result["terminal_states"] = {}
            return result

        step_mod.resolve_m3_inputs = tampered_resolve
        try:
            result = step_mod.run_m3(self.service, self.edition_part_id)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failed_check"], "input_contract")
        finally:
            step_mod.resolve_m3_inputs = original_resolve

    def test_page_set_entry_missing_fails_input_contract(self):
        from pipeline.corpus_compiler import step as step_mod

        original_resolve = step_mod.resolve_m3_inputs

        def tampered_resolve(reader, edition_part_id):
            result = original_resolve(reader, edition_part_id)
            result["page_revision_ids"].pop("page_001", None)
            return result

        step_mod.resolve_m3_inputs = tampered_resolve
        try:
            result = step_mod.run_m3(self.service, self.edition_part_id)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failed_check"], "input_contract")
        finally:
            step_mod.resolve_m3_inputs = original_resolve

    def test_post_begin_exception_seals_failure(self):
        from pipeline.corpus_compiler import step as step_mod

        original = LedgerService.record_transformation

        def boom(self, *args, **kwargs):
            raise RuntimeError("模拟 record_transformation 失败")

        LedgerService.record_transformation = boom
        try:
            result = step_mod.run_m3(self.service, self.edition_part_id)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failed_check"], "internal")
            step_run = self.service.get_step_run(result["step_run_id"])
            self.assertEqual(step_run["status"], "failed")
            failure_rev = self.service.get_revision(result["failure_revision_id"])
            self.assertEqual(failure_rev["status"], "sealed")
            self.assertNotIn("stage_package_id", result)
            count = self.service.store.conn.execute("select count(*) from stage_packages where stage='m3'").fetchone()[0]
            self.assertEqual(count, 0)
        finally:
            LedgerService.record_transformation = original

    def test_pre_begin_refusal_type_preserved(self):
        from pipeline.corpus_compiler.step import run_m3
        from pipeline.ledger.fixture_ingest import ingest as do_ingest

        tmp2 = tempfile.mkdtemp(prefix="m3-refusal-type-")
        self.addCleanup(shutil.rmtree, tmp2, True)
        svc2 = LedgerService(Path(tmp2) / "ledger")
        self.addCleanup(svc2.close)
        sum2 = do_ingest(FIXTURE_DIR, svc2, stages=("m1",))
        with self.assertRaises(CompileRefused) as ctx:
            run_m3(svc2, sum2["edition_part_id"])
        self.assertFalse(str(ctx.exception).startswith("M3 编译异常"))


class TestCLIExitCodes(unittest.TestCase):
    """__main__.py CLI 退出码：成功 0、只灌 m1 → 2。"""

    def test_cli_success_exit_0(self):
        tmp = tempfile.mkdtemp(prefix="m3-cli-")
        try:
            svc = LedgerService(Path(tmp) / "ledger")
            ingest(FIXTURE_DIR, svc, stages=("m1", "m2"))
            svc.close()
            proc = subprocess.run(
                [
                    sys.executable, "-m", "pipeline.corpus_compiler",
                    "--root", str(Path(tmp) / "ledger"), "--edition-part",
                    "art_000000000000000000000000000000e1",
                ],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            self.assertEqual(proc.returncode, 0)
            self.assertTrue(proc.stdout.strip().startswith("M3 OK"))
        finally:
            shutil.rmtree(tmp, True)

    def test_cli_refused_exit_2(self):
        tmp = tempfile.mkdtemp(prefix="m3-cli-refuse-")
        try:
            svc = LedgerService(Path(tmp) / "ledger")
            ingest(FIXTURE_DIR, svc, stages=("m1",))
            svc.close()
            proc = subprocess.run(
                [
                    sys.executable, "-m", "pipeline.corpus_compiler",
                    "--root", str(Path(tmp) / "ledger"), "--edition-part",
                    "art_000000000000000000000000000000e1",
                ],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            self.assertEqual(proc.returncode, 2)
            self.assertTrue(proc.stdout.strip().startswith("M3 REFUSED"))
        finally:
            shutil.rmtree(tmp, True)


if __name__ == "__main__":
    unittest.main()
