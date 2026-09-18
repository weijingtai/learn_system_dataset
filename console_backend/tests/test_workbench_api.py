"""Unit tests for Workbench M1, M2, Review, and Export API endpoints."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

# Add project root and generated directory to sys.path
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
GENERATED_DIR = BASE_DIR / "console_backend" / "generated"
if str(GENERATED_DIR) not in sys.path:
    sys.path.insert(0, str(GENERATED_DIR))

from fastapi.testclient import TestClient
from proto.console.v1 import common_pb2, pipeline_pb2, workbench_m1_m2_pb2, workbench_review_pb2

from console_backend.app.dependencies import set_repository, set_ws_manager
from console_backend.app.main import app
from console_backend.app.repository import SqlitePipelineRepository
from console_backend.app.ws import ConnectionManager


class TestWorkbenchApi(unittest.TestCase):
    """测试 Workbench M1/M2/Review 及 Export 路由与清洗引擎集成。"""

    def setUp(self):
        self.repo = SqlitePipelineRepository(":memory:")
        self.ws_mgr = ConnectionManager()
        set_repository(self.repo)
        set_ws_manager(self.ws_mgr)
        self.client = TestClient(app)

    def tearDown(self):
        self.repo.close()
        set_repository(None)
        set_ws_manager(None)

    # -------------------------------------------------------------
    # M1 OCR 测试
    # -------------------------------------------------------------

    def test_get_m1_page_scan_mock(self):
        """测试 GET /api/workbench/m1/{run_id} 返回古籍双栏版心 Mock 数据。"""
        res = self.client.get("/api/workbench/m1/run_m1_001")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # 检查基本结构与 snake_case 字段名保持
        self.assertEqual(data["page_index"], 1)
        self.assertEqual(data["width"], 1200)
        self.assertEqual(data["height"], 1800)
        self.assertTrue(data["image_url"].startswith("/static/scans/"))
        self.assertIn("cut_lines", data)
        self.assertIn(600, data["cut_lines"])  # 版心中缝切线

        # 检查字框列表包含双栏字符
        char_boxes = data.get("char_boxes", [])
        self.assertGreaterEqual(len(char_boxes), 16)
        line_indices = {box["line_index"] for box in char_boxes}
        self.assertIn(0, line_indices)  # 右栏
        self.assertIn(1, line_indices)  # 左栏

        # 检查首字
        first_box = char_boxes[0]
        self.assertEqual(first_box["char"], "天")
        self.assertEqual(first_box["line_index"], 0)
        self.assertEqual(first_box["char_index"], 0)
        self.assertIn("bbox", first_box)
        self.assertGreater(first_box["bbox"]["x"], 0)

        # 兼容测试 GET /api/workbench/m1/page?run_id=...
        res_alias = self.client.get("/api/workbench/m1/page?run_id=run_m1_001&page_index=1")
        self.assertEqual(res_alias.status_code, 200)
        self.assertEqual(res_alias.json()["page_index"], 1)

    def test_m1_rectify_and_ws_broadcast(self):
        """测试 POST /api/workbench/m1/rectify 微调 OCR 并广播 WebSocket 事件。"""
        with self.client.websocket_connect("/ws/events") as websocket:
            # 1. 提交 fix_char 校订动作
            rectify_payload = {
                "run_id": "run_m1_rectify_001",
                "page_index": 1,
                "action": "fix_char",
                "payload_json": json.dumps({"line_index": 0, "char_index": 0, "char": "乾"}),
            }
            res = self.client.post("/api/workbench/m1/rectify", json=rectify_payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()

            # 验证返回结果中该字符已被更新
            target_box = next(
                b for b in data["char_boxes"] if b["line_index"] == 0 and b["char_index"] == 0
            )
            self.assertEqual(target_box["char"], "乾")

            # 验证 WebSocket 收到微调事件广播
            ws_msg = websocket.receive_json()
            self.assertEqual(ws_msg["eventType"], "ocr_rectify")
            self.assertEqual(ws_msg["runId"], "run_m1_rectify_001")

            # 2. 再次通过 GET 查询验证改动已持久化
            res_get = self.client.get("/api/workbench/m1/run_m1_rectify_001")
            self.assertEqual(res_get.status_code, 200)
            persisted_box = next(
                b for b in res_get.json()["char_boxes"] if b["line_index"] == 0 and b["char_index"] == 0
            )
            self.assertEqual(persisted_box["char"], "乾")

            # 3. 提交 add_cutline 动作
            res_cut = self.client.post(
                "/api/workbench/m1/rectify",
                json={
                    "run_id": "run_m1_rectify_001",
                    "page_index": 1,
                    "action": "add_cutline",
                    "payload_json": json.dumps({"x": 650}),
                },
            )
            self.assertEqual(res_cut.status_code, 200)
            self.assertIn(650, res_cut.json()["cut_lines"])

    # -------------------------------------------------------------
    # M2 Sanitization 与 Cleaner 集成测试
    # -------------------------------------------------------------

    def test_get_m2_sanitization_data_with_cleaner_findings(self):
        """测试 GET /api/workbench/m2/{run_id} 真实触发 cleaner 产出 findings。"""
        res = self.client.get("/api/workbench/m2/run_m2_001")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["run_id"], "run_m2_001")
        self.assertIn("raw_text", data)
        self.assertIn("cleaned_text", data)
        self.assertIn("findings", data)
        self.assertGreater(data["total_findings"], 0)
        self.assertEqual(data["total_findings"], len(data["findings"]))

        # 验证 cleaner 检出真实规则项（如 escape_residue / watermark / textualized_diagram / replacement_char）
        finding_kinds = {f["kind"] for f in data["findings"]}
        self.assertIn("escape_residue", finding_kinds)
        self.assertIn("watermark", finding_kinds)
        self.assertIn("textualized_diagram", finding_kinds)

        # 检查字段名与格式规范
        first_finding = data["findings"][0]
        self.assertIn("rule_id", first_finding)
        self.assertIn("kind", first_finding)
        self.assertIn("start_offset", first_finding)
        self.assertIn("end_offset", first_finding)
        self.assertIn("original_text", first_finding)
        self.assertIn("terminal_state", first_finding)

        # 兼容测试 GET /api/workbench/m2/data?run_id=...
        res_alias = self.client.get("/api/workbench/m2/data?run_id=run_m2_001")
        self.assertEqual(res_alias.status_code, 200)
        self.assertEqual(res_alias.json()["run_id"], "run_m2_001")

    def test_post_m2_clean_realtime(self):
        """测试 POST /api/workbench/m2/clean 输入文本实时重跑清洗引擎。"""
        custom_raw = (
            "---\ntitle: 七政推步\nauthor: 钦天监\n---\n"
            "卷之一\\[七政历元\\]\n"
            "日行一度，月行十三度。\n"
            "https://bad-site.org/ads\n"
            "□字不可考。\n"
        )
        payload = {
            "run_id": "run_m2_custom_002",
            "raw_text": custom_raw,
        }
        res = self.client.post("/api/workbench/m2/clean", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["run_id"], "run_m2_custom_002")
        self.assertNotIn("https://bad-site.org/ads", data["cleaned_text"])
        self.assertNotIn("---\ntitle:", data["cleaned_text"])

        # 验证 findings 中包含清洗出的条目
        kinds = [f["kind"] for f in data["findings"]]
        self.assertIn("escape_residue", kinds)
        self.assertIn("watermark", kinds)
        self.assertIn("replacement_char", kinds)

        # 验证再次 GET 查询获得相同结果
        res_get = self.client.get("/api/workbench/m2/run_m2_custom_002")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["total_findings"], data["total_findings"])

    # -------------------------------------------------------------
    # M3/M6 Review 审核工作台测试
    # -------------------------------------------------------------

    def test_get_review_queue(self):
        """测试 GET /api/workbench/review/{run_id} 返回待审核队列及 AI 预审结果。"""
        res = self.client.get("/api/workbench/review/run_rev_001")
        self.assertEqual(res.status_code, 200)
        items = res.json()

        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 3)

        # 校验条目结构与预审结果
        verdicts = {it.get("auto_verdict") for it in items}
        self.assertIn("VERDICT_ACCEPT", verdicts)
        self.assertIn("VERDICT_MODIFY", verdicts)

        item = items[0]
        self.assertIn("queue_item_id", item)
        self.assertIn("target_entity_id", item)
        self.assertIn("proposition", item)
        self.assertIn("lane", item)
        self.assertIn("evidence_quotes", item)
        self.assertIn("auto_rationale", item)
        self.assertTrue(len(item["evidence_quotes"]) > 0)

        # 兼容测试 GET /api/workbench/review/queue?run_id=...
        res_alias = self.client.get("/api/workbench/review/queue?run_id=run_rev_001")
        self.assertEqual(res_alias.status_code, 200)
        self.assertEqual(len(res_alias.json()), len(items))

    def test_post_review_decide_and_pipeline_advancement(self):
        """测试 POST /api/workbench/review/decide 提交审核并在全部决议后推进流水线。"""
        run_id = "run_rev_advance_001"

        # 1. 预先创建 PipelineRun（处于 M6 阶段）
        run = pipeline_pb2.PipelineRun(
            run_id=run_id,
            work="新刻张果星宗",
            edition="四库全书本",
            overall_status=common_pb2.RUN_STATUS_RUNNING,
            current_stage=common_pb2.PIPELINE_STAGE_M6_REVIEW,
        )
        st_m6 = run.stages.add()
        st_m6.stage = common_pb2.PIPELINE_STAGE_M6_REVIEW
        st_m6.status = common_pb2.RUN_STATUS_AWAITING_HUMAN
        st_m7 = run.stages.add()
        st_m7.stage = common_pb2.PIPELINE_STAGE_M7_ASSEMBLY
        st_m7.status = common_pb2.RUN_STATUS_PENDING
        self.repo.save_run(run)

        # 2. 获取待审队列
        res_queue = self.client.get(f"/api/workbench/review/{run_id}")
        queue_items = res_queue.json()
        self.assertGreater(len(queue_items), 0)

        with self.client.websocket_connect("/ws/events") as websocket:
            # 3. 构造批量审核决议请求，覆盖所有 queue_items
            decisions = []
            for item in queue_items:
                decisions.append({
                    "queue_item_id": item["queue_item_id"],
                    "verdict": "VERDICT_ACCEPT",
                    "rationale": "人工复核无误，予以采纳",
                    "evidence_refs": item.get("evidence_quotes", []),
                })

            batch_req = {
                "run_id": run_id,
                "step_run_id": "step_m6_001",
                "resume_token": "token_m6_done",
                "decisions": decisions,
            }

            res_decide = self.client.post("/api/workbench/review/decide", json=batch_req)
            self.assertEqual(res_decide.status_code, 200)
            decide_data = res_decide.json()

            self.assertEqual(decide_data["status"], "ok")
            self.assertTrue(decide_data["all_completed"])
            self.assertEqual(decide_data["count"], len(decisions))

            # 4. 验证 WebSocket 广播了阶段变更事件（M6 完成）
            ws_msg = websocket.receive_json()
            self.assertEqual(ws_msg["eventType"], "stage_change")
            self.assertEqual(ws_msg["runId"], run_id)
            self.assertEqual(ws_msg["stage"], "PIPELINE_STAGE_M6_REVIEW")
            self.assertEqual(ws_msg["status"], "RUN_STATUS_SUCCEEDED")

            # 5. 验证 PipelineRun 状态在仓储中被推进至 M7_ASSEMBLY
            updated_run = self.repo.get_run(run_id)
            self.assertIsNotNone(updated_run)
            self.assertEqual(updated_run.current_stage, common_pb2.PIPELINE_STAGE_M7_ASSEMBLY)

            st6_updated = next(s for s in updated_run.stages if s.stage == common_pb2.PIPELINE_STAGE_M6_REVIEW)
            self.assertEqual(st6_updated.status, common_pb2.RUN_STATUS_SUCCEEDED)

            st7_updated = next(s for s in updated_run.stages if s.stage == common_pb2.PIPELINE_STAGE_M7_ASSEMBLY)
            self.assertEqual(st7_updated.status, common_pb2.RUN_STATUS_RUNNING)

    # -------------------------------------------------------------
    # Export 导出下载测试
    # -------------------------------------------------------------

    def test_export_release_bundle_download(self):
        """测试 GET /api/pipeline/export/{run_id} 导出 ReleaseBundle JSON 文件下载。"""
        run_id = "run_export_001"

        # 创建一个已有任务
        run = pipeline_pb2.PipelineRun(
            run_id=run_id,
            work="钦天监七政推步",
            edition="钦天文库精校本",
            overall_status=common_pb2.RUN_STATUS_RUNNING,
            current_stage=common_pb2.PIPELINE_STAGE_M3_STRUCTURAL,
        )
        self.repo.save_run(run)

        res = self.client.get(f"/api/pipeline/export/{run_id}")
        self.assertEqual(res.status_code, 200)

        # 验证 Content-Disposition attachment 文件名头
        content_disp = res.headers.get("Content-Disposition")
        self.assertIsNotNone(content_disp)
        self.assertIn("attachment", content_disp)
        self.assertIn(f'filename="release_bundle_{run_id}.json"', content_disp)

        # 验证 JSON 内容结构
        bundle = res.json()
        self.assertIn("manifest", bundle)
        self.assertIn("entities", bundle)
        self.assertIn("rules", bundle)

        manifest = bundle["manifest"]
        self.assertEqual(manifest["run_id"], run_id)
        self.assertEqual(manifest["work"], "钦天监七政推步")
        self.assertEqual(manifest["edition"], "钦天文库精校本")
        self.assertIn("schema_version", manifest)
        self.assertIn("closure_integrity_rate", manifest)

    def test_export_release_bundle_nonexistent_run_fallback(self):
        """测试未在 DB 中提前创建的 run_id 也能安全导出阶段包。"""
        res = self.client.get("/api/pipeline/export/run_unrecorded_999")
        self.assertEqual(res.status_code, 200)
        self.assertIn("attachment", res.headers.get("Content-Disposition", ""))

        bundle = res.json()
        self.assertEqual(bundle["manifest"]["run_id"], "run_unrecorded_999")
        self.assertIsInstance(bundle["entities"], list)
        self.assertIsInstance(bundle["rules"], list)


if __name__ == "__main__":
    unittest.main()
