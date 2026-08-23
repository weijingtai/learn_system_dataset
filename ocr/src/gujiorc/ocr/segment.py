"""gujiorc.ocr.segment — 单字切分（PLANS M2）。

对 PaddleOCR 输出的「整行/整列文本块」做单字切分，得到每个字的独立 box。

方法（针对竖排古籍）：
1. 识别一个文本块的「主方向」：宽>高 → 横排；高>宽 → 竖排
2. 沿主方向把块裁成细条，逐条统计暗像素密度（在原始灰度图上）
3. 密度高的条 = 笔画区，密度低的条 = 字间空白 → 投影找字边界
4. 由字边界得到每个单字的 box

依赖：需要原始图像（灰度）来测投影。
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from ..core.models import CharBox, PageResult, STATUS_UNRECOGNIZED


def _load_gray(image) -> np.ndarray:
    """加载为灰度 numpy 数组（H,W）。image 可为路径/numpy/PIL。"""
    if isinstance(image, str):
        return np.array(Image.open(image).convert("L"))
    if hasattr(image, "shape"):
        # 已是 numpy（BGR/RGB/灰度）
        arr = np.asarray(image)
        if arr.ndim == 3:
            return np.dot(arr[..., :3], [0.299, 0.587, 0.114]).astype(np.uint8)
        return arr
    return np.array(image.convert("L"))  # PIL


def is_vertical(box: dict) -> bool:
    """判断文本块主方向：高 > 宽 → 竖排。"""
    return box["h"] > box["w"]


# 墨迹二值化参数。不能用固定阈值 `region < 128`：古籍扫描的背面透印字、浅印字
# 整体灰度落在 176~229 之间，区域内不存在任何像素 < 128，固定阈值会把整行判为
# 空白（实测《三辰通载》前10页有 139 行因此被整行丢弃，吞掉 493 字）。
INK_MIN_CONTRAST = 20   # 区域灰度极差低于此值视为无墨迹（实测淡字行极差 ≥23）
INK_RATIO = 0.5         # 阈值取区域「最暗~最亮」之间的比例位置


def _ink_mask(region: np.ndarray) -> np.ndarray:
    """按区域自身灰度分布二值化，返回墨迹掩码（True = 笔画）。

    用 2/98 分位数而非 min/max 定出暗端与亮端，避免单个噪点把阈值带偏。
    深墨字（暗端≈0，亮端≈255）算出的阈值≈127，与原固定阈值等价；淡墨字
    （暗端 210、亮端 255）算出阈值≈232，笔画才能被认出来。
    """
    lo = float(np.percentile(region, 2))
    hi = float(np.percentile(region, 98))
    if hi - lo < INK_MIN_CONTRAST:
        return np.zeros(region.shape, dtype=bool)
    return region < lo + (hi - lo) * INK_RATIO


def ink_contrast(region: np.ndarray) -> float:
    """区域墨色对比度（2/98 分位极差）。淡到接近背景的区域（背面透印）值很小。"""
    if region.size == 0:
        return 0.0
    return float(np.percentile(region, 98)) - float(np.percentile(region, 2))


def segment_block(
    gray: np.ndarray,
    box: dict,
    pad: int = 2,
    min_gap: int = 3,
    density_thresh: float = 0.02,
) -> list[dict]:
    """把一个文本块切成单字 box（像素坐标，含 pad）。

    返回单字 box 列表 [{x,y,w,h}]，按阅读方向排序（竖排：从上到下）。
    """
    x, y, w, h = int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"])
    img_h, img_w = gray.shape[:2]
    x0, x1 = max(0, x), min(img_w, x + w)
    y0, y1 = max(0, y), min(img_h, y + h)
    if x1 <= x0 or y1 <= y0:
        return []

    region = gray[y0:y1, x0:x1]
    dark = _ink_mask(region)  # 墨迹掩码（按区域自身灰度分布定阈）

    if is_vertical(box):
        # 竖排：沿 Y 投影，按字间距切
        col_density = dark.mean(axis=1)  # 每行暗像素占比
        gaps = _find_gaps(col_density, min_gap, density_thresh)
        boxes = []
        for g0, g1 in gaps:
            boxes.append({
            "x": float(x0),
            "y": float(y0 + g0),
            "w": float(x1 - x0),
            "h": float(g1 - g0),
        })
        return _merge_thin_segments(boxes)
    else:
        # 横排：水平投影切
        row_density = dark.mean(axis=0)
        gaps = _find_gaps(row_density, min_gap, density_thresh)
        boxes = []
        for g0, g1 in gaps:
            sub = region[:, g0:g1]
            col_density = sub.mean(axis=0)
            row_nonzero = np.where(col_density > density_thresh)[0]
            if len(row_nonzero) == 0:
                continue
            cy0, cy1 = row_nonzero[0], row_nonzero[-1] + 1
            boxes.append({
                "x": float(x0 + g0),
                "y": float(y0 + cy0),
                "w": float(g1 - g0),
                "h": float(cy1 - cy0),
            })
        return _merge_thin_segments(boxes)


def _merge_thin_segments(boxes: list[dict], min_h_ratio: float = 0.45, min_h_floor: float = 4.0) -> list[dict]:
    """合并「过细」的字框到相邻框。

    竖排/横排中，个别字笔画稀疏（如「一」「丨」）或切分过度会产生异常细的框。
    高度 h 远小于正常字形。取所有高度中位数作为典型字高，把 < 0.45×中位数
    且 < 4px 的段合并到上一段（竖排向上，横排向左），保留 ≥4px 的有效字框。
    4px 阈值覆盖「一」「.」『.」等小符号/笔画，防止细字被吃掉。
    """
    if len(boxes) < 2:
        return boxes
    median_h = _median([b["h"] for b in boxes])
    if median_h <= 0:
        return boxes
    merged = []
    for b in boxes:
        if b["h"] < median_h * min_h_ratio and b["h"] < min_h_floor and merged:
            # 合并到上一段：扩展其 y 范围（竖排同列 w 相同，取并集高度）
            prev = merged[-1]
            prev["h"] = (max(prev["y"] + prev["h"], b["y"] + b["h"])) - prev["y"]
        else:
            merged.append(dict(b))
    return merged


def _median(vals: list[float]) -> float:
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return 0.0
    return s[n // 2]


def _even_split(box: dict, n: int, vertical: bool) -> list[dict]:
    """把一个块沿阅读方向等分成 n 段。

    投影完全找不到边界时的兜底：识别文字是真的（PaddleOCR 给的是整行文本），
    只有框的边界没法从像素上定出来，等分是确定性的最优猜测。
    绝不能因为切不出段就把整行文字丢掉。
    """
    if n <= 0:
        return []
    pos, size = ("y", "h") if vertical else ("x", "w")
    step = float(box[size]) / n
    out = []
    for i in range(n):
        b = {k: float(box[k]) for k in ("x", "y", "w", "h")}
        b[pos] = float(box[pos]) + step * i
        b[size] = step
        out.append(b)
    return out


def _align_to_count(boxes: list[dict], n: int, vertical: bool) -> list[dict]:
    """把切分段数强制对齐到 n（该行识别出的字数）。

    投影段数与识别文字数之间没有任何约束关系：PaddleOCR 给的是**整行文本**，
    段边界是另算的。「一」「二」「三」这类横笔画字、「宫」「主」这类内部有横向
    空隙的字，沿 Y 投影会被切成多段（实测「一二三」切出 6 段）。若按位置把第 si
    段配给第 si 个字，从该字起整列文字全部错位——这正是「字错位」「琅玕重叠」
    「八一合框」三个症状的同一个根因。

    段多于字：反复合并「边界最弱」的相邻两段，即间隙最小处。字内笔画间隙恒小于
      字间间隙，所以先被合并的必然是同一个字的笔画。
    段少于字：反复把跨度最大的段等分为二。投影在那里没能找出边界，几何等分是
      确定性的最优猜测。
    """
    if n <= 0 or not boxes:
        return []
    pos, size = ("y", "h") if vertical else ("x", "w")
    off, off_size = ("x", "w") if vertical else ("y", "h")
    out = [{k: float(b[k]) for k in ("x", "y", "w", "h")} for b in sorted(boxes, key=lambda b: b[pos])]

    while len(out) > n:
        gaps = [out[i + 1][pos] - (out[i][pos] + out[i][size]) for i in range(len(out) - 1)]
        i = int(np.argmin(gaps))
        a, b = out[i], out[i + 1]
        end = max(a[pos] + a[size], b[pos] + b[size])
        a[pos] = min(a[pos], b[pos])
        a[size] = end - a[pos]
        # 另一轴取并集（同列宽度一般相同，但检测框可能略有出入）
        far = max(a[off] + a[off_size], b[off] + b[off_size])
        a[off] = min(a[off], b[off])
        a[off_size] = far - a[off]
        del out[i + 1]

    while len(out) < n:
        i = max(range(len(out)), key=lambda k: out[k][size])
        b = out[i]
        half = b[size] / 2.0
        second = dict(b)
        second[pos] = b[pos] + half
        second[size] = b[size] - half
        b[size] = half
        out.insert(i + 1, second)

    return out


def symbol_gap_repair(
    image,
    chars: list["CharBox"],
    min_gap: int = 40,          # tightened from 25: fewer false gaps
    density_thresh: float = 0.03,  # tightened from 0.02: stricter dark threshold
) -> list["CharBox"]:
    """Stage-2 修复：符号合框漏扫。

    对每列做暗像素投影，找出"有笔画但无字框"的段落，插入占位框（status=STATUS_UNRECOGNIZED）。
    用户在前端可见并可手动补字。
    """
    gray = _load_gray(image)
    img_h, img_w = gray.shape[:2]

    if not chars:
        return chars

    # ① 按 x 分成若干列
    xs = sorted(c.box["x"] for c in chars)
    median_w = float(np.median([c.box["w"] for c in chars])) if chars else 0
    col_tol = max(median_w * 1.5, 40)  #  tightened: 40px 或 1.5倍中位宽

    cols: list[dict] = []
    cur_col = None
    for c in sorted(chars, key=lambda z: z.box["x"]):
        cx = c.box["x"]
        if cur_col is None or abs(cx - cur_col["x"]) > col_tol:
            cur_col = {"x": cx, "chars": []}
            cols.append(cur_col)
        cur_col["chars"].append(c)

    new_boxes: list["CharBox"] = []
    # robustly extract numeric suffix for gap id allocation
    _NUM = __import__("re").compile(r"\d+")
    def _last_num(s: str) -> int:
        m = _NUM.findall(s)
        return int(m[-1]) if m else -1
    next_seq = max((_last_num(c.id) for c in chars), default=-1) + 1
    inserted = 0

    for col in cols:
        col_chars = sorted(col["chars"], key=lambda z: z.box["y"])
        if not col_chars:
            continue

        col_x0 = min(c.box["x"] for c in col_chars) - 15
        col_x1 = max(c.box["x"] + c.box["w"] for c in col_chars) + 15
        col_y0 = max(0, int(min(c.box["y"] for c in col_chars)) - 30)
        col_y1 = min(img_h, int(max(c.box["y"] + c.box["h"] for c in col_chars)) + 30)

        sub = gray[col_y0:col_y1, max(0, int(col_x0)): min(img_w, int(col_x1))]
        if sub.size == 0:
            continue
        dark = _ink_mask(sub)  # 同 segment_block：按区域自身灰度分布定阈，淡字也能认出
        density = dark.mean(axis=1)
        blank = density <= density_thresh

        # 内容段（含空隙）注意将空白段 >= min_gap 像素视为真实间隙
        segments = []
        i = 0
        n = len(density)
        while i < n:
            if not blank[i]:
                j = i
                while j < n and not blank[j]:
                    j += 1
                if j - i >= min_gap:
                    segments.append((col_y0 + i, col_y0 + j))
                i = j
            else:
                i += 1

        # 已有字框覆盖区间（排除）
        covered = [(c.box["y"], c.box["y"] + c.box["h"]) for c in col_chars]

        def covered_by(y0: float, y1: float) -> bool:
            return any(not (y1 <= cy0 or y0 >= cy1) for cy0, cy1 in covered)

        for seg_y0, seg_y1 in segments:
            if covered_by(seg_y0, seg_y1):
                continue
            new_id = f"gap_{next_seq + inserted:06d}"
            inserted += 1
            new_boxes.append(CharBox(
                id=new_id,
                box={"x": float(col_x0), "y": float(seg_y0), "w": float(col_x1 - col_x0), "h": float(seg_y1 - seg_y0)},
                char="",
                orig_char="",
                conf=0.0,
                parent=None,
                status=STATUS_UNRECOGNIZED,
                is_rare=False,
                rare_reason=None,
                angle=0.0,
                extra={"band": col_chars[0].extra.get("band", 0) if col_chars else 0, "repair": "symbol_gap_repair"},
            ))

    # 合并（按 y 排序，保证竖排顺序）并把 gap 插入到合适位置
    all_chars = sorted(chars + new_boxes, key=lambda z: (z.box["y"], z.box["x"]))
    return all_chars


def _find_gaps(density: np.ndarray, min_gap: int, thresh: float) -> list[tuple[int, int]]:
    """沿一维投影密度找「内容段」。返回 [(start,end),...]（内容索引，而非空白）。"""
    below = density <= thresh  # 空白位置
    content = ~below
    segments = []
    i = 0
    n = len(density)
    while i < n:
        if content[i]:
            j = i
            while j < n and content[j]:
                j += 1
            segments.append((i, j))
            i = j
        else:
            i += 1
    # 过滤过窄片段（投影噪声），但保留单个字的窄笔画（如「一」）
    # 这里 min_gap 用于底部：若一段内容宽度 < min_gap×0.5 且被夹在空白中，可能是噪声，但保留
    return segments


def segment_page_chars(
    image,
    page: PageResult,
    min_gap: int = 2,
    density_thresh: float = 0.02,
) -> int:
    """对 page 中所有 level=line 块做单字切分，生成 CharBox 列表。

    把每个 line 块的整行识别文本逐字落到单字框上：先沿阅读方向投影切段，
    再把**段数强制对齐到该行字数**，最后按顺序一段配一字。
    更新 page.chars 为真正的单字框，page.lines 保留行级。

    两条不变量（`tests/test_segment_alignment.py` 为其疫苗）：
    1. 不丢字：每行的每一个识别字都必须落到一个框上。投影切不出段时兜底等分，
       绝不 `continue` 跳过整行。
    2. 不错位：框数恒等于字数，第 i 个框就是第 i 个字所在的位置。

    返回单字数。
    """
    gray = _load_gray(image)

    new_chars: list[CharBox] = []
    seq = 0
    for line in page.lines:
        text_chars = _clean_text(line.text or "")
        if not text_chars:
            continue
        vertical = is_vertical(line.box)
        seg_boxes = segment_block(gray, line.box, min_gap=min_gap, density_thresh=density_thresh)
        # 切不出段（背面透印字等淡到投影无信号）时兜底等分，绝不丢弃整行文字
        seg_source = "projection"
        if not seg_boxes:
            seg_boxes = _even_split(line.box, len(text_chars), vertical)
            seg_source = "even_split"
        # 段数强制对齐到字数：位置配字前必须先保证两者等长，否则整列错位
        seg_boxes = _align_to_count(seg_boxes, len(text_chars), vertical)

        # 记录该行墨色对比度：淡到接近背景的行多为背面透印的幽灵字，
        # 保留下来供人工判定，但要可筛出来，不能与正文混为一谈
        x0 = max(0, int(line.box["x"]))
        y0 = max(0, int(line.box["y"]))
        region = gray[y0:int(line.box["y"] + line.box["h"]), x0:int(line.box["x"] + line.box["w"])]
        contrast = ink_contrast(region)

        for sb, char in zip(seg_boxes, text_chars):
            extra = {"band": line.extra.get("band", 0), "seg": seg_source}
            if contrast < 128:
                extra["faint"] = round(contrast, 1)
            new_chars.append(CharBox(
                id=f"{page.page}c{seq:04d}",
                box=sb,
                char=char,
                orig_char=char,   # 原始识别文本（永不覆盖）
                conf=line.conf,
                parent=line.id,
                status="pending",
                angle=0.0,
                extra=extra,
            ))
            seq += 1

    page.chars = new_chars
    # 后置：过滤极小噪声框（宽<8 且 高<8 且 无字内容 → PaddleOCR检测的连接笔画假框）
    filtered = []
    for c in page.chars:
        if c.box["w"] < 8 and c.box["h"] < 8 and not c.char:
            continue  # 丢弃：太小且无字内容，是连接笔画噪声
        filtered.append(c)
    page.chars = filtered
    return len(page.chars)


def _clean_text(text: str) -> list[str]:
    """从行文本提取汉字+常用标点，去掉首尾空白。"""
    return list(text.strip()) if text else []