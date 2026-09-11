"""规格 §20 第 2/3 条的场景判定：在 mini_ed01 灌入的真实 Ledger 上执行（ACT impl-01/05）。

用法::

    python -m pipeline.ledger.acceptance --fixture <dir> --check 20_2|20_3 [--keep]

- 在 ``tempfile.mkdtemp()`` 里建 Ledger，经 ``pipeline.ledger.fixture_ingest`` 真实写路径灌入；
- 每条判定打印 ``PASS <name>`` / ``FAIL <name> <原因>``；
- 退出码：全过 ``0`` / 任一 FAIL ``1`` / 环境缺失 ``3``（fixture 不存在或缺 PyYAML/jsonschema）；
- 无 ``--keep`` 时删除临时目录。

20.2（失败后可从最近 StageCheckpoint 恢复、历史失败不被覆盖）判定名：
``chain_lengths``、``manifest_refs_last_checkpoint``、``failed_run_preserved``、
``recover_skips_completed``、``history_not_overwritten``。

20.3（每个语义转换的输入/输出/工具/配置/校验/人工决定记录齐全）判定名：
``transformations_count``、``inputs_recorded``、``outputs_recorded``、``tool_recorded``、
``config_recorded``、``validation_recorded``、``human_decisions_recorded``、
``step_run_succeeded_with_manifest``。

判据不是永真的：删一个 Checkpoint 或清空校验报告引用，同名判定即 FAIL。
"""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

# 判定名与顺序（两个 check 各自固定，run_all.sh 与测试都按此比对）
CHECK_NAMES = {
    "20_2": (
        "chain_lengths",
        "manifest_refs_last_checkpoint",
        "failed_run_preserved",
        "recover_skips_completed",
        "history_not_overwritten",
    ),
    "20_3": (
        "transformations_count",
        "inputs_recorded",
        "outputs_recorded",
        "tool_recorded",
        "config_recorded",
        "validation_recorded",
        "human_decisions_recorded",
        "step_run_succeeded_with_manifest",
    ),
}

# 恢复场景里重放的 m3 批次（sanche_b001 已完成，其余进入待办队列）
RECOVERED_TASK = "sanche_b001"
PENDING_TASKS = ("sanche_b002", "sanche_b003", "sanche_b004", "sanche_b005")


def _environment_error():
    """检查运行环境（PyYAML / jsonschema）；缺失时返回错误说明。"""
    try:
        import jsonschema  # noqa: F401
        import yaml  # noqa: F401
    except ImportError as exc:  # pragma: no cover - 依赖缺失时走 run_all 的 BLOCKED 分支
        return str(exc)
    return None


# ---------------------------------------------------------------- 只读小工具
def _artifact_type(service, revision_id):
    row = service.store.conn.execute(
        "SELECT a.artifact_type FROM artifacts a JOIN artifact_revisions r "
        "ON r.artifact_id = a.artifact_id WHERE r.artifact_revision_id=?",
        (revision_id,),
    ).fetchone()
    return None if row is None else row[0]


def _frozen_inputs(service, step_run_id):
    rows = service.store.conn.execute(
        "SELECT artifact_revision_id FROM frozen_inputs WHERE step_run_id=? "
        "ORDER BY artifact_revision_id",
        (step_run_id,),
    ).fetchall()
    return [row[0] for row in rows]


def _transformations(service):
    """返回全部 Transformation（含所属 StepRun 的 stage 与状态）。"""
    rows = service.store.conn.execute(
        "SELECT t.id AS id, t.step_run_id AS step_run_id, t.operation AS operation, "
        "t.tool AS tool, t.tool_version AS tool_version, "
        "t.configuration_revision_id AS configuration_revision_id, "
        "t.validation_report_revision_id AS validation_report_revision_id, "
        "s.stage AS stage, s.status AS step_status "
        "FROM transformations t JOIN step_runs s ON s.step_run_id = t.step_run_id "
        "ORDER BY t.id"
    ).fetchall()
    return [dict(row) for row in rows]


def _snapshot_step_run_revisions(service, step_run_id):
    """快照某 StepRun 的全部修订（revision → (status, sha256)）。"""
    rows = service.store.conn.execute(
        "SELECT artifact_revision_id, status, sha256 FROM artifact_revisions "
        "WHERE step_run_id=? ORDER BY artifact_revision_id",
        (step_run_id,),
    ).fetchall()
    return {
        row["artifact_revision_id"]: (row["status"], row["sha256"]) for row in rows
    }


def _event_total(service):
    return service.store.conn.execute(
        "SELECT COUNT(*) FROM step_run_events"
    ).fetchone()[0]


# --------------------------------------------------------------- 20.2 判定
def _check_chain_lengths(service, summary, fixture):
    expected = {"m1": 1, "m2": 3, "m3": 5}
    for stage in ("m1", "m2", "m3"):
        chain = service.list_checkpoints(summary["edition_part_id"], stage)
        if len(chain) != expected[stage]:
            return False, "stage %s 的 Checkpoint 链长 %d != %d" % (
                stage,
                len(chain),
                expected[stage],
            )
        if chain[0]["prev_checkpoint_revision_id"] is not None:
            return False, "stage %s 首个 Checkpoint 的 prev 不为 None" % stage
        for previous, current in zip(chain, chain[1:]):
            if current["prev_checkpoint_revision_id"] != previous["artifact_revision_id"]:
                return False, "stage %s 的 Checkpoint 链在 %s 处断链" % (
                    stage,
                    current["artifact_revision_id"],
                )
    return True, ""


def _check_manifest_refs_last_checkpoint(service, summary, fixture):
    for stage in ("m1", "m2", "m3"):
        manifest_revision_id = summary["stage_packages"][stage]["manifest_revision_id"]
        row = service.get_revision(manifest_revision_id)
        if row is None or row["status"] != "sealed":
            return False, "stage %s 的 StepManifest 修订缺失或未封存" % stage
        content = json.loads(service.objects.get(row["sha256"]).decode("utf-8"))
        last = service.latest_checkpoint(summary["edition_part_id"], stage)
        if last is None:
            return False, "stage %s 没有任何 Checkpoint 可被 StepManifest 引用" % stage
        if content.get("last_checkpoint_revision_id") != last["artifact_revision_id"]:
            return False, (
                "stage %s 的 StepManifest.last_checkpoint_revision_id %r != 最后 Checkpoint %s"
                % (stage, content.get("last_checkpoint_revision_id"),
                   last["artifact_revision_id"])
            )
    return True, ""


def _run_failure_scenario(service, summary, fixture):
    """为 m3 开 R2、完成一个 task、失败封存，再从最近 Checkpoint 恢复出 R3。"""
    from . import ids

    stage = summary["stage_packages"]["m3"]
    edition_part_id = summary["edition_part_id"]
    processing_run_id = summary["processing_run_id"]
    r1 = stage["step_run_id"]

    def request(step_run_id):
        return {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "input_artifact_ids": list(stage["input_revision_ids"]),
            "technique_profile_id": fixture.technique_id,
            "configuration_artifact_id": stage["configuration_revision_id"],
        }

    r2 = service.supersede_step_run(r1, request(ids.new_id("step_run_id")))
    _, task_revision = service.put_artifact(
        r2,
        "corpus_batch",
        json.dumps({"replayed": RECOVERED_TASK}, sort_keys=True).encode("utf-8"),
        producer_module="pipeline.ledger.acceptance",
        producer_version="1.0",
    )
    service.seal_revision(task_revision)
    pending = [{"task_id": name} for name in PENDING_TASKS]
    r2_checkpoint = service.write_checkpoint(
        r2,
        edition_part_id=edition_part_id,
        stage="m3",
        completed_tasks=[
            {
                "task_id": RECOVERED_TASK,
                "artifact_revision_id": task_revision,
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=[],
        pending_queue=pending,
        next_pointer=pending[0],
    )
    _, failure_revision = service.put_artifact(
        r2,
        "failure_report",
        json.dumps({"reason": "宿主缺页"}, sort_keys=True).encode("utf-8"),
        producer_module="pipeline.ledger.acceptance",
        producer_version="1.0",
    )
    service.seal_revision(failure_revision)
    service.fail_step_run(r2, [failure_revision], "宿主缺页导致任务失败")

    events_before_total = _event_total(service)
    events_before_by_run = {
        step_run_id: len(service.list_step_run_events(step_run_id))
        for step_run_id in (r1, r2)
    }
    r3, plan = service.recover_from_checkpoint(
        edition_part_id, "m3", request(ids.new_id("step_run_id"))
    )
    return {
        "r1": r1,
        "r2": r2,
        "r3": r3,
        "r2_checkpoint": r2_checkpoint,
        "failure_revision": failure_revision,
        "task_revision": task_revision,
        "plan": plan,
        "events_before_total": events_before_total,
        "events_before_by_run": events_before_by_run,
    }


def _check_failed_run_preserved(service, context, baseline, scenario_error):
    if context is None:
        return False, "失败场景未能执行（%s）" % scenario_error
    r2 = service.get_step_run(context["r2"])
    if r2 is None or r2["status"] != "failed":
        return False, "R2 (%s) 状态不是 failed" % context["r2"]
    failure = service.get_revision(context["failure_revision"])
    if failure is None or failure["status"] != "sealed":
        return False, "R2 的失败修订未保持 sealed 可读"
    if not service.objects.exists(failure["sha256"]):
        return False, "R2 的失败修订对象不可读"
    r1 = service.get_step_run(context["r1"])
    if r1 is None or r1["status"] != "succeeded":
        return False, "R1 (%s) 状态不再是 succeeded" % context["r1"]
    after = _snapshot_step_run_revisions(service, context["r1"])
    if after != baseline:
        return False, "R1 (%s) 的修订 status/sha256 与灌入后快照不一致" % context["r1"]
    return True, ""


def _check_recover_skips_completed(service, context, baseline, scenario_error):
    if context is None:
        return False, "失败场景未能执行（%s）" % scenario_error
    plan = context["plan"]
    if plan["checkpoint_revision_id"] != context["r2_checkpoint"]:
        return False, "恢复用的 Checkpoint %s != R2 的 Checkpoint %s" % (
            plan["checkpoint_revision_id"],
            context["r2_checkpoint"],
        )
    if plan["completed_task_ids"] != [RECOVERED_TASK]:
        return False, "completed_task_ids %r != [%r]" % (
            plan["completed_task_ids"],
            RECOVERED_TASK,
        )
    pending = [item["task_id"] for item in plan["pending_queue"]]
    if pending != list(PENDING_TASKS):
        return False, "待办队列 %r != %r" % (pending, list(PENDING_TASKS))
    r3 = service.get_step_run(context["r3"])
    if r3 is None or r3["supersedes_step_run_id"] != context["r2"]:
        return False, "R3 (%s) 的 supersedes_step_run_id 不是 R2" % context["r3"]
    if not [
        event
        for event in service.list_step_run_events(context["r3"])
        if event["event_type"] == "recovery"
    ]:
        return False, "R3 没有 recovery 事件"
    return True, ""


def _check_history_not_overwritten(service, context, baseline, scenario_error):
    if context is None:
        return False, "失败场景未能执行（%s）" % scenario_error
    r2 = service.get_step_run(context["r2"])
    if r2 is None or r2["status"] != "failed":
        return False, "R3 创建后 R2 状态不再是 failed"
    failure = service.get_revision(context["failure_revision"])
    if failure is None or failure["status"] != "sealed":
        return False, "R3 创建后 R2 的失败修订不再是 sealed"
    after_total = _event_total(service)
    if after_total < context["events_before_total"]:
        return False, "step_run_events 计数减少: %d -> %d" % (
            context["events_before_total"],
            after_total,
        )
    for step_run_id, before in context["events_before_by_run"].items():
        now = len(service.list_step_run_events(step_run_id))
        if now < before:
            return False, "StepRun %s 的事件计数减少: %d -> %d" % (
                step_run_id,
                before,
                now,
            )
    return True, ""


# --------------------------------------------------------------- 20.3 判定
def _check_transformations_count(service, summary, fixture):
    rows = _transformations(service)
    if len(rows) != 3:
        return False, "Transformation 数量 %d != 3" % len(rows)
    return True, ""


def _check_inputs_recorded(service, summary, fixture):
    for row in _transformations(service):
        inputs = service.store.list_transformation_inputs(row["id"])
        if row["stage"] == "m1":
            if inputs:
                return False, "m1 的输入应为空，实为 %r" % (inputs,)
            continue
        if not inputs:
            return False, "%s 的输入为空" % row["stage"]
        frozen = set(_frozen_inputs(service, row["step_run_id"]))
        if not set(inputs) <= frozen:
            return False, "%s 的输入 %r 不属于冻结输入 %r" % (
                row["stage"],
                inputs,
                sorted(frozen),
            )
    return True, ""


def _check_outputs_recorded(service, summary, fixture):
    for row in _transformations(service):
        outputs = service.store.list_transformation_outputs(row["id"])
        if not outputs:
            return False, "%s 的输出为空" % row["stage"]
        for revision_id in outputs:
            revision = service.get_revision(revision_id)
            if revision is None or revision["status"] != "sealed":
                return False, "%s 的输出修订未封存: %s" % (
                    row["stage"],
                    revision_id,
                )
    return True, ""


def _check_tool_recorded(service, summary, fixture):
    for row in _transformations(service):
        if not row["tool"] or not row["tool_version"]:
            return False, "%s 的 tool/tool_version 为空" % row["stage"]
    return True, ""


def _check_config_recorded(service, summary, fixture):
    for row in _transformations(service):
        revision_id = row["configuration_revision_id"]
        revision = service.get_revision(revision_id) if revision_id else None
        if revision is None or revision["status"] != "sealed":
            return False, "%s 的配置修订缺失或未封存" % row["stage"]
        if _artifact_type(service, revision_id) != "configuration":
            return False, "%s 的配置修订 artifact_type 不是 configuration" % row["stage"]
    return True, ""


def _check_validation_recorded(service, summary, fixture):
    for row in _transformations(service):
        revision_id = row["validation_report_revision_id"]
        revision = service.get_revision(revision_id) if revision_id else None
        if revision is None or revision["status"] != "sealed":
            return False, "%s 的校验报告修订缺失或未封存" % row["stage"]
        if _artifact_type(service, revision_id) != "validation_report":
            return False, "%s 的校验报告修订 artifact_type 不是 validation_report" % row[
                "stage"
            ]
    return True, ""


def _check_human_decisions_recorded(service, summary, fixture):
    for row in _transformations(service):
        events = [
            item[0]
            for item in service.store.conn.execute(
                "SELECT event_revision_id FROM transformation_human_events "
                "WHERE transformation_id=? ORDER BY event_revision_id",
                (row["id"],),
            ).fetchall()
        ]
        if row["stage"] == "m2" and len(events) != 1:
            return False, "m2 的人工决定数量 %d != 1" % len(events)
        for revision_id in events:
            revision = service.get_revision(revision_id)
            if revision is None or revision["status"] != "sealed":
                return False, "%s 的人工决定修订缺失或未封存" % row["stage"]
            if _artifact_type(service, revision_id) != "human_event":
                return False, "%s 的人工决定修订 artifact_type 不是 human_event" % row[
                    "stage"
                ]
    return True, ""


def _check_step_run_succeeded_with_manifest(service, summary, fixture):
    for row in _transformations(service):
        if row["step_status"] != "succeeded":
            return False, "%s 的 StepRun 状态不是 succeeded" % row["stage"]
        manifests = service.store.conn.execute(
            "SELECT r.artifact_revision_id FROM artifact_revisions r "
            "JOIN artifacts a ON a.artifact_id = r.artifact_id "
            "WHERE r.step_run_id=? AND a.artifact_type='step_manifest' "
            "AND r.status='sealed'",
            (row["step_run_id"],),
        ).fetchall()
        if not manifests:
            return False, "%s 的 StepManifest 修订未封存" % row["stage"]
    return True, ""


CHECKS = {
    "20_2": (
        ("chain_lengths", _check_chain_lengths),
        ("manifest_refs_last_checkpoint", _check_manifest_refs_last_checkpoint),
    ),
    "20_3": tuple(
        (name, globals()["_check_%s" % name]) for name in CHECK_NAMES["20_3"]
    ),
}

# 20.2 的失败/恢复场景判定（依赖场景上下文，单独接线）
SCENARIO_CHECKS = (
    ("failed_run_preserved", _check_failed_run_preserved),
    ("recover_skips_completed", _check_recover_skips_completed),
    ("history_not_overwritten", _check_history_not_overwritten),
)


def _safe(function, *args):
    """执行一个判定函数：异常一律转 FAIL，不向上抛。"""
    try:
        return function(*args)
    except Exception as exc:  # noqa: BLE001 - 判定失败必须以 FAIL 呈现
        return False, "判定抛异常: %s: %s" % (type(exc).__name__, exc)


def _result(name, outcome):
    ok, reason = outcome
    return {"name": name, "ok": bool(ok), "reason": "" if ok else reason}


def evaluate(check, service, summary, fixture):
    """执行一个 check 的全部判定，返回 ``[{"name", "ok", "reason"}, ...]``。"""
    if check not in CHECK_NAMES:
        raise ValueError("未知检查: %r" % (check,))
    results = []
    if check == "20_3":
        for name, function in CHECKS["20_3"]:
            results.append(_result(name, _safe(function, service, summary, fixture)))
        return results

    # 20.2：先做不改变 Ledger 的判定，再跑失败/恢复场景，最后基于场景上下文判定
    baseline = _snapshot_step_run_revisions(
        service, summary["stage_packages"]["m3"]["step_run_id"]
    )
    for name, function in CHECKS["20_2"]:
        results.append(_result(name, _safe(function, service, summary, fixture)))

    try:
        context = _run_failure_scenario(service, summary, fixture)
        scenario_error = None
    except Exception as exc:  # noqa: BLE001 - 场景失败必须以 FAIL 呈现
        context = None
        scenario_error = "%s: %s" % (type(exc).__name__, exc)

    for name, function in SCENARIO_CHECKS:
        results.append(
            _result(name, _safe(function, service, context, baseline, scenario_error))
        )
    return results


def checks_exit_code(results):
    """任一 FAIL → 1，否则 0。"""
    return 1 if any(not item["ok"] for item in results) else 0


def prepare(fixture_dir, root=None):
    """建 Ledger 并灌入 fixture，返回 ``(root, service, summary, fixture)``（调用方关闭 service）。"""
    from .fixture_ingest import Fixture, ingest
    from .service import LedgerService

    fixture = Fixture(fixture_dir)
    root = Path(root) if root is not None else Path(
        tempfile.mkdtemp(prefix="ledger-acceptance-")
    )
    service = LedgerService(root / "ledger")
    summary = ingest(fixture, service)
    return root, service, summary, fixture


def main(argv=None):
    """``python -m pipeline.ledger.acceptance`` 入口。"""
    parser = argparse.ArgumentParser(
        prog="pipeline.ledger.acceptance",
        description="§20 第 2/3 条场景判定（宿主 mini_ed01 真实 Ledger）",
    )
    parser.add_argument("--fixture", required=True, help="fixture 根目录")
    parser.add_argument("--check", required=True, choices=sorted(CHECK_NAMES))
    parser.add_argument("--keep", action="store_true", help="保留临时 Ledger 目录")
    args = parser.parse_args(argv)

    fixture_dir = Path(args.fixture)
    if not (fixture_dir / "manifest.yaml").is_file():
        print("FAIL %s fixture 不存在: %s" % (args.check, fixture_dir))
        return 3
    environment_error = _environment_error()
    if environment_error is not None:
        print("BLOCKED_ENV yaml/jsonschema 不可用: %s" % environment_error)
        return 3

    workdir = Path(tempfile.mkdtemp(prefix="ledger-acceptance-"))
    service = None
    try:
        _, service, summary, fixture = prepare(fixture_dir, workdir)
        results = evaluate(args.check, service, summary, fixture)
    except Exception as exc:  # noqa: BLE001 - 宿主不可用 → 环境缺失
        print(
            "FAIL %s 宿主准备失败: %s: %s" % (args.check, type(exc).__name__, exc)
        )
        return 3
    finally:
        if service is not None:
            service.close()
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)

    for item in results:
        if item["ok"]:
            print("PASS %s" % item["name"])
        else:
            print("FAIL %s %s" % (item["name"], item["reason"]))
    return checks_exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
