#!/usr/bin/env python3
"""PaddleOCR 识别结果画框标记：蓝框 + 框上方中文标签，输出原分辨率 PNG。

用法:
    /tmp/ocr_venv/bin/python ocr_box_mark.py <img> <out.png>

依赖: /tmp/ocr_venv (opencv-python-headless + paddlepaddle + paddleocr) + PIL
关键: cv2.putText 的 Hershey 字体不支持中文 → 必须用 PIL + 系统中文字体画标签。
macOS 中文字体: /System/Library/Fonts/STHeiti Medium.ttc
"""
import sys, warnings
warnings.filterwarnings('ignore')
import cv2
import numpy as np
from paddleocr import PaddleOCR
from PIL import Image, ImageDraw, ImageFont

img_path = sys.argv[1]
out_path = sys.argv[2]

ocr = PaddleOCR(lang="ch", use_doc_orientation_classify=False,
                use_doc_unwarping=False, use_textline_orientation=False)
raw = list(ocr.ocr(img_path))
res = raw[0]

# 用 PIL 读图(保留原始方向), 用系统中文字体
pil_img = Image.open(img_path).convert('RGB')
draw = ImageDraw.Draw(pil_img)
font = ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', 22)

texts = res['rec_texts']
polys = res['rec_polys']
scores = res['rec_scores']

for txt, poly, score in zip(texts, polys, scores):
    pts = np.array(poly, dtype=np.int32).reshape(-1, 2)
    x0 = int(pts[:, 0].min()); y0 = int(pts[:, 1].min())
    x1 = int(pts[:, 0].max()); y1 = int(pts[:, 1].max())
    # 蓝色边框
    draw.rectangle([x0, y0, x1, y1], outline=(0, 120, 255), width=3)
    # 中文标签 (框上方, 蓝底白字)
    bbox = draw.textbbox((x0, y0 - 26), txt, font=font)
    tw = bbox[2] - bbox[0]
    label_y0 = max(0, y0 - 28)
    draw.rectangle([x0, label_y0, x0 + tw + 6, label_y0 + 26], fill=(0, 120, 255))
    draw.text((x0 + 3, label_y0), txt, fill=(255, 255, 255), font=font)

pil_img.save(out_path)
print(f'saved {out_path}', file=sys.stderr)

# 文本输出
print('====识别结果(坐标)====')
for txt, poly, score in zip(texts, polys, scores):
    x0 = poly[:, 0].min(); x1 = poly[:, 0].max()
    y0 = poly[:, 1].min(); y1 = poly[:, 1].max()
    print(f'x[{x0:5.0f}-{x1:5.0f}] y[{y0:5.0f}-{y1:5.0f}] conf={score:.2f} | {txt}')
