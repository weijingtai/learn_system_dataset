"""gujiorc 路径与环境管理。

设计目标：同一套代码在「本地」和「Google Colab」都能运行。
用环境变量 OCR_ROOT 指定工作根目录（数据、索引、结果都放这里），
不硬编码任何绝对路径，保证本地 → Colab 无缝移植。

本地默认:    OCR_ROOT 未设置 → 当前目录的 ./data_work
Colab 设置:  OCR_ROOT=/content/drive/MyDrive/ocr_work （挂载 Drive 后持久化）
"""
from __future__ import annotations

import os
from pathlib import Path


def get_root() -> Path:
    """返回工作根目录（OCR_ROOT）。"""
    root = os.environ.get("OCR_ROOT", "")
    if root:
        return Path(root)
    # 默认: 包上级目录下的 data_work/
    here = Path(__file__).resolve().parent
    # src/gujiorc/core/  -> 项目根
    pkg_root = here.parents[2]
    return pkg_root / "data_work"


def is_colab() -> bool:
    """是否运行在 Colab（检测环境变量 / 挂载点）。"""
    if os.environ.get("COLAB_GPU"):
        return True
    try:
        import IPython
        shell = IPython.get_ipython()
        return shell is not None and "google.colab" in str(shell.__class__)
    except Exception:
        return False


def ensure_struct() -> dict[str, Path]:
    """创建并返回标准目录结构。返回 {key: Path}。"""
    root = get_root()
    dirs = {
        "root": root,
        "books": root / "books",          # 原图
        "data": root / "data",            # 每页识别结果 JSON
        "rare": root / "rare",            # 生僻字清单
        "glyph_samples": root / "glyph_samples",  # 生僻字截图
        "cache": root / ".cache",         # 临时中间产物
        "logs": root / "logs",            # 进度日志
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs