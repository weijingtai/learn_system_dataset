#!/usr/bin/env python3
"""validate_rag_index.py —— RAG 索引校验器"""

import sqlite3
import sys
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PIPELINE_ROOT / "rag" / "index.sqlite"

errors = []
warnings = []


def err(code, msg):
    errors.append(f"{code} | {msg}")


def warn(code, msg):
    warnings.append(f"WARN  {code} | {msg}")


def main():
    if not DB_PATH.exists():
        err("RAG_001", f"索引文件不存在: {DB_PATH}")
        for e in errors:
            print(f"      {e}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # RAG_001 表存在
    required_tables = {"meta", "spans", "assertions", "evidence", "mentions"}
    existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    existing.update(
        {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'")}
    )

    for t in required_tables:
        if t not in existing:
            err("RAG_001", f"表缺失: {t}")

    # meta 必有字段
    meta_keys = {r["key"] for r in conn.execute("SELECT key FROM meta")}
    for k in ["build_time", "unit_count", "skipped_units", "source_release"]:
        if k not in meta_keys:
            err("RAG_001", f"meta 缺少必填字段: {k}")

    # spans/assertions/evidence 非空
    for t in ["spans", "assertions", "evidence"]:
        count = conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        if count == 0:
            err("RAG_001", f"表 {t} 为空")

    # RAG_002 mentions 非空
    mention_count = conn.execute("SELECT count(*) FROM mentions").fetchone()[0]
    if mention_count == 0:
        err("RAG_002", "mentions 表为空")

    # RAG_003 端到端查询
    # 1. locate "二至还乡" → 应命中
    try:
        from opencc import OpenCC
        import re as re_mod
        PUNCT = re_mod.compile(r"[，。、；：？！「」『』（）《》—…,.!?;:\"'()\[\]{}@#$%^&*+=/\\|<>`~\s]+")
        cc = OpenCC("t2s")
        q = PUNCT.sub("", cc.convert("二至还乡")).lower()
        r1 = conn.execute("SELECT span_id FROM spans WHERE quote_norm LIKE ?", (f"%{q}%",)).fetchone()
        if not r1:
            r1 = conn.execute("SELECT s.span_id FROM spans_fts f JOIN spans s ON f.span_id=s.span_id WHERE spans_fts MATCH ?", (q,)).fetchone()
        if not r1:
            err("RAG_003", "locate 已知句'二至还乡'未命中")
    except Exception as e:
        err("RAG_003", f"locate 查询异常: {e}")

    # 2. locate "xyz不存在" → 必须空
    try:
        q2 = PUNCT.sub("", cc.convert("xyz不存在")).lower()
        r2 = conn.execute("SELECT span_id FROM spans WHERE quote_norm LIKE ?", (f"%{q2}%",)).fetchone()
        if not r2:
            r2 = conn.execute("SELECT s.span_id FROM spans_fts f JOIN spans s ON f.span_id=s.span_id WHERE spans_fts MATCH ?", (q2,)).fetchone()
        if r2:
            err("RAG_003", "locate 不存在词'xyz不存在'不应有命中")
    except Exception as e:
        err("RAG_003", f"locate 查询异常: {e}")

    # 3. 任取一个 concept_id 查询
    mc = conn.execute("SELECT concept_id FROM mentions LIMIT 1").fetchone()
    if mc:
        concept_id = mc["concept_id"]
        m_result = conn.execute("SELECT * FROM mentions WHERE concept_id=?", (concept_id,)).fetchall()
        if not m_result:
            err("RAG_003", f"mentions 查询 concept_id={concept_id} 无结果")

    # RAG_004 审计字段缺
    for k in ["unit_hashes", "script_sha256"]:
        if k not in meta_keys:
            warn("RAG_004", f"meta 缺审计字段: {k}（转正式索引前必须补）")

    conn.close()

    for w in warnings:
        print(w)
    if errors:
        print(f"FAIL  rag/index.sqlite  （{len(errors)} 条错误）")
        for e in errors:
            print(f"      {e}")
        sys.exit(1)
    print(f"PASS  rag/index.sqlite")
    sys.exit(0)


if __name__ == "__main__":
    main()
