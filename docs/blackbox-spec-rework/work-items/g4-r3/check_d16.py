#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D-16 映射表检查器（check_d16.py）。

用法：
    python3 check_d16.py [--plan PLAN.md] [--spec openspec/learn-system-blackbox-architecture.md]

对应 ACT `blackbox-g4-r3/01` 的 checker 六条规则（R1–R6）：
  R1 新节存在且位置在 `## G4 黑箱 D 类规格` 与 `## G6 注解社区线` 之间，恰 1 次；
  R2 表 A 首列与规格 §19 主表首列名多重集相等（各恰 1 次），且第 4 列为存在的路径；
  R3 表 B 每行「开头文字」在 PLAN 中恰匹配 1 条 `- [ ] <开头>` 或 `- [x] <开头>` 行（未勾选与已勾选合计恰 1），标注 ∈ 三值，行数 ≥ 43；
  R4 PLAN 其余 `- [ ]` 行要么在表 B、要么在新节 C、要么位于 G6/注解社区各节；
  R5 新节 C 内以 `- [ ] ` 或 `- [x] ` 开头的行合计恰 3 条；每条含 `run_all.sh 20.`；每条
     `- [x]` 行必须含至少一个反引号包裹的 7–40 位小写十六进制提交号（正则
     `[0-9a-f]{7,40}` 夹在反引号内），否则 FAIL R5（R4 不变，仍只考察 `- [ ]` 行，
     节 C 的 `- [x]` 行不参与 R4）；
  R6 三个 owner 文件各恰 1 行含 `唯一登记处`，且含 `KnowledgeReleaseCompiler` 的行数各为 1。

任一失败输出 `D16 FAIL <规则号> <原因>` 并退出 1；全部通过输出 `D16 OK` 并退出 0。
不得用 try/except 吞错；文件缺失即 FAIL。
"""

import argparse
import os
import re
import sys

# 新节标题（逐字来自 ACT plan_section）
SECTION_HEADING = "## 黑箱差距 → PLAN 条目 → owner 映射（D-16，2026-09-11；只增不删）"
G4_PREFIX = "## G4 黑箱 D 类规格"
G6_PREFIX = "## G6 注解社区线"

# 规格 §19 主表所在区间的起止标题前缀
SPEC_START_PREFIX = "## 19."
SPEC_END_PREFIX = "## 20."

# 表 B 第 2 列的合法标注集合
LABELS = {"mapped", "superseded-by", "out-of-scope"}

# R5：反引号夹住的 7-40 位小写十六进制提交号
COMMIT_HASH_RE = re.compile(r"`[0-9a-f]{7,40}`")

# R6 的三个 owner 文件
OWNER_FILES = [
    "pipeline/TODO.md",
    "pattern_knowledge_workbench/TODO.md",
    "LEARN_SYSTEM_TARGET.md",
]

# R4 允许承接剩余未勾选项的 `## ` 节名闭集（不含 `## ` 前缀）
CLOSED_HEADS = {
    "G6 注解社区线（C/S 会话；与 Dataset 会话的 G3 线并行、互不暂存）",
    "NC-001 首包补齐",
    "注解社区 v1.5 同步",
    "注解社区：本轮工程准备",
    "注解社区：下一阶段准入",
    "注解社区 v1.4",
    "注解社区 R2 六项返工（v1.3）",
    "注解社区 v1.1 补充复核",
    "上下游生产交付核对回执",
    "注解社区线：跨 Agent 数据契约（2026-09-10）",
}


def fail(rule, reason):
    """统一失败出口：打印 `D16 FAIL <规则号> <原因>` 并退出 1。"""
    print("D16 FAIL %s %s" % (rule, reason))
    sys.exit(1)


def read_lines(path):
    """读取文件为行列表；文件缺失即 FAIL（不允许吞错）。"""
    if not os.path.exists(path):
        fail("R0", "文件缺失: %s" % path)
    with open(path, encoding="utf-8") as handle:
        return handle.read().split("\n")


def path_exists(path):
    """判断表内登记的 owner 路径是否真实存在（相对当前工作目录或仓库根）。"""
    return os.path.exists(path) or os.path.exists(os.path.join(os.getcwd(), path))


def is_heading(line):
    """是否 `## ` 一级节标题（排除 `### ` 三级标题）。"""
    return line.startswith("## ") and not line.startswith("### ")


def first_heading_index(lines, prefix):
    """返回首个以 prefix 开头的行号，找不到返回 -1。"""
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            return index
    return -1


def find_one_heading(lines, prefix, rule, label):
    """断言恰有 1 行以 prefix 开头，返回其行号。"""
    hits = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(hits) != 1:
        fail(rule, "%s 标题匹配数=%d（应恰 1）" % (label, len(hits)))
    return hits[0]


def region(lines, start_index, end_index):
    """取 [start_index+1, end_index) 区间；end_index 为 None 时取到文件尾。"""
    if end_index is None:
        return lines[start_index + 1:]
    return lines[start_index + 1:end_index]


def next_top_heading(lines, after):
    """返回 after 之后首个 `## ` 标题行号，找不到返回 len(lines)。"""
    for index in range(after + 1, len(lines)):
        if is_heading(lines[index]):
            return index
    return len(lines)


def sub_region(body, marker, offset):
    """在 body 中取 `### <marker>` 子节区间（到下一个 `### ` 或结束）。

    返回 (全局起始行号, 行列表)；offset 为 body 首行在整份 PLAN 中的全局行号。
    """
    hits = [i for i, line in enumerate(body) if line.startswith(marker)]
    if len(hits) != 1:
        fail("R2", "%s 子节匹配数=%d（应恰 1）" % (marker, len(hits)))
    start = hits[0]
    end = len(body)
    for index in range(start + 1, len(body)):
        if body[index].startswith("### "):
            end = index
            break
    return offset + start + 1, body[start + 1:end]


def table_blocks(lines):
    """拆出所有以 `|` 开始的连续行块，按出现顺序返回。"""
    blocks = []
    current = []
    for line in lines:
        if line.startswith("|"):
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def is_separator(row):
    """Markdown 表格分隔行（仅由 | - : 与空白组成且含 -）。"""
    stripped = row.strip()
    return "-" in stripped and set(stripped) <= set("|-: ")


def first_table_data_rows(lines):
    """取区间内第一张表的全部数据行（跳过表头与分隔行）。"""
    for block in table_blocks(lines):
        if len(block) >= 3 and is_separator(block[1]):
            return [row for row in block[2:] if row.strip()]
    return []


def cells(row):
    """把一行 Markdown 表格行拆成去空白的单元格列表（去掉首尾空单元）。"""
    text = row.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [cell.strip() for cell in text.split("|")]


def main():
    parser = argparse.ArgumentParser(description="D-16 映射表检查器")
    parser.add_argument("--plan", default="PLAN.md", help="PLAN.md 路径")
    parser.add_argument(
        "--spec",
        default="openspec/learn-system-blackbox-architecture.md",
        help="规格文件路径",
    )
    args = parser.parse_args()

    plan = read_lines(args.plan)
    spec = read_lines(args.spec)

    # ---- R1 新节存在且位置正确 ----
    hits = [i for i, line in enumerate(plan) if line.strip() == SECTION_HEADING]
    if len(hits) != 1:
        fail("R1", "新节标题匹配数=%d（应恰 1）" % len(hits))
    section_index = hits[0]
    g4_index = find_one_heading(plan, G4_PREFIX, "R1", G4_PREFIX)
    g6_index = find_one_heading(plan, G6_PREFIX, "R1", G6_PREFIX)
    if not (g4_index < section_index < g6_index):
        fail(
            "R1",
            "新节位置错：G4=%d 新节=%d G6=%d" % (g4_index, section_index, g6_index),
        )
    section_end = next_top_heading(plan, section_index)
    body = region(plan, section_index, section_end)
    body_offset = section_index + 1  # body[0] 在整份 PLAN 中的全局行号

    # ---- R2 表 A 对 §19 主表首列全覆盖 ----
    spec_start = find_one_heading(spec, SPEC_START_PREFIX, "R2", SPEC_START_PREFIX)
    spec_end = find_one_heading(spec, SPEC_END_PREFIX, "R2", SPEC_END_PREFIX)
    spec_rows = first_table_data_rows(region(spec, spec_start, spec_end))
    spec_firsts = [cells(row)[0] for row in spec_rows]
    if len(spec_firsts) != 19:
        fail("R2", "§19 主表数据行数=%d（应 19）" % len(spec_firsts))

    _, a_body = sub_region(body, "### A.", body_offset)
    a_rows = first_table_data_rows(a_body)
    a_firsts = []
    for row in a_rows:
        row_cells = cells(row)
        if len(row_cells) < 4:
            fail("R2", "表 A 行单元格数=%d（应 ≥4）: %s" % (len(row_cells), row))
        a_firsts.append(row_cells[0])
        owner = row_cells[3]
        if not (owner.startswith("`") and owner.endswith("`") and len(owner) > 2):
            fail("R2", "表 A 第 4 列非反引号路径: %s" % owner)
        if not path_exists(owner.strip("`")):
            fail("R2", "表 A owner 路径不存在: %s" % owner.strip("`"))
    if sorted(a_firsts) != sorted(spec_firsts):
        fail(
            "R2",
            "表 A 首列与 §19 主表不一致: 表A=%d §19=%d"
            % (len(a_firsts), len(spec_firsts)),
        )

    # ---- R3 表 B 每条开头文字恰匹配 1 行（未勾选或已勾选） ----
    _, b_body = sub_region(body, "### B.", body_offset)
    b_rows = first_table_data_rows(b_body)
    if len(b_rows) < 43:
        fail("R3", "表 B 数据行数=%d（应 ≥ 43）" % len(b_rows))
    matched_indices = set()
    for row in b_rows:
        row_cells = cells(row)
        if len(row_cells) < 2:
            fail("R3", "表 B 行单元格数=%d（应 ≥2）: %s" % (len(row_cells), row))
        head = row_cells[0]
        if not (head.startswith("「") and head.endswith("」") and len(head) > 2):
            fail("R3", "表 B 第 1 列非「开头文字」形式: %s" % head)
        prefix = head[1:-1]
        label = row_cells[1]
        if label not in LABELS:
            fail("R3", "表 B 标注非法: %s（%s）" % (label, prefix))
        hit_indices = [
            i
            for i, line in enumerate(plan)
            if line.startswith("- [ ] " + prefix)
            or line.startswith("- [x] " + prefix)
        ]
        if len(hit_indices) != 1:
            fail(
                "R3",
                "开头文字匹配数=%d（应 1）: %s" % (len(hit_indices), prefix),
            )
        matched_indices.add(hit_indices[0])

    # ---- R4 其余未勾选项必须落在闭集节内 ----
    c_start, c_body = sub_region(body, "### C.", body_offset)
    c_indices = {
        c_start + i for i, line in enumerate(c_body) if line.startswith("- [ ]")
    }
    c_lines = [
        line
        for line in c_body
        if line.startswith("- [ ] ") or line.startswith("- [x] ")
    ]

    nearest = None
    for index, line in enumerate(plan):
        if is_heading(line):
            nearest = line[3:].strip()
        if line.startswith("- [ ]"):
            # R4 只考察 `- [ ]` 行：R3 中匹配到 `- [x]` 的索引天然落不到本分支，
            # 故「减去 R3 匹配到的且仍为 `- [ ]` 的行」等价于下面这一次判断。
            if index in matched_indices:
                continue
            if index in c_indices:
                continue
            if nearest not in CLOSED_HEADS:
                fail("R4", "未覆盖未勾选项（节=%s）: %s" % (nearest, line))

    # ---- R5 新节 C 恰 3 条（`- [ ] ` 与 `- [x] ` 合计），各含 run_all.sh 20.，
    #      已勾选行须附反引号提交号 ----
    if len(c_lines) != 3:
        fail("R5", "新节 C 未勾选项数=%d（应 3）" % len(c_lines))
    for line in c_lines:
        if "run_all.sh 20." not in line:
            fail("R5", "新节 C 缺 run_all.sh 20. 判据: %s" % line)
        if line.startswith("- [x] ") and COMMIT_HASH_RE.search(line) is None:
            fail("R5", "新节 C 已勾选行缺反引号提交号: %s" % line)

    # ---- R6 唯一 owner 收敛 ----
    for path in OWNER_FILES:
        lines = read_lines(path)
        unique_count = sum(1 for line in lines if "唯一登记处" in line)
        if unique_count != 1:
            fail("R6", "%s 含 `唯一登记处` 行数=%d（应 1）" % (path, unique_count))
        compiler_count = sum(1 for line in lines if "KnowledgeReleaseCompiler" in line)
        if compiler_count != 1:
            fail(
                "R6",
                "%s 含 `KnowledgeReleaseCompiler` 行数=%d（应 1）"
                % (path, compiler_count),
            )

    print("D16 OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
