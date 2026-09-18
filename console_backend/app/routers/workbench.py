"""Workbench REST router for M1 OCR, M2 Sanitization, and M3/M6 Review."""

from __future__ import annotations

import json
import time
from typing import Any, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from google.protobuf import json_format
from proto.console.v1 import common_pb2, pipeline_pb2, workbench_m1_m2_pb2, workbench_review_pb2

from console_backend.app.dependencies import get_repository, get_ws_manager
from console_backend.app.repository import SqlitePipelineRepository
from console_backend.app.ws import ConnectionManager
from pipeline.digitization.cleaner import CleanResult, Finding, clean_text, patch_replacement

router = APIRouter()

# 默认具有代表性的古籍真实感电子文本（包含 YAML 头残留、Markdown 转义、水印、框线图表与替换字符）
DEFAULT_M2_RAW_TEXT = """---
title: 钦天监七政星宗
author: 佚名
edition: 四库全书本
---
卷之一\\[七政历元\\]
钦天监推算历代星度，以日、月、五星为七政。
日行一度，月行十三度有奇。
https://www.guwen-archive.org/download/qizheng
┌──────────────┬──────────────┐
│ 太阳直照     │ 太阴映耀     │
└──────────────┴──────────────┘
周天三百六十五度四分度之一。□疑漏字。
"""


def _create_default_mock_page_scan(page_index: int = 1) -> workbench_m1_m2_pb2.PageScan:
    """构建符合古籍双栏版心布局的真实感 Mock PageScan 数据。"""
    scan = workbench_m1_m2_pb2.PageScan(
        page_index=page_index,
        image_url=f"/static/scans/page_{page_index:03d}.jpg",
        image_sha256="d41d8cd98f00b204e9800998ecf8427e98ec01",
        width=1200,
        height=1800,
        cut_lines=[150, 600, 1050],  # 左右边栏与中缝版心切线
    )

    # 右栏（第一列，Line 0）
    col0_chars = ["天", "文", "七", "政", "星", "垣", "周", "天"]
    for idx, ch in enumerate(col0_chars):
        cbox = scan.char_boxes.add()
        cbox.char = ch
        cbox.line_index = 0
        cbox.char_index = idx
        cbox.bbox.x = 750
        cbox.bbox.y = 200 + idx * 120
        cbox.bbox.width = 80
        cbox.bbox.height = 100

    # 左栏（第二列，Line 1）
    col1_chars = ["日", "月", "五", "星", "循", "行", "经", "纬"]
    for idx, ch in enumerate(col1_chars):
        cbox = scan.char_boxes.add()
        cbox.char = ch
        cbox.line_index = 1
        cbox.char_index = idx
        cbox.bbox.x = 350
        cbox.bbox.y = 200 + idx * 120
        cbox.bbox.width = 80
        cbox.bbox.height = 100

    return scan


def _finding_to_proto(f: Finding) -> workbench_m1_m2_pb2.SanitizationFinding:
    """将 cleaner 的 Finding 转换为 Protobuf SanitizationFinding。"""
    proto_f = workbench_m1_m2_pb2.SanitizationFinding()
    proto_f.rule_id = f.finding_id
    proto_f.kind = f.kind
    proto_f.start_offset = f.raw_start
    proto_f.end_offset = f.raw_end
    proto_f.original_text = f.raw_excerpt
    proto_f.suggested_replacement = patch_replacement(f)

    if f.terminal_state in ("cleaned", "deferred", "retained"):
        proto_f.terminal_state = f.terminal_state
    elif f.action == "patched" or f.terminal_state == "processed":
        proto_f.terminal_state = "cleaned"
    elif f.action == "kept":
        proto_f.terminal_state = "retained"
    else:
        proto_f.terminal_state = "deferred"

    return proto_f


def _build_m2_workbench_data(
    run_id: str,
    raw_text: str,
    rule_ids_to_clean: Optional[list[str]] = None,
) -> workbench_m1_m2_pb2.SanitizationWorkbenchData:
    """调用真实 cleaner.clean_text 生成 M2 SanitizationWorkbenchData。"""
    clean_res: CleanResult = clean_text(raw_text)

    wb_data = workbench_m1_m2_pb2.SanitizationWorkbenchData()
    wb_data.run_id = run_id
    wb_data.raw_text = raw_text
    wb_data.cleaned_text = clean_res.cleaned_text
    wb_data.total_findings = len(clean_res.findings)

    for f in clean_res.findings:
        proto_f = _finding_to_proto(f)
        if rule_ids_to_clean and (f.finding_id in rule_ids_to_clean or proto_f.rule_id in rule_ids_to_clean):
            proto_f.terminal_state = "cleaned"
        wb_data.findings.append(proto_f)

    return wb_data


def _create_default_review_queue() -> List[workbench_review_pb2.ReviewQueueItem]:
    """构建具有真实感的古籍术数知识抽取审校命题队列。"""
    items = []

    # 命题 1：太阳属性
    item1 = workbench_review_pb2.ReviewQueueItem(
        queue_item_id="rev_item_001",
        target_entity_id="ent_qizheng_taiyang",
        proposition="日者，太阳之精，诸阳之宗，君象也。",
        lane="lane_a",
        evidence_quotes=["《果老星宗·十一曜定局》：日者太阳之精，诸阳之宗，人君之象。"],
        model_suggestion_a="实体：太阳；属性：君象；分类：七政十一曜",
        model_suggestion_b="实体：太阳；角色：日君；作用：诸阳之主",
        auto_verdict=workbench_review_pb2.VERDICT_ACCEPT,
        auto_rationale="两路大模型抽取语义高度收敛，引文在底本有确定坐标，置信度 0.98",
    )
    items.append(item1)

    # 命题 2：太阴属性与夜生人判定
    item2 = workbench_review_pb2.ReviewQueueItem(
        queue_item_id="rev_item_002",
        target_entity_id="ent_qizheng_taiyin",
        proposition="月者，太阴之象，后妃之德，夜生人以月为主星。",
        lane="lane_b",
        evidence_quotes=["《星度指南》卷二：夜生人以月为主，主身命之原。"],
        model_suggestion_a="实体：太阴；作用：夜生人身命主星",
        model_suggestion_b="实体：太阴；条件：夜生人；影响：母星或身主",
        auto_verdict=workbench_review_pb2.VERDICT_MODIFY,
        auto_rationale="模型 A 与模型 B 对身命主星判定条件存在细微出入，需人工复核是否限定‘夜生’",
    )
    items.append(item2)

    # 命题 3：岁星（木星）属性
    item3 = workbench_review_pb2.ReviewQueueItem(
        queue_item_id="rev_item_003",
        target_entity_id="ent_qizheng_suixing",
        proposition="岁星，东方木之精，仁德之象，主十二年一周天。",
        lane="lane_a",
        evidence_quotes=["《天官书》：岁星曰东方木，德星也，十二岁一周天。"],
        model_suggestion_a="实体：岁星；五行：木；周期：12年",
        model_suggestion_b="实体：木星（岁星）；五德：仁；公转周期：12年",
        auto_verdict=workbench_review_pb2.VERDICT_ACCEPT,
        auto_rationale="典籍原文佐证充足，术语实体对齐无冲突",
    )
    items.append(item3)

    # 命题 4：荧惑（火星）主事
    item4 = workbench_review_pb2.ReviewQueueItem(
        queue_item_id="rev_item_004",
        target_entity_id="ent_qizheng_huoxing",
        proposition="荧惑者，南方火之宿，礼仪之端，失度则主兵丧。",
        lane="lane_b",
        evidence_quotes=["《晋书·天文志》：荧惑为火星，失行则逆，主兵革之变。"],
        model_suggestion_a="实体：荧惑；五行：火；征兆：兵革",
        model_suggestion_b="实体：火星；吉凶：凶（失行时）；分类：五星",
        auto_verdict=workbench_review_pb2.VERDICT_MODIFY,
        auto_rationale="引文出处跨典籍（《晋书》 vs 《果老》），建议核实当前批次底本归属",
    )
    items.append(item4)

    return items


# ==========================================
# M1 OCR 端点
# ==========================================

@router.get("/m1/page", response_model=dict, include_in_schema=False)
def get_m1_page_by_param(
    run_id: str = Query(...),
    page_index: int = Query(1),
    repo: SqlitePipelineRepository = Depends(get_repository),
) -> dict[str, Any]:
    """兼容 query 参数形式获取 M1 PageScan。"""
    return get_m1_page(run_id=run_id, page_index=page_index, repo=repo)


@router.get("/m1/{run_id}", response_model=dict)
def get_m1_page(
    run_id: str,
    page_index: int = Query(1, alias="page_index"),
    repo: SqlitePipelineRepository = Depends(get_repository),
) -> dict[str, Any]:
    """返回指定任务的 M1 OCR 数据（PageScan 结构），无数据时生成双栏版心 Mock 数据。"""
    scan = repo.get_m1_page_scan(run_id, page_index=page_index)
    if scan is None:
        scan = _create_default_mock_page_scan(page_index=page_index)
        repo.save_m1_page_scan(run_id, scan)
    res = json_format.MessageToDict(
        scan,
        always_print_fields_with_no_presence=True,
        preserving_proto_field_name=True,
    )
    res["charBoxes"] = res.get("char_boxes", [])
    res["cutLines"] = res.get("cut_lines", [])
    return res


@router.post("/m1/rectify", response_model=dict)
async def rectify_m1_ocr(
    request_data: dict[str, Any] = Body(...),
    repo: SqlitePipelineRepository = Depends(get_repository),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> dict[str, Any]:
    """接收 OcrRectifyRequest，更新并返回处理后的 PageScan 结果，并广播 WebSocket 事件。"""
    req = workbench_m1_m2_pb2.OcrRectifyRequest()
    try:
        json_format.ParseDict(request_data, req)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OcrRectifyRequest: {str(exc)}",
        ) from exc

    page_idx = req.page_index if req.page_index > 0 else 1
    scan = repo.get_m1_page_scan(req.run_id, page_index=page_idx)
    if scan is None:
        scan = _create_default_mock_page_scan(page_index=page_idx)

    # 处理校正动作
    payload_data: dict[str, Any] = {}
    if req.payload_json:
        try:
            payload_data = json.loads(req.payload_json)
        except Exception:
            payload_data = {}

    if req.action == "fix_char":
        target_char = payload_data.get("char")
        char_idx = payload_data.get("char_index", 0)
        line_idx = payload_data.get("line_index")
        for box in scan.char_boxes:
            if line_idx is not None and box.line_index != line_idx:
                continue
            if box.char_index == char_idx:
                if target_char is not None:
                    box.char = target_char
                break
    elif req.action == "add_cutline":
        cut_x = payload_data.get("x", payload_data.get("cut_line"))
        if cut_x is not None:
            scan.cut_lines.append(int(cut_x))
            scan.cut_lines.sort()

    repo.save_m1_page_scan(req.run_id, scan)

    # 广播 OCR 微调 WebSocket 事件
    ws_event = pipeline_pb2.WebSocketEvent(
        event_type="ocr_rectify",
        run_id=req.run_id,
        stage=common_pb2.PIPELINE_STAGE_M1_DIGITIZATION,
        status=common_pb2.RUN_STATUS_RUNNING,
        log_message=f"OCR rectified for run {req.run_id} page {page_idx}: action={req.action}",
        payload_json=req.payload_json,
        timestamp=int(time.time()),
    )
    await ws_manager.broadcast(ws_event)

    res = json_format.MessageToDict(
        scan,
        always_print_fields_with_no_presence=True,
        preserving_proto_field_name=True,
    )
    res["charBoxes"] = res.get("char_boxes", [])
    res["cutLines"] = res.get("cut_lines", [])
    return res


# ==========================================
# M2 Sanitization 端点
# ==========================================

@router.get("/m2/data", response_model=dict, include_in_schema=False)
def get_m2_data_by_param(
    run_id: str = Query(...),
    repo: SqlitePipelineRepository = Depends(get_repository),
) -> dict[str, Any]:
    """兼容 query 参数形式获取 M2 数据。"""
    return get_m2_data(run_id=run_id, repo=repo)


@router.get("/m2/{run_id}", response_model=dict)
def get_m2_data(
    run_id: str,
    repo: SqlitePipelineRepository = Depends(get_repository),
) -> dict[str, Any]:
    """返回 M2 数据清洗工作台数据（SanitizationWorkbenchData 结构）。"""
    wb_data = repo.get_m2_data(run_id)
    if wb_data is None:
        wb_data = _build_m2_workbench_data(run_id=run_id, raw_text=DEFAULT_M2_RAW_TEXT)
        repo.save_m2_data(run_id, wb_data)
    res = json_format.MessageToDict(
        wb_data,
        always_print_fields_with_no_presence=True,
        preserving_proto_field_name=True,
    )
    res["rawText"] = res.get("raw_text", "")
    res["cleanedText"] = res.get("cleaned_text", "")
    res["totalFindings"] = res.get("total_findings", len(res.get("findings", [])))
    return res


@router.post("/m2/clean", response_model=dict)
def clean_m2_text(
    request_data: dict[str, Any] = Body(...),
    repo: SqlitePipelineRepository = Depends(get_repository),
) -> dict[str, Any]:
    """接收 raw_text，直接调用 pipeline cleaner 实时重跑清洗，返回 SanitizationWorkbenchData。"""
    run_id = request_data.get("run_id") or request_data.get("runId") or "default_run"
    raw_text = request_data.get("raw_text") or request_data.get("rawText")
    rule_ids = request_data.get("rule_ids") or request_data.get("ruleIds")

    if not raw_text:
        existing = repo.get_m2_data(run_id)
        raw_text = existing.raw_text if existing else DEFAULT_M2_RAW_TEXT

    wb_data = _build_m2_workbench_data(run_id=run_id, raw_text=raw_text, rule_ids_to_clean=rule_ids)
    repo.save_m2_data(run_id, wb_data)
    res = json_format.MessageToDict(
        wb_data,
        always_print_fields_with_no_presence=True,
        preserving_proto_field_name=True,
    )
    res["rawText"] = res.get("raw_text", "")
    res["cleanedText"] = res.get("cleaned_text", "")
    res["totalFindings"] = res.get("total_findings", len(res.get("findings", [])))
    return res


# ==========================================
# Review (M3 / M6) 端点
# ==========================================

@router.get("/review/queue", response_model=List[dict], include_in_schema=False)
def get_review_queue_by_param(
    run_id: str = Query(...),
    repo: SqlitePipelineRepository = Depends(get_repository),
) -> List[dict[str, Any]]:
    """兼容 query 参数形式获取审核队列。"""
    return get_review_queue(run_id=run_id, repo=repo)


@router.get("/review/{run_id}", response_model=List[dict])
def get_review_queue(
    run_id: str,
    repo: SqlitePipelineRepository = Depends(get_repository),
) -> List[dict[str, Any]]:
    """返回 M3/M6 待审核队列（repeated ReviewQueueItem）。"""
    items = repo.get_review_items(run_id)
    if not items:
        items = _create_default_review_queue()
        repo.save_review_items(run_id, items)
    return [
        json_format.MessageToDict(
            item,
            always_print_fields_with_no_presence=True,
            preserving_proto_field_name=True,
        )
        for item in items
    ]


@router.post("/review/decide", response_model=dict)
@router.post("/review/batch", response_model=dict, include_in_schema=False)
async def submit_review_decisions(
    request_data: dict[str, Any] = Body(...),
    repo: SqlitePipelineRepository = Depends(get_repository),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> dict[str, Any]:
    """接收 ReviewBatchRequest，记录审核决策；若全部审核完毕，广播阶段完成事件并返回成功状态。"""
    req = workbench_review_pb2.ReviewBatchRequest()
    try:
        json_format.ParseDict(request_data, req)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ReviewBatchRequest: {str(exc)}",
        ) from exc

    # 确保存储了初始待审队列
    items = repo.get_review_items(req.run_id)
    if not items:
        items = _create_default_review_queue()
        repo.save_review_items(req.run_id, items)

    # 保存本次决策
    repo.save_review_decisions(req.run_id, list(req.decisions))

    # 判断是否全部审核完成
    all_decisions = repo.get_review_decisions(req.run_id)
    decided_ids = {d.queue_item_id for d in all_decisions}
    all_queue_ids = {item.queue_item_id for item in items}
    all_completed = bool(all_queue_ids and all_queue_ids.issubset(decided_ids))

    now_ts = int(time.time())

    # 若审核全部完成，更新关联的 PipelineRun 状态并广播
    if all_completed:
        run = repo.get_run(req.run_id)
        if run is not None:
            for stage in run.stages:
                if stage.stage == common_pb2.PIPELINE_STAGE_M6_REVIEW:
                    stage.status = common_pb2.RUN_STATUS_SUCCEEDED
                    stage.finished_at = now_ts
                    stage.summary = f"M6 Review completed with {len(decided_ids)} decisions"
                elif stage.stage == common_pb2.PIPELINE_STAGE_M7_ASSEMBLY:
                    stage.status = common_pb2.RUN_STATUS_RUNNING
                    stage.started_at = now_ts
                    stage.summary = "M7 Genesis Assembly in progress"
            run.current_stage = common_pb2.PIPELINE_STAGE_M7_ASSEMBLY
            repo.save_run(run)

        ws_event = pipeline_pb2.WebSocketEvent(
            event_type="stage_change",
            run_id=req.run_id,
            stage=common_pb2.PIPELINE_STAGE_M6_REVIEW,
            status=common_pb2.RUN_STATUS_SUCCEEDED,
            log_message=f"All review items decided for run {req.run_id}. Progressing to M7_ASSEMBLY.",
            timestamp=now_ts,
        )
        await ws_manager.broadcast(ws_event)

    result = json_format.MessageToDict(
        req,
        always_print_fields_with_no_presence=True,
        preserving_proto_field_name=True,
    )
    result["status"] = "ok"
    result["success"] = True
    result["count"] = len(req.decisions)
    result["all_completed"] = all_completed
    return result
