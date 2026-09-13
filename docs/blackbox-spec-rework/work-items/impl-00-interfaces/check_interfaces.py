#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""impl-00/12：INTERFACES.md §4 临时闭集登记检查器（IF01–IF24）。

只用标准库。按行解析 `INTERFACES.md` 的 §4 表，逐项判定并输出
`PASS IFnn <名>` / `FAIL IFnn <名> <原因>`，末行 `I00-IF SUMMARY pass=<n> fail=<n>`。
文件缺失时输出 `I00-IF BLOCKED 前置缺失: INTERFACES.md 不存在` 并返回 3。

IF01–IF18 为 impl-00/10 首纵切登记检查，编号与语义冻结（现有用例依赖）；
IF19–IF23 为 impl-00/12 新增的 M4 五个类型（各在 §4 表出现恰一次）；
IF24 禁止 §4 表残留旧 M4 名。
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
FORBIDDEN_TYPES = ("gate_report", "validator_report")   # IF18
FORBIDDEN_M4_NAMES = ("candidate_batch", "model_run", "candidate_diff_report")   # IF24
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

IF_NAMES = {
    "IF01": "§4 表存在且数据行 ≥ 15",
    "IF10": "artifact_type 无重复",
    "IF11": "required 类型行未标 DEFERRED/纵切后",
    "IF18": "§4 表不含 gate_report 与 validator_report",
    "IF24": "§4 表不含旧 M4 名 candidate_batch / model_run / candidate_diff_report",
}
# IF02–IF09：首纵切 required 类型
for _i, _t in enumerate(REQUIRED_TYPES):
    IF_NAMES["IF%02d" % (_i + 2)] = "required 类型 %s" % _t
# IF19–IF23：M4 required 类型（显式编号，避免占用 IF10/IF11）
for _i, _t in enumerate(M4_TYPES):
    IF_NAMES["IF%02d" % (_i + 19)] = "M4 required 类型 %s" % _t
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


def run_checks(path: Path) -> list:
    """执行 IF01–IF24，返回 [(编号, 状态, 原因)]，按编号升序。"""
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
    for token in REQUIRED_TYPES + M4_TYPES:
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
