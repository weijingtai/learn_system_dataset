"""M7 汇编子系统异常定义。"""

from pipeline.ledger.errors import LedgerError


class AssemblyRefused(LedgerError):
    """M7 汇编前置拒绝或业务拒绝。"""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message, code=code)
