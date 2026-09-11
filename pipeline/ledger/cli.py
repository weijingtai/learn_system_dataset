"""Ledger 命令行入口（规格 §17）。

用法::

    python -m pipeline.ledger.cli init --root <dir>                   建库（migrate）
    python -m pipeline.ledger.cli status --root <dir>                 只读：schema 版本 + 各表行数
    python -m pipeline.ledger.cli run-status --root <dir> <prun_id>   只读：ProcessingRun 状态
    python -m pipeline.ledger.cli stage-progress --root <dir> <prun_id>
    python -m pipeline.ledger.cli serve --root <dir> [--socket <path>]   等价 ledgerd

退出码：成功 ``0``；参数 / 引用错误 ``2``；写锁被占 ``3``。
只读子命令走 ``LedgerReader``（``mode=ro``，不取写锁），故可与写入者进程并发执行。
"""

import argparse
import json
import sqlite3
import sys

from .errors import LedgerError, WriterLocked
from .ledgerd import default_socket_path, run as run_daemon
from .service import LedgerReader, LedgerService


def _open_reader(root):
    """打开只读连接；库不可用时返回 ``None``（调用方转退出码 2）。"""
    try:
        return LedgerReader(root)
    except sqlite3.Error:
        return None


def cmd_init(args):
    """建库（幂等 migrate）并打印 ``LEDGER_INIT <root>``。"""
    try:
        service = LedgerService(args.root)
    except WriterLocked:
        print("LEDGER_WRITER_LOCKED %s" % args.root)
        return 3
    try:
        print("LEDGER_INIT %s" % args.root)
    finally:
        service.close()
    return 0


def cmd_status(args):
    """只读输出 schema 版本与各表行数（JSON 一行）。"""
    reader = _open_reader(args.root)
    if reader is None:
        print("ERR 无法只读打开 Ledger: %s" % args.root, file=sys.stderr)
        return 2
    try:
        row = reader.store.conn.execute(
            "SELECT value FROM schema_meta WHERE key='ledger_schema_version'"
        ).fetchone()
        version = row[0] if row else None
        names = [
            item[0]
            for item in reader.store.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            if item[0] != "sqlite_sequence"
        ]
        tables = {
            name: reader.store.conn.execute(
                "SELECT COUNT(*) FROM %s" % name
            ).fetchone()[0]
            for name in names
        }
    finally:
        reader.close()
    print(
        json.dumps(
            {"ledger_schema_version": version, "tables": tables},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _print_run_query(args, method_name):
    """只读执行 ``run_status`` / ``stage_progress`` 并打印 JSON 一行。"""
    reader = _open_reader(args.root)
    if reader is None:
        print("ERR 无法只读打开 Ledger: %s" % args.root, file=sys.stderr)
        return 2
    try:
        payload = getattr(reader, method_name)(args.processing_run_id)
    except LedgerError as exc:
        print("ERR %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2
    finally:
        reader.close()
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_run_status(args):
    """只读输出 ProcessingRun 状态。"""
    return _print_run_query(args, "run_status")


def cmd_stage_progress(args):
    """只读输出按 stage 聚合的进度。"""
    return _print_run_query(args, "stage_progress")


def cmd_serve(args):
    """等价于 ``python -m pipeline.ledger.ledgerd``。"""
    socket_path = (
        args.socket if args.socket else default_socket_path(args.root)
    )
    return run_daemon(args.root, socket_path)


def build_parser():
    """构造 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="pipeline.ledger.cli", description="Artifact Ledger 命令行（规格 §17）"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="建库（migrate）")
    init_parser.add_argument("--root", required=True)
    init_parser.set_defaults(handler=cmd_init)

    status_parser = subparsers.add_parser("status", help="只读：schema 版本与表行数")
    status_parser.add_argument("--root", required=True)
    status_parser.set_defaults(handler=cmd_status)

    run_parser = subparsers.add_parser("run-status", help="只读：ProcessingRun 状态")
    run_parser.add_argument("--root", required=True)
    run_parser.add_argument("processing_run_id")
    run_parser.set_defaults(handler=cmd_run_status)

    progress_parser = subparsers.add_parser(
        "stage-progress", help="只读：按 stage 聚合的进度"
    )
    progress_parser.add_argument("--root", required=True)
    progress_parser.add_argument("processing_run_id")
    progress_parser.set_defaults(handler=cmd_stage_progress)

    serve_parser = subparsers.add_parser("serve", help="启动本地进程（等价 ledgerd）")
    serve_parser.add_argument("--root", required=True)
    serve_parser.add_argument("--socket", default=None)
    serve_parser.set_defaults(handler=cmd_serve)

    return parser


def main(argv=None):
    """``python -m pipeline.ledger.cli`` 入口。"""
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
