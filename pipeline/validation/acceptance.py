"""m5-evidence-gate 验收：十四项判定（规格 §19.0）。

判定一律自行重算，不信任 ``run_m5`` 返回的 gate 报告；本模块不 import
``g1_source`` / ``g2_coverage`` / ``g3_evidence`` / ``replay``（重放经
``registry.resolve`` 调用）。用法::

    python -m pipeline.validation.acceptance --fixture <dir> [--keep]

退出码：任一 FAIL → 1；无 FAIL 有 BLOCKED → 2；全部 PASS → 0；宿主或依赖缺失 → 3。
"""

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from pipeline.corpus_compiler import compiler as _compiler
from pipeline.corpus_compiler.serialize import dump_yaml
from pipeline.corpus_compiler.step import run_m3
from pipeline.ledger import fixture_ingest
from pipeline.ledger.service import LedgerService

from .context import build_context
from .inputs import resolve_m5_inputs
from .registry import VALIDATORS, resolve
from .step import run_m5

EDITION_PART = "art_000000000000000000000000000000e1"

# 四项 BLOCKED（名称固定，说明逐字取自 §19 第一列行名）
BLOCKED_ITEMS = (
    ("candidate_evidence", "前置缺失: M4 Knowledge Extraction；Candidate 证据范围与 direct proposition 忠实性未实现"),
    ("g4_content_layering", "前置缺失: M4 Knowledge Extraction；无 Case/editorial 分层输入"),
    ("g5_concept_search", "前置缺失: M4 Knowledge Extraction；无 confirmed concept"),
    ("g6_rule_executability", "前置缺失: M4 Knowledge Extraction；ApplicabilityRule 未产出"),
)

# offset 片段按实判定用的证据级别
_OFFSET_LEVEL = "offset_level"

# OCR 档 spans 未存储 quote hash 的过时文案（§19 第一列行名，逐字保留）
QUOTE_HASH_BLOCKED = "前置缺失: M3 Corpus Compilation；spans 未存储 quote hash（§11.1）"

_KNOWN_TERMINAL = (None, "manually_transcribed", "known_unrecognizable")
_CONTENT_STATUSES = (
    "source_verified", "machine_extracted", "cross_model_reviewed", "disputed",
    "needs_expert", "expert_verified", "deprecated",
)


def _read_doc(service, revision_id):
    row = service.get_revision(revision_id)
    return json.loads(service.objects.get(row["sha256"]).decode("utf-8"))


def _page_block(doc):
    return "\n".join(line["text"] for line in doc.get("lines") or [])


@contextmanager
def harness(fixture_dir, *, keep=False):
    """准备临时 Ledger（ingest m1,m2 → run_m3 → run_m5）并产出验收状态。"""
    root = tempfile.mkdtemp(prefix="m5-acc-")
    service = LedgerService(Path(root) / "ledger")
    try:
        fixture_ingest.ingest(fixture_dir, service, stages=("m1", "m2"))
        m3_summary = run_m3(service, EDITION_PART)
        inputs = resolve_m5_inputs(service, EDITION_PART)
        summary = run_m5(service, EDITION_PART)
        state = {
            "fixture": Path(fixture_dir),
            "service": service,
            "m3": m3_summary,
            "inputs": inputs,
            "summary": summary,
            "ctx": build_context(service, inputs, target_consumption_level="INTERNAL_DEMO"),
            "gate_results": _read_doc(service, summary["gate_results_revision_id"]),
            "package": _read_doc(service, summary["package_revision_id"]),
            "validation_package": _read_doc(
                service, summary["validation_package_revision_id"]
            ),
        }
        yield state
    finally:
        service.close()
        if not keep:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------- 独立重算
def _unresolved_count(ctx):
    """独立重算未决字符发现数（按 Span 聚合未识别/空字框，按页聚合 pending）。"""
    spans = (ctx.get("spans_doc") or {}).get("spans") or []
    line_to_span = {
        (span.get("page"), (span.get("source_anchor") or {}).get("line_id")): span
        for span in spans
    }
    span_groups = set()
    pending_pages = set()
    for page, doc in (ctx.get("page_docs") or {}).items():
        for char in doc.get("chars") or []:
            if char.get("status") == "unrecognized" or char.get("char") in (None, ""):
                span = line_to_span.get((page, char.get("parent")))
                span_groups.add(span.get("span_id") if span else page)
            elif char.get("status") == "pending":
                pending_pages.add(page)
    return len(span_groups) + len(pending_pages)


def _frozen_mismatch_count(ctx):
    frozen = (ctx.get("raw") or {}).get("frozen") or {}
    return sum(
        1
        for entry in frozen.values()
        if entry.get("actual_sha256") is None
        or entry.get("actual_sha256") != entry.get("sha256")
    )


def _content_hash_ok(ctx):
    frozen = (ctx.get("raw") or {}).get("frozen") or {}
    registered = (frozen.get(ctx.get("corpus_spans_revision_id")) or {}).get("sha256")
    declared = ((ctx.get("m3_package") or {}).get("manifest") or {}).get("content_sha256")
    return registered is not None and registered == declared


def _coverage_ok(ctx):
    pages = ((ctx.get("manifest") or {}).get("edition_part") or {}).get("pages") or []
    terminal = ctx.get("terminal_states") or {}
    page_docs = ctx.get("page_docs") or {}
    spans = (ctx.get("spans_doc") or {}).get("spans") or []
    covered = [p for p in pages if terminal.get(p) in (None, "manually_transcribed")]
    excluded = [p for p in pages if terminal.get(p) == "known_unrecognizable"]
    if set(covered) | set(excluded) != set(pages):
        return False
    by_page = {}
    for span in spans:
        by_page.setdefault(span.get("page"), []).append(span)
    for page in covered:
        doc = page_docs.get(page)
        if doc is None:
            return False
        block = _page_block(doc)
        ordered = sorted(by_page.get(page, []), key=lambda s: s.get("start_offset", 0))
        if not ordered:
            return False
        position = 0
        for index, span in enumerate(ordered):
            if span.get("start_offset") != position:
                return False
            if block[span["start_offset"]:span["end_offset"]] != span.get("text"):
                return False
            position = span["end_offset"]
            if index < len(ordered) - 1:
                if position >= len(block) or block[position] != "\n":
                    return False
                position += 1
        if position != len(block):
            return False
        if "\n".join(s.get("text", "") for s in ordered) != block:
            return False
    return True


def _anchor_stats(ctx):
    spans = (ctx.get("spans_doc") or {}).get("spans") or []
    page_docs = ctx.get("page_docs") or {}
    offset_bad = 0
    glyph_misaligned = 0
    for span in spans:
        block = _page_block(page_docs.get(span.get("page")) or {"lines": []})
        start = span.get("start_offset")
        end = span.get("end_offset")
        if not all(isinstance(v, int) for v in (start, end)) or start < 0 or end > len(block) or block[start:end] != span.get("text"):
            offset_bad += 1
        joined = "".join(
            char.get("char")
            for char in (span.get("source_anchor") or {}).get("chars") or []
            if char.get("char")
        )
        if joined != span.get("text"):
            glyph_misaligned += 1
    quote_stored = any(span.get("quote_sha256") is not None for span in spans)
    return {
        "offset_bad": offset_bad,
        "glyph_misaligned": glyph_misaligned,
        "quote_stored": quote_stored,
        "level": (ctx.get("spans_doc") or {}).get("evidence_level"),
    }


# ---------------------------------------------------------------- 九项判定
def _check_inputs_frozen(state):
    summary = state["summary"]
    if summary.get("status") != "succeeded":
        return False, "run_m5 未成功: %s" % summary.get("status")
    row = state["service"].get_step_run(summary["step_run_id"])
    request = json.loads(row["request_json"])
    frozen = request["input_artifact_ids"]
    if len(frozen) != 17:
        return False, "冻结输入 %d != 17" % len(frozen)
    for revision_id in frozen:
        revision = state["service"].get_revision(revision_id)
        if revision is None or revision["status"] != "sealed":
            return False, "冻结修订未 sealed: %s" % revision_id
    if set(frozen) != set(state["inputs"]["frozen_revision_ids"]):
        return False, "冻结集合 != resolve_m5_inputs 角色集合"
    return True, "frozen=17"


def _check_validator_checkpoints(state):
    reports = state["summary"]["validator_report_revision_ids"]
    if len(reports) != 14:
        return False, "Validator 报告 %d != 14" % len(reports)
    checkpoints = state["service"].list_checkpoints(EDITION_PART, "m5")
    if len(checkpoints) != 14:
        return False, "m5 Checkpoint %d != 14" % len(checkpoints)
    task_ids = [cp["content"]["completed_tasks"][0]["task_id"] for cp in checkpoints]
    if task_ids != [vid for vid, _g, _f in VALIDATORS]:
        return False, "task_id 顺序与注册表不符"
    step_manifest = _read_doc(state["service"], state["summary"]["step_manifest_revision_id"])
    if step_manifest["last_checkpoint_revision_id"] != checkpoints[-1]["artifact_revision_id"]:
        return False, "StepManifest.last_checkpoint_revision_id 不是末个 Checkpoint"
    return True, "reports=14 checkpoints=14"


def _check_g1_source_replay(state):
    ctx = state["ctx"]
    if _frozen_mismatch_count(ctx):
        return False, "冻结字节哈希不符"
    if not _content_hash_ok(ctx):
        return False, "content_sha256 与 spans 修订不符"
    if _unresolved_count(ctx) != 4:
        return False, "未决字符发现 %d != 4" % _unresolved_count(ctx)
    _gate, replay = resolve("g1_replay")
    if replay(ctx)["findings"]:
        return False, "重放发现非空"
    if state["gate_results"]["gates"]["G1"] != "passed_with_warnings":
        return False, "gate_results.G1 != passed_with_warnings"
    return True, "unresolved=4 replay=ok"


def _check_g2_coverage(state):
    if not _coverage_ok(state["ctx"]):
        return False, "覆盖/连续/拼接重算失败"
    if state["gate_results"]["gates"]["G2"] != "passed":
        return False, "gate_results.G2 != passed"
    return True, "coverage=ok"


def _check_g3_anchor_offset(state):
    stats = _anchor_stats(state["ctx"])
    if stats["offset_bad"]:
        return False, "严格 offset 失败 %d 条" % stats["offset_bad"]
    if stats["glyph_misaligned"] != 2:
        return False, "字框文本不对齐 %d != 2" % stats["glyph_misaligned"]
    if stats["level"] != "glyphbox_level":
        return False, "evidence_level != glyphbox_level"
    if state["gate_results"]["gates"]["G3"] != "passed_with_warnings":
        return False, "gate_results.G3 != passed_with_warnings"
    return True, "offset=ok glyph_misaligned=2"


def _check_gate_and_levels(state):
    gate = state["gate_results"]
    verdicts = gate["level_verdicts"]
    if dict(verdicts) != {
        "INTERNAL_DEMO": "passed",
        "DEV_SEARCH": "failed",
        "PUBLIC_RELEASE": "failed",
    }:
        return False, "level_verdicts 非 {passed, failed, failed}"
    if gate["gate"]["passed"] != (verdicts["INTERNAL_DEMO"] == "passed"):
        return False, "gate.passed 与 INTERNAL_DEMO 结论不一致"
    return True, "gate.passed=true"


def _check_package_lineage(state):
    package = state["package"]
    _validate_stage_package(package)
    gate_bytes = _canonical(state["gate_results"])
    if package["manifest"]["content_sha256"] != hashlib.sha256(gate_bytes).hexdigest():
        return False, "content_sha256 != gate_results 字节哈希"
    frozen = json.loads(
        state["service"].get_step_run(state["summary"]["step_run_id"])["request_json"]
    )["input_artifact_ids"]
    lineage_revisions = {
        ref["artifact_revision_id"] for ref in package["lineage"]["upstream_artifacts"]
    }
    if not lineage_revisions <= set(frozen):
        return False, "lineage 输入不在冻结集合内"
    for value in package["payload"].values():
        if isinstance(value, str) and value.startswith("rev_"):
            if state["service"].get_revision(value) is None:
                return False, "payload 修订不可解析: %s" % value
    config_revision = json.loads(
        state["service"].get_step_run(state["summary"]["step_run_id"])["request_json"]
    )["configuration_artifact_id"]
    config = _read_doc(state["service"], config_revision)
    if config.get("target_consumption_level") != "INTERNAL_DEMO":
        return False, "配置未记录 target_consumption_level"
    return True, "package=sealed lineage=ok"


def _check_fail_closed_tamper(state):
    result = fail_closed_probe(state["fixture"])
    if result["skipped"] != 13:
        return False, "skipped_fail_closed %d != 13" % result["skipped"]
    if result["level_verdicts"]["INTERNAL_DEMO"] != "failed":
        return False, "三级未全 failed"
    if not result["step_run_succeeded"]:
        return False, "gate 未过时 StepRun 应为 succeeded"
    if not result["package_sealed"] or result["validation_passed"]:
        return False, "m5 包应照常封存且 validation.passed=false"
    if result["downstream_consumable"]:
        return False, "下游仅凭 succeeded 不得放行"
    return True, "skipped=13 levels=failed sealed"


def _check_adversarial_bypass(state):
    expected = {
        "offset_mismatch": "offset_mismatch",
        "page_hash_mismatch": "page_image_hash_mismatch",
        "dropped_last_span": "coverage_gap",
        "offset_level": "evidence_level_insufficient",
    }
    for name, check in expected.items():
        hits = adversarial_checks(state["fixture"], name)
        if check not in hits and not (
            name == "dropped_last_span"
            and ({"span_boundary_mismatch", "count_mismatch"} & hits)
        ):
            return False, "对抗场景 %s 未命中 %s" % (name, check)
    return True, "adversarial=4/4"


_CHECKS = (
    ("inputs_frozen", _check_inputs_frozen),
    ("validator_checkpoints", _check_validator_checkpoints),
    ("g1_source_replay", _check_g1_source_replay),
    ("g2_coverage", _check_g2_coverage),
    ("g3_anchor_offset", _check_g3_anchor_offset),
    ("gate_and_levels", _check_gate_and_levels),
    ("package_lineage", _check_package_lineage),
    ("fail_closed_tamper", _check_fail_closed_tamper),
    ("adversarial_bypass", _check_adversarial_bypass),
)


def _canonical(doc):
    return json.dumps(
        doc, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def _validate_stage_package(package):
    import jsonschema
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    schemas_dir = Path(__file__).resolve().parents[2] / "openspec" / "schemas"
    schema = json.loads((schemas_dir / "stage_package.schema.json").read_text(encoding="utf-8"))
    artifact_ref = json.loads((schemas_dir / "artifact_ref.schema.json").read_text(encoding="utf-8"))
    registry = Registry().with_resource(
        "artifact_ref.schema.json",
        Resource.from_contents(artifact_ref, default_specification=DRAFT202012),
    )
    jsonschema.Draft202012Validator(schema, registry=registry).validate(package)


# ---------------------------------------------------------------- 对抗与 fail-closed
def _reserialize(result):
    result["spans_bytes"] = dump_yaml(result["spans_doc"])
    result["spans_sha256"] = hashlib.sha256(result["spans_bytes"]).hexdigest()
    return result


def _mut_offset(result):
    result["spans"][0]["start_offset"] += 1
    result["spans"][0]["end_offset"] += 1
    return _reserialize(result)


def _mut_page_hash(result):
    result["spans"][0]["source_anchor"]["image_sha256"] = "0" * 64
    return _reserialize(result)


def _mut_drop_last(result):
    result["spans_doc"]["spans"] = result["spans_doc"]["spans"][:-1]
    result["spans"] = result["spans_doc"]["spans"]
    return _reserialize(result)


def _mut_offset_level(result):
    result["spans_doc"]["evidence_level"] = "offset_level"
    return _reserialize(result)


ADVERSARIAL = {
    "offset_mismatch": (_mut_offset, "INTERNAL_DEMO", "offset_mismatch"),
    "page_hash_mismatch": (_mut_page_hash, "INTERNAL_DEMO", "page_image_hash_mismatch"),
    "dropped_last_span": (_mut_drop_last, "INTERNAL_DEMO", "coverage_gap"),
    "offset_level": (_mut_offset_level, "PUBLIC_RELEASE", "evidence_level_insufficient"),
}


def _passed_gate():
    return {
        "gate_profile": "structural_only",
        "structural": "passed",
        "semantic": "not_evaluated",
        "checks": {},
        "pages": {},
    }


def _fake_structural(mutate):
    def fake(*args, **kwargs):
        return mutate(_compiler.compile_structural(*args, **kwargs))

    return fake


def adversarial_checks(fixture_dir, name):
    """在 mock compiler 构造的 sealed 错误 m3 包上跑 M5，返回命中的检查名集合。"""
    mutate, target_level, _expected = ADVERSARIAL[name]
    root = tempfile.mkdtemp(prefix="m5-adv-")
    service = LedgerService(Path(root) / "ledger")
    try:
        fixture_ingest.ingest(fixture_dir, service, stages=("m1", "m2"))
        with mock.patch(
            "pipeline.corpus_compiler.step.compile_structural",
            side_effect=_fake_structural(mutate),
        ), mock.patch(
            "pipeline.corpus_compiler.step.evaluate_structural",
            return_value=_passed_gate(),
        ):
            run_m3(service, EDITION_PART)
        summary = run_m5(
            service, EDITION_PART, target_consumption_level=target_level
        )
        gate_results = _read_doc(service, summary["gate_results_revision_id"])
        return {
            finding["check"]
            for finding in gate_results["failures"] + gate_results["warnings"]
        }
    finally:
        service.close()
        shutil.rmtree(root, ignore_errors=True)


def fail_closed_probe(fixture_dir):
    """篡改 corpus_spans 对象一字节，跑 M5，返回 fail-closed 观测结果。"""
    root = tempfile.mkdtemp(prefix="m5-tamper-")
    service = LedgerService(Path(root) / "ledger")
    try:
        fixture_ingest.ingest(fixture_dir, service, stages=("m1", "m2"))
        run_m3(service, EDITION_PART)
        inputs = resolve_m5_inputs(service, EDITION_PART)
        spans_row = service.get_revision(inputs["corpus_spans_revision_id"])
        (service.root / spans_row["object_key"]).write_bytes(b"tampered: true\n")
        summary = run_m5(service, EDITION_PART)
        gate_results = _read_doc(service, summary["gate_results_revision_id"])
        statuses = [item["task_status"] for item in gate_results["validators"]]
        package = _read_doc(service, summary["package_revision_id"])
        step_run_succeeded = (
            service.get_step_run(summary["step_run_id"])["status"] == "succeeded"
        )
        validation_passed = package["validation"]["passed"]
        return {
            "skipped": statuses.count("skipped_fail_closed"),
            "level_verdicts": gate_results["level_verdicts"],
            "step_run_succeeded": step_run_succeeded,
            "package_sealed": package["status"] == "sealed",
            "validation_passed": validation_passed,
            "downstream_consumable": step_run_succeeded and validation_passed,
        }
    finally:
        service.close()
        shutil.rmtree(root, ignore_errors=True)


def _quote_hash_line(state):
    """``quote_hash_stored`` 按实判定（R83，第 100 条 D5）。

    - offset 档：片段确实存了 ``quote_sha256`` → PASS；未存 → BLOCKED（如实）。
    - OCR 档（``glyphbox_level``）：逐字保留原 BLOCKED 文案——fixture 的
      ``glyphbox_level`` spans 本就不带 quote hash（§11.1）。
    """
    stats = _anchor_stats(state["ctx"])
    if stats["level"] != _OFFSET_LEVEL:
        return "BLOCKED quote_hash_stored %s" % QUOTE_HASH_BLOCKED
    if stats["quote_stored"]:
        return "PASS quote_hash_stored offset 片段已存储 quote_sha256"
    return "BLOCKED quote_hash_stored 前置缺失: M3 Corpus Compilation；offset 片段未存储 quote hash（§11.1）"


# ---------------------------------------------------------------- 入口
def _evaluate(fixture_dir, *, keep=False):
    lines = []
    with harness(fixture_dir, keep=keep) as state:
        for name, func in _CHECKS:
            try:
                ok, detail = func(state)
            except Exception as exc:  # noqa: BLE001 —— 判定内异常转该项 FAIL
                ok, detail = False, "%s: %s" % (type(exc).__name__, exc)
            lines.append(("PASS %s" % name) if ok else ("FAIL %s %s" % (name, detail)))
        for name, description in BLOCKED_ITEMS:
            lines.append("BLOCKED %s %s" % (name, description))
        lines.append(_quote_hash_line(state))
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pipeline.validation.acceptance",
        description="m5-evidence-gate 验收（规格 §19.0）",
    )
    parser.add_argument("--fixture", required=True, help="fixture 根目录")
    parser.add_argument("--keep", action="store_true", help="保留临时目录")
    args = parser.parse_args(argv)

    fixture = Path(args.fixture)
    if not (fixture / "manifest.yaml").is_file():
        print("BLOCKED m5_evidence_gate 前置缺失: fixture/manifest.yaml 不存在")
        print("SUMMARY pass=0 fail=0 blocked=1")
        return 3
    try:
        import jsonschema  # noqa: F401
        import yaml  # noqa: F401
    except ImportError:
        print("BLOCKED m5_evidence_gate 前置缺失: yaml/jsonschema 不可导入")
        print("SUMMARY pass=0 fail=0 blocked=1")
        return 3

    try:
        lines = _evaluate(fixture, keep=args.keep)
    except Exception as exc:  # noqa: BLE001 —— 宿主准备失败
        print("FAIL m5_acceptance 宿主准备失败: %s: %s" % (type(exc).__name__, exc))
        print("SUMMARY pass=0 fail=1 blocked=0")
        return 1

    for line in lines:
        print(line)
    passed = sum(1 for line in lines if line.startswith("PASS "))
    failed = sum(1 for line in lines if line.startswith("FAIL "))
    blocked = sum(1 for line in lines if line.startswith("BLOCKED "))
    print("SUMMARY pass=%d fail=%d blocked=%d" % (passed, failed, blocked))
    if failed:
        return 1
    if blocked:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
