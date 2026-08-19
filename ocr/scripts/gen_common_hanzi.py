#!/usr/bin/env python3
"""生成完整《常用字表》(common_hanzi.txt) 供生僻字判定。

数据来源：GB2312 一级字库（3755 常用简字）— 内嵌码表解码，
         + 常用繁体字扩展 + 术数专名白名单。

用法：
    python scripts/gen_common_hanzi.py [输出路径]
默认输出: data/common_hanzi.txt（程序自动优先加载）

为什么需要完整字表：
    内置兜底集合太小，正文会误判常见字为生僻（如 妾/路/限/則/帶）。
    放完整字表后生僻字判定才准确。
"""
from __future__ import annotations

import sys
from pathlib import Path

# GB2312 一级字库（区位码 16-55，常用简体字）
# 用 Python 内置编码 gb2312 解码 0xB0A1 起的一级字库
def gen_gb2312_level1() -> str:
    """解码 GB2312 一级字库（3755 常用字）。"""
    chars = []
    # 一级汉字区 0xA1A1 之后: 从第16区(0xB0A1)到第55区
    for row in range(0xB0, 0xD8):  # 176-215 区
        for col in range(0xA1, 0xFF):
            if len(chars) >= 3755:
                break
            code = bytes([row, col])
            try:
                chars.append(code.decode("gb2312"))
            except UnicodeDecodeError:
                continue
        if len(chars) >= 3755:
            break
    return "".join(chars)


# 常用繁体字补充（常见但不在 GB2312 一级的繁体）
_TRAD_EXTRA = (
    "為貴逢夾臨晝殺看法只休咎然新駕近馬格東脫陷弱宮並富高強實滋妙餘"
    "皆客曜假秘訣錢唐朝長樂鄭機振録西全菴胡文煥論目總本篇後前另四正"
    "處識醫藥萬華豐經籍書畫體製質麗聲響聽歸歸會會擴擴護護讓讓議議論辨"
    "發達進退過適選擇還這那麼她它什麼樣那些和他們我你的真的很就都是不會"
    "則帶奪僕妾陰陽幹支辰星宿曆並萬歲嘉靖洪武崇禎康熙乾納祿癸乙戊庚辛"
    "鸞鳳麒麟鶴鹿龜蛇龍虎豹象鳥魚鱗羽頦翼絲縷綵繡旗旂旌麾鍾鼓鐸鈴笏笏"
    "時時閑飛勞華傳賢內助榮垣斷應俊貧賤歲業蕩胎劫霞忌亡破居符害尅即應"
    "璧池灣無則帶奪僕妾結麗巽坎離震兌艮乾坤天地泰孫將帥兵卒朝廷官府衙"
    "禦衛侍僕隸從隨喚喚請華榮貴顯貴達路道途程屯戍邊疆域表裡內外官司訟"
    "牒文契據守護衛衛戰鬪鬪競勝負勝敗降服扶佐佐助嘉慶賀慶壽誕辰亥巳午"
    "酉丑未卯辰巳於焉無論皆悉只緣卻终究該當故因此所以則然者矣乎哉焉耳"
)

# 术数专名白名单
_TECH = "孛炁羅計睺曜格祿祕訣"

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else str(
        Path(__file__).resolve().parent.parent / "data" / "common_hanzi.txt"
    )
    all_chars = gen_gb2312_level1() + _TRAD_EXTRA + _TECH

    # 去重保序
    seen = set()
    unique = []
    for ch in all_chars:
        if ch not in seen and "\u4e00" <= ch <= "\u9fff":
            seen.add(ch)
            unique.append(ch)

    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(unique), encoding="utf-8")
    print(f"✅ 生成常用字表 {len(unique)} 字 → {path}")
    print(f"   探测器 build_common_set() 将自动加载它（若位于 data/common_hanzi.txt）")


if __name__ == "__main__":
    main()