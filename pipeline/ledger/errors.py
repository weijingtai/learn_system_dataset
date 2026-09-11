"""Ledger 异常类与错误码常量（规格 §8.2 第 3 表）。

设计约定：

- ``LedgerError`` 是所有 Ledger 内部错误的基类，携带 ``code`` 与 ``message``；
- 子类名即语义，不新造错误码；只有语义与 §8.2 第 3 表吻合时才复用 9 个既有码；
- 状态迁移非法、写锁被占用等 Ledger 内部错误用 ``code=None`` 的异常类表达。
"""

# 规格 §8.2 第 3 表逐字转录（9 个校验错误码）
ERROR_CODES = frozenset(
    {
        "SRC_001",
        "SRC_003",
        "TXT_001",
        "ID_001",
        "ID_002",
        "REF_001",
        "SCH_001",
        "SCH_002",
        "SEM_001",
    }
)


class LedgerError(Exception):
    """Ledger 内部错误基类。

    :param message: 人类可读的错误说明。
    :param code: §8.2 第 3 表的错误码，或 ``None``（内部错误）。
    """

    def __init__(self, message="", code=None):
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidIdentifier(LedgerError):
    """标识格式非法（§8.1），错误码 ``ID_001``。"""

    def __init__(self, message="", code="ID_001"):
        super().__init__(message, code)


class DuplicateIdentifier(LedgerError):
    """标识已存在（§8.1），错误码 ``ID_002``。"""

    def __init__(self, message="", code="ID_002"):
        super().__init__(message, code)


class MissingReference(LedgerError):
    """引用的对象不存在（§8.2 第 3 表），错误码 ``REF_001``。"""

    def __init__(self, message="", code="REF_001"):
        super().__init__(message, code)


class HashMismatch(LedgerError):
    """内容哈希不匹配（§8.2 第 3 表），错误码 ``SRC_003``。"""

    def __init__(self, message="", code="SRC_003"):
        super().__init__(message, code)


class SchemaViolation(LedgerError):
    """Schema 校验失败；错误码由调用方指定为 ``SCH_001``（缺字段）或 ``SCH_002``（非法枚举）。"""

    def __init__(self, message="", code=None):
        super().__init__(message, code)


class IllegalTransition(LedgerError):
    """状态迁移不在 §8.2 合法迁移表内；Ledger 内部错误，``code=None``。"""

    def __init__(self, message="", code=None):
        super().__init__(message, code)


class NotConsumable(LedgerError):
    """引用了非 ``sealed`` Revision；Ledger 内部错误，``code=None``。"""

    def __init__(self, message="", code=None):
        super().__init__(message, code)


class WriterLocked(LedgerError):
    """写入者锁已被其他进程持有；Ledger 内部错误，``code=None``。"""

    def __init__(self, message="", code=None):
        super().__init__(message, code)


class InvalidResumeToken(LedgerError):
    """``resume_token`` 无效、已消费或与 status_version 不匹配；内部错误，``code=None``。"""

    def __init__(self, message="", code=None):
        super().__init__(message, code)
