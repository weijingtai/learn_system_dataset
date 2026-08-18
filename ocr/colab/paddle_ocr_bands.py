#!/usr/bin/env python3
"""古籍 OCR：PaddleOCR 3.x 识别 + OCR框y间隙切区块 + 竖排排序（已验证 2026-08-04）
用法: python paddle_ocr_bands.py <image> [gap_thresh] [col_gap_thresh]
环境: uv venv /tmp/ocr_venv --python 3.11 && uv pip install opencv-python-headless paddlepaddle paddleocr
"""
import sys
import warnings
warnings.filterwarnings('ignore')
import numpy as np
from paddleocr import PaddleOCR


def split_bands_by_ocr_boxes(res, gap_thresh=40):
    """用 OCR 框 y 间隙切区块（比图像空白带可靠：顶部留白不误判、不受栏线印章噪点影响）
    返回: (items 按y排序, band_ids 每框所属区块)
    """
    items = []
    for txt, poly in zip(res['rec_texts'], res['rec_polys']):
        y0 = float(poly[:, 1].min()); y1 = float(poly[:, 1].max())
        cy = float(np.mean(poly[:, 1])); cx = float(np.mean(poly[:, 0]))
        items.append((y0, y1, cy, cx, txt))
    items.sort(key=lambda t: t[0])
    cut_positions = [i for i in range(1, len(items))
                     if items[i][0] - items[i-1][1] >= gap_thresh]
    band_ids, band = [], 0
    for i in range(len(items)):
        if i in cut_positions:
            band += 1
        band_ids.append(band)
    return items, band_ids


def sort_vertical_by_bands(items, band_ids, col_gap_thresh=30):
    """区块(上→下) → 区块内按x聚列 → 列右→左 → 列内y上→下（古籍阅读序）"""
    n_bands = max(band_ids) + 1
    out = []
    for bi in range(n_bands):
        band_items = [it for it, b in zip(items, band_ids) if b == bi]
        if not band_items:
            continue
        band_items.sort(key=lambda t: t[3])  # 按 cx
        cols = []
        cur = [band_items[0]]
        for it in band_items[1:]:
            if abs(it[3] - cur[-1][3]) > col_gap_thresh:
                cols.append(cur); cur = [it]
            else:
                cur.append(it)
        cols.append(cur)
        cols.sort(key=lambda cl: -np.mean([t[3] for t in cl]))  # 列右→左
        out.append(f'--- 区块{bi+1} ---')
        for col in cols:
            col_sorted = sorted(col, key=lambda t: t[2])  # 列内 y 上→下
            out.append("".join(t[4] for t in col_sorted))
    return "\n".join(out)


def main():
    img_path = sys.argv[1]
    gap_thresh = float(sys.argv[2]) if len(sys.argv) > 2 else 40
    ocr = PaddleOCR(lang="ch", use_doc_orientation_classify=False,
                    use_doc_unwarping=False, use_textline_orientation=False)
    raw = list(ocr.ocr(img_path))
    res = raw[0]
    items, band_ids = split_bands_by_ocr_boxes(res, gap_thresh)
    print("====识别输出====")
    print(sort_vertical_by_bands(items, band_ids))


if __name__ == "__main__":
    main()
