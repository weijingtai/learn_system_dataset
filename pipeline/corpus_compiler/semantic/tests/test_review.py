"""act/05 语义层人工裁决与恢复（open_semantic_review / submit_boundary_decision / resume_m3_text_full）具名用例。

synthetic_fixture: true —— M2 前置产物与录制、裁决均为内联合成数据，写入临时 Ledger 目录。
P7：裁决事件一律标 synthetic_fixture: true，不冒充真实专家签发。
"""

import json
import tempfile
import unittest

from pipeline.corpus_compiler.semantic.review import (
    DECISION_SCHEMA,
    DECISION_TYPE,
    DisputesUnresolved,
    SemanticRefused,
    open_semantic_review,
    resume_m3_text_full,
    submit_boundary_decision,
)
from pipeline.ledger import ids
from pipeline.ledger.errors import InvalidResumeToken
from pipeline.ledger.service import LedgerService

EDITION_PART = "art_000000000000000000000000000000e1"
WORK = "qianyuan"

SEG1 = "天地玄黄。\n"
SEG2 = "宇宙洪荒，日月盈昃，辰宿列张。\n"
SEG3 = "寒来暑往秋收冬藏闰余成岁。\n"
SEG4 = "律吕调阳，云腾致雨，露结为霜。"
RAW_TEXT = "天地玄黄。\n【广告】\n" + SEG2 + SEG3 + SEG4
CLEANED_TEXT = SEG1 + SEG2 + SEG3 + SEG4
PATCHES = [
    {
        "patch_id": "patch_001",
        "raw_start": 6,
        "raw_end": 11,
        "cleaned_start": 6,
        "cleaned_end": 6,
        "action": "deletion",
        "basis": "watermark",
    }
]

# w001 双路一致；w002 / w003 双路边界不一致（分歧）
W001_SEGMENTS = [[0, 9], [9, 16]]
W002_A_SEGMENTS = [[0, 7], [7, 14]]
W002_B_SEGMENTS = [[0, 6], [6, 14]]
W003_A_SEGMENTS = [[0, 8], [8, 15]]
W003_B_SEGMENTS = [[0, 7], [7, 15]]


def _response(segments, *, prefix="r"):
    items = [
        {
            "start_offset": start,
            "end_offset": end,
            "reason": "%s%d" % (prefix, index),
        }
        for index, (start, end) in enumerate(segments)
    ]
    return json.dumps({"segments": items}, ensure_ascii=False)


def _recordings_bytes():
    doc = {
        "schema": "m3_boundary_recordings/1",
        "synthetic": True,
        "template_id": "m3_boundary_v1",
        "recordings": [
            {"window_id": "%s_w001" % WORK, "slot": "a", "response": _response(W001_SEGMENTS)},
            {"window_id": "%s_w001" % WORK, "slot": "b", "response": _response(W001_SEGMENTS)},
            {"window_id": "%s_w002" % WORK, "slot": "a", "response": _response(W002_A_SEGMENTS)},
            {"window_id": "%s_w002" % WORK, "slot": "b", "response": _response(W002_B_SEGMENTS)},
            {"window_id": "%s_w003" % WORK, "slot": "a", "response": _response(W003_A_SEGMENTS)},
            {"window_id": "%s_w003" % WORK, "slot": "b", "response": _response(W003_B_SEGMENTS)},
        ],
    }
    return json.dumps(doc, ensure_ascii=False).encode("utf-8")


def _setup_m2_ledger(ledger_dir):
    """在临时 Ledger 中构造 M2 前置产物（P5 succeeded + 无 deferred），返回 service。"""
    service = LedgerService(ledger_dir)
    proc = service.create_processing_run("edition_run", EDITION_PART, "qizheng")

    cfg_m1 = json.dumps({"stage": "m1"}).encode("utf-8")
    _, cfg_m1_rev = service.put_run_artifact(
        proc, "configuration", cfg_m1, producer_module="test_setup", producer_version="0.1.0"
    )
    srun_m1 = ids.new_id("step_run_id")
    service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": proc,
            "step_run_id": srun_m1,
            "input_artifact_ids": [],
            "technique_profile_id": "qizheng",
            "configuration_artifact_id": cfg_m1_rev,
        }
    )
    _, raw_rev = service.put_artifact(
        srun_m1,
        "raw_text",
        RAW_TEXT.encode("utf-8"),
        producer_module="test_setup",
        producer_version="0.1.0",
    )
    service.seal_revision(raw_rev)
    service.finish_step_run(
        srun_m1,
        {
            "schema_version": "1.0.0",
            "processing_run_id": proc,
            "step_run_id": srun_m1,
            "status_version": 1,
            "status": "succeeded",
            "output_artifact_ids": [raw_rev],
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
        },
    )

    cfg_m2 = json.dumps({"stage": "m2"}).encode("utf-8")
    _, cfg_m2_rev = service.put_run_artifact(
        proc, "configuration", cfg_m2, producer_module="test_setup", producer_version="0.1.0"
    )
    srun_m2 = ids.new_id("step_run_id")
    service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": proc,
            "step_run_id": srun_m2,
            "input_artifact_ids": [raw_rev],
            "technique_profile_id": "qizheng",
            "configuration_artifact_id": cfg_m2_rev,
        }
    )
    outputs = []
    for artifact_type, payload in (
        ("cleaned_text_revision", CLEANED_TEXT.encode("utf-8")),
        ("deterministic_patch_set", json.dumps(PATCHES, ensure_ascii=False).encode("utf-8")),
    ):
        _, rev = service.put_artifact(
            srun_m2, artifact_type, payload, producer_module="test_setup", producer_version="0.1.0"
        )
        service.seal_revision(rev)
        outputs.append(rev)

    report = {
        "schema_version": "0.1.0-draft",
        "findings": [],
        "patches": PATCHES,
        "summary": {"deferred_count": 0},
        "deferred_count": 0,
    }
    _, report_rev = service.put_artifact(
        srun_m2,
        "sanitization_report",
        json.dumps(report, ensure_ascii=False).encode("utf-8"),
        producer_module="test_setup",
        producer_version="0.1.0",
    )
    service.seal_revision(report_rev)
    outputs.append(report_rev)

    service.record_transformation(
        srun_m2,
        operation="sanitize_text",
        tool="pipeline.digitization",
        tool_version="0.1.0",
        configuration_revision_id=cfg_m2_rev,
        input_revision_ids=[raw_rev],
        output_revision_ids=outputs,
    )
    service.write_checkpoint(
        srun_m2,
        edition_part_id=EDITION_PART,
        stage="m2",
        completed_tasks=[
            {
                "task_id": "sanitize_text",
                "artifact_revision_id": outputs[0],
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )
    service.finish_step_run(
        srun_m2,
        {
            "schema_version": "1.0.0",
            "processing_run_id": proc,
            "step_run_id": srun_m2,
            "status_version": 1,
            "status": "succeeded",
            "output_artifact_ids": outputs,
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
        },
    )
    return service


def passing_gate(**kwargs):
    """确定性通过桩（act/06 的独立 Gate 在 act/05 阶段尚未落地）。"""
    return {"semantic": "passed", "checks": {}}


def failing_gate(**kwargs):
    """确定性失败桩：用于证明 Gate 结果 load-bearing。"""
    return {"semantic": "failed", "checks": {}}


def make_decision(window_id, *, choice, segments, synthetic=True):
    return {
        "schema": DECISION_SCHEMA,
        "window_id": window_id,
        "decision_type": DECISION_TYPE,
        "choice": choice,
        "segments": [list(pair) for pair in segments],
        "rationale": "合成裁决（synthetic_fixture）",
        "synthetic_fixture": synthetic,
        "actor_ref": "fixture_reviewer",
    }


class TestSemanticReview(unittest.TestCase):
    """边界分歧队列、人工裁决即时落盘与恢复封存（act/05，§17.1）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = _setup_m2_ledger(self.tmp.name)
        self.opened = open_semantic_review(
            self.service, EDITION_PART, recordings=_recordings_bytes()
        )
        self.step_run_id = self.opened["step_run_id"]
        self.resume_token = self.opened["resume_token"]

    def tearDown(self):
        self.service.close()
        self.tmp.cleanup()

    # ---- 内部辅助 ----
    def _my_checkpoints(self):
        return [
            cp
            for cp in self.service.list_checkpoints(EDITION_PART, "m3")
            if cp["content"].get("step_run_id") == self.step_run_id
        ]

    def test_submit_boundary_decision_success(self):
        """合法裁决被接受：写入 human_event 并立即落盘 Checkpoint，返回窗口与事件修订。"""
        decision = make_decision("%s_w002" % WORK, choice="b", segments=W002_B_SEGMENTS)
        before = len(self._my_checkpoints())

        result = submit_boundary_decision(
            self.service, self.step_run_id, self.resume_token, decision
        )

        self.assertEqual(result["window_id"], "%s_w002" % WORK)
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["remaining_disputes"], 1)
        self.assertEqual(len(self._my_checkpoints()), before + 1)

        event_rev = result["event_revision_id"]
        self.assertTrue(event_rev.startswith("rev_"))
        self.assertEqual(self.service.get_revision(event_rev)["status"], "sealed")
        self.assertEqual(
            json.loads(
                self.service.objects.get(self.service.get_revision(event_rev)["sha256"]).decode("utf-8")
            )["synthetic_fixture"],
            True,
        )

    def test_submit_boundary_decision_invalid_token_rejected(self):
        """resume_token 非法时拒绝裁决（抛 InvalidResumeToken）。"""
        decision = make_decision("%s_w002" % WORK, choice="b", segments=W002_B_SEGMENTS)
        with self.assertRaises(InvalidResumeToken):
            submit_boundary_decision(
                self.service, self.step_run_id, "not-a-valid-token", decision
            )
        self.assertEqual(self.service.get_step_run(self.step_run_id)["status"], "awaiting_human")

    def test_submit_boundary_decision_non_disputed_window_rejected(self):
        """对非分歧窗口（双路已一致）提交裁决必须被拒。"""
        agreed = make_decision("%s_w001" % WORK, choice="a", segments=W001_SEGMENTS)
        with self.assertRaises(SemanticRefused):
            submit_boundary_decision(
                self.service, self.step_run_id, self.resume_token, agreed
            )

        unknown = make_decision("%s_w999" % WORK, choice="a", segments=W001_SEGMENTS)
        with self.assertRaises(SemanticRefused):
            submit_boundary_decision(
                self.service, self.step_run_id, self.resume_token, unknown
            )

    def test_checkpoint_written_immediately_after_each_decision(self):
        """第 88 条护栏：每条裁决后 Checkpoint 立即 +1，task_id 为 review:<window_id>。"""
        baseline = len(self._my_checkpoints())

        first = submit_boundary_decision(
            self.service,
            self.step_run_id,
            self.resume_token,
            make_decision("%s_w002" % WORK, choice="b", segments=W002_B_SEGMENTS),
        )
        after_first = self._my_checkpoints()
        self.assertEqual(len(after_first), baseline + 1)

        second = submit_boundary_decision(
            self.service,
            self.step_run_id,
            self.resume_token,
            make_decision("%s_w003" % WORK, choice="a", segments=W003_A_SEGMENTS),
        )
        after_second = self._my_checkpoints()
        self.assertEqual(len(after_second), baseline + 2)

        for result, expected_task in (
            (first, "review:%s_w002" % WORK),
            (second, "review:%s_w003" % WORK),
        ):
            cp = next(
                c
                for c in [after_first[-1], after_second[-1]]
                if c["artifact_revision_id"] == result["checkpoint_revision_id"]
            )
            tasks = cp["content"]["completed_tasks"]
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0]["task_id"], expected_task)
            self.assertEqual(tasks[0]["artifact_revision_id"], result["event_revision_id"])
            self.assertEqual(tasks[0]["status"], "succeeded")

    def test_resume_without_resolving_all_disputes_rejected(self):
        """第 88 条护栏：2 个分歧只裁 1 个时恢复必须阻断，StepRun 维持 awaiting_human。"""
        submit_boundary_decision(
            self.service,
            self.step_run_id,
            self.resume_token,
            make_decision("%s_w002" % WORK, choice="b", segments=W002_B_SEGMENTS),
        )

        with self.assertRaises(DisputesUnresolved):
            resume_m3_text_full(
                self.service, self.step_run_id, self.resume_token, gate=passing_gate
            )

        self.assertEqual(self.service.get_step_run(self.step_run_id)["status"], "awaiting_human")
        self.assertEqual(self.opened["dispute_count"], 2)

    def test_resume_all_resolved_succeeds(self):
        """全部分歧解决后恢复成功；Gate 结果 load-bearing（失败则拒绝且不消费 token）。"""
        submit_boundary_decision(
            self.service,
            self.step_run_id,
            self.resume_token,
            make_decision("%s_w002" % WORK, choice="b", segments=W002_B_SEGMENTS),
        )
        submit_boundary_decision(
            self.service,
            self.step_run_id,
            self.resume_token,
            make_decision("%s_w003" % WORK, choice="a", segments=W003_A_SEGMENTS),
        )

        # Gate 判 failed → 严禁放行，且 StepRun 仍停在 awaiting_human
        with self.assertRaises(SemanticRefused):
            resume_m3_text_full(
                self.service, self.step_run_id, self.resume_token, gate=failing_gate
            )
        self.assertEqual(self.service.get_step_run(self.step_run_id)["status"], "awaiting_human")

        # Gate 判 passed → 恢复并封存
        result = resume_m3_text_full(
            self.service, self.step_run_id, self.resume_token, gate=passing_gate
        )
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["semantic"], "passed")
        self.assertEqual(result["span_count"], 7)

    def test_resume_registers_stage_package_with_structural_and_semantic_profile(self):
        """恢复后登记 m3 StagePackage，gate_profile=structural_and_semantic。"""
        self._resolve_all()
        result = resume_m3_text_full(
            self.service, self.step_run_id, self.resume_token, gate=passing_gate
        )

        package = self._read_package(result["stage_package_revision_id"])
        self.assertEqual(package["stage"], "m3")
        self.assertEqual(package["status"], "sealed")
        self.assertEqual(
            package["payload"]["gate_profile"], "structural_and_semantic"
        )
        self.assertEqual(package["validation"]["passed"], True)
        self.assertTrue(package["stage_package_id"].startswith("pkg_m3_"))

    def test_resume_m3_stage_package_payload_semantic_passed(self):
        """StagePackage payload 的 semantic 与 evidence_level 如实标注。"""
        self._resolve_all()
        result = resume_m3_text_full(
            self.service, self.step_run_id, self.resume_token, gate=passing_gate
        )
        package = self._read_package(result["stage_package_revision_id"])
        self.assertEqual(package["payload"]["semantic"], "passed")
        self.assertEqual(package["payload"]["evidence_level"], "offset_level")
        self.assertEqual(package["payload"]["coverage"], 7)
        self.assertEqual(package["manifest"]["counts"]["spans"], 7)
        self.assertEqual(package["manifest"]["counts"]["disputes"], 2)

    def test_resume_lineage_contains_all_transformations(self):
        """lineage 承载本运行的编译变换，且变换输入输出与制品一致。"""
        self._resolve_all()
        result = resume_m3_text_full(
            self.service, self.step_run_id, self.resume_token, gate=passing_gate
        )
        transformations = self.service.list_transformations(self.step_run_id)
        operations = [t["operation"] for t in transformations]
        self.assertIn("compile_semantic", operations)

        package = self._read_package(result["stage_package_revision_id"])
        lineage_transformations = package["lineage"]["transformations"]
        self.assertEqual(len(lineage_transformations), len(transformations))
        self.assertEqual(
            [t["operation"] for t in lineage_transformations], operations
        )
        semantic_transform = next(
            t for t in lineage_transformations if t["operation"] == "compile_semantic"
        )
        self.assertEqual(
            semantic_transform["output_artifact_revision_ids"],
            [result["spans_revision_id"]],
        )
        self.assertEqual(
            semantic_transform["step_run_id"], self.step_run_id
        )

    def test_resume_step_run_transitions_to_succeeded(self):
        """恢复封存后 StepRun 终态为 succeeded。"""
        self._resolve_all()
        resume_m3_text_full(
            self.service, self.step_run_id, self.resume_token, gate=passing_gate
        )
        step = self.service.get_step_run(self.step_run_id)
        self.assertEqual(step["status"], "succeeded")

    # ---- 内部辅助 ----
    def _resolve_all(self):
        submit_boundary_decision(
            self.service,
            self.step_run_id,
            self.resume_token,
            make_decision("%s_w002" % WORK, choice="b", segments=W002_B_SEGMENTS),
        )
        submit_boundary_decision(
            self.service,
            self.step_run_id,
            self.resume_token,
            make_decision("%s_w003" % WORK, choice="a", segments=W003_A_SEGMENTS),
        )

    def _read_package(self, revision_id):
        revision = self.service.get_revision(revision_id)
        return json.loads(self.service.objects.get(revision["sha256"]).decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
