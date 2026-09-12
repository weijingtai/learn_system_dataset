"""薄 M1 页图登记 register_source_assets（规格 §16:723、§22.3:991，裁决 D2）。

从 Ledger 中已封存的 m1 ``source_manifest`` 读来源清单，把 ``--asset-root`` 下
的派生页图逐页登记进本地 Object Store（``artifact_type = source_asset_page``，
``rights_scope = internal``），每页一个 m1 Checkpoint。

差异登记（主 Agent 裁定 G7-RULINGS §9.2 第 32 条）：新建 m1 StepRun 采用
``service.supersede_step_run(<该 EditionPart 最近一个 succeeded 的 m1 StepRun>, request)``
——因为 Ledger 的阶段封存守卫（``pipeline/ledger/service.py:1280-1285``）要求续写
已 succeeded 的 m1 阶段时新运行必须处于 supersedes 链上。被接替的 m1 StepRun 经
Ledger 读接口查出，不写死常量。其余 artifact_type / task_id / 返回键 / CLI 按
ACT impl-04/03 契约逐字不变。
"""

import argparse
import hashlib
import sys
from pathlib import Path

import yaml

from pipeline.dataset_compiler import canonical
from pipeline.dataset_compiler.errors import DatasetRefused
from pipeline.dataset_compiler.packs import png_size
from pipeline.ledger import ids
from pipeline.ledger.errors import HashMismatch, LedgerError, WriterLocked
from pipeline.ledger.service import LedgerService

from . import SHIM_TOOL, SHIM_TOOL_VERSION


class SourceAssetMissing(DatasetRefused):
    """派生页图缺失；错误码 ``SRC_001``，消息以 ``BLOCKED_SOURCE_ASSET_MISSING `` 开头。"""

    def __init__(self, missing_path_refs):
        super().__init__(
            "BLOCKED_SOURCE_ASSET_MISSING " + " ".join(missing_path_refs),
            code="SRC_001",
        )


def _artifact_type(service, artifact_revision_id):
    """经只读 SELECT 取修订的 artifact_type。"""
    row = service.store.conn.execute(
        "SELECT a.artifact_type FROM artifacts a "
        "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
        "WHERE r.artifact_revision_id=?",
        (artifact_revision_id,),
    ).fetchone()
    return None if row is None else row[0]


def _resolve_manifest(service, edition_part_id):
    """P1：解析 m1 ``ingest_source`` 成功记录指向的 source_manifest 修订。"""
    manifest_revision_id = None
    for checkpoint in service.list_checkpoints(edition_part_id, "m1"):
        for task in checkpoint["content"].get("completed_tasks", []):
            if task["task_id"] == "ingest_source" and task["status"] == "succeeded":
                manifest_revision_id = task["artifact_revision_id"]
    if manifest_revision_id is None:
        raise DatasetRefused("M1 未灌入：没有 ingest_source 成功记录", code="REF_001")
    revision = service.get_revision(manifest_revision_id)
    if (
        revision is None
        or revision["status"] != "sealed"
        or _artifact_type(service, manifest_revision_id) != "source_manifest"
    ):
        raise DatasetRefused(
            "M1 清单修订非法或未封存: %s" % manifest_revision_id, code="REF_001"
        )
    return manifest_revision_id, revision


def _most_recent_succeeded_m1_step_run(service, edition_part_id):
    """取该 EditionPart 最近一个 succeeded 的 m1 StepRun（裁定 §9.2-32）。"""
    succeeded = []
    for checkpoint in service.list_checkpoints(edition_part_id, "m1"):
        step_run_id = checkpoint["content"]["step_run_id"]
        if step_run_id in succeeded:
            continue
        row = service.get_step_run(step_run_id)
        if row is not None and row["status"] == "succeeded":
            succeeded.append(step_run_id)
    if not succeeded:
        raise DatasetRefused("M1 未通过：没有 succeeded 的 m1 StepRun", code="REF_001")
    return succeeded[-1]


def _already_registered_task(service, edition_part_id):
    """P2：若已有 ``source_asset_`` 任务且所属 StepRun succeeded，返回其 task_id。"""
    for checkpoint in service.list_checkpoints(edition_part_id, "m1"):
        for task in checkpoint["content"].get("completed_tasks", []):
            if task["task_id"].startswith("source_asset_"):
                row = service.get_step_run(checkpoint["content"]["step_run_id"])
                if row is not None and row["status"] == "succeeded":
                    return task["task_id"]
    return None


def _fail(service, step_run_id, check, detail):
    """begin 之后的失败封存：put failure_report → seal → fail_step_run。"""
    _, failure_revision_id = service.put_artifact(
        step_run_id,
        "failure_report",
        canonical.canonical_bytes({"check": check, "detail": detail}),
        producer_module=SHIM_TOOL,
        producer_version=SHIM_TOOL_VERSION,
    )
    service.seal_revision(failure_revision_id)
    service.fail_step_run(
        step_run_id, [failure_revision_id], "M1 register_source_assets %s: %s" % (check, detail)
    )
    return {
        "status": "failed",
        "step_run_id": step_run_id,
        "failed_check": check,
        "failure_revision_id": failure_revision_id,
        "reason": detail,
    }


def _register_after_begin(
    service, step_run_id, edition_part_id, processing_run_id, manifest,
    page_bytes, manifest_revision_id, config_revision_id,
):
    """begin 成功之后的完整流程（P5）。"""
    source_assets = manifest["source_assets"]
    asset_revision_ids = {}
    checkpoint_revision_ids = []
    log_lines = ["resolve m1 manifest %s" % manifest_revision_id]

    for index, item in enumerate(source_assets):
        page = item["page"]
        _, revision_id = service.put_artifact(
            step_run_id,
            "source_asset_page",
            page_bytes[page],
            producer_module=SHIM_TOOL,
            producer_version=SHIM_TOOL_VERSION,
            rights_scope="internal",
        )
        service.seal_revision(revision_id)
        asset_revision_ids[page] = revision_id
        log_lines.append("register %s %s" % (page, revision_id))
        remaining = [
            {"task_id": "source_asset_%s" % later["page"]}
            for later in source_assets[index + 1:]
        ]
        checkpoint_revision_ids.append(
            service.write_checkpoint(
                step_run_id,
                edition_part_id=edition_part_id,
                stage="m1",
                completed_tasks=[
                    {
                        "task_id": "source_asset_%s" % page,
                        "artifact_revision_id": revision_id,
                        "status": "succeeded",
                        "terminal_state": None,
                    }
                ],
                human_decisions=[],
                pending_queue=remaining,
                next_pointer=remaining[0] if remaining else None,
            )
        )

    register_doc = canonical.canonical_bytes(
        {
            item["page"]: {
                "artifact_revision_id": asset_revision_ids[item["page"]],
                "sha256": item["sha256"],
                "size": len(page_bytes[item["page"]]),
                "width": item["width"],
                "height": item["height"],
            }
            for item in source_assets
        }
    )
    _, register_revision_id = service.put_artifact(
        step_run_id,
        "source_asset_register",
        register_doc,
        producer_module=SHIM_TOOL,
        producer_version=SHIM_TOOL_VERSION,
    )
    service.seal_revision(register_revision_id)

    _, validation_revision_id = service.put_artifact(
        step_run_id,
        "validation_report",
        canonical.canonical_bytes({"checks": ["sha256", "png_size"], "passed": True}),
        producer_module=SHIM_TOOL,
        producer_version=SHIM_TOOL_VERSION,
    )
    service.seal_revision(validation_revision_id)

    _, log_revision_id = service.put_artifact(
        step_run_id,
        "step_log",
        "\n".join(log_lines).encode("utf-8"),
        producer_module=SHIM_TOOL,
        producer_version=SHIM_TOOL_VERSION,
    )
    service.seal_revision(log_revision_id)

    output_revision_ids = list(asset_revision_ids.values()) + [register_revision_id]
    transformation_id = service.record_transformation(
        step_run_id,
        operation="register_source_assets",
        tool=SHIM_TOOL,
        tool_version=SHIM_TOOL_VERSION,
        configuration_revision_id=config_revision_id,
        input_revision_ids=[manifest_revision_id],
        output_revision_ids=output_revision_ids,
        validation_report_revision_id=validation_revision_id,
        human_event_revision_ids=[],
    )

    current_version = service.get_step_run(step_run_id)["status_version"]
    step_manifest_revision_id = service.finish_step_run(
        step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "status_version": current_version + 1,
            "status": "succeeded",
            "output_artifact_ids": output_revision_ids,
            "validation_report_ids": [validation_revision_id],
            "log_artifact_ids": [log_revision_id],
            "failure_artifact_ids": [],
        },
    )

    return {
        "status": "succeeded",
        "processing_run_id": processing_run_id,
        "step_run_id": step_run_id,
        "asset_revision_ids": asset_revision_ids,
        "register_revision_id": register_revision_id,
        "validation_report_revision_id": validation_revision_id,
        "log_revision_id": log_revision_id,
        "step_manifest_revision_id": step_manifest_revision_id,
        "transformation_id": transformation_id,
        "checkpoint_revision_ids": checkpoint_revision_ids,
    }


def register_source_assets(service, edition_part_id, asset_root):
    """把 ``asset_root`` 下的派生页图登记进 Ledger（规格 §16:723）。"""
    manifest_revision_id, manifest_revision = _resolve_manifest(
        service, edition_part_id
    )
    registered_task = _already_registered_task(service, edition_part_id)
    if registered_task is not None:
        raise DatasetRefused("SourceAsset 已登记: %s" % registered_task)

    # P3：清单字节与解析
    manifest_bytes = service.objects.get(manifest_revision["sha256"])
    if hashlib.sha256(manifest_bytes).hexdigest() != manifest_revision["sha256"]:
        raise HashMismatch("清单对象哈希不一致（SRC_003）", code="SRC_003")
    manifest = yaml.safe_load(manifest_bytes.decode("utf-8"))
    source_assets = manifest["source_assets"]

    # P4：预检（全部完成之前不得有任何写入）
    missing = []
    for item in source_assets:
        path = Path(asset_root) / Path(item["path_ref"]).name
        if not path.is_file():
            missing.append(item["path_ref"])
    if missing:
        raise SourceAssetMissing(missing)

    page_bytes = {}
    for item in source_assets:
        path = Path(asset_root) / Path(item["path_ref"]).name
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise HashMismatch("页 %s 资产哈希不符（SRC_003）" % item["page"], code="SRC_003")
        if png_size(content) != (item["width"], item["height"]):
            raise HashMismatch("页 %s 资产尺寸不符（SRC_003）" % item["page"], code="SRC_003")
        page_bytes[item["page"]] = content

    # P5：写入（新建 m1 StepRun 须 supersede 最近一个 succeeded 的 m1 运行，裁定 §9.2-32）
    supersede_step_run_id = _most_recent_succeeded_m1_step_run(service, edition_part_id)
    processing_run_id = service.get_step_run(supersede_step_run_id)["processing_run_id"]

    _, config_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        canonical.canonical_bytes(
            {
                "stage": "m1",
                "tool": SHIM_TOOL,
                "tool_version": SHIM_TOOL_VERSION,
                "task": "register_source_assets",
                "asset_count": len(source_assets),
            }
        ),
        producer_module=SHIM_TOOL,
        producer_version=SHIM_TOOL_VERSION,
    )

    request = {
        "schema_version": "1.0.0",
        "processing_run_id": processing_run_id,
        "step_run_id": ids.new_id("step_run_id"),
        "input_artifact_ids": [manifest_revision_id],
        "technique_profile_id": manifest["technique_id"],
        "configuration_artifact_id": config_revision_id,
    }
    step_run_id = service.supersede_step_run(supersede_step_run_id, request)

    try:
        return _register_after_begin(
            service, step_run_id, edition_part_id, processing_run_id, manifest,
            page_bytes, manifest_revision_id, config_revision_id,
        )
    except Exception as exc:
        try:
            return _fail(
                service, step_run_id, "internal", "%s: %s" % (type(exc).__name__, exc)
            )
        except Exception as fail_exc:
            raise exc from fail_exc


def main(argv=None):
    """``python -m pipeline.dataset_compiler.shim.m1_shim_source_assets`` 入口。"""
    parser = argparse.ArgumentParser(
        prog="pipeline.dataset_compiler.shim.m1_shim_source_assets",
        description="薄 M1：派生页图登记进本地 Object Store（裁决 D2）",
    )
    parser.add_argument("--root", required=True, help="Ledger 根目录")
    parser.add_argument("--edition-part", required=True, help="版本部件 artifact_id")
    parser.add_argument("--asset-root", required=True, help="派生页图素材根目录")
    args = parser.parse_args(argv)

    service = LedgerService(args.root)
    try:
        try:
            result = register_source_assets(service, args.edition_part, args.asset_root)
        except WriterLocked:
            return 3
        except SourceAssetMissing as exc:
            print(str(exc))
            return 3
        except DatasetRefused as exc:
            print("ASSETS REFUSED %s: %s" % (type(exc).__name__, exc))
            return 2
        except LedgerError as exc:
            print("ASSETS REFUSED %s: %s" % (type(exc).__name__, exc))
            return 2

        if result["status"] == "succeeded":
            print(
                "ASSETS OK %s pages=%d"
                % (result["step_run_id"], len(result["asset_revision_ids"]))
            )
            return 0
        print("ASSETS FAILED %s %s" % (result["step_run_id"], result["failed_check"]))
        return 1
    finally:
        service.close()


if __name__ == "__main__":
    raise SystemExit(main())
