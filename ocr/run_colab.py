#!/usr/bin/env python3
"""Colab 一键古籍 OCR 全流程入口。

在 Google Colab 里运行即可完成：
  1. 识别（PaddleOCR 竖排/横排）
  2. 单字切分（一字一框）
  3. 生僻字判定 + 圈框标记图
  4. 全字索引 + 重复字统计
  5. 导入 SQLite 数据库（book.db）

------------------------------------------------------------------
★ 关键：怎么把书告诉程序
------------------------------------------------------------------
书籍位置用一个参数指定（图片文件 / PDF / 目录均可）。两种方式任选：

  A) 命令行参数（最直接）：
     !python run_colab.py '/content/drive/MyDrive/ocr_work/books/qizhengsiyu/《新刻琴堂五星》明刻本.pdf'

  B) 环境变量 OCR_BOOK（不改代码）：
     !OCR_BOOK='/content/drive/MyDrive/ocr_work/books/qizhengsiyu/《新刻琴堂五星》明刻本.pdf' python run_colab.py

书可以是：
  · .pdf 文件      → 程序先用 PyMuPDF 自动拆成图片再 OCR
  · 图片文件       → 单页图直接识别
  · 目录           → 递归收集目录下所有 png/jpg/jpeg/bmp/tif/tiff 识别

小括号提醒：OCR 识别的是「图片」，不是 PDF。若你给 PDF，
程序会在 books/ 下自动生成同名 _pages/*.png 再识别。

数据目录约定：
  books/               原书（也可用 OCR_SOURCE_DIR 指定）
  data/*.json          每页识别结果（JSON 主档案）
  glyph_samples/       生僻字标记图
  rare/                生僻字清单 + report.md
  book.db              SQLite 数据库（统一存档）
  index.db             全字索引
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# 项目根加入 sys.path
_HERE = Path(__file__).resolve().parent
for _r in (_HERE, _HERE / "scripts"):
    if (_r / "src").exists():
        sys.path.insert(0, str(_r / "src"))
        break

from gujiorc.core.paths import get_source_dir, get_output_dir, ensure_struct  # noqa: E402


def pdf_to_images(pdf: Path) -> list[Path]:
    """用 PyMuPDF 把 PDF 每页转成 PNG，输出到 同目录/{PDF名}_pages/*.png。"""
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        print(f"✗ 需要 PyMuPDF 才能解析 PDF。先装: !pip install -q pymupdf （{e}）")
        sys.exit(1)
    out_dir = pdf.parent / f"{pdf.stem}_pages"
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf))
    print(f"PDF 共 {doc.page_count} 页，正在拆分为图片 → {out_dir} ...", flush=True)
    imgs = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=200)  # 200dpi 保真竖排小字
        out = out_dir / f"page_{i + 1:03d}.png"
        pix.save(str(out))
        imgs.append(out)
    doc.close()
    print(f"✅ 已生成 {len(imgs)} 张页图", flush=True)
    return imgs


def resolve_book(target: str | Path) -> list[Path]:
    """把书位置解析成「要识别的图片文件列表」。支持 PDF/图片/目录。"""
    target = Path(target)
    if not target.exists():
        print(f"✗ 找不到书: {target}")
        print("  请确认路径正确（Colab 路径注意用绝对路径，含中文/空格要加引号）")
        sys.exit(1)
    if target.is_file():
        if target.suffix.lower() == ".pdf":
            return pdf_to_images(target)
        return [target]  # 单张图
    # 目录：递归收集图片
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
    imgs = sorted(p for p in target.rglob("*") if p.suffix.lower() in exts)
    if not imgs:
        print(f"✗ 目录 {target} 下没有图片。")
        sys.exit(1)
    return imgs


def _run(cmd: list[str]) -> int:
    print(f"\n===== {' '.join(cmd)} =====", flush=True)
    return subprocess.call(cmd, env=dict(os.environ, PYTHONPATH="src"))


def main() -> int:
    # 书的路径：命令行参数优先，其次 OCR_BOOK 环境变量
    if len(sys.argv) > 1 and sys.argv[1] and not sys.argv[1].startswith("-"):
        book_arg = sys.argv[1]
    else:
        book_arg = os.environ.get("OCR_BOOK", "")

    workbench = next(p for p in (_HERE / "scripts" / "ocr_workbench.py",
                                 _HERE / "ocr_workbench.py") if p.exists())
    struct = ensure_struct()
    src = get_source_dir()

    # 1) 解析书 → 图片列表
    if book_arg:
        images = resolve_book(book_arg)
    else:
        # 没给书路径 → 用 books/ 目录
        if not src.exists():
            print(f"✗ 未给书籍路径，且默认 'books/' 目录 {src} 不存在。")
            print("  用法: python run_colab.py '<书路径>'  （或用环境变量 OCR_BOOK）")
            sys.exit(1)
        images = sorted(p for p in src.rglob("*") if p.suffix.lower() in {".png",".jpg",".jpeg",".bmp",".tif",".tiff"})
        if not images:
            print(f"✗ books/ 目录 {src} 没有图片。")
            sys.exit(1)
    print(f"将识别 {len(images)} 张图", flush=True)

    # 2) 把图片拷到 books/（Colab 内存改 /content 也统一来源）——可选，
    #    这里不强制拷，直接识别列表里的原路径。但 rare 需要图片存在，
    #    图片 URL 已是真实路径，直接传给 CLI。

    images_root = str(Path(images[0]).parent)

    # 3) 识别 + 单字切分 + 全索引
    cmd = [sys.executable, str(workbench)]
    if _run(cmd + ["run", images_root, "--segment"]) != 0:
        return 1
    # 4) 生僻字圈框 + 标记图 + 清单
    if _run(cmd + ["rare", images_root]) != 0:
        return 1
    # 5) 质量报告
    _run(cmd + ["report", "--book", os.environ.get("OCR_BOOK_NAME", "")])
    # 6) 导入 SQLite
    _run(cmd + ["json2db", "--book", os.environ.get("OCR_BOOK_NAME", "book")])

    out = get_output_dir()
    print("\n✅ 全部完成!", flush=True)
    print(f"   JSON 识别结果 : {out / 'data'}", flush=True)
    print(f"   生僻字标记图  : {struct['glyph_samples']}", flush=True)
    print(f"   SQLite 数据库 : {out / 'book.db'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())