"""测试辅助工具模块（只供测试，标 synthetic_fixture: true）。"""

import os
import tempfile
from pathlib import Path

# 测试环境临时基目录（synthetic_fixture: true）
_FIXTURE_TMP_DIR = None


def _get_tmp_dir() -> Path:
    global _FIXTURE_TMP_DIR
    if _FIXTURE_TMP_DIR is None or not Path(_FIXTURE_TMP_DIR).exists():
        _FIXTURE_TMP_DIR = tempfile.mkdtemp(prefix="intake_fixture_")
    return Path(_FIXTURE_TMP_DIR)


def make_text_file(name: str, content: str | bytes, encoding: str = "utf-8", target_dir: Path | str | None = None) -> Path:
    """写入临时文件，返回路径（synthetic_fixture: true）。"""
    base_dir = Path(target_dir) if target_dir is not None else _get_tmp_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    file_path = base_dir / name
    if isinstance(content, str):
        file_path.write_text(content, encoding=encoding)
    else:
        file_path.write_bytes(content)
    return file_path


def fixture_source() -> dict:
    """返回合法 source_info（乾元秘旨片段，synthetic_fixture: true）。"""
    return {
        "source_id": "src_qianyuan_ed01",
        "work_title": "乾元秘旨",
        "edition_note": "殆知阁电子文本",
        "technique_id": "qizheng",
        "rights_status": "站方声明免费下载、未附许可证",
        "release_policy": "reference_and_hash_only",
        "edition_part": {
            "artifact_id": "art_000000000000000000000000000000e1",
            "label": "卷一·太极图说",
            "pages": ["page_001"],
        },
        "source_site": "daizhige.org",
        "source_url": "https://daizhige.org/qianyuan/01.txt",
        "file_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "pages": ["page_001"],
    }
