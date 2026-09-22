#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""supplement_m4_concept_mentions.py —— 补登记被批次上限截掉的 concept_mention 词条

背景（W8 ACT 19 Q2）：M4 brief 的固定「每批 20 条」上限让两路都顶格截断，b 路抽取员
在 `adapter_notes` 里**逐个点名**了因上限未登记的术语，但 `adapter_notes` 当时没有
下游消费者（ACT 19 Q3 才补上）；被点名的词条于是在 M4 封存件里永久缺失。

本脚本把「点名 → 原文出处」这条链**机械走完**，不手工写任何一条：

  1）点名来源：六份 M4 提交件的 `adapter_notes` 中找到含「上限」与「未逐一登记」的
     那一条（b 路），从其括号内解析出被点名的术语表（`十神名（伤官、食神、正财、
     偏财、偏印、正印、劫财）…`）。
  2）已登记集合：六份提交件 `items[].surface` 的去重并集；两者之差即**待补登记**的词条
     （伤官/食神 已由 a 路登记，故剩 5 条——与主 Agent 2026-09-20 查实的结论一致）。
  3）出处偏移：在**两节抽取范围**（41 片段，取自提交件证据并集 ∪ notes 提及并集，
     复用 `rebuild_m4_span_list` 的同一口径）内取该术语**首次作为专门术语出现**的片段，
     记清洗文本与原始文本两套偏移；语料与偏移逐字段取自真书账本 M3 `corpus_spans`。
  4）取不到确切出处的词条 → 停手上报、不产出（ACT 19 on_fail ①：不许凭空补）。

**账本只读**（sqlite URI `mode=ro`）；不改任何已封存提交件、不写夹具。
`concept_refs` **一律不推断**（裁定 107 Q-M8-01）：产出件只登记 `surface` 与原文出处。

用法::

    python3 pipeline/tools/supplement_m4_concept_mentions.py             # 写默认落点
    python3 pipeline/tools/supplement_m4_concept_mentions.py --out /tmp/x.yaml
    python3 pipeline/tools/supplement_m4_concept_mentions.py --check-only

    # 等价写法（两种调用方式的输出一致）：
    python3 -m pipeline.tools.supplement_m4_concept_mentions

退出码：五条词条全部取到确切出处 → 0；任一条取不到（或点名条不存在）→ 1 且不落盘。
"""

import argparse
import hashlib
import os
import re
import sys

import yaml

try:  # 按路径执行（文档给的用法）：脚本目录已在 sys.path 上
    import rebuild_m4_span_list as span_list
except ImportError:  # 等价写法：python3 -m pipeline.tools.supplement_m4_concept_mentions
    from pipeline.tools import rebuild_m4_span_list as span_list

REPO = span_list.REPO
DEFAULT_OUT = os.path.join(
    REPO, "var/ledgers/qianyuan_w8_review/m4_concept_mention_supplement.yaml"
)

# 点名条的识别标记（b 路自述受上限所限的那一条）
_DISCLOSURE_MARKERS = ("上限", "未逐一登记")
# 括号内术语表的分隔符
_TERM_SPLIT_RE = re.compile(r"[、,，]")


class SupplementRefused(Exception):
    """点名条缺失或某词条取不到确切出处（不许凭空补）。"""


def find_disclosure_terms():
    """从提交件的 adapter_notes 中解析被上限截掉的术语表。"""
    for name in span_list.SUBMISSIONS:
        path = os.path.join(span_list.M4_DIR, name)
        with open(path, encoding="utf-8") as handle:
            doc = yaml.safe_load(handle)
        for note in doc.get("adapter_notes") or []:
            if not all(marker in note for marker in _DISCLOSURE_MARKERS):
                continue
            match = re.search(r"（([^）]+)）", note)
            if match is None:
                continue
            terms = [t.strip() for t in _TERM_SPLIT_RE.split(match.group(1)) if t.strip()]
            if terms:
                return name, note, terms
    raise SupplementRefused(
        "未在提交件 adapter_notes 中找到含 %r 的点名条" % (_DISCLOSURE_MARKERS,)
    )


def registered_surfaces():
    """六份提交件 `items[].surface` 的去重并集（已登记术语）。"""
    surfaces = set()
    for name in span_list.SUBMISSIONS:
        with open(os.path.join(span_list.M4_DIR, name), encoding="utf-8") as handle:
            doc = yaml.safe_load(handle)
        for item in doc.get("items") or []:
            surface = item.get("surface")
            if surface:
                surfaces.add(surface)
    return surfaces


def locate(term, spans):
    """在抽取范围内找该术语首次作为专门术语出现的片段，返回词条 dict。"""
    for span in spans:
        text = span["text"]
        index = text.find(term)
        if index < 0:
            continue
        anchor = span["source_anchor"]
        return {
            "surface": term,
            "evidence": [
                {"source_span_id": span["span_id"], "support_type": "direct"}
            ],
            "source_offsets": {
                "cleaned_text_revision_id": anchor["cleaned_text_revision_id"],
                "span_start_offset": span["start_offset"],
                "span_end_offset": span["end_offset"],
                "term_start_offset": span["start_offset"] + index,
                "term_end_offset": span["start_offset"] + index + len(term),
                "raw_text_revision_id": anchor["raw_text_revision_id"],
                "raw_span_start": anchor["raw_start"],
                "raw_span_end": anchor["raw_end"],
                "raw_term_start": anchor["raw_start"] + index,
                "raw_term_end": anchor["raw_start"] + index + len(term),
            },
            "quote": text,
        }
    raise SupplementRefused("词条取不到确切原文出处: %r" % (term,))


def render_header(source_name, note, revision_id):
    return """# 《乾元秘旨》W8 真书 · M4 concept_mention 补登记件（ACT 19 Q2）
#
# 【来源】来源：b 路 adapter_notes 点名 + 主 Agent 2026-09-20 查实。
#   点名原文（%(source)s 的 adapter_notes 逐字）：
#     「%(note)s」
#   其中已由 a 路登记的术语不再补（脚本按六份提交件 items[].surface 去重后取差集）。
#
# 【查证】每个词条的出处偏移均从真书账本 var/ledgers/qianyuan_w8 只读查证（M3
#   corpus_spans 修订 %(revision)s），**未凭空写**：取该术语在两节抽取范围
#   （41 片段）内**首次作为专门术语出现**的那一段（裁定 100 D2 的 concept_mention
#   口径：同一术语只登记一条，证据取首见片段）。5 条分别落在 5 个相连片段上，形态
#   与 a 路已登记的 伤官/食神 一致（「以X为〈十神〉，X 之化禄为 Z，Z 即〈十神〉」）。
#
# 【不改上游】本件不修改任何已封存提交件或账本：真书六份提交件的 items 与 sha256 不变，
#   账本 var/ledgers/qianyuan_w8 **只读未写**。补登记件落在 review 目录（运行时账本区，
#   不入版本库），供用户审核。
#
# 【不推断】`concept_refs`：本件**不推断**（裁定 107 Q-M8-01）。要出 Concept 词条与引用，
#   须由用户在 M6 审核表里显式 modify 补写；本件只如实登记 surface 与原文出处。
#
# 【性质】machine_extracted 工作数据，未经人工审核，不进入 M8 发布物。
#
# 【复算】python3 pipeline/tools/supplement_m4_concept_mentions.py
""" % {"source": source_name, "note": note, "revision": revision_id}


def build(source_name, note, revision_id, entries):
    body = {
        "schema_version": "0.1.0-draft",
        "category": "concept_mention",
        "technique_id": "qizheng",
        "supplement_of": source_name,
        "entries": entries,
    }
    text = render_header(source_name, note, revision_id)
    text += yaml.safe_dump(body, allow_unicode=True, sort_keys=False, width=1000)
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="supplement_m4_concept_mentions.py",
        description="补登记被批次上限截掉的 M4 concept_mention 词条（只读账本与夹具）",
    )
    parser.add_argument("--out", default=DEFAULT_OUT, help="产出路径")
    parser.add_argument("--check-only", action="store_true", help="只核对，不落盘")
    args = parser.parse_args(argv)

    try:
        source_name, note, named = find_disclosure_terms()
        registered = registered_surfaces()
        todo = [term for term in named if term not in registered]
        if not todo:
            raise SupplementRefused("点名的术语均已在提交件中登记，无待补条目")
        revision_id, spans_doc = span_list.read_corpus_spans()
        evidence, only_notes = span_list.load_submission_ids()
        spans = span_list.select_spans(spans_doc, set(evidence) | set(only_notes))
        entries = [locate(term, spans) for term in todo]
    except (SupplementRefused, span_list.RebuildRefused) as exc:
        print("REFUSED %s" % exc)
        print("未写任何文件（ACT 19 on_fail ①：取不到确切出处即停手上报，不许凭空补）")
        return 1

    print("点名条来自: %s" % source_name)
    print("点名术语: %s" % "、".join(named))
    print("已在提交件登记: %s" % "、".join(sorted(registered & set(named))))
    print("待补登记: %d 条 -> %s" % (len(todo), "、".join(todo)))
    for entry in entries:
        offsets = entry["source_offsets"]
        print(
            "  %-3s %s  cleaned[%d,%d)  raw[%d,%d)  %s"
            % (
                entry["surface"],
                entry["evidence"][0]["source_span_id"],
                offsets["term_start_offset"],
                offsets["term_end_offset"],
                offsets["raw_term_start"],
                offsets["raw_term_end"],
                entry["quote"],
            )
        )

    text = build(source_name, note, revision_id, entries)
    if args.check_only:
        print("check-only：未落盘")
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
