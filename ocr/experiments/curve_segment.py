"""星盘曲线字切分原型实验（spike，不改生产代码）。

按 `docs/TASKS_ENG_GAPS.md` 任务 D.3 的六步实现：

    1. 圆心估计    HoughCircles 候选 + 字框中心最小二乘圆拟合 refine
    2. 分环        框心到圆心的距离一维聚类 → ring
    3. 每字定向    朝向 = 圆心指向该字的半径方向；「头朝外」「头朝圆心」两种假设都试
    4. 重识别      按框 crop（外扩 4px）→ 旋转到正立 → PaddleOCR rec 单字识别
    5. 择优        原识别 vs 各旋转假设，取 conf 最高者，输出对比表
    6. 阅读序      按 (ring, 极角θ) 排序输出，而不是 (x, y)

诚实闸门（本文件与任务书的唯一出入，理由见 CURVE_REPORT.md §2）：
第 1 步会算出圆拟合的**相对残差**。残差超过 `MAX_RADIUS_RESIDUAL` 说明这一页的字
根本不在圆弧上（比如密排的分野表），此时第 2/3 步的「环」和「半径方向」是没有意义的
数字。脚本不会假装它成立——会明确报告假设不成立，并把角度假设退化为固定集
{0°,90°,180°,270°}（覆盖旋转的夹注），继续跑第 4/5 步，阅读序退回按列排。
这样无论版面是不是圆的，都能得到一张可判断的对比表。

用法：
    OCR_ROOT=data_work PYTHONPATH=src python experiments/curve_segment.py \
        data_work/sanche_pages/page_010.png --page page_010 --out /tmp/p010_curve.png

不修改 `src/gujiorc/` 下任何生产文件（任务书 D.6）。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gujiorc.ocr.preprocess import suppress_bleed_through  # noqa: E402

# 圆拟合相对残差（半径 std / 半径均值）超过此值，即判定「字不在圆弧上」。
# 真圆弧排字的字心到圆心距离几乎恒定，残差应远小于 10%；
# 实测 page_010（密排分野表）为 37.1%，前提不成立。
MAX_RADIUS_RESIDUAL = 0.10
# 圆弧假设不成立时的退化角度假设（覆盖竖排页里旋转的夹注/边注）
FALLBACK_ANGLES = (0.0, 90.0, 180.0, 270.0)
# 裁图外扩。实测配方对 rec 准确率影响显著：紧贴 pad4 与参照一致 96.7%，
# 而「加 20% 白边 + 3x 放大」准确率降到 93.3% 却把均置信从 0.92 抬到 0.96
# —— 置信度在不同裁法之间不可比，所以全程只用一种裁法，只在角度之间比较。
CROP_PAD = 4


# ── 第 1 步：圆心估计 ───────────────────────────────────────────────────

def hough_center(gray: np.ndarray) -> Optional[tuple[float, float, int]]:
    """HoughCircles 找候选圆心。返回 (cx, cy, 候选数)。"""
    blur = cv2.GaussianBlur(gray, (9, 9), 2)
    circles = cv2.HoughCircles(
        blur, cv2.HOUGH_GRADIENT, dp=1.2, minDist=60,
        param1=100, param2=30, minRadius=30, maxRadius=int(min(gray.shape[:2]) / 2),
    )
    if circles is None:
        return None
    cands = np.uint16(np.around(circles))[0]
    best = max(cands, key=lambda c: c[2])   # 取半径最大者（最外环）
    return float(best[0]), float(best[1]), len(cands)


def fit_circle(points: np.ndarray) -> Optional[tuple[float, float, float, float]]:
    """代数最小二乘圆拟合。返回 (cx, cy, 平均半径, 相对残差)。"""
    if len(points) < 3:
        return None
    x, y = points[:, 0], points[:, 1]
    xm, ym = float(x.mean()), float(y.mean())
    u, v = x - xm, y - ym
    Suu, Suv, Svv = float((u * u).sum()), float((u * v).sum()), float((v * v).sum())
    Suuu, Suvv = float((u ** 3).sum()), float((u * v * v).sum())
    Svvv, Svuu = float((v ** 3).sum()), float((v * u * u).sum())
    A = np.array([[Suu, Suv], [Suv, Svv]])
    if abs(np.linalg.det(A)) < 1e-9:
        return None
    uc, vc = np.linalg.solve(A, np.array([0.5 * (Suuu + Suvv), 0.5 * (Svvv + Svuu)]))
    cx, cy = xm + float(uc), ym + float(vc)
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    if not np.isfinite([cx, cy]).all() or r.mean() <= 0:
        return None
    return cx, cy, float(r.mean()), float(r.std() / r.mean())


# ── 第 2 步：分环 ───────────────────────────────────────────────────────

def cluster_rings(radii: np.ndarray, gap_factor: float = 1.5) -> np.ndarray:
    """按到圆心的距离做一维聚类。排序后在「显著大于典型间距」处断开成环。"""
    order = np.argsort(radii)
    diffs = np.diff(radii[order])
    if len(diffs) == 0:
        return np.zeros(len(radii), dtype=int)
    thresh = float(np.median(diffs)) * gap_factor + 1e-9
    ring_sorted = np.cumsum(np.concatenate([[0], (diffs > thresh).astype(int)]))
    rings = np.empty(len(radii), dtype=int)
    rings[order] = ring_sorted
    return rings


# ── 第 3 步：每字定向 ───────────────────────────────────────────────────

def polar_angle(cx: float, cy: float, x: float, y: float) -> float:
    """字心相对圆心的极角（度，数学方向：x 轴向右为 0，逆时针为正）。"""
    return float(np.degrees(np.arctan2(y - cy, x - cx)))


def radial_hypotheses(theta: float) -> tuple[float, float]:
    """两种头向假设下，把该字转回正立所需的旋转角。

    「头朝外」：字的上方指向远离圆心的方向，即字的局部上方 = 极角方向；
    「头朝圆心」：字的上方指向圆心，与前者相差 180°。
    """
    head_out = -(theta + 90.0)
    return head_out, head_out + 180.0


# ── 第 4 步：重识别 ─────────────────────────────────────────────────────

def crop_box(img: np.ndarray, box: dict, pad: int = CROP_PAD) -> np.ndarray:
    h, w = img.shape[:2]
    y0 = max(0, int(box["y"] - pad)); y1 = min(h, int(box["y"] + box["h"] + pad))
    x0 = max(0, int(box["x"] - pad)); x1 = min(w, int(box["x"] + box["w"] + pad))
    return img[y0:y1, x0:x1]


def rotate_upright(crop: np.ndarray, angle: float) -> np.ndarray:
    """把 crop 旋转 angle 度（白底补边，不裁掉笔画）。"""
    if abs(angle % 360.0) < 1e-6:
        return crop
    im = Image.fromarray(crop)
    return np.array(im.rotate(angle, expand=True, fillcolor=(255, 255, 255),
                              resample=Image.BICUBIC))


def batch_recognize(rec, crops: list[np.ndarray], batch: int = 64) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for i in range(0, len(crops), batch):
        chunk = [c for c in crops[i:i + batch] if c.size > 0]
        if not chunk:
            out.extend(("", 0.0) for _ in crops[i:i + batch])
            continue
        for r in rec.predict(chunk):
            out.append((str(r.get("rec_text", "") or "").strip(), float(r.get("rec_score", 0.0))))
    return out


def write_page_for_web(page: str, out_root: str, image: str, shape, boxes, rows, zero_label: str):
    """把择优结果写成 Web UI 能读的页 JSON，落到独立的 OCR_ROOT（不碰生产数据）。

    严守数据铁律：`orig_char` 保留**生产管线的原始识别**永不覆盖，`char` 放实验的
    择优结果，改动写进 `mapping`（含旋转角与来源假设），可逐字回退比对。
    被改动的字标 `status=corrected`，认不出的标 `unrecognized`。
    """
    import os
    from datetime import datetime, timezone
    prev_root = os.environ.get("OCR_ROOT")
    os.environ["OCR_ROOT"] = out_root
    try:
        # 延迟 import：paths 模块在 import 时读 OCR_ROOT
        import importlib
        from gujiorc.core import paths as _paths
        importlib.reload(_paths)
        from gujiorc.core.models import (
            CharBox, PageResult, STATUS_CORRECTED, STATUS_PENDING, STATUS_UNRECOGNIZED,
        )
        from gujiorc.core.storage import save_page_json
        from gujiorc.rare.detector import build_common_set, detect_rare_chars

        bx = {b["id"]: b for b in boxes}
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        chars = []
        for r in rows:
            b = bx[r["id"]]
            changed = r["best_char"] != r["orig_char"]
            chars.append(CharBox(
                id=r["id"], box=dict(b["box"]),
                char=r["best_char"],
                orig_char=r["orig_char"],        # 生产管线的识别，永不覆盖
                conf=r["best_conf"],
                status=(STATUS_UNRECOGNIZED if not r["best_char"]
                        else STATUS_CORRECTED if changed else STATUS_PENDING),
                mapping=({"target": r["best_char"], "from": r["orig_char"],
                          "source": f"curve_exp:{r['best_label']}", "ts": ts}
                         if changed else None),
                angle=0.0,
                extra={"curve_exp": {
                    "best_label": r["best_label"], "best_conf": round(r["best_conf"], 3),
                    "zero_char": r["zero_char"], "zero_conf": round(r["zero_conf"], 3),
                    "orig_conf": round(r["orig_conf"], 3),
                    "ring": r["ring"], "theta": round(r["theta"], 1),
                }},
            ))
        pr = PageResult(page=page, image=str(image), width=int(shape[1]), height=int(shape[0]),
                        chars=chars, lines=[],
                        extra={"source": "curve_segment experiment", "zero_label": zero_label})
        detect_rare_chars(pr, build_common_set())
        save_page_json(pr)
        print(f"\n实验结果页已写入 {out_root}/data/{page}.json（Web UI 可读）")
        print(f"  起第二个 Web 实例对比：")
        print(f"  OCR_ROOT={out_root} OCR_WEB_PORT=8001 PYTHONPATH=src .venv/bin/python local/app.py")
    finally:
        if prev_root is None:
            os.environ.pop("OCR_ROOT", None)
        else:
            os.environ["OCR_ROOT"] = prev_root


# ── 主流程 ──────────────────────────────────────────────────────────────

def load_boxes(page: str) -> list[dict]:
    """从生产管线已产出的 page JSON 取单字框（只读，不修改）。"""
    from gujiorc.core.storage import load_page_json
    pr = load_page_json(page)
    if pr is None:
        raise SystemExit(f"未找到 {page} 的 JSON，请先跑 workbench run --segment")
    return [{"id": c.id, "box": dict(c.box), "char": c.char, "conf": float(c.conf)}
            for c in pr.chars if c.char]


def main() -> int:
    ap = argparse.ArgumentParser(description="星盘曲线字切分实验（spike）")
    ap.add_argument("image", help="图片路径")
    ap.add_argument("--page", required=True, help="页号（如 page_010），用于取已有单字框")
    ap.add_argument("--out", default="/tmp/curve_out.png", help="标注图输出路径")
    ap.add_argument("--table", default="", help="对比表 CSV 输出路径（可选）")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 个字（调试用）")
    ap.add_argument("--no-bleed", action="store_true", help="不做背面透印抹除")
    ap.add_argument("--write-page", default="",
                    help="把择优结果写成页 JSON 到指定 OCR_ROOT（独立目录，供 Web UI 对比）")
    args = ap.parse_args()

    img_path = Path(args.image)
    if not img_path.exists():
        raise SystemExit(f"图片不存在: {img_path}")

    rgb = np.array(Image.open(img_path).convert("RGB"))
    if not args.no_bleed:
        rgb, _ = suppress_bleed_through(rgb)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    boxes = load_boxes(args.page)
    print(f"页 {args.page}：取到 {len(boxes)} 个有字的单字框，图幅 {gray.shape[1]}x{gray.shape[0]}\n")

    # 第 1 步 ────────────────────────────────────────────────
    print("【第1步】圆心估计")
    hc = hough_center(gray)
    if hc:
        print(f"  HoughCircles：{hc[2]} 个候选圆，最大半径者圆心=({hc[0]:.0f},{hc[1]:.0f})")
        if hc[2] > 20:
            print(f"  ⚠ 候选圆多达 {hc[2]} 个 —— 密排文字造成的噪声投票，真星盘只有几个同心环")
    else:
        print("  HoughCircles：未找到任何圆")

    centers = np.array([[b["box"]["x"] + b["box"]["w"] / 2,
                         b["box"]["y"] + b["box"]["h"] / 2] for b in boxes])
    fit = fit_circle(centers)
    if fit is None:
        raise SystemExit("圆拟合失败（点太少或退化）")
    cx, cy, r_mean, residual = fit
    print(f"  字框中心最小二乘圆拟合：圆心=({cx:.0f},{cy:.0f}) 平均半径={r_mean:.0f}")
    print(f"  半径相对残差={residual:.1%}（阈值 {MAX_RADIUS_RESIDUAL:.0%}）")

    arc_valid = residual <= MAX_RADIUS_RESIDUAL
    if arc_valid:
        print("  ✅ 圆弧假设成立，按半径方向定向\n")
    else:
        print(f"  ❌ 圆弧假设不成立：字心到圆心的距离散布达 ±{residual:.0%}，字不在圆弧上。")
        print(f"     第2/3步的「环」与「半径方向」在本页没有意义，不予采用。")
        print(f"     角度假设退化为固定集 {FALLBACK_ANGLES}，阅读序退回按列排。\n")

    # 第 2 步 ────────────────────────────────────────────────
    radii = np.sqrt((centers[:, 0] - cx) ** 2 + (centers[:, 1] - cy) ** 2)
    thetas = np.array([polar_angle(cx, cy, p[0], p[1]) for p in centers])
    if arc_valid:
        rings = cluster_rings(radii)
        print(f"【第2步】分环：{rings.max() + 1} 个环，各环字数 "
              f"{[int((rings == k).sum()) for k in range(rings.max() + 1)]}\n")
    else:
        rings = np.zeros(len(boxes), dtype=int)
        print("【第2步】分环：跳过（圆弧假设不成立）\n")

    # --limit 只截断后续的 rec 工作量，几何量已用全部框算完（否则子集会让圆拟合虚假成立）
    if args.limit:
        keep = list(range(min(args.limit, len(boxes))))
        boxes = [boxes[i] for i in keep]
        thetas = thetas[keep]
        rings = rings[keep]
        print(f"⚠ --limit {args.limit}：几何量用全部框算，rec 只跑前 {len(boxes)} 字\n")

    # 第 3 步 ────────────────────────────────────────────────
    if arc_valid:
        hypotheses = [(0.0, "原样")]
        print("【第3步】每字定向：两种头向假设（朝外 / 朝圆心）\n")
    else:
        hypotheses = [(a, f"{a:.0f}°") for a in FALLBACK_ANGLES]
        print(f"【第3步】每字定向：退化为固定角度 {[h[1] for h in hypotheses]}\n")

    # 第 4 步 ────────────────────────────────────────────────
    print("【第4步】逐字 crop → 旋转 → rec 重识别")
    from paddleocr import TextRecognition
    t0 = time.time()
    rec = TextRecognition()
    print(f"  rec 模型加载 {time.time() - t0:.1f}s")

    base_crops = [crop_box(rgb, b["box"]) for b in boxes]
    variants: list[tuple[str, list[float]]] = []   # (标签, 每字旋转角)
    if arc_valid:
        out_ang = [radial_hypotheses(t)[0] for t in thetas]
        in_ang = [radial_hypotheses(t)[1] for t in thetas]
        variants = [("0°原样", [0.0] * len(boxes)),
                    ("头朝外", out_ang), ("头朝圆心", in_ang)]
    else:
        variants = [(lab, [a] * len(boxes)) for a, lab in hypotheses]

    results: dict[str, list[tuple[str, float]]] = {}
    for label, angles in variants:
        crops = [rotate_upright(c, a) for c, a in zip(base_crops, angles)]
        t0 = time.time()
        results[label] = batch_recognize(rec, crops)
        print(f"  {label:<8} {len(crops)} 字，{time.time() - t0:.1f}s "
              f"（{(time.time() - t0) / max(len(crops),1) * 1000:.0f}ms/字）")
    print()

    # 第 5 步 ────────────────────────────────────────────────
    print("【第5步】择优（各旋转假设间取 conf 最高）")
    rows = []
    for i, b in enumerate(boxes):
        cand = [(lab, results[lab][i][0], results[lab][i][1]) for lab in results]
        best_lab, best_char, best_conf = max(cand, key=lambda t: t[2])
        rows.append({
            "id": b["id"], "ring": int(rings[i]), "theta": float(thetas[i]),
            "orig_char": b["char"], "orig_conf": b["conf"],
            "best_label": best_lab, "best_char": best_char, "best_conf": best_conf,
            "zero_char": results[variants[0][0]][i][0],
            "zero_conf": results[variants[0][0]][i][1],
        })

    n = len(rows)
    rotated_wins = sum(1 for r in rows if r["best_label"] != variants[0][0])
    changed = sum(1 for r in rows if r["best_char"] != r["orig_char"])
    conf_up = sum(1 for r in rows if r["best_conf"] > r["orig_conf"])
    agree0 = sum(1 for r in rows if r["zero_char"] == r["orig_char"])
    print(f"  总字数              : {n}")
    print(f"  0°单字重识别与原识别一致: {agree0} ({agree0/n:.1%})")
    print(f"  最优来自旋转假设     : {rotated_wins} ({rotated_wins/n:.1%})")
    print(f"  择优后字内容改变     : {changed} ({changed/n:.1%})")
    print(f"  择优后 conf 高于原值 : {conf_up} ({conf_up/n:.1%})")
    print(f"  原识别均 conf        : {np.mean([r['orig_conf'] for r in rows]):.3f}")
    print(f"  0°重识别均 conf      : {np.mean([r['zero_conf'] for r in rows]):.3f}")
    print(f"  择优后均 conf        : {np.mean([r['best_conf'] for r in rows]):.3f}")
    print("  ⚠ 原 conf 来自**行级**识别（整行一个分数摊给该行每个字），"
          "与单字 conf 不同量纲，只可作参考不可直接判优劣。\n")

    # ── 两个揭穿「置信度上升」假象的指标 ──────────────────────────────
    # 指标1：单字框吐出多字 = 明确的垃圾输出。旋转后的汉字常被读成一串字。
    multi_zero = sum(1 for r in rows if len(r["zero_char"]) > 1)
    multi_best = sum(1 for r in rows if len(r["best_char"]) > 1)
    empty_best = sum(1 for r in rows if not r["best_char"])
    print("【校验1】单字框吐出多个字（明确的垃圾输出）")
    print(f"  0°重识别 : {multi_zero} ({multi_zero/n:.1%})   择优后: {multi_best} ({multi_best/n:.1%})"
          f"   择优后为空: {empty_best} ({empty_best/n:.1%})")
    if multi_best:
        bad = [r for r in rows if len(r["best_char"]) > 1][:8]
        print("  例：" + "  ".join(
            f"{r['orig_char']}→{r['best_char']}({r['best_conf']:.2f})" for r in bad))
    print()

    # 指标2：代理真值。原识别 conf>=0.95 的字极可能是对的（在正常竖排页上实测
    # 与单字重识别一致率 96.7%），拿它当参照，看算法是把它们改对了还是改坏了。
    trusted = [r for r in rows if r["orig_conf"] >= 0.95]
    print(f"【校验2】代理真值对照（原识别 conf>=0.95 的 {len(trusted)} 字，极可能本来就是对的）")
    if trusted:
        keep0 = sum(1 for r in trusted if r["zero_char"] == r["orig_char"])
        keepb = sum(1 for r in trusted if r["best_char"] == r["orig_char"])
        print(f"  0°重识别保住   : {keep0}/{len(trusted)} ({keep0/len(trusted):.1%})")
        print(f"  择优后保住     : {keepb}/{len(trusted)} ({keepb/len(trusted):.1%})"
              f"  → **改坏 {len(trusted)-keepb} 个**")
        broken = [r for r in trusted if r["best_char"] != r["orig_char"]][:10]
        if broken:
            print("  被改坏的例子：" + "  ".join(
                f"{r['orig_char']}({r['orig_conf']:.2f})→{r['best_char'] or '□'}"
                f"({r['best_conf']:.2f},{r['best_label']})" for r in broken))
    else:
        print("  本页没有 conf>=0.95 的字，无法做代理真值对照")
    print()

    # 第 6 步 ────────────────────────────────────────────────
    if arc_valid:
        rows.sort(key=lambda r: (r["ring"], r["theta"]))
        print("【第6步】阅读序：按 (ring, 极角θ) 排序")
    else:
        bx = {b["id"]: b["box"] for b in boxes}
        rows.sort(key=lambda r: (-bx[r["id"]]["x"], bx[r["id"]]["y"]))
        print("【第6步】阅读序：退回按列排（x 由右至左、列内 y 由上至下）")
    print()

    # 对比表（前 30 行）
    print("对比表（前 30 字；★=最优来自旋转）")
    print(f"{'环':>2} {'θ':>7} {'原(行级)':>10} {'0°单字':>10} {'择优':>10} {'来源':>8}")
    for r in rows[:30]:
        star = "★" if r["best_label"] != variants[0][0] else " "
        cell_o = f"{r['orig_char'] or '□'} {r['orig_conf']:.2f}"
        cell_z = f"{r['zero_char'] or '□'} {r['zero_conf']:.2f}"
        cell_b = f"{r['best_char'] or '□'} {r['best_conf']:.2f}"
        print(f"{r['ring']:>2} {r['theta']:>7.1f} {cell_o:>10} {cell_z:>10} "
              f"{cell_b:>10} {star}{r['best_label']:>7}")

    if args.table:
        import csv
        with open(args.table, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f"\n完整对比表已写入 {args.table}")

    if args.write_page:
        write_page_for_web(args.page, args.write_page, args.image, rgb.shape, boxes, rows,
                           variants[0][0])

    # 标注图：绿=择优与原识别一致，橙=内容变了，红=择优也认不出
    from PIL import ImageDraw, ImageFont
    vis = Image.fromarray(rgb).convert("RGB")
    dr = ImageDraw.Draw(vis)
    fp = "/System/Library/Fonts/STHeiti Medium.ttc"
    font = ImageFont.truetype(fp, 16) if Path(fp).exists() else None
    bx = {b["id"]: b["box"] for b in boxes}
    for r in rows:
        b = bx[r["id"]]
        col = (0, 170, 0) if r["best_char"] == r["orig_char"] else (
            (255, 140, 0) if r["best_char"] else (220, 0, 0))
        dr.rectangle([b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]], outline=col, width=2)
        if font and r["best_char"] != r["orig_char"]:
            dr.text((b["x"] + b["w"] + 2, b["y"]), r["best_char"] or "□", fill=col, font=font)
    if arc_valid:
        dr.ellipse([cx - r_mean, cy - r_mean, cx + r_mean, cy + r_mean],
                   outline=(0, 100, 255), width=2)
        dr.line([cx - 12, cy, cx + 12, cy], fill=(0, 100, 255), width=2)
        dr.line([cx, cy - 12, cx, cy + 12], fill=(0, 100, 255), width=2)
    vis.save(args.out)
    print(f"标注图已写入 {args.out}（绿=与原一致，橙=内容变了，红=认不出）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
