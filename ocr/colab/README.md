# ocr/colab — 古籍 OCR 识别脚本（Colab/本地通用）

本节脚本实现「Colab 端识别」，对应 PLANS.md §4.2/§4.3 的层级框与区块切分。全部为 Python 脚本（.py），Colab 中可直接以单元格 `!python` 运行，或在本机 venv 跑。

## 依赖与运行环境

```bash
uv venv /tmp/ocr_venv --python 3.11 && source /tmp/ocr_venv/bin/activate
uv pip install opencv-python-headless paddlepaddle paddleocr
```

首次运行自动下载 PP-OCRv6 权重到 `~/.paddlex/official_models/`。
PaddleOCR 3.x API：`PaddleOCR(lang="ch", use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)`，返回 `OCRResult` dict（rec_texts / rec_polys / rec_scores）。

## 脚本清单

| 脚本 | 说明 | 区块切分方法 |
|---|---|---|
| `paddle_ocr_bands.py` | **主脚本（定稿 §4.3）**：PaddleOCR 识别 → OCR框 y 间隙切区块 → 竖排排序，可调 gap_thresh/col_gap_thresh | OCR 框 y 间隙（可靠，推荐） |
| `paddle_ocr_image_bands.py` | 旧法参考：图像行密度找空白带切区块。顶部/底部留白会误判、星盘图易漏检，仅保留作对比 | 图像空白带（不推荐） |
| `ocr_box_mark.py` | 识别 + 画框标记：在底图上叠加蓝框 + 中文标签（PIL + STHeiti 字体），输出标记 PNG | - |

## 用法

```bash
# 主脚本：识别 + 区块切分 + 竖排排序
python paddle_ocr_bands.py <image.png> [gap_thresh=40] [col_gap_thresh=30]
# 例：识别目录图(两页拼一图需切区块)，gap 阈值 40px
python paddle_ocr_bands.py 目录.png 40 30

# 画框标记（含坐标输出，供本地工作台复原）
python ocr_box_mark.py <image.png> <输出标记.png>
```

## 测试图片

- `~/Downloads/目录.PNG` — 三辰通载目录页（上下两区块：卷第二/卷第三）
- `~/Downloads/图.PNG` — 星盘图（图形密集，图画式排列；曲线字 PaddleOCR 识别为乱码，需本地人工）
- `~/Downloads/Snipaste_2026-08-04_18-11-25.png` — 琴堂五星正文（上中下三区块）

## 关键结论（实测 2026-08-04）

1. **竖排正文 PaddleOCR 识别质量高**（置信度 0.9+），Apple Vision 基本失败
2. **原图直读最好**，豆包式二值化预处理反损伤字形
3. **区块切分用 OCR 框 y 间隙**（非图像空白带），见 PLANS.md §4.3
4. 画框中文标签必须用 PIL + 系统中文字体（cv2.putText 输出 ????）