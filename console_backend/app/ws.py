"""WebSocket connection manager and event bus."""

from __future__ import annotations

import logging
from typing import Any, List, Union

from fastapi import WebSocket
from google.protobuf import json_format
from proto.console.v1 import pipeline_pb2

logger = logging.getLogger(__name__)


class ConnectionManager:
    """管理活跃 WebSocket 连接，支持单播与全网广播。"""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """接受并注册新的 WebSocket 连接。"""
        try:
            await websocket.accept()
        except RuntimeError:
            # 兼容连接已被其他逻辑提前 accept 的情形
            pass
        if websocket not in self.active_connections:
            self.active_connections.append(websocket)
            logger.info("WebSocket client connected. Total clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """注销 WebSocket 连接。"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected. Total clients: %d", len(self.active_connections))

    async def broadcast(self, event: Union[pipeline_pb2.WebSocketEvent, dict[str, Any]]) -> None:
        """向所有活跃连接广播 WebSocketEvent。"""
        if isinstance(event, pipeline_pb2.WebSocketEvent):
            payload = json_format.MessageToDict(event)
        else:
            payload = event

        disconnected: List[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(payload)
            except Exception as exc:
                logger.warning("Failed to send message to websocket client: %s", exc)
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)
