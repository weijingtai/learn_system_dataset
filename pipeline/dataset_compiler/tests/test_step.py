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

from pipeline.corpus_compiler.step_offset import run_m3_text
from pipeline.corpus_compiler.tests.test_step_offset import _setup_m2_ledger
from pipeline.dataset_compiler import gate, packs
from pipeline.dataset_compiler.canonical import normalized_sha256
from pipeline.dataset_compiler.errors import DatasetRefused
from pipeline.dataset_compiler.inputs import _check_input_references, resolve_m8_inputs
from pipeline.dataset_compiler.step import (
    FAILURE_CHECKS,
    _assemble_frozen_inputs,
    run_m8,
)
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


def _m3_package_with(references):
    """合成最小 m3 包（仅 manifest.input_artifacts，供 _check_input_references 纯校验）。"""
    return {"manifest": {"input_artifacts": list(references)}}


def _etext_m3_package(inputs):
    """合成电子文本形态 m3 包：只有 M2 四类产物，无 source_manifest/页图。"""
    return _m3_package_with(
        [
            {
                "artifact_type": artifact_type,
                "artifact_revision_id": inputs[key],
            }
            for key, artifact_type in (
                ("raw_text_revision_id", "raw_text"),
                ("cleaned_text_revision_id", "cleaned_text_revision"),
                ("deterministic_patch_set_revision_id", "deterministic_patch_set"),
                ("sanitization_report_revision_id", "sanitization_report"),
            )
        ]
    )


def _ocr_m3_package(inputs):
    """合成 OCR 形态 m3 包：source_manifest + ocr_page_set + 逐页 ocr_page。"""
    references = [
        {
            "artifact_type": "source_manifest",
            "artifact_revision_id": inputs["manifest_revision_id"],
        },
        {
            "artifact_type": "ocr_page_set",
            "artifact_revision_id": inputs["ocr_page_set_revision_id"],
        },
    ]
    references.extend(
        {"artifact_type": "ocr_page", "artifact_revision_id": revision_id}
        for revision_id in inputs["page_revision_ids"].values()
    )
    return _m3_package_with(references)


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


class ElectronicTextStepBase(StepTestBase):
    """ACT 15：电子文本路线（offset 档）的 run_m8 脚手架：无页图、无 SourceAsset。

    与 StepTestBase 不同，本类不建 ``self.service = LedgerService(tmp/ledger)``，而是用
    ``_setup_m2_ledger``（git 跟踪的 M2 夹具）现造一个电子文本 Ledger，因此不依赖
    gitignored 的 ``ocr/data_work`` 页图（不引入 skip）。
    """

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m8-step-etext-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.edition_part_id = "art_000000000000000000000000000000e1"
        self.service, self.meta = _setup_m2_ledger(
            self._tmp, edition_part_id=self.edition_part_id
        )
        self.addCleanup(self.service.close)
        summary = run_m3_text(self.service, self.edition_part_id)
        self.assertEqual(summary["status"], "succeeded")

    def _run_etext(self):
        return run_m8(
            self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO"
        )

    def _rewrite_object(self, revision_id, mutate):
        """重写某修订的内容，并同步登记 sha256/size_bytes（保持内容寻址自洽）。

        与 ``_tamper_object``（故意制造哈希不符）相反：本方法让内容与新登记值一致，
        因此冻结校验照常通过，可用来构造「上游包确实带着某种引用」的事实。
        """
        revision = self.service.get_revision(revision_id)
        document = json.loads(self.service.objects.get(revision["sha256"]).decode("utf-8"))
        mutate(document)
        data = json.dumps(document, ensure_ascii=False, sort_keys=True).encode("utf-8")
        sha256, size_bytes = self.service.objects.put(data)
        self.service.store.conn.execute(
            "UPDATE artifact_revisions SET sha256=?, size_bytes=? "
            "WHERE artifact_revision_id=?",
            (sha256, size_bytes, revision_id),
        )

    def _enrich_manifest(self, inputs):
        """把合成夹具的 M1 清单补齐成真书形状（ACT 16 才补规范夹具 manifest.yaml）。

        ``_setup_m2_ledger`` 的清单是 ``release_policy/rights_status = "synthetic"``、
        ``source_assets = []``；真书是 ``reference_and_hash_only`` + 一条六键底本资产
        （``sha256`` = raw_text 修订 sha256，见 ACT 14 背景实样）。不补齐的话，
        运行会在第 7 步 admission 以「发布策略非法: 'synthetic'」失败，
        根本走不到契约之后的编译。
        """
        raw_text_revision = self.service.get_revision(inputs["raw_text_revision_id"])

        def mutate(manifest):
            manifest["release_policy"] = "reference_and_hash_only"
            manifest["rights_status"] = "public_domain"
            manifest["source_assets"] = [
                {
                    "page": "qianyuan_ed01_text",
                    "path_ref": "qianyuan_ed01_text.md",
                    "sha256": raw_text_revision["sha256"],
                    "normalized_sha256": raw_text_revision["sha256"],
                    "original_encoding": "utf-8",
                    "size": raw_text_revision["size_bytes"],
                }
            ]

        self._rewrite_object(inputs["manifest_revision_id"], mutate)

    def _ready(self):
        """解析输入 + 把清单补齐成真书形状，返回 inputs。"""
        inputs = resolve_m8_inputs(self.service, self.edition_part_id)
        self._enrich_manifest(inputs)
        return inputs



class ElectronicTextFrozenInputTests(ElectronicTextStepBase):
    """ACT 15：电子文本路线冻结 M2 四件，不再遍历页/资产（D-W8-15）。"""

    def test_frozen_inputs_electronic_text_exclude_page_and_asset_revisions(self):
        inputs = self._ready()
        result = self._run_etext()
        frozen = self.service._frozen_input_ids(result["step_run_id"])
        self.assertEqual(
            set(frozen),
            {
                inputs["m3_package_revision_id"],
                inputs["spans_revision_id"],
                inputs["manifest_revision_id"],
                inputs["raw_text_revision_id"],
                inputs["cleaned_text_revision_id"],
                inputs["deterministic_patch_set_revision_id"],
                inputs["sanitization_report_revision_id"],
            },
        )
        self.assertEqual(len(frozen), 7)
        self.assertNotIn(None, frozen)
        # 页/资产路径为空：冻结集里不可能混入 None 或页图修订
        self.assertIsNone(inputs["ocr_page_set_revision_id"])
        self.assertEqual(inputs["page_revision_ids"], {})
        self.assertEqual(inputs["asset_revision_ids"], {})

    def test_run_m8_electronic_text_passes_begin_step_run(self):
        result = self._run_etext()
        self.assertIn("step_run_id", result)
        step_run = self.service.get_step_run(result["step_run_id"])
        self.assertIsNotNone(step_run)
        self.assertEqual(step_run["stage"], "m8")
        self.assertIn(step_run["status"], ("succeeded", "failed"))
        # 封存失败（而非 begin 之前崩掉）：check 在闭集内
        if result["status"] == "failed":
            self.assertIn(result["failed_check"], FAILURE_CHECKS)

    def test_input_contract_electronic_text_accepts_m2_references(self):
        self._ready()
        result = self._run_etext()
        # 契约放行：失败点不在 input_contract，且已过 admission 进入编译（两个子包已封存）
        self.assertNotEqual(result.get("failed_check"), "input_contract")
        self.assertEqual(self._artifact_count("source_asset_pack"), 1)
        self.assertEqual(self._artifact_count("evidence_map_pack"), 1)

    def test_input_contract_electronic_text_refuses_ocr_page_reference(self):
        inputs = self._ready()

        def mutate(package):
            package["manifest"]["input_artifacts"].append(
                {
                    "artifact_type": "ocr_page",
                    "artifact_revision_id": "rev_" + "f" * 32,
                }
            )

        self._rewrite_object(inputs["m3_package_revision_id"], mutate)
        result = self._run_etext()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_check"], "input_contract")
        self.assertIn("ocr_page", result["reason"])
        self.assertEqual(self._m8_package_count(), 0)

    def test_input_contract_electronic_text_refuses_raw_text_sha_mismatch(self):
        """ACT 15 三.3：电子文本清单 source_assets 对账的是 raw_text 修订的 sha256。"""
        inputs = self._ready()

        def mutate(manifest):
            manifest["source_assets"][0]["sha256"] = "0" * 64

        self._rewrite_object(inputs["manifest_revision_id"], mutate)
        result = self._run_etext()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_check"], "input_contract")
        self.assertIn("RawText", result["reason"])
        self.assertEqual(self._m8_package_count(), 0)


class GateEvidenceKwargTests(ElectronicTextStepBase):
    """ACT 17 三：step.py 必须把三个 offset 档冻结输入传给独立发布 Gate。"""

    def _spy_gate(self):
        """记录传给 gate.evaluate_publication 的 kwargs，并照常委派原实现。"""
        captured = {}
        original = gate.evaluate_publication

        def spy(**kwargs):
            captured.update(kwargs)
            return original(**kwargs)

        gate.evaluate_publication = spy
        self.addCleanup(setattr, gate, "evaluate_publication", original)
        return captured

    def test_raw_text_binding_receives_kwargs_from_frozen_inputs(self):
        captured = self._spy_gate()
        inputs = self._ready()
        self._run_etext()

        self.assertTrue(captured, "Gate 未被调用")
        self.assertIsInstance(captured.get("raw_text_binding"), dict)
        self.assertRegex(captured["raw_text_binding"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertIsInstance(captured.get("raw_text"), dict)
        self.assertIsInstance(captured["raw_text"].get("text"), str)
        self.assertIsInstance(captured.get("sanitization_report"), dict)

        # 必须取自冻结输入：raw_text_binding.sha256 == 冻结 raw_text 修订的 sha256；
        # raw_text.text 的 UTF-8 字节逐字等于该冻结对象字节（不许现读账本旁路冻结集）。
        frozen_sha256 = self.service.get_revision(inputs["raw_text_revision_id"])["sha256"]
        self.assertEqual(captured["raw_text_binding"]["sha256"], frozen_sha256)
        self.assertEqual(
            captured["raw_text"]["text"].encode("utf-8"),
            self.service.objects.get(frozen_sha256),
        )


    def test_patch_set_and_cleaned_text_receive_kwargs_from_frozen_inputs(self):
        """ACT 18：DeterministicPatchSet / CleanedText 作为冻结输入传给 Gate。"""
        captured = self._spy_gate()
        inputs = self._ready()
        self._run_etext()

        self.assertIsInstance(captured.get("deterministic_patch_set"), list)
        self.assertIsInstance(captured.get("cleaned_text"), dict)
        self.assertIsInstance(captured["cleaned_text"].get("text"), str)

        # 必须取自冻结输入：字节逐字等于冻结对象（不许现读账本旁路冻结集）
        patch_sha = self.service.get_revision(
            inputs["deterministic_patch_set_revision_id"]
        )["sha256"]
        self.assertEqual(
            json.dumps(captured["deterministic_patch_set"], ensure_ascii=False),
            json.dumps(
                json.loads(self.service.objects.get(patch_sha).decode("utf-8")),
                ensure_ascii=False,
            ),
        )
        cleaned_sha = self.service.get_revision(inputs["cleaned_text_revision_id"])["sha256"]
        self.assertEqual(
            captured["cleaned_text"]["text"].encode("utf-8"),
            self.service.objects.get(cleaned_sha),
        )


class OcrRouteGateKwargTests(StepTestBase):
    """ACT 17 三 / ACT 18：OCR 路线 offset 档 kwarg 一律 None（gate 侧行为逐字不变）。"""

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_ocr_route_kwargs_are_none(self):
        captured = {}
        original = gate.evaluate_publication

        def spy(**kwargs):
            captured.update(kwargs)
            return original(**kwargs)

        gate.evaluate_publication = spy
        self.addCleanup(setattr, gate, "evaluate_publication", original)
        self.ready()
        run_m8(self.service, self.edition_part_id, consumption_level="INTERNAL_DEMO")

        self.assertTrue(captured, "Gate 未被调用")
        for name in (
            "raw_text_binding",
            "raw_text",
            "sanitization_report",
            "deterministic_patch_set",
            "cleaned_text",
        ):
            self.assertIn(name, captured)
            self.assertIsNone(captured[name], msg=name)


class FrozenInputAssemblyTests(unittest.TestCase):
    """ACT 15：冻结输入按路线装配（纯函数，两条路线均不读页图）。"""

    @staticmethod
    def _revision(seed):
        return "rev_" + (seed * 32)

    @classmethod
    def _etext_inputs(cls):
        return {
            "route": "electronic_text",
            "m3_package_revision_id": cls._revision("1"),
            "spans_revision_id": cls._revision("2"),
            "manifest_revision_id": cls._revision("3"),
            "ocr_page_set_revision_id": None,
            "page_revision_ids": {},
            "asset_revision_ids": {},
            "raw_text_revision_id": cls._revision("4"),
            "cleaned_text_revision_id": cls._revision("5"),
            "deterministic_patch_set_revision_id": cls._revision("6"),
            "sanitization_report_revision_id": cls._revision("7"),
        }

    @classmethod
    def _ocr_inputs(cls):
        return {
            "route": "ocr",
            "m3_package_revision_id": cls._revision("1"),
            "spans_revision_id": cls._revision("2"),
            "manifest_revision_id": cls._revision("3"),
            "ocr_page_set_revision_id": cls._revision("8"),
            "page_revision_ids": {
                "page_001": cls._revision("a"),
                "page_002": cls._revision("b"),
            },
            "asset_revision_ids": {
                "page_001": cls._revision("c"),
                "page_002": cls._revision("d"),
            },
            "raw_text_revision_id": None,
            "cleaned_text_revision_id": None,
            "deterministic_patch_set_revision_id": None,
            "sanitization_report_revision_id": None,
        }

    @staticmethod
    def _manifest():
        return {"edition_part": {"pages": ["page_001", "page_002"]}}

    def test_frozen_inputs_never_contain_none(self):
        etext = self._etext_inputs()
        frozen = _assemble_frozen_inputs(etext, self._manifest())
        self.assertNotIn(None, frozen)
        # 电子文本冻结集不许混入 ocr_page_set（其值为 None）
        self.assertNotIn(etext["ocr_page_set_revision_id"], frozen)
        self.assertEqual(len(frozen), 7)

        ocr = self._ocr_inputs()
        frozen = _assemble_frozen_inputs(ocr, self._manifest())
        self.assertNotIn(None, frozen)
        self.assertEqual(len(frozen), 8)

        # 必填键为 None → REF_001，消息指明键名
        broken = self._etext_inputs()
        broken["raw_text_revision_id"] = None
        with self.assertRaises(DatasetRefused) as ctx:
            _assemble_frozen_inputs(broken, self._manifest())
        self.assertEqual(ctx.exception.code, "REF_001")
        self.assertIn("raw_text_revision_id", str(ctx.exception))

    def test_ocr_route_frozen_and_contract_unchanged(self):
        ocr = self._ocr_inputs()
        frozen = _assemble_frozen_inputs(ocr, self._manifest())
        self.assertEqual(
            frozen,
            [
                ocr["m3_package_revision_id"],
                ocr["spans_revision_id"],
                ocr["manifest_revision_id"],
                ocr["ocr_page_set_revision_id"],
                ocr["page_revision_ids"]["page_001"],
                ocr["page_revision_ids"]["page_002"],
                ocr["asset_revision_ids"]["page_001"],
                ocr["asset_revision_ids"]["page_002"],
            ],
        )
        package = _ocr_m3_package(ocr)
        _check_input_references("ocr", ocr, package)
        drifted = dict(ocr)
        drifted["manifest_revision_id"] = self._revision("9")
        with self.assertRaises(DatasetRefused) as ctx:
            _check_input_references("ocr", drifted, package)
        self.assertEqual(ctx.exception.code, "REF_001")
        self.assertIn("source_manifest", str(ctx.exception))
        drifted = dict(ocr)
        drifted["ocr_page_set_revision_id"] = self._revision("9")
        with self.assertRaises(DatasetRefused) as ctx:
            _check_input_references("ocr", drifted, package)
        self.assertEqual(ctx.exception.code, "REF_001")
        self.assertIn("ocr_page_set", str(ctx.exception))
        drifted = dict(ocr)
        drifted["page_revision_ids"] = {"page_001": self._revision("a")}
        with self.assertRaises(DatasetRefused):
            _check_input_references("ocr", drifted, package)

    def test_input_contract_electronic_text_accepts_m2_references(self):
        etext = self._etext_inputs()
        package = _etext_m3_package(etext)
        _check_input_references("electronic_text", etext, package)
        drifted = dict(etext)
        drifted["cleaned_text_revision_id"] = self._revision("9")
        with self.assertRaises(DatasetRefused) as ctx:
            _check_input_references("electronic_text", drifted, package)
        self.assertEqual(ctx.exception.code, "REF_001")
        self.assertIn("cleaned_text_revision", str(ctx.exception))

    def test_input_contract_electronic_text_refuses_ocr_page_reference(self):
        etext = self._etext_inputs()
        package = _etext_m3_package(etext)
        package["manifest"]["input_artifacts"].append(
            {"artifact_type": "ocr_page", "artifact_revision_id": self._revision("f")}
        )
        with self.assertRaises(DatasetRefused) as ctx:
            _check_input_references("electronic_text", etext, package)
        self.assertEqual(ctx.exception.code, "REF_001")
        self.assertIn("ocr_page", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
