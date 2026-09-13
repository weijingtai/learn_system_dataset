"""Contract Registry 异常类。

``RegistryInvalid`` 继承 Ledger 错误基类，携带可选 ``code``（语义与 §8.2 吻合时复用
既有 9 码，否则为 ``None``）。
"""

from pipeline.ledger.errors import LedgerError


class RegistryInvalid(LedgerError):
    """登记表结构或语义非法。

    :param message: 人类可读的错误说明。
    :param code: §8.2 第 3 表的错误码，或 ``None``（内部错误）。
    """

    def __init__(self, message="", code=None):
        super().__init__(message, code)
