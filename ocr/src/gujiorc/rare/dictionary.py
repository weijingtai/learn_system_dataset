"""gujiorc.rare.dictionary — 生僻字查询 + 拆解（R8/R9，PLANS M6_）。

本地方案（全离线）：
1. 查询读音/释义：
   - 优先：外部 Unihan 离线库 data/unihan/unihan.json（读音 kMandarin / 释义 kDefinition）
   - 回退：Python 内置 unicodedata（只给名字/分类，无读音）
2. 拆解部首/笔画：
   - Unihan kRSUnicode（部首）+ kTotalStrokes（笔画）
   - 回退：内置常用部首表 + 简单笔画统计

设计：Unihan 数据可选。缺省时用内置 unicodedata + 部首表兜底，保证开箱可用。
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Optional


# ---------------- 内置常用部首表（CJK 部首，用于拆解兜底） ----------------
_COMMON_RADICALS = {
    "一": "横", "丨": "竖", "丶": "点", "丿": "撇", "乙": "折", "亅": "竖钩",
    "二": "二", "亠": "亠", "人": "人", "儿": "儿", "入": "入", "八": "八",
    "冂": "冂", "冖": "冖", "冫": "两点水", "几": "几", "凵": "凵", "刀": "刀",
    "力": "力", "勹": "包字头", "匕": "匕", "匚": "区字框", "匸": "匸", "十": "十字",
    "卜": "卜", "卩": "单耳旁", "厂": "厂", "厶": "私字旁", "又": "又", "口": "口",
    "囗": "国字框", "土": "土", "士": "士", "夂": "夂", "夊": "夊", "夕": "夕",
    "大": "大", "女": "女", "子": "子", "宀": "宝盖头", "寸": "寸", "小": "小",
    "尢": "尢", "尸": "尸", "屮": "屮", "山": "山", "巛": "巛", "工": "工",
    "己": "己", "巾": "巾", "干": "干", "幺": "幺", "广": "广", "廴": "建字旁",
    "廾": "廾", "弋": "弋", "弓": "弓", "彐": "彐", "彡": "三撇", "彳": "双人旁",
    "心": "心", "戈": "戈", "戶": "户", "手": "手", "支": "支", "攴": "攴",
    "文": "文", "斗": "斗", "斤": "斤", "方": "方", "无": "无", "日": "日",
    "曰": "曰", "月": "月", "木": "木", "欠": "欠", "止": "止", "歹": "歹",
    "殳": "殳", "毋": "毋", "比": "比", "毛": "毛", "氏": "氏", "气": "气",
    "水": "水", "火": "火", "爪": "爪", "父": "父", "爻": "爻", "爿": "爿",
    "片": "片", "牙": "牙", "牛": "牛", "犬": "犬", "玄": "玄", "玉": "玉",
    "瓜": "瓜", "瓦": "瓦", "甘": "甘", "生": "生", "用": "用", "田": "田",
    "疋": "疋", "疒": "病字头", "癶": "癶", "白": "白", "皮": "皮", "皿": "皿",
    "目": "目", "矛": "矛", "矢": "矢", "石": "石", "示": "示", "禸": "禸",
    "禾": "禾", "穴": "穴", "立": "立", "竹": "竹", "米": "米", "糸": "糸",
    "缶": "缶", "网": "网", "羊": "羊", "羽": "羽", "老": "老", "而": "而",
    "耒": "耒", "耳": "耳", "聿": "聿", "肉": "肉", "臣": "臣", "自": "自",
    "至": "至", "臼": "臼", "舌": "舌", "舛": "舛", "舟": "舟", "艮": "艮",
    "色": "色", "艸": "艹", "虍": "虍", "虫": "虫", "血": "血", "行": "行",
    "衣": "衣", "襾": "襾", "見": "见", "角": "角", "言": "言", "谷": "谷",
    "豆": "豆", "豕": "豕", "豸": "豸", "貝": "贝", "赤": "赤", "走": "走",
    "足": "足", "身": "身", "車": "车", "辛": "辛", "辰": "辰", "辵": "辶",
    "邑": "邑", "酉": "酉", "釆": "釆", "里": "里", "金": "金", "長": "长",
    "門": "门", "阜": "阜", "隶": "隶", "隹": "隹", "雨": "雨", "靑": "青",
    "非": "非", "面": "面", "革": "革", "韋": "韦", "韭": "韭", "音": "音",
    "頁": "页", "風": "风", "飛": "飞", "食": "食", "首": "首", "香": "香",
    "馬": "马", "骨": "骨", "高": "高", "髟": "髟", "鬥": "斗", "鬯": "鬯",
    "鬲": "鬲", "鬼": "鬼", "魚": "鱼", "鳥": "鸟", "鹵": "卤", "鹿": "鹿",
    "麥": "麦", "麻": "麻", "黃": "黄", "黍": "黍", "黑": "黑", "黹": "黹",
    "黽": "黾", "鼎": "鼎", "鼓": "鼓", "鼠": "鼠", "鼻": "鼻", "齊": "齐",
    "齒": "齿", "龍": "龙", "龜": "龟", "龠": "龠",
}


# ---------------- 内置术数生僻字字典（开箱即用，不依赖 Unihan） ----------------
# 覆盖常见术数/古籍生僻字。字段：reading=拼音, radical=部首, strokes=笔画, definition=释义
_BUILTIN_DICT: dict[str, dict] = {
    "孛": {"reading": "bèi", "radical": "子", "strokes": 7,
            "definition": "星名；光芒四射。七政四余中的月孛"},
    "炁": {"reading": "qì", "radical": "火", "strokes": 8,
            "definition": "同'气'；紫炁（七政四余中的吉星）"},
    "羅": {"reading": "luó", "radical": "网", "strokes": 19,
            "definition": "同'罗'；罗睺（七政四余中的蚀神）"},
    "計": {"reading": "jì", "radical": "言", "strokes": 9,
            "definition": "同'计'；计都（七政四余中的蚀神）"},
    "睺": {"reading": "hóu", "radical": "目", "strokes": 15,
            "definition": "罗睺之'睺'"},
    "曜": {"reading": "yào", "radical": "日", "strokes": 18,
            "definition": "日、月、星总称；七政七曜"},
    "格": {"reading": "gé", "radical": "木", "strokes": 10,
            "definition": "格式、格局；命理中的格"},
    "祿": {"reading": "lù", "radical": "示", "strokes": 12,
            "definition": "同'禄'；官禄、天禄"},
    "祕": {"reading": "mì", "radical": "示", "strokes": 10,
            "definition": "同'秘'；神秘、秘书"},
    "訣": {"reading": "jué", "radical": "言", "strokes": 11,
            "definition": "同'诀'；口诀、要诀"},
    "巍": {"reading": "wēi", "radical": "山", "strokes": 20,
            "definition": "高大"},
    "龘": {"reading": "dá", "radical": "龍", "strokes": 48,
            "definition": "龙飞之貌（三龙）"},
    "龢": {"reading": "hé", "radical": "龠", "strokes": 22,
            "definition": "同'和'；和谐"},
    "曇": {"reading": "tán", "radical": "日", "strokes": 16,
            "definition": "多云"},
    "玅": {"reading": "miào", "radical": "玉", "strokes": 7,
            "definition": "同'妙'；高妙"},
    "建": {"reading": "jiàn", "radical": "廴", "strokes": 8,
            "definition": "建立"},
}


def _builtin_lookup(char: str) -> dict | None:
    return _BUILTIN_DICT.get(char)


# ---------------- Unihan 离线库 ----------------

class Unihan:
    """Unihan 数据库查询（读音/部首/笔画）。data/unihan/unihan.json 可选。"""

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent / "data" / "unihan"
        self._db: dict = {}
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        for fname in self.data_dir.glob("*.json"):
            try:
                with open(fname, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    # 兼容两种结构：{码点: {...}} 或 {char: {...}}
                    for k, v in data.items():
                        real = unicode_from_key(k)
                        if real:
                            self._db[real] = v
                    self._loaded = True
                    return
            except Exception:  # noqa
                continue
        # 找到第一个可用 json 即返回
        for fname in self.data_dir.glob("Unihan*.txt"):
            try:
                self._load_txt(fname)
                self._loaded = True
                return
            except Exception:  # noqa
                continue
        self._loaded = True  # 无数据

    def _load_txt(self, path: Path):
        """解析 Unihan_*.txt 格式（U+XXXXX \t field \t value）。"""
        recs: dict[str, dict] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            cp = parts[0].strip()
            field = parts[1].strip()
            value = parts[2].strip()
            ch = unicode_from_key(cp)
            if ch:
                recs.setdefault(ch, {})[field] = value
        self._db = recs

    def lookup(self, char: str) -> dict | None:
        self._load()
        if not self._db:
            return None
        return self._db.get(char)


def unicode_from_key(key: str) -> str:
    """把 'U+4E16' / '4E16' / 直接字符 转为字符。"""
    key = key.strip()
    if len(key) == 1 and "\u4e00" <= key <= "\u9fff":
        return key
    if key.upper().startswith("U+"):
        key = key[2:]
    try:
        return chr(int(key, 16))
    except ValueError:
        return ""


# ---------------- 统一查询入口 ----------------

def lookup_char(char: str, unihan: Unihan | None = None) -> dict:
    """查询一个字：读音/部首/笔画/释义。返回 dict（部分字段可能缺失）。"""
    if unihan is None:
        unihan = Unihan()
    info = unihan.lookup(char)
    result = {"char": char, "unicode": f"U+{ord(char):04X}"}

    # 内置字典（优先，术数生僻字开箱即用）
    builtin = _builtin_lookup(char)
    if builtin:
        result.update({k: v for k, v in builtin.items() if k != "char"})

    # 内置 unicodedata 基本信息
    try:
        result["name"] = unicodedata.name(char, "（无名称）")
        result["category"] = unicodedata.category(char)
    except Exception:  # noqa
        pass

    # Unihan 增强字段（覆盖内置的字段）
    if info:
        r = info.get("kRSUnicode")
        if r:
            result["radical"] = r
        s = info.get("kTotalStrokes")
        if s:
            result["strokes"] = s.split(" ")[0]
        m = info.get("kMandarin")
        if m:
            result["reading"] = m
        d = info.get("kDefinition")
        if d:
            result["definition"] = d

    return result


def decompose_char(char: str, unihan: Unihan | None = None) -> dict:
    """拆解生僻字：部首 + 笔画 + 音 + 义。"""
    if unihan is None:
        unihan = Unihan()
    info = lookup_char(char, unihan)

    # 拆解：若 char 恰为常用部首本身，或含成字部件
    result = {
        "char": char,
        "unicode": info.get("unicode", f"U+{ord(char):04X}"),
    }

    # 部首（Unihan 或匹配内置表）
    radical = info.get("radical") or _match_radical(char)
    if radical:
        result["radical"] = radical

    # 笔画（Unihan 或内置估算）
    strokes = info.get("strokes") or _estimate_strokes(char)
    if strokes:
        result["strokes"] = strokes

    # 读音释义
    for k in ("reading", "definition", "name"):
        if info.get(k):
            result[k] = info[k]

    return result


def _match_radical(char: str) -> str | None:
    """用内置部首表匹配：若 char 恰是某部首页，或包含某部首。"""
    # 精确匹配（char 本身就是部首页）
    if char in _COMMON_RADICALS:
        return _COMMON_RADICALS[char]
    # 未命中则返回 None（不臆造）
    return None


def _estimate_strokes(char: str) -> int:
    """笔画估算（fallback）：用 Unicode 规范化后的简单计数。非精确，仅在无 Unihan 时用。"""
    # 简化估算：按字母/笔画近似，实际应由 Unihan 提供
    return 0  # 未知，返回 0 表示无数据


# ---------------- 快捷函数 ----------------

def query_rare(char: str, data_dir: str | Path | None = None) -> dict:
    """便捷查询：综合 lookup + decompose。"""
    unihan = Unihan(data_dir)
    return decompose_char(char, unihan)