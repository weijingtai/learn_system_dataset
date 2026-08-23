"""gujiorc 路径与环境管理。

设计目标：同一套代码在「本地」和「Google Colab」都能运行。
用环境变量指定数据位置，不硬编码任何绝对路径，保证本地 → Colab 无缝移植。

输入源 / 输出目标可自由指定（Drive 书目录 / 结果目录分离）：

  OCR_SOURCE_DIR   原书图片根目录（默认：未设置 → OCR_ROOT/books）
  OCR_OUTPUT_DIR   结果存储根目录（JSON/SQLite/生僻字/截图/audit 全落这里）
                   默认：未设置 → OCR_ROOT
  OCR_ROOT         兼容旧单根用法。当 OCR_SOURCE/OUTPUT 未设时作为两者兜底。
                   本地默认：当前目录的 ./data_work
                   Colab: OCR_ROOT=/content/drive/MyDrive/ocr_work

目录结构（本地/Colab 同构，仅根不同）：
  {输出根}/books/          原图（OCR_SOURCE_DIR 未指定时从这里读）
  {输出根}/data/*.json     每页识别结果（git可diff，主档案）
  {输出根}/book.db         统一 SQLite 主存档库（可自由指定路径，见 library.py）
  {输出根}/index.db        全字索引（gitignore，兼容旧用法）
  {输出根}/rare/           生僻字清单 + glyph_groups.json + report.md
  {输出根}/glyph_samples/  生僻字截图
  {输出根}/logs/            进度心跳 + audit.jsonl
"""
from __future__ import annotations

import os
from pathlib import Path


def _default_root() -> Path:
    """未设 OCR_ROOT 时：包上级目录下的 data_work/。"""
    here = Path(__file__).resolve().parent
    # src/gujiorc/core/  -> 项目根
    pkg_root = here.parents[2]
    return pkg_root / "data_work"


def get_root() -> Path:
    """返回兼容旧单根用法的工作根（OCR_ROOT，未设则 data_work/）。

    当 OCR_OUTPUT_DIR 已设置时，get_root() 返回输出根（即设了就用输出根
    作为历史 get_root() 的上游根；否则再用 OCR_ROOT）。
    """
    out = os.environ.get("OCR_OUTPUT_DIR", "")
    if out:
        return Path(out)
    root = os.environ.get("OCR_ROOT", "")
    if root:
        return Path(root)
    return _default_root()


def get_source_dir() -> Path:
    """返回原书图片根目录（OCR_SOURCE_DIR，未设 → get_root()/books）。"""
    src = os.environ.get("OCR_SOURCE_DIR", "")
    if src:
        return Path(src)
    return Path(get_root()) / "books"


def get_output_dir() -> Path:
    """返回结果存储根目录（OCR_OUTPUT_DIR，未设 → get_root()）。"""
    out = os.environ.get("OCR_OUTPUT_DIR", "")
    if out:
        return Path(out)
    return Path(get_root())


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
    """创建并返回标准目录结构。返回 {key: Path}。

    books → get_source_dir()（原书来源，可自由指定 Drive 目录）
    其余 → get_output_dir()（结果存储，JSON/SQLite/生僻字/截图/日志）
    """
    out = get_output_dir()
    cache_base = out / ".cache"
    dirs = {
        "root": get_root(),               # 兼容旧 get_root()
        "output": out,                    # 结果存储根
        "books": get_source_dir(),        # 原图（自由指定来源）
        "data": out / "data",             # 每页识别结果 JSON（主档案）
        "rare": out / "rare",             # 生僻字清单
        "glyph_samples": out / "glyph_samples",  # 生僻字截图
        "cache": cache_base,              # 临时中间产物
        "logs": out / "logs",             # 进度日志 + audit
    }
    for d in dict.fromkeys(dirs.values()):
        d.mkdir(parents=True, exist_ok=True)
    return dirs