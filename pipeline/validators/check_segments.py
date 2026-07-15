#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_segments.py —— 工位 3（语义切分）输出的确定性校验

用法：
    python3 validators/check_segments.py <任务包目录> [--type A|B|C|D]
    默认检查任务包 output/ 下最新一次运行的 response.yaml；
    也可用 --file 指定任意 segments YAML。

检查项（错误码）：
    SEG_001  覆盖不等：所有段 text 拼接（去空白）≠ input/text.md 原文（去空白）
    SEG_002  半联结尾（仅 --type A）：段以"，、；"结尾，疑似把一联腰斩
    SEG_003  seg_id 格式或顺序错误（应为 s01、s02… 连续递增）
    SEG_004  text 或 note 为空
    SEG_005  段长超限（仅 --type B）：单段超过 300 字，疑似含多个论点（警告，不阻塞）
    SEG_008  类型 C 缺 entry_title / path 字段（阻塞）
    SEG_009  类型 C 段内疑似嵌入命例（≥2 干支组合）却未标 case_candidate（警告）
    SEG_010  类型 C 的 entry_title 丢天干（只有月令，如"二月"应为"二月辛金"）（阻塞）

退出码：0 = PASS（可含警告）；1 = FAIL。只报错，不修改任何文件。
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

WS = re.compile(r"\s+")


def norm(s):
    return WS.sub("", s)


def latest_response(task_dir):
    outs = sorted((task_dir / "output").glob("*/response.yaml"))
    return outs[-1] if outs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task_dir")
    ap.add_argument("--type", default=None, choices=["A", "B", "C", "D"],
                    help="文本类型（HANDBOOK 第 3 章）；A 启用半联检测，B 启用段长警告")
    ap.add_argument("--file", default=None, help="直接指定 segments YAML 文件")
    args = ap.parse_args()

    task_dir = Path(args.task_dir)
    seg_file = Path(args.file) if args.file else latest_response(task_dir)
    input_file = task_dir / "input" / "text.md"

    errors, warnings = [], []

    if seg_file is None or not seg_file.exists():
        print("FAIL  找不到切分结果文件（output/*/response.yaml 或 --file）")
        sys.exit(1)
    if not input_file.exists():
        print("FAIL  找不到 input/text.md")
        sys.exit(1)

    try:
        data = yaml.safe_load(seg_file.read_text(encoding="utf-8"))
        segments = data["segments"]
        assert isinstance(segments, list) and segments
    except Exception as e:
        print(f"FAIL  SEG_003 | {seg_file} | 无法解析出 segments 列表: {e}")
        sys.exit(1)

    # SEG_003 / SEG_004
    for i, s in enumerate(segments, start=1):
        sid = s.get("seg_id", "")
        expect = f"s{i:02d}"
        if sid != expect:
            errors.append(f"SEG_003 | {sid or '(空)'} | 应为 {expect}（连续递增，两位补零）")
        if not str(s.get("text", "")).strip():
            errors.append(f"SEG_004 | {sid} | text 为空")
        if not str(s.get("note", "")).strip():
            errors.append(f"SEG_004 | {sid} | note 为空")

    # SEG_001 覆盖检查
    joined = norm("".join(str(s.get("text", "")) for s in segments))
    original = norm(input_file.read_text(encoding="utf-8"))
    if joined != original:
        # 给出第一处分歧位置，帮助定位
        pos = next((k for k in range(min(len(joined), len(original)))
                    if joined[k] != original[k]), min(len(joined), len(original)))
        errors.append(
            f"SEG_001 | 全文 | 拼接与原文不一致（长度 {len(joined)} vs {len(original)}，"
            f"首个分歧在第 {pos + 1} 字附近：拼接『…{joined[max(0,pos-5):pos+5]}…』 "
            f"原文『…{original[max(0,pos-5):pos+5]}…』）")

    # SEG_002 半联（类型 A）
    if args.type == "A":
        for s in segments:
            if str(s.get("text", "")).rstrip().endswith(("，", "、", "；")):
                errors.append(f"SEG_002 | {s.get('seg_id')} | 段以逗号/顿号/分号结尾，疑似半联被腰斩"
                              "（类型 A 应按联或完整意群切，见 HANDBOOK 第 3 章）")

    # SEG_005 段长（类型 B）
    if args.type == "B":
        for s in segments:
            if len(norm(str(s.get("text", "")))) > 300:
                warnings.append(f"SEG_005 | {s.get('seg_id')} | 段长超 300 字，检查是否含多个论点")

    # SEG_006 连续 ≥5 段 note 完全相同（WARN）
    run_start = 0
    for i in range(1, len(segments)):
        prev_note = segments[i - 1].get("note", "")
        cur_note = segments[i].get("note", "")
        if prev_note == cur_note and prev_note:
            continue
        run_len = i - run_start
        if run_len >= 5:
            first = segments[run_start].get("seg_id", "?")
            last = segments[i - 1].get("seg_id", "?")
            warnings.append(
                f"SEG_006 | {first}–{last} | 连续 {run_len} 段 note 完全相同"
                f"（\"{prev_note[:40]}...\"），疑似批量复制")
        run_start = i
    # 检查末尾段
    run_len = len(segments) - run_start
    if run_len >= 5:
        first = segments[run_start].get("seg_id", "?")
        last = segments[-1].get("seg_id", "?")
        same_note = segments[run_start].get("note", "")
        warnings.append(
            f"SEG_006 | {first}–{last} | 连续 {run_len} 段 note 完全相同"
            f"（\"{same_note[:40]}...\"），疑似批量复制")

    # SEG_007 段 text 含编者标记（括号/方括号）（WARN）
    BRACKET_RE = re.compile(r"[()（）\[\]【】]")
    for s in segments:
        if BRACKET_RE.search(str(s.get("text", ""))):
            warnings.append(
                f"SEG_007 | {s.get('seg_id')} | 段含编者标记（括号/方括号），"
                "确认 editorial_notes 已覆盖")

    # 类型 D：layer / attached_to
    if args.type == "D":
        for s in segments:
            if "layer" not in s:
                errors.append(
                    f"SEG_003 | {s.get('seg_id')} | 类型 D 缺少 layer 字段")
            elif s.get("layer") == "commentary":
                if "attached_to" not in s or not s.get("attached_to"):
                    errors.append(
                        f"SEG_003 | {s.get('seg_id')} | layer=commentary 缺少 attached_to")
                if "commentator" not in s:
                    errors.append(
                        f"SEG_003 | {s.get('seg_id')} | layer=commentary 缺少 commentator")

    # 类型 C（条目/表格）：entry_title / path 必填 + 命例检测
    # 依据：HANDBOOK 3.2（条目式一条一段）＋ 试运行章程第 2、3 条
    #   —— 条目的路径条件必须落到 path 字段（下游主张的 conditions 要继承它）；
    #   —— 嵌入的举例命造是 Case 候选，不是主张，切分阶段先标出来提醒工位 5。
    if args.type == "C":
        # 干支组合：十天干 + 十二地支，用于识别命例（如"甲午日庚午时""甲子、乙丑"）
        GAN = "甲乙丙丁戊己庚辛壬癸"
        ZHI = "子丑寅卯辰巳午未申酉戌亥"
        GANZHI_RE = re.compile(f"[{GAN}][{ZHI}]")
        # 天干五行（论X木/三春X金…），用于校验 entry_title 是否丢天干
        GANWX_RE = re.compile(f"[{GAN}](?:木|火|土|金|水)")
        for s in segments:
            sid = s.get("seg_id", "")
            et = str(s.get("entry_title", "")).strip()
            path = str(s.get("path", ""))
            if not et:
                errors.append(
                    f"SEG_008 | {sid} | 类型 C 缺少 entry_title（条目标目，如『正月甲木』）")
            if not str(s.get("path", "")).strip():
                errors.append(
                    f"SEG_008 | {sid} | 类型 C 缺少 path（条目路径，如『论甲木 / 三春甲木 / 正月』"
                    "——下游主张的 conditions 要继承此路径条件）")
            # SEG_010 entry_title 丢天干：含"月"却不含天干五行，但 path 上级有天干可参照
            if et and "月" in et and not GANWX_RE.search(et):
                path_gan = GANWX_RE.findall(path)
                if path_gan:
                    errors.append(
                        f"SEG_010 | {sid} | entry_title『{et}』只有月令、丢了天干"
                        f"（应为『{et}{path_gan[-1]}』，路径含『{path_gan[-1]}』）——"
                        "entry_title 必须是完整标目，严禁脚本机械切割丢字")
            # 命例检测：段内出现 ≥2 个干支组合，疑似举例命造，须标 case_candidate
            text = str(s.get("text", ""))
            ganzhi_hits = GANZHI_RE.findall(text)
            if len(ganzhi_hits) >= 2 and not s.get("case_candidate"):
                warnings.append(
                    f"SEG_009 | {sid} | 段内含 {len(ganzhi_hits)} 处干支组合"
                    f"（{'、'.join(ganzhi_hits[:4])}…），疑似嵌入命例。"
                    "若为举例命造须标 case_candidate: true，工位 5 不得提成主张")

    for w in warnings:
        print(f"WARN  {w}")
    if errors:
        print(f"FAIL  {task_dir.name}  （{len(errors)} 条错误）")
        for e in errors:
            print(f"      {e}")
        sys.exit(1)
    print(f"PASS  {task_dir.name}  （{len(segments)} 段，覆盖完整）")
    sys.exit(0)


if __name__ == "__main__":
    main()
