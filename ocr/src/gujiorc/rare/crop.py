"""gujiorc.rare.crop — 生僻字截图（M10_）。

按 box 坐标从底图裁剪字形样本图，存到 glyph_samples/。
同一字多页可存多张样本。
"""
from __future__ import annotations

from pathlib import Path

from ..core.paths import get_root, ensure_struct
from ..core.models import PageResult


def crop_char_sample(
    image,  # PIL 或 numpy 或路径
    page: PageResult,
    char_id: str,
    char: str,
    out_dir: str | None = None,
    pad: int = 3,                 # 外扩像素，留边
    min_side: int = 40,           # 最小边长（文字太小则缩放）
) -> Path | None:
    """裁剪一个字框为 PNG 样本图。返回路径。

    image: 底图（PIL Image 或 numpy RGB/BGR 或路径）。需与 PageResult 同页。
    """
    from PIL import Image
    import numpy as np

    # 定位字框
    ch = next((c for c in page.chars if c.id == char_id), None)
    if ch is None:
        return None
    box = ch.box
    x, y, w, h = box["x"], box["y"], box["w"], box["h"]

    # 加载图像为 RGB
    if isinstance(image, str):
        img = Image.open(image).convert("RGB")
    elif hasattr(image, "shape"):
        img = Image.fromarray(image)
    else:
        img = image.convert("RGB")

    # 裁剪（含外扩，越界截断）
    img_w, img_h = img.size
    x0 = max(0, int(x) - pad); y0 = max(0, int(y) - pad)
    x1 = min(img_w, int(x + w) + pad); y1 = min(img_h, int(y + h) + pad)
    if x1 <= x0 or y1 <= y0:
        return None
    crop = img.crop((x0, y0, x1, y1))

    # 若小于 min_side 则放大（小字截图才有意义）
    if crop.size[0] < min_side or crop.size[1] < min_side:
        factor = max(min_side / crop.size[0], min_side / crop.size[1])
        crop = crop.resize((int(crop.size[0] * factor), int(crop.size[1] * factor)), Image.LANCZOS)

    # 存储
    struct = ensure_struct()
    base = Path(out_dir) if out_dir else struct["glyph_samples"]
    base.mkdir(parents=True, exist_ok=True)
    # 找同字已有序号
    seq = _next_seq(base, char)
    fname = f"{char}_{page.page}_{seq}.png"
    path = base / fname
    crop.save(path)
    return path


def _next_seq(base: Path, char: str) -> int:
    """同字已有的最大序号 +1。"""
    if not base.exists():
        return 1
    max_seq = 0
    for p in base.glob(f"{char}_*.png"):
        try:
            seq = int(p.stem.split("_")[-1])
            max_seq = max(max_seq, seq)
        except ValueError:
            continue
    return max_seq + 1


def crop_all_rare(
    image,
    page: PageResult,
    out_dir: str | None = None,
) -> dict[str, Path]:
    """对一页所有 is_rare 的字框截图。返回 {char_id: 路径}。"""
    result = {}
    for ch in page.chars:
        if not ch.is_rare:
            continue
        path = crop_char_sample(image, page, ch.id, ch.char or "unknown", out_dir)
        if path:
            ch.sample_img = str(path)
            result[ch.id] = path
    return result