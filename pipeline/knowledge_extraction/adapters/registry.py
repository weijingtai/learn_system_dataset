"""Contract Registry Adapter：由 canon 目录生成运行级 ``technique_profile``（D-05）。

只读 canon 目录（``pipeline/schemas/shared/canon/*.yaml``）；流派闭集本批不冻结
（``schools: []``），任何 ``school_id`` 一律由装配阶段 REF_001 拒收。
"""

import hashlib
from pathlib import Path

import yaml

from pipeline.ledger import ids

from .. import CANDIDATE_SCHEMA_VERSION, M4_TOOL, M4_TOOL_VERSION
from ..errors import ExtractionRefused
from ..serialize import canonical_json


def build_technique_profile(*, technique_id, canon_dir):
    """读 canon 目录生成运行级 ``technique_profile`` 的 canonical JSON 字节。"""
    root = Path(canon_dir)
    files = []
    concepts = []
    seen = set()
    for path in sorted(root.glob("*.yaml")):
        data = path.read_bytes()
        files.append({"name": path.name, "sha256": hashlib.sha256(data).hexdigest()})
        doc = yaml.safe_load(data.decode("utf-8"))
        entries = doc.get("concepts") or []
        if len(entries) != doc.get("closed_set_size"):
            raise ExtractionRefused(
                "canon 文件 %s 的 concepts 数 %d != closed_set_size %r"
                % (path.name, len(entries), doc.get("closed_set_size")),
                code="SCH_002",
            )
        for entry in entries:
            concept_id = entry["concept_id"]
            ids.validate("shared_concept_id", concept_id)  # 非法 → InvalidIdentifier(ID_001)
            if concept_id in seen:
                raise ExtractionRefused("concept_id 重复: %s" % concept_id, code="ID_002")
            seen.add(concept_id)
            concepts.append(
                {
                    "concept_id": concept_id,
                    "surface": entry["surface"],
                    "aliases": list(entry.get("aliases", [])),
                    "domain": entry["domain"],
                    "rev": entry["rev"],
                }
            )
    profile = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "technique_id": technique_id,
        "canon": {
            "files": files,
            "concepts": sorted(concepts, key=lambda row: row["concept_id"]),
        },
        "homographs": [],
        "glossary": [],
        "schools": [],
    }
    return canonical_json(profile)


def register_technique_profile(service, processing_run_id, *, technique_id, canon_dir):
    """写入并封存运行级 ``technique_profile`` 修订，返回其修订号。"""
    data = build_technique_profile(technique_id=technique_id, canon_dir=canon_dir)
    _, revision_id = service.put_run_artifact(
        processing_run_id,
        "technique_profile",
        data,
        producer_module=M4_TOOL + ".adapters.registry",
        producer_version=M4_TOOL_VERSION,
    )
    return revision_id
