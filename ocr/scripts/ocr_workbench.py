#!/usr/bin/env python3
"""gujiorc 命令行入口 — 全部功能，本地 + Colab 通用。

命令：
  run <image/dir>       识别整本书/单图 → 输出 PageResult JSON + 生僻字标记图 + 全字索引
  rare <image/dir>      生僻字圈划（红框标记图）+ 生僻字清单
  index <book_root>     从已有 JSON 重建全字索引
  query <char>          查某字全书所有出现位置
  dups [min_count]      重复字统计表
  groups                生僻字分组清单（glyph_groups.json）

全局：
  --root PATH           OCR_ROOT（默认：包上级 data_work/）
  --gap THRESH          区块切分阈值（默认 40）
兼容 Colab：设 OCR_ROOT=/content/drive/MyDrive/ocr_work 后同样命令生效。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# 保证可从 scripts/ 直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def _img_files(target: Path) -> list[Path]:
    """收集要识别的图片文件。target 可以是文件或目录。"""
    if target.is_file():
        return [target]
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
    files = sorted(p for p in target.rglob("*") if p.suffix.lower() in exts)
    return files


def cmd_run(args):
    from gujiorc.core.paths import get_root
    from gujiorc.core.progress import ProgressReporter
    from gujiorc.ocr.pipeline import image_to_page
    from gujiorc.ocr.segment import segment_page_chars
    from gujiorc.core.storage import save_page_json
    from gujiorc.index.fulltext import CharIndex
    from gujiorc.rare.detector import detect_rare_chars, build_common_set

    target = Path(args.image)
    files = _img_files(target)
    if not files:
        print(f"未找到图片于 {target}")
        return 1
    print(f"共 {len(files)} 张图待识别")

    common_set = build_common_set(table_path=os.path.join(get_root(), "data", "common_hanzi.txt"))
    progress = ProgressReporter(total=len(files), report_every=args.report_every)
    idx = CharIndex()

    for i, f in enumerate(files):
        page = f"page_{i + 1:03d}"
        try:
            page_result = image_to_page(
                str(f), page=page,
                image_path=str(f),
                gap_thresh=args.gap,
                conf_thresh=args.conf,
            )
            # 单字切分（PLANS M2）：整行块 → 单字框
            if args.segment:
                n_chars = segment_page_chars(str(f), page_result)
                print(f"  [{page}] 单字切分 {n_chars} 字", file=sys.stderr)
            # 生僻字判定（按单字精度）
            detect_rare_chars(page_result, common_set, conf_thresh=args.conf)
            # 存 JSON
            save_page_json(page_result)
            # 索引
            idx.rebuild_from_page(page_result)
            # 生僻字截图（红框标记图单独由 rare 命令做）
            progress.tick(current=page)
        except Exception as e:
            progress.add_error(page, str(e))
            progress.tick(current=f"{page} (错误)")

    progress.finish()
    idx.close()
    return 0


def cmd_rare(args):
    """生僻字圈划：原图叠加红框 + 生僻字清单 JSON。"""
    from PIL import Image, ImageDraw, ImageFont
    from gujiorc.core.paths import get_root, ensure_struct
    from gujiorc.core.storage import load_page_json, save_rare_list
    from gujiorc.rare.detector import build_common_set, detect_rare_chars, build_rare_list

    target = Path(args.image)
    files = _img_files(target)
    if not files:
        print(f"未找到图片于 {target}")
        return 1

    common_set = build_common_set(table_path=os.path.join(get_root(), "data", "common_hanzi.txt"))
    font_path = args.font or "/System/Library/Fonts/STHeiti Medium.ttc"
    font = ImageFont.truetype(font_path, 22) if os.path.exists(font_path) else None

    struct = ensure_struct()
    all_pages = []
    for i, img_path in enumerate(files):
        page = f"page_{i + 1:03d}"
        # 重新识别（若已有 JSON 用 JSON，否则识别）
        pr = load_page_json(page)
        if pr is None:
            from gujiorc.ocr.pipeline import image_to_page
            pr = image_to_page(str(img_path), page=page, image_path=str(img_path),
                               gap_thresh=args.gap, conf_thresh=args.conf)
            detect_rare_chars(pr, common_set)
            from gujiorc.core.storage import save_page_json
            save_page_json(pr)
        all_pages.append(pr)

        # 画红框标记
        img = Image.open(img_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        for ch in pr.chars:
            if not ch.is_rare:
                continue
            b = ch.box
            # 生僻字红框；低置信度黄框
            color = (255, 0, 0) if ch.rare_reason == "not_in_common_set" else (255, 200, 0)
            draw.rectangle([b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]],
                           outline=color, width=3)
            # 标注字（若有）
            if ch.char and font:
                from gujiorc.rare.detector import parse_char
                label = "".join(dict.fromkeys(parse_char(ch.char)))
                if label:
                    draw.text((b["x"], max(0, b["y"] - 26)), label, fill=color, font=font)

        out = ensure_struct()["data"] / f"{page}.marked.png"
        img.save(out)
        print(f"  标记图: {out}")

    # 生僻字清单
    rare_list = build_rare_list(all_pages)
    save_rare_list(rare_list)
    print(f"\n生僻字共 {len(rare_list)} 个:")
    for r in rare_list:
        print(f"  {r.char}  ×{r.count}  {[p['page'] for p in r.positions]}")
    return 0


def cmd_index(args):
    """从已有 page JSON 重建全字索引。"""
    from gujiorc.core.paths import get_root
    from gujiorc.core.storage import load_page_json
    from gujiorc.index.fulltext import CharIndex
    import json as _json

    root = Path(get_root()) / "data"
    idx = CharIndex()
    count = 0
    for p in root.glob("page_*.json"):
        page = load_page_json(p.stem)
        if page:
            idx.rebuild_from_page(page)
            count += 1
    idx.close()
    print(f"已重建索引，共 {count} 页")
    return 0


def cmd_query(args):
    from gujiorc.index.fulltext import CharIndex
    idx = CharIndex()
    rows = idx.query_char(args.char)
    idx.close()
    if not rows:
        print(f"未找到字符「{args.char}」")
        return 0
    print(f"「{args.char}」出现 {len(rows)} 次:")
    for r in rows:
        box = json.loads(r["box"])
        print(f"  {r['page']}  {r['char_id']}  坐标({box['x']:.0f},{box['y']:.0f})  status={r['status']}")
    return 0


def cmd_dups(args):
    from gujiorc.index.fulltext import CharIndex
    idx = CharIndex()
    dups = idx.duplicates(args.min_count)
    idx.close()
    if not dups:
        print("无重复字")
        return 0
    print(f"{'字':<4} {'次数':<5} 位置")
    for d in dups:
        print(f"{d['char']:<4} {d['cnt']:<5} {d['positions'][:80]}")
    return 0


def cmd_groups(args):
    from gujiorc.rare.groups import load_groups
    groups = load_groups()
    if not groups:
        print("暂无分组")
        return 0
    for g in groups:
        print(f"[{g.id}] {g.name}  status={g.status}  样本数={len(g.samples)}  "
              f"char={g.char or '未定义'}  font={g.font or '-'}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="古籍 OCR 工作台 (gujiorc)")
    parser.add_argument("--root", help="OCR_ROOT（数据根目录）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="识别整本书/单图")
    p_run.add_argument("image", help="图片文件或目录")
    p_run.add_argument("--gap", type=float, default=40)
    p_run.add_argument("--conf", type=float, default=0.6)
    p_run.add_argument("--segment", action="store_true", help="单字切分（竖排列→单字框）")
    p_run.add_argument("--report-every", type=float, default=5.0)
    p_run.set_defaults(func=cmd_run)

    p_rare = sub.add_parser("rare", help="生僻字圈划+清单")
    p_rare.add_argument("image", help="图片文件或目录")
    p_rare.add_argument("--gap", type=float, default=40)
    p_rare.add_argument("--conf", type=float, default=0.6)
    p_rare.add_argument("--font", default=None, help="中文字体路径")
    p_rare.set_defaults(func=cmd_rare)

    p_idx = sub.add_parser("index", help="重建全字索引")
    p_idx.set_defaults(func=cmd_index)

    p_q = sub.add_parser("query", help="查某字全书位置")
    p_q.add_argument("char")
    p_q.set_defaults(func=cmd_query)

    p_d = sub.add_parser("dups", help="重复字统计")
    p_d.add_argument("--min-count", type=int, default=2)
    p_d.set_defaults(func=cmd_dups)

    p_g = sub.add_parser("groups", help="生僻字分组清单")
    p_g.set_defaults(func=cmd_groups)

    args = parser.parse_args()
    if args.root:
        os.environ["OCR_ROOT"] = args.root
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())