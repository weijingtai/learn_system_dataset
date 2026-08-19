"""gujiorc.index.fulltext — 全字全文索引（M5）+ 重复字统计（M11_）。

用 SQLite 普通表 + 索引（兼容 FTS5 不可用环境），支持：
- rebuild_from_page：从一页识别结果建索引
- query_char：查某字所有出现位置
- duplicates：重复字统计
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..core.models import PageResult
from ..core.paths import get_root


class CharIndex:
    """全字全文索引。可换 FTS5（若本机支持），默认普通表 + BTREE 索引。"""

    def __init__(self, db_path: str | Path | None = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(get_root()) / "index.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        c = self._conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS char_index(
                book TEXT DEFAULT '',
                page TEXT NOT NULL,
                char_id TEXT NOT NULL,
                char TEXT NOT NULL,
                status TEXT,
                box TEXT,
                PRIMARY KEY(page, char_id)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_char_char ON char_index(char)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_char_page ON char_index(page)")
        self._conn.commit()

    def rebuild_from_page(self, page: PageResult):
        """用一页识别结果重建/覆盖该页索引。"""
        c = self._conn.cursor()
        c.execute("DELETE FROM char_index WHERE page=?", (page.page,))
        for ch in page.chars:
            char = (ch.char or "").strip()
            if not char:
                continue
            c.execute(
                "INSERT OR REPLACE INTO char_index(book,page,char_id,char,status,box) "
                "VALUES(?,?,?,?,?,?)",
                (page.book or "", page.page, ch.id, char, ch.status, json.dumps(ch.box, ensure_ascii=False)),
            )
        self._conn.commit()

    def query_char(self, target: str, substring: bool = True) -> list[dict]:
        """查某字所有出现位置（页+框ID+坐标+状态）。

        当前阶段 char 存整行/列文本（单字切分前），用子串匹配（LIKE）
        保证能查出包含该字的行；单字切分完成后可改为精确匹配。
        """
        c = self._conn.cursor()
        if substring:
            c.execute(
                "SELECT page, char_id, char, status, box FROM char_index "
                "WHERE char LIKE ? ORDER BY page, char_id",
                (f"%{target}%",),
            )
        else:
            c.execute(
                "SELECT page, char_id, char, status, box FROM char_index "
                "WHERE char=? ORDER BY page, char_id",
                (target,),
            )
        return [dict(r) for r in c.fetchall()]

    def duplicates(self, min_count: int = 2) -> list[dict]:
        """重复字统计（M11_）：字+次数+位置列表。"""
        c = self._conn.cursor()
        c.execute("""
            SELECT char, COUNT(*) cnt,
                   GROUP_CONCAT(page || ':' || char_id, ' | ') positions
            FROM char_index
            GROUP BY char HAVING cnt >= ?
            ORDER BY cnt DESC
        """, (min_count,))
        return [dict(r) for r in c.fetchall()]

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()