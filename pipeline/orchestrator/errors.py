"""Orchestrator 异常类。"""

from pipeline.ledger.errors import LedgerError


class OrchestratorRefused(LedgerError):
    """编排层拒绝推进（未登记 Module、绑定不符、legacy 入口异常、写入前校验失败等）。

    :param message: 人类可读的错误说明。
    :param code: §8.2 第 3 表的错误码，或 ``None``。
    """

    def __init__(self, message="", code=None):
        super().__init__(message, code)
