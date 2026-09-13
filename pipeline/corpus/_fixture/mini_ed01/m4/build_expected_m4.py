#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mini_ed01 m4 金标期望包生成器（impl-00/05，独占 ACT，P4）。

只读 `m4/candidate_set.yaml`（canonical JSON 字节）与四个输入金标，确定性地产出
`<out>/expected/m4.stage_package.yaml`。

约束：
- 只用标准库 + PyYAML；不 import impl-05 的 knowledge_extraction 子包；
- 无 uuid / 时间 / 随机；两次运行字节相同；
- `expected/m4.stage_package.yaml` 仅含占位 ID 与由 `candidate_set` 计算的
  `counts` / `content_sha256`（真实运行期 ID 由 impl-05 生成，验收不比对）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

FIXTURE = Path(__file__).resolve().parents[1]
PLACEHOLDER32 = "0" * 32
PROCESSING_RUN_ID = "prun_" + PLACEHOLDER32
STEP_RUN_ID = "srun_" + PLACEHOLDER32

INPUT_GOLDENS = (
    "submission_assertion_a.yaml",
    "submission_assertion_b.yaml",
    "submission_concept_mention_a.yaml",
    "ruling_m4_d001.yaml",
)


def _rev(suffix: str) -> str:
    return "rev_" + "0" * 31 + suffix


def _art_ref(artifact_id, revision_id, artifact_type, *, kind="artifact", stage_package_id=None):
    ref = {
        "schema_version": "1.0.0",
        "artifact_kind": kind,
        "artifact_revision_id": revision_id,
        "artifact_type": artifact_type,
    }
    if kind == "stage_package":
        ref["stage_package_id"] = stage_package_id
    else:
        ref["artifact_id"] = artifact_id
    return ref


def build_package(candidate_bytes: bytes, counts: dict) -> dict:
    """由 candidate_set 字节与 counts 构造 m4 期望 StagePackage（全占位 ID）。"""
    content_sha256 = hashlib.sha256(candidate_bytes).hexdigest()
    m3_pkg_rev = _rev("2")
    corpus_pkg_rev = _rev("3")
    spans_rev = _rev("4")
    profile_rev = _rev("5")
    config_rev = _rev("6")
    submission_revs = [_rev("7"), _rev("8"), _rev("9")]
    out_rev = _rev("a")
    inputs = [
        _art_ref(None, m3_pkg_rev, "stage_package", kind="stage_package",
                 stage_package_id="pkg_m3_" + PLACEHOLDER32),
        _art_ref("art_" + "0" * 31 + "3", corpus_pkg_rev, "corpus_package"),
        _art_ref("art_" + "0" * 31 + "4", spans_rev, "corpus_spans"),
        _art_ref("art_" + "0" * 31 + "5", profile_rev, "technique_profile"),
        _art_ref("art_" + "0" * 31 + "7", submission_revs[0], "candidate_submission"),
        _art_ref("art_" + "0" * 31 + "8", submission_revs[1], "candidate_submission"),
        _art_ref("art_" + "0" * 31 + "9", submission_revs[2], "candidate_submission"),
    ]
    return {
        "schema_version": "1.0.0",
        "stage_package_id": "pkg_m4_" + PLACEHOLDER32,
        "artifact_revision_id": _rev("1"),
        "stage": "m4",
        "status": "sealed",
        "payload": {
            "candidate_set_revision_id": _rev("b"),
            "corpus_stage_package_revision_id": m3_pkg_rev,
            "spans_revision_id": spans_rev,
            "technique_profile_revision_id": profile_rev,
            "gate_profile": "thin_no_model",
            "span_layer": "structural",
            "cross_model": "not_evaluated",
            "term_layering": "verify_only",
            "content_status_counts": dict(counts),
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": PROCESSING_RUN_ID,
            "step_run_id": STEP_RUN_ID,
            "input_artifacts": inputs,
            "output_artifacts": [_art_ref("art_" + "0" * 31 + "a", out_rev, "candidate_package")],
            "counts": dict(counts),
            "content_sha256": content_sha256,
        },
        "validation": {"passed": True, "report_artifacts": []},
        "lineage": {
            "upstream_artifacts": [
                _art_ref(None, m3_pkg_rev, "stage_package", kind="stage_package",
                         stage_package_id="pkg_m3_" + PLACEHOLDER32),
                _art_ref("art_" + "0" * 31 + "4", spans_rev, "corpus_spans"),
                _art_ref("art_" + "0" * 31 + "5", profile_rev, "technique_profile"),
            ],
            "transformations": [{
                "operation": "extract_candidates",
                "step_run_id": STEP_RUN_ID,
                "configuration_artifact_revision_id": config_rev,
                "input_artifact_revision_ids": [
                    m3_pkg_rev, corpus_pkg_rev, spans_rev, profile_rev,
                    submission_revs[0], submission_revs[1], submission_revs[2],
                ],
                "output_artifact_revision_ids": [out_rev],
            }],
        },
        "logs": [],
        "failures": [],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="生成 mini_ed01 m4 期望 StagePackage")
    parser.add_argument("--out", default=str(FIXTURE), help="输出根目录（默认 fixture 目录）")
    args = parser.parse_args(argv)

    out_root = Path(args.out)
    cset_path = FIXTURE / "m4" / "candidate_set.yaml"
    if not cset_path.is_file():
        print("missing: %s" % cset_path, file=sys.stderr)
        return 3
    for name in INPUT_GOLDENS:
        if not (FIXTURE / "m4" / name).is_file():
            print("missing: %s" % (FIXTURE / "m4" / name), file=sys.stderr)
            return 3

    candidate_bytes = cset_path.read_bytes()
    candidate = json.loads(candidate_bytes.decode("utf-8"))
    package = build_package(candidate_bytes, candidate["counts"])

    target_dir = out_root / "expected"
    target_dir.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(package, allow_unicode=True, sort_keys=False, default_flow_style=False)
    (target_dir / "m4.stage_package.yaml").write_bytes(text.encode("utf-8"))
    print("wrote %s" % (target_dir / "m4.stage_package.yaml"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
