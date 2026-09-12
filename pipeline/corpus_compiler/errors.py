"""M3 结构编译器专用异常（规格 §10.1、§11）。

``CompileRefused`` 覆盖编译被拒绝的语义场景：``deferred`` 阻断、漏编、
裸标（``known_unrecognizable`` 却有文字行）、页序与页文档不一致、引用
缺失（如缺图像哈希）等。不新增错误码闭集，按语义可选复用 §8.2 既有码，
未指定语义码时 ``code=None``。
"""

from pipeline.ledger.errors import LedgerError


class CompileRefused(LedgerError):
    """M3 编译被拒绝（规格 §10.1「严禁裸标/deferred 阻断」、§11 结构层约束）。"""

    def __init__(self, message="", code=None):
        super().__init__(message, code)
