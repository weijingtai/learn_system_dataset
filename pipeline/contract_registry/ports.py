"""存储端口：LedgerPort 方法闭集与两个 Adapter（规格 §20.10）。

- ``LEDGER_PORT_METHODS``：Orchestrator 允许经端口调用的 Ledger 方法闭集（以
  ``LedgerClient`` 公开方法为准）；
- ``DirectLedgerAdapter``：直连 ``LedgerService``（唯一允许触达 ``.objects`` 的生产
  代码位置之一，供 ``legacy_self_driving`` 经 ``unwrap()`` 取直连服务）；
- ``LedgerdClientAdapter``：经 Unix socket 的 ``LedgerClient``；
- ``PortGuard``：把端口收窄到闭集，拦截 ``store``/``objects`` 等内部属性。

本模块不 import 任何加工 Module，也不依赖编排层。
"""

from pathlib import Path

from pipeline.ledger.client import LedgerClient
from pipeline.ledger.service import LedgerService

# LedgerPort 方法闭集（依据 pipeline/ledger/client.py 公开方法）
LEDGER_PORT_METHODS = (
    "create_processing_run",
    "begin_step_run",
    "supersede_step_run",
    "put_artifact",
    "put_run_artifact",
    "seal_revision",
    "register_stage_package",
    "record_transformation",
    "write_checkpoint",
    "await_human",
    "record_human_event",
    "resume",
    "suspend",
    "recover",
    "finish_step_run",
    "fail_step_run",
    "recover_from_checkpoint",
    "get_revision",
    "get_step_run",
    "list_step_run_events",
    "list_transformations",
    "latest_checkpoint",
    "list_checkpoints",
    "run_status",
    "stage_progress",
    "read_object",
)

# 直连委托给 LedgerService 的方法（read_object 走 objects.get，单独实现）
_DELEGATED_TO_SERVICE = tuple(
    name for name in LEDGER_PORT_METHODS if name != "read_object"
)
# socket 客户端委托给 LedgerClient 的方法（含 read_object）
_DELEGATED_TO_CLIENT = LEDGER_PORT_METHODS


class DirectLedgerAdapter:
    """直连 ``LedgerService`` 的存储 Adapter（持写锁）。"""

    def __init__(self, root):
        Path(root).mkdir(parents=True, exist_ok=True)
        self._service = LedgerService(root)

    def read_object(self, sha256):
        """按 SHA-256 读取对象字节（``LedgerService`` 无公开 read_object）。"""
        return self._service.objects.get(sha256)

    def unwrap(self):
        """返回直连 ``LedgerService``（``legacy_self_driving`` 绑定的唯一例外）。"""
        return self._service

    def close(self):
        """释放写锁并关闭连接（幂等）。"""
        self._service.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def __getattr__(self, name):
        if name in _DELEGATED_TO_SERVICE:
            return getattr(self._service, name)
        raise AttributeError(name)


class LedgerdClientAdapter:
    """经 ``ledgerd`` Unix socket 的存储 Adapter。"""

    def __init__(self, socket_path):
        self._client = LedgerClient(socket_path)

    def unwrap(self):
        """ledgerd Adapter 不提供直连服务。"""
        raise NotImplementedError("ledgerd Adapter 不提供直连服务")

    def close(self):
        """关闭连接（幂等）。"""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def __getattr__(self, name):
        if name in _DELEGATED_TO_CLIENT:
            return getattr(self._client, name)
        raise AttributeError(name)


class PortGuard:
    """把任意端口对象收窄到 LedgerPort 闭集：闭集外访问抛 ``AttributeError``。"""

    def __init__(self, port):
        self._port = port

    def __getattr__(self, name):
        if name in LEDGER_PORT_METHODS or name == "unwrap":
            return getattr(self._port, name)
        raise AttributeError("非 LedgerPort 方法: %s" % name)


def port_surface(obj):
    """返回 ``obj`` 上可调用的闭集方法名（字典序）。"""
    return sorted(
        name for name in LEDGER_PORT_METHODS if callable(getattr(obj, name, None))
    )


def missing_port_methods(obj):
    """返回 ``obj`` 上不可调用的闭集方法名（保持元组顺序）。"""
    return [name for name in LEDGER_PORT_METHODS if not callable(getattr(obj, name, None))]
