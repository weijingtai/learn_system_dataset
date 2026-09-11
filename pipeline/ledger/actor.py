"""操作者身份接口（规格 §17）。

当前为单人单机工具，不实现登录/会话/RBAC；边界只保留极薄的
``ActorProvider.current_actor()``，本地实现固定返回 ``local_owner``。
未来可替换为 OIDC 等在线身份适配器，不修改领域对象或历史审计记录。
"""

from typing import Protocol


class ActorProvider(Protocol):
    """操作者身份提供者协议。"""

    def current_actor(self) -> str:
        """返回当前操作者引用（写入 ``actor_ref``）。"""
        ...


class LocalActorProvider:
    """本地单机实现：固定返回 ``local_owner``。"""

    def current_actor(self) -> str:
        return "local_owner"
