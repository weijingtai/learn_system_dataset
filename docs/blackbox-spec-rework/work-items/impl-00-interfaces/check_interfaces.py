#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""impl-00/15：INTERFACES.md §4 临时闭集登记检查器（IF01–IF44）。

只用标准库。按行解析 `INTERFACES.md` 的 §4 表，逐项判定并输出
`PASS IFnn <名>` / `FAIL IFnn <名> <原因>`，末行 `I00-IF SUMMARY pass=<n> fail=<n>`。
文件缺失时输出 `I00-IF BLOCKED 前置缺失: INTERFACES.md 不存在` 并返回 3。

IF01–IF18 为 impl-00/10 首纵切登记检查，编号与语义冻结（现有用例依赖）；
IF19–IF23 为 impl-00/12 新增的 M4 五个类型（各在 §4 表出现恰一次）；
IF24 禁止 §4 表残留旧 M4 名；
IF25–IF28 为 impl-00/13 新增的 M6 四个类型（各在 §4 表出现恰一次）；
IF29 禁止 §4 表把 `correction_request` 登记为独立 artifact_type（impl-06 D-10：
CorrectionRequest 为 `human_event`，不是独立类型）；
IF30–IF33 为 impl-00/14 新增的 M2 电子文本四个类型（各在 §4 表出现恰一次）；
IF34 检查 `sanitization_report` 行含最小键集说明；
IF35 检查 `ss_` 行含偏移形态说明；
IF36 检查 `sem_` 前缀在登记册出现；
IF37–IF39 为第 103 条 D2 新增（impl-00 返工 R83c）：§4 `sanitization_report` 行
若复述 `kind`／`terminal_state` 枚举，必须与代码常量逐一相等（IF37／IF38）；
代码常量必须与 impl-09 README《清洗发现》的权威闭集逐一相等（IF39）；
IF40 为第 107 条（W8 8.6 ACT 08）新增：M8 词条发号表 `entry_id_allocation` 登记；
IF41 检查 `graph_projection_pack` 边定义不含独立 ID 键（禁止 edge_id/id/e_）；
IF42 检查 `graph_projection_pack` 节点 ID 符合 ids.py 闭集且无 c_/e_ 前缀；
IF43 检查 `evidence_map_pack` 两变体（glyphbox 档与 offset 档）均恰含 7 键；
IF44 检查 M8 检查名闭集 23 项齐全，并如实报告与 `pipeline/dataset_compiler/gate.py` 的差异（XFAIL 处理）。
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

# 首纵切登记类型（IF02–IF09；编号与语义冻结，不得改动）
REQUIRED_TYPES = (
    "gate_results",
    "validation_package",
    "source_asset_page",
    "source_asset_register",
    "source_asset_pack",
    "evidence_map_pack",
    "release_manifest",
    "publication_package",
)
# M4 薄接入类型（IF19–IF23；impl-00/12 登记，显式编号）
M4_TYPES = (
    "candidate_submission",
    "candidate_lane_set",
    "dispute_queue",
    "candidate_set",
    "candidate_package",
)
# M6 薄接入类型（IF25–IF28；impl-00/13 登记，显式编号）
M6_TYPES = (
    "review_queue",
    "reviewed_edition",
    "reviewed_edition_package",
    "rework_impact_report",
)
# M2 电子文本类型（IF30–IF33；impl-00/14 登记，显式编号）
M2_ET_TYPES = (
    "raw_text",
    "cleaned_text_revision",
    "deterministic_patch_set",
    "sanitization_report",
)
# M8 W8 登记类型（IF40；impl-00/15 登记，显式编号，第 107 条 Q-M8-02）
M8_W8_TYPES = (
    "entry_id_allocation",
)

# M8 Gate 检查项 23 项闭集（第 107 条 Q-M8-08）
M8_CHECK_NAMES = (
    "span_identity",
    "span_page_binding",
    "text_offsets",
    "glyph_anchor_closure",
    "highlight_level",
    "ocr_page_binding",
    "source_asset_binding",
    "coordinate_frame",
    "reverse_index",
    "release_manifest_hashes",
    "input_reconciliation",
    "consumption_level",
    "watermark_disclosure",
    "knowledge_chain",
    "chain_closure",
    "no_assertion_bypass",
    "quote_hash_integrity",
    "content_status_admission",
    "offset_anchor_continuity",
    "patch_reversible",
    "raw_text_binding",
    "sanitization_disclosure",
    "graph_projection_closure",
)
M8_GATE_RELPATH = ("pipeline", "dataset_compiler", "gate.py")

FORBIDDEN_TYPES = ("gate_report", "validator_report")   # IF18
FORBIDDEN_M4_NAMES = ("candidate_batch", "model_run", "candidate_diff_report")   # IF24
FORBIDDEN_M6_TYPES = ("correction_request",)   # IF29（impl-06 D-10）
RULING_MARKERS = {
    "IF12": "not_compiled",
    "IF13": "corpus_only",
    "IF14": "只读 SELECT",
    "IF15": "页图字节登记进 Ledger",
    "IF16": "validation.passed",
    "IF17": "succeeded",
}
SECTION_START = "## 4."
SECTION_END = "## 5."
TOKEN_RE = re.compile(r"`([^`]+)`")
SEPARATOR_RE = re.compile(r"^\|[\s\-:|]+\|$")

# 第 103 条 D2：§4 `sanitization_report` 行若复述枚举，形态为 `` `kind` ∈ `{a, b}` ``
ENUM_CLAUSE_RE = "`%s`\\s*∈\\s*`\\{([^}]*)\\}`"
# 代码常量形态（pipeline/digitization/__init__.py）：NAME = ( "a", "b", )
CODE_TUPLE_RE = '^%s\\s*=\\s*\\(([^)]*)\\)'
# impl-09 README 权威闭集行首：``**`kind` 闭集**``
README_SET_PREFIX = "**`%s` 闭集**"
# M2 清洗发现的权威来源（第 85、103 条 D2）
M2_CONSTANTS_RELPATH = ("pipeline", "digitization", "__init__.py")
IMPL09_README_RELPATH = ("impl-09-intake", "README.md")

IF_NAMES = {
    "IF01": "§4 表存在且数据行 ≥ 15",
    "IF10": "artifact_type 无重复",
    "IF11": "required 类型行未标 DEFERRED/纵切后",
    "IF18": "§4 表不含 gate_report 与 validator_report",
    "IF24": "§4 表不含旧 M4 名 candidate_batch / model_run / candidate_diff_report",
    "IF29": "§4 表不含 correction_request（D-10 归 human_event）",
    "IF34": "sanitization_report 行含最小键集说明",
    "IF35": "ss_ 行含偏移形态说明",
    "IF36": "sem_ 前缀在登记册出现",
    "IF37": "sanitization_report 行的 kind 枚举（若复述）== 代码常量 FINDING_KINDS",
    "IF38": "sanitization_report 行的 terminal_state 枚举（若复述）== 代码常量 TERMINAL_STATES",
    "IF39": "代码常量 FINDING_KINDS/TERMINAL_STATES == impl-09 README 权威闭集",
    "IF40": "M8 词条发号表 entry_id_allocation 登记",
    "IF41": "graph_projection_pack 边定义无独立 ID",
    "IF42": "graph_projection_pack 节点 ID 符合 ids.py 闭集且无 c_/e_",
    "IF43": "evidence_map_pack 两变体均恰含 7 键",
    "IF44": "M8 检查名闭集 23 项齐全且如实报告 gate.py 差异",
}
# IF02–IF09：首纵切 required 类型
for _i, _t in enumerate(REQUIRED_TYPES):
    IF_NAMES["IF%02d" % (_i + 2)] = "required 类型 %s" % _t
# IF19–IF23：M4 required 类型（显式编号，避免占用 IF10/IF11）
for _i, _t in enumerate(M4_TYPES):
    IF_NAMES["IF%02d" % (_i + 19)] = "M4 required 类型 %s" % _t
# IF25–IF28：M6 required 类型（显式编号）
for _i, _t in enumerate(M6_TYPES):
    IF_NAMES["IF%02d" % (_i + 25)] = "M6 required 类型 %s" % _t
# IF30–IF33：M2 电子文本 required 类型（显式编号）
for _i, _t in enumerate(M2_ET_TYPES):
    IF_NAMES["IF%02d" % (_i + 30)] = "M2 电子文本类型 %s" % _t
for _num, _marker in RULING_MARKERS.items():
    IF_NAMES[_num] = "标记 %s" % _marker


def name_of(num: str) -> str:
    """返回检查项的显示名。"""
    return IF_NAMES.get(num, num)


def parse_table(text: str) -> list:
    """返回 §4 表的数据行（每行按 `|` 分列去空白），排除表头与分隔行。"""
    lines = text.splitlines()
    start = end = None
    for i, line in enumerate(lines):
        if start is None:
            if line.startswith(SECTION_START):
                start = i
            continue
        if line.startswith(SECTION_END):
            end = i
            break
    if start is None:
        return []
    if end is None:
        end = len(lines)
    rows = []
    for line in lines[start + 1:end]:
        stripped = line.strip()
        if not stripped.startswith("|") or SEPARATOR_RE.match(stripped):
            continue
        rows.append([cell.strip() for cell in stripped.strip("|").split("|")])
    return rows[1:] if rows else []


def type_names(rows) -> list:
    """取每行第二列（artifact_type）反引号内的名字，按出现顺序返回。"""
    names = []
    for cells in rows:
        if len(cells) >= 2:
            names.extend(TOKEN_RE.findall(cells[1]))
    return names


def _status_cell(rows, token: str):
    """返回 artifact_type 列含该名字的行的末列（状态），找不到返回 None。"""
    for cells in rows:
        if len(cells) >= 2 and token in TOKEN_RE.findall(cells[1]):
            return cells[-1] if cells else ""
    return None


def sanitization_row_text(rows) -> str:
    """返回 §4 表中 `sanitization_report` 那一行的全文（各列以空格连接）。"""
    for cells in rows:
        if len(cells) >= 2 and "sanitization_report" in TOKEN_RE.findall(cells[1]):
            return " ".join(cells)
    return ""


def enum_tokens(text: str, label: str):
    """取 `` `LABEL` ∈ `{a, b}` `` 的取值列表；未复述枚举时返回 None。"""
    match = re.search(ENUM_CLAUSE_RE % re.escape(label), text)
    if match is None:
        return None
    return [
        token.strip().strip("`")
        for token in match.group(1).split(",")
        if token.strip()
    ]


def code_tuple(text: str, name: str):
    """从代码文本取 ``NAME = ( "a", "b", )`` 的字符串元组；找不到返回 None。"""
    match = re.search(CODE_TUPLE_RE % re.escape(name), text, re.M)
    if match is None:
        return None
    return re.findall(r'"([^"]+)"', match.group(1))


def readme_closed_set(text: str, label: str):
    """从 impl-09 README 取 ``**`LABEL` 闭集**：...`` 行的反引号取值列表。"""
    for line in text.splitlines():
        if line.startswith(README_SET_PREFIX % label):
            return [token for token in TOKEN_RE.findall(line) if token != label]
    return None


def _repo_root() -> Path:
    """返回仓库根（本文件位于 docs/blackbox-spec-rework/work-items/impl-00-interfaces/）。"""
    return Path(__file__).resolve().parents[4]


def extract_section(text: str, start_header: str, end_header: str) -> str:
    """提取两个指定标题之间的文本。"""
    lines = text.splitlines()
    start = end = None
    for i, line in enumerate(lines):
        if start is None:
            if line.startswith(start_header):
                start = i
            continue
        if line.startswith(end_header):
            end = i
            break
    if start is None:
        return ""
    if end is None:
        end = len(lines)
    return "\n".join(lines[start:end])


def run_checks(
    path: Path,
    registry_path: Path | None = None,
    *,
    impl09_readme_path: Path | None = None,
    m2_constants_path: Path | None = None,
    gate_path: Path | None = None,
) -> list:
    """执行 IF01–IF44，返回 [(编号, 状态, 原因)]，按编号升序。"""
    try:
        text = Path(path).read_text(encoding="utf-8")
        rows = parse_table(text)
        names = type_names(rows)
        counts = Counter(names)
    except Exception as exc:  # noqa: BLE001
        detail = "%s: %s" % (type(exc).__name__, exc)
        return [(num, "FAIL", detail) for num in sorted(IF_NAMES)]

    out = []

    def add(num, ok, reason=""):
        out.append((num, "PASS" if ok else "FAIL", reason))

    add("IF01", len(rows) >= 15, "" if len(rows) >= 15 else "数据行=%d" % len(rows))
    # IF02–IF09：首纵切 required 类型
    for i, token in enumerate(REQUIRED_TYPES):
        count = counts.get(token, 0)
        add("IF%02d" % (i + 2), count == 1, "%s 出现 %d 次" % (token, count))
    dup = sorted(name for name, count in counts.items() if count > 1)
    add("IF10", not dup, "重复: %s" % ",".join(dup) if dup else "")
    bad_rows = []
    for token in REQUIRED_TYPES + M4_TYPES + M6_TYPES + M2_ET_TYPES + M8_W8_TYPES:
        status = _status_cell(rows, token)
        if status is None:
            bad_rows.append("%s 缺行" % token)
        elif "DEFERRED" in status or "纵切后" in status:
            bad_rows.append("%s 状态=%s" % (token, status))
    add("IF11", not bad_rows, "; ".join(bad_rows))
    for num, marker in RULING_MARKERS.items():
        add(num, marker in text, "" if marker in text else "缺 %s" % marker)
    forbidden = sorted({name for name in names if name in FORBIDDEN_TYPES})
    add("IF18", not forbidden, "出现 %s" % ",".join(forbidden) if forbidden else "")
    # IF19–IF23：M4 required 类型（显式编号）
    for i, token in enumerate(M4_TYPES):
        count = counts.get(token, 0)
        add("IF%02d" % (i + 19), count == 1, "%s 出现 %d 次" % (token, count))
    # IF24：§4 表不含旧 M4 名
    legacy = sorted({name for name in names if name in FORBIDDEN_M4_NAMES})
    add("IF24", not legacy, "出现 %s" % ",".join(legacy) if legacy else "")
    # IF25–IF28：M6 required 类型（显式编号）
    for i, token in enumerate(M6_TYPES):
        count = counts.get(token, 0)
        add("IF%02d" % (i + 25), count == 1, "%s 出现 %d 次" % (token, count))
    # IF29：§4 表不得把 correction_request 登记为独立 artifact_type（D-10）
    forbidden_m6 = sorted({name for name in names if name in FORBIDDEN_M6_TYPES})
    add("IF29", not forbidden_m6, "出现 %s" % ",".join(forbidden_m6) if forbidden_m6 else "")
    # IF30–IF33：M2 电子文本 required 类型（显式编号）
    for i, token in enumerate(M2_ET_TYPES):
        count = counts.get(token, 0)
        add("IF%02d" % (i + 30), count == 1, "%s 出现 %d 次" % (token, count))
    # IF34：sanitization_report 行含最小键集说明（finding_id 出现）
    add("IF34", "finding_id" in text, "" if "finding_id" in text else "缺 finding_id")
    # IF35：ss_ 行含偏移形态说明（o<NNNNNNN> 出现于登记册）
    if registry_path is None:
        _reg = Path(__file__).resolve().parent.parent.parent.parent.parent / "openspec" / "id-prefix-registry.md"
    else:
        _reg = registry_path
    _reg_text = _reg.read_text(encoding="utf-8") if _reg.is_file() else ""
    add("IF35", "o<NNNNNNN>" in _reg_text, "" if "o<NNNNNNN>" in _reg_text else "缺 o<NNNNNNN>")
    # IF36：sem_ 前缀在登记册出现
    if registry_path is None:
        registry_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "openspec" / "id-prefix-registry.md"
    registry_text = registry_path.read_text(encoding="utf-8") if registry_path.is_file() else ""
    add("IF36", "sem_" in registry_text, "" if "sem_" in registry_text else "缺 sem_")
    # IF37–IF39：第 103 条 D2（登记表不复述枚举；复述则须与代码常量、README 权威一致）
    _root = _repo_root()
    constants_path = m2_constants_path or _root.joinpath(*M2_CONSTANTS_RELPATH)
    readme_path = impl09_readme_path or (
        Path(__file__).resolve().parent.parent.joinpath(*IMPL09_README_RELPATH)
    )
    try:
        constants_text = constants_path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        constants_text = ""
    try:
        readme_text = readme_path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        readme_text = ""
    code_kinds = code_tuple(constants_text, "FINDING_KINDS")
    code_terminals = code_tuple(constants_text, "TERMINAL_STATES")
    row_text = sanitization_row_text(rows)

    for num, label, code_values in (
        ("IF37", "kind", code_kinds),
        ("IF38", "terminal_state", code_terminals),
    ):
        declared = enum_tokens(row_text, label)
        if code_values is None:
            add(num, False, "代码常量缺失: %s" % constants_path)
        elif declared is None:
            add(num, True, "未复述枚举（引用权威）")
        else:
            add(
                num,
                declared == code_values,
                "登记 %r != 代码常量 %r" % (declared, code_values),
            )

    if code_kinds is None or code_terminals is None:
        add("IF39", False, "代码常量缺失: %s" % constants_path)
    else:
        readme_kinds = readme_closed_set(readme_text, "kind")
        readme_terminals = readme_closed_set(readme_text, "terminal_state")
        problems = []
        if readme_kinds is None:
            problems.append("README 缺 kind 闭集行")
        elif readme_kinds != code_kinds:
            problems.append("kind 代码常量 %r != README %r" % (code_kinds, readme_kinds))
        if readme_terminals is None:
            problems.append("README 缺 terminal_state 闭集行")
        elif readme_terminals != code_terminals:
            problems.append(
                "terminal_state 代码常量 %r != README %r" % (code_terminals, readme_terminals)
            )
        add("IF39", not problems, "; ".join(problems))

    # IF40：M8 词条发号表 entry_id_allocation 登记（显式编号，第 107 条 Q-M8-02）
    count_eid = counts.get("entry_id_allocation", 0)
    add("IF40", count_eid == 1, "%s 出现 %d 次" % ("entry_id_allocation", count_eid))

    # IF41：graph_projection_pack 边定义无独立 ID（禁止 edge_id、id 或 e_ 边 ID，第 107 条 Q-M8-05）
    sec_315 = extract_section(text, "### 3.15", "### 3.16")
    sec_315_edges_fail = []
    if not sec_315:
        sec_315_edges_fail.append("缺 §3.15 graph_projection_pack")
    else:
        if re.search(r'edges\[\][^|]*\|[^|]*\b(?:edge_id|id)\b', sec_315):
            sec_315_edges_fail.append("edges[] 字段定义含 edge_id 或 id")
        if re.search(r'"edges"\s*:\s*\[[^\]]*"(?:edge_id|id)"\s*:', sec_315):
            sec_315_edges_fail.append("edges 示例 JSON 含 edge_id 或 id")
        if re.search(r'["\']e_[0-9a-zA-Z]+["\']', sec_315):
            sec_315_edges_fail.append("出现 e_ 边 ID")
    add("IF41", not sec_315_edges_fail, "; ".join(sec_315_edges_fail))

    # IF42：graph_projection_pack 登记的 node_id 前缀均在 ids.py 闭集内，严禁 c_ / e_（第 107 条更正）
    sec_315_nodes_fail = []
    if not sec_315:
        sec_315_nodes_fail.append("缺 §3.15 graph_projection_pack")
    else:
        if re.search(r'"node_id"\s*:\s*"(?:c|e)_[^"]+"', sec_315):
            sec_315_nodes_fail.append("node_id 示例含未登记的 c_ 或 e_ 前缀")
        if re.search(r'"(?:source|target)"\s*:\s*"(?:c|e)_[^"]+"', sec_315):
            sec_315_nodes_fail.append("边 source/target 引用含未登记的 c_ 或 e_ 前缀")
        if "c_" not in sec_315 or "e_" not in sec_315:
            sec_315_nodes_fail.append("未明确说明禁止 c_ / e_ 前缀")
        node_ids = re.findall(r'"node_id"\s*:\s*"([^"]+)"', sec_315)
        if not node_ids:
            sec_315_nodes_fail.append("缺示例 node_id")
        else:
            valid_prefixes = ("pat_", "co_", "as_", "sv_", "cg_")
            for nid in node_ids:
                if not any(nid.startswith(p) for p in valid_prefixes):
                    sec_315_nodes_fail.append("node_id %r 前缀非合法前缀" % nid)
    add("IF42", not sec_315_nodes_fail, "; ".join(sec_315_nodes_fail))

    # IF43：evidence_map_pack 两变体均恰含 7 键（第 107 条 Q-M8-07 否决 8 段）
    sec_310 = extract_section(text, "### 3.10", "### 3.11")
    sec_310_fail = []
    if not sec_310:
        sec_310_fail.append("缺 §3.10 evidence_map_pack")
    else:
        if "恰含 7 个键" not in sec_310 and "恰 7 键" not in sec_310:
            sec_310_fail.append("未明文声明恰含 7 个键")
        for m in re.finditer(r'[8八]\s*(?:段|键|个键)', sec_310):
            prefix = sec_310[max(0, m.start() - 10):m.start()]
            if not any(neg in prefix for neg in ("否决", "禁止", "非", "不得", "不采纳")):
                sec_310_fail.append("出现 8 键或 8 段描述: %s" % m.group(0))
        for k in ("entry_id", "assertion_id", "evidence_link", "source_span", "source_anchor"):
            if k not in sec_310:
                sec_310_fail.append("缺公共键 %s" % k)
        for k in ("ocr_page", "source_asset", "text_mapping"):
            if k not in sec_310:
                sec_310_fail.append("缺分派键 %s" % k)
    add("IF43", not sec_310_fail, "; ".join(sec_310_fail))

    # IF44：M8 检查名闭集 23 项齐全且如实报告 gate.py 差异（第 107 条 Q-M8-08）
    sec_33 = extract_section(text, "### 3.3", "### 3.4")
    tokens_in_sec_33 = set(TOKEN_RE.findall(sec_33))
    missing_in_doc = [chk for chk in M8_CHECK_NAMES if chk not in tokens_in_sec_33]
    if missing_in_doc:
        add("IF44", False, "INTERFACES §3.3 缺检查项: %s" % ", ".join(missing_in_doc))
    else:
        gate_file = gate_path or _root.joinpath(*M8_GATE_RELPATH)
        try:
            gate_text = gate_file.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            gate_text = ""
        gate_checks = code_tuple(gate_text, "_CHECK_NAMES")
        if gate_checks is None:
            m_chk = re.search(r'_CHECK_NAMES\s*=\s*\(([^)]*)\)', gate_text, re.M)
            if m_chk:
                gate_checks = re.findall(r'"([^"]+)"', m_chk.group(1))
        if gate_checks is None:
            add("IF44", False, "gate.py 缺失或无法解析 _CHECK_NAMES: %s" % gate_file)
        else:
            missing_in_gate = sorted(set(M8_CHECK_NAMES) - set(gate_checks))
            if missing_in_gate:
                add(
                    "IF44",
                    True,
                    "XFAIL: gate.py 待实现新增 %d 项检查: %s" % (
                        len(missing_in_gate), ", ".join(missing_in_gate)
                    ),
                )
            else:
                add("IF44", True, "gate.py 已与登记册 23 项检查一致")

    out.sort(key=lambda item: item[0])
    return out


def main(argv=None) -> int:
    args = list(sys.argv[1:]) if argv is None else list(argv)
    path = Path(__file__).resolve().parent / "INTERFACES.md"
    i = 0
    while i < len(args):
        if args[i] == "--file" and i + 1 < len(args):
            path = Path(args[i + 1])
            i += 2
        else:
            i += 1
    if not path.is_file():
        print("I00-IF BLOCKED 前置缺失: INTERFACES.md 不存在")
        return 3
    npass = nfail = 0
    for num, status, reason in run_checks(path):
        line = "%s %s %s" % (status, num, name_of(num))
        if reason:
            line += " %s" % reason
        print(line)
        if status == "PASS":
            npass += 1
        else:
            nfail += 1
    print("I00-IF SUMMARY pass=%d fail=%d" % (npass, nfail))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
