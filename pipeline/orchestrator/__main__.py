"""Orchestrator CLI：``python -m pipeline.orchestrator --root <ledger_root> <命令>``。

退出码纪律：executed/waiting/complete/started/status/suspended → 0；blocked → 1；
refused（含 ``OrchestratorRefused``）→ 2；``WriterLocked`` → 3；其他 ``LedgerError`` → 1。
"""

import argparse
import json
import sys

from pipeline.contract_registry.catalog import load_registry
from pipeline.contract_registry.ports import DirectLedgerAdapter
from pipeline.ledger.errors import LedgerError, WriterLocked

from .edition_run import (
    advance,
    adopt_edition_run,
    start_edition_run,
)
from .errors import OrchestratorRefused
from .human import rerun_from_checkpoint, resume, suspend
from .queries import (
    blocking_reasons,
    pending_queue,
    run_status,
    stage_progress,
)


def _build_parser():
    parser = argparse.ArgumentParser(prog="python -m pipeline.orchestrator")
    parser.add_argument("--root", required=True)
    parser.add_argument("--registry", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start")
    start.add_argument("--edition-part", required=True)
    start.add_argument("--technique", required=True)

    for name in ("advance", "status", "resume", "rerun"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--run", required=True)
        sub.add_argument("--edition-part", required=True)
        sub.add_argument("--technique", required=True)
        if name == "resume":
            sub.add_argument("--step-run", required=True)
            sub.add_argument("--token", required=True)
        if name == "rerun":
            sub.add_argument("--stage", required=True)

    suspend_parser = subparsers.add_parser("suspend")
    suspend_parser.add_argument("--step-run", required=True)
    suspend_parser.add_argument("--reason", required=True)
    return parser


def _print_executed(step_result, stage):
    if step_result["status"] == "awaiting_human":
        print("RESUME_TOKEN %s" % step_result["resume_token"])
    print(
        "ORCH EXECUTED %s %s %s"
        % (stage, step_result["step_run_id"], step_result["status"])
    )
    return 0


def _cmd_advance(port, registry, handle):
    result = advance(port, registry, handle)
    for stage in sorted(result["gate_reports"]):
        print("ORCH GATE %s %s" % (stage, result["gate_reports"][stage]["gate"]))
    action = result["action"]
    if action == "executed":
        step_result = result["step_result"]
        if step_result["status"] == "awaiting_human":
            print("RESUME_TOKEN %s" % step_result["resume_token"])
        print(
            "ORCH EXECUTED %s %s %s"
            % (result["stage"], result["step_run_id"], step_result["status"])
        )
        return 0
    if action == "waiting":
        print("ORCH WAITING %s %s" % (result["stage"], result["step_run_id"]))
        return 0
    if action == "complete":
        print("ORCH COMPLETE")
        return 0
    if action == "blocked":
        print("ORCH BLOCKED %s %s" % (result["stage"], result["reason"]))
        return 1
    print("ORCH REFUSED %s %s" % (result["stage"] or "-", result["reason"]))
    return 2


def _cmd_status(port, registry, handle):
    payload = {
        "RunStatus": run_status(port, registry, handle),
        "StageProgress": stage_progress(port, registry, handle),
        "PendingQueue": pending_queue(port, registry, handle),
        "BlockingReasons": blocking_reasons(port, registry, handle),
    }
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    print("ORCH STATUS OK")
    return 0


def _dispatch(args):
    port = DirectLedgerAdapter(args.root)
    try:
        registry = (
            load_registry(args.registry) if args.registry else load_registry()
        )
        if args.command == "start":
            handle = start_edition_run(
                port, edition_part_id=args.edition_part, technique_id=args.technique
            )
            print("ORCH STARTED %s" % handle["processing_run_id"])
            return 0
        if args.command == "suspend":
            suspend(port, args.step_run, args.reason)
            print("ORCH SUSPENDED %s" % args.step_run)
            return 0

        handle = adopt_edition_run(
            port,
            processing_run_id=args.run,
            edition_part_id=args.edition_part,
            technique_id=args.technique,
        )
        if args.command == "advance":
            return _cmd_advance(port, registry, handle)
        if args.command == "status":
            return _cmd_status(port, registry, handle)
        if args.command == "resume":
            step_result = resume(port, registry, handle, args.step_run, args.token)
            stage = port.get_step_run(args.step_run)["stage"]
            return _print_executed(step_result, stage)
        if args.command == "rerun":
            step_result = rerun_from_checkpoint(port, registry, handle, args.stage)
            return _print_executed(step_result, args.stage)
    finally:
        port.close()
    return 2


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        return _dispatch(args)
    except WriterLocked:
        print("ORCH LOCKED")
        return 3
    except OrchestratorRefused as exc:
        print("ORCH REFUSED - %s" % exc)
        return 2
    except LedgerError as exc:
        print("ORCH ERROR %s: %s" % (type(exc).__name__, exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
