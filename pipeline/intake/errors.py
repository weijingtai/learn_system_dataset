"""M1 电子文本入库异常定义。"""


class IntakeRefused(Exception):
    """M1 入库拒绝异常基类。

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


class SourceAssetMissing(IntakeRefused):
    """来源资产文件缺失异常。

    参数：
        paths：缺失文件路径列表。
    """

    def __init__(self, paths: list[str]):
        self.paths = list(paths)
        message = "\n".join("BLOCKED_SOURCE_ASSET_MISSING %s" % p for p in self.paths)
        super().__init__(message, code="SRC_001")
