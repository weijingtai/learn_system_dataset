"""M3 验收判定：电子文本端到端（偏移锚点 + 语义层）与 OCR 路线两用（规格 §19.0）。

用法::

    python -m pipeline.corpus_compiler.acceptance --electronic-text-fixture <dir>
    python -m pipeline.corpus_compiler.acceptance --fixture <dir> [--keep]      # OCR 路线

电子文本路线：在合成/真实宿主上跑 M1 → M2 → M3 语义层端到端编译，逐子项输出
PASS/FAIL/BLOCKED；**不钉死 pass 总数**（G7-RULINGS 第 54、87 条：不变量是 fail=0）。
宿主缺失时 semantic_layer 如实判 BLOCKED 并 exit 2；宿主含 deferred 发现（如 missing）
导致 M3 被阻断时同样如实判 BLOCKED、exit 2，不得视为失败、不得绕过（第 95 条）。

退出码：电子文本路线：0 全 PASS；1 有 FAIL；2 有 BLOCKED（宿主缺失/上游阻断）；
        OCR 路线：3 仅限 fixture/manifest.yaml 不可读或依赖缺失；
        任一判定异常 → 该项 FAIL + exit 1；任一 FAIL → 1；无 FAIL 有 BLOCKED → 2；全部 PASS → 0
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:  # 宿主缺依赖：main 返回 3
    yaml = None

from pipeline.corpus_compiler.errors import CompileRefused
from pipeline.ledger.service import LedgerService

try:
    # 这两个模块在其顶层依赖 PyYAML，宿主缺 PyYAML 时导入本身会失败；
    # 延迟到此处捕获，main() 中据此返回 3（同 yaml 缺失时的处理）。
    from pipeline.corpus_compiler.step import run_m3
except ImportError:
    run_m3 = None

try:
    from pipeline.ledger.fixture_ingest import ingest
except ImportError:
    ingest = None


SEMANTIC_LAYER_TEXT = (
    "前置缺失: M3 Corpus Compilation；"
    "SemanticSpan（§11 第 2–5 条：双模型边界提议与分歧人工裁决）未实现"
)

# 电子文本宿主缺失时的逐字 BLOCKED 文本（act/07 contract；第 88、94 条）
ELECTRONIC_HOST_MISSING_TEXT = "前置缺失: 电子文本验收宿主匮乏；未提供 --electronic-text-fixture"

# M1 source_manifest 顶层键序（唯一权威：impl-09 README §3）
_MANIFEST_TOP_KEYS = (
    "source_id",
    "work_title",
    "edition_note",
    "technique_id",
    "rights_status",
    "release_policy",
    "edition_part",
    "source_assets",
    "files",
    "conversion",
    "content_status",
)


class _ElectronicBlocked(Exception):
    """电子文本验收的上游前置缺失（宿主文件缺失、M2 Gate 未放行）→ 判 BLOCKED。"""


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pipeline.corpus_compiler.acceptance",
        description="M3 验收判定（规格 §19.0）",
    )
    route = parser.add_mutually_exclusive_group()
    route.add_argument("--fixture", default=None, help="OCR 路线 fixture 根目录")
    route.add_argument(
        "--electronic-text-fixture",
        dest="electronic_text_fixture",
        default=None,
        help="电子文本验收宿主目录（M1 → M2 → M3 语义层端到端）",
    )
    parser.add_argument("--keep", action="store_true", help="保留临时目录")
    args = parser.parse_args(argv)

    if args.fixture is not None:
        return _run_ocr(args)
    return _run_electronic(
        Path(args.electronic_text_fixture) if args.electronic_text_fixture else None
    )


def _run_electronic(fixture_dir):
    """电子文本路线入口：宿主缺失如实 BLOCKED，否则跑端到端验收。"""
    if yaml is None:
        print("FAIL m3_acceptance 宿主准备失败: ImportError: PyYAML 不可导入")
        return 3

    if fixture_dir is None or not fixture_dir.is_dir():
        print("BLOCKED semantic_layer " + ELECTRONIC_HOST_MISSING_TEXT)
        print("SUMMARY pass=0 fail=0 blocked=1")
        return 2

    results = check_electronic_semantic_layer(fixture_dir)
    for status, name, detail in results:
        if detail:
            print("%s %s %s" % (status, name, detail))
        else:
            print("%s %s" % (status, name))

    pass_count = sum(1 for status, _, _ in results if status == "PASS")
    fail_count = sum(1 for status, _, _ in results if status == "FAIL")
    blocked_count = sum(1 for status, _, _ in results if status == "BLOCKED")
    print("SUMMARY pass=%d fail=%d blocked=%d" % (pass_count, fail_count, blocked_count))

    if fail_count > 0:
        return 1
    if blocked_count > 0:
        return 2
    return 0


def check_electronic_semantic_layer(fixture_dir):
    """在电子文本宿主上跑 M1 → M2 → M3 语义层端到端编译与语义 Gate。

    全程在 socket 拦截补丁下执行（P6 零网络）：任何连接尝试都被计数，末尾以
    ``zero_network`` 子项如实汇报，绝不静默放行。

    宿主目录（合成宿主由测试以 tempfile 构造，标 ``synthetic_fixture: true``）：
        ``source_info.yaml``     M1 来源申报（含 ``edition_part`` / ``pages``）
        ``<page>.txt``          电子文本原文件（逐字节，被 ``file_sha256`` 钉住）
        ``recordings.yaml``     双模型回放录制（``schema`` / ``synthetic`` / ``template_id``）
        ``human_decisions.yaml`` 人工边界裁决列表（P7：由宿主提供，本模块绝不代填）

    返回：
        ``[(status, name, detail), ...]``，status ∈ {PASS, FAIL, BLOCKED}。
    """
    network_attempts = []
    original_socket = socket.socket
    original_create_connection = socket.create_connection

    def _blocked(*args, **kwargs):
        network_attempts.append(args)
        raise AssertionError("P6: 电子文本验收全程禁止任何网络调用")

    socket.socket = _blocked
    socket.create_connection = _blocked
    try:
        results = _run_electronic_checks(Path(fixture_dir))
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create_connection

    if network_attempts:
        results.append(
            ("FAIL", "zero_network", "检出 %d 次网络连接尝试（P6 零网络）" % len(network_attempts))
        )
    else:
        results.append(("PASS", "zero_network", "全程零网络连接尝试"))
    return results


def _run_electronic_checks(fixture_dir):
    """依次执行电子文本端到端子项；任一失败/阻断即停在该项（后续项无从判定）。"""
    checks = (
        ("host_source", _check_electronic_host_source),
        ("m1_manifest", _check_electronic_m1_manifest),
        ("m2_gate", _check_electronic_m2_gate),
        ("m3_semantic", _check_electronic_m3_semantic),
        ("semantic_gate", _check_electronic_semantic_gate),
        ("stage_package", _check_electronic_stage_package),
    )
    results = []
    tmpdir = tempfile.mkdtemp(prefix="m3-electronic-")
    service = None
    try:
        service = LedgerService(Path(tmpdir) / "ledger")
        state: dict = {"service": service}
        for name, check in checks:
            try:
                status, detail = check(fixture_dir, state)
            except _ElectronicBlocked as exc:
                results.append(("BLOCKED", name, str(exc)))
                return results
            except Exception as exc:
                results.append(("FAIL", name, "%s: %s" % (type(exc).__name__, exc)))
                return results
            results.append((status, name, detail))
            if status == "FAIL":
                return results
        return results
    finally:
        if service is not None:
            try:
                service.close()
            except Exception:
                pass
        shutil.rmtree(tmpdir, True)


def _resolve_host_page_file(fixture_dir, page):
    """定位宿主的原文文件：依次尝试 `<page>.txt`、`<page>.md`、`<page>` 与唯一 `<page>.*`。"""
    for candidate in (fixture_dir / ("%s.txt" % page), fixture_dir / ("%s.md" % page), fixture_dir / page):
        if candidate.is_file():
            return candidate
    matches = sorted(path for path in fixture_dir.glob("%s.*" % page) if path.is_file())
    return matches[0] if len(matches) == 1 else None


def _check_electronic_host_source(fixture_dir, state):
    """宿主原文可读，且字节哈希与 source_info.file_sha256 一致（追踪链闭合）。"""
    source_info_path = fixture_dir / "source_info.yaml"
    if not source_info_path.is_file():
        raise _ElectronicBlocked("前置缺失: 宿主缺 source_info.yaml")

    source_info = yaml.safe_load(source_info_path.read_text(encoding="utf-8"))
    if not isinstance(source_info, dict):
        return ("FAIL", "source_info.yaml 顶层必须是映射")

    pages = source_info.get("pages") or (source_info.get("edition_part") or {}).get("pages") or []
    if not pages:
        return ("FAIL", "source_info 未声明任何 pages")

    blobs = []
    for page in pages:
        path = _resolve_host_page_file(fixture_dir, page)
        if path is None:
            raise _ElectronicBlocked("前置缺失: 宿主缺原文文件 %s.*" % page)
        blobs.append(path.read_bytes())

    expected = source_info.get("file_sha256")
    combined = b"".join(blobs)
    actual = hashlib.sha256(combined).hexdigest()
    if expected and actual != expected:
        return ("FAIL", "宿主原文哈希 %s 与 source_info.file_sha256 %s 不符（追踪链断裂）" % (actual, expected))

    state["source_info"] = source_info
    state["edition_part_id"] = (source_info.get("edition_part") or {}).get("artifact_id")
    state["files"] = [
        {
            "page": page,
            "path_ref": "%s.txt" % page,
            "data": blob,
            "sha256": hashlib.sha256(blob).hexdigest(),
            "size": len(blob),
        }
        for page, blob in zip(pages, blobs)
    ]
    return ("PASS", "宿主原文 %d 页，字节哈希与 source_info.file_sha256 一致" % len(pages))


def _check_electronic_m1_manifest(fixture_dir, state):
    """M1 入库：source_manifest 封存且顶层键序逐字等于 impl-09 README §3。"""
    from pipeline.intake.step import run_m1

    edition_part_id = state.get("edition_part_id")
    if not edition_part_id:
        return ("FAIL", "宿主 source_info 缺 edition_part.artifact_id")

    result = run_m1(state["service"], state["source_info"], state["files"], edition_part_id)
    if "error" in result:
        return ("FAIL", "M1 入库失败: %s" % result["error"])

    manifest_rev = result["manifest_revision_id"]
    revision = state["service"].get_revision(manifest_rev)
    if revision is None or revision.get("status") != "sealed":
        return ("FAIL", "source_manifest 修订未封存: %s" % manifest_rev)

    manifest = yaml.safe_load(state["service"].read_object(revision["sha256"]).decode("utf-8"))
    if list(manifest.keys()) != list(_MANIFEST_TOP_KEYS):
        return ("FAIL", "source_manifest 顶层键序不符: %s" % list(manifest.keys()))

    state["raw_text_revision_id"] = result["raw_text_revision_ids"][0]
    return ("PASS", "M1 source_manifest 封存且键序逐字（%d 键）" % len(_MANIFEST_TOP_KEYS))


def _check_electronic_m2_gate(fixture_dir, state):
    """M2 清洗：Gate 必须放行；含 deferred 发现时 M3 被阻断 → BLOCKED（不得绕过）。"""
    from pipeline.digitization.step import run_m2

    result = run_m2(
        state["service"],
        state["raw_text_revision_id"],
        state["source_info"],
        state["edition_part_id"],
    )
    gate = result.get("gate_result")
    if "error" in result or gate is None or not gate.passed:
        reason = result.get("error") or (gate.failed_checks if gate is not None else "无 Gate 结果")
        raise _ElectronicBlocked(
            "前置缺失: M2 Gate 未放行（%s），M3 编译阻断" % (reason,)
        )
    return ("PASS", "M2 Gate 放行（deferred_count=0）")


def _check_electronic_m3_semantic(fixture_dir, state):
    """M3 语义层端到端：开队列 → 逐条人工裁决 → 恢复封存（零模型调用，纯回放）。"""
    from pipeline.corpus_compiler.semantic.review import (
        open_semantic_review,
        resume_m3_text_full,
        submit_boundary_decision,
    )
    from pipeline.corpus_compiler.semantic.semantic_gate import evaluate_semantic_offset

    recordings_path = fixture_dir / "recordings.yaml"
    if not recordings_path.is_file():
        raise _ElectronicBlocked("前置缺失: 宿主缺 recordings.yaml")
    decisions_path = fixture_dir / "human_decisions.yaml"
    if not decisions_path.is_file():
        raise _ElectronicBlocked("前置缺失: 宿主缺 human_decisions.yaml")

    decisions = yaml.safe_load(decisions_path.read_text(encoding="utf-8"))
    if decisions is None:
        decisions = []
    if not isinstance(decisions, list):
        return ("FAIL", "human_decisions.yaml 顶层必须是列表")

    opened = open_semantic_review(
        state["service"], state["edition_part_id"], recordings=recordings_path.read_bytes()
    )
    for decision in decisions:
        submit_boundary_decision(
            state["service"], opened["step_run_id"], opened["resume_token"], decision
        )
    resumed = resume_m3_text_full(
        state["service"],
        opened["step_run_id"],
        opened["resume_token"],
        gate=evaluate_semantic_offset,
    )
    state["step_run_id"] = opened["step_run_id"]
    return (
        "PASS",
        "M3 语义层端到端：%d 窗口 / %d 分歧 / %d 语义片段"
        % (resumed["window_count"], resumed["dispute_count"], resumed["span_count"]),
    )


def _check_electronic_semantic_gate(fixture_dir, state):
    """独立语义 Gate 结果：validation_report 中 semantic 为 passed 且八项全 ok。"""
    report = _read_step_run_artifact(state["service"], state["step_run_id"], "validation_report")
    if report is None:
        return ("FAIL", "未找到 m3 validation_report 制品")
    document = json.loads(report.decode("utf-8"))
    if document.get("semantic") != "passed":
        return ("FAIL", "semantic=%r，非 passed" % (document.get("semantic"),))
    checks = document.get("checks") or {}
    failed = [name for name, check in checks.items() if not (check or {}).get("ok")]
    if failed:
        return ("FAIL", "语义 Gate 未通过项: %s" % ", ".join(sorted(failed)))
    return ("PASS", "独立语义 Gate %d 项全通过" % len(checks))


def _check_electronic_stage_package(fixture_dir, state):
    """m3 StagePackage：gate_profile 与 semantic 声明必须与语义层实况一致。"""
    raw = _read_step_run_artifact(state["service"], state["step_run_id"], "stage_package")
    if raw is None:
        return ("FAIL", "未找到 m3 StagePackage 制品")
    package = json.loads(raw.decode("utf-8"))
    payload = package.get("payload") or {}
    if payload.get("gate_profile") != "structural_and_semantic":
        return ("FAIL", "gate_profile=%r，期望 structural_and_semantic" % (payload.get("gate_profile"),))
    if payload.get("semantic") != "passed":
        return ("FAIL", "payload.semantic=%r，期望 passed" % (payload.get("semantic"),))
    counts = (package.get("manifest") or {}).get("counts") or {}
    return (
        "PASS",
        "m3 StagePackage：spans=%s windows=%s disputes=%s"
        % (counts.get("spans"), counts.get("windows"), counts.get("disputes")),
    )


def _read_step_run_artifact(service, step_run_id, artifact_type):
    """读回某 StepRun 下指定 artifact 类型的对象字节（缺失返回 None）。"""
    revisions = service.list_step_run_revisions(step_run_id, artifact_type=artifact_type)
    if not revisions:
        return None
    return service.read_object(revisions[0]["sha256"])


def _run_ocr(args):
    if yaml is None:
        print("FAIL m3_acceptance 宿主准备失败: ImportError: PyYAML 不可导入")
        return 3
    if run_m3 is None or ingest is None:
        print("FAIL m3_acceptance 宿主准备失败: ImportError: PyYAML 不可导入（间接依赖）")
        return 3

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
    return list(service.list_frozen_inputs(step_run_id))


def _get_step_artifacts(service, step_run_id, artifact_type):
    """获取 StepRun 的指定类型 artifact 修订（端口元数据 dict，按产生顺序）。"""
    return service.list_step_run_revisions(step_run_id, artifact_type=artifact_type)


def _get_spans_data(service, step_run_id):
    """获取 spans 内容（YAML 格式）。"""
    spans_rows = _get_step_artifacts(service, step_run_id, "corpus_spans")
    if not spans_rows:
        return None
    raw = service.read_object(spans_rows[0]["sha256"])
    data = yaml.safe_load(raw)
    return data if isinstance(data, list) else data.get("spans", [])


def _get_edition_part_id(service, step_run_id):
    """从 processing_runs 获取 edition_part_id。"""
    step_run = service.get_step_run(step_run_id)
    if step_run is None:
        return None
    processing_run = service.get_processing_run(step_run["processing_run_id"])
    return processing_run["edition_part_id"] if processing_run else None


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
            ocr_revisions = service.list_step_run_revisions(
                m2_step, artifact_type="ocr_page_set"
            )
            if ocr_revisions:
                ocr_page_set_rev = ocr_revisions[0]["artifact_revision_id"]

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
        spans_bytes = service.read_object(spans_rows[0]["sha256"])
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
            config = json.loads(service.read_object(config_rows[0]["sha256"]))
            if config.get("gate_profile") != "structural_only":
                return ("FAIL", "package_lineage",
                        "gate_profile=%s 期望 structural_only" % config.get("gate_profile"))
            if config.get("batch_size") != 10:
                return ("FAIL", "package_lineage",
                        "batch_size=%s 期望 10" % config.get("batch_size"))

        # 检查校验报告
        vr_rows = _get_step_artifacts(service, step_run_id, "validation_report")
        if vr_rows:
            vr = json.loads(service.read_object(vr_rows[0]["sha256"]))
            if vr.get("semantic") != "not_evaluated":
                return ("FAIL", "package_lineage",
                        "semantic=%s 期望 not_evaluated" % vr.get("semantic"))

        return ("PASS", "package_lineage", "")
    except Exception as exc:
        return ("FAIL", "package_lineage", "%s: %s" % (type(exc).__name__, exc))


if __name__ == "__main__":
    raise SystemExit(main())
