"""M1 清单构建纯函数模块。

实现 build_source_manifest 与 manifest_bytes。
"""

import copy

from . import M1_TOOL, M1_TOOL_VERSION
from .serialize import dump_manifest_yaml


def build_source_manifest(source_info: dict, files: list[dict]) -> dict:
    """构建 source_manifest 字典（纯函数）。

    顶层包含 11 个键，严格按固定键序排列；
    source_assets[] 包含 12 个键，严格按固定键序排列；
    顶层不含 source_sites。

    参数：
        source_info：经校验的来源信息字典。
        files：来源文件对象列表。

    返回：
        符合契约规范的 source_manifest 字典。
    """
    source_assets = []
    for f in files:
        page = f["page"]
        path_ref = f.get("path_ref", page)
        sha256 = f["sha256"]
        size = f["size"]

        asset = {
            "page": page,
            "path_ref": path_ref,
            "sha256": sha256,
            "size": size,
            "width": None,
            "height": None,
            "object_store": "local",
            "in_git": False,
            "yaml_metadata": copy.deepcopy(source_info.get("yaml_metadata", None)),
            "source_site": source_info["source_site"],
            "source_url": source_info["source_url"],
            "repo_commit": source_info.get("repo_commit", None),
        }
        source_assets.append(asset)

    inputs = [asset["path_ref"] for asset in source_assets]
    conversion = {
        "tool": M1_TOOL,
        "tool_version": M1_TOOL_VERSION,
        "inputs": inputs,
        "note": "M1 电子文本入库；不做清洗（§9）",
    }

    manifest = {
        "source_id": source_info["source_id"],
        "work_title": source_info["work_title"],
        "edition_note": source_info["edition_note"],
        "technique_id": source_info["technique_id"],
        "rights_status": source_info["rights_status"],
        "release_policy": source_info["release_policy"],
        "edition_part": copy.deepcopy(source_info["edition_part"]),
        "source_assets": source_assets,
        "files": [],
        "conversion": conversion,
        "content_status": "machine_extracted",
    }
    return manifest


def manifest_bytes(source_info: dict, files: list[dict]) -> bytes:
    """构建 source_manifest 并序列化为确定性 YAML 字节。

    参数：
        source_info：经校验的来源信息字典。
        files：来源文件对象列表。

    返回：
        确定性 YAML 字节序列（UTF-8 编码）。
    """
    manifest = build_source_manifest(source_info, files)
    return dump_manifest_yaml(manifest)
