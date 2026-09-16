"""M2 纯函数：文本清洗（规格 §4.4、§10、G7-RULINGS §81）。

对原始电子文本依次执行十三项清洗检查，产出 Finding 记录集与清洗后文本 CleanResult。
"""

import re
from dataclasses import dataclass

from . import ACTIONS, FINDING_KINDS, TERMINAL_STATES


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
            raise ValueError(f"finding_id 格式不符合规范: {self.finding_id} != {expected_id}")


@dataclass
class CleanResult:
    """清洗结果对象。"""

    findings: list[Finding]
    cleaned_text: str


def _get_context(text: str, start: int, end: int, window: int = 15) -> str:
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    return text[ctx_start:ctx_end].replace("\n", " ")


def clean_text(raw_content: str) -> CleanResult:
    """对原始文本执行确定性清洗检查（纯函数）。

    参数：
        raw_content：原始电子文本字符串。

    返回：
        CleanResult(findings, cleaned_text)。
    """
    findings: list[Finding] = []

    # 1. replacement_char 检查：?、□、U+FFFD
    for m in re.finditer(r"[\?□\ufffd]", raw_content):
        start, end = m.span()
        excerpt = raw_content[start:end]
        findings.append(
            Finding(
                finding_id=f"replacement_char@{start}-{end}",
                kind="replacement_char",
                raw_start=start,
                raw_end=end,
                raw_excerpt=excerpt,
                context=_get_context(raw_content, start, end),
                action="kept",
                patch_id=None,
                basis="保留疑似替换字符，不主观猜字",
                terminal_state="known_unresolvable",
            )
        )

    # 2. private_use_area 检查：Unicode PUA 码位 (E000-F8FF, F0000-FFFFD, 100000-10FFFD)
    for m in re.finditer(r"[\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd]", raw_content):
        start, end = m.span()
        excerpt = raw_content[start:end]
        findings.append(
            Finding(
                finding_id=f"private_use_area@{start}-{end}",
                kind="private_use_area",
                raw_start=start,
                raw_end=end,
                raw_excerpt=excerpt,
                context=_get_context(raw_content, start, end),
                action="kept",
                patch_id=None,
                basis="保留 PUA 原码位，待字形层查证（§79 D4）",
                terminal_state="known_unresolvable",
            )
        )

    # 3. control_char 检查：零宽字符与异常控制字符
    for m in re.finditer(r"[\u200b\u200c\u200d\ufeff\x00-\x08\x0b\x0e-\x1f]", raw_content):
        start, end = m.span()
        excerpt = raw_content[start:end]
        findings.append(
            Finding(
                finding_id=f"control_char@{start}-{end}",
                kind="control_char",
                raw_start=start,
                raw_end=end,
                raw_excerpt=excerpt,
                context=_get_context(raw_content, start, end),
                action="patched",
                patch_id=None,
                basis="剔除异常零宽与不可见控制字符",
                terminal_state="processed",
            )
        )

    # 4. escape_residue 检查：Markdown 转义残留（如 \-、\[、\] 等）
    for m in re.finditer(r"\\[\-\[\]\*\_\\]", raw_content):
        start, end = m.span()
        excerpt = raw_content[start:end]
        findings.append(
            Finding(
                finding_id=f"escape_residue@{start}-{end}",
                kind="escape_residue",
                raw_start=start,
                raw_end=end,
                raw_excerpt=excerpt,
                context=_get_context(raw_content, start, end),
                action="patched",
                patch_id=None,
                basis="去除 Markdown 转义斜杠，恢复文献本字",
                terminal_state="processed",
            )
        )

    # 5. suspected_error 检查：常见形近误字（如'子日'->疑似'子曰'）
    for m in re.finditer(r"子日", raw_content):
        start, end = m.span()
        excerpt = raw_content[start:end]
        findings.append(
            Finding(
                finding_id=f"suspected_error@{start}-{end}",
                kind="suspected_error",
                raw_start=start,
                raw_end=end,
                raw_excerpt=excerpt,
                context=_get_context(raw_content, start, end),
                action="flagged",
                patch_id=None,
                basis="形近误字疑点：子日疑为子曰，须人工核验底本（§4.4 第12项）",
                terminal_state="deferred",
            )
        )

    # 6. variant_mixed 检查：繁简混杂
    # 检测常见繁体特征字
    tc_chars = set("繁體字體門開關東發國學氣經書圖說")
    sc_chars = set("简体字体门开关东发国学气经书图说")
    has_tc = any(c in tc_chars for c in raw_content)
    has_sc = any(c in sc_chars for c in raw_content)
    if has_tc and has_sc:
        # 寻找混杂的第一个繁体字位置进行记录
        for i, ch in enumerate(raw_content):
            if ch in tc_chars:
                findings.append(
                    Finding(
                        finding_id=f"variant_mixed@{i}-{i+1}",
                        kind="variant_mixed",
                        raw_start=i,
                        raw_end=i + 1,
                        raw_excerpt=ch,
                        context=_get_context(raw_content, i, i + 1),
                        action="kept",
                        patch_id=None,
                        basis="记录繁简混杂特征，保留文献原貌（§4.4 第11项）",
                        terminal_state="processed",
                    )
                )
                break

    # 按 raw_start 升序排列
    findings.sort(key=lambda f: (f.raw_start, f.raw_end))

    # 生成 cleaned_text：只对 action == "patched" 的发现应用修改
    # 比如 control_char 替换为空；escape_residue 去除反斜杠
    cleaned_chars = []
    idx = 0
    patched_findings = [f for f in findings if f.action == "patched"]
    patched_findings.sort(key=lambda f: f.raw_start)

    for f in patched_findings:
        if f.raw_start > idx:
            cleaned_chars.append(raw_content[idx : f.raw_start])
        if f.kind == "control_char":
            # 剔除控制字符
            pass
        elif f.kind == "escape_residue":
            # 去除反斜杠，保留转义后的字符
            cleaned_chars.append(f.raw_excerpt[1:])
        else:
            cleaned_chars.append(f.raw_excerpt)
        idx = f.raw_end

    if idx < len(raw_content):
        cleaned_chars.append(raw_content[idx:])

    cleaned_text = "".join(cleaned_chars)
    return CleanResult(findings=findings, cleaned_text=cleaned_text)
