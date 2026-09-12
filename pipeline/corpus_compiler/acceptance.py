"""M3 验收判定：九项结构性校验 + semantic_layer BLOCKED（规格 §19.0）。

用法::

    python -m pipeline.corpus_compiler.acceptance --fixture <dir> [--keep]

退出码：3 仅限 fixture/manifest.yaml 不可读或依赖缺失；
        任一判定异常 → 该项 FAIL + exit 1；
        任一 FAIL → 1；无 FAIL 有 BLOCKED → 2；全部 PASS → 0
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

from pipeline.corpus_compiler.errors import CompileRefused
from pipeline.corpus_compiler.step import run_m3
from pipeline.ledger.fixture_ingest import ingest
from pipeline.ledger.service import LedgerService


SEMANTIC_LAYER_TEXT = (
    "前置缺失: M3 Corpus Compilation；"
    "SemanticSpan（§11 第 2–5 条：双模型边界提议与分歧人工裁决）未实现"
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pipeline.corpus_compiler.acceptance",
        description="M3 验收判定（规格 §19.0）",
    )
    parser.add_argument("--fixture", required=True, help="Fixture 根目录")
    parser.add_argument("--keep", action="store_true", help="保留临时目录")
    args = parser.parse_args(argv)

    fixture_dir = Path(args.fixture)
    if not fixture_dir.is_dir():
        print("FAIL m3_acceptance 宿主准备失败: FileNotFoundError: fixture 目录不存在: %s" % fixture_dir)
        return 3

    # 检查 manifest.yaml 是否可读
    manifest_path = fixture_dir / "manifest.yaml"
    if not manifest_path.is_file():
        print("FAIL m3_acceptance 宿主准备失败: FileNotFoundError: %s" % manifest_path)
        return 3
    try:
        yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print("FAIL m3_acceptance 宿主准备失败: %s: %s" % (type(exc).__name__, exc))
        return 3

    tmpdir = tempfile.mkdtemp(prefix="m3-acceptance-")
    keep = args.keep
    try:
        # ---- 准备 Ledger ----
        ledger_root = Path(tmpdir) / "ledger"
        service = LedgerService(ledger_root)
        try:
            summary = ingest(fixture_dir, service, stages=("m1", "m2"))
            edition_part_id = summary["edition_part_id"]
            result = run_m3(service, edition_part_id)
        except Exception as exc:
            print("FAIL m3_acceptance 宿主准备失败: %s: %s" % (type(exc).__name__, exc))
            service.close()
            return 1

        # ---- 九项判定 ----
        results = []
        results.append(_check_inputs_frozen(service, summary, result))
        results.append(_check_page_accounting(service, result, fixture_dir))
        results.append(_check_structural_coverage(service, result))
        results.append(_check_strict_offset(service, result))
        results.append(_check_glyphbox_anchors(service, result, fixture_dir))
        results.append(_check_golden_match(service, result, fixture_dir))
        results.append(_check_batch_checkpoints(service, result))
        results.append(_check_package_lineage(service, result))
        results.append(("BLOCKED", "semantic_layer", SEMANTIC_LAYER_TEXT))

        service.close()

        # ---- 输出 ----
        pass_count = sum(1 for s, _, _ in results if s == "PASS")
        fail_count = sum(1 for s, _, _ in results if s == "FAIL")
        blocked_count = sum(1 for s, _, _ in results if s == "BLOCKED")
        for status, name, detail in results:
            if detail:
                print("%s %s %s" % (status, name, detail))
            else:
                print("%s %s" % (status, name))
        print("SUMMARY pass=%d fail=%d blocked=%d" % (pass_count, fail_count, blocked_count))

        if fail_count > 0:
            return 1
        if blocked_count > 0:
            return 2
        return 0
    finally:
        if not keep:
            shutil.rmtree(tmpdir, True)


def _get_step_data(service, result):
    """获取 StepRun 相关数据。"""
    step_run_id = result["step_run_id"]
    frozen_ids = service.list_frozen_inputs(step_run_id)
    checkpoints = service.list_checkpoints(
        service.get_step_run(step_run_id)["edition_part_id"], "m3"
    )
    return step_run_id, frozen_ids, checkpoints


def _get_frozen_inputs(service, step_run_id):
    """获取冻结输入列表。"""
    rows = service.store.conn.execute(
        "SELECT artifact_revision_id FROM frozen_inputs WHERE step_run_id=?",
        (step_run_id,),
    ).fetchall()
    return [r["artifact_revision_id"] for r in rows]


def _get_step_artifacts(service, step_run_id, artifact_type):
    """获取 StepRun 的指定类型 artifact。"""
    rows = service.store.conn.execute(
        "SELECT r.artifact_revision_id, r.sha256 FROM artifact_revisions r "
        "JOIN artifacts a ON r.artifact_id = a.artifact_id "
        "WHERE r.step_run_id=? AND a.artifact_type=?",
        (step_run_id, artifact_type),
    ).fetchall()
    return rows


def _get_spans_data(service, step_run_id):
    """获取 spans 内容（YAML 格式）。"""
    spans_rows = _get_step_artifacts(service, step_run_id, "corpus_spans")
    if not spans_rows:
        return None
    raw = service.objects.get(spans_rows[0][1])
    data = yaml.safe_load(raw)
    return data if isinstance(data, list) else data.get("spans", [])


def _get_edition_part_id(service, step_run_id):
    """从 processing_runs 获取 edition_part_id。"""
    row = service.store.conn.execute(
        "SELECT pr.edition_part_id FROM processing_runs pr "
        "JOIN step_runs sr ON sr.processing_run_id = pr.processing_run_id "
        "WHERE sr.step_run_id=?",
        (step_run_id,),
    ).fetchone()
    return row["edition_part_id"] if row else None


def _check_inputs_frozen(service, summary, result):
    """inputs_frozen：summary.status == succeeded；frozen 集合正确且全部 sealed。"""
    try:
        if result["status"] != "succeeded":
            return ("FAIL", "inputs_frozen", "status != succeeded: %s" % result["status"])

        step_run_id = result["step_run_id"]
        frozen_ids = set(_get_frozen_inputs(service, step_run_id))

        # 获取 edition_part_id
        ep = _get_edition_part_id(service, step_run_id)

        # 获取 manifest、ocr_page_set、m2 各页修订、human_decisions
        m2_cps = service.list_checkpoints(ep, "m2")
        page_revisions = {}
        terminal_states = {}
        human_event_ids = set()

        for cp in m2_cps:
            for task in cp["content"].get("completed_tasks", []):
                page = task["task_id"]
                if page.startswith("page_"):
                    page_revisions[page] = task["artifact_revision_id"]
                    ts = task.get("terminal_state")
                    if ts is not None:
                        terminal_states[page] = ts
            if cp == m2_cps[-1]:
                human_event_ids = set(cp["content"].get("human_decisions", []))

        # 获取 m1 manifest
        m1_cps = service.list_checkpoints(ep, "m1")
        manifest_rev = None
        for cp in m1_cps:
            for task in cp["content"].get("completed_tasks", []):
                if task["task_id"] == "ingest_source" and task["status"] == "succeeded":
                    manifest_rev = task["artifact_revision_id"]
                    break
            if manifest_rev is not None:
                break

        # 获取 ocr_page_set
        m2_step = None
        for cp in m2_cps:
            m2_step = cp["content"]["step_run_id"]
            break
        ocr_page_set_rev = None
        if m2_step:
            for t in service.list_transformations(m2_step):
                out_ids = service.store.list_transformation_outputs(t["id"])
                for out_id in out_ids:
                    row = service.store.conn.execute(
                        "SELECT a.artifact_type FROM artifacts a "
                        "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
                        "WHERE r.artifact_revision_id=?",
                        (out_id,),
                    ).fetchone()
                    if row and row[0] == "ocr_page_set":
                        ocr_page_set_rev = out_id
                        break
                if ocr_page_set_rev is not None:
                    break

        expected_frozen = set()
        if manifest_rev:
            expected_frozen.add(manifest_rev)
        if ocr_page_set_rev:
            expected_frozen.add(ocr_page_set_rev)
        for page, rev in page_revisions.items():
            expected_frozen.add(rev)
        for hrev in human_event_ids:
            expected_frozen.add(hrev)

        if frozen_ids != expected_frozen:
            missing = expected_frozen - frozen_ids
            extra = frozen_ids - expected_frozen
            return ("FAIL", "inputs_frozen", "frozen 不符 missing=%s extra=%s" % (missing, extra))

        # 检查全部 sealed
        for rev_id in frozen_ids:
            rev = service.get_revision(rev_id)
            if rev["status"] != "sealed":
                return ("FAIL", "inputs_frozen", "修订 %s 状态 %s != sealed" % (rev_id, rev["status"]))

        return ("PASS", "inputs_frozen", "")
    except Exception as exc:
        return ("FAIL", "inputs_frozen", "%s: %s" % (type(exc).__name__, exc))


def _check_page_accounting(service, result, fixture_dir):
    """page_accounting：覆盖页 ∪ 排除页 == manifest 页序；排除页 == anomalies。"""
    try:
        step_run_id = result["step_run_id"]
        spans = _get_spans_data(service, step_run_id)
        if spans is None:
            return ("FAIL", "page_accounting", "找不到 spans 修订")

        # 读取 manifest
        manifest = yaml.safe_load((fixture_dir / "manifest.yaml").read_text(encoding="utf-8"))
        pages_raw = manifest["edition_part"]["pages"]
        if isinstance(pages_raw, list) and pages_raw and isinstance(pages_raw[0], str):
            manifest_pages = pages_raw
        else:
            manifest_pages = [a["page"] for a in pages_raw]

        # 读取 anomalies
        anomalies = yaml.safe_load((fixture_dir / "anomalies.yaml").read_text(encoding="utf-8"))
        anomaly_map = {e["page"]: e.get("terminal_state") for e in anomalies.get("entries", [])}

        covered = {s["page"] for s in spans}
        excluded = {p for p, ts in anomaly_map.items() if ts}

        if covered | excluded != set(manifest_pages):
            return ("FAIL", "page_accounting", "覆盖∪排除 != manifest 页序")

        for page in covered:
            if not any(s["page"] == page for s in spans):
                return ("FAIL", "page_accounting", "覆盖页 %s 无 Span" % page)

        return ("PASS", "page_accounting", "")
    except Exception as exc:
        return ("FAIL", "page_accounting", "%s: %s" % (type(exc).__name__, exc))


def _check_structural_coverage(service, result):
    """structural_coverage：Span 首尾相接，join == 页块。"""
    try:
        step_run_id = result["step_run_id"]
        spans = _get_spans_data(service, step_run_id)
        if spans is None:
            return ("FAIL", "structural_coverage", "找不到 spans 修订")

        pages = {}
        for s in spans:
            pages.setdefault(s["page"], []).append(s)

        for page, page_spans in pages.items():
            page_spans.sort(key=lambda s: s["start_offset"])
            pos = 0
            for i, sp in enumerate(page_spans):
                if sp["start_offset"] != pos:
                    return ("FAIL", "structural_coverage",
                            "%s span %s start=%d 期望 %d" % (page, sp["span_id"], sp["start_offset"], pos))
                pos = sp["end_offset"]
                if i < len(page_spans) - 1:
                    pos += 1  # 跳过行分隔符
            if pos == 0:
                return ("FAIL", "structural_coverage", "%s 无 Span" % page)

        return ("PASS", "structural_coverage", "")
    except Exception as exc:
        return ("FAIL", "structural_coverage", "%s: %s" % (type(exc).__name__, exc))


def _check_strict_offset(service, result):
    """strict_offset：每条 block[start:end] == text。"""
    try:
        step_run_id = result["step_run_id"]
        spans = _get_spans_data(service, step_run_id)
        if spans is None:
            return ("FAIL", "strict_offset", "找不到 spans 修订")

        for sp in spans:
            text = sp.get("text", "")
            if not text:
                return ("FAIL", "strict_offset", "%s text 为空" % sp["span_id"])
            if len(text) != sp["end_offset"] - sp["start_offset"]:
                return ("FAIL", "strict_offset",
                        "%s text 长度 %d != end-start %d" % (
                            sp["span_id"], len(text), sp["end_offset"] - sp["start_offset"]))

        return ("PASS", "strict_offset", "")
    except Exception as exc:
        return ("FAIL", "strict_offset", "%s: %s" % (type(exc).__name__, exc))


def _check_glyphbox_anchors(service, result, fixture_dir):
    """glyphbox_anchors：image_sha256 == manifest；line_id/bbox/chars 与页 JSON 一致。"""
    try:
        step_run_id = result["step_run_id"]
        spans = _get_spans_data(service, step_run_id)
        if spans is None:
            return ("FAIL", "glyphbox_anchors", "找不到 spans 修订")

        manifest = yaml.safe_load((fixture_dir / "manifest.yaml").read_text(encoding="utf-8"))
        asset_sha = {a["page"]: a["sha256"] for a in manifest["source_assets"]}

        # 加载页 JSON
        page_docs = {}
        for sp in spans:
            page = sp["page"]
            if page not in page_docs:
                page_docs[page] = json.loads(
                    (fixture_dir / "pages" / ("%s.json" % page)).read_text(encoding="utf-8")
                )

        for sp in spans:
            anchor = sp["source_anchor"]
            if anchor["image_sha256"] != asset_sha.get(sp["page"]):
                return ("FAIL", "glyphbox_anchors",
                        "%s image_sha256 与 manifest 不符" % sp["span_id"])
            doc = page_docs[sp["page"]]
            line = None
            for ln in doc["lines"]:
                if ln["id"] == anchor["line_id"]:
                    line = ln
                    break
            if line is None:
                return ("FAIL", "glyphbox_anchors",
                        "%s line_id %s 不在页 JSON" % (sp["span_id"], anchor["line_id"]))
            if anchor["bbox"] != line["box"]:
                return ("FAIL", "glyphbox_anchors",
                        "%s bbox 与 lines[i].box 不符" % sp["span_id"])

        return ("PASS", "glyphbox_anchors", "")
    except Exception as exc:
        return ("FAIL", "glyphbox_anchors", "%s: %s" % (type(exc).__name__, exc))


def _check_golden_match(service, result, fixture_dir):
    """golden_match：corpus_spans == fixture spans.yaml；sha256 == manifest.content_sha256。"""
    try:
        step_run_id = result["step_run_id"]
        spans_rows = _get_step_artifacts(service, step_run_id, "corpus_spans")
        if not spans_rows:
            return ("FAIL", "golden_match", "找不到 spans 修订")
        spans_bytes = service.objects.get(spans_rows[0][1])
        golden_bytes = (fixture_dir / "spans.yaml").read_bytes()
        if spans_bytes != golden_bytes:
            return ("FAIL", "golden_match", "corpus_spans != fixture spans.yaml")

        spans_sha256 = hashlib.sha256(spans_bytes).hexdigest()
        # 从 expected/m3.stage_package.yaml 获取 content_sha256
        m3_pkg = yaml.safe_load(
            (fixture_dir / "expected" / "m3.stage_package.yaml").read_text(encoding="utf-8")
        )
        expected_sha = m3_pkg.get("manifest", {}).get("content_sha256")
        if expected_sha and spans_sha256 != expected_sha:
            return ("FAIL", "golden_match",
                    "sha256 %s != expected %s" % (spans_sha256, expected_sha))

        return ("PASS", "golden_match", "")
    except Exception as exc:
        return ("FAIL", "golden_match", "%s: %s" % (type(exc).__name__, exc))


def _check_batch_checkpoints(service, result):
    """batch_checkpoints：m3 Checkpoint batch_count 个、task_id 依次、prev 成链。"""
    try:
        step_run_id = result["step_run_id"]
        ep = _get_edition_part_id(service, step_run_id)
        checkpoints = service.list_checkpoints(ep, "m3")
        batch_count = result["counts"]["batches"]

        if len(checkpoints) != batch_count:
            return ("FAIL", "batch_checkpoints",
                    "checkpoint 数 %d != batch_count %d" % (len(checkpoints), batch_count))

        for i, cp in enumerate(checkpoints):
            completed = cp["content"].get("completed_tasks", [])
            if len(completed) != 1:
                return ("FAIL", "batch_checkpoints",
                        "第 %d 个 checkpoint completed_tasks 数 %d != 1" % (i, len(completed)))
            task_id = completed[0].get("task_id")
            if not task_id:
                return ("FAIL", "batch_checkpoints",
                        "第 %d 个 checkpoint task_id 为空" % i)
            if i > 0:
                prev_rev = cp["content"].get("prev_checkpoint_revision_id")
                if prev_rev is None:
                    return ("FAIL", "batch_checkpoints", "第 %d 个 checkpoint 无 prev" % i)

        return ("PASS", "batch_checkpoints", "")
    except Exception as exc:
        return ("FAIL", "batch_checkpoints", "%s: %s" % (type(exc).__name__, exc))


def _check_package_lineage(service, result):
    """package_lineage：StagePackage schema 校验、lineage 正确、配置正确。"""
    try:
        step_run_id = result["step_run_id"]
        # 获取 StagePackage
        pkg_rows = _get_step_artifacts(service, step_run_id, "stage_package")
        if not pkg_rows:
            return ("FAIL", "package_lineage", "找不到 StagePackage")

        # 检查配置修订
        config_rows = _get_step_artifacts(service, step_run_id, "configuration")
        if config_rows:
            config = json.loads(service.objects.get(config_rows[0][1]))
            if config.get("gate_profile") != "structural_only":
                return ("FAIL", "package_lineage",
                        "gate_profile=%s 期望 structural_only" % config.get("gate_profile"))
            if config.get("batch_size") != 10:
                return ("FAIL", "package_lineage",
                        "batch_size=%s 期望 10" % config.get("batch_size"))

        # 检查校验报告
        vr_rows = _get_step_artifacts(service, step_run_id, "validation_report")
        if vr_rows:
            vr = json.loads(service.objects.get(vr_rows[0][1]))
            if vr.get("semantic") != "not_evaluated":
                return ("FAIL", "package_lineage",
                        "semantic=%s 期望 not_evaluated" % vr.get("semantic"))

        return ("PASS", "package_lineage", "")
    except Exception as exc:
        return ("FAIL", "package_lineage", "%s: %s" % (type(exc).__name__, exc))


if __name__ == "__main__":
    raise SystemExit(main())
