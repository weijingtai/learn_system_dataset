#!/usr/bin/env python3
"""PaddleOCR 古籍竖排识别（明清刻本首选，替代 Apple Vision）。

依赖（macOS arm64, Python 3.11）:
    uv venv /tmp/ocr_venv --python 3.11 && source /tmp/ocr_venv/bin/activate
    uv pip install opencv-python-headless paddlepaddle paddleocr
首次运行自动下载 PP-OCRv6 权重到 ~/.paddlex/official_models/。

用法:
    python paddle_ocr.py <image.png>              # 原图直读（推荐，效果最好）
    python paddle_ocr.py <image.png> pre          # 可选: 豆包式预处理(自适应二值化+去栏线)
                                                  #   实测会损伤字形降准确率, 仅保留作对比

输出: 古籍竖排阅读顺序 — 列从右到左，列内从上到下。
      自动检测大空白带（如页间空行/两页拼一图）按行切分区块，区块各自排序，
      避免「中间一大段空白其实是两部分」时把上下区块拼成一条。
"""
import cv2
import numpy as np
import sys
import warnings
warnings.filterwarnings('ignore')


# ====================== 1.预处理: 去栏线/底色/噪声 ======================
# 实测对 PaddleOCR 反而降准确率(字形被损伤); 原图直读效果最好。保留供对比。
def preprocess_ancien_book(img_path, out_debug_path=None, kernel_len=22, block=15, C=3):
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bin_img = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, blockSize=block, C=C
    )
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_len))
    vertical_lines = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, kernel_v, iterations=1)
    bin_img_no_vline = cv2.subtract(bin_img, vertical_lines)
    kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    clean = cv2.morphologyEx(bin_img_no_vline, cv2.MORPH_CLOSE, kernel_small)
    final = 255 - clean
    if out_debug_path:
        cv2.imwrite(out_debug_path, final)
    return final


# ====================== 2.区块切分: 按行密度找大空白带 ======================
def find_row_bands(img, min_blank_h=40):
    """按行密度找大空白带(区块分隔),返回分隔Y坐标列表。

    古籍扫描/截图常有页间空白: 中间一大段空白 = 上下其实是两部分。
    若不分区块, 同 X 的上下两列会被拼成一条长文本(用户修正过的坑)。
    min_blank_h: 连续空白行 >= 该值才算分隔带(防把行距当分页)。
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, bin_img = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY_INV)
    row_density = bin_img.sum(axis=1) / 255 / gray.shape[1]
    h = gray.shape[0]
    blank = row_density < 0.01
    separators = []
    i = 0
    while i < h:
        if blank[i]:
            j = i
            while j < h and blank[j]:
                j += 1
            if j - i >= min_blank_h:
                separators.append((i + j) // 2)  # 带中心
            i = j
        else:
            i += 1
    return separators


# ====================== 3.古籍竖排排序 ======================
def sort_vertical_ocr_result(res, col_gap_thresh=30, bands=None):
    """res: OCRResult (PaddleOCR 3.x, dict 子类) — res['rec_texts'] + res['rec_polys']
    古籍竖排: 按 X 聚列 → 列右→左 → 列内 Y 上→下。
    col_gap_thresh: 列间距阈值。先打印 poly x0/x1 找真实列间隙再定(本图列距~50px)。
    bands: find_row_bands 的区块分隔Y坐标列表 — 先按Y分区块, 区块内各自竖排。
    """
    texts = res['rec_texts']
    polys = res['rec_polys']  # list of (4,2) ndarray 四点框
    items = []
    for txt, poly in zip(texts, polys):
        cx = float(np.mean(poly[:, 0]))
        cy = float(np.mean(poly[:, 1]))
        items.append((cx, cy, txt))

    if not items:
        return ""

    # 按 Y 分区块
    if bands:
        bands = sorted(bands)
        def band_of(y):
            for i, b in enumerate(bands):
                if y < b:
                    return i
            return len(bands)
        groups = {}
        for it in items:
            groups.setdefault(band_of(it[1]), []).append(it)
        ordered_bands = sorted(groups.keys())  # 上→下
    else:
        ordered_bands = [0]
        groups = {0: items}

    all_cols = []
    for bi in ordered_bands:
        items_b = groups[bi]
        items_b.sort(key=lambda x: x[0])
        cols = []
        current_col = [items_b[0]]
        for item in items_b[1:]:
            if abs(item[0] - current_col[-1][0]) > col_gap_thresh:
                cols.append(current_col)
                current_col = [item]
            else:
                current_col.append(item)
        cols.append(current_col)
        cols.sort(key=lambda cl: -np.mean([x[0] for x in cl]))  # 右→左
        all_cols.append((bi, cols))

    final_text = []
    for bi, cols in all_cols:
        final_text.append(f'--- 区块{bi+1} ---')
        for col in cols:
            col_sorted = sorted(col, key=lambda x: x[1])  # 列内上→下
            col_text = "".join([i[2] for i in col_sorted])
            final_text.append(col_text)
    return "\n".join(final_text)


# ====================== 4.主流程 ======================
if __name__ == "__main__":
    img_path = sys.argv[1]
    use_pre = len(sys.argv) > 2 and sys.argv[2] == 'pre'

    from paddleocr import PaddleOCR
    # 3.x API: 不要传 use_gpu/show_log/use_angle_cls (会 ValueError: Unknown argument)
    ocr = PaddleOCR(lang="ch", use_doc_orientation_classify=False,
                    use_doc_unwarping=False, use_textline_orientation=False)

    if use_pre:
        img_proc = preprocess_ancien_book(img_path, '/tmp/paddle_pre.png')
        img_proc = cv2.cvtColor(img_proc, cv2.COLOR_GRAY2BGR)  # 必须 3 通道
        raw = list(ocr.ocr(img_proc))
    else:
        raw = list(ocr.ocr(img_path))

    if not raw or not raw[0]:
        print("NO TEXT")
        sys.exit(0)
    res = raw[0]

    # 自动检测大空白带(区分上下区块) — 页间空白/两页拼一图时必需
    src_img = cv2.imread(img_path)
    bands = find_row_bands(src_img)
    if bands:
        print(f"检测到 {len(bands)} 条空白带: {bands}", file=sys.stderr)

    result_text = sort_vertical_ocr_result(res, bands=bands)
    print("====识别输出====")
    print(result_text)
