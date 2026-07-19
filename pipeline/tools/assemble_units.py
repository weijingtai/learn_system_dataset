#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
assemble_units.py —— 从工位5 assert 产物组装知识单元 units/ku_bazi_*

数据流缺口的确定性补齐：把 TASKS/task_bazi_qtbj_assert_*/ 里已签发的
1317 条权威主张，忠实搬运进 units/ 三件套，供 rag/build_index.py 索引。

粒度（方案 C）：一 segment 一临时 unit——不做产品语义聚合，unit 边界
即 segment（span_id），聚合交给下游工位9。137 个 span → 137 个 unit。

输入（全部现成，无需回转录源）：
    TASKS/task_bazi_qtbj_assert_*/output/authoritative.yaml   权威主张
    TASKS/task_bazi_qtbj_assert_*/input/segments.yaml         span→原文+标题
    corpus/bazi/qtbj_ed01/source/sections.yaml                伪页→标题(备用)

产出 units/ku_bazi_NNNNNN/：
    unit.yaml         title=entry_title, status=machine_extracted(未经确权)
    provenance.yaml   quote=segment 正文, location 由 span_id 解析
    assertions.yaml   按 evidence.span_id 分配, 保留 concept_ids

用法：
    python3 tools/assemble_units.py                # 生成到 units/
    python3 tools/assemble_units.py --dry-run      # 只报统计，不写文件

确定性：同输入同输出，无时间戳（created 取 sections 无关的固定源）。
"""
import re
import sys
from pathlib import Path

import yaml

PIPELINE = Path(__file__).resolve().parent.parent
ASSERT_GLOB = "TASKS/task_bazi_qtbj_assert_*"
CORPUS = PIPELINE / "corpus/bazi/qtbj_ed01"
UNITS = PIPELINE / "units"
SOURCE_ID = "src_qtbj_ed01"
TECHNIQUE_ID = "bazi"
TRANSCRIPT_FILE = "source/transcript_v1.md"
CREATED = "2026-07-16"  # 组装日期，固定以保确定性

SPAN_RE = re.compile(r"ss_\w+_p(\d+)_s(\d+)")

# 私用区(PUA)乱码勘误表——epub 字体私用区残留，人工对照纸质原书核出的 1:1
# 稳定映射，来源 commit 1bdb4ff 与 lessons/LESSONS.md(2026-07-14)。
# transcript 源已勘误干净，但工位5 的 segments 输入快照拍摄于勘误前，仍冻结
# 残留 PUA；quote 只能取自 segments(唯一句级边界)，故在此按确权表补正。
# 表外的未知 PUA 一律报错退出(遵模板铁律7「遇乱码不猜字」)，绝不静默放过。
# 用 chr(码位) 书写键，避免字面 PUA 字符在编辑/复制中被吃掉(LESSONS 2026-07-14)
PUA_FIX = {
    chr(0xE10F): "克", chr(0xE509): "斗", chr(0xE71F): "碍",
    chr(0xE4DF): "颖", chr(0xE03D): "冲",
}


def fix_pua(text, where):
    """按确权表补正 PUA 乱码；遇表外未知 PUA 则报错退出。"""
    out = []
    for ch in text:
        o = ord(ch)
        if 0xE000 <= o <= 0xF8FF:  # 私用区
            if ch in PUA_FIX:
                out.append(PUA_FIX[ch])
            else:
                print(f"错误：{where} 含未登记的 PUA 乱码 {hex(o)}，"
                      f"须人工核实原书后补入 PUA_FIX 再重跑（不猜字）",
                      file=sys.stderr)
                sys.exit(1)
        else:
            out.append(ch)
    return "".join(out)


def parse_location(span_id):
    """从 span_id 解析人类可读位置：ss_qtbj_ed01_p0001_s02 → 第1页 第2句"""
    m = SPAN_RE.search(span_id)
    if not m:
        return ""
    return f"第{int(m.group(1))}页 第{int(m.group(2))}句"


def clean_quote(text, where):
    """segment 正文清洗为引文：补正 PUA 乱码 + 去 markdown 标题行 + 去首尾空白"""
    text = fix_pua(text, where)
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    return "\n".join(lines).strip()


def load_all():
    """汇总所有 assert 任务的 span→segment 与 span→主张列表。"""
    span_seg = {}            # span_id -> (quote, entry_title)
    span_asserts = {}        # span_id -> [assertion, ...]（按证据首个 span 归属）
    seg_files = sorted(PIPELINE.glob(f"{ASSERT_GLOB}/input/segments.yaml"))
    auth_files = sorted(PIPELINE.glob(f"{ASSERT_GLOB}/output/authoritative.yaml"))

    for f in seg_files:
        for s in (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("segments", []):
            sid = s["span_id"]
            if sid not in span_seg:  # 同 span 只登记一次（跨任务边界去重）
                span_seg[sid] = (clean_quote(s.get("text", ""), sid),
                                 s.get("entry_title") or "")

    for f in auth_files:
        for a in (yaml.safe_load(f.read_text(encoding="utf-8")) or {})["assertions"]:
            ev = a.get("evidence") or []
            if not ev:
                continue
            # 主张归属到其第一个证据 span 所在的 unit（一 segment 一 unit）
            home = ev[0]["source_span_id"]
            span_asserts.setdefault(home, []).append(a)

    return span_seg, span_asserts, len(seg_files), len(auth_files)


def build_unit(idx, span_id, quote, title, asserts):
    """产出一个 unit 的三件套字典。"""
    unit_id = f"ku_bazi_{idx:06d}"
    unit = {
        "unit_id": unit_id,
        "technique_id": TECHNIQUE_ID,
        "source_id": SOURCE_ID,
        "title": title or "(无标题)",
        "span_ids": [span_id],
        "status": "machine_extracted",  # 工位5 机器抽取，未经专家确权
        "created": CREATED,
    }
    prov = {
        "source_spans": [{
            "source_span_id": span_id,
            "source_id": SOURCE_ID,
            "file": TRANSCRIPT_FILE,
            "quote": quote,
            "location": parse_location(span_id),
        }]
    }
    # 忠实搬运主张，保留 concept_ids（工位4 产物）；不造 school_ids
    assertions = {"assertions": asserts}
    return unit_id, unit, prov, assertions


def main():
    dry = "--dry-run" in sys.argv[1:]
    span_seg, span_asserts, n_seg, n_auth = load_all()

    # 只为「被主张引用到」的 span 建 unit（无主张的 span 不成 unit）
    active_spans = sorted(span_asserts.keys())
    orphan = [s for s in active_spans if s not in span_seg]
    if orphan:
        print(f"错误：{len(orphan)} 个主张引用的 span 在 segments 中找不到原文，"
              f"样本 {orphan[:3]}", file=sys.stderr)
        sys.exit(1)

    total_asserts = sum(len(v) for v in span_asserts.values())
    print(f"输入：{n_seg} 个 assert 任务，{n_auth} 份 authoritative")
    print(f"    span 提供原文 {len(span_seg)} 个；被主张引用 {len(active_spans)} 个")
    print(f"    主张总数 {total_asserts} 条 → {len(active_spans)} 个 unit")

    if dry:
        print("--dry-run：未写文件。")
        return

    UNITS.mkdir(exist_ok=True)
    for idx, span_id in enumerate(active_spans, start=1):
        quote, title = span_seg[span_id]
        unit_id, unit, prov, assertions = build_unit(
            idx, span_id, quote, title, span_asserts[span_id])
        d = UNITS / unit_id
        d.mkdir(exist_ok=True)
        (d / "unit.yaml").write_text(
            yaml.dump(unit, allow_unicode=True, sort_keys=False), encoding="utf-8")
        (d / "provenance.yaml").write_text(
            yaml.dump(prov, allow_unicode=True, sort_keys=False), encoding="utf-8")
        (d / "assertions.yaml").write_text(
            yaml.dump(assertions, allow_unicode=True, sort_keys=False), encoding="utf-8")

    print(f"完成：{len(active_spans)} 个 unit 写入 units/ku_bazi_000001..{len(active_spans):06d}")


if __name__ == "__main__":
    main()
