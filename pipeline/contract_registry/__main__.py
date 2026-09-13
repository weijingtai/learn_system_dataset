"""Contract Registry CLI：``python -m pipeline.contract_registry check``。

末行 ``REGISTRY OK modules=<n> ports=<n>``（exit 0）或 ``REGISTRY INVALID <n>``（exit 1）。
"""

import argparse
import sys
from pathlib import Path

from . import DEFAULT_REGISTRY_PATH
from .catalog import check_registry, load_registry


def _build_parser():
    parser = argparse.ArgumentParser(prog="python -m pipeline.contract_registry")
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="校验登记表一致性")
    check.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH))
    check.add_argument("--resolve-entries", action="store_true")
    return parser


def _run_check(args):
    try:
        registry = load_registry(Path(args.registry))
    except Exception as exc:  # noqa: BLE001 - 不可读即报告
        print("PROBLEM registry_unreadable %s" % exc)
        print("REGISTRY INVALID 1")
        return 1
    problems = check_registry(registry, resolve_entries=args.resolve_entries)
    if not problems:
        print(
            "REGISTRY OK modules=%d ports=%d"
            % (len(registry.modules), len(registry.ports))
        )
        return 0
    for problem in problems:
        print("PROBLEM %s %s" % (problem["code"], problem["detail"]))
    print("REGISTRY INVALID %d" % len(problems))
    return 1


def main(argv=None):
    args = _build_parser().parse_args(argv)
    if args.command == "check":
        return _run_check(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
