#!/usr/bin/env python3
"""query.py —— 检索脚本（L1＋L2）"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

import yaml
from opencc import OpenCC

RAG_DIR = Path(__file__).resolve().parent
DB_PATH = RAG_DIR / "index.sqlite"
PUNCT = re.compile(r"[，。、；：？！「」『』（）《》—…,.!?;:\"'()\[\]{}@#$%^&*+=/\\|<>`~\s]+")

cc = OpenCC("t2s")


def norm(text):
    simplified = cc.convert(text)
    no_punct = PUNCT.sub("", simplified)
    return no_punct.lower()


def locate(args):
    if not DB_PATH.exists():
        yaml.dump({"hits": [], "note": "索引库未构建，先运行 build_index.py"}, sys.stdout, allow_unicode=True)
        return

    query_norm = norm(args.query)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # 1. 精确子串匹配
    rows = conn.execute(
        "SELECT span_id, quote, source_id, file, location FROM spans WHERE quote_norm LIKE ?",
        (f"%{query_norm}%",)
    ).fetchall()

    # 2. 无结果 → FTS5
    if not rows:
        rows = conn.execute(
            "SELECT s.span_id, s.quote, s.source_id, s.file, s.location "
            "FROM spans_fts f JOIN spans s ON f.span_id = s.span_id "
            "WHERE spans_fts MATCH ?",
            (query_norm,)
        ).fetchall()

    hits = []
    for r in rows:
        hits.append({
            "span_id": r["span_id"],
            "quote": r["quote"],
            "source_id": r["source_id"],
            "file": r["file"],
            "location": r["location"],
        })

    if not hits:
        result = {"hits": [], "note": "未找到，可能原因：不在已索引范围/用词不同（L3 未启用）"}
    else:
        result = {"hits": hits}

    conn.close()
    yaml.dump(result, sys.stdout, allow_unicode=True, sort_keys=False)


def concept(args):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT concept_id, surface, span_id, unit_id FROM mentions WHERE concept_id = ?",
        (args.concept_id,)
    ).fetchall()

    hits = []
    for r in rows:
        spans = conn.execute(
            "SELECT quote, location FROM spans WHERE span_id = ?",
            (r["span_id"],)
        ).fetchall()
        span_list = [{"span_id": r["span_id"], "quote": s["quote"], "location": s["location"]} for s in spans]
        hits.append({
            "concept_id": r["concept_id"],
            "surface": r["surface"],
            "unit_id": r["unit_id"],
            "spans": span_list,
        })

    if not hits:
        result = {"hits": [], "note": "未找到该术语索引记录"}
    else:
        result = {"hits": hits}

    conn.close()
    yaml.dump(result, sys.stdout, allow_unicode=True, sort_keys=False)


def assertion(args):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        "SELECT * FROM assertions WHERE assertion_id = ?",
        (args.assertion_id,)
    ).fetchone()

    if not row:
        result = {"hits": [], "note": f"未找到 assertion {args.assertion_id}"}
    else:
        evidence_rows = conn.execute(
            "SELECT e.span_id, e.support_type, s.quote, s.location "
            "FROM evidence e JOIN spans s ON e.span_id = s.span_id "
            "WHERE e.assertion_id = ?",
            (args.assertion_id,)
        ).fetchall()

        evidence_list = []
        for er in evidence_rows:
            evidence_list.append({
                "span_id": er["span_id"],
                "support_type": er["support_type"],
                "quote": er["quote"],
                "location": er["location"],
            })

        result = {
            "assertion_id": row["assertion_id"],
            "unit_id": row["unit_id"],
            "proposition_id": row["proposition_id"],
            "proposition": row["proposition"],
            "relation": row["relation"],
            "status": row["status"],
            "conditions": json.loads(row["conditions"]) if row["conditions"] else [],
            "exceptions": json.loads(row["exceptions"]) if row["exceptions"] else [],
            "school_ids": json.loads(row["school_ids"]) if row["school_ids"] else [],
            "evidence": evidence_list,
        }

    conn.close()
    yaml.dump(result, sys.stdout, allow_unicode=True, sort_keys=False)


def main():
    parser = argparse.ArgumentParser(description="检索脚本（L1＋L2）")
    sub = parser.add_subparsers(dest="cmd")

    p_locate = sub.add_parser("locate", help="L2：定位原句")
    p_locate.add_argument("query", help="查询词")
    p_locate.set_defaults(func=lambda a: locate(a))

    p_concept = sub.add_parser("concept", help="L1：术语 → 相关主张")
    p_concept.add_argument("concept_id", help="术语编号（如 qimen.star.tianpeng）")
    p_concept.set_defaults(func=lambda a: concept(a))

    p_assert = sub.add_parser("assertion", help="L1：主张 → 全部字段＋证据原文")
    p_assert.add_argument("assertion_id", help="主张编号（如 as_qimen_000001）")
    p_assert.set_defaults(func=lambda a: assertion(a))

    args = parser.parse_args()
    if args.cmd is None:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
