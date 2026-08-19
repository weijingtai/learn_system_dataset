"""gujiorc.core.storage — 存储抽象层（本地 + Colab 复用）。

对应 PLANS.md §4.2「存储双轨」：
- 主存储：每页一个 JSON（git 可 diff/回滚）
- 派生索引：SQLite FTS5（全文索引所有字）

所有路径通过 paths.get_root() 解析，不硬编码，保证本地 → Colab 无缝。
本地默认根 data_work/；Colab 设 OCR_ROOT=/content/drive/MyDrive/ocr_work。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from .models import PageResult, RareChar
from .paths import get_root, ensure_struct


# ---------------- JSON 主存储 ----------------

def save_page_json(page: PageResult) -> Path:
    """保存一页识别结果为 JSON，原子写入。"""
    struct = ensure_struct()
    path = struct["data"] / f"{page.page}.json"
    _atomic_write_json(path, page.to_dict())
    return path


def load_page_json(page: str) -> Optional[PageResult]:
    """读取一页识别结果 JSON。"""
    struct = ensure_struct()
    path = struct["data"] / f"{page}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return PageResult.from_dict(json.load(f))


def _atomic_write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


# ---------------- SQLite 派生索引 ----------------

class CharIndex:
    """全字全文索引（M5）。SQLite FTS5。用 from_json 重建，不手工编辑。"""

    DB_NAME = "index.db"

    def __init__(self, db_path: str | Path | None = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(get_root()) / self.DB_NAME
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._create()

    def _create(self):
        cur = self.conn.cursor()
        # FTS5 虚拟表（若 FTS5 可用）
        cur.execute("""
            CREATE TABLE IF NOT EXISTS char_index(
                book TEXT, page TEXT, char_id TEXT, char TEXT,
                status TEXT, box TEXT,
                PRIMARY KEY(page, char_id)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_char ON char_index(char)")
        self.conn.commit()

    def rebuild_from_page(self, page: PageResult):
        """用一页识别结果重建该页索引。"""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM char_index WHERE page=?", (page.page,))
        for c in page.chars:
            cur.execute(
                "INSERT OR REPLACE INTO char_index(book,page,char_id,char,status,box) "
                "VALUES(?,?,?,?,?,?)",
                (page.book, page.page, c.id, c.char, c.status, json.dumps(c.box)),
            )
        self.conn.commit()

    def query_char(self, target: str) -> list[dict]:
        """查询某字所有出现位置（页+框ID+坐标+状态）。"""
        cur = self.conn.cursor()
        cur.execute("SELECT page, char_id, char, status, box FROM char_index "
                    "WHERE char=? ORDER BY page, char_id", (target,))
        return [dict(r) for r in cur.fetchall()]

    def duplicates(self, min_count: int = 2) -> list[dict]:
        """重复字统计（M11_）：字 + 次数 + 位置列表。"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT char, COUNT(*) cnt, GROUP_CONCAT(page || ':' || char_id) positions
            FROM char_index GROUP BY char HAVING cnt >= ? ORDER BY cnt DESC
        """, (min_count,))
        return [dict(r) for r in cur.fetchall()]

    def close(self):
        self.conn.close()


# ---------------- 生僻字清单 ----------------

def save_rare_list(rare_chars: list[RareChar]) -> Path:
    struct = ensure_struct()
    path = struct["rare"] / "rare_characters.json"
    _atomic_write_json(path, {"rare_characters": [r.to_dict() for r in rare_chars]})
    return path