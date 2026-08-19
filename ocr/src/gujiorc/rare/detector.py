"""gujiorc.rare.detector — 生僻字判定（M4）。

方法：反向筛选——识别出的字若不在「常用字集合」→ 生僻字。
常用字来源：内置小型常用字集（可扩展为《通用规范汉字表》文件）。

判定规则（对应 PLANS.md M4）：
- char 非空 且 在常用字集合 → 非生僻
- char 非空 且 不在常用字集合 → is_rare, reason=not_in_common_set
- char 为空 或 为(非法)  → 由管道 conf 标记 low_conf（此处保留原 is_rare）

白名单：术数常用字（孛/罗/炁/计等），避免误判。
"""
from __future__ import annotations

from pathlib import Path

from ..core.models import PageResult, CharBox, RARE_NOT_IN_COMMON, RARE_LOW_CONF

# 内置常用字集合（子集 + 术数白名单）
# 生产应改为加载《通用规范汉字表》文件（见 data/common_hanzi.txt），
# 这里内置常用字符 + 术数专名白名单，确保开箱可用。
# 说明：内置集合为「兜底」，覆盖常用简体/繁体字 + 术数术语；
# 如需精确覆盖请放置 data/common_hanzi.txt（8105字），程序优先加载它。
_COMMON_HANZI = set(
    "的一是在不了有和人这中大为上国个我到他产与子说地产地山水"
    "金银木土火日月星辰天地神鬼阴阳五行金木水火土甲乙丙丁戊己庚辛壬癸"
    "子丑寅卯辰巳午未申酉戌亥东南西北中上下前后左右吉凶祸福生死贵贱"
    "命身官禄财帛兄弟妻子父母奴仆相貌福德夫妻田宅迁移疾厄交友官禄十二"
    "年岁时日时刻春秋冬夏寒热燥湿长短大小多少善恶美丑轻重方圆曲直经纬"
    "星命七政四余宫度篇姓名术数占卜算卦命理流年大运小运流月流日流时"
    "卷之一二三目錄論定名下總本全卷篇錄後前另共又分合生克冲"
    "得之用其于而所则为如果因此之地与缘来去在方等作物事时行成"
    "其因所主割归断察凡唯当故知乎道其之言不作有生其在人如此"
    "也無知二七八九十百千万罗计孛炁六七八九数不天地下"
    "論日出入生時端的关于命由自无有相自日月所与同合对三也"
)
# 扩充常见常用字（保证日常用字不误判）
_COMMON_HANZI |= set(
    "你你我我是他她它我们他们它们这那这哪些什么怎问好吗吗呢吧啊"
    "今明天地人风鸟鱼马牛羊鸡犬豕兽谷豆麦稻粟禾稼穑耕农工商贾贩买"
    "学教习读记张绘画写文章诗书琴棋书画酒茶杯盘碗筷桌椅床凳门窗墙壁"
    "花叶果枝根茎藤草树林木竹松柏桃李梅杏橘柚橘果蔬"
    "手足口眼耳鼻舌身血脉肉骨皮毛羽翼爪牙角蹄须发面颚颈肩背腰腹膝踝踵趾"
    "毛发须鬓眉睫唇齿舌咽喉肠胃肝胆脾肺心肾膀胱大小肠"
    "圣贤才智德仁义礼智信忠孝节廉耻勇刚柔仁义"
    "天地玄黄宇宙洪荒日月盈昃辰宿列张寒来暑往秋收冬藏闰余成岁律吕调阳"
    "云腾致雨露结为霜金生丽水玉出昆冈剑号巨阙珠称夜光果珍李柰菜重芥姜"
    "海咸河淡鳞潜羽翔龙师火帝鸟官人皇始制文字乃服衣裳推位让国有虞陶唐"
    "吊民伐罪周发殷汤坐朝问道垂拱平章爱育黎首臣伏戎羌遐迩壹体率宾归王"
    "鸣凤在竹白驹食场化被草木赖及万方盖此身发四大五常恭惟鞠养岂敢毁伤"
    "女慕贞洁男效才良知过必改得能莫忘罔谈彼短靡恃己长信使可覆器欲难量"
    "墨悲丝染诗赞羔羊景行维贤克念作圣德建名立形端表正空谷传声虚堂习听"
    "祸因恶积福缘善庆尺璧非宝寸阴是竞资父事君曰严与敬孝当竭力忠则尽命"
    "临深履薄夙兴温凊似兰斯馨如松之盛川流不息渊澄取映容止若思言辞安定"
    "笃初诚美慎终宜令荣业所基籍甚无竟学优登仕摄职从政存以甘棠去而益咏"
    "乐殊贵贱礼别尊卑上和下睦夫唱妇随外受傅训入奉母仪诸姑伯叔犹子比儿"
    "孔怀兄弟同气连枝交友投分切磨箴规仁慈隐恻造次弗离节义廉退颠沛匪亏"
    "性静情逸心动神疲守真志满逐物意移坚持雅操好爵自縻都邑华夏东西二京"
    "背邙面洛浮渭据泾宫殿盘郁楼观飞惊图写禽兽画彩仙灵丙舍傍启甲帐对楹"
)


# 术数专名白名单（常见但不在常用字表的星曜/术语）
_TECHNIQUE_WHITELIST = set("孛炁羅計測祿祿臺祭審銓") | {"罗", "计", "孛", "炁", "敬", "龢", "乾"}

# 繁体常用字扩充（本系统针对繁体古籍，内置覆盖常用繁简字，降低误判）
_COMMON_HANZI |= set(
    "為貴逢夾臨晝殺或看法只休咎然新駕近馬格東脫陷弱宮並富高強實滋"
    "妙餘皆客曜假秘訣錢唐朝長樂鄭機振録西全菴胡文煥論目總本篇篇後前另四正"
    "春令水孛妙金處地又心智明於與這那誰什麼並定實久久難進達廬遠近過過"
    "應該當謝釀解釋決絕況況然棄棄輩屬屬氣條條後電電發發頭頭顧顧願願"
    "顯顯現現談談討討論論謙謙讓讓讓護護醫醫藥藥療療瞭瞭魚魚鳥鳥馬馬"
    "車車貝貝財財買買賣賣貴貴賤賤賢賢德德禮禮節節謙謙讓讓信信仰仰承承"
)

# 用于快速过滤「非汉字」（标点/数字/符号不判生僻）
_HANZI_CHECK = lambda c: '\u4e00' <= c <= '\u9fff'   # noqa: E731


def build_common_set(extra: str = "", table_path: str | None = None) -> set[str]:
    """构建常用字集合。

    优先级：外部 common_hanzi.txt（若提供且存在） > 内置常用字集。
    再叠加术数白名单 + extra。
    """
    s = set(_COMMON_HANZI) | _TECHNIQUE_WHITELIST

    if table_path and Path(table_path).exists():
        try:
            text = Path(table_path).read_text(encoding="utf-8")
            loaded = set(text.replace("\n", "").replace("\r", ""))
            loaded.discard(" ")
            if loaded:
                s = loaded | _TECHNIQUE_WHITELIST  # 外部表为准 + 白名单
        except Exception:
            pass  # 加载失败则用内置

    for ch in extra:
        s.add(ch)
    return s


def parse_char(text: str) -> str:
    """从 PaddleOCR 输出的文本块提取判定用字符。

    本阶段文本块可能含多字/标点；生僻判定主要针对单字。
    若文本含多个汉字且全部常见，不算生僻；若有任一不常见汉字，标生僻。
    """
    # 取所有汉字字符
    hanzi = [c for c in text if _HANZI_CHECK(c)]
    return "".join(hanzi)


def detect_rare_chars(page: PageResult, common_set: set[str] | None = None,
                      conf_thresh: float = 0.6) -> list[CharBox]:
    """对一页所有字框做生僻判定，更新 is_rare/rare_reason。

    生僻字来源二：
    1. not_in_common_set：汉字不在常用字集（含白名单）
    2. low_conf：识别置信度 < conf_thresh（形变/模糊字，需人工确认）

    注意：本阶段 PaddleOCR 输出的是「行/列文本块」，先按整块判定；
    真正的单字切分(M2)完成后，生僻判定按单字重新跑。
    """
    if common_set is None:
        common_set = build_common_set()

    for ch in page.chars:
        # 低置信度 → 标 low_conf（不因常见字就免除）
        if ch.conf < conf_thresh:
            ch.is_rare = True
            ch.rare_reason = RARE_LOW_CONF
            ch.extra["rare_hits"] = list(parse_char(ch.char))
            continue

        hanzi = parse_char(ch.char)
        if not hanzi:
            # 无汉字(纯符号/空) → 保持原状态，不判生僻
            continue

        # 若整块文本的所有汉字都在常用集 → 非生僻
        rare_chars = [c for c in hanzi if c not in common_set]
        if rare_chars:
            ch.is_rare = True
            ch.rare_reason = RARE_NOT_IN_COMMON
            # 记录命中的生僻字（供清单用）
            ch.extra["rare_hits"] = rare_chars
        # 否则 ch.is_rare 保持原状（可能 false 或 low_conf）

    return page.chars


def build_rare_list(pages: list[PageResult]) -> list:
    """汇总多页生僻字清单（RareChar 列表）。"""
    from collections import defaultdict
    from ..core.models import RareChar

    agg = defaultdict(list)   # char -> [position dicts]
    for page in pages:
        for ch in page.chars:
            hits = ch.extra.get("rare_hits") or ([ch.char] if ch.is_rare and ch.char else [])
            for hc in hits:
                if not _HANZI_CHECK(hc):
                    continue
                agg[hc].append({
                    "page": page.page,
                    "id": ch.id,
                    "box": ch.box,
                    "reason": ch.rare_reason,
                    "conf": ch.conf,
                })

    rare_list = []
    for char, positions in agg.items():
        rare_list.append(_mk_rarechar(char, positions))
    rare_list.sort(key=lambda r: -r.count)
    return rare_list


def _mk_rarechar(char, positions):
    from ..core.models import RareChar
    return RareChar(
        char=char,
        count=len(positions),
        positions=positions,
    )