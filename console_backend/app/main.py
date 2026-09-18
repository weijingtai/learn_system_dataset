"""Main FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from console_backend.app.dependencies import get_ws_manager
from console_backend.app.routers import pipeline, workbench
from console_backend.app.ws import ConnectionManager

app = FastAPI(
    title="Learn System Web Console API",
    description="Backend API and WebSocket event bus for Learn System Web Console",
    version="0.1.0",
)

# 配置跨域资源共享 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载业务路由
app.include_router(pipeline.router)
app.include_router(workbench.router, prefix="/api/workbench", tags=["workbench"])



# 挂载 WebSocket 实时事件端点
@app.websocket("/ws/events")
async def websocket_events(
    websocket: WebSocket,
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> None:
    """WebSocket 全双工事件总线通道。"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # 持续监听客户端指令或心跳
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """系统健康检查探针。"""
    return {"status": "ok"}
