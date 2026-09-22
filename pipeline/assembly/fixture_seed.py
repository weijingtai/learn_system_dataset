"""M7 合成输入播种工具（act/g0-04；act/impl-07/20 追加 release 播种）。

非生产代码；只经参数读取 tests/data 或 fixture 的合成输入，灌入临时 Ledger。
"""

import json
from pathlib import Path
from typing import Any, Dict

import yaml


def seed_genesis_package(service, doc: dict) -> Dict[str, Any]:
    """按 doc 的 ledger_constants 灌入合成 M4 与 M6 历史。"""
    lc = doc["ledger_constants"]
    technique_id = lc["technique_id"]
    edition_part_id = lc["edition_part_artifact_id"]
    proc_id = lc["processing_run_id"]

    # 1. 创建 ProcessingRun（release_run）
    service.create_processing_run(
        "release_run",
        edition_part_id,
        technique_id,
        processing_run_id=proc_id,
    )

    # 2. M4 配置与 StepRun
    m4_cfg_data = json.dumps({"stage": "m4", "synthetic": True}, sort_keys=True).encode("utf-8")
    m4_cfg_id, m4_cfg_rev_id = service.put_run_artifact(
        proc_id,
        "configuration",
        m4_cfg_data,
        producer_module="pipeline.assembly",
        producer_version="0.1.0-draft",
    )

    m4_step_run_id = lc["m4_step_run_id"]
    service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "step_run_id": m4_step_run_id,
            "processing_run_id": proc_id,
            "input_artifact_ids": [],
            "technique_profile_id": technique_id,
            "configuration_artifact_id": m4_cfg_rev_id,
        }
    )

    # 写入 candidate_set
    cset_bytes = json.dumps(doc["candidate_set"], sort_keys=True, ensure_ascii=False).encode("utf-8")
    service.put_artifact(
        m4_step_run_id,
        "candidate_set",
        cset_bytes,
        artifact_id=lc["candidate_set_artifact_id"],
        artifact_revision_id=lc["candidate_set_revision_id"],
        producer_module="pipeline.assembly",
        producer_version="0.1.0-draft",
    )
    service.seal_revision(lc["candidate_set_revision_id"])

    # 写入 candidate_package
    cp_bytes = json.dumps(
        {
            "synthetic": True,
            "output_artifacts": [lc["candidate_set_revision_id"]],
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    service.put_artifact(
        m4_step_run_id,
        "candidate_package",
        cp_bytes,
        artifact_id=lc["candidate_package_artifact_id"],
        artifact_revision_id=lc["candidate_package_revision_id"],
        producer_module="pipeline.assembly",
        producer_version="0.1.0-draft",
    )
    service.seal_revision(lc["candidate_package_revision_id"])

    # 终结 M4 StepRun 为 succeeded
    service.finish_step_run(
        m4_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": proc_id,
            "step_run_id": m4_step_run_id,
            "status_version": 1,
            "status": "succeeded",
            "output_artifact_ids": [lc["candidate_package_revision_id"], lc["candidate_set_revision_id"]],
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
        },
    )

    # 3. M6 配置与 StepRun
    m6_cfg_data = json.dumps({"stage": "m6", "synthetic": True}, sort_keys=True).encode("utf-8")
    m6_cfg_id, m6_cfg_rev_id = service.put_run_artifact(
        proc_id,
        "configuration",
        m6_cfg_data,
        producer_module="pipeline.assembly",
        producer_version="0.1.0-draft",
    )

    m6_step_run_id = lc["m6_step_run_id"]
    service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "step_run_id": m6_step_run_id,
            "processing_run_id": proc_id,
            "input_artifact_ids": [lc["candidate_package_revision_id"]],
            "technique_profile_id": technique_id,
            "configuration_artifact_id": m6_cfg_rev_id,
        }
    )

    # 写入 reviewed_edition
    re_bytes = json.dumps(doc["reviewed_edition"], sort_keys=True, ensure_ascii=False).encode("utf-8")
    service.put_artifact(
        m6_step_run_id,
        "reviewed_edition",
        re_bytes,
        artifact_id=lc["reviewed_edition_artifact_id"],
        artifact_revision_id=lc["reviewed_edition_revision_id"],
        producer_module="pipeline.assembly",
        producer_version="0.1.0-draft",
    )
    service.seal_revision(lc["reviewed_edition_revision_id"])

    # 写入 reviewed_edition_package
    rep_bytes = json.dumps(doc["reviewed_edition_package"], sort_keys=True, ensure_ascii=False).encode("utf-8")
    service.put_artifact(
        m6_step_run_id,
        "reviewed_edition_package",
        rep_bytes,
        artifact_id=lc["reviewed_edition_package_artifact_id"],
        artifact_revision_id=lc["reviewed_edition_package_revision_id"],
        producer_module="pipeline.assembly",
        producer_version="0.1.0-draft",
    )
    service.seal_revision(lc["reviewed_edition_package_revision_id"])

    # 写入 M6 StagePackage
    m6_stage_package = {
        "schema_version": "1.0.0",
        "stage_package_id": lc["m6_stage_package_id"],
        "artifact_revision_id": lc["m6_package_revision_id"],
        "stage": "m6",
        "status": "draft",
        "payload": {},
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": proc_id,
            "step_run_id": m6_step_run_id,
            "input_artifacts": [
                {
                    "schema_version": "1.0.0",
                    "artifact_kind": "artifact",
                    "artifact_id": lc["candidate_package_artifact_id"],
                    "artifact_revision_id": lc["candidate_package_revision_id"],
                    "artifact_type": "candidate_package",
                }
            ],
            "output_artifacts": [
                {
                    "schema_version": "1.0.0",
                    "artifact_kind": "artifact",
                    "artifact_id": lc["reviewed_edition_package_artifact_id"],
                    "artifact_revision_id": lc["reviewed_edition_package_revision_id"],
                    "artifact_type": "reviewed_edition_package",
                }
            ],
            "counts": {"reviewed_edition_package": 1},
            "content_sha256": "0" * 64,
        },
        "validation": {
            "passed": True,
            "report_artifacts": [],
        },
        "lineage": {
            "upstream_artifacts": [
                {
                    "schema_version": "1.0.0",
                    "artifact_kind": "artifact",
                    "artifact_id": lc["candidate_package_artifact_id"],
                    "artifact_revision_id": lc["candidate_package_revision_id"],
                    "artifact_type": "candidate_package",
                }
            ],
            "transformations": [],
        },
        "logs": [],
        "failures": [],
    }
    m6_stage_pkg_bytes = json.dumps(m6_stage_package, sort_keys=True, ensure_ascii=False).encode("utf-8")
    service.register_stage_package(
        m6_step_run_id,
        m6_stage_package,
        m6_stage_pkg_bytes,
        stage_package_id=lc["m6_stage_package_id"],
        artifact_revision_id=lc["m6_package_revision_id"],
    )
    service.seal_revision(lc["m6_package_revision_id"])

    # 终结 M6 StepRun 为 succeeded
    service.finish_step_run(
        m6_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": proc_id,
            "step_run_id": m6_step_run_id,
            "status_version": 1,
            "status": "succeeded",
            "output_artifact_ids": [lc["reviewed_edition_package_revision_id"], lc["m6_package_revision_id"]],
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
        },
    )

    return {
        "candidate_set_revision_id": lc["candidate_set_revision_id"],
        "candidate_package_revision_id": lc["candidate_package_revision_id"],
        "reviewed_edition_revision_id": lc["reviewed_edition_revision_id"],
        "reviewed_edition_package_revision_id": lc["reviewed_edition_package_revision_id"],
        "m6_package_revision_id": lc["m6_package_revision_id"],
        "config_revision_id": m6_cfg_rev_id,
    }


def _seed_one_edition(
    service,
    technique_id: str,
    edition_part_id: str,
    proc_id: str,
    lc: Dict[str, Any],
    candidate_set: dict,
    reviewed_edition: dict,
    reviewed_edition_package: dict,
) -> Dict[str, Any]:
    """把单个版次的 M4/M6 合成历史灌入 Ledger（act/impl-07/20 新增，供 release 播种复用）。

    事务序列与 :func:`seed_genesis_package` 逐段同构，只是输入来自入参而非单包文档。
    """
    # 1. M4 配置与 StepRun
    m4_cfg_data = json.dumps({"stage": "m4", "synthetic": True}, sort_keys=True).encode("utf-8")
    _, m4_cfg_rev_id = service.put_run_artifact(
        proc_id,
        "configuration",
        m4_cfg_data,
        producer_module="pipeline.assembly",
        producer_version="0.1.0-draft",
    )

    m4_step_run_id = lc["m4_step_run_id"]
    service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "step_run_id": m4_step_run_id,
            "processing_run_id": proc_id,
            "input_artifact_ids": [],
            "technique_profile_id": technique_id,
            "configuration_artifact_id": m4_cfg_rev_id,
        }
    )

    cset_bytes = json.dumps(candidate_set, sort_keys=True, ensure_ascii=False).encode("utf-8")
    service.put_artifact(
        m4_step_run_id,
        "candidate_set",
        cset_bytes,
        artifact_id=lc["candidate_set_artifact_id"],
        artifact_revision_id=lc["candidate_set_revision_id"],
        producer_module="pipeline.assembly",
        producer_version="0.1.0-draft",
    )
    service.seal_revision(lc["candidate_set_revision_id"])

    cp_bytes = json.dumps(
        {"synthetic": True, "output_artifacts": [lc["candidate_set_revision_id"]]},
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    service.put_artifact(
        m4_step_run_id,
        "candidate_package",
        cp_bytes,
        artifact_id=lc["candidate_package_artifact_id"],
        artifact_revision_id=lc["candidate_package_revision_id"],
        producer_module="pipeline.assembly",
        producer_version="0.1.0-draft",
    )
    service.seal_revision(lc["candidate_package_revision_id"])

    service.finish_step_run(
        m4_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": proc_id,
            "step_run_id": m4_step_run_id,
            "status_version": 1,
            "status": "succeeded",
            "output_artifact_ids": [lc["candidate_package_revision_id"], lc["candidate_set_revision_id"]],
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
        },
    )

    # 2. M6 配置与 StepRun
    m6_cfg_data = json.dumps({"stage": "m6", "synthetic": True}, sort_keys=True).encode("utf-8")
    _, m6_cfg_rev_id = service.put_run_artifact(
        proc_id,
        "configuration",
        m6_cfg_data,
        producer_module="pipeline.assembly",
        producer_version="0.1.0-draft",
    )

    m6_step_run_id = lc["m6_step_run_id"]
    service.begin_step_run(
        {
            "schema_version": "1.0.0",
            "step_run_id": m6_step_run_id,
            "processing_run_id": proc_id,
            "input_artifact_ids": [lc["candidate_package_revision_id"]],
            "technique_profile_id": technique_id,
            "configuration_artifact_id": m6_cfg_rev_id,
        }
    )

    re_bytes = json.dumps(reviewed_edition, sort_keys=True, ensure_ascii=False).encode("utf-8")
    service.put_artifact(
        m6_step_run_id,
        "reviewed_edition",
        re_bytes,
        artifact_id=lc["reviewed_edition_artifact_id"],
        artifact_revision_id=lc["reviewed_edition_revision_id"],
        producer_module="pipeline.assembly",
        producer_version="0.1.0-draft",
    )
    service.seal_revision(lc["reviewed_edition_revision_id"])

    rep_bytes = json.dumps(reviewed_edition_package, sort_keys=True, ensure_ascii=False).encode("utf-8")
    service.put_artifact(
        m6_step_run_id,
        "reviewed_edition_package",
        rep_bytes,
        artifact_id=lc["reviewed_edition_package_artifact_id"],
        artifact_revision_id=lc["reviewed_edition_package_revision_id"],
        producer_module="pipeline.assembly",
        producer_version="0.1.0-draft",
    )
    service.seal_revision(lc["reviewed_edition_package_revision_id"])

    m6_stage_package = {
        "schema_version": "1.0.0",
        "stage_package_id": lc["m6_stage_package_id"],
        "artifact_revision_id": lc["m6_package_revision_id"],
        "stage": "m6",
        "status": "sealed",
        "payload": {},
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": proc_id,
            "step_run_id": m6_step_run_id,
            "input_artifacts": [
                {
                    "schema_version": "1.0.0",
                    "artifact_kind": "artifact",
                    "artifact_id": lc["candidate_package_artifact_id"],
                    "artifact_revision_id": lc["candidate_package_revision_id"],
                    "artifact_type": "candidate_package",
                }
            ],
            "output_artifacts": [
                {
                    "schema_version": "1.0.0",
                    "artifact_kind": "artifact",
                    "artifact_id": lc["reviewed_edition_package_artifact_id"],
                    "artifact_revision_id": lc["reviewed_edition_package_revision_id"],
                    "artifact_type": "reviewed_edition_package",
                }
            ],
            "counts": {"reviewed_edition_package": 1},
            "content_sha256": "0" * 64,
        },
        "validation": {"passed": True, "report_artifacts": []},
        "lineage": {
            "upstream_artifacts": [
                {
                    "schema_version": "1.0.0",
                    "artifact_kind": "artifact",
                    "artifact_id": lc["candidate_package_artifact_id"],
                    "artifact_revision_id": lc["candidate_package_revision_id"],
                    "artifact_type": "candidate_package",
                }
            ],
            "transformations": [],
        },
        "logs": [],
        "failures": [],
    }
    m6_stage_pkg_bytes = json.dumps(m6_stage_package, sort_keys=True, ensure_ascii=False).encode("utf-8")
    service.register_stage_package(
        m6_step_run_id,
        m6_stage_package,
        m6_stage_pkg_bytes,
        stage_package_id=lc["m6_stage_package_id"],
        artifact_revision_id=lc["m6_package_revision_id"],
    )
    service.seal_revision(lc["m6_package_revision_id"])

    service.finish_step_run(
        m6_step_run_id,
        {
            "schema_version": "1.0.0",
            "processing_run_id": proc_id,
            "step_run_id": m6_step_run_id,
            "status_version": 1,
            "status": "succeeded",
            "output_artifact_ids": [lc["reviewed_edition_package_revision_id"], lc["m6_package_revision_id"]],
            "validation_report_ids": [],
            "log_artifact_ids": [],
            "failure_artifact_ids": [],
        },
    )

    return {
        "edition_part_artifact_id": edition_part_id,
        "processing_run_id": proc_id,
        "candidate_set_revision_id": lc["candidate_set_revision_id"],
        "candidate_package_revision_id": lc["candidate_package_revision_id"],
        "reviewed_edition_revision_id": lc["reviewed_edition_revision_id"],
        "reviewed_edition_package_revision_id": lc["reviewed_edition_package_revision_id"],
        "m6_package_revision_id": lc["m6_package_revision_id"],
        "m6_stage_package_id": lc["m6_stage_package_id"],
        "config_revision_id": m6_cfg_rev_id,
    }


def seed_release_package(service, fixture_dir) -> Dict[str, Any]:
    """按 mini_release01 fixture 的 manifest 灌入**多个版次**的 M4/M6 合成历史。

    只读 fixture 目录（manifest.yaml 与各版次视图），写入调用方给出的临时 Ledger；
    返回 ``{"manifest": ..., "editions": {<edition_key>: {...}}}``。
    """
    fixture_dir = Path(fixture_dir)
    manifest = yaml.safe_load((fixture_dir / "manifest.yaml").read_text(encoding="utf-8"))
    technique_id = manifest["technique_id"]

    seeded: Dict[str, Any] = {}
    for edition in manifest["editions"]:
        edition_key = edition["edition_key"]
        edition_part_id = edition["edition_part_artifact_id"]
        lc = edition["ledger_constants"]
        views = fixture_dir / edition["views_dir"]
        candidate_set = json.loads((views / "candidate_set.json").read_text(encoding="utf-8"))
        reviewed_edition = json.loads((views / "reviewed_edition.json").read_text(encoding="utf-8"))
        reviewed_edition_package = json.loads(
            (views / "reviewed_edition_package.json").read_text(encoding="utf-8")
        )

        service.create_processing_run(
            "release_run",
            edition_part_id,
            technique_id,
            processing_run_id=lc["processing_run_id"],
        )
        seeded[edition_key] = _seed_one_edition(
            service,
            technique_id,
            edition_part_id,
            lc["processing_run_id"],
            lc,
            candidate_set,
            reviewed_edition,
            reviewed_edition_package,
        )

    return {"manifest": manifest, "editions": seeded}
