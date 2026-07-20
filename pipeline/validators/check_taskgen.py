#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_taskgen.py —— 下游任务包生成器（工位4/5/6）回归门禁

固化 P1/P2 重构时的等价性验收：三工具经 tools/lib/taskgen.py 生成的产物
必须与黄金快照 byte 一致。任何人改动 taskgen 或三工具后跑一次即可确认
没有破坏产物。

golden 只存**生成类**文件（segments.yaml / spans.yaml / task.yaml）；
INSTRUCTIONS.md 与 glossary_v0.yaml 是逐字拷贝，另行核对其来源解析正确
（顺带验证 resolve_template 与按技法解析 glossary）。

用法：
    python3 validators/check_taskgen.py            # 校验（CI/日常）
    python3 validators/check_taskgen.py --update    # 重新采集黄金快照（有意变更产物后）

退出码：0 = 全部通过；1 = 有差异。
"""
import contextlib
import filecmp
import io
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from lib.taskgen import PIPELINE, build, resolve_template  # noqa: E402

import gen_concept_task
import gen_assertion_task
import gen_paraphrase_task

GOLDEN = Path(__file__).resolve().parent / "goldens" / "taskgen"
CORPUS = "corpus/bazi/qtbj_ed01"
GEN = {"concepts": gen_concept_task, "assert": gen_assertion_task, "para": gen_paraphrase_task}
# 生成类文件（byte 快照）；其余（INSTRUCTIONS/glossary）单独核对来源
GEN_FILES = ["task.yaml", "input/segments.yaml", "input/spans.yaml"]

# 代表性用例：三工位各取一个真实轮次（覆盖 emit_spans 有/无、extra_meta、done_note 各分支）
CASES = [
    ("concepts", "r1", ["qtbj_b001", "qtbj_b005", "qtbj_b006", "qtbj_b007",
                        "qtbj_b008", "qtbj_b009", "qtbj_b010", "qtbj_b011"]),
    ("assert", "s1", ["qtbj_b001", "qtbj_b002", "qtbj_b003"]),
    ("para", "s1", ["qtbj_b001", "qtbj_b002", "qtbj_b003"]),
]


def generate(suffix, rnd, batches, out_root):
    """用当前工具生成一个任务包到 out_root，返回任务目录。吞掉 build 的完成语。"""
    spec = GEN[suffix].make_spec(CORPUS, rnd, batches)
    with contextlib.redirect_stdout(io.StringIO()):
        return build(spec, out_root=out_root)


def do_update():
    if GOLDEN.exists():
        shutil.rmtree(GOLDEN)
    GOLDEN.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        for suffix, rnd, batches in CASES:
            td = generate(suffix, rnd, batches, Path(tmp))
            dst = GOLDEN / td.name
            (dst / "input").mkdir(parents=True, exist_ok=True)
            for rel in GEN_FILES:
                src = td / rel
                if src.exists():
                    shutil.copy(src, dst / rel)
    print(f"已采集黄金快照 → {GOLDEN.relative_to(PIPELINE)}  （{len(CASES)} 个任务包）")


def do_check():
    errors = []
    with tempfile.TemporaryDirectory() as tmp:
        for suffix, rnd, batches in CASES:
            td = generate(suffix, rnd, batches, Path(tmp))
            gold = GOLDEN / td.name
            if not gold.exists():
                errors.append(f"{td.name}: 无黄金快照（先跑 --update）")
                continue
            # 1) 生成类文件 byte 比对
            for rel in GEN_FILES:
                g, n = gold / rel, td / rel
                if g.exists() != n.exists():
                    errors.append(f"{td.name}/{rel}: 存在性不一致（golden={g.exists()} new={n.exists()}）")
                elif g.exists() and not filecmp.cmp(g, n, shallow=False):
                    errors.append(f"{td.name}/{rel}: byte 差异")
            # 2) INSTRUCTIONS/glossary 核对来源解析（非快照）
            _check_sources(suffix, td, errors)
    if errors:
        print(f"FAIL  check_taskgen  （{len(errors)} 条）")
        for e in errors:
            print(f"      {e}")
        sys.exit(1)
    print(f"PASS  check_taskgen  （{len(CASES)} 个任务包 byte 一致）")
    sys.exit(0)


def _check_sources(suffix, td, errors):
    """确认 INSTRUCTIONS.md 来自技法解析的模板、glossary 来自技法目录。"""
    stage_dir = {"concepts": "stage4_concepts", "assert": "stage5_assertions",
                 "para": "stage6_paraphrase"}[suffix]
    tmpl = resolve_template(stage_dir, "bazi")
    if not filecmp.cmp(tmpl, td / "INSTRUCTIONS.md", shallow=False):
        errors.append(f"{td.name}/INSTRUCTIONS.md: 与解析模板 {tmpl.name} 不一致")
    gloss = PIPELINE / "schemas/techniques/bazi/glossary_v0.yaml"
    if not filecmp.cmp(gloss, td / "input/glossary_v0.yaml", shallow=False):
        errors.append(f"{td.name}/glossary_v0.yaml: 与技法术语表不一致")


def check_fallback():
    """独立单测：resolve_template 三路径（命中派生 / 回落基座 / 全缺报错）。"""
    errs = []
    if resolve_template("stage6_paraphrase", "bazi").parent.name != "stage6_paraphrase_bazi":
        errs.append("bazi 未命中 _bazi 派生模板")
    if resolve_template("stage6_paraphrase", "qimen").parent.name != "stage6_paraphrase":
        errs.append("qimen 未回落到通用基座")
    try:
        resolve_template("stage_nope", "qimen")
        errs.append("全缺场景未抛 FileNotFoundError")
    except FileNotFoundError:
        pass
    return errs


def main():
    if "--update" in sys.argv:
        do_update()
        return
    fb = check_fallback()
    if fb:
        print(f"FAIL  check_taskgen  （resolve_template：{len(fb)} 条）")
        for e in fb:
            print(f"      {e}")
        sys.exit(1)
    do_check()


if __name__ == "__main__":
    main()
