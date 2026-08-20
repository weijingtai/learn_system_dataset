"""gujiorc.core.export — 数据导出（PLANS §6 与 pipeline 衔接）。

支持格式：
- JSON   : 原样导出（含完整映射）→ 机器可读
- TXT    : 纯文本（按页，逐字拼接，未识别用 □）   → 人类阅读
- TSV    : 表格（字/坐标/置信度/映射）             → 表格处理
- transcript_v1.md : pipeline/corpus 转录格式（PLANS §6.1）
  - 每页 `<!-- p0001 -->` 标记 + 正文按阅读序（列右→左、列内上→下）
  - 繁体保持原字形；未识别字按 M12_ 分组映射/□ 占位
  - 与 pipeline/corpus/{technique}/{book}_edNN/source/transcript_v1.md 对齐
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import PageResult, CharBox


def char_display(c: CharBox, groups_resolve=None) -> str:
    """导出用字符：优先分组映射后的 char；未识别/空用 □。"""
    if c.char:
        return c.char
    return "□"


def page_to_text(page: PageResult, groups_resolve=None, sep: str = "") -> str:
    """按阅读序把一页字框拼成文本。

    阅读序依赖 chars 已按区块→列→行→字排序（run 时处理）。
    若 chars 有序，直接按序拼接；未识别字 → □。
    """
    return sep.join(char_display(c, groups_resolve) for c in page.chars)


def gen_all_pages_text(pages: list[PageResult], groups_resolve=None) -> str:
    """多页纯文本导出。"""
    return "\n".join(page_to_text(p, groups_resolve) for p in pages)


# ---------------- pipeline / corpus transcript v1.md ----------------

def gen_transcript_md(pages: list[PageResult], groups_resolve=None, pageno_start: int = 1) -> str:
    """生成 pipeline/corpus 格式的 transcript_v1.md（PLANS §6.1）。

    每页 `<!-- p0001 -->` + 正文。**繁体保持原字形**（系统内已繁体，
    严禁简繁转换）；未识别字 □。
    """
    lines = []
    for i, page in enumerate(pages):
        pageno = pageno_start + i
        lines.append(f"<!-- p{pageno:04d} -->")
        text = page_to_text(page, groups_resolve)
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


# ---------------- TSV 导出 ----------------

def gen_tsv(pages: list[PageResult], groups_resolve=None) -> str:
    """TSV 表格导出：页/框ID/坐标/原字/当前字/置信度/生僻/映射。"""
    out = ["page\tchar_id\tx\ty\tw\th\torig\tchar\tconf\tis_rare\tmapping"]
    for page in pages:
        for c in page.chars:
            b = c.box
            m = c.mapping
            mstr = f"{m['from']}->{m['target']}({m['source']})" if m else ""
            out.append(
                f"{page.page}\t{c.id}\t{b['x']:.1f}\t{b['y']:.1f}\t{b['w']:.1f}\t{b['h']:.1f}\t"
                f"{c.orig_char or ''}\t{c.char or ''}\t{c.conf:.3f}\t{c.is_rare}\t{mstr}"
            )
    return "\n".join(out)


# ---------------- 通用导出入口 ----------------

def export_common(pages: list[PageResult], out_dir: str | Path,
                  prefix: str = "book", groups_resolve=None,
                  formats: tuple[str, ...] = ("json", "txt", "tsv", "transcript")) -> dict[str, Path]:
    """按格式导出所有页。返回 {format: 输出路径}。"""
    import json
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}

    # JSON：所有页合并为一个
    if "json" in formats:
        p = out_dir / f"{prefix}.json"
        p.write_text(json.dumps(
            {"pages": [pg.to_dict() for pg in pages]}, ensure_ascii=False, indent=2), encoding="utf-8")
        result["json"] = p

    if "txt" in formats:
        p = out_dir / f"{prefix}.txt"
        p.write_text(gen_all_pages_text(pages, groups_resolve), encoding="utf-8")
        result["txt"] = p

    if "tsv" in formats:
        p = out_dir / f"{prefix}.tsv"
        p.write_text(gen_tsv(pages, groups_resolve), encoding="utf-8")
        result["tsv"] = p

    if "transcript" in formats:
        p = out_dir / f"{prefix}_transcript_v1.md"
        p.write_text(gen_transcript_md(pages, groups_resolve), encoding="utf-8")
        result["transcript"] = p

    return result


# ---------------- pipeline corpus 导出（manifest.yaml） ----------------

def sha256_file(path: Path) -> str:
    """计算文件 sha256 十六进制。分块读，不一次载入。"""
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_unknown(pages: list[PageResult]) -> int:
    """统计导出后会变成 □ 的字框数（char 为空）。"""
    return sum(1 for p in pages for c in p.chars if not c.char)


def _safe_quote(value: str) -> str:
    """把普通字符串转成双引号包裹的 YAML 字面量（处理换行/反斜杠）。"""
    inner = value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")
    return f'"{inner}"'


def export_corpus(
    pages: list[PageResult],
    corpus_dir: str | Path,
    *,
    book: str,
    work_title: str,
    technique_id: str,
    edition: int = 1,
    edition_note: str = "",
    rights_status: str = "public_domain",
    groups_resolve=None,
) -> dict[str, Path | int]:
    """导出为 pipeline/corpus 结构 + manifest.yaml（PLANS §6.1）。"""
    book_dir = Path(corpus_dir) / technique_id / f"{book}_ed{edition:02d}"
    (book_dir / "source").mkdir(parents=True, exist_ok=True)

    transcript_path = book_dir / "source" / "transcript_v1.md"
    transcript_path.write_text(gen_transcript_md(pages, groups_resolve), encoding="utf-8")

    unknown = count_unknown(pages)
    note = edition_note
    if unknown and "未识别字形待人工补录" not in note:
        note = (note + "；" if note else "") + f"该底本存在 {unknown} 个未识别字形待人工补录（导出为 □ 占位）"

    manifest = "\n".join([
        f'source_id: "src_{book}_ed{edition:02d}"',
        f'work_title: {_safe_quote(work_title)}',
        f'edition_note: {_safe_quote(note)}',
        f'technique_id: "{technique_id}"',
        f'rights_status: "{rights_status}"',
        "files:",
        '  - path: "source/transcript_v1.md"',
        '    role: "transcript"',
        f'    sha256: "{sha256_file(transcript_path)}"',
        "",
    ])
    manifest_path = book_dir / "manifest.yaml"
    manifest_path.write_text(manifest, encoding="utf-8")
    return {"manifest": manifest_path, "transcript": transcript_path, "unknown": unknown}