"""``python -m pipeline.dataset_compiler`` CLI 入口（规格 §16、§17）。

用法::

    python -m pipeline.dataset_compiler --root <ledger_root> --edition-part <art_id> --level <LEVEL> [--min-app-version X.Y.Z]

末行与退出码：
    成功 ``M8 OK <step_run_id> release=<release_id> packs=2``（exit 0）
    begin 之后封存失败 ``M8 FAILED <step_run_id> <failed_check>``（exit 1）
    begin 之前被拒 ``M8 REFUSED <异常类名>: <消息>``（exit 2）
    WriterLocked（exit 3）
"""

import argparse

from pipeline.dataset_compiler.step import run_m8
from pipeline.ledger.errors import LedgerError, WriterLocked
from pipeline.ledger.service import LedgerService


def main(argv=None):
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        prog="pipeline.dataset_compiler",
        description="M8 Dataset Compilation 首切片（规格 §16）",
    )
    parser.add_argument("--root", required=True, help="Ledger 根目录")
    parser.add_argument("--edition-part", required=True, help="版本部件 artifact_id")
    parser.add_argument("--level", required=True, help="消费级别（INTERNAL_DEMO 等）")
    parser.add_argument("--min-app-version", default=None, help="最低 App 版本（semver）")
    args = parser.parse_args(argv)

    service = LedgerService(args.root)
    try:
        try:
            result = run_m8(
                service,
                args.edition_part,
                consumption_level=args.level,
                min_app_version=args.min_app_version,
            )
        except WriterLocked:
            return 3
        except LedgerError as exc:
            print("M8 REFUSED %s: %s" % (type(exc).__name__, exc))
            return 2

        if result["status"] == "succeeded":
            print(
                "M8 OK %s release=%s packs=%d"
                % (
                    result["step_run_id"],
                    result["release_id"],
                    result["counts"]["packs"],
                )
            )
            return 0
        print("M8 FAILED %s %s" % (result["step_run_id"], result["failed_check"]))
        return 1
    finally:
        service.close()


if __name__ == "__main__":
    raise SystemExit(main())
