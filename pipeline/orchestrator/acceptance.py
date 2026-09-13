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
from pipeline.ledger import fixture_ingest, ids
from pipeline.ledger.service import LedgerService

try:
    from pipeline.dataset_compiler.shim import m1_shim_source_assets

    SourceAssetMissing = m1_shim_source_assets.SourceAssetMissing
except ImportError:  # 宿主缺依赖：main 返回 3
    SourceAssetMissing = None
    m1_shim_source_assets = None

from pipeline.orchestrator import EDITION_STAGES, FIRST_SLICE_EDITION_STAGES
from pipeline.orchestrator.edition_run import (
    advance,
    adopt_edition_run,
    edition_status,
    run_release,
    run_until,
    start_edition_run,
)
from pipeline.orchestrator.human import rerun_from_checkpoint
from pipeline.orchestrator.stubs import StubModule

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


def _render_stages(stages):
    """把连续阶段折叠为区间：``["m1","m2","m3","m5"]`` → ``"m1–m3、m5"``。"""
    groups = []
    index = 0
    while index < len(stages):
        end = index
        while (
            end + 1 < len(stages)
            and _stage_index(stages[end + 1]) == _stage_index(stages[end]) + 1
        ):
            end += 1
        if end > index:
            groups.append("%s–%s" % (stages[index], stages[end]))
        else:
            groups.append(stages[index])
        index = end + 1
    return "、".join(groups)


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
def _check_real_chain(fixture_dir, registry, asset_root, keep):
    if m1_shim_source_assets is None or SourceAssetMissing is None:
        raise RuntimeError("薄 M1 页图登记依赖不可导入")

    root = _temp_root(keep)
    service = LedgerService(root)
    try:
        summary = fixture_ingest.ingest(fixture_dir, service, stages=("m1", "m2"))
        try:
            m1_shim_source_assets.register_source_assets(
                service, summary["edition_part_id"], str(asset_root)
            )
        except SourceAssetMissing:
            raise _PreconditionMissing("前置缺失: M1 Source Intake；派生页图缺失")
        except FileNotFoundError:
            raise _PreconditionMissing("前置缺失: M1 Source Intake；派生页图缺失")
    finally:
        service.close()

    adapter = DirectLedgerAdapter(root)
    try:
        handle = adopt_edition_run(
            adapter,
            processing_run_id=summary["processing_run_id"],
            edition_part_id=summary["edition_part_id"],
            technique_id=summary["technique_id"],
        )
        results = run_until(
            adapter, registry, handle, "m5", stages=FIRST_SLICE_EDITION_STAGES
        )
        executed = [item for item in results if item["action"] == "executed"]
        if executed and [item["stage"] for item in executed] == ["m3", "m5"]:
            for item in executed:
                if item["step_result"]["status"] != "succeeded":
                    return ("FAIL", "real_chain_mini_ed01", "%s 未 succeeded" % item["stage"])
        else:
            return ("FAIL", "real_chain_mini_ed01", "EditionRun 段未按 m3→m5 推进")
        m3_item = executed[0]
        for stage in ("m1", "m2"):
            report = m3_item["gate_reports"].get(stage)
            if not report or report["gate"] != "passed":
                return ("FAIL", "real_chain_mini_ed01", "%s Gate 未 passed" % stage)

        release = run_release(
            adapter,
            registry,
            edition_part_id=summary["edition_part_id"],
            technique_id=summary["technique_id"],
        )
        if (
            release["action"] != "executed"
            or release["stage"] != "m8"
            or release["step_result"]["status"] != "succeeded"
            or not str(release["processing_run_id"]).startswith("prun_")
        ):
            return ("FAIL", "real_chain_mini_ed01", "release 段未成功执行 m8")

        failure = _recompute_real_chain(adapter, summary, release, fixture_dir)
        if failure is not None:
            return ("FAIL", "real_chain_mini_ed01", failure)
    finally:
        adapter.close()
        _cleanup(root, keep)

    # 准备 B（负例）：只灌 m1
    root_b = _temp_root(keep)
    service_b = LedgerService(root_b)
    try:
        summary_b = fixture_ingest.ingest(fixture_dir, service_b, stages=("m1",))
    finally:
        service_b.close()
    adapter_b = DirectLedgerAdapter(root_b)
    try:
        handle_b = adopt_edition_run(
            adapter_b,
            processing_run_id=summary_b["processing_run_id"],
            edition_part_id=summary_b["edition_part_id"],
            technique_id=summary_b["technique_id"],
        )
        item = advance(adapter_b, registry, handle_b, stages=FIRST_SLICE_EDITION_STAGES)
        if item["action"] != "refused" or item["stage"] != "m2" or "imported" not in (item["reason"] or ""):
            return ("FAIL", "real_chain_mini_ed01", "准备 B 未在 m2 refused（imported）")
        step_runs = adapter_b.run_status(summary_b["processing_run_id"])["step_runs"]
        if any(row["stage"] == "m3" for row in step_runs):
            return ("FAIL", "real_chain_mini_ed01", "准备 B 出现 m3 StepRun")
    finally:
        adapter_b.close()
        _cleanup(root_b, keep)
    return ("PASS", "real_chain_mini_ed01", "")


def _recompute_real_chain(adapter, summary, release, fixture_dir):
    """从 Ledger 事实独立重算首纵切链（不调用 Gate、不信任 step_result）。"""
    edition_prun = summary["processing_run_id"]
    release_prun = release["processing_run_id"]

    def runs(prun, stage):
        return [
            row for row in adapter.run_status(prun)["step_runs"] if row["stage"] == stage
        ]

    for stage in ("m2", "m3", "m5"):
        rows = runs(edition_prun, stage)
        if len(rows) != 1 or rows[0]["status"] != "succeeded":
            return "%s 的有效运行不是恰 1 个 succeeded" % stage

    m1_rows = runs(edition_prun, "m1")
    if len(m1_rows) != 2 or any(row["status"] != "succeeded" for row in m1_rows):
        return "m1 有效运行不是 2 个 succeeded"
    if len([row for row in m1_rows if _packages(adapter, row)]) != 1:
        return "m1 承载 StagePackage 的运行不是恰 1 个"

    m3_row = runs(edition_prun, "m3")[0]
    m5_row = runs(edition_prun, "m5")[0]
    for upstream in ("m1", "m2"):
        if not _has_upstream(adapter, m3_row, upstream, edition_prun):
            return "m3 冻结输入缺 %s 产出" % upstream
    if not _has_upstream(adapter, m5_row, "m3", edition_prun):
        return "m5 冻结输入缺 m3 产出"

    m8_rows = runs(release_prun, "m8")
    if len(m8_rows) != 1 or m8_rows[0]["status"] != "succeeded":
        return "m8 的有效运行不是恰 1 个 succeeded"
    m8_row = m8_rows[0]
    for upstream in ("m1", "m2", "m3"):
        if not _has_upstream(adapter, m8_row, upstream, edition_prun):
            return "m8 冻结输入缺 %s 产出" % upstream

    contents = {}
    for stage, row in (("m3", m3_row), ("m5", m5_row), ("m8", m8_row)):
        packages = _packages(adapter, row)
        if len(packages) != 1:
            return "%s 的 StagePackage 不是恰 1 个" % stage
        content = _read_content(adapter, packages[0])
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
        contents[stage] = content

    expected = yaml.safe_load(
        (Path(fixture_dir) / "expected" / "m3.stage_package.yaml").read_text(
            encoding="utf-8"
        )
    )
    if (
        contents["m3"]["manifest"]["content_sha256"]
        != expected["manifest"]["content_sha256"]
    ):
        return "m3 StagePackage content_sha256 与 fixture 金标不一致"
    if contents["m8"]["payload"].get("consumption_level") != "INTERNAL_DEMO":
        return "m8 StagePackage payload.consumption_level 非 INTERNAL_DEMO"
    return None


# ------------------------------------------------------- registered_modules
def _check_registered_modules(fixture_dir, registry, asset_root, keep):
    problems = check_registry(registry)
    if any(problem["code"] == "stub_in_production" for problem in problems):
        return ("FAIL", "registered_modules_m1_m6", "登记表含桩（stub_in_production），不得计入")
    for stage in EDITION_STAGES:
        if registry.module_for(stage) is None:
            unregistered = [
                item for item in EDITION_STAGES if registry.module_for(item) is None
            ]
            return (
                "BLOCKED",
                "registered_modules_m1_m6",
                "前置缺失: %s；Local Orchestrator 首切片已串联 %s Gate，%s 未登记生产 Module"
                % (
                    registry.stage_rows[stage],
                    _render_stages(FIRST_SLICE_EDITION_STAGES),
                    "/".join(unregistered),
                ),
            )
    registered = [
        (stage, registry.module_for(stage)["binding"]) for stage in EDITION_STAGES
    ]
    return (
        "PASS",
        "registered_modules_m1_m6",
        "首纵切链已登记 %d 个 Stage（%s）"
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
