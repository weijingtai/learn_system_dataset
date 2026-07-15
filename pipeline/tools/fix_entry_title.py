#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_entry_title.py —— 修复 C 类 draft 中 entry_title 丢天干的问题
（b030–b041 脚本生成 draft 遗留：entry_title="二月" 应为 "二月辛金"）

原理：entry_title 应是原文完整标目（月令+天干），从 path 的上级节点补天干。
      path 形如 "十干分论 / 论辛金 / 三春辛金 / 二月"，上级"三春辛金"含天干"辛金"，
      末级"二月" + 天干 = "二月辛金"。只改 entry_title，绝不碰 text（忠实性不受影响）。

安全性：
- 只在 entry_title 含"月"但不含对应天干时才补；已完整的不动；
- 天干从 path 上级用正则提取，提不出则跳过并报告（不猜）；
- 修改前后打印对照，dry-run 默认关闭需显式 --write。

用法：
    python3 tools/fix_entry_title.py <corpus目录> [--write]
"""
import re
import sys
from pathlib import Path

import yaml

PIPELINE = Path(__file__).resolve().parent.parent
GAN = "甲乙丙丁戊己庚辛壬癸"
# 天干+五行名（论X木/X火…），从 path 上级节点提取
GANWX_RE = re.compile(f"([{GAN}](?:木|火|土|金|水))")


def main():
    corpus = Path(sys.argv[1])
    write = "--write" in sys.argv
    batches = yaml.safe_load((corpus / "batches.yaml").read_text())["batches"]

    fixed, skipped = [], []
    for b in batches:
        draft = PIPELINE / b["task_dir"] / "output/draft_opencode.yaml"
        if not draft.exists():
            continue
        data = yaml.safe_load(draft.read_text())
        changed = False
        for s in data.get("segments", []):
            et = str(s.get("entry_title", ""))
            path = str(s.get("path", ""))
            if "月" not in et:
                continue
            # 从 path 上级节点提天干五行（如"三春辛金"→"辛金"）
            m = GANWX_RE.findall(path)
            if not m:
                skipped.append(f'{b["batch_id"]}/{s.get("seg_id")}: path 无天干可补 "{path}"')
                continue
            ganwx = m[-1]  # 取最靠近末级的天干五行
            if ganwx[0] in et:
                continue  # 已含天干，完整，不动
            new_et = et + ganwx  # "二月" + "辛金" = "二月辛金"
            fixed.append(f'{b["batch_id"]}/{s.get("seg_id")}: "{et}" → "{new_et}"')
            s["entry_title"] = new_et
            changed = True
        if changed and write:
            draft.write_text(
                yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    print(f"{'已修复' if write else '待修复(dry-run)'} {len(fixed)} 处：")
    for f in fixed:
        print(f"  {f}")
    if skipped:
        print(f"跳过 {len(skipped)} 处（需人工看）：")
        for s in skipped:
            print(f"  {s}")
    if not write and fixed:
        print("\n加 --write 执行实修。")


if __name__ == "__main__":
    main()
