from pipeline.ledger.errors import LedgerError

class ReviewRefused(LedgerError):
    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message, code=code)
