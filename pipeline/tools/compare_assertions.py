#!/usr/bin/env python3
"""双路主张比对器：按 span 对齐两路提取，暴露单边遗漏与拆分差异。
用法: compare_assertions.py <任务包目录> <路A draft> <路B draft>
交叉验证核心：同一段两路提取数差异大 = 有一路漏提或过度拆分，需人工定夺。"""
import sys
import yaml
from collections import defaultdict


def load(path):
    d = yaml.safe_load(open(path))
    by = defaultdict(list)
    for a in d.get("assertions", []):
        for ev in a.get("evidence", []):
            by[ev.get("source_span_id", "")].append(a.get("proposition", ""))
    return by


def main():
    task_dir, fa, fb = sys.argv[1], sys.argv[2], sys.argv[3]
    segs = {s["span_id"]: s for s in
            yaml.safe_load(open(f"{task_dir}/input/segments.yaml"))["segments"]}
    A = load(f"{task_dir}/output/{fa}")
    B = load(f"{task_dir}/output/{fb}")
    name = task_dir.split("/")[-1]
    ta = sum(len(v) for v in A.values())
    tb = sum(len(v) for v in B.values())
    print(f"{name}: A({fa})={ta}条  B({fb})={tb}条")
    print(f"{'段':<11}{'A提':<5}{'B提':<5}{'差':<5}标记")
    big = []
    for sp in sorted(segs):
        na, nb = len(A.get(sp, [])), len(B.get(sp, []))
        diff = abs(na - nb)
        flag = ""
        if na == 0 and nb > 0:
            flag = "A漏整段"
        elif nb == 0 and na > 0:
            flag = "B漏整段"
        elif diff >= 4:
            flag = f"差{diff}(核对遗漏)"
        if flag:
            big.append(sp)
            print(f"{sp[-9:]:<11}{na:<5}{nb:<5}{diff:<5}{flag}")
    print(f"需人工核对段: {len(big)}\n")


if __name__ == "__main__":
    main()
