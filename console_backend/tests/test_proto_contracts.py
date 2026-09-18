"""Protobuf 契约自检测试（Contract-First 门禁）。"""

import sys
import unittest
from pathlib import Path

# Add generated directory to sys.path
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR / "console_backend" / "generated"))

from proto.console.v1 import common_pb2, pipeline_pb2, workbench_m1_m2_pb2, workbench_review_pb2
from google.protobuf import json_format


class TestProtoContracts(unittest.TestCase):
    """验证 Protobuf 契约模式与 ProtoJSON 转换完整性。"""

    def test_pipeline_stages_and_run_roundtrip(self):
        run = pipeline_pb2.PipelineRun(
            run_id="run_test_001",
            work="qianyuan",
            edition="ed01",
            edition_part_id="ep_001",
            overall_status=common_pb2.RUN_STATUS_RUNNING,
            current_stage=common_pb2.PIPELINE_STAGE_M6_REVIEW,
        )
        stage_m1 = run.stages.add()
        stage_m1.stage = common_pb2.PIPELINE_STAGE_M1_DIGITIZATION
        stage_m1.status = common_pb2.RUN_STATUS_SUCCEEDED
        stage_m1.step_run_id = "srun_m1_001"

        stage_m6 = run.stages.add()
        stage_m6.stage = common_pb2.PIPELINE_STAGE_M6_REVIEW
        stage_m6.status = common_pb2.RUN_STATUS_AWAITING_HUMAN
        stage_m6.step_run_id = "srun_m6_001"

        json_data = json_format.MessageToDict(run)
        self.assertEqual(json_data["runId"], "run_test_001")
        self.assertEqual(json_data["currentStage"], "PIPELINE_STAGE_M6_REVIEW")
        self.assertEqual(len(json_data["stages"]), 2)

        restored = json_format.ParseDict(json_data, pipeline_pb2.PipelineRun())
        self.assertEqual(restored.run_id, "run_test_001")
        self.assertEqual(restored.stages[1].status, common_pb2.RUN_STATUS_AWAITING_HUMAN)

    def test_ocr_workbench_bbox_contracts(self):
        page = workbench_m1_m2_pb2.PageScan(
            page_index=1,
            image_url="/api/m1/page/1/image",
            image_sha256="abc123sha",
            width=1000,
            height=1500,
            cut_lines=[200, 400, 600, 800],
        )
        cbox = page.char_boxes.add()
        cbox.char = "天"
        cbox.line_index = 0
        cbox.char_index = 0
        cbox.bbox.x = 100
        cbox.bbox.y = 150
        cbox.bbox.width = 40
        cbox.bbox.height = 40

        json_data = json_format.MessageToDict(page)
        self.assertEqual(json_data["pageIndex"], 1)
        self.assertEqual(json_data["cutLines"], [200, 400, 600, 800])
        self.assertEqual(json_data["charBoxes"][0]["char"], "天")

    def test_sanitization_workbench_contracts(self):
        wb = workbench_m1_m2_pb2.SanitizationWorkbenchData(
            run_id="run_clean_001",
            raw_text="乾元秘旨\nhttp://bad-watermark.com\n太極而動",
            cleaned_text="乾元秘旨\n太極而動",
            total_findings=1,
        )
        finding = wb.findings.add()
        finding.rule_id = "R_WATERMARK"
        finding.kind = "watermark"
        finding.start_offset = 5
        finding.end_offset = 30
        finding.original_text = "http://bad-watermark.com\n"
        finding.suggested_replacement = ""
        finding.terminal_state = "cleaned"

        json_data = json_format.MessageToDict(wb)
        self.assertEqual(len(json_data["findings"]), 1)
        self.assertEqual(json_data["findings"][0]["kind"], "watermark")

    def test_review_workbench_contracts(self):
        batch = workbench_review_pb2.ReviewBatchRequest(
            run_id="run_review_001",
            step_run_id="srun_3009b37a",
            resume_token="tok_abc",
        )
        d1 = batch.decisions.add()
        d1.queue_item_id = "as_qizheng_000001#review_source_fidelity"
        d1.verdict = workbench_review_pb2.VERDICT_ACCEPT
        d1.rationale = "忠实原文"

        d2 = batch.decisions.add()
        d2.queue_item_id = "as_qizheng_000025#review_source_fidelity"
        d2.verdict = workbench_review_pb2.VERDICT_MODIFY
        d2.rationale = "修正行五为行伍"
        d2.modified_content = "惟武职官员，由行伍起者"

        json_data = json_format.MessageToDict(batch)
        self.assertEqual(json_data["stepRunId"], "srun_3009b37a")
        self.assertEqual(len(json_data["decisions"]), 2)
        self.assertEqual(json_data["decisions"][1]["verdict"], "VERDICT_MODIFY")


if __name__ == "__main__":
    unittest.main()
