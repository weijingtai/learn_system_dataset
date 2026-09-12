"""python -m pipeline.corpus_compiler CLI 入口（规格 §17）。

用法::

    python -m pipeline.corpus_compiler --root <ledger_root> --edition-part <art_id> [--batch-size 10]

成功末行：``M3 OK <step_run_id> spans=<n> batches=<m>``（exit 0）
失败末行：``M3 FAILED <step_run_id> <failed_check>``（exit 1）
begin 之前被拒：``M3 REFUSED <异常类名>: <消息>``（exit 2）
WriterLocked：exit 3
"""

import argparse
import sys

from .errors import CompileRefused
from .step import run_m3
from pipeline.ledger.errors import LedgerError, WriterLocked
from pipeline.ledger.service import LedgerService


def main(argv=None):
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        prog="pipeline.corpus_compiler",
        description="M3 Corpus Compilation 结构层（规格 §11）",
    )
    parser.add_argument("--root", required=True, help="Ledger 根目录")
    parser.add_argument("--edition-part", required=True, help="版本部件 artifact_id")
    parser.add_argument("--batch-size", type=int, default=10, help="每批最大行数")
    args = parser.parse_args(argv)

    service = LedgerService(args.root)
    try:
        try:
            result = run_m3(service, args.edition_part, batch_size=args.batch_size)
        except WriterLocked:
            service.close()
            return 3
        except CompileRefused as exc:
            print("M3 REFUSED %s: %s" % (type(exc).__name__, exc))
            return 2
        except LedgerError as exc:
            print("M3 REFUSED %s: %s" % (type(exc).__name__, exc))
            return 2

        if result["status"] == "succeeded":
            print(
                "M3 OK %s spans=%d batches=%d"
                % (
                    result["step_run_id"],
                    result["counts"]["spans"],
                    result["counts"]["batches"],
                )
            )
            return 0
        else:
            print(
                "M3 FAILED %s %s" % (result["step_run_id"], result["failed_check"])
            )
            return 1
    finally:
        service.close()


if __name__ == "__main__":
    raise SystemExit(main())
