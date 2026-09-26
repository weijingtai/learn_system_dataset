"""独立 Stage Gate：八项契约级检查（规格 §6.1 :149、§20.1 :937）。

只读：只调用 LedgerPort 读方法（``get_revision``/``get_step_run``/
``list_step_run_events``/``latest_checkpoint``/``run_status``/``read_object``），不写入；
不 import ``runner``/``module``/``stubs``/``edition_run``，也不 import 任何加工 Module。
"""

import json
from pathlib import Path

import jsonschema
import yaml
from referencing import Registry as _SchemaRegistry, Resource
from referencing.jsonschema import DRAFT202012

# 八项检查（名称与顺序固定）
GATE_CHECKS = (
    "tasks_present",
    "all_tasks_succeeded",
    "stage_package_valid",
    "output_contract",
    "validation_passed",
    "failures_zero",
    "no_pending_work",
    "upstream_lineage",
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMAS_DIR = _REPO_ROOT / "openspec" / "schemas"
_STAGE_PACKAGE_VALIDATOR = None


def _validator():
    """惰性加载 StagePackage 校验器（注册 ``artifact_ref.schema.json``）。"""
    global _STAGE_PACKAGE_VALIDATOR
    if _STAGE_PACKAGE_VALIDATOR is None:
        schema = json.loads(
            (_SCHEMAS_DIR / "stage_package.schema.json").read_text(encoding="utf-8")
        )
        artifact_ref = json.loads(
            (_SCHEMAS_DIR / "artifact_ref.schema.json").read_text(encoding="utf-8")
        )
        referring = _SchemaRegistry().with_resource(
            "artifact_ref.schema.json",
            Resource.from_contents(artifact_ref, default_specification=DRAFT202012),
        )
        _STAGE_PACKAGE_VALIDATOR = jsonschema.Draft202012Validator(
            schema, registry=referring
        )
    return _STAGE_PACKAGE_VALIDATOR


def _parse_json(value):
    if value is None or isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return None
    return None


def _with_parsed(row):
    parsed = dict(row)
    parsed["request"] = _parse_json(row.get("request_json"))
    parsed["result"] = _parse_json(row.get("result_json"))
    return parsed


def _step_run_id(row):
    return row.get("step_run_id")


def _stage_runs(port, handle, stage):
    rows = [
        row
        for row in port.run_status(handle["processing_run_id"])["step_runs"]
        if row.get("stage") == stage
    ]
    rows.sort(key=lambda row: row.get("created_at") or "")
    return rows


def _chain_reaches(port, start, target):
    """``start`` 是否经 ``supersedes_step_run_id`` 链（含自身）指向 ``target``。"""
    seen = set()
    current = start
    while current is not None and current not in seen:
        if current == target:
            return True
        seen.add(current)
        row = port.get_step_run(current)
        current = row.get("supersedes_step_run_id") if row else None
    return False


def _package_revisions(port, row):
    """返回该 StepRun 的 result 中自述的 stage_package 修订行列表。"""
    result = _parse_json(row.get("result_json")) or {}
    packages = []
    for revision_id in result.get("output_artifact_ids", []) or []:
        revision = port.get_revision(revision_id)
        if (
            revision is not None
            and revision.get("schema_id") == "stage_package"
            and revision.get("step_run_id") == _step_run_id(row)
        ):
            packages.append(revision)
    return packages


def _read_package_content(port, package_revision):
    """读取 StagePackage 内容；非映射或不可读返回 ``None``。

    StagePackage 修订字节由产出方决定：``run_m3``/``run_m5``/``run_m8`` 写 JSON，
    ``fixture_ingest`` 写 YAML 金标信封（``expected/mN.stage_package.yaml``）。用
    ``yaml.safe_load`` 容错读取（JSON 是 YAML 子集），仅接受映射（裁定 57）。
    """
    sha256 = package_revision.get("sha256")
    if not sha256:
        return None
    try:
        content = yaml.safe_load(port.read_object(sha256).decode("utf-8"))
    except Exception:  # noqa: BLE001 - 内容不可读按失败处理
        return None
    return content if isinstance(content, dict) else None


def effective_step_runs(port, handle, stage):
    """该 stage 的有效 StepRun（去 ID、解析 request/result，按 created_at 顺序）。

    仅当接替者（沿 supersedes 链指向被接替者）自身为该 stage 承载恰 1 个
    StagePackage 时，才从有效运行中移除被接替者（G7-RULINGS 第 45 条）。
    """
    rows = _stage_runs(port, handle, stage)
    carriers = {
        _step_run_id(row) for row in rows if len(_package_revisions(port, row)) == 1
    }
    effective = []
    for row in rows:
        removed = any(
            other is not row
            and _step_run_id(other) in carriers
            and _chain_reaches(port, _step_run_id(other), _step_run_id(row))
            for other in rows
        )
        if not removed:
            effective.append(_with_parsed(row))
    return effective


def succeeded_step_runs(port, handle, stage):
    """该 stage 全部 ``succeeded`` 的 StepRun（含已被 supersede 者），仅供血缘判定。"""
    rows = [
        row for row in _stage_runs(port, handle, stage) if row.get("status") == "succeeded"
    ]
    return [_with_parsed(row) for row in rows]


def _result(stage, handle, gate, checks, effective_ids):
    return {
        "stage": stage,
        "edition_part_id": handle["edition_part_id"],
        "processing_run_id": handle["processing_run_id"],
        "gate": gate,
        "checks": checks,
        "effective_step_run_ids": effective_ids,
    }


def _output_contract(port, descriptor, carrier, run_packages):
    produces = set()
    if descriptor is not None:
        produces = {
            item.get("artifact_type") for item in (descriptor.get("produces") or [])
        }
    if carrier is not None:
        packages = run_packages[_step_run_id(carrier)]
    else:
        packages = [pkg for pkgs in run_packages.values() for pkg in pkgs]
    contents = [
        content
        for content in (_read_package_content(port, pkg) for pkg in packages)
        if content is not None
    ]
    produced = set()
    for content in contents:
        for ref in (content.get("manifest") or {}).get("output_artifacts", []) or []:
            produced.add(ref.get("artifact_type"))

    ok = True
    details = []
    missing = produces - produced
    if missing:
        ok = False
        details.append("缺少 produces 类型: %s" % sorted(missing))

    if carrier is not None:
        carrier_id = _step_run_id(carrier)
        listed = set((carrier.get("result") or {}).get("output_artifact_ids") or [])
        for content in contents:
            for ref in (content.get("manifest") or {}).get("output_artifacts", []) or []:
                revision_id = ref.get("artifact_revision_id")
                revision = port.get_revision(revision_id)
                if revision is None:
                    ok = False
                    details.append("output ref 不存在: %s" % revision_id)
                    continue
                if revision.get("status") != "sealed":
                    ok = False
                    details.append("output ref 未 sealed: %s" % revision_id)
                if revision.get("step_run_id") != carrier_id:
                    ok = False
                    details.append("output ref 不属 carrier: %s" % revision_id)
                if revision_id not in listed:
                    ok = False
                    details.append("output ref 不在 result.output_artifact_ids: %s" % revision_id)
    return {
        "ok": ok,
        "detail": "produces 齐全且引用合法" if ok else "；".join(details),
    }


def _no_pending_work(port, handle, stage, effective, effective_ids):
    ok = True
    details = []
    latest = port.latest_checkpoint(handle["edition_part_id"], stage)
    if latest is not None:
        content = latest.get("content") or {}
        if latest.get("step_run_id") not in effective_ids:
            ok = False
            details.append("最新 Checkpoint 不属于有效运行")
        if (content.get("pending_queue") or []) != []:
            ok = False
            details.append("最新 Checkpoint 仍有待办")
        if content.get("next_pointer") is not None:
            ok = False
            details.append("最新 Checkpoint next_pointer 非空")
    for row in effective:
        events = [
            event.get("event_type")
            for event in port.list_step_run_events(_step_run_id(row))
        ]
        if "await_human" in events:
            last_index = len(events) - 1 - events[::-1].index("await_human")
            if "resume" not in events[last_index + 1 :]:
                ok = False
                details.append("await_human 之后无 resume: %s" % _step_run_id(row))
    return {"ok": ok, "detail": "无待办" if ok else "；".join(details)}


def _upstream_lineage(port, handle, descriptor, effective, upstream_handles=None):
    """``consumes`` 的每个上游 stage 都须有 succeeded 产出被有效运行冻结。

    上游默认在本句柄的运行里找；``upstream_handles``（stage → 句柄）由调度器显式给出
    上游所在运行（T04 Q7：发布段的 m1–m6 在 EditionRun、m7 在 M7 自己的 release run）。
    只按句柄的运行号取数，不按 EditionPart 回退。
    """
    if descriptor is None:
        return {"ok": True, "detail": "未登记 Module，血缘不判"}
    consumes = descriptor.get("consumes") or []
    if not consumes:
        return {"ok": True, "detail": "无 consumes"}
    from_stages = sorted(
        {item.get("from_stage") for item in consumes if item.get("from_stage")}
    )
    problems = []
    for upstream_stage in from_stages:
        upstream_handle = (upstream_handles or {}).get(upstream_stage, handle)
        upstream_ids = {
            _step_run_id(row)
            for row in succeeded_step_runs(port, upstream_handle, upstream_stage)
        }
        for row in effective:
            request = row.get("request") or {}
            refs = request.get("input_artifact_ids") or []
            matched = any(
                (port.get_revision(revision_id) or {}).get("step_run_id")
                in upstream_ids
                for revision_id in refs
            )
            if not matched:
                problems.append(
                    "%s 未冻结 %s 的 succeeded 产出"
                    % (_step_run_id(row), upstream_stage)
                )
    return {"ok": not problems, "detail": "血缘 ok" if not problems else "；".join(problems)}


def evaluate_stage_gate(port, registry, handle, stage, upstream_handles=None):
    """独立判定某 stage 的 Stage Gate，返回报告 dict（不落盘）。

    ``upstream_handles`` 只影响 ``upstream_lineage`` 去哪个运行找上游，见 ``_upstream_lineage``。
    """
    descriptor = registry.module_for(stage) if registry is not None else None
    effective = effective_step_runs(port, handle, stage)
    effective_ids = [_step_run_id(row) for row in effective]
    checks = {}
    if not effective:
        for name in GATE_CHECKS:
            checks[name] = {"ok": False, "detail": "无任务"}
        return _result(stage, handle, "blocked", checks, effective_ids)

    run_packages = {
        _step_run_id(row): _package_revisions(port, row) for row in effective
    }
    carriers = [
        row for row in effective if len(run_packages[_step_run_id(row)]) == 1
    ]
    overfull = [
        row for row in effective if len(run_packages[_step_run_id(row)]) > 1
    ]

    checks["tasks_present"] = {"ok": True, "detail": "有效运行 %d 个" % len(effective)}

    not_succeeded = [
        (_step_run_id(row), row.get("status"))
        for row in effective
        if row.get("status") != "succeeded" or row.get("result") is None
    ]
    checks["all_tasks_succeeded"] = {
        "ok": not not_succeeded,
        "detail": "全部 succeeded" if not not_succeeded else "非 succeeded: %s" % not_succeeded,
    }

    # stage_package_valid（G7-RULINGS 第 45 条）
    ok = True
    details = []
    if len(carriers) != 1:
        ok = False
        details.append("承载 StagePackage 的有效运行数 = %d（须恰 1）" % len(carriers))
    if overfull:
        ok = False
        details.append(
            "存在承载多个 StagePackage 的运行: %s"
            % [_step_run_id(row) for row in overfull]
        )
    carrier = carriers[0] if len(carriers) == 1 else None
    if carrier is not None:
        carrier_id = _step_run_id(carrier)
        package_revision = run_packages[carrier_id][0]
        if package_revision.get("status") != "sealed":
            ok = False
            details.append("carrier 包修订未 sealed: %s" % package_revision.get("status"))
        content = _read_package_content(port, package_revision)
        if content is None:
            ok = False
            details.append("carrier 包内容不可读")
        else:
            try:
                _validator().validate(content)
            except jsonschema.ValidationError as exc:
                ok = False
                details.append("carrier 包过 Schema 失败: %s" % exc.message)
            manifest = content.get("manifest") or {}
            if content.get("stage") != stage:
                ok = False
                details.append("包 stage %r != %r" % (content.get("stage"), stage))
            if manifest.get("step_run_id") != carrier_id:
                ok = False
                details.append("manifest.step_run_id != carrier")
            if manifest.get("processing_run_id") != handle["processing_run_id"]:
                ok = False
                details.append("manifest.processing_run_id != handle")
        for row in effective:
            run_id = _step_run_id(row)
            if run_id == carrier_id or run_packages[run_id]:
                continue
            if row.get("status") != "succeeded":
                ok = False
                details.append("非承载运行未 succeeded: %s" % run_id)
            elif not _chain_reaches(port, run_id, carrier_id):
                ok = False
                details.append("非承载运行 supersedes 链未回溯到 carrier: %s" % run_id)
    checks["stage_package_valid"] = {
        "ok": ok,
        "detail": "carrier 包合法" if ok else "；".join(details),
    }

    checks["output_contract"] = _output_contract(
        port, descriptor, carrier, run_packages
    )

    bad_validation = sorted(
        {
            _step_run_id(row)
            for row in effective
            for pkg in run_packages[_step_run_id(row)]
            if (_read_package_content(port, pkg) or {})
            .get("validation", {})
            .get("passed")
            is not True
        }
    )
    checks["validation_passed"] = {
        "ok": not bad_validation,
        "detail": "全部 validation.passed=true"
        if not bad_validation
        else "未通过: %s" % bad_validation,
    }

    bad_failures = set()
    for row in effective:
        run_id = _step_run_id(row)
        if (row.get("result") or {}).get("failure_artifact_ids"):
            bad_failures.add(run_id)
        for pkg in run_packages[run_id]:
            if (_read_package_content(port, pkg) or {}).get("failures"):
                bad_failures.add(run_id)
    checks["failures_zero"] = {
        "ok": not bad_failures,
        "detail": "无失败" if not bad_failures else "有 failure: %s" % sorted(bad_failures),
    }

    checks["no_pending_work"] = _no_pending_work(
        port, handle, stage, effective, effective_ids
    )
    checks["upstream_lineage"] = _upstream_lineage(
        port, handle, descriptor, effective, upstream_handles
    )

    gate = (
        "passed"
        if all(check["ok"] for check in checks.values())
        else "blocked"
    )
    return _result(stage, handle, gate, checks, effective_ids)
