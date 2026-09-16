"""M1 来源校验与文件读取模块。

实现 load_source（来源元数据校验）与 read_source_files（原始文件读取与统一 UTF-8 编码）。
"""

import copy
import hashlib
from pathlib import Path
import re

from .errors import IntakeRefused, SourceAssetMissing

# 必填键集合与可选键集合（§2.1、§9.19 第 85 条）
REQUIRED_KEYS = (
    "source_id",
    "work_title",
    "edition_note",
    "technique_id",
    "rights_status",
    "release_policy",
    "edition_part",
    "source_site",
    "source_url",
    "file_sha256",
    "pages",
)

OPTIONAL_KEYS = (
    "repo_commit",
    "yaml_metadata",
)

ALLOWED_KEYS = set(REQUIRED_KEYS) | set(OPTIONAL_KEYS)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_PAGE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def load_source(data: dict) -> dict:
    """校验并加载来源申报件字典，返回固定键序的新字典（不修改入参）。

    参数：
        data：来源申报数据字典。

    返回：
        按固定键序排列的新字典。

    异常：
        IntakeRefused(code="SCH_001")：缺少必填键或入参非字典。
        IntakeRefused(code="SCH_002")：出现表外键或字段格式不合法。
    """
    if not isinstance(data, dict):
        raise IntakeRefused("来源申报数据必须为字典", code="SCH_001")

    # 1. 必填键检查
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise IntakeRefused("缺少必填键: %s" % (missing,), code="SCH_001")

    # 2. 表外键检查
    extra = [k for k in data if k not in ALLOWED_KEYS]
    if extra:
        raise IntakeRefused("出现表外键: %s" % (extra,), code="SCH_002")

    # 3. 字段值格式校验
    if not isinstance(data["source_id"], str) or not data["source_id"].strip():
        raise IntakeRefused("source_id 必须为非空字符串", code="SCH_002")

    if not isinstance(data["work_title"], str) or not data["work_title"].strip():
        raise IntakeRefused("work_title 必须为非空字符串", code="SCH_002")

    if not isinstance(data["edition_note"], str):
        raise IntakeRefused("edition_note 必须为字符串", code="SCH_002")

    if not isinstance(data["technique_id"], str) or not data["technique_id"].strip():
        raise IntakeRefused("technique_id 必须为非空字符串", code="SCH_002")

    if not isinstance(data["rights_status"], str) or not data["rights_status"].strip():
        raise IntakeRefused("rights_status 必须为非空字符串", code="SCH_002")

    if not isinstance(data["release_policy"], str) or not data["release_policy"].strip():
        raise IntakeRefused("release_policy 必须为非空字符串", code="SCH_002")

    # source_site：非空 str
    if not isinstance(data["source_site"], str) or not data["source_site"].strip():
        raise IntakeRefused("source_site 必须为非空字符串", code="SCH_002")

    # source_url：以 http:// 或 https:// 开头
    if not isinstance(data["source_url"], str) or not (
        data["source_url"].startswith("http://") or data["source_url"].startswith("https://")
    ):
        raise IntakeRefused("source_url 必须以 http:// 或 https:// 开头", code="SCH_002")

    # file_sha256：匹配 ^[0-9a-f]{64}$
    if not isinstance(data["file_sha256"], str) or not _HEX64_RE.match(data["file_sha256"]):
        raise IntakeRefused("file_sha256 必须为 64 位小写十六进制字符串", code="SCH_002")

    # pages：非空 list，每项匹配 ^[a-zA-Z0-9_-]+$，无重复
    pages = data["pages"]
    if not isinstance(pages, list) or len(pages) == 0:
        raise IntakeRefused("pages 必须为非空列表", code="SCH_002")

    seen_pages = set()
    for p in pages:
        if not isinstance(p, str) or not _PAGE_ID_RE.match(p):
            raise IntakeRefused("pages 元素非法: %r" % (p,), code="SCH_002")
        if p in seen_pages:
            raise IntakeRefused("pages 包含重复项: %r" % (p,), code="SCH_002")
        seen_pages.add(p)

    # edition_part：键集合 == {artifact_id, label, pages}；artifact_id 非空 str；label 非空 str
    ed_part = data["edition_part"]
    if not isinstance(ed_part, dict):
        raise IntakeRefused("edition_part 必须为字典", code="SCH_002")
    if set(ed_part.keys()) != {"artifact_id", "label", "pages"}:
        raise IntakeRefused("edition_part 键集合必须为 {artifact_id, label, pages}", code="SCH_002")
    if not isinstance(ed_part["artifact_id"], str) or not ed_part["artifact_id"].strip():
        raise IntakeRefused("edition_part.artifact_id 必须为非空字符串", code="SCH_002")
    if not isinstance(ed_part["label"], str) or not ed_part["label"].strip():
        raise IntakeRefused("edition_part.label 必须为非空字符串", code="SCH_002")
    if not isinstance(ed_part["pages"], list):
        raise IntakeRefused("edition_part.pages 必须为列表", code="SCH_002")

    # 可选字段：repo_commit, yaml_metadata（缺省为 None）
    repo_commit = data.get("repo_commit", None)
    if repo_commit is not None and not isinstance(repo_commit, str):
        raise IntakeRefused("repo_commit 必须为字符串或 None", code="SCH_002")

    yaml_metadata = data.get("yaml_metadata", None)

    # 按固定键序重建新 dict（13 个键）
    return {
        "source_id": data["source_id"],
        "work_title": data["work_title"],
        "edition_note": data["edition_note"],
        "technique_id": data["technique_id"],
        "rights_status": data["rights_status"],
        "release_policy": data["release_policy"],
        "edition_part": {
            "artifact_id": ed_part["artifact_id"],
            "label": ed_part["label"],
            "pages": list(ed_part["pages"]),
        },
        "source_site": data["source_site"],
        "source_url": data["source_url"],
        "file_sha256": data["file_sha256"],
        "pages": list(pages),
        "repo_commit": repo_commit,
        "yaml_metadata": copy.deepcopy(yaml_metadata),
    }


def read_source_files(source_dir: Path | str, pages: list[str]) -> list[dict]:
    """读取指定目录下的电子文本源文件，并统一转换为 UTF-8 编码字节。

    参数：
        source_dir：来源文件所在目录路径。
        pages：页名/文件名 stem 列表。

    返回：
        文件对象列表，每项形如：
        {"page": str, "path_ref": str, "data": bytes,
         "sha256": str, "normalized_sha256": str, "original_encoding": str, "size": int}

        `data`：归一化（统一 UTF-8）后的字节，即冻结进 raw_text 的内容；
        `sha256`：**磁盘原始文件字节**的 SHA-256，与 source_info.file_sha256 同源，
                  使追踪链闭合到下载物（G7-RULINGS 第 94 条 D4）；
        `normalized_sha256`：归一化后字节的 SHA-256，使追踪链闭合到 RawText；
        `original_encoding`：探测到的原编码，`utf-8-sig`（带 BOM）／`utf-8`／`gb18030`；
        `size`：归一化后字节长度。

    异常：
        SourceAssetMissing：目录不存在或文件缺失时抛出。
        IntakeRefused(code="SCH_002")：文件既不能按 UTF-8 也不能按 GB18030 解码时抛出。
    """
    sdir = Path(source_dir)
    if not sdir.is_dir():
        raise SourceAssetMissing([str(sdir)])

    missing_paths = []
    found_files = []

    for page in pages:
        exact_path = sdir / page
        if exact_path.is_file():
            found_files.append((page, exact_path))
            continue

        # 若无精确匹配，尝试在目录中寻找 stem 匹配的文件（如 page.txt、page.md）
        matched = [p for p in sdir.iterdir() if p.is_file() and p.stem == page]
        if matched:
            found_files.append((page, sorted(matched)[0]))
        else:
            missing_paths.append(str(exact_path))

    if missing_paths:
        raise SourceAssetMissing(missing_paths)

    results = []
    for page, file_path in found_files:
        raw_bytes = file_path.read_bytes()
        # 磁盘原始文件字节的哈希：追踪链闭合到「当初下载的就是这个文件」
        raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()

        # 编码检测与统一 UTF-8 编码
        if raw_bytes.startswith(b"\xef\xbb\xbf"):
            # 带 UTF-8 BOM，去除 BOM
            text = raw_bytes[3:].decode("utf-8")
            norm_bytes = text.encode("utf-8")
            original_encoding = "utf-8-sig"
        else:
            try:
                text = raw_bytes.decode("utf-8")
                norm_bytes = text.encode("utf-8")
                original_encoding = "utf-8"
            except UnicodeDecodeError:
                try:
                    text = raw_bytes.decode("gb18030")
                    norm_bytes = text.encode("utf-8")
                    original_encoding = "gb18030"
                except UnicodeDecodeError as exc:
                    raise IntakeRefused("文件 %s 无法按 UTF-8/GB18030 解码" % (file_path,), code="SCH_002") from exc

        path_ref = str(file_path.relative_to(sdir))
        results.append({
            "page": page,
            "path_ref": path_ref,
            "data": norm_bytes,
            "sha256": raw_sha256,
            "normalized_sha256": hashlib.sha256(norm_bytes).hexdigest(),
            "original_encoding": original_encoding,
            "size": len(norm_bytes),
        })

    return results
