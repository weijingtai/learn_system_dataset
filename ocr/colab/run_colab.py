#!/usr/bin/env python3
"""Colab 一键入口：识别 + 生僻字圈划 + 全字索引 + 进度汇报。

在 Colab 里通过 Google Drive 持久化，断点续传。

用法（Colab notebook cell）：
    # 1. 挂载 Drive
    from google.colab import drive
    drive.mount('/content/drive')

    # 2. 设置工作根（持久盘）
    import os
    os.environ['OCR_ROOT'] = '/content/drive/MyDrive/ocr_work'

    # 3. 上传本脚本后运行
    !python ocr/scripts/ocr_workbench.py --root "$OCR_ROOT" run /content/drive/MyDrive/ocr_work/books

本模块提供 Colab 专属封装：
- ensure_drive()：检查/提示挂载 Drive
- 识别完成后自动重建索引 + 生僻字清单
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 将 repo/src 加入路径
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))


def check_drive(ocr_root: str | None = None) -> str:
    """校验 OCR_ROOT 是否可用（Colab 挂载 Drive 后）。"""
    if ocr_root is None:
        ocr_root = os.environ.get("OCR_ROOT", "/content/drive/MyDrive/ocr_work")
    p = Path(ocr_root)
    if not p.exists():
        print(f"⚠️  {ocr_root} 不存在，请先挂载 Drive 并创建目录")
        print("    from google.colab import drive; drive.mount('/content/drive')")
        return ocr_root
    # 写探测文件
    probe = p / ".colab_ok"
    probe.touch()
    print(f"✅ Drive 可用: {ocr_root}")
    return ocr_root


def full_pipeline(books_dir: str, ocr_root: str | None = None,
                  gap: float = 40, conf: float = 0.6, report_every: float = 5.0):
    """一键全流程：识别 → 生僻字圈划 → 索引 → 清单。

    先跑 run（识别+索引+生僻字标记），再跑 rare（红框标记图+清单）。
    """
    if ocr_root is None:
        ocr_root = os.environ.get("OCR_ROOT", "/content/drive/MyDrive/ocr_work")
    os.environ["OCR_ROOT"] = ocr_root
    check_drive(ocr_root)

    from gujiorc.ocr.pipeline import image_to_page
    from gujiorc.core.progress import ProgressReporter
    from gujiorc.core.storage import save_page_json, save_rare_list
    from gujiorc.index.fulltext import CharIndex
    from gujiorc.rare.detector import detect_rare_chars, build_common_set, build_rare_list
    from gujiorc.rare.crop import crop_all_rare
    from gujiorc.core.paths import get_root, ensure_struct

    # 收集图片
    book_path = Path(books_dir)
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
    files = sorted(p for p in book_path.rglob("*") if p.suffix.lower() in exts)
    if not files:
        print(f"未找到图片于 {book_path}")
        return

    common = build_common_set(table_path=str(Path(ocr_root) / "data" / "common_hanzi.txt"))
    prog = ProgressReporter(total=len(files), report_every=report_every,
                            progress_path=str(Path(ocr_root) / "logs" / "progress.json"))
    idx = CharIndex()

    rare_all = []
    for i, f in enumerate(files):
        page = f"page_{i + 1:03d}"
        try:
            pr = image_to_page(str(f), page=page, image_path=str(f),
                               gap_thresh=gap, conf_thresh=conf)
            detect_rare_chars(pr, common, conf_thresh=conf)
            save_page_json(pr)
            idx.rebuild_from_page(pr)
            # 生僻字截图（每字样本）
            crop_all_rare(str(f), pr)
            rare_all.append(pr)
            prog.tick(page)
        except Exception as e:
            prog.add_error(page, str(e))
            prog.tick(page + " (错误)")

    prog.finish()

    # 生僻字清单
    rare_list = build_rare_list(rare_all)
    save_rare_list(rare_list)
    print(f"\n生僻字共 {len(rare_list)} 个")
    idx.close()


if __name__ == "__main__":
    # 直接运行：python run_colab.py <books_dir>
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("books_dir")
    ap.add_argument("--root", default=os.environ.get("OCR_ROOT"))
    ap.add_argument("--gap", type=float, default=40)
    ap.add_argument("--conf", type=float, default=0.6)
    a = ap.parse_args()
    full_pipeline(a.books_dir, a.root, a.gap, a.conf)