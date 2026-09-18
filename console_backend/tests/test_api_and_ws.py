"""API, WebSocket, and Repository integration tests."""

from __future__ import annotations

import sys
import tempfile
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
from google.protobuf import json_format
from proto.console.v1 import common_pb2, pipeline_pb2

from console_backend.app.dependencies import (
    get_repository,
    get_ws_manager,
    set_repository,
    set_ws_manager,
)
from console_backend.app.main import app
from console_backend.app.repository import SqlitePipelineRepository
from console_backend.app.ws import ConnectionManager


class TestSqlitePipelineRepository(unittest.TestCase):
    """测试 SqlitePipelineRepository 的存储、查询与数据恢复。"""

    def test_in_memory_repository_crud(self):
        repo = SqlitePipelineRepository(":memory:")

        # 1. 存储初始 Run
        run = pipeline_pb2.PipelineRun(
            run_id="run_test_001",
            work="qizheng",
            edition="v1",
            edition_part_id="qizheng_v1",
            overall_status=common_pb2.RUN_STATUS_RUNNING,
            current_stage=common_pb2.PIPELINE_STAGE_M1_DIGITIZATION,
            created_at="2026-09-18T00:00:00Z",
        )
        stage_m1 = run.stages.add()
        stage_m1.stage = common_pb2.PIPELINE_STAGE_M1_DIGITIZATION
        stage_m1.status = common_pb2.RUN_STATUS_RUNNING
        stage_m1.summary = "Processing OCR"

        repo.save_run(run)

        # 2. 查询单个 Run
        fetched = repo.get_run("run_test_001")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.run_id, "run_test_001")
        self.assertEqual(fetched.work, "qizheng")
        self.assertEqual(fetched.overall_status, common_pb2.RUN_STATUS_RUNNING)
        self.assertEqual(len(fetched.stages), 1)
        self.assertEqual(fetched.stages[0].summary, "Processing OCR")

        # 3. 列表查询
        runs = repo.list_runs()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].run_id, "run_test_001")

        # 4. 更新现有 Run
        fetched.overall_status = common_pb2.RUN_STATUS_SUCCEEDED
        fetched.current_stage = common_pb2.PIPELINE_STAGE_M8_DATASET
        repo.save_run(fetched)

        updated = repo.get_run("run_test_001")
        self.assertEqual(updated.overall_status, common_pb2.RUN_STATUS_SUCCEEDED)
        self.assertEqual(updated.current_stage, common_pb2.PIPELINE_STAGE_M8_DATASET)

        # 5. 查询不存在的 Run
        self.assertIsNone(repo.get_run("non_existent_id"))

        # 6. 空 run_id 校验
        invalid_run = pipeline_pb2.PipelineRun()
        with self.assertRaises(ValueError):
            repo.save_run(invalid_run)

        repo.close()

    def test_file_db_persistence_and_recovery(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test_pipeline.db")

            # 实例 1：写入数据
            repo1 = SqlitePipelineRepository(db_path)
            run1 = pipeline_pb2.PipelineRun(
                run_id="run_persist_1",
                work="book_a",
                overall_status=common_pb2.RUN_STATUS_RUNNING,
            )
            run2 = pipeline_pb2.PipelineRun(
                run_id="run_persist_2",
                work="book_b",
                overall_status=common_pb2.RUN_STATUS_SUCCEEDED,
            )
            repo1.save_run(run1)
            repo1.save_run(run2)
            repo1.close()

            # 实例 2：重启后重新打开并验证数据恢复
            repo2 = SqlitePipelineRepository(db_path)
            recovered_runs = repo2.list_runs()
            self.assertEqual(len(recovered_runs), 2)

            recovered_1 = repo2.get_run("run_persist_1")
            self.assertIsNotNone(recovered_1)
            self.assertEqual(recovered_1.work, "book_a")

            recovered_2 = repo2.get_run("run_persist_2")
            self.assertIsNotNone(recovered_2)
            self.assertEqual(recovered_2.work, "book_b")
            repo2.close()


class TestPipelineApiAndWs(unittest.TestCase):
    """测试 FastAPI REST 端点与 WebSocket 广播总线。"""

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

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_pipeline_runs_crud_endpoints(self):
        # 1. 初始查询应为空
        res_list = self.client.get("/api/pipeline/runs")
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(res_list.json(), [])

        # 2. 创建 Run (POST /api/pipeline/run)
        create_payload = {
            "work": "qianyuan_mizhi",
            "edition": "ed_1900",
            "fileType": "txt",
            "sourceFilePath": "raw_books/qianyuan.txt",
            "techniqueId": "qizheng",
            "promptProfileId": "v1.0",
        }
        res_create = self.client.post("/api/pipeline/run", json=create_payload)
        self.assertEqual(res_create.status_code, 200)
        created_data = res_create.json()

        self.assertIn("runId", created_data)
        run_id = created_data["runId"]
        self.assertEqual(created_data["work"], "qianyuan_mizhi")
        self.assertEqual(created_data["edition"], "ed_1900")
        self.assertEqual(created_data["currentStage"], "PIPELINE_STAGE_M1_DIGITIZATION")
        self.assertEqual(created_data["overallStatus"], "RUN_STATUS_RUNNING")
        self.assertEqual(len(created_data["stages"]), 8)

        # 3. 按 run_id 获取
        res_get = self.client.get(f"/api/pipeline/run/{run_id}")
        self.assertEqual(res_get.status_code, 200)
        get_data = res_get.json()
        self.assertEqual(get_data["runId"], run_id)
        self.assertEqual(get_data["work"], "qianyuan_mizhi")

        # 4. 再次获取列表
        res_list_after = self.client.get("/api/pipeline/runs")
        self.assertEqual(res_list_after.status_code, 200)
        runs_list = res_list_after.json()
        self.assertEqual(len(runs_list), 1)
        self.assertEqual(runs_list[0]["runId"], run_id)

        # 5.        # 验证 404 容错
        res_404 = self.client.get("/api/pipeline/run/non_existent_run")
        self.assertEqual(res_404.status_code, 404)

    def test_pipeline_export_endpoint(self):
        # 验证 release bundle 导出端点
        res = self.client.get("/api/pipeline/export/run_test_export")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("manifest", data)
        self.assertEqual(data["manifest"]["run_id"], "run_test_export")
        self.assertIn("entities", data)
        self.assertIn("rules", data)

    def test_workbench_endpoints(self):
        # 1. M1 OCR
        res_m1 = self.client.get("/api/workbench/m1/page", params={"run_id": "run_01", "page_index": 1})
        self.assertEqual(res_m1.status_code, 200)
        m1_data = res_m1.json()
        self.assertIn("charBoxes", m1_data)
        self.assertIn("cutLines", m1_data)

        # 2. M2 Sanitization
        res_m2 = self.client.get("/api/workbench/m2/data", params={"run_id": "run_01"})
        self.assertEqual(res_m2.status_code, 200)
        m2_data = res_m2.json()
        self.assertIn("findings", m2_data)
        self.assertIn("rawText", m2_data)
        self.assertIn("cleanedText", m2_data)

        # 3. Review queue
        res_rev = self.client.get("/api/workbench/review/queue", params={"run_id": "run_01"})
        self.assertEqual(res_rev.status_code, 200)
        queue_data = res_rev.json()
        self.assertIsInstance(queue_data, list)
        self.assertGreater(len(queue_data), 0)


    def test_create_run_validation_failure(self):
        # 传入非法 Proto 字段结构
        bad_payload = {"unknownField": 12345}
        response = self.client.post("/api/pipeline/run", json=bad_payload)
        self.assertEqual(response.status_code, 400)

    def test_alias_endpoints_and_multiple_runs(self):
        # 测试 POST /api/pipeline/runs 别名端点
        res1 = self.client.post("/api/pipeline/runs", json={"work": "book1", "edition": "e1"})
        self.assertEqual(res1.status_code, 200)
        run1_id = res1.json()["runId"]

        res2 = self.client.post("/api/pipeline/runs", json={"work": "book2", "edition": "e2"})
        self.assertEqual(res2.status_code, 200)
        run2_id = res2.json()["runId"]

        # 测试 GET /api/pipeline/runs/{run_id} 别名端点
        res_alias = self.client.get(f"/api/pipeline/runs/{run1_id}")
        self.assertEqual(res_alias.status_code, 200)
        self.assertEqual(res_alias.json()["runId"], run1_id)

        # 检查列表顺序
        res_list = self.client.get("/api/pipeline/runs")
        self.assertEqual(res_list.status_code, 200)
        runs = res_list.json()
        self.assertEqual(len(runs), 2)
        # 最近创建的应该排在最前面
        self.assertEqual(runs[0]["runId"], run2_id)
        self.assertEqual(runs[1]["runId"], run1_id)

    def test_websocket_connection_and_broadcast(self):
        with self.client.websocket_connect("/ws/events") as ws:
            # 1. 发起 POST 创建任务，触发自动 stage_change 广播
            create_payload = {
                "work": "taiji_shu",
                "edition": "ed_modern",
                "runId": "run_ws_check_01",
            }
            res = self.client.post("/api/pipeline/run", json=create_payload)
            self.assertEqual(res.status_code, 200)

            # 2. 检查 WebSocket 接收到的广播事件
            event_data = ws.receive_json()
            self.assertEqual(event_data.get("eventType"), "stage_change")
            self.assertEqual(event_data.get("runId"), "run_ws_check_01")
            self.assertEqual(event_data.get("stage"), "PIPELINE_STAGE_M1_DIGITIZATION")
            self.assertEqual(event_data.get("status"), "RUN_STATUS_RUNNING")


class TestConnectionManager(unittest.IsolatedAsyncioTestCase):
    """测试 ConnectionManager 核心机制。"""

    class DummyWebSocket:
        def __init__(self, should_fail: bool = False):
            self.accepted = False
            self.messages = []
            self.should_fail = should_fail

        async def accept(self):
            self.accepted = True

        async def send_json(self, data):
            if self.should_fail:
                raise RuntimeError("Connection broken")
            self.messages.append(data)

    async def test_connect_disconnect_and_broadcast(self):
        mgr = ConnectionManager()
        ws1 = self.DummyWebSocket()
        ws2 = self.DummyWebSocket(should_fail=True)
        ws3 = self.DummyWebSocket()

        await mgr.connect(ws1)
        await mgr.connect(ws2)
        await mgr.connect(ws3)

        self.assertEqual(len(mgr.active_connections), 3)

        # 广播 WebSocketEvent
        evt = pipeline_pb2.WebSocketEvent(
            event_type="log_append",
            run_id="run_cm_01",
            log_message="Hello from bus",
        )
        await mgr.broadcast(evt)

        # ws1 和 ws3 应该收到，ws2 报错后被自动移除
        self.assertEqual(len(ws1.messages), 1)
        self.assertEqual(ws1.messages[0]["eventType"], "log_append")
        self.assertEqual(ws1.messages[0]["logMessage"], "Hello from bus")
        self.assertEqual(len(ws3.messages), 1)
        self.assertNotIn(ws2, mgr.active_connections)
        self.assertEqual(len(mgr.active_connections), 2)

        # 广播 dict 载荷
        await mgr.broadcast({"eventType": "custom", "data": 42})
        self.assertEqual(len(ws1.messages), 2)
        self.assertEqual(ws1.messages[1]["eventType"], "custom")

        # 手动断开 ws1
        mgr.disconnect(ws1)
        self.assertEqual(len(mgr.active_connections), 1)
        self.assertIn(ws3, mgr.active_connections)


if __name__ == "__main__":
    unittest.main()
