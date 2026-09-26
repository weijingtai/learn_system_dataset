#!/usr/bin/env python3
"""实验脚本（不接生产线）：词典 + 原文逐字匹配识别概念提及，
在《乾元秘旨》M4「天官/七煞」41 个片段上跑一遍，输出命中清单。

用法：
    python3 pipeline/tools/experiments/dict_mention_eval.py

只读，不改任何生产文件；输出写到本脚本旁的 matches.yaml（人工检查用）。

匹配算法：对每个片段的 text，从左到右扫描字符位置；在每个位置尝试词典中
「最长的、以该位置为起点且逐字相等」的 surface；命中则记录并跳过该长度，
否则位置 +1。词典最长 surface 为 2 个字，故等价于「2 字优先，否则退化到 1 字」。
"""
from __future__ import annotations

import pathlib
import sys

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CORPUS_DIR = REPO_ROOT / "pipeline/corpus/_fixture/qianyuan_ed01_text"
DICT_PATH = REPO_ROOT / "docs/research/2026-09-26-dict-vs-model/dictionary.yaml"
OUT_PATH = pathlib.Path(__file__).resolve().parent / "matches.yaml"

RAW_START = 8663
RAW_END = 9397


def load_terms() -> list[str]:
    d = yaml.safe_load(DICT_PATH.read_text(encoding="utf-8"))
    terms = sorted({t["surface"] for t in d["terms"]}, key=len, reverse=True)
    return terms


def load_target_spans() -> list[dict]:
    d = yaml.safe_load((CORPUS_DIR / "spans.yaml").read_text(encoding="utf-8"))
    spans = d["spans"]
    sel = [
        s
        for s in spans
        if s["source_anchor"]["raw_start"] >= RAW_START
        and s["source_anchor"]["raw_end"] <= RAW_END
    ]
    sel.sort(key=lambda s: s["source_anchor"]["raw_start"])
    return sel


def match_span(text: str, terms: list[str]) -> list[dict]:
    """最长优先逐字匹配，返回该片段内的命中列表（含片段内偏移）。"""
    hits = []
    i = 0
    n = len(text)
    while i < n:
        matched = None
        for term in terms:  # terms already sorted longest-first
            L = len(term)
            if i + L <= n and text[i : i + L] == term:
                matched = term
                break
        if matched:
            hits.append(
                {
                    "term": matched,
                    "span_local_start": i,
                    "span_local_end": i + len(matched),
                }
            )
            i += len(matched)
        else:
            i += 1
    return hits


def main() -> int:
    terms = load_terms()
    spans = load_target_spans()
    assert len(spans) == 41, f"期望 41 个片段，实得 {len(spans)}"

    all_matches = []
    for s in spans:
        text = s["text"]
        for h in match_span(text, terms):
            all_matches.append(
                {
                    "span_id": s["span_id"],
                    "term": h["term"],
                    "span_local_start": h["span_local_start"],
                    "span_local_end": h["span_local_end"],
                    "raw_start": s["source_anchor"]["raw_start"] + h["span_local_start"],
                    "raw_end": s["source_anchor"]["raw_start"] + h["span_local_end"],
                    "context": text,
                }
            )

    out = {
        "method": "dict_longest_match_v0",
        "dictionary": str(DICT_PATH.relative_to(REPO_ROOT)),
        "span_count": len(spans),
        "match_count": len(all_matches),
        "matches": all_matches,
    }
    OUT_PATH.write_text(
        yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    print(f"{len(spans)} spans scanned, {len(all_matches)} matches -> {OUT_PATH}")
    for m in all_matches:
        print(f"  {m['span_id']}\t{m['term']}\t[{m['raw_start']},{m['raw_end']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
