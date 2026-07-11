#!/usr/bin/env python3
"""build_index.py —— 从 units/ 编译 L1＋L2 检索库（SQLite＋FTS5）"""

import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from opencc import OpenCC

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
UNITS_DIR = PIPELINE_ROOT / "units"
RAG_DIR = PIPELINE_ROOT / "rag"
DB_PATH = RAG_DIR / "index.sqlite"
VALIDATOR = PIPELINE_ROOT / "validators" / "validate.py"
PUNCT = re.compile(r"[，。、；：？！「」『』（）《》—…,.!?;:\"'()\[\]{}@#$%^&*+=/\\|<>`~\s]+")

cc = OpenCC("t2s")


def norm(text):
    """繁转简 → 去标点 → 去空白 → 小写"""
    simplified = cc.convert(text)
    no_punct = PUNCT.sub("", simplified)
    return no_punct.lower()


def validate_unit(unit_dir):
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(unit_dir)],
        capture_output=True, text=True, cwd=str(PIPELINE_ROOT)
    )
    return result.returncode == 0, result.stdout.strip()


def build():
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    conn.executescript("""
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE spans(
            span_id TEXT PRIMARY KEY, source_id TEXT, file TEXT,
            quote TEXT, quote_norm TEXT, location TEXT);
        CREATE TABLE assertions(
            assertion_id TEXT PRIMARY KEY, unit_id TEXT, proposition_id TEXT,
            proposition TEXT, relation TEXT, status TEXT,
            conditions TEXT, exceptions TEXT, school_ids TEXT);
        CREATE TABLE evidence(assertion_id TEXT, span_id TEXT, support_type TEXT);
        CREATE TABLE mentions(concept_id TEXT, surface TEXT, span_id TEXT, unit_id TEXT);
        CREATE VIRTUAL TABLE spans_fts USING fts5(quote_norm, span_id UNINDEXED);
    """)

    all_units = sorted(
        [d for d in UNITS_DIR.iterdir() if d.is_dir() and d.name.startswith("ku_")]
    )

    passed = 0
    skipped_units = []

    for unit_dir in all_units:
        ok, output = validate_unit(unit_dir)
        if not ok:
            skipped_units.append(unit_dir.name)
            print(f"SKIP  {unit_dir.name}（校验 FAIL，已跳过）")
            print(f"      校验输出: {output[:200]}")
            continue

        unit_yaml = yaml.safe_load((unit_dir / "unit.yaml").read_text(encoding="utf-8"))
        prov_yaml = yaml.safe_load((unit_dir / "provenance.yaml").read_text(encoding="utf-8"))
        assert_yaml = yaml.safe_load((unit_dir / "assertions.yaml").read_text(encoding="utf-8"))

        unit_id = unit_yaml["unit_id"]

        # spans 去重——同一个 span 可能被多个 assertion 引用
        span_quotes = {}
        for s in prov_yaml["source_spans"]:
            sid = s["source_span_id"]
            quote = s["quote"]
            quote_norm = norm(quote)
            loc = s.get("location", "")
            src = s.get("source_id", "")
            fl = s.get("file", "")
            if sid not in span_quotes:
                span_quotes[sid] = (quote, quote_norm, src, fl, loc)

        for sid, (quote, quote_norm, src, fl, loc) in span_quotes.items():
            conn.execute(
                "INSERT OR IGNORE INTO spans VALUES(?,?,?,?,?,?)",
                (sid, src, fl, quote, quote_norm, loc)
            )
            conn.execute(
                "INSERT INTO spans_fts(quote_norm, span_id) VALUES(?,?)",
                (quote_norm, sid)
            )

        for a in assert_yaml["assertions"]:
            aid = a["assertion_id"]
            pid = a.get("proposition_id", "")
            prop = a.get("proposition", "")
            rel = a.get("relation", "supports")
            status = a.get("status", "")
            conditions = json.dumps(a.get("conditions", []), ensure_ascii=False)
            exceptions = json.dumps(a.get("exceptions", []), ensure_ascii=False)
            schools = json.dumps(a.get("school_ids", []), ensure_ascii=False)

            conn.execute(
                "INSERT INTO assertions VALUES(?,?,?,?,?,?,?,?,?)",
                (aid, unit_id, pid, prop, rel, status, conditions, exceptions, schools)
            )

            for ev in a.get("evidence", []):
                e_span = ev.get("source_span_id", "")
                e_type = ev.get("support_type", "")
                conn.execute(
                    "INSERT INTO evidence VALUES(?,?,?)",
                    (aid, e_span, e_type)
                )

        passed += 1
        print(f"OK    {unit_dir.name}")

    # mentions（术语→span）：数据来源是各技法术语表 schemas/techniques/*/glossary*.yaml
    # 的 seg_ids（RAG_GUIDE 第 2 章补充规定）；只收已被 units 索引的 span，rejected 术语不收。
    span_map = {}   # source_id -> {seg序号: span_id}
    unit_of_span = {}
    for span_id, src in conn.execute("SELECT span_id, source_id FROM spans"):
        m = re.search(r"_s(\d+)$", span_id)
        if m:
            span_map.setdefault(src, {})[int(m.group(1))] = span_id
    for aid, e_span in conn.execute(
            "SELECT a.unit_id, e.span_id FROM evidence e JOIN assertions a USING(assertion_id)"):
        unit_of_span.setdefault(e_span, aid)
    mention_count = 0
    for gp in sorted((PIPELINE_ROOT / "schemas" / "techniques").rglob("glossary*.yaml")):
        g = yaml.safe_load(gp.read_text(encoding="utf-8"))
        for c in g.get("concepts", []):
            if str(c.get("status", "")).startswith("rejected"):
                continue
            src = c.get("source_id", "")
            for seg in c.get("seg_ids", []):
                try:
                    n = int(str(seg).lstrip("s"))
                except ValueError:
                    continue
                span_id = span_map.get(src, {}).get(n)
                if span_id:
                    conn.execute("INSERT INTO mentions VALUES(?,?,?,?)",
                                 (c["concept_id"], c["surface"], span_id,
                                  unit_of_span.get(span_id, "")))
                    mention_count += 1
    print(f"mentions: {mention_count} 条")

    now = datetime.now(timezone.utc).isoformat()
    conn.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", ("build_time", now))
    conn.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", ("unit_count", str(passed)))
    conn.execute("INSERT OR REPLACE INTO meta VALUES(?,?)",
                 ("skipped_units", json.dumps(skipped_units, ensure_ascii=False)))
    conn.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", ("source_release", "dev"))

    conn.commit()
    conn.close()

    print(f"\n建库完成: {passed} 个单元通过, {len(skipped_units)} 个跳过")
    print(f"索引文件: {DB_PATH}")


if __name__ == "__main__":
    build()
