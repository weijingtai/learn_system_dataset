"""impl-04 K2 测试脚手架：临时 Ledger、合成 PNG、灌入合成 m1 清单。

只供测试使用；提供 ``assets_available`` / ``make_synthetic_png`` /
``seed_m1_manifest`` / ``table_counts``，ACT 04 起按 contract 只允许追加函数。
"""

import hashlib
import json
import struct
import zlib
from pathlib import Path

import yaml

from pipeline.ledger import ids
from pipeline.ledger.fixture_ingest import ingest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"
REPO_ASSET_ROOT = REPO_ROOT / "ocr" / "data_work" / "sanche_pages"


def assets_available():
    """本机三页页图是否齐备。"""
    return all(
        (REPO_ASSET_ROOT / ("page_%03d.png" % number)).is_file()
        for number in (1, 2, 3)
    )


def make_synthetic_png(width, height, payload=b""):
    """构造一个带合法 IHDR 的合成 PNG 字节（仅用于合成清单单元测试）。"""

    def chunk(type_bytes, data):
        return (
            struct.pack(">I", len(data))
            + type_bytes
            + data
            + struct.pack(">I", zlib.crc32(type_bytes + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", payload)
        + chunk(b"IEND", b"")
    )


def seed_m1_manifest(service, manifest_dict):
    """把一个合成 m1 清单经真实 Ledger 写路径灌入，返回 manifest 修订号。"""
    edition_part_id = manifest_dict["edition_part"]["artifact_id"]
    technique_id = manifest_dict["technique_id"]
    processing_run_id = service.create_processing_run(
        "edition_run", edition_part_id, technique_id
    )
    _, config_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        json.dumps(
            {"stage": "m1", "tool": "test.seed", "tool_version": "0"},
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8"),
        producer_module="test.seed",
        producer_version="0",
    )
    step_run_id = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": ids.new_id("step_run_id"),
            "input_artifact_ids": [],
            "technique_profile_id": technique_id,
            "configuration_artifact_id": config_revision_id,
        }
    )
    manifest_bytes = yaml.safe_dump(
        manifest_dict, allow_unicode=True, sort_keys=False
    ).encode("utf-8")
    _, manifest_revision_id = service.put_artifact(
        step_run_id,
        "source_manifest",
        manifest_bytes,
        producer_module="test.seed",
        producer_version="0",
    )
    service.seal_revision(manifest_revision_id)
    service.write_checkpoint(
        step_run_id,
        edition_part_id=edition_part_id,
        stage="m1",
        completed_tasks=[
            {
                "task_id": "ingest_source",
                "artifact_revision_id": manifest_revision_id,
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )
    _, report_revision_id = service.put_artifact(
        step_run_id,
        "validation_report",
        json.dumps({"passed": True}, sort_keys=True).encode("utf-8"),
        producer_module="test.seed",
        producer_version="0",
    )
    service.seal_revision(report_revision_id)
    _, log_revision_id = service.put_artifact(
        step_run_id,
        "step_log",
        b"seed_m1_manifest",
        producer_module="test.seed",
        producer_version="0",
    )
    service.seal_revision(log_revision_id)
    service.record_transformation(
        step_run_id,
        operation="ingest_source",
        tool="test.seed",
        tool_version="0",
        configuration_revision_id=config_revision_id,
        input_revision_ids=[],
        output_revision_ids=[manifest_revision_id],
        validation_report_revision_id=report_revision_id,
        human_event_revision_ids=[],
    )
    current_version = service.get_step_run(step_run_id)["status_version"]
    service.finish_step_run(
        step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "status_version": current_version + 1,
            "status": "succeeded",
            "output_artifact_ids": [manifest_revision_id],
            "validation_report_ids": [report_revision_id],
            "log_artifact_ids": [log_revision_id],
            "failure_artifact_ids": [],
        },
    )
    return manifest_revision_id


def table_counts(service):
    """返回关键表行数，用于断言「拒绝路径无写入」。"""
    connection = service.store.conn

    def count(table):
        return connection.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]

    return {
        "processing_runs": count("processing_runs"),
        "artifact_revisions": count("artifact_revisions"),
        "step_runs": count("step_runs"),
        "audit_log": count("audit_log"),
    }


def sha256_hex(data):
    """测试内使用的 SHA-256 助手。"""
    return hashlib.sha256(data).hexdigest()


def prepare_m3(service):
    """灌入 m1/m2 并在真实 Ledger 上跑 ``run_m3``。

    返回 ``{"edition_part_id", "m3": summary}``。
    """
    from pipeline.corpus_compiler.step import run_m3

    summary = ingest(FIXTURE, service, stages=("m1", "m2"))
    edition_part_id = summary["edition_part_id"]
    m3_summary = run_m3(service, edition_part_id)
    return {"edition_part_id": edition_part_id, "m3": m3_summary}


def prepare_m8_ready(service):
    """``prepare_m3`` 后再登记本机真实页图。返回 ``{"edition_part_id", "m3", "assets"}``。"""
    from pipeline.dataset_compiler.shim.m1_shim_source_assets import (
        register_source_assets,
    )

    prepared = prepare_m3(service)
    prepared["assets"] = register_source_assets(
        service, prepared["edition_part_id"], REPO_ASSET_ROOT
    )
    return prepared


def seed_succeeded_m8_checkpoint(service, edition_part_id):
    """只用于 R1 测试：造一个 succeeded 的 m8 StepRun 及其 Checkpoint。"""
    processing_run_id = service.create_processing_run(
        "release_run", edition_part_id, "qizheng"
    )
    _, config_revision_id = service.put_run_artifact(
        processing_run_id,
        "configuration",
        json.dumps(
            {"stage": "m8", "tool": "test.seed", "tool_version": "0"},
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8"),
        producer_module="test.seed",
        producer_version="0",
    )
    step_run_id = service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": ids.new_id("step_run_id"),
            "input_artifact_ids": [],
            "technique_profile_id": "qizheng",
            "configuration_artifact_id": config_revision_id,
        }
    )
    _, log_revision_id = service.put_artifact(
        step_run_id,
        "step_log",
        b"seed_succeeded_m8_checkpoint",
        producer_module="test.seed",
        producer_version="0",
    )
    service.seal_revision(log_revision_id)
    service.write_checkpoint(
        step_run_id,
        edition_part_id=edition_part_id,
        stage="m8",
        completed_tasks=[
            {
                "task_id": "seed",
                "artifact_revision_id": log_revision_id,
                "status": "succeeded",
                "terminal_state": None,
            }
        ],
        human_decisions=[],
        pending_queue=[],
        next_pointer=None,
    )
    current_version = service.get_step_run(step_run_id)["status_version"]
    service.finish_step_run(
        step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "status_version": current_version + 1,
            "status": "succeeded",
            "output_artifact_ids": [log_revision_id],
            "validation_report_ids": [],
            "log_artifact_ids": [log_revision_id],
            "failure_artifact_ids": [],
        },
    )
    return step_run_id
