"""gujiorc.core.library — 将 data/*.json 识别结果导入数据库。

目标：把「每页一个 JSON 文件（git 主档案）」导入一个可查询的数据库。
JSON 仍是主档案（可 diff/校验/Web UI）；DB 是导入产物，可从 JSON 随时重建。

提供两种导入目标：
  1. SQLite 单文件（默认）—— pages 表存整页 JSON 文档 + char_index 单字检索
     + rare 生僻字清单。既是 SQL 数据库又是（JSON 文档列的）文档库。
  2. 统一入口 load_all_page_dicts() 由调用方决定 sink（可再接 MongoDB 等）。

用法（CLI）：  ocr_workbench.py json2db [--db 路径] [--book 书名]
本地:          OCR_ROOT=数据路径 PYTHONPATH=src python scripts/ocr_workbench.py json2db
Colab:         同上，OCR_ROOT 指向 Drive；DB 落 {输出根}/book.db
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterator, Optional

from .paths import get_output_dir


def load_all_page_dicts(data_dir: str | Path) -> Iterator[dict]:
    """从 data/ 目录 yield 每页的 PageResult.to_dict()（跳过 .marked 等非 page_.json）。"""
    data_dir = Path(data_dir)
    if not data_dir.exists():
        return
    for p in sorted(data_dir.glob("page_*.json")):
        try:
            yield json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue


# ---------------- SQLite 导入 ----------------

def default_db_path() -> Path:
    """默认导入目标：{输出根}/book.db。可经 --db 覆盖。"""
    return get_output_dir() / "book.db"


def import_json_to_sqlite(
    data_dir: str | Path,
    db_path: str | Path | None = None,
    *,
    book: str = "book",
) -> dict[str, int]:
    """把 data/*.json 全部导入 SQLite 数据库。

    建表：
      pages       每页整篇 JSON 文档（doc TEXT）+ 元数据列
      char_index  单字检索（char/orig_char/status/is_rare/box）
      rare        生僻字清单

    返回统计 {pages, chars, rare}。
    """
    db_path = Path(db_path) if db_path else default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS pages(
            page TEXT PRIMARY KEY, book TEXT, image TEXT,
            width INTEGER, height INTEGER, doc TEXT NOT NULL)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS char_index(
            book TEXT, page TEXT, char_id TEXT, char TEXT, orig_char TEXT,
            status TEXT, is_rare INTEGER, rare_reason TEXT,
            box TEXT, PRIMARY KEY(page, char_id))""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_char ON char_index(char)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rare ON char_index(is_rare)")
        cur.execute("""CREATE TABLE IF NOT EXISTS rare(
            char TEXT PRIMARY KEY, count INTEGER, positions TEXT,
            group_id TEXT, note TEXT)""")

        n_pages = n_chars = 0
        rare_buckets: dict[str, dict] = {}
        for page_dict in load_all_page_dicts(data_dir):
            page = page_dict["page"]
            cur.execute("INSERT OR REPLACE INTO pages(page,book,image,width,height,doc) "
                        "VALUES(?,?,?,?,?,?)",
                        (page, book, page_dict.get("image", ""),
                         page_dict.get("width", 0), page_dict.get("height", 0),
                         json.dumps(page_dict, ensure_ascii=False)))
            cur.execute("DELETE FROM char_index WHERE page=?", (page,))
            for c in page_dict.get("chars", []):
                is_rare = 1 if c.get("is_rare") else 0
                cur.execute(
                    "INSERT OR REPLACE INTO char_index"
                    "(book,page,char_id,char,orig_char,status,is_rare,rare_reason,box) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (book, page, c.get("id", ""), c.get("char", ""),
                     c.get("orig_char", ""), c.get("status", ""),
                     is_rare, c.get("rare_reason"),
                     json.dumps(c.get("box", {}))))
                n_chars += 1
                if is_rare:
                    ch = c.get("char", "") or c.get("orig_char", "")
                    if ch:
                        b = rare_buckets.setdefault(ch, {"count": 0, "positions": []})
                        b["count"] += 1
                        b["positions"].append({"page": page, "id": c.get("id", ""),
                                               "reason": c.get("rare_reason")})
            n_pages += 1

        cur.execute("DELETE FROM rare")
        for ch, b in rare_buckets.items():
            cur.execute("INSERT OR REPLACE INTO rare(char,count,positions,group_id,note) "
                        "VALUES(?,?,?,?,?)",
                        (ch, b["count"], json.dumps(b["positions"], ensure_ascii=False),
                         None, ""))
        conn.commit()
        return {"pages": n_pages, "chars": n_chars, "rare": len(rare_buckets)}
    finally:
        conn.close()


def load_from_sqlite(db_path: str | Path) -> Iterator[dict]:
    """从导入的 SQLite 库读取每页文档，还原为 PageResult.to_dict()。"""
    db_path = Path(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT doc FROM pages ORDER BY page").fetchall()
        for r in rows:
            yield json.loads(r["doc"])
    finally:
        conn.close()