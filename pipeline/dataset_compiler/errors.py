"""M8 子包编译器专用异常（规格 §16）。

``DatasetRefused`` 覆盖编译被拒绝的语义场景（准入不通过、发布策略未实现、
级别闭集外、排除页出现 Span 等）。不新增错误码闭集：按语义复用 §8.2 既有
9 个错误码，未指定语义码时 ``code=None``。
"""

from pipeline.ledger.errors import LedgerError


class DatasetRefused(LedgerError):
    """M8 编译被拒绝（规格 §16 准入与子包约束）。"""

    def __init__(self, message="", code=None):
        super().__init__(message, code)
