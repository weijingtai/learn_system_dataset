"""gujiorc.core.report — 质量报告（M6_）。

汇总每页/整书 OCR 识别质量：
- 总字数、生僻字/低置信数、未识别数、错误修正数
- 各 status（pending/verified/corrected/unrecognized）分布
- 高置信但字节数异常的框（疑似切分问题）

导出 report.md（简洁表格）。可在 Colab 跑完后对本地的 data/ 汇总。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import PageResult, STATUSES, STATUS_CORRECTED, STATUS_UNRECOGNIZED


def page_stats(page: PageResult) -> dict[str, Any]:
    """单页质量统计。"""
    chars = page.chars
    total = len(chars)
    rare = sum(1 for c in chars if c.is_rare)
    low_conf = sum(1 for c in chars if c.is_rare and c.rare_reason == "low_conf")
    not_common = rare - low_conf
    unrecognized = sum(1 for c in chars if c.status == STATUS_UNRECOGNIZED or not c.char)
    corrected = sum(1 for c in chars if c.status == STATUS_CORRECTED)
    mapped = sum(1 for c in chars if c.mapping)

    return {
        "page": page.page,
        "total": total,
        "rare": rare,
        "low_conf": low_conf,
        "not_common": not_common,
        "unrecognized": unrecognized,
        "corrected": corrected,
        "mapped": mapped,
        # status 分布
        "status": {s: sum(1 for c in chars if c.status == s) for s in STATUSES},
    }


def book_report(pages: list[PageResult]) -> dict[str, Any]:
    """整书汇总。"""
    pages_stats = [page_stats(p) for p in pages]
    agg = {
        "total": sum(s["total"] for s in pages_stats),
        "rare": sum(s["rare"] for s in pages_stats),
        "low_conf": sum(s["low_conf"] for s in pages_stats),
        "not_common": sum(s["not_common"] for s in pages_stats),
        "unrecognized": sum(s["unrecognized"] for s in pages_stats),
        "corrected": sum(s["corrected"] for s in pages_stats),
        "mapped": sum(s["mapped"] for s in pages_stats),
        "pages_count": len(pages_stats),
    }
    return {"summary": agg, "pages": pages_stats}


def render_report_md(report: dict[str, Any], book: str = "") -> str:
    """把报告渲染为 Markdown。"""
    s = report["summary"]
    lines = []
    lines.append(f"# 古籍 OCR 质量报告 {f'— {book}' if book else ''}")
    lines.append("")
    lines.append("## 汇总")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|---|---|")
    lines.append(f"| 页数 | {s['pages_count']} |")
    lines.append(f"| 总字数 | {s['total']} |")
    lines.append(f"| 生僻字(不在常用表) | {s['not_common']} |")
    lines.append(f"| 低置信度(需复核) | {s['low_conf']} |")
    lines.append(f"| 未识别(空) | {s['unrecognized']} |")
    lines.append(f"| 已改正(人工) | {s['corrected']} |")
    lines.append(f"| 有映射(orig→char) | {s['mapped']} |")
    lines.append("")
    if s["total"]:
        rare_pct = s["rare"] / s["total"] * 100
        low_pct = s["low_conf"] / s["total"] * 100
        lines.append(f"- 生僻/可疑占比: {s['rare']}/{s['total']} ({rare_pct:.1f}%)")
        lines.append(f"- 低置信度占比: {low_pct:.1f}%（建议人工优先复核）")
    lines.append("")

    lines.append("## 分页明细")
    lines.append("")
    lines.append("| 页 | 字数 | 生僻 | 低置信 | 未识别 | 已改正 | ")
    lines.append("|---|---|---|---|---|---|")
    for ps in report["pages"]:
        lines.append(f"| {ps['page']} | {ps['total']} | {ps['not_common']} | "
                     f"{ps['low_conf']} | {ps['unrecognized']} | {ps['corrected']} |")
    lines.append("")
    return "\n".join(lines)


def load_all_pages(data_dir: str | Path) -> list[PageResult]:
    """从 data/ 目录加载所有页面（跳过 .marked 等非 page_.json 文件）。"""
    from .storage import load_page_json
    data_dir = Path(data_dir)
    pages = []
    for p in sorted(data_dir.glob("page_*.json")):
        if p.stem.endswith(".marked"):
            continue
        pr = load_page_json(p.stem, validate=False)
        if pr is not None:
            pages.append(pr)
    return pages