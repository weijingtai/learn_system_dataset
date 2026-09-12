"""M5 CLI：``python -m pipeline.validation``（规格 §13）。

退出码纪律：``0`` 成功 / ``1`` gate 未过 / ``2`` ``begin`` 之前被拒（或内部
失败）/ ``3`` WriterLocked。stdout 末行为机器可读结论。
"""

import argparse
import json
import sys

from pipeline.ledger.errors import WriterLocked
from pipeline.ledger.service import LedgerService

from .errors import ValidationRefused
from .step import run_m5


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pipeline.validation",
        description="M5 Automatic Validation（规格 §13）",
    )
    parser.add_argument("--root", required=True, help="Ledger 根目录")
    parser.add_argument("--edition-part", required=True, dest="edition_part", help="版本部件标识")
    parser.add_argument(
        "--target-consumption-level",
        default="INTERNAL_DEMO",
        dest="target_consumption_level",
        help="目标消费级别（默认 INTERNAL_DEMO）",
    )
    args = parser.parse_args(argv)

    try:
        service = LedgerService(args.root)
    except WriterLocked as exc:
        print("M5 LOCKED %s: %s" % (type(exc).__name__, exc))
        return 3

    try:
        try:
            summary = run_m5(
                service,
                args.edition_part,
                target_consumption_level=args.target_consumption_level,
            )
        except ValidationRefused as exc:
            print("M5 REFUSED %s: %s" % (type(exc).__name__, exc))
            return 2
    finally:
        service.close()

    if summary["status"] != "succeeded":
        print(
            "M5 FAILED %s: %s"
            % (summary.get("failed_check"), summary.get("reason"))
        )
        return 2
    if not summary["gate"]["passed"]:
        print(
            "M5 GATE_FAILED %s verdicts=%s"
            % (summary["step_run_id"], json.dumps(summary["level_verdicts"], ensure_ascii=False))
        )
        return 1
    print("M5 OK %s" % summary["step_run_id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
