"""gujiorc.ocr.engine — PaddleOCR 引擎封装 + 区块切分 + 竖排排序。

移植自已验证的 paddle_ocr_bands.py（PLANS.md §4.3 定稿：OCR 框 y 间隙切区块）。

引擎懒加载（首次调用才 import paddleocr，避免无 GPU/未安装时导入失败）。
识别结果转为通用 dict（不影响后续生僻字/索引模块对 PaddleOCR 版本的依赖）。
"""
from __future__ import annotations

import numpy as np


class PaddleOcrEngine:
    """PaddleOCR 3.x 封装。

    init_paddleocr() 懒初始化，返回 PaddleOCR 实例（可复用，避免重复下载模型）。
    recognize() 返回原始 OCRResult。
    """

    _ocr = None

    @classmethod
    def get(cls):
        if cls._ocr is None:
            from paddleocr import PaddleOCR
            cls._ocr = PaddleOCR(
                lang="ch",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        return cls._ocr

    def recognize(self, image) -> list:
        ocr = self.get()
        # image: numpy array (BGR) 或文件路径
        return list(ocr.ocr(image))


def split_bands_by_ocr_boxes(res, gap_thresh=40):
    """OCR 框 y 间隙切区块（PLANS.md §4.3 定稿）。

    res: PaddleOCR OCRResult（含 rec_polys/rec_texts/rec_scores）
    返回 (items, band_ids, cut_positions)。
    items: [(y0,y1,cy,cx,txt)] 按 y 排序
    """
    texts = res["rec_texts"]
    polys = res["rec_polys"]
    items = []
    for txt, poly in zip(texts, polys):
        y0 = float(np.min(poly[:, 1]))
        y1 = float(np.max(poly[:, 1]))
        cy = float(np.mean(poly[:, 1]))
        cx = float(np.mean(poly[:, 0]))
        items.append((y0, y1, cy, cx, txt))
    items.sort(key=lambda t: t[0])

    cut_positions = []
    for i in range(1, len(items)):
        gap = items[i][0] - items[i - 1][1]
        if gap >= gap_thresh:
            cut_positions.append(i)

    band_ids = []
    band = 0
    for i in range(len(items)):
        if i in cut_positions:
            band += 1
        band_ids.append(band)
    return items, band_ids, cut_positions


def sort_vertical_by_bands(items, band_ids, col_gap_thresh=30):
    """区块内竖排排序：先按 x 聚列 → 列右→左 → 列内 y 上→下。"""
    n_bands = max(band_ids) + 1 if band_ids else 1
    out = []
    for bi in range(n_bands):
        band_items = [it for it, b in zip(items, band_ids) if b == bi]
        if not band_items:
            continue
        band_items.sort(key=lambda t: t[3])
        cols = []
        cur = [band_items[0]]
        for it in band_items[1:]:
            if abs(it[3] - cur[-1][3]) > col_gap_thresh:
                cols.append(cur)
                cur = [it]
            else:
                cur.append(it)
        cols.append(cur)
        cols.sort(key=lambda cl: -np.mean([t[3] for t in cl]))
        out.append(f"--- 区块{bi + 1} ---")
        for col in cols:
            col_sorted = sorted(col, key=lambda t: t[2])
            out.append("".join(t[4] for t in col_sorted))
    return "\n".join(out)


def ocr_to_text(image, gap_thresh=40, col_gap_thresh=30) -> str:
    """一个函数完成：识别 → 区块切分 → 竖排排序 → 文本。"""
    engine = PaddleOcrEngine()
    raw = engine.recognize(image)
    if not raw or not raw[0]:
        return ""
    res = raw[0]
    items, band_ids, _ = split_bands_by_ocr_boxes(res, gap_thresh)
    return sort_vertical_by_bands(items, band_ids, col_gap_thresh)


def recognize_crop_text(image) -> dict:
    """局部裁剪区域的识别（工作台补标/重识别用）。

    与整页不同：裁剪块通常只有一两个竖排字列，不需要区块切分，
    直接 det+rec 后按古籍阅读序拼接——列间从右到左、列内从上到下；
    列归属按检测框中心 x 聚类（间距超过平均字高即视为换列）。
    返回 {"text", "lines": [{text, score}], "score"}。
    """
    engine = PaddleOcrEngine()
    raw = engine.recognize(image)
    if not raw or not raw[0]:
        return {"text": "", "lines": [], "score": 0.0}
    res = raw[0]
    entries = []
    for txt, poly, sc in zip(res["rec_texts"], res["rec_polys"], res["rec_scores"]):
        xs = [float(p[0]) for p in poly]
        ys = [float(p[1]) for p in poly]
        entries.append({
            "text": txt, "score": float(sc),
            "cx": float(np.mean(xs)), "cy": float(np.mean(ys)),
            "h": max(ys) - min(ys),
        })
    if not entries:
        return {"text": "", "lines": [], "score": 0.0}

    avg_h = float(np.mean([e["h"] for e in entries])) or 1.0
    entries.sort(key=lambda e: -e["cx"])          # 右边的列先读
    cols: list[list[dict]] = [[entries[0]]]
    for e in entries[1:]:
        if abs(e["cx"] - cols[-1][-1]["cx"]) > avg_h:
            cols.append([e])
        else:
            cols[-1].append(e)

    ordered = []
    for col in cols:
        ordered.extend(sorted(col, key=lambda e: e["cy"]))
    return {
        "text": "".join(e["text"] for e in ordered),
        "lines": [{"text": e["text"], "score": round(e["score"], 4)} for e in ordered],
        "score": round(float(np.mean([e["score"] for e in ordered])), 4),
    }