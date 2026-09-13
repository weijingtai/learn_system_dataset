"""``python -m pipeline.knowledge_extraction`` CLI（profile / submit / assemble）。

退出码：begin 之前被拒（ExtractionRefused / SchemaViolation / MissingReference /
NotConsumable）→ 2；``WriterLocked`` → 3；失败封存 → 1；等待人工 → 4；成功 → 0。
"""

import argparse
from pathlib import Path

import yaml

from pipeline.ledger.errors import (
    MissingReference,
    NotConsumable,
    SchemaViolation,
    WriterLocked,
)
from pipeline.ledger.service import LedgerService

from .adapters.registry import register_technique_profile
from .errors import ExtractionRefused
from .step import record_category_ruling, resume_m4, run_m4
from .submit import run_m4_submit

_REFUSALS = (ExtractionRefused, SchemaViolation, MissingReference, NotConsumable)


def _build_parser():
    parser = argparse.ArgumentParser(prog="pipeline.knowledge_extraction")
    sub = parser.add_subparsers(dest="command", required=True)

    profile = sub.add_parser("profile")
    profile.add_argument("--root", required=True)
    profile.add_argument("--processing-run", required=True)
    profile.add_argument("--technique", required=True)
    profile.add_argument("--canon-dir", required=True)

    submit = sub.add_parser("submit")
    submit.add_argument("--root", required=True)
    submit.add_argument("--edition-part", required=True)
    submit.add_argument("--from", dest="from_path", required=True)
    submit.add_argument("--producer", required=True)
    submit.add_argument("--producer-version", required=True)

    assemble = sub.add_parser("assemble")
    assemble.add_argument("--root", required=True)
    assemble.add_argument("--edition-part", required=True)

    rule = sub.add_parser("rule")
    rule.add_argument("--root", required=True)
    rule.add_argument("--step-run", required=True)
    rule.add_argument("--token", required=True)
    rule.add_argument("--from", dest="from_path", required=True)

    resume = sub.add_parser("resume")
    resume.add_argument("--root", required=True)
    resume.add_argument("--step-run", required=True)
    resume.add_argument("--token", required=True)
    return parser


def _emit_assemble(summary):
    if summary["status"] == "succeeded":
        counts = summary["counts"]
        print(
            "M4 OK %s assertions=%d disputes=%d"
            % (summary["step_run_id"], counts["assertions"], counts["disputes"])
        )
        return 0
    if summary["status"] == "awaiting_human":
        print(
            "M4 AWAITING_HUMAN %s disputes=%s token=%s"
            % (
                summary["step_run_id"],
                ",".join(summary["dispute_ids"]),
                summary["resume_token"],
            )
        )
        return 4
    print("M4 FAILED %s %s" % (summary["step_run_id"], summary["failed_check"]))
    return 1


def _dispatch(args, service):
    if args.command == "profile":
        try:
            revision_id = register_technique_profile(
                service,
                args.processing_run,
                technique_id=args.technique,
                canon_dir=args.canon_dir,
            )
        except _REFUSALS as exc:
            print("M4 REFUSED %s: %s" % (type(exc).__name__, exc))
            return 2
        print("M4 PROFILE %s" % revision_id)
        return 0

    if args.command == "submit":
        data = Path(args.from_path).read_bytes()
        try:
            summary = run_m4_submit(
                service,
                args.edition_part,
                data,
                producer_module=args.producer,
                producer_version=args.producer_version,
            )
        except _REFUSALS as exc:
            print("M4 REFUSED %s: %s" % (type(exc).__name__, exc))
            return 2
        if summary["status"] == "succeeded":
            print(
                "M4 SUBMIT OK %s %s/%s"
                % (summary["step_run_id"], summary["category"], summary["lane"])
            )
            return 0
        print("M4 SUBMIT FAILED %s %s" % (summary["step_run_id"], summary["failed_check"]))
        return 1

    if args.command == "rule":
        ruling = yaml.safe_load(Path(args.from_path).read_text(encoding="utf-8"))
        try:
            result = record_category_ruling(service, args.step_run, args.token, ruling)
        except _REFUSALS as exc:
            print("M4 REFUSED %s: %s" % (type(exc).__name__, exc))
            return 2
        print(
            "M4 RULED %s remaining=%d"
            % (ruling["dispute_id"], len(result["remaining_dispute_ids"]))
        )
        return 0

    try:
        if args.command == "resume":
            summary = resume_m4(service, args.step_run, args.token)
        else:
            summary = run_m4(service, args.edition_part)
    except _REFUSALS as exc:
        print("M4 REFUSED %s: %s" % (type(exc).__name__, exc))
        return 2
    return _emit_assemble(summary)


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        service = LedgerService(args.root)
    except WriterLocked as exc:
        print("M4 REFUSED WriterLocked: %s" % exc)
        return 3
    try:
        return _dispatch(args, service)
    finally:
        service.close()


if __name__ == "__main__":
    raise SystemExit(main())
