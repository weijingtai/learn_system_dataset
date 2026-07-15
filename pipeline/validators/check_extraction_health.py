#!/usr/bin/env python3
"""工位5 提取健康度体检（单路流程的程序兜底）。
用法: check_extraction_health.py <任务包目录> [draft文件名(默认 authoritative.yaml)]

三查（对应三次真实事故的程序化闭合检查）：
  EXT_001 覆盖缺口：段既无主张也不在 skipped
  EXT_002 命例误丢：case_candidate 段被整段 skip 且无四柱命造特征（连续干支<2组）
          —— 2026-07-14 case_candidate 语义误读事故的兜底
  EXT_003 欠提取：长段(>200字)提取主张数显著低于断语分句数
          —— 2026-07-14 单模型"抓大放小"事故的兜底
任何一项非空即 FAIL。单路提取签发前必须 PASS。"""
import sys
import re
import yaml
from pathlib import Path
from collections import defaultdict

GZ = re.compile(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]")
VERB = re.compile(r"(用|取|佐|忌|喜|宜|主|定主|可许|不可|非.{0,3}不|得|作|名为?|"
                  r"方妙|方可|须|亦|之造|之人|下贱|贫|富|贵|夭)")
UNDER_LEN = 200      # 超过此字数才算"长段"
UNDER_RATIO = 0.5    # 提取数 < 断语句数 * 此比例 → 疑似欠提


def main():
    task_dir = Path(sys.argv[1])
    draft = sys.argv[2] if len(sys.argv) > 2 else "authoritative.yaml"
    segs = {s["span_id"]: s for s in
            yaml.safe_load((task_dir / "input/segments.yaml").read_text(encoding="utf-8"))["segments"]}
    d = yaml.safe_load((task_dir / "output" / draft).read_text(encoding="utf-8"))

    cnt = defaultdict(int)
    for a in d.get("assertions", []):
        for ev in a.get("evidence", []):
            cnt[ev.get("source_span_id", "")] += 1
    skipped = set()
    for s in d.get("skipped_segments", []):
        k = (s.get("span_id") or s.get("seg_id")) if isinstance(s, dict) else s
        skipped.add(k if k in segs else next((x for x in segs if x.endswith(k)), k))

    errors = []
    for sp, s in segs.items():
        text = s.get("text", "")
        n = cnt[sp]
        # EXT_001 覆盖缺口
        if n == 0 and sp not in skipped:
            errors.append(f"EXT_001 段 {sp} 无主张也不在 skipped_segments（覆盖缺口）")
        # EXT_002 命例误丢
        if s.get("case_candidate") and sp in skipped and n == 0 and len(GZ.findall(text)) < 2:
            errors.append(f"EXT_002 段 {sp}（case_candidate）被整段 skip 且无四柱命造"
                          f"（连续干支{len(GZ.findall(text))}组）——疑把通则误当命例丢")
        # EXT_003 欠提取
        if n > 0 and len(text) > UNDER_LEN:
            rc = len([c for c in re.split(r"[。；]", text) if len(c) > 5 and VERB.search(c)])
            if n < rc * UNDER_RATIO:
                errors.append(f"EXT_003 段 {sp} {len(text)}字含约{rc}个断语句，仅提{n}条"
                              f"（疑抓大放小欠提取）")

    if errors:
        print(f"FAIL  {task_dir.name}  （{len(errors)} 条）")
        for e in errors:
            print(f"      {e}")
        sys.exit(1)
    na = len(d.get("assertions", []))
    print(f"PASS  {task_dir.name}  （{na}主张，覆盖/命例/欠提取三查通过）")
    sys.exit(0)


if __name__ == "__main__":
    main()
