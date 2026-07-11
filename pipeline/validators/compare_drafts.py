#!/usr/bin/env python3
"""compare_drafts.py — 双路盲提取草稿的结构化比对（T0-3）。

用法:
    python3 validators/compare_drafts.py <draft_a.yaml> <draft_b.yaml> [-o report.yaml]

职责边界（对齐 AGENT_GUIDE 分工）:
  - 本工具只做机械比对：按证据 span 集合对齐、字段级 diff、缺漏与拆合检测。
  - 命题文本是否语义一致（"措辞不同不算分歧"）属于仲裁判断，本工具
    只把配对双方的原文并排列出，供仲裁模型/人工裁决，不打分、不判胜负。
  - 输出为机器可读 YAML，可作为 review_compare.yaml 的底稿。
"""
import argparse
import sys
from collections import defaultdict

import yaml


def load_assertions(path):
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "assertions" not in data:
        sys.exit(f"错误: {path} 中没有 assertions 列表")
    return data["assertions"]


def span_key(assertion):
    spans = tuple(sorted(e["source_span_id"] for e in assertion.get("evidence", [])))
    return spans


def support_types(assertion):
    return sorted({e.get("support_type", "?") for e in assertion.get("evidence", [])})


def field_diffs(a, b):
    """机械可判的字段差异（不含命题文本语义）。"""
    diffs = {}
    if a.get("relation") != b.get("relation"):
        diffs["relation"] = {"a": a.get("relation"), "b": b.get("relation")}
    if support_types(a) != support_types(b):
        diffs["support_type"] = {"a": support_types(a), "b": support_types(b)}
    a_cond, b_cond = bool(a.get("conditions")), bool(b.get("conditions"))
    if a_cond != b_cond:
        diffs["conditions_presence"] = {"a": a_cond, "b": b_cond}
    a_exc, b_exc = bool(a.get("exceptions")), bool(b.get("exceptions"))
    if a_exc != b_exc:
        diffs["exceptions_presence"] = {"a": a_exc, "b": b_exc}
    if sorted(a.get("school_ids", [])) != sorted(b.get("school_ids", [])):
        diffs["school_ids"] = {"a": a.get("school_ids"), "b": b.get("school_ids")}
    return diffs


def brief(assertion):
    return {
        "assertion_id": assertion.get("assertion_id"),
        "proposition": assertion.get("proposition"),
        "spans": list(span_key(assertion)),
        "support_type": support_types(assertion),
        "conditions": assertion.get("conditions", []),
    }


def compare(a_list, b_list):
    a_by_key, b_by_key = defaultdict(list), defaultdict(list)
    for x in a_list:
        a_by_key[span_key(x)].append(x)
    for x in b_list:
        b_by_key[span_key(x)].append(x)

    report = {
        "summary": {},
        "paired": [],            # span 集合完全一致的配对 → 语义仲裁对象
        "split_merge": [],       # 同一 span 双方条数不同 → 拆合分歧（HANDBOOK: 一条一个命题）
        "partial_overlap": [],   # span 集合部分重叠 → 疑似跨段合并/上下文渗入
        "a_only": [],            # 仅 A 提取
        "b_only": [],            # 仅 B 提取
    }

    matched_a, matched_b = set(), set()
    for key in sorted(set(a_by_key) & set(b_by_key)):
        aa, bb = a_by_key[key], b_by_key[key]
        if len(aa) == len(bb):
            # 条数相等：组内按命题文本相似度贪心配对（相似度只用于排序配对，不用于语义裁决）
            import difflib
            pairs, used = [], set()
            for a in aa:
                best, best_r = None, -1.0
                for j, b in enumerate(bb):
                    if j in used:
                        continue
                    r = difflib.SequenceMatcher(
                        None, a.get("proposition", ""), b.get("proposition", "")).ratio()
                    if r > best_r:
                        best, best_r = j, r
                used.add(best)
                pairs.append((a, bb[best]))
            for a, b in pairs:
                report["paired"].append({
                    "spans": list(key),
                    "a": brief(a), "b": brief(b),
                    "mechanical_diffs": field_diffs(a, b) or "none",
                    "semantic_ruling": "PENDING_ARBITRATION",
                })
        else:
            report["split_merge"].append({
                "spans": list(key),
                "a_count": len(aa), "b_count": len(bb),
                "a": [brief(x) for x in aa], "b": [brief(x) for x in bb],
                "note": "双方对同一证据的命题条数不同，检查是否违反'一条一个命题'",
            })
        matched_a.update(id(x) for x in aa)
        matched_b.update(id(x) for x in bb)

    rest_a = [x for x in a_list if id(x) not in matched_a]
    rest_b = [x for x in b_list if id(x) not in matched_b]

    # 部分重叠匹配：单个 span 有交集即配对候选
    used_b = set()
    for a in list(rest_a):
        a_spans = set(span_key(a))
        for b in rest_b:
            if id(b) in used_b:
                continue
            if a_spans & set(span_key(b)):
                report["partial_overlap"].append({
                    "shared_spans": sorted(a_spans & set(span_key(b))),
                    "a": brief(a), "b": brief(b),
                    "note": "span 集合不一致但有交集：检查跨段合并或上下文渗入（参照 000004 之 s06 教训）",
                })
                used_b.add(id(b))
                rest_a.remove(a)
                break
    rest_b = [x for x in rest_b if id(x) not in used_b]

    report["a_only"] = [brief(x) for x in rest_a]
    report["b_only"] = [brief(x) for x in rest_b]

    n_pair = len(report["paired"])
    clean = sum(1 for p in report["paired"] if p["mechanical_diffs"] == "none")
    report["summary"] = {
        "a_total": len(a_list), "b_total": len(b_list),
        "paired_exact_spans": n_pair,
        "paired_no_mechanical_diff": clean,
        "split_merge_groups": len(report["split_merge"]),
        "partial_overlap_pairs": len(report["partial_overlap"]),
        "a_only": len(report["a_only"]), "b_only": len(report["b_only"]),
        "next_step": "对 paired 逐条做语义仲裁；split_merge/partial_overlap 按 HANDBOOK 裁决；"
                     "a_only/b_only 核对原文判断漏提还是多提",
    }
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("draft_a")
    p.add_argument("draft_b")
    p.add_argument("-o", "--out", default=None)
    args = p.parse_args()

    report = compare(load_assertions(args.draft_a), load_assertions(args.draft_b))
    text = yaml.safe_dump(report, allow_unicode=True, sort_keys=False, width=100)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"报告已写入 {args.out}")
        s = report["summary"]
        print(f"A={s['a_total']} B={s['b_total']} 配对={s['paired_exact_spans']} "
              f"无机械分歧={s['paired_no_mechanical_diff']} 拆合={s['split_merge_groups']} "
              f"部分重叠={s['partial_overlap_pairs']} 仅A={s['a_only']} 仅B={s['b_only']}")
    else:
        print(text)


if __name__ == "__main__":
    main()
