"""Dependency injection providers for repository and WebSocket manager."""

from __future__ import annotations

from typing import Optional

from console_backend.app.repository import SqlitePipelineRepository
from console_backend.app.ws import ConnectionManager

_repo_instance: Optional[SqlitePipelineRepository] = None
_ws_instance: Optional[ConnectionManager] = None


def get_repository() -> SqlitePipelineRepository:
    """获取单例 Repository 实例，默认使用内存数据库。"""
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = SqlitePipelineRepository(":memory:")
    return _repo_instance


def set_repository(repo: Optional[SqlitePipelineRepository]) -> None:
    """设置或重置 Repository 实例（主要用于测试配置）。"""
    global _repo_instance
    _repo_instance = repo


def get_ws_manager() -> ConnectionManager:
    """获取单例 WebSocket ConnectionManager 实例。"""
    global _ws_instance
    if _ws_instance is None:
        _ws_instance = ConnectionManager()
    return _ws_instance


def set_ws_manager(ws: Optional[ConnectionManager]) -> None:
    """设置或重置 WebSocket ConnectionManager 实例。"""
    global _ws_instance
    _ws_instance = ws
