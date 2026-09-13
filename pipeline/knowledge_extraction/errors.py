"""M4 知识抽取的异常类。

``ExtractionRefused`` 用于「整件/整轮拒绝」的场景（形状之外的准入判断）；形状类
校验失败仍沿用 ``pipeline.ledger.errors.SchemaViolation``（SCH_001 / SCH_002）。
"""

from pipeline.ledger.errors import LedgerError


class ExtractionRefused(LedgerError):
    """M4 拒绝执行（携带 §8.2 九码之一或 ``None``）。"""

    def __init__(self, message="", code=None):
        super().__init__(message, code)
