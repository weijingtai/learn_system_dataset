#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rebuild_m4_span_list.py —— 重建《乾元秘旨》「天官」「七煞」两节 M4 抽取用片段清单

背景（W8 ACT 19 Q4）：M4 提交件 README 记录了片段清单 `spans_tianguan_qisha.yaml` 的
sha256 `b4240c74…`，但**全盘无此文件**（仓库与 ~/tmux-agents 均已搜过）——抽取用输入
清单丢失，可复现性缺口。本脚本从**仍可复现的两处事实**机械重建该清单：

  1）片段 ID 集合 = 六份已入库 M4 提交件
     （`pipeline/corpus/_fixture/qianyuan_ed01_text/m4/submission_{assertion,pattern,
     concept_mention}_{a,b}.yaml`）中 `evidence[].source_span_id` 的去重并集（37 个）
     ∪ 各件 `adapter_notes` 中提及的片段 ID（4 个，全部未被任何证据引用）= 41 个。
     （清单里的片段就是抽取员实际看到的那一批：被抽中的 + 被点名跳过的。）
  2）片段记录本身 = 真书账本 `var/ledgers/qianyuan_w8` 的 M3 `corpus_spans` 修订，
     逐字段原样取用（span_id / sequence / start_offset / end_offset / text /
     quote_sha256 / evidence_level / source_anchor），按 `sequence` 升序。

**账本只读**：以 sqlite URI `mode=ro` 打开，不写账本、不写夹具、不改任何已封存提交件。

【sha256 状态】重建件**无法**与 README 记录的 `b4240c74…` 核对（原文件不存在），
产出文件头部已逐字标注「未能核对」，脚本**不得**声称已核对。

用法::

    python3 pipeline/tools/rebuild_m4_span_list.py                # 写到默认落点
    python3 pipeline/tools/rebuild_m4_span_list.py --out /tmp/x.yaml
    python3 pipeline/tools/rebuild_m4_span_list.py --check-only    # 只核对事实，不落盘

退出码：事实核对全部成立 → 0；任一条不成立（段数不是 41、偏移不连续、字数不是 734
等）→ 1，且不写文件（ACT 19 on_fail ③：重建前提错了必须停手上报）。
"""

import argparse
import hashlib
import os
import re
import sqlite3
import sys

import yaml

# 仓库根：本文件位于 <repo>/pipeline/tools/
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LEDGER = os.path.join(REPO, "var/ledgers/qianyuan_w8/ledger.sqlite")
M4_DIR = os.path.join(REPO, "pipeline/corpus/_fixture/qianyuan_ed01_text/m4")
DEFAULT_OUT = os.path.join(REPO, "var/ledgers/qianyuan_w8_review/spans_tianguan_qisha.yaml")

SUBMISSIONS = (
    "submission_assertion_a.yaml",
    "submission_pattern_a.yaml",
    "submission_concept_mention_a.yaml",
    "submission_assertion_b.yaml",
    "submission_pattern_b.yaml",
    "submission_concept_mention_b.yaml",
)

# 提交件里的片段 ID 形态（ss_<work>_<edNN>_o<7 位原始偏移>）
SPAN_ID_RE = re.compile(r"ss_[a-z0-9_]+_o\d{7}")

# 机械转换注记不是抽取员 notes，其中的 ID 不作数（它是「转换说明」不是「抽取范围」）
_TRANSFORM_MARKER = "机械转换"

# 已知事实（ACT 19 Q4 背景，主 Agent 查实）：README 记录的原文 sha256、两节 raw 跨度
RECORDED_SHA256 = "b4240c748ca0cc0883980328d01e4c06effeef7f99bd6924724fea747f9e4cd7"
EXPECTED_SPAN_COUNT = 41
EXPECTED_CHARS = 734
EXPECTED_RAW_RANGE = (8663, 9397)


class RebuildRefused(Exception):
    """重建前提不成立（字段缺失、段数/偏移/字数与已知事实不符）。"""


def load_submission_ids():
    """返回 ``(evidence_ids, note_only_ids)``——两个有序的片段 ID 集合。

    只读已入库提交件；`items[].evidence[].source_span_id` 计入证据集合，
    `adapter_notes` 中出现的片段 ID 计入 notes 集合（机械转换注记除外）。
    """
    evidence, noted = {}, {}
    for name in SUBMISSIONS:
        path = os.path.join(M4_DIR, name)
        with open(path, encoding="utf-8") as handle:
            doc = yaml.safe_load(handle)
        for item in doc.get("items") or []:
            for entry in item.get("evidence") or []:
                evidence.setdefault(entry["source_span_id"], set()).add(name)
        for note in doc.get("adapter_notes") or []:
            if _TRANSFORM_MARKER in note:
                continue
            for span_id in SPAN_ID_RE.findall(note):
                noted.setdefault(span_id, set()).add(name)
    return evidence, {k: v for k, v in noted.items() if k not in evidence}


def read_corpus_spans():
    """只读打开真书账本，返回 ``(revision_id, spans_doc)``（M3 corpus_spans 修订）。"""
    if not os.path.isfile(LEDGER):
        raise RebuildRefused("账本不存在: %s" % LEDGER)
    conn = sqlite3.connect("file:%s?mode=ro" % LEDGER, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT r.artifact_revision_id, r.sha256, r.object_key "
            "FROM artifact_revisions r JOIN artifacts a ON a.artifact_id = r.artifact_id "
            "WHERE a.artifact_type='corpus_spans'"
        ).fetchall()
    finally:
        conn.close()
    if len(rows) != 1:
        raise RebuildRefused("corpus_spans 修订不是恰 1 个: %d" % len(rows))
    row = rows[0]
    path = os.path.join(REPO, "var/ledgers/qianyuan_w8", row["object_key"])
    if not os.path.isfile(path):
        path = os.path.join(REPO, "var/ledgers/qianyuan_w8/objects", row["sha256"])
    if not os.path.isfile(path):
        raise RebuildRefused("corpus_spans 对象缺失: %s" % row["object_key"])
    data = open(path, "rb").read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != row["sha256"]:
        raise RebuildRefused(
            "corpus_spans 对象字节哈希不符: %s != %s" % (actual, row["sha256"])
        )
    return row["artifact_revision_id"], yaml.safe_load(data.decode("utf-8"))


def select_spans(spans_doc, wanted):
    """按 ``sequence`` 升序取出 ``wanted`` 里的片段，并核对已知事实。"""
    picked = [span for span in spans_doc["spans"] if span["span_id"] in wanted]
    picked.sort(key=lambda span: span["sequence"])
    only_set = set(wanted) - {span["span_id"] for span in picked}
    if only_set:
        raise RebuildRefused("这些片段 ID 不在账本 spans 里: %s" % sorted(only_set))
    if len(picked) != EXPECTED_SPAN_COUNT:
        raise RebuildRefused(
            "段数 %d != %d（重建前提错了）" % (len(picked), EXPECTED_SPAN_COUNT)
        )
    chars = sum(len(span["text"]) for span in picked)
    if chars != EXPECTED_CHARS:
        raise RebuildRefused(
            "字数合计 %d != %d（重建前提错了）" % (chars, EXPECTED_CHARS)
        )
    cursor = None
    for span in picked:
        if cursor is not None and span["start_offset"] != cursor:
            raise RebuildRefused(
                "清洗偏移不连续: %s start=%d，前段 end=%d"
                % (span["span_id"], span["start_offset"], cursor)
            )
        cursor = span["end_offset"]
    raw_range = (
        picked[0]["source_anchor"]["raw_start"],
        picked[-1]["source_anchor"]["raw_end"],
    )
    if raw_range != EXPECTED_RAW_RANGE:
        raise RebuildRefused(
            "raw 跨度 %r != %r（重建前提错了）" % (raw_range, EXPECTED_RAW_RANGE)
        )
    return picked


def render_header(revision_id, only_notes):
    """产出文件头注释（含「sha256 未能核对」的逐字标注）。"""
    return """# 《乾元秘旨》「天官」「七煞」两节 · M4 抽取用片段清单（41 段）
# 只引用出处的 4 段（未被任何证据引用，仅 notes 提及）: %(notes)s
#
# 【sha256 状态：未能核对】本文件是**重建件**，不是原文件。
#   仓库里记录的原文 sha256（pipeline/corpus/_fixture/qianyuan_ed01_text/m4/README.md）：
#     %(recorded)s
#   原文件全盘不存在（仓库与 ~/tmux-agents 均已搜过，ACT 19 Q4 背景），**因此本文件
#   的 sha256 与上述记录**无法核对**，也不得声称已核对。本重建件自身的 sha256 记在
#   docs/blackbox-spec-rework/work-items/impl-05-knowledge/M4_SPAN_LIST_REBUILD.md。
#
# 【重建来源】机械重建，未人工增删一条：
#   片段 ID 集合 = 六份 M4 提交件（pipeline/corpus/_fixture/qianyuan_ed01_text/m4/
#     submission_{assertion,pattern,concept_mention}_{a,b}.yaml）中
#     `evidence[].source_span_id` 的去重并集（37 个）∪ 各件 `adapter_notes` 里提及的
#     片段 ID（4 个，全部未被证据引用）= 41 个。
#   片段记录本身逐字段取自真书账本 var/ledgers/qianyuan_w8 的 M3 corpus_spans
#     （修订 %(revision)s），按 sequence 升序，未改写任何字段。
#   核对：清洗偏移首尾相接、无空洞无重叠；raw 偏移 [%(raw_start)d, %(raw_end)d)；
#     字数合计 %(chars)d。
#
# 【重建命令】python3 pipeline/tools/rebuild_m4_span_list.py
#
# 【性质】本件是抽取用输入清单的重建存档，属 `machine_extracted` 工作数据，
#   不含任何人工审核结论；不进入 M8 发布物。
""" % {
        "notes": ", ".join(only_notes),
        "recorded": RECORDED_SHA256,
        "revision": revision_id,
        "raw_start": EXPECTED_RAW_RANGE[0],
        "raw_end": EXPECTED_RAW_RANGE[1],
        "chars": EXPECTED_CHARS,
    }


def build(spans_doc, revision_id, spans, only_note_ids):
    body = {
        "source_id": spans_doc["source_id"],
        "work": spans_doc["work"],
        "edition_part_artifact_id": spans_doc["edition_part_artifact_id"],
        "evidence_level": spans_doc["evidence_level"],
        "content_status": spans_doc.get("content_status"),
        "span_count": len(spans),
        "spans": spans,
    }
    text = render_header(revision_id, sorted(only_note_ids))
    text += yaml.safe_dump(
        body, allow_unicode=True, sort_keys=False, width=1000, default_flow_style=False
    )
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="rebuild_m4_span_list.py",
        description="重建《乾元秘旨》两节 M4 抽取用片段清单（只读账本与夹具）",
    )
    parser.add_argument("--out", default=DEFAULT_OUT, help="产出路径")
    parser.add_argument(
        "--check-only", action="store_true", help="只核对事实，不落盘"
    )
    args = parser.parse_args(argv)

    try:
        evidence, only_notes = load_submission_ids()
        wanted = set(evidence) | set(only_notes)
        if len(evidence) != 37 or len(only_notes) != 4:
            raise RebuildRefused(
                "证据引用 %d（期望 37）/ 仅 notes 提及 %d（期望 4）"
                % (len(evidence), len(only_notes))
            )
        revision_id, spans_doc = read_corpus_spans()
        spans = select_spans(spans_doc, wanted)
    except RebuildRefused as exc:
        print("REFUSED %s" % exc)
        print("未写任何文件（ACT 19 on_fail ③：重建前提不成立即停手上报）")
        return 1

    print("证据引用片段: %d" % len(evidence))
    print("仅 notes 提及（未被引用）: %d -> %s" % (len(only_notes), sorted(only_notes)))
    print("并集: %d 段" % len(spans))
    print("corpus_spans 修订: %s" % revision_id)
    print(
        "raw 跨度: [%d, %d)  字数合计: %d"
        % (
            spans[0]["source_anchor"]["raw_start"],
            spans[-1]["source_anchor"]["raw_end"],
            sum(len(span["text"]) for span in spans),
        )
    )
    print("清洗偏移: %d..%d 首尾相接" % (spans[0]["start_offset"], spans[-1]["end_offset"]))

    text = build(spans_doc, revision_id, spans, only_notes)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if args.check_only:
        print("check-only：未落盘；产出将含 %d 段" % len(spans))
        return 0

    out = args.out
    directory = os.path.dirname(os.path.abspath(out))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(text)
    written = open(out, "rb").read()
    print("写出: %s（%d 字节）" % (out, len(written)))
    print("sha256: %s" % hashlib.sha256(written).hexdigest())
    print("（README 记录的原文 sha256 %s 无法核对：原文件不存在）" % RECORDED_SHA256)
    return 0


if __name__ == "__main__":
    sys.exit(main())
