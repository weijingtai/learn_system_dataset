"""M2 纯函数：文本清洗（规格 §4.4、§10、G7-RULINGS §81、§90、§91）。

对原始电子文本依次执行十三项清洗检查，产出 Finding 记录集与清洗后文本 CleanResult。
支持数据驱动（繁简字表、形近字表）与全文去重比对、文内目录核验。
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from . import ACTIONS, FINDING_KINDS, TERMINAL_STATES

DATA_DIR = Path(__file__).resolve().parent / "data"

_DEFAULT_VARIANT_PAIRS: list[dict[str, str]] | None = None
_DEFAULT_SUSPECTED_PAIRS: list[dict[str, str]] | None = None

# 文件头 YAML front matter（含首尾 --- 围栏）：转换站点添加的元数据，不是书的正文（第 98 条①）
_YAML_FRONT_MATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL
)
_YAML_SEPARATION_BASIS = "YAML 头与正文分离（转换残留检查项之一，README §5 第 5 项）"

# Markdown 单字符转义对（\-、\[、\]、\*、\_、\\）
_ESCAPE_PAIR_RE = re.compile(r"\\[\-\[\]\*\_\\]\Z")

# 框线与 ASCII 图形字符集，及成块判定的数量阈值（README §5 第 10 项、第 98 条④）
_BOX_CHARS = frozenset("┌┐└┘├┤┬┴┼─│━┃┏┓┗┛═║╔╗╚╝╠╣╦╩╬+-—―|")
_DIAGRAM_LINE_MIN_BOX_CHARS = 3
_DIAGRAM_MIN_LINES = 2

# 紧邻重复的重复单元须至少含一个 CJK 字符或字母（第 98 条②）
_LETTER_OR_CJK_RE = re.compile(r"[A-Za-z\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def split_front_matter(raw_content: str) -> tuple[int, str]:
    """切出文件头 YAML front matter，返回 (头结束偏移, 供检测器扫描的掩码文本)。

    头部区间内的字符一律换成空格（换行保留），长度不变，因此各检测器偏移与原文一致，
    但**不再扫描该区间**（第 98 条①）。无 front matter 时返回 (0, raw_content)。
    """
    m = _YAML_FRONT_MATTER_RE.match(raw_content)
    if m is None:
        return 0, raw_content
    end = m.end()
    masked = "".join(
        "\n" if ch == "\n" else " " for ch in raw_content[:end]
    ) + raw_content[end:]
    return end, masked


def diagram_runs(text: str) -> list[tuple[int, int]]:
    """返回连续 >= 2 行、每行 >= 3 个框线/ASCII 图形字符的区块区间（第 98 条④）。

    只要求行内该类字符达到数量阈值，不要求整行皆是——星曜名与分隔符交替的排布因此可检出。
    """
    runs: list[tuple[int, int]] = []
    offset = 0
    run_start: int | None = None
    run_end = 0
    run_lines = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        boxes = sum(1 for ch in content if ch in _BOX_CHARS)
        if boxes >= _DIAGRAM_LINE_MIN_BOX_CHARS:
            if run_start is None:
                run_start = offset
                run_lines = 0
            run_end = offset + len(content)
            run_lines += 1
        else:
            if run_start is not None and run_lines >= _DIAGRAM_MIN_LINES:
                runs.append((run_start, run_end))
            run_start = None
            run_lines = 0
        offset += len(line)
    if run_start is not None and run_lines >= _DIAGRAM_MIN_LINES:
        runs.append((run_start, run_end))
    return runs


def is_fully_covered(ranges: list[tuple[int, int]], start: int, end: int) -> bool:
    """判断 [start, end) 是否被 ranges 完全覆盖（第 98 条⑥）。"""
    pos = start
    for r_start, r_end in sorted(ranges):
        if r_end <= pos:
            continue
        if r_start > pos:
            return False
        pos = max(pos, r_end)
        if pos >= end:
            return True
    return pos >= end


def patch_replacement(finding: Finding) -> str:
    """返回 finding 在清洗文本中的替换内容（clean_text 与 patcher 共用的唯一定义）。

    第 85/96 条：同一契约只允许一处权威出处——两处各自实现必然漂移。
    """
    if finding.action != "patched":
        return finding.raw_excerpt
    if finding.kind == "escape_residue":
        if _ESCAPE_PAIR_RE.match(finding.raw_excerpt):
            # Markdown 单字符转义对：去除反斜杠，恢复文献本字
            return finding.raw_excerpt[1:]
        # YAML 头与正文分离：整块移出正文
        return ""
    if finding.kind in ("control_char", "encoding_issue", "watermark", "header_footer"):
        return ""
    return finding.raw_excerpt


def load_default_variant_pairs() -> list[dict[str, str]]:
    """加载默认繁简字对照表（数据驱动，≥ 100 对）。"""
    global _DEFAULT_VARIANT_PAIRS
    if _DEFAULT_VARIANT_PAIRS is None:
        p = DATA_DIR / "variant_pairs.yaml"
        if p.is_file():
            with open(p, encoding="utf-8") as f:
                d = yaml.safe_load(f)
                _DEFAULT_VARIANT_PAIRS = d.get("pairs", [])
        else:
            _DEFAULT_VARIANT_PAIRS = []
    return list(_DEFAULT_VARIANT_PAIRS)


def load_default_suspected_pairs() -> list[dict[str, str]]:
    """加载默认形近误字对照表（数据驱动，≥ 20 对）。"""
    global _DEFAULT_SUSPECTED_PAIRS
    if _DEFAULT_SUSPECTED_PAIRS is None:
        p = DATA_DIR / "suspected_error_pairs.yaml"
        if p.is_file():
            with open(p, encoding="utf-8") as f:
                d = yaml.safe_load(f)
                _DEFAULT_SUSPECTED_PAIRS = d.get("pairs", [])
        else:
            _DEFAULT_SUSPECTED_PAIRS = []
    return list(_DEFAULT_SUSPECTED_PAIRS)


@dataclass
class Finding:
    """清洗发现项数据结构（规格 §81）。"""

    finding_id: str
    kind: str
    raw_start: int
    raw_end: int
    raw_excerpt: str
    context: str
    action: str
    patch_id: str | None
    basis: str
    terminal_state: str

    def __post_init__(self):
        if self.kind not in FINDING_KINDS:
            raise ValueError(f"非法 kind: {self.kind}")
        if self.terminal_state not in TERMINAL_STATES:
            raise ValueError(f"非法 terminal_state: {self.terminal_state}")
        if self.action not in ACTIONS:
            raise ValueError(f"非法 action: {self.action}")
        expected_id = f"{self.kind}@{self.raw_start}-{self.raw_end}"
        if self.finding_id != expected_id:
            raise ValueError(
                f"finding_id 格式不符合规范: {self.finding_id} != {expected_id}"
            )


@dataclass
class CleanResult:
    """清洗结果对象。"""

    findings: list[Finding]
    cleaned_text: str


def _get_context(text: str, start: int, end: int, window: int = 15) -> str:
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    return text[ctx_start:ctx_end].replace("\n", " ")


def clean_text(
    raw_content: str,
    variant_pairs: list[dict[str, str]] | None = None,
    suspected_error_pairs: list[dict[str, str]] | None = None,
) -> CleanResult:
    """对原始文本执行确定性清洗检查（纯函数）。

    参数：
        raw_content：原始电子文本字符串。
        variant_pairs：可选自定义繁简字对照表（缺省从数据文件加载）。
        suspected_error_pairs：可选自定义形近字对照表（缺省从数据文件加载）。

    返回：
        CleanResult(findings, cleaned_text)。
    """
    findings: list[Finding] = []

    # 0. YAML 头与正文分离（第 98 条①）：头是转换站点的元数据，不是书的正文。
    #    登记一条 escape_residue，以可逆 patch 整块移出正文，其余检测器一律不扫描该区间。
    front_matter_end, scan_text = split_front_matter(raw_content)
    if front_matter_end > 0:
        findings.append(
            Finding(
                finding_id=f"escape_residue@0-{front_matter_end}",
                kind="escape_residue",
                raw_start=0,
                raw_end=front_matter_end,
                raw_excerpt=raw_content[:front_matter_end],
                context=f"文件头 YAML front matter（{front_matter_end} 字符，含首尾 --- 围栏），非书的正文",
                action="patched",
                patch_id=None,
                basis=_YAML_SEPARATION_BASIS,
                terminal_state="processed",
            )
        )

    # 1. encoding_issue 检查：BOM 与编码声明
    for m in re.finditer(
        r"\ufeff|<!--\s*coding:[^>]+-->|#\s*-\*-\s*coding:[^\n]+", scan_text
    ):
        start, end = m.span()
        findings.append(
            Finding(
                finding_id=f"encoding_issue@{start}-{end}",
                kind="encoding_issue",
                raw_start=start,
                raw_end=end,
                raw_excerpt=raw_content[start:end],
                context=_get_context(raw_content, start, end),
                action="patched",
                patch_id=None,
                basis="检测 BOM 与编码声明，规范为统一 UTF-8 纯文本",
                terminal_state="processed",
            )
        )

    # 2. replacement_char 检查：?、□、U+FFFD
    for m in re.finditer(r"[\?□\ufffd]", scan_text):
        start, end = m.span()
        findings.append(
            Finding(
                finding_id=f"replacement_char@{start}-{end}",
                kind="replacement_char",
                raw_start=start,
                raw_end=end,
                raw_excerpt=raw_content[start:end],
                context=_get_context(raw_content, start, end),
                action="kept",
                patch_id=None,
                basis="保留疑似替换字符，不主观猜字",
                terminal_state="known_unresolvable",
            )
        )

    # 3. private_use_area 检查：Unicode PUA 码位 (E000-F8FF, F0000-FFFFD, 100000-10FFFD)
    for m in re.finditer(
        r"[\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd]",
        scan_text,
    ):
        start, end = m.span()
        findings.append(
            Finding(
                finding_id=f"private_use_area@{start}-{end}",
                kind="private_use_area",
                raw_start=start,
                raw_end=end,
                raw_excerpt=raw_content[start:end],
                context=_get_context(raw_content, start, end),
                action="kept",
                patch_id=None,
                basis="保留 PUA 原码位，待字形层查证（§79 D4）",
                terminal_state="known_unresolvable",
            )
        )

    # 4. control_char 检查：零宽字符与异常控制字符（BOM 归入 encoding_issue）
    for m in re.finditer(
        r"[\u200b\u200c\u200d\x00-\x08\x0b\x0e-\x1f]", scan_text
    ):
        start, end = m.span()
        findings.append(
            Finding(
                finding_id=f"control_char@{start}-{end}",
                kind="control_char",
                raw_start=start,
                raw_end=end,
                raw_excerpt=raw_content[start:end],
                context=_get_context(raw_content, start, end),
                action="patched",
                patch_id=None,
                basis="剔除异常零宽与不可见控制字符",
                terminal_state="processed",
            )
        )

    # 5. escape_residue 检查：Markdown 转义残留（如 \-、\[、\] 等）；逐字符登记（第 98 条③）
    for m in re.finditer(r"\\[\-\[\]\*\_\\]", scan_text):
        start, end = m.span()
        findings.append(
            Finding(
                finding_id=f"escape_residue@{start}-{end}",
                kind="escape_residue",
                raw_start=start,
                raw_end=end,
                raw_excerpt=raw_content[start:end],
                context=_get_context(raw_content, start, end),
                action="patched",
                patch_id=None,
                basis="去除 Markdown 转义斜杠，恢复文献本字",
                terminal_state="processed",
            )
        )

    # 6. watermark 检查：非文献内容检测（页脚、维护者声明、链接）
    for m in re.finditer(
        r"(?:https?://[^\s]+|www\.[^\s]+|殆知阁整理|本电子书由[^\s\n]+提供|下载自[^\s\n]+|扫校[：:][^\s\n]+|扫描制作[：:][^\s\n]+)",
        scan_text,
    ):
        start, end = m.span()
        findings.append(
            Finding(
                finding_id=f"watermark@{start}-{end}",
                kind="watermark",
                raw_start=start,
                raw_end=end,
                raw_excerpt=raw_content[start:end],
                context=_get_context(raw_content, start, end),
                action="patched",
                patch_id=None,
                basis="非文献内容检测（页脚、维护者声明、链接）",
                terminal_state="processed",
            )
        )

    # 7. header_footer 检查（§91）：
    # 同一非空行在全文重复出现 >= 3 次（或按固定间隔重复）即登记；分页标记作为附加触发保留。
    lines = scan_text.splitlines(keepends=True)
    line_counts = Counter()
    for line in lines:
        stripped = line.strip()
        # 过滤出适合作为页眉页脚标题行的短行（2-40 字符）
        if 2 <= len(stripped) <= 40:
            line_counts[stripped] += 1

    # 收集出现 >= 3 次的页眉标题行
    repeated_headers = {
        hdr for hdr, count in line_counts.items() if count >= 3
    }

    cur_pos = 0
    for line in lines:
        stripped = line.strip()
        line_len = len(line)
        start = cur_pos
        end = cur_pos + len(line.rstrip("\r\n"))
        if stripped in repeated_headers:
            findings.append(
                Finding(
                    finding_id=f"header_footer@{start}-{end}",
                    kind="header_footer",
                    raw_start=start,
                    raw_end=end,
                    raw_excerpt=raw_content[start:end],
                    context=_get_context(raw_content, start, end),
                    action="patched",
                    patch_id=None,
                    basis="重复标题行检测（全文重复出现 >= 3 次）",
                    terminal_state="processed",
                )
            )
        cur_pos += line_len

    # 附加触发：分页标记
    for m in re.finditer(
        r"(?:---\s*第\s*\d+\s*页\s*---|===+\s*.*?\s*===+|【第\s*[0-9一二三四五六七八九十]+\s*页】)",
        scan_text,
    ):
        start, end = m.span()
        # 避免与重复标题行区间重合
        if not any(f.kind == "header_footer" and f.raw_start == start for f in findings):
            findings.append(
                Finding(
                    finding_id=f"header_footer@{start}-{end}",
                    kind="header_footer",
                    raw_start=start,
                    raw_end=end,
                    raw_excerpt=raw_content[start:end],
                    context=_get_context(raw_content, start, end),
                    action="patched",
                    patch_id=None,
                    basis="分页标记与页眉页脚检测",
                    terminal_state="processed",
                )
            )

    # 10.（前移：第 98 条⑥ 要求 duplicate 排除图形区间，故图形判定须先于 duplicate）
    # textualized_diagram 检查（§91）：
    # 节标题识别、正文/注文/夹注格式、文本化图表区块登记；增加连续框线／制表符／ASCII 图形区块识别
    # (a) 显式图表标记与 Markdown 表格
    for m in re.finditer(
        r"(?:【图(?:表|式)?(?:：.*?)?】|\[图(?:表|式)?(?:：.*?)?\]|\|(?:\s*---\s*\|)+)",
        scan_text,
    ):
        start, end = m.span()
        findings.append(
            Finding(
                finding_id=f"textualized_diagram@{start}-{end}",
                kind="textualized_diagram",
                raw_start=start,
                raw_end=end,
                raw_excerpt=raw_content[start:end],
                context=_get_context(raw_content, start, end),
                action="flagged",
                patch_id=None,
                basis="节标题识别、正文/注文/夹注格式、文本化图表区块登记",
                terminal_state="processed",
            )
        )

    # (b) 连续框线、制表线、破折连线与 ASCII/几何图形区块（§92 覆盖制表符、ASCII 框线与破折连线）
    diagram_box_pattern = re.compile(
        r"(?:(?:^[ \t]*[┌┐└┘├┤┬┴┼─│━┃┏┓┗┛═║╔╗╚╝╠╣╦╩╬+\-—―|]{3,}[ \t]*$\n?){2,}"
        r"|(?:^[ \t]*[┌│├└+|║][^\n]*[┐│┤┘+|║][ \t]*$\n?){2,}"
        r"|(?:[|+][\-+|=—―]{3,}[|+]\n?){2,})",
        re.MULTILINE,
    )
    for m in diagram_box_pattern.finditer(scan_text):
        start, end = m.span()
        if not any(f.kind == "textualized_diagram" and f.raw_start <= start and f.raw_end >= end for f in findings):
            findings.append(
                Finding(
                    finding_id=f"textualized_diagram@{start}-{end}",
                    kind="textualized_diagram",
                    raw_start=start,
                    raw_end=end,
                    raw_excerpt=raw_content[start:end],
                    context=_get_context(raw_content, start, end),
                    action="flagged",
                    patch_id=None,
                    basis="文本化图表与几何框线区块识别（制表符/ASCII框线/破折连线）",
                    terminal_state="processed",
                )
            )

    # (c) 行内框线／ASCII 图形字符达数量阈值、连续 >= 2 行成块（第 98 条④：不要求整行皆是）
    for start, end in diagram_runs(scan_text):
        if not any(
            f.kind == "textualized_diagram" and f.raw_start <= start and f.raw_end >= end
            for f in findings
        ):
            findings.append(
                Finding(
                    finding_id=f"textualized_diagram@{start}-{end}",
                    kind="textualized_diagram",
                    raw_start=start,
                    raw_end=end,
                    raw_excerpt=raw_content[start:end],
                    context=_get_context(raw_content, start, end),
                    action="flagged",
                    patch_id=None,
                    basis="行内框线/ASCII 图形字符达阈值且连续 >= 2 行成块（文本化图表）",
                    terminal_state="processed",
                )
            )

    # 8. duplicate 检查（§91）：全文去重比对，登记每一处出现位置（含非紧邻的重复段落），不静默删除
    # 第 98 条⑥：不得命中已被 escape_residue 或 textualized_diagram 覆盖的区间。
    covered_ranges = [
        (f.raw_start, f.raw_end)
        for f in findings
        if f.kind in ("escape_residue", "textualized_diagram")
    ]

    # 按段落切分，收集长度 >= 8 字符的段落
    paragraphs = re.split(r"(\n+)", scan_text)
    para_counts = Counter()
    p_offset = 0
    para_positions: dict[str, list[tuple[int, int]]] = {}
    for part in paragraphs:
        stripped_p = part.strip()
        p_len = len(part)
        if len(stripped_p) >= 8 and "\n" not in stripped_p:
            para_counts[stripped_p] += 1
            start = scan_text.find(stripped_p, p_offset)
            end = start + len(stripped_p)
            para_positions.setdefault(stripped_p, []).append((start, end))
        p_offset += p_len

    # 对出现次数 >= 2 的段落，登记每一处重复位置
    for text_block, count in para_counts.items():
        if count >= 2:
            for start, end in para_positions[text_block]:
                if is_fully_covered(covered_ranges, start, end):
                    continue
                findings.append(
                    Finding(
                        finding_id=f"duplicate@{start}-{end}",
                        kind="duplicate",
                        raw_start=start,
                        raw_end=end,
                        raw_excerpt=raw_content[start:end],
                        context=_get_context(raw_content, start, end),
                        action="flagged",
                        patch_id=None,
                        basis="全文去重比对发现重复段落（全文出现 >= 2 次），登记位置不静默删除",
                        terminal_state="processed",
                    )
                )

    # 附加触发：连续紧邻重复短语（重复单元须 >= 4 字符且至少含一个 CJK 字符或字母，第 98 条②）
    for m in re.finditer(r"([^\s，。！？、]{4,})\1+", scan_text):
        start, end = m.span()
        if not _LETTER_OR_CJK_RE.search(m.group(1)):
            continue
        if is_fully_covered(covered_ranges, start, end):
            continue
        if not any(f.kind == "duplicate" and f.raw_start <= start and f.raw_end >= end for f in findings):
            findings.append(
                Finding(
                    finding_id=f"duplicate@{start}-{end}",
                    kind="duplicate",
                    raw_start=start,
                    raw_end=end,
                    raw_excerpt=raw_content[start:end],
                    context=_get_context(raw_content, start, end),
                    action="flagged",
                    patch_id=None,
                    basis="全文去重比对发现紧邻重复内容，登记位置但不静默删除",
                    terminal_state="processed",
                )
            )

    # 9. missing 检查（§91）：
    # (a) 解析文内目录（目錄/目录/卷目等节），逐条核对其标题是否在正文中出现；缺者登记，终态恒 deferred
    # 边界（README §5）：文内无目录时不产出 finding
    toc_pattern = re.compile(r"(?:^|\n)[ \t]*(?:[^\n]{0,15})?(?:目錄|目录|卷目|目次)[ \t*：:\n]+")
    toc_match = toc_pattern.search(scan_text)
    if toc_match:
        toc_start_pos = toc_match.end()
        remainder = scan_text[toc_start_pos:]
        lines = remainder.splitlines(keepends=True)
        toc_items = []
        body_start_pos = toc_start_pos

        cur_offset = toc_start_pos
        seen_items = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if seen_items:
                    cur_offset += len(line)
                    body_start_pos = cur_offset
                    break
                else:
                    cur_offset += len(line)
                    continue

            # 若遇到正文特征（行长>40、含句号且长、显式正文标识、或重复此前出现过的条目），视为目录结束进入正文
            if seen_items and (
                len(stripped) > 40
                or ("。" in stripped and len(stripped) > 15)
                or stripped == "正文"
                or any(stripped == prev_item or (len(prev_item) >= 4 and prev_item in stripped) for prev_item, _, _ in toc_items)
            ):
                body_start_pos = cur_offset
                break

            # 目录条目行
            seen_items = True
            line_start = cur_offset + line.find(stripped)
            line_end = line_start + len(stripped)
            toc_items.append((stripped, line_start, line_end))
            cur_offset += len(line)
            body_start_pos = cur_offset

        body_text = scan_text[body_start_pos:]
        for item, f_start, f_end in toc_items:
            clean_title = re.sub(r"^(?:卷[0-9一二三四五六七八九十]+|第[0-9一二三四五六七八九十]+[章节卷回]|[0-9]+)[、.\s·]*", "", item).strip()
            match_title = clean_title if len(clean_title) >= 2 else item
            if match_title not in body_text and item not in body_text:
                findings.append(
                    Finding(
                        finding_id=f"missing@{f_start}-{f_end}",
                        kind="missing",
                        raw_start=f_start,
                        raw_end=f_end,
                        raw_excerpt=raw_content[f_start:f_end],
                        context=_get_context(raw_content, f_start, f_end),
                        action="flagged",
                        patch_id=None,
                        basis="对照文内目录核对章节完整性，发现章节未在正文中出现（终态恒 deferred）",
                        terminal_state="deferred",
                    )
                )

    # 附加触发：原显式缺失标记
    for m in re.finditer(
        r"(?:【缺(?:字|失)?】|\[缺(?:字|失)?\]|〔阙〕)", scan_text
    ):
        start, end = m.span()
        if not any(f.kind == "missing" and f.raw_start == start for f in findings):
            findings.append(
                Finding(
                    finding_id=f"missing@{start}-{end}",
                    kind="missing",
                    raw_start=start,
                    raw_end=end,
                    raw_excerpt=raw_content[start:end],
                    context=_get_context(raw_content, start, end),
                    action="flagged",
                    patch_id=None,
                    basis="对照底本核对完整性，缺失登记为已知缺口",
                    terminal_state="deferred",
                )
            )

    # 11. suspected_error 检查（§91 数据驱动）：
    suspected_list = (
        suspected_error_pairs
        if suspected_error_pairs is not None
        else load_default_suspected_pairs()
    )
    for pair in suspected_list:
        wrong = pair.get("wrong")
        if not wrong:
            continue
        basis = pair.get(
            "basis",
            f"形近误字疑点：{wrong} 疑为 {pair.get('correct', '')}，须人工核验底本",
        )
        for m in re.finditer(re.escape(wrong), scan_text):
            start, end = m.span()
            findings.append(
                Finding(
                    finding_id=f"suspected_error@{start}-{end}",
                    kind="suspected_error",
                    raw_start=start,
                    raw_end=end,
                    raw_excerpt=raw_content[start:end],
                    context=_get_context(raw_content, start, end),
                    action="flagged",
                    patch_id=None,
                    basis=basis,
                    terminal_state="deferred",
                )
            )

    # 12. variant_mixed 检查（§91 数据驱动，第 98 条⑤：逐处登记，不因首处命中而止）：
    v_pairs = (
        variant_pairs
        if variant_pairs is not None
        else load_default_variant_pairs()
    )
    tc_set = {p["tc"] for p in v_pairs if p.get("tc") and p.get("sc") and p["tc"] != p["sc"]}
    sc_set = {p["sc"] for p in v_pairs if p.get("tc") and p.get("sc") and p["tc"] != p["sc"]}

    has_tc = any(c in tc_set for c in scan_text)
    has_sc = any(c in sc_set for c in scan_text)
    if has_tc and has_sc:
        for i, ch in enumerate(scan_text):
            if ch in tc_set:
                findings.append(
                    Finding(
                        finding_id=f"variant_mixed@{i}-{i+1}",
                        kind="variant_mixed",
                        raw_start=i,
                        raw_end=i + 1,
                        raw_excerpt=raw_content[i:i + 1],
                        context=_get_context(raw_content, i, i + 1),
                        action="kept",
                        patch_id=None,
                        basis="记录繁简混杂特征，保留文献原貌（数据驱动繁简字表比对）",
                        terminal_state="processed",
                    )
                )

    # 按 raw_start 升序排列
    findings.sort(key=lambda f: (f.raw_start, f.raw_end))

    # 生成 cleaned_text：只对 action == "patched" 的发现应用修改
    cleaned_chars = []
    idx = 0
    patched_findings = [f for f in findings if f.action == "patched"]
    patched_findings.sort(key=lambda f: (f.raw_start, f.raw_end))

    for f in patched_findings:
        if f.raw_start > idx:
            cleaned_chars.append(raw_content[idx : f.raw_start])
        cleaned_chars.append(patch_replacement(f))
        idx = max(idx, f.raw_end)

    if idx < len(raw_content):
        cleaned_chars.append(raw_content[idx:])

    cleaned_text = "".join(cleaned_chars)
    return CleanResult(findings=findings, cleaned_text=cleaned_text)
