"""星盘图曲线字切分原型实验（spike，不改生产代码）。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# 离线图
import cv2
import numpy as np
from PIL import Image, ImageOps

# OCR：按项目约定的 PaddleOCR 调用方式推断；若环境不同则在报告里说明。
try:
    from paddleocr import PaddleOCR
except Exception as exc:  # pragma: no cover - 环境缺失时运行报告形态
    PaddleOCR = None
    _paddle_import_error = exc
else:
    _paddle_import_error = None


def make_page_result(image_path: Path):
    """将一张图经 det 后转成与项目对齐的 OCR 结果。"""
    if PaddleOCR is None:
        raise RuntimeError(f"PaddleOCR 不可用（{_paddle_import_error}）。")
    ocr = PaddleOCR(lang="ch")
    res = ocr.ocr(str(image_path), det=True, rec=True)
    return res


def summarize_result(image_path: Path) -> dict:
    data = make_page_result(image_path)
    texts: list[str] = []
    try:
        for page in data or []:
            for item in page or []:
                text = (item[1][0] if len(item) > 1 else "") if item else ""
                if text:
                    texts.append(text)
    except Exception:
        pass
    return data, texts


def detect_center(image: np.ndarray) -> Optional[tuple[float, float]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 2)
    circles = cv2.HoughCircles(
        blur, cv2.HOUGH_GRADIENT, dp=1.2, minDist=60,
        param1=100, param2=30, minRadius=30, maxRadius=int(min(image.shape[:2]) / 2),
    )
    if circles is None:
        return None
    circles = np.uint16(np.around(circles))
    best = max(circles[0, :], key=lambda c: c[2])
    return float(best[0]), float(best[1])


def fit_circle(points: np.ndarray) -> Optional[tuple[float, float, float]]:
    # 最小二乘圆拟合 (Algebraic fit)
    x = points[:, 0]
    y = points[:, 1]
    xm, ym = np.mean(x), np.mean(y)
    u, v = x - xm, y - ym
    Suu = float(np.sum(u * u))
    Suv = float(np.sum(u * v))
    Svv = float(np.sum(v * v))
    Suuu = float(np.sum(u * u * u))
    Suvv = float(np.sum(u * v * v))
    Svvv = float(np.sum(v * v * v))
    Svvv = float(np.sum(v * v * v))
    Suvv = float(np.sum(u * v * v))
    Svvv = float(np.sum(v * v * v))
    Svvv = float(np.sum(v * v * v))
    Suvv = float(np.sum(u * v * v))
    Suvv = float(np.sum(u * v * v))
    Svvv = float(np.sum(v * v * v))
    A = np.array([[Suu, Suv], [Suv, Svv]])
    B = np.array([0.5 * (Suuu + Suvv), 0.5 * (Svvv + Suvv)])
    if np.linalg.det(A) == 0:
        return None
    uc, vc = np.linalg.solve(A, B)
    cx, cy = xm + uc, ym + vc
    r = float(np.mean(np.sqrt((x - cx) ** 2 + (y - cy) ** 2)))
    if r <= 0 or not np.isfinite([cx, cy, r]).all():
        return None
    return cx, cy, r


def angle_of(cx: float, cy: float, x: float, y: float) -> float:
    return float(np.degrees(np.arctan2(y - cy, x - cx)))


def main() -> int:
    parser = argparse.ArgumentParser(description="星盘曲线字切分实验（spike）")
    parser.add_argument("image", help="星盘图路径")
    parser.add_argument("--out", default="ocr/experiments/star_chart_out.png", help="结果标注图")
    args = parser.parse_args()
    img_path = Path(args.image)
    if not img_path.exists():
        raise SystemExit(f"图片不存在: {img_path}")
    try:
        raw, texts = summarize_result(img_path)
    except Exception as exc:
        raise SystemExit(f"PaddleOCR 运行失败: {exc}") from exc
    print(f"识别文本数: {len(texts)}")
    for i, t in enumerate(texts[:20], 1):
        print(f"{i:02d}. {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())