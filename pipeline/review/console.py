import argparse
import json
import sys
from pathlib import Path

import yaml

from pipeline.knowledge_extraction.serialize import canonical_json
from pipeline.ledger.errors import (
    InvalidIdentifier,
    InvalidResumeToken,
    LedgerError,
    MissingReference,
    NotConsumable,
    SchemaViolation,
    WriterLocked,
)
from pipeline.ledger.service import LedgerReader, LedgerService
from pipeline.review import model, rework, step
from pipeline.review.errors import ReviewRefused
from pipeline.review.inputs import _read_doc

REFUSED_EXCEPTIONS = (
    ReviewRefused,
    MissingReference,
    NotConsumable,
    InvalidResumeToken,
    SchemaViolation,
    InvalidIdentifier,
)


def cmd_open(args):
    try:
        service = LedgerService(args.root)
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2

    try:
        res = step.open_review(service, args.edition_part)
        for it in res["queue"]:
            print(f"{it['queue_item_id']}\t{it['decision_type']}\tpending")
        print(f"M6 AWAITING {res['step_run_id']} token={res['resume_token']} pending={len(res['queue'])}")
        return 0
    except REFUSED_EXCEPTIONS as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    finally:
        service.close()


def cmd_queue(args):
    try:
        reader = LedgerReader(args.root)
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2

    try:
        srun = reader.get_step_run(args.step_run)
        if srun is None:
            raise MissingReference(f"StepRun 不存在: {args.step_run}", code="REF_001")

        queue_row = reader.store.conn.execute(
            "SELECT r.artifact_revision_id FROM artifact_revisions r "
            "JOIN artifacts a ON a.artifact_id = r.artifact_id "
            "WHERE a.artifact_type = 'review_queue' AND r.step_run_id = ?",
            (args.step_run,),
        ).fetchone()
        if not queue_row:
            queue_row = reader.store.conn.execute(
                "SELECT r.artifact_revision_id FROM frozen_inputs f "
                "JOIN artifact_revisions r ON r.artifact_revision_id = f.artifact_revision_id "
                "JOIN artifacts a ON a.artifact_id = r.artifact_id "
                "WHERE a.artifact_type = 'review_queue' AND f.step_run_id = ?",
                (args.step_run,),
            ).fetchone()
        if not queue_row:
            raise ReviewRefused("找不到 review_queue", code="REF_001")
        queue = _read_doc(reader, queue_row[0]) or []

        cur_events = reader.store.conn.execute(
            "SELECT event_revision_id FROM human_events WHERE step_run_id=? AND decision_type IS NOT NULL ORDER BY rowid ASC",
            (args.step_run,),
        ).fetchall()

        entries = []
        for r in cur_events:
            d_rev = r[0]
            ev_doc = _read_doc(reader, d_rev)
            if not ev_doc or ev_doc.get("event_kind") != "review_decision":
                continue
            ev_qid = model.queue_item_id(ev_doc["target"]["entity_id"], ev_doc["decision_type"])
            ev_qitem = next((it for it in queue if it["queue_item_id"] == ev_qid), None)
            if not ev_qitem:
                continue
            entry = model.decision_entry(
                decision_revision_id=d_rev,
                queue_item=ev_qitem,
                event=ev_doc,
                standing="active",
            )
            entries.append(entry)

        folded = model.fold_decisions(queue, entries)
        pending_count = 0
        for it in queue:
            qid = it["queue_item_id"]
            dt = it["decision_type"]
            ent = folded.get(qid)
            if ent is None:
                status = "pending"
                pending_count += 1
            else:
                verdict = ent["verdict"]
                standing = ent["standing"]
                if standing == "needs_review":
                    status = "needs_review"
                    pending_count += 1
                elif standing == "carried_forward":
                    status = "carried_forward"
                elif verdict == "request_evidence":
                    status = "request_evidence"
                    pending_count += 1
                else:
                    status = verdict
            print(f"{qid}\t{dt}\t{status}")

        print(f"M6 QUEUE {args.step_run} pending={pending_count}")
        return 0
    except REFUSED_EXCEPTIONS as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    finally:
        reader.close()


def cmd_show(args):
    try:
        reader = LedgerReader(args.root)
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2

    try:
        srun = reader.get_step_run(args.step_run)
        if srun is None:
            raise MissingReference(f"StepRun 不存在: {args.step_run}", code="REF_001")
        req = json.loads(srun["request_json"] or "{}")
        frozen = list(req.get("input_artifact_ids") or [])

        types_map = {}
        if frozen:
            placeholders = ",".join("?" * len(frozen))
            t_rows = reader.store.conn.execute(
                f"SELECT r.artifact_revision_id, a.artifact_type FROM artifact_revisions r "
                f"JOIN artifacts a ON a.artifact_id = r.artifact_id "
                f"WHERE r.artifact_revision_id IN ({placeholders})",
                tuple(frozen),
            ).fetchall()
            types_map = {r[0]: r[1] for r in t_rows}

        cand_set_rev = next((r for r in frozen if types_map.get(r) == "candidate_set"), None)
        spans_rev = next((r for r in frozen if types_map.get(r) == "corpus_spans"), None)
        val_pkg_rev = next((r for r in frozen if types_map.get(r) == "validation_package"), None)

        cand_set_doc = _read_doc(reader, cand_set_rev) or {}
        spans_doc = _read_doc(reader, spans_rev) or {}
        val_pkg_doc = _read_doc(reader, val_pkg_rev) or {}

        item_parts = args.item.split("#")
        entity_id = item_parts[0]
        decision_type = item_parts[1] if len(item_parts) > 1 else None

        target = next((a for a in cand_set_doc.get("assertions", []) if a.get("assertion_id") == entity_id), None)
        kind = "assertion"
        if not target:
            target = next((v for v in cand_set_doc.get("school_views", []) if v.get("school_view_id") == entity_id), None)
            kind = "school_view"
        if not target:
            raise MissingReference(f"Target entity {entity_id} 不在 candidate_set 中", code="REF_001")

        print(f"TARGET {entity_id} kind={kind} seen={cand_set_rev}")
        print(canonical_json(target).decode("utf-8"))

        raw_spans = spans_doc.get("spans")
        spans_dict = (
            {s["span_id"]: s for s in raw_spans if isinstance(s, dict) and "span_id" in s}
            if isinstance(raw_spans, list)
            else (raw_spans or {})
        )

        for ev in target.get("evidence", []):
            span_id = ev.get("source_span_id")
            span = spans_dict.get(span_id, {})
            anchor = span.get("source_anchor") or {}
            is_offset_level = (
                span.get("evidence_level") == "offset_level"
                or "raw_text_revision_id" in anchor
                or spans_doc.get("evidence_level") == "offset_level"
            )
            quote = ev.get("quote")
            if quote is None:
                text = span.get("text", "")
                start = ev.get("start_offset", ev.get("start", 0))
                end = ev.get("end_offset", ev.get("end", len(text)))
                quote = text[start:end]

            if is_offset_level:
                raw_rev = anchor.get("raw_text_revision_id", "-")
                raw_start = anchor.get("raw_start", "-")
                raw_end = anchor.get("raw_end", "-")
                s_off = anchor.get("start_offset", span.get("start_offset", "-"))
                e_off = anchor.get("end_offset", span.get("end_offset", "-"))
                print(
                    f"EVIDENCE {span_id} raw_text_revision_id={raw_rev} "
                    f"raw_start={raw_start} raw_end={raw_end} "
                    f"start_offset={s_off} end_offset={e_off} quote={quote}"
                )
            else:
                page = span.get("page", "-")
                line_id = anchor.get("line_id", "-")
                bbox = anchor.get("bbox")
                if bbox and isinstance(bbox, dict):
                    bbox_str = f"{bbox.get('x', 0)},{bbox.get('y', 0)},{bbox.get('w', 0)},{bbox.get('h', 0)}"
                else:
                    bbox_str = "-"
                image_sha256 = anchor.get("image_sha256", "-")
                print(f"EVIDENCE {span_id} page={page} line={line_id} bbox={bbox_str} image_sha256={image_sha256} quote={quote}")

        gr_rev = val_pkg_doc.get("gate_results_revision_id")
        gr_doc = _read_doc(reader, gr_rev) if gr_rev else {}
        if gr_doc:
            for f in gr_doc.get("failures", []):
                print(f"VALIDATION {f.get('check', '-')} failed {f.get('code', '-')}")
            for w in gr_doc.get("warnings", []):
                print(f"VALIDATION {w.get('check', '-')} warning {w.get('code', '-')}")
            for ch in gr_doc.get("passed_checks", []):
                print(f"VALIDATION {ch} passed -")

        he_rows = reader.store.conn.execute(
            "SELECT event_revision_id FROM human_events WHERE step_run_id=? AND decision_type IS NOT NULL ORDER BY rowid ASC",
            (args.step_run,),
        ).fetchall()
        for he_row in he_rows:
            ev_doc = _read_doc(reader, he_row[0])
            if ev_doc and ev_doc.get("event_kind") == "review_decision":
                t_eid = ev_doc.get("target", {}).get("entity_id")
                dt = ev_doc.get("decision_type")
                if t_eid == entity_id and (decision_type is None or dt == decision_type):
                    verdict = ev_doc.get("verdict", "-")
                    print(f"DECISION {he_row[0]} {verdict} active")

        return 0
    except REFUSED_EXCEPTIONS as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    finally:
        reader.close()


def cmd_decide(args):
    try:
        service = LedgerService(args.root)
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2

    try:
        mod_content = None
        if args.modified_content_file:
            mod_content = json.loads(Path(args.modified_content_file).read_text(encoding="utf-8"))

        res = step.record_decision(
            service,
            args.step_run,
            args.resume_token,
            queue_item_id=args.item,
            verdict=args.verdict,
            rationale=args.rationale,
            modified_content=mod_content,
            evidence_refs=tuple(args.evidence_ref or ()),
        )
        print(f"M6 DECIDED {res['decision_revision_id']} remaining={res['remaining']}")
        return 0
    except REFUSED_EXCEPTIONS as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    finally:
        service.close()


def cmd_decide_batch(args):
    try:
        service = LedgerService(args.root)
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2

    try:
        file_path = Path(args.from_file)
        if not file_path.exists():
            print(f"M6 REFUSED MissingReference: File not found {args.from_file}")
            return 2
        content = file_path.read_text(encoding="utf-8")
        raw = yaml.safe_load(content)
        decisions = raw.get("decisions", []) if isinstance(raw, dict) else (raw or [])

        for d in decisions:
            try:
                res = step.record_decision(
                    service,
                    args.step_run,
                    args.resume_token,
                    queue_item_id=d["queue_item_id"],
                    verdict=d["verdict"],
                    rationale=d["rationale"],
                    modified_content=d.get("modified_content"),
                    evidence_refs=tuple(d.get("evidence_refs") or ()),
                )
                print(f"M6 DECIDED {res['decision_revision_id']} remaining={res['remaining']}")
            except (*REFUSED_EXCEPTIONS, ValueError, KeyError) as exc:
                print(f"M6 REFUSED {type(exc).__name__}: {str(exc)}")
                return 2
        return 0
    except REFUSED_EXCEPTIONS as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    finally:
        service.close()


def cmd_close(args):
    try:
        service = LedgerService(args.root)
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2

    try:
        res = step.close_review(service, args.step_run, args.resume_token)
        if res.get("status") == "succeeded":
            ed_row = service.get_revision(res["reviewed_edition_revision_id"])
            ed_doc = json.loads(service.objects.get(ed_row["sha256"]).decode("utf-8"))
            num_decisions = len(ed_doc.get("decisions", []))
            print(
                f"M6 OK {res['step_run_id']} approved={len(res['approved'])} rejected={len(res['rejected'])} decisions={num_decisions}"
            )
            return 0
        else:
            print(f"M6 FAILED {res['step_run_id']} {res.get('failed_check', 'unknown')}")
            return 1
    except REFUSED_EXCEPTIONS as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    finally:
        service.close()


def cmd_recover(args):
    try:
        service = LedgerService(args.root)
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2

    try:
        res = step.recover_review(service, args.edition_part, reason=args.reason)
        print(
            f"M6 AWAITING {res['step_run_id']} token={res['resume_token']} pending={len(res['replayed_pending'])} supersedes={res['supersedes_step_run_id']}"
        )
        return 0
    except REFUSED_EXCEPTIONS as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    finally:
        service.close()


def cmd_correct(args):
    try:
        service = LedgerService(args.root)
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2

    try:
        res = rework.request_correction(
            service,
            args.step_run,
            args.resume_token,
            source_span_ids=list(args.span or ()),
            description=args.description,
        )
        print(f"M6 CORRECTION {res['correction_request_revision_id']}")
        return 0
    except REFUSED_EXCEPTIONS as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    finally:
        service.close()


def cmd_rework(args):
    try:
        service = LedgerService(args.root)
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2

    try:
        res = rework.run_rework_propagation(
            service,
            args.edition_part,
            correction_request_revision_id=args.correction_request,
            new_corpus_package_revision_id=args.new_corpus_package,
        )
        if res.get("status") == "succeeded":
            warnings = ",".join(res["warnings"]) if res["warnings"] else "-"
            counts = res["counts"]
            print(
                f"M6 REWORK {res['step_run_id']} "
                f"invalidated={counts['invalidated']} "
                f"carried_forward={counts['carried_forward']} "
                f"needs_review={counts['needs_review']} warnings={warnings}"
            )
            return 0
        print(f"M6 FAILED {res['step_run_id']} {res.get('failed_check', 'unknown')}")
        return 1
    except REFUSED_EXCEPTIONS as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    finally:
        service.close()


def cmd_rework_open(args):
    try:
        service = LedgerService(args.root)
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2

    try:
        res = rework.open_rework_review(
            service,
            args.edition_part,
            rework_impact_report_revision_id=args.report,
            acknowledge_rework_warning=bool(args.ack_rework_warning),
        )
        print(
            f"M6 AWAITING {res['step_run_id']} token={res['resume_token']} "
            f"pending={len(res['queue'])} "
            f"carried={len(res['carried_decision_revision_ids'])}"
        )
        return 0
    except REFUSED_EXCEPTIONS as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    except WriterLocked as e:
        print(f"M6 REFUSED WriterLocked: {str(e)}")
        return 3
    except Exception as e:
        print(f"M6 REFUSED {type(e).__name__}: {str(e)}")
        return 2
    finally:
        service.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.review",
        description="M6 Review & Curation Console",
    )
    parser.add_argument("--root", required=True, help="Ledger 根目录路径")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # open
    p_open = subparsers.add_parser("open", help="打开首审 StepRun")
    p_open.add_argument("--edition-part", required=True, help="待审分卷 ID")

    # queue
    p_queue = subparsers.add_parser("queue", help="查看审阅队列（只读）")
    p_queue.add_argument("--step-run", required=True, help="StepRun ID")

    # show
    p_show = subparsers.add_parser("show", help="查看队列项详情（只读）")
    p_show.add_argument("--step-run", required=True, help="StepRun ID")
    p_show.add_argument("--item", required=True, help="Queue Item ID")

    # decide
    p_decide = subparsers.add_parser("decide", help="提交单项决定")
    p_decide.add_argument("--step-run", required=True, help="StepRun ID")
    p_decide.add_argument("--resume-token", required=True, help="Resume Token")
    p_decide.add_argument("--item", required=True, help="Queue Item ID")
    p_decide.add_argument("--verdict", required=True, help="立项裁定")
    p_decide.add_argument("--rationale", required=True, help="裁定理由")
    p_decide.add_argument("--modified-content-file", help="修改后内容 JSON 文件路径")
    p_decide.add_argument("--evidence-ref", action="append", help="引文依据 span_id")

    # decide-batch
    p_batch = subparsers.add_parser("decide-batch", help="批量提交决定")
    p_batch.add_argument("--step-run", required=True, help="StepRun ID")
    p_batch.add_argument("--resume-token", required=True, help="Resume Token")
    p_batch.add_argument("--from-file", required=True, help="YAML 决定文件路径")

    # close
    p_close = subparsers.add_parser("close", help="结审")
    p_close.add_argument("--step-run", required=True, help="StepRun ID")
    p_close.add_argument("--resume-token", required=True, help="Resume Token")

    # recover
    p_recover = subparsers.add_parser("recover", help="从检查点恢复审阅")
    p_recover.add_argument("--edition-part", required=True, help="分卷 ID")
    p_recover.add_argument("--reason", required=True, help="恢复原因")

    # correct
    p_correct = subparsers.add_parser("correct", help="提交 CorrectionRequest")
    p_correct.add_argument("--step-run", required=True, help="StepRun ID")
    p_correct.add_argument("--resume-token", required=True, help="Resume Token")
    p_correct.add_argument("--span", action="append", help="待修正 span_id（可重复）")
    p_correct.add_argument("--description", required=True, help="修正说明")

    # rework
    p_rework = subparsers.add_parser("rework", help="执行精确失效传播")
    p_rework.add_argument("--edition-part", required=True, help="分卷 ID")
    p_rework.add_argument("--correction-request", required=True, help="CorrectionRequest 修订")
    p_rework.add_argument("--new-corpus-package", required=True, help="修正后 corpus_package 修订")

    # rework-open
    p_rework_open = subparsers.add_parser("rework-open", help="打开复审（只重放待复核项）")
    p_rework_open.add_argument("--edition-part", required=True, help="分卷 ID")
    p_rework_open.add_argument("--report", required=True, help="ReworkImpactReport 修订")
    p_rework_open.add_argument(
        "--ack-rework-warning", action="store_true", help="确认返工阈值告警"
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code

    handlers = {
        "open": cmd_open,
        "queue": cmd_queue,
        "show": cmd_show,
        "decide": cmd_decide,
        "decide-batch": cmd_decide_batch,
        "close": cmd_close,
        "recover": cmd_recover,
        "correct": cmd_correct,
        "rework": cmd_rework,
        "rework-open": cmd_rework_open,
    }
    handler = handlers.get(args.subcommand)
    if handler is None:
        parser.print_help()
        return 2

    return handler(args)
