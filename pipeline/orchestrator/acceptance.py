"""§20.1 验收判定（规格 §19.0/§20.1/§22.3）。

用法::

    python -m pipeline.orchestrator.acceptance --fixture <dir> [--asset-root <dir>]
                                               [--keep] [--registry <path>]

退出码：3 仅限 fixture/manifest.yaml 不可读或 PyYAML/jsonschema 不可导入；
        某项准备或判定抛异常 → 该项 FAIL 宿主准备失败；任一 FAIL → 1；无 FAIL 有 BLOCKED → 2。

首纵切 Stage Gate 报告不落盘（G7-RULINGS 第 46 条）：本模块只读 Ledger 事实独立重算，
不调用 ``gate.evaluate_stage_gate`` 做判定（``gate_blocks_incomplete`` 除外，用于确认 Gate 真的阻断）。
"""

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

try:
    import jsonschema
    import yaml
except ImportError:  # 宿主缺依赖：main 返回 3
    yaml = None
    jsonschema = None

import pipeline.orchestrator.gate as gate
from pipeline.contract_registry.catalog import Registry, check_registry, load_registry
from pipeline.contract_registry.ports import DirectLedgerAdapter
from pipeline.knowledge_extraction import CANDIDATE_SCHEMA_VERSION
from pipeline.knowledge_extraction.step import record_category_ruling
from pipeline.knowledge_extraction.submit import run_m4_submit
from pipeline.ledger import ids
from pipeline.orchestrator import EDITION_STAGES
from pipeline.orchestrator.edition_run import (
    advance,
    edition_status,
    run_release,
    run_until,
    start_edition_run,
)
from pipeline.orchestrator.human import rerun_from_checkpoint, resume
from pipeline.orchestrator.stubs import StubModule
from pipeline.review.step import record_decision

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASSET_ROOT = REPO_ROOT / "ocr" / "data_work" / "sanche_pages"
DEFAULT_REGISTRY_PATH = REPO_ROOT / "pipeline" / "contract_registry" / "registry.yaml"

CHECKS = (
    "gate_blocks_incomplete",
    "gate_chain_stub_m1_m6",
    "edition_conjunction",
    "recovery_via_orchestrator",
    "real_chain_mini_ed01",
    "registered_modules_m1_m6",
)

# 20.1 宿主路线（裁决 4）：电子文本 fixture。路线权威 = 宿主 spans.yaml 顶层
# evidence_level（与 m8-span-identity.sh 的 D-W8-16 同源）：宿主不是该路线即 BLOCKED，
# **绝不**回落 OCR 路线的 mini_ed01。
_TEXT_ROUTE_EVIDENCE = "offset_level"

# 宿主自带的 M4 六份提交件（经公开提交入口 ``run_m4_submit`` 交进去，不新造数据）
TEXT_HOST_SUBMISSIONS = (
    "submission_assertion_a.yaml",
    "submission_assertion_b.yaml",
    "submission_pattern_a.yaml",
    "submission_pattern_b.yaml",
    "submission_concept_mention_a.yaml",
    "submission_concept_mention_b.yaml",
)

# M4 运行输入要求的技法画像 canon 目录（与全线用例同源）
DEFAULT_CANON_DIR = REPO_ROOT / "pipeline" / "schemas" / "shared" / "canon"

_PACKAGE_VALIDATOR = None


class _PreconditionMissing(Exception):
    """前置缺失（映射为 BLOCKED）。"""

    def __init__(self, text):
        super().__init__(text)
        self.text = text


def _stage_index(stage):
    return EDITION_STAGES.index(stage)


def _package_validator():
    global _PACKAGE_VALIDATOR
    if _PACKAGE_VALIDATOR is None:
        from referencing import Registry as _SchemaRegistry, Resource
        from referencing.jsonschema import DRAFT202012

        schemas_dir = REPO_ROOT / "openspec" / "schemas"
        schema = json.loads(
            (schemas_dir / "stage_package.schema.json").read_text(encoding="utf-8")
        )
        artifact_ref = json.loads(
            (schemas_dir / "artifact_ref.schema.json").read_text(encoding="utf-8")
        )
        referencing = _SchemaRegistry().with_resource(
            "artifact_ref.schema.json",
            Resource.from_contents(artifact_ref, default_specification=DRAFT202012),
        )
        _PACKAGE_VALIDATOR = jsonschema.Draft202012Validator(
            schema, registry=referencing
        )
    return _PACKAGE_VALIDATOR


def _temp_root(keep):
    return Path(tempfile.mkdtemp(prefix="orch-acceptance-"))


def _cleanup(root, keep):
    if not keep:
        shutil.rmtree(root, True)


def _row_counts(root):
    connection = sqlite3.connect(
        "file:%s?mode=ro" % (Path(root) / "ledger.sqlite"), uri=True
    )
    try:
        return tuple(
            connection.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
            for table in ("artifact_revisions", "step_runs", "audit_log")
        )
    finally:
        connection.close()


def _stub_registry(stubs):
    doc = yaml.safe_load(DEFAULT_REGISTRY_PATH.read_text(encoding="utf-8"))
    doc["modules"] = [stub.descriptor() for stub in stubs]
    return Registry.from_dict(doc, repo_root=REPO_ROOT, allow_stub=True)


def _stub_stages(overrides):
    return [overrides.get(stage, StubModule(stage)) for stage in EDITION_STAGES]


def _read_content(port, revision):
    if not revision or not revision.get("sha256"):
        return None
    try:
        return yaml.safe_load(port.read_object(revision["sha256"]).decode("utf-8"))
    except Exception:  # noqa: BLE001 - 不可读按失败处理
        return None


def _packages(port, row):
    result = json.loads(row["result_json"]) if row.get("result_json") else {}
    packages = []
    for revision_id in result.get("output_artifact_ids", []):
        revision = port.get_revision(revision_id)
        if (
            revision is not None
            and revision.get("schema_id") == "stage_package"
            and revision.get("step_run_id") == row["step_run_id"]
        ):
            packages.append(revision)
    return packages


def _has_upstream(port, row, upstream_stage, upstream_prun):
    """下游冻结输入中是否含该上游 stage 任一 succeeded 运行名下的修订。

    与 Gate 的 ``upstream_lineage`` 同语义：按修订的 ``step_run_id`` 归属判血缘
    （m1 的 manifest 修订是任务级产物，不在 result.output_artifact_ids 里）。
    """
    upstream_ids = {
        upstream["step_run_id"]
        for upstream in port.run_status(upstream_prun)["step_runs"]
        if upstream["stage"] == upstream_stage and upstream["status"] == "succeeded"
    }
    request = json.loads(row["request_json"]) if row.get("request_json") else {}
    return any(
        (port.get_revision(revision_id) or {}).get("step_run_id") in upstream_ids
        for revision_id in request.get("input_artifact_ids", [])
    )


class _NoUpstreamInputs(StubModule):
    """plan 故意不冻结任何上游产出（负例 missing_consumed_input）。"""

    def plan(self, port, *, edition_part_id, processing_run_id, technique_id, upstream):
        planned = super().plan(
            port,
            edition_part_id=edition_part_id,
            processing_run_id=processing_run_id,
            technique_id=technique_id,
            upstream=upstream,
        )
        planned["input_artifact_ids"] = []
        return planned


# --------------------------------------------------------------- 五项桩判定
def _check_gate_blocks_incomplete(fixture_dir, registry, asset_root, keep):
    cases = (
        ("failed_task", "m3", {"m3": StubModule("m3", fail_on_task="t2")}, "m4"),
        ("awaiting_human", "m2", {"m2": StubModule("m2", human_queue=True)}, "m3"),
        (
            "validation_failed",
            "m3",
            {"m3": StubModule("m3", validation_passed=False)},
            "m4",
        ),
        (
            "stage_package_invalid",
            "m3",
            {"m3": StubModule("m3", stage_package_mode="wrong_stage")},
            "m4",
        ),
        ("missing_consumed_input", "m4", {"m4": _NoUpstreamInputs("m4")}, "m5"),
    )
    for label, injected, overrides, downstream in cases:
        root = _temp_root(keep)
        adapter = DirectLedgerAdapter(root)
        try:
            stubs = _stub_stages(overrides)
            stub_registry = _stub_registry(stubs)
            modules = {stub.module_id: stub for stub in stubs}
            handle = start_edition_run(
                adapter, edition_part_id=ids.new_id("artifact_id"), technique_id="qizheng"
            )
            run_until(
                adapter, stub_registry, handle, injected,
                modules=modules, stages=EDITION_STAGES,
            )
            before = _row_counts(root)
            item = advance(
                adapter, stub_registry, handle, modules=modules, stages=EDITION_STAGES
            )
            after = _row_counts(root)
            gate_now = gate.evaluate_stage_gate(adapter, stub_registry, handle, injected)
            if item["action"] not in ("blocked", "waiting"):
                return ("FAIL", "gate_blocks_incomplete", "%s: action=%s" % (label, item["action"]))
            if gate_now["gate"] == "passed":
                return ("FAIL", "gate_blocks_incomplete", "%s: Gate 放行了未完成任务" % label)
            if before != after:
                return ("FAIL", "gate_blocks_incomplete", "%s: advance 非零写入" % label)
            step_runs = adapter.run_status(handle["processing_run_id"])["step_runs"]
            if any(step["stage"] == downstream for step in step_runs):
                return ("FAIL", "gate_blocks_incomplete", "%s: 下游 %s 已有 StepRun" % (label, downstream))
        finally:
            adapter.close()
            _cleanup(root, keep)
    return ("PASS", "gate_blocks_incomplete", "")


def _check_gate_chain_stub_m1_m6(fixture_dir, registry, asset_root, keep):
    root = _temp_root(keep)
    adapter = DirectLedgerAdapter(root)
    try:
        stubs = [StubModule(stage) for stage in EDITION_STAGES]
        stub_registry = _stub_registry(stubs)
        modules = {stub.module_id: stub for stub in stubs}
        handle = start_edition_run(
            adapter, edition_part_id=ids.new_id("artifact_id"), technique_id="qizheng"
        )
        results = run_until(
            adapter, stub_registry, handle, "m6", modules=modules, stages=EDITION_STAGES
        )
        if results[-1]["action"] != "complete":
            return ("FAIL", "gate_chain_stub_m1_m6", "末次 action=%s" % results[-1]["action"])
        for item in results:
            if item["action"] != "executed":
                continue
            index = _stage_index(item["stage"])
            if index == 0:
                continue
            previous = EDITION_STAGES[index - 1]
            report = item["gate_reports"].get(previous)
            if not report or report["gate"] != "passed" or report["stage"] != previous:
                return ("FAIL", "gate_chain_stub_m1_m6", "%s 缺上游 %s 的 passed Gate" % (item["stage"], previous))
        step_runs = adapter.run_status(handle["processing_run_id"])["step_runs"]
        for stage in EDITION_STAGES:
            index = _stage_index(stage)
            if index == 0:
                continue
            previous = EDITION_STAGES[index - 1]
            upstream_packages = set()
            for row in step_runs:
                if row["stage"] == previous:
                    for package in _packages(adapter, row):
                        upstream_packages.add(package["artifact_revision_id"])
            for row in step_runs:
                if row["stage"] != stage or not row.get("request_json"):
                    continue
                request = json.loads(row["request_json"])
                if not upstream_packages <= set(request["input_artifact_ids"]):
                    return ("FAIL", "gate_chain_stub_m1_m6", "%s 未冻结 %s 的 StagePackage" % (stage, previous))
        for row in step_runs:
            if not row.get("result_json"):
                continue
            result = json.loads(row["result_json"])
            for revision_id in result.get("validation_report_ids", []):
                content = _read_content(adapter, adapter.get_revision(revision_id))
                if isinstance(content, dict) and content.get("kind") == "stage_gate":
                    return ("FAIL", "gate_chain_stub_m1_m6", "存在落盘的 Gate 证据修订")
        return ("PASS", "gate_chain_stub_m1_m6", "")
    finally:
        adapter.close()
        _cleanup(root, keep)


def _check_edition_conjunction(fixture_dir, registry, asset_root, keep):
    root = _temp_root(keep)
    adapter = DirectLedgerAdapter(root)
    try:
        stubs = [StubModule(stage) for stage in EDITION_STAGES]
        stub_registry = _stub_registry(stubs)
        modules_a = {stub.module_id: stub for stub in stubs}
        modules_b = dict(modules_a)
        modules_b["stub.m3"] = StubModule("m3", fail_on_task="t2")

        handle_a = start_edition_run(
            adapter, edition_part_id=ids.new_id("artifact_id"), technique_id="qizheng"
        )
        run_until(
            adapter, stub_registry, handle_a, "m6", modules=modules_a, stages=EDITION_STAGES
        )
        handle_b = start_edition_run(
            adapter, edition_part_id=ids.new_id("artifact_id"), technique_id="qizheng"
        )
        run_until(
            adapter, stub_registry, handle_b, "m3", modules=modules_b, stages=EDITION_STAGES
        )

        status = edition_status(adapter, stub_registry, [handle_a, handle_b])
        if status["complete"]:
            return ("FAIL", "edition_conjunction", "B 停在 m3 失败却判 complete")
        if status["parts"][handle_a["edition_part_id"]] != "complete":
            return ("FAIL", "edition_conjunction", "A 未判 complete")
        if status["parts"][handle_b["edition_part_id"]] != "incomplete":
            return ("FAIL", "edition_conjunction", "B 未判 incomplete")

        result = rerun_from_checkpoint(
            adapter, stub_registry, handle_b, "m3", modules=modules_a
        )
        if result["status"] != "succeeded":
            return ("FAIL", "edition_conjunction", "B 重跑 m3 未成功")
        run_until(
            adapter, stub_registry, handle_b, "m6", modules=modules_a, stages=EDITION_STAGES
        )
        status_after = edition_status(adapter, stub_registry, [handle_a, handle_b])
        if not status_after["complete"]:
            return ("FAIL", "edition_conjunction", "两 Part 均完成后仍判不 complete")
        return ("PASS", "edition_conjunction", "")
    finally:
        adapter.close()
        _cleanup(root, keep)


def _check_recovery_via_orchestrator(fixture_dir, registry, asset_root, keep):
    root = _temp_root(keep)
    adapter = DirectLedgerAdapter(root)
    try:
        failing = StubModule("m4", fail_on_task="t2", supports_recovery=True)
        stubs = [failing if stage == "m4" else StubModule(stage) for stage in EDITION_STAGES]
        stub_registry = _stub_registry(stubs)
        modules = {stub.module_id: stub for stub in stubs}
        handle = start_edition_run(
            adapter, edition_part_id=ids.new_id("artifact_id"), technique_id="qizheng"
        )
        run_until(
            adapter, stub_registry, handle, "m4", modules=modules, stages=EDITION_STAGES
        )
        old = [
            row for row in adapter.run_status(handle["processing_run_id"])["step_runs"]
            if row["stage"] == "m4"
        ][-1]["step_run_id"]
        if adapter.get_step_run(old)["status"] != "failed":
            return ("FAIL", "recovery_via_orchestrator", "m4 旧运行非 failed")
        failure_event = [
            event for event in adapter.list_step_run_events(old)
            if event["event_type"] == "failure"
        ][-1]
        failure_ids = json.loads(failure_event["payload_json"])["failure_revision_ids"]
        if not failure_ids or adapter.get_revision(failure_ids[0])["status"] != "sealed":
            return ("FAIL", "recovery_via_orchestrator", "失败修订未封存")

        failing.fail_on_task = None
        result = rerun_from_checkpoint(
            adapter, stub_registry, handle, "m4", modules=modules
        )
        if result["status"] != "succeeded":
            return ("FAIL", "recovery_via_orchestrator", "重跑未成功")
        new = [
            row["step_run_id"]
            for row in adapter.run_status(handle["processing_run_id"])["step_runs"]
            if row["stage"] == "m4" and row["step_run_id"] != old
        ]
        if len(new) != 1 or adapter.get_step_run(new[0])["supersedes_step_run_id"] != old:
            return ("FAIL", "recovery_via_orchestrator", "新运行未 supersede 旧运行")
        if [task for _srun, task in failing.executed_tasks].count("t1") != 1:
            return ("FAIL", "recovery_via_orchestrator", "t1 被重复执行")
        results = run_until(
            adapter, stub_registry, handle, "m6", modules=modules, stages=EDITION_STAGES
        )
        if results[-1]["action"] != "complete":
            return ("FAIL", "recovery_via_orchestrator", "重跑后未跑至 complete")
        return ("PASS", "recovery_via_orchestrator", "")
    finally:
        adapter.close()
        _cleanup(root, keep)


# ------------------------------------------------------------ 真实链判定
def _text_host_gap(fixture_dir):
    """20.1 宿主（裁决 4：电子文本路线）齐备性；缺什么报什么，**绝不**回落 OCR 宿主。

    返回值形如 ``前置缺失: <§19 差距行名>；<为什么>``（run_all.sh 的 BLOCKED 解析口径）。
    """
    fixture_dir = Path(fixture_dir)
    for name in ("source_info.yaml", "spans.yaml"):
        if not (fixture_dir / name).is_file():
            return (
                "前置缺失: M1 Source Intake；裁决 4 指定的电子文本宿主缺 %s：%s"
                % (name, fixture_dir)
            )
    try:
        document = yaml.safe_load((fixture_dir / "spans.yaml").read_bytes())
    except Exception:  # noqa: BLE001 - 宿主不可读按缺失处理
        return "前置缺失: M1 Source Intake；宿主 spans.yaml 不可解析：%s" % fixture_dir
    if not isinstance(document, dict) or document.get("evidence_level") != _TEXT_ROUTE_EVIDENCE:
        return (
            "前置缺失: M1 Source Intake；宿主非电子文本路线"
            "（spans.yaml evidence_level 不是 %s）：%s"
            % (_TEXT_ROUTE_EVIDENCE, fixture_dir)
        )
    if not (fixture_dir / "expected" / "m1_source_expected.yaml").is_file():
        return (
            "前置缺失: M1 Source Intake；宿主缺独立期望 expected/m1_source_expected.yaml"
            "（缺期望即不可判定）"
        )
    missing = [
        name
        for name in TEXT_HOST_SUBMISSIONS
        if not (fixture_dir / "m4" / name).is_file()
    ]
    if missing:
        return "前置缺失: M4 Knowledge Extraction；宿主 M4 提交件缺失：%s" % "、".join(
            missing
        )
    return None


def _read_step_run_doc(service, step_run_id, artifact_type):
    """读该 StepRun 该类型的唯一封存文档；不是恰一个或不可读返回 ``None``。"""
    rows = service.list_step_run_revisions(step_run_id, artifact_type=artifact_type)
    if len(rows) != 1:
        return None
    revision = service.get_revision(rows[0]["artifact_revision_id"])
    if revision is None:
        return None
    return json.loads(service.read_object(revision["sha256"]).decode("utf-8"))


def _drive_text_chain(adapter, registry, handle, host):
    """按公开入口驱动 M1→M6 全线；返回 ``None`` 表示全链成立，否则返回失败说明。

    人工环节只走公开入口：M4 的六份宿主提交件经 ``run_m4_submit``、分歧经
    ``record_category_ruling``；M6 的签发经审核台 ``record_decision``；两处恢复统一经
    ``human.resume``（legacy 绑定走描述符 ``resume_entry``）。本函数不写金标、不直接改
    Ledger 造人工结果，除 m4/m6 外没有任何手工推进。
    """
    service = adapter.unwrap()
    edition_part_id = handle["edition_part_id"]
    awaitings = []

    def executed(results):
        return [item for item in results if item["action"] == "executed"]

    results = run_until(adapter, registry, handle, "m3")
    stages = [item["stage"] for item in executed(results)]
    if stages != ["m1", "m2", "m3"]:
        return "EditionRun 段未按 m1→m2→m3 推进: %r" % (stages,)
    for item in executed(results):
        if item["step_result"]["status"] != "succeeded":
            return "%s 未 succeeded: %s" % (item["stage"], item["step_result"]["status"])

    # M4：六份宿主提交件只经公开提交入口登记（不直接写 Ledger）
    for name in TEXT_HOST_SUBMISSIONS:
        summary = run_m4_submit(
            service,
            edition_part_id,
            (host / "m4" / name).read_bytes(),
            producer_module="orchestrator.acceptance",
            producer_version="1.0.0",
        )
        if summary["status"] != "succeeded":
            return "M4 提交 %s 未 succeeded" % name

    item = advance(adapter, registry, handle)
    if (item["action"], item["stage"]) != ("executed", "m4"):
        return "M4 未执行: action=%s stage=%s" % (item["action"], item["stage"])
    if (item.get("step_result") or {}).get("status") != "awaiting_human":
        return "M4 未停成 awaiting_human"
    awaitings.append("m4")
    m4_step_run_id = item["step_run_id"]
    m4_token = item["step_result"]["resume_token"]
    dispute_doc = _read_step_run_doc(service, m4_step_run_id, "dispute_queue")
    dispute_ids = [
        row["dispute_id"] for row in (dispute_doc or {}).get("disputes") or []
    ]
    if not dispute_ids:
        return "M4 停 awaiting_human 时待裁决分歧为空"
    for dispute_id in dispute_ids:
        record_category_ruling(
            service,
            m4_step_run_id,
            m4_token,
            {
                "schema_version": CANDIDATE_SCHEMA_VERSION,
                "dispute_id": dispute_id,
                "choice": "a",
                "rationale": "20.1 验收：按 A 路归属裁决",
                "actor_ref": "orchestrator.acceptance",
            },
        )
    resumed = resume(adapter, registry, handle, m4_step_run_id, m4_token)
    if resumed["status"] != "succeeded":
        return "M4 恢复未 succeeded: %s" % resumed["status"]

    item = advance(adapter, registry, handle)
    if (item["action"], item["stage"]) != ("executed", "m5"):
        return "M5 未自动执行: action=%s stage=%s" % (item["action"], item["stage"])
    if item["step_result"]["status"] != "succeeded":
        return "M5 未 succeeded: %s" % item["step_result"]["status"]

    item = advance(adapter, registry, handle)
    if (item["action"], item["stage"]) != ("executed", "m6"):
        return "M6 未执行: action=%s stage=%s" % (item["action"], item["stage"])
    if (item.get("step_result") or {}).get("status") != "awaiting_human":
        return "M6 未停成 awaiting_human"
    awaitings.append("m6")
    m6_step_run_id = item["step_run_id"]
    m6_token = item["step_result"]["resume_token"]
    queue_doc = _read_step_run_doc(service, m6_step_run_id, "review_queue") or []
    queue_item_ids = [row["queue_item_id"] for row in queue_doc]
    if not queue_item_ids:
        return "M6 停 awaiting_human 时审核队列为空"
    for queue_item_id in queue_item_ids:
        record_decision(
            service,
            m6_step_run_id,
            m6_token,
            queue_item_id=queue_item_id,
            verdict="accept",
            rationale="20.1 验收：签发",
        )
    resumed = resume(adapter, registry, handle, m6_step_run_id, m6_token)
    if resumed["status"] != "succeeded":
        return "M6 恢复未 succeeded: %s" % resumed["status"]

    item = advance(adapter, registry, handle)
    if item["action"] != "complete":
        return "全线未收口: action=%s" % item["action"]

    if awaitings != ["m4", "m6"]:
        return "人工暂停顺序不是 m4→m6: %r" % (awaitings,)
    # Ledger 层面复核：全链只发生过两次 ``await_human`` 事件，且恰在 m4/m6
    stopped = []
    for row in adapter.run_status(handle["processing_run_id"])["step_runs"]:
        events = [
            event.get("event_type")
            for event in adapter.list_step_run_events(row["step_run_id"])
        ]
        stopped.extend([row["stage"]] * events.count("await_human"))
    if stopped != ["m4", "m6"]:
        return "Ledger 中 await_human 事件不是恰 m4、m6 各一次: %r" % (stopped,)
    return None


def _supersedes_reaches(adapter, start, target):
    """``start`` 是否经 ``supersedes_step_run_id`` 链（含自身）指向 ``target``。"""
    seen = set()
    current = start
    while current is not None and current not in seen:
        if current == target:
            return True
        seen.add(current)
        row = adapter.get_step_run(current)
        current = row.get("supersedes_step_run_id") if row else None
    return False


def _check_real_chain(fixture_dir, registry, asset_root, keep):
    """20.1：电子文本宿主上由调度器走完 M1→M6 全线（裁决 4）。

    判据（全部要成立）：① m1..m6 每 stage 恰 1 个阶段包、且来自生产模块（binding 非
    ``imported``）；② 只在 m4、m6 停 ``awaiting_human``，除此之外无任何手工推进；
    ③ 人工环节只走公开入口；④ 恢复经 ``human.resume`` → 描述符 ``resume_entry`` 后自动
    续跑到 m6 succeeded。宿主缺失即 BLOCKED，**绝不**回落 OCR 宿主；本函数只读 Ledger
    事实独立重算，不调用 ``gate.evaluate_stage_gate`` 做判定（G7-RULINGS 第 46 条）。
    """
    gap = _text_host_gap(fixture_dir)
    if gap is not None:
        raise _PreconditionMissing(gap)

    host = Path(fixture_dir)
    source_info = yaml.safe_load((host / "source_info.yaml").read_text(encoding="utf-8"))
    technique_id = source_info["technique_id"]

    root = _temp_root(keep)
    adapter = DirectLedgerAdapter(root)
    try:
        handle = start_edition_run(
            adapter,
            edition_part_id=source_info["edition_part"]["artifact_id"],
            technique_id=technique_id,
            run_inputs={
                "route": "text",
                "source_dir": str(host),
                "source_info": source_info,
                "technique_profile": {
                    "technique_id": technique_id,
                    "canon_dir": str(DEFAULT_CANON_DIR),
                },
            },
        )
        failure = _drive_text_chain(adapter, registry, handle, host)
        if failure is None:
            failure = _recompute_real_chain(adapter, registry, handle, host)
        if failure is not None:
            return ("FAIL", "real_chain_mini_ed01", failure)
    finally:
        adapter.close()
        _cleanup(root, keep)
    return (
        "PASS",
        "real_chain_mini_ed01",
        "宿主 qianyuan_ed01_text：调度器 M1→M6 全线（人工节点只 m4/m6，且只经公开入口）",
    )


def _recompute_real_chain(adapter, registry, handle, fixture_dir):
    """从 Ledger 事实独立重算 M1→M6 全线（不调用 Gate、不信任 step_result）。

    逐 stage 重算：恰 1 个承载 StagePackage 的运行、其余同阶段运行须经 ``supersedes``
    链回溯到该承载者；包须 sealed、过 Schema、``validation.passed=true``、``failures``
    为空；描述符 ``consumes`` 声明的每个上游 stage 都要出现在冻结输入里；最后用宿主
    独立期望 ``expected/m1_source_expected.yaml``（第 95 条）核对 M1 的 raw_text 修订。
    """
    edition_prun = handle["processing_run_id"]
    all_rows = adapter.run_status(edition_prun)["step_runs"]
    contents = {}
    for stage in EDITION_STAGES:
        descriptor = registry.module_for(stage)
        if descriptor is None:
            return "阶段 %s 未登记 Module" % stage
        if descriptor.get("binding") == "imported":
            return "阶段 %s 来自 imported 绑定（非生产模块）" % stage
        rows = [row for row in all_rows if row["stage"] == stage]
        overfull = [row for row in rows if len(_packages(adapter, row)) > 1]
        if overfull:
            return "%s 存在承载多个 StagePackage 的运行: %s" % (
                stage,
                [row["step_run_id"] for row in overfull],
            )
        carriers = [row for row in rows if len(_packages(adapter, row)) == 1]
        if len(carriers) != 1:
            return "%s 承载 StagePackage 的运行不是恰 1 个（%d 个）" % (
                stage,
                len(carriers),
            )
        carrier = carriers[0]
        if carrier["status"] != "succeeded":
            return "%s 的承载运行非 succeeded: %s" % (stage, carrier["status"])
        package = _packages(adapter, carrier)[0]
        if package.get("status") != "sealed":
            return "%s 的 StagePackage 未 sealed" % stage
        content = _read_content(adapter, package)
        if not isinstance(content, dict):
            return "%s 的 StagePackage 内容不可读" % stage
        try:
            _package_validator().validate(content)
        except jsonschema.ValidationError as exc:
            return "%s 的 StagePackage 过 Schema 失败: %s" % (stage, exc.message)
        if content.get("stage") != stage:
            return "%s 的 StagePackage stage 写错" % stage
        if content.get("validation", {}).get("passed") is not True:
            return "%s 的 StagePackage validation.passed 非 true" % stage
        if content.get("failures") != []:
            return "%s 的 StagePackage failures 非空" % stage
        for row in rows:
            if row["step_run_id"] == carrier["step_run_id"]:
                continue
            if row["status"] != "succeeded":
                return "%s 的非承载运行未 succeeded: %s" % (stage, row["status"])
            # 承载者的 supersedes 链必须向下覆盖该运行（即它确被接替），否则它是游离的
            # 同阶段运行，不得计入有效运行。
            if not _supersedes_reaches(
                adapter, carrier["step_run_id"], row["step_run_id"]
            ):
                return "%s 的非承载运行未被承载者接替: %s" % (stage, row["step_run_id"])
        contents[stage] = content

    # 血缘：描述符 consumes 声明的每个上游 stage 都必须出现在冻结输入里
    for stage in EDITION_STAGES:
        descriptor = registry.module_for(stage)
        carrier = [
            row
            for row in all_rows
            if row["stage"] == stage and len(_packages(adapter, row)) == 1
        ][0]
        upstreams = sorted(
            {
                item.get("from_stage")
                for item in (descriptor.get("consumes") or [])
                if item.get("from_stage")
            }
        )
        for upstream in upstreams:
            if not _has_upstream(adapter, carrier, upstream, edition_prun):
                return "%s 冻结输入缺 %s 产出" % (stage, upstream)

    # 金标：M1 的 raw_text 修订 sha256 必须等于宿主独立期望
    expected = yaml.safe_load(
        (Path(fixture_dir) / "expected" / "m1_source_expected.yaml").read_text(
            encoding="utf-8"
        )
    )
    raw_ids = list(
        (contents["m1"].get("payload") or {}).get("raw_text_revision_ids") or []
    )
    if len(raw_ids) != 1:
        return "M1 StagePackage 的 raw_text 修订不是恰 1 个"
    revision = adapter.get_revision(raw_ids[0])
    if revision is None or revision.get("sha256") != expected.get("sha256"):
        return "M1 raw_text 修订 sha256 与宿主独立期望不一致"
    return None


# ------------------------------------------------------- registered_modules
def _check_registered_modules(fixture_dir, registry, asset_root, keep):
    problems = check_registry(registry)
    if any(problem["code"] == "stub_in_production" for problem in problems):
        return ("FAIL", "registered_modules_m1_m6", "登记表含桩（stub_in_production），不得计入")
    # 按真实登记情况判：`imported` 绑定不是生产模块（裁决 2/4），与未登记一并计入缺口。
    gaps = [
        stage
        for stage in EDITION_STAGES
        if registry.module_for(stage) is None
        or registry.module_for(stage).get("binding") == "imported"
    ]
    if gaps:
        return (
            "BLOCKED",
            "registered_modules_m1_m6",
            "前置缺失: %s；Local Orchestrator M1–M6 链路已接线，%s 未登记生产 Module"
            "（未登记或 imported 绑定）"
            % (registry.stage_rows[gaps[0]], "/".join(gaps)),
        )
    registered = [
        (stage, registry.module_for(stage)["binding"]) for stage in EDITION_STAGES
    ]
    return (
        "PASS",
        "registered_modules_m1_m6",
        "M1–M6 已登记 %d 个生产 Stage（%s）"
        % (len(registered), ", ".join("%s:%s" % item for item in registered)),
    )


_CHECKERS = (
    ("gate_blocks_incomplete", _check_gate_blocks_incomplete),
    ("gate_chain_stub_m1_m6", _check_gate_chain_stub_m1_m6),
    ("edition_conjunction", _check_edition_conjunction),
    ("recovery_via_orchestrator", _check_recovery_via_orchestrator),
    ("real_chain_mini_ed01", _check_real_chain),
    ("registered_modules_m1_m6", _check_registered_modules),
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pipeline.orchestrator.acceptance",
        description="§20.1 验收判定（规格 §19.0/§20.1）",
    )
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--asset-root", default=None)
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--registry", default=None)
    args = parser.parse_args(argv)

    if yaml is None or jsonschema is None:
        print("FAIL orchestrator_acceptance 宿主准备失败: ImportError: PyYAML/jsonschema 不可导入")
        print("SUMMARY pass=0 fail=1 blocked=0")
        return 3
    fixture_dir = Path(args.fixture)
    if not (fixture_dir / "manifest.yaml").is_file():
        print(
            "FAIL orchestrator_acceptance 宿主准备失败: FileNotFoundError: %s"
            % (fixture_dir / "manifest.yaml")
        )
        print("SUMMARY pass=0 fail=1 blocked=0")
        return 3

    registry = load_registry(args.registry) if args.registry else load_registry()
    asset_root = (
        args.asset_root
        or os.environ.get("FIXTURE_ASSET_ROOT")
        or str(DEFAULT_ASSET_ROOT)
    )

    results = []
    for name, checker in _CHECKERS:
        try:
            results.append(checker(fixture_dir, registry, asset_root, args.keep))
        except _PreconditionMissing as exc:
            results.append(("BLOCKED", name, exc.text))
        except Exception as exc:  # noqa: BLE001 - 记为 FAIL 而非中断
            results.append(
                ("FAIL", name, "宿主准备失败: %s: %s" % (type(exc).__name__, exc))
            )

    pass_count = fail_count = blocked_count = 0
    for status, name, detail in results:
        if status == "PASS":
            pass_count += 1
            print("PASS %s%s" % (name, (" " + detail) if detail else ""))
        elif status == "FAIL":
            fail_count += 1
            print("FAIL %s %s" % (name, detail))
        else:
            blocked_count += 1
            print("BLOCKED %s %s" % (name, detail))
    print(
        "SUMMARY pass=%d fail=%d blocked=%d" % (pass_count, fail_count, blocked_count)
    )
    if fail_count > 0:
        return 1
    if blocked_count > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
