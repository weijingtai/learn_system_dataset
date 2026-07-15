#!/usr/bin/env python3
"""双路合并（以 A 路为忠实主干，B 路作查漏）。
用法: merge_assertions.py <任务包目录> <主干draft A> <查漏draft B>
产出: output/merge_review.yaml —— A 全采用；B 中"A 未覆盖"的条目列为 candidate 待人工裁。
不自动并入 B（B 可能意译/改写），只标出 B 独有条目供人工核对。"""
import sys
import re
import yaml
from collections import defaultdict


def load(path):
    by = defaultdict(list)
    for a in yaml.safe_load(open(path)).get("assertions", []):
        for ev in a.get("evidence", []):
            by[ev.get("source_span_id", "")].append(a.get("proposition", ""))
    return by


def norm(s):
    return set(re.sub(r"[，。；、！？\s]", "", s))


def covered(prop_b, props_a):
    """B 的某条是否已被 A 覆盖：字符重合度≥0.6 视为同一主张。"""
    cb = norm(prop_b)
    for pa in props_a:
        ca = norm(pa)
        if not (ca | cb):
            continue
        if len(ca & cb) / len(ca | cb) >= 0.6:
            return True
    return False


def main():
    task_dir, fa, fb = sys.argv[1], sys.argv[2], sys.argv[3]
    A = load(f"{task_dir}/output/{fa}")
    B = load(f"{task_dir}/output/{fb}")
    review = {}
    n_cand = 0
    for sp in sorted(set(A) | set(B)):
        b_only = [p for p in B.get(sp, []) if not covered(p, A.get(sp, []))]
        if b_only:
            review[sp] = {
                "a_props": A.get(sp, []),
                "b_only_candidates": b_only,
            }
            n_cand += len(b_only)
    out = f"{task_dir}/output/merge_review.yaml"
    yaml.dump({"task": task_dir.split("/")[-1],
               "a_total": sum(len(v) for v in A.values()),
               "b_only_segments": len(review),
               "b_only_candidates": n_cand,
               "review": review},
              open(out, "w"), allow_unicode=True, sort_keys=False)
    print(f"{task_dir.split('/')[-1]}: A主干{sum(len(v) for v in A.values())}条  "
          f"B独有待核{n_cand}条(分布{len(review)}段) -> {out}")


if __name__ == "__main__":
    main()
