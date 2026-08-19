"""gujiorc.rare.dictionary — 生僻字查询 + 拆解（M6_）。

本地方案：
- 查询：macOS Dictionary.app（CJK）+ Unihan 离线库（读音/部首/笔画/释义）
- 拆解：Unihan kRSUnicode（部首） + GlyphWiki 字形分解（可选，需离线库）

这些是「可选增强」——若对应系统/数据不可用，手动回退。
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


# ---------------- Unihan 离线库 ----------------

class Unihan:
    """Unihan 数据库查询（读音/部首/笔画）。数据从 data/unihan/ 加载。

    若 Unihan 数据未安装，方法返回 None（退化）。
    """

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent / "data" / "unihan"
        self._db: dict = {}
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        # 尝试加载单调 JSON 或 field 文件
        for fname in ("unihan.json", "Unihan.json"):
            p = self.data_dir / fname
            if p.exists():
                with open(p, encoding="utf-8") as f:
                    self._db = json.load(f)
                self._loaded = True
                return
        # 空 → 未安装
        self._loaded = True

    def lookup(self, char: str) -> dict | None:
        self._load()
        if not self._db:
            return None
        cp = hex(ord(char)).upper()[2:]
        rec = self._db.get(cp) or self._db.get(char)
        if not rec:
            return None
        return {"char": char, "unicode": f"U+{cp:04X}", **rec}


# ---------------- macOS Dictionary ----------------

def macos_dictionary_lookup(char: str) -> str | None:
    """调用 macOS Dictionary.app 查字。返回释义文本或 None。"""
    # 尝试用 `dict`/AppleScript 查询（非所有系统可用）
    script = f'''
    tell application "Dictionary"
        {{frontmost}}
    end tell
    '''
    try:
        # 使用 dictionaries 查询（仅限本机 macOS + GUI）
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5,
        )
        # 这里仅为探测 Dictionary 可用性；实际查询交互式较复杂
        if r.returncode == 0:
            return None  # 返回 None，避免假数据
    except Exception:
        pass
    return None


# ---------------- 拆解（Unihan 部首） ----------------

def decompose_unicode(char: str, unihan: Unihan | None = None) -> dict | None:
    """拆解生僻字（部首/部件）。基于 Unihan kRSUnicode。"""
    if unihan is None:
        unihan = Unihan()
    info = unihan.lookup(char)
    if info is None:
        return None
    radical = info.get("kRSUnicode") or info.get("radical")
    strokes = info.get("kTotalStrokes") or info.get("strokes")
    return {
        "char": char,
        "radical": radical,
        "strokes": strokes,
        "kDefinition": info.get("kDefinition"),
        "kMandarin": info.get("kMandarin"),
    }