# 合成星盘式圆形文本图用于离线实验
# 用法：python synth_star_chart.py [--out ocr/experiments/star_chart.png] [--chars 8字圆周] [--size 512]
import argparse
from pathlib import Path
import math

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"[合成星盘图失败] pil 不可用: {exc}") from exc


def synth_star_chart(out: str, chars: str = "星盤圖曲字切分實驗", size: int = 512) -> Path:
    out_path = Path(out)
    img = Image.new("RGB", (size, size), (255, 248, 214))
    draw = ImageDraw.Draw(img)

    # 中心十字+同心圆（星盘底色）
    cx = size // 2
    cy = size // 2
    for r in (size // 16, size // 8, size // 5, size // 3):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(120, 120, 120), width=1)
    draw.line([(cx, cy - size // 3), (cx, cy + size // 3)], fill=(180, 180, 180), width=1)
    draw.line([(cx - size // 3, cy), (cx + size // 3, cy)], fill=(180, 180, 180), width=1)

    font_paths = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
    ]
    font_path = next((p for p in font_paths if Path(p).exists()), None)
    font = ImageFont.truetype(font_path, size=28) if font_path else ImageFont.load_default()

    n = len(chars)
    radius = size // 4
    for i, ch in enumerate(chars):
        angle = 2 * math.pi * i / n - math.pi / 2  # 顶部起
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        put_char_rotated(draw, ch, x, y, angle + math.pi / 2, font)

    img.save(out_path)
    print(f"[合成星盘图] 输出: {out_path}")
    return out_path


def put_char_rotated(draw: ImageDraw.ImageDraw, ch: str, x: float, y: float, theta: float, font):
    """临时生成单字图后按朝向贴回（这里先用中心绘制避免重采样量太大）。"""
    # 简化：直接画字，方向通过后续检测方框重现，这里只做占位合成图
    draw.text((x - 8, y - 8), ch, fill=(30, 30, 30), font=font)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="star_chart.png")
    parser.add_argument("--chars", default="星盤圖曲字切分實驗")
    parser.add_argument("--size", type=int, default=512)
    args = parser.parse_args()
    synth_star_chart(args.out, args.chars, args.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())