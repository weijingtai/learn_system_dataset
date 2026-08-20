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

    common_set = build_common_set()
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

    common_set = build_common_set()
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


def cmd_fix(args):
    """改正识别错误/异体字（manual 映射）。保留 orig_char + 记录 mapping。

    用法：fix <page> <char_id|'all'> <new_char> [--from-char X]
    若指定 --from-char，则只改该页中 orig_char 或 char 等于 X 的框。
    """
    from gujiorc.core.storage import load_page_json, save_page_json

    pr = load_page_json(args.page)
    if pr is None:
        print(f"页面 {args.page} 不存在")
        return 1

    target_new = args.new_char
    from_char = args.from_char or ""
    count = 0
    matched_id = None if args.match == "all" else args.match

    for ch in pr.chars:
        # 触发条件：指定了id单改，或 from-char 匹配，或 all
        hit = False
        if matched_id:
            hit = (ch.id == matched_id)
        elif from_char:
            hit = (ch.orig_char == from_char or ch.char == from_char)
        elif args.match == "all":
            hit = True  # 全页改（慎用，通常需配合 from-char）

        if not hit:
            continue
        if ch.orig_char == target_new and ch.char == target_new:
            continue  # 已一致
        ch.set_char(target_new, mapping_source="manual")
        count += 1

    save_page_json(pr)
    print(f"✅ {args.page} 共改正 {count} 字 →「{target_new}」(orig_char 已保留，映射已记录)")
    try:
        from gujiorc.core.audit import log_event
        logged = 0
        for ch in pr.chars:
            if ch.mapping and ch.mapping.get("target") == target_new:
                log_event("fix", actor="cli", page=args.page, char_id=ch.id,
                          **{"from": ch.mapping.get("from", ""), "to": target_new, "source": "manual"})
                logged += 1
    except Exception:
        pass
    return 0


def cmd_show_char(args):
    """查看某页某字框的原始识别与映射信息。"""
    from gujiorc.core.storage import load_page_json

    pr = load_page_json(args.page)
    if pr is None:
        print(f"页面 {args.page} 不存在")
        return 1
    if args.char_id:
        target = [c for c in pr.chars if c.id == args.char_id]
    else:
        target = [c for c in pr.chars if c.orig_char == args.from_char or c.char == args.from_char]
    if not target:
        print("未找到匹配字框")
        return 0
    for c in target[:10]:
        m = c.mapping or {}
        print(f"  {c.id}  orig={c.orig_char!r}  char={c.char!r}  "
              f"从{m.get('from','-')}→{m.get('target','-')}[{m.get('source','-')}]  "
              f"rare={c.is_rare}")
    return 0


def cmd_export(args):
    """导出识别成果（JSON/TXT/TSV/transcript / 可选 corpus manifest）。"""
    from gujiorc.core.paths import get_root
    from gujiorc.core.report import load_all_pages
    from gujiorc.core.export import export_common, export_corpus
    from gujiorc.rare.groups import load_groups, resolve_char

    root = Path(get_root())
    pages = load_all_pages(root / "data")
    if not pages:
        print(f"无页面数据于 {root / 'data'}")
        return 1

    groups = load_groups()

    def gr(char_id: str):
        return next((g.char for g in groups if g.status == "defined" and g.char and char_id in g.samples), None)

    if args.corpus_out:
        for name in ("--work-title", "--technique-id"):
            if not getattr(args, name.replace("-", "_").replace("--", "")):
                print(f"corpus 模式需要 {name}")
                return 1
        out = export_corpus(
            pages,
            args.corpus_out,
            book=args.book,
            work_title=args.work_title,
            technique_id=args.technique_id,
            edition=args.edition,
            edition_note=args.edition_note or "",
            rights_status=args.rights_status or "public_domain",
            groups_resolve=gr,
        )
        print(f"📦 corpus 导出完成 → {args.corpus_out}")
        print(f"  manifest: {out['manifest']}")
        print(f"  transcript: {out['transcript']}")
        print(f"  未知字 {out['unknown']} 个已按 □ 导出")
        return 0

    out_dir = root / "export"
    fmts = tuple(args.formats.split(",")) if args.formats else ("json", "txt", "tsv", "transcript")
    outs = export_common(pages, out_dir, prefix=args.book or "book", groups_resolve=gr, formats=fmts)
    print(f"📦 导出完成 → {out_dir}")
    for fmt, p in outs.items():
        print(f"  {fmt}: {p}")
    return 0


def cmd_report(args):
    """生成 OCR 质量报告（M6_）。导出 report.md。"""
    from gujiorc.core.paths import get_root
    from gujiorc.core.report import load_all_pages, book_report, render_report_md

    root = Path(get_root())
    pages = load_all_pages(root / "data")
    if not pages:
        print(f"无页面数据于 {root / 'data'}")
        return 1
    report = book_report(pages)
    md = render_report_md(report, book=args.book)
    out_dir = root / "rare"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "report.md"
    out.write_text(md, encoding="utf-8")
    print(f"📄 质量报告已生成: {out}")
    print(md)
    return 0


def cmd_dict(args):
    """生僻字查询/拆解（R8/R9）：查读音/部首/笔画/释义。"""
    from gujiorc.rare.dictionary import query_rare
    from gujiorc.core.paths import get_root
    result = query_rare(args.char, data_dir=str(Path(get_root()) / "data" / "unihan"))
    print(f"字: {result.get('char')} ({result.get('unicode', '')})")
    for k, v in result.items():
        if k in ("char", "unicode"):
            continue
        print(f"  {k}: {v}")
    if not any(k in result for k in ("radical", "strokes", "reading", "definition", "name")):
        print("  （未找到读音/部首数据——可放置 Unihan 离线库增强，见 data/README.md）")
    return 0


def cmd_groups(args):
    """生僻字分组归并（M12）：展示/创建/添加/定义。"""
    from gujiorc.rare.groups import load_groups, save_groups, create_group, \
        add_samples, define_group, remove_samples

    groups = load_groups()

    if args.action == "list" or args.action is None:
        _print_groups(groups)
    elif args.action == "create":
        g = create_group(groups, args.name, args.samples or [], args.note or "")
        save_groups(groups)
        print(f"✅ 创建组 {g.id}「{g.name}」(样本 {len(g.samples)} 个)")
        try:
            from gujiorc.core.audit import log_event
            log_event("group_create", actor="cli", group_id=g.id, name=g.name or "")
        except Exception:
            pass
    elif args.action == "add":
        if not args.id or not args.samples:
            print("add 需要 --id 和 --samples")
            return 1
        add_samples(groups, args.id, args.samples)
        save_groups(groups)
        print(f"✅ 组 {args.id} 已添加 {len(args.samples)} 个样本")
        try:
            from gujiorc.core.audit import log_event
            log_event("group_add", actor="cli", group_id=args.id, samples=list(args.samples))
        except Exception:
            pass
    elif args.action == "define":
        if not args.id or (args.char is None and args.font is None):
            print("define 需要 --id 和 --char 或 --font")
            return 1
        define_group(groups, args.id, char=args.char, font=args.font)
        save_groups(groups)
        print(f"✅ 组 {args.id} 已定义 char={args.char or '（沿用）'} font={args.font or '-'}")
        try:
            from gujiorc.core.audit import log_event
            log_event("group_define", actor="cli", group_id=args.id, char=args.char)
        except Exception:
            pass
    elif args.action == "remove":
        if not args.id or not args.samples:
            print("remove 需要 --id 和 --samples")
            return 1
        remove_samples(groups, args.id, args.samples)
        save_groups(groups)
        print(f"✅ 组 {args.id} 已移除 {len(args.samples)} 个样本")
        try:
            from gujiorc.core.audit import log_event
            log_event("group_remove", actor="cli", group_id=args.id, samples=list(args.samples))
        except Exception:
            pass
    return 0


def _print_groups(groups):
    if not groups:
        print("暂无生僻字分组（用 `groups create --name 组名` 创建）")
        return
    for g in groups:
        print(f"[{g.id}] {g.name}  status={g.status}  样本数={len(g.samples)}  "
              f"char={g.char or '未定义'}  font={g.font or '-'}  note={g.note or ''}")


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

    p_dict = sub.add_parser("dict", help="生僻字查询/拆解")
    p_dict.add_argument("char")
    p_dict.set_defaults(func=cmd_dict)

    p_fix = sub.add_parser("fix", help="改正字（保留orig_char+记录映射）")
    p_fix.add_argument("page", help="页面（如 page_001）")
    p_fix.add_argument("match", help="字框ID、all、或--from-char匹配")
    p_fix.add_argument("new_char", help="改正后的字")
    p_fix.add_argument("--from-char", default=None, help="按原字/当前字匹配批量改")
    p_fix.set_defaults(func=cmd_fix)

    p_show = sub.add_parser("show", help="查看字框原始识别与映射")
    p_show.add_argument("page", help="页面（如 page_001）")
    p_show.add_argument("--id", dest="char_id", default=None, help="字框ID")
    p_show.add_argument("--from-char", default=None, help="按字符查")
    p_show.set_defaults(func=cmd_show_char)

    p_report = sub.add_parser("report", help="生成OCR质量报告")
    p_report.add_argument("--book", default="", help="书名（用于标题）")
    p_report.set_defaults(func=cmd_report)

    p_export = sub.add_parser("export", help="导出识别成果(JSON/TXT/TSV/transcript/corpus)")
    p_export.add_argument("--book", default="book", help="输出文件前缀/书目ID")
    p_export.add_argument("--formats", default="json,txt,tsv,transcript",
                          help="逗号分隔格式: json,txt,tsv,transcript")
    p_export.add_argument("--corpus-out", default="", help="pipeline corpus 导出目录（给路径则切 corpus 模式）")
    p_export.add_argument("--work-title", default="", help="corpus 模式必填：书名原文")
    p_export.add_argument("--technique-id", default="", help="corpus 模式必填：技法ID")
    p_export.add_argument("--edition", type=int, default=1, help="版次（目录名 _edNN）")
    p_export.add_argument("--edition-note", default="", help="版本说明/补充说明")
    p_export.add_argument("--rights-status", default="public_domain", help="rights_status")
    p_export.set_defaults(func=cmd_export)

    p_g = sub.add_parser("groups", help="生僻字分组归并")
    p_g.add_argument("action", nargs="?", default="list", choices=["list", "create", "add", "define", "remove"],
                     help="list=展示, create=创建, add=加样本, define=定义字/字体, remove=移样本")
    p_g.add_argument("--name", help="组名（create）")
    p_g.add_argument("--id", help="组 ID")
    p_g.add_argument("--samples", nargs="*", help="字框 ID 列表")
    p_g.add_argument("--char", help="定义的目标字（define）")
    p_g.add_argument("--font", help="TTF 字体名（define）")
    p_g.add_argument("--note", help="备注")
    p_g.set_defaults(func=cmd_groups)

    args = parser.parse_args()
    if args.root:
        os.environ["OCR_ROOT"] = args.root
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())