"""Unit tests for M3 electronic-text input resolution and step run transaction (Ruling 78, act/02).

synthetic_fixture: true
"""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from pipeline.corpus_compiler.errors import CompileRefused
from pipeline.corpus_compiler.step import run_m3
from pipeline.corpus_compiler.step_offset import (
    M3TextInputs,
    resolve_m3_text_inputs,
    run_m3_text,
)
from pipeline.intake import MANIFEST_TASK_ID
from pipeline.ledger import ids
from pipeline.ledger.fixture_ingest import ingest
from pipeline.ledger.service import LedgerService

REPO_ROOT = Path(__file__).resolve().parents[3]
OCR_FIXTURE_DIR = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"

# 电子文本路线的页单位即 M1 page 标识（第 102 条 Q4①）
E_TEXT_PAGE = "qianyuan_ed01_text"


def _m1_source_manifest(edition_part_id: str) -> dict:
    """构造最小 M1 ``source_manifest``（页单位取自 ``edition_part.pages``）。"""
    return {
        "schema_version": "1.0.0",
        "source_id": "src_qianyuan_ed01",
        "work_title": "乾元秘旨",
        "edition_note": "synthetic",
        "technique_id": "qizheng",
        "rights_status": "synthetic",
        "release_policy": "synthetic",
        "edition_part": {
            "artifact_id": edition_part_id,
            "label": "synthetic",
            "pages": [E_TEXT_PAGE],
        },
        "source_assets": [],
        "files": [],
        "conversion": {"tool": "test_setup", "tool_version": "0.1.0", "inputs": []},
        "content_status": "source_verified",
    }


def _setup_m2_ledger(
    ledger_dir: str,
    *,
    edition_part_id: str = "art_000000000000000000000000000000e1",
    m2_status: str = "succeeded",
    deferred_count: int = 0,
    raw_text: str = "天地玄黄。\n宇宙洪荒。\n日月盈昃，辰宿列张。",
    cleaned_text: str = "天地玄黄。\n宇宙洪荒。\n日月盈昃，辰宿列张。",
    patches: list | None = None,
    omit_patch_set: bool = False,
    omit_raw_text: bool = False,
    omit_cleaned_text: bool = False,
    raw_rev_id: str | None = None,
    cleaned_rev_id: str | None = None,
    patch_rev_id: str | None = None,
    report_rev_id: str | None = None,
) -> tuple[LedgerService, dict]:
    """辅助函数：在临时 Ledger 中构造 M2 前置数据（synthetic_fixture: true）。"""
    service = LedgerService(ledger_dir)
    technique_id = "qizheng"
    proc_run_id = service.create_processing_run("edition_run", edition_part_id, technique_id)

    # 1. 注入 M1 阶段与 raw_text
    cfg_bytes = json.dumps({"stage": "m1"}).encode("utf-8")
    _, cfg_rev = service.put_run_artifact(
        proc_run_id, "configuration", cfg_bytes, producer_module="test_setup", producer_version="0.1.0"
    )
    srun_m1_id = ids.new_id("step_run_id")
    service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": proc_run_id,
            "step_run_id": srun_m1_id,
            "input_artifact_ids": [],
            "technique_profile_id": technique_id,
            "configuration_artifact_id": cfg_rev,
        }
    )

    raw_bytes = raw_text.encode("utf-8")
    _, raw_rev = service.put_artifact(
        srun_m1_id,
        "raw_text",
        raw_bytes,
        artifact_revision_id=raw_rev_id,
        producer_module="test_setup",
        producer_version="0.1.0",
    )
    service.seal_revision(raw_rev)

    # M1 source_manifest（电子文本的页单位来源；第 102 条 Q4①）
    manifest_bytes = json.dumps(
        _m1_source_manifest(edition_part_id), ensure_ascii=False, sort_keys=True
    ).encode("utf-8")
    _, manifest_rev = service.put_artifact(
        srun_m1_id,
        "source_manifest",
        manifest_bytes,
        producer_module="test_setup",
        producer_version="0.1.0",
    )
    service.seal_revision(manifest_rev)

    service.write_checkpoint(
        srun_m1_id,
        edition_part_id=edition_part_id,
        stage="m1",
        completed_tasks=[
            {
                "task_id": MANIFEST_TASK_ID,
                "artifact_revision_id": manifest_rev,
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )

    service.finish_step_run(
        srun_m1_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": proc_run_id,
            "step_run_id": srun_m1_id,
            "status_version": 1,
            "status": "succeeded",
            "output_artifact_ids": [manifest_rev, raw_rev],
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
        },
    )

    # 2. 注入 M2 StepRun
    cfg_m2_bytes = json.dumps({"stage": "m2"}).encode("utf-8")
    _, cfg_m2_rev = service.put_run_artifact(
        proc_run_id, "configuration", cfg_m2_bytes, producer_module="test_setup", producer_version="0.1.0"
    )
    srun_m2_id = ids.new_id("step_run_id")
    input_artifacts = [] if omit_raw_text else [raw_rev]
    service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": proc_run_id,
            "step_run_id": srun_m2_id,
            "input_artifact_ids": input_artifacts,
            "technique_profile_id": technique_id,
            "configuration_artifact_id": cfg_m2_rev,
        }
    )

    m2_outputs = []

    # cleaned_text_revision
    cleaned_rev = None
    if not omit_cleaned_text:
        _, cleaned_rev = service.put_artifact(
            srun_m2_id,
            "cleaned_text_revision",
            cleaned_text.encode("utf-8"),
            artifact_revision_id=cleaned_rev_id,
            producer_module="test_setup",
            producer_version="0.1.0",
        )
        service.seal_revision(cleaned_rev)
        m2_outputs.append(cleaned_rev)

    # deterministic_patch_set
    patch_rev = None
    if not omit_patch_set:
        actual_patches = patches if patches is not None else []
        patches_bytes = json.dumps(actual_patches, ensure_ascii=False, indent=2).encode("utf-8")
        _, patch_rev = service.put_artifact(
            srun_m2_id,
            "deterministic_patch_set",
            patches_bytes,
            artifact_revision_id=patch_rev_id,
            producer_module="test_setup",
            producer_version="0.1.0",
        )
        service.seal_revision(patch_rev)
        m2_outputs.append(patch_rev)

    # sanitization_report
    report_dict = {
        "schema_version": "0.1.0-draft",
        "findings": [],
        "patches": patches or [],
        "summary": {"deferred_count": deferred_count},
        "deferred_count": deferred_count,
    }
    report_bytes = json.dumps(report_dict, ensure_ascii=False, indent=2).encode("utf-8")
    _, report_rev = service.put_artifact(
        srun_m2_id,
        "sanitization_report",
        report_bytes,
        artifact_revision_id=report_rev_id,
        producer_module="test_setup",
        producer_version="0.1.0",
    )
    service.seal_revision(report_rev)
    m2_outputs.append(report_rev)

    # 记录 M2 transformation
    service.record_transformation(
        srun_m2_id,
        operation="sanitize_text",
        tool="pipeline.digitization",
        tool_version="0.1.0",
        configuration_revision_id=cfg_m2_rev,
        input_revision_ids=input_artifacts,
        output_revision_ids=m2_outputs,
    )

    if m2_status == "succeeded":
        # 写入 M2 checkpoint
        service.write_checkpoint(
            srun_m2_id,
            edition_part_id=edition_part_id,
            stage="m2",
            completed_tasks=[
                {
                    "task_id": "sanitize_text",
                    "artifact_revision_id": cleaned_rev or report_rev,
                    "status": "succeeded",
                    "terminal_state": None,
                }
            ],
            human_decisions=[],
            pending_queue=[],
            next_pointer=None,
        )
        service.finish_step_run(
            srun_m2_id,
            {
                "schema_version": "1.0.0",
                "processing_run_id": proc_run_id,
                "step_run_id": srun_m2_id,
                "status_version": 1,
                "status": "succeeded",
                "output_artifact_ids": m2_outputs,
                "validation_report_ids": [],
                "log_artifact_ids": [],
                "failure_artifact_ids": [],
            },
        )
    elif m2_status == "failed":
        service.fail_step_run(srun_m2_id, [], "M2 failed in test setup")
    # if m2_status == "running", 保持 begin 后的初始 running 状态，不完成也不写入 checkpoint

    meta = {
        "edition_part_id": edition_part_id,
        "raw_rev": raw_rev,
        "cleaned_rev": cleaned_rev,
        "patch_rev": patch_rev,
        "report_rev": report_rev,
        "srun_m2_id": srun_m2_id,
        "proc_run_id": proc_run_id,
    }
    return service, meta


class TestStepOffset(unittest.TestCase):
    """测试 M3 电子文本输入解析与 StepRun 事务（act/02）。"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.edition_part_id = "art_000000000000000000000000000000e1"
        self.service, self.meta = _setup_m2_ledger(self.tmp_dir.name, edition_part_id=self.edition_part_id)

    def tearDown(self):
        self.service.close()
        self.tmp_dir.cleanup()

    def test_resolve_m3_text_inputs_success(self):
        """测试正常 M2 产物成功解析并返回 M3TextInputs。"""
        inputs = resolve_m3_text_inputs(self.service, self.edition_part_id)
        self.assertIsInstance(inputs, M3TextInputs)
        self.assertEqual(inputs.edition_part_id, self.edition_part_id)
        self.assertEqual(inputs.raw_text_revision_id, self.meta["raw_rev"])
        self.assertEqual(inputs.cleaned_text_revision_id, self.meta["cleaned_rev"])
        self.assertEqual(inputs.patch_set_revision_id, self.meta["patch_rev"])
        self.assertEqual(inputs.report_revision_id, self.meta["report_rev"])
        self.assertIn("天地玄黄", inputs.cleaned_text)
        self.assertEqual(inputs.sanitization_report["summary"]["deferred_count"], 0)

    def test_non_succeeded_m2_run_rejected(self):
        """护栏用例：当 M2 状态为 running 或 failed 时拒绝解析，断言抛 CompileRefused。"""
        with tempfile.TemporaryDirectory() as td:
            svc_failed, _ = _setup_m2_ledger(td, m2_status="failed")
            with self.assertRaises(CompileRefused) as ctx:
                resolve_m3_text_inputs(svc_failed, self.edition_part_id)
            self.assertIn("P5", str(ctx.exception))
            svc_failed.close()

        with tempfile.TemporaryDirectory() as td2:
            svc_running, _ = _setup_m2_ledger(td2, m2_status="running")
            with self.assertRaises(CompileRefused) as ctx2:
                resolve_m3_text_inputs(svc_running, self.edition_part_id)
            self.assertIn("P5", str(ctx2.exception))
            svc_running.close()

    def test_deferred_sanitization_findings_blocks_compilation(self):
        """第 88 条护栏用例：构造 deferred_count=1 的 M2 报告，断言严禁放行，抛 CompileRefused 且 Ledger 表无变动。"""
        with tempfile.TemporaryDirectory() as td:
            svc, _ = _setup_m2_ledger(td, deferred_count=1)
            # 记录此时 Ledger 行数
            initial_count = svc.store.conn.execute("SELECT count(*) FROM step_runs").fetchone()[0]

            with self.assertRaises(CompileRefused) as ctx:
                resolve_m3_text_inputs(svc, self.edition_part_id)
            self.assertIn("deferred", str(ctx.exception))

            # 验证 Ledger 零写入回滚
            final_count = svc.store.conn.execute("SELECT count(*) FROM step_runs").fetchone()[0]
            self.assertEqual(initial_count, final_count)
            svc.close()

    def test_resolve_m3_text_inputs_missing_patch_set_SCH_001(self):
        """缺失 deterministic_patch_set 时抛出 CompileRefused('SCH_001: ...')。"""
        with tempfile.TemporaryDirectory() as td:
            svc, _ = _setup_m2_ledger(td, omit_patch_set=True)
            with self.assertRaises(CompileRefused) as ctx:
                resolve_m3_text_inputs(svc, self.edition_part_id)
            self.assertIn("SCH_001", str(ctx.exception))
            svc.close()

    def test_resolve_m3_text_inputs_missing_raw_text_SCH_001(self):
        """缺失 raw_text 时抛出 CompileRefused('SCH_001: ...')。"""
        with tempfile.TemporaryDirectory() as td:
            svc, _ = _setup_m2_ledger(td, omit_raw_text=True)
            with self.assertRaises(CompileRefused) as ctx:
                resolve_m3_text_inputs(svc, self.edition_part_id)
            self.assertIn("SCH_001", str(ctx.exception))
            svc.close()

    def test_resolve_m3_text_inputs_missing_cleaned_text_SCH_001(self):
        """缺失 cleaned_text_revision 时抛出 CompileRefused('SCH_001: ...')。"""
        with tempfile.TemporaryDirectory() as td:
            svc, _ = _setup_m2_ledger(td, omit_cleaned_text=True)
            with self.assertRaises(CompileRefused) as ctx:
                resolve_m3_text_inputs(svc, self.edition_part_id)
            self.assertIn("SCH_001", str(ctx.exception))
            svc.close()

    def test_run_m3_text_emits_offset_spans_artifact(self):
        """run_m3_text 产出 corpus_spans 制品，evidence_level 为 offset_level。"""
        summary = run_m3_text(self.service, self.edition_part_id)
        self.assertEqual(summary["status"], "succeeded")
        spans_rev_id = summary["spans_revision_id"]

        # 检查制品在 Ledger 中已封存
        rev = self.service.get_revision(spans_rev_id)
        self.assertEqual(rev["status"], "sealed")
        row = self.service.store.conn.execute(
            "SELECT a.artifact_type FROM artifacts a "
            "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
            "WHERE r.artifact_revision_id=?",
            (spans_rev_id,),
        ).fetchone()
        self.assertEqual(row[0], "corpus_spans")

    def test_run_m3_text_frozen_inputs_include_all_four_m2_artifacts(self):
        """断言 M3 StepRun 的 input_artifact_ids 完整冻结 M2 四类产物修订。"""
        summary = run_m3_text(self.service, self.edition_part_id)
        step_run = self.service.get_step_run(summary["step_run_id"])
        req = json.loads(step_run["request_json"])
        frozen_inputs = set(req["input_artifact_ids"])

        expected = {
            self.meta["raw_rev"],
            self.meta["cleaned_rev"],
            self.meta["patch_rev"],
            self.meta["report_rev"],
        }
        self.assertTrue(expected.issubset(frozen_inputs), f"冻结输入不全: {expected} vs {frozen_inputs}")

    def test_run_m3_text_checkpoints_chain_in_order(self):
        """验证按批次生成的 Checkpoint 链路连续有序。"""
        summary = run_m3_text(self.service, self.edition_part_id, batch_size=1)
        self.assertEqual(summary["status"], "succeeded")
        checkpoints = self.service.list_checkpoints(self.edition_part_id, "m3")
        self.assertGreaterEqual(len(checkpoints), 2)
        # 链上每项包含 completed_tasks
        for cp in checkpoints:
            self.assertIn("completed_tasks", cp["content"])
            self.assertEqual(cp["content"]["completed_tasks"][0]["status"], "succeeded")

    def test_run_m3_text_records_compile_corpus_transformation(self):
        """验证记录了 operation='compile_corpus' 的血缘变换。"""
        summary = run_m3_text(self.service, self.edition_part_id)
        step_run_id = summary["step_run_id"]
        transformations = self.service.list_transformations(step_run_id)
        self.assertGreaterEqual(len(transformations), 1)
        trans = next(t for t in transformations if t["operation"] == "compile_corpus")
        self.assertEqual(trans["tool"], "pipeline.corpus_compiler.step_offset")
        trans_inputs = self.service.store.list_transformation_inputs(trans["id"])
        self.assertIn(self.meta["raw_rev"], trans_inputs)
        trans_outputs = self.service.store.list_transformation_outputs(trans["id"])
        self.assertIn(summary["spans_revision_id"], trans_outputs)

    def test_run_m3_text_configuration_contains_tool_and_evidence_level(self):
        """配置修订包含 tool 与 evidence_level='offset_level'。"""
        summary = run_m3_text(self.service, self.edition_part_id)
        step_run = self.service.get_step_run(summary["step_run_id"])
        req = json.loads(step_run["request_json"])
        cfg_rev_id = req["configuration_artifact_id"]
        cfg_bytes = self.service.objects.get(self.service.get_revision(cfg_rev_id)["sha256"])
        cfg = json.loads(cfg_bytes.decode("utf-8"))
        self.assertEqual(cfg["tool"], "pipeline.corpus_compiler.step_offset")
        self.assertEqual(cfg["evidence_level"], "offset_level")

    def test_run_m3_text_succeeded_summary_keys(self):
        """成功摘要包含必要键。"""
        summary = run_m3_text(self.service, self.edition_part_id)
        required_keys = {"status", "step_run_id", "spans_revision_id", "spans_sha256", "counts"}
        self.assertTrue(required_keys.issubset(summary.keys()))
        self.assertEqual(summary["status"], "succeeded")

    def test_run_m3_text_input_contract_tampered_fails_gracefully(self):
        """输入内容被篡改时优雅失败，走 _fail('input_contract') 记录失败报告。"""
        # 篡改 cleaned_rev 的 Object 存储内容
        rev = self.service.get_revision(self.meta["cleaned_rev"])
        obj_path = self.service.objects.path_for(rev["sha256"])
        obj_path.write_bytes(b"tampered_content_violating_hash")

        summary = run_m3_text(self.service, self.edition_part_id)
        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["failed_check"], "input_contract")

    def test_run_m3_text_already_sealed_stage_refuses_rerun(self):
        """同一阶段已存在 succeeded StepRun 时拒绝重新运行。"""
        run_m3_text(self.service, self.edition_part_id)
        with self.assertRaises(CompileRefused) as ctx:
            run_m3_text(self.service, self.edition_part_id)
        self.assertIn("已封存", str(ctx.exception))

    def test_run_m3_text_empty_input_handled(self):
        """原始文本为空时优雅处理并拒绝编译。"""
        with tempfile.TemporaryDirectory() as td:
            svc, _ = _setup_m2_ledger(td, raw_text="", cleaned_text="")
            with self.assertRaises(CompileRefused):
                run_m3_text(svc, self.edition_part_id)
            svc.close()

    def test_run_m3_text_zero_network_via_socket_guard(self):
        """护栏用例：打补丁拦截 socket 连接，验证全流程零网络。"""
        with patch("socket.socket", side_effect=RuntimeError("P6 铁律拦截：严禁发起任何外部网络连接")):
            summary = run_m3_text(self.service, self.edition_part_id)
            self.assertEqual(summary["status"], "succeeded")

    def test_run_m3_text_spans_bytes_deterministic_between_runs(self):
        """两次运行在相同输入修订下生成相同的 spans_bytes 与 sha256。"""
        fixed_ids = {
            "raw_rev_id": "rev_00000000000000000000000000000001",
            "cleaned_rev_id": "rev_00000000000000000000000000000002",
            "patch_rev_id": "rev_00000000000000000000000000000003",
            "report_rev_id": "rev_00000000000000000000000000000004",
        }
        with tempfile.TemporaryDirectory() as td1:
            svc1, _ = _setup_m2_ledger(td1, edition_part_id=self.edition_part_id, **fixed_ids)
            summary1 = run_m3_text(svc1, self.edition_part_id)
            sha1 = summary1["spans_sha256"]
            svc1.close()

        with tempfile.TemporaryDirectory() as td2:
            svc2, _ = _setup_m2_ledger(td2, edition_part_id=self.edition_part_id, **fixed_ids)
            summary2 = run_m3_text(svc2, self.edition_part_id)
            sha2 = summary2["spans_sha256"]
            self.assertEqual(sha1, sha2)
            svc2.close()

    def test_run_m3_text_batch_size_configuration_respected(self):
        """batch_size 配置有效生效。"""
        # raw_text 有 3 句，batch_size=1 时切为 3 个批次
        summary = run_m3_text(self.service, self.edition_part_id, batch_size=1)
        self.assertEqual(summary["status"], "succeeded")
        self.assertEqual(summary["batches"], 3)

    # ------------------------------------------------- 三件产物与 m3 阶段包（R81b）

    def _revisions_of_type(self, service, step_run_id, artifact_type):
        rows = service.store.conn.execute(
            "SELECT r.artifact_revision_id FROM artifacts a "
            "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
            "WHERE r.step_run_id=? AND a.artifact_type=?",
            (step_run_id, artifact_type),
        ).fetchall()
        return [row[0] for row in rows]

    def _read_doc(self, service, revision_id):
        rev = service.get_revision(revision_id)
        return json.loads(service.objects.get(rev["sha256"]).decode("utf-8"))

    def _m3_stage_package_docs(self, service):
        rows = service.store.conn.execute(
            "SELECT r.artifact_revision_id FROM stage_packages sp "
            "JOIN artifact_revisions r ON r.artifact_id = sp.artifact_id "
            "WHERE sp.stage='m3'"
        ).fetchall()
        return [self._read_doc(service, row[0]) for row in rows]

    def test_run_m3_text_registers_structural_stage_package(self):
        """三件产物各 1 个，且登记 m3 阶段包 gate_profile=structural_only（第 100 条 D2）。"""
        summary = run_m3_text(self.service, self.edition_part_id)
        self.assertEqual(summary["status"], "succeeded")
        step_run_id = summary["step_run_id"]
        for artifact_type in ("corpus_spans", "coverage_report", "corpus_package"):
            revisions = self._revisions_of_type(self.service, step_run_id, artifact_type)
            self.assertEqual(
                len(revisions), 1, "%s 应为恰 1 个，实际 %r" % (artifact_type, revisions)
            )
        packages = self._m3_stage_package_docs(self.service)
        self.assertEqual(len(packages), 1)
        package = packages[0]
        self.assertEqual(package["stage"], "m3")
        self.assertEqual(package["status"], "sealed")
        self.assertEqual(package["payload"]["gate_profile"], "structural_only")
        self.assertEqual(package["payload"]["spans_revision_id"], summary["spans_revision_id"])
        self.assertEqual(
            package["payload"]["coverage"], {E_TEXT_PAGE: 1.0},
            "coverage 为 M1 页标识到实算覆盖率的映射（第 102 条 Q4①）",
        )
        self.assertEqual(package["payload"]["excluded_pages"], {})
        self.assertEqual(package["payload"]["semantic"], "not_evaluated")
        corpus_package = self._read_doc(
            self.service,
            self._revisions_of_type(self.service, step_run_id, "corpus_package")[0],
        )
        self.assertEqual(corpus_package["gate_profile"], "structural_only")
        self.assertEqual(corpus_package["semantic"], "not_evaluated")
        self.assertEqual(corpus_package["coverage"], {E_TEXT_PAGE: 1.0})
        self.assertEqual(corpus_package["excluded_pages"], {})

    def test_run_m3_text_output_resolvable_by_m4(self):
        """跨模块契约护栏：M4 的 resolve_m3_outputs 必须能直接消费真书 M3 输出。"""
        from pipeline.knowledge_extraction.inputs import resolve_m3_outputs

        summary = run_m3_text(self.service, self.edition_part_id)
        outputs = resolve_m3_outputs(self.service, self.edition_part_id)
        self.assertEqual(outputs["spans_revision_id"], summary["spans_revision_id"])
        self.assertEqual(outputs["corpus_package_revision_id"], summary["corpus_package_revision_id"])
        self.assertEqual(outputs["corpus_stage_package_id"], summary["stage_package_id"])
        self.assertEqual(outputs["corpus_stage_package_revision_id"], summary["package_revision_id"])

    def test_run_m3_text_gate_failure_registers_no_stage_package(self):
        """Gate 不过 → 封存失败，且不登记 m3 阶段包、不产出 corpus_package。"""
        import pipeline.corpus_compiler.step_offset as step_offset_module

        real_compile = step_offset_module.compile_offset_spans

        def broken_compile(*args, **kwargs):
            result = real_compile(*args, **kwargs)
            # 令顶层 span_count 与 spans 列表长度不符 → Gate 的 header_counts 判错
            result["spans_doc"]["span_count"] += 1
            return result

        with patch.object(step_offset_module, "compile_offset_spans", side_effect=broken_compile):
            summary = run_m3_text(self.service, self.edition_part_id)

        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["failed_check"], "structural_gate")
        self.assertEqual(self._m3_stage_package_docs(self.service), [])
        self.assertEqual(
            self._revisions_of_type(self.service, summary["step_run_id"], "corpus_package"), []
        )

    def test_run_m3_text_coverage_report_carries_ocr_shape(self):
        """coverage_report 取 OCR 外形，由电子文本 Gate 结果转换得到（第 102 条 Q4③）。

        两条路线都以 ``json.dumps(..., sort_keys=True)`` 落盘，故**落盘键序即排序序**；
        下面的期望值同时是「OCR 同键」的证明（键集与排序后顺序逐一相等）。
        """
        summary = run_m3_text(self.service, self.edition_part_id)
        revisions = self._revisions_of_type(self.service, summary["step_run_id"], "coverage_report")
        self.assertEqual(len(revisions), 1)
        report = self._read_doc(self.service, revisions[0])
        self.assertEqual(
            list(report.keys()),
            ["checks", "gate_profile", "pages", "semantic", "structural"],
        )
        self.assertEqual(report["structural"], "passed")
        self.assertEqual(report["semantic"], "not_evaluated")
        self.assertEqual(report["gate_profile"], "structural_only")
        for check in report["checks"].values():
            self.assertEqual(check["failures"], [])
        page_report = report["pages"][E_TEXT_PAGE]
        self.assertEqual(
            list(page_report.keys()),
            [
                "coverage",
                "gaps",
                "line_count",
                "overlaps",
                "span_count",
                "status",
                "terminal_state",
            ],
        )
        self.assertEqual(page_report["status"], "covered")
        self.assertEqual(page_report["coverage"], 1.0)
        self.assertEqual(page_report["span_count"], summary["counts"]["spans"])
        self.assertEqual(page_report["gaps"], [])
        self.assertEqual(page_report["overlaps"], [])

    def test_run_m3_text_package_key_sets_match_ocr_route(self):
        """下游不得为电子文本另写读取分支：包内键名与键序逐字等于 OCR 路线（第 100 条 D2）。"""
        text_summary = run_m3_text(self.service, self.edition_part_id)
        text_package = self._m3_stage_package_docs(self.service)[0]
        text_corpus_package = self._read_doc(
            self.service,
            self._revisions_of_type(self.service, text_summary["step_run_id"], "corpus_package")[0],
        )
        text_coverage = self._read_doc(
            self.service,
            self._revisions_of_type(self.service, text_summary["step_run_id"], "coverage_report")[0],
        )

        with tempfile.TemporaryDirectory() as td:
            ocr_service = LedgerService(Path(td) / "ledger")
            try:
                ingested = ingest(OCR_FIXTURE_DIR, ocr_service, stages=("m1", "m2"))
                ocr_summary = run_m3(ocr_service, ingested["edition_part_id"])
                ocr_package = self._m3_stage_package_docs(ocr_service)[0]
                ocr_corpus_package = self._read_doc(
                    ocr_service,
                    self._revisions_of_type(
                        ocr_service, ocr_summary["step_run_id"], "corpus_package"
                    )[0],
                )
                ocr_coverage = self._read_doc(
                    ocr_service,
                    self._revisions_of_type(
                        ocr_service, ocr_summary["step_run_id"], "coverage_report"
                    )[0],
                )
            finally:
                ocr_service.close()

        self.assertEqual(list(text_package.keys()), list(ocr_package.keys()))
        self.assertEqual(list(text_package["payload"].keys()), list(ocr_package["payload"].keys()))
        self.assertEqual(list(text_package["manifest"].keys()), list(ocr_package["manifest"].keys()))
        self.assertEqual(
            list(text_package["validation"].keys()), list(ocr_package["validation"].keys())
        )
        self.assertEqual(list(text_package["lineage"].keys()), list(ocr_package["lineage"].keys()))
        self.assertEqual(
            list(text_package["lineage"]["transformations"][0].keys()),
            list(ocr_package["lineage"]["transformations"][0].keys()),
        )
        self.assertEqual(list(text_corpus_package.keys()), list(ocr_corpus_package.keys()))
        self.assertEqual(list(text_coverage.keys()), list(ocr_coverage.keys()))
        self.assertEqual(
            list(next(iter(text_coverage["pages"].values())).keys()),
            list(next(iter(ocr_coverage["pages"].values())).keys()),
        )


if __name__ == "__main__":
    unittest.main()
