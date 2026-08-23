"""gujiorc.ocr.preprocess — 识别前的图像预处理。

目前只做一件事：抹除**背面透印字**（bleed-through / show-through）。

古籍影印本纸张极薄，扫描时背面的字会透到正面。这些幽灵字在 OCR 眼里和真字
一样，检测器会给它们框、识别器会给它们文字，于是：

1. 正文里混进整页背面的内容（《三辰通载》前10页实测 531 个幽灵字框）
2. 生僻字判定被幽灵字污染（page_003 实测 148 个"生僻字"里 146 个是幽灵）
3. **真字的识别也被拖累**——幽灵笔画和真笔画重叠在同一个检测框里，识别器把
   两者一起读，实测出现 `卷第七` 被读成 `卷第七吧`、整行读成 `11`/`37` 这类垃圾

关键观察：透印字的墨色和真墨**不重叠**。《三辰通载》前10页实测，真墨的墨迹
像素灰度在 32~88（区域最暗像素中位数 9），透印的墨迹像素在 116~240（区域最暗
像素中位数 210）。中间 88~116 是一段干净的空隙。所以只要把亮于该空隙的像素
推成纯白，就能整块抹掉透印而完全不碰真墨。
"""
from __future__ import annotations

import numpy as np

# 默认阈值取真墨(≤88)与透印(≥116)之间的空隙。0 表示不做抹除。
DEFAULT_BLEED_THRESH = 110
# 「幽灵墨带」上界：亮于此值的像素本就是纸张，抹掉它们不算抹墨，不计入报告。
PAPER_LEVEL = 235
# 「近黑」下界：扫描件四周的黑底和装订线阴影在 0~25，不是墨，统计真墨时排除。
BORDER_LEVEL = 25
# 抹除后残留真墨低于此比例即告警：正常页实测留 5.0%~12.3%，
# 模拟淡印本（真墨整体抬到 150）只留 0.00%，余量极大。
MIN_KEPT_INK = 0.01


def suppress_bleed_through(image, thresh: int = DEFAULT_BLEED_THRESH):
    """把亮于 thresh 的像素推成纯白，抹除背面透印字。

    返回 (处理后的数组, 统计字典)。统计字典：

    - ``erased``：被抹掉的幽灵墨占全图比例（thresh~PAPER_LEVEL 之间的像素）。
      纸张本来就是白的，把它变白不算抹墨，不计入。注意这个数不能当告警信号——
      真笔画的抗锯齿边缘也落在这一带，实测正常页就有 3%~14%。
    - ``kept_ink``：抹除后残留的真墨比例（BORDER_LEVEL~thresh 之间的像素，
      排除近黑的扫描边框）。**这个才是告警信号**：低于 ``MIN_KEPT_INK`` 说明
      这本书的真墨本身就淡（淡印本/褪色本），默认阈值会连正文一起抹掉，
      必须调低 thresh 或用 thresh=0 关闭。

    thresh <= 0 时原样返回，不做任何修改。
    """
    arr = np.asarray(image)
    if thresh <= 0:
        return arr, {"erased": 0.0, "kept_ink": 0.0}
    gray = arr if arr.ndim == 2 else np.dot(arr[..., :3], [0.299, 0.587, 0.114])
    erased = (gray > thresh) & (gray <= PAPER_LEVEL)
    kept_ink = (gray >= BORDER_LEVEL) & (gray <= thresh)
    out = arr.copy()
    out[gray > thresh] = 255
    return out, {"erased": float(erased.mean()), "kept_ink": float(kept_ink.mean())}
