"""M7 命令行入口（act/g0-04）。

用法：
    python -m pipeline.assembly run --edition-part-id <art_…> --technique-id <t> --reviewed-package-revision-id <rev_…>
"""

import argparse
import sys
from pathlib import Path

from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.step import run_m7
from pipeline.ledger.service import LedgerService


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pipeline.assembly")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run M7 knowledge assembly")
    run_parser.add_argument("--edition-part-id", required=True, help="Edition part artifact id")
    run_parser.add_argument("--technique-id", required=True, help="Technique id")
    run_parser.add_argument(
        "--reviewed-package-revision-id",
        action="append",
        required=True,
        dest="reviewed_package_revision_ids",
        help="Reviewed package revision id (repeatable)",
    )
    run_parser.add_argument("--ledger-dir", default="ledger", help="Ledger directory")
    run_parser.add_argument("--base-snapshot-revision-id", default=None, help="Base snapshot revision id")

    args = parser.parse_args(argv)

    if args.command == "run":
        service = LedgerService(Path(args.ledger_dir))
        try:
            res = run_m7(
                service,
                args.edition_part_id,
                technique_id=args.technique_id,
                reviewed_package_revision_ids=args.reviewed_package_revision_ids,
                base_snapshot_revision_id=args.base_snapshot_revision_id,
            )
            if res.get("status") == "succeeded":
                print("M7 OK: snapshot=%s assembly_package=%s" % (res["snapshot_revision_id"], res["assembly_package_revision_id"]))
                sys.exit(0)
            else:
                print("M7 FAILED: %s" % res.get("gate"), file=sys.stderr)
                sys.exit(1)
        except AssemblyRefused as e:
            print("M7 REFUSED: %s" % e, file=sys.stderr)
            sys.exit(2)
        except Exception as e:
            print("M7 ERROR: %s" % e, file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
