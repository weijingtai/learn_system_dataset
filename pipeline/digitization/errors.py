"""M2 清洗异常体系。"""


class DigitizationError(Exception):
    """M2 清洗异常基类。"""


class DigitizationRefused(DigitizationError):
    """M2 清洗拒绝异常。

    参数：
        message：错误说明文本。
        code：错误码字符串（可选）。
    """

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message
