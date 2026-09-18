"""Pipeline REST router."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Body, Depends, HTTPException, status
from google.protobuf import json_format
from proto.console.v1 import common_pb2, pipeline_pb2

from console_backend.app.dependencies import get_repository, get_ws_manager
from console_backend.app.repository import SqlitePipelineRepository
from console_backend.app.ws import ConnectionManager

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

_STAGE_ENUMS = [
    common_pb2.PIPELINE_STAGE_M1_DIGITIZATION,
    common_pb2.PIPELINE_STAGE_M2_SANITIZATION,
    common_pb2.PIPELINE_STAGE_M3_STRUCTURAL,
    common_pb2.PIPELINE_STAGE_M4_KNOWLEDGE,
    common_pb2.PIPELINE_STAGE_M5_VALIDATION,
    common_pb2.PIPELINE_STAGE_M6_REVIEW,
    common_pb2.PIPELINE_STAGE_M7_ASSEMBLY,
    common_pb2.PIPELINE_STAGE_M8_DATASET,
]


@router.get("/runs", response_model=List[dict])
def list_pipeline_runs(
    repo: SqlitePipelineRepository = Depends(get_repository),
) -> List[dict[str, Any]]:
    """返回所有运行任务（ProtoJSON 格式列表）。"""
    runs = repo.list_runs()
    return [json_format.MessageToDict(run) for run in runs]


@router.post("/run", response_model=dict)
@router.post("/runs", response_model=dict, include_in_schema=False)
async def create_pipeline_run(
    request_data: dict[str, Any] = Body(...),
    repo: SqlitePipelineRepository = Depends(get_repository),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> dict[str, Any]:
    """接收 PipelineRunRequest，创建初始 PipelineRun，广播 stage_change 事件并持久化。"""
    # 支持测试或显式传入的 run_id，缺省则自动生成
    run_id = (
        request_data.get("run_id")
        or request_data.get("runId")
        or f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    )
    req_dict = {k: v for k, v in request_data.items() if k not in ("run_id", "runId")}

    req = pipeline_pb2.PipelineRunRequest()
    try:
        json_format.ParseDict(req_dict, req)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid PipelineRunRequest: {str(exc)}",
        ) from exc
    now_ts = int(time.time())
    now_iso = datetime.now(timezone.utc).isoformat()

    edition_part_id = (
        f"{req.work}_{req.edition}" if (req.work and req.edition) else req.work
    )

    run = pipeline_pb2.PipelineRun(
        run_id=run_id,
        work=req.work,
        edition=req.edition,
        edition_part_id=edition_part_id,
        overall_status=common_pb2.RUN_STATUS_RUNNING,
        current_stage=common_pb2.PIPELINE_STAGE_M1_DIGITIZATION,
        created_at=now_iso,
    )

    for stage_enum in _STAGE_ENUMS:
        progress = run.stages.add()
        progress.stage = stage_enum
        if stage_enum == common_pb2.PIPELINE_STAGE_M1_DIGITIZATION:
            progress.status = common_pb2.RUN_STATUS_RUNNING
            progress.started_at = now_ts
            progress.summary = "M1 Digitization in progress"
        else:
            progress.status = common_pb2.RUN_STATUS_PENDING

    # 广播初始 stage_change 事件
    ws_event = pipeline_pb2.WebSocketEvent(
        event_type="stage_change",
        run_id=run.run_id,
        stage=common_pb2.PIPELINE_STAGE_M1_DIGITIZATION,
        status=common_pb2.RUN_STATUS_RUNNING,
        log_message=f"Pipeline run {run.run_id} started at stage M1_DIGITIZATION",
        timestamp=now_ts,
    )
    await ws_manager.broadcast(ws_event)

    # 存入仓储并返回
    repo.save_run(run)
    return json_format.MessageToDict(run)


@router.get("/run/{run_id}", response_model=dict)
@router.get("/runs/{run_id}", response_model=dict, include_in_schema=False)
def get_pipeline_run(
    run_id: str,
    repo: SqlitePipelineRepository = Depends(get_repository),
) -> dict[str, Any]:
    """查询指定 run_id 的任务状态与进度详情。"""
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run '{run_id}' not found",
        )
    return json_format.MessageToDict(run)
